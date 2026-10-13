"""Measured interval adapters using the existing light schedule and photon arithmetic.

All timestamps are elapsed UTC internally. No endpoint extrapolation, gap filling,
lamp-output normalization, or inference of darkness is performed here.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any
from zoneinfo import ZoneInfo

from tools.compound_growth import aware_time
from tools.leaf_light.common import StudyError
from tools.light_time import _fraction, _schedules, photon_integral, schedule_boundaries
from tools.reference_dli_contract import Missing, day_bounds, number, require


def dated_schedule(position: dict, schedule: dict, dates: list[str]) -> dict:
    """Adapt explicitly dated HH:MM windows; daily duration alone is not a schedule."""
    if schedule.get('timezone') != position.get('timezone'):
        raise StudyError('reference_schedule_timezone_mismatch')
    requested = set(dates)
    declared = schedule.get('dates')
    if not isinstance(declared, list) or not requested.issubset(declared):
        raise Missing('dated_schedule_missing')
    raw = schedule.get('fixtures')
    if not isinstance(raw, dict) or not raw or any(v is None for v in raw.values()):
        raise Missing('fixture_schedule_missing')
    if any(not seg.get('start_hhmm') or not seg.get('end_hhmm')
           for segments in raw.values() for seg in segments):
        raise Missing('clock_windows_missing')
    zone, fixtures = _schedules(schedule)
    budget = position.get('max_schedule_minutes')
    if type(budget) is not int or budget <= 0:
        raise Missing('schedule_resource_budget_missing')
    used = 0
    days = {}
    for local_date in dates:
        start, end = day_bounds(local_date, zone)
        used += math.ceil((end-start).total_seconds()/60) + 1
        if used > budget:
            raise StudyError('schedule_scan_budget_exceeded')
        edges = sorted(schedule_boundaries(start, end, zone, fixtures, budget))
        intervals = []
        for a, b in zip(edges, edges[1:]):
            fractions = {fid: _fraction(a, zone, windows) for fid, windows in fixtures.items()}
            intervals.append(dict(start_at=a.isoformat(), end_at=b.isoformat(),
                                  duration_s=(b-a).total_seconds(), fixture_fractions=fractions))
        days[local_date] = dict(start_at=start.isoformat(), end_at=end.isoformat(),
            duration_s=(end-start).total_seconds(), intervals=intervals,
            on_duration_s=math.fsum(r['duration_s'] for r in intervals
                                   if any(v > 0 for v in r['fixture_fractions'].values())))
    return dict(timezone=zone.key, days=days, scanned_minutes=used,
                fixture_windows=fixtures)


def mean_support_timeline(position: dict, dates: list[str], schedule_reason: str) -> dict:
    """Measured interval means establish their own support without lamp clocks.

    No lamp on-duration is inferred. Instantaneous reconstruction cannot use this
    adapter because unknown switch times cannot establish transition support.
    """
    if position.get('logger_sample_semantics') != 'interval_mean':
        raise Missing(schedule_reason)
    zone = ZoneInfo(position['timezone'])
    days = {}
    for local_date in dates:
        start, end = day_bounds(local_date, zone)
        days[local_date] = dict(start_at=start.isoformat(), end_at=end.isoformat(),
            duration_s=(end-start).total_seconds(), on_duration_s=None, intervals=[])
    return dict(timezone=zone.key, days=days, scanned_minutes=0, fixture_windows={},
                schedule_status='unavailable', schedule_reason=schedule_reason,
                coverage_source='explicit_measured_interval_support')


def _signature(t: datetime, timeline: dict) -> tuple:
    zone = ZoneInfo(timeline['timezone'])
    return tuple(_fraction(t, zone, windows) for windows in timeline['fixture_windows'].values())


def _transitions(a: datetime, b: datetime, timeline: dict) -> list[datetime]:
    # Include a transition at the right endpoint: the new reading describes the
    # post-transition state and cannot make a ramp in the preceding interval.
    cuts = {aware_time(r['start_at']) for day in timeline['days'].values() for r in day['intervals']}
    cuts.update(aware_time(day['end_at']) for day in timeline['days'].values())
    return sorted(t for t in cuts if a < t <= b
                  and _signature(t-timedelta(microseconds=1), timeline) != _signature(t, timeline))


def _piece(a: datetime, b: datetime, q0: float, q1: float, ids: list[str], rule: str) -> dict:
    return dict(start_at=a.isoformat(), end_at=b.isoformat(), duration_s=(b-a).total_seconds(),
                start_ppfd_umol_m2_s=q0, end_ppfd_umol_m2_s=q1,
                mean_ppfd_umol_m2_s=(q0+q1)/2, reading_ids=ids, rule=rule)


def logged_intervals(position: dict, rows: list[dict], included_ids: set[str],
                     timeline: dict) -> tuple[list[dict], list[dict]]:
    """Retain rejected rows as barriers; never bridge across an excluded sample.

    `interval_mean` rows carry explicit half-open support_start_at/support_end_at.
    `instantaneous` rows reconstruct only adjacent samples under an explicit gap
    policy. A single transition uses evidenced endpoint holds on each side;
    multiple transitions lack intermediate observations and remain unsupported.
    """
    semantics = position.get('logger_sample_semantics')
    if semantics not in ('instantaneous', 'interval_mean'):
        raise Missing('logger_sample_semantics_missing')
    pieces: list[dict] = []
    gaps: list[dict] = []
    if semantics == 'interval_mean':
        supports = []
        for row in rows:
            start = require(row.get('support_start_at'), 'interval_mean_support_missing')
            end = require(row.get('support_end_at'), 'interval_mean_support_missing')
            a, b = aware_time(start), aware_time(end)
            if b <= a or not a <= row['time'] <= b:
                raise StudyError('invalid_interval_mean_support')
            supports.append((a, b, row))
        supports.sort(key=lambda item: item[0])
        if any(left[1] > right[0] for left, right in zip(supports, supports[1:])):
            raise StudyError('overlapping_interval_mean_support')
        for a, b, row in supports:
            if row['reading_id'] not in included_ids or row['ppfd'] is None:
                gaps.append(dict(start_at=a.isoformat(), end_at=b.isoformat(),
                                 reason='excluded_or_unknown_interval', reading_ids=[row['reading_id']]))
                continue
            # An observed interval mean remains the mean over its whole support;
            # transition boundaries do not authorize inventing a within-interval
            # light profile. Complete-day integration is valid, but cutting a mean
            # across midnight requires an explicit representativeness assumption.
            pieces.append(_piece(a, b, row['ppfd'], row['ppfd'], [row['reading_id']], 'interval_mean_step'))
        return pieces, gaps

    maximum = number(require(position.get('max_gap_seconds'), 'max_gap_policy_missing'),
                     'max_gap_seconds', 0)
    if maximum <= 0:
        raise StudyError('max_gap_seconds_must_be_positive')
    for left, right in zip(rows, rows[1:]):
        a, b = left['time'], right['time']
        ids = [left['reading_id'], right['reading_id']]
        if b <= a:
            raise StudyError('ambiguous_duplicate_reading_time')
        reason = None
        if any(r['reading_id'] not in included_ids or r['ppfd'] is None for r in (left, right)):
            reason = 'excluded_or_unknown_adjacent_sample'
        elif (b-a).total_seconds() > maximum:
            reason = 'logger_gap_exceeds_declared_maximum'
        transitions = _transitions(a, b, timeline)
        if reason is None and len(transitions) > 1:
            reason = 'unobserved_intermediate_schedule_state'
        if reason is None and transitions:
            if position.get('transition_policy') != 'hold_observed_endpoint_on_each_side':
                reason = 'transition_support_policy_missing'
            elif not position.get('transition_source_ref'):
                reason = 'transition_support_evidence_missing'
        if reason:
            gaps.append(dict(start_at=a.isoformat(), end_at=b.isoformat(), reason=reason, reading_ids=ids))
            continue
        if transitions:
            t = transitions[0]
            pieces.append(_piece(a, t, left['ppfd'], left['ppfd'], ids, 'transition_left_hold'))
            if t < b:
                pieces.append(_piece(t, b, right['ppfd'], right['ppfd'], ids, 'transition_right_hold'))
        else:
            pieces.append(_piece(a, b, left['ppfd'], right['ppfd'], ids, 'instantaneous_trapezoid'))
    return pieces, gaps


def daily_logged(position: dict, rows: list[dict], included_ids: set[str], timeline: dict) -> dict:
    pieces, rejected = logged_intervals(position, rows, included_ids, timeline)
    result = {}
    for local_date, day in timeline['days'].items():
        a, b = aware_time(day['start_at']), aware_time(day['end_at'])
        selected = []
        gaps = []
        cursor = a
        for piece in pieces:
            x, y = aware_time(piece['start_at']), aware_time(piece['end_at'])
            lo, hi = max(a, x), min(b, y)
            if hi <= lo:
                continue
            if piece['rule'] == 'interval_mean_step' and (lo != x or hi != y):
                if position.get('interval_mean_split_policy') != 'constant_within_supported_interval':
                    gaps.append(dict(start_at=lo.isoformat(), end_at=hi.isoformat(),
                                     reason='interval_mean_midnight_profile_unavailable'))
                    continue
                if not position.get('interval_mean_split_source_ref'):
                    gaps.append(dict(start_at=lo.isoformat(), end_at=hi.isoformat(),
                                     reason='interval_mean_split_evidence_missing'))
                    continue
            fraction0 = (lo-x).total_seconds()/(y-x).total_seconds()
            fraction1 = (hi-x).total_seconds()/(y-x).total_seconds()
            q0, q1 = piece['start_ppfd_umol_m2_s'], piece['end_ppfd_umol_m2_s']
            selected.append(_piece(lo, hi, q0+(q1-q0)*fraction0, q0+(q1-q0)*fraction1,
                                   piece['reading_ids'], piece['rule']))
            if lo > cursor:
                gaps.append(dict(start_at=cursor.isoformat(), end_at=lo.isoformat(), reason='unsupported_coverage'))
            if lo < cursor:
                raise StudyError('overlapping_reconstructed_intervals')
            cursor = hi
        if cursor < b:
            gaps.append(dict(start_at=cursor.isoformat(), end_at=b.isoformat(), reason='unsupported_coverage'))
        complete = not gaps and cursor == b
        integral = photon_integral((p['mean_ppfd_umol_m2_s'], p['duration_s']) for p in selected)
        ids = sorted({rid for p in selected for rid in p['reading_ids']})
        result[local_date] = dict(local_date=local_date, start_at=day['start_at'], end_at=day['end_at'],
            duration_s=day['duration_s'], on_duration_s=day['on_duration_s'],
            coverage_status='complete' if complete else 'incomplete',
            dli_mol_m2_day=integral if complete else None,
            mean_ppfd_umol_m2_s=integral*1e6/day['duration_s'] if complete else None,
            mean_definition='elapsed_full_day_time_weighted_logged_ppfd', n_readings=len(ids),
            included_reading_ids=ids, integration_segments=selected, gaps=gaps,
            reason=None if complete else 'incomplete_logged_coverage')
    return dict(days=result, rejected_intervals=rejected)


def spot_scale(position: dict, timeline: dict) -> dict:
    """Measured-output basis -> target photons exactly once, under explicit evidence."""
    if position.get('ambient_light') != 'none' or position.get('output_constant') is not True:
        raise Missing('spot_schedule_assumption_undeclared')
    measured = number(require(position.get('measurement_output_fraction'),
                              'measurement_output_fraction_missing'), 'measurement_output_fraction', 0)
    target = number(require(position.get('output_fraction'), 'output_fraction_missing'), 'output_fraction', 0)
    if not 0 < measured <= 1 or not 0 < target <= 1:
        raise StudyError('invalid_spot_output_fraction')
    for day in timeline['days'].values():
        for interval in day['intervals']:
            values = list(interval['fixture_fractions'].values())
            if any(v > 0 for v in values) and any(v != target for v in values):
                raise Missing('reference_schedule_output_fraction_conflict')
    if measured == target:
        return dict(factor=1., rule='measured_at_target_output_no_rescaling',
                    measurement_output_fraction=measured, target_output_fraction=target)
    if measured != 1. or position.get('dimming_response') != 'linear_photon_output':
        raise Missing('fractional_measurement_normalization_unsupported')
    if not position.get('dimming_source_ref'):
        raise Missing('dimming_response_evidence_missing')
    return dict(factor=target, rule='declared_linear_full_output_to_target',
                measurement_output_fraction=measured, target_output_fraction=target)


def daily_spot(position: dict, rows: list[dict], timeline: dict) -> dict:
    scale = spot_scale(position, timeline)
    zone = ZoneInfo(timeline['timezone'])
    result = {}
    for local_date, day in timeline['days'].items():
        selected = [r for r in rows if r['time'].astimezone(zone).date().isoformat() == local_date
                    and r['lights_state'] == 'on' and r['ppfd'] is not None]
        for row in selected:
            if not any(_signature(row['time'], timeline)):
                raise Missing('spot_lights_state_schedule_conflict')
        q = math.fsum(r['ppfd'] for r in selected)/len(selected) if selected else None
        segments = []
        if q is not None:
            for interval in day['intervals']:
                on = any(v > 0 for v in interval['fixture_fractions'].values())
                ppfd = q*scale['factor'] if on else 0.
                segments.append(_piece(aware_time(interval['start_at']), aware_time(interval['end_at']),
                    ppfd, ppfd, [r['reading_id'] for r in selected],
                    'spot_mean_scaled_once' if on else 'declared_no_ambient_lights_off_estimate'))
        value = photon_integral((r['mean_ppfd_umol_m2_s'], r['duration_s']) for r in segments) if selected else None
        result[local_date] = dict(local_date=local_date, start_at=day['start_at'], end_at=day['end_at'],
            duration_s=day['duration_s'], on_duration_s=day['on_duration_s'],
            coverage_status='complete' if selected else 'incomplete',
            coverage_basis='schedule_based_estimate_under_declared_assumptions',
            dli_mol_m2_day=value, mean_ppfd_umol_m2_s=q,
            mean_definition='arithmetic_mean_of_accepted_reference_lights_on_spots',
            n_readings=len(selected), included_reading_ids=[r['reading_id'] for r in selected],
            integration_segments=segments, gaps=[], reason=None if selected else 'no_usable_lights_on_readings')
    return dict(days=result, output_scaling=scale)
