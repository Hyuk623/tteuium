"""Versioned frozen spatial predictions for reference DLI, separate from measurements.

Exact point/frame matching only; no interpolation, inferred clock, or automatic P3 activation.
Single-plant association is supported. Spatially shared references require further evidence.
"""
from __future__ import annotations

import math
import json
from pathlib import Path

from tools.leaf_light.common import DLI_UNIT, StudyError, file_hash, read_json, rows
from tools.reference_dli_contract import Missing, association, dates_and_geometry, evidence
from tools.reference_dli_intervals import dated_schedule
from tools.reference_dli_policy import choose_value, domain, sensor_flags
from tools.compound_growth import aware_time

SCHEMA = 'frozen-reference-ppfd-1'
COLUMNS = ('point_id', 'x_mm', 'y_mm', 'z_mm', 'ppfd_umol_m2_s', 'seed_standard_error_umol_m2_s')


def require(ok, reason):
    if not ok: raise StudyError(reason)


def read_prediction(path: Path, position: dict, hashes: dict) -> tuple[dict, dict]:
    path = path.resolve(); data = read_json(path); hashes[str(path)] = file_hash(path)
    require(data.get('schema_version') == SCHEMA, 'frozen_prediction_schema')
    require(data.get('quantity') == 'incident' and data.get('unit') == 'umol/m2/s'
            and data.get('source_kind') == 'fitted', 'frozen_prediction_quantity_or_provenance')
    require(data.get('sensor_normal') == [0, 0, 1], 'frozen_prediction_horizontal_only')
    require(data.get('source_hashes') and data.get('fit_ref') and data.get('scene_ref'), 'frozen_prediction_lineage_missing')
    for name, expected in data['source_hashes'].items():
        source = (path.parent/name).resolve()
        require(file_hash(source) == expected, 'frozen_prediction_source_hash_mismatch')
        hashes[str(source)] = expected
    for key in ('fit_ref', 'scene_ref'):
        ref = (path.parent/data[key]).resolve()
        require(str(ref) in hashes, 'frozen_prediction_fit_scene_not_hashed')
    table = (path.parent/data['predictions_csv']).resolve()
    require(file_hash(table) == data.get('predictions_sha256'), 'frozen_prediction_table_hash_mismatch')
    hashes[str(table)] = file_hash(table)
    records = rows(table, COLUMNS)
    require(len({r['point_id'] for r in records}) == len(records), 'frozen_prediction_duplicate_point')
    for row in records:
        for field in COLUMNS[1:]:
            v = float(row[field]); require(math.isfinite(v), 'frozen_prediction_nonfinite')
            if field in COLUMNS[4:]: require(v >= 0, 'frozen_prediction_negative')
    require(isinstance(data.get('conditional_reasons'), list), 'frozen_prediction_conditions_missing')
    require(data.get('uncertainty') and data['uncertainty'].get('systematic_status'), 'frozen_prediction_uncertainty_missing')
    require(data.get('fixture_ids') and len(set(data['fixture_ids'])) == len(data['fixture_ids']), 'frozen_fixture_ids')
    require(data.get('output_basis') == 'all_fixtures_full_photon_output', 'frozen_output_basis')
    require(data.get('fixed_optics_beam_spectrum') is True, 'frozen_fixed_optics_missing')
    require(data.get('coordinate_frame') == position.get('coordinate_frame')
            and data.get('frame_id') == position.get('frame_id')
            and data.get('height_basis') == position.get('height_basis'), 'frozen_prediction_frame_mismatch')
    match = [r for r in records if [float(r[f'{a}_mm']) for a in 'xyz'] == position.get('position_mm')]
    require(len(match) == 1, 'frozen_prediction_exact_position_required')
    support = data.get('time_support') or {}
    if not support.get('start_at') or not support.get('end_at'): raise Missing('frozen_prediction_time_support_missing')
    a, b = aware_time(support['start_at']), aware_time(support['end_at'])
    require(b > a and support.get('source_ref'), 'frozen_prediction_time_support_missing')
    evidence(support['source_ref'], path.parent, hashes, 'frozen_time_support')
    return data, match[0]


