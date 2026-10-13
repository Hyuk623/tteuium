"""P1 rim inner plane (2026-10-13): inner edge / medium depth records, the reference plane travels with every mm
value (refused without it), per-line planes, three-edge solve with the fourth side occluded, plane bias."""

from __future__ import annotations

import math

import numpy as np
import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import camera as cam
from tomato3d.state import potscale as ps
from tomato3d.state import schema as s

F, PP = 6000.0, (1512.0, 1512.0)
SPEC = ps.PotSpec("cell", "square", ("dwt_1*",), 60.0, None, 70.0, "measured", "pot_spec.csv#line2",
                  inner_edge_mm=59.0, inner_edge_source="measured", medium_depth_mm=10.0,
                  medium_depth_source="measured", wall_taper="none", wall_taper_source="measured")
LEGACY_SPEC = ps.PotSpec("cell", "square", ("dwt_1*",), 60.0, None, 70.0, "measured", "pot_spec.csv#line2")
KW = dict(draws=120, seed=5, accept_rel=0.02, stop_rel=0.05, record_ref="t")
HALF = {"outer_top": (30.0, 0.0), "inner_top": (29.5, 0.0), "medium_junction": (29.5, -10.0)}


def camera(elev_deg: float, dist: float = 230.0, az_deg: float = 0.0):
    e, a = math.radians(elev_deg), math.radians(az_deg)
    centre = dist * np.array([math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)])
    z = -centre / np.linalg.norm(centre)
    x = np.cross(z, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    rot = np.vstack([x, np.cross(z, x), z])
    return rot, -rot @ centre, cam.intrinsics(F, PP)


def points(rot, t, k, edges: dict[int, str], occluded: tuple[int, ...] = (), sigma: float = 0.5) -> list[ps.RimPoint]:
    """Sides 1 (y=-h, front), 2 (x=+h), 3 (y=+h, back), 4 (x=-h), each on its own line and plane."""
    out = []
    for side, edge in edges.items():
        if side in occluded:
            continue
        h, z = HALF[edge]
        u = np.linspace(-0.7, 0.7, 4) * h
        xy = {1: np.c_[u, np.full(4, -h)], 2: np.c_[np.full(4, h), u], 3: np.c_[u[::-1], np.full(4, h)],
              4: np.c_[np.full(4, -h), u[::-1]]}[side]
        for px, py in cam.project(rot, t, k, np.c_[xy, np.full(4, z)]):
            out.append(ps.RimPoint("rim_edge", side, (float(px), float(py)), sigma, None, edge))
    out += [ps.RimPoint("side_occluded", side, (math.nan, math.nan), None, None, UNAVAILABLE) for side in occluded]
    return out


def true_scale(rot, t, k, z0: float) -> float:
    """mm per px at the image of the pot axis on the plane z = z0 (sqrt |det J| of image -> plane)."""
    g = k @ np.c_[rot[:, 0], rot[:, 1], rot[:, 2] * z0 + t]
    h = np.linalg.inv(g)
    h /= h[2, 2]
    c = ps.apply_h(g / g[2, 2], np.zeros((1, 2)))[0]
    return math.sqrt(abs(np.linalg.det(ps._jacobian(h, c))))


ALL = lambda e: {1: e, 2: e, 3: e, 4: e}  # noqa: E731


# ---------------------------------------------------------------- records

def _write(path, columns, rows):
    import csv
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        w.writerows(rows)
    return path


def test_new_pot_spec_columns_and_old_records(tmp_path) -> None:
    row = ["c", "square", "dwt_1*", "60", "", "70", "measured", "59", "measured", "10", "measured", "none", "measured",
           "caliper", "2026-10-13", ""]
    spec = ps.read_pot_spec(_write(tmp_path / "a.csv", ps.POT_SPEC_COLUMNS, [row]))[0]
    assert (spec.inner_edge_mm, spec.medium_depth_mm, spec.wall_taper) == (59.0, 10.0, "none")
    old = ps.read_pot_spec(_write(tmp_path / "b.csv", ps.POT_SPEC_COLUMNS_V1, [
        ["c", "square", "dwt_1*", "60", "", "70", "measured", "caliper", "2026-10-12", ""]]))[0]
    assert (old.outer_edge_mm, old.inner_edge_mm, old.medium_depth_mm) == (60.0, None, None), "old records parse"
    for i, val, match in ((7, "61", "smaller than"), (8, "", "measured | user_stated"), (11, "conical", "wall_taper"),
                          (10, "guess", "measured | user_stated")):
        bad = list(row)
        bad[i] = val
        with pytest.raises(ps.PotRecordError, match=match):
            ps.read_pot_spec(_write(tmp_path / "c.csv", ps.POT_SPEC_COLUMNS, [bad]))


def test_rim_point_edge_and_occluded_rules(tmp_path) -> None:
    def rows(*r):
        return ps.read_rim_points(_write(tmp_path / "r.csv", ps.RIM_POINTS_COLUMNS, list(r)))
    pts = rows(["dwt_101", "a", "rim_edge", "1", "inner_top", "1", "2", "2", "", "x", ""],
               ["dwt_101", "a", "side_occluded", "3", "", "", "", "", "", "x", ""])[("dwt_101", "a")]
    assert [(p.kind, p.side, p.edge) for p in pts] == [("rim_edge", 1, "inner_top"), ("side_occluded", 3, UNAVAILABLE)]
    with pytest.raises(ps.PotRecordError, match="which rim line"):
        rows(["dwt_101", "a", "rim_edge", "1", "outer", "1", "2", "2", "", "x", ""])
    with pytest.raises(ps.PotRecordError, match="both occluded and clicked"):
        rows(["dwt_101", "a", "rim_edge", "3", "outer_top", "1", "2", "2", "", "x", ""],
             ["dwt_101", "a", "side_occluded", "3", "", "", "", "", "", "x", ""])
    legacy = ps.read_rim_points(_write(tmp_path / "old.csv", ps.RIM_POINTS_COLUMNS_V1,
                                       [["dwt_101", "a", "rim_edge", "1", "1", "2", "2", "", "x", ""]]))
    p = legacy[("dwt_101", "a")][0]
    assert p.edge == "outer_top" and not p.edge_recorded, "old records were clicked on the outer edge"


# ---------------------------------------------------------------- planes

def test_each_line_gives_the_scale_of_its_own_plane() -> None:
    rot, t, k = camera(80)
    rim, medium = true_scale(rot, t, k, 0.0), true_scale(rot, t, k, -10.0)
    outer = ps.derive(points(rot, t, k, ALL("outer_top")), SPEC, **KW)
    inner = ps.derive(points(rot, t, k, ALL("inner_top")), SPEC, **KW)
    junction = ps.derive(points(rot, t, k, ALL("medium_junction")), SPEC, **KW)
    mixed = ps.derive(points(rot, t, k, {1: "inner_top", 2: "outer_top", 3: "outer_top", 4: "outer_top"}), SPEC, **KW)
    for r in (outer, inner, mixed):
        assert r.reference_plane == "pot_rim" and r.reference_plane_offset_mm == 0.0
        assert r.mm_per_px == pytest.approx(rim, rel=1e-6)
    assert outer.convention == "pot_rim_outer_edge_square" and mixed.convention == "pot_rim_edges_square"
    assert "s1:inner_top_edge_59mm" in mixed.reference
    assert junction.reference_plane == "medium_surface" and junction.reference_plane_offset_mm == -10.0
    assert junction.convention == "pot_medium_junction_square"
    assert junction.mm_per_px == pytest.approx(medium, rel=1e-6)
    assert medium / rim - 1 == pytest.approx(10.0 / 230.0, rel=0.05), "a plane 10 mm further: (d + 10) / d"


def test_the_59mm_line_read_as_if_on_the_rim_is_wrong_by_the_plane_distance() -> None:
    """The prompt's warning, made concrete: medium-junction clicks recorded as the outer rim edge."""
    rot, t, k = camera(80)
    pts = [ps.RimPoint(p.kind, p.side, p.xy, p.sigma_px, None, "outer_top")
           for p in points(rot, t, k, ALL("medium_junction"))]
    wrong = ps.derive(pts, SPEC, **KW).mm_per_px
    assert wrong / true_scale(rot, t, k, 0.0) - 1 > 0.05, "(60/59) (d+10)/d - 1 = +6 %: never mix line and plane"


def test_lines_on_two_planes_or_missing_records_leave_it_unavailable() -> None:
    rot, t, k = camera(80)
    r = ps.derive(points(rot, t, k, {1: "medium_junction", 2: "outer_top", 3: "outer_top", 4: "outer_top"}), SPEC, **KW)
    assert r.status == "unavailable" and "different planes" in r.reason
    r = ps.derive(points(rot, t, k, ALL("inner_top")), LEGACY_SPEC, **KW)
    assert r.status == "unavailable" and "pot_rim_inner_edge_mm is not recorded" in r.reason
    tapered = ps.PotSpec(**{**SPEC.__dict__, "wall_taper": UNAVAILABLE, "wall_taper_source": UNAVAILABLE})
    r = ps.derive(points(rot, t, k, ALL("medium_junction")), tapered, **KW)
    assert r.status == "unavailable" and "straight walls" in r.reason
    r = ps.derive(points(rot, t, k, ALL("outer_top"), occluded=(3,)), SPEC, **KW)
    assert r.status == "unavailable" and "homography needs all four" in r.reason and r.occluded_sides == (3,)


# ---------------------------------------------------------------- mandatory plane

def _capture(result: ps.PotScale, **over) -> dict[str, str]:
    row = {c: UNAVAILABLE for c in s.CAPTURES_COLUMNS}
    row.update(capture_id="c", plant_instance_id="dwt_101", source_plant_id="dwt_101", evidence="real_photo",
               view="top", frame="image_px", image_sha256="abc", scale_sources="0")
    row.update({k: v for k, v in ps.capture_fields(result).items() if k in row})
    row.update(over)
    return row


def test_a_mm_value_without_its_reference_plane_is_refused() -> None:
    rot, t, k = camera(80)
    for edges in (ALL("outer_top"), ALL("medium_junction")):
        s.check_captures([_capture(ps.derive(points(rot, t, k, edges), SPEC, **KW))])
    good = _capture(ps.derive(points(rot, t, k, ALL("outer_top")), SPEC, **KW))
    assert (good["scale_reference_plane"], good["scale_reference_plane_offset_mm"]) == ("pot_rim", "0")
    for over, match in ((dict(scale_reference_plane=UNAVAILABLE), "reference plane is unstated"),
                        (dict(scale_reference=UNAVAILABLE), "reference plane is unstated"),
                        (dict(scale_reference_plane="medium_surface"), "refers to plane pot_rim"),
                        (dict(scale_reference_plane_offset_mm="-10"), "offset 0"),
                        (dict(scale_reference_plane_offset_mm=UNAVAILABLE), "not a number"),
                        (dict(scale_reference_plane="table"), "not in")):
        with pytest.raises(s.P1SchemaError, match=match):
            s.check_captures([dict(good, **over)])
    medium = _capture(ps.derive(points(rot, t, k, ALL("medium_junction")), SPEC, **KW))
    with pytest.raises(s.P1SchemaError, match="below the rim"):
        s.check_captures([dict(medium, scale_reference_plane_offset_mm="10")])
    # a revision-5/6 package states its plane in scale_plane; a pre-T6 header has none -> a real mm value is refused
    s.check_captures([{c: good[c] for c in s.CAPTURES_COLUMNS_REV6}])
    with pytest.raises(s.P1SchemaError, match="without its reference plane"):
        s.check_captures([{c: good[c] for c in s.CAPTURES_COLUMNS_REV4}])
    assert s.reference_plane_of({c: good[c] for c in s.CAPTURES_COLUMNS_REV6}) == "pot_rim"
    # areas and frames: an mm value whose capture / frame states no plane is refused
    area = {c: UNAVAILABLE for c in s.AREAS_COLUMNS}
    area.update(plant_instance_id="dwt_101", capture_id="c", evidence="real_photo", area_basis="full_outline",
                scale_source="pot_rim:x", visible_projected_area_mm2="100", visible_projected_area_mm2__status="observed",
                visible_projected_area_mm2_sd="2")
    s.check_areas([area], {"c": "solved"}, {"c": "pot_rim"})
    with pytest.raises(s.P1SchemaError, match="states no reference plane"):
        s.check_areas([area], {"c": "solved"}, {"c": UNAVAILABLE})
    frame = {c: UNAVAILABLE for c in s.FRAME_TRANSFORMS_COLUMNS}
    frame.update(plant_instance_id="dwt_101", capture_id="c", scale_status="solved", mm_per_px="0.04",
                 scale_reference_plane="pot_rim", scale_reference_plane_offset_mm="0")
    s.check_frame_transforms([frame])
    with pytest.raises(s.P1SchemaError, match="without its reference plane"):
        s.check_frame_transforms([dict(frame, scale_reference_plane=UNAVAILABLE)])


# ---------------------------------------------------------------- pose on the rim frame, three edges

def test_pose_from_the_medium_plane_is_reported_in_the_rim_frame() -> None:
    rot, t, k = camera(55, dist=240.0)
    r = cam.analyse(points(rot, t, k, ALL("medium_junction")), SPEC, focal={"width": F}, pp=PP, view="side",
                    draws=100, seed=1, k_sigma=2.0, accept_rel=0.02, stop_rel=0.05)
    assert r.status == "validated" and r.reference_plane == "medium_surface"
    assert r.distance_mm == pytest.approx(240.0, abs=0.5), "distance to the RIM centre, not to the medium plane"
    assert r.vertical_mm_per_px == pytest.approx(cam.vertical_mm_per_px(rot, t, k), rel=1e-4)


def test_three_edges_with_the_back_occluded() -> None:
    rot, t, k = camera(45, dist=250.0)
    edges = {1: "inner_top", 2: "outer_top", 3: "outer_top", 4: "outer_top"}
    pts = points(rot, t, k, edges, occluded=(3,))
    r = cam.analyse(pts, SPEC, focal={"width": F, "diagonal": F * 1.04}, pp=PP, view="side", draws=80, seed=2,
                    k_sigma=2.0, accept_rel=0.02, stop_rel=0.05)
    assert r.status == "approximate" and r.occluded_sides == (3,)
    assert "side 3 occluded" in r.reason and "not a detection failure" in r.reason
    width = r.per_basis["width"]
    assert width["pose"]["distance"] == pytest.approx(250.0, abs=0.5), "right focal -> right pose from three lines"
    assert width["vertical"] == pytest.approx(cam.vertical_mm_per_px(rot, t, k), rel=1e-3)
    assert width["ratio_residual"] is None, "three lines: no redundancy for the self-check"
    assert abs(r.per_basis["diagonal"]["pose"]["distance"] - 250.0) > 3, "the focal is not identifiable from 3 lines"
    row = {c: UNAVAILABLE for c in s.CAMERA_POSES_COLUMNS}
    row.update(plant_instance_id="dwt_101", capture_id="c", view="side", image_sha256="abc", pose_status="approximate",
               reason=r.reason, f_px="6000", camera_distance_mm="250", camera_distance_sd_mm="1", evidence="real_photo",
               occluded_sides="3")
    s.check_camera_poses([row])
    with pytest.raises(s.P1SchemaError, match="cannot be validated"):
        s.check_camera_poses([dict(row, pose_status="validated", reason=UNAVAILABLE)])


# ---------------------------------------------------------------- bias

def test_plane_bias_grows_when_the_reference_plane_drops() -> None:
    rim = ps.plane_bias_factor(230.0, 20.0)
    medium = ps.plane_bias_factor(230.0, 20.0, -10.0)
    assert rim == pytest.approx(230 / 210) and medium == pytest.approx(240 / 210)
    assert (rim - 1, rim ** 2 - 1) == (pytest.approx(0.0952, abs=1e-4), pytest.approx(0.1995, abs=1e-4))
    assert (medium - 1, medium ** 2 - 1) == (pytest.approx(0.1429, abs=1e-4), pytest.approx(0.3061, abs=1e-4))
    assert ps.plane_bias_factor(230.0, 0.0, -10.0) > 1, "even the rim itself is overestimated by a medium reference"
    assert ps.PLANE_BIAS == {"pot_rim": "overestimates_above_rim",
                             "medium_surface": "overestimates_above_medium_surface"}
