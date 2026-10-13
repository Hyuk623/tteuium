"""Adopted V2 policies on synthetic evidence; no real coefficient validation."""
from copy import deepcopy
import csv
import json

import pytest
from tools import fsp_carbon_diagnostic as fsp
from tools.fsp_carbon_diagnostic_demo import synthetic_request, seal
from tools.leaf_light import common
from tools.tests.test_fsp_carbon_diagnostic import run, pack_edit, inverse_setup
from tools.tests.test_fsp_growth_science import rgr_request, shift_interval, ledger_for


def dwarf_request():
    request = synthetic_request()
    pack_edit(request, lambda p: p.update(source_family='butturini_dwarf', light_basis='absorbed'))
    pack_edit(request, lambda p: p['parameters']['Tref'].update(value=25, source_family='butturini_dwarf', locator='Synthetic provenance exercise of D17 / eq7 p7'))
    for row in request['light_series']['samples']:
        row['light_basis'] = 'absorbed'
    return request


def net_request():
    request = synthetic_request()
    pack_edit(request, lambda p: p.update(respiration_accounting='net_leaf'))
    pack_edit(request, lambda p: p['respiration_ownership'][0].update(maintenance='leaf_exchange'))
    return request


def code(request, component):
    return [i['code'] for i in run(request)['components'][component]['issues']]


@pytest.mark.parametrize('role', ['alpha', 'Pmax', 'theta'])
def test_coefficient_basis_conflict_is_nonfatal_and_identified(role):
    request = synthetic_request(); reference = run(request)
    pack_edit(request, lambda p: p['parameters'][role].update(measured_light_basis='absorbed'))
    result = run(request)
    assert result['diagnostic']['status'] == 'sufficient'
    assert result['components']['supply']['value_gC'] == reference['components']['supply']['value_gC']
    for row in result['components']['supply']['rows']:
        issue = row['issues'][0]
        assert issue['code'] == 'alpha_calibration_basis_conflict'
        assert issue['parameter_id'] == role and issue['measured_light_basis'] == 'absorbed' and issue['pack_light_basis'] == 'incident'
    assert 'alpha_calibration_basis_conflict' in result['diagnostic']['issue_codes']


@pytest.mark.parametrize('role', ['alpha', 'Pmax', 'theta'])
def test_missing_measured_basis_unavailable(role):
    request = synthetic_request()
    pack_edit(request, lambda p: p['parameters'][role].pop('measured_light_basis'))
    assert 'measured_light_basis_missing' in code(request, 'supply')


def test_dwarf_policy_and_source_specific_tref_no_global_default():
    request = dwarf_request()
    assert run(request)['diagnostic']['status'] == 'sufficient'
    pack_edit(request, lambda p: p['parameters']['Tref'].update(value=20))
    assert 'dwarf_maintenance_tref_conflict' in code(request, 'maintenance')
    pack_edit(request, lambda p: p.update(light_basis='incident'))
    assert 'dwarf_source_requires_absorbed_light' in code(request, 'supply')
    plain = synthetic_request()
    assert plain['parameter_pack']['payload']['parameters']['Tref']['value'] == 20
    assert run(plain)['diagnostic']['status'] == 'sufficient'


def test_source_discriminator_no_name_guess_and_missing_is_unavailable():
    request = synthetic_request()
    pack_edit(request, lambda p: p.update(pack_id='butturini_dwarf_is_only_a_name'))
    assert run(request)['components']['supply']['status'] == 'available'
    pack_edit(request, lambda p: p.pop('source_family'))
    assert 'source_family_undeclared' in code(request, 'supply')


def test_parameter_source_dwarf_triggers_policy():
    request = synthetic_request()
    pack_edit(request, lambda p: p['parameters']['theta'].update(source_family='butturini_dwarf'))
    assert 'dwarf_source_requires_absorbed_light' in code(request, 'supply')


