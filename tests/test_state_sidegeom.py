"""P1.6 - side-view geometry from P0..Pm points; validation against R.1 truth."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import geometry as g
from tomato3d.state import schema as s
from tomato3d.state import sidegeom as sg

SIDE = Path(__file__).parent / "fixtures" / "p1" / "sideprop" / "scenes" / "scene_0000"


def _pt(x: float, y: float) -> np.ndarray:
    return np.array([x, y], float)


def test_planar_points_give_exact_angles() -> None:
    # stem straight up; petiole at 60 deg from the stem; each later segment bends 10 deg downward
    p0 = _pt(0, 0)
    stem_up = _pt(0, 10)
    a = math.radians(30.0)  # petiole elevation above horizontal = 90 - 60
    n1 = p0 + 10 * np.array([math.cos(a), math.sin(a)])
    d2 = math.radians(20.0)
    n2 = n1 + 10 * np.array([math.cos(d2), math.sin(d2)])
    d3 = math.radians(10.0)
    end = n2 + 10 * np.array([math.cos(d3), math.sin(d3)])
    v = sg.measure(sg.SidePoints(p0, [n1, n2], end, stem_up))
    assert abs(v["compound_insertion_angle_deg"] - 60.0) < 1e-9
    assert np.allclose(v["alphas"], [10.0, 10.0])
    assert abs(v["rachis_curvature_deg"] - 20.0) < 1e-9
    # theta excludes the last bend: P1 -> P3 path; here theta = angle(P0->N1, P2->N2) = 10 deg
    assert abs(v["rachis_bend_theta_deg"] - 10.0) < 1e-9
    # a rising distal segment gives a negative alpha
    up_end = n2 + 10 * np.array([math.cos(math.radians(40.0)), math.sin(math.radians(40.0))])
    assert sg.measure(sg.SidePoints(p0, [n1, n2], up_end, stem_up))["alphas"][1] < 0


def test_elevation_and_azimuth_conventions() -> None:
    assert g.elevation_deg(np.array([1.0, 0.0, 1.0])) == 45.0
    assert g.elevation_deg(np.array([1.0, 0.0, -1.0])) == -45.0
    assert g.azimuth_deg(np.array([0.0, 1.0, 0.0])) == 90.0  # +X toward +Y, counter-clockwise from above
    assert g.azimuth_deg(np.array([0.0, 0.0, 1.0])) is None


def test_r1_fixture_validation_and_foreshortening() -> None:
    rows, errors = sg.validate_scene(SIDE, "fxs")
    assert rows and errors
    for r in rows:
        assert r["evidence"] == "synthetic_fixture" and r["points_source"] == sg.POINTS_SOURCE_FIXTURE
        assert r["frame"] == "image_px"
    summary = {(r["quantity"], r["view_angle_bin_deg"]): r for r in sg.summarize_errors(errors, [0, 30, 60, 90.01])}
    face_on = float(summary[("compound_insertion_angle_deg", "[0,30)")]["median_abs_error"])
    edge_on = float(summary[("compound_insertion_angle_deg", "[60,90.01)")]["median_abs_error"])
    assert face_on < edge_on, "foreshortening grows as the insertion plane turns edge-on"
    assert ("compound_insertion_angle_deg", "class:cl_left") in summary
    assert all(r["direction_class"] in ("cl_left", "cl_right", "cl_toward", "cl_away", "unclear", UNAVAILABLE)
               for r in rows)
    assert summary[("blade_azimuth_quadrant", "all")]["p90_abs_error"].startswith("exact ")
    n_q = summary[("blade_azimuth_quadrant", "all")]["p90_abs_error"].split()[1]
    assert n_q.split("/")[0] == n_q.split("/")[1], "quadrant converter matches truth on clear labels"


def test_human_points_path_and_no_flat_bent_class() -> None:
    pts = [("P0", 100, 200), ("N1", 120, 190), ("N2", 140, 185), ("END", 160, 190), ("STEM_UP", 100, 150)]
    rows = sg.from_human_points([dict(plant_instance_id="dwt_101", capture_id="cap", view_id="side_000",
                                      compound_id="dwt_101/C0001", point=p, u_px=str(u), v_px=str(v),
                                      labeled_by="person") for p, u, v in pts])
    assert len(rows) == 1 and rows[0]["compound_insertion_angle_deg__status"] == "photo_estimate"
    assert rows[0]["blade_azimuth_quadrant"] == UNAVAILABLE
    s.check_table_header(s.SIDE_GEOMETRY_COLUMNS, "side_geometry.csv")
    assert not any("type" in c for c in s.SIDE_GEOMETRY_COLUMNS)
