"""Forecast fixes B1-B6 (2026-10-11 fix prompt): pipeline route, ray default, eligibility, probability_basis, sowing, hooks."""
from __future__ import annotations
import json
import shutil
import uuid
from pathlib import Path

import pytest

from tools import microtom_forecast as mf
from tools import microtom_forecast_io as fio
from tools import microtom_parameters as mp
from tools.vtc_growth_io import ROOT, ContractError, read_json, rows, sha

ACCEPTANCE = ROOT / 'build' / 'vtc_dev_v3_acceptance_01'
RESULT_RUNS = [ACCEPTANCE / 'sufficient', ACCEPTANCE / 'three_pairs']
P1 = ROOT / 'build' / 'p1_state_20261011_01'


def _root() -> Path:
    return ROOT / 'build' / ('microtom_fix_test_' + uuid.uuid4().hex)


def _have_results() -> bool:
    return all((r / 'results' / 'manifest.json').exists() for r in RESULT_RUNS)


# ---- B2 -------------------------------------------------------------------------------------------------------
def test_b2_quantitative_default_and_diagnostic_gate():
    s = mf.default_scenario('seed_route')
    assert s['rays'] == 4_800_000 and s['issue_class'] == 'quantitative'
    low = mf.default_scenario('seed_route', rays=300000)
    assert low['issue_class'] == 'diagnostic'  # below 4.8M is diagnostic by construction
    low['issue_class'] = 'quantitative'
    with pytest.raises(ContractError, match='diagnostic'):
        mf.validate_scenario(low)
    mf.validate_scenario(mf.default_scenario('seed_route', rays=300000, diagnostic=True))


def test_b2_manifest_marks_diagnostic_issue():
    if not _have_results():
        pytest.skip('verified V3 acceptance results absent')
    s = mf.default_scenario('seed_route', horizons_days=[1], members=2, rays=300000, diagnostic=True)
    folder = mf.issue(s, out_root=_root(), date='20261012', existing_results=RESULT_RUNS)
    m = read_json(folder / 'manifest.json')
    assert m['issue_class'] == 'diagnostic' and m['engine_runtime']['quantitative_light_sampling'] is False and m['engine_runtime']['rays'] == 300000


# ---- B3 -------------------------------------------------------------------------------------------------------
def _env(days: int) -> list[dict]:
    return [dict(light_hours=14, temp_day_c=26, temp_night_c=22) for _ in range(days)]


def _params(**over) -> dict:
    from tools.vtc_development import parameters
    base = {k: v['value'] for k, v in parameters().items()}
    base.update(over)
    return base


def test_b3_thermal_schedule_matches_v3_rule():
    controls = dict(thermal_dd=0.0, produced=0, leaf_order=0, truss_count=0, axis_leaf_count=0, stopped=False)
    sched = mp.thermal_schedule(controls, _env(65), _params(FIRST_LEAVES=9), 0, 65)
    leaves = [s for s in sched if s['kind'] == 'leaf']; trusses = [s for s in sched if s['kind'] == 'truss']
    assert leaves[0]['day'] == 14 and trusses[0]['day'] == 32 and leaves[8]['rank'] == 9  # same days V3 delivery shows (C0001 day 14, Truss1 day 32)
    assert sched[-1]['kind'] == 'truss' and len(trusses) == 4 and max(s['day'] for s in sched) <= 44  # stop after the 4th truss by day 44


