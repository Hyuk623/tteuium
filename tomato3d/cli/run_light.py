"""Leaf light-use run: lamps + leaf geometry (+ PPFD readings) -> light, energy, errors.

    python -m tomato3d.cli.run_light --scene config/light_scene.json \\
        --geometry data/derived/.../leaf_surfaces.csv data/records/_light/leaf_patches.csv \\
        --readings data/records/_light/ppfd_readings.csv \\
        --reference-variant multiview_41 --run-id pilot_0920

Writes into ``<data_root>/outputs/light/<run_id>/``:

    run_summary.json                 inputs and their provenance, limits, warnings
    leaf_triangle_light.csv          the leaf light map
    leaf_light.csv / plant_light.csv per-leaf / per-plant light
    scenario_summary.csv             headline numbers per arrangement x geometry variant
    sensor_predictions.csv           predicted vs measured PPFD per reading
    validation.csv                   MAE / RMSE / bias, calibration vs evaluation
    geometry_variant_comparison.csv  each geometry variant against the reference

The run folder is written to a staging folder and moved into place only when complete,
and an existing run folder is never overwritten.

Exit codes: ``0`` success, ``2`` a hard failure (a file fails its schema, inputs are
inconsistent, the run folder already exists).
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from tomato3d.config import Settings, get_settings
from tomato3d.io.schemas import (
    AS_BUILT_SCENARIO_ID,
    GEOMETRY_VARIANT_COMPARISON_CSV_COLUMNS,
    LEAF_LIGHT_CSV_COLUMNS,
    LEAF_TRIANGLE_LIGHT_CSV_COLUMNS,
    NO_PLANTS_VARIANT_ID,
    PLANT_LIGHT_CSV_COLUMNS,
    SCENARIO_SUMMARY_CSV_COLUMNS,
    SENSOR_PREDICTIONS_CSV_COLUMNS,
    VALIDATION_CSV_COLUMNS,
    SchemaError,
    dump_json_model,
)
from tomato3d.io.tables import write_table
from tomato3d.light import pipeline
from tomato3d.light.scene import load_scene
from tomato3d.logging_setup import configure_logging

logger = logging.getLogger(__name__)

_STAGING_PREFIX = ".light-staging-"
_RUN_ID_FORMAT = "%Y%m%d_%H%M%S"


class RunFolderExistsError(SchemaError):
    """The run folder already exists; a run is never written over another."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tomato3d.cli.run_light",
        description=(
            "Direct LED light on reconstructed or simplified leaves: per-leaf PPFD, DLI, "
            "absorbed photons, electricity, and error against quantum-sensor readings."
        ),
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=None,
        help="Light scene JSON (default: <TOMATO3D_CONFIG_DIR>/light_scene.json).",
    )
    parser.add_argument(
        "--geometry",
        type=Path,
        nargs="*",
        default=[],
        help="leaf_surfaces.csv and/or leaf_patches.csv files (board frame). "
        f"The empty space '{NO_PLANTS_VARIANT_ID}' is always included.",
    )
    parser.add_argument(
        "--readings", type=Path, default=None, help="ppfd_readings.csv (grow frame)."
    )
    parser.add_argument(
        "--reference-variant",
        default=None,
        help="Geometry variant the others are compared against (e.g. multiview_41).",
    )
    parser.add_argument(
        "--calibration-variant",
        default=NO_PLANTS_VARIANT_ID,
        help="Geometry variant whose predictions the lamp calibration factor is fitted to "
        f"(default: {NO_PLANTS_VARIANT_ID}).",
    )
    parser.add_argument(
        "--run-id", default=None, help="Run folder name (default: current local time)."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Run folder (default: <TOMATO3D_DATA_ROOT>/outputs/light/<run_id>).",
    )
    return parser


