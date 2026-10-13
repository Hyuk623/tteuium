"""Actual producer -> current P3 validator only; model fields are frozen in advance."""
from copy import deepcopy

import pytest

from tools import probabilistic_compound_growth as p3
from tools import reference_dli as producer
from tools.leaf_light.common import DLI_UNIT, StudyError, read_json, write_json, file_hash
from tools.reference_dli_demo import create_inputs, write_readings
from tools.reference_dli_p3 import map_single_day


def setup(tmp_path, monkeypatch, rule='single_representative_day', q=None):
    import tools.leaf_light.common as common
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    source=tmp_path/'reference_inputs'; inputs=create_inputs(source)
    ref=dict(inputs['position']['applicability_source_ref'],path=str((source/'synthetic_evidence.json').resolve()))
    # Predeclare model coefficients/domain before producing any reference value.
    light=dict(kind='size_target_dli', unit=DLI_UNIT, center=10., scale=10.,
        source_kind='user_assumed', source_ref='PREDECLARED SYNTHETIC MODEL ONLY',
        applicability_interval=dict(min=0.,max=30.,unit=DLI_UNIT,source_kind='user_assumed',
            source_ref='PREDECLARED SYNTHETIC COEFFICIENT DOMAIN',applicability_source_ref=ref),
        coefficients={'exponential':dict(coefficient_id='synthetic_exponential_fixed',role='remaining_increment',c_DLI=.1,
            source_kind='user_assumed',source_ref='PREDECLARED SYNTHETIC COEFFICIENT',applicability_source_ref=deepcopy(ref))})
    config=dict(environment_profile='d9',clock=dict(kind='calendar'),light_response=deepcopy(light),parameter_particles=[dict(
        existing_blocks={'synthetic_block':'existing'},axes={},families={'existing':dict(growth_curve='exponential',features=[])})])
    write_json(tmp_path/'predeclared_p3_config.json',config)
    p=inputs['position'];p.update(value_rule=rule,applicability_source_ref=ref)
    if rule=='declared_scenario':
        scenario=tmp_path/'scenario.json';write_json(scenario,dict(value=11.52,unit=DLI_UNIT,source_kind='synthetic_only'))
        p.update(scenario_value=11.52,scenario_source_ref=dict(path=str(scenario),sha256=file_hash(scenario)))
    write_json(source/'reference_position.json',p)
    if q is not None:write_readings(source/'reference_readings.csv',[dict(r,ppfd_umol_m2_s=q) for r in inputs['readings']])
    record,audit=producer.prepare_record(source/'reference_position.json',source/'schedule.json',route='spot_schedule',
        readings_path=source/'reference_readings.csv',survey_path=source/'spot_survey.csv')
    producer.save_result(record,audit,tmp_path/'result')
    return tmp_path/'result/reference_dli.json',config


def test_actual_canonical_reference_validates_without_model_or_coefficient_changes(tmp_path,monkeypatch):
    path,config=setup(tmp_path,monkeypatch)
    frozen=deepcopy(config['light_response'])
    def forbidden(*args,**kwargs):raise AssertionError('forecast is outside the bounded validator test')
    monkeypatch.setattr(p3,'sample_forecast',forbidden)
    config['light_response']=map_single_day(path,frozen,evidence_kind='user_assumed')
    p3._validate_d9(config,{})
    actual=config['light_response']
    for field in ('kind','center','scale','coefficients','applicability_interval'):assert actual[field]==frozen[field]
    assert actual['value']==pytest.approx(11.52,abs=1e-12,rel=1e-12)
    assert actual['unit']==DLI_UNIT and actual['producer_source_kind']=='measured_spot_schedule'
    assert actual['local_day']['coverage']=='complete'
    bad=deepcopy(config);bad['light_response']['value']=31.
    with pytest.raises(p3.ScienceUnavailable,match='outside_applicability'):p3._validate_d9(bad,{})
    bad=deepcopy(config);bad['p2_tissue_manifest']={'area_basis_id':actual['basis_id']}
    with pytest.raises(p3.ScienceUnavailable,match='basis_collides_with_tissue_basis'):p3._validate_d9(bad,{})


def test_out_of_domain_producer_cannot_become_p3_input(tmp_path,monkeypatch):
    path,config=setup(tmp_path,monkeypatch,q=1000.)
    assert read_json(path)['status']=='out_of_applicability'
    with pytest.raises(StudyError,match='p3_reference_result_out_of_applicability'):
        map_single_day(path,config['light_response'],evidence_kind='user_assumed')


@pytest.mark.parametrize('rule',['mean_of_complete_days','declared_scenario'])
def test_other_rules_keep_provenance_and_do_not_fake_p3_local_day(tmp_path,monkeypatch,rule):
    path,config=setup(tmp_path,monkeypatch,rule=rule)
    assert read_json(path)['status']=='available'
    with pytest.raises(StudyError,match='p3_single_local_day_contract_cannot_represent_'+rule):
        map_single_day(path,config['light_response'],evidence_kind='user_assumed')


def test_legacy_and_conflicting_frozen_model_domain_are_refused(tmp_path,monkeypatch):
    path,config=setup(tmp_path,monkeypatch)
    config['light_response']['unit']='mol/m2/d'
    with pytest.raises(StudyError,match='legacy_dli_unit_spelling'):
        map_single_day(path,config['light_response'],evidence_kind='user_assumed')
    config['light_response']['unit']=DLI_UNIT
    config['light_response']['coefficients']['exponential']['applicability_source_ref']='different_domain'
    with pytest.raises(StudyError,match='predeclared_p3_coefficient_domain_does_not_match_reference'):
        map_single_day(path,config['light_response'],evidence_kind='user_assumed')
