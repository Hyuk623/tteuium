"""Read-only human CSV normalization; no correction of missing identity or time."""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path

from tools.vtc_growth_io import rows, sha, aware, require
from tools.nutrient_reservoir import Missing, SCHEMA, EC_UNIT, EQ_UNIT, quantity, evidence, estimate

STATUSES = {'measured', 'assumed', 'unavailable', 'approximate', 'derived', 'user_stated', 'user_assumed'}
MISSING = {'', 'unavailable', 'n/a', 'null'}
LOG_FIELDS = {
    'supply_volume_ml': ('L', .001, None),
    'supply_ec_ms_cm': (EC_UNIT, 1.0, 'supply_ec__status'),
    'pool_depth_mm_before': ('mm', 1.0, None),
    'pool_depth_mm_after': ('mm', 1.0, None),
    'pool_ec_ms_cm': (EC_UNIT, 1.0, 'pool_ec__status'),
    'removed_volume_ml': ('L', .001, None),
    'water_temp_c': ('degC', 1.0, None),
    'nitrate_strip_mg_l': ('mg/L_as_recorded_not_used', 1.0, None),
}
OBS_FIELDS = {'ec_us_cm': (EC_UNIT, .001, None), 'tds_ppm': ('ppm_meter_scale_not_elements', 1.0, None),
              'ph': ('pH', 1.0, None), 'solution_temp_c': ('degC', 1.0, None),
              'minutes_after_feeding': ('min', 1.0, None)}
TRAY_FIELDS = {'tray_inner_length_mm': ('mm', 1.0, None),
               'tray_inner_width_mm': ('mm', 1.0, None),
               'medium_volume_per_pot_ml': ('L', .001, None), 'pot_count': ('count', 1.0, None)}


def _cell(row: dict, field: str, unit: str, factor: float, status_field: str | None,
          source: Path, source_hash: str, line: int, issues: list) -> dict:
    raw = row.get(field, '')
    status = row.get(field+'__status', row.get(status_field, '') if status_field else '')
    if not status:
        status = row.get('source_kind', 'unavailable')
    if status not in STATUSES:
        issues.append(dict(line=line, field=field, reason='unknown_status', raw_status=status))
        status = 'unavailable'
    value = None
    if raw.strip().lower() not in MISSING and status != 'unavailable':
        try:
            candidate = float(raw)*factor
            if not math.isfinite(candidate) or (candidate < 0 and unit != 'degC'):
                raise ValueError('invalid physical value')
            value = candidate
        except ValueError:
            issues.append(dict(line=line, field=field, reason='invalid_numeric_value'))
    if value is None:
        if raw.strip().lower() not in MISSING and status == 'unavailable':
            issues.append(dict(line=line, field=field, reason='value_with_unavailable_status_retained_raw'))
        status = 'unavailable'
    return dict(record_line=line, tray_id=row.get('tray_id', ''), field=field, raw_value=raw,
                value=value, unit=unit, status=status, source_kind=row.get('source_kind', 'unavailable'),
                source_ref=f'{source.resolve()}:{line}:{field}', source_sha256=source_hash,
                element_resolved=False, scenario_id='records_audit', uncertainty_status='unavailable')


