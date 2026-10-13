"""P3 V3 axis/truss/segment-aware forecasting: software criteria only (no biological claim).

Deterministic tests consume Codex's verified side-axis runs (committed checkpoints) and the P1 fixture package
`build/p1_state_20261012_09`; the native test runs one pipeline member and is skipped without GroIMP/Java.
"""
from __future__ import annotations
import json
import shutil
import uuid
from pathlib import Path

import pytest

from tools import microtom_axes as ax
from tools import microtom_forecast as mf
from tools import microtom_forecast_eval as fe
from tools import microtom_forecast_io as fio
from tools import microtom_parameters as mp
from tools.vtc_growth_io import ROOT, ContractError, read_json, rows, sha, write_csv

P1 = ROOT / 'build' / 'p1_state_20261012_09'
SIDE_STOP = ROOT / 'build' / 'fsp_truss_20261012_acceptance_04' / 'side_stop'
BOTH_STOPPED = ROOT / 'build' / 'fsp_truss_20261012_acceptance_04' / 'both_stopped'
LEGACY_RUN = ROOT / 'build' / 'fsp_integration_20261011_producer_run_02'  # no axes.csv: legacy single-axis package


def _root() -> Path:
    return ROOT / 'build' / ('microtom_axes_test_' + uuid.uuid4().hex)


def _scn(**kw) -> dict:
    s = mf.default_scenario('p1_pipeline', horizons_days=[1, 3], members=1, seed=5, rays=300000, diagnostic=True, p1_package='build/p1_state_20261012_09')
    s.update(kw)
    return s


def _have(*paths: Path) -> bool:
    return all(p.exists() for p in paths)


# ---- F1 registry -----------------------------------------------------------------------------------------------
def test_f1_registry_axis_rows_and_provenance_separation():
    registry = mp.load_registry()
    by = {r['key']: r for r in registry}
    assert by['SUBSTEM_SINK_SCALE']['engine_status'] == 'axis' and by['SUBSTEM_SINK_SCALE']['value'] == 1.0 and by['SUBSTEM_SINK_SCALE']['source_kind'] == 'user_assumed'
    assert by['APPLY_DETERMINATE_STOP']['engine_status'] == 'axis' and by['APPLY_DETERMINATE_STOP']['value'] is True and by['APPLY_DETERMINATE_STOP']['source_kind'] == 'user_assumed'
    assert by['SUBSTEM_TRUSS_APPLICABILITY']['source_kind'] == 'user_stated' and by['SUBSTEM_TRUSS_APPLICABILITY']['engine_status'] == 'layer_only'
    assert by['AXIS_CADENCE_PER_AXIS']['engine_status'] == 'blocked_engine_extension' and by['AXIS_CADENCE_PER_AXIS']['value'] == 'unavailable'
    assert 'SHARED' in by['TRUSS_INTERVAL']['note']
    o = mp.build_request_overrides(registry)
    assert set(o['axis_parameters']) == {'SUBSTEM_SINK_SCALE', 'APPLY_DETERMINATE_STOP'} and o['blocked_engine_extension'][0]['key'] == 'AXIS_CADENCE_PER_AXIS'
    assert 'CADENCE' in o['parameters'] and 'CADENCE' not in o['axis_parameters']  # shared, never per axis
    # the per-axis entries satisfy the engine owner's record validator
    from tools.fsp_axes import validate_records
    rec = dict(plant_instance_id='p', axis_id='M', axis_vertex_id='p/A0', order=0, parent_axis_id='', parent_node_id='', parent_rank=0, stage='main',
               source_kind='synthetic_assumed', source_ref='t', registration_leaf_ids=[], parameters=o['axis_parameters'],
               initialization=dict(thermal_dd=1.0, produced=0, leaf_order=0, truss_count=0, axis_leaf_count=0, apex_stopped=False, stem_mass_gDM=.02, stem_width_m=.002,
                                   source_kind='user_assumed', source_ref='t'))
    validate_records(dict(axis_contract='fsp-axes-1', topology_scope='provided_axes', topology_completeness='unavailable', axes=[rec]), {'p'})


