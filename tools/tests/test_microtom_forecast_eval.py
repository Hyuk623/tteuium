"""Rolling-origin evaluation, observation linkage, leakage and baseline preconditions (software criteria only)."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools import microtom_forecast as mf
from tools import microtom_forecast_eval as fe
from tools import microtom_forecast_io as fio
from tools.vtc_growth_io import ROOT, ContractError, read_json, rows, write_csv

ACCEPTANCE = ROOT / 'build' / 'vtc_dev_v3_acceptance_01'
RESULT_RUNS = [ACCEPTANCE / 'sufficient', ACCEPTANCE / 'three_pairs']


def _root() -> Path:
    return ROOT / 'build' / ('microtom_eval_test_' + uuid.uuid4().hex)


@pytest.fixture
def issued() -> Path:
    if not all((r / 'results' / 'manifest.json').exists() for r in RESULT_RUNS):
        pytest.skip('verified V3 acceptance results absent')
    s = mf.default_scenario('seed_route', horizons_days=[1, 3], members=2, seed=11, rays=300000, diagnostic=True)
    s['lights_on_clock_time'] = '06:00'  # declared for the test so the phase is defined
    return mf.issue(s, out_root=_root(), date='20261011', existing_results=RESULT_RUNS)


def _boundary(manifest: dict, h: int) -> datetime:
    return fe.boundary_time(manifest, h)


def _obs(vid, t, quantity, unit, value, role='target', ref='synthetic_truth', phase='0', plant='p1'):
    return dict(observed_vertex_id=vid, plant_id=plant, capture_id='cap_' + t.strftime('%Y%m%dT%H%M'), observed_at=t.isoformat(),
                time_since_lights_on_min=phase, photoperiod_phase='lights_on', quantity=quantity, unit=unit, value=value,
                reference_status=ref, role=role)


def test_preconditions_blocked_today_and_runnable_with_admissible_history(tmp_path):
    blocked = fe.check_preconditions(dict(frame='plant_local_mm', scale_status='unavailable', identity_status='model_generated',
                                          repeated_observations=0, lights_on_clock_time=None, history=None))
    assert [c['status'] for c in blocked] == ['blocked'] * 4 + ['limitation', 'blocked']
    assert all(c['reference'].startswith('tools/compound_growth.py::') for c in blocked)
    result = fe.run_baselines(tmp_path / 'b1', dict(frame='plant_local_mm', scale_status='unavailable', identity_status='model_generated',
                                                    repeated_observations=0, lights_on_clock_time=None, history=None))
    assert result['status'].startswith('blocked_by_preconditions') and result['models'] == {}
    assert len(rows(tmp_path / 'b1' / 'preconditions.csv')) == 6
    from tools.tests.test_compound_growth import state  # synthetic board-frame history (confirmed identity, mm)
    history = [state(0), state(1, angle=5, length=11)]
    result = fe.run_baselines(tmp_path / 'b2', dict(frame='board_mm', scale_status='solved', identity_status='confirmed', repeated_observations=2,
                                                    lights_on_clock_time='06:00', history=history), horizons_days=[1],
                              model_parameters=dict(max_horizon_days=3, provenance='synthetic_fixture'))
    assert result['status'].startswith('run_via_compound_growth.forecast')
    assert set(result['models']) == {'persistence', 'recent_change'}
    for model, out in result['models'].items():
        assert out['schema'] == 'compound-forecast-1' and out['validated_growth'] is False
        assert out['predictions'][0]['status'] == 'diagnostic_forecast' and out['predictions'][0]['state']['eligible_state'] is False


def test_link_observation_is_append_only_and_outside_namespace(issued):
    fid = next(r['forecast_id'] for r in fio.read_table(issued / 'forecast_intervals.csv', fio.INTERVAL_COLUMNS) if r['forecast_id'].endswith(':p1/Plant'))
    m = read_json(issued / 'manifest.json'); t = _boundary(m, 1)
    n = fe.link_observation(issued, [dict(forecast_id=fid, observed_vertex_id='obs:p1', observed_at=t.isoformat(), observed_capture_id='c1')], 'test')
    assert n == 1
    before = (issued / 'forecast_map.csv').read_bytes()
    assert fe.link_observation(issued, [dict(forecast_id=fid, observed_vertex_id='obs:p1', observed_at=t.isoformat())], 'test') == 0
    fe.link_observation(issued, [dict(forecast_id=fid, observed_vertex_id='obs:p1b', observed_at=t.isoformat())], 'test')
    after = (issued / 'forecast_map.csv').read_bytes()
    assert after.startswith(before) and len(rows(issued / 'forecast_map.csv')) == 2
    fio.verify_forecast(issued)  # the map is append-only and excluded from the frozen set
    with pytest.raises(ContractError):
        fe.link_observation(issued, [dict(forecast_id=fid, observed_vertex_id=fid, observed_at=t.isoformat())], 'test')
    with pytest.raises(ContractError, match='unknown forecast_id'):
        fe.link_observation(issued, [dict(forecast_id='F:nope:x', observed_vertex_id='obs:z', observed_at=t.isoformat())], 'test')


def test_evaluate_uses_only_later_phase_matched_linked_observations(issued, tmp_path):
    m = read_json(issued / 'manifest.json')
    iv = {(r['forecast_id'].rsplit(':', 1)[1], r['quantity'], int(r['horizon_day'])): r for r in fio.read_table(issued / 'forecast_intervals.csv', fio.INTERVAL_COLUMNS)}
    fid = 'F:' + m['forecast_run_id'] + ':p1/Plant'
    t1, t3 = _boundary(m, 1), _boundary(m, 3)
    fe.link_observation(issued, [dict(forecast_id=fid, observed_vertex_id='obs:p1', observed_at=t1.isoformat())], 'test')
    inside = float(iv[('p1/Plant', 'compounds', 1)]['point'])
    high3 = float(iv[('p1/Plant', 'stem_length_mm', 3)]['interval_high'])
    observations = [
        _obs('obs:p1', t1, 'compounds', 'count', inside),                      # covered
        _obs('obs:p1', t3, 'stem_length_mm', 'mm', high3 + 100),               # not covered, abs error 100 above point? (>= high)
        _obs('obs:p1', t3, 'event_count:new_compound', 'count', 1),           # count error
        _obs('obs:p1', t3, 'event_time:apex_stop', 'day', 2),                 # event never occurred -> unavailable
        _obs('obs:p1', t1, 'compounds', 'count', inside, phase='300'),         # phase mismatch -> unavailable
        _obs('obs:p1', t1 + timedelta(hours=5), 'compounds', 'count', inside),  # not a boundary -> unavailable
        _obs('obs:p1', _boundary(m, 0), 'compounds', 'count', inside),       # at/before issue -> unavailable
        _obs('obs:p2', t1, 'compounds', 'count', inside, plant='p2'),          # unlinked -> unavailable
        _obs('obs:p1', _boundary(m, -2), 'compounds', 'count', 7, role='input'),  # legitimate input before issue
    ]
    write_csv(tmp_path / 'obs.csv', observations, list(fe.OBSERVATION_COLUMNS))
    summary = fe.evaluate(issued, tmp_path / 'obs.csv', ROOT / 'build' / ('microtom_eval_out_' + uuid.uuid4().hex))
    assert summary['leakage']['passed'] and summary['leakage']['leaked_inputs'] == 0
    assert summary['interval_coverage'] == dict(n=2, mean=0.5)
    assert summary['count_error']['n'] == 1 and summary['event_timing_error_days']['n'] == 0
    assert summary['evaluation_status'] == 'evaluated_unaccepted' and summary['growth_accuracy_status'] == 'software_check_only_synthetic_truth'
    reasons = ' '.join(summary['unavailable_reasons'])
    assert 'phase differs' in reasons and 'not a forecast boundary' in reasons and 'not after issue' in reasons and 'no correspondence' in reasons
    assert 'accepted_for_domain' not in str(summary)


def test_leakage_detected_and_deletion_equivalence(issued, tmp_path):
    m = read_json(issued / 'manifest.json'); t1 = _boundary(m, 1)
    fid = 'F:' + m['forecast_run_id'] + ':p1/Plant'
    fe.link_observation(issued, [dict(forecast_id=fid, observed_vertex_id='obs:p1', observed_at=t1.isoformat())], 'test')
    base = [_obs('obs:p1', t1, 'trusses', 'count', 0)]
    early_inputs = [_obs('obs:p1', _boundary(m, -5), 'compounds', 'count', 6, role='input'), _obs('obs:p1', _boundary(m, -1), 'compounds', 'count', 8, role='input')]
    write_csv(tmp_path / 'a.csv', base, list(fe.OBSERVATION_COLUMNS))
    write_csv(tmp_path / 'b.csv', base + early_inputs, list(fe.OBSERVATION_COLUMNS))
    out_a = fe.evaluate(issued, tmp_path / 'a.csv', ROOT / 'build' / ('microtom_eval_out_' + uuid.uuid4().hex))
    out_b = fe.evaluate(issued, tmp_path / 'b.csv', ROOT / 'build' / ('microtom_eval_out_' + uuid.uuid4().hex))
    drop = ('evaluated_at',)
    assert {k: v for k, v in out_a.items() if k not in drop and k != 'leakage'} == {k: v for k, v in out_b.items() if k not in drop and k != 'leakage'}
    write_csv(tmp_path / 'c.csv', base + [_obs('obs:p1', t1, 'compounds', 'count', 9, role='input')], list(fe.OBSERVATION_COLUMNS))
    with pytest.raises(ContractError, match='future information'):
        fe.evaluate(issued, tmp_path / 'c.csv', ROOT / 'build' / ('microtom_eval_out_' + uuid.uuid4().hex))
    # the forecast itself never read an observation: its snapshot is the frozen member input set
    assert m['input_snapshot_kind'] == 'seed_route_frozen_inputs' and len(m['input_snapshot_sha256']) == 64


def test_phase_unavailable_makes_every_comparison_unavailable(tmp_path):
    if not all((r / 'results' / 'manifest.json').exists() for r in RESULT_RUNS):
        pytest.skip('verified V3 acceptance results absent')
    s = mf.default_scenario('seed_route', horizons_days=[1], members=2, seed=11, rays=300000, diagnostic=True)  # lights-on unknown (today's records)
    folder = mf.issue(s, out_root=_root(), date='20261011', existing_results=RESULT_RUNS)
    m = read_json(folder / 'manifest.json'); t1 = _boundary(m, 1)
    fid = 'F:' + m['forecast_run_id'] + ':p1/Plant'
    fe.link_observation(folder, [dict(forecast_id=fid, observed_vertex_id='obs:p1', observed_at=t1.isoformat())], 'test')
    write_csv(tmp_path / 'o.csv', [_obs('obs:p1', t1, 'compounds', 'count', 9)], list(fe.OBSERVATION_COLUMNS))
    summary = fe.evaluate(folder, tmp_path / 'o.csv', ROOT / 'build' / ('microtom_eval_out_' + uuid.uuid4().hex))
    assert summary['n_scored'] == 0 and any('diurnal_confound' in r for r in summary['unavailable_reasons'])


def test_observation_table_rejects_forecast_namespace_ids(tmp_path):
    t = datetime(2026, 11, 1, 6, tzinfo=timezone(timedelta(hours=9)))
    write_csv(tmp_path / 'o.csv', [_obs('F:forecast_20261011_01:p1/Plant', t, 'compounds', 'count', 9)], list(fe.OBSERVATION_COLUMNS))
    with pytest.raises(ContractError, match='namespace'):
        fe.load_observations(tmp_path / 'o.csv')
    write_csv(tmp_path / 'o2.csv', [dict(_obs('obs:x', t, 'compounds', 'count', 9), observed_at='2026-11-01T06:00:00')], list(fe.OBSERVATION_COLUMNS))
    with pytest.raises(ContractError, match='aware'):
        fe.load_observations(tmp_path / 'o2.csv')
