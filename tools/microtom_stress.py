"""F9 — allocation-cap stress fixture and reserve-threshold sweep. Software verification only; never a forecast.

python -X utf8 -m tools.microtom_stress run --scenario build/forecast_scenarios_20261012/scenario_p3_axes_pipeline.json ^
    --stress-reserve 0.10 --sweep 0.20 0.17 0.15 0.144 0.142 0.140 0.12 0.10 0.05 --horizon-days 8
python -X utf8 -m tools.microtom_stress verify build/stress_20261013_01

What this is. The capped sink-weighted allocation (`a_i = min(d_i, lambda d_i s_axis)`, P4 resource contract section 2) had never
executed its binding branch: in F8 (`build/forecast_20261012_07`) `allocated_gC == demand_gC` in every committed step because the
engine-owner fixture's declared 0.2 gC plant reserve plus daily gross exceed demand. This module runs the SAME engine on the SAME P1
fixture package through the same public pipeline functions, but with a DECLARED stress hidden state — `plant_initialization.reserve_gC`
replaced in this module's own engine scenario JSON (engine input data, `source_kind = fixture_declared`) — and checks the contract:
  G1  the cap binds; allocation is demand-proportional under the cap (organ-level oracle `tools.fsp_axes.allocation_reference`);
      `SUBSTEM_SINK_SCALE` shifts the split in the declared direction (high -> more to S axes, low -> less); carbon closure holds;
      per-axis sums equal the plant ledger.
  G2  a reserve SWEEP (base scenario, everything else fixed) finds the reserve below which the cap first binds — a property of the
      model, reported with the sweep that produced it, never adopted — and a longer-horizon run at the declared reserve answers the
      horizon question separately.

What this is NOT: a forecast. Folders are `build/stress_<YYYYMMDD>_<NN>` (never `forecast_*`), every table row and the manifest carry
`reuse_as_prediction = forbidden`, the mark is written into the engine scenario's `initialization_provenance` (hence into native
`plants.csv`), and `tools.microtom_forecast` refuses such runs as members. No headline, interval or scenario range is drawn here.
The main fixture's declared value is not changed (the engine-owner fixture file is not edited; the forecasts `_04` / `_07` are untouched).
Member draws are not used: every run takes the registry's declared values (the scenario set is the only thing varied, side by side).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from tools import microtom_axes as ax
from tools import microtom_forecast as mf
from tools.microtom_forecast_io import FORBIDDEN_STATUS, NO_REUSE_MARK, artifact_hashes, code_digest, now_iso, write_table
from tools.microtom_parameters import REGISTRY_PATH, SCENARIO_LABELS, load_registry, registry_hash, scenario_set
from tools.vtc_growth_io import ROOT, ContractError, digest, read_json, require, rows, sha, write_json

SCHEMA = 'microtom-stress-1'
SCENARIO_SCHEMA = 'microtom-stress-scenario-1'
FOLDER_RE = re.compile(r'^stress_(\d{8})_(\d{2})$')
FIXTURE_PURPOSE = 'exercise_allocation_cap'
NO_REUSE = 'forbidden'
RESERVE_KEY = 'PLANT_RESERVE_GC'
CLOSURE_TOL = 1e-9       # gC, plant ledger residual (engine contract: closure at plant scope)
ORACLE_TOL = 1e-9        # gC per organ, native allocation vs the independent bisection oracle
LAW_TOL = 1e-9           # gC, funded total vs min(max(0, budget), demand)
BIND_TOL = 1e-10         # gC, the cap binds when funded < demand - BIND_TOL
STEP_COLUMNS = ('case_id', 'scenario_id', 'scenario_value', 'reserve_gC', 'reserve_source_kind', 'step', 'plant_instance_id', 'axis_id', 'sink_scale',
                'budget_gC', 'demand_gC', 'allocated_gC', 'funded_fraction', 'allocation_over_demand', 'allocated_share', 'demand_share',
                'cap_binding', 'oracle_max_abs_diff_gC', 'ledger_residual_gC', 'ledger_deficit_gC', 'axis_leaf_count', 'axis_leaf_area_mm2',
                'reuse_as_prediction')
STATEMENT = ('This folder is a software stress fixture (fixture_purpose = exercise_allocation_cap). Its reserve is a declared value chosen to '
             'make the allocation cap bind; its numbers are never a forecast of anything, may not be quoted as a prediction, and no headline, '
             'interval or scenario range is drawn from them. The main fixture keeps its declared reserve (user decision 2026-10-13).')


# ---------------------------------------------------------------------------------------------------------------
# folders / scenario
# ---------------------------------------------------------------------------------------------------------------

def new_stress_dir(root: Path = ROOT / 'build', date: str | None = None) -> Path:
    """Next free `stress_<YYYYMMDD>_<NN>` under `root` (below project build/), created write-once."""
    root = Path(root)
    require(root.resolve().is_relative_to((ROOT / 'build').resolve()), 'stress folders live below project build/')
    date = date or datetime.now().strftime('%Y%m%d')
    require(re.fullmatch(r'\d{8}', date) is not None, 'date must be YYYYMMDD')
    taken = {int(m.group(2)) for p in root.iterdir() for m in [FOLDER_RE.match(p.name)] if m and m.group(1) == date} if root.exists() else set()
    nn = next(i for i in range(1, 100) if i not in taken)
    folder = root / f'stress_{date}_{nn:02d}'
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def declared_reserve(registry: list[dict]) -> dict:
    """The registry's record of the engine fixture's declared plant reserve (user_assumed, hidden_state)."""
    row = next((r for r in registry if r['key'] == RESERVE_KEY), None)
    require(row is not None and row['engine_status'] == 'hidden_state', f'registry lacks the {RESERVE_KEY} hidden_state row')
    return dict(value=float(row['value']), unit=row['unit'], source_kind=row['source_kind'], source_ref=row['source_ref'], engine_key=row['engine_key'])


def stress_scenario(forecast_scenario: dict, stress_reserve: float, sweep: list[float], horizon_days: int | None,
                    declared: dict, rays: int | None = None) -> dict:
    """The declared stress plan: which hidden-state values are fixture_declared, which runs are made, what is held fixed."""
    fs = mf.validate_scenario(dict(forecast_scenario))
    require(fs['engine'] == 'pipeline', 'stress fixtures use the pipeline engine (axis records are per-axis)')
    if rays is not None:
        require(type(rays) is int and rays >= 1, 'rays must be a positive integer')
        fs = dict(fs, rays=rays, issue_class='diagnostic' if rays < mf.QUANTITATIVE_RAYS else fs['issue_class'])
    require(stress_reserve > 0 and all(v > 0 for v in sweep), 'reserve values must be positive (gC)')
    require(len(set(sweep)) == len(sweep), 'sweep values must be distinct')
    require(horizon_days is None or (type(horizon_days) is int and horizon_days >= 1), 'horizon_days must be a positive integer')
    ref = ('declared stress hidden state (F9, user decision 2026-10-13: a separate stress fixture for software verification only); '
           f'replaces {declared["source_ref"]}')
    return dict(schema=SCENARIO_SCHEMA, fixture_purpose=FIXTURE_PURPOSE, reuse_as_prediction=NO_REUSE, not_a_forecast=True, statement=STATEMENT,
                source_forecast_scenario=fs, p1_package=fs['p1_package'], state_source=fs['state_source'], rays=fs['rays'], seed=fs['ensemble']['seed'],
                declared_hidden_state=dict(reserve_gC=dict(value=stress_reserve, unit='gC', source_kind='fixture_declared', source_ref=ref,
                                                           engine_key=declared['engine_key'])),
                main_fixture_declared_reserve=dict(declared, changed=False),
                stress_runs=dict(scenarios=list(SCENARIO_LABELS), reserve_gC=stress_reserve, intervals=max(fs['horizons_days']),
                                 members='none: registry declared values, no member draw (software verification)'),
                sweep=dict(reserve_values_gC=sorted(sweep, reverse=True), scenario='base', intervals=max(fs['horizons_days']), source_kind='fixture_declared',
                           purpose='find the reserve below which the allocation cap first binds; a model property, none of these values is adopted'),
                horizon_run=(dict(days=horizon_days, reserve_gC=declared['value'], scenario='base', source_kind=declared['source_kind'],
                                  purpose='does the cap bind at a longer horizon with the DECLARED reserve (nothing changed but the number of intervals)')
                             if horizon_days else None),
                held_fixed=['P1 fixture package and state_source', 'organ_initialization (engine-owner fixture hidden organ state)', 'root/stem hidden state',
                            'climate set-points, lamps, reference PPFD (user_assumed), ray count and light seed', 'registry declared parameter values',
                            'APPLY_DETERMINATE_STOP = true on every axis'],
                nutrient_feedback_enabled=False)


def reserve_edit(reserve_gC: float, record: dict | None = None):
    """Engine-scenario edit: replace every plant's declared reserve, and stamp the provenance with the no-reuse mark.

    `record` (optional) receives the engine fixture's original values so the manifest can show what was replaced.
    """
    def edit(scen: dict) -> dict:
        scen = json.loads(json.dumps(scen))
        original = {pid: p['reserve_gC'] for pid, p in scen['plant_initialization'].items()}
        if record is not None:
            record.setdefault('original_reserve_gC', original)
        for p in scen['plant_initialization'].values():
            p['reserve_gC'] = reserve_gC
        scen['initialization_provenance'] = (f'fixture_declared stress hidden state: plant reserve_gC={reserve_gC} replaces the engine-owner fixture value '
                                             f'{sorted(set(original.values()))} for software verification; fixture_purpose={FIXTURE_PURPOSE}; {NO_REUSE_MARK}; '
                                             f'all other hidden state unchanged ({scen["initialization_provenance"]})')
        return scen
    return edit


def case_forecast_scenario(fs: dict, intervals: int) -> dict:
    """One-member copy of the forecast scenario with horizons 1..intervals (same seed, lamps, light, package)."""
    return dict(fs, horizons_days=list(range(1, intervals + 1)), ensemble=dict(size=1, seed=fs['ensemble']['seed']),
                scenario_id=f'{fs["scenario_id"]}__stress', declared_assumptions=list(fs['declared_assumptions']) + [STATEMENT])


# ---------------------------------------------------------------------------------------------------------------
# analysis of one committed run
# ---------------------------------------------------------------------------------------------------------------

def _axis_scales(engine_scenario: dict) -> dict[tuple[str, str], float]:
    return {(a['plant_instance_id'], a['axis_id']): float(a['parameters']['SUBSTEM_SINK_SCALE']['value']) for a in engine_scenario.get('axes', [])}


def analyse_run(run_dir: Path, intervals: int, scales: dict[tuple[str, str], float]) -> dict:
    """Per committed step and plant: budget, demand, funded, binding flag, oracle and law checks, per-axis split, closure."""
    from tools.fsp_axes import allocation_reference
    run_dir = Path(run_dir)
    steps_out = []
    for k in range(1, intervals + 1):
        step = run_dir / 'committed' / f'step_{k:04d}'
        ledger = {r['plant_instance_id']: r for r in rows(step / 'carbon_ledger.csv')}
        organs = rows(step / 'organ_allocations.csv')
        flux = rows(step / 'axis_flux.csv')
        states = rows(step / 'state.csv')
        for pid, led in sorted(ledger.items()):
            po = [o for o in organs if o['plant_instance_id'] == pid]
            budget = float(led['reserve_start_gC']) + float(led['gross_gC']) - float(led['maintenance_gC'])
            demand = sum(float(o['demand_gC']) for o in po)
            funded = sum(float(o['allocated_gC']) for o in po)
            law = min(max(0.0, budget), demand)
            binding = funded < demand - BIND_TOL
            d = [float(o['demand_gC']) for o in po]
            s = [scales.get((pid, o['axis_id']), 1.0) for o in po]
            expected = allocation_reference(d, s, budget) if demand > 0 else [0.0] * len(po)
            oracle = max((abs(float(o['allocated_gC']) - e) for o, e in zip(po, expected)), default=0.0)
            # within one axis every organ shares the scale, so allocation/demand must be one ratio per axis (unless saturated at d_i)
            per_axis: dict[str, dict] = {}
            for o in po:
                a = per_axis.setdefault(o['axis_id'], dict(demand=0.0, allocated=0.0, ratios=[]))
                a['demand'] += float(o['demand_gC']); a['allocated'] += float(o['allocated_gC'])
                if float(o['demand_gC']) > 0:
                    a['ratios'].append(float(o['allocated_gC']) / float(o['demand_gC']))
            fx = {r['axis_id']: r for r in flux if r['plant_instance_id'] == pid}
            axis_rows = {}
            for aid, a in sorted(per_axis.items()):
                organs_k = [t for t in states if t['plant_instance_id'] == pid and t['axis_id'] == aid]
                axis_rows[aid] = dict(
                    sink_scale=scales.get((pid, aid), 1.0), demand_gC=a['demand'], allocated_gC=a['allocated'],
                    allocation_over_demand=(a['allocated'] / a['demand']) if a['demand'] > 0 else 'n/a',
                    within_axis_ratio_spread=(max(a['ratios']) - min(a['ratios'])) if a['ratios'] else 0.0,
                    allocated_share=(a['allocated'] / funded) if funded > 0 else 'n/a', demand_share=(a['demand'] / demand) if demand > 0 else 'n/a',
                    axis_flux_vs_organ_sum_gC=dict(demand=abs(float(fx[aid]['demand_gC']) - a['demand']) if aid in fx else 'n/a',
                                                   allocated=abs(float(fx[aid]['allocated_gC']) - a['allocated']) if aid in fx else 'n/a'),
                    axis_leaf_count=sum(t['class'] == 'CompoundLeaf' for t in organs_k),
                    axis_leaf_area_mm2=sum(float(t['area_m2']) for t in organs_k if t['class'] == 'Leaflet') * 1e6)
            all_ratios = [r for a in per_axis.values() for r in a['ratios']]
            steps_out.append(dict(step=k, plant_instance_id=pid, reserve_start_gC=float(led['reserve_start_gC']), gross_gC=float(led['gross_gC']),
                                  maintenance_gC=float(led['maintenance_gC']), budget_gC=budget, demand_gC=demand, funded_gC=funded,
                                  funded_fraction=(funded / demand) if demand > 0 else 'n/a', cap_binding=binding,
                                  law_abs_diff_gC=abs(funded - law), oracle_max_abs_diff_gC=oracle,
                                  cross_organ_ratio_spread=(max(all_ratios) - min(all_ratios)) if all_ratios else 0.0,
                                  reserve_end_gC=float(led['reserve_end_gC']), ledger_deficit_gC=float(led['deficit_gC']), ledger_residual_gC=float(led['residual_gC']),
                                  axes=axis_rows))
    binding_steps = sorted({s['step'] for s in steps_out if s['cap_binding']})
    return dict(intervals=intervals, steps=steps_out, binding_steps=binding_steps, any_binding=bool(binding_steps),
                first_binding_step=binding_steps[0] if binding_steps else None,
                max_abs_residual_gC=max(abs(s['ledger_residual_gC']) for s in steps_out), max_deficit_gC=max(s['ledger_deficit_gC'] for s in steps_out),
                max_oracle_abs_diff_gC=max(s['oracle_max_abs_diff_gC'] for s in steps_out), max_law_abs_diff_gC=max(s['law_abs_diff_gC'] for s in steps_out),
                max_axis_flux_vs_organ_sum_gC=max((v for s in steps_out for a in s['axes'].values() for v in a['axis_flux_vs_organ_sum_gC'].values() if v != 'n/a'), default=0.0),
                reserve_trajectory_gC=[dict(step=s['step'], plant_instance_id=s['plant_instance_id'], start=s['reserve_start_gC'], end=s['reserve_end_gC'],
                                            demand=s['demand_gC'], gross=s['gross_gC']) for s in steps_out])


def step_rows(case: dict) -> list[dict]:
    out = []
    for s in case['analysis']['steps']:
        for aid, a in s['axes'].items():
            out.append(dict(case_id=case['case_id'], scenario_id=case['scenario_id'], scenario_value=case['scenario_value'], reserve_gC=case['reserve_gC'],
                            reserve_source_kind=case['reserve_source_kind'], step=s['step'], plant_instance_id=s['plant_instance_id'], axis_id=aid,
                            sink_scale=a['sink_scale'], budget_gC=s['budget_gC'], demand_gC=a['demand_gC'], allocated_gC=a['allocated_gC'],
                            funded_fraction=s['funded_fraction'], allocation_over_demand=a['allocation_over_demand'], allocated_share=a['allocated_share'],
                            demand_share=a['demand_share'], cap_binding=s['cap_binding'], oracle_max_abs_diff_gC=s['oracle_max_abs_diff_gC'],
                            ledger_residual_gC=s['ledger_residual_gC'], ledger_deficit_gC=s['ledger_deficit_gC'], axis_leaf_count=a['axis_leaf_count'],
                            axis_leaf_area_mm2=a['axis_leaf_area_mm2'], reuse_as_prediction=NO_REUSE))
    return out


# ---------------------------------------------------------------------------------------------------------------
# contract checks
# ---------------------------------------------------------------------------------------------------------------

def direction_check(cases: dict[str, dict]) -> dict:
    """At the first binding step the S axes must receive a strictly larger share as the scale rises (low < base < high) and M the reverse.

    Also reports the per-axis leaf area / count at the last step per scenario (software evidence of the shifted split, not a prediction).
    """
    require(set(cases) == set(SCENARIO_LABELS), 'direction check needs low/base/high at one reserve')
    first = {lab: c['analysis']['first_binding_step'] for lab, c in cases.items()}
    if any(v is None for v in first.values()):
        return dict(passed=False, reason='the cap did not bind in every scenario; no direction can be checked', first_binding_step=first)
    k = min(first.values())
    plants = sorted({s['plant_instance_id'] for s in cases['base']['analysis']['steps']})
    detail, passed = {}, True
    for pid in plants:
        row = {}
        for lab in SCENARIO_LABELS:
            s = next(x for x in cases[lab]['analysis']['steps'] if x['step'] == k and x['plant_instance_id'] == pid)
            s_share = sum(a['allocated_gC'] for aid, a in s['axes'].items() if aid != 'M')
            m_share = s['axes'].get('M', {}).get('allocated_gC', 0.0)
            row[lab] = dict(S_allocated_gC=s_share, M_allocated_gC=m_share, funded_gC=s['funded_gC'])
        s_ok = row['low']['S_allocated_gC'] < row['base']['S_allocated_gC'] < row['high']['S_allocated_gC']
        m_ok = row['low']['M_allocated_gC'] > row['base']['M_allocated_gC'] > row['high']['M_allocated_gC']
        passed = passed and s_ok and m_ok
        detail[pid] = dict(step=k, per_scenario=row, S_increases_with_scale=s_ok, M_decreases_with_scale=m_ok)
    last = {}
    for lab, c in cases.items():
        steps = [s for s in c['analysis']['steps'] if s['step'] == c['analysis']['intervals']]
        last[lab] = {f'{s["plant_instance_id"]}:{aid}': dict(axis_leaf_count=a['axis_leaf_count'], axis_leaf_area_mm2=a['axis_leaf_area_mm2'])
                     for s in steps for aid, a in s['axes'].items()}
    return dict(passed=passed, first_binding_step=k, allocation_split=detail, last_step_per_axis=last,
                declared_direction='SUBSTEM_SINK_SCALE multiplies S-axis demand weights: high favours side shoots, low favours the main stem (resource contract section 2)')


def threshold_from_sweep(sweep_cases: list[dict]) -> dict:
    """Bracket the reserve below which the cap first binds; compare with the analytic value demand_1 - gross_1 + maintenance_1."""
    pts = sorted(((c['reserve_gC'], c['analysis']) for c in sweep_cases), key=lambda t: t[0])
    binding = [r for r, a in pts if a['any_binding']]
    free = [r for r, a in pts if not a['any_binding']]
    monotone = (not binding or not free) or max(binding) < min(free)
    analytic = []
    for r, a in pts:
        for s in a['steps']:
            if s['step'] == 1:
                analytic.append(s['demand_gC'] - s['gross_gC'] + s['maintenance_gC'])
    theta = dict(value_gC=sum(analytic) / len(analytic), spread_across_runs_gC=(max(analytic) - min(analytic)) if analytic else 0.0,
                 formula='reserve_start + gross_1 - maintenance_1 < demand_1  <=>  reserve_start < demand_1 - gross_1 + maintenance_1 (day-1 budget law, vtc_development_native.rgg)',
                 holds_when='the step-1 state is identical across the sweep (same package, light seed and parameters), which the spread column verifies')
    first_steps = {f'{r:.4f}': a['first_binding_step'] for r, a in pts}
    return dict(sweep_values_gC=[r for r, _ in pts], binding_values_gC=binding, non_binding_values_gC=free, monotone_in_reserve=monotone,
                bracket_gC=dict(max_non_binding=min(free) if free else None, min_binding=max(binding) if binding else None),
                analytic_threshold=theta, first_binding_step_by_reserve=first_steps,
                statement=(f'the cap binds below about {theta["value_gC"]:.4f} gC (bracket: binds at {max(binding):.4f}, not at {min(free):.4f}); '
                           if binding and free else 'the sweep did not bracket the threshold; ') +
                          'a model property conditional on this fixture\'s imported demand, assumed light and set-points; not adopted as a reserve value')


# ---------------------------------------------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------------------------------------------

def _run_case(folder: Path, fs: dict, registry: list[dict], case_id: str, label: str, value: float, reserve: float, reserve_kind: str,
              intervals: int, timeout_s: float, transients: list[dict], record: dict) -> dict:
    sset = scenario_set(registry)
    built = mf.build_pipeline_member_with_retry(folder, case_forecast_scenario(fs, intervals), registry, 0, {}, timeout_s,
                                                {sset['parameter']: value}, case_id, transients, scenario_edit=reserve_edit(reserve, record))
    mem = mf.load_pipeline_member(built)
    scen = built['scenario']
    for pid, p in scen['plant_initialization'].items():
        require(p['reserve_gC'] == reserve, 'engine scenario reserve not applied')
    require(NO_REUSE_MARK in read_json(built['run_dir'] / 'scenario.json')['initialization_provenance'], 'frozen engine scenario lacks the no-reuse mark')
    analysis = analyse_run(built['run_dir'], intervals, _axis_scales(scen))
    rel = built['run_dir'].relative_to(folder)
    return dict(case_id=case_id, scenario_id=label, scenario_value=value, reserve_gC=reserve, reserve_source_kind=reserve_kind, intervals=intervals,
                run_dir=str(rel).replace('\\', '/'), engine_scenario=str((built['scenario_path']).relative_to(folder)).replace('\\', '/'),
                checkpoint_hashes=[c['checkpoint_sha256'] for c in mem['checkpoints']], axis_sums=mem['axis_sums'], plants=mem['plants'],
                axes=[dict(plant_instance_id=a['plant_instance_id'], axis_id=a['axis_id'], sink_scale=a['parameters']['SUBSTEM_SINK_SCALE']['value'],
                           apply_determinate_stop=a['parameters']['APPLY_DETERMINATE_STOP']['value']) for a in scen['axes']],
                analysis=analysis, prepared=built['prepared'], execution=read_json(built['run_dir'] / 'native' / 'execution.json'))


def run_stress(forecast_scenario_path: Path, stress_reserve: float, sweep: list[float], horizon_days: int | None, registry_path: Path = REGISTRY_PATH,
               out_root: Path = ROOT / 'build', timeout_s: float = 1200, date: str | None = None, rays: int | None = None) -> Path:
    registry = load_registry(registry_path)
    declared = declared_reserve(registry)
    plan = stress_scenario(read_json(forecast_scenario_path), stress_reserve, sweep, horizon_days, declared, rays)
    folder = new_stress_dir(out_root, date)
    try:
        return _run_into(folder, plan, registry, registry_path, forecast_scenario_path, timeout_s)
    except Exception as exc:
        write_json(folder / 'FAILED.json', dict(status='failed', error=f'{type(exc).__name__}: {exc}', failed_at=now_iso(),
                                                 note='no manifest.json was written; this folder is neither a stress result nor a forecast'))
        raise


def _run_into(folder: Path, plan: dict, registry: list[dict], registry_path: Path, forecast_scenario_path: Path, timeout_s: float) -> Path:
    fs = plan['source_forecast_scenario']
    sset = scenario_set(registry)
    require(sset is not None, 'no declared scenario set in the registry')
    write_json(folder / 'scenario.json', plan)
    transients: list[dict] = []
    record: dict = {}
    cases: list[dict] = []
    intervals = plan['stress_runs']['intervals']
    # G2 sweep (base scenario) — descending so the declared value runs first
    for v in plan['sweep']['reserve_values_gC']:
        cases.append(_run_case(folder, fs, registry, f'sweep_base_r{v:.4f}', 'base', sset['values']['base'], v, 'fixture_declared', intervals, timeout_s, transients, record))
    # G1 stress scenarios at the stress reserve (base reused from the sweep when present)
    r = plan['stress_runs']['reserve_gC']
    stress_cases: dict[str, dict] = {}
    for label in SCENARIO_LABELS:
        existing = next((c for c in cases if c['scenario_id'] == label and c['reserve_gC'] == r and c['intervals'] == intervals), None)
        stress_cases[label] = existing or _run_case(folder, fs, registry, f'stress_{label}_r{r:.4f}', label, sset['values'][label], r, 'fixture_declared', intervals, timeout_s, transients, record)
        if existing is None:
            cases.append(stress_cases[label])
    # horizon run at the DECLARED reserve
    horizon = None
    if plan['horizon_run']:
        h = plan['horizon_run']['days']
        hc = _run_case(folder, fs, registry, f'horizon_base_r{plan["horizon_run"]["reserve_gC"]:.4f}_d{h}', 'base', sset['values']['base'], plan['horizon_run']['reserve_gC'],
                       plan['main_fixture_declared_reserve']['source_kind'], h, timeout_s, transients, record)
        cases.append(hc)
        horizon = dict(case_id=hc['case_id'], days=h, reserve_gC=hc['reserve_gC'], any_binding=hc['analysis']['any_binding'],
                       first_binding_step=hc['analysis']['first_binding_step'], reserve_trajectory_gC=hc['analysis']['reserve_trajectory_gC'],
                       statement=('the cap never binds through day %d at the declared reserve' % h if not hc['analysis']['any_binding']
                                  else 'the cap first binds at day %s at the declared reserve' % hc['analysis']['first_binding_step']))
    # tables
    write_table(folder / 'stress_steps.csv', [row for c in cases for row in step_rows(c)], STEP_COLUMNS)
    write_json(folder / 'cases.json', [dict(c, analysis=dict(c['analysis'], steps='see stress_steps.csv'), prepared='see run_dir/prepared.json', execution=dict(status=c['execution']['status'])) for c in cases])
    sweep_cases = [c for c in cases if c['case_id'].startswith('sweep_')]
    thr = threshold_from_sweep(sweep_cases)
    direction = direction_check(stress_cases)
    write_json(folder / 'sweep_summary.json', dict(thr, reuse_as_prediction=NO_REUSE, cases=[c['case_id'] for c in sweep_cases]))
    write_json(folder / 'direction.json', dict(direction, reuse_as_prediction=NO_REUSE))
    if horizon:
        write_json(folder / 'horizon.json', dict(horizon, reuse_as_prediction=NO_REUSE))
    # checks (software contract, P4 resource contract section 2)
    base_binding = [s for s in stress_cases['base']['analysis']['steps'] if s['cap_binding']]
    checks = dict(
        cap_binds=dict(passed=stress_cases['base']['analysis']['any_binding'], first_binding_step=stress_cases['base']['analysis']['first_binding_step'],
                       funded_fraction_at_first_binding=base_binding[0]['funded_fraction'] if base_binding else 'n/a'),
        demand_proportional_under_cap=dict(passed=bool(base_binding) and max(s['cross_organ_ratio_spread'] for s in base_binding) <= ORACLE_TOL,
                                           max_cross_organ_ratio_spread_at_binding=max((s['cross_organ_ratio_spread'] for s in base_binding), default='n/a'),
                                           meaning='base scenario (all scales 1): every organ receives the same fraction of its demand when the cap binds'),
        oracle_allocation=dict(passed=all(c['analysis']['max_oracle_abs_diff_gC'] <= ORACLE_TOL for c in cases), tolerance_gC=ORACLE_TOL,
                               max_abs_diff_gC=max(c['analysis']['max_oracle_abs_diff_gC'] for c in cases),
                               oracle='tools.fsp_axes.allocation_reference (independent bisection, organ level, per-axis scale)'),
        budget_law=dict(passed=all(c['analysis']['max_law_abs_diff_gC'] <= LAW_TOL for c in cases), max_abs_diff_gC=max(c['analysis']['max_law_abs_diff_gC'] for c in cases),
                        law='funded = min(max(0, reserve_start + gross - maintenance), demand)'),
        direction=dict(passed=direction['passed'], first_binding_step=direction.get('first_binding_step')),
        carbon_closure=dict(passed=all(c['analysis']['max_abs_residual_gC'] <= CLOSURE_TOL and c['analysis']['max_deficit_gC'] == 0 for c in cases),
                            max_abs_residual_gC=max(c['analysis']['max_abs_residual_gC'] for c in cases), max_deficit_gC=max(c['analysis']['max_deficit_gC'] for c in cases)),
        axis_sums_equal_plant_ledger=dict(passed=all(c['axis_sums']['status'] == 'axis_sums_match_plant_ledger' for c in cases),
                                          max_abs_difference_gC=max(c['axis_sums']['max_abs_difference_gC'] for c in cases),
                                          axis_flux_vs_organ_sum_max_gC=max(c['analysis']['max_axis_flux_vs_organ_sum_gC'] for c in cases)),
        main_fixture_unchanged=dict(passed=all(set(v.values()) == {plan['main_fixture_declared_reserve']['value']} for v in [record.get('original_reserve_gC', {})]) and bool(record),
                                    engine_fixture_reserve_gC_before_edit=record.get('original_reserve_gC'), registry_declared_gC=plan['main_fixture_declared_reserve']['value'],
                                    meaning='the engine-owner fixture still declares the registry value; this layer replaced it only inside its own scenario JSON'),
        no_reuse_mark_in_every_frozen_engine_scenario=dict(passed=all(NO_REUSE_MARK in read_json(folder / c['run_dir'] / 'scenario.json')['initialization_provenance'] for c in cases)),
    )
    executions = [c['execution'] for c in cases]
    prepared0 = cases[0]['prepared']
    manifest = dict(
        stress_run_id=folder.name, issued_at=now_iso(), schema_version=SCHEMA, fixture_purpose=FIXTURE_PURPOSE, not_a_forecast=True, reuse_as_prediction=NO_REUSE,
        statement=STATEMENT, source_forecast_scenario=dict(path=str(Path(forecast_scenario_path)).replace('\\', '/'), sha256=sha(Path(forecast_scenario_path))),
        p1_package=fs['p1_package'], state_source=fs['state_source'], p1_hashes=prepared0['p1_hashes'],
        input_snapshot_sha256=digest(dict(p1_hashes=prepared0['p1_hashes'], state_source=fs['state_source'], plan=sha(folder / 'scenario.json'))),
        code_sha256=code_digest([ROOT / 'tools' / 'microtom_stress.py'] + [p for p in mf.CODE_FILES if p.exists()]), parameter_sha256=registry_hash(registry_path),
        registry_path=str(Path(registry_path).relative_to(ROOT)).replace('\\', '/') if Path(registry_path).is_relative_to(ROOT) else str(registry_path),
        declared_hidden_state=plan['declared_hidden_state'], main_fixture_declared_reserve=plan['main_fixture_declared_reserve'], held_fixed=plan['held_fixed'],
        scenario_set=dict(parameter=sset['parameter'], values=sset['values'], reference='base', applied_side_by_side=True, pooled=False,
                          what_varies_between_stress_runs=f'{sset["parameter"]} on every S axis (M and root stay 1.0); the declared stress reserve is the same in all three'),
        members='none (registry declared values; no member draw)', engine='pipeline',
        state_advance_authority='tools.tomato_fsp_pipeline (prepare_run/run; results read from committed/step_NNNN only; advance_interval never called)',
        engine_runtime=dict(rays=fs['rays'], seed=fs['ensemble']['seed'], groimp_version=sorted({e.get('groimp_version', 'unavailable') for e in executions}),
                            java_version=sorted({e.get('java_version', '').strip().splitlines()[0] if e.get('java_version') else 'unavailable' for e in executions}),
                            native_elapsed_s_total=sum(float(e.get('elapsed_s', 0)) for e in executions)),
        cases=[dict(case_id=c['case_id'], scenario_id=c['scenario_id'], scenario_value=c['scenario_value'], reserve_gC=c['reserve_gC'], reserve_source_kind=c['reserve_source_kind'],
                    intervals=c['intervals'], run_dir=c['run_dir'], checkpoint_hashes=c['checkpoint_hashes'], any_binding=c['analysis']['any_binding'],
                    first_binding_step=c['analysis']['first_binding_step'], axis_sums=c['axis_sums']) for c in cases],
        checks=checks, all_checks_passed=all(v['passed'] for v in checks.values()),
        threshold=thr, direction=dict(passed=direction['passed'], first_binding_step=direction.get('first_binding_step'), allocation_split=direction.get('allocation_split'),
                                      last_step_per_axis=direction.get('last_step_per_axis')),
        horizon_run=horizon, transient_retries=transients,
        rerun_conditions={k: v for k, v in mf.RERUN_TRIGGERS.items() if k != 'initial_issue'},
        real_plant_verified=False, biological_validation='not_established', conditional_simulation=True, nutrient_feedback_enabled=False,
        forbidden_uses=['quoting any number here as a forecast or prediction', 'drawing a headline, interval or scenario range from it',
                        'consuming any run here as a forecast member (tools.microtom_forecast refuses the mark)', 'adopting the threshold or the stress reserve as the fixture value'])
    finalize_stress(folder, manifest)
    return folder


def finalize_stress(folder: Path, manifest: dict) -> dict:
    folder = Path(folder)
    require(not (folder / 'manifest.json').exists(), 'stress folder already finalized')
    require(manifest.get('reuse_as_prediction') == NO_REUSE and manifest.get('not_a_forecast') is True and manifest.get('fixture_purpose') == FIXTURE_PURPOSE,
            'stress manifest must carry the no-reuse flags')
    require(FORBIDDEN_STATUS not in str(manifest) and 'headline' not in manifest, 'a stress manifest carries no acceptance label and no headline')
    manifest = dict(manifest, schema=SCHEMA, artifact_hashes=artifact_hashes(folder, exclude=('manifest.json',)))
    manifest['artifact_digest'] = digest(manifest['artifact_hashes'])
    write_json(folder / 'manifest.json', manifest)
    return manifest


def verify_stress(folder: Path) -> dict:
    folder = Path(folder)
    manifest = read_json(folder / 'manifest.json')
    require(manifest.get('schema') == SCHEMA and manifest.get('reuse_as_prediction') == NO_REUSE, 'not a stress folder')
    require(artifact_hashes(folder, exclude=('manifest.json',)) == manifest['artifact_hashes'], 'stress folder changed after finalization')
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='op', required=True)
    p = sub.add_parser('run', help='run the stress fixture + reserve sweep (+ horizon run) into a new build/stress_<date>_<NN>')
    p.add_argument('--scenario', type=Path, required=True, help='the forecast scenario JSON whose package/light/lamps are reused (e.g. the F8 one)')
    p.add_argument('--stress-reserve', type=float, required=True, help='fixture_declared plant reserve (gC) for the three-scenario stress runs')
    p.add_argument('--sweep', type=float, nargs='+', required=True, help='fixture_declared reserve values (gC) for the base-scenario threshold sweep')
    p.add_argument('--horizon-days', type=int, default=None, help='run base at the DECLARED reserve for this many intervals')
    p.add_argument('--registry', type=Path, default=REGISTRY_PATH); p.add_argument('--out-root', type=Path, default=ROOT / 'build')
    p.add_argument('--timeout', type=float, default=1200); p.add_argument('--date', default=None); p.add_argument('--rays', type=int, default=None)
    p = sub.add_parser('verify', help='recompute the frozen-file hashes of a stress folder'); p.add_argument('folder', type=Path)
    a = parser.parse_args(argv)
    try:
        if a.op == 'run':
            folder = run_stress(a.scenario, a.stress_reserve, a.sweep, a.horizon_days, a.registry, a.out_root, a.timeout, a.date, a.rays)
            m = read_json(folder / 'manifest.json')
            print(json.dumps(dict(stress=str(folder), all_checks_passed=m['all_checks_passed'], threshold=m['threshold']['statement'],
                                  horizon=(m['horizon_run'] or {}).get('statement'), reuse_as_prediction=m['reuse_as_prediction']), indent=2))
        else:
            m = verify_stress(a.folder)
            print(json.dumps(dict(verified=str(a.folder), all_checks_passed=m['all_checks_passed'], reuse_as_prediction=m['reuse_as_prediction']), indent=2))
    except (ContractError, ValueError, KeyError, OSError, TimeoutError) as exc:
        parser.exit(1, f'{type(exc).__name__}: {exc}\n')


if __name__ == '__main__':
    main()
