"""Safety contracts from the 2026-10-04 P4 Science review; synthetic evidence only."""
from copy import deepcopy
from datetime import datetime, timedelta
import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest
from tools import fsp_carbon_diagnostic as fsp
from tools.fsp_carbon_diagnostic_demo import synthetic_request
from tools.tests.test_fsp_carbon_diagnostic import run, pack_edit, inverse_setup, rehash_geometry
from tools.leaf_light import common


def rgr_request():
    request = synthetic_request()
    pack_edit(request, lambda p: p['organ_parameter_map']['leaf'].update(activity_kind='RGR5', activity_f='f_days', rgr5_scope='plant'))
    p3 = request['p3_interval']
    request['carbon_state']['plant_rgr5_history'] = [dict(
        t_start=p3['t_start'], t_end=p3['t_end'], rgr5_scope='plant', plant_instance_id=p3['plant_instance_id'],
        mass_basis='structural_dm_excluding_reserve', whole_plant_coverage_complete=True,
        coverage_statement='Synthetic complete vegetative plant including root', history_complete=True,
        window_days=5, structural_dm_5days_ago_g=1, structural_dm_now_g=2,
        mass_at_now=p3['t_start'], mass_at_5days_ago='2026-09-29T00:00:00+09:00', source_ref='synthetic_total_mass')]
    return request


@pytest.mark.parametrize('field,value', [('rgr5_scope', None), ('rgr5_scope', 'organ'), ('whole_plant_coverage_complete', False),
    ('mass_basis', 'total_dm'), ('history_complete', False), ('plant_instance_id', 'wrong'), ('window_days', 4),
    ('coverage_statement', None), ('mass_at_5days_ago', '2026-09-30T00:00:00+09:00')])
def test_plant_history_guards(field, value):
    request = rgr_request()
    request['carbon_state']['plant_rgr5_history'][0][field] = value
    assert run(request)['components']['maintenance']['status'] == 'unavailable'


@pytest.mark.parametrize('scope', [None, 'organ'])
def test_rgr5_parameter_scope_guard(scope):
    request = rgr_request()
    pack_edit(request, lambda p: p['organ_parameter_map']['leaf'].update(rgr5_scope=scope))
    assert run(request)['components']['maintenance']['issues'][0]['code'] == 'RGR5_scope_missing'


def test_organ_local_history_does_not_substitute_for_plant():
    request = rgr_request()
    history = request['carbon_state'].pop('plant_rgr5_history')[0]
    request['carbon_state']['organ_masses'][0]['maintenance_history'] = [dict(
        t_start=history['t_start'], t_end=history['t_end'], structural_dm_g=1, rgr5=history)]
    assert run(request)['components']['maintenance']['issues'][0]['code'] == 'RGR5_history_missing'


def test_zero_activity_and_saturation():
    request = rgr_request()
    request['carbon_state']['plant_rgr5_history'][0]['structural_dm_now_g'] = 1
    result = run(request)
    assert result['diagnostic']['maintenance_activity_zero'] is True
    leaf = result['components']['maintenance']['rows'][0]
    assert leaf['activity'] == 0 and leaf['value_gC'] == 0 and leaf['rgr5_scope'] == 'plant'
    request['carbon_state']['plant_rgr5_history'][0]['structural_dm_now_g'] = 1e100
    assert run(request)['components']['maintenance']['issues'][0]['code'] == 'RGR5_activity_out_of_domain'


def multiple_inverses():
    request = synthetic_request(); inverse_setup(request)
    pack_edit(request, lambda p: p['mass_form_mapping']['leaf']['inverses'][0].update(inverse_id='area'))
    pack_edit(request, lambda p: p['mass_form_mapping']['leaf']['inverses'].append(dict(
        inverse_id='length', kind='dimension', field='rachis_arc_length_mm', **{'lambda': 'lambda', 'gamma': 'gamma'})))
    return request


def test_agreeing_inverses_require_primary():
    request = multiple_inverses()
    assert run(request)['components']['demand']['issues'][0]['code'] == 'primary_inverse_missing'


def test_primary_selects_second_inverse_within_tolerance():
    request = multiple_inverses()
    request['p3_interval']['organ_states_end'][0]['rachis_arc_length_mm'] = 110.5
    rehash_geometry(request)
    pack_edit(request, lambda p: p['mass_form_mapping']['leaf'].update(primary_inverse='length'))
    pack_edit(request, lambda p: p['numerics'].update(mass_abs_tol_gDM=.01))
    row = run(request)['components']['demand']['rows'][0]
    assert row['primary_inverse'] == 'length' and row['structural_increment_gDM'] == pytest.approx(.105)
    pack_edit(request, lambda p: p['numerics'].update(mass_abs_tol_gDM=1e-12))
    assert run(request)['components']['demand']['issues'][0]['code'] == 'inconsistent_mass_form'


