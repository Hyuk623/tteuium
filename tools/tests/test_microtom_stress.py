"""F9 (2026-10-13): allocation-cap stress fixture, reserve-threshold sweep, no-reuse flag. Software criteria only.

Deterministic tests use synthetic committed tables and the existing F8 member; the native test runs three one-interval
pipeline cases at a declared stress reserve and is skipped without GroIMP/Java or the P1 package.
"""
from __future__ import annotations
import json
import shutil
import uuid
from pathlib import Path

import pytest

from tools import microtom_forecast as mf
from tools import microtom_forecast_eval as fe
from tools import microtom_forecast_io as fio
from tools import microtom_parameters as mp
from tools import microtom_stress as ms
from tools.fsp_axes import allocation_reference
from tools.vtc_growth_io import ROOT, ContractError, read_json, rows, write_csv, write_json

P1 = ROOT / 'build' / 'p1_state_20261012_09'
F8 = ROOT / 'build' / 'forecast_20261012_07'
F7 = ROOT / 'build' / 'forecast_20261012_04'


def _root() -> Path:
    return ROOT / 'build' / ('microtom_stress_test_' + uuid.uuid4().hex)


def _scn(**kw) -> dict:
    s = mf.default_scenario('p1_pipeline', horizons_days=[1], members=1, seed=11, rays=100000, diagnostic=True, p1_package='build/p1_state_20261012_09')
    s.update(kw)
    return s


def _native_available() -> bool:
    from tools.groimp_light_sanity import CORE
    return CORE.is_file() and shutil.which('java') is not None


# ---- G2: the dominant assumption is recorded, never tuned ------------------------------------------------------
def test_g2_registry_records_reserve_as_user_assumed_hidden_state():
    registry = mp.load_registry()
    by = {r['key']: r for r in registry}
    row = by['PLANT_RESERVE_GC']
    assert row['value'] == 0.2 and row['unit'] == 'gC' and row['source_kind'] == 'user_assumed' and row['engine_status'] == 'hidden_state'
    assert row['engine_key'] == 'plant_initialization[].reserve_gC' and 'tomato_fsp_acceptance.py' in row['source_ref'] and 'F9' in row['uncertainty']
    assert row['uncertainty_kind'] == 'unavailable' and row['candidates'] is None  # never drawn, never a scenario set
    o = mp.build_request_overrides(registry)
    assert o['hidden_state']['PLANT_RESERVE_GC']['value'] == 0.2 and 'PLANT_RESERVE_GC' not in o['parameters'] and 'PLANT_RESERVE_GC' not in o['axis_parameters']
    assert ms.declared_reserve(registry)['value'] == 0.2
    assert 'PLANT_RESERVE_GC' not in {r['key'] for r in mp.sampled_rows(registry)}


def test_g2_threshold_row_is_a_model_property_never_adopted():
    registry = mp.load_registry()
    by = {r['key']: r for r in registry}
    row = by['RESERVE_CAP_THRESHOLD_GC']
    assert row['source_kind'] == 'model_property' and row['engine_status'] == 'layer_only' and 'adopt' in row['note']
    assert isinstance(row['value'], float) and 0.0 < row['value'] < by['PLANT_RESERVE_GC']['value']  # binds below the declared value
    assert 'build/stress_' in row['source_ref'] and 'bracket' in row['uncertainty']
    assert by['PLANT_RESERVE_GC']['value'] == 0.2  # the declared value did not move with the finding


def test_registry_vocabulary_rules_for_new_kinds(tmp_path):
    registry_text = mp.REGISTRY_PATH.read_text(encoding='utf-8-sig')
    bad = registry_text.replace('PLANT_RESERVE_GC,0.2,gC,user_assumed', 'PLANT_RESERVE_GC,0.2,gC,fixture_declared')
    p = tmp_path / 'r.csv'; p.write_text(bad, encoding='utf-8')
    with pytest.raises(ContractError, match='hidden_state row'):
        mp.load_registry(p)  # a fixture_declared value cannot pose as the engine's hidden state in the registry
    bad = registry_text.replace('PLANT_RESERVE_GC,0.2,gC,user_assumed', 'PLANT_RESERVE_GC,0.2,gC,measured')
    p.write_text(bad, encoding='utf-8')
    with pytest.raises(ContractError, match='measured'):
        mp.load_registry(p)


