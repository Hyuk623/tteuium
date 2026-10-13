"""Tray EC-equivalent accounting and explicitly gated response insertion API.

No uptake kinetics, EC response law or native plant-state mutation is supplied.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import math
from pathlib import Path
from typing import Callable, Any

from tools.vtc_growth_io import (ContractError, require, number, aware, digest,
                                 read_json, write_json, fresh_build, sha, write_csv)

SCHEMA = 'tray-reservoir-1'
EC_UNIT = 'mS/cm'
EQ_UNIT = 'mS/cm*L'
SOURCE_KINDS = {'measured', 'user_stated', 'user_assumed', 'assumed', 'derived',
                'fixture_declared', 'fitted', 'literature', 'unavailable'}
MM3_PER_L = 1_000_000.0
SCENARIOS = ('none', 'moderate', 'strong')


class Missing(ContractError):
    """An explicitly unavailable observation or scientific input."""


def evidence(row: dict, label: str) -> None:
    if not isinstance(row, dict) or row.get('source_kind') == 'unavailable':
        raise Missing(f'{label}: evidence unavailable')
    require(row.get('source_kind') in SOURCE_KINDS, f'{label}: source_kind required')
    require(isinstance(row.get('source_ref'), str) and bool(row['source_ref'].strip()),
            f'{label}: source_ref required')


def identity(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()) and value not in
            {'unavailable', 'n/a'} and not any(c in value for c in '\r\n'), label)
    return value


def quantity(row: dict | None, unit: str, label: str, bounds: bool = False) -> tuple[float, float]:
    if not isinstance(row, dict) or row.get('value') is None or row.get('status') == 'unavailable':
        raise Missing(f'{label}: unavailable')
    evidence(row, label)
    require(row.get('unit') == unit, f'{label}: expected {unit}')
    value = number(row['value'], label, 0)
    if bounds:
        if row.get('abs_error') is None:
            raise Missing(f'{label}: absolute uncertainty bound unavailable')
        evidence(row.get('uncertainty_evidence'), label + ' uncertainty')
        error = number(row['abs_error'], label + ' error', 0)
    else:
        error = 0.0
    return value, error


def context(request: dict) -> dict:
    require(request.get('schema_version') == SCHEMA, 'unsupported reservoir schema')
    sid = identity(request.get('scenario_id'), 'scenario_id required')
    return dict(schema_version=SCHEMA, scenario_id=sid, element_resolved=False,
                interval_start=request.get('interval_start'), interval_end=request.get('interval_end'),
                quantity_basis='EC_equivalent', biological_validation='not_established',
                native_causality=False, growth_feedback_applied=False)


def interval(row: dict) -> tuple:
    start, end = aware(row['interval_start']), aware(row['interval_end'])
    require(end > start, 'nonpositive interval')
    return start, end


def trays(rows: list[dict]) -> dict[str, dict]:
    require(isinstance(rows, list) and bool(rows), 'trays required')
    result, plants = {}, set()
    for row in rows:
        tid = identity(row.get('tray_id'), 'tray identity required')
        require(tid not in result, 'duplicate tray')
        require(type(row.get('has_plants')) is bool, 'has_plants must be boolean')
        ids = row.get('plant_ids')
        require(isinstance(ids, list), 'plant_ids list required')
        for pid in ids:
            identity(pid, 'plant identity required')
            require(pid not in plants, 'duplicate/cross-tray plant')
            plants.add(pid)
        require(bool(ids) == row['has_plants'], 'blank/planted membership mismatch')
        for field in ('inner_length_mm', 'inner_width_mm'):
            value, _ = quantity(row.get(field), 'mm', field)
            require(value > 0, 'positive internal dimensions required')
        value, _ = quantity(row.get('medium_volume_L'), 'L', 'medium_volume_L')
        require(value > 0, 'positive medium volume required')
        identity(row.get('medium_mix'), 'medium_mix required')
        result[tid] = deepcopy(row)
    return result


def _pool(row: dict | None, label: str) -> dict:
    if not isinstance(row, dict):
        raise Missing(label + ': initial solution state unavailable')
    water, _ = quantity(row.get('water_L'), 'L', label + ' water')
    solute, _ = quantity(row.get('ec_equivalent'), EQ_UNIT, label + ' solute')
    require(water > 0 or solute == 0, 'dry solution with dissolved stock')
    return dict(water_L=water, ec_equivalent=solute)


def replay(request: dict) -> dict:
    """Finite prescribed stocks; all events are applied on private candidate state."""
    out = context(request)
    try:
        registry = trays(request.get('trays'))
        start, end = interval(request)
        require(request.get('mixing_model') == 'well_mixed_each_solution', 'declare mixing model')
        evidence(request.get('mixing_evidence'), 'mixing')
        evidence(request.get('schedule_evidence'), 'complete prescribed event schedule')
        initial = request.get('initial')
        if not isinstance(initial, dict):
            raise Missing('initial state unavailable')
        require(set(initial) == set(registry), 'initial tray coverage mismatch')
        state = {}
        for tid, row in initial.items():
            stored, _ = quantity(row.get('stored_ec_equivalent'), EQ_UNIT, tid + ' stored pool')
            state[tid] = dict(reservoir=_pool(row.get('reservoir'), tid + ' reservoir'),
                              medium=_pool(row.get('medium'), tid + ' medium'), stored_ec_equivalent=stored)
        before = deepcopy(state)
        totals = {tid: dict(water_in=0.0, water_out=0.0, solute_in=0.0, solute_out=0.0,
                           prescribed_uptake=0.0, evaporation=0.0, plant_water=0.0) for tid in registry}
        events = request.get('events')
        require(isinstance(events, list), 'explicit complete event list required')
        previous, seen, ledger = start, set(), []
        for event in events:
            eid = identity(event.get('event_id'), 'event identity required')
            require(eid not in seen, 'duplicate event')
            seen.add(eid)
            at = aware(event['at'])
            require(previous <= at <= end, 'unordered/out-of-interval event')
            previous = at
            tid = event.get('tray_id')
            require(tid in state, 'unknown event tray')
            evidence(event, 'prescribed event')
            s, t = state[tid], totals[tid]
            kind = event.get('kind')
            solute = water = 0.0
            if kind in {'adsorb', 'release', 'uptake'}:
                solute, _ = quantity(event.get('ec_equivalent'), EQ_UNIT, kind)
                if kind == 'release':
                    require(solute <= s['stored_ec_equivalent'], 'stored pool overdraw')
                    s['stored_ec_equivalent'] -= solute
                    s['medium']['ec_equivalent'] += solute
                else:
                    require(solute <= s['medium']['ec_equivalent'], 'medium solute overdraw')
                    s['medium']['ec_equivalent'] -= solute
                    if kind == 'adsorb':
                        s['stored_ec_equivalent'] += solute
                    else:
                        require(registry[tid]['has_plants'] or solute == 0, 'blank cannot take up solute')
                        t['solute_out'] += solute
                        t['prescribed_uptake'] += solute
            elif kind in {'supply', 'remove', 'transfer', 'evaporate', 'plant_water'}:
                pool_id = event.get('pool')
                require(pool_id in {'reservoir', 'medium'}, 'solution pool required')
                pool = s[pool_id]
                water, _ = quantity(event.get('water_L'), 'L', kind)
                if kind == 'supply':
                    ec, _ = quantity(event.get('ec_ms_cm'), EC_UNIT, 'supply EC')
                    solute = water * ec
                    pool['water_L'] += water
                    pool['ec_equivalent'] += solute
                    t['water_in'] += water
                    t['solute_in'] += solute
                else:
                    require(water <= pool['water_L'], 'solution water overdraw')
                    if kind in {'remove', 'transfer'}:
                        solute = pool['ec_equivalent'] * water / pool['water_L'] if water else 0.0
                        pool['ec_equivalent'] -= solute
                    pool['water_L'] -= water
                    if kind == 'transfer':
                        other = event.get('to_pool')
                        require(other in {'reservoir', 'medium'} and other != pool_id, 'invalid transfer destination')
                        s[other]['water_L'] += water
                        s[other]['ec_equivalent'] += solute
                    else:
                        if kind == 'plant_water':
                            require(registry[tid]['has_plants'] or water == 0, 'blank cannot take up water')
                            t['plant_water'] += water
                        if kind == 'evaporate':
                            t['evaporation'] += water
                        t['water_out'] += water
                        t['solute_out'] += solute
            else:
                raise ContractError('unsupported event kind')
            for p in ('reservoir', 'medium'):
                for key, value in s[p].items():
                    number(value, key, 0)
                require(s[p]['water_L'] > 0 or s[p]['ec_equivalent'] == 0, 'dry-pool chemistry unavailable')
            number(s['stored_ec_equivalent'], 'stored stock', 0)
            ledger.append(dict(**out, tray_id=tid, event_id=eid, at=event['at'], kind=kind,
                               water_L=water, ec_equivalent=solute, state_sha256=digest(s)))
        closure = []
        for tid, s in state.items():
            a, t = before[tid], totals[tid]
            def total(v: dict, field: str) -> float:
                return math.fsum(v[p][field] for p in ('reservoir', 'medium'))
            wr = math.fsum([total(a, 'water_L'), t['water_in'], -t['water_out'], -total(s, 'water_L')])
            sr = math.fsum([total(a, 'ec_equivalent'), a['stored_ec_equivalent'], t['solute_in'],
                            -t['solute_out'], -total(s, 'ec_equivalent'), -s['stored_ec_equivalent']])
            number(wr, 'water closure'); number(sr, 'EC-equivalent closure')
            closure.append(dict(**out, tray_id=tid, water_residual_L=wr, ec_equivalent_residual=sr,
                                prescribed_uptake_ec_equivalent=t['prescribed_uptake'],
                                uptake_status='prescribed_not_observed', **t))
        return dict(**out, status='available_prescribed_accounting', initial_sha256=digest(before),
                    final_state=state, final_sha256=digest(state), events=ledger, closure=closure)
    except Missing as exc:
        return dict(**out, status='unavailable', reason=str(exc), final_state=None, uptake=None)


# Conservative absolute-bound arithmetic. No probability distribution is implied.
# Triples are (central value, lower bound, upper bound).
def bounded(row: dict | None, unit: str, label: str) -> tuple[float, float, float]:
    v, e = quantity(row, unit, label, bounds=True)
    return v, max(0.0, v-e), v+e


def _add(a: tuple, b: tuple) -> tuple:
    return tuple(a[i]+b[i] for i in range(3))


def _sub(a: tuple, b: tuple) -> tuple:
    return a[0]-b[0], a[1]-b[2], a[2]-b[1]


def _mul(a: tuple, b: tuple) -> tuple:
    corners = [x*y for x in a[1:] for y in b[1:]]
    return a[0]*b[0], min(corners), max(corners)


def _scaled(a: tuple, scalar: float) -> tuple:
    return tuple(v*scalar for v in a)


def _summary(a: tuple, unit: str) -> dict:
    for v in a:
        number(v, 'propagated bound')
    return dict(value=a[0], lower=a[1], upper=a[2], unit=unit,
                uncertainty_kind='conservative_absolute_bounds_not_probability_interval')


def observed_solution(tray: dict, row: dict) -> tuple[tuple, tuple]:
    """Measured pool depth is never substituted for medium-held water."""
    if not isinstance(row, dict):
        raise Missing('solution observation unavailable')
    length = bounded(tray.get('inner_length_mm'), 'mm', 'inner length')
    width = bounded(tray.get('inner_width_mm'), 'mm', 'inner width')
    depth = bounded(row.get('pool_depth_mm'), 'mm', 'pool depth')
    pool_water = _scaled(_mul(_mul(length, width), depth), 1/MM3_PER_L)
    ec = bounded(row.get('pool_ec_ms_cm'), EC_UNIT, 'pool EC')
    medium_water = bounded(row.get('medium_water_L'), 'L', 'medium-held water')
    medium_ec = bounded(row.get('medium_ec_ms_cm'), EC_UNIT, 'medium EC')
    return (_add(pool_water, medium_water),
            _add(_mul(pool_water, ec), _mul(medium_water, medium_ec)))


def _residual(tray: dict, record: dict) -> tuple[tuple, tuple]:
    v0, d0 = observed_solution(tray, record.get('start'))
    v1, d1 = observed_solution(tray, record.get('end'))
    iw = bounded(record.get('supplied_water_L'), 'L', 'supplied water')
    ow = bounded(record.get('removed_water_L'), 'L', 'removed water')
    iq = bounded(record.get('supplied_ec_equivalent'), EQ_UNIT, 'supplied EC-equivalent')
    oq = bounded(record.get('removed_ec_equivalent'), EQ_UNIT, 'removed EC-equivalent')
    return _sub(_sub(iw, ow), _sub(v1, v0)), _sub(_sub(iq, oq), _sub(d1, d0))


def estimate(request: dict) -> dict:
    """Blank-adjusted signed residuals, conditional on explicit comparability."""
    out = context(request)
    try:
        registry = trays(request.get('trays'))
        interval(request)
        require(request.get('uncertainty_mode') == 'absolute_bounds', 'declare absolute uncertainty bounds')
        blank_id = request.get('blank_tray_id')
        if blank_id not in registry or registry[blank_id]['has_plants']:
            raise Missing('independent plant-free blank tray unavailable')
        records = request.get('observations')
        if not isinstance(records, dict):
            raise Missing('observations unavailable')
        if set(records) != set(registry):
            raise Missing('complete tray observations unavailable')
        for tid, record in records.items():
            require(record.get('tray_id') == tid, 'observation tray binding mismatch')
            require(interval(record) == interval(request), 'observation interval mismatch')
            evidence(record, 'observation record')
        bv, bq = _residual(registry[blank_id], records[blank_id])
        if bv[0] < 0:
            raise Missing('blank water residual negative; evaporation interpretation unsupported')
        result = []
        for tid, tray in registry.items():
            if tid == blank_id:
                result.append(dict(**out, tray_id=tid, status='blank_reference', uptake_ec_equivalent=None,
                                   plant_uptake_constraint=0.0, zero_basis='declared_no_plants_not_independent_validation',
                                   net_adsorption_minus_release=_summary(bq, EQ_UNIT),
                                   evaporation_residual=_summary(bv, 'L')))
                continue
            require(tray['has_plants'], 'additional blanks need separate explicit comparisons')
            comparison = request.get('comparisons', {}).get(tid)
            if not isinstance(comparison, dict):
                raise Missing('blank comparability declaration unavailable')
            evidence(comparison, 'blank comparability')
            require(comparison.get('blank_tray_id') == blank_id, 'wrong comparison blank')
            require(comparison.get('same_medium_and_supply') is True, 'same medium/supply must be evidenced')
            require(tray['medium_mix'] == registry[blank_id]['medium_mix'], 'medium mix mismatch')
            require(comparison.get('exchange_scaling') == 'medium_volume_ratio', 'declare medium-volume scaling')
            pv = bounded(tray.get('medium_volume_L'), 'L', 'planted medium volume')
            blank_volume = bounded(registry[blank_id].get('medium_volume_L'), 'L', 'blank medium volume')
            require(blank_volume[1] > 0, 'blank medium volume bounds include zero')
            k = _mul(pv, (1/blank_volume[0], 1/blank_volume[2], 1/blank_volume[1]))
            k_evap = bounded(comparison.get('evaporation_scale'), 'dimensionless', 'evaporation scale')
            require(comparison.get('blank_evaporation_is_upper_bound') is True, 'evaporation bound assumption required')
            # Explicit discrepancy bounds are required, even if the caller declares zero.
            mismatch_q, _ = quantity(comparison.get('exchange_discrepancy_bound'), EQ_UNIT, 'exchange discrepancy')
            mismatch_v, _ = quantity(comparison.get('evaporation_discrepancy_bound'), 'L', 'evaporation discrepancy')
            v, q = _residual(tray, records[tid])
            uptake = _sub(q, _mul(k, bq))
            uptake = uptake[0], uptake[1]-mismatch_q, uptake[2]+mismatch_q
            water = _sub(v, _mul(k_evap, bv))
            water = water[0], water[1]-mismatch_v, water[2]+mismatch_v
            valid = uptake[0] >= 0
            result.append(dict(**out, tray_id=tid, status='conditional_estimate' if valid else 'unavailable_negative_residual',
                               uptake_ec_equivalent=uptake[0] if valid else None,
                               signed_uptake_residual=_summary(uptake, EQ_UNIT),
                               water_uptake_lower_estimate=_summary(water, 'L'),
                               water_uptake_status='conditional_lower_estimate' if water[0] >= 0 else 'unavailable_negative_residual',
                               blank_exchange_scale=_summary(k, 'dimensionless'),
                               blank_net_adsorption_minus_release=_summary(bq, EQ_UNIT),
                               evaporation_bias='blank_overestimate_biases_plant_water_uptake_downward',
                               source_kind='derived', source_ref=comparison['source_ref']))
        return dict(**out, status='conditional_residuals', rows=result,
                    initial_stored_pools='unidentified_not_fitted',
                    exchange_direction='net_only_individual_adsorption_and_release_unidentified')
    except Missing as exc:
        return dict(**out, status='unavailable', reason=str(exc), uptake_ec_equivalent=None, rows=[])


def modelled_split(tray: dict, uptake: dict, demand: dict) -> dict:
    """A distribution of an existing tray total, never measured per-plant uptake."""
    out = dict(tray_id=tray['tray_id'], scenario_id=uptake['scenario_id'], element_resolved=False,
               quantity_basis='EC_equivalent', allocation_kind='modelled_split', source_kind='derived')
    require(uptake.get('tray_id') == tray['tray_id'], 'uptake/tray identity mismatch')
    if uptake.get('uptake_ec_equivalent') is None:
        return dict(**out, status='unavailable', rows=[], reason='tray uptake unavailable')
    amount = number(uptake['uptake_ec_equivalent'], 'tray uptake', 0)
    require(tray['has_plants'] and bool(tray['plant_ids']), 'plant split requires planted tray')
    require(demand.get('scenario_id') == uptake['scenario_id'], 'demand scenario mismatch')
    require(demand.get('interval_start') == uptake.get('interval_start') and
            demand.get('interval_end') == uptake.get('interval_end') and
            bool(demand.get('interval_start')), 'demand interval binding required')
    interval(demand)
    evidence(demand, 'modelled demand')
    identity(demand.get('unit'), 'common demand unit required')
    weights = demand.get('values')
    require(isinstance(weights, dict) and set(weights) == set(tray['plant_ids']) and
            len(tray['plant_ids']) == len(set(tray['plant_ids'])), 'plant demand coverage mismatch')
    values = {pid: number(v, 'modelled demand', 0) for pid, v in weights.items()}
    total = number(math.fsum(values.values()), 'total demand', 0)
    if total == 0 and amount > 0:
        return dict(**out, status='unavailable', rows=[], reason='positive uptake with zero modelled demand')
    return dict(**out, status='conditional_modelled_split', rows=[dict(**out, plant_instance_id=pid,
        uptake_ec_equivalent=amount*(v/total) if total else 0.0, unit=EQ_UNIT,
        source_ref=demand['source_ref']) for pid, v in values.items()])


def validate_registry(registry: dict) -> None:
    """Metadata is necessary, not sufficient evidence of scientific acceptance."""
    if not isinstance(registry, dict):
        raise Missing('response registry unavailable')
    require(registry.get('schema_version') == 'tray-nutrient-response-registry-1', 'response registry schema')
    for field in ('law_id', 'law_version', 'ec_input_definition', 'time_support', 'temperature_convention',
                  'deficiency_equation', 'high_ec_equation', 'breakpoint_definitions', 'domain',
                  'exchange_contract_ref', 'initial_pool_contract_ref'):
        if not registry.get(field):
            raise Missing('registry field unavailable: ' + field)
    require(registry.get('ec_unit') == EC_UNIT, 'response EC unit mismatch')
    require(registry.get('coupling_site') == 'gross_assimilation_once_before_allocation', 'wrong coupling site')
    review = registry.get('review')
    evidence(review, 'response review')
    require(review.get('status') in {'accepted_scenario_contract', 'fixture_only'}, 'response not accepted')
    require(registry.get('fixture') is True or review['status'] != 'fixture_only', 'fixture registry mislabelled')
    require(set(registry.get('scenarios', {})) == set(SCENARIOS), 'separate none/moderate/strong required')
    for sid, records in registry['scenarios'].items():
        require(isinstance(records, dict) and bool(records), 'complete explicit parameter records required')
        for key, record in records.items():
            evidence(record, sid + '/' + key)
            if record.get('value') is None:
                raise Missing('parameter unavailable: ' + key)
            number(record['value'], key)
            identity(record.get('unit'), 'parameter unit required')
            require(record.get('uncertainty') is not None, 'parameter uncertainty required')


def response_diagnostic(ec: dict | None, scenario_id: str, registry: dict | None = None,
                        evaluator: Callable | None = None, evaluator_law: tuple | None = None,
                        evaluate: bool = False) -> dict:
    """Inject a reviewed equation later; output cannot enable native feedback."""
    require(scenario_id in SCENARIOS, 'unknown severity scenario')
    base = dict(scenario_id=scenario_id, growth_feedback_applied=False, native_causality=False,
                element_resolved=False, biological_validation='not_established')
    if not evaluate or scenario_id == 'none':
        return dict(**base, status='disabled_reference', f_nut=None, engine_action='unchanged')
    try:
        validate_registry(registry)
        value, _ = quantity(ec, EC_UNIT, 'response EC')
        require(ec.get('input_definition') == registry['ec_input_definition'] and
                ec.get('time_support') == registry['time_support'] and
                ec.get('temperature_convention') == registry['temperature_convention'], 'response EC semantics mismatch')
        if evaluator is None:
            raise Missing('registered executable response evaluator unavailable')
        require(evaluator_law == (registry['law_id'], registry['law_version']), 'response law ID/version mismatch')
        factor = number(evaluator(value, scenario_id, deepcopy(registry)), 'f_nut', 0)
        require(factor <= 1, 'f_nut exceeds one')
        return dict(**base, status='diagnostic_only', f_nut=factor, registry_sha256=digest(registry),
                    fixture=registry.get('fixture') is True, engine_action='no_native_hook')
    except Missing as exc:
        return dict(**base, status='unavailable', f_nut=None, reason=str(exc))


def feedback_gate(enable: bool = False) -> dict:
    require(type(enable) is bool, 'feedback flag must be boolean')
    require(not enable, 'native nutrient causality unavailable: reviewed law and accepted native joint commit required')
    return dict(ENABLE_NUTRIENT_FEEDBACK=False, engine_action='unchanged')


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['replay', 'estimate', 'audit-records', 'records-estimate'])
    p.add_argument('--request', type=Path)
    p.add_argument('--tray-spec', type=Path)
    p.add_argument('--log', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    try:
        if a.command == 'records-estimate':
            require(a.log is not None and a.tray_spec is not None and a.request is not None,
                    '--log, --tray-spec, --request (supplement) required')
            from tools.nutrient_reservoir_records import records_estimate
            result = records_estimate(a.log, a.tray_spec, read_json(a.request))
            result['status'] = result['result']['status']
        elif a.command == 'audit-records':
            require(a.log is not None, '--log required')
            from tools.nutrient_reservoir_records import audit_records
            result = audit_records(a.log, a.tray_spec)
        else:
            require(a.request is not None, '--request required')
            result = (replay if a.command == 'replay' else estimate)(read_json(a.request))
        output = fresh_build(a.out)
        write_json(output/'result.json', result)
        flat = result.get('closure') or result.get('normalized_rows')
        if flat:
            write_csv(output/'rows.csv', flat)
        write_json(output/'manifest.json', dict(command=a.command,
            sources={str(f.resolve()): sha(f) for f in (a.request, a.tray_spec, a.log) if f is not None},
            code_sha256={name: sha(Path(__file__).with_name(name)) for name in
                         ('nutrient_reservoir.py', 'nutrient_reservoir_records.py',
                          'nutrient_reservoir_transaction.py', 'vtc_growth_io.py')},
            result_sha256=sha(output/'result.json'),
            biological_validation='not_established', native_causality=False))
        print(result['status'])
    except (ContractError, ValueError, KeyError, TypeError) as exc:
        p.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    main()