def shift_interval(request, days=1):
    def shift(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {'t_start', 't_end', 'stock_at'}:
                    value[key] = (datetime.fromisoformat(item) + timedelta(days=days)).isoformat()
                else: shift(item)
        elif isinstance(value, list):
            for item in value: shift(item)
    shift(request)
    return request


def test_table_contiguous_reuse_and_explicit_assumption(tmp_path, monkeypatch):
    first = synthetic_request(); second = shift_interval(deepcopy(first))
    with pytest.raises(common.StudyError, match='reserve_reuse_assumption'):
        fsp.validate_diagnostic_table([run(second), run(first)])
    second['carbon_state']['reserve_reuse_assumption'] = 'Independent reset scenarios with equal measured starting stocks'
    results = [run(first), run(second)]
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    validated = fsp.export_diagnostic_table(results, tmp_path/'table')
    assert validated['contiguous_comparisons'][0]['identical_reserve'] is True
    rows = list(csv.DictReader((tmp_path/'table/diagnostics.csv').open(encoding='utf-8')))
    assert rows[1]['reserve_reuse_assumption'] == second['carbon_state']['reserve_reuse_assumption']
    assert all(row['reserve_propagation'] == 'none' and row['interval_independence'] == 'independent_single_interval' for row in rows)
    assert json.loads((tmp_path/'table/row_0001/result.json').read_text()) == results[1]


@pytest.mark.parametrize('change', ['gap', 'plant', 'trajectory', 'draw', 'boundary', 'reserve'])
def test_table_comparison_scope(change):
    first = synthetic_request(); second = shift_interval(deepcopy(first), 2 if change == 'gap' else 1)
    if change == 'plant':
        def replace(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'plant_instance_id': obj[key] = 'plant2'
                    else: replace(value)
            elif isinstance(obj, list):
                for value in obj: replace(value)
        replace(second)
    if change == 'trajectory': second['p3_interval']['trajectory_id'] = 'trajectory2'
    if change == 'draw': pack_edit(second, lambda p: p.update(draw_id='draw2'))
    if change == 'boundary': second['carbon_state']['boundary_policy'] = 'Different independently declared boundary'
    if change == 'reserve': second['carbon_state']['reserve_gC'] = .3
    result = fsp.validate_diagnostic_table([run(first), run(second)])
    assert len(result['contiguous_comparisons']) == (1 if change == 'reserve' else 0)


def ledger_for(result):
    comps = result['components']; state = result['inputs']['carbon_state']; d = comps['demand']
    return dict(pack_id=result['diagnostic']['pack_id'], reserve_start_gC=state['reserve_gC'],
        reserve_end_gC=comps['budget']['unprotected_budget_gC'] - d['value_gC'],
        supply_gC=comps['supply']['value_gC'], maintenance_gC=comps['maintenance']['value_gC'],
        growth_respiration_gC=sum(r['growth_respiration_required_gC'] for r in d['rows']),
        structural_increment_gC=sum(r['structural_increment_gC'] for r in d['rows']),
        external_import_gC=0, external_export_gC=0, funded=True, hypothetical=True, abs_tol_gC=1e-12, rel_tol=1e-12)


def test_balance_verified_association_and_tampering():
    result = run(synthetic_request()); ledger = ledger_for(result)
    assert fsp.audit_carbon_balance(ledger)['code'] == 'originating_diagnostic_missing'
    assert fsp.audit_carbon_balance(ledger, result)['association_verified'] is True
    for bad in (None, 'wrong'):
        assert fsp.audit_carbon_balance(dict(ledger, pack_id=bad), result)['code'] == 'ledger_pack_mismatch'
    assert fsp.audit_carbon_balance(dict(ledger, structural_increment_gC=.01), result)['code'] == 'ledger_origin_value_mismatch'
    tampered = deepcopy(result)
    tampered['components']['demand']['rows'][0]['structural_increment_gC'] += .01
    with pytest.raises(common.StudyError, match='recomputed'):
        fsp.audit_carbon_balance(ledger, tampered)


def test_missing_reserve_table_remains_unavailable():
    first = synthetic_request(); first['carbon_state']['reserve_gC'] = None
    second = shift_interval(deepcopy(first))
    results = [run(first),run(second)]
    assert fsp.validate_diagnostic_table(results)['contiguous_comparisons'][0]['identical_reserve'] is False
    assert all(r['diagnostic']['status'] == 'unavailable' for r in results)


def test_run_label_does_not_bypass_reserve_guard():
    first = synthetic_request(); second = shift_interval(deepcopy(first))
    second['p3_interval']['run_id'] = 'other_run'
    with pytest.raises(common.StudyError, match='reserve_reuse_assumption'):
        fsp.validate_diagnostic_table([run(first), run(second)])


def test_unreviewed_pack_exports_unavailable(tmp_path, monkeypatch):
    request = synthetic_request()
    pack_edit(request, lambda p: p.update(review_status='unreviewed'))
    result = run(request)
    assert result['diagnostic']['status'] == 'unavailable'
    assert result['diagnostic']['pack_id'] is None
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    fsp.export_diagnostic(result, tmp_path/'unreviewed')
    assert fsp.validate_diagnostic_table([result])['status'] == 'valid'