def test_saturation_role_alias_does_not_add_coefficient():
    request = synthetic_request(); expected = run(request)['components']['supply']['value_gC']
    pack_edit(request, lambda p: p['photosynthesis'].update(P_sat=p['photosynthesis'].pop('Pmax')))
    assert run(request)['components']['supply']['value_gC'] == expected
    pack_edit(request, lambda p: p['photosynthesis'].update(Pmax='different'))
    with pytest.raises(common.StudyError, match='same saturation'):
        run(request)


@pytest.mark.parametrize('mutation', ['missing_day', 'missing_night', 'dwarf_Rd', 'missing_source', 'missing_evidence', 'dwarf_pack'])
def test_net_leaf_requires_rd_bearing_non_dwarf_source(mutation):
    request = net_request()
    if mutation == 'missing_day': pack_edit(request, lambda p: p['photosynthesis'].pop('Rd_day'))
    if mutation == 'missing_night': pack_edit(request, lambda p: p['photosynthesis'].pop('Rd_night'))
    if mutation == 'dwarf_Rd': pack_edit(request, lambda p: p['parameters']['Rd_day'].update(source_family='butturini_dwarf'))
    if mutation == 'missing_source': pack_edit(request, lambda p: p['parameters']['Rd_night'].pop('source_id'))
    if mutation == 'missing_evidence': pack_edit(request, lambda p: p['parameters']['Rd_day'].update(evidence_kind='unidentified'))
    if mutation == 'dwarf_pack':
        pack_edit(request, lambda p: p.update(source_family='butturini_dwarf', light_basis='absorbed'))
        for row in request['light_series']['samples']: row['light_basis'] = 'absorbed'
    assert 'net_leaf_requires_rd_bearing_source' in code(request, 'supply')


def test_evidenced_net_night_signed_and_charged_once():
    request = net_request()
    request['environment']['records'][0]['phase'] = 'night'
    for row in request['light_series']['samples']: row['ppfd_umol_m2_s'] = 0
    result = run(request)
    assert result['components']['supply']['value_gC'] == pytest.approx(-.02*86400*12.011e-6)
    assert result['components']['maintenance']['rows'][0]['component'] == 'maintenance_excluded'
    assert result['diagnostic']['respiration_accounting'] == 'net_leaf'


@pytest.mark.parametrize('face,reason', [(None,'illuminated_faces_undeclared'),('both','two_sided_exchange_unavailable'),('abaxial_only','abaxial_exchange_unavailable')])
def test_patch_face_gate(face, reason):
    request = synthetic_request()
    request['light_series']['patches'][0]['illuminated_faces'] = face
    assert reason in code(request, 'supply')


def test_face_mapping_requires_evidence():
    request = synthetic_request()
    request['light_series']['patches'][0].pop('face_source_ref')
    assert 'illuminated_faces_evidence_missing' in code(request, 'supply')


def test_fixture_faces_checked_before_combined_exchange():
    request = synthetic_request(); expected = run(request)['components']['supply']['value_gC']
    request['light_series']['fixture_ids'].append('fixture2')
    for row in request['light_series']['samples']: row['ppfd_umol_m2_s'] /= 2
    request['light_series']['samples'] += [dict(row, fixture_id='fixture2') for row in deepcopy(request['light_series']['samples'])]
    assert run(request)['components']['supply']['value_gC'] == expected
    request['light_series']['samples'][-1]['illuminated_faces'] = 'abaxial_only'
    assert 'two_sided_exchange_unavailable' in code(request, 'supply')
    request['light_series']['samples'][-1].pop('illuminated_faces')
    assert 'illuminated_faces_undeclared' in code(request, 'supply')


@pytest.mark.parametrize('field,value', [('source_ref','different'),('structural_dm_now_g',3),('rgr5_scope','organ'),('mass_basis','total_dm')])
def test_retained_organ_rgr5_payload_cannot_conflict(field, value):
    request = rgr_request(); state = request['carbon_state']
    copy = deepcopy(state['plant_rgr5_history'][0]); copy[field] = value
    state['organ_masses'][1]['rgr5'] = copy
    assert 'rgr5_scope_inconsistent' in code(request, 'maintenance')


