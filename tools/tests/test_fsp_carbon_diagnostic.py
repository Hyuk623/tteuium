"""Independent numerical and rejection checks for isolated P4 diagnostics."""
from copy import deepcopy
from datetime import datetime, timedelta
import csv
import json
import math
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from tools import fsp_carbon_diagnostic as fsp
from tools.fsp_carbon_diagnostic_demo import synthetic_request, seal
from tools.leaf_light import common


@pytest.fixture
def request_data():
    return synthetic_request()


def run(request):
    return fsp.compute_carbon_sufficiency(*(request[key] for key in ('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack')))


def pack_edit(request, edit):
    payload = request['parameter_pack']['payload']; edit(payload)
    request['parameter_pack'] = seal(payload)


def rehash_geometry(request):
    p3 = request['p3_interval']
    for side in ('start', 'end'):
        p3['geometry_hash_' + side] = common.digest(p3['organ_states_' + side])
    request['light_series']['context']['geometry_hash'] = p3['geometry_hash_start']
    for row in request['light_series']['samples']:
        row['geometry_hash'] = p3['geometry_hash_start']


def dark(request):
    for row in request['light_series']['samples']:
        row['ppfd_umol_m2_s'] = 0


def nrh_reference(irradiance):
    # Original quadratic form, distinct from the stable production form.
    alpha, pmax, theta = .05, 20, .7
    z = alpha * irradiance + pmax
    return (z - math.sqrt(z * z - 4 * theta * alpha * irradiance * pmax)) / (2 * theta)


def test_analytical_supply_maintenance_demand_and_immutability(request_data):
    before = deepcopy(request_data)
    result = run(request_data); row = result['diagnostic']; comps = result['components']
    supply = (nrh_reference(100) * .005 + nrh_reference(400) * .015) * 86400 * 12.011e-6
    maintenance = (12.011 / 30.026) * .01 * 2
    demand = (12.011 / 30.026) * 1.5 * .2
    assert comps['supply']['value_gC'] == pytest.approx(supply)
    assert comps['maintenance']['value_gC'] == pytest.approx(maintenance)
    assert comps['demand']['value_gC'] == pytest.approx(demand)
    assert row['sufficiency_ratio'] == pytest.approx((.2 + supply - maintenance - .05) / demand)
    assert request_data == before
    assert result['input_hash_before'] == result['input_hash_after']
    assert row['trajectory_weight'] == 1 and row['accepted_for_domain'] is False
    assert row['feedback_action'] == 'none' and 'next_state' not in result


def test_nonlinear_samples_before_mean(request_data):
    value = run(request_data)['components']['supply']['value_gC']
    mean = (100 * .005 + 400 * .015) / .02
    wrong = nrh_reference(mean) * .02 * 86400 * 12.011e-6
    assert value < wrong


def test_fixture_sum_before_nonlinearity(request_data):
    expected = run(request_data)['components']['supply']['value_gC']
    request_data['light_series']['fixture_ids'] = ['fixture1', 'fixture2']
    samples = request_data['light_series']['samples']
    for row in samples:
        row['ppfd_umol_m2_s'] /= 2
    samples.extend([dict(row, fixture_id='fixture2') for row in deepcopy(samples)])
    assert run(request_data)['components']['supply']['value_gC'] == pytest.approx(expected)


@pytest.mark.parametrize('field,value', [('replicate', 'other'), ('backend', 'other'), ('plant_instance_id', 'other'), ('geometry_hash', '0' * 64), ('area_basis_id', 'image_pixels')])
def test_reject_mixed_light_context(request_data, field, value):
    request_data['light_series']['samples'][0][field] = value
    with pytest.raises(common.StudyError):
        run(request_data)


