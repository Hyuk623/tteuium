"""F10 (2026-10-13): per-interval carbon budget trajectory of pipeline members, base-only diagnostic issue. Software criteria only."""
from __future__ import annotations
import shutil
import uuid
from pathlib import Path

import pytest

from tools import microtom_forecast as mf
from tools import microtom_forecast_io as fio
from tools import microtom_parameters as mp
from tools.vtc_growth_io import ROOT, ContractError, read_json, rows, write_csv

P1 = ROOT / 'build' / 'p1_state_20261012_09'
SIDE_STOP = ROOT / 'build' / 'fsp_truss_20261012_acceptance_04' / 'side_stop'
F8_RUN = ROOT / 'build' / 'forecast_20261012_07' / 'scenarios' / 'base' / 'members' / 'm00' / 'run'


def _root() -> Path:
    return ROOT / 'build' / ('microtom_horizon_test_' + uuid.uuid4().hex)


def _scn(**kw) -> dict:
    s = mf.default_scenario('p1_pipeline', horizons_days=[1, 3], members=1, seed=5, rays=300000, diagnostic=True, p1_package='build/p1_state_20261012_09')
    s.update(kw)
    return s


def _mem_from_run(run_dir: Path, intervals: int) -> dict:
    scen = read_json(run_dir / 'scenario.json'); coll = read_json(run_dir / 'collection.json')
    return mf.load_pipeline_member(dict(run_dir=run_dir, scenario=scen, collection=coll, intervals=intervals))


def test_base_only_mode_is_declared_and_validated():
    if not P1.exists():
        pytest.skip('P1 package absent')
    s = _scn(); assert mf.validate_scenario(s)['scenario_set_mode'] == 'all'
    s = mf.default_scenario('p1_pipeline', horizons_days=[1], members=1, seed=5, rays=300000, diagnostic=True, p1_package='build/p1_state_20261012_09', base_only=True)
    assert mf.validate_scenario(s)['scenario_set_mode'] == 'base_only'
    s['scenario_set_mode'] = 'pooled'
    with pytest.raises(ContractError, match='scenario_set_mode'):
        mf.validate_scenario(s)
    old = _scn(); old.pop('scenario_set_mode')  # scenarios written before F10
    assert mf.validate_scenario(old)['scenario_set_mode'] == 'all'


def test_trajectory_of_f8_member_never_binds_and_carries_rays():
    if not (F8_RUN / 'committed' / 'step_0003').exists():
        pytest.skip('F8 forecast folder absent')
    mem = _mem_from_run(F8_RUN, 3)
    t = mf.carbon_trajectory('run', 'base', 1.0, 0, mem, 4800000)
    assert [r['day'] for r in t] == [1, 2, 3] and all(r['rays'] == 4800000 for r in t) and not any(r['cap_binding'] for r in t)
    assert t[0]['reserve_start_gC'] == 0.2 and t[0]['allocated_gC'] == pytest.approx(t[0]['demand_gC'])
    assert t[0]['budget_gC'] == pytest.approx(0.2 + t[0]['gross_gC'] - t[0]['maintenance_gC'])
    assert t[1]['reserve_start_gC'] == pytest.approx(t[0]['reserve_end_gC'])  # continuity
    s = mf.cap_summary(t, {'base': [mem]}, 3)
    assert s['per_scenario']['base']['binds_within_horizon'] is False and s['per_scenario']['base']['first_binding_day_min'] is None
    assert s['per_scenario']['base']['members'][0]['all_declared_axes_stopped_before_binding'] is False and s['rays'] == 4800000
    assert 'model_property' in s['label']


