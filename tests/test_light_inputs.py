"""The environment variables of the light calculation: schema, schedule, energy, geometry."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from conftest import LIGHT_FIXTURE_DIR, light_input, light_scene_payload, point_fixture_payload
from tomato3d.io.schemas import (
    LEAF_PATCHES_CSV_COLUMNS,
    LEAF_SURFACES_CSV_COLUMNS,
    LightScene,
    ScalarInput,
    SchemaError,
    validate_model,
)
from tomato3d.io.tables import write_table
from tomato3d.light.budget import absorbed_umol_per_j, dli_mol_m2_day
from tomato3d.light.geometry import (
    load_geometry,
    patch_vertices_mm,
    subdivision_barycentrics,
    triangle_areas_mm2,
    triangle_unit_normals,
)
from tomato3d.light.scene import (
    LightInputError,
    electricity_kwh_day,
    full_output_hours_per_day,
    input_records,
    load_scene,
    non_observed_input_names,
    resolve_scenario,
)


def _scene(payload: dict) -> LightScene:
    return validate_model(payload, LightScene)


# --------------------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------------------


def test_an_unknown_value_must_say_so() -> None:
    assert ScalarInput(value=0.0, status="measured", source="meter").is_available
    with pytest.raises(ValueError, match="unavailable"):
        ScalarInput(value=None, status="assumed", source="x")
    with pytest.raises(ValueError, match="unavailable"):
        ScalarInput(value=0.0, status="unavailable", source="x")


def test_the_example_scene_validates_and_reports_every_placeholder() -> None:
    scene = load_scene(LIGHT_FIXTURE_DIR / "light_scene.example.json")
    records = input_records(scene)
    names = {record.name for record in records}
    assert "fixtures[LED-front].photon_flux_umol_s" in names
    assert "plants[DT-001].board_origin_grow_mm" in names
    assert "leaf_optics.absorptance" in names
    flagged = non_observed_input_names(records)
    assert len(flagged) == len(records)  # every example value is a placeholder
    assert scene.scenario_ids == ["as_built", "leds_up_100mm", "bars_tilted_inward"]


def test_optical_properties_cannot_exceed_one() -> None:
    payload = light_scene_payload()
    payload["leaf_optics"]["transmittance"] = light_input(0.2)
    payload["leaf_optics"]["absorptance"] = light_input(0.9)
    with pytest.raises(SchemaError, match="exceeds 1"):
        validate_model(payload, LightScene)


def test_an_unplaced_plant_is_refused() -> None:
    payload = light_scene_payload(plants=["P"])
    payload["plants"][0]["board_yaw_deg"] = light_input(None, "unavailable")
    with pytest.raises(SchemaError, match="placement"):
        validate_model(payload, LightScene)


def test_scenarios_may_only_touch_known_fixtures_and_not_reuse_as_built() -> None:
    payload = light_scene_payload()
    payload["scenarios"] = [
        {"scenario_id": "x", "description": "d", "fixture_overrides": [{"fixture_id": "nope"}]}
    ]
    with pytest.raises(SchemaError, match="unknown fixture"):
        validate_model(payload, LightScene)
    payload["scenarios"] = [{"scenario_id": "as_built", "description": "d"}]
    with pytest.raises(SchemaError, match="reserved"):
        validate_model(payload, LightScene)


# --------------------------------------------------------------------------------------
# Schedule, DLI and electricity
# --------------------------------------------------------------------------------------


def test_the_arithmetic_calculator_example_is_reproduced() -> None:
    """40 W, 16 h, 300 umol m-2 s-1 point PPFD, 60 of 100 umol/s absorbed."""
    scene = _scene(light_scene_payload([point_fixture_payload(electrical_input_w=40.0)]))
    state = resolve_scenario(scene, "as_built").fixtures[0]
    assert state.full_output_hours_per_day == 16.0
    assert dli_mol_m2_day(300.0, state.full_output_hours_per_day) == pytest.approx(17.28)
    assert state.electricity_kwh_day == pytest.approx(0.640)
    absorbed_mol_day = 60.0 * 16.0 * 3600.0 / 1e6
    assert absorbed_umol_per_j(absorbed_mol_day, state.electricity_kwh_day) == pytest.approx(1.50)


def test_schedule_segments_cross_midnight_and_weight_by_output() -> None:
    schedule = [
        {"start_hhmm": "20:00", "end_hhmm": "04:00", "output_fraction": 1.0},
        {"start_hhmm": "04:00", "end_hhmm": "06:00", "output_fraction": 0.5,
         "electrical_input_w": light_input(22.0, "measured")},
    ]
    scene = _scene(light_scene_payload([point_fixture_payload(schedule=schedule)]))
    fixture = scene.fixtures[0]
    assert full_output_hours_per_day(fixture) == pytest.approx(9.0)
    kwh, reason = electricity_kwh_day(fixture)
    assert reason is None
    assert kwh == pytest.approx((40.0 * 8.0 + 22.0 * 2.0) / 1000.0)


def test_a_dimmed_segment_without_measured_power_leaves_electricity_unavailable() -> None:
    schedule = [{"start_hhmm": "06:00", "end_hhmm": "22:00", "output_fraction": 0.7}]
    scene = _scene(light_scene_payload([point_fixture_payload(schedule=schedule)]))
    kwh, reason = electricity_kwh_day(scene.fixtures[0])
    assert kwh is None
    assert "dimmed" in reason


def test_overlapping_or_empty_segments_are_refused() -> None:
    overlap = [
        {"start_hhmm": "06:00", "end_hhmm": "12:00", "output_fraction": 1.0},
        {"start_hhmm": "11:00", "end_hhmm": "13:00", "output_fraction": 1.0},
    ]
    with pytest.raises(SchemaError, match="overlap"):
        _scene(light_scene_payload([point_fixture_payload(schedule=overlap)]))
    empty = [{"start_hhmm": "06:00", "end_hhmm": "06:00", "output_fraction": 1.0}]
    with pytest.raises(SchemaError, match="duration"):
        _scene(light_scene_payload([point_fixture_payload(schedule=empty)]))


def test_a_scenario_marks_what_it_changed_and_can_switch_a_lamp_off() -> None:
    payload = light_scene_payload([point_fixture_payload("A"), point_fixture_payload("B")])
    payload["scenarios"] = [
        {
            "scenario_id": "raise_a",
            "description": "raise A",
            "fixture_overrides": [
                {"fixture_id": "A", "emitting_center_grow_mm": [0.0, 0.0, 1200.0]},
                {"fixture_id": "B", "enabled": False},
            ],
        }
    ]
    resolved = resolve_scenario(_scene(payload), "raise_a")
    assert [state.fixture_id for state in resolved.fixtures] == ["A"]
    center = resolved.fixtures[0].fixture.emitting_center_grow_mm
    assert center.value == (0.0, 0.0, 1200.0)
    assert center.status == "scenario"
    assert resolved.fixtures[0].fixture.aim_tilt_deg.status == "assumed"
    with pytest.raises(LightInputError, match="not defined"):
        resolve_scenario(_scene(payload), "missing")


# --------------------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tilt_deg", "azimuth_deg"), [(0.0, 0.0), (30.0, 0.0), (45.0, 135.0), (120.0, 270.0)]
)
def test_a_leaf_patch_has_its_area_and_upper_normal(tilt_deg: float, azimuth_deg: float) -> None:
    tilt, azimuth = math.radians(tilt_deg), math.radians(azimuth_deg)
    triangles = patch_vertices_mm((1.0, 2.0, 3.0), 1200.0, tilt, azimuth, 2.0)
    assert triangle_areas_mm2(triangles).sum() == pytest.approx(1200.0)
    expected = [
        math.sin(tilt) * math.cos(azimuth),
        math.sin(tilt) * math.sin(azimuth),
        math.cos(tilt),
    ]
    np.testing.assert_allclose(triangle_unit_normals(triangles), [expected, expected], atol=1e-12)
    np.testing.assert_allclose(triangles.reshape(-1, 3).mean(axis=0), [1.0, 2.0, 3.0], atol=1e-12)


@pytest.mark.parametrize("subdivisions", [1, 2, 5])
def test_sub_triangle_samples_are_inside_and_centred(subdivisions: int) -> None:
    coords = subdivision_barycentrics(subdivisions)
    assert coords.shape == (subdivisions**2, 2)
    assert (coords > 0).all() and (coords.sum(axis=1) < 1).all()
    np.testing.assert_allclose(coords.mean(axis=0), [1.0 / 3.0, 1.0 / 3.0], atol=1e-12)


def _surface_row(**overrides: str) -> dict[str, str]:
    row = {
        "plant_id": "P",
        "session_id": "P_20260920_0900",
        "geometry_variant_id": "multiview_41",
        "geometry_source": "reconstructed",
        "organ_class": "leaf",
        "organ_id": "leaf_001",
        "leaflet_id": "unavailable",
        "triangle_id": "t0",
        "v0_x_mm": "0", "v0_y_mm": "0", "v0_z_mm": "100",
        "v1_x_mm": "10", "v1_y_mm": "0", "v1_z_mm": "100",
        "v2_x_mm": "0", "v2_y_mm": "10", "v2_z_mm": "100",
        "normal_convention": "adaxial_ccw",
    }
    row.update(overrides)
    return row


def _patch_row(**overrides: str) -> dict[str, str]:
    row = {
        "plant_id": "P",
        "session_id": "P_20260920_0900",
        "geometry_variant_id": "multiview_41",
        "geometry_source": "simplified",
        "organ_id": "leaf_002",
        "centroid_x_mm": "0", "centroid_y_mm": "0", "centroid_z_mm": "120",
        "area_mm2": "900", "normal_tilt_deg": "20", "normal_azimuth_deg": "0",
        "length_to_width_ratio": "1.5",
    }
    row.update(overrides)
    return row


def test_surfaces_and_patches_merge_into_one_variant(tmp_path: Path) -> None:
    surfaces_csv, patches_csv = tmp_path / "leaf_surfaces.csv", tmp_path / "leaf_patches.csv"
    stem = _surface_row(organ_class="stem_segment", organ_id="stem", triangle_id="s0")
    write_table(surfaces_csv, [_surface_row(), stem], LEAF_SURFACES_CSV_COLUMNS)
    write_table(patches_csv, [_patch_row()], LEAF_PATCHES_CSV_COLUMNS)
    variants = load_geometry([surfaces_csv, patches_csv])
    surfaces = variants["multiview_41"]
    assert surfaces.n_triangles == 4
    assert surfaces.is_receiver.tolist() == [True, False, True, True]
    assert sorted(set(surfaces.organ_ids)) == ["leaf_001", "leaf_002", "stem"]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([_surface_row(v1_z_mm="unavailable")], "unavailable"),
        ([_surface_row(v1_x_mm="0", v1_y_mm="0")], "degenerate"),
        ([_surface_row(geometry_variant_id="no_plants")], "reserved"),
        ([_surface_row(), _surface_row()], "repeats"),
        ([_surface_row(), _surface_row(triangle_id="t1", session_id="P_20260922_0900")], "mixes"),
        ([_surface_row(organ_class="flower")], "organ_class"),
    ],
)
def test_bad_geometry_is_refused(tmp_path: Path, rows: list[dict[str, str]], message: str) -> None:
    path = tmp_path / "leaf_surfaces.csv"
    write_table(path, rows, LEAF_SURFACES_CSV_COLUMNS)
    with pytest.raises(LightInputError, match=message):
        load_geometry([path])


def test_one_leaf_described_twice_is_refused(tmp_path: Path) -> None:
    surfaces_csv, patches_csv = tmp_path / "s.csv", tmp_path / "p.csv"
    write_table(surfaces_csv, [_surface_row(organ_id="leaf_002")], LEAF_SURFACES_CSV_COLUMNS)
    write_table(patches_csv, [_patch_row(organ_id="leaf_002")], LEAF_PATCHES_CSV_COLUMNS)
    with pytest.raises(LightInputError, match="both"):
        load_geometry([surfaces_csv, patches_csv])


def test_an_unknown_table_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "other.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(LightInputError, match="neither"):
        load_geometry([path])
