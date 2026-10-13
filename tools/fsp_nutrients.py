"""Fertilizer formulation and two-layer nutrient accounting CLI.

All numerical biology remains externally prescribed; see tools/FSP_NUTRIENTS.md.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import json
from pathlib import Path
from typing import Any

from tools.leaf_light.common import (StudyError, digest, file_hash, output_dir,
                                    read_json, write_json)
from tools.nutrient_contract import SCHEMA, Unavailable, species, science_readiness, time
from tools.nutrient_composition import formulate
from tools.nutrient_balance import EVENT_FIELDS, simulate
from tools.nutrient_fsp_bridge import compute_with_nutrients

EVENT_COLUMNS = ('scenario_id', 'plant_instance_id', 'event_id', 'at', 'kind', 'layer_id',
                 'from_layer_id', 'to_layer_id', 'batch_id', 'water_ml', 'organ_id',
                 'evidence_kind', 'source_ref', 'assumption')
OBS_COLUMNS = ('observation_id', 'plant_instance_id', 'at', 'metric', 'value', 'unit',
               'evidence_kind', 'source_ref', 'assumption')


def _csv(path: Path, columns: tuple[str, ...]) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(columns):
            raise StudyError(f'{path.name}: exact documented CSV header required')
        result = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in result):
        raise StudyError('Malformed CSV row')
    return result


def _numeric_cell(value: str) -> float | None:
    if not value.strip():
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise StudyError('Invalid CSV numeric value') from exc


def _ev(row: dict) -> dict | None:
    if not row['evidence_kind'] and not row['source_ref'] and not row['assumption']:
        return None
    return dict(kind=row['evidence_kind'], source_ref=row['source_ref'], assumption=row['assumption'])


def load_scenario(path: Path) -> tuple[dict, dict]:
    """Resolve explicit CSV refs read-only; retain physical file and row lineage."""
    path = path.resolve()
    request = read_json(path)
    if not isinstance(request, dict):
        raise StudyError('Scenario object required')
    hashes = {str(path): file_hash(path)}
    scope = species(request.get('tracked_species'))
    for field in ('events', 'observations'):
        reference = request.pop(field + '_file', None)
        if reference is None:
            continue
        if field in request:
            raise StudyError('Use either inline records or CSV reference, never both')
        if not isinstance(reference, str) or not reference:
            raise StudyError('CSV reference must be a nonempty path')
        ref = (path.parent / reference).resolve()
        sha = file_hash(ref)
        hashes[str(ref)] = sha
        columns = EVENT_COLUMNS + tuple(s + '_mg' for s in scope) if field == 'events' else OBS_COLUMNS
        loaded = []
        for row_number, row in enumerate(_csv(ref, columns), 2):
            ev = _ev(row)
            if ev is not None:
                ev.update(record_file_sha256=sha, record_row=row_number)
            if field == 'events':
                if row['scenario_id'] != request.get('scenario_id') or row['plant_instance_id'] != request.get('plant_instance_id'):
                    raise StudyError('CSV event context mismatch')
                kind = row['kind']
                if kind not in EVENT_FIELDS:
                    raise StudyError('Unsupported CSV event kind')
                data = dict(event_id=row['event_id'], at=row['at'], kind=kind, evidence=ev)
                for key in ('layer_id', 'from_layer_id', 'to_layer_id', 'batch_id', 'organ_id', 'water_ml'):
                    if key in EVENT_FIELDS[kind]:
                        data[key] = _numeric_cell(row[key]) if key == 'water_ml' else row[key]
                    elif row[key]:
                        raise StudyError('Irrelevant CSV event field must be blank')
                if 'nutrient_mg' in EVENT_FIELDS[kind]:
                    data['nutrient_mg'] = {s: _numeric_cell(row[s + '_mg']) for s in scope}
                elif any(row[s + '_mg'] for s in scope):
                    raise StudyError('Transport solutes are computed, not separately supplied')
            else:
                data = {k: row[k] for k in ('observation_id', 'plant_instance_id', 'at', 'metric', 'unit')}
                data.update(value=_numeric_cell(row['value']), evidence=ev)
            loaded.append(data)
        request[field] = loaded
    return request, hashes


def code_hashes() -> dict:
    root = Path(__file__).resolve().parent
    paths = [root / name for name in ('fsp_nutrients.py', 'nutrient_contract.py',
        'nutrient_composition.py', 'nutrient_balance.py', 'nutrient_fsp_bridge.py',
        'fsp_nutrients_demo.py', 'fsp_carbon_diagnostic.py', 'leaf_light/common.py')]
    return {str(p): file_hash(p) for p in paths}


def write_csv(path: Path, rows: list[dict], columns: tuple[str, ...] | list[str]) -> None:
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='raise')
        writer.writeheader()
        writer.writerows(rows)  # None is a blank cell; numeric zero stays zero.


def save_result(out: Path, result: dict, input_files: dict) -> None:
    write_json(out / 'result.json', result)
    state_rows = result.get('layer_states', [])
    if state_rows:
        write_csv(out / 'layer_states.csv', state_rows, list(state_rows[0]))
    event_rows = []
    water_rows = []
    for event in result.get('events', []):
        context = {k: event[k] for k in ('scenario_id', 'plant_instance_id', 'source_plant_id',
            'event_id', 'at', 'kind', 'elapsed_seconds', 'source_event_hash', 'layer_id',
            'from_layer_id', 'to_layer_id', 'batch_id', 'organ_id')}
        provenance = dict(evidence_kind=event['evidence']['kind'], source_ref=event['evidence']['source_ref'])
        water_rows.append(dict(**context, water_ml=event['water_ml'],
                               water_residual_ml=event['water_residual_ml'], **provenance))
        for s, amount in event['nutrient_mg'].items():
            event_rows.append(dict(**context, species=s, nutrient_mg=amount,
                                  nutrient_residual_mg=event['nutrient_residual_mg'][s], **provenance))
    if event_rows:
        write_csv(out / 'event_ledger.csv', event_rows, list(event_rows[0]))
        write_csv(out / 'water_ledger.csv', water_rows, list(water_rows[0]))
    if result.get('concentration_mg_L'):
        rows = [dict(batch_id=result['batch_id'], species=s, element_mass_mg=result['element_mass_mg'][s],
                     concentration_mg_L=value, concentration_mmol_element_L=result['concentration_mmol_element_L'][s],
                     quantity_basis='mg_element') for s, value in result['concentration_mg_L'].items()]
        write_csv(out / 'formulation.csv', rows, list(rows[0]))
    if result.get('comparison_rows'):
        rows = result['comparison_rows']
        write_csv(out / 'scenario_comparison.csv', rows, list(rows[0]))
    write_json(out / 'provenance.json', dict(schema_version=SCHEMA, input_files=input_files,
        code_hashes=code_hashes(), result_hash=digest(result),
        files={p.name: file_hash(p) for p in out.iterdir() if p.is_file()}))


def compare_scenarios(requests: list[dict]) -> dict:
    """Compare supplied scenarios, not automatically fitted probability samples."""
    if not isinstance(requests, list) or not requests:
        raise StudyError('Nonempty scenario list required')
    ids = [r.get('scenario_id') for r in requests]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise StudyError('Comparison requires distinct scenario IDs')
    baseline = requests[0]
    for r in requests[1:]:
        for key in ('source_plant_id', 'tracked_species'):
            if r.get(key) != baseline.get(key):
                raise StudyError('Scenario comparison scope mismatch: ' + key)
        for key in ('t_start', 't_end'):
            if time(r.get(key), key) != time(baseline.get(key), key):
                raise StudyError('Comparison intervals must match')
    results = [simulate(r) for r in requests]
    rows = []
    for request, result in zip(requests, results):
        for s in request['tracked_species']:
            valid = result['status'] == 'available'
            rows.append(dict(scenario_id=request['scenario_id'], plant_instance_id=request['plant_instance_id'],
                species=s, status=result['status'], reason=result.get('reason'),
                irrigation_mg=result['totals']['irrigation_nutrient_mg'][s] if valid else None,
                prescribed_uptake_mg=result['totals']['prescribed_uptake_mg'][s] if valid else None,
                root_zone_dissolved_mg=sum(l['dissolved_mg'][s] for l in result['final_state']['layers'].values()) if valid else None,
                root_zone_retained_mg=sum(l['retained_mg'][s] for l in result['final_state']['layers'].values()) if valid else None,
                constrained_growth=None))
    return dict(schema_version=SCHEMA, status='available' if all(r['status'] == 'available' for r in results) else 'partial',
                scenario_results=results, comparison_rows=rows,
                interpretation='declared_scenario_comparison_not_calibrated_uncertainty',
                growth_constraints=science_readiness(), validated_nutrient_model=False)


def write_input_bundle(out: Path, request: dict) -> None:
    """Keep event/observation tables in CSV; metadata and recipes in JSON."""
    config = deepcopy(request)
    scope = config['tracked_species']
    rows = []
    for ev in config.pop('events'):
        row = {k: '' for k in EVENT_COLUMNS + tuple(s + '_mg' for s in scope)}
        row.update(scenario_id=config['scenario_id'], plant_instance_id=config['plant_instance_id'])
        row.update({k: v for k, v in ev.items() if k in EVENT_COLUMNS})
        info = ev.get('evidence') or {}
        row.update(evidence_kind=info.get('kind'), source_ref=info.get('source_ref'), assumption=info.get('assumption'))
        row.update({s + '_mg': v for s, v in ev.get('nutrient_mg', {}).items()})
        rows.append(row)
    write_csv(out / 'events.csv', rows, EVENT_COLUMNS + tuple(s + '_mg' for s in scope))
    observations = []
    for ob in config.pop('observations'):
        info = ob.get('evidence') or {}
        observations.append({**{k: ob.get(k) for k in OBS_COLUMNS if k not in {'evidence_kind', 'source_ref', 'assumption'}},
            'evidence_kind': info.get('kind'), 'source_ref': info.get('source_ref'), 'assumption': info.get('assumption')})
    write_csv(out / 'observations.csv', observations, OBS_COLUMNS)
    config.update(events_file='events.csv', observations_file='observations.csv')
    write_json(out / 'scenario.json', config)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('templates', 'demo', 'formulate', 'audit', 'simulate', 'compare', 'fsp'):
        sub = commands.add_parser(command)
        sub.add_argument('--out', type=Path, required=True)
        if command == 'formulate':
            sub.add_argument('--recipe', type=Path, required=True)
        if command in {'audit', 'simulate'}:
            sub.add_argument('--scenario', type=Path, required=True)
        if command == 'compare':
            sub.add_argument('--scenarios', type=Path, nargs='+', required=True)
        if command == 'fsp':
            sub.add_argument('--request', type=Path, required=True)
            sub.add_argument('--scenario', type=Path)
            sub.add_argument('--enabled', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command in {'templates', 'demo'}:
            from tools.fsp_nutrients_demo import blank_template, synthetic_scenario
            out = output_dir(args.out)
            if args.command == 'templates':
                write_input_bundle(out, blank_template())
                write_json(out / 'science_readiness.json', science_readiness())
            else:
                requests = []
                for label, dose, p_percent in [('baseline', .1, 10.0), ('double_dose', .2, 10.0),
                                              ('different_ratio', .1, 20.0), ('uptake_assumption', .1, 10.0)]:
                    case = synthetic_scenario()
                    case['scenario_id'] = label
                    case['recipes'][0]['doses'][0]['amount'] = dose
                    case['recipes'][0]['products'][0]['labels'][3]['value'] = p_percent
                    if label == 'uptake_assumption':
                        for event in case['events']:
                            if event['kind'] == 'uptake':
                                event['nutrient_mg'] = {s: .2 for s in case['tracked_species']}
                    case_out = out / label
                    case_out.mkdir()
                    write_input_bundle(case_out, case)
                    # Replay the written CSV to exercise the same path as real inputs.
                    loaded, hashes = load_scenario(case_out / 'scenario.json')
                    requests.append(loaded)
                    save_result(case_out, simulate(loaded), hashes)
                save_result(out, compare_scenarios(requests), {})
                from tools.fsp_carbon_diagnostic_demo import synthetic_request
                p4 = synthetic_request()
                case = synthetic_scenario()
                fsp_dir = out / 'fsp'
                fsp_dir.mkdir()
                write_json(fsp_dir / 'p4_request.json', p4)
                write_input_bundle(fsp_dir, case)
                save_result(fsp_dir, compute_with_nutrients(p4, case, enabled=True), {})
            print(f'{args.command}: {out}')
            return
        inputs = {}
        if args.command == 'formulate':
            result = formulate(read_json(args.recipe))
            inputs[str(args.recipe.resolve())] = file_hash(args.recipe)
        elif args.command in {'simulate', 'audit'}:
            request, inputs = load_scenario(args.scenario)
            result = simulate(request)
            if args.command == 'audit':
                result = dict(schema_version=SCHEMA, accounting_status=result['status'],
                    reason=result.get('reason'), detail=result.get('detail'), input_hash=digest(request),
                    scientific_readiness=science_readiness(), validated_nutrient_model=False)
        elif args.command == 'compare':
            requests = []
            for path in args.scenarios:
                request, hashes = load_scenario(path)
                requests.append(request)
                inputs.update(hashes)
            result = compare_scenarios(requests)
        else:
            request = read_json(args.request)
            inputs[str(args.request.resolve())] = file_hash(args.request)
            scenario = None
            if args.enabled and args.scenario:
                scenario, hashes = load_scenario(args.scenario)
                inputs.update(hashes)
            result = compute_with_nutrients(request, scenario, enabled=args.enabled)
        out = output_dir(args.out)
        save_result(out, result, inputs)
        print(f'{args.command}: {out}')
    except (StudyError, Unavailable, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f'{type(exc).__name__}: {exc}\n')


if __name__ == '__main__':
    main()
