"""Direct light, shading and photon bookkeeping, against cases with a known answer.

A wrong light model still produces plausible PPFD numbers, so every test here pins a
value that can be derived by hand: the inverse-square law, Lambert's cosine law,
conservation of emitted photons, and attenuation by a known number of leaves.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from conftest import light_scene_payload, point_fixture_payload
from tomato3d.io.schemas import LightScene, SchemaError, validate_model
from tomato3d.light.frames import board_to_grow_mm, fixture_axes
from tomato3d.light.geometry import patch_vertices_mm, sample_triangles, triangle_areas_mm2
from tomato3d.light.raytrace import (
    Occluders,
    Receivers,
    count_crossings,
    direct_light,
)
from tomato3d.light.scene import (
    FixtureState,
    axial_intensity_umol_s_sr,
    cosine_exponent,
    resolve_scenario,
)
from tomato3d.light.units import MM2_PER_M2


def _scene(fixtures: list[dict], **kwargs: object) -> LightScene:
    return validate_model(light_scene_payload(fixtures, **kwargs), LightScene)


def _fixtures(scene: LightScene) -> tuple[FixtureState, ...]:
    return resolve_scenario(scene, "as_built").fixtures


def _receivers(
    points_mm: list[tuple[float, float, float]], normal=(0.0, 0.0, 1.0), two_sided=False
) -> Receivers:
    points = np.asarray(points_mm, dtype=np.float64)
    normals = np.tile(np.asarray(normal, dtype=np.float64), (points.shape[0], 1))
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    return Receivers(points, normals, two_sided, np.full(points.shape[0], -1))


def _square(center_mm, half_mm: float) -> np.ndarray:
    """Two horizontal triangles; their shared diagonal passes through ``center_mm``."""
    cx, cy, cz = center_mm
    corners = [
        (cx - half_mm, cy - half_mm, cz),
        (cx + half_mm, cy - half_mm, cz),
        (cx + half_mm, cy + half_mm, cz),
        (cx - half_mm, cy + half_mm, cz),
    ]
    return np.array([[corners[0], corners[1], corners[2]], [corners[0], corners[2], corners[3]]])


def _occluders(squares: list[tuple[np.ndarray, bool]]) -> Occluders:
    vertices = np.concatenate([square for square, _ in squares])
    is_leaf = np.concatenate([[leaf, leaf] for _, leaf in squares]).astype(bool)
    codes = np.repeat(np.arange(len(squares)), 2)
    return Occluders(vertices, is_leaf, codes, np.zeros(codes.size, dtype=np.int64))


def _ppfd(receivers, scene, occluders=None) -> np.ndarray:
    light = direct_light(
        receivers,
        _fixtures(scene),
        occluders if occluders is not None else Occluders.none(),
        scene.leaf_optics.transmittance.value,
        scene.simulation,
    )
    return light.ppfd_umol_m2_s.sum(axis=0)


# --------------------------------------------------------------------------------------
# Emission and irradiance
# --------------------------------------------------------------------------------------


def test_lambertian_point_lamp_matches_the_closed_form() -> None:
    """m = 1 gives I0 = flux / pi, so E below the lamp is flux / (pi d**2)."""
    scene = _scene([point_fixture_payload(center_mm=(0.0, 0.0, 1000.0), photon_flux_umol_s=100.0)])
    ppfd = _ppfd(_receivers([(0.0, 0.0, 500.0), (0.0, 0.0, 0.0)]), scene)
    expected_at_500mm = 100.0 / (math.pi * 0.5**2)
    assert ppfd[0] == pytest.approx(expected_at_500mm, rel=1e-12)
    assert ppfd[0] / ppfd[1] == pytest.approx(4.0, rel=1e-12)


def test_tilted_receiver_follows_lamberts_cosine_law() -> None:
    scene = _scene([point_fixture_payload()])
    tilt_rad = math.radians(60.0)
    flat = _ppfd(_receivers([(0.0, 0.0, 0.0)]), scene)[0]
    tilted = _ppfd(
        _receivers([(0.0, 0.0, 0.0)], normal=(math.sin(tilt_rad), 0.0, math.cos(tilt_rad))), scene
    )[0]
    assert tilted == pytest.approx(flat * 0.5, rel=1e-12)


def test_one_sided_sensor_is_dark_from_behind_but_a_leaf_is_not() -> None:
    scene = _scene([point_fixture_payload()])
    down = (0.0, 0.0, -1.0)
    up_value = _ppfd(_receivers([(0.0, 0.0, 0.0)]), scene)[0]
    assert _ppfd(_receivers([(0.0, 0.0, 0.0)], normal=down), scene)[0] == 0.0
    assert _ppfd(_receivers([(0.0, 0.0, 0.0)], normal=down, two_sided=True), scene)[0] == (
        pytest.approx(up_value, rel=1e-12)
    )


@pytest.mark.parametrize(
    ("half_angle_deg", "cutoff_deg"), [(60.0, 90.0), (20.0, 90.0), (60.0, 45.0)]
)
def test_normalisation_emits_exactly_the_photon_flux(
    half_angle_deg: float, cutoff_deg: float
) -> None:
    """Integrating I0 cos(theta)**m over the cutoff cone returns the configured flux."""
    exponent = cosine_exponent(math.radians(half_angle_deg))
    cutoff_rad = math.radians(cutoff_deg)
    i0 = axial_intensity_umol_s_sr(100.0, exponent, cutoff_rad)
    theta = np.linspace(0.0, cutoff_rad, 200_001)
    integrand = i0 * np.cos(theta) ** exponent * np.sin(theta) * 2.0 * math.pi
    assert np.trapezoid(integrand, theta) == pytest.approx(100.0, rel=1e-6)
    assert math.cos(math.radians(half_angle_deg)) ** exponent == pytest.approx(0.5)


def test_the_floor_receives_every_photon_the_lamp_emits() -> None:
    """Photon conservation: PPFD integrated over a floor that holds the beam equals the flux.

    A test on PPFD ratios would pass even with the absolute scale wrong; this one does not.
    """
    scene = _scene(
        [
            point_fixture_payload(
                center_mm=(0.0, 0.0, 400.0), half_angle_deg=15.0, photon_flux_umol_s=250.0
            )
        ]
    )
    cell_mm, half_extent_mm, subdivisions = 20.0, 400.0, 2
    triangles = []
    edges = np.arange(-half_extent_mm, half_extent_mm, cell_mm)
    for x in edges:
        for y in edges:
            triangles.extend(_square((x + cell_mm / 2, y + cell_mm / 2, 0.0), cell_mm / 2))
    vertices = np.array(triangles)
    points, _ = sample_triangles(vertices, subdivisions)
    ppfd = _ppfd(_receivers(points.tolist()), scene)
    sample_area_m2 = triangle_areas_mm2(vertices)[0] / subdivisions**2 / MM2_PER_M2
    assert float((ppfd * sample_area_m2).sum()) == pytest.approx(250.0, rel=5e-3)


def test_narrowing_the_beam_concentrates_the_same_photons() -> None:
    below = _receivers([(0.0, 0.0, 0.0)])
    wide = _ppfd(below, _scene([point_fixture_payload(half_angle_deg=60.0)]))[0]
    narrow = _ppfd(below, _scene([point_fixture_payload(half_angle_deg=30.0)]))[0]
    assert narrow > 2.0 * wide


def test_light_outside_the_cutoff_cone_is_zero() -> None:
    scene = _scene([point_fixture_payload(cutoff_deg=30.0)])
    inside = (math.tan(math.radians(29.0)) * 1000.0, 0.0, 0.0)
    outside = (math.tan(math.radians(31.0)) * 1000.0, 0.0, 0.0)
    ppfd = _ppfd(_receivers([inside, outside]), scene)
    assert ppfd[0] > 0.0
    assert ppfd[1] == 0.0


def test_a_bar_lamp_spreads_its_emitters_along_its_long_side() -> None:
    scene = _scene([point_fixture_payload(length_mm=500.0, emitter_grid=(5, 1))])
    emitters = _fixtures(scene)[0].emitters
    assert emitters is not None
    np.testing.assert_allclose(
        emitters.positions_grow_mm[:, 0], [-200.0, -100.0, 0.0, 100.0, 200.0]
    )
    np.testing.assert_allclose(emitters.positions_grow_mm[:, 1:], [[0.0, 1000.0]] * 5)


def test_tilting_a_lamp_moves_its_light_toward_the_lean() -> None:
    scene = _scene([point_fixture_payload(aim_tilt_deg=30.0, aim_azimuth_deg=0.0)])
    ppfd = _ppfd(_receivers([(400.0, 0.0, 0.0), (-400.0, 0.0, 0.0)]), scene)
    assert ppfd[0] > ppfd[1]


def test_a_long_axis_parallel_to_the_aim_is_refused() -> None:
    with pytest.raises(SchemaError, match="parallel"):
        fixture_axes(math.radians(90.0), 0.0, 0.0)


# --------------------------------------------------------------------------------------
# Shading
# --------------------------------------------------------------------------------------


def test_leaves_attenuate_once_each_and_opaque_surfaces_block() -> None:
    """The ray below the lamp runs through each square's shared diagonal: one leaf, one factor."""
    scene = _scene([point_fixture_payload()], transmittance=0.1)
    below = _receivers([(0.0, 0.0, 0.0)])
    clear = _ppfd(below, scene)[0]
    one_leaf = _occluders([(_square((0.0, 0.0, 500.0), 50.0), True)])
    two_leaves = _occluders(
        [(_square((0.0, 0.0, 400.0), 50.0), True), (_square((0.0, 0.0, 600.0), 50.0), True)]
    )
    stem = _occluders([(_square((0.0, 0.0, 500.0), 50.0), False)])
    assert _ppfd(below, scene, one_leaf)[0] == pytest.approx(clear * 0.1, rel=1e-12)
    assert _ppfd(below, scene, two_leaves)[0] == pytest.approx(clear * 0.01, rel=1e-12)
    assert _ppfd(below, scene, stem)[0] == 0.0


