"""P1.3 - real capture ingest, human labels, flagged proposals."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import ingest
from tomato3d.state import schema as s

HEADER = ("plant_id,session_id,photo_file,photo_kind,azimuth_deg,camera_elevation_deg_approx,captured_at,"
          "scale_reference,ruler_plane,exposure_note,notes,source_filename,sha256,azimuth_basis,height_above_rim_cm")


def _raw(root: Path, payload: bytes, csv_sha: str | None = None) -> Path:
    session = root / "data" / "raw" / "dwt_901" / "dwt_901_gen_20261005"
    session.mkdir(parents=True)
    (session / "top.heic").write_bytes(payload)
    sha = csv_sha or hashlib.sha256(payload).hexdigest()
    (session / "generator_capture.csv").write_text(
        HEADER + f"\ndwt_901,dwt_901_gen_20261005,top.heic,top,,90,2026-10-05 17:02:03,ruler_cm,pot_rim,,,"
                 f"IMG.HEIC,{sha},,\n", encoding="utf-8")
    return root / "data" / "raw"


def test_real_capture_rows_reference_by_hash_and_leave_time_and_scale_unavailable(tmp_path) -> None:
    root = tmp_path / "프로젝트"
    raw = _raw(root, b"heic-bytes")
    rows, problems = ingest.real_capture_rows(ingest.discover_raw(raw, "dwt_9*"), root)
    assert not problems
    s.check_captures(rows)
    r = rows[0]
    assert r["capture_id"] == "dwt_901_gen_20261005/top" and r["evidence"] == "real_photo"
    assert r["capture_time"] == "2026-10-05T17:02:03" and r["capture_time__status"] == "measured"
    assert r["time_since_lights_on_min"] == UNAVAILABLE and r["photoperiod_phase"] == UNAVAILABLE
    assert r["scale_status"] == UNAVAILABLE and r["mm_per_px"] == UNAVAILABLE and r["frame"] == "image_px"
    assert r["image_path"] == "data/raw/dwt_901/dwt_901_gen_20261005/top.heic"
    assert r["image_sha256"] == hashlib.sha256(b"heic-bytes").hexdigest()


def test_hash_mismatch_is_reported(tmp_path) -> None:
    raw = _raw(tmp_path, b"heic-bytes", csv_sha="0" * 64)
    _, problems = ingest.real_capture_rows(ingest.discover_raw(raw, "dwt_9*"), tmp_path)
    assert problems and "sha256" in problems[0]


def test_coco_import_and_proposals(tmp_path) -> None:
    coco = dict(categories=[dict(id=1, name="compound_leaf"), dict(id=2, name="leaflet")],
                images=[dict(id=7, file_name="dwt_901_top.jpg", width=40, height=30)],
                annotations=[dict(id=1, image_id=7, category_id=1, bbox=[2, 2, 10, 10],
                                  segmentation=[[2, 2, 12, 2, 12, 12, 2, 12]]),
                             dict(id=2, image_id=7, category_id=2, bbox=[20, 5, 5, 5], segmentation=[])])
    path = tmp_path / "labels.json"
    path.write_text(json.dumps(coco), encoding="utf-8")
    rows, masks, quality = ingest.import_coco(path, {"dwt_901_top.jpg": "cap"}, "dwt_901")
    s.check_observations(rows, "real_photo")
    assert rows[0]["provenance"] == "human" and rows[0]["mask_quality"] == "human_polygon" and "h0001" in masks
    assert rows[1]["mask_ref"] == UNAVAILABLE and rows[1]["mask_quality"] == "box_only_no_mask"
    assert quality["cap"] == "mixed"
    with pytest.raises(ingest.IngestError):
        ingest.import_coco(path, {}, "dwt_901")
    det = [dict(key="dwt_901_top.jpg", rgb_sha256="x", detector_args=dict(weights="w.pt", weights_sha256="ab" * 32,
                                                                             imgsz=512, conf=0.25),
                detections=[dict(cls="compound_leaf", box=[1, 2, 3, 4], conf=0.9)])]
    prop = ingest.proposal_rows(det, {"dwt_901_top.jpg": "cap"}, {"dwt_901_top.jpg": "dwt_901"})
    s.check_observations(prop, "real_photo")
    assert prop[0]["review_state"] == "unreviewed" and prop[0]["detector_status"] == "unvalidated_on_boardfree_top"
    # proposals are never tracked; human rows need this_plant attribution and a mask
    rows[0]["plant_attribution"] = "this_plant"
    assert [r["obs_id"] for r in ingest.trackable(rows + prop)] == ["h0001"]


def test_mask_packing_round_trip() -> None:
    m = np.zeros((7, 9), bool)
    m[1:3, 2:6] = True
    m[5, 8] = True
    doc = ingest.pack_masks({"o1": m})
    assert np.array_equal(ingest.unpack_masks(json.loads(json.dumps(doc)))["o1"], m)