@pytest.mark.parametrize('change', ['duplicate', 'missing_fixture', 'area', 'two_sided', 'basis'])
def test_light_inventory_and_basis(request_data, change):
    light = request_data['light_series']
    if change == 'duplicate':
        light['samples'].append(deepcopy(light['samples'][0]))
    elif change == 'missing_fixture':
        light['fixture_ids'].append('missing')
        assert run(request_data)['components']['supply']['status'] == 'unavailable'
        return
    elif change == 'area':
        light['samples'][0]['area_weight_m2'] *= 2
    elif change == 'two_sided':
        light['samples'][0]['one_sided_area_basis'] = False
    else:
        light['samples'][0]['light_basis'] = 'absorbed'
    with pytest.raises(common.StudyError):
        run(request_data)


def test_absorbed_light_not_absorbed_twice(request_data):
    expected = run(request_data)['components']['supply']['value_gC']
    pack_edit(request_data, lambda p: p.update(light_basis='absorbed'))
    for row in request_data['light_series']['samples']:
        row.update(light_basis='absorbed', absorptance=.1)
    assert run(request_data)['components']['supply']['value_gC'] == pytest.approx(expected)


@pytest.mark.parametrize('mutation,component', [('unknown_light', 'supply'), ('domain_missing', 'supply'), ('domain_outside', 'supply'), ('future_envelope', 'supply'), ('missing_root', 'demand'), ('missing_reserve', 'budget'), ('missing_activity', 'maintenance'), ('unknown_mass', 'maintenance')])
def test_component_missingness(request_data, mutation, component):
    if mutation == 'unknown_light': request_data['light_series']['samples'][0]['ppfd_umol_m2_s'] = None
    if mutation == 'domain_missing': request_data['environment']['records'][0]['co2_ppm'] = None
    if mutation == 'domain_outside': request_data['environment']['records'][0]['co2_ppm'] = 400
    if mutation == 'future_envelope': request_data['light_series']['patches'][0]['optical_eligible'] = False
    if mutation == 'missing_root': request_data['carbon_state']['included_organ_ids'] = ['leaf']
    if mutation == 'missing_reserve': request_data['carbon_state']['reserve_gC'] = None
    if mutation == 'missing_activity': pack_edit(request_data, lambda p: p['parameters']['activity'].update(value=None))
    if mutation == 'unknown_mass': request_data['carbon_state']['organ_masses'][0]['structural_dm_g'] = None
    result = run(request_data)
    assert result['diagnostic']['status'] == 'unavailable'
    assert result['diagnostic']['sufficiency_ratio'] is None
    assert result['components'][component]['status'] == 'unavailable'
    assert result['diagnostic']['limiting_inputs']


def test_zero_light_zero_growth_and_maintenance_deficit(request_data):
    dark(request_data)
    for row in request_data['carbon_state']['mass_increments']:
        row['structural_dm_end_g'] = row['structural_dm_start_g']
    row = run(request_data)['diagnostic']
    assert row['status'] == 'no_growth_demand' and row['sufficiency_ratio'] is None
    assert row['growth_deficit_gC'] == 0
    request_data['carbon_state']['reserve_gC'] = 0
    row = run(request_data)['diagnostic']
    assert row['status'] == 'maintenance_deficit' and row['sufficiency_ratio'] is None
    assert row['available_growth_carbon_gC'] is None
    assert row['growth_deficit_gC'] is None
    assert row['maintenance_deficit_gC'] == pytest.approx((12.011 / 30.026) * .02)


def test_growth_deficit_and_minimum_reserve(request_data):
    dark(request_data); request_data['carbon_state']['reserve_gC'] = .02
    row = run(request_data)['diagnostic']
    assert row['status'] == 'growth_deficit' and row['sufficiency_ratio'] == 0
    assert row['available_growth_carbon_gC'] == 0 and row['maintenance_deficit_gC'] == 0
    assert row['growth_deficit_gC'] == row['required_growth_carbon_gC']


def test_tolerance_preserves_raw_deficit(request_data):
    base = run(request_data); comps = base['components']
    needed = comps['demand']['value_gC'] + .05 - comps['supply']['value_gC'] + comps['maintenance']['value_gC']
    # Add an external export so the required reserve remains positive.
    request_data['carbon_state']['external_export_gC'] = 1
    request_data['carbon_state']['reserve_gC'] = needed + 1 - 5e-7
    pack_edit(request_data, lambda p: p['numerics'].update(carbon_abs_tol_gC=1e-6))
    row = run(request_data)['diagnostic']
    assert row['status'] == 'sufficient' and row['numerical_tolerance_applied']
    assert row['sufficiency_ratio'] < 1 and row['growth_deficit_gC'] > 0


