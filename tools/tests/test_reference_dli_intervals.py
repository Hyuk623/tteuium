"""Explicit synthetic support tests; these do not establish real sensor accuracy."""
from copy import deepcopy

import pytest

from tools.compound_growth import aware_time
from tools.leaf_light.common import StudyError
from tools.reference_dli_contract import Missing
from tools.reference_dli_intervals import dated_schedule, daily_logged, daily_spot, logged_intervals

ABS = 1e-12
REL = 1e-12


def inputs(zone='Asia/Seoul', dates=None, start='06:00', end='22:00', fraction=1.):
    dates = dates or ['2026-10-04']
    p = dict(timezone=zone, dates=dates, max_schedule_minutes=10000,
             logger_sample_semantics='instantaneous', max_gap_seconds=3600,
             transition_policy='hold_observed_endpoint_on_each_side',
             transition_source_ref={'path': 'synthetic-policy.json', 'sha256': 'checked_by_caller'},
             ambient_light='none', output_constant=True, output_fraction=fraction,
             measurement_output_fraction=fraction)
    schedule = dict(timezone=zone, dates=dates, provenance={'source': 'synthetic'},
                    fixed_optics_beam_spectrum=True,
                    fixtures={name: [dict(start_hhmm=start, end_hhmm=end, output_fraction=fraction)]
                              for name in ('LED-01', 'LED-02', 'LED-03')})
    return p, schedule


def reading(rid, at, q, state='on', support=None):
    row = dict(reading_id=rid, measured_at=at, time=aware_time(at), ppfd=q, lights_state=state)
    if support:
        row.update(support_start_at=support[0], support_end_at=support[1])
    return row


def hourly():
    return [reading(str(hour), f'2026-10-04T{hour:02}:00:00+09:00',
                    200. if 6 <= hour < 22 else 0., 'on' if 6 <= hour < 22 else 'off')
            for hour in range(24)] + [reading('24', '2026-10-05T00:00:00+09:00', 0., 'off')]


def logged(p, schedule, rows, ids=None):
    return daily_logged(p, rows, ids if ids is not None else {r['reading_id'] for r in rows},
                        dated_schedule(p, schedule, p['dates']))


def test_logged_200_for_16h_has_supported_night_and_no_double_fraction():
    p, s = inputs(fraction=.5)
    day = logged(p, s, hourly())['days']['2026-10-04']
    assert day['coverage_status'] == 'complete'
    assert day['dli_mol_m2_day'] == pytest.approx(11.52, rel=REL, abs=ABS)
    assert day['mean_ppfd_umol_m2_s'] == pytest.approx(200*16/24, rel=REL, abs=ABS)
    assert day['on_duration_s'] == 16*3600


@pytest.mark.parametrize('missing', ['endpoint', 'gap', 'unknown', 'excluded'])
def test_missing_coverage_never_becomes_darkness(missing):
    p, s = inputs()
    rows = hourly()
    ids = {r['reading_id'] for r in rows}
    if missing == 'endpoint': rows.pop()
    if missing == 'gap': rows.pop(12)
    if missing == 'unknown': rows[12]['ppfd'] = None
    if missing == 'excluded': ids.remove('12')
    day = logged(p, s, rows, ids)['days']['2026-10-04']
    assert day['coverage_status'] == 'incomplete'
    assert day['dli_mol_m2_day'] is None
    assert day['gaps']


def test_instantaneous_transition_strictly_inside_interval_is_step_not_ramp():
    p, s = inputs()
    p['max_gap_seconds'] = 4*3600
    rows = [reading('a', '2026-10-04T05:00:00+09:00', 0., 'off'),
            reading('b', '2026-10-04T09:00:00+09:00', 200.)]
    pieces, gaps = logged_intervals(p, rows, {'a', 'b'}, dated_schedule(p, s, p['dates']))
    assert not gaps
    assert [x['duration_s'] for x in pieces] == [3600., 3*3600.]
    assert [x['mean_ppfd_umol_m2_s'] for x in pieces] == [0., 200.]
    assert sum(x['mean_ppfd_umol_m2_s']*x['duration_s'] for x in pieces) == 200*3*3600
    assert sum(x['mean_ppfd_umol_m2_s']*x['duration_s'] for x in pieces) != 100*4*3600


