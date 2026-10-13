"""P1 T6: per-pot rim scale (square cell, outer edge across the flats), uncertainty, ruler cross-check."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import package as pk
from tomato3d.state import potscale as ps
from tomato3d.state import schema as s
from tomato3d.state import update as up

EDGE = 60.0
SPEC = ps.PotSpec("cell", "square", ("dwt_1*",), EDGE, None, 70.0, "measured", "pot_spec.csv#line2")
KW = dict(draws=200, seed=7, accept_rel=0.02, stop_rel=0.05, record_ref="rim_points.csv#t")
# plane (mm, Y up, origin = pot centre) -> image px: a tilted handheld perspective view
H_TRUE = np.array([[24.0, 1.5, 1500.0], [0.8, -23.0, 1600.0], [0.0009, 0.0006, 1.0]])


def _to_image(plane_xy) -> np.ndarray:
    return ps.apply_h(H_TRUE, np.asarray(plane_xy, float))


def _rim_points(sigma: float | None = 2.0, per_side: int = 4, noise: float = 0.0, seed: int = 0) -> list[ps.RimPoint]:
    """Points on the FLAT parts of the four outer edges (the cut corners, 8 mm each, are avoided)."""
    rng = np.random.default_rng(seed)
    h = EDGE / 2
    t = np.linspace(-h + 8, h - 8, per_side)
    sides = {1: np.c_[t, np.full_like(t, -h)], 2: np.c_[np.full_like(t, h), t],
             3: np.c_[t[::-1], np.full_like(t, h)], 4: np.c_[np.full_like(t, -h), t[::-1]]}
    out = []
    for k, plane in sides.items():
        for xy in _to_image(plane):
            xy = xy + rng.normal(0, noise, 2) if noise else xy
            out.append(ps.RimPoint("rim_edge", k, (float(xy[0]), float(xy[1])), sigma, None))
    return out


def _ruler(readings_mm: tuple[float, float], plane_a=(-20.0, -25.0), plane_b=(20.0, -25.0)) -> list[ps.RimPoint]:
    a, b = _to_image([plane_a, plane_b])
    return [ps.RimPoint("ruler_tick", None, tuple(a), 2.0, readings_mm[0]),
            ps.RimPoint("ruler_tick", None, tuple(b), 2.0, readings_mm[1])]


def _true_scale_at_centre() -> float:
    hinv = np.linalg.inv(H_TRUE)
    centre = _to_image([[0.0, 0.0]])[0]
    return math.sqrt(abs(np.linalg.det(ps._jacobian(hinv, centre))))


# ---------------------------------------------------------------- derivation

def test_homography_recovers_the_true_rim_plane_scale_and_centre() -> None:
    r = ps.derive(_rim_points(), SPEC, **KW)
    assert r.status == "solved" and r.convention == "pot_rim_outer_edge_square"
    assert r.mm_per_px == pytest.approx(_true_scale_at_centre(), rel=1e-9)
    assert np.allclose(r.center_px, _to_image([[0.0, 0.0]])[0], atol=1e-6)
    h = np.array(r.homography)
    assert np.linalg.det(ps._jacobian(h, np.array(r.center_px))) < 0, "right-handed seen from above (image y down)"
    corner = ps.apply_h(h, _to_image([[EDGE / 2, EDGE / 2]]))[0]
    assert np.allclose(np.abs(corner), EDGE / 2, atol=1e-6), "virtual corners of the across-flats square"
    assert r.anisotropy > 1.0, "perspective: the scale is not isotropic - hence per pot, from its own rim"
    assert r.scale_sources == 1 and r.cross_check == "none_single_source"


def test_uncertainty_follows_the_stated_click_uncertainty() -> None:
    sd1 = ps.derive(_rim_points(sigma=1.0), SPEC, **KW).mm_per_px_sd
    sd4 = ps.derive(_rim_points(sigma=4.0), SPEC, **KW).mm_per_px_sd
    assert 0 < sd1 < sd4 and sd4 / sd1 == pytest.approx(4.0, rel=0.25)
    noisy = ps.derive(_rim_points(sigma=0.1, noise=3.0, per_side=6), SPEC, **KW)
    assert all(noisy.side_sigma_px[k] > 0.1 for k in (1, 2, 3, 4)), "fit residual wins over an optimistic click"
    again = ps.derive(_rim_points(sigma=1.0), SPEC, **KW)
    assert again.mm_per_px_sd == sd1, "seeded: replayable"


@pytest.mark.parametrize("points, spec, reason", [
    (_rim_points(sigma=None), SPEC, "click_uncertainty_px"),
    ([p for p in _rim_points() if p.side != 3], SPEC, "side 3"),
    ([], SPEC, "no rim_edge points"),
    (_rim_points(), None, "no pot type"),
    (_rim_points(), ps.PotSpec("r", "round", ("*",), None, 55.0, None, "measured", "x"), "round-pot"),
])
def test_missing_inputs_leave_the_scale_unavailable(points, spec, reason) -> None:
    r = ps.derive(points, spec, **KW)
    assert r.status == "unavailable" and reason in r.reason and r.mm_per_px is None


def test_sides_out_of_order_are_rejected() -> None:
    pts = [ps.RimPoint(p.kind, {1: 1, 2: 3, 3: 2, 4: 4}[p.side], p.xy, p.sigma_px, None) for p in _rim_points()]
    r = ps.derive(pts, SPEC, **KW)
    assert r.status == "unavailable" and ("convex" in r.reason or "parallel" in r.reason)


@pytest.mark.parametrize("readings, expected, status", [
    ((0.0, 40.0), "accepted_within_2pct", "solved"),
    ((0.0, 41.2), "flagged_2_to_5pct", "solved"),
    ((0.0, 43.0), "stopped_over_5pct", "unavailable"),
])
def test_ruler_cross_check_bands(readings, expected, status) -> None:
    r = ps.derive(_rim_points() + _ruler(readings), SPEC, **KW)
    assert (r.cross_check, r.status, r.scale_sources) == (expected, status, 2)
    assert r.ruler_disagreement == pytest.approx(40.0 / (readings[1] - readings[0]) - 1.0, abs=1e-6)
    row = _capture_row(**_cap_fields(r))
    s.check_captures([row])


# ---------------------------------------------------------------- records

def _write(path: Path, columns, rows) -> Path:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        w.writerows(rows)
    return path


@pytest.mark.parametrize("row, match", [
    (["c", "square", "dwt_1*", "60", "57", "70", "measured", "caliper", "2026-10-12", ""], "never both"),
    (["c", "square", "dwt_1*", "", "", "70", "measured", "caliper", "2026-10-12", ""], "outer_edge"),
    (["c", "round", "dwt_1*", "", "", "70", "measured", "caliper", "2026-10-12", ""], "inner_diameter"),
    (["c", "hex", "dwt_1*", "60", "", "70", "measured", "caliper", "2026-10-12", ""], "shape"),
    (["c", "square", "dwt_1*", "60", "", "70", "guessed", "caliper", "2026-10-12", ""], "source_kind"),
    (["c", "square", "dwt_1*", "-60", "", "70", "measured", "caliper", "2026-10-12", ""], "positive"),
])
def test_pot_spec_rules(tmp_path, row, match) -> None:
    with pytest.raises(ps.PotRecordError, match=match):
        ps.read_pot_spec(_write(tmp_path / "pot_spec.csv", ps.POT_SPEC_COLUMNS_V1, [row]))


def test_pot_spec_matching_and_templates(tmp_path) -> None:
    specs = ps.read_pot_spec(_write(tmp_path / "a.csv", ps.POT_SPEC_COLUMNS_V1, [
        ["c", "square", "dwt_1*", "60", "", "70", "measured", "caliper", "2026-10-12", ""],
        ["d", "square", "dwt_101", "60", "", "70", "measured", "caliper", "2026-10-12", ""]]))
    assert ps.spec_for(specs, "dwt_201") is None
    with pytest.raises(ps.PotRecordError, match="more than one"):
        ps.spec_for(specs, "dwt_101")
    files = ps.write_templates(tmp_path / "tpl")
    spec = ps.read_pot_spec(files[0])[0]
    assert (spec.outer_edge_mm, spec.inner_diameter_mm, spec.depth_mm, spec.source_kind) == (60.0, None, 70.0, "measured")
    assert (spec.inner_edge_mm, spec.medium_depth_mm, spec.wall_taper) == (59.0, 10.0, "none")
    assert (spec.inner_edge_source, spec.medium_depth_source, spec.wall_taper_source) == ("measured",) * 3
    pts = ps.read_rim_points(files[1])
    assert sorted(p.kind for v in pts.values() for p in v) == ["rim_edge", "ruler_tick", "side_occluded"]


@pytest.mark.parametrize("row, match", [
    (["dwt_101", "abc", "rim_edge", "5", "1", "2", "2", "", "x", ""], "side must be 1-4"),
    (["dwt_101", "abc", "ruler_tick", "", "1", "2", "2", "", "x", ""], "ruler_reading_mm"),
    (["dwt_101", "abc", "corner", "1", "1", "2", "2", "", "x", ""], "kind"),
    (["dwt_101", "abc", "rim_edge", "1", "", "2", "2", "", "x", ""], "x_px"),
])
def test_rim_point_rules(tmp_path, row, match) -> None:
    with pytest.raises(ps.PotRecordError, match=match):
        ps.read_rim_points(_write(tmp_path / "rim_points.csv", ps.RIM_POINTS_COLUMNS_V1, [row]))


# ---------------------------------------------------------------- validators

def _cap_fields(result: ps.PotScale) -> dict[str, str]:
    """capture_fields also returns the frame-only homography; captures.csv takes the rest."""
    return {k: v for k, v in ps.capture_fields(result).items() if k in s.CAPTURES_COLUMNS}


def _capture_row(**over: str) -> dict[str, str]:
    row = {c: UNAVAILABLE for c in s.CAPTURES_COLUMNS}
    row.update(capture_id="dwt_101_top", plant_instance_id="dwt_101", source_plant_id="dwt_101", evidence="real_photo",
               view="top", photoperiod_phase=UNAVAILABLE, frame="image_px", scale_status=UNAVAILABLE,
               image_sha256="abc", scale_sources="0")
    row.update(over)
    return row


def test_capture_scale_validator() -> None:
    good = _capture_row(**_cap_fields(ps.derive(_rim_points(), SPEC, **KW)))
    s.check_captures([good])
    for over, match in ((dict(mm_per_px_sd=UNAVAILABLE), "uncertainty"),
                        (dict(scale_source="image_wide_mean"), "image-wide"),
                        (dict(scale_convention="synthetic_ortho_camera_declared"), "convention"),
                        (dict(scale_plane="synthetic_camera"), "rim-plane"),
                        (dict(scale_cross_check="stopped_over_5pct", scale_sources="2"), "more than 5"),
                        (dict(scale_cross_check="accepted_within_2pct"), "two scale sources"),
                        (dict(scale_convention="square"), "scale_convention")):
        with pytest.raises(s.P1SchemaError, match=match):
            s.check_captures([dict(good, **over)])
    legacy = {c: good[c] for c in s.CAPTURES_COLUMNS_REV4}
    legacy.update(scale_status=UNAVAILABLE, scale_source=UNAVAILABLE, mm_per_px=UNAVAILABLE)
    s.check_captures([legacy])


def test_area_uncertainty_is_required_on_real_rows_and_propagated() -> None:
    row = {c: UNAVAILABLE for c in s.AREAS_COLUMNS}
    row.update(plant_instance_id="dwt_101", capture_id="c", evidence="real_photo", area_basis="full_outline",
               scale_source="pot_rim:x", visible_projected_area_mm2="100", visible_projected_area_mm2__status="observed")
    with pytest.raises(s.P1SchemaError, match="uncertainty"):
        s.check_areas([row], {"c": "solved"})
    s.check_areas([dict(row, visible_projected_area_mm2_sd="2")], {"c": "solved"})
    info = up.CaptureInfo("c", "image_px", 0.1, None, None, UNAVAILABLE, None, "real_photo", "pot_rim:x",
                          mm_per_px_sd=0.001)
    obs = {c: UNAVAILABLE for c in s.OBSERVATIONS_COLUMNS}
    obs.update(obs_id="o1", obs_class="compound_leaf", review_state="accepted", area_px2="10000")
    inp = up.SnapshotInputs("dwt_101", "dwt_101", info, [obs], {}, [])
    out = up.area_rows(inp, {})[0]
    assert float(out["visible_projected_area_mm2"]) == pytest.approx(100.0)
    assert float(out["visible_projected_area_mm2_sd"]) == pytest.approx(2.0), "relative sd doubles for an area"
    info_no_sd = up.CaptureInfo("c", "image_px", 0.1, None, None, UNAVAILABLE, None, "real_photo", "pot_rim:x")
    out = up.area_rows(up.SnapshotInputs("dwt_101", "dwt_101", info_no_sd, [obs], {}, []), {})[0]
    assert out["visible_projected_area_mm2"] == UNAVAILABLE, "never an mm value without its uncertainty"


# ---------------------------------------------------------------- real path wiring

def test_real_capture_scale_per_pot(tmp_path, monkeypatch) -> None:
    spec_path = _write(tmp_path / "pot_spec.csv", ps.POT_SPEC_COLUMNS_V1,
                       [["cell", "square", "dwt_1*", "60", "", "70", "measured", "caliper", "2026-10-12", ""]])
    pts = _rim_points() + _ruler((0.0, 40.0))
    rows = [["dwt_101", "sha_top", p.kind, p.side or "", f"{p.xy[0]:.6f}", f"{p.xy[1]:.6f}", "2",
             "" if p.ruler_mm is None else p.ruler_mm, "t", ""] for p in pts]
    pts_path = _write(tmp_path / "rim_points.csv", ps.RIM_POINTS_COLUMNS_V1, rows)
    monkeypatch.setattr(ps, "POT_SPEC_PATH", spec_path)
    monkeypatch.setattr(ps, "RIM_POINTS_PATH", pts_path)
    captures = [_capture_row(capture_id="dwt_101_top", image_sha256="sha_top"),
                _capture_row(capture_id="dwt_101_level_000", view="level", image_sha256="sha_level"),
                _capture_row(capture_id="dwt_102_top", plant_instance_id="dwt_102", source_plant_id="dwt_102",
                             image_sha256="sha_other")]
    gaps: list[dict[str, str]] = []
    frames, reports, poses = pk._real_pot_scale(captures, gaps)
    assert len(poses) == 2 and all(r["pose_status"] == UNAVAILABLE for r in poses), \
        "no readable photo EXIF in this fake package -> pose unavailable, but the top rim scale is still solved"
    s.check_camera_poses(poses, captures)
    s.check_captures(captures)
    top = captures[0]
    assert top["scale_status"] == "solved" and top["scale_cross_check"] == "accepted_within_2pct"
    assert float(top["mm_per_px"]) == pytest.approx(_true_scale_at_centre(), rel=1e-6)
    assert top["scale_source"].startswith("pot_rim:pot_spec.csv#line2")
    assert captures[2]["scale_status"] == UNAVAILABLE, "another pot's rim is never borrowed (no image-wide scale)"
    assert {(g["capture_id"], g["item"]) for g in gaps} == {("dwt_101_level_000", "scale"), ("dwt_102_top", "scale")}
    assert "edge-on" in next(g for g in gaps if g["capture_id"] == "dwt_101_level_000")["missing_input"]
    assert len(frames) == 2 and frames[0]["method"] == "pot_rim_square_homography"
    assert "overestimates" in reports[0]["plane_note"], "leaves above the rim are magnified (Z_rim / Z_leaf > 1)"


def test_real_input_snapshot_hashes_human_records(tmp_path, monkeypatch) -> None:
    spec_path = _write(tmp_path / "pot_spec.csv", ps.POT_SPEC_COLUMNS_V1,
                       [["cell", "square", "dwt_1*", "60", "", "70", "measured", "caliper", "2026-10-12", ""]])
    request = dict(mode="real", raw_dir="data/raw", plant_glob="dwt_1*")
    if not (pk.PROJECT_ROOT / "data/raw").exists():
        pytest.skip("raw data absent")
    before = pk._input_snapshot(request)
    monkeypatch.setattr(ps, "POT_SPEC_PATH", spec_path)
    after = pk._input_snapshot(request)
    added = set(after) - set(before)
    assert len(added) == 1 and next(iter(added)).endswith("pot_spec.csv"), "a new record changes the input snapshot"