def test_net_night_exchange_excludes_leaf_maintenance(request_data):
    dark(request_data); request_data['environment']['records'][0]['phase'] = 'night'
    def edit(pack):
        pack['respiration_accounting'] = 'net_leaf'
        pack['respiration_ownership'][0]['maintenance'] = 'leaf_exchange'
    pack_edit(request_data, edit)
    result = run(request_data)
    assert result['components']['supply']['value_gC'] == pytest.approx(-.02 * 86400 * 12.011e-6)
    assert result['components']['maintenance']['value_gC'] == pytest.approx(.01 * 12.011 / 30.026)
    pack_edit(request_data, lambda p: p['respiration_ownership'][0].update(growth='leaf_exchange'))
    assert run(request_data)['components']['supply']['status'] == 'unavailable'


def test_q10_temperature_and_air_substitution(request_data):
    initial = run(request_data)['components']['maintenance']['value_gC']
    request_data['environment']['records'][0]['leaf_temperature_c'] = 30
    assert run(request_data)['components']['maintenance']['value_gC'] == pytest.approx(initial * 2)
    request_data['environment']['records'][0]['leaf_temperature_c'] = None
    assert run(request_data)['components']['maintenance']['status'] == 'unavailable'
    request_data['carbon_state']['air_temperature_substitution_assumption'] = 'Synthetic explicit air substitute'
    assert run(request_data)['components']['maintenance']['value_gC'] == pytest.approx(initial)


def test_rgr5_requires_history_and_rejects_negative_growth(request_data):
    pack_edit(request_data, lambda p: p['organ_parameter_map']['leaf'].update(activity_kind='RGR5', activity_f='f_days', rgr5_scope='plant'))
    assert run(request_data)['components']['maintenance']['status'] == 'unavailable'
    state = request_data['carbon_state']; p3 = request_data['p3_interval']
    history = dict(t_start=p3['t_start'], t_end=p3['t_end'], rgr5_scope='plant',
                   plant_instance_id=p3['plant_instance_id'], mass_basis='structural_dm_excluding_reserve',
                   whole_plant_coverage_complete=True, coverage_statement='Invented full plant mass',
                   history_complete=True, window_days=5, structural_dm_5days_ago_g=1, structural_dm_now_g=2,
                   mass_at_now=p3['t_start'], mass_at_5days_ago='2026-09-29T00:00:00+09:00', source_ref='assumed_history')
    state['plant_rgr5_history'] = [history]
    expected = (.01 + .01 * (1 - math.exp(-33 * math.log(2) / 5))) * 12.011 / 30.026
    assert run(request_data)['components']['maintenance']['value_gC'] == pytest.approx(expected)
    history['structural_dm_5days_ago_g'] = 3
    assert run(request_data)['components']['maintenance']['status'] == 'unavailable'



def inverse_setup(request):
    request['carbon_state']['mass_increments'] = [request['carbon_state']['mass_increments'][1]]
    request['p3_interval']['organ_states_end'][0].update(supported_area_cm2=220, rachis_arc_length_mm=110)
    rehash_geometry(request)
    pack_edit(request, lambda p: p['mass_form_mapping'].update(leaf=dict(source_ref='hypothetical_allometry', inverses=[dict(kind='area', sla_start='sla0', sla_end='sla1')])))


def test_area_inverse_units_and_variable_sla(request_data):
    inverse_setup(request_data)
    result = run(request_data)['components']['demand']
    assert result['rows'][0]['structural_increment_gDM'] == pytest.approx(.1)
    pack_edit(request_data, lambda p: p['parameters']['sla1'].update(value=.01))
    assert run(request_data)['components']['demand']['rows'][0]['structural_increment_gDM'] == pytest.approx(1.2)


