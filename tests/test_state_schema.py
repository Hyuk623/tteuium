"""P1.1 - the P1 package schema rejects every contract violation it is responsible for."""

from __future__ import annotations

import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import schema as s


def _capture(**over: str) -> dict[str, str]:
    row = {c: UNAVAILABLE for c in s.CAPTURES_COLUMNS}
    row.update(
        capture_id="cap1",
        plant_instance_id="dwt_101",
        source_plant_id="dwt_101",
        evidence="real_photo",
        view="top",
        frame="image_px",
        photoperiod_phase=UNAVAILABLE,
        scale_status=UNAVAILABLE,
        image_path="data/raw/x.heic",
        image_sha256="ab" * 32,
        session_id="s",
        note="",
    )
    row.update(over)
    return row


def _area(**over: str) -> dict[str, str]:
    row = {c: UNAVAILABLE for c in s.AREAS_COLUMNS}
    row.update(
        plant_instance_id="p",
        capture_id="cap1",
        compound_id="p/C0001",
        leaflet_id="p/C0001/T",
        evidence="synthetic_fixture",
        area_basis="full_outline",
        visible_projected_area_px2="120",
        visible_projected_area_px2__status="observed",
    )
    row.update(over)
    return row


def test_vocabularies_are_closed_and_fixture_extension_is_named() -> None:
    assert "synthetic_truth" in s.VALUE_STATUSES
    assert s.FIXTURE_ONLY_STATUSES == {"synthetic_truth"}
    assert set(s.FRAME_TOKENS) == {"board_mm", "plant_local_mm", "image_px", "canopy_mm"}
    assert "image_px" not in s.MM_FRAMES
    assert set(s.TRACK_STATES) == {
        "continued", "unobserved", "reappeared", "first_observed", "removal_confirmed", "ambiguous"
    }
    for word in ("new", "occluded", "disappeared_unconfirmed", "removed_confirmed", "split", "merge"):
        assert word in s.PROMPT_TRACK_WORDS


def test_mm_without_scale_rejected() -> None:
    rows = [_area(visible_projected_area_mm2="5.0", visible_projected_area_mm2__status="observed")]
    with pytest.raises(s.P1SchemaError, match="without a scale"):
        s.check_areas(rows, {"cap1": UNAVAILABLE})
    rows[0]["scale_source"] = "pot_rim_inner_diameter_mm"
    s.check_areas(rows, {"cap1": "solved"})


def test_capture_scale_consistency() -> None:
    s.check_captures([_capture()])
    with pytest.raises(s.P1SchemaError, match="mm_per_px"):
        s.check_captures([_capture(mm_per_px="0.1")])
    with pytest.raises(s.P1SchemaError, match="scale_source"):
        s.check_captures([_capture(scale_status="solved", mm_per_px="0.1")])
    with pytest.raises(s.P1SchemaError, match="sha256"):
        s.check_captures([_capture(image_sha256=UNAVAILABLE)])


def test_cross_frame_mixing_rejected() -> None:
    row = s.blank_mtg_row()
    row.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c",
               vertex_id="p/C0001", scale="3", **{"class": "CompoundLeaf"}, frame="image_px",
               evidence="synthetic_fixture")
    s.set_value(row, "length_mm", "12.5", "observed")
    with pytest.raises(s.P1SchemaError, match="millimetre value in frame 'image_px'"):
        s.check_mtg_rows([row])
    row["frame"] = "plant_local_mm"
    s.check_mtg_rows([row])
    row["frame"] = "pixels"
    with pytest.raises(s.P1SchemaError, match="frame"):
        s.check_mtg_rows([row])


def test_top_view_cannot_carry_insertion_angle() -> None:
    row = s.blank_mtg_row()
    row.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c",
               vertex_id="p/C0001", scale="3", **{"class": "CompoundLeaf"}, frame="image_px",
               evidence="real_photo")
    s.set_value(row, "compound_insertion_angle_deg", "40", "reconstructed")
    with pytest.raises(s.P1SchemaError, match="top view alone"):
        s.check_mtg_rows([row])


def test_unprefixed_insertion_angle_rejected() -> None:
    with pytest.raises(s.P1SchemaError, match="MTG 12.2"):
        s.check_table_header(["vertex_id", "insertion_angle_deg"], "x.csv")
    s.check_table_header(["compound_insertion_angle_deg", "leaflet_insertion_angle_deg"], "x.csv")


def test_green_only_never_in_main_area_column() -> None:
    with pytest.raises(s.P1SchemaError, match="full_outline"):
        s.check_areas([_area(area_basis="green_only")], {})
    with pytest.raises(s.P1SchemaError, match="area_green_only_"):
        s.check_table_header(["area_mm2_green"], "x.csv")
    s.check_table_header(["area_green_only_mm2"], "x.csv")


def test_on_hold_fields_rejected() -> None:
    for bad in ("blade_curl_deg", "leaflet_rugosity", "theta_threshold_deg", "flat_bent_class"):
        with pytest.raises(s.P1SchemaError, match="on-hold"):
            s.check_table_header(["vertex_id", bad], "x.csv")


def test_rachis_bend_type_is_human_label_only() -> None:
    row = s.blank_mtg_row()
    row.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c",
               vertex_id="p/C0001", scale="3", **{"class": "CompoundLeaf"}, frame="plant_local_mm",
               evidence="synthetic_fixture")
    s.set_value(row, "rachis_bend_type", "bent", "derived")
    with pytest.raises(s.P1SchemaError, match="human label"):
        s.check_mtg_rows([row])
    s.set_value(row, "rachis_bend_type", "bent", "user_stated")
    s.check_mtg_rows([row])


