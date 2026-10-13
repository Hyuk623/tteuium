"""The whole light flow: budgets, scenarios, geometry variants, validation, CLI."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import LIGHT_FIXTURE_DIR, light_scene_payload
from tomato3d.config import Settings
from tomato3d.io.schemas import (
    GEOMETRY_VARIANT_COMPARISON_CSV_COLUMNS,
    LEAF_LIGHT_CSV_COLUMNS,
    LEAF_PATCHES_CSV_COLUMNS,
    LEAF_TRIANGLE_LIGHT_CSV_COLUMNS,
    PLANT_LIGHT_CSV_COLUMNS,
    PPFD_READINGS_CSV_COLUMNS,
    SCENARIO_SUMMARY_CSV_COLUMNS,
    SENSOR_PREDICTIONS_CSV_COLUMNS,
    UNAVAILABLE,
    VALIDATION_CSV_COLUMNS,
    LightRunSummary,
    LightScene,
    load_json_model,
    validate_model,
)
from tomato3d.io.tables import read_table, write_table
from tomato3d.light import pipeline
from tomato3d.light.scene import LightInputError, load_scene

EXAMPLE_SCENE = LIGHT_FIXTURE_DIR / "light_scene.example.json"
EXAMPLE_PATCHES = LIGHT_FIXTURE_DIR / "leaf_patches.example.csv"
EXAMPLE_READINGS = LIGHT_FIXTURE_DIR / "ppfd_readings.example.csv"
_CREATED_AT = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def _run(scene: LightScene, geometry: list[Path], readings: Path | None = None, **kwargs):
    return pipeline.run_light(
        scene=scene,
        scene_path=Path("scene.json"),
        geometry_paths=geometry,
        readings_path=readings,
        reference_variant_id=kwargs.get("reference_variant_id"),
        calibration_variant_id=kwargs.get("calibration_variant_id", "no_plants"),
        run_id="test",
        created_at=_CREATED_AT,
    )


@pytest.fixture(scope="module")
def example_result() -> pipeline.LightRunResult:
    return _run(
        load_scene(EXAMPLE_SCENE),
        [EXAMPLE_PATCHES],
        EXAMPLE_READINGS,
        reference_variant_id="multiview_41",
    )


def _row(rows: list[dict[str, str]], **match: str) -> dict[str, str]:
    found = [row for row in rows if all(row[k] == v for k, v in match.items())]
    assert len(found) == 1, f"expected one row for {match}, found {len(found)}"
    return found[0]


def _patch(
    organ_id: str, z_mm: float, area_mm2: float = 100.0, plant_id: str = "P", variant: str = "v"
) -> dict[str, str]:
    return {
        "plant_id": plant_id,
        "session_id": f"{plant_id}_20260920_0900",
        "geometry_variant_id": variant,
        "geometry_source": "manual",
        "organ_id": organ_id,
        "centroid_x_mm": "0",
        "centroid_y_mm": "0",
        "centroid_z_mm": repr(z_mm),
        "area_mm2": repr(area_mm2),
        "normal_tilt_deg": "0",
        "normal_azimuth_deg": "0",
        "length_to_width_ratio": "1",
    }


# --------------------------------------------------------------------------------------
# Budgets
# --------------------------------------------------------------------------------------


def test_a_small_leaf_under_a_lamp_matches_the_hand_calculation(tmp_path: Path) -> None:
    """E = flux / (pi d**2); intercepted = E * area; absorbed = absorptance * intercepted."""
    scene = validate_model(light_scene_payload(plants=["P"], subdivisions=4), LightScene)
    geometry = tmp_path / "leaf_patches.csv"
    write_table(geometry, [_patch("leaf_001", 500.0, area_mm2=4.0)], LEAF_PATCHES_CSV_COLUMNS)
    result = _run(scene, [geometry])
    leaf = _row(result.leaf_rows, geometry_variant_id="v")
    expected_ppfd = 100.0 / (math.pi * 0.5**2)
    assert float(leaf["ppfd_mean_full_output_umol_m2_s"]) == pytest.approx(expected_ppfd, rel=1e-4)
    intercepted = float(leaf["intercepted_full_output_umol_s"])
    assert intercepted == pytest.approx(expected_ppfd * 4.0e-6, rel=1e-4)
    assert float(leaf["absorbed_full_output_umol_s"]) == pytest.approx(0.85 * intercepted)
    assert float(leaf["dli_mol_m2_day"]) == pytest.approx(expected_ppfd * 16 * 3600 / 1e6, rel=1e-4)
    assert float(leaf["occlusion_loss_fraction"]) == 0.0
    assert float(leaf["adaxial_incident_fraction"]) == 1.0


def test_a_leaf_above_another_shades_it_by_the_transmittance(tmp_path: Path) -> None:
    scene = validate_model(light_scene_payload(plants=["P"], transmittance=0.1), LightScene)
    geometry = tmp_path / "leaf_patches.csv"
    write_table(
        geometry,
        [_patch("upper", 600.0, area_mm2=10000.0), _patch("lower", 300.0, area_mm2=1.0)],
        LEAF_PATCHES_CSV_COLUMNS,
    )
    result = _run(scene, [geometry])
    lower = _row(result.leaf_rows, organ_id="lower")
    assert float(lower["occlusion_loss_fraction"]) == pytest.approx(0.9, rel=1e-9)


def test_absorbed_photons_never_exceed_emitted_ones(example_result) -> None:
    for budget in example_result.budgets:
        canopy = budget.canopy
        assert 0.0 <= canopy.absorbed_mol_day <= canopy.intercepted_mol_day
        assert canopy.intercepted_mol_day <= canopy.emitted_mol_day


def test_the_empty_space_is_the_no_plant_baseline(example_result) -> None:
    empty = _row(
        example_result.scenario_rows, scenario_id="as_built", geometry_variant_id="no_plants"
    )
    assert empty["n_leaves"] == "0"
    assert float(empty["absorbed_mol_day"]) == 0.0
    assert empty["leaf_ppfd_mean_umol_m2_s"] == UNAVAILABLE


def test_raising_the_lamps_changes_light_not_electricity(example_result) -> None:
    rows = example_result.scenario_rows
    built = _row(rows, scenario_id="as_built", geometry_variant_id="multiview_41")
    raised = _row(rows, scenario_id="leds_up_100mm", geometry_variant_id="multiview_41")
    assert float(raised["leaf_ppfd_mean_umol_m2_s"]) < float(built["leaf_ppfd_mean_umol_m2_s"])
    assert raised["electricity_kwh_day"] == built["electricity_kwh_day"]
    assert float(raised["delta_absorbed_mol_day_vs_as_built"]) < 0.0
    assert float(built["delta_absorbed_mol_day_vs_as_built"]) == 0.0


def test_unknown_absorptance_leaves_absorbed_light_unavailable(tmp_path: Path) -> None:
    scene = validate_model(light_scene_payload(plants=["P"], absorptance=None), LightScene)
    geometry = tmp_path / "leaf_patches.csv"
    write_table(geometry, [_patch("leaf_001", 500.0)], LEAF_PATCHES_CSV_COLUMNS)
    result = _run(scene, [geometry])
    leaf = _row(result.leaf_rows, geometry_variant_id="v")
    assert leaf["absorbed_mol_day"] == UNAVAILABLE
    assert float(leaf["intercepted_full_output_umol_s"]) > 0.0
    summary = _row(result.scenario_rows, geometry_variant_id="v")
    assert summary["absorbed_umol_per_j"] == UNAVAILABLE
    assert any("absorptance" in warning for warning in result.summary.warnings)


def test_leaves_at_lamp_height_are_warned_about(tmp_path: Path) -> None:
    scene = validate_model(light_scene_payload(plants=["P"]), LightScene)
    geometry = tmp_path / "leaf_patches.csv"
    write_table(geometry, [_patch("leaf_001", 1100.0)], LEAF_PATCHES_CSV_COLUMNS)
    result = _run(scene, [geometry])
    assert any("at or above fixture L1" in warning for warning in result.summary.warnings)


def test_geometry_for_a_plant_the_scene_does_not_place_is_refused(tmp_path: Path) -> None:
    scene = validate_model(light_scene_payload(plants=[]), LightScene)
    geometry = tmp_path / "leaf_patches.csv"
    write_table(geometry, [_patch("leaf_001", 500.0)], LEAF_PATCHES_CSV_COLUMNS)
    with pytest.raises(LightInputError, match="does not place"):
        _run(scene, [geometry])


# --------------------------------------------------------------------------------------
# Geometry variants
# --------------------------------------------------------------------------------------


def test_a_reduced_view_variant_is_compared_leaf_by_leaf(example_result) -> None:
    rows = [r for r in example_result.variant_rows if r["scenario_id"] == "as_built"]
    assert {r["plant_id"] for r in rows} == {"DT-001", "DT-002"}
    for row in rows:
        assert row["candidate_variant_id"] == "side12_T0"
        assert row["n_leaves_matched"] == "4"
        assert row["n_leaves_reference_only"] == "1"
        assert row["n_leaves_candidate_only"] == "0"
        assert float(row["candidate_leaf_area_mm2"]) < float(row["reference_leaf_area_mm2"])


def test_an_unknown_reference_variant_is_refused() -> None:
    with pytest.raises(LightInputError, match="reference variant"):
        _run(load_scene(EXAMPLE_SCENE), [EXAMPLE_PATCHES], reference_variant_id="missing")


# --------------------------------------------------------------------------------------
# Validation against readings
# --------------------------------------------------------------------------------------


def test_every_variant_is_scored_on_the_same_evaluation_readings(example_result) -> None:
    wanted = ("as_built", "evaluation", "all")
    evaluation = [
        row
        for row in example_result.validation_rows
        if (row["scenario_id"], row["split_role"], row["subset"]) == wanted
    ]
    variants = {row["geometry_variant_id"] for row in evaluation}
    assert variants == {"no_plants", "multiview_41", "side12_T0"}
    assert len({row["n_used"] for row in evaluation}) == 1
    assert len({row["calibration_factor"] for row in evaluation}) == 1
    assert example_result.summary.calibration_factor_by_scenario["leds_up_100mm"] == UNAVAILABLE


def test_the_calibration_factor_ignores_evaluation_readings(tmp_path: Path, example_result) -> None:
    rows = read_table(EXAMPLE_READINGS, PPFD_READINGS_CSV_COLUMNS)
    for row in rows:
        if row["split_role"] == "evaluation":
            row["ppfd_umol_m2_s"] = repr(float(row["ppfd_umol_m2_s"]) * 3.0)
    altered = tmp_path / "ppfd_readings.csv"
    write_table(altered, rows, PPFD_READINGS_CSV_COLUMNS)
    result = _run(
        load_scene(EXAMPLE_SCENE), [EXAMPLE_PATCHES], altered, reference_variant_id="multiview_41"
    )
    before = example_result.summary.calibration_factor_by_scenario["as_built"]
    after = result.summary.calibration_factor_by_scenario["as_built"]
    assert after == pytest.approx(before, rel=1e-12)
    key = {
        "scenario_id": "as_built",
        "geometry_variant_id": "multiview_41",
        "split_role": "evaluation",
        "subset": "all",
    }
    mae_after = _row(result.validation_rows, **key)["mae_umol_m2_s"]
    assert mae_after != _row(example_result.validation_rows, **key)["mae_umol_m2_s"]


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("setup_id", "other_shelf", "setup_id"),
        ("scenario_id", "never_built", "scenario_id"),
        ("all_fixtures_full_output", "no", "full output"),
        ("z_mm", UNAVAILABLE, "cannot be placed"),
        ("split_role", "training", "split_role"),
    ],
)
def test_inconsistent_readings_are_refused(
    tmp_path: Path, column: str, value: str, message: str
) -> None:
    rows = read_table(EXAMPLE_READINGS, PPFD_READINGS_CSV_COLUMNS)
    rows[0][column] = value
    path = tmp_path / "ppfd_readings.csv"
    write_table(path, rows, PPFD_READINGS_CSV_COLUMNS)
    with pytest.raises(LightInputError, match=message):
        _run(load_scene(EXAMPLE_SCENE), [], path)


def test_an_unavailable_reading_is_counted_not_scored(tmp_path: Path) -> None:
    rows = read_table(EXAMPLE_READINGS, PPFD_READINGS_CSV_COLUMNS)
    evaluation = [row for row in rows if row["split_role"] == "evaluation"]
    evaluation[0]["ppfd_umol_m2_s"] = UNAVAILABLE
    path = tmp_path / "ppfd_readings.csv"
    write_table(path, rows, PPFD_READINGS_CSV_COLUMNS)
    result = _run(load_scene(EXAMPLE_SCENE), [], path)
    row = _row(
        result.validation_rows,
        geometry_variant_id="no_plants",
        split_role="evaluation",
        subset="all",
    )
    assert row["n_measured_unavailable"] == "1"
    assert int(row["n_used"]) == len(evaluation) - 1


def test_ppfd_bins_are_reported_only_when_set(tmp_path: Path) -> None:
    payload = json.loads(EXAMPLE_SCENE.read_text(encoding="utf-8"))
    payload["validation"]["ppfd_bin_edges_umol_m2_s"] = [0.0, 150.0, 1000.0]
    scene = validate_model(payload, LightScene)
    result = _run(scene, [], EXAMPLE_READINGS)
    subsets = {row["subset"] for row in result.validation_rows}
    assert subsets == {"all", "[0,150)", "[150,1000)"}


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def test_cli_writes_every_table_and_never_overwrites_a_run(
    clean_settings: Settings, capsys
) -> None:
    from tomato3d.cli.run_light import main

    argv = [
        "--scene", str(EXAMPLE_SCENE),
        "--geometry", str(EXAMPLE_PATCHES),
        "--readings", str(EXAMPLE_READINGS),
        "--reference-variant", "multiview_41",
        "--run-id", "cli_test",
    ]
    assert main(argv) == 0
    run_dir = clean_settings.light_runs_dir / "cli_test"
    contracts = {
        pipeline.LEAF_TRIANGLE_LIGHT_FILENAME: LEAF_TRIANGLE_LIGHT_CSV_COLUMNS,
        pipeline.LEAF_LIGHT_FILENAME: LEAF_LIGHT_CSV_COLUMNS,
        pipeline.PLANT_LIGHT_FILENAME: PLANT_LIGHT_CSV_COLUMNS,
        pipeline.SCENARIO_SUMMARY_FILENAME: SCENARIO_SUMMARY_CSV_COLUMNS,
        pipeline.SENSOR_PREDICTIONS_FILENAME: SENSOR_PREDICTIONS_CSV_COLUMNS,
        pipeline.VALIDATION_FILENAME: VALIDATION_CSV_COLUMNS,
        pipeline.GEOMETRY_VARIANT_COMPARISON_FILENAME: GEOMETRY_VARIANT_COMPARISON_CSV_COLUMNS,
    }
    for filename, columns in contracts.items():
        assert read_table(run_dir / filename, columns), f"{filename} is empty"
    summary = load_json_model(run_dir / pipeline.RUN_SUMMARY_FILENAME, LightRunSummary)
    assert summary.reference_variant_id == "multiview_41"
    assert any("reflect" in limit for limit in summary.model_limits)
    assert "written" in capsys.readouterr().out

    assert main(argv) == 2
    assert not [p for p in run_dir.parent.iterdir() if p.name.startswith(".light-staging-")]


def test_cli_refuses_a_missing_scene(clean_settings: Settings) -> None:
    from tomato3d.cli.run_light import main

    assert main(["--scene", str(LIGHT_FIXTURE_DIR / "missing.json"), "--run-id", "x"]) == 2
    assert not (clean_settings.light_runs_dir / "x").exists()


def test_light_scene_defaults_to_the_config_dir(clean_settings: Settings) -> None:
    assert clean_settings.light_scene_path.parent == clean_settings.config_dir