def test_interval_mean_crossing_transition_preserves_measured_mean_not_endpoint_ramp():
    p, s = inputs()
    p['logger_sample_semantics'] = 'interval_mean'
    rows = [reading('mean', '2026-10-04T09:00:00+09:00', 60., 'mixed',
                    ('2026-10-04T05:00:00+09:00', '2026-10-04T09:00:00+09:00'))]
    pieces, gaps = logged_intervals(p, rows, {'mean'}, dated_schedule(p, s, p['dates']))
    assert not gaps and len(pieces) == 1
    assert pieces[0]['rule'] == 'interval_mean_step'
    assert pieces[0]['mean_ppfd_umol_m2_s']*pieces[0]['duration_s'] == 60*4*3600


@pytest.mark.parametrize('field', ['transition_policy', 'transition_source_ref'])
def test_transition_needs_declared_observational_support(field):
    p, s = inputs()
    del p[field]
    day = logged(p, s, hourly())['days']['2026-10-04']
    assert day['dli_mol_m2_day'] is None


def test_multiple_unobserved_transitions_cannot_imply_zero_day():
    p, s = inputs()
    p['max_gap_seconds'] = 86400
    rows = [hourly()[0], hourly()[-1]]
    result = logged(p, s, rows)
    assert result['days']['2026-10-04']['dli_mol_m2_day'] is None
    assert result['rejected_intervals'][0]['reason'] == 'unobserved_intermediate_schedule_state'


def test_interval_means_complete_day_and_overlap_refusal():
    p, s = inputs()
    p['logger_sample_semantics'] = 'interval_mean'
    rows = [reading('n1', '2026-10-04T06:00:00+09:00', 0., 'off',
                    ('2026-10-04T00:00:00+09:00', '2026-10-04T06:00:00+09:00')),
            reading('on', '2026-10-04T22:00:00+09:00', 200., 'on',
                    ('2026-10-04T06:00:00+09:00', '2026-10-04T22:00:00+09:00')),
            reading('n2', '2026-10-05T00:00:00+09:00', 0., 'off',
                    ('2026-10-04T22:00:00+09:00', '2026-10-05T00:00:00+09:00'))]
    assert logged(p, s, rows)['days']['2026-10-04']['dli_mol_m2_day'] == pytest.approx(11.52, rel=REL, abs=ABS)
    rows[1]['support_start_at'] = '2026-10-04T05:00:00+09:00'
    with pytest.raises(StudyError, match='overlapping_interval_mean_support'):
        logged(p, s, rows)


def test_mean_cannot_be_partitioned_across_midnight_without_evidence():
    p, s = inputs()
    p['logger_sample_semantics'] = 'interval_mean'
    rows = [reading('wide', '2026-10-05T01:00:00+09:00', 100., 'mixed',
                    ('2026-10-03T23:00:00+09:00', '2026-10-05T01:00:00+09:00'))]
    assert logged(p, s, rows)['days']['2026-10-04']['dli_mol_m2_day'] is None
    p.update(interval_mean_split_policy='constant_within_supported_interval',
             interval_mean_split_source_ref={'path': 'synthetic', 'sha256': 'caller_checks'})
    assert logged(p, s, rows)['days']['2026-10-04']['dli_mol_m2_day'] == pytest.approx(8.64, rel=REL, abs=ABS)


def test_missing_semantics_and_support_are_named():
    p, s = inputs()
    del p['logger_sample_semantics']
    with pytest.raises(Missing, match='logger_sample_semantics_missing'): logged(p, s, hourly())
    p['logger_sample_semantics'] = 'interval_mean'
    with pytest.raises(Missing, match='interval_mean_support_missing'): logged(p, s, hourly())


@pytest.mark.parametrize('zone,date,hours,offset', [
    ('America/New_York', '2026-03-08', 23, '-04:00'),
    ('America/New_York', '2026-11-01', 25, '-05:00'),
    ('Asia/Seoul', '2026-10-04', 24, '+09:00')])