def check_timeline(data, timeline, position):
    require(set(timeline['fixture_windows']) == set(data['fixture_ids']), 'frozen_prediction_fixture_mismatch')
    if position.get('ambient_light') != 'none': raise Missing('frozen_prediction_ambient_not_modelled')
    start = aware_time(data['time_support']['start_at']); end = aware_time(data['time_support']['end_at'])
    for day in timeline['days'].values():
        if aware_time(day['start_at']) < start or aware_time(day['end_at']) > end:
            raise Missing('frozen_prediction_outside_time_support')
        for segment in day['intervals']:
            fractions = list(segment['fixture_fractions'].values())
            if len(set(fractions)) != 1: raise Missing('frozen_total_prediction_requires_common_fixture_fraction')
            if fractions[0] not in (0, 1) and position.get('dimming_response') != 'linear_photon_output':
                raise Missing('frozen_prediction_dimming_response_missing')


def reduction(position, days, base, hashes):
    reasons = []; associated = applicability = None
    try:
        if len((position.get('plant_association') or {}).get('plant_instance_ids') or []) != 1:
            raise Missing('frozen_reference_shared_position_unverified')
        associated = association(position, {}, base, hashes)
    except Missing as exc: reasons.append(str(exc))
    try: applicability = domain(position, base, hashes)
    except Missing as exc: reasons.append(str(exc))
    try: chosen = choose_value(position, days, applicability, base, hashes)
    except Missing as exc:
        chosen = dict(status='unavailable', value=None, candidate_value=None, value_rule=position.get('value_rule'),
                      fixed_over_horizon=None, days_used=[], days_not_used=[], reasons=[str(exc)])
    reasons.extend(chosen['reasons'])
    return chosen, associated, applicability, reasons


