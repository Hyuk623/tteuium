"""Plant structure from the existing P3 engine (imported read-only from ``tools/``).

The P3 engine (``tools/probabilistic_compound_growth.py``) is an assumption-conditioned
growth forecaster. Here it is fed an explicitly synthetic origin (a short stem with one
first true leaf) and a synthetic parameter particle drawn from ``generator_config.json``;
one trajectory decoded at ``plant_age_days`` gives the stem polyline and every compound
leaf's attachment, direction, rachis length and left/right extents.

Frame: ``plant_local_mm`` - origin at the soil surface on the stem axis, ``+Z`` up, mm.
:mod:`tomato3d.synth.scene` places it on the board.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.synth import GENERATOR_VERSION, ORIGIN
from tomato3d.synth.config import constant, make_rng, sample_range

GRAPH_SCHEMA = "synth-plant-graph-1"
LOCAL_FRAME = "plant_local_mm"
#: Optional integer range (cell O, 2026-10-08): determinate cap on compounds per plant, L1 included. When present the
#: P3 stem axis gets a point-mass ``node_budget`` (the engine's own determinate mechanism) instead of
#: ``stop_probability``; the stem stops producing leaves at the cap and the existing ones keep growing.
CAP_RANGE = "compounds_per_plant_cap"
_TIMESTAMP = "2026-10-05T00:00:00+00:00"
_STEM = "stem"


class StructureRejected(RuntimeError):
    """The P3 trajectory could not provide a usable plant; the caller resamples."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_csv(path: Path, records: list[dict[str, Any]], columns: tuple[str, ...]) -> dict[str, str]:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow({k: ("" if record.get(k) is None else record[k]) for k in columns})
    return {"path": path.name, "sha256": _sha256(path)}


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=1) + "\n", encoding="utf-8")


def sample_plant_params(cfg: dict[str, Any], seed: int, attempt: int = 0) -> dict[str, float]:
    """Scene-level draws for the P3 origin and parameter particle."""
    rng = make_rng(seed, "plant", attempt)
    names = ("plant_age_days", "stem_initial_length_mm", "stem_lean_deg", "first_leaf_wait_dev_days",
             "leaf_interval_dev_days", "phyllotaxis_divergence_deg", "leaf_elevation_deg",
             "internode_increment_mm", "internode_rate_per_day", "rachis_increment_mm",
             "rachis_rate_per_day", "extent_target_mm", "extent_rate_per_day",
             "l1_rachis_length_mm", "l1_extent_mm")
    out = {name: sample_range(rng, cfg, name) for name in names}
    out["stem_lean_azimuth_rad"] = float(rng.uniform(0.0, 2.0 * math.pi))
    out["l1_azimuth_rad"] = float(rng.uniform(0.0, 2.0 * math.pi))
    out["p3_seed"] = int(rng.integers(1, 2**31 - 1))
    if CAP_RANGE in cfg.get("ranges", {}):           # cell O (2026-10-08): drawn last so earlier draws pair exactly
        out[CAP_RANGE] = int(sample_range(rng, cfg, CAP_RANGE))
    return out


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def write_p3_inputs(work_dir: Path, params: dict[str, float], cfg: dict[str, Any],
                    plant_id: str) -> tuple[Path, Path, dict[str, Any]]:
    """Write the synthetic P3 observation bundle + structure; return paths and origin config."""
    from tools import compound_growth as observed  # lazy: tools/ is read-only here

    work_dir = Path(work_dir)
    obs_dir = work_dir / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    session = f"{plant_id}_p3origin"
    lean = math.radians(params["stem_lean_deg"])
    lean_dir = np.array([math.sin(lean) * math.cos(params["stem_lean_azimuth_rad"]),
                         math.sin(lean) * math.sin(params["stem_lean_azimuth_rad"]), math.cos(lean)])
    h0 = params["stem_initial_length_mm"]
    stem_points = [np.zeros(3), 0.5 * h0 * lean_dir, h0 * lean_dir]
    attach = stem_points[0] + 0.8 * (stem_points[1] - stem_points[0])
    elev = math.radians(params["leaf_elevation_deg"])
    az = params["l1_azimuth_rad"]
    d = np.array([math.cos(elev) * math.cos(az), math.cos(elev) * math.sin(az), math.sin(elev)])
    l1 = params["l1_rachis_length_mm"]
    rachis = [attach + s * l1 * d for s in (0.0, 0.5, 1.0)]
    transverse = _unit(np.cross([0.0, 0.0, 1.0], d))
    base = dict(plant_id=plant_id, compound_leaf_id="L1", session_id=session)
    record = dict(base, observed_at=_TIMESTAMP, parent_stem_id=_STEM, identity_status="confirmed",
                  review_source="synthetic_generator", geometry_status="observed_axis",
                  development_state="unfolding", first_observed_at=None, supported_area_cm2=1.0,
                  area_basis_id="synthetic_patch", estimated_total_area_cm2=None,
                  transverse_x=transverse[0], transverse_y=transverse[1], transverse_z=transverse[2])
    tables = {
        "observations": _write_csv(obs_dir / "observations.csv", [record], observed.OBS_COLUMNS),
        "axes": _write_csv(obs_dir / "axes.csv", [dict(base, station=s, x_mm=p[0], y_mm=p[1], z_mm=p[2])
                                                    for s, p in zip((0.0, 0.5, 1.0), rachis)], observed.AXIS_COLUMNS),
        "extents": _write_csv(obs_dir / "extents.csv", [dict(base, station=0.5, left_mm=params["l1_extent_mm"],
                                                              right_mm=params["l1_extent_mm"])], observed.EXTENT_COLUMNS),
    }
    _write_json(obs_dir / "observations.json", dict(
        schema="compound-observations-1", coordinate_frame="board_mm", frame_id=LOCAL_FRAME,
        frame_stability="confirmed", frame_evidence="synthetic_generator", data_kind="synthetic",
        reference_status="synthetic_truth", tables=tables))
    axis_rows = [dict(parent_stem_id=_STEM, point_id=f"p{i}", order=i, x_mm=p[0], y_mm=p[1], z_mm=p[2],
                      source_ref="synthetic_generator", review_status="confirmed") for i, p in enumerate(stem_points)]
    attach_rows = [dict(compound_leaf_id="L1", parent_stem_id=_STEM, segment_start_id="p0", segment_end_id="p1",
                        fraction=0.8, material_node_id="n1", predecessor_id="", adjacency_status="confirmed",
                        projection_residual_mm=0.0, review_ref="synthetic_generator")]
    structure_tables = {
        "parent_axis_points": _write_csv(work_dir / "parent_axis_points.csv", axis_rows, tuple(axis_rows[0])),
        "attachments": _write_csv(work_dir / "attachments.csv", attach_rows, tuple(attach_rows[0])),
    }
    reference = _unit(np.cross(lean_dir, [0.0, 1.0, 0.0])) if abs(lean_dir[1]) < 0.9 else np.array([1.0, 0, 0])
    axis = dict(parent_stem_id=_STEM, apex_status="active", apex_point_id="p2", apex_review="confirmed",
                reference_vector=reference.tolist())
    if CAP_RANGE in params:                      # node_budget needs the reviewed node count at the origin
        axis.update(observed_node_count=1, node_count_source_ref="synthetic_generator: L1 is the only compound "
                                                                   "at the synthetic origin")
    _write_json(work_dir / "structure.json", dict(
        plant_id=plant_id, observed_at=_TIMESTAMP, frame_id=LOCAL_FRAME, coordinate_frame="board_mm",
        axes=[axis], **structure_tables))
    origin_cfg = dict(plant_id=plant_id, session_id=session, observed_at=_TIMESTAMP,
                      numeric_tolerance=constant(cfg, "p3_numeric_tolerance"),
                      projection_tolerance_mm=constant(cfg, "p3_projection_tolerance_mm"))
    _write_json(work_dir / "origin.json", origin_cfg)
    return obs_dir, work_dir / "structure.json", origin_cfg