def audit_records(log: Path, tray_spec: Path | None = None) -> dict:
    """Both existing template and October 13 observation-only dialects retained."""
    raw = rows(log)
    require(bool(raw), 'empty nutrient CSV')
    dialect = 'template' if 'event_time' in raw[0] else 'observation_only'
    required = {'tray_id', 'event_time', 'event_kind', 'supply_volume_ml', 'pool_ec_ms_cm'} if dialect == 'template' else {
        'sample_id', 'tray_id', 'measured_time', 'sample_kind', 'ec_us_cm'}
    require(required <= set(raw[0]), 'unsupported nutrient record schema')
    issues, normalized, identities, specs = [], [], {}, []
    hashes = {str(log.resolve()): sha(log)}
    if tray_spec is not None:
        specs = rows(tray_spec)
        hashes[str(tray_spec.resolve())] = sha(tray_spec)
        plant_ids = set()
        for line, row in enumerate(specs, 2):
            tid = row.get('tray_id', '')
            if tid in identities or tid.lower() in MISSING:
                issues.append(dict(line=line, field='tray_id', reason='duplicate_or_missing_tray_identity'))
            identities[tid] = row
            planted = row.get('has_plants', '').lower()
            ids = [s.strip() for s in row.get('plant_ids', '').split(';') if s.strip()]
            if planted not in {'true', 'false'} or (planted == 'true') != bool(ids):
                issues.append(dict(line=line, field='plant_ids', reason='blank_or_membership_invalid'))
            for pid in ids:
                if pid in plant_ids or '1xx' in pid or pid.lower() in MISSING:
                    issues.append(dict(line=line, field='plant_ids', reason='duplicate_or_placeholder_plant'))
                plant_ids.add(pid)
            for field, (unit, factor, sf) in TRAY_FIELDS.items():
                cell = _cell(row, field, unit, factor, sf, tray_spec, hashes[str(tray_spec.resolve())], line, issues)
                normalized.append(cell)
                if cell['value'] is None or cell['value'] <= 0 or (field == 'pot_count' and not cell['value'].is_integer()):
                    issues.append(dict(line=line, field=field, reason='positive_dimension_or_count_unavailable'))
    else:
        issues.append(dict(reason='tray_spec_unavailable'))
    times, supply_count = {}, 0
    for line, row in enumerate(raw, 2):
        tid = row['tray_id']
        if tid.lower() in MISSING or (dialect == 'template' and tid not in identities):
            issues.append(dict(line=line, field='tray_id', reason='tray_identity_unavailable'))
        time_field = 'event_time' if dialect == 'template' else 'measured_time'
        time_status = row.get(time_field+'__status', 'unavailable')
        try:
            dt = aware(row[time_field])
            require(time_status in {'measured', 'assumed', 'derived', 'user_stated', 'user_assumed'}, 'exact time not supported')
            if tid in times:
                require(dt >= times[tid], 'unordered record time')
            times[tid] = dt
        except (ValueError, TypeError):
            issues.append(dict(line=line, field=time_field, reason='exact_aware_time_unavailable', raw=row[time_field]))
        for field, (unit, factor, sf) in (LOG_FIELDS if dialect == 'template' else OBS_FIELDS).items():
            normalized.append(_cell(row, field, unit, factor, sf, log, hashes[str(log.resolve())], line, issues))
        if dialect == 'template':
            if row['event_kind'] not in {'supply', 'measure_only', 'remove'}:
                issues.append(dict(line=line, field='event_kind', reason='unknown_event_kind'))
            supply_count += row['event_kind'] == 'supply'
    blanks = [tid for tid, row in identities.items() if row.get('has_plants', '').lower() == 'false']
    if not blanks:
        issues.append(dict(reason='blank_tray_unavailable'))
    return dict(status='read_only_records_audit', schema_version='tray-nutrient-records-1',
                scenario_id='records_audit', dialect=dialect, element_resolved=False,
                source_hashes=hashes, raw_records=raw, raw_tray_specs=specs,
                normalized_rows=normalized, issues=issues, uptake_status='unavailable',
                uptake_ec_equivalent=None, missing_inputs=['explicit_interval_mapping', 'medium_held_states',
                    'initial_stored_pools_for_replay', 'uncertainty_bounds', 'blank_comparability'],
                recorded_supply_rows=supply_count,
                calibration_status='not_fitted_seven_events_not_sufficient_for_identification',
                release_interpretation='hypothesis_not_identified_by_EC_only', native_causality=False)


