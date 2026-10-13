"""Micro-Tom parameter registry and its mapping onto the V3 request `parameters` block.

python -X utf8 -m tools.microtom_parameters --help

The registry (`tools/microtom_parameters.csv`) holds priors, not fitted values: every row carries a
`source_kind` and a source reference, no row is `measured`, and rows the V3 engine cannot express
(`inactive_in_engine`, `engine_default_retained`, `candidate`, `layer_only`) never reach a request.
This module never edits `tools/vtc_development*`; it reads V3's parameter list at runtime (capability
check, B6) and only produces the override dictionary that a request JSON accepts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.vtc_development_io import PARAMS as ENGINE_PARAMS
from tools.vtc_growth_io import ROOT, ContractError, require, sha

REGISTRY_PATH = ROOT / 'tools' / 'microtom_parameters.csv'
ENGINE_FILES = (ROOT / 'tools' / 'vtc_development_io.py', ROOT / 'tools' / 'vtc_development_native.rgg')
COLUMNS = ('key', 'value', 'unit', 'source_kind', 'source_ref', 'cultivar', 'uncertainty',
           'uncertainty_kind', 'candidates', 'engine_key', 'engine_status', 'note')
# Layer vocabulary (binding rule 1 of the work order + MTG A1.2 `user_stated` for set-points).
SOURCE_KINDS = ('measured', 'literature_other_cultivar', 'literature_wild_species', 'user_assumed',
                'user_stated', 'unavailable',
                'fixture_declared',   # F9: a hidden-state value declared by a stress fixture for software verification; never a plant value
                'model_property')     # F9: a property of the model found by a sweep (e.g. a threshold); publishable, never adopted as a value
# Exactly what vtc_development_io.load_package accepts for a request parameter (verified 2026-10-11).
ENGINE_SOURCE_KINDS = ('user_assumed', 'synthetic_assumed', 'literature_other_cultivar')
ENGINE_STATUS = ('active', 'inactive_in_engine', 'engine_default_retained', 'layer_only', 'environment', 'candidate', 'axis', 'blocked_engine_extension',
                 'hidden_state')  # F9: engine plant_initialization value the forecast layer passes through unchanged (declared on the engine side)
AXIS_PARAMETERS = ('SUBSTEM_SINK_SCALE', 'APPLY_DETERMINATE_STOP')  # exactly the per-axis set fsp_axes.validate_records requires
UNCERTAINTY_KINDS = ('candidate_set', 'scenario_set', 'unavailable')
SCENARIO_LABELS = ('low', 'base', 'high')  # F8: a declared scenario set is reported side by side, never pooled or drawn
UNAVAILABLE = 'unavailable'
ACCOUNTING_ONLY = ('AREA_CORRECTION',)  # never optical geometry, even when the engine exposes the key


def _json(text: str, key: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractError(f'registry value is not JSON for {key}: {text!r}') from exc


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    """Read and validate the registry as written (static statuses). Raises ContractError on any provenance gap."""
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        require(tuple(reader.fieldnames or ()) == COLUMNS, f'registry header must be {",".join(COLUMNS)}')
        rows = list(reader)
    require(bool(rows), 'empty registry')
    keys = [r['key'] for r in rows]
    require(len(set(keys)) == len(keys), 'duplicate registry key')
    out = []
    for r in rows:
        key = r['key']
        require(bool(key) and bool(r['unit']) and bool(r['source_ref']), f'unit and source_ref required: {key}')
        require(r['source_kind'] in SOURCE_KINDS, f'unknown source_kind for {key}: {r["source_kind"]}')
        require(r['source_kind'] != 'measured', f'registry row claims measured: {key}')
        require(r['engine_status'] in ENGINE_STATUS, f'unknown engine_status for {key}')
        require(r['uncertainty_kind'] in UNCERTAINTY_KINDS, f'unknown uncertainty_kind for {key}')
        require(bool(r['uncertainty']), f'uncertainty text required (V3 rejects empty): {key}')
        value = _json(r['value'], key)
        candidates = _json(r['candidates'], key) if r['candidates'] else None
        if r['uncertainty_kind'] == 'candidate_set':
            require(isinstance(candidates, list) and len(candidates) >= 2, f'candidate_set needs >= 2 candidates: {key}')
            require(value in candidates, f'declared value must be one of its candidates: {key}')
        elif r['uncertainty_kind'] == 'scenario_set':
            require(isinstance(candidates, list) and len(candidates) == 3 and candidates == sorted(candidates), f'scenario_set needs 3 ascending values (low/base/high): {key}')
            require(value == candidates[1], f'declared value must be the base (middle) scenario: {key}')
            require(r['engine_status'] == 'axis', f'scenario_set is defined for axis rows only today: {key}')
        else:
            require(candidates is None, f'candidates given without candidate_set: {key}')
        if r['engine_status'] in ('active', 'engine_default_retained'):
            require(r['engine_key'] in ENGINE_PARAMS, f'engine_key is not a V3 parameter: {key} -> {r["engine_key"]!r}')
        if r['engine_status'] == 'inactive_in_engine':
            require(bool(r['engine_key']), f'inactive row needs the hook name it waits for: {key}')
        if r['engine_status'] == 'active':
            require(value != UNAVAILABLE, f'active row cannot be unavailable: {key}')
            require(r['source_kind'] in ENGINE_SOURCE_KINDS, f'active row source_kind not accepted by V3: {key}')
        if r['engine_status'] == 'engine_default_retained':
            require(value == UNAVAILABLE and r['source_kind'] == UNAVAILABLE, f'retained row must be unavailable: {key}')
        if r['engine_status'] == 'environment':
            require(r['engine_key'], f'environment row needs a target column: {key}')
        if r['engine_status'] == 'axis':
            require(r['engine_key'] == f'axes[].parameters.{key}' and key in AXIS_PARAMETERS, f'axis row must map to a per-axis fsp-axes-1 parameter: {key}')
            require(value != UNAVAILABLE and r['source_kind'] in ENGINE_SOURCE_KINDS, f'axis row needs an engine-accepted value: {key}')
        if r['engine_status'] == 'blocked_engine_extension':
            require(value == UNAVAILABLE and r['source_kind'] == UNAVAILABLE and 'LOG' in r['note'], f'blocked row must be unavailable with a LOG request: {key}')
        if r['engine_status'] == 'hidden_state':
            require(bool(r['engine_key']) and r['uncertainty_kind'] != 'candidate_set', f'hidden_state row needs its engine field and is never drawn: {key}')
            require(r['source_kind'] in ('user_assumed', 'synthetic_assumed', 'user_stated', UNAVAILABLE), f'hidden_state row source_kind must say it is unmeasured: {key}')
        if r['source_kind'] == 'model_property':
            require(r['engine_status'] == 'layer_only' and 'adopt' in r['note'], f'model_property row is layer_only and must state it is never adopted: {key}')
        if r['source_kind'] == 'fixture_declared':
            require(r['engine_status'] == 'layer_only', f'fixture_declared values live in stress fixtures, not in engine rows: {key}')
        if r['source_kind'] == UNAVAILABLE:
            require(value == UNAVAILABLE, f'unavailable source with a numeric value: {key}')
        out.append({**r, 'value': value, 'candidates': candidates, 'static_engine_status': r['engine_status']})
    return out


def registry_hash(path: Path = REGISTRY_PATH) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def engine_capabilities(engine_params: set[str] | None = None) -> dict:
    """What the V3 boundary exposes right now: its parameter key set and the hashes of the files that define it."""
    params = set(ENGINE_PARAMS) if engine_params is None else set(engine_params)
    return dict(parameter_keys=sorted(params), n_parameters=len(params),
                engine_version={p.name: sha(p) for p in ENGINE_FILES if p.exists()} if engine_params is None else {'fixture': 'supplied parameter list'},
                source='tools.vtc_development_io.PARAMS at runtime' if engine_params is None else 'fixture')


HOOK_METADATA = {  # declarations (labels), not values: what the owner's hook contract needs beside the registry value
    'AREA_CORRECTION': {'area_basis': 'summed_one_sided_full_outline_lamina_m2'},
}
HOOK_OWNER_NOTICE = ('Codex LOG 2026-10-11: do NOT auto-enable from PARAMS membership alone; CURVE_RATIO needs an exact-count vector or '
                     'by_segment_count for every PAIRS count (no [1,2,2] truncation), BENT_FRACTION needs numeric value + templates, '
                     'AREA_CORRECTION needs area_basis; defer enabled-hook execution until the owner RESULT')


def hook_contract_check(row: dict, pairs_value: list) -> str | None:
    """Validate a would-be hook entry against the owner's contract (`tools.fsp_extensions.hook_settings`); None = OK, else reason."""
    try:
        from tools.fsp_extensions import hook_settings
    except ImportError:
        return 'owner hook contract (tools.fsp_extensions.hook_settings) not importable'
    entry = dict(value=row['value'], **HOOK_METADATA.get(row['key'], {}))
    params = {row['engine_key']: entry, 'PAIRS': dict(value=pairs_value)}
    try:
        hook_settings(params)
    except Exception as exc:  # ContractError or ValueError from the owner's checker
        return f'hook contract not satisfied: {exc}'
    return None