def test_a_surface_beyond_the_lamp_or_beside_the_ray_does_not_shade() -> None:
    scene = _scene([point_fixture_payload()])
    below = _receivers([(0.0, 0.0, 0.0)])
    clear = _ppfd(below, scene)[0]
    above_lamp = _occluders([(_square((0.0, 0.0, 1200.0), 50.0), False)])
    beside = _occluders([(_square((200.0, 0.0, 500.0), 50.0), False)])
    assert _ppfd(below, scene, above_lamp)[0] == clear
    assert _ppfd(below, scene, beside)[0] == clear


def test_unknown_transmittance_makes_only_rays_through_leaves_unavailable() -> None:
    scene = _scene([point_fixture_payload()], transmittance=None)
    receivers = _receivers([(0.0, 0.0, 0.0), (600.0, 0.0, 0.0)])
    leaf = _occluders([(_square((0.0, 0.0, 500.0), 50.0), True)])
    ppfd = _ppfd(receivers, scene, leaf)
    assert np.isnan(ppfd[0])
    assert np.isfinite(ppfd[1]) and ppfd[1] > 0.0


def test_a_lamp_with_unknown_flux_leaves_its_light_unavailable_not_zero() -> None:
    scene = _scene([point_fixture_payload(photon_flux_umol_s=None)])
    assert np.isnan(_ppfd(_receivers([(0.0, 0.0, 0.0)]), scene)[0])