def _fake_member(root: Path, ends: list[float], binding_days: set[int], stops: list[tuple[int, str]] = ()) -> dict:
    run = root / uuid.uuid4().hex; events = []
    start = 0.2
    for k, end in enumerate(ends, start=1):
        step = run / 'committed' / f'step_{k:04d}'; step.mkdir(parents=True)
        demand, alloc = 0.05, (0.03 if k in binding_days else 0.05)
        write_csv(step / 'carbon_ledger.csv', [dict(interval=k - 1, plant_instance_id='p', reserve_start_gC=start, gross_gC=0.01, maintenance_gC=0.0002, structural_gC=0, growth_resp_gC=0,
                                                    reserve_end_gC=end, deficit_gC=0.0, residual_gC=0.0)])
        write_csv(step / 'axis_flux.csv', [dict(interval=k - 1, plant_instance_id='p', axis_id='M', parent_rank=0, absorbed_umol_s=0, gross_gC=0.01, maintenance_gC=0.0002,
                                                demand_gC=demand, allocated_gC=alloc, structural_gC=0, growth_resp_gC=0)])
        start = end
    for day, axis in stops:
        events.append(dict(day=str(day), organ_id=f'p/{axis}/Apex', parent_id='', event='determinate_stop', rule='two_successive_trusses', structural_gC='0', axis_id=axis))
    events.append(dict(day='2', organ_id='p/Truss9', parent_id='', event='funded_birth', rule='first_positive_allocation', structural_gC='1e-5', axis_id='M'))
    request = dict(axes=[dict(axis_id='M'), dict(axis_id='S1')], runtime=dict(rays=300000))
    return dict(run_dir=run, intervals=len(ends), events=events, request=request, plants=['p'])


def test_trajectory_turning_points_binding_and_growth_ending_events(tmp_path):
    mem = _fake_member(tmp_path, [0.06, 0.07, 0.09, 0.08, 0.05, 0.06], binding_days={5, 6}, stops=[(3, 'M'), (4, 'S1')])
    t = mf.carbon_trajectory('run', 'base', 1.0, 0, mem, 300000)
    tp = {r['day']: r['turning_point'] for r in t if r['turning_point']}
    assert tp == {3: 'peak', 5: 'trough'}
    assert [r['day'] for r in t if r['cap_binding']] == [5, 6] and t[4]['funded_fraction'] == pytest.approx(0.6)
    assert t[1]['events_this_day'] == 'funded_birth:p/Truss9' and t[2]['events_this_day'] == 'determinate_stop:p/M/Apex'
    s = mf.cap_summary(t, {'base': [mem]}, 6)['per_scenario']['base']
    assert s['binds_within_horizon'] is True and s['first_binding_day_min'] == 5
    m0 = s['members'][0]
    assert m0['determinate_stops_before_binding'] == [dict(day=3, axis_id='M', organ_id='p/M/Apex'), dict(day=4, axis_id='S1', organ_id='p/S1/Apex')]
    assert m0['all_declared_axes_stopped_before_binding'] is True  # every declared axis stopped before the cap bound: growth ended first
    assert m0['truss_births_before_binding'] == [dict(day=2, axis_id='M', organ_id='p/Truss9')] and m0['turning_points'][0]['kind'] == 'peak'
    assert m0['reserve_end_last_gC'] == {'p': 0.06}
    for row in t:
        assert set(row) == set(fio.TRAJECTORY_COLUMNS)


def test_issue_writes_trajectory_and_base_only_status():
    if not (P1.exists() and (SIDE_STOP / 'collection.json').exists()):
        pytest.skip('P1 package or verified side_stop run absent')
    root = _root()
    folder = mf.issue(_scn(scenario_set_mode='base_only'), out_root=root, date='20261013', existing_results=[SIDE_STOP])
    m = fio.verify_forecast(folder)
    assert m['scenario_set']['applied'] == ['base'] and m['scenario_set']['pooled'] is False
    # Codex's side_stop fixture declares a 0.003 gC reserve, so its cap binds from day 1: the mechanics are exercised, nothing is claimed about plants
    assert 'carbon_trajectory.csv' in m['artifact_hashes'] and m['carbon_cap']['per_scenario']['base']['binds_within_horizon'] is True
    assert m['carbon_cap']['per_scenario']['base']['first_binding_day_min'] == 1
    t = rows(folder / 'carbon_trajectory.csv')
    assert [r['day'] for r in t] == ['1', '2', '3'] and {r['scenario_id'] for r in t} == {'base'} and {r['rays'] for r in t} == {str(m['engine_runtime']['rays'])}
    assert {r['cap_binding'] for r in t} == {'True'} and float(t[0]['reserve_start_gC']) == 0.003
    shutil.rmtree(root, ignore_errors=True)


def test_registry_binding_day_row_is_model_property():
    by = {r['key']: r for r in mp.load_registry()}
    row = by['RESERVE_CAP_BINDING_DAY']
    assert row['source_kind'] == 'model_property' and row['engine_status'] == 'layer_only' and 'adopt' in row['note'] and 'build/forecast_20261013' in row['source_ref']
    assert row['unit'] == 'day' and 'rays' in row['uncertainty'] and by['PLANT_RESERVE_GC']['value'] == 0.2