def resolve_engine_capabilities(registry: list[dict], engine_params: set[str] | None = None, allow_hook_activation: bool = False,
                                pairs_value: list | None = None) -> tuple[list[dict], dict]:
    """B6: switch `inactive_in_engine` rows to `active` when V3's parameter list exposes their hook AND the owner's
    hook contract accepts the registry value AND activation is explicitly allowed (`--enable-hooks`).

    Decisions, in order: `inactive_hook_absent`; `inactive_hook_present_value_unavailable`;
    `inactive_hook_present_contract_unmet` (reason recorded); `inactive_hook_present_activation_deferred` (owner notice,
    default); `activated_by_capability_check`. Returns a new registry (never mutates the input) and a report.
    """
    caps = engine_capabilities(engine_params)
    present = set(caps['parameter_keys'])
    pairs_value = pairs_value or next((r['value'] for r in registry if r['engine_key'] == 'PAIRS'), [1, 1, 2])
    out, decisions = [], []
    for r in registry:
        row = dict(r)
        if r['static_engine_status'] == 'inactive_in_engine':
            hook = r['engine_key']; reason = ''
            if hook not in present:
                decision = 'inactive_hook_absent'
            elif row['value'] == UNAVAILABLE or r['source_kind'] not in ENGINE_SOURCE_KINDS:
                decision = 'inactive_hook_present_value_unavailable'
            else:
                reason = hook_contract_check(row, pairs_value) or ''
                if reason:
                    decision = 'inactive_hook_present_contract_unmet'
                elif not allow_hook_activation:
                    decision = 'inactive_hook_present_activation_deferred'; reason = HOOK_OWNER_NOTICE
                else:
                    decision = 'activated_by_capability_check'
                    row['engine_status'] = 'active'
                    row['hook_metadata'] = HOOK_METADATA.get(r['key'], {})
            row['activation'] = decision
            decisions.append(dict(key=r['key'], hook=hook, decision=decision, reason=reason,
                                  accounting_only=r['key'] in ACCOUNTING_ONLY, optical_geometry=False))
        out.append(row)
    return out, dict(**caps, hook_decisions=decisions, allow_hook_activation=allow_hook_activation, owner_notice=HOOK_OWNER_NOTICE)


