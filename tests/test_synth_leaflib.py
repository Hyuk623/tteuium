"""Addendum D: library loader, contour permission, rot_grid layout matching, de-lighting."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import cv2
import numpy as np

from tomato3d.synth import leaflib as lb

COLS = ["session_id", "photo_file", "source_filename", "sha256", "captured_at", "level", "content", "attachment",
        "pressed", "condition", "ruler_in_frame", "quality_flags", "rotation_series", "rotation_step", "uses", "notes"]


def _lib(tmp: Path, rows: list[dict], files: dict[str, bytes]) -> Path:
    d = tmp / "leaf_lib_20261006"
    d.mkdir()
    for name, data in files.items():
        (d / name).write_bytes(data)
    with (d / lb.CSV_NAME).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    return d


def _row(name, data=b"x", **k):
    r = dict(session_id="leaf_lib_20261006", photo_file=name, source_filename="IMG.HEIC",
             sha256=hashlib.sha256(data).hexdigest(), captured_at="", level="leaflet", content="", attachment="detached",
             pressed="no", condition="mixed", ruler_in_frame="yes", quality_flags="", rotation_series="",
             rotation_step="", uses="texture;shape_contour", notes="")
    r.update(k)
    return r


def test_loader_rejects_missing_and_mismatch_without_plant_id(tmp_path):
    d = _lib(tmp_path, [_row("a.heic"), _row("b.heic", sha256="0" * 64), _row("c.heic")],
             {"a.heic": b"x", "b.heic": b"x"})
    res = lb.load_library(d)
    assert [r["photo_file"] for r in res["rows"]] == ["a.heic"]
    assert {p["problem"] for p in res["problems"]} == {"sha256_mismatch", "missing_file"}
    assert "plant_id" not in COLS


def test_contour_only_with_shape_use_and_no_occlusion():
    base = dict(uses_set={"texture", "shape_contour"}, flags_set=set())
    assert lb.contour_allowed(base)
    assert not lb.contour_allowed(dict(base, uses_set={"texture", "vein"}))
    assert not lb.contour_allowed(dict(base, flags_set={"hand_occlusion"}))


def test_rot_grid_matching_recovers_90_degrees():
    rng = np.random.default_rng(1)
    pts = np.array([[x * 100 + rng.normal(0, 8), y * 120 + rng.normal(0, 8)] for x in range(6) for y in range(5)])
    a = np.radians(90)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    other = (pts - pts.mean(0)) @ R.T * 1.05 + np.array([900, 700])     # sheet rotated 90 deg, slight zoom
    perm = rng.permutation(len(other))
    m = lb.match_layout(pts, other[perm], -90)
    assert abs(abs(m["rotation_deg"]) - 90) < 2
    assert all(j == int(perm[i]) for i, j in m["pairs"]) and len(m["pairs"]) == len(pts)


def test_delight_recovers_albedo_under_gradient():
    h, w = 200, 300
    albedo = np.full((h, w, 3), 120.0)
    for x in range(20, w, 40):
        albedo[:, x:x + 3] = 70.0                                             # vein lines
    grad = np.linspace(0.5, 1.5, w)[None, :, None]
    img = np.clip(albedo * grad, 0, 255).astype(np.uint8)
    mask = np.ones((h, w), bool)
    rec = lb.delight(img, mask, sigma_px=25).astype(float)
    inner = (slice(30, -30), slice(40, -40))
    # gradient removed: column means of the vein-free background are flat within 6 %
    bg = rec[inner][:, :, 0]
    col = np.array([bg[:, i].mean() for i in range(bg.shape[1])])
    assert np.ptp(col[col > np.median(col) * 0.9]) / np.median(col) < 0.25
    left, right = rec[inner][:, :60, 0].mean(), rec[inner][:, -60:, 0].mean()
    assert abs(left - right) / ((left + right) / 2) < 0.06
    # vein contrast kept
    assert rec[100, 20:23].mean() < rec[100, 30:35].mean() * 0.8


def test_condition_label_is_exposure_invariant():
    img = np.full((300, 300, 3), 215, np.uint8)                       # white paper
    cv2.ellipse(img, (150, 150), (80, 45), 0, 0, 360, (70, 140, 60), -1)   # green leaflet (BGR)
    mask = np.zeros((300, 300), bool)
    cv2.ellipse(mask.view(np.uint8), (150, 150), (80, 45), 0, 0, 360, 1, -1)
    dark = (img.astype(float) * 0.35).astype(np.uint8)              # under-exposed copy
    a, b = lb.classify_condition(img, mask), lb.classify_condition(dark, mask)
    assert a["condition"] == b["condition"] == "healthy"