def test_main_fixture_declared_values_unchanged():
    if not P1.exists():
        pytest.skip('P1 package absent')
    from tools.tomato_fsp_acceptance import scenario_fixture
    out = _root()
    path = scenario_fixture(P1, out, intervals=1, rays=1000, state_source='fixture_truth')
    scen = read_json(path)
    declared = ms.declared_reserve(mp.load_registry())['value']
    assert {p['reserve_gC'] for p in scen['plant_initialization'].values()} == {declared}  # engine-owner fixture still declares 0.2 gC
    assert fio.NO_REUSE_MARK not in scen['initialization_provenance']
    for folder in (F8, F7):
        if not folder.exists():
            continue
        for sj in folder.glob('**/scenario/scenario.json'):
            s = read_json(sj)
            assert {p['reserve_gC'] for p in s['plant_initialization'].values()} == {declared} and fio.NO_REUSE_MARK not in s['initialization_provenance']
    shutil.rmtree(out, ignore_errors=True)


# ---- G1: stress plan, edit and the no-reuse flag ---------------------------------------------------------------
def test_reserve_edit_replaces_value_and_marks_provenance():
    scen = dict(plant_initialization={'a': dict(reserve_gC=0.2, root_mass_gDM=.04), 'b': dict(reserve_gC=0.2, root_mass_gDM=.04)},
                initialization_provenance='explicit synthetic boundary assumptions')
    record = {}
    out = ms.reserve_edit(0.05, record)(scen)
    assert {p['reserve_gC'] for p in out['plant_initialization'].values()} == {0.05} and scen['plant_initialization']['a']['reserve_gC'] == 0.2  # input untouched
    assert fio.NO_REUSE_MARK in out['initialization_provenance'] and ms.FIXTURE_PURPOSE in out['initialization_provenance'] and 'fixture_declared' in out['initialization_provenance']
    assert record['original_reserve_gC'] == {'a': 0.2, 'b': 0.2}
    assert out['plant_initialization']['a']['root_mass_gDM'] == .04  # only the reserve changes


def test_stress_plan_carries_purpose_flags_and_declared_kinds():
    if not P1.exists():
        pytest.skip('P1 package absent')
    declared = ms.declared_reserve(mp.load_registry())
    plan = ms.stress_scenario(_scn(), 0.1, [0.2, 0.1, 0.05], 8, declared)
    assert plan['fixture_purpose'] == 'exercise_allocation_cap' and plan['reuse_as_prediction'] == 'forbidden' and plan['not_a_forecast'] is True
    assert plan['declared_hidden_state']['reserve_gC'] == dict(value=0.1, unit='gC', source_kind='fixture_declared', engine_key='plant_initialization[].reserve_gC',
                                                               source_ref=plan['declared_hidden_state']['reserve_gC']['source_ref'])
    assert 'replaces' in plan['declared_hidden_state']['reserve_gC']['source_ref'] and plan['main_fixture_declared_reserve']['changed'] is False
    assert plan['sweep']['reserve_values_gC'] == [0.2, 0.1, 0.05] and plan['horizon_run']['reserve_gC'] == 0.2 and plan['horizon_run']['source_kind'] == 'user_assumed'
    assert plan['stress_runs']['members'].startswith('none') and 'APPLY_DETERMINATE_STOP = true' in ' '.join(plan['held_fixed'])
    with pytest.raises(ContractError, match='positive'):
        ms.stress_scenario(_scn(), 0.0, [0.2], None, declared)
    with pytest.raises(ContractError, match='distinct'):
        ms.stress_scenario(_scn(), 0.1, [0.2, 0.2], None, declared)
    seed = _scn(route='seed_route', engine='v3_direct', p1_package=None, start_time='2026-09-12T06:00:00+09:00')
    with pytest.raises(ContractError, match='pipeline'):
        ms.stress_scenario(seed, 0.1, [0.2], None, declared)