# ---- F2 input state --------------------------------------------------------------------------------------------
def test_f2_two_parent_rank_meanings_never_cross():
    if not P1.exists():
        pytest.skip('P1 fixture package absent')
    t = ax.read_axis_tables(P1, {'fx_ss0': 'c2'})
    axes = {a['axis_id']: a for a in t['axes']}
    assert ax.axis_attachment_rank(axes['S1']) == 2 and ax.axis_attachment_rank(axes['S2']) == 5 and ax.axis_attachment_rank(axes['M']) == 0
    trusses = {r['truss_vertex_id']: r for r in t['trusses']}
    assert ax.truss_above_rank(trusses['fx_ss0/F0001']) == 4 and trusses['fx_ss0/F0001']['axis_id'] == 'M'
    assert ax.truss_above_rank(trusses['fx_ss0/F0002']) == 3 and trusses['fx_ss0/F0002']['axis_id'] == 'S1'
    assert 'parent_rank' not in axes['S1'] and 'parent_rank' not in trusses['fx_ss0/F0002']  # the ambiguous key is gone
    with pytest.raises(ContractError, match='truss_above_rank'):
        ax.axis_attachment_rank(trusses['fx_ss0/F0002'])  # a truss's above-rank (3) must never be read as an attachment
    with pytest.raises(ContractError, match='axil_parent_rank'):
        ax.truss_above_rank(axes['S1'])


def test_f2_axis_records_copy_producer_values_and_never_derive_segments():
    if not P1.exists():
        pytest.skip('P1 fixture package absent')
    registry = mp.load_registry(); o = mp.build_request_overrides(registry)
    caps = {'fx_ss0': 'c2'}
    vertices = ax.selected_vertices(P1, caps, 'fixture_truth')
    records, notes = ax.build_axis_records(P1, caps, vertices, o['axis_parameters'], mf.AXIS_HIDDEN_DEFAULT, dict(GERMINATION_DD=206.3, PHYLLOCHRON_DD=37.9))
    by = {r['axis_id']: r for r in records}
    assert by['S1']['parent_rank'] == 2 and by['S2']['parent_rank'] == 5 and by['M']['parent_rank'] == 0
    assert by['M']['segment_index'] == 2 and by['S1']['segment_index'] == 2 and by['S2']['segment_index'] == 1  # producer values verbatim
    assert by['M']['initialization']['truss_count'] == 1 and by['S1']['initialization']['truss_count'] == 1 and by['S2']['initialization']['truss_count'] == 0
    assert by['M']['parameters']['SUBSTEM_SINK_SCALE']['value'] == 1.0 and by['S1']['initialization']['apex_stopped'] is False
    assert by['S2']['registration_leaf_ids'] == ['fx_ss0/C0010', 'fx_ss0/C0011'] and by['M']['registration_leaf_ids'] == []
    assert notes['trusses'][1]['truss_above_rank'] == 3 and notes['fx_ss0/S1']['axil_parent_rank'] == 2
    from tools.fsp_axes import select_axes
    selected, _ = select_axes(P1, dict(axis_contract='fsp-axes-1', topology_scope='provided_axes', topology_completeness='unavailable', captures_by_instance=caps, axes=records), vertices)
    sel = {a['axis_id']: a for a in selected}
    assert sel['M']['truss_history'] == [dict(node_id='fx_ss0/F0001', segment_index=1)] and sel['S1']['truss_history'] == [dict(node_id='fx_ss0/F0002', segment_index=1)]
    assert all(a['truss_rule_status'] == 'available' for a in selected)
    # an unavailable producer segment stays unavailable and the axis's truss rule reports unavailable (never derived from rank/age/count)
    tmp = ROOT / 'build' / ('microtom_axes_pkg_' + uuid.uuid4().hex); shutil.copytree(P1, tmp)
    table = rows(tmp / 'axes.csv')
    for r in table:
        if r['axis_id'] == 'S2' and r['capture_id'] == 'c2':
            r['segment_index'] = 'unavailable'; r['segment_index__status'] = 'unavailable'
    write_csv(tmp / 'axes.csv', table, list(table[0]))
    vv = []
    for v in ax.selected_vertices(tmp, caps, 'fixture_truth'):
        if v['vertex_id'] in ('fx_ss0/S2', 'fx_ss0/C0010', 'fx_ss0/C0011') or (v.get('axis') == 'S2'):
            v = dict(v, segment_index='unavailable', segment_index__status='unavailable')
        vv.append(v)
    records2, _ = ax.build_axis_records(tmp, caps, vv, o['axis_parameters'], mf.AXIS_HIDDEN_DEFAULT, dict(GERMINATION_DD=206.3, PHYLLOCHRON_DD=37.9))
    s2 = next(r for r in records2 if r['axis_id'] == 'S2')
    assert 'segment_index' not in s2
    selected2, _ = select_axes(tmp, dict(axis_contract='fsp-axes-1', topology_scope='provided_axes', topology_completeness='unavailable', captures_by_instance=caps, axes=records2), vv)
    s2 = next(a for a in selected2 if a['axis_id'] == 'S2')
    assert s2['segment_index'] == 'unavailable' and s2['truss_rule_status'] == 'unavailable'
    assert ax.axis_controls(selected2)['fx_ss0/S2']['can_truss'] is False