def test_dimension_inverse_and_conflicting_inverses(request_data):
    inverse_setup(request_data)
    pack_edit(request_data, lambda p: p['mass_form_mapping']['leaf']['inverses'].append(dict(kind='dimension', field='rachis_arc_length_mm', **{'lambda': 'lambda', 'gamma': 'gamma'})))
    pack_edit(request_data, lambda p: p['mass_form_mapping']['leaf'].update(primary_inverse='area'))
    pack_edit(request_data, lambda p: [inv.update(inverse_id=inv['kind']) for inv in p['mass_form_mapping']['leaf']['inverses']])
    assert run(request_data)['components']['demand']['rows'][0]['structural_increment_gDM'] == pytest.approx(.1)
    request_data['p3_interval']['organ_states_end'][0]['supported_area_cm2'] = 230
    rehash_geometry(request_data)
    result = run(request_data)['components']['demand']
    assert result['status'] == 'unavailable' and result['issues'][0]['code'] == 'inconsistent_mass_form'


def test_negative_growth_no_carbon_credit(request_data):
    request_data['carbon_state']['mass_increments'][0]['structural_dm_end_g'] = .9
    assert run(request_data)['components']['demand']['status'] == 'unavailable'


@pytest.mark.parametrize('field,value', [('ASR', .5), ('carbon', 1.1), ('theta', 1.2), ('Q10', 0)])
def test_invalid_parameters(request_data, field, value):
    pack_edit(request_data, lambda p: p['parameters'][field].update(value=value))
    with pytest.raises(common.StudyError): run(request_data)


@pytest.mark.parametrize('unit', ['gCO2/g_structural_DM/day', 'gCH2O/g_fresh_mass/day'])
def test_maintenance_source_unit_conflicts_not_guessed(request_data, unit):
    pack_edit(request_data, lambda p: p['parameters']['maintenance'].update(unit=unit))
    with pytest.raises(common.StudyError): run(request_data)


def test_new_organ_cost_and_birth_transfer(request_data):
    request_data['p3_interval']['organ_states_start'] = []
    rehash_geometry(request_data)
    assert run(request_data)['components']['demand']['status'] == 'unavailable'
    mass = request_data['carbon_state']['organ_masses'][0]
    mass.update(birth_mass_accounted=True, structural_dm_g=0)
    request_data['carbon_state']['mass_increments'][0].update(structural_dm_start_g=0, structural_dm_end_g=.1)
    result = run(request_data)['components']['demand']
    assert result['status'] == 'available' and result['rows'][0]['structural_increment_gDM'] == .1
    mass['structural_dm_g'] = .05
    request_data['carbon_state']['mass_increments'][0]['structural_dm_start_g'] = .05
    assert run(request_data)['components']['demand']['issues'][0]['code'] == 'birth_transfer_unresolved'


@pytest.mark.parametrize('case', ['terminal', 'retention', 'truss', 'incomplete_tissue', 'nonfoliar'])
def test_scope_prevents_wholeplant_overclaim(request_data, case):
    if case == 'terminal': request_data['p3_interval']['post_termination_scope'] = 'unavailable'
    if case == 'retention':
        request_data['p3_interval']['organ_states_end'][0]['retention_assumption_exceeded'] = True
        rehash_geometry(request_data)
    if case == 'truss': request_data['p3_interval']['events'] = [dict(event_id='truss1', event_kind='truss', geometry=None)]
    if case == 'incomplete_tissue': request_data['carbon_state']['organ_masses'][0]['supported_area_m2'] = .03
    if case == 'nonfoliar': del request_data['carbon_state']['nonfoliar_assimilation_assumption']
    result = run(request_data)
    assert result['diagnostic']['status'] == 'unavailable'
    assert result['components']['supply']['status'] == 'available'


def test_partial_scope_budget_requires_boundary(request_data):
    state = request_data['carbon_state']; state.update(scope='supported_leaf_subset', included_organ_ids=['leaf'], excluded_organ_ids=['root'], boundary_policy=None)
    pack_edit(request_data, lambda p: p.update(scope='supported_leaf_subset'))
    result = run(request_data)
    assert result['components']['supply']['status'] == 'available'
    assert result['diagnostic']['sufficiency_ratio'] is None
    state['boundary_policy'] = 'Explicit synthetic subset reserve allocation and zero transfers'
    assert run(request_data)['diagnostic']['diagnostic_scope'] == 'supported_leaf_subset'
    assert run(request_data)['diagnostic']['status'] == 'sufficient'


