"""P1.4 - compound tracking on generator fixtures with controlled changes (software checks only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tomato3d.state import fixture_truth as ft
from tomato3d.state import schema as s
from tomato3d.state.fixture_sequence import Step, compound_observations, identity_score, run_sequence
from tomato3d.state.topraster import OrthoCamera
from tomato3d.track import link

FIX = Path(__file__).parent / "fixtures" / "p1" / "O-mature" / "scenes"
CAM = OrthoCamera(512, 0.4)
MIN_PX = 150


@pytest.fixture(scope="module")
def plants() -> tuple[ft.FixturePlant, ft.FixturePlant]:
    return ft.load_plant(FIX / "scene_0000", "fxa"), ft.load_plant(FIX / "scene_0001", "fxb")


def _run(plant: ft.FixturePlant, steps: list[Step], cfg_path: Path = link.FIXTURE_CONFIG,
         decisions: list[link.Decision] | None = None):
    states = run_sequence(plant, steps, CAM, MIN_PX, plant.source_plant_id)
    obs = {st.step.capture_id: compound_observations(st) for st in states}
    result = link.track_plant(plant.source_plant_id, plant.source_plant_id, [st.frame for st in states], obs,
                              link.load_config(cfg_path), decisions or [])
    s.check_identity_rows(result.identity_rows)
    return states, result


def _rows(result: link.TrackResult, capture: str, organ_class: str = "compound_leaf") -> list[dict[str, str]]:
    return [r for r in result.identity_rows if r["capture_id"] == capture and r["organ_class"] == organ_class]


def test_ids_preserved_under_known_pot_rotation(plants) -> None:
    states, result = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", yaw_deg=40),
                                      Step("c2", 24, "am", yaw_deg=-75)])
    score = identity_score(states, result.obs_to_track)
    assert score["wrong_links"] == 0 and score["fragmented_truth_compounds"] == 0
    assert {r["track_state"] for r in _rows(result, "c1") + _rows(result, "c2")} == {"continued"}
    assert all(r["correspondence_status"] == "proposed" for r in result.identity_rows)


def test_ids_are_never_renumbered_across_reruns(plants) -> None:
    steps = [Step("c0", 0, "am"), Step("c1", 12, "pm", yaw_deg=40)]
    _, a = _run(plants[0], steps)
    _, b = _run(plants[0], steps)
    assert a.identity_rows == b.identity_rows
    ids = [r["organ_id"] for r in _rows(a, "c0")]
    assert ids == [s.compound_id("fxa", k) for k in range(1, len(ids) + 1)]


def test_absence_is_not_removal_and_new_compound_gets_new_id(plants) -> None:
    a, b = plants
    states, result = _run(a, [Step("c0", 0, "am"),
                              Step("c1", 12, "pm", yaw_deg=20, remove=[1], add=[(b, 3, 120.0)]),
                              Step("c2", 24, "am", yaw_deg=10, occlude=[2]),
                              Step("c3", 36, "pm")])
    score = identity_score(states, result.obs_to_track)
    assert score["wrong_links"] == 0
    states_by = {(r["capture_id"], r["organ_id"]): r for r in result.identity_rows}
    removed = states_by[("c1", "fxa/C0001")]
    assert removed["track_state"] == "unobserved" and removed["unobserved_reason"] == "unknown"
    assert all(r["track_state"] != "removal_confirmed" for r in result.identity_rows)
    new = [r for r in _rows(result, "c1") if r["track_state"] == "first_observed"]
    assert len(new) == 1 and new[0]["organ_id"] == "fxa/C0007"
    assert new[0]["emergence_interval_start"] == "c0" and new[0]["emergence_interval_end"] == "c1"
    assert states_by[("c2", "fxa/C0002")]["track_state"] == "unobserved"
    assert states_by[("c3", "fxa/C0002")]["track_state"] == "reappeared"
    assert states_by[("c3", "fxa/C0002")]["gap_captures"] == "1"


def test_removal_only_from_a_decision(plants) -> None:
    decision = link.Decision("removal_confirmed", "c1", "fxa/C0001", None, "data/records/manual_events.csv#row7")
    _, result = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", remove=[1])], decisions=[decision])
    row = next(r for r in _rows(result, "c1") if r["organ_id"] == "fxa/C0001")
    assert row["track_state"] == "removal_confirmed" and row["events"].startswith("fxa/E")
    assert result.events[0]["decision_ref"].startswith("data/records")


def test_human_confirmation_and_occlusion_decisions(plants) -> None:
    steps = [Step("c0", 0, "am"), Step("c1", 12, "pm", occlude=[2])]
    _, before = _run(plants[0], steps)
    obs_c3 = next(r for r in _rows(before, "c1") if r["organ_id"] == "fxa/C0003")["obs_id"]
    decisions = [link.Decision("same", "c1", "fxa/C0003", obs_c3, "review.json#1"),
                 link.Decision("occluded", "c1", "fxa/C0002", None, "review.json#2")]
    _, result = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", occlude=[2])], decisions=decisions)
    by = {r["organ_id"]: r for r in _rows(result, "c1")}
    assert by["fxa/C0003"]["correspondence_status"] == "confirmed"
    assert by["fxa/C0002"]["unobserved_reason"] == "occluded"
    assert by["fxa/C0004"]["correspondence_status"] == "proposed"


def test_merge_and_split_are_flagged_not_resolved(plants) -> None:
    _, merged = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", merge=[[2, 5]])])
    assert [e["event_type"] for e in merged.events] == ["merge_suspect"]
    assert {r["track_state"] for r in _rows(merged, "c1") if r["organ_id"] in ("fxa/C0002", "fxa/C0005")} == {
        "ambiguous"}
    _, split = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", split=[3])])
    assert [e["event_type"] for e in split.events] == ["fragment_suspect"]
    assert not [r for r in _rows(split, "c1") if r["track_state"] == "first_observed"], "no new id for a fragment"


def test_unknown_rotation_disables_azimuth_and_never_forces(plants) -> None:
    states, result = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", yaw_deg=60, rotation_known=False)])
    assert all(m["d_azimuth_deg"] == "unavailable" and m["mask_iou_prev"] == "unavailable"
               for m in result.match_rows)
    assert identity_score(states, result.obs_to_track)["wrong_links"] == 0


def test_null_template_routes_everything_to_review(plants) -> None:
    _, result = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", yaw_deg=40),
                                 Step("c2", 24, "am", add=[(plants[1], 2, 200.0)])], cfg_path=link.TEMPLATE_CONFIG)
    later = [r for r in result.identity_rows if r["capture_id"] != "c0" and r["organ_class"] == "compound_leaf"]
    observed = [r for r in later if r["track_state"] != "unobserved"]
    assert observed and {r["track_state"] for r in observed} == {"ambiguous"}
    assert any(r["organ_id"] == s.UNASSIGNED_ORGAN for r in later), "a new compound gets no id without a threshold"
    assert result.config_status["no_match_cost"].startswith("null")


def test_terminal_leaflet_carried_by_explicit_membership(plants) -> None:
    _, result = _run(plants[0], [Step("c0", 0, "am"), Step("c1", 12, "pm", yaw_deg=40)])
    terminals = _rows(result, "c1", "terminal_leaflet")
    assert terminals and all(r["organ_id"] == f"{r['parent_id']}/T" for r in terminals)


def test_out_of_order_captures_rejected(plants) -> None:
    with pytest.raises(link.TrackingError):
        _run(plants[0], [Step("c0", 12, "am"), Step("c1", 0, "pm")])


def test_stub_entry_point_still_raises() -> None:
    with pytest.raises(NotImplementedError):
        link.link_organs("dwt_101")


def test_prompt_vocabulary_maps_to_contract() -> None:
    assert s.PROMPT_TRACK_WORDS["removed_confirmed"] == "state=removal_confirmed"
    assert "fragment_suspect" in s.PROMPT_TRACK_WORDS["split"]