def records_estimate(log: Path, tray_spec: Path, supplement: dict) -> dict:
    """Bind explicit endpoint/event CSV lines to an interval supplement.

    Supplement supplies states that CSV cannot observe, bounds and comparability.
    It never replaces numeric EC/depth/geometry CSV evidence. Interval endpoints
    refer to AFTER-event pool depths; only start < event <= end contributes flux.
    Every in-interval log row must be accounted for. Removal EC must be explicit.
    """
    audit = audit_records(log, tray_spec)
    require(audit['dialect'] == 'template', 'observation-only CSV cannot identify intervals')
    require(not audit['issues'], 'record identity/time/geometry errors prevent interval binding')
    require(supplement.get('record_sha256') == sha(log) and supplement.get('tray_spec_sha256') == sha(tray_spec),
            'stale record supplement')
    req = deepcopy(supplement['request'])
    require(req.get('schema_version') == SCHEMA, 'supplement schema')
    require(not req.get('observations') and not req.get('trays'), 'records-derived fields must not be overridden')
    cells = {(c['source_sha256'], c['record_line'], c['field']): c for c in audit['normalized_rows']}
    def cell(path: Path, line: int, field: str) -> dict:
        c = cells[(sha(path), line, field)]
        if c['value'] is None:
            raise Missing('recorded value unavailable: ' + c['source_ref'])
        err = supplement.get('bounds', {}).get(f'{path.name}:{line}:{field}')
        if err is None:
            raise Missing('record uncertainty unavailable: ' + c['source_ref'])
        evidence(err, 'record uncertainty')
        # Bounds use normalized units, never raw uS or mL.
        return dict(value=c['value'], unit=c['unit'], source_kind=c['status'], source_ref=c['source_ref'],
                    abs_error=err['abs_error'], uncertainty_evidence=err)
    req['trays'], req['observations'] = [], {}
    for line, spec in enumerate(audit['raw_tray_specs'], 2):
        tid = spec['tray_id']
        bind = supplement['bindings'][tid]
        length, width = cell(tray_spec, line, 'tray_inner_length_mm'), cell(tray_spec, line, 'tray_inner_width_mm')
        mv, count = cell(tray_spec, line, 'medium_volume_per_pot_ml'), cell(tray_spec, line, 'pot_count')
        # Discrete pot count must be exactly declared, not treated as continuous uncertainty.
        require(count['abs_error'] == 0, 'pot count must be exact')
        mv['value'] *= count['value']; mv['abs_error'] *= count['value']
        mv['source_ref'] += ' multiplied by recorded pot_count'
        req['trays'].append(dict(tray_id=tid, has_plants=spec['has_plants'].lower() == 'true',
            plant_ids=[p.strip() for p in spec['plant_ids'].split(';') if p.strip()], inner_length_mm=length,
            inner_width_mm=width, medium_volume_L=mv, medium_mix=spec['medium_mix_vermiculite_perlite']))
        obs = dict(tray_id=tid, interval_start=req['interval_start'], interval_end=req['interval_end'],
                   source_kind='derived', source_ref=str(log.resolve()))
        for endpoint, moment in (('start', req['interval_start']), ('end', req['interval_end'])):
            lineno = bind[endpoint+'_line']
            require(type(lineno) is int and 2 <= lineno <= len(audit['raw_records'])+1,
                    'endpoint must select an actual CSV data line')
            row = audit['raw_records'][lineno-2]
            require(row['tray_id'] == tid and aware(row['event_time']) == aware(moment), 'endpoint identity/time mismatch')
            obs[endpoint] = dict(pool_depth_mm=cell(log, lineno, 'pool_depth_mm_after'),
                                 pool_ec_ms_cm=cell(log, lineno, 'pool_ec_ms_cm'),
                                 medium_water_L=bind[endpoint+'_medium_water_L'],
                                 medium_ec_ms_cm=bind[endpoint+'_medium_ec_ms_cm'])
        expected = [n for n, row in enumerate(audit['raw_records'], 2) if row['tray_id'] == tid and
                    aware(req['interval_start']) < aware(row['event_time']) <= aware(req['interval_end'])]
        require(bind['event_lines'] == expected, 'incomplete/duplicate interval event coverage')
        sums = {k: [0.0, 0.0] for k in ('supplied_water_L', 'removed_water_L', 'supplied_ec_equivalent', 'removed_ec_equivalent')}
        for lineno in expected:
            row = audit['raw_records'][lineno-2]
            kind = row['event_kind']
            if kind == 'measure_only':
                require(cell(log, lineno, 'supply_volume_ml')['value'] == 0, 'measure_only supply must explicitly be zero')
                require(cell(log, lineno, 'removed_volume_ml')['value'] == 0, 'measure_only removal must explicitly be zero')
                continue
            water = cell(log, lineno, 'supply_volume_ml' if kind == 'supply' else 'removed_volume_ml')
            other = cell(log, lineno, 'removed_volume_ml' if kind == 'supply' else 'supply_volume_ml')
            require(other['value'] == 0, 'split simultaneous supply/removal into separate ordered records')
            ec = cell(log, lineno, 'supply_ec_ms_cm') if kind == 'supply' else bind['removed_ec_by_line'][str(lineno)]
            ev, ee = quantity(ec, EC_UNIT, 'event EC', bounds=True)
            v, ve = quantity(water, 'L', 'event water', bounds=True)
            prefix = 'supplied' if kind == 'supply' else 'removed'
            sums[prefix+'_water_L'][0] += v; sums[prefix+'_water_L'][1] += ve
            sums[prefix+'_ec_equivalent'][0] += v*ev
            sums[prefix+'_ec_equivalent'][1] += v*ee+ve*ev+ve*ee
        evidence(bind.get('complete_event_coverage_evidence'), 'complete records coverage')
        for name, (value, err) in sums.items():
            obs[name] = dict(value=value, abs_error=err, unit='L' if name.endswith('_L') else EQ_UNIT,
                source_kind='derived', source_ref=str(log.resolve())+' explicit event coverage',
                uncertainty_evidence=bind['complete_event_coverage_evidence'])
        req['observations'][tid] = obs
    return dict(request=req, result=estimate(req), record_source_hashes=audit['source_hashes'])