def prepare(position_path, schedule_path, prediction_path, tissue_manifest=None):
    from tools.reference_dli import _empty_day, _tissue_ids, code_hashes
    p = read_json(position_path); schedule = read_json(schedule_path); base = position_path.resolve().parent
    hashes = {str(x.resolve()):file_hash(x) for x in (position_path, schedule_path, prediction_path)}
    tissue = set()
    if tissue_manifest:
        hashes[str(tissue_manifest.resolve())] = file_hash(tissue_manifest)
        tissue = _tissue_ids(read_json(tissue_manifest))
    days = {}; reasons = []; associated = applicability = data = None
    chosen = dict(status='unavailable', value=None, candidate_value=None, value_rule=p.get('value_rule'),
                  fixed_over_horizon=None, days_used=[], days_not_used=[], reasons=[])
    audit = dict(route='frozen_prediction', schedule=None, integration={}, prediction=None)
    try:
        dates, _ = dates_and_geometry(p, base, hashes, tissue)
        data, row = read_prediction(prediction_path, p, hashes)
        audit['prediction'] = dict(point_id=row['point_id'], uncertainty=data['uncertainty'],
                                    seed_standard_error_umol_m2_s=float(row['seed_standard_error_umol_m2_s']))
        timeline = dated_schedule(p, schedule, dates); audit['schedule'] = timeline
        check_timeline(data, timeline, p)
        if any(v not in (0, 1) for d in timeline['days'].values() for s in d['intervals'] for v in s['fixture_fractions'].values()):
            evidence(p.get('dimming_source_ref'), base, hashes, 'dimming_response')
        q = float(row['ppfd_umol_m2_s'])
        for date, timing in timeline['days'].items():
            segments = []
            for s in timing['intervals']:
                duration = (aware_time(s['end_at'])-aware_time(s['start_at'])).total_seconds()
                rate = q*next(iter(s['fixture_fractions'].values()))
                segments.append(dict(start_at=s['start_at'], end_at=s['end_at'], duration_s=duration,
                                     mean_ppfd_umol_m2_s=rate, fixture_fractions=s['fixture_fractions']))
            dose = sum(s['mean_ppfd_umol_m2_s']*s['duration_s'] for s in segments)/1e6
            days[date] = dict(local_date=date, start_at=timing['start_at'], end_at=timing['end_at'],
                duration_s=timing['duration_s'], on_duration_s=timing['on_duration_s'], coverage_status='complete',
                dli_mol_m2_day=dose, mean_ppfd_umol_m2_s=dose*1e6/timing['duration_s'],
                n_readings=0, included_reading_ids=[], integration_segments=segments, gaps=[], reason=None)
        chosen, associated, applicability, more = reduction(p, days, base, hashes); reasons.extend(more)
        if data['conditional_reasons']: reasons.append('frozen_prediction_conditional')
        if data['uncertainty']['systematic_status'] == 'unavailable': reasons.append('frozen_prediction_systematic_uncertainty_unavailable')
    except Missing as exc:
        reasons.append(str(exc))
        if not days: days = {date:_empty_day(date, str(exc)) for date in p.get('dates', [])}
    if not days: days = {'unselected':_empty_day(None, reasons[0] if reasons else 'date_selection_missing')}
    for day in days.values():
        value = day['dli_mol_m2_day']
        day.update(basis_id=p.get('basis_id'), source_kind='simulated', flags=sensor_flags(p),
            ambient_light='declared_excluded_by_model', ambient_light_declared=p.get('ambient_light'),
            applicability_low=applicability['min'] if applicability else None,
            applicability_high=applicability['max'] if applicability else None,
            applicability_status='unavailable' if value is None or applicability is None else
                'in_applicability' if applicability['min'] <= value <= applicability['max'] else 'out_of_applicability',
            cosine_corrected=p.get('cosine_corrected'), levelled=p.get('levelled'))
    if reasons:
        chosen.update(value=None, status='out_of_applicability' if set(reasons) == {'out_of_applicability'} else 'unavailable',
                      fixed_over_horizon=None)
    audit['integration'] = dict(days=days)
    record = dict(schema_version='reference-dli-result-1', quantity='incident', model_scope='whole_plant',
        unit=DLI_UNIT, basis_id=p.get('basis_id'), source_kind='simulated', time_basis='complete_local_day',
        spatial_basis='declared_reference_position_horizontal_plane', **chosen)
    record.update(reasons=sorted(set(reasons)), reference={k:p.get(k) for k in ('frame_id', 'coordinate_frame',
        'position_mm', 'sensor_normal', 'plane', 'height_basis', 'source_ref', 'cosine_corrected', 'cosine_source_ref',
        'levelled', 'level_source_ref')}, timezone=p.get('timezone'), dst_policy=p.get('dst_policy'), days=days,
        applicability_interval=[applicability['min'], applicability['max']] if applicability else [None,None],
        applicability_domain=applicability, applicability_source_ref=p.get('applicability_source_ref'),
        plant_association=associated, operating_metadata=p.get('operating_metadata'), source_hashes=hashes,
        code_hashes=code_hashes(), inputs=dict(position=str(position_path.resolve()), schedule=str(schedule_path.resolve()),
        frozen_prediction=str(prediction_path.resolve()), tissue_manifest=str(tissue_manifest.resolve()) if tissue_manifest else None),
        prediction_provenance=data, disclosures=['fitted_spatial_prediction_not_measured',
        'incident_reference_not_tissue_average', 'no_interpolation_or_growth_prediction'])
    return record, audit