def test_missing_coupling_does_not_erase_supported_arithmetic(request_data):
    request_data['p3_interval']['p3_manifest_ref'] = None
    result = run(request_data)
    assert result['diagnostic']['status'] == 'sufficient'
    assert result['diagnostic']['coupling_audit_status'] == 'unavailable'
    assert result['diagnostic']['d9_compatibility'] == 'unavailable'


def set_config(request, config, paths, light='none'):
    p3 = request['p3_interval']; p3['frozen_config_ref'] = seal(config)
    manifest = deepcopy(p3['p3_manifest_ref']['payload'])
    manifest.update(config_hash=common.digest(config), p3_environment_paths=paths, p3_light_coupling=light)
    p3['p3_manifest_ref'] = seal(manifest)


def test_dli_keeps_supply_without_feedback(request_data):
    expected = run(request_data)['components']['supply']['value_gC']
    config = request_data['p3_interval']['frozen_config_ref']['payload']
    config['light_response'] = dict(kind='size_target_dli', unit=common.DLI_UNIT, fixed_over_horizon=True)
    set_config(request_data, config, [dict(path='light_response', metric='dli_mol_m2_day', target='size_target')], 'size_target_dli')
    result = run(request_data)
    assert result['components']['supply']['value_gC'] == expected
    assert result['diagnostic']['feedback_action'] == 'none'


def test_hidden_calibrated_effect_and_manifest_omission(request_data):
    config = request_data['p3_interval']['frozen_config_ref']['payload']
    config['calibration'] = dict(applied_features=[dict(column='co2_ppm', role='size_target')])
    paths = [dict(path='calibration.applied_features[0]', metric='co2_ppm', target='size_target')]
    set_config(request_data, config, paths)
    p3 = request_data['p3_interval']
    p3['calibration_provenance'] = seal(dict(parameter_set_id='fixture', fit_plan_hash='0' * 64, applied_features=config['calibration']['applied_features']))
    assert run(request_data)['diagnostic']['d9_compatibility'] == 'incompatible'
    set_config(request_data, config, [])
    with pytest.raises(common.StudyError): run(request_data)


@pytest.mark.parametrize('case', ['pack_hash', 'geometry_hash', 'nan', 'negative_weight', 'naive_time', 'reverse_time', 'stock_time', 'duplicate_organs'])
def test_malformed_inputs_fail_closed(request_data, case):
    if case == 'pack_hash': request_data['parameter_pack']['payload']['parameters']['alpha']['value'] = .1
    if case == 'geometry_hash': request_data['p3_interval']['geometry_hash_start'] = '0' * 64
    if case == 'nan': request_data['environment']['records'][0]['co2_ppm'] = float('nan')
    if case == 'negative_weight': request_data['p3_interval']['trajectory_weight'] = -1
    if case == 'naive_time': request_data['p3_interval']['t_start'] = '2026-10-04T00:00:00'
    if case == 'reverse_time': request_data['p3_interval']['t_end'] = request_data['p3_interval']['t_start']
    if case == 'stock_time': request_data['carbon_state']['stock_at'] = request_data['p3_interval']['t_end']
    if case == 'duplicate_organs': request_data['carbon_state']['organ_masses'].append(deepcopy(request_data['carbon_state']['organ_masses'][0]))
    with pytest.raises(common.StudyError): run(request_data)


