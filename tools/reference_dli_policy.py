"""Evidence-bearing reference light policy; values do not define biological policy."""
from __future__ import annotations

import math
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.leaf_light.common import DLI_UNIT, StudyError, read_json
from tools.reference_dli_contract import Missing, canonical_unit, evidence, number, require


def domain(position: dict, base: Path, hashes: dict) -> dict:
    """Bind supplied bounds to an explicit P3 coefficient-domain JSON object."""
    ref = evidence(position.get('applicability_source_ref'), base, hashes, 'applicability')
    pointer = ref.get('json_pointer')
    if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')):
        raise Missing('applicability_domain_pointer_missing')
    source = read_json(Path(ref['path']))
    try:
        for token in pointer.split('/')[1:] if pointer else []:
            key = token.replace('~1', '/').replace('~0', '~')
            source = source[int(key)] if isinstance(source, list) else source[key]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise StudyError('applicability_domain_pointer_invalid') from exc
    if not isinstance(source, dict):
        raise StudyError('applicability_domain_record_required')
    canonical_unit(source.get('unit'))
    low, high = number(source.get('min'), 'domain_min', 0), number(source.get('max'), 'domain_max', 0)
    bounds = position.get('applicability_interval_mol_m2_day')
    if not isinstance(bounds, list) or len(bounds) != 2 or None in bounds:
        raise Missing('applicability_bounds_missing')
    values = [number(v, 'applicability_bound', 0) for v in bounds]
    if low > high or values != [low, high]:
        raise StudyError('applicability_bounds_do_not_match_source_domain')
    return dict(min=low, max=high, unit=DLI_UNIT, applicability_source_ref=ref,
                source_kind='declared_p3_coefficient_domain', source_ref=ref)


def sensor_flags(position: dict) -> list[str]:
    return [] if position.get('cosine_corrected') is True else ['cosine_response_uncorrected']


def ambient_evidence(position: dict, rows: list[dict], dates: list[str], base: Path,
                     hashes: dict) -> dict:
    declared = position.get('ambient_light')
    if declared not in ('none', 'present', 'unknown', None):
        raise StudyError('invalid_ambient_light_declaration')
    identifiers = position.get('daytime_ambient_reading_ids') or []
    if len(set(identifiers)) != len(identifiers):
        raise StudyError('duplicate_daytime_ambient_reading_id')
    by_id = {r['reading_id']: r for r in rows}
    if identifiers:
        evidence(position.get('daytime_source_ref'), base, hashes, 'daytime_ambient')
    for rid in identifiers:
        if rid not in by_id or by_id[rid]['lights_state'] != 'off' or by_id[rid]['ppfd'] is None:
            raise Missing('daytime_ambient_reading_not_supported_at_reference')
    zone = ZoneInfo(position['timezone']) if position.get('timezone') else None
    result = {}
    for day in dates:
        selected = [r for rid, r in by_id.items() if rid in identifiers and zone is not None
                    and r['time'].astimezone(zone).date().isoformat() == day]
        contradictory = [r['reading_id'] for r in rows if declared == 'none'
                         and r['lights_state'] == 'off' and r['ppfd'] is not None and r['ppfd'] > 0
                         and zone is not None and r['time'].astimezone(zone).date().isoformat() == day]
        measured = 'present' if any(r['ppfd'] > 0 for r in selected) else 'none'
        result[day] = dict(ambient_light=measured if selected else 'asserted_not_measured',
            ambient_light_declared=declared, evidence_status='measured_daytime_lights_off' if selected else 'asserted_not_measured',
            reading_ids=[r['reading_id'] for r in selected], contradictory_reading_ids=contradictory,
            source_ref=position.get('daytime_source_ref') if selected else None)
    return result


def choose_value(position: dict, days: dict, applicability: dict | None, base: Path,
                 hashes: dict) -> dict:
    """Keep every selected day; reject unsupported fixed-horizon reduction."""
    rule = position.get('value_rule')
    if rule not in ('mean_of_complete_days', 'single_representative_day', 'declared_scenario'):
        raise Missing('value_rule_missing')
    chosen = list(days)
    if rule == 'single_representative_day':
        selected = require(position.get('representative_date'), 'representative_date_missing')
        if selected not in days:
            raise StudyError('representative_date_not_in_selected_dates')
        chosen = [selected]
    used = [dict(local_date=d, value=days[d]['dli_mol_m2_day'], coverage_status=days[d]['coverage_status'])
            for d in chosen]
    result = dict(value=None, candidate_value=None, value_rule=rule, days_used=used,
        days_not_used=[dict(local_date=d, reason='explicit_single_representative_day_rule')
                       for d in days if d not in chosen], fixed_over_horizon=None,
        status='unavailable', reasons=[], value_provenance=rule)
    if not used or any(d['value'] is None or d['coverage_status'] != 'complete' for d in used):
        result['reasons'] = ['selected_day_coverage_incomplete']
        return result
    values = [d['value'] for d in used]
    candidate = math.fsum(values)/len(values)
    if rule == 'declared_scenario':
        ref = evidence(position.get('scenario_source_ref'), base, hashes, 'scenario')
        source = read_json(Path(ref['path']))
        canonical_unit(source.get('unit'))
        candidate = number(require(position.get('scenario_value'), 'scenario_value_missing'), 'scenario_value', 0)
        if source.get('value') != candidate:
            raise StudyError('scenario_value_source_mismatch')
        result['scenario_source_ref'] = ref
    result['candidate_value'] = candidate
    # Even a one-day selection needs an explicit tolerance/evidence declaration;
    # an observed zero spread does not validate constancy over a future horizon.
    try:
        policy = require(position.get('fixed_horizon_tolerance'), 'fixed_horizon_tolerance_missing')
        canonical_unit(policy.get('unit'))
        if policy.get('spread_metric') != 'max_minus_min':
            raise Missing('fixed_horizon_spread_metric_unsupported')
        ref = evidence(policy.get('source_ref'), base, hashes, 'fixed_horizon_tolerance')
        limit = number(require(policy.get('value'), 'fixed_horizon_tolerance_missing'), 'spread_tolerance', 0)
    except Missing as exc:
        result['reasons'] = [str(exc)]
        return result
    spread = max(values)-min(values)
    result['fixed_horizon_check'] = dict(spread_metric='max_minus_min', observed_spread=spread,
        declared_tolerance=limit, unit=DLI_UNIT, source_ref=ref,
        interpretation='observed_days_test_under_declared_horizon_assumption_not_a_future_light_prediction')
    if spread > limit:
        result.update(fixed_over_horizon=False, reasons=['dli_not_constant_over_horizon'])
        return result
    if applicability is None:
        result['reasons'] = ['applicability_unavailable']
        return result
    if any(not applicability['min'] <= value <= applicability['max'] for value in values+[candidate]):
        result.update(status='out_of_applicability', reasons=['out_of_applicability'])
        return result
    result.update(value=candidate, fixed_over_horizon=True, status='available')
    return result
