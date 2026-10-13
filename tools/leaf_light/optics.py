"""Finite-area quantum sensor adapter around Claude Code's direct-light engine."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np

from tomato3d.io.schemas import PPFD_READINGS_CSV_COLUMNS
from tomato3d.light.geometry import empty_surface_set, load_geometry, place_in_grow_frame
from tomato3d.light.pipeline import build_occluders, leaf_receivers
from tomato3d.light.raytrace import Receivers, direct_light
from tomato3d.light.scene import load_scene, resolve_scenario, input_records, non_observed_input_names
from tomato3d.light.validate import calibration_factor

from .common import (StudyError, digest, file_hash, load_protocol, number, output_dir,
                     read_json, rows, write_json, write_rows)

READING_COLUMNS = PPFD_READINGS_CSV_COLUMNS + (
    "site_id", "replicate_id", "sensor_radius_mm", "photon_band",
    "environment_state", "measurement_status")
PREDICTION_COLUMNS = ("plant_id", "session_id", "session_slot", "variant_id", "view_count",
                      "reading_id", "site_id", "replicate_id", "region_label", "measurement_status",
                      "measured_ppfd_umol_m2_s", "predicted_ppfd_umol_m2_s", "raw_predicted_ppfd_umol_m2_s",
                      "no_plants_ppfd_umol_m2_s", "calibration_factor", "run_status")
MAP_COLUMNS = ("variant_id", "organ_id", "leaflet_id", "triangle_id",
               "ppfd_umol_m2_s") + tuple(f"v{i}_{a}_mm" for i in range(3) for a in "xyz")


def read_measurements(path: Path, scene) -> list[dict]:
    records = rows(path, READING_COLUMNS)
    seen = set()
    site_repeats = set()
    for row in records:
        if not row["reading_id"] or row["reading_id"] in seen:
            raise StudyError("Duplicate/empty sensor reading ID")
        seen.add(row["reading_id"])
        if row["setup_id"] != scene.setup_id or row["scenario_id"] != "as_built":
            raise StudyError("Readings must belong to this as-built setup")
        if row["all_fixtures_full_output"] != "yes":
            raise StudyError("The current engine supports full-output readings only")
        role = row["split_role"]
        if role not in ("calibration", "evaluation"):
            raise StudyError("Unknown measurement split")
        expected_environment = "empty" if role == "calibration" else "plant_present"
        if row["environment_state"] != expected_environment:
            raise StudyError("Calibration must be empty; evaluation must contain the plant")
        if row["measurement_status"] not in ("valid", "unavailable", "leaf_moved"):
            raise StudyError("Unknown measurement status")
        if row["photon_band"] != scene.leaf_optics.photon_band:
            raise StudyError("Sensor and simulation photon bands disagree")
        if not row["sensor_model"].strip():
            raise StudyError("Sensor model is required")
        normal = np.array([number(row[f"normal_{a}"], "normal") for a in "xyz"])
        if not np.isclose(np.linalg.norm(normal), 1.0, atol=1e-3):
            raise StudyError("Sensor normal must be a unit vector")
        radius = number(row["sensor_radius_mm"], "sensor radius")
        if radius <= 0:
            raise StudyError("Finite positive sensor radius required")
        row["point_mm"] = np.array([number(row[f"{a}_mm"], "sensor position") for a in "xyz"])
        row["normal"] = normal / np.linalg.norm(normal)
        row["radius_mm"] = radius
        measured = number(row["ppfd_umol_m2_s"], "PPFD", missing=True)
        if measured is not None and measured < 0:
            raise StudyError("Measured PPFD cannot be negative")
        if row["measurement_status"] == "valid" and measured is None:
            raise StudyError("Valid measurement must have PPFD")
        row["measured"] = measured if row["measurement_status"] == "valid" else None
        if role == "evaluation":
            key = (row["site_id"], row["replicate_id"])
            if not all(key) or key in site_repeats:
                raise StudyError("Duplicate or empty site/replicate ID")
            site_repeats.add(key)
    return records


def disk_receivers(records: list[dict], p: dict) -> tuple[Receivers, int]:
    nr, na = p["sensor_radial_samples"], p["sensor_angular_samples"]
    points, normals = [], []
    for row in records:
        normal = row["normal"]
        axis = np.eye(3)[np.argmin(np.abs(normal))]
        u = np.cross(normal, axis)
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        for r in range(nr):
            radius = row["radius_mm"] * np.sqrt((r + 0.5) / nr)
            for a in range(na):
                angle = (a + 0.5) * 2 * np.pi / na
                points.append(row["point_mm"] + radius * (np.cos(angle) * u + np.sin(angle) * v))
                normals.append(normal)
    return Receivers(np.asarray(points).reshape(-1, 3), np.asarray(normals).reshape(-1, 3),
                     False, np.full(len(points), -1, dtype=np.int64)), nr * na


def sensor_predictions(records: list[dict], p: dict, resolved, surfaces, scene) -> np.ndarray:
    if not records:
        return np.array([])
    receivers, samples = disk_receivers(records, p)
    vertices = place_in_grow_frame(surfaces, resolved.placements)
    light = direct_light(receivers, resolved.fixtures, build_occluders(surfaces, vertices),
                         scene.leaf_optics.transmittance.value, scene.simulation)
    # A missing ray is not a zero or a sample to discard.
    return light.ppfd_umol_m2_s.sum(axis=0).reshape(len(records), samples).mean(axis=1)


def finite(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def run(reconstruction_path: Path, scene_path: Path, readings_path: Path,
        protocol_path: Path, session_slot: str, out: Path) -> dict:
    p, protocol_hash = load_protocol(protocol_path)
    reconstruction = read_json(reconstruction_path)
    if reconstruction["protocol_sha256"] != protocol_hash:
        raise StudyError("Reconstruction and study protocols differ")
    plant = reconstruction["plant_id"]
    if plant not in p["development_plants"] + p["evaluation_plants"] or session_slot not in p["session_slots"]:
        raise StudyError("Plant/session slot is not in the frozen plan")
    if reconstruction["capture_sha256"] != file_hash(Path(reconstruction["capture_path"])):
        raise StudyError("Capture inspection changed after reconstruction")
    scene = load_scene(scene_path)
    if len(scene.plants) != 1 or scene.plants[0].plant_id != plant:
        raise StudyError("The approved study uses exactly one matching plant per scene")
    measurements = read_measurements(readings_path, scene)
    calibration = [r for r in measurements if r["split_role"] == "calibration"]
    evaluation = [r for r in measurements if r["split_role"] == "evaluation"]
    resolved = resolve_scenario(scene, "as_built")
    empty = empty_surface_set()
    predicted_calibration = sensor_predictions(calibration, p, resolved, empty, scene)
    n_calibration = sum(int(r["measured"] is not None and np.isfinite(predicted_calibration[i])) for i, r in enumerate(calibration))
    factor = (calibration_factor([r["measured"] for r in calibration], predicted_calibration)
              if n_calibration >= p["minimum_calibration_readings"] else None)
    if factor is not None and factor <= 0:
        factor = None
    baseline = sensor_predictions(evaluation, p, resolved, empty, scene)
    folder = output_dir(out)
    predictions, maps, timings = [], [], []
    blockers = list(reconstruction["physical_blockers"])
    if reconstruction["data_kind"] == "observed" and scene.plants[0].posture_since_capture != "unchanged_checked":
        blockers.append("plant_posture_not_checked")
    if factor is None:
        blockers.append("empty_scene_calibration_unavailable")
    for variant in reconstruction["variants"]:
        started = perf_counter()
        path = reconstruction_path.parent / variant["geometry_file"]
        if file_hash(path) != variant["geometry_sha256"]:
            raise StudyError("Geometry file changed after reconstruction")
        geometry = load_geometry([path])
        surfaces = geometry.get(variant["variant_id"])
        status = "ok" if not blockers and surfaces is not None and variant["status"] == "reconstructed" else "failed"
        raw = (sensor_predictions(evaluation, p, resolved, surfaces, scene) if surfaces is not None else np.full(len(evaluation), np.nan))
        for i, reading in enumerate(evaluation):
            predictions.append(dict(plant_id=plant, session_id=reconstruction["session_id"],
                session_slot=session_slot, variant_id=variant["variant_id"], view_count=variant["view_count"],
                reading_id=reading["reading_id"], site_id=reading["site_id"], replicate_id=reading["replicate_id"],
                region_label=reading["region_label"], measurement_status=reading["measurement_status"],
                measured_ppfd_umol_m2_s=reading["measured"], raw_predicted_ppfd_umol_m2_s=finite(raw[i]),
                predicted_ppfd_umol_m2_s=finite(raw[i] * factor) if status == "ok" else None,
                no_plants_ppfd_umol_m2_s=finite(baseline[i] * factor) if factor is not None else None,
                calibration_factor=factor, run_status=status))
        if surfaces is not None:
            vertices = place_in_grow_frame(surfaces, resolved.placements)
            receivers, triangle_ids = leaf_receivers(surfaces, vertices, scene.simulation.triangle_subdivisions)
            light = direct_light(receivers, resolved.fixtures, build_occluders(surfaces, vertices),
                                 scene.leaf_optics.transmittance.value, scene.simulation)
            ppfd = light.ppfd_umol_m2_s.sum(axis=0).reshape(len(triangle_ids), -1).mean(axis=1)
            for i, ti in enumerate(triangle_ids):
                item = dict(variant_id=variant["variant_id"], organ_id=surfaces.organ_ids[ti],
                            leaflet_id=surfaces.leaflet_ids[ti], triangle_id=surfaces.triangle_ids[ti],
                            ppfd_umol_m2_s=finite(ppfd[i] * factor) if status == "ok" else None)
                item.update({f"v{k}_{axis}_mm": float(vertices[ti, k, j]) for k in range(3) for j, axis in enumerate("xyz")})
                maps.append(item)
        timings.append({"variant_id": variant["variant_id"], "view_count": variant["view_count"],
                        "capture_seconds": variant.get("capture_seconds"),
                        "reconstruction_seconds": variant["reconstruction_seconds"],
                        "light_seconds": perf_counter() - started,
                        "annotation_seconds": variant.get("annotation_seconds"),
                        "correction_seconds": variant.get("correction_seconds"),
                        "work_scope": variant.get("work_scope", "unavailable")})
    write_rows(folder / "predictions.csv", predictions, PREDICTION_COLUMNS)
    write_rows(folder / "leaf_light_map.csv", maps, MAP_COLUMNS)
    write_rows(folder / "timings.csv", timings, list(timings[0]))
    result = {"protocol_sha256": protocol_hash, "plant_id": plant, "session_id": reconstruction["session_id"],
              "session_slot": session_slot, "data_kind": reconstruction["data_kind"],
              "scene_sha256": file_hash(scene_path), "readings_sha256": file_hash(readings_path),
              "reconstruction_sha256": file_hash(reconstruction_path),
              "source_model_sha256": digest({k: scene.model_dump(mode="json")[k] for k in ("fixtures", "leaf_optics", "simulation")}),
              "predictions_sha256": file_hash(folder / "predictions.csv"),
              "calibration_factor": factor, "n_calibration": n_calibration, "blockers": blockers,
              "inputs": [item.model_dump(mode="json") for item in input_records(scene)],
              "non_observed_inputs": non_observed_input_names(input_records(scene)),
              "model_limits": ["Direct light and straight-line transmission only; no reflected/scattered light.",
                               "Finite disk average; sensor body does not displace leaves.",
                               "A model with uncertain geometry/optics is not a guaranteed lower bound.",
                               "PPFD accuracy is not absorption or photosynthesis validation."],
              "input_paths": {"scene": str(scene_path.resolve()), "readings": str(readings_path.resolve()),
                              "reconstruction": str(reconstruction_path.resolve())}}
    write_json(folder / "run.json", result)
    return result
