"""Rim-point clicking tool (P1 T6 helper): JS preview == potscale.py, CSV round trip, builder refusals."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tomato3d.cli import rim_points_tool as tool
from tomato3d.io.tables import write_table
from tomato3d.state import potscale as ps
from tomato3d.state import schema as s

CORE = Path(tool.__file__).with_name("rim_core.js")
NODE = shutil.which("node")
H_TRUE = np.array([[24.0, 1.5, 1500.0], [0.8, -23.0, 1600.0], [0.0009, 0.0006, 1.0]])


def _points() -> list[dict]:
    h, t = 30.0, np.linspace(-22, 22, 4)
    sides = {1: np.c_[t, np.full_like(t, -h)], 2: np.c_[np.full_like(t, h), t],
             3: np.c_[t[::-1], np.full_like(t, h)], 4: np.c_[np.full_like(t, -h), t[::-1]]}
    rng = np.random.default_rng(3)
    pts = []
    for k, plane in sides.items():
        for x, y in ps.apply_h(H_TRUE, plane) + rng.normal(0, 1.5, (len(plane), 2)):
            pts.append(dict(kind="rim_edge", side=k, x=float(x), y=float(y)))
    for mm, plane in ((0.0, (-20.0, -25.0)), (40.0, (20.0, -25.0))):
        x, y = ps.apply_h(H_TRUE, np.array([plane]))[0]
        pts.append(dict(kind="ruler_tick", side=None, x=float(x), y=float(y), mm=mm))
    return pts


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_js_preview_equals_potscale_and_csv_round_trips(tmp_path) -> None:
    pts = _points()
    script = tmp_path / "run.js"
    script.write_text(
        f"const C = require({json.dumps(str(CORE))});\n"
        f"const pts = {json.dumps(pts)};\n"
        "const csv = C.toCSV([{plant_id: 'dwt_101', image_sha256: 'abc', points: pts}], 2, 'T');\n"
        "const back = C.parseCSV(csv);  // derive from what the record holds (coordinates rounded to 0.01 px)\n"
        "const sides = {1: [], 2: [], 3: [], 4: []}, ticks = [];\n"
        "for (const p of back) { if (p.kind === 'rim_edge') sides[+p.side].push([+p.x_px, +p.y_px]); "
        "else ticks.push({xy: [+p.x_px, +p.y_px], mm: +p.ruler_reading_mm}); }\n"
        "const r = C.derive(sides, 60, ticks);\n"
        "console.log(JSON.stringify({ok: r.ok, mmPerPx: r.mmPerPx, ruler: r.rulerDisagreement, csv, n: back.length}));\n",
        encoding="utf-8")
    out = json.loads(subprocess.run([NODE, str(script)], capture_output=True, text=True, check=True).stdout)
    csv_path = tmp_path / "rim_points.csv"
    csv_path.write_text(out["csv"], encoding="utf-8")
    points = ps.read_rim_points(csv_path)[("dwt_101", "abc")]
    spec = ps.PotSpec("cell", "square", ("dwt_1*",), 60.0, None, 70.0, "measured", "spec")
    py = ps.derive(points, spec, draws=50, seed=1, accept_rel=0.02, stop_rel=0.05, record_ref="r")
    assert out["ok"] and out["n"] == len(pts)
    assert out["mmPerPx"] == pytest.approx(py.mm_per_px, rel=1e-6), "the preview shows what the P1 run computes"
    assert out["ruler"] == pytest.approx(py.ruler_disagreement, abs=1e-6)
    assert out["csv"].splitlines()[0] == ",".join(ps.RIM_POINTS_COLUMNS)


def _fake_heic(path: Path, w: int, h: int, irot: int | None = None) -> None:
    def box(typ: bytes, body: bytes) -> bytes:
        return struct.pack(">I4s", 8 + len(body), typ) + body
    props = box(b"ispe", b"\0\0\0\0" + struct.pack(">II", w, h))
    if irot is not None:
        props += box(b"irot", bytes([irot]))
    path.write_bytes(box(b"ftyp", b"heic\0\0\0\0") + box(b"meta", b"\0\0\0\0" + box(b"iprp", box(b"ipco", props))))


def _package(tmp: Path, heic: Path) -> Path:
    pkg = tmp / "pkg"
    pkg.mkdir()
    row = {c: "unavailable" for c in s.CAPTURES_COLUMNS}
    row.update(capture_id="dwt_101_gen/top", plant_instance_id="dwt_101", source_plant_id="dwt_101",
               evidence="real_photo", view="top", image_path=heic.relative_to(tool.PROJECT_ROOT).as_posix(),
               image_sha256=tool._sha(heic))
    write_table(pkg / "captures.csv", [row], s.CAPTURES_COLUMNS)
    return pkg


@pytest.fixture()
def project_tmp(tmp_path):
    """A scratch folder inside the project (image_path is project-relative)."""
    d = tool.PROJECT_ROOT / "build" / f"_test_rim_tool_{tmp_path.name}"
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_builder_writes_page_and_refuses_mismatches(project_tmp) -> None:
    heic, images = project_tmp / "top.heic", project_tmp / "imgs"
    images.mkdir()
    _fake_heic(heic, 64, 64)
    Image.new("RGB", (64, 64), "white").save(images / "dwt_101_top.jpg")
    pkg = _package(project_tmp, heic)
    page = tool.build(pkg, project_tmp / "out", images)
    html = page.read_text(encoding="utf-8")
    assert "__MANIFEST__" not in html and "dwt_101" in html and (page.parent / "rim_core.js").exists()
    assert "data:image/jpeg;base64," in html and 'src="rim_core.js"' not in html and "RimCore = api" in html, \
        "self-contained: photos and preview code embedded"
    doc = json.loads((page.parent / "manifest.json").read_text(encoding="utf-8"))
    assert doc["columns"] == list(ps.RIM_POINTS_COLUMNS) and doc["photos"][0]["image_sha256"] == tool._sha(heic)
    assert (project_tmp / "out" / doc["photos"][0]["jpg"]).resolve() == (images / "dwt_101_top.jpg").resolve()
    with pytest.raises(tool.ToolInputError, match="never overwritten"):
        tool.build(pkg, project_tmp / "out", images)
    Image.new("RGB", (64, 48), "white").save(images / "dwt_101_top.jpg")
    with pytest.raises(tool.ToolInputError, match="different pixel grids"):
        tool.build(pkg, project_tmp / "out2", images)
    Image.new("RGB", (64, 64), "white").save(images / "dwt_101_top.jpg")
    _fake_heic(heic, 64, 64, irot=1)
    with pytest.raises(tool.ToolInputError, match="sha256"):
        tool.build(pkg, project_tmp / "out3", images)
    pkg2 = project_tmp / "pkg2"
    shutil.copytree(pkg, pkg2)
    rows = [dict(r, image_sha256=tool._sha(heic)) for r in __import__("tomato3d.io.tables", fromlist=["x"]).read_table(pkg / "captures.csv")]
    write_table(pkg2 / "captures.csv", rows, s.CAPTURES_COLUMNS)
    with pytest.raises(tool.ToolInputError, match="rotation"):
        tool.build(pkg2, project_tmp / "out4", images)
