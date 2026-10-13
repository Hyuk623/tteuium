"""P1.5 - structure update: rank anchoring, no promotion, top-view limits, candidates, diurnal guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import fixture_truth as ft
from tomato3d.state import schema as s
from tomato3d.state import update as up
from tomato3d.state.fixture_sequence import Step, compound_observations, run_sequence
from tomato3d.state.topraster import OrthoCamera
from tomato3d.track import link

SCENES = Path(__file__).parent / "fixtures" / "p1" / "O-mature" / "scenes"
CAM = OrthoCamera(512, 0.4)


def test_rank_anchoring_rule_a11() -> None:
    first = up.anchor_ranks({"a": 10.0, "b": 30.0, "c": 20.0}, None)
    assert first.ranks == {"a": 1, "c": 2, "b": 3}
    # lost leaf keeps its rank; new leaf above takes max + 1; nothing renumbered
    later = up.anchor_ranks({"c": 21.0, "b": 31.0, "d": 45.0}, first.ranks)
    assert later.ranks == {"a": 1, "c": 2, "b": 3, "d": 4}
    # a hidden lower leaf discovered later gets 0, then -1
    lower = up.anchor_ranks({"c": 21.0, "e": 5.0, "f": 2.0}, later.ranks)
    assert lower.ranks["e"] == 0 and lower.ranks["f"] == -1 and lower.ranks["a"] == 1
    # a new leaf between ranked ones has no case in A1.1 -> unavailable with reason, no renumbering
    between = up.anchor_ranks({"a": 10.0, "c": 20.0, "g": 15.0}, first.ranks)
    assert "g" not in between.ranks and "renumbering" in between.unresolved["g"]


@pytest.fixture(scope="module")
def sequence():
    plant = ft.load_plant(SCENES / "scene_0000", "fxa")
    states = run_sequence(plant, [Step("c0", 0, "am"), Step("c1", 12, "pm", yaw_deg=30),
                                  Step("c2", 24, "am", yaw_deg=10, occlude=[2])], CAM, 150, "fxa")
    result = link.track_plant("fxa", "fxa", [st.frame for st in states],
                              {st.step.capture_id: compound_observations(st) for st in states},
                              link.load_config(link.FIXTURE_CONFIG))
    return states, result


def _info(st, phase: str, lights: float | None, rotation: bool = True) -> up.CaptureInfo:
    return up.CaptureInfo(st.step.capture_id, "plant_local_mm" if rotation else "image_px", CAM.mm_per_px,
                          (CAM.center_px, CAM.center_px), st.step.yaw_deg if rotation else None, phase, lights,
                          "synthetic_fixture", "synthetic_ortho_camera_declared")


def _snap(st, result, **kw) -> tuple[up.SnapshotInputs, list[dict[str, str]]]:
    inp = up.SnapshotInputs("fxa", "fxa", _info(st, st.step.phase, 60.0), st.obs.rows, st.obs.masks,
                            result.identity_rows, **kw)
    snap = up.build_snapshot(inp)
    s.check_mtg_rows(snap)
    return inp, snap


def test_top_view_snapshot_leaves_3d_and_angles_unavailable(sequence) -> None:
    states, result = sequence
    _, snap = _snap(states[0], result)
    comps = [r for r in snap if r["class"] == "CompoundLeaf"]
    assert comps
    for r in comps:
        for attr in ("base_xyz_mm", "elevation_deg", "compound_insertion_angle_deg", "rank", "length_mm",
                     "rachis_bend_alpha_1_deg", "rachis_bend_theta_deg", "petiole_base_azimuth_deg"):
            assert r[attr] == UNAVAILABLE, attr
        assert r["blade_azimuth_deg__status"] == "reconstructed"
        assert r["blade_azimuth_basis"] == up.TOP_BLADE_BASIS
    unres = up.unresolved_rows(snap, "x")
    cells = sum(1 for v in snap for a in s.MTG_VALUE_ATTRIBUTES if v[a] == UNAVAILABLE)
    assert len(unres) == cells and all(r["reason"] for r in unres)


def test_no_promotion_and_absent_vertex_kept_unobserved(sequence) -> None:
    states, result = sequence
    _, s0 = _snap(states[0], result)
    _, s2 = _snap(states[2], result)
    occluded = next(r for r in s2 if r["vertex_id"] == "fxa/C0002")
    assert occluded["observed"] == "false" and occluded["blade_azimuth_deg"] == UNAVAILABLE, \
        "a hidden compound keeps its vertex but no value is carried from c0"
    log = up.change_log(s0, s2)
    rule = {(r["vertex_id"], r["attr"]): r["rule_applied"] for r in log}
    assert rule[("fxa/C0002", "blade_azimuth_deg")] == "not_observed_this_capture_no_carry"


def test_human_records_and_side_values_enter_with_their_status(sequence) -> None:
    states, result = sequence
    with pytest.raises(s.P1SchemaError, match="unfolded"):
        _snap(states[0], result, human_records={"fxa/C0001": {"rank": "1"}})
    _, snap = _snap(states[0], result,
                    human_records={"fxa/C0001": {"rank": "1", "leaf_unfolded": "true", "rachis_bend_type": "flat"}},
                    side_values={"fxa/C0001": {"compound_insertion_angle_deg": ("41.5", "photo_estimate")}})
    row = next(r for r in snap if r["vertex_id"] == "fxa/C0001")
    assert row["rank__status"] == "user_stated" and row["rachis_bend_type__status"] == "user_stated"
    assert row["compound_insertion_angle_deg__status"] == "photo_estimate"


def test_unknown_rotation_writes_image_px_and_no_azimuth(sequence) -> None:
    states, result = sequence
    inp = up.SnapshotInputs("fxa", "fxa", _info(states[1], "pm", 540.0, rotation=False), states[1].obs.rows,
                            states[1].obs.masks, result.identity_rows)
    snap = up.build_snapshot(inp)
    s.check_mtg_rows(snap)
    assert all(r["frame"] == "image_px" and r["blade_azimuth_deg"] == UNAVAILABLE for r in snap)


def test_areas_mm_only_with_scale_and_full_outline(sequence) -> None:
    states, result = sequence
    inp, _ = _snap(states[0], result)
    rows = up.area_rows(inp, result.obs_to_track)
    s.check_areas(rows, {"c0": "solved"})
    assert all(r["area_basis"] == "full_outline" and r["one_sided_lamina_area_mm2"] == UNAVAILABLE for r in rows)
    no_scale = up.SnapshotInputs("fxa", "fxa", up.CaptureInfo("c0", "image_px", None, None, None, "am", None,
                                                              "synthetic_fixture", UNAVAILABLE),
                                 states[0].obs.rows, states[0].obs.masks, result.identity_rows)
    assert all(r["visible_projected_area_mm2"] == UNAVAILABLE for r in up.area_rows(no_scale, result.obs_to_track))


def test_diurnal_guard(sequence) -> None:
    states, result = sequence
    infos = [_info(st, st.step.phase, 60.0 if st.step.phase == "am" else 540.0) for st in states]
    areas = [up.area_rows(up.SnapshotInputs("fxa", "fxa", i, st.obs.rows, st.obs.masks, result.identity_rows),
                          result.obs_to_track) for i, st in zip(infos, states)]
    am_pm = up.comparisons("fxa", infos[0], infos[1], areas[0], areas[1])
    assert am_pm and {r["comparison_status"] for r in am_pm} == {"unavailable_diurnal_confound"}
    assert all(r["delta"] == UNAVAILABLE for r in am_pm)
    am_am = up.comparisons("fxa", infos[0], infos[2], areas[0], areas[2])
    assert am_am and {r["comparison_status"] for r in am_am} == {"compared_same_phase"}
    no_clock = up.CaptureInfo("c2", "plant_local_mm", 0.4, None, None, "am", None, "synthetic_fixture", "x")
    assert {r["comparison_status"] for r in up.comparisons("fxa", infos[0], no_clock, areas[0], areas[2])} == {
        "unavailable_diurnal_confound"}


def test_candidate_sub_mtg_is_segregated() -> None:
    rows = up.candidate_rows("fxa", "fxa", "c0", "fxa/C0003", "fxa/C0003#cand001", "plant_local_mm",
                             "synthetic_fixture", [dict(tag="T", area_mm2=50.0, base_mm=[1.0, 2.0, 3.0])])
    s.check_candidate_rows(rows, "candidates.csv")
    with pytest.raises(s.P1SchemaError, match="separate sub-MTG"):
        s.check_mtg_rows(rows)