def _publish(result: pipeline.LightRunResult, out_dir: Path) -> None:
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=_STAGING_PREFIX, dir=out_dir.parent))
    try:
        dump_json_model(staging / pipeline.RUN_SUMMARY_FILENAME, result.summary)
        tables = (
            (
                pipeline.LEAF_TRIANGLE_LIGHT_FILENAME,
                result.triangle_rows,
                LEAF_TRIANGLE_LIGHT_CSV_COLUMNS,
            ),
            (pipeline.LEAF_LIGHT_FILENAME, result.leaf_rows, LEAF_LIGHT_CSV_COLUMNS),
            (pipeline.PLANT_LIGHT_FILENAME, result.plant_rows, PLANT_LIGHT_CSV_COLUMNS),
            (
                pipeline.SCENARIO_SUMMARY_FILENAME,
                result.scenario_rows,
                SCENARIO_SUMMARY_CSV_COLUMNS,
            ),
            (
                pipeline.SENSOR_PREDICTIONS_FILENAME,
                result.sensor_rows,
                SENSOR_PREDICTIONS_CSV_COLUMNS,
            ),
            (pipeline.VALIDATION_FILENAME, result.validation_rows, VALIDATION_CSV_COLUMNS),
            (
                pipeline.GEOMETRY_VARIANT_COMPARISON_FILENAME,
                result.variant_rows,
                GEOMETRY_VARIANT_COMPARISON_CSV_COLUMNS,
            ),
        )
        for filename, rows, columns in tables:
            write_table(staging / filename, rows, columns)
        staging.replace(out_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _print_summary(result: pipeline.LightRunResult, out_dir: Path) -> None:
    summary = result.summary
    print(f"setup                      {summary.setup_id}")
    print(f"run                        {summary.run_id}")
    print(f"scenarios                  {', '.join(summary.scenario_ids)}")
    print(
        "geometry variants          "
        + ", ".join(v.geometry_variant_id for v in summary.geometry_variants)
    )
    print()
    print(
        f"{'scenario':<22}{'variant':<22}{'absorbed mol/d':>15}{'of emitted':>12}"
        f"{'kWh/d':>12}{'umol/J':>12}{'leaf PPFD':>12}"
    )
    for row in result.scenario_rows:
        print(
            f"{row['scenario_id']:<22}{row['geometry_variant_id']:<22}"
            f"{_short(row['absorbed_mol_day']):>15}"
            f"{_short(row['absorbed_fraction_of_emitted']):>12}"
            f"{_short(row['electricity_kwh_day']):>12}"
            f"{_short(row['absorbed_umol_per_j']):>12}"
            f"{_short(row['leaf_ppfd_mean_umol_m2_s']):>12}"
        )
    evaluation = [
        row
        for row in result.validation_rows
        if row["split_role"] == "evaluation" and row["subset"] == "all"
        and row["scenario_id"] == AS_BUILT_SCENARIO_ID
    ]
    if evaluation:
        print()
        print(
            f"{'evaluation readings, as built':<44}{'n':>4}{'MAE':>12}{'bias':>12}"
            f"{'cal. MAE':>12}"
        )
        for row in evaluation:
            print(
                f"{row['geometry_variant_id']:<44}{row['n_used']:>4}"
                f"{_short(row['mae_umol_m2_s']):>12}{_short(row['bias_umol_m2_s']):>12}"
                f"{_short(row['calibrated_mae_umol_m2_s']):>12}"
            )
    print()
    print(f"inputs not observed on rig {len(summary.non_observed_inputs)}")
    print(f"warnings                   {len(summary.warnings)}")
    for warning in summary.warnings:
        print(f"  - {warning}")
    print(f"written                    {out_dir}")


def _short(cell: str) -> str:
    try:
        return f"{float(cell):.4g}"
    except ValueError:
        return cell


def run(args: argparse.Namespace, settings: Settings) -> int:
    scene_path = args.scene or settings.light_scene_path
    run_id = args.run_id or datetime.now().strftime(_RUN_ID_FORMAT)
    out_dir = args.out or settings.light_runs_dir / run_id
    if out_dir.exists():
        raise RunFolderExistsError(f"run folder {out_dir} already exists; choose another --run-id")

    scene = load_scene(scene_path)
    result = pipeline.run_light(
        scene=scene,
        scene_path=scene_path,
        geometry_paths=args.geometry,
        readings_path=args.readings,
        reference_variant_id=args.reference_variant,
        calibration_variant_id=args.calibration_variant,
        run_id=run_id,
        created_at=datetime.now().astimezone(),
    )
    _publish(result, out_dir)
    _print_summary(result, out_dir)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        return run(args, settings)
    except SchemaError as exc:
        logger.error("%s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
