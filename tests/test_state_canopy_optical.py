"""P1.7 optical surfaces + P1.8 canopy placement: readiness, conventions, round trip, duplicates."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.io.tables import read_table
from tomato3d.state import canopy as cn
from tomato3d.state import fixture_truth as ft
from tomato3d.state import optical as op
from tomato3d.state import schema as s
from tomato3d.state.topraster import OrthoCamera

ROOT = Path(__file__).resolve().parents[1]
SCENES = Path(__file__).parent / "fixtures" / "p1" / "O-mature" / "scenes"
SLOTS = ROOT / cn.SLOT_TABLE
pytestmark = pytest.mark.skipif(not SLOTS.exists(), reason="slot record table not on disk")


@pytest.fixture(scope="module")
def plant() -> ft.FixturePlant:
    return ft.load_plant(SCENES / "scene_0000", "fxa")


@pytest.fixture(scope="module")
def cfg() -> dict:
    return ft.load_p1_config()


def test_truth_surfaces_are_supported_and_adaxial(plant, tmp_path) -> None:
    rows = op.export_truth(tmp_path, Path("optical_surfaces"), plant, "fxa", "c0")
    s.check_optical_rows(rows)
    assert {r["optical_readiness"] for r in rows} == {"supported"}
    assert {r["face_convention"] for r in rows} == {"adaxial_ccw"}
    tri = read_table(tmp_path / Path(rows[0]["surface_file"]).name, s.OPTICAL_TRIANGLES_COLUMNS)
    assert len(tri) == sum(int(r["n_triangles"]) for r in rows)
    # adaxial_ccw: summed normal of each leaflet agrees with the generator's "up" vector
    leaf = plant.compounds[0].leaflets[0]
    verts, faces = plant.compounds[0].meshes[leaf["tag"]]
    n = np.cross(verts[faces[:, 1]] - verts[faces[:, 0]], verts[faces[:, 2]] - verts[faces[:, 0]]).sum(axis=0)
    assert float(n @ np.asarray(leaf["up"])) > 0


def test_unavailable_and_forbidden_geometry(plant) -> None:
    rows = op.unavailable_rows("dwt_101", "cap", ["dwt_101/C0001/T"], op.Q2_UNAVAILABLE, "real_photo")
    s.check_optical_rows(rows)
    bad = dict(rows[0], optical_readiness="supported", geometry_source="compound_envelope",
               surface_file="x.csv", face_convention="adaxial_ccw")
    with pytest.raises(s.P1SchemaError, match="not certified"):
        s.check_optical_rows([bad])
    with pytest.raises(s.P1SchemaError, match="synthetic truth labelled as real"):
        s.check_optical_rows([dict(bad, geometry_source="synthetic_truth")])


def test_conditional_completion_covers_observed_pixels(plant, tmp_path) -> None:
    cam = OrthoCamera(512, 0.4)
    donor = ft.load_plant(SCENES / "scene_0001", "pool")
    pool = [(f"scene_0001#{c.gen_compound_id}", c) for c in donor.compounds]
    render = ft.render_capture(plant, 0.0, cam)
    obs = ft.observe_top(render, "fxa", "c0", 150, "t")
    mask = obs.masks[next(r["obs_id"] for r in obs.rows if r["obs_class"] == "compound_leaf")]
    kept, report = op.complete_compound(mask, render.visible > 0, 0.0, cam, pool, 0.5, 3, "fxa/C0001")
    assert report["n_generated"] == len(pool) and report["prior_status"] == "user_assumed_unvalidated"
    assert all(c.coverage >= 0.5 for c in kept)
    rows = op.export_candidates(tmp_path, Path("optical_surfaces"), "fxa", "c0", kept)
    s.check_optical_rows(rows)
    assert all(r["optical_readiness"] == "conditional_completion" and r["geometry_source"] == "generated_candidate"
               for r in rows)


def _requests() -> list[cn.InstanceRequest]:
    return [cn.InstanceRequest("fxa", "T2-row1-L", 0.0, "micro_tom", "fixture_declared", "fixture_declared"),
            cn.InstanceRequest("fxa#2", "T2-row1-R", 90.0, "micro_tom", "fixture_declared", "fixture_declared"),
            cn.InstanceRequest("fxo", "T2-row4-L", 0.0, "other", "fixture_declared", "fixture_declared"),
            cn.InstanceRequest("dwt_101", None, None, UNAVAILABLE, UNAVAILABLE, UNAVAILABLE)]


def test_placement_round_trip_duplicates_and_blocks(plant, cfg, tmp_path) -> None:
    slots = cn.load_slots(SLOTS)
    placements = cn.place(_requests(), slots, cfg)
    pmap = {p.plant_instance_id: p for p in placements}
    assert pmap["fxa"].placed and pmap["fxa#2"].placed
    assert not pmap["dwt_101"].placed and "slot_id unavailable" in pmap["dwt_101"].reason
    assert pmap["fxo"].placed and not pmap["fxo"].in_optical_scene
    # slot geometry: same row, L/R one pot pitch apart along X
    pitch = cfg["canopy_assumed"]["pot_pitch_mm"]["value"]
    assert np.isclose(pmap["fxa"].translation_mm[0] - pmap["fxa#2"].translation_mm[0], pitch)
    pts = np.random.default_rng(0).normal(size=(50, 3)) * 30
    for p in (pmap["fxa"], pmap["fxa#2"]):
        assert np.allclose(p.to_plant(p.to_canopy(pts)), pts, atol=1e-9)
    rows = []
    for inst in ("fxa", "fxa#2"):
        rows += read_table(tmp_path / Path(op.export_truth(tmp_path, Path("o"), plant, inst, "c0")[0]["surface_file"]).name,
                           s.OPTICAL_TRIANGLES_COLUMNS)
    merged = cn.merge_triangles(pmap, rows)
    assert {s.split_external_id(r["external_leaflet_id"])[0] for r in merged} == {"fxa", "fxa#2"}
    assert len({r["external_leaflet_id"] for r in merged}) == 2 * len({r["external_leaflet_id"] for r in rows
                                                                        if r["external_leaflet_id"].startswith("fxa|")})
    back = cn.split_triangles(pmap, merged)
    orig = {(r["external_leaflet_id"], r["triangle_id"]): r for r in rows}
    worst = max(abs(float(r[f"v0_{a}_mm"]) - float(orig[(r["external_leaflet_id"], r["triangle_id"])][f"v0_{a}_mm"]))
                for inst in back.values() for r in inst for a in "xyz")
    assert worst < 1e-3
    doc = cn.placement_document(placements, _requests(), cfg, "sha", "synthetic_fixture")
    inst = {i["plant_instance_id"]: i for i in doc["instances"]}
    assert inst["fxa"]["duplicate_of_source"] and inst["fxa"]["sibling_instances"] == ["fxa#2"]
    assert inst["fxa"]["light_ratio_status"] == "app_ratio"
    assert doc["tray_geometry"]["tray_pitch_mm"]["source_kind"] == "assumed_unmeasured"
    assert inst["dwt_101"]["transform"]["matrix_4x4"] == UNAVAILABLE


def test_slot_conflicts_rejected(cfg) -> None:
    slots = cn.load_slots(SLOTS)
    with pytest.raises(cn.CanopyError, match="used by"):
        cn.place([cn.InstanceRequest("a", "T1-row1-L", 0.0, "micro_tom", "x", "x"),
                  cn.InstanceRequest("b", "T1-row1-L", 0.0, "micro_tom", "x", "x")], slots, cfg)
    with pytest.raises(cn.CanopyError, match="variety"):
        cn.place([cn.InstanceRequest("a", "T1-row4-L", 0.0, "micro_tom", "x", "x")], slots, cfg)
    with pytest.raises(cn.CanopyError, match="unknown slot"):
        cn.place([cn.InstanceRequest("a", "T9-row1-L", 0.0, "micro_tom", "x", "x")], slots, cfg)