def test_forecast_layer_refuses_stress_runs_as_members():
    if not P1.exists():
        pytest.skip('P1 package absent')
    root = _root(); fake = root / 'stress_run'; fake.mkdir(parents=True)
    write_json(fake / 'scenario.json', dict(initialization_provenance=f'fixture_declared stress hidden state; {fio.NO_REUSE_MARK}', plant_initialization={}))
    write_json(fake / 'collection.json', dict(status='complete_conditional_trajectory', last_valid_boundary=1))
    with pytest.raises(ContractError, match='stress-fixture run'):
        mf.issue(_scn(), out_root=root, date='20261013', existing_results=[fake])
    failed = [p for p in root.iterdir() if p.name.startswith('forecast_')]
    assert failed and (failed[0] / 'FAILED.json').exists() and not (failed[0] / 'manifest.json').exists()
    # an engine-scenario edit that forgets the mark is refused before the engine is prepared
    with pytest.raises(ContractError, match='no-reuse mark'):
        mf.build_pipeline_member(root, _scn(), mp.load_registry(), 0, {}, 10, None, 'x', scenario_edit=lambda s: s)
    shutil.rmtree(root, ignore_errors=True)


def test_stress_folder_is_never_a_forecast(tmp_path):
    root = _root(); root.mkdir()
    folder = ms.new_stress_dir(root, '20261013')
    assert ms.FOLDER_RE.match(folder.name) and not fio.FOLDER_RE.match(folder.name)
    (folder / 'stress_steps.csv').write_text('x\n', encoding='utf-8')
    with pytest.raises(ContractError, match='no-reuse'):
        ms.finalize_stress(folder, dict(stress_run_id=folder.name))
    with pytest.raises(ContractError, match='headline'):
        ms.finalize_stress(folder, dict(fixture_purpose=ms.FIXTURE_PURPOSE, reuse_as_prediction='forbidden', not_a_forecast=True, headline='x'))
    ms.finalize_stress(folder, dict(fixture_purpose=ms.FIXTURE_PURPOSE, reuse_as_prediction='forbidden', not_a_forecast=True, all_checks_passed=True))
    assert ms.verify_stress(folder)['schema'] == ms.SCHEMA
    with pytest.raises(ContractError, match='not a forecast folder'):
        fio.verify_forecast(folder)
    with pytest.raises(ContractError, match='not a forecast folder'):
        fe.evaluate(folder, tmp_path / 'obs.csv', root / 'eval')
    assert fio.list_forecasts(root) == []
    with pytest.raises(ContractError, match='already finalized'):
        ms.finalize_stress(folder, dict(fixture_purpose=ms.FIXTURE_PURPOSE, reuse_as_prediction='forbidden', not_a_forecast=True))
    import tempfile
    with pytest.raises(ContractError, match='below project build'):
        ms.new_stress_dir(Path(tempfile.gettempdir()) / 'not_build', '20261013')  # pytest's tmp_path is configured under build/
    shutil.rmtree(root, ignore_errors=True)


# ---- analysis on synthetic committed tables ----------------------------------------------------------------------
def _fake_run(root: Path, name: str, reserve: float, gross: float, maint: float, demands: dict[str, list[float]], scales: dict[str, float],
              allocations: dict[str, list[float]] | None = None) -> Path:
    """One committed step for plant p with organs per axis; allocations default to the oracle (what the engine must produce)."""
    run = root / name; step = run / 'committed' / 'step_0001'; step.mkdir(parents=True)
    budget = reserve + gross - maint
    organs = [(aid, i, d) for aid, ds in demands.items() for i, d in enumerate(ds)]
    alloc = allocation_reference([d for _, _, d in organs], [scales[aid] for aid, _, _ in organs], budget) if allocations is None else \
        [allocations[aid][i] for aid, i, _ in organs]
    funded = sum(alloc); structural = funded * 0.75; gr = funded * 0.25
    write_csv(step / 'carbon_ledger.csv', [dict(interval=0, plant_instance_id='p', reserve_start_gC=reserve, gross_gC=gross, maintenance_gC=maint, structural_gC=structural,
                                                growth_resp_gC=gr, reserve_end_gC=max(0.0, budget - funded), deficit_gC=max(0.0, -budget), residual_gC=0.0)])
    write_csv(step / 'organ_allocations.csv', [dict(interval=0, plant_instance_id='p', organ_id=f'p|{aid}/{i}', absorbed_umol_s=0, gross_gC=0, maintenance_gC=0, target_gDM=0,
                                                    demand_gC=d, allocated_gC=a, structural_gC=a * .75, growth_resp_gC=a * .25, axis_id=aid, parent_rank=0, segment_index=1)
                                               for (aid, i, d), a in zip(organs, alloc)])
    write_csv(step / 'axis_flux.csv', [dict(interval=0, plant_instance_id='p', axis_id=aid, parent_rank=0, absorbed_umol_s=0, gross_gC=0, maintenance_gC=0,
                                            demand_gC=sum(ds), allocated_gC=sum(a for (x, _, _), a in zip(organs, alloc) if x == aid), structural_gC=0, growth_resp_gC=0)
                                       for aid, ds in demands.items()])
    write_csv(step / 'state.csv', [{'day': 1, 'plant_instance_id': 'p', 'organ_id': f'p|{aid}/{i}', 'axis_id': aid, 'class': 'Leaflet', 'area_m2': d * 1e-3}
                                   for aid, i, d in organs])
    return run