def test_matching_legacy_rgr5_order_and_source_deviation():
    request = rgr_request(); state = request['carbon_state']
    state['organ_masses'][0]['rgr5'] = dict(reversed(list(state['plant_rgr5_history'][0].items())))
    pack_edit(request, lambda p: p['parameters']['f_days'].update(source_family='butturini_dwarf'))
    result = run(request)
    assert result['components']['maintenance']['status'] == 'available'
    assert result['diagnostic']['rgr5_scope'] == 'plant'
    assert 'source_total_dm_with_roots_and_buffer' in result['diagnostic']['rgr5_mass_basis_deviation_from_source']


def test_sla_existing_unit_check_named_no_conversion():
    request = synthetic_request(); inverse_setup(request)
    pack_edit(request, lambda p: p['parameters']['sla0'].update(unit='m2/mg'))
    assert 'sla_unit_incompatible' in code(request, 'demand')


@pytest.mark.parametrize('missing', ['source_ref','lineage_id'])
def test_reserve_evidence_required(missing):
    request = synthetic_request(); request['carbon_state']['reserve_evidence'].pop(missing)
    row = run(request)['diagnostic']
    assert row['status'] == 'unavailable' and row['reserve_provenance_chain_id'] == 'unavailable'
    assert ('reserve_source_missing' if missing == 'source_ref' else 'reserve_lineage_missing') in row['issue_codes']


def test_reserve_lineage_stable_across_calls_but_evidence_hash_changes(tmp_path, monkeypatch):
    first = synthetic_request(); second = shift_interval(deepcopy(first))
    second['p3_interval']['run_id'] = 'separate_call'
    a,b = run(first),run(second)
    assert a['diagnostic']['reserve_provenance_chain_id'] == b['diagnostic']['reserve_provenance_chain_id']
    assert a['diagnostic']['reserve_evidence_hash'] != b['diagnostic']['reserve_evidence_hash']
    monkeypatch.setattr(common,'BUILD',tmp_path)
    fsp.export_diagnostic(a,tmp_path/'a');fsp.export_diagnostic(b,tmp_path/'b')
    loaded = [json.loads((tmp_path/n/'result.json').read_text()) for n in ('a','b')]
    with pytest.raises(common.StudyError,match='reserve_reuse_assumption'): fsp.validate_diagnostic_table(loaded)
    second['carbon_state']['reserve_reuse_assumption']='Explicit independent stock reinitialization for synthetic cases'
    audit = fsp.validate_diagnostic_table([a,run(second)])
    assert audit['contiguous_comparisons'][0]['same_reserve_lineage']
    changed=deepcopy(first);changed['carbon_state']['reserve_evidence']['source_ref']='different_evidence'
    c=run(changed)['diagnostic']
    assert c['reserve_provenance_chain_id']==a['diagnostic']['reserve_provenance_chain_id']
    assert c['reserve_evidence_hash']!=a['diagnostic']['reserve_evidence_hash']
    changed['carbon_state']['boundary_policy']='different_boundary'
    assert run(changed)['diagnostic']['reserve_provenance_chain_id']!=c['reserve_provenance_chain_id']


def test_total_dm_note_does_not_convert_or_enable_mass_path():
    request = synthetic_request(); base = run(request)['components']['maintenance']['value_gC']
    request['carbon_state']['total_dm_substitute']='Explicit hypothetical sensitivity assumption only'
    result=run(request)
    assert result['components']['maintenance']['value_gC']==base
    assert '90 percent' in result['diagnostic']['total_dm_substitute_caveat']
    request['carbon_state']['organ_masses'][0]['mass_basis']='total_dm'
    assert 'maintenance_mass_basis_unresolved' in code(request,'maintenance')


