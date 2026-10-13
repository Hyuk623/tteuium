"""P1 side shoots (MTG Amendment A4): schema, registry, distinction, tracking, fixture package."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import axes as ax
from tomato3d.state import canopy as cn
from tomato3d.state import fixture_truth as ft
from tomato3d.state import ingest
from tomato3d.state import package as pk
from tomato3d.state import schema as s
from tomato3d.state import update as up
from tomato3d.state.fixture_sequence import Step, compound_observations, run_sequence
from tomato3d.state.topraster import OrthoCamera
from tomato3d.track import link

FIX = Path(__file__).parent / "fixtures" / "p1" / "O-mature"
SCENES = "tests/fixtures/p1/O-mature/scenes"
KST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------- S2 schema

def _axes_row(**over: str) -> dict[str, str]:
    row = {c: UNAVAILABLE for c in s.AXES_COLUMNS}
    row.update(plant_instance_id="p", capture_id="c1", axis_id="S1", axis="S1", axis_vertex_id="p/S1", order="1",
               parent_axis_id="M", stage="axis_shoot", axis_state="axis_shoot", source_kind="user_stated",
               source_ref="reg", registration_ref="side_shoot_registry.csv#line2", evidence="real_photo")
    row.update(over)
    return row


def test_axes_rows_rules() -> None:
    s.check_axes([_axes_row()])
    with pytest.raises(s.P1SchemaError, match="registration record"):
        s.check_axes([_axes_row(registration_ref=UNAVAILABLE)])
    with pytest.raises(s.P1SchemaError, match="order"):
        s.check_axes([_axes_row(order="2")])
    with pytest.raises(s.P1SchemaError, match="disagree"):
        s.check_axes([_axes_row(axis_id="S2")])
    with pytest.raises(s.P1SchemaError, match="prime"):
        s.check_axes([_axes_row(source_ref="shoot′")])
    with pytest.raises(s.P1SchemaError, match="two leaves"):
        s.check_axes([_axes_row(registration_leaf_ids="p/C0007")])
    main = _axes_row(axis_id="M", axis="M", axis_vertex_id="p/A0", order="0", parent_axis_id=UNAVAILABLE,
                     parent_rank="0", parent_rank__status="derived", stage="main", axis_state="main",
                     registration_ref="definition:main_axis")
    s.check_axes([main])
    with pytest.raises(s.P1SchemaError, match="main axis"):
        s.check_axes([dict(main, order="1")])


def _mtg_row(**over: str) -> dict[str, str]:
    row = s.blank_mtg_row()
    row.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c", vertex_id="p/C0001",
               scale="3", frame="plant_local_mm", evidence="synthetic_fixture", axis="S1", **{"class": "CompoundLeaf"})
    row.update(over)
    return row


def test_mtg_axis_rules() -> None:
    row = _mtg_row()
    s.set_value(row, "rank", "1", "user_stated")
    with pytest.raises(s.P1SchemaError, match="unfolded"):
        s.check_mtg_rows([row])
    s.set_value(row, "leaf_unfolded", "true", "user_stated")
    s.check_mtg_rows([row])
    with pytest.raises(s.P1SchemaError, match="not M or S"):
        s.check_mtg_rows([dict(row, axis="S0")])
    with pytest.raises(s.P1SchemaError, match="prime"):
        s.check_mtg_rows([dict(row, display_name="1′")])
    order2 = dict(row)
    s.set_value(order2, "order", "2", "user_stated")
    with pytest.raises(s.P1SchemaError, match="order"):
        s.check_mtg_rows([order2])
    with pytest.raises(s.P1SchemaError, match="registration"):
        s.check_axes_coverage([], [row])


def test_pre_axis_headers_still_validate() -> None:
    row = _mtg_row()
    legacy = {k: v for k, v in row.items() if k in s.MTG_VERTICES_COLUMNS_REV2}
    s.check_mtg_rows([legacy])
    ident = {c: UNAVAILABLE for c in s.IDENTITY_COLUMNS_REV2}
    ident.update(plant_instance_id="p", source_plant_id="p", capture_id="c", organ_id="p/C0001",
                 organ_class="compound_leaf", track_state="first_observed", correspondence_status="proposed")
    s.check_identity_rows([ident])


def test_display_labels_are_never_stored() -> None:
    assert s.display_label(1, 0) == "1" and s.display_label(1, 1) == "1′" and s.display_label(2, 2) == "2″"
    for ch in s.PRIME_CHARACTERS:
        with pytest.raises(s.P1SchemaError):
            s.check_no_primes([{"axis": f"S1{ch}"}], "x.csv")


# ---------------------------------------------------------------- S3 registry

def _registry(tmp_path: Path, rows: list[list[str]]) -> Path:
    path = tmp_path / "side_shoot_registry.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(ax.REGISTRY_COLUMNS)
        w.writerows(rows)
    return path


def test_template_is_a_valid_registry(tmp_path) -> None:
    path = ax.write_template(tmp_path / "tpl")
    entries = ax.read_registry(path)
    assert entries[0].axis == "S1" and entries[0].parent_rank == 2
    assert "EXAMPLE" in path.read_text(encoding="utf-8")


def test_registry_rejects_bad_rows(tmp_path) -> None:
    bad = [
        [["dwt_101", "M", "", "2026-10-12", "axis_shoot", "2026-10-12", ""]],
        [["dwt_101", "S1′", "", "2026-10-12", "axis_shoot", "2026-10-12", ""]],
        [["dwt_101", "S1", "2", "2026-10-12", "shoot", "2026-10-12", ""]],
        [["dwt_101", "S1", "2", "2026-10-12", "substem", "2026-10-13", ""],
         ["dwt_101", "S1", "2", "2026-10-12", "axis_shoot", "2026-10-14", ""]],
        [["dwt_101", "S1", "2", "2026-10-12", "axis_shoot", "2026-10-11", ""]],
        [["dwt_101", "S2", "2", "2026-10-12", "axis_shoot", "2026-10-12", ""]],
        [["dwt_101", "S1", "3", "2026-10-12", "axis_shoot", "2026-10-12", ""],
         ["dwt_101", "S2", "1", "2026-10-12", "axis_shoot", "2026-10-12", ""]],
    ]
    for i, rows in enumerate(bad):
        folder = tmp_path / str(i)
        folder.mkdir()
        path = _registry(folder, rows)
        with pytest.raises((ax.RegistryError, s.P1SchemaError)):
            ax.read_registry(path)


def test_registry_to_axes_rows(tmp_path) -> None:
    path = _registry(tmp_path, [
        ["dwt_101", "S1", "2", "2026-10-09", "substem", "2026-10-10", "seen before capture"],
        ["dwt_101", "S2", "", "2026-10-12", "axis_shoot", "2026-10-12", ""],
        ["dwt_101", "S2", "", "2026-10-12", "substem", "2026-10-13", ""]])
    entries = ax.read_registry(path)
    clock = [ax.CaptureClock(f"c{i}", datetime(2026, 10, 11 + i, 17, tzinfo=KST)) for i in range(3)]
    rows = ax.axes_rows("dwt_101", "dwt_101", clock, entries, {2: "dwt_101/C0002"}, "real_photo", "user_stated")
    s.check_axes(rows)
    by = {(r["capture_id"], r["axis"]): r for r in rows}
    assert {r["axis"] for r in rows if r["capture_id"] == "c0"} == {"M", "S1"}, "S2 is not registered before c1"
    s1 = by[("c0", "S1")]
    assert s1["first_observed_capture_id"] == UNAVAILABLE and s1["emergence_interval_end"] == "c0"
    assert s1["parent_rank"] == "2" and s1["parent_rank__status"] == "user_stated" and s1["parent_node_id"] == "dwt_101/C0002"
    s2 = by[("c1", "S2")]
    assert (s2["first_observed_capture_id"], s2["emergence_interval_start"], s2["emergence_interval_end"]) == ("c1", "c0", "c1")
    assert s2["axis_state"] == "axis_shoot" and by[("c2", "S2")]["axis_state"] == "substem"
    assert by[("c2", "S2")]["axis_state_since_capture_id"] == "c2"
    assert s2["parent_rank"] == UNAVAILABLE, "no parent_rank in the registry -> unavailable, never inferred"
    # A4 proposals confirmed by the user 2026-10-12 (MTG A5 16.1)
    assert s2["numbering_basis"] == s.NUMBERING_BASIS and s2["tie_rule"] == s.TIE_RULE
    assert by[("c0", "M")]["parent_rank"] == "0" and by[("c0", "M")]["axis_state"] == "main"


# ---------------------------------------------------------------- S4 distinction

def test_classification_rules() -> None:
    obs = [dict(plant_instance_id="p", capture_id="c", obs_id=f"o{i}", obs_class=cls, axis_hint=hint,
                axis_hint_source="human" if hint != UNAVAILABLE else UNAVAILABLE)
           for i, (cls, hint) in enumerate([("growth_shoot", "M"), ("growth_shoot", "S1"), ("growth_shoot", "S2"),
                                            ("compound_leaf", "S1"), ("compound_leaf", "S2"), ("compound_leaf", "M"),
                                            ("truss", UNAVAILABLE), ("compound_leaf", UNAVAILABLE),
                                            ("compound_leaf", "S3"), ("sub_stem", UNAVAILABLE)])]
    got = [r["cluster_class"] for r in ax.classify(obs, {"S1": "substem", "S2": "axis_shoot"})]
    assert got == ["shoot", "side_shoot_apex", "axis_shoot", "substem_leaves", "axis_shoot_leaves", "main_leaves",
                   "truss", "leaves_axis_unavailable", "side_leaves_unregistered", "side_stem"]


def test_label_classes_map_to_axes(tmp_path) -> None:
    coco = dict(categories=[dict(id=1, name="main_stem"), dict(id=2, name="sub_stem"), dict(id=3, name="compound_leaf"),
                            dict(id=4, name="growth_shoot")],
                images=[dict(id=1, file_name="a.jpg", width=20, height=20)],
                annotations=[dict(id=1, image_id=1, category_id=1, bbox=[0, 0, 2, 2], segmentation=[]),
                             dict(id=2, image_id=1, category_id=2, bbox=[0, 0, 2, 2], segmentation=[]),
                             dict(id=3, image_id=1, category_id=3, bbox=[0, 0, 2, 2], segmentation=[],
                                  attributes={"axis": "S1"}),
                             dict(id=4, image_id=1, category_id=4, bbox=[0, 0, 2, 2], segmentation=[])])
    path = tmp_path / "c.json"
    path.write_text(json.dumps(coco), encoding="utf-8")
    rows, _, _ = ingest.import_coco(path, {"a.jpg": "cap"}, "p")
    s.check_observations(rows, "real_photo")
    assert [(r["obs_class"], r["axis_hint"]) for r in rows] == [
        ("main_stem", "M"), ("sub_stem", UNAVAILABLE), ("compound_leaf", "S1"), ("growth_shoot", UNAVAILABLE)]
    det = [dict(key="a.jpg", rgb_sha256="x", detector_args=dict(weights="w", weights_sha256="0" * 64, imgsz=512, conf=.25),
                detections=[dict(cls="main_stem", box=[0, 0, 1, 1], conf=.9)])]
    prop = ingest.proposal_rows(det, {"a.jpg": "cap"}, {"a.jpg": "p"})
    assert prop[0]["axis_hint"] == "M" and prop[0]["axis_hint_source"] == "detector_class"


# ---------------------------------------------------------------- S5 tracking + S6 fixture

SIDE = dict(axis="S1", parent_serial=2, leaf_lengths_mm=[30.0, 26.0, 18.0], seed=11, stem_length_mm=14.0,
            stem_elevation_deg=50.0)


@pytest.fixture(scope="module")
def generator():
    gen_cfg, contours = pk._generator_inputs(FIX / "scenes" / "scene_0000")
    return ft.load_plant(FIX / "scenes" / "scene_0000", "fxs"), gen_cfg, contours


def _track(plant, gen_cfg, contours, steps):
    states = run_sequence(plant, steps, OrthoCamera(512, 0.4), 150, "fxs", gen_cfg, contours)
    result = link.track_plant("fxs", "fxs", [st.frame for st in states],
                              {st.step.capture_id: compound_observations(st) for st in states},
                              link.load_config(link.FIXTURE_CONFIG))
    s.check_identity_rows(result.identity_rows)
    return states, result


def test_side_shoot_truth_ranks_and_axis_vertices(generator) -> None:
    plant, gen_cfg, contours = generator
    grown = ft.set_side_shoot(plant, **{k: v for k, v in SIDE.items() if k != "axis"}, axis="S1",
                              gen_cfg=gen_cfg, contours=contours)
    assert [c.axis for c in grown.compounds].count("S1") == 3
    states = run_sequence(plant, [Step("c0", 0, "am", side_shoots=[SIDE])], OrthoCamera(512, 0.4), 150, "fxs",
                          gen_cfg, contours)
    ranks = pk._truth_ranks_per_axis(states)["c0"]
    rows = ft.truth_mtg(states[0].plant, "fxs", "c0", ranks)
    s.check_mtg_rows(rows)
    axis_rows = {r["axis"]: r for r in rows if r["class"] == "Axis"}
    assert set(axis_rows) == {"M", "S1"} and axis_rows["S1"]["order"] == "1"
    assert axis_rows["S1"]["parent_rank"] == str(ranks["fxs/C0002"])
    side = sorted((r for r in rows if r["class"] == "CompoundLeaf" and r["axis"] == "S1"), key=lambda r: int(r["rank"]))
    assert [r["rank"] for r in side] == ["1", "2", "3"] and all(r["complex_id"] == "fxs/S1" for r in side)
    assert all(r["axis"] == "S1" for r in rows if r["vertex_id"].startswith(side[0]["vertex_id"] + "/"))


def test_cross_axis_links_are_forbidden_and_new_side_leaves_get_new_ids(generator) -> None:
    plant, gen_cfg, contours = generator
    s2_young = dict(axis="S2", parent_serial=6, leaf_lengths_mm=[14.0, 13.0], seed=12, stem_length_mm=4.0,
                    stem_elevation_deg=50.0)
    states, result = _track(plant, gen_cfg, contours, [
        Step("c0", 0, "am", side_shoots=[SIDE]),
        Step("c1", 24, "am", yaw_deg=30, side_shoots=[SIDE, s2_young]),
        Step("c2", 48, "am", yaw_deg=-15, side_shoots=[SIDE, dict(s2_young, leaf_lengths_mm=[24.0, 21.0])],
             occlude=[7])])
    axis_of: dict[str, set[str]] = {}
    for r in result.identity_rows:
        if r["organ_class"] == "compound_leaf" and r["organ_id"] != s.UNASSIGNED_ORGAN:
            axis_of.setdefault(r["organ_id"], set()).add(r["axis"])
    assert all(len(v) == 1 for v in axis_of.values()), "a compound belongs to one axis for life"
    forbidden = [m for m in result.match_rows if m["cost"] == "forbidden_cross_axis"]
    assert forbidden
    new_s2 = [r for r in result.identity_rows if r["capture_id"] == "c1" and r["axis"] == "S2"
              and r["track_state"] == "first_observed"]
    assert len(new_s2) >= 1
    occluded = next(r for r in result.identity_rows if r["capture_id"] == "c2" and r["organ_id"] == "fxs/C0007")
    assert occluded["track_state"] == "unobserved" and occluded["unobserved_reason"] == "unknown", "absence != removal"
    from tomato3d.state.fixture_sequence import identity_score

    assert identity_score(states, result.obs_to_track)["wrong_links"] == 0


def test_unknown_axis_is_assigned_once() -> None:
    import numpy as np

    mask = np.zeros((64, 64), bool)
    mask[30:34, 34:50] = True
    frames = [link.CaptureFrame(c, float(i * 24), "am", (32.0, 32.0), 0.0) for i, c in enumerate(("c0", "c1", "c2"))]
    obs = {"c0": [link.CompoundObs("o1", mask)], "c1": [link.CompoundObs("o1", mask, None, "S1")],
           "c2": [link.CompoundObs("o1", mask, None, "M")]}
    result = link.track_plant("p", "p", frames, obs, link.load_config(link.FIXTURE_CONFIG))
    rows = [(r["capture_id"], r["organ_id"], r["axis"], r["track_state"]) for r in result.identity_rows]
    assert ("c0", "p/C0001", UNAVAILABLE, "first_observed") in rows
    assert ("c1", "p/C0001", "S1", "continued") in rows
    assert [e["event_type"] for e in result.events] == ["axis_assigned"]
    # c2: the same mask labelled M cannot join the S1 track -> the track is unobserved, the M leaf is a new id
    assert ("c2", "p/C0001", "S1", "unobserved") in rows
    assert ("c2", "p/C0002", "M", "first_observed") in rows


def test_sideshoot_package_validates(tmp_path) -> None:
    if not (pk.PROJECT_ROOT / cn.SLOT_TABLE).exists():
        pytest.skip("slot table absent")
    s2 = dict(axis="S2", parent_serial=6, leaf_lengths_mm=[14.0, 13.0], seed=12, stem_length_mm=4.0,
              stem_elevation_deg=50.0)
    request = dict(
        mode="fixture", source_plants=[dict(source_plant_id="fxs", scene_dir=f"{SCENES}/scene_0000")],
        donor_scene=f"{SCENES}/scene_0001", completion_pool_scenes=[f"{SCENES}/scene_0001"],
        sequences={"fxs": [dict(capture_id="c0", time_h=0, phase="am", side_shoots=[SIDE]),
                           dict(capture_id="c1", time_h=24, phase="am", side_shoots=[SIDE, s2])]},
        side_shoot_registry={"fxs": [
            dict(axis="S1", parent_serial=2, first_observed="2026-10-09", states=[["substem", "2026-10-10"]], note="t"),
            dict(axis="S2", parent_serial=6, first_observed="2026-10-12", states=[["axis_shoot", "2026-10-12"]],
                 note="t")]},
        instances=[dict(plant_instance_id="fxs", slot_id="T3-row1-L", yaw_deg=0.0, variety="micro_tom")],
        decisions=None)
    out = pk.build_fixture(tmp_path / "pkg", request)
    assert pk.validate(out) == []
    axes_rows = list(csv.DictReader((out / "axes.csv").open(encoding="utf-8")))
    s2_row = next(r for r in axes_rows if r["capture_id"] == "c1" and r["axis"] == "S2")
    assert s2_row["first_observed_capture_id"] == "c1" and s2_row["emergence_interval_start"] == "c0"
    assert (out / "axis_classification.csv").exists()
    text = "".join(p.read_text(encoding="utf-8") for p in out.rglob("*.csv"))
    assert not any(ch in text for ch in s.PRIME_CHARACTERS), "no prime character in any package table"
    assert pk.p2_dry_read(out)["ok"]