def test_analysis_detects_binding_proportionality_and_oracle(tmp_path):
    demands = {'M': [0.06, 0.04], 'S1': [0.03], 'S2': [0.02]}
    scales = {'M': 1.0, 'S1': 1.0, 'S2': 1.0}
    free = ms.analyse_run(_fake_run(tmp_path, 'free', 0.2, 0.012, 0.0002, demands, scales), 1, {('p', k): v for k, v in scales.items()})
    assert free['any_binding'] is False and free['max_oracle_abs_diff_gC'] <= ms.ORACLE_TOL and free['steps'][0]['funded_gC'] == pytest.approx(0.15)
    bound = ms.analyse_run(_fake_run(tmp_path, 'bound', 0.05, 0.012, 0.0002, demands, scales), 1, {('p', k): v for k, v in scales.items()})
    s = bound['steps'][0]
    assert bound['any_binding'] is True and bound['first_binding_step'] == 1 and s['funded_gC'] == pytest.approx(s['budget_gC'])
    assert s['cross_organ_ratio_spread'] <= 1e-12 and s['oracle_max_abs_diff_gC'] <= ms.ORACLE_TOL and s['law_abs_diff_gC'] <= 1e-12
    assert s['axes']['M']['allocated_share'] == pytest.approx(0.1 / 0.15)  # demand-proportional under the cap
    # a wrong (non-proportional) allocation is caught by the oracle even when the total is right
    wrong = ms.analyse_run(_fake_run(tmp_path, 'wrong', 0.05, 0.012, 0.0002, demands, scales,
                                     allocations={'M': [0.0418, 0.0], 'S1': [0.01], 'S2': [0.01]}), 1, {('p', k): v for k, v in scales.items()})
    assert wrong['max_oracle_abs_diff_gC'] > 1e-3 and wrong['steps'][0]['cross_organ_ratio_spread'] > 0.1
    rows_ = ms.step_rows(dict(case_id='c', scenario_id='base', scenario_value=1.0, reserve_gC=0.05, reserve_source_kind='fixture_declared', analysis=bound))
    assert {r['reuse_as_prediction'] for r in rows_} == {'forbidden'} and {r['axis_id'] for r in rows_} == {'M', 'S1', 'S2'} and all(r['cap_binding'] for r in rows_)


def test_direction_check_follows_the_declared_direction(tmp_path):
    demands = {'M': [0.06, 0.04], 'S1': [0.03], 'S2': [0.02]}
    cases = {}
    for label, sc in (('low', 0.5), ('base', 1.0), ('high', 2.0)):
        scales = {'M': 1.0, 'S1': sc, 'S2': sc}
        run = _fake_run(tmp_path, label, 0.05, 0.012, 0.0002, demands, scales)
        cases[label] = dict(analysis=ms.analyse_run(run, 1, {('p', k): v for k, v in scales.items()}))
    d = ms.direction_check(cases)
    assert d['passed'] is True and d['first_binding_step'] == 1
    split = d['allocation_split']['p']['per_scenario']
    assert split['low']['S_allocated_gC'] < split['base']['S_allocated_gC'] < split['high']['S_allocated_gC']
    assert split['low']['M_allocated_gC'] > split['base']['M_allocated_gC'] > split['high']['M_allocated_gC']
    assert all(v['funded_gC'] == pytest.approx(0.0618) for v in split.values())  # the cap fixes the total; only the split moves
    swapped = dict(cases, low=cases['high'], high=cases['low'])
    assert ms.direction_check(swapped)['passed'] is False
    unbound = {k: dict(analysis=ms.analyse_run(_fake_run(tmp_path, 'u' + k, 0.5, 0.012, 0.0002, demands, {'M': 1.0, 'S1': 1.0, 'S2': 1.0}), 1, {})) for k in cases}
    assert ms.direction_check(unbound)['passed'] is False and 'did not bind' in ms.direction_check(unbound)['reason']