def test_funded_ledger_and_wrong_sign_detection(request_data):
    result = run(request_data); comps = result['components']; d = comps['demand']
    ledger = dict(reserve_start_gC=.2, reserve_end_gC=.2 + comps['supply']['value_gC'] - comps['maintenance']['value_gC'] - d['value_gC'],
                  supply_gC=comps['supply']['value_gC'], maintenance_gC=comps['maintenance']['value_gC'],
                  growth_respiration_gC=sum(r['growth_respiration_required_gC'] for r in d['rows']),
                  structural_increment_gC=sum(r['structural_increment_gC'] for r in d['rows']),
                  external_import_gC=0, external_export_gC=0, funded=True, hypothetical=True, abs_tol_gC=1e-12, rel_tol=1e-12)
    ledger['pack_id'] = result['diagnostic']['pack_id']
    assert fsp.audit_carbon_balance(ledger, result)['status'] == 'balanced'
    ledger['reserve_end_gC'] += .1
    assert fsp.audit_carbon_balance(ledger, result)['status'] == 'imbalance'
    ledger['funded'] = False
    assert fsp.audit_carbon_balance(ledger, result)['status'] == 'unavailable'


def subdivide(records, count, varying_temperature=False):
    out = []
    for row in records:
        a, b = datetime.fromisoformat(row['t_start']), datetime.fromisoformat(row['t_end'])
        for i in range(count):
            copy = dict(row, t_start=(a + (b-a)*i/count).isoformat(), t_end=(a + (b-a)*(i+1)/count).isoformat())
            if varying_temperature: copy['leaf_temperature_c'] = 20 + 10 * (i + .5) / count
            out.append(copy)
    return out


def test_partition_invariance_and_temperature_refinement(request_data):
    reference = run(request_data)
    request_data['light_series']['samples'] = subdivide(request_data['light_series']['samples'], 7)
    request_data['environment']['records'] = subdivide(request_data['environment']['records'], 3)
    split = run(request_data)
    for key in ['supply', 'maintenance', 'demand']:
        assert split['components'][key]['value_gC'] == pytest.approx(reference['components'][key]['value_gC'])
    errors = []
    exact = .02 * (12.011/30.026) / math.log(2)  # integral of 2**t over t in [0,1]
    for count in [1, 2, 4]:
        req = synthetic_request()
        req['environment']['records'] = subdivide(req['environment']['records'], count, True)
        errors.append(abs(run(req)['components']['maintenance']['value_gC'] - exact))
    assert errors[2] < errors[1] < errors[0]
    assert errors[0]/errors[1] > 3.8 and errors[1]/errors[2] > 3.8


def test_blank_audit_and_no_pack(request_data):
    audit = fsp.audit_diagnostic_inputs({}, None)
    assert audit['status'] == 'unavailable' and audit['issues']
    request_data['parameter_pack'] = None
    result = run(request_data)
    assert result['diagnostic']['status'] == 'unavailable'


def test_result_schema_exports_and_fresh_output(request_data, tmp_path, monkeypatch):
    result = run(request_data)
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    out = tmp_path / 'run'
    manifest = fsp.export_diagnostic(result, out)
    for filename, expected in manifest['artifact_hashes'].items():
        assert common.file_hash(out / filename) == expected
    assert json.loads((out/'inputs.json').read_text(encoding='utf-8')) == result['inputs']
    assert 'metadata_ref' in (out/'diagnostics.csv').read_text(encoding='utf-8')
    with pytest.raises(common.StudyError): fsp.export_diagnostic(result, out)
    schema = json.loads(Path(fsp.__file__).with_name('fsp_carbon_diagnostic_schema.json').read_text())['$defs']['result']
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for variant in [synthetic_request(), deepcopy(request_data)]:
        variant['parameter_pack'] = None
        validator.validate(run(variant)['diagnostic'])