def build_p3_model(params: dict[str, float], cfg: dict[str, Any]) -> dict[str, Any]:
    """A synthetic P3 model: one particle, joint gaussian over wait/azimuth/length/elevation."""
    from tools import probabilistic_compound_growth as p3  # lazy

    elev_t = math.atanh(math.radians(params["leaf_elevation_deg"]) / (math.pi / 2))
    div = math.radians(params["phyllotaxis_divergence_deg"])
    cov = np.diag([constant(cfg, "within_plant_log_wait_var"), constant(cfg, "within_plant_azimuth_var"),
                   constant(cfg, "within_plant_log_length_var"), constant(cfg, "within_plant_elevation_var")])
    consts = dict(birth_axis_length_mm=constant(cfg, "birth_axis_length_mm"),
                  birth_left_extent_mm=constant(cfg, "birth_extent_mm"),
                  birth_right_extent_mm=constant(cfg, "birth_extent_mm"),
                  k_length=params["rachis_rate_per_day"], left_target_mm=params["extent_target_mm"],
                  right_target_mm=params["extent_target_mm"], k_width=params["extent_rate_per_day"],
                  rotation_x_rad=0.0, rotation_y_rad=0.0, rotation_z_rad=0.0, k_rotation=0.1,
                  D_segment_mm=params["internode_increment_mm"], k_segment=params["internode_rate_per_day"],
                  D_area_cm2=1.0, k_area=0.1)

    def family(wait: float) -> dict[str, Any]:
        return dict(mean=[math.log(wait), div, math.log(params["rachis_increment_mm"]), elev_t],
                    features=[], coefficients=[[], [], [], []], standardization={},
                    rho=constant(cfg, "family_rho"), innovation_covariance=cov.tolist(),
                    initial_covariance=cov.tolist(),
                    constants={k: dict(value=v, unit=p3.UNITS[k]) for k, v in consts.items()})

    particle = dict(
        id="synthetic_generator_particle", weight=1, source_kind="user_assumed",
        source_ref="SYNTHETIC GENERATOR ONLY - tomato3d.synth generator_config.json; not a crop parameter",
        coordinates=[dict(name="wait_dev_days", unit="development_day", transform="exp", reference=1),
                     dict(name="azimuth_rad", unit="rad", transform="identity"),
                     dict(name="D_length_mm", unit="mm", transform="exp", reference=1),
                     dict(name="elevation_rad", unit="rad", transform="elevation")],
        plant_covariance=np.diag([constant(cfg, "plant_shared_var")] * 4).tolist(),
        families={"residual": family(params["first_leaf_wait_dev_days"]),
                  "interval": family(params["leaf_interval_dev_days"]),
                  "existing": family(params["leaf_interval_dev_days"]),
                  "segment": family(params["leaf_interval_dev_days"])},
        axes={_STEM: dict(**(dict(node_budget=dict(pmf=[dict(n=int(params[CAP_RANGE]), p=1.0)], source_kind="user_assumed",
                                                   source_ref="SYNTHETIC GENERATOR ONLY - generator_config.json range "
                                                              f"{CAP_RANGE}, drawn per plant"))
                            if CAP_RANGE in params else dict(stop_probability=constant(cfg, "p3_stop_probability"))),
                          residual_family="residual", inter_event_family="interval", direction_reference="predecessor",
                          predecessor_id="L1", segment_families={"p0:p1": "segment", "p1:p2": "segment"})},
        existing_blocks={"L1": "existing"})
    model = p3.blank_model()
    model.update(leaf_retention_assumption="no_loss_over_horizon", parameter_particles=[particle],
                 environment_scenario=dict(id="synthetic_generator_scenario", values=None, response_ref=None),
                 computation=dict(seed=int(params["p3_seed"]), sample_count=1, output_days=[0],
                                  numeric_tolerance=constant(cfg, "p3_numeric_tolerance"),
                                  max_events_per_axis=int(constant(cfg, "max_events_per_axis"))))
    return model