def engine_entry(row: dict, value: Any | None = None) -> dict:
    """One V3 `parameters` entry: value, unit, source_kind, source_ref, cultivar, uncertainty."""
    require(row['engine_status'] == 'active', f'only active rows map to the engine: {row["key"]}')
    note = ' [accounting-only; never optical geometry]' if row['key'] in ACCOUNTING_ONLY else ''
    return dict(value=row['value'] if value is None else value, unit=row['unit'], source_kind=row['source_kind'],
                source_ref=f'{row["key"]}: {row["source_ref"]}{note}', cultivar=row['cultivar'], uncertainty=row['uncertainty'],
                **row.get('hook_metadata', {}))


def build_request_overrides(registry: list[dict], member_values: dict[str, Any] | None = None, scenario_values: dict[str, Any] | None = None) -> dict:
    """Map registry rows onto a V3 request without touching V3 code.

    Returns `parameters` (engine key -> entry) for active rows, `environment` (column -> value, source_kind)
    for set-point rows, and bookkeeping lists for everything the engine cannot express. `member_values`
    replaces declared values for sampled rows (see `sample_member`).
    """
    member_values = member_values or {}
    scenario_values = scenario_values or {}
    for key, val in scenario_values.items():
        row = next((r for r in registry if r['key'] == key), None)
        require(row is not None and row['uncertainty_kind'] == 'scenario_set' and val in row['candidates'], f'scenario value outside the declared scenario set: {key}={val}')
    unknown = set(member_values) - {r['key'] for r in registry}
    require(not unknown, f'member values for unknown registry keys: {sorted(unknown)}')
    parameters: dict[str, dict] = {}
    environment: dict[str, dict] = {}
    axis_parameters: dict[str, dict] = {}
    blocked: list[dict] = []
    hidden_state: dict[str, dict] = {}
    inactive, retained, layer_only, candidates, activated = [], [], {}, [], []
    for r in registry:
        value = member_values.get(r['key'], r['value'])
        if r['key'] in member_values:
            require(r['uncertainty_kind'] == 'candidate_set' and value in r['candidates'],
                    f'member value outside the declared candidate set: {r["key"]}')
        status = r['engine_status']
        if status == 'active':
            require(r['engine_key'] not in parameters, f'two rows map to {r["engine_key"]}')
            parameters[r['engine_key']] = engine_entry(r, value)
            if r.get('activation') == 'activated_by_capability_check':
                activated.append(r['key'])
        elif status == 'environment':
            environment[r['engine_key']] = dict(value=value, source_kind=r['source_kind'], registry_key=r['key'])
        elif status == 'inactive_in_engine':
            inactive.append(dict(key=r['key'], hook=r['engine_key'], value=value, unit=r['unit'], source_kind=r['source_kind'],
                                 reason=r['note'], activation=r.get('activation', 'inactive_hook_absent')))
        elif status == 'engine_default_retained':
            retained.append(dict(key=r['key'], engine_key=r['engine_key'], reason=r['note']))
        elif status == 'layer_only':
            layer_only[r['key']] = dict(value=value, unit=r['unit'], source_kind=r['source_kind'])
        elif status == 'candidate':
            candidates.append(dict(key=r['key'], form=r['source_ref'], source_kind=r['source_kind'], status='candidate_inactive'))
        elif status == 'axis':
            value = scenario_values.get(r['key'], value)
            axis_parameters[r['key']] = dict(value=value, unit=r['unit'], source_kind=r['source_kind'], source_ref=f'{r["key"]}: {r["source_ref"]}',
                                             cultivar=r['cultivar'], uncertainty=r['uncertainty'])
        elif status == 'blocked_engine_extension':
            blocked.append(dict(key=r['key'], engine_key=r['engine_key'], reason=r['note'], source_ref=r['source_ref']))
        elif status == 'hidden_state':
            # F9: recorded, never written into a request by this layer; the engine fixture declares it (the forecast passes it through)
            hidden_state[r['key']] = dict(value=value, unit=r['unit'], source_kind=r['source_kind'], source_ref=r['source_ref'], engine_key=r['engine_key'],
                                          uncertainty=r['uncertainty'], note=r['note'])
    require(not axis_parameters or set(axis_parameters) == set(AXIS_PARAMETERS), 'axis parameter rows must cover exactly the fsp-axes-1 set')
    return dict(parameters=parameters, environment=environment, inactive_in_engine=inactive,
                engine_default_retained=retained, layer_only=layer_only, candidates=candidates,
                activated_by_capability_check=activated, axis_parameters=axis_parameters, blocked_engine_extension=blocked,
                hidden_state=hidden_state, registry_sha256=None)


