"""Adopted protocol unit tests with supplied chunks; actual transport tests are separate."""
from copy import deepcopy

import numpy as np
import pytest

from tomato3d.light.raytrace import DirectLight
from tools.leaf_light.common import StudyError
from tools.light_direction_diagnostics import DirectionCollector, PROTOCOL


def sink(inventory=None, areas=(2.,), normals=None, **limits):
    return DirectionCollector(inventory or {'led': 2},
        normals if normals is not None else [[0., 0., 1.]] * len(areas), areas,
        **dict(dict(max_paths=100, max_chunk_paths=20, max_receiver_fixture_pairs=20), **limits))


def chunk(q=(3., 1.), u=((0., 0., 1.), (0., 0., -1.)), *, start=0, emitters=2,
          receivers=1, fixture='led'):
    q = np.array(q, dtype=float)
    u = np.array(u, dtype=float)
    ids = np.arange(start, start + len(q))
    valid = np.isfinite(q)
    direction_valid = np.linalg.norm(u, axis=1) > 0
    return dict(protocol=PROTOCOL, kind='paths', fixture_id=fixture,
        receiver_count=receivers, emitter_count=emitters, expected_path_count=receivers * emitters,
        path_start=start, path_stop=start + len(q), receiver_index=ids // emitters,
        emitter_index=ids % emitters, incident_ppfd_umol_m2_s=q, arrival_unit_grow_xyz=u,
        ppfd_valid=valid, direction_valid=direction_valid,
        missing_reason=[None if ok else 'leaf_transmittance_unavailable' for ok in valid],
        direction_missing_reason=[None if ok else 'coincident_receiver_emitter' for ok in direction_valid])


def reference(total=((4.,),), upper=((3.,),), ids=('led',)):
    return DirectLight(ids, np.asarray(total), np.asarray(total), np.asarray(upper))


def test_asymmetric_flux_first_second_and_upper_side():
    collector = sink()
    collector(chunk())
    result = collector.finish(reference())
    assert result.flux_umol_s.tolist() == [[8.]]
    assert result.first_umol_s.tolist() == [[[0., 0., 4.]]]
    assert result.second_umol_s.tolist() == [[[0., 0., 0., 0., 0., 8.]]]
    assert result.unknown_path_count.tolist() == [[0]]


def test_opposing_sources_retain_second_moment_and_known_zero_is_not_unknown():
    collector = sink()
    collector(chunk(q=(3., 3.)))
    result = collector.finish(reference(total=((6.,),)))
    assert result.first_umol_s.tolist() == [[[0., 0., 0.]]]
    assert result.second_umol_s[0, 0, 5] == 12
    zero = sink({'led': 1})
    zero(chunk(q=(0.,), u=((0., 0., 0.),), emitters=1))
    result = zero.finish(reference(((0.,),), ((0.,),)))
    assert result.flux_umol_s[0, 0] == 0
    assert result.first_missing_reason == ((None,),)


@pytest.mark.parametrize('unknown_above', [True, False])
def test_unknown_attenuation_preserves_known_geometry_and_strict_missingness(unknown_above):
    collector = sink()
    q = (np.nan, 1.) if unknown_above else (3., np.nan)
    collector(chunk(q=q))
    upper = np.nan if unknown_above else 3.
    result = collector.finish(reference(((np.nan,),), ((upper,),)))
    assert np.isnan(result.flux_umol_s).all()
    assert np.isnan(result.first_umol_s).all()
    assert np.isnan(result.second_umol_s).all()
    assert result.unknown_path_count[0, 0] == 1
    assert result.first_missing_reason == (('leaf_transmittance_unavailable',),)


def test_unknown_fixture_needs_explicit_event_not_empty_zero_inventory():
    collector = sink({'unknown': None})
    event = dict(protocol=PROTOCOL, kind='fixture_unavailable', fixture_id='unknown', receiver_count=1,
                 emitter_count=None, expected_path_count=None, missing_reason='fixture_emitters_unavailable')
    collector(event)
    result = collector.finish(reference(((np.nan,),), ((np.nan,),), ('unknown',)))
    assert np.isnan(result.flux_umol_s).all()
    assert result.unknown_path_count[0, 0] == -1
    collector = sink({'unknown': None})
    with pytest.raises(StudyError, match='missing_direction_paths_or_fixture'):
        collector.finish(reference())
    collector = sink({'unknown': None})
    collector(event)
    with pytest.raises(StudyError, match='duplicate_unavailable'):
        collector(event)
    incomplete = dict(event)
    del incomplete['expected_path_count']
    with pytest.raises(StudyError, match='invalid_or_duplicate_unavailable'):
        sink({'unknown': None})(incomplete)


def test_chunk_boundary_crossing_receivers_and_reused_buffers():
    collector = sink(areas=(2., 3.))
    # First chunk ends in the middle of receiver 1's path inventory.
    a = chunk(q=(3., 1., 2.), u=((0, 0, 1), (0, 0, -1), (0, 0, 1)), receivers=2)
    collector(a)
    a['incident_ppfd_umol_m2_s'][:] = 900
    a['arrival_unit_grow_xyz'][:] = 0
    collector(chunk(q=(4.,), u=((0, 0, -1),), start=3, receivers=2))
    result = collector.finish(reference(((4., 6.),), ((3., 2.),)))
    assert result.flux_umol_s.tolist() == [[8., 18.]]
    assert result.first_umol_s[0, :, 2].tolist() == [4., -6.]
    assert result.second_umol_s[0, :, 5].tolist() == [8., 18.]
    with pytest.raises(StudyError, match='closed'):
        collector(a)


