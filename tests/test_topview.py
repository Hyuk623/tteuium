"""Top view -> 3D (handoff/CLAUDE_CODE_CLI_PROMPT_TOP_TO_3D_2026-10-12.md): T0 intake + gate, T1 mask measures,
T3 aspect-prior baseline, T2 gate and leaflet truth. Toy inputs only - no detector, SAM or network."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from tomato3d.synth import pairs
from tomato3d.topview import calibration as cal
from tomato3d.topview import geometry as geo
from tomato3d.topview import measure2d as m2


# --------------------------------------------------------------------------- T0
def _write_records(path: Path, rows: list[list[str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cal.COLUMNS)
        w.writerows(rows)
    return path


def _row(i, bend, theta="", alpha=""):
    return [f"R{i}", "dwt_101", "2026-10-12T11:00:00+09:00", "x.HEIC", "ab" * 32, "M", str(i), bend, theta, alpha,
            "", "me", ""]


def test_bend_records_validate_and_derive(tmp_path):
    p = _write_records(tmp_path / "r.csv", [_row(1, "flat", "10"), _row(2, "bent", "100", "10;40;50"),
                                            _row(3, "bent", "120"), _row(4, "intermediate", ""), _row(5, "unknown")])
    rows = cal.read_bend_records(p)
    d = cal.derive_bending(rows, "r.csv")
    assert d["counts"] == {"flat": 1, "bent": 2, "intermediate": 1, "unknown": 1}
    assert d["BENT_FRACTION"]["value"] == 0.5 and d["BENT_FRACTION"]["n"] == 4
    assert d["BENT_FRACTION"]["source_kind"] == "measured"
    assert d["theta_deg_all"]["n"] == 3 and d["theta_deg_bent"]["n"] == 2
    assert d["theta_deg_intermediate"]["value"] == "unavailable"
    ok, _ = cal.calibration_gate(dict(bending=d))
    assert ok


@pytest.mark.parametrize("bad, match", [(_row(1, "curved"), "bend_type"), (_row(1, "bent", "200"), "0-180"),
                                        (_row(1, "bent", "abc"), "not a number")])
def test_bend_records_reject_malformed_rows(tmp_path, bad, match):
    with pytest.raises(cal.BendRecordError, match=match):
        cal.read_bend_records(_write_records(tmp_path / "r.csv", [bad]))


def test_no_records_closes_the_gate_and_examples_are_not_counted(tmp_path):
    ex = tmp_path / "records/compound_bend_types_20261010/compound_bend_examples_20261010.csv"
    ex.parent.mkdir(parents=True)
    ex.write_text("example_id,bend_type\nCURV-1,bent\n", encoding="utf-8")
    r = cal.run_calibration(tmp_path, tmp_path / "out.json")
    assert r["bending"]["BENT_FRACTION"]["value"] == "unavailable"
    assert r["illustrative_examples"]["present"] and "NOT counted" in r["illustrative_examples"]["use"]
    assert r["t2_gate"]["open"] is False


def test_template_example_row_parses(tmp_path):
    tpl, readme = cal.write_template(tmp_path / "tpl")
    assert readme.exists()
    rows = cal.read_bend_records(tpl)
    assert rows[0]["bend_type"] == "bent" and rows[0]["alpha_deg"] == [10.0, 40.0, 35.0]


# --------------------------------------------------------------------------- T1
def test_measure_mask_rotated_ellipse():
    m = np.zeros((400, 400), np.uint8)
    cv2.ellipse(m, (200, 200), (90, 60), 30, 0, 360, 1, -1)   # full axes 180 x 120, long axis at 30 deg
    r = m2.measure_mask(m.astype(bool))
    assert r["length_px"] == pytest.approx(180, abs=3) and r["width_px"] == pytest.approx(120, abs=3)
    assert r["projected_aspect"] == pytest.approx(1.5, abs=0.04)
    assert min(abs(r["axis_deg_image"] - 30), abs(r["axis_deg_image"] - 210)) < 2
    assert r["area_px"] == pytest.approx(math.pi * 90 * 60, rel=0.02)
    assert m2.measure_mask(np.zeros((5, 5), bool)) is None


def test_leaflet_boxes_scale_and_filter():
    cfg = cal.load_config()
    pred = dict(image=dict(width=880, height=880), predictions=[
        dict(x=440, y=440, width=88, height=44, confidence=0.9, **{"class": "leaf"}),
        dict(x=100, y=100, width=10, height=10, confidence=0.9, **{"class": "compond_leaf"}),
        dict(x=100, y=100, width=10, height=10, confidence=0.01, **{"class": "leaf2"})])
    b = m2.leaflet_boxes(pred, cfg, (3024, 3024))
    assert len(b) == 1 and b[0]["cls"] == "leaf"
    s = 3024 / 880
    assert b[0]["box"] == pytest.approx([396 * s, 418 * s, 484 * s, 462 * s])


def test_no_mm_without_a_rim_record(tmp_path):
    r = m2.pot_scale("ab" * 32, None, tmp_path)
    assert r.status == "unavailable" and "plant_id" in r.reason
    r = m2.pot_scale("ab" * 32, "dwt_101", tmp_path)
    assert r.status == "unavailable" and "absent" in r.reason


# --------------------------------------------------------------------------- T3 baseline
def test_pure_pitch_recovers_tilt_and_true_size():
    e_true = 40.0
    r_true = 1.55                                  # mid of the 1.4-1.7 prior
    L, W = 31.0 * math.cos(math.radians(e_true)), 31.0 / r_true
    A = 600.0 * math.cos(math.radians(e_true))
    r = geo.estimate_leaflet(L, W, A, (1.4, 1.7))
    assert r["tilt_deg"] == pytest.approx(e_true, abs=0.05)
    assert r["true_length"] == pytest.approx(31.0, rel=1e-3) and r["true_area"] == pytest.approx(600.0, rel=1e-3)
    lo, hi = r["tilt_deg_interval"]
    assert lo < e_true < hi
    assert r["tilt_sign"] == "unavailable" and r["status"].startswith("inferred")


def test_aspect_above_prior_is_flagged_not_explained():
    r = geo.estimate_leaflet(20.0, 10.0, 150.0, (1.4, 1.7))
    assert r["tilt_deg"] == 0.0 and "flag" in r


# --------------------------------------------------------------------------- T2
def test_leaflet_truth_of_a_tilted_flat_square():
    e = math.radians(30)
    v = np.array([[0, 0, 0], [10 * math.cos(e), 0, 10 * math.sin(e)], [10 * math.cos(e), 10, 10 * math.sin(e)],
                  [0, 10, 0]], float)
    part = dict(vertices=v, faces=np.array([[0, 1, 2], [0, 2, 3]]))
    leaf = dict(heading=[1, 0, 0], length_mm=10.0, bend_deg=0, roll_deg=0, twist_deg=0)
    t = pairs.leaflet_truth(part, leaf, rotation_deg=0.0)
    assert t["true_area_mm2"] == pytest.approx(100.0)
    assert t["normal_tilt_deg"] == pytest.approx(30.0, abs=1e-6)
    assert t["chord_elevation_deg"] == pytest.approx(30.0, abs=1e-6)


def test_export_refuses_without_calibration(tmp_path):
    c = tmp_path / "cal.json"
    c.write_text(json.dumps(dict(bending=dict(BENT_FRACTION=dict(value="unavailable")))), encoding="utf-8")
    with pytest.raises(SystemExit, match="gate closed"):
        pairs.export_pairs([], tmp_path / "out", calibration=c, geometry_path=tmp_path / "missing.json",
                           generator_config=tmp_path / "missing.json")