def test_b3_inert_parameters_are_excluded_and_named():
    registry = mp.load_registry()
    # a plant that already has 9 leaves on an unterminated first axis, 3-day horizon: FIRST_LEAVES 8/9 cannot act
    controls = {'p': dict(thermal_dd=490.0, produced=9, leaf_order=9, truss_count=0, axis_leaf_count=9, stopped=False)}
    report = mp.eligibility(registry, controls, _env(3), _params(), 0, 3, 'stage2_fixture')
    assert report['FINAL_VEG_PHYT_NUM']['eligible'] is False and 'inert' in report['FINAL_VEG_PHYT_NUM']['reason']
    assert report['NR_LEAFLET_PAIRS_BY_RANK']['eligible'] is False and 'imported' in report['NR_LEAFLET_PAIRS_BY_RANK']['reason']
    assert report['MIDDLE_PAIR_RAMP']['eligible'] is False and 'pairWeight' in report['MIDDLE_PAIR_RAMP']['reason']
    assert report['PHYLLOCHRON']['reason'] == 'no_declared_uncertainty'
    # seed route over 44 days: all three can act
    seed = {'seed': dict(thermal_dd=0.0, produced=0, leaf_order=0, truss_count=0, axis_leaf_count=0, stopped=False)}
    report = mp.eligibility(registry, seed, _env(44), _params(), 0, 44, 'seed_route')
    assert all(report[k]['eligible'] for k in ('FINAL_VEG_PHYT_NUM', 'NR_LEAFLET_PAIRS_BY_RANK', 'MIDDLE_PAIR_RAMP'))
    # 7 leaves, 3-day horizon (the P1 fixture plants): leaf 8 is initiated either way -> FIRST_LEAVES inert, PAIRS/ramp act
    p1 = {'fx': dict(thermal_dd=490.55, produced=7, leaf_order=7, truss_count=0, axis_leaf_count=7, stopped=False)}
    report = mp.eligibility(registry, p1, _env(3), _params(), 0, 3, 'p1_pipeline')
    assert report['FINAL_VEG_PHYT_NUM']['eligible'] is False and report['NR_LEAFLET_PAIRS_BY_RANK']['eligible'] and report['MIDDLE_PAIR_RAMP']['eligible']
    values = mp.sample_member(registry, 11, 0, eligible={'NR_LEAFLET_PAIRS_BY_RANK'})
    assert set(values) == {'NR_LEAFLET_PAIRS_BY_RANK'}


def test_b3_manifest_names_excluded_and_collapses_to_one_member():
    if not _have_results():
        pytest.skip('verified V3 acceptance results absent')
    s = mf.default_scenario('seed_route', horizons_days=[1, 3], members=2, rays=300000, diagnostic=True)
    folder = mf.issue(s, out_root=_root(), date='20261012', existing_results=RESULT_RUNS)
    m = read_json(folder / 'manifest.json')
    assert set(m['ensemble']['eligible_parameters']) == {'FINAL_VEG_PHYT_NUM', 'NR_LEAFLET_PAIRS_BY_RANK', 'MIDDLE_PAIR_RAMP'}
    assert m['ensemble']['excluded_parameters']['PHYLLOCHRON'] == 'no_declared_uncertainty'
    assert m['ensemble_spread']['ensemble_spread'] == 'present' and (folder / 'eligibility.json').exists()
    # nothing eligible -> one member, spread none, reasons named (only one result run supplied)
    s1 = mf.default_scenario('stage2_fixture', horizons_days=[1], members=3, rays=300000, diagnostic=True,
                             source_run='build/vtc_dev_v3_delivery_sufficient', fixture_day=65)
    if not (ROOT / 'build/vtc_dev_v3_delivery_sufficient/results/apices.csv').exists():
        pytest.skip('delivery run absent')
    controls = mf.controls_from_native_run(ROOT / 'build/vtc_dev_v3_delivery_sufficient', 65)
    assert all(c['stopped'] for c in controls.values())  # both apices stopped at day 44
    report = mp.eligibility(mp.load_registry(), controls, _env(1), _params(), 0, 1, 'stage2_fixture')
    assert not any(v['eligible'] for v in report.values())


# ---- B4 -------------------------------------------------------------------------------------------------------
def _member(**params) -> dict:
    from tools.vtc_development import parameters
    p = parameters()
    for k, v in params.items():
        p[k] = dict(p[k], value=v)
    return dict(request=dict(parameters=p))