def test_synthetic_truth_cannot_appear_on_real_rows() -> None:
    row = s.blank_mtg_row()
    row.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c",
               vertex_id="p/C0001", scale="3", **{"class": "CompoundLeaf"}, frame="plant_local_mm",
               evidence="real_photo")
    s.set_value(row, "length_mm", "30", "synthetic_truth")
    with pytest.raises(s.P1SchemaError, match="never pass as photo"):
        s.check_mtg_rows([row])


def test_unavailable_value_and_status_go_together() -> None:
    row = s.blank_mtg_row()
    row.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c",
               vertex_id="p/C0001", scale="3", **{"class": "CompoundLeaf"}, frame="plant_local_mm",
               evidence="synthetic_fixture")
    row["length_mm"] = "0"
    with pytest.raises(s.P1SchemaError, match="go together"):
        s.check_mtg_rows([row])
    with pytest.raises(s.P1SchemaError):
        s.set_value(row, "length_mm", "3", UNAVAILABLE)


def test_candidates_never_in_main_snapshot() -> None:
    row = s.blank_mtg_row()
    row.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c",
               vertex_id="p/C0001", scale="3", **{"class": "CompoundLeaf"}, frame="plant_local_mm",
               evidence="synthetic_fixture", candidate_id="cand1")
    with pytest.raises(s.P1SchemaError, match="separate sub-MTG"):
        s.check_mtg_rows([row])
    s.set_value(row, "length_mm", "3", "observed")
    with pytest.raises(s.P1SchemaError, match="candidate sub-MTG"):
        s.check_candidate_rows([row], "candidates.csv")


def test_removal_needs_evidence_and_detector_proposals_need_review() -> None:
    row = {c: UNAVAILABLE for c in s.IDENTITY_COLUMNS}
    row.update(plant_instance_id="p", source_plant_id="p", capture_id="c", organ_id="p/C0001",
               organ_class="compound_leaf", track_state="removal_confirmed",
               correspondence_status="proposed", events="")
    with pytest.raises(s.P1SchemaError, match="never removal"):
        s.check_identity_rows([row])
    obs = {c: UNAVAILABLE for c in s.OBSERVATIONS_COLUMNS}
    obs.update(plant_instance_id="p", capture_id="c", obs_id="o1", obs_class="compound_leaf",
               provenance="detector_proposal", detector_status="unvalidated_on_boardfree_top",
               review_state="accepted", frame="image_px", evidence="real_photo",
               plant_attribution="this_plant", membership_status=UNAVAILABLE)
    with pytest.raises(s.P1SchemaError, match="never accepted"):
        s.check_observations([obs], "real_photo")


def test_optical_readiness_rules() -> None:
    row = {c: UNAVAILABLE for c in s.OPTICAL_MANIFEST_COLUMNS}
    row.update(plant_instance_id="p", source_plant_id="p", capture_id="c",
               external_leaflet_id="p|p/C0001/T", vertex_id="p/C0001/T", compound_id="p/C0001",
               frame="plant_local_mm", surface_file="optical_surfaces/x.csv", geometry_source="bbox",
               optical_readiness="supported", readiness_reason="x", evidence="synthetic_fixture")
    with pytest.raises(s.P1SchemaError, match="not certified"):
        s.check_optical_rows([row])
    row["geometry_source"] = "generated_candidate"
    with pytest.raises(s.P1SchemaError, match="conditional_completion"):
        s.check_optical_rows([row])
    row["optical_readiness"] = "conditional_completion"
    s.check_optical_rows([row])
    row.update(optical_readiness="unavailable", readiness_reason="")
    with pytest.raises(s.P1SchemaError, match="reason"):
        s.check_optical_rows([row])


def test_ids_and_external_ids_round_trip() -> None:
    assert s.instance_id("dwt_101", 1) == "dwt_101"
    assert s.instance_id("dwt_101", 2) == "dwt_101#2"
    assert s.source_of_instance("dwt_101#2") == "dwt_101"
    ext = s.external_leaflet_id("dwt_101#2", "dwt_101/C0003/P1L")
    assert s.split_external_id(ext) == ("dwt_101#2", "dwt_101/C0003/P1L")
    assert s.compound_id("dwt_101", 3) == "dwt_101/C0003"
    with pytest.raises(s.P1SchemaError):
        s.instance_id("a/b", 1)
    with pytest.raises(s.P1SchemaError):
        s.check_identifier("a,b", "id")


def test_segment_status_requires_reason() -> None:
    with pytest.raises(s.P1SchemaError):
        s.SegmentStatus("ingest", "unavailable", "")
    with pytest.raises(s.P1SchemaError):
        s.SegmentStatus("ingest", "done", "x")
    assert s.SegmentStatus("ingest", "executed", "").as_dict()["run_status"] == "executed"


def test_fmt_never_writes_zero_for_missing() -> None:
    assert s.fmt(None) == UNAVAILABLE
    assert s.fmt(float("nan")) == UNAVAILABLE
    assert s.fmt(1.5) == "1.5"
    assert s.fmt_triple(None) == UNAVAILABLE
    assert s.fmt_triple([1, 2, 3]) == "[1.0, 2.0, 3.0]"