def test_threshold_from_sweep_brackets_the_analytic_value():
    def case(r):
        binding = r < 0.142
        return dict(reserve_gC=r, analysis=dict(any_binding=binding, first_binding_step=1 if binding else None,
                                                steps=[dict(step=1, demand_gC=0.1536, gross_gC=0.0118, maintenance_gC=0.0002)]))
    t = ms.threshold_from_sweep([case(r) for r in (0.2, 0.15, 0.1425, 0.1415, 0.1, 0.05)])
    assert t['monotone_in_reserve'] is True and t['bracket_gC'] == dict(max_non_binding=0.1425, min_binding=0.1415)
    assert t['analytic_threshold']['value_gC'] == pytest.approx(0.142) and t['analytic_threshold']['spread_across_runs_gC'] == 0
    assert 'not adopted' in t['statement'] and 'binds below about 0.1420' in t['statement']


def test_f8_member_is_unbound_and_closed():
    run = F8 / 'scenarios' / 'base' / 'members' / 'm00' / 'run'
    if not (run / 'committed' / 'step_0003').exists():
        pytest.skip('F8 forecast folder absent')
    a = ms.analyse_run(run, 3, ms._axis_scales(read_json(run / 'scenario.json')))
    assert a['any_binding'] is False and a['max_oracle_abs_diff_gC'] <= ms.ORACLE_TOL and a['max_abs_residual_gC'] <= ms.CLOSURE_TOL
    s1 = a['steps'][0]
    assert s1['demand_gC'] - s1['gross_gC'] + s1['maintenance_gC'] == pytest.approx(0.1420, abs=5e-4)  # the F9 analytic threshold


# ---- native --------------------------------------------------------------------------------------------------------
def test_native_stress_fixture_binds_cap_and_separates_scenarios(monkeypatch):
    if not (_native_available() and P1.exists()):
        pytest.skip('GroIMP/Java or the P1 package is absent')
    import tools.tomato_fsp_pipeline as pipe
    monkeypatch.setattr(pipe, 'advance_interval', lambda *a, **k: (_ for _ in ()).throw(AssertionError('advance_interval must never be called')))
    root = _root(); root.mkdir()
    spath = root / 'f.json'; write_json(spath, _scn())
    folder = ms.run_stress(spath, 0.05, [0.05], None, out_root=root, date='20261013', rays=100000)
    m = ms.verify_stress(folder)
    assert m['all_checks_passed'] is True and m['checks']['cap_binds']['first_binding_step'] == 1 and m['checks']['direction']['passed'] is True
    assert m['checks']['main_fixture_unchanged']['engine_fixture_reserve_gC_before_edit'] == {'fx_ss0': 0.2}
    assert [c['case_id'] for c in m['cases']] == ['sweep_base_r0.0500', 'stress_low_r0.0500', 'stress_high_r0.0500']  # base reused from the sweep
    assert m['reuse_as_prediction'] == 'forbidden' and m['not_a_forecast'] is True and 'headline' not in m
    steps = rows(folder / 'stress_steps.csv')
    assert steps and {r['reuse_as_prediction'] for r in steps} == {'forbidden'} and {r['scenario_id'] for r in steps} == {'low', 'base', 'high'}
    for c in m['cases']:
        scen = read_json(folder / c['run_dir'] / 'scenario.json')
        assert fio.NO_REUSE_MARK in scen['initialization_provenance'] and {p['reserve_gC'] for p in scen['plant_initialization'].values()} == {0.05}
        assert rows(folder / c['run_dir'] / 'native_inputs' / 'plants.csv')[0]['provenance'].count(fio.NO_REUSE_MARK) == 1
    with pytest.raises(ContractError, match='not a forecast folder'):
        fio.verify_forecast(folder)
    with pytest.raises(ContractError, match='stress-fixture run'):
        mf.issue(_scn(), out_root=root, date='20261013', existing_results=[folder / m['cases'][0]['run_dir']])
    shutil.rmtree(root, ignore_errors=True)