def apply_overrides(request: dict, overrides: dict) -> dict:
    """Return a copy of a V3 request with the active overrides written into `parameters`.

    Keys the registry does not cover keep the request's own (V3) entries; those are what the forecast
    manifest later records as `v3_default_retained`. An activated hook key must exist in the request
    (i.e. V3 really exposes it); otherwise the override is refused rather than silently added.
    """
    result = deepcopy(request)
    params = result['parameters']
    for key, entry in overrides['parameters'].items():
        # optional hook keys (activated by the capability check) may be absent from V3's default request
        require(key in params or key in ENGINE_PARAMS, f'request lacks engine parameter {key}')
        params[key] = dict(entry)
    for item in overrides['engine_default_retained']:
        require(item['engine_key'] in params, f'retained engine key missing from request: {item["engine_key"]}')
    return result


def sampled_rows(registry: list[dict]) -> list[dict]:
    return [r for r in registry if r['engine_status'] in ('active', 'axis') and r['uncertainty_kind'] == 'candidate_set']


def scenario_set(registry: list[dict]) -> dict | None:
    """F8: the declared scenario set (one row allowed today). Returns {parameter, labels->value, reference, source...} or None."""
    rows_ = [r for r in registry if r['uncertainty_kind'] == 'scenario_set']
    if not rows_:
        return None
    require(len(rows_) == 1, 'one scenario-set row supported')
    r = rows_[0]
    return dict(parameter=r['key'], engine_key=r['engine_key'], values=dict(zip(SCENARIO_LABELS, r['candidates'])), reference='base',
                source_kind=r['source_kind'], source_ref=r['source_ref'], uncertainty=r['uncertainty'],
                rule='a scenario is not a probability: one forecast per value, reported side by side, never pooled into an interval, never drawn as a member sample')


