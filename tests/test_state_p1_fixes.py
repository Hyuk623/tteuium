"""P1 fixes (2026-10-12): A1 capture timezone, A2 side-view rule recorded, A4 generator candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tomato3d.cli import run_p1
from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import fixture_truth as ft
from tomato3d.state import ingest
from tomato3d.state import optical as op
from tomato3d.state import schema as s
from tomato3d.state import sidegeom as sg
from tomato3d.state.topraster import OrthoCamera

FIX = Path(__file__).parent / "fixtures" / "p1"
HEADER = ("plant_id,session_id,photo_file,photo_kind,azimuth_deg,camera_elevation_deg_approx,captured_at,"
          "scale_reference,ruler_plane,exposure_note,notes,source_filename,sha256,azimuth_basis,height_above_rim_cm")


def _raw(root: Path, captured_at: str = "2026-10-05 17:02:03") -> Path:
    session = root / "data" / "raw" / "dwt_901" / "dwt_901_gen_20261005"
    session.mkdir(parents=True)
    (session / "top.heic").write_bytes(b"x")
    sha = hashlib.sha256(b"x").hexdigest()
    (session / "generator_capture.csv").write_text(
        HEADER + f"\ndwt_901,dwt_901_gen_20261005,top.heic,top,,90,{captured_at},ruler_cm,pot_rim,,,IMG,{sha},,\n",
        encoding="utf-8")
    return root / "data" / "raw"


# ---------------------------------------------------------------- A1 capture timezone

def test_without_timezone_times_stay_naive_and_unavailable(tmp_path) -> None:
    rows, problems = ingest.real_capture_rows(ingest.discover_raw(_raw(tmp_path), "dwt_9*"), tmp_path)
    assert not problems
    s.check_captures(rows)
    assert rows[0]["capture_time"] == "2026-10-05T17:02:03"
    assert rows[0]["capture_tz"] == UNAVAILABLE and rows[0]["capture_tz_source"] == UNAVAILABLE


def test_stated_timezone_makes_times_aware(tmp_path) -> None:
    rows, problems = ingest.real_capture_rows(ingest.discover_raw(_raw(tmp_path), "dwt_9*"), tmp_path, "Asia/Seoul")
    assert not problems
    s.check_captures(rows)
    assert rows[0]["capture_time"] == "2026-10-05T17:02:03+09:00"
    assert rows[0]["capture_tz"] == "Asia/Seoul" and rows[0]["capture_tz_source"] == "user_stated"


def test_invalid_timezone_rejected(tmp_path) -> None:
    for bad in ("Seoul", "Mars/Base", "UTC+9", "", "unavailable", "local"):
        with pytest.raises(s.P1SchemaError):
            s.parse_capture_tz(bad)
    with pytest.raises(s.P1SchemaError):
        ingest.real_capture_rows(ingest.discover_raw(_raw(tmp_path), "dwt_9*"), tmp_path, "Seoul")
    assert str(s.parse_capture_tz("UTC+09:00")) == "UTC+09:00"


def test_dst_gap_and_fold_are_errors_not_guesses(tmp_path) -> None:
    with pytest.raises(s.P1SchemaError, match="does not exist"):
        s.localize_capture_time("2026-03-08T02:30:00", "America/New_York")
    with pytest.raises(s.P1SchemaError, match="ambiguous"):
        s.localize_capture_time("2026-11-01T01:30:00", "America/New_York")
    raw = _raw(tmp_path, "2026-11-01 01:30:00")
    _, problems = ingest.real_capture_rows(ingest.discover_raw(raw, "dwt_9*"), tmp_path, "America/New_York")
    assert problems and "ambiguous" in problems[0]


def test_no_implicit_offset_and_offset_must_match(tmp_path) -> None:
    rows, _ = ingest.real_capture_rows(ingest.discover_raw(_raw(tmp_path), "dwt_9*"), tmp_path, "Asia/Seoul")
    implicit = dict(rows[0], capture_tz=UNAVAILABLE, capture_tz_source=UNAVAILABLE)
    with pytest.raises(s.P1SchemaError, match="no implicit offset"):
        s.check_captures([implicit])
    wrong = dict(rows[0], capture_time="2026-10-05T17:02:03+02:00")
    with pytest.raises(s.P1SchemaError, match="disagrees"):
        s.check_captures([wrong])
    naive = dict(rows[0], capture_time="2026-10-05T17:02:03")
    with pytest.raises(s.P1SchemaError, match="naive"):
        s.check_captures([naive])


def test_revision1_capture_headers_still_validate(tmp_path) -> None:
    rows, _ = ingest.real_capture_rows(ingest.discover_raw(_raw(tmp_path), "dwt_9*"), tmp_path)
    old = [{k: v for k, v in r.items() if k in s.CAPTURES_COLUMNS_REV1} for r in rows]
    s.check_captures(old)
    assert s.P1_SCHEMA_VERSION == "p1_state_v1" and s.P1_SCHEMA_REVISION >= 2


def test_cli_capture_tz_guards(tmp_path) -> None:
    out = tmp_path / "x"
    assert run_p1.main(["prepare", "--mode", "fixture", "--out", str(out), "--capture-tz", "Asia/Seoul",
                        "--capture-tz-ref", "u"]) == 2
    assert run_p1.main(["prepare", "--mode", "real", "--out", str(out), "--capture-tz", "Seoul",
                        "--capture-tz-ref", "u"]) == 2
    assert run_p1.main(["prepare", "--mode", "real", "--out", str(out), "--capture-tz", "Asia/Seoul"]) == 2
    assert not out.exists() or not any(out.iterdir())


# ---------------------------------------------------------------- A2 side-view rule recorded

def test_side_view_rule_selects_first_side_on_view_and_records_rule() -> None:
    def row(view: str, cls: str, ang: str = "40") -> dict[str, str]:
        r = sg.side_row("p", "c", view, "p/C0001", {"compound_insertion_angle_deg": float(ang)},
                        sg.POINTS_SOURCE_FIXTURE, "synthetic_fixture", "derived", None, UNAVAILABLE, cls)
        return r

    rows = sg.select_views([row("02_x", "cl_left"), row("00_x", "cl_toward"), row("01_x", "cl_right"),
                            row("03_x", "unclear")])
    chosen = [r["view_id"] for r in rows if r["selected_for_mtg"] == "true"]
    assert chosen == ["01_x"], "first side-on view by view_id"
    assert {r["view_selection_rule"] for r in rows} == {sg.VIEW_SELECTION_RULE}
    none = sg.select_views([row("00_x", "cl_toward"), row("01_x", "cl_away")])
    assert not [r for r in none if r["selected_for_mtg"] == "true"], "no side-on view -> no MTG side values"


def test_one_selected_view_per_compound_on_a_real_scene() -> None:
    rows, _ = sg.validate_scene(FIX / "sideprop" / "scenes" / "scene_0000", "fxs")
    assert {r["capture_id"] for r in rows} == {"scene_0000"}, "the four views are one capture"
    selected = [r for r in sg.select_views(rows) if r["selected_for_mtg"] == "true"]
    per_compound = [r["compound_id"] for r in selected]
    assert len(per_compound) == len(set(per_compound)) and selected
    for r in selected:
        side_on = sorted(x["view_id"] for x in rows if x["compound_id"] == r["compound_id"]
                         and x["direction_class"] in sg.SIDE_ON_CLASSES)
        assert r["view_id"] == side_on[0]


def test_rule_summary_compares_rule_with_first_view() -> None:
    rows, errors = sg.validate_scene(FIX / "sideprop" / "scenes" / "scene_0000", "fxs")
    summ = {(r["quantity"], r["selection"]): r for r in sg.rule_summary(errors)}
    assert ("compound_insertion_angle_deg", "mtg_a3_side_on") in summ
    assert ("compound_insertion_angle_deg", "first_view") in summ


# ---------------------------------------------------------------- A4 generator candidates

@pytest.fixture(scope="module")
def occluded_case():
    plant = ft.load_plant(FIX / "O-mature" / "scenes" / "scene_0000", "fxa")
    cam = OrthoCamera(512, 0.4)
    render = ft.render_capture(plant, 0.0, cam)
    obs = ft.observe_top(render, "fxa", "c0", 150, "t")
    terminal_of = {r["parent_obs_id"]: r["obs_id"] for r in obs.rows if r["obs_class"] == "terminal_leaflet"}
    comp = next(r for r in obs.rows if r["obs_class"] == "compound_leaf" and r["touches_other_mask"] == "true")
    cell = FIX / "O-mature"
    gen_cfg = json.loads((cell / "generator_config.json").read_text(encoding="utf-8"))
    from tomato3d.synth.contours import load_library

    contours, _ = load_library(cell / "leaflet_contours.json")
    return cam, render, obs.masks[comp["obs_id"]], obs.masks.get(terminal_of.get(comp["obs_id"], "")), gen_cfg, contours


def test_generator_candidates_keep_threshold_and_provenance(occluded_case) -> None:
    cam, render, mask, tmask, gen_cfg, contours = occluded_case
    tol = ft.load_p1_config()["completion"]["coverage_tolerance"]["value"]
    assert tol == 0.98, "the coverage threshold is not lowered"
    kept, rep = op.generate_candidates(mask, render.visible > 0, 0.0, cam, gen_cfg, contours, 12, 0.5, tol, 5,
                                       "fxa/C0001", tmask, 4, (-5.0, 0.0, 5.0), (1.0, 1.05))
    assert rep["adapter"] == "generator_numpy_conditioned" and rep["prior_status"] == "user_assumed_unvalidated"
    assert rep["n_generated"] + rep["n_contract_rejected"] == 12
    assert all(c.coverage >= tol for c in kept)
    assert all(c.donor_ref.startswith("build_compound(numpy") for c in kept)
    again, _ = op.generate_candidates(mask, render.visible > 0, 0.0, cam, gen_cfg, contours, 12, 0.5, tol, 5,
                                      "fxa/C0001", tmask, 4, (-5.0, 0.0, 5.0), (1.0, 1.05))
    assert [c.candidate_id for c in kept] == [c.candidate_id for c in again], "fixed seeds replay"


def test_candidates_never_become_observations(occluded_case, tmp_path) -> None:
    cam, render, mask, tmask, gen_cfg, contours = occluded_case
    kept, _ = op.generate_candidates(mask, render.visible > 0, 0.0, cam, gen_cfg, contours, 12, 0.5, 0.0, 2,
                                     "fxa/C0001", tmask)
    assert kept
    rows = op.export_candidates(tmp_path, Path("o"), "fxa", "c0", kept)
    s.check_optical_rows(rows)
    assert {r["optical_readiness"] for r in rows} == {"conditional_completion"}
    assert {r["geometry_source"] for r in rows} == {"generated_candidate"}
    from tomato3d.state import update as up

    sub = up.candidate_rows("fxa", "fxa", "c0", "fxa/C0001", kept[0].candidate_id, "plant_local_mm",
                            "synthetic_fixture", [dict(tag="T", area_mm2=1.0, base_mm=[0.0, 0.0, 0.0])])
    s.check_candidate_rows(sub, "candidates.csv")
    with pytest.raises(s.P1SchemaError):
        s.check_mtg_rows(sub)


def test_terminal_pins_stay_inside_generator_ranges(occluded_case) -> None:
    cam, render, mask, tmask, gen_cfg, contours = occluded_case
    obs = op.observed_geometry(mask, 0.0, cam)
    pins, notes = op.terminal_pins(tmask, obs, 0.0, cam, gen_cfg, contours)
    from tomato3d.synth.config import range_of

    if "terminal_rel_length" in pins:
        lo, hi = range_of(gen_cfg, "terminal_rel_length")
        assert lo <= pins["terminal_rel_length"] <= hi
    if "width_scale.T" in pins:
        lo, hi = range_of(gen_cfg, "leaflet_width_scale")
        assert lo <= pins["width_scale.T"] <= hi
    assert set(pins) <= {"terminal_rel_length", "contour_index.T", "width_scale.T"}
    assert notes
