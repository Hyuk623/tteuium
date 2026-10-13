"""Addendum C: grid rectification, area round trip, QA rule, incomplete reporting, C0 tiering."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from tomato3d.synth import leafarea as la
from tomato3d.synth.contours import unit_area_points

PITCH_MM = 10.0
SRC_PPM = 8.0
COLS, ROWS = 9, 6                      # inner corners -> 10 x 7 squares


def _sheet(leaf_axes_mm=(18.0, 11.0), leaf_center_mm=(140.0, 40.0)) -> tuple[np.ndarray, float]:
    """White sheet with a checkerboard (top-left) and a green elliptical 'leaflet'; returns (img, area_mm2)."""
    w_mm, h_mm = 190.0, 100.0
    img = np.full((int(h_mm * SRC_PPM), int(w_mm * SRC_PPM), 3), 255, np.uint8)
    ox, oy = 5.0, 5.0
    for j in range(ROWS + 1):
        for i in range(COLS + 1):
            if (i + j) % 2 == 0:
                x0, y0 = (ox + i * PITCH_MM) * SRC_PPM, (oy + j * PITCH_MM) * SRC_PPM
                cv2.rectangle(img, (int(round(x0)), int(round(y0))),
                              (int(round(x0 + PITCH_MM * SRC_PPM)) - 1, int(round(y0 + PITCH_MM * SRC_PPM)) - 1),
                              (0, 0, 0), -1)
    a, b = leaf_axes_mm
    cv2.ellipse(img, (int(leaf_center_mm[0] * SRC_PPM), int(leaf_center_mm[1] * SRC_PPM)),
                (int(a * SRC_PPM), int(b * SRC_PPM)), 25, 0, 360, (40, 150, 60), -1, lineType=cv2.LINE_AA)
    return img, np.pi * a * b


def _perspective(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[40, 30], [w - 10, 0], [w + 30, h + 20], [0, h - 15]])
    H = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, H, (w + 60, h + 60), borderValue=(255, 255, 255))


def test_grid_rectification_recovers_pitch_within_1pct():
    img, _ = _sheet()
    rect = la.rectify(_perspective(img), PITCH_MM, 8.0, [(COLS, ROWS)])
    assert rect["status"] == "ok"
    assert abs(rect["pitch_check_mm"] - PITCH_MM) / PITCH_MM < 0.01


def test_leaflet_area_round_trip_within_2pct():
    img, area = _sheet()
    rect = la.rectify(_perspective(img), PITCH_MM, 8.0, [(COLS, ROWS)])
    mask = la.segment_leaf(rect["image"], la.DEFAULTS["min_saturation"], 50, largest_only=True)
    est = mask.sum() / rect["px_per_mm"] ** 2
    assert abs(est - area) / area < 0.02


def test_no_grid_is_scale_unavailable_not_guessed():
    img = np.full((400, 600, 3), 255, np.uint8)
    cv2.ellipse(img, (300, 200), (80, 40), 0, 0, 360, (40, 150, 60), -1)
    assert la.rectify(img, PITCH_MM, 8.0, [(COLS, ROWS)])["status"] == "scale_unavailable"


def test_compound_whose_leaflet_sum_exceeds_area_is_reported():
    assert la.check_compound_sum([500.0, 600.0], 1000.0, 0.02) == "qa_fail_leaflet_sum_exceeds_compound"
    assert la.check_compound_sum([400.0, 500.0], 1000.0, 0.02) == "ok"
    comp = [dict(status="ok", plant_id="p", compound_id="L01", compound_area_mm2=1000.0,
                 leaflets=[dict(leaflet_id="T", area_mm2=500.0), dict(leaflet_id="P1L", area_mm2=400.0)])]
    leaf = [dict(plant_id="p", compound_id="L01", leaflet_id="T", area_mm2=600.0),
            dict(plant_id="p", compound_id="L01", leaflet_id="P1L", area_mm2=500.0)]
    _, qa = la.leaflet_in_compound(comp, leaf)
    assert qa[0]["status"] == "qa_fail_leaflet_sum_exceeds_compound"
    # a compound without a full leaflet set is skipped by QA and marked leaflet_photos_absent (rev. C.1)
    rows, qa2 = la.leaflet_in_compound(comp, leaf[:1])
    assert qa2 == [] and any(r["status"] == "leaflet_photos_absent" for r in rows)


def _leaf_session(tmp: Path, rows: list[dict], extra_files=()) -> Path:
    s = tmp / "raw" / "dwt_900" / "dwt_900_leaf_20261005"
    s.mkdir(parents=True)
    for r in rows:
        (s / r["photo_file"]).write_bytes(b"x")
    for e in extra_files:
        (s / e).write_bytes(b"x")
    with (s / "leaf_area_capture.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=la.LEAF_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return s


def _row(**k):
    base = dict(plant_id="dwt_900", session_id="dwt_900_leaf_20261005", photo_file="L01_compound.jpg",
                compound_id="L01", leaflet_id="", level="compound", attachment="attached", condition="healthy",
                grid_pitch_mm="10", captured_at="2026-10-05T23:00:00+09:00", pressed="yes", notes="")
    base.update(k)
    return base


def test_missing_pitch_or_unlisted_photo_is_incomplete(tmp_path):
    s = _leaf_session(tmp_path, [_row(), _row(photo_file="L01_T.jpg", level="leaflet", leaflet_id="T", grid_pitch_mm="")],
                      extra_files=("L01_P1L.jpg",))
    res = la.validate_leaf_session(s)
    probs = {(p.get("photo"), p["problem"], p["reason"]) for p in res["problems"]}
    assert ("L01_T.jpg", "incomplete", "incomplete_grid_pitch") in probs
    assert ("L01_P1L.jpg", "incomplete", "photo_not_in_csv") in probs
    assert res["status"] == "incomplete"


def test_compound_only_session_is_ok(tmp_path):
    s = _leaf_session(tmp_path, [_row()])
    assert la.validate_leaf_session(s)["status"] == "ok"


def test_unit_area_tier_b_contour():
    t = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    p = unit_area_points(np.c_[30 * np.cos(t), 10 * np.sin(t)])
    x, y = p[:, 0], p[:, 1]
    area = abs(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    assert area == pytest.approx(1.0, rel=1e-6)
    assert np.ptp(x) > np.ptp(y)        # aligned to the principal axis
