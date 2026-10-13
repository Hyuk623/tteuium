"""P1 side rim pose (2026-10-12): EXIF focal bases, pose + self-check, vertical scale, ruler ambiguity, records, tool."""

from __future__ import annotations

import csv
import json
import math
import shutil
import struct
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tomato3d.cli import rim_points_tool as tool
from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.io.tables import write_table
from tomato3d.state import camera as cam
from tomato3d.state import potscale as ps
from tomato3d.state import schema as s

F, PP = 6000.0, (1512.0, 1512.0)
SPEC = ps.PotSpec("cell", "square", ("dwt_1*",), 60.0, None, 70.0, "measured", "pot_spec.csv#line2")
KW = dict(pp=PP, draws=200, seed=3, k_sigma=2.0, accept_rel=0.02, stop_rel=0.05)


def look_at(centre: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    z = -centre / np.linalg.norm(centre)
    x = np.cross(z, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    rot = np.vstack([x, np.cross(z, x), z])
    return rot, -rot @ centre


def scene(elev_deg: float, dist: float = 250.0, ticks: tuple[float, ...] = ()):
    e = math.radians(elev_deg)
    centre = np.array([0.0, -dist * math.cos(e), dist * math.sin(e)])
    rot, t = look_at(centre)
    k = cam.intrinsics(F, PP)
    h, s_ = 30.0, np.linspace(-22, 22, 3)
    plane = {1: np.c_[s_, np.full(3, -h)], 2: np.c_[np.full(3, h), s_], 3: np.c_[s_[::-1], np.full(3, h)],
             4: np.c_[np.full(3, -h), s_[::-1]]}
    pts = [ps.RimPoint("rim_edge", side, (float(u), float(v)), 1.0, None)
           for side, xy in plane.items() for u, v in cam.project(rot, t, k, np.c_[xy, np.zeros(len(xy))])]
    for reading in ticks:  # upright ruler at (45, 20), reading 0 at z = -70 (the table)
        (u, v), = cam.project(rot, t, k, np.array([[45.0, 20.0, -70.0 + reading]]))
        pts.append(ps.RimPoint("ruler_tick", None, (float(u), float(v)), 1.0, reading))
    return pts, rot, t, k


def test_focal_bases_from_exif_numbers() -> None:
    fc = cam.focal_candidates(dict(f35_mm=52.0, exif_width_px=4032, exif_height_px=3024))
    assert fc["width"] == pytest.approx(5824.0) and fc["diagonal"] == pytest.approx(52 * 5040 / math.hypot(36, 24), rel=1e-12)


def test_real_heic_exif_if_present() -> None:
    heics = sorted(Path(tool.PROJECT_ROOT, "data/raw").glob("dwt_101/*/side_000.heic"))
    if not heics:
        pytest.skip("raw photos absent")
    ex = cam.read_exif(heics[0])
    assert ex["f35_mm"] == 52.0 and (ex["exif_width_px"], ex["exif_height_px"]) == (4032.0, 3024.0)
    assert cam.heic_geometry(heics[0])[0] == (3024, 3024), "stored photo = a crop of the EXIF frame"


def test_side_view_pose_validates_the_right_focal_basis() -> None:
    pts, rot, t, k = scene(25)
    r = cam.analyse(pts, SPEC, focal={"width": F, "diagonal": F * 1.15}, view="side", **KW)
    assert r.status == "validated" and r.f_basis == "width"
    assert not r.per_basis["diagonal"]["passes"], "a 15 % wrong focal fails the two-axis self-check"
    assert r.distance_mm == pytest.approx(250.0, abs=0.5) and r.tilt_deg == pytest.approx(65.0, abs=0.2)
    assert r.focal_from_rim_px == pytest.approx(F, rel=1e-6)
    assert r.vertical_mm_per_px == pytest.approx(cam.vertical_mm_per_px(rot, t, k), rel=1e-6)
    assert r.vertical_mm_per_px_sd > 0, "never an mm value without its uncertainty"


def test_pose_is_approximate_when_no_basis_closes_the_self_check() -> None:
    pts, *_ = scene(25)
    r = cam.analyse(pts, SPEC, focal={"width": F * 1.15, "diagonal": F * 1.2}, view="side", **KW)
    assert r.status == "approximate" and "crop offset" in r.reason
    assert r.vertical_mm_per_px is not None, "computed, but a vertical scale is published only for validated poses"


def test_frontal_top_views_cannot_tell_the_bases_apart() -> None:
    pts, *_ = scene(85)
    r = cam.analyse(pts, SPEC, focal={"width": F, "diagonal": F * 1.04}, view="top", **KW)
    assert r.per_basis["width"]["passes"] and r.per_basis["diagonal"]["passes"]
    assert r.focal_from_rim_sd_px > 0.05 * F, "near-frontal: the focal the rim implies is ill conditioned"


def test_upright_ruler_needs_an_anchor() -> None:
    pts, rot, t, k = scene(25, ticks=(20.0, 120.0))
    ticks = [(p.xy, p.ruler_mm) for p in pts if p.kind == "ruler_tick"]
    with pytest.raises(cam.CameraError, match="ambiguity"):
        cam.ruler_vertical_fit(rot, t, k, ticks)
    fit = cam.ruler_vertical_fit(rot, t, k, ticks, z0_mm=-70.0)
    assert fit["k_ratio"] == pytest.approx(1.0, abs=1e-6) and fit["x_mm"] == pytest.approx(45.0, abs=1e-4)
    # the ambiguity itself: the same ruler scaled about the camera centre projects to the same pixels
    c = -rot.T @ t
    for reading in (20.0, 120.0):
        p = np.array([45.0, 20.0, -70.0 + reading])
        q = c + 1.3 * (p - c)
        assert np.allclose(cam.project(rot, t, k, p[None]), cam.project(rot, t, k, q[None]), atol=1e-6)
    r = cam.analyse(pts, SPEC, focal={"width": F, "diagonal": F * 1.15}, view="side", **KW)
    assert r.cross_check == "unavailable" and r.scale_sources == 1 and "ambiguity" in r.reason


def _pose_row(**over: str) -> dict[str, str]:
    row = {c: UNAVAILABLE for c in s.CAMERA_POSES_COLUMNS}
    row.update(plant_instance_id="dwt_101", capture_id="c_side", view="side", image_sha256="abc", pose_status="validated",
               reason=UNAVAILABLE, f_px="6000", camera_distance_mm="250", camera_distance_sd_mm="1",
               self_check_ratio_residual="0.001", self_check_ratio_sd="0.008", self_check_orth_residual="0.002",
               self_check_orth_sd="0.01", evidence="real_photo")
    row.update(over)
    return row


def test_camera_pose_and_vertical_scale_validators() -> None:
    s.check_camera_poses([_pose_row()])
    with pytest.raises(s.P1SchemaError, match="reason"):
        s.check_camera_poses([_pose_row(pose_status="approximate")])
    with pytest.raises(s.P1SchemaError, match="without camera_distance_mm"):
        s.check_camera_poses([_pose_row(camera_distance_mm=UNAVAILABLE)])
    cap = {c: UNAVAILABLE for c in s.CAPTURES_COLUMNS}
    cap.update(capture_id="c_side", plant_instance_id="dwt_101", source_plant_id="dwt_101", evidence="real_photo",
               view="side", frame="image_px", image_sha256="abc", scale_status="solved", mm_per_px="0.05",
               mm_per_px_sd="0.0005", scale_convention="pot_rim_pose_vertical_axis", scale_sources="1",
               scale_cross_check="none_single_source", scale_plane="pot_axis_vertical", scale_source="pot_rim:x;pose",
               scale_reference="outer_top_edge_60mm", scale_reference_plane="pot_rim", scale_reference_plane_offset_mm="0")
    s.check_captures([cap])
    with pytest.raises(s.P1SchemaError, match="pot_axis_vertical"):
        s.check_captures([dict(cap, scale_plane="rim_plane")])
    with pytest.raises(s.P1SchemaError, match="validated pose"):
        s.check_camera_poses([_pose_row(pose_status="approximate", reason="self-check fails")], [cap])


def test_rim_point_files_merge_and_old_record_parses(tmp_path) -> None:
    head = ",".join(ps.RIM_POINTS_COLUMNS_V1)  # an old record (no edge column) still parses
    (tmp_path / "rim_points.csv").write_text(head + "\ndwt_101,aaa,rim_edge,1,1,2,4,,s,\n", encoding="utf-8")
    (tmp_path / "rim_points_side.csv").write_text(head + "\ndwt_101,bbb,rim_edge,1,1,2,4,,s,\n", encoding="utf-8")
    merged = ps.read_rim_points_all(ps.rim_point_files(tmp_path))
    assert set(merged) == {("dwt_101", "aaa"), ("dwt_101", "bbb")}
    (tmp_path / "rim_points_more.csv").write_text(head + "\ndwt_101,aaa,rim_edge,2,1,2,4,,s,\n", encoding="utf-8")
    with pytest.raises(ps.PotRecordError, match="appears in both"):
        ps.read_rim_points_all(ps.rim_point_files(tmp_path))


def _fake_heic(path: Path, w: int, h: int) -> None:
    def box(typ: bytes, body: bytes) -> bytes:
        return struct.pack(">I4s", 8 + len(body), typ) + body
    props = box(b"ispe", b"\0\0\0\0" + struct.pack(">II", w, h))
    path.write_bytes(box(b"ftyp", b"heic\0\0\0\0") + box(b"meta", b"\0\0\0\0" + box(b"iprp", box(b"ipco", props))))


def test_tool_side_view(tmp_path) -> None:
    d = tool.PROJECT_ROOT / "build" / f"_test_rim_tool_side_{tmp_path.name}"
    d.mkdir(parents=True)
    try:
        (d / "raw").mkdir()
        heic, imgs = d / "raw" / "side_090.heic", d / "imgs"
        imgs.mkdir()
        _fake_heic(heic, 64, 64)
        Image.new("RGB", (64, 64), "white").save(imgs / "dwt_101_side_090.jpg")
        pkg = d / "pkg"
        pkg.mkdir()
        row = {c: UNAVAILABLE for c in s.CAPTURES_COLUMNS}
        row.update(capture_id="dwt_101_gen/side_090", plant_instance_id="dwt_101", source_plant_id="dwt_101",
                   evidence="real_photo", view="side", image_path=heic.relative_to(tool.PROJECT_ROOT).as_posix(),
                   image_sha256=tool._sha(heic))
        write_table(pkg / "captures.csv", [row], s.CAPTURES_COLUMNS)
        page = tool.build(pkg, d / "out", imgs, view="side")
        doc = json.loads((page.parent / "manifest.json").read_text(encoding="utf-8"))
        assert doc["view"] == "side" and doc["output_name"] == "rim_points_side.csv"
        assert doc["photos"][0]["label"] == "dwt_101 side_090"
        with pytest.raises(tool.ToolInputError, match="no real top captures"):
            tool.build(pkg, d / "out2", imgs, view="top")
        Image.new("RGB", (64, 32), "white").save(imgs / "dwt_101_side_090.jpg")
        with pytest.raises(tool.ToolInputError, match="different pixel grids"):
            tool.build(pkg, d / "out3", imgs, view="side")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_tool_stem_filter_names_the_output(tmp_path) -> None:
    d = tool.PROJECT_ROOT / "build" / f"_test_rim_tool_stem_{tmp_path.name}"
    d.mkdir(parents=True)
    try:
        (d / "raw").mkdir()
        (d / "imgs").mkdir()
        heic = d / "raw" / "side_090.heic"
        _fake_heic(heic, 32, 32)
        Image.new("RGB", (32, 32), "white").save(d / "imgs" / "dwt_101_side_090.jpg")
        (d / "pkg").mkdir()
        row = {c: UNAVAILABLE for c in s.CAPTURES_COLUMNS}
        row.update(capture_id="dwt_101_gen/side_090", plant_instance_id="dwt_101", source_plant_id="dwt_101",
                   evidence="real_photo", view="side", image_path=heic.relative_to(tool.PROJECT_ROOT).as_posix(),
                   image_sha256=tool._sha(heic))
        write_table(d / "pkg" / "captures.csv", [row], s.CAPTURES_COLUMNS)
        page = tool.build(d / "pkg", d / "out", d / "imgs", view="side", stem="side_090")
        doc = json.loads((page.parent / "manifest.json").read_text(encoding="utf-8"))
        assert doc["output_name"] == "rim_points_side_090.csv" and len(doc["photos"]) == 1
        assert ps.rim_point_files.__doc__ and "rim_points_*" in ps.rim_point_files.__doc__, "per-stem files are read"
        with pytest.raises(tool.ToolInputError, match="with photo side_000"):
            tool.build(d / "pkg", d / "out2", d / "imgs", view="side", stem="side_000")
    finally:
        shutil.rmtree(d, ignore_errors=True)
