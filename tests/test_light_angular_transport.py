"""Actual core transport diagnostics; no lamp-center substitute or second tracer."""
from dataclasses import replace

import numpy as np
import pytest

from conftest import light_scene_payload, point_fixture_payload
from tomato3d.io.schemas import LightScene
from tomato3d.light import raytrace
from tomato3d.light.raytrace import Receivers, Occluders, direct_light
from tomato3d.light.scene import resolve_scenario

ATOL, RTOL = 1e-10, 1e-9


def case(payloads=None, tau=.1):
    scene = LightScene.model_validate(light_scene_payload(payloads, transmittance=tau))
    fixtures = resolve_scenario(scene, 'as_built').fixtures
    receivers = Receivers(np.array([[0., 0., 0.], [80., 30., 20.], [-90., 15., 40.]]),
                          np.tile([0., 0., 1.], (3, 1)), True, np.full(3, -1))
    return receivers, fixtures, Occluders.none(), tau, scene.simulation


def surface(z=500., leaf=True):
    v = np.array([[[-300., -300., z], [300., -300., z], [300., 300., z]],
                  [[-300., -300., z], [300., 300., z], [-300., 300., z]]])
    return Occluders(v, np.full(2, leaf), np.zeros(2, dtype=int), np.zeros(2, dtype=int))