def generate_structure(cfg: dict[str, Any], seed: int, work_dir: Path, plant_id: str,
                       attempt: int = 0) -> dict[str, Any]:
    """Run P3 once and return the plant graph (stem + compound leaves, plant-local frame)."""
    from tools import probabilistic_compound_growth as p3  # lazy

    params = sample_plant_params(cfg, seed, attempt)
    obs_dir, structure_path, origin_cfg = write_p3_inputs(Path(work_dir), params, cfg, plant_id)
    origin = p3.prepare_origin(obs_dir, structure_path, origin_cfg)
    model = build_p3_model(params, cfg)
    _write_json(Path(work_dir) / "model.json", model)
    bank = p3.sample_forecast(origin, model)
    trajectory = bank["trajectories"][0]
    if not trajectory.get("valid"):
        raise StructureRejected(f"p3_trajectory_invalid: {trajectory.get('status_reason')}")
    day = float(params["plant_age_days"])
    states = p3.decode_trajectory(trajectory, [day])
    stem = p3._axis_points(trajectory, _STEM, p3._clock(bank["config"], day))  # noqa: SLF001 - read-only use
    if stem is None:
        raise StructureRejected("p3_stem_geometry_unavailable")
    births = {b["block_id"]: b["birth_day"] for b in trajectory["blocks"]}
    compounds = []
    for s in states:
        if s.get("existence") != "appeared":
            continue
        needed = ("attachment_xyz_mm", "direction_unit_xyz", "rachis_arc_length_mm")
        if any(s.get(k) is None for k in needed) or not s.get("left_extent_mm") or not s.get("right_extent_mm"):
            raise StructureRejected(f"p3_block_unavailable: {s['block_id']} {s.get('availability')}")
        compounds.append(dict(
            p3_block_id=s["block_id"], attachment_mm=[float(x) for x in s["attachment_xyz_mm"]],
            direction_unit=[float(x) for x in s["direction_unit_xyz"]],
            rachis_arc_length_mm=float(s["rachis_arc_length_mm"]),
            left_extent_mm=float(max(s["left_extent_mm"])), right_extent_mm=float(max(s["right_extent_mm"])),
            age_days=float(day - births.get(s["block_id"], 0.0))))
    if not compounds:
        raise StructureRejected("p3_no_compound_leaves")
    compounds.sort(key=lambda c: (c["attachment_mm"][2], c["p3_block_id"]))
    for rank, c in enumerate(compounds, start=1):
        c["compound_id"] = f"L{rank:02d}"
        c["rank_from_bottom"] = rank
    return dict(
        schema=GRAPH_SCHEMA, origin=ORIGIN, generator_version=GENERATOR_VERSION, plant_id=plant_id,
        seed=int(seed), attempt=int(attempt), frame=LOCAL_FRAME, params=params,
        p3=dict(run_id=bank["run_id"], trajectory_id=trajectory["trajectory_id"], decode_day=day,
                model_sha256=hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest(),
                validated_growth=False, suitable_for_ppfd=False),
        stem=dict(points_mm=[[float(x) for x in p] for p in stem]),
        compounds=compounds)
