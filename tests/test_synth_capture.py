"""Synthetic generator, Addendum A: capture validation, height rule, unresolved compounds,
measured ranges, contour source tagging and test-plant exclusion. Project environment only."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from tomato3d.synth.capture import (EXPECTED_STEMS, capture_status, discover_sessions, height_from_readings,
                                    resolve_compounds, validate_session)
from tomato3d.synth.config import apply_measured_range, load_generator_config, validate_generator_config

COLUMNS = ["plant_id", "session_id", "photo_file", "photo_kind", "azimuth_deg", "notes", "sha256"]


def _tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _session(raw: Path, plant: str = "dwt_900", *, rows_override=None, skip_files=()) -> Path:
    s = raw / plant / f"{plant}_gen_20261005"
    s.mkdir(parents=True)
    rows = []
    for stem in EXPECTED_STEMS:
        kind = stem.split("_")[0]
        az = "" if kind == "top" else str(int(stem.split("_")[1]))
        name = f"{stem}.heic"
        if stem not in skip_files:
            (s / name).write_bytes(f"photo {stem}".encode())
        rows.append(dict(plant_id=plant, session_id=s.name, photo_file=name, photo_kind=kind, azimuth_deg=az,
                         notes="pot_height_cm=7; soil_depth_below_rim_cm=0.5; strong curl" if kind == "top" else "",
                         sha256=""))
    if rows_override:
        rows = rows_override(rows)
    with (s / "generator_capture.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return s


def test_capture_csv_problems_reported_not_crashed_and_data_untouched(tmp_path):
    raw = tmp_path / "raw"

    def bad(rows):
        rows[1] = dict(rows[1], photo_kind="closeup")            # unknown kind
        rows[2] = dict(rows[2], photo_file=rows[3]["photo_file"])  # duplicate file
        rows.append(dict(rows[0], photo_file="ghost.heic"))       # missing file (and duplicate top slot)
        return rows

    _session(raw, rows_override=bad)
    before = _tree_hash(raw)
    sessions = [validate_session(s) for s in discover_sessions(raw)]
    after = _tree_hash(raw)
    assert before == after
    problems = {p["problem"] for p in sessions[0]["problems"]}
    assert {"unknown_photo_kind", "duplicate_photo_file", "incomplete"} <= problems
    assert sessions[0]["status"] != "ok"
    assert capture_status(sessions) == "pending"


def test_complete_session_ok_and_incomplete_listed(tmp_path):
    raw = tmp_path / "raw"
    _session(raw, "dwt_901")
    _session(raw, "dwt_902", skip_files=("level_180",))
    sessions = {s["plant_id"]: s for s in (validate_session(p) for p in discover_sessions(raw))}
    assert sessions["dwt_901"]["status"] == "ok"
    assert sessions["dwt_901"]["notes"]["soil_depth_below_rim_cm"] == "0.5"
    s2 = sessions["dwt_902"]
    assert s2["status"] in ("incomplete", "issues")
    inc = [p for p in s2["problems"] if p["problem"] == "incomplete"]
    assert inc and "level_180" in inc[0]["missing"]
    assert capture_status(list(sessions.values())) == "partial"


def test_no_capture_folder_is_pending(tmp_path):
    assert discover_sessions(tmp_path / "does_not_exist") == []
    assert capture_status([]) == "pending"
    cfg = load_generator_config()
    assert cfg["compound_capture_status"] == "pending"


def test_height_inconsistent_when_spread_exceeds_limit():
    ok = height_from_readings([dict(azimuth_deg=a, rim_cm=7.0, top_cm=13.0 + d) for a, d in
                               zip((0, 90, 180, 270), (0.0, 0.2, 0.4, 0.1))], 1.0)
    assert ok["flags"] == [] and abs(ok["height_above_rim_cm"] - 6.15) < 1e-9
    bad = height_from_readings([dict(azimuth_deg=a, rim_cm=7.0, top_cm=13.0 + d) for a, d in
                                zip((0, 90, 180, 270), (0.0, 1.2, 0.3, 0.1))], 1.0)
    assert "height_inconsistent" in bad["flags"]


def test_unresolved_compound_reported():
    status = resolve_compounds({"L01": ["side_090"], "L02": []})
    assert status == {"L01": "resolved", "L02": "unresolved"}


def test_measured_range_carries_source_and_keeps_history():
    cfg = load_generator_config()
    new = apply_measured_range(cfg, "leaflet_pairs", 2, 3, {"compound_priors.csv": "ab" * 32}, "test")
    entry = new["ranges"]["leaflet_pairs"]
    assert entry["source_kind"] == "measured_range" and entry["source_ref"]
    assert new["history"][-1]["old"]["source_kind"] == "user_assumed"
    assert cfg["ranges"]["leaflet_pairs"]["source_kind"] == "user_assumed"   # input not mutated
    broken = json.loads(json.dumps(new))
    broken["ranges"]["leaflet_pairs"]["source_kind"] = "guess"
    with pytest.raises(ValueError):
        validate_generator_config(broken)


def _fake_export(root: Path, plant: str) -> Path:
    exp = root / plant / "exports" / "accepted_x"
    exp.mkdir(parents=True)
    obs = []
    for i, (cx, cy) in enumerate([(200, 200), (600, 600)]):
        m = np.zeros((1000, 1000), np.uint8)
        cv2.ellipse(m, (cx, cy), (90, 45), 20, 0, 360, 255, -1)
        name = f"{plant}_a{i}.png"
        cv2.imencode(".png", m)[1].tofile(str(exp / name))
        obs.append(dict(id=f"{plant}_a{i}", organ_class="leaflet", image_file=f"{plant}_img.png", mask_file=name,
                        image_provenance=dict(view_group="middle")))
    (exp / "accepted.json").write_text(json.dumps(dict(observations=obs)), encoding="utf-8")
    return exp


def test_contour_sources_tagged_and_test_plants_excluded(tmp_path):
    from tomato3d.synth.contours import build_library

    sources = {"dwt_801": _fake_export(tmp_path, "dwt_801"), "dwt_802": _fake_export(tmp_path, "dwt_802")}
    lib, audit = build_library(sources, [], n_points=32, max_contact=0.1, min_solidity=0.85, min_dominant=0.95,
                               downscale=4, exclude_plants=["dwt_802"])
    assert lib and all(r["source"] == "view18_reviewed" for r in lib)
    assert {r["plant_id"] for r in lib} == {"dwt_801"}
    assert all(a["selection"] == "excluded_test_plant" for a in audit if a["plant_id"] == "dwt_802")
    pts = np.asarray(lib[0]["points"])
    assert pts[:, 0].min() == pytest.approx(0.0, abs=1e-6) and pts[:, 0].max() == pytest.approx(1.0, abs=1e-3)