def run(args, chunk=2):
    events = []
    def collect(event):
        assert event['protocol'] == 'direct-angular-1'
        for value in event.values():
            if isinstance(value, np.ndarray): assert not value.flags.writeable
        events.append({k: v.copy() if isinstance(v, np.ndarray) else v for k, v in event.items()})
    off = direct_light(*args)
    on = direct_light(*args, diagnostic_callback=collect, diagnostic_max_paths_per_chunk=chunk)
    for name in ('ppfd_umol_m2_s', 'upper_side_ppfd_umol_m2_s', 'unoccluded_ppfd_umol_m2_s'):
        np.testing.assert_allclose(getattr(off, name), getattr(on, name), atol=ATOL, rtol=RTOL, equal_nan=True)
    for f, fid in enumerate(on.fixture_ids):
        selected = [e for e in events if e['fixture_id'] == fid]
        if selected[0]['kind'] == 'fixture_unavailable':
            assert len(selected) == 1 and selected[0]['expected_path_count'] is None
            assert selected[0]['missing_reason'] and np.isnan(on.ppfd_umol_m2_s[f]).all()
            continue
        ecount = len(args[1][f].emitters.positions_grow_mm)
        assert selected[0]['path_start'] == 0 and selected[-1]['path_stop'] == len(args[0].points_grow_mm) * ecount
        for left, right in zip(selected, selected[1:]): assert left['path_stop'] == right['path_start']
        total = np.zeros(len(args[0].points_grow_mm)); upper = np.zeros_like(total)
        for e in selected:
            assert e['path_stop']-e['path_start'] <= chunk
            ids = np.arange(e['path_start'], e['path_stop'])
            np.testing.assert_array_equal(e['receiver_index'], ids // ecount)
            np.testing.assert_array_equal(e['emitter_index'], ids % ecount)
            q = e['incident_ppfd_umol_m2_s']; u = e['arrival_unit_grow_xyz']; i = e['receiver_index']
            np.testing.assert_array_equal(np.isfinite(q), e['ppfd_valid'])
            np.add.at(total, i, q)
            positive = np.einsum('ij,ij->i', u, args[0].unit_normals[i]) > 0
            np.add.at(upper, i, np.where(positive, q, 0))
        np.testing.assert_allclose(total, on.ppfd_umol_m2_s[f], atol=ATOL, rtol=RTOL, equal_nan=True)
        np.testing.assert_allclose(upper, on.upper_side_ppfd_umol_m2_s[f], atol=ATOL, rtol=RTOL, equal_nan=True)
    return on, events


def moments(events):
    chunks = [e for e in events if e['kind'] == 'paths']
    q = np.concatenate([e['incident_ppfd_umol_m2_s'] for e in chunks])
    u = np.concatenate([e['arrival_unit_grow_xyz'] for e in chunks])
    return q.sum(), np.einsum('i,ij->j', q, u), np.einsum('i,ij,ik->jk', q, u, u)


@pytest.mark.parametrize('mode', ['single', 'multiple', 'asymmetric', 'opposing', 'zero', 'missing_fixture', 'unknown_tau', 'opaque', 'crossing'])
def test_actual_off_on_and_received_positive_normal_path_parity(mode):
    lamps = [point_fixture_payload(length_mm=600, emitter_grid=(5, 1))] if mode == 'multiple' else [point_fixture_payload()]
    if mode in ('asymmetric', 'opposing'):
        lamps.append(point_fixture_payload('below', center_mm=(0, 0, -1000), aim_tilt_deg=180,
                                           photon_flux_umol_s=100 if mode == 'opposing' else 30))
    if mode == 'zero': lamps = [point_fixture_payload(photon_flux_umol_s=0)]
    if mode == 'missing_fixture': lamps = [point_fixture_payload(photon_flux_umol_s=None)]
    args = case(lamps, tau=None if mode in ('unknown_tau', 'opaque') else .1)
    if mode in ('unknown_tau', 'opaque', 'crossing'): args = (*args[:2], surface(leaf=mode != 'opaque'), *args[3:])
    value, events = run(args)
    if mode == 'unknown_tau':
        assert np.isnan(value.ppfd_umol_m2_s).all()
        assert all(e['missing_reason'][0] == 'leaf_transmittance_unavailable' for e in events)
    if mode in ('zero', 'opaque'): assert (value.ppfd_umol_m2_s == 0).all()
    if mode == 'crossing':
        clear = direct_light(args[0], args[1], Occluders.none(), args[3], args[4])
        # Two triangles on the same physical leaf attenuate once even on the shared edge.
        np.testing.assert_allclose(value.ppfd_umol_m2_s, clear.ppfd_umol_m2_s * .1, atol=ATOL, rtol=RTOL)


def test_multi_emitter_second_moment_is_not_lamp_center_direction():
    args = case([point_fixture_payload(length_mm=1000., emitter_grid=(4, 1))])
    args = (replace(args[0], points_grow_mm=np.zeros((1, 3)), unit_normals=np.array([[0., 0., 1.]]), own_triangle=np.array([-1])), *args[1:])
    _, events = run(args, chunk=3)
    f, m, b = moments(events)
    assert f > 0 and b[0, 0] > 0 and m[2] < f
    # A lamp-center approximation would give Bxx=0 and |M|/F=1 here.
    assert np.linalg.norm(m) / f < .999


def test_equal_opposite_actual_sources_cancel_m_not_b():
    args = case([point_fixture_payload(), point_fixture_payload('below', center_mm=(0, 0, -1000), aim_tilt_deg=180)])
    args = (replace(args[0], points_grow_mm=np.zeros((1, 3)), unit_normals=np.array([[0., 0., 1.]]), own_triangle=np.array([-1])), *args[1:])
    _, events = run(args)
    f, m, b = moments(events)
    np.testing.assert_allclose(m, 0, atol=ATOL, rtol=RTOL)
    assert f > 0 and b[2, 2] == pytest.approx(f, abs=ATOL, rel=RTOL)


def test_actual_rotation_inverse_translation_with_original_occluders():
    args = case([point_fixture_payload(length_mm=500, emitter_grid=(4, 1))])
    args = (*args[:2], surface(), *args[3:])
    _, base_events = run(args)
    f, m, b = moments(base_events)
    angle = .63
    r = np.array([[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]])
    shift = np.array([91., -57., 31.])
    def change(args, rotation, offset):
        receivers, fixtures, occluders, tau, settings = args
        receivers = replace(receivers, points_grow_mm=receivers.points_grow_mm @ rotation.T + offset,
                            unit_normals=receivers.unit_normals @ rotation.T)
        fixtures = tuple(replace(s, emitters=replace(s.emitters, positions_grow_mm=s.emitters.positions_grow_mm @ rotation.T + offset,
                                                    aim=rotation @ s.emitters.aim)) for s in fixtures)
        return receivers, fixtures, replace(occluders, vertices_grow_mm=occluders.vertices_grow_mm @ rotation.T + offset), tau, settings
    transformed = change(args, r, shift)
    _, rotated = run(transformed); rf, rm, rb = moments(rotated)
    np.testing.assert_allclose(rf, f, atol=ATOL, rtol=RTOL)
    np.testing.assert_allclose(rm, r @ m, atol=ATOL, rtol=RTOL)
    np.testing.assert_allclose(rb, r @ b @ r.T, atol=ATOL, rtol=RTOL)
    for changed in (change(args, np.eye(3), shift), change(transformed, r.T, -r.T @ shift)):
        _, events = run(changed)
        for actual, wanted in zip(moments(events), (f, m, b)):
            np.testing.assert_allclose(actual, wanted, atol=ATOL, rtol=RTOL)


def test_callback_disabled_skips_diagnostic_helper_and_invalid_budget_rejected(monkeypatch):
    args = case()
    def fail(*args): raise RuntimeError('callback sentinel')
    monkeypatch.setattr(raytrace, '_emit_direction_chunks', fail)
    direct_light(*args)
    for limit in (None, 0, -1, True, 1.5):
        with pytest.raises(ValueError, match='chunk_budget'):
            direct_light(*args, diagnostic_callback=lambda e: None, diagnostic_max_paths_per_chunk=limit)
    with pytest.raises(RuntimeError, match='sentinel'):
        direct_light(*args, diagnostic_callback=lambda e: None, diagnostic_max_paths_per_chunk=1)


def test_borrowed_payload_cannot_mutate_solver_and_callback_error_propagates():
    args = case()
    expected = direct_light(*args)
    def mutate(e):
        with pytest.raises(ValueError): e['incident_ppfd_umol_m2_s'][0] = 0
        with pytest.raises(TypeError): e['fixture_id'] = 'fake'
        # Even deliberate write-flag circumvention only affects diagnostic copies.
        e['incident_ppfd_umol_m2_s'].flags.writeable = True
        e['incident_ppfd_umol_m2_s'][:] = 0
    result = direct_light(*args, diagnostic_callback=mutate, diagnostic_max_paths_per_chunk=1)
    np.testing.assert_allclose(result.ppfd_umol_m2_s, expected.ppfd_umol_m2_s, atol=ATOL, rtol=RTOL)
    def fail(e): raise RuntimeError('consumer rejected chunk')
    with pytest.raises(RuntimeError, match='consumer rejected'):
        direct_light(*args, diagnostic_callback=fail, diagnostic_max_paths_per_chunk=1)


def test_actual_coincident_receiver_and_emitter_is_explicit_known_zero():
    args = case()
    point = args[1][0].emitters.positions_grow_mm[:1].copy()
    receivers = Receivers(point, np.array([[0., 0., 1.]]), True, np.array([-1]))
    value, events = run((receivers, *args[1:]))
    assert value.ppfd_umol_m2_s[0, 0] == 0
    assert events[0]['ppfd_valid'].tolist() == [True]
    assert events[0]['direction_valid'].tolist() == [False]
    assert events[0]['direction_missing_reason'] == ('coincident_receiver_emitter',)


def test_actual_beam_exclusion_keeps_zero_path_and_geometric_direction():
    args = case([point_fixture_payload(cutoff_deg=30.)])
    rec = Receivers(np.array([[2000.,0.,0.]]),np.array([[0.,0.,1.]]),True,np.array([-1]))
    value, events = run((rec,*args[1:]))
    assert value.ppfd_umol_m2_s[0,0] == 0
    assert events[0]['expected_path_count'] == 1
    assert events[0]['ppfd_valid'].tolist() == [True]
    assert events[0]['direction_valid'].tolist() == [True]
    assert events[0]['missing_reason'] == (None,)


def test_actual_own_triangle_exclusion_and_other_background_remains():
    args = case(tau=0.)
    # Explicit self index excludes only that triangle; a distinct opaque background remains.
    vertices = np.array([[[-300., -300., 500.], [300., -300., 500.], [0., 300., 500.]]])
    own = Occluders(vertices, np.array([True]), np.array([0]), np.array([0]))
    rec = Receivers(np.array([[0., 0., 0.]]), np.array([[0., 0., 1.]]), True, np.array([0]))
    clear, _ = run((rec, args[1], own, *args[3:]))
    assert clear.ppfd_umol_m2_s[0, 0] > 0
    blocked = Occluders(np.concatenate([vertices, vertices + [0., 0., 100.]]),
                        np.array([True, False]), np.array([0, 1]), np.array([0, 1]))
    value, _ = run((rec, args[1], blocked, *args[3:]))
    assert value.ppfd_umol_m2_s[0, 0] == 0
