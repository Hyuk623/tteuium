"""Read-only reference-channel consumer with independent raw-reading dose arithmetic.

The consumer shares input/evidence policy and the existing schedule contract. It
never calls the producer, daily_logged/daily_spot, or its photon integrator. CSV,
JSON and integration audit values are checked against original hashed readings.
"""
from __future__ import annotations

import argparse
import csv
from datetime import timedelta
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.compound_growth import aware_time
from tools.leaf_light.common import DLI_UNIT, StudyError, file_hash, read_json
from tools.light_time import _fraction
from tools.reference_dli_contract import (Missing, association, dates_and_geometry, evidence,
    read_readings, select_readings, survey_tolerance)
from tools.reference_dli_intervals import dated_schedule, mean_support_timeline, spot_scale
from tools.reference_dli_policy import ambient_evidence, choose_value, domain, sensor_flags

ABS_TOL = 1e-12
REL_TOL = 1e-12


def _same(actual, expected, label: str) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise StudyError('reference_dli_'+label+'_mismatch')
        for key, value in expected.items(): _same(actual[key], value, label+'.'+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise StudyError('reference_dli_'+label+'_mismatch')
        for i, value in enumerate(expected): _same(actual[i], value, label+'.'+str(i))
    elif type(expected) is bool:
        if type(actual) is not bool or actual != expected: raise StudyError('reference_dli_'+label+'_mismatch')
    elif type(expected) in (int, float):
        if type(actual) not in (int, float) or not math.isfinite(actual) or not math.isclose(
                actual, expected, rel_tol=REL_TOL, abs_tol=ABS_TOL):
            raise StudyError('reference_dli_'+label+'_mismatch')
    elif actual != expected:
        raise StudyError('reference_dli_'+label+'_mismatch')


def _raw_logged_day(p: dict, rows: list[dict], accepted: set[str], timeline: dict, day: dict) -> dict:
    start, end = aware_time(day['start_at']), aware_time(day['end_at'])
    spans = []
    semantics = p.get('logger_sample_semantics')
    if semantics == 'interval_mean':
        previous = None
        intervals = sorted((aware_time(r['support_start_at']), aware_time(r['support_end_at']), r) for r in rows)
        for a, b, row in intervals:
            if b <= a or previous is not None and a < previous:
                raise StudyError('reference_dli_invalid_raw_support')
            previous = b
            if row['reading_id'] not in accepted: continue
            x, y = max(start, a), min(end, b)
            if x >= y: continue
            if (x, y) != (a, b) and (p.get('interval_mean_split_policy') != 'constant_within_supported_interval'
                                    or not p.get('interval_mean_split_source_ref')):
                continue
            spans.append((x, y, row['ppfd'], {row['reading_id']}))
    elif semantics == 'instantaneous':
        zone = ZoneInfo(timeline['timezone'])
        windows = timeline['fixture_windows']
        def signature(t): return tuple(_fraction(t, zone, w) for w in windows.values())
        edges = {aware_time(r['start_at']) for d in timeline['days'].values() for r in d['intervals']}
        edges.update(aware_time(d['end_at']) for d in timeline['days'].values())
        switches = sorted(t for t in edges if signature(t-timedelta(microseconds=1)) != signature(t))
        for left, right in zip(rows, rows[1:]):
            a, b = left['time'], right['time']
            if a >= b: raise StudyError('reference_dli_invalid_sample_order')
            if (b-a).total_seconds() > p['max_gap_seconds'] or any(r['reading_id'] not in accepted for r in (left, right)):
                continue
            changed = [t for t in switches if a < t <= b]
            if len(changed) > 1: continue
            ids = {left['reading_id'], right['reading_id']}
            if changed:
                if p.get('transition_policy') != 'hold_observed_endpoint_on_each_side' or not p.get('transition_source_ref'):
                    continue
                split = changed[0]
                for lo, hi, q in ((a, split, left['ppfd']), (split, b, right['ppfd'])):
                    x, y = max(start, lo), min(end, hi)
                    if x < y: spans.append((x, y, q, ids))
            else:
                x, y = max(start, a), min(end, b)
                if x < y:
                    # Independent antiderivative of the linear reconstruction.
                    midpoint_fraction = ((x-a).total_seconds()+(y-a).total_seconds())/(2*(b-a).total_seconds())
                    q = left['ppfd'] + (right['ppfd']-left['ppfd'])*midpoint_fraction
                    spans.append((x, y, q, ids))
    else:
        raise Missing('logger_sample_semantics_missing')
    cursor = start; complete = True
    for a, b, _, _ in spans:
        if a != cursor: complete = False
        if a < cursor: raise StudyError('reference_dli_overlapping_support')
        cursor = b
    complete = complete and cursor == end
    value = sum(q*(b-a).total_seconds()/1_000_000 for a, b, q, _ in spans) if complete else None
    ids = sorted({rid for _, _, _, group in spans for rid in group})
    return dict(dli_mol_m2_day=value, coverage_status='complete' if complete else 'incomplete',
        mean_ppfd_umol_m2_s=value*1_000_000/(end-start).total_seconds() if complete else None,
        n_readings=len(ids), included_reading_ids=ids, _spans=spans)


def _raw_spot_day(p: dict, accepted: list[dict], timeline: dict, day: dict, date: str, factor: float) -> dict:
    zone = ZoneInfo(p['timezone'])
    rows = [r for r in accepted if r['time'].astimezone(zone).date().isoformat() == date and r['lights_state'] == 'on']
    for row in rows:
        if not any(_fraction(row['time'], zone, w) for w in timeline['fixture_windows'].values()):
            raise Missing('spot_lights_state_schedule_conflict')
    mean = sum(r['ppfd'] for r in rows)/len(rows) if rows else None
    value = mean*factor*day['on_duration_s']/1_000_000 if rows else None
    ids = [r['reading_id'] for r in rows]
    spans = [(aware_time(s['start_at']), aware_time(s['end_at']),
              mean*factor if any(v > 0 for v in s['fixture_fractions'].values()) else 0., set(ids))
             for s in day['intervals']] if rows else []
    return dict(dli_mol_m2_day=value, coverage_status='complete' if rows else 'incomplete',
        mean_ppfd_umol_m2_s=mean, n_readings=len(rows), included_reading_ids=ids, _spans=spans)


def validate_result(path: Path, *, tissue_bases: set[str] | None = None,
                    current_configuration: Path | None = None) -> dict:
    path = path.resolve(); record = read_json(path); folder = path.parent
    if record.get('schema_version') == 'reference-dli-empirical-result-1':
        from tools.reference_dli_empirical import validate_result as validate_empirical
        return validate_empirical(path, current_configuration)
    for group in ('source_hashes', 'code_hashes'):
        hashes = record.get(group)
        if not isinstance(hashes, dict) or not hashes: raise StudyError('reference_dli_'+group+'_missing')
        for name, expected in hashes.items():
            if file_hash(Path(name)) != expected: raise StudyError('reference_dli_'+group+'_mismatch')
    artifacts = record.get('artifact_hashes') or {}
    if set(artifacts) != {'reference_dli.csv', 'integration_evidence.json'}:
        raise StudyError('reference_dli_artifacts_missing')
    for name, expected in artifacts.items():
        if file_hash(folder/name) != expected: raise StudyError('reference_dli_artifact_hash_mismatch')
    audit = read_json(folder/'integration_evidence.json')
    with (folder/'reference_dli.csv').open(encoding='utf-8-sig', newline='') as stream:
        csv_days = list(csv.DictReader(stream))
    if len(csv_days) != len(record.get('days', {})): raise StudyError('reference_dli_csv_days_mismatch')
    for csv_day, day in zip(csv_days, record['days'].values()):
        for key, value in csv_day.items():
            expected = '|'.join(day['flags']) if key == 'flags' else day.get(key)
            if type(expected) in (float, int):
                _same(float(value), expected, 'csv_'+key)
            elif value != ('' if expected is None else str(expected)):
                raise StudyError('reference_dli_csv_'+key+'_mismatch')
    _same(record.get('schema_version'), 'reference-dli-result-1', 'schema')
    _same(record.get('quantity'), 'incident', 'quantity'); _same(record.get('unit'), DLI_UNIT, 'unit')
    _same(record.get('model_scope'), 'whole_plant', 'scope')
    _same(record.get('time_basis'), 'complete_local_day', 'time_basis')
    if record.get('status') not in ('available', 'unavailable', 'out_of_applicability'):
        raise StudyError('reference_dli_invalid_status')
    if record['status'] != 'available' and record.get('value') is not None:
        raise StudyError('reference_dli_unavailable_has_usable_value')
    inputs = record.get('inputs') or {}
    for field in ('position', 'schedule'):
        if inputs.get(field) not in record['source_hashes']: raise StudyError('reference_dli_input_hash_missing')
    p = read_json(Path(inputs['position'])); base = Path(inputs['position']).parent
    schedule = read_json(Path(inputs['schedule']))
    _same(record.get('basis_id'), p.get('basis_id'), 'basis')
    if record.get('basis_id') in (tissue_bases or set()): raise StudyError('basis_collides_with_tissue_basis')
    reference_keys = ('frame_id', 'coordinate_frame', 'position_mm', 'sensor_normal', 'plane', 'height_basis',
                      'source_ref', 'cosine_corrected', 'cosine_source_ref', 'levelled', 'level_source_ref')
    if set(record['reference']) != set(reference_keys): raise StudyError('reference_dli_geometry_fields_missing')
    for key in reference_keys: _same(record['reference'][key], p.get(key), 'reference_'+key)
    _same(record.get('timezone'), p.get('timezone'), 'timezone')
    if inputs.get('frozen_prediction'):
        if record.get('source_kind') != 'simulated': raise StudyError('frozen_prediction_wrong_source_kind')
        from tools.reference_dli_frozen import validate_result as validate_frozen
        return validate_frozen(record, audit, tissue_bases)
    hashes: dict = {}
    try:
        dates, _ = dates_and_geometry(p, base, hashes, tissue_bases or set())
        for field in ('transition_source_ref', 'interval_mean_split_source_ref', 'dimming_source_ref'):
            if p.get(field): evidence(p[field], base, hashes, field)
        route = record.get('source_kind')
        if route == 'simulated': raise Missing('simulation_execution_deferred')
        if route not in ('measured_logged', 'measured_spot_schedule'): raise StudyError('reference_dli_unknown_source_kind')
        for field in ('readings', 'survey'):
            if inputs.get(field) not in record['source_hashes']: raise Missing('reference_dli_reading_source_missing')
        raw = read_readings(Path(inputs['readings']), p)
        survey = read_readings(Path(inputs['survey']), p, survey=True)
        try: timeline = dated_schedule(p, schedule, dates)
        except Missing as exc:
            if route != 'measured_logged': raise
            timeline = mean_support_timeline(p, dates, str(exc))
        factor = spot_scale(p, timeline)['factor'] if route == 'measured_spot_schedule' else 1.
        mode = p.get('gradient_exposure_basis')
        duration_field = 'on_duration_s' if mode == 'scheduled_on_duration' else 'duration_s'
        if mode not in ('scheduled_on_duration', 'full_elapsed_day'):
            raise Missing('gradient_temporal_exposure_basis_missing')
        duration = max(d[duration_field] for d in timeline['days'].values())*factor
        tolerance = survey_tolerance(p, survey, duration, base, hashes)
        accepted, excluded = select_readings(p, raw, tolerance)
        _same(audit['selection']['included_reading_ids'], [r['reading_id'] for r in accepted], 'selection')
        _same(audit['selection']['excluded_readings'], excluded, 'exclusions')
        ambient = ambient_evidence(p, accepted, dates, base, hashes)
        expected_days = {}
        if set(record['days']) != set(dates): raise StudyError('reference_dli_selected_dates_mismatch')
        for date in dates:
            day = record['days'][date]; timing = timeline['days'][date]
            expected = (_raw_logged_day(p, raw, {r['reading_id'] for r in accepted}, timeline, timing)
                        if route == 'measured_logged' else _raw_spot_day(p, accepted, timeline, timing, date, factor))
            raw_spans = expected.pop('_spans')
            for key, value in expected.items(): _same(day.get(key), value, 'raw_'+key)
            for key in ('start_at', 'end_at', 'duration_s', 'on_duration_s'):
                _same(day.get(key), timing[key], key)
            _same(day.get('flags'), sensor_flags(p), 'sensor_flags')
            _same(day.get('cosine_corrected'), p.get('cosine_corrected'), 'cosine_corrected')
            _same(day.get('levelled'), p.get('levelled'), 'levelled')
            _same(day.get('ambient_light'), ambient[date]['ambient_light'], 'ambient_light')
            if len(day['integration_segments']) != len(raw_spans): raise StudyError('reference_dli_segment_count_mismatch')
            for segment, (a, b, q, ids) in zip(day['integration_segments'], raw_spans):
                _same(aware_time(segment['start_at']), a, 'raw_segment_start')
                _same(aware_time(segment['end_at']), b, 'raw_segment_end')
                _same(segment['mean_ppfd_umol_m2_s'], q, 'raw_segment_mean')
                _same(set(segment['reading_ids']), ids, 'raw_segment_readings')
            # Serialized integration audit must independently sum to the verified
            # value and cover a complete day once when completeness is claimed.
            if expected['coverage_status'] == 'complete':
                spans = day['integration_segments']; cursor = aware_time(timing['start_at']); total = 0.
                for segment in spans:
                    a, b = aware_time(segment['start_at']), aware_time(segment['end_at'])
                    if a != cursor or b <= a: raise StudyError('reference_dli_audit_support_mismatch')
                    _same(segment['duration_s'], (b-a).total_seconds(), 'audit_seconds')
                    _same(segment['mean_ppfd_umol_m2_s'], (segment['start_ppfd_umol_m2_s']+segment['end_ppfd_umol_m2_s'])/2, 'audit_mean')
                    total += segment['mean_ppfd_umol_m2_s']*(b-a).total_seconds()/1_000_000
                    cursor = b
                _same(cursor, aware_time(timing['end_at']), 'audit_end')
                _same(total, expected['dli_mol_m2_day'], 'audit_integral')
            _same(audit['integration']['days'][date], day, 'audit_daily_record')
            expected_days[date] = expected
        blocked = any(v['contradictory_reading_ids'] for v in ambient.values())
        try: associated = association(p, tolerance, base, hashes)
        except Missing:
            associated = None; blocked = True
        _same(record['plant_association'], associated, 'association')
        try: applicability = domain(p, base, hashes)
        except Missing:
            applicability = None; blocked = True
        _same(record.get('applicability_domain'), applicability, 'domain')
        chosen = choose_value(p, expected_days, applicability, base, hashes)
        if blocked:
            chosen['status'] = 'unavailable'; chosen['value'] = None
        for key in ('status', 'value', 'candidate_value', 'value_rule', 'days_used', 'days_not_used'):
            _same(record.get(key), chosen[key], 'reduction_'+key)
        if record['status'] == 'available':
            _same(record.get('fixed_over_horizon'), True, 'fixed_horizon')
            _same(record.get('reasons'), [], 'available_reasons')
    except Missing as exc:
        if record['status'] != 'unavailable' or record.get('value') is not None:
            raise StudyError('reference_dli_claim_exceeds_evidence:'+str(exc)) from exc
        if any(day['dli_mol_m2_day'] is not None for day in record['days'].values()):
            # Missing reduction policy can coexist with already verified daily
            # values; missing early raw-support evidence cannot establish them.
            if 'expected_days' not in locals() or len(expected_days) != len(record['days']):
                raise StudyError('reference_dli_unverified_numeric_audit') from exc
    for name, sha in hashes.items():
        _same(record['source_hashes'].get(name), sha, 'evidence_source_hash')
    return dict(valid=True, status=record['status'], value=record['value'],
                absolute_tolerance=ABS_TOL, relative_tolerance=REL_TOL,
                arithmetic='independent_raw_reading_integration')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--current-configuration', type=Path)
    args = parser.parse_args(argv)
    try: print(validate_result(args.result, current_configuration=args.current_configuration)); return 0
    except (StudyError, OSError, ValueError) as exc: parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