@pytest.mark.parametrize('variant',['normal','no_pack','constant','missing_face','maintenance_deficit','growth_deficit'])
def test_disclosures_on_all_statuses_roundtrip(variant,tmp_path,monkeypatch):
    request=synthetic_request()
    if variant=='no_pack':request['parameter_pack']=None
    if variant=='missing_face':request['light_series']['patches'][0].pop('illuminated_faces')
    if variant in {'maintenance_deficit','growth_deficit'}:
        for sample in request['light_series']['samples']:sample['ppfd_umol_m2_s']=0
        request['carbon_state']['reserve_gC']=0 if variant=='maintenance_deficit' else .02
    result=run(request);row=result['diagnostic']
    required=['respiration_accounting','light_basis','rgr5_scope','source_buffer_feedback','nonfoliar_assimilation','maintenance_temperature_integration','diagnostic_interpretation','nrh_fit_preprocessing','two_sided_exchange','fvcb']
    assert all(row[key] is not None for key in required)
    assert row['diagnostic_interpretation']=='cross_cultivar_consistency_check'
    if variant=='no_pack':assert row['respiration_accounting']=='undeclared' and row['light_basis']=='undeclared' and row['disclosure_reasons']
    if variant=='constant':assert row['rgr5_scope']=='not_applicable'
    monkeypatch.setattr(common,'BUILD',tmp_path)
    fsp.export_diagnostic(result,tmp_path/variant)
    csv_row=list(csv.DictReader((tmp_path/variant/'diagnostics.csv').open(encoding='utf-8')))[0]
    assert all(csv_row[key]==row[key] for key in required)


def test_nonfatal_basis_issues_csv_json(tmp_path,monkeypatch):
    request=dwarf_request();result=run(request)
    monkeypatch.setattr(common,'BUILD',tmp_path);fsp.export_diagnostic(result,tmp_path/'conflict')
    row=list(csv.DictReader((tmp_path/'conflict/diagnostics.csv').open(encoding='utf-8')))[0]
    assert len(json.loads(row['calibration_basis_issues_json']))==3
    flux=list(csv.DictReader((tmp_path/'conflict/component_fluxes.csv').open(encoding='utf-8')))
    assert all(len(json.loads(r['issues']))==3 for r in flux if r['component']=='supply')


@pytest.mark.parametrize('unit,expected',[(common.DLI_UNIT,'compatible'),('mol/m2/d','incompatible')])
def test_single_canonical_dli_constant_and_legacy_reason(unit,expected):
    request=synthetic_request();p3=request['p3_interval'];config=p3['frozen_config_ref']['payload'];manifest=p3['p3_manifest_ref']['payload']
    config['light_response']=dict(kind='size_target_dli',unit=unit,fixed_over_horizon=True)
    manifest.update(p3_light_coupling='size_target_dli',p3_environment_paths=[dict(path='light_response',metric='dli_mol_m2_day',target='size_target')],config_hash=common.digest(config))
    result=fsp.inspect_p3_coupling(seal(manifest),seal(config),None)
    assert result['d9_compatibility']==expected
    if expected=='incompatible':
        issue=next(i for i in result['issues'] if i['code']=='legacy_dli_unit_spelling')
        assert issue['field']=='light_response.unit' and issue['actual']=='mol/m2/d' and issue['expected']==common.DLI_UNIT
        assert config['light_response']['unit']==unit


def test_p3_declared_lower_knot_is_not_a_false_incompatibility():
    request=synthetic_request();p3=request['p3_interval'];config=p3['frozen_config_ref']['payload']
    config['clock']=dict(kind='piecewise_linear_response', input_metric='temperature_c', input_unit='deg C',
        normalization=dict(t_base_c=5,t_ref_c=20,m_max=2,upper_knot_c=35,lower_knot_c=0),
        knots=[dict(value=x,multiplier=m) for x,m in [(0,0),(5,0),(20,1),(35,2)]])
    manifest=deepcopy(p3['p3_manifest_ref']['payload'])
    manifest.update(config_hash=common.digest(config),p3_environment_paths=[dict(path='clock.input_metric',metric='temperature_c',target='clock')])
    assert fsp.inspect_p3_coupling(seal(manifest),seal(config),None)['d9_compatibility']=='compatible'