def sample_member(registry: list[dict], seed: int, index: int, exclude: tuple[str, ...] = (),
                  eligible: set[str] | None = None) -> dict[str, Any]:
    """Draw one scenario-set member: one candidate per `candidate_set` row, seeded and index-stable.

    This is a declared scenario set, not a calibrated distribution; every draw is uniform over the
    candidates the human/literature review listed. Rows named in `exclude`, or outside `eligible` when
    it is given, keep their declared value and are not drawn (B3: only parameters that can act on the
    input state are varied).
    """
    rng = random.Random(f'{seed}:{index}')
    values = {}
    for r in sampled_rows(registry):
        if r['key'] in exclude or (eligible is not None and r['key'] not in eligible):
            continue
        values[r['key']] = rng.choice(r['candidates'])
    return values


def retained_from_request(request: dict, overrides: dict) -> dict[str, dict]:
    """V3 parameters the registry leaves untouched, with V3's own provenance."""
    return {k: v for k, v in request['parameters'].items() if k not in overrides['parameters']}


# ---------------------------------------------------------------------------------------------------------------
# B3 — which registered uncertainties can act on a given input state within the horizon
# ---------------------------------------------------------------------------------------------------------------

def thermal_schedule(controls: dict, environment: list[dict], params: dict, start_interval: int, days: int) -> list[dict]:
    """Replica of V3's thermal initiation program (`vtc_development_native.rgg::develop`, independently re-coded in
    `vtc_development_io.validate_outputs`): which organ kinds are initiated on which boundary, given the apex counters.

    `controls`: thermal_dd, produced, leaf_order, truss_count, axis_leaf_count, stopped (bool). `params`: plain values.
    Returns one row per initiation {day, kind in (leaf, truss), rank, pairs}. Carbon never enters this clock.
    """
    clock = float(controls['thermal_dd']); produced = int(controls['produced']); leaves = int(controls['leaf_order'])
    trusses = int(controls['truss_count']); axis_leaves = int(controls['axis_leaf_count']); stopped = bool(controls.get('stopped', False))
    pairs = params['PAIRS']; cadence = params['CADENCE']; out = []
    for step in range(days):
        e = environment[start_interval + step]
        h = float(e['light_hours'])
        clock += max(0.0, (float(e['temp_day_c']) * h + float(e['temp_night_c']) * (24 - h)) / 24 - params['BASE_C'])
        if clock < params['GERMINATION_DD']:
            continue
        due = math.floor((clock - params['GERMINATION_DD']) / params['PHYLLOCHRON_DD'])
        while produced < due and not stopped:
            produced += 1
            target = params['FIRST_LEAVES'] if trusses == 0 else cadence[min(trusses - 1, len(cadence) - 1)]
            if axis_leaves < target:
                leaves += 1; axis_leaves += 1
                out.append(dict(day=start_interval + step + 1, kind='leaf', rank=leaves, pairs=pairs[min(leaves - 1, len(pairs) - 1)]))
            else:
                trusses += 1; axis_leaves = 0
                out.append(dict(day=start_interval + step + 1, kind='truss', rank=leaves, pairs=0))
                stopped = trusses > 1 and target == 0
    return out


