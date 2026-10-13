"""P1.2 - synthetic truth export vs observation-like view."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import fixture_truth as ft
from tomato3d.state import geometry as g
from tomato3d.state import schema as s
from tomato3d.state.topraster import OrthoCamera

SCENES = Path(__file__).parent / "fixtures" / "p1" / "O-mature" / "scenes"
CAM = OrthoCamera(512, 0.4)


@pytest.fixture(scope="module")
def plant() -> ft.FixturePlant:
    return ft.load_plant(SCENES / "scene_0000", "fxa")


def _ranks(p: ft.FixturePlant) -> dict[str, int]:
    return {p.compound_vertex_id(c): c.gen_rank_from_bottom for c in p.compounds}


def test_truth_mtg_validates_and_ids_are_stable(plant) -> None:
    rows = ft.truth_mtg(plant, "fxa", "c0", _ranks(plant))
    s.check_mtg_rows(rows)
    again = ft.truth_mtg(ft.load_plant(SCENES / "scene_0000", "fxa"), "fxa", "c0", _ranks(plant))
    assert [r["vertex_id"] for r in rows] == [r["vertex_id"] for r in again]
    ids = {r["vertex_id"] for r in rows}
    assert "fxa" in ids and "fxa/A0" in ids and "fxa/C0001/T" in ids and "fxa/C0001/PT1" in ids
    # creation order: oldest generator compound gets C0001
    oldest = max(plant.compounds, key=lambda c: c.age_days)
    assert plant.compound_vertex_id(oldest) == "fxa/C0001"
    # removing a compound never renumbers the others
    smaller = ft.remove_compound(plant, 2)
    assert {smaller.compound_vertex_id(c) for c in smaller.compounds} == {
        plant.compound_vertex_id(c) for c in plant.compounds} - {"fxa/C0002"}


def test_truth_structure_and_a2_quantities(plant) -> None:
    rows = {r["vertex_id"]: r for r in ft.truth_mtg(plant, "fxa", "c0", _ranks(plant))}
    t = rows["fxa/C0001/T"]
    assert t["edge_type"] == "<" and t["parent_id"].startswith("fxa/C0001/R"), "terminal continues the rachis"
    lateral = rows["fxa/C0001/P1L"]
    assert lateral["edge_type"] == "+" and lateral["pair_index"] == "1" and lateral["side"] == "L"
    c = rows["fxa/C0001"]
    n = int(c["n_bend_nodes"])
    alphas = [float(c[f"rachis_bend_alpha_{i}_deg"]) for i in range(1, n + 1)]
    assert abs(sum(alphas) - float(c["rachis_curvature_deg"])) < 1e-3
    assert c["rachis_bend_type"] == UNAVAILABLE, "bend type stays a human label"
    assert c["petiole_base_azimuth_deg__status"] == "derived" and c["blade_azimuth_basis"] == "terminal_tip"
    assert 0.0 <= float(c["compound_insertion_angle_deg"]) <= 180.0
    assert c["length_mm__status"] == "synthetic_truth" and c["evidence"] == "synthetic_fixture"


def test_area_kinds_differ_under_occlusion_and_bending(plant) -> None:
    render = ft.render_capture(plant, 0.0, CAM)
    rows = ft.truth_area_rows(plant, "fxa", "c0", render, CAM)
    s.check_areas(rows, {"c0": "solved"})
    vis = np.array([float(r["visible_projected_area_px2"]) for r in rows])
    amo = np.array([float(r["completed_projected_area_px2"]) for r in rows])
    lam = np.array([float(r["one_sided_lamina_area_mm2"]) for r in rows])
    proj_mm2 = np.array([float(r["completed_projected_area_mm2"]) for r in rows])
    assert np.all(vis <= amo) and np.any(vis < amo), "occlusion: visible < occlusion-completed"
    # rasterised projection stays below the one-sided surface except for the boundary-pixel
    # inflation of cv2.fillPoly (about half a pixel along each outline; declared in the manifest)
    assert np.median(proj_mm2 / lam) < 1.0
    assert np.all(proj_mm2 <= lam * 1.15)
    # a flat horizontal leaflet projects to its surface; bending makes the two kinds differ
    from tomato3d.synth.leaflet_surface import surface_points, triangulate_contour

    contour = np.c_[np.linspace(0, 1, 40), 0.2 * np.sin(np.linspace(0, np.pi, 40))]
    contour = np.vstack([contour, contour[::-1][1:-1] * [1, -1]])
    uv, faces = triangulate_contour(contour, 18)
    flat = dict(length_mm=30.0, width_scale=1.0, roll_deg=0.0, twist_deg=0.0, bend_deg=0.0,
                heading=[1.0, 0.0, 0.0], left=[0.0, 1.0, 0.0], up=[0.0, 0.0, 1.0], base_mm=[0.0, 0.0, 30.0])
    for leaf, (lo, hi) in ((flat, (0.999, 1.001)), (dict(flat, bend_deg=60.0), (0.5, 0.97))):
        v = surface_points(uv, leaf)
        surface = g.triangle_areas(v, faces).sum()
        projected = g.triangle_areas(np.c_[v[:, :2], np.zeros(len(v))], faces).sum()
        assert lo <= projected / surface <= hi


def test_observation_view_drops_what_a_camera_cannot_see(plant) -> None:
    render = ft.render_capture(plant, 0.0, CAM)
    obs = ft.observe_top(render, "fxa", "c0", 150, "synthetic_gt:test")
    s.check_observations(obs.rows, "synthetic_fixture")
    observed_leaflets = {j["truth_vertex_id"] for j in obs.truth_join if j["truth_vertex_id"].count("/") == 2}
    hidden = {lid for lid in render.ids if int(render.visible_mask(lid).sum()) < 150}
    assert hidden and not (hidden & observed_leaflets), "occluded leaflets are not observed"
    assert all(r["provenance"] == "synthetic_gt" and r["frame"] == "image_px" for r in obs.rows)
    terminal = [r for r in obs.rows if r["obs_class"] == "terminal_leaflet"]
    assert terminal and all(r["membership_status"] == "confirmed" and r["parent_obs_id"] != UNAVAILABLE
                            for r in terminal)
    # no geometry, rank or angle leaks into the observation rows
    assert not any(k for k in obs.rows[0] if k.endswith(("_mm", "_deg")) or k == "rank")


def test_existing_perspective_render_can_be_observed(plant) -> None:
    view = SCENES / "scene_0000" / "views" / "00_dwt_t1_20261002_27"
    obs = ft.observe_rendered_view(SCENES / "scene_0000", view, plant, "fxa", "persp", 150)
    assert sum(r["obs_class"] == "compound_leaf" for r in obs.rows) >= 4
    assert all(j["truth_vertex_id"].startswith("fxa/C") for j in obs.truth_join)


def test_added_compound_gets_next_serial_and_provenance(plant) -> None:
    donor = ft.load_plant(SCENES / "scene_0001", "fxb")
    grown = ft.add_compound_from(plant, donor, 1, 90.0)
    assert grown.compounds[-1].serial == len(plant.compounds) + 1
    assert any("added C0007" in m for m in grown.provenance["modifications"])
    assert plant.provenance["modifications"] == [], "the source plant is not mutated"
