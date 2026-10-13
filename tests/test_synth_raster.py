"""Synthetic generator: rasteriser, camera model, depth, organ classes, manifest origin.

Needs only numpy/OpenCV - runs in the project environment without L-Py/PlantGL/bpy.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from tomato3d.synth.camera import RigView, build_render_geometry
from tomato3d.synth.raster import INVALID_LABEL, ORGAN_CLASSES, rasterize

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRIAL_CAPTURE = PROJECT_ROOT / "build/plants_dwt_test_20261002/plants/dwt_t3/pose_session_merged/edit_session/capture.json"
CORNER_TOLERANCE_PX = 1.0
DEPTH_TOLERANCE_MM = 0.5


def _look_at_view(dist, *, elevation_deg=55.0, azimuth_deg=30.0, distance_mm=400.0, target=(95.0, -57.0, 0.0),
                  size_px=3024, f_px=3200.0) -> RigView:
    target = np.asarray(target, float)
    el, az = math.radians(elevation_deg), math.radians(azimuth_deg)
    center = target + distance_mm * np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    z = target - center
    z /= np.linalg.norm(z)
    x = np.cross(z, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.stack([x, y, z])
    t = -R @ center
    K = ((f_px, 0.0, size_px / 2 - 0.5), (0.0, f_px, size_px / 2 - 0.5), (0.0, 0.0, 1.0))
    return RigView(view_id="test/01", session_id="test", capture_path="", image_file="", camera_matrix=K,
                   dist_coeffs=tuple(dist), image_size_px=(size_px, size_px),
                   rvec_rad=tuple(cv2.Rodrigues(R)[0].ravel()), tvec_mm=tuple(t), reprojection_error_px=0.0,
                   camera_center_mm=tuple(center), elevation_deg=elevation_deg, passes_pose_gate=True)


def _geom(view, out_px=512):
    return build_render_geometry(view, out_px, tolerance_px=0.5, iterations=100, max_canvas_scale=1.6)


def _square(center, half_mm, z=0.0):
    cx, cy = center
    v = np.array([[cx - half_mm, cy - half_mm, z], [cx + half_mm, cy - half_mm, z],
                  [cx + half_mm, cy + half_mm, z], [cx - half_mm, cy + half_mm, z]])
    return v, np.array([(0, 1, 2), (0, 2, 3)], np.int32)


def _corner_check(view):
    geom = _geom(view)
    corners = np.array([[x, y, 0.0] for x in (40.0, 76.0, 114.0, 152.0) for y in (-20.0, -57.0, -95.0)])
    parts = []
    for i, c in enumerate(corners, start=1):
        v, f = _square(c[:2], 1.5, 0.0)
        parts.append(dict(name=f"c{i}", organ="leaflet", instance=i, vertices=v, faces=f))
    layers = rasterize(parts, view.rotation, view.translation, geom)
    expected, _ = cv2.projectPoints(corners, np.asarray(view.rvec_rad), np.asarray(view.tvec_mm), geom.K_out, geom.dist)
    expected = expected[:, 0]
    checked = 0
    for i, e in enumerate(expected, start=1):
        ys, xs = np.nonzero(layers.visible == i)
        u, v = int(round(e[0])), int(round(e[1]))
        h, w = geom.valid.shape
        if len(xs) == 0 or not (0 <= u < w and 0 <= v < h) or not geom.valid[v, u]:
            continue
        assert np.hypot(xs.mean() - e[0], ys.mean() - e[1]) <= CORNER_TOLERANCE_PX
        checked += 1
    return checked


def test_board_corners_match_projectpoints_with_distortion():
    view = _look_at_view((0.08, -0.05, 0.001, -0.001, 0.0))
    assert _corner_check(view) >= 10


@pytest.mark.skipif(not TRIAL_CAPTURE.exists(), reason="rig capture.json not present")
def test_board_corners_match_projectpoints_real_rig_camera():
    from tomato3d.synth.camera import load_rig_views

    views = load_rig_views(TRIAL_CAPTURE, 10.0, np.array([95.0, -57.0, 0.0]))
    assert views
    checked = sum(_corner_check(v) for v in views[:3])
    assert checked >= 10


def test_amodal_contains_visible_and_hidden_leaflet():
    view = _look_at_view((0.0,) * 5, elevation_deg=89.0)
    geom = _geom(view)
    a_v, a_f = _square((95.0, -57.0), 10.0, z=5.0)      # partly hidden leaflet
    b_v, b_f = _square((95.0, -57.0), 3.0, z=2.0)       # fully hidden under the occluder
    o_v, o_f = _square((92.0, -57.0), 8.0, z=20.0)      # stem-like occluder above both
    parts = [dict(name="a", organ="leaflet", instance=1, vertices=a_v, faces=a_f),
             dict(name="b", organ="leaflet", instance=2, vertices=b_v, faces=b_f),
             dict(name="occ", organ="stem", instance=0, vertices=o_v, faces=o_f)]
    layers = rasterize(parts, view.rotation, view.translation, geom)
    for inst in (1, 2):
        vis = layers.visible == inst
        assert np.all(layers.amodal[inst][vis]), "amodal must contain visible"
    assert not np.any(layers.visible == 2)
    assert layers.amodal[2].sum() > 0
    assert 0 < (layers.visible == 1).sum() < layers.amodal[1].sum()
    # same instance ids across a second view
    view2 = _look_at_view((0.0,) * 5, elevation_deg=40.0, azimuth_deg=120.0)
    layers2 = rasterize(parts, view2.rotation, view2.translation, _geom(view2))
    assert set(np.unique(layers2.visible)) <= {0, 1, 2}
    assert set(layers2.amodal) == set(layers.amodal)


def test_depth_is_camera_z_in_mm_and_organ_classes_complete():
    view = _look_at_view((0.0,) * 5, elevation_deg=60.0)
    geom = _geom(view)
    v, f = _square((95.0, -57.0), 30.0, z=12.0)
    parts = [dict(name="plane", organ="board", instance=0, vertices=v, faces=f)]
    layers = rasterize(parts, view.rotation, view.translation, geom)
    cx, cy = geom.out_size_px[0] // 2, geom.out_size_px[1] // 2
    ys, xs = np.nonzero(layers.depth_mm > 0)
    k = np.argmin((xs - cx) ** 2 + (ys - cy) ** 2)
    u, w = xs[k], ys[k]
    ray = cv2.undistortPoints(np.array([[[u, w]]], float), geom.K_out, geom.dist)[0, 0]
    R, t = view.rotation, view.translation
    # intersect the pixel ray with the plane z = 12 mm (board frame)
    d_cam = np.array([ray[0], ray[1], 1.0])
    origin = -R.T @ t
    d_board = R.T @ d_cam
    s = (12.0 - origin[2]) / d_board[2]
    point = origin + s * d_board
    z_expected = (R @ point + t)[2]
    assert abs(layers.depth_mm[w, u] - z_expected) <= DEPTH_TOLERANCE_MM
    assert set(np.unique(layers.organ)) <= set(ORGAN_CLASSES.values()) | {INVALID_LABEL}
    assert len(set(ORGAN_CLASSES.values())) == len(ORGAN_CLASSES)


def test_manifest_rows_are_synthetic(tmp_path):
    from tomato3d.synth.pipeline import manifest_row

    scene_dir = tmp_path / "scenes" / "scene_0000"
    vdir = scene_dir / "views" / "00_test_01"
    vdir.mkdir(parents=True)
    scene = dict(scene_id="scene_0000", seed=1, parameter_hash="x", scene_dir=scene_dir)
    row = manifest_row(scene, _look_at_view((0.0,) * 5), vdir, tmp_path, view_kind="top", rgb_written=True)
    assert row["origin"] == "synthetic"
    for key in ("scene_id", "view_id", "camera_source_session", "rgb", "visible_mask", "amodal_dir", "depth",
                "organ_mask", "plant_graph", "seed", "parameter_hash", "generator_version"):
        assert key in row


def test_import_without_heavy_dependencies():
    code = ("import sys\n"
            "for m in ('openalea', 'openalea.lpy', 'openalea.plantgl', 'bpy', 'pillow_heif', 'mathutils'):\n"
            "    sys.modules[m] = None\n"
            "import tomato3d, tomato3d.synth\n"
            "import tomato3d.synth.cli, tomato3d.synth.pipeline, tomato3d.synth.compound_leaf\n"
            "import tomato3d.synth.render_blender, tomato3d.synth.capture, tomato3d.synth.realism\n"
            "print('ok')\n")
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", code], cwd=PROJECT_ROOT, capture_output=True,
                         text=True, env=None)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("ok")