def validate_result(record, audit, tissue_bases=None):
    """Independent rectangular-dose arithmetic; never calls prepare()."""
    from tools.reference_dli_consumer import _same
    inputs = record['inputs']; p = read_json(Path(inputs['position'])); base = Path(inputs['position']).parent
    hashes = {}; expected_days = {}; reasons = []
    if inputs.get('tissue_manifest'):
        from tools.reference_dli import _tissue_ids
        tissue_path = Path(inputs['tissue_manifest']); hashes[str(tissue_path)] = file_hash(tissue_path)
        tissue_bases = (tissue_bases or set()) | _tissue_ids(read_json(tissue_path))
    try:
        dates, _ = dates_and_geometry(p, base, hashes, tissue_bases or set())
        data, row = read_prediction(Path(inputs['frozen_prediction']), p, hashes)
        _same(record.get('prediction_provenance'), data, 'frozen_provenance')
        timeline = dated_schedule(p, read_json(Path(inputs['schedule'])), dates)
        check_timeline(data, timeline, p)
        if any(v not in (0,1) for d in timeline['days'].values() for s in d['intervals'] for v in s['fixture_fractions'].values()):
            evidence(p.get('dimming_source_ref'), base, hashes, 'dimming_response')
        _same(audit['schedule'], json.loads(json.dumps(timeline)), 'frozen_schedule')
        _same(set(record['days']), set(dates), 'frozen_dates')
        for date, day in timeline['days'].items():
            intervals = day['intervals']; total = 0.; cursor = aware_time(day['start_at'])
            actual = record['days'][date]; segments = actual['integration_segments']
            require(len(segments) == len(intervals), 'frozen_segment_count')
            for s, exported in zip(intervals, segments):
                a, b = aware_time(s['start_at']), aware_time(s['end_at'])
                require(a == cursor and b > a, 'frozen_noncontiguous_day')
                fraction = s['fixture_fractions'][data['fixture_ids'][0]]
                rate = float(row['ppfd_umol_m2_s'])*fraction; seconds = (b-a).total_seconds()
                total += rate*seconds/1e6; cursor = b
                _same(exported, dict(start_at=s['start_at'], end_at=s['end_at'], duration_s=seconds,
                                     mean_ppfd_umol_m2_s=rate, fixture_fractions=s['fixture_fractions']), 'frozen_segment')
            require(cursor == aware_time(day['end_at']), 'frozen_incomplete_day')
            _same(actual['dli_mol_m2_day'], total, 'frozen_dose')
            _same(actual['coverage_status'], 'complete', 'frozen_coverage')
            _same(actual['source_kind'], 'simulated', 'frozen_source')
            _same(actual['mean_ppfd_umol_m2_s'], total*1e6/day['duration_s'], 'frozen_daily_mean')
            for key in ('start_at','end_at','duration_s','on_duration_s'):
                _same(actual[key], day[key], 'frozen_'+key)
            _same(actual['n_readings'], 0, 'frozen_not_measured')
            _same(actual['included_reading_ids'], [], 'frozen_not_reading_ids')
            _same(actual['flags'], sensor_flags(p), 'frozen_flags')
            expected_days[date] = dict(dli_mol_m2_day=total, coverage_status='complete')
        chosen, associated, applicability, more = reduction(p, expected_days, base, hashes); reasons.extend(more)
        if data['conditional_reasons']: reasons.append('frozen_prediction_conditional')
        if data['uncertainty']['systematic_status'] == 'unavailable': reasons.append('frozen_prediction_systematic_uncertainty_unavailable')
        if reasons: chosen.update(value=None, status='out_of_applicability' if set(reasons) == {'out_of_applicability'} else 'unavailable')
        for key in ('status','value','candidate_value','value_rule','days_used','days_not_used'):
            _same(record.get(key), chosen[key], 'frozen_'+key)
        _same(record['plant_association'], associated, 'frozen_association')
        _same(record['applicability_domain'], applicability, 'frozen_domain')
        _same(record['reasons'], sorted(set(reasons)), 'frozen_reasons')
        _same(audit['integration']['days'], record['days'], 'frozen_audit')
    except Missing as exc:
        require(record['status'] == 'unavailable' and record.get('value') is None, 'frozen_claim_exceeds_evidence')
        require(all(d['dli_mol_m2_day'] is None for d in record['days'].values()), 'frozen_unverified_daily_value')
        require(str(exc) in record['reasons'], 'frozen_missing_reason')
    for name, sha in hashes.items(): _same(record['source_hashes'].get(name), sha, 'frozen_hash')
    return dict(valid=True, status=record['status'], value=record['value'], absolute_tolerance=1e-12,
                relative_tolerance=1e-12, arithmetic='independent_frozen_prediction_schedule_integration')