def eligibility(registry: list[dict], controls_by_plant: dict[str, dict], environment: list[dict], base_params: dict,
                start_interval: int, days: int, route: str) -> dict[str, dict]:
    """Per candidate_set row: can any candidate change what happens to this input state within `days`?

    Decided by running the thermal schedule for each candidate (the rule V3 uses), never by guessing.
    `route` is needed for one engine fact: outside the pipeline, V3 checks imported compounds against the
    member's PAIRS, so PAIRS cannot vary for a Stage-2 fixture.
    """
    report = {}
    rows = {r['key']: r for r in registry}
    engine_key = {r['key']: r['engine_key'] for r in registry}

    def schedules(key: str, candidates: list) -> list[list[dict]]:
        result = []
        for cand in candidates:
            per_plant = []
            for pid, c in sorted(controls_by_plant.items()):
                p = dict(base_params); p[engine_key[key]] = cand
                per_plant.append([dict(s) for s in thermal_schedule(c, environment, p, start_interval, days)])
            result.append(per_plant)
        return result

    any_substem = any(c.get('is_substem') for c in controls_by_plant.values())
    any_can_truss = any(c.get('can_truss', not c.get('stopped', False)) for c in controls_by_plant.values())
    for r in registry:
        if r['engine_status'] == 'axis':
            structural = any_substem if r['key'] == 'SUBSTEM_SINK_SCALE' else any_can_truss
            if structural:
                why = '>= 1 substem in the input state' if r['key'] == 'SUBSTEM_SINK_SCALE' else 'an axis that can still truss'
            else:
                why = 'no substem in the input state' if r['key'] == 'SUBSTEM_SINK_SCALE' else 'no axis can still truss'
            if r['uncertainty_kind'] == 'scenario_set':
                report[r['key']] = dict(eligible=False, reason=f'scenario_set (reported side by side, not drawn; structurally {"eligible" if structural else "inert"}: {why})',
                                        candidates=r['candidates'], structurally_eligible=structural, scenario_set=True)
                continue
            if r['uncertainty_kind'] != 'candidate_set':
                report[r['key']] = dict(eligible=False, reason=f'no_declared_uncertainty (structurally {"eligible" if structural else "inert"}: {why})',
                                        candidates=None, structurally_eligible=structural)
            else:
                report[r['key']] = dict(eligible=structural, reason='' if structural else f'inert: {why}', candidates=r['candidates'], structurally_eligible=structural)
            continue
        if r['uncertainty_kind'] != 'candidate_set' or r['engine_status'] != 'active':
            if r['engine_status'] == 'active':
                report[r['key']] = dict(eligible=False, reason='no_declared_uncertainty', candidates=None)
            continue
        key, cands = r['key'], r['candidates']
        if key == 'NR_LEAFLET_PAIRS_BY_RANK' and route == 'stage2_fixture':
            report[key] = dict(eligible=False, reason='engine_inventory_check_binds_imported_compounds_to_PAIRS (vtc_development_io.validate_outputs)', candidates=cands)
            continue
        if key == 'MIDDLE_PAIR_RAMP':
            # acts only on compounds initiated within the horizon that have >= 3 pairs (pairWeight == 1 for m <= 2)
            pairs_options = rows['NR_LEAFLET_PAIRS_BY_RANK']['candidates'] if report.get('NR_LEAFLET_PAIRS_BY_RANK', {}).get('eligible') else [base_params['PAIRS']]
            acts = False
            for po in pairs_options:
                p = dict(base_params); p['PAIRS'] = po
                for c in controls_by_plant.values():
                    if any(s['kind'] == 'leaf' and s['pairs'] >= 3 for s in thermal_schedule(c, environment, p, start_interval, days)):
                        acts = True
            report[key] = dict(eligible=acts, reason='' if acts else 'inert: no compound with >= 3 pairs initiated within the horizon (pairWeight is 1 for 1-2 pairs)', candidates=cands)
            continue
        scheds = schedules(key, cands)
        differs = any(scheds[0] != s for s in scheds[1:])
        if key == 'NR_LEAFLET_PAIRS_BY_RANK':
            # the schedule itself is PAIRS-independent except for the recorded pair count; eligible iff some new compound gets a differing count
            differs = any(a != b for a, b in zip(scheds[0], scheds[1:][0])) if len(scheds) > 1 else False
            reason = '' if differs else 'inert: no compound initiated within the horizon whose pair count differs between candidates'
        else:
            reason = '' if differs else 'inert on this input state within the horizon (identical thermal schedule for every candidate)'
        report[key] = dict(eligible=differs, reason=reason, candidates=cands)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--registry', type=Path, default=REGISTRY_PATH)
    sub = parser.add_subparsers(dest='op', required=True)
    sub.add_parser('validate', help='validate the registry and print a summary (static statuses)')
    p = sub.add_parser('capabilities', help='B6: resolve inactive rows against the live V3 parameter list')
    p.add_argument('--enable-hooks', action='store_true', help='allow activation when the hook is present and its contract is met (owner RESULT required)')
    p = sub.add_parser('overrides', help='print the V3 request overrides as JSON')
    p.add_argument('--seed', type=int, default=None, help='draw one scenario-set member instead of the declared values')
    p.add_argument('--index', type=int, default=0)
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
        if args.op == 'validate':
            summary = {s: [r['key'] for r in registry if r['engine_status'] == s] for s in ENGINE_STATUS}
            summary['sampled'] = [r['key'] for r in sampled_rows(registry)]
            summary['registry_sha256'] = registry_hash(args.registry)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        elif args.op == 'capabilities':
            resolved, report = resolve_engine_capabilities(registry, allow_hook_activation=args.enable_hooks)
            report['active_after_check'] = [r['key'] for r in resolved if r['engine_status'] == 'active']
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            resolved, _ = resolve_engine_capabilities(registry)
            values = sample_member(resolved, args.seed, args.index) if args.seed is not None else {}
            out = build_request_overrides(resolved, values)
            out['registry_sha256'] = registry_hash(args.registry)
            out['member_values'] = values
            print(json.dumps(out, ensure_ascii=False, indent=2))
    except ContractError as exc:
        parser.exit(1, f'ContractError: {exc}\n')


if __name__ == '__main__':
    main()