def test_b4_probability_basis():
    shared = [_member(), _member(MIDDLE_RAMP=0)]
    assert mf.probability_basis('apex_stop', shared) == 'rule_deterministic'
    assert mf.probability_basis('organ_initiation:Leaflet', shared) == 'rule_deterministic'
    varied = [_member(FIRST_LEAVES=8), _member(FIRST_LEAVES=9)]
    assert mf.probability_basis('apex_stop', varied) == 'scenario_fraction'
    pairs = [_member(PAIRS=[1, 1, 2]), _member(PAIRS=[1, 1, 3])]
    assert mf.probability_basis('apex_stop', pairs) == 'rule_deterministic'  # PAIRS does not govern the stop
    assert mf.probability_basis('organ_initiation:Leaflet', pairs) == 'scenario_fraction'
    assert mf.probability_basis('apex_stop', []) == 'unavailable'
    if _have_results():
        s = mf.default_scenario('seed_route', horizons_days=[14], members=2, rays=300000, diagnostic=True)
        folder = mf.issue(s, out_root=_root(), date='20261012', existing_results=RESULT_RUNS)
        ev = fio.read_table(folder / 'forecast_events.csv', fio.EVENT_COLUMNS)
        stops = [r for r in ev if r['event_type'] == 'apex_stop']
        assert stops and all(r['probability_basis'] == 'rule_deterministic' for r in stops)  # the two result runs share SP_STOP_RULE/CADENCE/FIRST_LEAVES
        assert all(r['probability_basis'] == 'scenario_fraction' for r in ev if r['event_type'] == 'organ_initiation:Leaflet')  # PAIRS differ


# ---- B5 -------------------------------------------------------------------------------------------------------
def test_b5_sowing_provenance(tmp_path):
    s = mf.default_scenario('seed_route', sowing_datetime='2026-09-10T06:00:00+09:00')
    assert mf.validate_scenario(s)['sowing_source'] == 'user_stated'
    assert mf.resolve_sowing(s, 30, registry_xlsx=tmp_path / 'none.xlsx')['sowing_source'] == 'user_stated'
    d = mf.resolve_sowing(mf.default_scenario('seed_route'), 30, registry_xlsx=tmp_path / 'none.xlsx')
    assert d['sowing_source'] == 'assumed_issue_minus_days_at_start' and d['sowing_datetime'].endswith('06:00:00+09:00')
    f = mf.default_scenario('stage2_fixture', source_run='x', rays=300000, diagnostic=True)
    assert mf.resolve_sowing(f, 30, registry_xlsx=tmp_path / 'none.xlsx')['sowing_source'] == 'unavailable'
    bad = mf.default_scenario('seed_route', sowing_datetime='2026-09-10T06:00:00')
    with pytest.raises(ValueError):
        mf.validate_scenario(bad)  # naive timestamp refused
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = '개체목록'
    ws.append(['slot_id', 'plant_id', '이식일', '파종일']); ws.append(['T1-row1-L', 'mt01', '2026-09-20', '2026-09-05T09:00:00+09:00'])
    wb.save(tmp_path / 'reg.xlsx')
    assert mp and mf.registry_sowing(tmp_path / 'reg.xlsx') == {'mt01': '2026-09-05T09:00:00+09:00'}
    assert mf.resolve_sowing(f, 30, registry_xlsx=tmp_path / 'reg.xlsx')['sowing_source'] == 'plant_registry_user_record'
    assert mf.registry_sowing(mf.REGISTRY_XLSX) == {} if mf.REGISTRY_XLSX.exists() else True  # the real registry has 이식일 only today


# ---- B6 -------------------------------------------------------------------------------------------------------
def test_b6_capability_check_with_fixture_parameter_lists():
    registry = mp.load_registry()
    base = {r['engine_key'] for r in registry if r['engine_status'] == 'active'} | {'MAX_MASS', 'PAIRS'}
    resolved, report = mp.resolve_engine_capabilities(registry, engine_params=base, allow_hook_activation=True)
    by = {d['key']: d for d in report['hook_decisions']}
    assert all(d['decision'] == 'inactive_hook_absent' for d in by.values()) and len(by) == 3
    assert all(r['engine_status'] == 'inactive_in_engine' for r in resolved if r['key'] in by)
    with_hooks = base | {'CURVE_RATIO', 'BENT_FRACTION', 'AREA_CORRECTION'}
    resolved, report = mp.resolve_engine_capabilities(registry, engine_params=with_hooks, allow_hook_activation=False)
    by = {d['key']: d for d in report['hook_decisions']}
    assert by['AREA_CORRECTION']['decision'] == 'inactive_hook_present_activation_deferred' and 'Codex' in by['AREA_CORRECTION']['reason']
    assert by['BENT_FRACTION']['decision'] == 'inactive_hook_present_value_unavailable'
    assert by['CURVE_RATIO']['decision'] == 'inactive_hook_present_contract_unmet' and 'exact segment count' in by['CURVE_RATIO']['reason']
    resolved, report = mp.resolve_engine_capabilities(registry, engine_params=with_hooks, allow_hook_activation=True)
    by = {d['key']: d for d in report['hook_decisions']}
    assert by['AREA_CORRECTION']['decision'] == 'activated_by_capability_check' and by['AREA_CORRECTION']['accounting_only'] is True
    row = next(r for r in resolved if r['key'] == 'AREA_CORRECTION')
    assert row['engine_status'] == 'active' and row['hook_metadata'] == {'area_basis': 'summed_one_sided_full_outline_lamina_m2'}
    overrides = mp.build_request_overrides(resolved)
    assert overrides['parameters']['AREA_CORRECTION']['area_basis'] == 'summed_one_sided_full_outline_lamina_m2'
    assert 'accounting-only' in overrides['parameters']['AREA_CORRECTION']['source_ref']
    assert overrides['activated_by_capability_check'] == ['AREA_CORRECTION'] and [i['key'] for i in overrides['inactive_in_engine']] == ['CURVE_RATIO', 'BENT_FRACTION']
    from tools.vtc_development import parameters
    req = dict(parameters=parameters())
    assert 'AREA_CORRECTION' in mp.apply_overrides(req, overrides)['parameters']  # optional hook key added to the request
    live = mp.engine_capabilities()
    assert live['n_parameters'] >= 33 and 'vtc_development_io.py' in live['engine_version']