def test_a_flat_leaf_is_not_shaded_by_itself() -> None:
    from tomato3d.light.pipeline import build_occluders, leaf_receivers
    from tomato3d.light.geometry import SurfaceSet

    vertices = patch_vertices_mm((0.0, 0.0, 300.0), 2500.0, math.radians(20.0), 0.0, 1.5)
    surfaces = SurfaceSet(
        geometry_variant_id="v",
        plant_ids=("P", "P"),
        session_ids=("P_20260920_0900",) * 2,
        geometry_sources=("manual",) * 2,
        surface_classes=("leaf", "leaf"),
        organ_ids=("leaf_001", "leaf_001"),
        leaflet_ids=("unavailable",) * 2,
        triangle_ids=("patch_0", "patch_1"),
        vertices_board_mm=vertices,
        normal_known=np.array([True, True]),
    )
    scene = _scene([point_fixture_payload()], subdivisions=3)
    receivers, _ = leaf_receivers(surfaces, vertices, 3)
    light = direct_light(
        receivers, _fixtures(scene), build_occluders(surfaces, vertices), 0.1, scene.simulation
    )
    np.testing.assert_allclose(light.ppfd_umol_m2_s, light.unoccluded_ppfd_umol_m2_s)
    np.testing.assert_allclose(light.upper_side_ppfd_umol_m2_s, light.ppfd_umol_m2_s)


def test_bounding_box_culling_does_not_change_the_crossings() -> None:
    rng = np.random.default_rng(7)
    centers = rng.uniform(-300.0, 300.0, size=(60, 3))
    vertices = centers[:, None, :] + rng.uniform(-60.0, 60.0, size=(60, 3, 3))
    is_leaf = rng.random(60) < 0.7
    codes = np.arange(60)
    origins = rng.uniform(-400.0, 400.0, size=(500, 3))
    segments = rng.uniform(-800.0, 800.0, size=(500, 3))
    own = np.full(500, -1)
    grouped = Occluders(vertices, is_leaf, codes, np.arange(60) // 10)
    single = Occluders(vertices, is_leaf, codes, np.zeros(60, dtype=np.int64))
    crossings_grouped, blocked_grouped = count_crossings(origins, segments, own, grouped, 997)
    crossings_single, blocked_single = count_crossings(origins, segments, own, single, 10**6)
    np.testing.assert_array_equal(crossings_grouped, crossings_single)
    np.testing.assert_array_equal(blocked_grouped, blocked_single)
    assert crossings_single.sum() > 0 and blocked_single.any()


def test_board_to_grow_rotates_then_translates() -> None:
    point = np.array([[10.0, 0.0, 5.0]])
    moved = board_to_grow_mm(point, np.array([100.0, 200.0, 30.0]), math.radians(90.0))
    np.testing.assert_allclose(moved, [[100.0, 210.0, 35.0]], atol=1e-12)