def test_f2_truss_geometry_supplement_is_labelled_bookkeeping():
    if not P1.exists():
        pytest.skip('P1 fixture package absent')
    vertices = ax.selected_vertices(P1, {'fx_ss0': 'c2'}, 'fixture_truth')
    init = {}
    done = ax.truss_geometry_supplement(init, vertices)
    assert set(done) == {'fx_ss0|fx_ss0/F0001', 'fx_ss0|fx_ss0/F0002'}
    e = init['fx_ss0|fx_ss0/F0001']
    assert e['base_xyz_m'] == [0, 0, 0] == e['tip_xyz_m'] and e['geometry_source_kind'] == 'user_assumed' and ax.ZERO_EXTENT_LABEL in e['geometry_source_ref']
    assert 'not an observed truss location' in e['geometry_source_ref']


# ---- F3 ensemble -----------------------------------------------------------------------------------------------
def test_f3_axis_parameters_in_eligibility_without_invented_ranges():
    registry = mp.load_registry()
    env = [dict(light_hours=14, temp_day_c=26, temp_night_c=22) for _ in range(3)]
    from tools.vtc_development import parameters
    base = {k: v['value'] for k, v in parameters().items()}
    controls = {'p/M': dict(thermal_dd=400.0, produced=5, leaf_order=5, truss_count=0, axis_leaf_count=5, stopped=False, is_substem=False, can_truss=True),
                'p/S1': dict(thermal_dd=300.0, produced=2, leaf_order=2, truss_count=0, axis_leaf_count=2, stopped=False, is_substem=True, can_truss=True)}
    report = mp.eligibility(registry, controls, env, base, 0, 3, 'p1_pipeline')
    assert report['SUBSTEM_SINK_SCALE']['structurally_eligible'] is True and report['SUBSTEM_SINK_SCALE']['eligible'] is False
    assert report['SUBSTEM_SINK_SCALE']['reason'].startswith('scenario_set')  # F8: declared scenario set, reported side by side, never drawn
    assert report['APPLY_DETERMINATE_STOP']['structurally_eligible'] is True and 'no_declared_uncertainty' in report['APPLY_DETERMINATE_STOP']['reason']
    stopped = {'p/M': dict(controls['p/M'], stopped=True, can_truss=False)}
    report = mp.eligibility(registry, stopped, env, base, 0, 3, 'p1_pipeline')
    assert report['SUBSTEM_SINK_SCALE']['structurally_eligible'] is False and report['APPLY_DETERMINATE_STOP']['structurally_eligible'] is False
    assert 'SUBSTEM_SINK_SCALE' not in mp.sample_member(registry, 1, 0)  # never drawn without a declared candidate set


