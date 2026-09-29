"""Explicit synthetic integration fixture, never a real-image/plant result.

This projects known leaf landmarks, not ChArUco images; it does not duplicate the
repository's existing ChArUco renderer. Camera-pose acquisition is tested separately.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .annotations import POINT_COLUMNS, CONTOUR_COLUMNS
from .common import (ROOT, digest, file_hash, load_protocol, output_dir, read_json,
                     variants, write_json, write_rows)
from .optics import READING_COLUMNS, disk_receivers
from .reconstruction import project


def camera_frame(name: str, center: np.ndarray, target: np.ndarray,
                 view_type: str, top_position: str | None = None) -> dict:
    forward = target - center
    forward /= np.linalg.norm(forward)
    up = np.array([0., 0., 1.])
    if abs(forward @ up) > 0.95:
        up = np.array([0., 1., 0.])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    rotation = np.vstack((right, down, forward))
    return dict(image_file=name, image_path=None, sha256=None,
                view_type=view_type, top_position=top_position, pose_status="solved",
                rvec_rad=cv2.Rodrigues(rotation)[0].reshape(3).tolist(),
                tvec_mm=(-rotation @ center).tolist(), reprojection_error_px=0)


def make_inputs(protocol_path: Path, out: Path) -> dict:
    p, protocol_hash = load_protocol(protocol_path)
    root = output_dir(out)
    plant = p["evaluation_plants"][0]
    intrinsics = dict(schema_version="1.0", camera_id="synthetic", image_width_px=1600,
        image_height_px=1200, camera_matrix=[[1200,0,800],[0,1200,600],[0,0,1]],
        dist_coeffs=[0,0,0,0,0], rms_reprojection_error_px=0, n_calibration_images=20,
        calibrated_at="2026-09-17T00:00:00Z", distortion_model="opencv_pinhole")
    frames = []
    target = np.array([0.,0.,150.])
    for i in range(36):
        angle = 2*np.pi*i/36
        frames.append(camera_frame(f"side_{i:03d}.png", np.array([550*np.cos(angle),550*np.sin(angle),350.]), target, "side"))
    for i, (x,y) in enumerate([(0,0),(135,135),(-135,135),(-135,-135),(135,-135)]):
        frames.append(camera_frame(f"top_T{i}.png", np.array([float(x),float(y),550.]), target, "top", f"T{i}"))
    capture = dict(protocol_sha256=protocol_hash, data_kind="synthetic", plant_id=plant,
        session_id="synthetic_projection_only", intrinsics=intrinsics, frames=frames,
        physical_blockers=[], variants=variants(p, frames),
        notice="SYNTHETIC LANDMARK PROJECTIONS. No photographs or plant measurements. Camera poses are exact fixture inputs.")
    write_json(root / "capture.json", capture)
    points, contours = [], []
    corners = np.array([[-70.,-35.,150.],[70.,-35.,150.],[70.,35.,150.],[-70.,35.,150.],[0.,0.,150.]])
    for frame in frames:
        projected = project(corners, frame, intrinsics)
        for i, xy in enumerate(projected):
            points.append(dict(image_file=frame["image_file"], organ_id="L1", leaflet_id="A",
                point_id=f"P{i}", x_px=xy[0], y_px=xy[1], boundary_index=i if i<4 else -1, boundary_count=4))
        for i, xy in enumerate(projected[:4]):
            contours.append(dict(image_file=frame["image_file"], organ_id="L1", leaflet_id="A", vertex_index=i, x_px=xy[0], y_px=xy[1]))
    write_rows(root / "points.csv", points, POINT_COLUMNS)
    write_rows(root / "contours.csv", contours, CONTOUR_COLUMNS)
    scene = read_json(ROOT / "tests/fixtures/light/light_scene.example.json")
    scene["scenarios"] = []
    scene["plants"] = [scene["plants"][0]]
    scene["plants"][0]["plant_id"] = plant
    scene["plants"][0]["board_origin_grow_mm"]["value"] = [300.,200.,0.]
    scene["plants"][0]["posture_since_capture"] = "unchanged_checked"
    scene["notes"] = "SYNTHETIC. Analytic flat leaf and model-generated readings; not validation of plants or LED hardware."
    write_json(root / "scene.json", scene)
    measurements = []
    for i in range(p["minimum_calibration_readings"]):
        measurements.append(_reading(f"C{i}", [150.+100*i,50.,50.], "calibration", "empty", f"C{i}", "1", scene["setup_id"]))
    for i in range(p["sites_per_session"]):
        for repeat in range(p["replicates_per_site"]):
            measurements.append(_reading(f"R{i}_{repeat}", [230.+i*17,200.,110.+(i%3)*55], "evaluation", "plant_present", f"S{i}", str(repeat+1), scene["setup_id"]))
    # Generate fixture truth analytically through the engine with an exact mesh.
    from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS
    from tomato3d.light.geometry import load_geometry, empty_surface_set
    from tomato3d.light.scene import load_scene, resolve_scenario
    from .optics import read_measurements, sensor_predictions
    true_rows = []
    for i, ids in enumerate([[0,1,2],[0,2,3]]):
        row = dict(plant_id=plant, session_id=capture["session_id"], geometry_variant_id="truth", geometry_source="assumed",
                   organ_class="leaf", organ_id="L1", leaflet_id="A", triangle_id=f"t{i}", normal_convention="unknown")
        row.update({f"v{k}_{a}_mm": corners[ids[k],j] for k in range(3) for j,a in enumerate("xyz")})
        true_rows.append(row)
    write_rows(root / "synthetic_truth.csv", true_rows, LEAF_SURFACES_CSV_COLUMNS)
    write_rows(root / "readings.csv", measurements, READING_COLUMNS)
    model = load_scene(root / "scene.json")
    resolved = resolve_scenario(model, "as_built")
    loaded = read_measurements(root / "readings.csv", model)
    truth = load_geometry([root / "synthetic_truth.csv"])["truth"]
    for i, reading in enumerate(loaded):
        geom = empty_surface_set() if reading["split_role"] == "calibration" else truth
        value = sensor_predictions([reading], p, resolved, geom, model)[0]
        measurements[i]["ppfd_umol_m2_s"] = float(value * 1.12)
    write_rows(root / "readings.csv", measurements, READING_COLUMNS)
    return capture


def _reading(rid: str, xyz: list, role: str, environment: str, site: str, repeat: str, setup: str) -> dict:
    return dict(reading_id=rid, setup_id=setup, scenario_id="as_built", measured_at="2026-09-17T00:00:00Z",
        sensor_model="SYNTHETIC circular sensor", x_mm=xyz[0], y_mm=xyz[1], z_mm=xyz[2],
        normal_x=0,normal_y=0,normal_z=1,all_fixtures_full_output="yes",ppfd_umol_m2_s=1,
        split_role=role,region_label="synthetic_plane",observer="software",note="SYNTHETIC - NOT MEASURED",
        site_id=site,replicate_id=repeat,sensor_radius_mm=5,photon_band="PAR_400_700nm",
        environment_state=environment,measurement_status="valid")