def test_interleaved_fixture_chunks_stay_separate():
    collector = sink({'a': 2, 'b': 1})
    collector(chunk(q=(3.,), u=((0, 0, 1),), fixture='a'))
    collector(chunk(q=(4.,), u=((1, 0, 0),), emitters=1, fixture='b'))
    collector(chunk(q=(1.,), u=((0, 0, -1),), start=1, fixture='a'))
    result = collector.finish(reference(((4.,), (4.,)), ((3.,), (0.,)), ('a', 'b')))
    assert result.flux_umol_s.tolist() == [[8.], [8.]]
    assert result.first_umol_s.tolist() == [[[0., 0., 4.]], [[8., 0., 0.]]]


@pytest.mark.parametrize('mode', ['leading_gap', 'duplicate', 'trailing_gap', 'whole_fixture'])
def test_missing_and_duplicate_paths_fail_closed(mode):
    collector = sink({'led': 2, 'other': 1} if mode == 'whole_fixture' else None)
    event = chunk(q=(3.,), u=((0, 0, 1),))
    if mode == 'leading_gap':
        event = chunk(q=(1.,), u=((0, 0, -1),), start=1)
    if mode in ('leading_gap', 'duplicate'):
        if mode == 'duplicate':
            collector(event)
        with pytest.raises(StudyError, match='duplicate_missing_or_unordered'):
            collector(event)
        with pytest.raises(StudyError, match='closed'):
            collector.finish(reference())
    else:
        collector(chunk() if mode == 'whole_fixture' else event)
        with pytest.raises(StudyError, match='missing_direction_paths_or_fixture'):
            collector.finish(reference())


@pytest.mark.parametrize('field,value,reason', [
    ('expected_path_count', 3, 'inventory_changed'),
    ('receiver_index', [1, 1], 'unstable_global'),
    ('emitter_index', [0., 1.], 'unstable_global'),
    ('ppfd_valid', [True, False], 'invalid_path_ppfd'),
    ('missing_reason', ['fake', None], 'missing_reason_mismatch'),
    ('incident_ppfd_umol_m2_s', [-1., 1.], 'invalid_path_ppfd'),
    ('incident_ppfd_umol_m2_s', [np.inf, 1.], 'invalid_path_ppfd'),
    ('arrival_unit_grow_xyz', [[0, 0, 2], [0, 0, -1]], 'unit_vector'),
    ('direction_valid', [False, True], 'missing_reason_mismatch'),
    ('fixture_id', 'all', 'foreign_direction'),
    ('path_start', True, 'invalid_path_start'),
])
def test_invalid_payload_is_not_recoverable(field, value, reason):
    collector = sink()
    event = chunk()
    event[field] = value
    with pytest.raises(StudyError, match=reason):
        collector(event)
    with pytest.raises(StudyError, match='closed'):
        collector(chunk())


@pytest.mark.parametrize('total,upper', [(5., 3.), (4., 2.), (np.nan, 3.), (4., np.nan)])
def test_parity_rejects_values_and_missingness_disagreements(total, upper):
    collector = sink()
    collector(chunk())
    with pytest.raises(StudyError, match='transport_parity_failed'):
        collector.finish(reference(((total,),), ((upper,),)))


def test_budget_guards_and_storage_does_not_grow_with_emitter_count():
    with pytest.raises(StudyError, match='resource_budget'):
        sink(max_paths=1)
    with pytest.raises(StudyError, match='resource_budget'):
        sink(areas=(1., 1.), max_receiver_fixture_pairs=1)
    collector = sink(max_chunk_paths=1)
    with pytest.raises(StudyError, match='chunk_budget'):
        collector(chunk())
    # An explicitly bounded stream of 1000 paths retains only per-receiver sums.
    collector = sink({'led': 1000}, max_paths=1000, max_chunk_paths=1)
    for start in range(1000):
        collector(chunk(q=(1.,), u=((0, 0, 1),), emitters=1000, start=start))
    result = collector.finish(reference(((1000.,),), ((1000.,),)))
    assert result.flux_umol_s[0, 0] == 2000
    small = sink()
    assert collector._totals.nbytes == small._totals.nbytes


def test_protocol_rotation_covariance_without_point_translation():
    # Translation is absent from the callback vector contract; this tests only
    # sink covariance, not the missing producer's translation invariance.
    rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
    original = chunk(q=(3., 1.), u=((1, 0, 0), (0, 1, 0)))
    rotated = deepcopy(original)
    rotated['arrival_unit_grow_xyz'] = original['arrival_unit_grow_xyz'] @ rotation.T
    outputs = []
    for event in (original, rotated):
        collector = sink()
        collector(event)
        outputs.append(collector.finish(reference(((4.,),), ((0.,),))))
    np.testing.assert_allclose(outputs[1].first_umol_s[0, 0], rotation @ outputs[0].first_umol_s[0, 0], atol=1e-10, rtol=1e-9)
    assert outputs[0].second_umol_s[0, 0, [0, 3]].tolist() == [6., 2.]
    assert outputs[1].second_umol_s[0, 0, [0, 3]].tolist() == [2., 6.]