def test_actual_elapsed_dst_day_is_used(zone, date, hours, offset):
    p, s = inputs(zone=zone, dates=[date], start='00:00', end='24:00')
    t = dated_schedule(p, s, p['dates'])
    assert t['days'][date]['duration_s'] == hours*3600
    result = daily_spot(p, [reading('on', date+'T12:00:00'+offset, 200.)], t)
    assert result['days'][date]['dli_mol_m2_day'] == pytest.approx(200*hours*3600e-6, rel=REL, abs=ABS)


def test_midnight_crossing_schedule_uses_declared_timezone():
    p, s = inputs(start='22:00', end='14:00')
    t = dated_schedule(p, s, p['dates'])
    row = reading('on', '2026-10-04T03:00:00+09:00', 200.)
    result = daily_spot(p, [row], t)['days']['2026-10-04']
    assert result['on_duration_s'] == 16*3600
    assert result['dli_mol_m2_day'] == pytest.approx(11.52, rel=REL, abs=ABS)


def test_spot_mean_and_target_fraction_are_not_doubled():
    p, s = inputs(fraction=.5)
    rows = [reading('a', '2026-10-04T12:00:00+09:00', 190.),
            reading('b', '2026-10-04T12:00:30+09:00', 210.),
            reading('off', '2026-10-04T01:00:00+09:00', 0., 'off')]
    result = daily_spot(p, rows, dated_schedule(p, s, p['dates']))
    day = result['days']['2026-10-04']
    assert day['n_readings'] == 2
    assert day['mean_ppfd_umol_m2_s'] == 200.
    assert day['dli_mol_m2_day'] == pytest.approx(11.52, rel=REL, abs=ABS)
    assert result['output_scaling']['factor'] == 1.


def test_explicit_full_output_to_target_scaling_once():
    p, s = inputs(fraction=.5)
    p['measurement_output_fraction'] = 1.
    row = reading('on', '2026-10-04T12:00:00+09:00', 200.)
    t = dated_schedule(p, s, p['dates'])
    with pytest.raises(Missing, match='fractional_measurement_normalization_unsupported'):
        daily_spot(p, [row], t)
    p['dimming_response'] = 'linear_photon_output'
    with pytest.raises(Missing, match='dimming_response_evidence_missing'): daily_spot(p, [row], t)
    p['dimming_source_ref'] = {'path': 'synthetic', 'sha256': 'checked_by_caller'}
    assert daily_spot(p, [row], t)['days']['2026-10-04']['dli_mol_m2_day'] == pytest.approx(5.76, rel=REL, abs=ABS)


@pytest.mark.parametrize('change', ['constant', 'ambient', 'conflict', 'no_clocks', 'no_dates', 'budget'])
def test_spot_unestablished_inputs_refused(change):
    p, s = inputs()
    if change == 'constant': p['output_constant'] = None
    if change == 'ambient': p['ambient_light'] = None
    if change == 'conflict': s['fixtures']['LED-01'][0]['output_fraction'] = .5
    if change == 'no_clocks': s['fixtures']['LED-01'][0]['start_hhmm'] = None
    if change == 'no_dates': s['dates'] = []
    if change == 'budget': p['max_schedule_minutes'] = 1
    with pytest.raises(StudyError):
        daily_spot(p, [reading('on', '2026-10-04T12:00:00+09:00', 200.)], dated_schedule(p, s, p['dates']))


def test_spot_never_reuses_another_day_or_a_lights_off_time():
    p, s = inputs(dates=['2026-10-04', '2026-10-05'])
    t = dated_schedule(p, s, p['dates'])
    result = daily_spot(p, [reading('on', '2026-10-04T12:00:00+09:00', 200.)], t)
    assert result['days']['2026-10-05']['dli_mol_m2_day'] is None
    with pytest.raises(Missing, match='spot_lights_state_schedule_conflict'):
        daily_spot(p, [reading('bad', '2026-10-04T03:00:00+09:00', 200.)], t)