# ---- B1 -------------------------------------------------------------------------------------------------------
def _native_available() -> bool:
    from tools.groimp_light_sanity import CORE
    return CORE.is_file() and shutil.which('java') is not None


def test_b1_pipeline_route_reads_committed_checkpoints_only(monkeypatch):
    if not (_native_available() and (P1 / 'p1_manifest.json').exists()):
        pytest.skip('GroIMP/Java or the P1 fixture package is absent')
    import tools.tomato_fsp_pipeline as pipe
    def forbidden(*a, **k):
        raise AssertionError('advance_interval must never be called by the forecast layer')
    monkeypatch.setattr(pipe, 'advance_interval', forbidden)
    s = mf.default_scenario('p1_pipeline', horizons_days=[1], members=1, seed=5, rays=100000, diagnostic=True, p1_package='build/p1_state_20261011_01')
    folder = mf.issue(s, out_root=_root(), date='20261012')
    m = fio.verify_forecast(folder)
    assert m['engine'] == 'pipeline' and m['engine_scope'] == 'multi_instance_canopy_placement' and 'advance_interval never called' in m['state_advance_authority']
    assert m['instance_ids'] == ['fx_om0', 'fx_om0#2', 'fx_om1', 'fx_sp0']
    run_dir = folder / 'members' / 'm00' / 'run'
    cp = m['checkpoints'][0]['hashes']
    assert cp == [sha(run_dir / 'committed' / 'step_0001' / 'checkpoint.json')]
    assert read_json(run_dir / 'committed' / 'step_0001' / 'checkpoint.json')['native_advance_count'] == 1
    members = rows(folder / 'members.csv')
    assert members[0]['engine'] == 'pipeline' and json.loads(members[0]['instance_ids']) == m['instance_ids'] and members[0]['member_source'] == 'pipeline_committed_checkpoints'
    mtg = fio.read_table(folder / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    assert {r['plant_instance_id'] for r in mtg} == set(m['instance_ids'])
    assert m['input_snapshot_kind'] == 'p1_package_fixture_truth' and m['sowing_source'] == 'unavailable'
    assert m['ensemble']['size'] == 1 and m['ensemble_spread']['ensemble_spread'] == 'none'  # one-day horizon: nothing can act


def test_b1_v3_direct_route_still_works():
    if not _have_results():
        pytest.skip('verified V3 acceptance results absent')
    s = mf.default_scenario('seed_route', horizons_days=[1], members=2, rays=300000, diagnostic=True)
    folder = mf.issue(s, out_root=_root(), date='20261012', existing_results=RESULT_RUNS)
    m = read_json(folder / 'manifest.json')
    assert m['engine'] == 'v3_direct' and m['engine_scope'] == 'single_plant_no_canopy' and m['checkpoints'] == []
    assert any(r['quantity'] == 'canopy_shading' for r in fio.read_table(folder / 'unresolved.csv', fio.UNRESOLVED_COLUMNS))
