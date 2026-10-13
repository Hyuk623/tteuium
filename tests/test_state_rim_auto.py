"""Automatic rim-line proposals (each names its line), the occluded back side, and the page pre-fill."""

from __future__ import annotations

import json
import shutil
import struct
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from tomato3d.cli import rim_points_tool as tool
from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.io.tables import write_table
from tomato3d.state import potscale as ps
from tomato3d.state import rim_auto as ra
from tomato3d.state import schema as s

# rim band ~20 px wide, inside the module's search band (4 % of the soil width, at least 25 px), as on real photos
OUTER = np.array([[156, 234], [444, 234], [464, 460], [136, 460]], np.int32)  # rim outer edge (side view, flattened)
INNER = np.array([[172, 250], [428, 250], [446, 440], [154, 440]], np.int32)  # soil boundary inside the rim band


def synthetic_side() -> np.ndarray:
    img = np.full((600, 600, 3), 235, np.uint8)            # white paper
    cv2.fillPoly(img, [OUTER], (190, 190, 190))             # translucent rim band (grey)
    cv2.fillPoly(img, [INNER], (40, 80, 140))               # brown soil (BGR)
    return cv2.GaussianBlur(img, (3, 3), 0)


def test_proposals_name_their_line_and_the_back_side_is_occluded() -> None:
    prop = ra.propose(synthetic_side(), "side")
    by = {sp.position: sp for sp in prop.sides}
    assert set(by) == {"front", "back", "left", "right"}
    assert not by["back"].proposed and by["back"].occluded, "the back is proposed as occluded, never as points"
    front = by["front"]
    assert front.proposed and front.edge == "inner_top"
    assert np.allclose(front.points[:, 1], 440, atol=3), "front: the sharp rim/soil line (inner top edge), not 460"
    for side in ("left", "right"):
        assert by[side].proposed and by[side].edge == "outer_top"
    assert prop.status == "proposed", "three lines + one occluded side"
    rows = ra.proposal_rows("dwt_101", "abc", prop)
    assert all(r[9] == ra.METHOD and r[7] == "" for r in rows), "method named; click uncertainty left to the person"
    assert {(r[2], int(r[3])) for r in rows if r[2] == "side_occluded"} == {("side_occluded", by["back"].side)}
    assert {int(r[3]) for r in rows if r[2] == "rim_edge"} == {sp.side for sp in prop.sides if sp.proposed}
    assert ra.propose(synthetic_side(), "top").status == "none", "top photos are not supported"


def test_no_interior_no_proposal() -> None:
    assert ra.propose(np.full((200, 200, 3), 235, np.uint8), "side").status == "none"


def _fake_heic(path: Path, w: int, h: int) -> None:
    def box(typ: bytes, body: bytes) -> bytes:
        return struct.pack(">I4s", 8 + len(body), typ) + body
    props = box(b"ispe", b"\0\0\0\0" + struct.pack(">II", w, h))
    path.write_bytes(box(b"ftyp", b"heic\0\0\0\0") + box(b"meta", b"\0\0\0\0" + box(b"iprp", box(b"ipco", props))))


def test_page_prefill_from_proposals(tmp_path) -> None:
    d = tool.PROJECT_ROOT / "build" / f"_test_rim_prefill_{tmp_path.name}"
    d.mkdir(parents=True)
    try:
        (d / "raw").mkdir()
        (d / "imgs").mkdir()
        heic = d / "raw" / "side_000.heic"
        _fake_heic(heic, 600, 600)
        Image.fromarray(synthetic_side()[..., ::-1]).save(d / "imgs" / "dwt_101_side_000.jpg")
        sha = tool._sha(heic)
        (d / "pkg").mkdir()
        row = {c: UNAVAILABLE for c in s.CAPTURES_COLUMNS}
        row.update(capture_id="dwt_101_gen/side_000", plant_instance_id="dwt_101", source_plant_id="dwt_101",
                   evidence="real_photo", view="side", image_path=heic.relative_to(tool.PROJECT_ROOT).as_posix(),
                   image_sha256=sha)
        write_table(d / "pkg" / "captures.csv", [row], s.CAPTURES_COLUMNS)
        prop = ra.propose(synthetic_side(), "side")
        csv_path = ra.write_proposals(d / "prop.csv", ra.proposal_rows("dwt_101", sha, prop))
        assert ps.read_rim_points(csv_path), "proposals use the record columns (blank click uncertainty is allowed)"
        page = tool.build(d / "pkg", d / "out", d / "imgs", view="side", stem="side_000", prefill=csv_path)
        doc = json.loads((page.parent / "manifest.json").read_text(encoding="utf-8"))
        assert len(doc["photos"][0]["prefill"]) == sum(len(sp.points) for sp in prop.sides)
        assert {q["edge"] for q in doc["photos"][0]["prefill"]} == {"inner_top", "outer_top"}
        assert doc["photos"][0]["prefill_occluded"] == [next(sp.side for sp in prop.sides if sp.occluded)]
        html = page.read_text(encoding="utf-8")
        assert "auto_proposal_kept" in html and "rim_points_tool_v3_" in html, "kept proposals are marked when saved"
    finally:
        shutil.rmtree(d, ignore_errors=True)