# ---- F4 outputs from Codex's verified runs -----------------------------------------------------------------------
@pytest.fixture
def side_stop_forecast() -> Path:
    if not _have(P1, SIDE_STOP / 'collection.json'):
        pytest.skip('P1 package or verified side_stop run absent')
    return mf.issue(_scn(), out_root=_root(), date='20261012', existing_results=[SIDE_STOP])


def test_f4_axis_columns_round_trip_and_counters_kept_apart(side_stop_forecast):
    m = fio.verify_forecast(side_stop_forecast)
    assert m['axis_mode'] == 'fsp-axes-1' and {a['axis_id'] for a in m['axes']} == {'M', 'S1'}
    s1 = next(a for a in m['axes'] if a['axis_id'] == 'S1')
    assert s1['axil_parent_rank'] == 1 and s1['producer_segment_index'] == 4 and s1['axis_segment_index_at_boundary_1'] == '5' and s1['truss_rule_status'] == 'available'
    mtg = fio.read_table(side_stop_forecast / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    s1_rows = [r for r in mtg if r['axis_id'] == 'S1']
    assert s1_rows and {r['axil_parent_rank'] for r in s1_rows} == {'1'} and {r['axis_segment_index'] for r in s1_rows} == {'5'}
    assert {r['organ_segment_index'] for r in s1_rows} >= {'1', '2', '3', '4'}  # immutable organ segments differ from the current counter 5
    m_rows = [r for r in mtg if r['axis_id'] == 'M']
    assert m_rows and {r['axil_parent_rank'] for r in m_rows} == {'0'}
    assert m['axis_columns']['axil_parent_rank'].startswith('side attachment rank') and 'truss above-rank' in m['axis_columns']['axil_parent_rank']
    inv = fio.read_table(side_stop_forecast / 'forecast_intervals.csv', fio.INTERVAL_COLUMNS)
    assert {r['axis_id'] for r in inv} >= {'M', 'S1', 'plant'}
    per_axis = {(r['axis_id'], r['quantity'], r['horizon_day']): r for r in inv if r['forecast_id'].endswith('/Axis')}
    assert float(per_axis[('S1', 'axis_leaf_count', '3')]['point']) == 2.0 and float(per_axis[('M', 'axis_leaf_count', '3')]['point']) == 7.0
    assert float(per_axis[('S1', 'axis_truss_count_generated', '3')]['point']) == 1.0 and float(per_axis[('S1', 'axis_truss_count_registry', '3')]['point']) == 3.0
    assert m['axis_sums_check'][0]['status'] == 'axis_sums_match_plant_ledger' and m['axis_sums_check'][0]['max_abs_difference_gC'] < 1e-12


def test_f4_generated_trusses_never_labelled_observed_and_stopped_axis_emits_no_new_leaf(side_stop_forecast):
    mtg = fio.read_table(side_stop_forecast / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    trusses = [r for r in mtg if r['class'] == 'TrussAxis']
    assert {r['truss_provenance'] for r in trusses} == {'registry_truss', 'generated_truss'}
    assert all(r['truss_provenance'] == 'generated_truss' for r in trusses if r['root_relation'] == 'new_organ')
    assert all(r['truss_provenance'] == 'registry_truss' for r in trusses if r['root_relation'] == 'continuation')
    assert all(r['truss_provenance'] == 'n/a' for r in mtg if r['class'] != 'TrussAxis')
    ev = {(r['axis_id'], r['event_type'], r['horizon_day']): r for r in fio.read_table(side_stop_forecast / 'forecast_events.csv', fio.EVENT_COLUMNS) if r['scope_id'].endswith('/Axis')}
    assert ev[('S1', 'apex_stop', '1')]['probability'] == '1.0' and ev[('S1', 'apex_stop', '1')]['probability_basis'] == 'rule_deterministic'
    assert ev[('S1', 'new_truss_generated', '1')]['probability'] == '1.0' and ev[('S1', 'new_truss_generated', '1')]['truss_provenance'] == 'generated_truss'
    assert ev[('S1', 'new_leaf', '3')]['probability'] == '0.0' and ev[('M', 'new_leaf', '3')]['probability'] == '1.0'
    assert ev[('M', 'apex_stop', '3')]['probability'] == '0.0'
    inv = {(r['axis_id'], r['quantity'], r['horizon_day']): float(r['point']) for r in fio.read_table(side_stop_forecast / 'forecast_intervals.csv', fio.INTERVAL_COLUMNS) if r['forecast_id'].endswith('/Axis')}
    assert inv[('S1', 'axis_leaf_area_mm2', '3')] > inv[('S1', 'axis_leaf_area_mm2', '1')]  # existing S1 tissue keeps growing after its stop
    m = read_json(side_stop_forecast / 'manifest.json')
    assert m['headline'].startswith('Conditional') and m['real_plant_verified'] is False and m['topology_scope'] == 'provided_axes' and m['completeness'] == 'unavailable'


def test_f4_no_invented_axes_on_legacy_package():
    if not _have(LEGACY_RUN / 'collection.json', ROOT / 'build' / 'p1_state_20261011_01'):
        pytest.skip('legacy pipeline run absent')
    s = mf.default_scenario('p1_pipeline', horizons_days=[1], members=1, seed=5, rays=300000, diagnostic=True, p1_package='build/p1_state_20261011_01')
    folder = mf.issue(s, out_root=_root(), date='20261012', existing_results=[LEGACY_RUN])
    m = read_json(folder / 'manifest.json')
    assert m['axis_mode'].startswith('legacy') and m['axes'] == []
    mtg = fio.read_table(folder / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    assert not any(r['axis_id'].startswith('S') for r in mtg) and {r['axis_id'] for r in mtg} == {'M'}


def test_f4_reproducible_and_immutable_from_committed_checkpoints():
    if not _have(P1, SIDE_STOP / 'collection.json'):
        pytest.skip('P1 package or verified side_stop run absent')
    a = mf.issue(_scn(), out_root=_root(), date='20261012', existing_results=[SIDE_STOP])
    b = mf.issue(_scn(), out_root=_root(), date='20261012', existing_results=[SIDE_STOP])
    files = lambda f: {p.relative_to(f).as_posix(): p.read_bytes() for p in f.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    assert files(a) == files(b)
    ma, mb = read_json(a / 'manifest.json'), read_json(b / 'manifest.json')
    assert {k for k in ma if ma[k] != mb[k]} <= {'issued_at'}
    assert ma['checkpoints'][0]['hashes'] == [sha(SIDE_STOP / 'committed' / f'step_{k:04d}' / 'checkpoint.json') for k in (1, 2, 3)]
    (SIDE_STOP / 'collection.json').read_bytes()  # never written: the run dir is read-only input


# ---- F5 evaluation ---------------------------------------------------------------------------------------------
def test_f5_per_axis_evaluation_and_registry_only_truss_timing(side_stop_forecast, tmp_path):
    m = read_json(side_stop_forecast / 'manifest.json')
    fid_s1 = 'F:' + m['forecast_run_id'] + ':fixture_a#2/S1/Axis'
    t1 = fe.boundary_time(m, 1)
    fe.link_observation(side_stop_forecast, [dict(forecast_id=fid_s1, observed_vertex_id='obs:fixture_a#2/S1', observed_at=t1.isoformat(), axis='S1')], 'test')
    assert rows(side_stop_forecast / 'forecast_map.csv')[0]['axis'] == 'S1'
    def obs(q, unit, value, truss_source='', phase='0'):
        return dict(observed_vertex_id='obs:fixture_a#2/S1', plant_id='fixture_a#2', capture_id='c', observed_at=t1.isoformat(), time_since_lights_on_min=phase,
                    photoperiod_phase='lights_on', quantity=q, unit=unit, value=value, reference_status='synthetic_truth', role='target', axis='S1', truss_source=truss_source)
    scenario = read_json(side_stop_forecast / 'scenario.json')
    table = [obs('axis_leaf_count', 'count', 3), obs('event_time:new_truss_generated', 'day', 1, 'registry'), obs('event_time:new_truss_generated', 'day', 1, 'generated'),
             obs('event_time:apex_stop', 'day', 2)]
    write_csv(tmp_path / 'o.csv', table, list(fe.OBSERVATION_COLUMNS))
    if scenario.get('lights_on_clock_time') is None:
        summary = fe.evaluate(side_stop_forecast, tmp_path / 'o.csv', ROOT / 'build' / ('microtom_axes_eval_' + uuid.uuid4().hex))
        assert summary['n_scored'] == 0 and any('diurnal' in r for r in summary['unavailable_reasons'])
        return
    summary = fe.evaluate(side_stop_forecast, tmp_path / 'o.csv', ROOT / 'build' / ('microtom_axes_eval_' + uuid.uuid4().hex))
    assert summary['substem_leaf_count_error'] == dict(n=1, mean=1.0)
    assert summary['truss_timing_error_days']['n'] == 1 and any('registry trusses' in r for r in summary['unavailable_reasons'])


def test_f5_phase_declared_evaluation_scores_per_axis():
    if not _have(P1, SIDE_STOP / 'collection.json'):
        pytest.skip('P1 package or verified side_stop run absent')
    folder = mf.issue(_scn(lights_on_clock_time='06:00'), out_root=_root(), date='20261012', existing_results=[SIDE_STOP])
    m = read_json(folder / 'manifest.json'); t1 = fe.boundary_time(m, 1)
    fid = 'F:' + m['forecast_run_id'] + ':fixture_a#2/S1/Axis'
    fe.link_observation(folder, [dict(forecast_id=fid, observed_vertex_id='obs:S1', observed_at=t1.isoformat(), axis='S1')], 'test')
    def obs(q, unit, value, truss_source=''):
        return dict(observed_vertex_id='obs:S1', plant_id='fixture_a#2', capture_id='c', observed_at=t1.isoformat(), time_since_lights_on_min='0',
                    photoperiod_phase='lights_on', quantity=q, unit=unit, value=value, reference_status='synthetic_truth', role='target', axis='S1', truss_source=truss_source)
    tmp = ROOT / 'build' / ('microtom_axes_obs_' + uuid.uuid4().hex); tmp.mkdir()
    write_csv(tmp / 'o.csv', [obs('axis_leaf_count', 'count', 3), obs('event_time:new_truss_generated', 'day', 1, 'registry'),
                              obs('event_time:new_truss_generated', 'day', 1, 'generated')], list(fe.OBSERVATION_COLUMNS))
    summary = fe.evaluate(folder, tmp / 'o.csv', ROOT / 'build' / ('microtom_axes_eval_' + uuid.uuid4().hex))
    assert summary['substem_leaf_count_error'] == dict(n=1, mean=1.0)
    assert summary['truss_timing_error_days'] == dict(n=1, mean=0.0) and any('registry trusses' in r for r in summary['unavailable_reasons'])
    assert summary['growth_accuracy_status'] == 'software_check_only_synthetic_truth'


# ---- F7 native ---------------------------------------------------------------------------------------------------
def _native_available() -> bool:
    from tools.groimp_light_sanity import CORE
    return CORE.is_file() and shutil.which('java') is not None


def test_f7_native_pipeline_member_on_package_09(monkeypatch):
    if not (_native_available() and P1.exists()):
        pytest.skip('GroIMP/Java or the P1 package is absent')
    import tools.tomato_fsp_pipeline as pipe
    monkeypatch.setattr(pipe, 'advance_interval', lambda *a, **k: (_ for _ in ()).throw(AssertionError('advance_interval must never be called')))
    s = mf.default_scenario('p1_pipeline', horizons_days=[1], members=1, seed=5, rays=100000, diagnostic=True, p1_package='build/p1_state_20261012_09')
    folder = mf.issue(s, out_root=_root(), date='20261012')
    m = fio.verify_forecast(folder)
    assert m['axis_mode'] == 'fsp-axes-1' and {a['axis_id'] for a in m['axes']} == {'M', 'S1', 'S2'}
    by = {a['axis_id']: a for a in m['axes']}
    assert by['S1']['axil_parent_rank'] == 2 and by['S2']['axil_parent_rank'] == 5 and by['M']['producer_segment_index'] == 2 and by['S2']['producer_segment_index'] == 1
    assert by['M']['registry_truss_history'] == [dict(node_id='fx_ss0/F0001', segment_index=1)]
    mtg = fio.read_table(folder / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    reg = {r['source_organ_id']: r['truss_provenance'] for r in mtg if r['class'] == 'TrussAxis'}
    assert reg['fx_ss0|fx_ss0/F0001'] == 'registry_truss' and reg['fx_ss0|fx_ss0/F0002'] == 'registry_truss'
    assert {r['axis_id'] for r in mtg} == {'M', 'S1', 'S2'} and m['truss_geometry_status'] == ax.ZERO_EXTENT_LABEL
    assert m['axis_sums_check'][0]['status'] == 'axis_sums_match_plant_ledger' and m['checkpoints'][0]['hashes']


# ---- F8 scenario set (added 2026-10-12) -------------------------------------------------------------------------
def test_f8_registry_declares_scenario_set_not_distribution():
    registry = mp.load_registry()
    sset = mp.scenario_set(registry)
    assert sset['parameter'] == 'SUBSTEM_SINK_SCALE' and sset['values'] == {'low': 0.5, 'base': 1.0, 'high': 2.0} and sset['reference'] == 'base'
    assert sset['source_kind'] == 'user_assumed' and 'user decision 2026-10-12' in sset['source_ref'] and 'not a probability' in sset['rule']
    by = {r['key']: r for r in registry}
    assert by['APPLY_DETERMINATE_STOP']['uncertainty_kind'] == 'unavailable' and by['APPLY_DETERMINATE_STOP']['value'] is True  # no scenario set, stays true
    assert 'SUBSTEM_SINK_SCALE' not in {r['key'] for r in mp.sampled_rows(registry)}  # never drawn as a member sample
    o = mp.build_request_overrides(registry, None, {'SUBSTEM_SINK_SCALE': 2.0})
    assert o['axis_parameters']['SUBSTEM_SINK_SCALE']['value'] == 2.0 and o['axis_parameters']['APPLY_DETERMINATE_STOP']['value'] is True
    with pytest.raises(ContractError, match='scenario set'):
        mp.build_request_overrides(registry, None, {'SUBSTEM_SINK_SCALE': 1.5})
    env = [dict(light_hours=14, temp_day_c=26, temp_night_c=22) for _ in range(3)]
    from tools.vtc_development import parameters
    base = {k: v['value'] for k, v in parameters().items()}
    rep = mp.eligibility(registry, {'p/S1': dict(thermal_dd=300.0, produced=2, leaf_order=2, truss_count=0, axis_leaf_count=2, stopped=False, is_substem=True, can_truss=True)}, env, base, 0, 3, 'p1_pipeline')
    assert rep['SUBSTEM_SINK_SCALE']['eligible'] is False and rep['SUBSTEM_SINK_SCALE'].get('scenario_set') is True


def test_f8_from_results_is_single_base_scenario_and_rows_carry_scenario(side_stop_forecast):
    m = read_json(side_stop_forecast / 'manifest.json')
    assert m['scenario_set']['applied'] == ['base'] and m['scenario_set']['status'].startswith('single_scenario_base_only') and m['scenario_set']['pooled'] is False
    for name, cols in (('forecast_mtg.csv', fio.MTG_COLUMNS), ('forecast_intervals.csv', fio.INTERVAL_COLUMNS), ('forecast_events.csv', fio.EVENT_COLUMNS)):
        table = fio.read_table(side_stop_forecast / name, cols)
        assert table and {r['scenario_id'] for r in table} == {'base'} and {r['scenario_value'] for r in table} == {'1.0'}


def test_f8_three_scenarios_side_by_side_never_pooled(monkeypatch):
    if not (_native_available() and P1.exists()):
        pytest.skip('GroIMP/Java or the P1 package is absent')
    import tools.tomato_fsp_pipeline as pipe
    monkeypatch.setattr(pipe, 'advance_interval', lambda *a, **k: (_ for _ in ()).throw(AssertionError('advance_interval must never be called')))
    s = mf.default_scenario('p1_pipeline', horizons_days=[1], members=1, seed=5, rays=100000, diagnostic=True, p1_package='build/p1_state_20261012_09')
    folder = mf.issue(s, out_root=_root(), date='20261012')
    m = fio.verify_forecast(folder)
    ss = m['scenario_set']
    assert ss['applied'] == ['low', 'base', 'high'] and ss['status'] == 'three_forecasts_side_by_side' and ss['pooled'] is False
    assert 'S axis' in ss['what_scenarios_vary'] and 'candidate_set' in ss['what_members_vary']
    members = rows(folder / 'members.csv')
    assert [(r['scenario_id'], r['scenario_value']) for r in members] == [('low', '0.5'), ('base', '1.0'), ('high', '2.0')]
    assert all(r['member_values'] == members[0]['member_values'] for r in members)  # the same member draw inside every scenario
    for label, value in (('low', 0.5), ('base', 1.0), ('high', 2.0)):
        scen = read_json(folder / 'scenarios' / label / 'members' / 'm00' / 'scenario' / 'scenario.json')
        by = {a['axis_id']: a for a in scen['axes']}
        assert by['S1']['parameters']['SUBSTEM_SINK_SCALE']['value'] == value and by['M']['parameters']['SUBSTEM_SINK_SCALE']['value'] == 1.0
        assert all(a['parameters']['APPLY_DETERMINATE_STOP']['value'] is True for a in scen['axes'])
    iv = fio.read_table(folder / 'forecast_intervals.csv', fio.INTERVAL_COLUMNS)
    assert {r['scenario_id'] for r in iv} == {'low', 'base', 'high'}
    assert all(r['n_members'] == '1' for r in iv)  # per-scenario envelopes: members per scenario, never 3 x members
    ids = {r['scenario_id']: {r['forecast_id'] for r in iv if r['scenario_id'] == r['scenario_id']} for r in iv}
    fids = {(r['scenario_id'], r['forecast_id']) for r in iv}
    assert all(f'F:{m["forecast_run_id"]}:{sid}:' in fid for sid, fid in fids)  # scenario in the id namespace, ids disjoint across scenarios
    ev = fio.read_table(folder / 'forecast_events.csv', fio.EVENT_COLUMNS)
    assert {r['scenario_id'] for r in ev} == {'low', 'base', 'high'}
    comp = ss['comparison']
    assert set(comp['per_scenario_per_axis_at_last_horizon']) == {'low', 'base', 'high'} and 'S1:axis_leaf_area_mm2' in comp['low_high_distance']
    d = comp['low_high_distance']['S1:axis_leaf_area_mm2']
    assert d['low'] <= d['base'] <= d['high'] or d['low'] >= d['base'] >= d['high']  # monotone in the multiplier for this one-interval run
    assert m['ensemble_spread']['n_interval_rows'] == len([r for r in iv if r['scenario_id'] == 'base'])  # spread reported for base only
