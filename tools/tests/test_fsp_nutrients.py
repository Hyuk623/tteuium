"""Conservation and evidence tests; all physical/biological inputs are invented."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.leaf_light.common import StudyError, digest, file_hash
from tools.nutrient_contract import SCHEMA, ATOMIC_MASS, zeros
from tools.nutrient_composition import formulate
from tools.nutrient_balance import simulate, PROCESS
from tools.nutrient_fsp_bridge import compute_with_nutrients
from tools.fsp_nutrients import (compare_scenarios, load_scenario, main,
                                 write_input_bundle, save_result)
from tools.fsp_nutrients_demo import (synthetic_recipe, synthetic_scenario,
                                     blank_template, assumption, DEMO_SPECIES)


def idle():
    request = synthetic_scenario()
    request['events'] = []
    request['processes'] = {p: dict(mode='assumed_zero', evidence=assumption('Explicit zero process fixture'))
                            for p in set(PROCESS.values())}
    return request


def one_event(request, kind, **fields):
    request['processes'][PROCESS[kind]]['mode'] = 'prescribed_events'
    request['events'].append(dict(event_id=f'e{len(request["events"])+1}',
        at='2026-10-04T01:00:00+09:00', kind=kind, evidence=assumption(), **fields))
    return request


def independent_totals(state, scope):
    water = sum(x['water_ml'] for x in state['layers'].values()) + state['drainage']['water_ml'] + state['water_lost_ml']
    mass = {}
    for s in scope:
        mass[s] = sum(x['dissolved_mg'][s] + x['retained_mg'][s] for x in state['layers'].values())
        mass[s] += state['drainage']['dissolved_mg'][s] + state['plant']['labile_mg'][s]
        mass[s] += sum(x[s] for x in state['plant']['organs'].values())
    return water, mass


def test_label_conversions_and_total_n_not_double_counted():
    r = formulate(synthetic_recipe())
    assert r['status'] == 'available'
    assert r['element_mass_mg']['NO3_N'] == 8
    assert r['element_mass_mg']['NH4_N'] == 2
    assert r['element_mass_mg']['unspecified_N'] == 0
    assert r['element_mass_mg']['P'] == pytest.approx(4.364268, abs=1e-6)
    assert r['element_mass_mg']['K'] == pytest.approx(16.603026, abs=1e-6)
    assert r['concentration_mmol_element_L']['NO3_N'] == pytest.approx(8/14.007)


def test_same_ratio_different_dose_and_different_ratio():
    a, b, c = [formulate(x) for x in (synthetic_recipe(), synthetic_recipe(dose_g=.2), synthetic_recipe(p_percent=20))]
    assert a['npk_molar_ratio_N1'] == b['npk_molar_ratio_N1']
    assert b['concentration_mg_L']['K'] == 2*a['concentration_mg_L']['K']
    assert c['npk_molar_ratio_N1']['P'] == 2*a['npk_molar_ratio_N1']['P']
    assert c['npk_molar_ratio_N1']['K'] == a['npk_molar_ratio_N1']['K']


def test_total_n_without_forms_is_explicitly_unspecified():
    r = synthetic_recipe()
    r['products'][0]['labels'] = [dict(analyte='total_N', value=10)]
    out = formulate(r)
    assert out['element_mass_mg']['unspecified_N'] == 10
    assert out['element_mass_mg']['NO3_N'] == 0


@pytest.mark.parametrize('basis,dose_unit,dose,density,expected', [
    ('mass_percent', 'g', .1, None, 10),
    ('mass_percent', 'mL', .1, 1.2, 12),
    ('g_per_L_product', 'mL', 1, None, 10),
    ('g_per_L_product', 'g', 1.2, 1.2, 10),
])
def test_liquid_and_solid_basis(basis, dose_unit, dose, density, expected):
    r = synthetic_recipe()
    p = r['products'][0]
    p['label_basis'] = basis
    p['labels'] = [dict(analyte='K', value=10)]
    p.update(density_g_ml=density, density_evidence=assumption())
    r['doses'][0].update(unit=dose_unit, amount=dose)
    assert formulate(r)['element_mass_mg']['K'] == pytest.approx(expected)


def test_missing_density_and_unknown_composition_not_assumed():
    r = synthetic_recipe()
    r['doses'][0]['unit'] = 'mL'
    assert formulate(r)['status'] == 'unavailable'
    r = synthetic_recipe()
    r['products'][0]['unlisted_tracked_species'] = 'unknown'
    r['products'][0]['labels'] = [dict(analyte='P', value=10)]
    assert formulate(r)['reason'] == 'composition_incomplete'


@pytest.mark.parametrize('mutation', ['double_P', 'N_excess', 'duplicate_product', 'duplicate_dose', 'wrong_unit', 'outside_scope'])
def test_bad_composition_rejected(mutation):
    r = synthetic_recipe()
    if mutation == 'double_P': r['products'][0]['labels'].append(dict(analyte='P', value=10))
    if mutation == 'N_excess': r['products'][0]['labels'][1]['value'] = 20
    if mutation == 'duplicate_product': r['products'].append(deepcopy(r['products'][0]))
    if mutation == 'duplicate_dose': r['doses'].append(deepcopy(r['doses'][0]))
    if mutation == 'wrong_unit': r['doses'][0]['unit'] = 'kg'
    if mutation == 'outside_scope': r['tracked_species'].remove('P'); r['source_water_mg_L'].pop('P')
    with pytest.raises(StudyError): formulate(r)


def test_source_water_and_final_volume_are_separate():
    r = synthetic_recipe()
    r.update(source_water_volume_L=.5, final_volume_L=2)
    r['source_water_mg_L']['Ca'] = 10
    out = formulate(r)
    assert out['element_mass_mg']['Ca'] == 8
    assert out['concentration_mg_L']['Ca'] == 4


def test_all_events_conserve_water_and_elements_independently():
    request = synthetic_scenario()
    before = deepcopy(request)
    r = simulate(request)
    assert request == before
    assert r['status'] == 'available'
    assert [v['geometric_volume_ml'] for v in r['geometry']] == [180, 36]
    assert r['geometry'][0]['water_capacity_ml'] != 180
    iw, im = independent_totals(r['initial_state'], request['tracked_species'])
    fw, fm = independent_totals(r['final_state'], request['tracked_species'])
    assert fw == pytest.approx(iw + 20)
    for s in request['tracked_species']:
        added = formulate(request['recipes'][0])['concentration_mg_L'][s] * .02
        assert fm[s] == pytest.approx(im[s] + added, abs=1e-12)
        assert r['final_state']['plant']['labile_mg'][s] == pytest.approx(.05)
        assert r['final_state']['plant']['organs']['leaf'][s] == pytest.approx(.05)
    assert r['final_state']['drainage']['water_ml'] == 3
    assert r['growth_prediction'] is None
    assert not r['growth_feedback_applied']


def test_clean_water_dilutes_without_adding_nutrients():
    request = idle()
    request['recipes'][0]['doses'] = []
    one_event(request, 'irrigate', layer_id='upper', batch_id='batch1', water_ml=20)
    r = simulate(request)
    assert r['totals']['irrigation_nutrient_mg'] == zeros(DEMO_SPECIES)
    assert r['final_state']['layers']['upper']['dissolved_mg'] == request['layers'][0]['dissolved_mg']
    final_upper = [row for row in r['layer_states'] if row['event_id'] == 'e1' and row['layer_id'] == 'upper']
    assert all(row['concentration_mg_L'] == pytest.approx(12.5) for row in final_upper)


@pytest.mark.parametrize('kind', ['evaporate', 'transpire'])
def test_water_loss_concentrates_without_removing_ions(kind):
    request = idle()
    one_event(request, kind, layer_id='upper', water_ml=30)
    r = simulate(request)
    assert r['final_state']['layers']['upper']['water_ml'] == 30
    assert r['final_state']['layers']['upper']['dissolved_mg'] == request['layers'][0]['dissolved_mg']


@pytest.mark.parametrize('mutation', ['uptake_overdraw', 'release_overdraw', 'allocation_overdraw', 'water_overdraw',
    'capacity', 'discard_reuse', 'duplicate_event', 'out_of_order', 'outside_time', 'naive_time', 'unknown_layer',
    'self_transfer', 'zero_conflict', 'batch_overdraw', 'negative_water', 'boolean_number', 'extra_field'])
def test_ledger_rejects_invalid_flows_atomically(mutation):
    request = synthetic_scenario()
    if mutation == 'uptake_overdraw': request['events'][8]['nutrient_mg']['K'] = 100
    if mutation == 'release_overdraw': request['events'][7]['nutrient_mg']['K'] = 100
    if mutation == 'allocation_overdraw': request['events'][9]['nutrient_mg']['K'] = 100
    if mutation == 'water_overdraw': request['events'][4]['water_ml'] = 100
    if mutation == 'capacity': request['events'][0]['water_ml'] = 50
    if mutation == 'discard_reuse': request['drainage_mode'] = 'discard'
    if mutation == 'duplicate_event': request['events'][1]['event_id'] = 'e1'
    if mutation == 'out_of_order': request['events'][1]['at'] = '2026-10-04T00:00:00+09:00'
    if mutation == 'outside_time': request['events'][0]['at'] = '2026-10-03T00:00:00+09:00'
    if mutation == 'naive_time': request['events'][0]['at'] = '2026-10-04T01:00:00'
    if mutation == 'unknown_layer': request['events'][0]['layer_id'] = 'other'
    if mutation == 'self_transfer': request['events'][1]['to_layer_id'] = 'upper'
    if mutation == 'zero_conflict': request['processes']['uptake']['mode'] = 'assumed_zero'
    if mutation == 'batch_overdraw': request['recipes'][0].update(final_volume_L=.01, source_water_volume_L=.01)
    if mutation == 'negative_water': request['events'][0]['water_ml'] = -1
    if mutation == 'boolean_number': request['events'][0]['water_ml'] = True
    if mutation == 'extra_field': request['events'][0]['nutrient_mg'] = zeros(DEMO_SPECIES)
    frozen = deepcopy(request)
    with pytest.raises(StudyError): simulate(request)
    assert request == frozen


@pytest.mark.parametrize('mutation,reason', [
    ('initial_ions', 'input_missing'), ('capacity', 'input_missing'),
    ('uptake', 'process_coverage_missing'), ('exchange', 'process_not_specified'),
    ('missing_events', 'prescribed_process_events_missing'), ('dry', 'dry_pool_chemistry_unspecified'),
    ('evidence', 'evidence_missing'), ('mixing', 'mixing_model_undeclared')])
def test_missing_science_stays_unavailable(mutation, reason):
    request = synthetic_scenario()
    if mutation == 'initial_ions': request['layers'][0]['dissolved_mg']['P'] = None
    if mutation == 'capacity': request['layers'][0]['water_capacity_ml'] = None
    if mutation == 'uptake': request['processes'].pop('uptake')
    if mutation == 'exchange': request['processes']['exchange']['mode'] = 'not_modelled'
    if mutation == 'missing_events': request['events'] = []
    if mutation == 'dry':
        request = idle(); one_event(request, 'evaporate', layer_id='upper', water_ml=60)
    if mutation == 'evidence': request['events'][0]['evidence'] = None
    if mutation == 'mixing': request['mixing_model'] = None
    out = simulate(request)
    assert out['status'] == 'unavailable' and out['reason'] == reason
    assert 'final_state' not in out


def test_ec_ph_metadata_cannot_change_ion_state():
    request = synthetic_scenario()
    reference = simulate(request)
    request['observations'] = [dict(observation_id='o1', plant_instance_id='plant1',
        at=request['t_start'], metric='ec_ms_cm', value=100.0, unit='mS/cm', evidence=assumption())]
    result = simulate(request)
    assert result['final_state'] == reference['final_state']
    assert result['observation_comparison']['status'] == 'unavailable'


def test_scenario_comparison_retains_missing_and_does_not_predict_growth():
    a, b = synthetic_scenario(), synthetic_scenario()
    b['scenario_id'] = 'b'; b['recipes'][0]['doses'][0]['amount'] *= 2
    result = compare_scenarios([a, b])
    assert result['status'] == 'available'
    assert result['comparison_rows'][8]['irrigation_mg'] == 2*result['comparison_rows'][0]['irrigation_mg']
    assert all(row['constrained_growth'] is None for row in result['comparison_rows'])
    b['processes'].pop('uptake')
    assert compare_scenarios([a, b])['status'] == 'partial'


def test_disabled_fsp_is_exact_and_enabled_only_binds_accounting():
    from tools.fsp_carbon_diagnostic import compute_carbon_sufficiency
    from tools.fsp_carbon_diagnostic_demo import synthetic_request
    r = synthetic_request(); before = deepcopy(r)
    fields = ('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack')
    baseline = compute_carbon_sufficiency(**{k: r[k] for k in fields})
    assert compute_with_nutrients(r, {'ignored': 'invalid'}, enabled=False) == baseline
    enabled = compute_with_nutrients(r, synthetic_scenario(), enabled=True)
    assert enabled['p4_diagnostic'] == baseline
    assert enabled['binding']['status'] == 'available'
    assert enabled['growth_constraints']['status'] == 'unavailable'
    assert enabled['carbon_and_nutrient_growth_commit'] is None
    assert r == before


@pytest.mark.parametrize('field,value', [('plant_instance_id', 'other'), ('source_plant_id', 'other'),
    ('scenario_id', 'other'), ('t_end', '2026-10-06T00:00:00+09:00')])
def test_fsp_mismatched_identity_or_time_not_bound(field, value):
    from tools.fsp_carbon_diagnostic_demo import synthetic_request
    case = synthetic_scenario(); case[field] = value
    result = compute_with_nutrients(synthetic_request(), case, enabled=True)
    assert result['binding']['reason'] == 'nutrient_fsp_context_mismatch'
    assert result['nutrient_accounting'] is None


def test_csv_round_trip_and_input_hashes(tmp_path):
    original = synthetic_scenario()
    write_input_bundle(tmp_path, original)
    files = {str(p): file_hash(p) for p in tmp_path.iterdir()}
    loaded, hashes = load_scenario(tmp_path/'scenario.json')
    result = simulate(loaded)
    assert result['final_state'] == simulate(original)['final_state']
    assert hashes == files
    assert loaded['events'][0]['evidence']['record_row'] == 2
    assert files == {str(p): file_hash(p) for p in tmp_path.iterdir()}
    out = tmp_path/'out'; out.mkdir()
    save_result(out, result, hashes)
    assert (out/'event_ledger.csv').is_file() and (out/'layer_states.csv').is_file()


def test_blank_template_has_no_fake_physical_values(tmp_path):
    r = blank_template()
    assert r['geometry']['width_mm'] == 60
    assert r['layers'][0]['water_ml'] is None
    assert all(v is None for v in r['layers'][0]['dissolved_mg'].values())
    assert r['recipes'][0]['products'] == []
    write_input_bundle(tmp_path, r)
    loaded, _ = load_scenario(tmp_path/'scenario.json')
    assert simulate(loaded)['status'] == 'unavailable'


def test_cli_export_and_output_safety(tmp_path, monkeypatch):
    from tools.leaf_light import common
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    source = tmp_path/'source'; source.mkdir(); write_input_bundle(source, synthetic_scenario())
    main(['simulate', '--scenario', str(source/'scenario.json'), '--out', str(tmp_path/'run')])
    assert json.loads((tmp_path/'run'/'result.json').read_text())['status'] == 'available'
    with pytest.raises(SystemExit) as ex:
        main(['simulate', '--scenario', str(source/'scenario.json'), '--out', str(tmp_path/'run')])
    assert ex.value.code == 2
    with pytest.raises(SystemExit) as ex:
        main(['templates', '--out', str(tmp_path.parent/'outside')])
    assert ex.value.code == 2


def test_cli_bad_csv_context_is_refused_without_output(tmp_path, monkeypatch):
    from tools.leaf_light import common
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    src = tmp_path/'input'; src.mkdir(); write_input_bundle(src, synthetic_scenario())
    p = src/'events.csv'; p.write_text(p.read_text().replace('plant1', 'wrong'), encoding='utf-8')
    with pytest.raises(SystemExit) as ex:
        main(['simulate', '--scenario', str(src/'scenario.json'), '--out', str(tmp_path/'bad')])
    assert ex.value.code == 2
    assert not (tmp_path/'bad').exists()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
def test_nonfinite_values_are_malformed_not_missing(value):
    recipe = synthetic_recipe(); recipe['doses'][0]['amount'] = value
    with pytest.raises(StudyError, match='Finite JSON'):
        formulate(recipe)
    request = synthetic_scenario(); request['layers'][0]['water_ml'] = value
    with pytest.raises(StudyError, match='Finite JSON'):
        simulate(request)


def test_initial_dry_dissolved_pool_needs_chemistry_even_without_events():
    r = idle(); r['layers'][0]['water_ml'] = 0
    assert simulate(r)['reason'] == 'dry_pool_chemistry_unspecified'


def test_reuse_is_internal_not_a_second_fertilizer_input():
    r = idle()
    one_event(r, 'drain', layer_id='upper', water_ml=10)
    one_event(r, 'reuse', layer_id='upper', water_ml=10)
    result = simulate(r)
    assert result['initial_state'] == result['final_state']
    assert result['totals']['irrigation_nutrient_mg'] == zeros(DEMO_SPECIES)


def test_retained_release_uses_existing_pool_not_new_nutrients():
    r = idle()
    one_event(r, 'release', layer_id='upper', nutrient_mg={s: .1 for s in DEMO_SPECIES})
    result = simulate(r)
    assert result['final_state']['layers']['upper']['dissolved_mg']['K'] == pytest.approx(1.1)
    assert result['final_state']['layers']['upper']['retained_mg']['K'] == pytest.approx(.1)
    assert all(abs(v)<1e-12 for v in result['totals']['nutrient_residual_mg'].values())


def test_scientific_missing_in_one_comparison_is_not_zero():
    a, b = synthetic_scenario(), synthetic_scenario()
    b['scenario_id'] = 'missing'; b['plant_initial']['labile_mg']['P'] = None
    result = compare_scenarios([a, b])
    assert result['status'] == 'partial'
    assert all(row['irrigation_mg'] is None for row in result['comparison_rows'] if row['scenario_id']=='missing')


def test_comparison_rejects_unmatched_time_and_duplicate_scenario():
    a, b = synthetic_scenario(), synthetic_scenario()
    with pytest.raises(StudyError, match='distinct'): compare_scenarios([a,b])
    b['scenario_id']='b'; b['t_end']='2026-10-06T00:00:00+09:00'
    with pytest.raises(StudyError, match='intervals'): compare_scenarios([a,b])


def test_no_N_normalized_ratio_when_N_is_zero():
    r=synthetic_recipe(); r['products'][0]['labels']=[dict(analyte='K',value=10)]
    result=formulate(r)
    assert result['npk_molar_ratio_N1'] is None


def test_zero_species_values_are_not_csv_missing(tmp_path):
    r=idle(); r['layers'][0]['dissolved_mg']=zeros(DEMO_SPECIES)
    write_input_bundle(tmp_path,r)
    loaded,_=load_scenario(tmp_path/'scenario.json')
    result=simulate(loaded)
    out=tmp_path/'output';out.mkdir();save_result(out,result,{})
    assert result['status']=='available'
    import csv
    rows=list(csv.DictReader((out/'layer_states.csv').open(encoding='utf-8')))
    assert rows[0]['dissolved_mg']=='0.0'


def test_enabled_bridge_without_scenario_or_dates_is_truthfully_unavailable():
    from tools.fsp_carbon_diagnostic_demo import synthetic_request
    r=synthetic_request()
    result=compute_with_nutrients(r,enabled=True)
    assert result['binding']['reason']=='nutrient_scenario_missing'
    case=synthetic_scenario();case['t_start']=None
    result=compute_with_nutrients(r,case,enabled=True)
    assert result['binding']['reason']=='nutrient_fsp_context_mismatch'


def test_export_water_rows_are_not_repeated_per_species(tmp_path):
    import csv
    result=simulate(synthetic_scenario()); save_result(tmp_path,result,{})
    water=list(csv.DictReader((tmp_path/'water_ledger.csv').open(encoding='utf-8')))
    nutrient=list(csv.DictReader((tmp_path/'event_ledger.csv').open(encoding='utf-8')))
    assert len(water)==len(result['events'])
    assert len(nutrient)==len(water)*len(DEMO_SPECIES)
    assert 'water_ml' not in nutrient[0]
    assert water[0]['batch_id']=='batch1' and water[0]['layer_id']=='upper'