@pytest.mark.parametrize('what', ['reserve', 'ratio', 'reason_identity', 'component_sum'])
def test_export_rejects_modified_result(request_data, tmp_path, monkeypatch, what):
    result = run(request_data)
    if what == 'reserve': result['inputs']['carbon_state']['reserve_gC'] = 999
    if what == 'ratio': result['diagnostic']['sufficiency_ratio'] = 999
    if what == 'reason_identity':
        request_data['p3_interval']['p3_manifest_ref'] = None
        result = run(request_data)
        result['diagnostic']['limiting_inputs'][0]['plant_instance_id'] = 'other'
    if what == 'component_sum': result['components']['supply']['rows'][0]['value_gC'] += 1
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    with pytest.raises(common.StudyError): fsp.export_diagnostic(result, tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def test_clock_normalization_and_unknown_binding(request_data):
    config = request_data['p3_interval']['frozen_config_ref']['payload']
    config['clock'] = dict(kind='piecewise_linear_response', input_metric='temperature_c', input_unit='deg C', normalization=dict(t_base_c=10, t_ref_c=20, m_max=2, upper_knot_c=30), knots=[dict(value=10, multiplier=0), dict(value=20, multiplier=1), dict(value=30, multiplier=2)])
    paths = [dict(path='clock.input_metric', metric='temperature_c', target='clock')]
    set_config(request_data, config, paths)
    assert run(request_data)['diagnostic']['d9_compatibility'] == 'compatible'
    config['clock']['knots'][1]['multiplier'] = .8
    set_config(request_data, config, paths)
    assert run(request_data)['diagnostic']['d9_compatibility'] == 'incompatible'
    config['clock']['knots'][1]['multiplier'] = 1
    config['calibration'] = dict(applied_features=[])
    set_config(request_data, config, paths)
    request_data['p3_interval']['calibration_provenance'] = seal(dict(applied_features=[], parameter_set_id='fixture', fit_plan_hash='1'*64))
    assert run(request_data)['diagnostic']['d9_compatibility'] == 'unavailable'


def test_unknown_reproductive_scope_and_organ_temperature(request_data):
    request_data['carbon_state']['reproductive_scope']['status'] = 'unavailable'
    assert run(request_data)['diagnostic']['status'] == 'unavailable'
    request_data['carbon_state']['reproductive_scope']['status'] = 'not_present'
    pack_edit(request_data, lambda p: p['organ_parameter_map']['root'].pop('temperature_metric'))
    assert run(request_data)['components']['maintenance']['status'] == 'unavailable'


def test_indirect_family_environment_cannot_hide_behind_none(request_data):
    config = request_data['p3_interval']['frozen_config_ref']['payload']
    config['parameter_particles'] = [dict(families={'test': dict(features=['co2_ppm'], coefficients=[[1]])})]
    paths = [dict(path='parameter_particles[0].families.test.features[0]', metric='co2_ppm', target='family')]
    set_config(request_data, config, paths)
    row = run(request_data)['diagnostic']
    assert row['d9_compatibility'] == 'incompatible' and row['status'] == 'sufficient'


def test_no_implicit_response_or_review_promotion(request_data):
    pack_edit(request_data, lambda p: p.update(response_multipliers={'vpd': 1}))
    with pytest.raises(common.StudyError): run(request_data)
    pack_edit(request_data, lambda p: (p.pop('response_multipliers'), p.update(review_status='reviewed', review_ref='claimed_review')))
    assert run(request_data)['diagnostic']['status'] == 'unavailable'


def test_unknown_audit_does_not_infer_independence(request_data):
    config = request_data['p3_interval']['frozen_config_ref']['payload']
    config['calibration'] = dict(parameter_set_id='legacy_without_features')
    set_config(request_data, config, [dict(path='calibration', metric='unknown', target='provenance_unavailable')])
    row = run(request_data)['diagnostic']
    assert row['coupling_audit_status'] == 'unavailable' and row['status'] == 'sufficient'


def test_gap_never_becomes_zero_exposure(request_data):
    request_data['light_series']['samples'][0]['t_end'] = '2026-10-04T12:00:00+09:00'
    result = run(request_data)
    assert result['components']['supply']['status'] == 'unavailable'
    assert result['components']['supply']['issues'][0]['code'] == 'time_coverage_missing'


def test_semantic_time_units_and_parent_child_overlap(request_data):
    with pytest.raises(common.StudyError):
        fsp.compute_respiration(request_data['carbon_state'], request_data['environment'], request_data['parameter_pack'], 1)
    request_data['carbon_state']['organ_masses'][0]['child_organ_ids'] = ['root']
    with pytest.raises(common.StudyError): run(request_data)


def test_joint_draw_preserved_without_changing_p3_weights(request_data):
    other = deepcopy(request_data)
    pack_edit(other, lambda p: (p.update(draw_id='joint_draw2'), p['parameters']['Pmax'].update(value=10)))
    a, b = run(request_data), run(other)
    assert a['diagnostic']['p4_parameter_draw_id'] != b['diagnostic']['p4_parameter_draw_id']
    assert a['components']['supply']['value_gC'] > b['components']['supply']['value_gC']
    assert a['diagnostic']['trajectory_id'] == b['diagnostic']['trajectory_id']
    assert a['diagnostic']['trajectory_weight'] == b['diagnostic']['trajectory_weight']


def test_csv_materialization_byte_hashes_and_blank_metadata(request_data, tmp_path):
    expected = run(request_data)['diagnostic']
    for group, field, ref_key in [('light_series', 'samples', 'samples_csv'), ('environment', 'records', 'records_csv')]:
        rows = request_data[group].pop(field)
        path = tmp_path / (field + '.csv')
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        request_data[group][ref_key] = dict(path=path.name, sha256=common.file_hash(path))
    source = tmp_path/'request.json'; source.write_text(json.dumps(request_data), encoding='utf-8')
    loaded, sources = fsp._load_request(source)
    row = run(loaded)['diagnostic']
    assert row['sufficiency_ratio'] == expected['sufficiency_ratio']
    assert len(sources) == 3
    assert loaded['environment']['records'][0]['ph'] is None
    (tmp_path/'samples.csv').write_text('modified', encoding='utf-8')
    with pytest.raises(common.StudyError): fsp._load_request(source)


def test_cli_blank_and_synthetic_commands(request_data, tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    assert fsp.main(['templates','--out',str(tmp_path/'blank')]) == 0
    assert fsp.main(['audit','--input',str(tmp_path/'blank/request.json'),'--out',str(tmp_path/'audit')]) == 0
    assert json.loads((tmp_path/'audit/audit.json').read_text())['status'] == 'unavailable'
    source = tmp_path/'request.json'; source.write_text(json.dumps(request_data), encoding='utf-8')
    assert fsp.main(['diagnose','--input',str(source),'--out',str(tmp_path/'diagnosed')]) == 0
    assert json.loads((tmp_path/'diagnosed/result.json').read_text())['diagnostic']['status'] == 'sufficient'


def test_reproductive_event_needs_accounted_compartments(request_data):
    request_data['carbon_state']['reproductive_scope'] = dict(status='accounted', organ_ids=['fruit'], source_ref='claimed_mass')
    assert run(request_data)['components']['demand']['status'] == 'unavailable'


@pytest.mark.parametrize('unknown', ['light_basis', 'model_id', 'alpha'])
def test_missing_photosynthesis_does_not_block_independent_demand(request_data, unknown):
    if unknown == 'alpha':
        pack_edit(request_data, lambda p: p['parameters']['alpha'].update(value=None))
    else:
        pack_edit(request_data, lambda p: p.update({unknown: None}))
    result = run(request_data)
    assert result['components']['supply']['status'] == 'unavailable'
    assert result['components']['demand']['status'] == 'available'
    assert result['components']['maintenance']['status'] == 'available'
    assert result['diagnostic']['required_growth_carbon_gC'] > 0
    assert result['diagnostic']['sufficiency_ratio'] is None


def test_unknown_feature_alias_cannot_hide_environment(request_data):
    config = request_data['p3_interval']['frozen_config_ref']['payload']
    config['parameter_particles'] = [dict(families={'test': dict(features=['hidden_light_alias'], coefficients=[[1]])})]
    set_config(request_data, config, [])
    with pytest.raises(common.StudyError): run(request_data)


def test_pack_scope_is_not_silently_transferred(request_data):
    pack_edit(request_data, lambda p: p.update(scope='supported_leaf_subset'))
    result=run(request_data)
    assert result['diagnostic']['status']=='unavailable'
    assert result['components']['demand']['issues'][0]['code']=='parameter_scope_mismatch'
    assert result['components']['supply']['status']=='available'
