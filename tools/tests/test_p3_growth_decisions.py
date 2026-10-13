"""D8–D10 synthetic invariants, not biological validation."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import math
from uuid import uuid4

import numpy as np
import pytest

from tools import probabilistic_compound_growth as p
from tools import growth_calibration as g
from tools import compound_growth as observed
from tools.leaf_light.common import DLI_UNIT, BUILD, StudyError, digest, read_json, write_json, rows, file_hash


@pytest.fixture(scope='module')
def fixture():
    root = BUILD / ('test_d8_d10_' + uuid4().hex)
    o,c = p.synthetic_fixture(root/'inputs')
    c['computation']['sample_count'] = 32
    part = c['parameter_particles'][0]
    part['plant_covariance'] = np.zeros((3,3)).tolist()
    for f in part['families'].values():
        f['initial_covariance'] = np.zeros((3,3)).tolist()
        f['innovation_covariance'] = np.zeros((3,3)).tolist()
    part['families']['residual']['mean'][0] = 0.
    part['families']['interval']['mean'][0] = math.log(5)
    part['axes']['stem']['stop_probability'] = 0
    return root,o,c


def beta_config(fixture):
    _,o,c = fixture; o,c = deepcopy(o),deepcopy(c)
    for name in ('residual','interval'):
        f = c['parameter_particles'][0]['families'][name]
        f['growth_curve'] = 'determinate_beta'
        for trait,target in dict(length=8,left=3,right=4,segment=6,area=5).items():
            for key,value in {f'{trait}_x_max_{p.BETA_TRAITS[trait]}':target,
                              f'{trait}_a_e_dev_days':10,f'{trait}_a_m_over_a_e':.5}.items():
                f['constants'][key] = dict(value=value,unit=p.UNITS[key])
        f['constants']['birth_area_cm2'] = dict(value=.2,unit='cm2')
    c['parameter_particles'][0]['axes']['stem']['area_basis_id'] = 'synthetic_patch'
    return o,c


def budget_config(fixture, pmf=None):
    _,o,c = fixture; o,c = deepcopy(o),deepcopy(c)
    o['axes']['stem'].update(observed_node_count=1,node_count_source_ref='synthetic_count')
    ap = c['parameter_particles'][0]['axes']['stem']; ap.pop('stop_probability')
    ap['node_budget'] = dict(pmf=pmf or [dict(n=2,p=.5),dict(n=4,p=.5)],source_kind='user_assumed',source_ref='synthetic')
    ap['truss_rule'] = dict(first_truss_rank_pmf=[dict(n=3,p=1)],interval_leaves=2,truss_observable='visible_bud',source_kind='user_assumed',source_ref='synthetic')
    return o,c


def light_response():
    return dict(kind='size_target_dli',time_basis='complete_local_day',value=20,center=10,scale=10,unit=DLI_UNIT,light_basis='incident',
                fixed_over_horizon=True,basis_id='synthetic_incident_daily_photon_dose',scope='whole_plant',
                source_kind='user_assumed',source_ref='SYNTHETIC ONLY',
                reference=dict(position_mm=[0,0,100],normal_unit_xyz=[0,0,1],frame_id='synthetic_board',
                    coordinate_frame='board_mm',source_kind='user_assumed',source_ref='synthetic reference plane'),
                local_day=dict(start_at='2026-10-03T00:00:00+09:00',end_at='2026-10-04T00:00:00+09:00',
                    timezone='Asia/Seoul',coverage='complete',source_kind='user_assumed',source_ref='synthetic complete day'),
                applicability_interval=dict(min=0,max=30,unit=DLI_UNIT,source_kind='user_assumed',source_ref='synthetic domain',applicability_source_ref='synthetic_p3_coefficient_domain'),
                coefficients={curve:dict(coefficient_id='synthetic_'+curve,role=role,c_DLI=math.log(2),
                    source_kind='user_assumed',source_ref='synthetic independent '+curve+' assumption',applicability_source_ref='synthetic_p3_coefficient_domain')
                    for curve,role in [('exponential','remaining_increment'),('determinate_beta','absolute_potential_maximum')]})


def clock():
    return p.normalized_temperature_clock(t_base_c=10,t_ref_c=20,m_max=2,upper_knot_c=40,
        intervals=[dict(start_day=0,end_day=30,input_value=20)],source_kind='user_assumed',
        source_ref='synthetic_setpoint',applicability='synthetic only')


def event_history(fixture, day=7, kind='truss', rank=3):
    root,o,_ = fixture; folder = root/('history_'+uuid4().hex)
    observed.templates(folder)
    manifest = read_json(folder/'observations.json')
    original = read_json(root/'inputs/observations/observations.json')
    manifest.update({k:v for k,v in original.items() if k!='tables'})
    now = (observed.aware_time(o['observed_at'])+timedelta(days=day)).isoformat()
    event = dict(plant_id=o['plant_id'],parent_stem_id='stem',event_kind=kind,node_rank=rank,truss_observable='visible_bud' if kind=='truss' else None,
                 observed_at=now,visibility='confirmed',source_ref='synthetic')
    table = folder/'event_observations.csv'; p._csv(table,[event],tuple(event))
    manifest['event_observations'] = dict(path=table.name,sha256=file_hash(table))
    write_json(folder/'observations.json',manifest)
    return folder,dict(observed_at=now,records=[])


@pytest.mark.parametrize('peak,end',[(5,10),(2,10),(8,10)])
def test_beta_endpoints_rates_and_monotonicity(peak,end):
    values = [p.beta_shape(a,peak,end) for a in np.linspace(0,end,101)]
    assert values[0] == 0 and values[-1] == 1
    assert np.all(np.diff(values)>=0)
    eps = 1e-8
    assert p.beta_shape(eps,peak,end)/eps < .003
    assert (1-p.beta_shape(end-eps,peak,end))/eps < 1e-5
    assert p.beta_shape(end+1,peak,end) == 1


@pytest.mark.parametrize('peak,end',[(0,10),(10,10),(11,10),(float('nan'),10)])
def test_beta_rejects_invalid_times(peak,end):
    with pytest.raises(StudyError): p.beta_shape(1,peak,end)


def test_beta_birth_and_target_and_preserved_measurements(fixture):
    o,c = beta_config(fixture); tr = p.sample_forecast(o,c)['trajectories'][0]
    assert tr['valid']
    day0 = p.decode_trajectory(tr,[0])[0]
    assert day0['rachis_points_mm'] == o['blocks'][0]['rachis_points_mm']
    b = tr['blocks'][1]; at_birth = p._decode_block(tr,b,1); at_end = p._decode_block(tr,b,11)
    assert at_birth['rachis_arc_length_mm'] == 2
    assert at_birth['supported_area_cm2'] == .2
    assert at_end['rachis_arc_length_mm'] == 8
    assert at_end['left_extent_mm'] == [3] and at_end['right_extent_mm'] == [4]
    assert at_end['supported_area_cm2'] == 5 and not at_end['optical_eligible']
    assert np.linalg.norm(np.array(p._axis_points(tr,'stem',11))[3]-np.array(p._axis_points(tr,'stem',11))[2]) == pytest.approx(6)


@pytest.mark.parametrize('key,value',[('length_x_max_mm',1),('length_a_m_over_a_e',1),('length_a_e_dev_days',0)])
def test_beta_invalid_particle_not_clipped(fixture,key,value):
    o,c = beta_config(fixture)
    c['parameter_particles'][0]['families']['residual']['constants'][key]['value'] = value
    b = p.sample_forecast(o,c)
    assert b['status']=='sample_failure' and all(not t['valid'] for t in b['trajectories'])


def test_beta_stochastic_coordinate_transforms_and_covariance(fixture):
    o,c = beta_config(fixture); part = c['parameter_particles'][0]
    part['coordinates'][2] = dict(name='length_x_max_mm',unit='mm',transform='exp',reference=1)
    for f in part['families'].values():
        f['constants'].pop('length_x_max_mm',None)
        f['constants']['D_length_mm'] = dict(value=5,unit='mm')
    assert p.sample_forecast(o,c)['trajectories'][0]['valid']
    part['coordinates'][2]['transform'] = 'identity'
    with pytest.raises(StudyError,match='x_max requires exp'): p.sample_forecast(o,c)


def test_beta_existing_binding_refused(fixture):
    o,c = beta_config(fixture)
    c['parameter_particles'][0]['existing_blocks']['L1'] = 'residual'
    with pytest.raises(StudyError,match='Existing blocks'): p.sample_forecast(o,c)


def test_temperature_normalization_and_domain(fixture):
    _,o,c = fixture; c = deepcopy(c); c.update(clock=clock(),environment_profile='d9')
    assert p._clock(c,30)==30
    assert p.sample_forecast(o,c)['environment_used']
    reference = dict(kind='fixed_setpoint',time_basis='calendar_day',temperature_c=20,source_kind='user_assumed',source_ref='synthetic')
    p.validate_calibration_clock(c,reference)
    with pytest.raises(StudyError,match=r'm\(T_ref\)'): p.validate_calibration_clock(c,dict(reference,temperature_c=25))
    with pytest.raises(StudyError,match='fluctuating'): p.validate_calibration_clock(c,dict(reference,kind='period_mean'))
    c['clock']['intervals'][0]['input_value']=41
    with pytest.raises(StudyError,match='outside supplied domain'): p.sample_forecast(o,c)


def test_dli_size_only_and_post_response_validity(fixture):
    _,o,c = fixture; c=deepcopy(c)
    before=p.sample_forecast(o,c)['trajectories'][0]
    c.update(environment_profile='d9',light_response=light_response())
    bank=p.sample_forecast(o,c); after=bank['trajectories'][0]
    assert after['events']==before['events']
    assert after['blocks'][0]['growth']['D_length_mm']==2*before['blocks'][0]['growth']['D_length_mm']
    assert p._decode_block(after,after['blocks'][0],7)['direction_unit_xyz']==p._decode_block(before,before['blocks'][0],7)['direction_unit_xyz']
    assert bank['p3_light_coupling']=='size_target_dli' and bank['light_used']
    o,c=beta_config(fixture); c['light_response']=light_response()
    after=p.sample_forecast(o,c)['trajectories'][0]
    assert p._decode_block(after,after['blocks'][1],11)['rachis_arc_length_mm']==16
    c['light_response']['coefficients']['determinate_beta']['c_DLI']=-10
    low=p.sample_forecast(o,c)
    assert low['status']=='assumption_conditioned' and all(t['valid'] for t in low['trajectories'])
    assert low['trajectories'][0]['availability'][0]['reason_code']=='dli_target_below_birth'


@pytest.mark.parametrize('metric',['dli_mol_m2_day','ppfd_umol_m2_s','temperature_c','relative_humidity_pct','co2_ppm','ec_ms_cm','ph'])
def test_d9_forbidden_family_paths(fixture,metric):
    _,o,c=fixture; c=deepcopy(c); c['environment_profile']='d9'
    f=c['parameter_particles'][0]['families']['existing']
    f.update(features=[metric],coefficients=[[0],[1],[0]],standardization={metric:dict(center=0,scale=1)})
    with pytest.raises(StudyError,match='D9'): p.sample_forecast(o,c)


def test_full_audit_legacy_family_stop_and_pack(fixture):
    _,o,c=fixture; c=deepcopy(c)
    c['environment_scenario']['values']={'co2_ppm':700}
    f=c['parameter_particles'][0]['families']['existing']
    f.update(features=['co2_ppm'],coefficients=[[0],[0],[.1]],standardization={'co2_ppm':dict(center=500,scale=100)})
    b=p.sample_forecast(o,c)
    assert b['environment_used'] and any('families.existing' in x['path'] for x in b['p3_environment_paths'])
    c['calibration']={'applied_features':[dict(column='ppfd_umol_m2_s',role='D')]}
    audit=p.environment_audit(c)
    assert audit['light_used'] and any(x['path'].startswith('calibration.') for x in audit['p3_environment_paths'])
    c['calibration']={ 'parameter_set_id':'legacy_without_provenance'}
    assert p.environment_audit(c)['environment_audit_status']=='unavailable'


@pytest.mark.parametrize('field',['basis_id','scope','source_ref','coefficients'])
def test_dli_missing_contract_refused(fixture,field):
    _,o,c=fixture; c=deepcopy(c); c['light_response']=light_response(); c['light_response'].pop(field)
    assert p.sample_forecast(o,c)['status']=='unavailable'


def test_budget_truncation_events_and_terminal(fixture):
    o,c=budget_config(fixture,[dict(n=0,p=.9),dict(n=2,p=.1)])
    b=p.sample_forecast(o,c)
    for tr in b['trajectories']:
        assert tr['n_max_drawn']=={'stem':2}
        assert len(tr['blocks'])==2
        terminal=[e for e in tr['events'] if e['event_kind']=='terminal']
        assert terminal[0]['node_rank']==2 and terminal[0]['appearance_elapsed_days']==1
        assert terminal[0]['geometry'] is None and terminal[0]['predicted_block_id'] is None
        assert not terminal[0]['optical_eligible']
    summaries=p.summarize_forecast(b,dict(quantiles=[.5],output_days=[7]))
    whole=next(r for r in summaries if r['quantity']=='new_block_count')
    assert whole['value'] is None and whole['post_termination_scope']=='unavailable'
    main=next(r for r in summaries if r['quantity']=='main_axis_new_leaf_count')
    assert main['count']==1 and main['value']==1


def test_empty_budget_and_conflicting_stop(fixture):
    o,c=budget_config(fixture,[dict(n=0,p=1)])
    b=p.sample_forecast(o,c)
    assert b['status']=='unavailable' and all('no_mass' in t['status_reason'] for t in b['trajectories'])
    c['parameter_particles'][0]['axes']['stem']['stop_logit']=dict(intercept=0,coefficients={},standardization={})
    with pytest.raises(StudyError,match='cannot be combined'): p.sample_forecast(o,c)


def test_budget_at_origin_no_wait_needed(fixture):
    o,c=budget_config(fixture,[dict(n=1,p=1)])
    ap=c['parameter_particles'][0]['axes']['stem']; ap.pop('residual_family'); ap.pop('inter_event_family')
    tr=p.sample_forecast(o,c)['trajectories'][0]
    assert tr['valid'] and tr['events'][0]['event_kind']=='terminal' and tr['events'][0]['appearance_elapsed_days']==0


def test_observed_truss_reweights_without_resampling(fixture):
    o,c=budget_config(fixture); b=p.sample_forecast(o,c); original=deepcopy(b)
    folder,assoc=event_history(fixture)
    model=dict(fields=[],units={},covariance=[],numeric_tolerance=1e-9,source_kind='user_assumed',source_ref='synthetic')
    update=p.update_forecast(b,folder,assoc,model)
    assert update['status']=='reweighted' and b==original
    after=update['bank']['trajectories']
    assert [t['trajectory_id'] for t in after]==[t['trajectory_id'] for t in b['trajectories']]
    assert [t['n_max_drawn'] for t in after]==[t['n_max_drawn'] for t in b['trajectories']]
    assert all(t['weight']==0 for t in after if t['n_max_drawn']['stem']==2)
    assert sum(t['weight'] for t in after)==pytest.approx(1)
    assert update['bank']['origin']['event_history'][0]['event_kind']=='truss'
    assert all(e.get('geometry') is None and e['predicted_block_id'] is None for t in after for e in t['events'] if e['event_kind']!='leaf')


@pytest.mark.parametrize('kind,rank',[('terminal',2),('leaf',3)])
def test_other_confirmed_event_evidence(fixture,kind,rank):
    o,c=budget_config(fixture); b=p.sample_forecast(o,c)
    folder,assoc=event_history(fixture,kind=kind,rank=rank)
    model=dict(fields=[],units={},covariance=[],numeric_tolerance=1e-9,source_kind='user_assumed',source_ref='synthetic')
    after=p.update_forecast(b,folder,assoc,model)['bank']['trajectories']
    expected=2 if kind=='terminal' else 4
    assert all(t['n_max_drawn']['stem']==expected for t in after if t['weight']>0)


def test_rank_event_evaluation_and_whole_plant_unavailable(fixture):
    o,c=budget_config(fixture); b=p.sample_forecast(o,c); folder,assoc=event_history(fixture)
    event=dict(plant_id=o['plant_id'],forecast_origin=o['observed_at'],target_at=assoc['observed_at'],
               kind='event',event_kind='truss',truss_observable='visible_bud',node_rank=3,parent_stem_id='stem',visibility='confirmed')
    plan=dict(train_plant_ids=['other'],test_plant_ids=[o['plant_id']],split_provenance='synthetic',interval_quantiles=[.1,.9],
              targets=[event,dict(event,kind='count',count=2)])
    result=p.evaluate_forecasts([b],folder,plan)
    probability=sum(t['weight'] for t in b['trajectories'] if t['n_max_drawn']['stem']==4)
    assert result['metrics'][0]['value']==pytest.approx(-math.log(probability))
    assert result['failures'][0]['reason']=='sympodial_continuation_not_modeled'


def test_retention_age_and_beta_continuation(fixture):
    o,c=beta_config(fixture); c.update(max_leaf_age_dev_days=3,leaf_age_evidence=dict(source_kind='user_assumed',source_ref='synthetic'))
    b=p.sample_forecast(o,c); tr=b['trajectories'][0]
    assert not p._decode_block(tr,tr['blocks'][1],4).get('retention_assumption_exceeded')
    assert p._decode_block(tr,tr['blocks'][1],4.1)['retention_assumption_exceeded']
    assert not p._decode_block(tr,tr['blocks'][0],20).get('retention_assumption_exceeded')
    folder,assoc=event_history(fixture,day=7,kind='leaf',rank=3)
    # No likelihood model: deterministic re-anchor without claiming a posterior.
    after=p.update_forecast(b,folder,assoc,None)['bank']['trajectories'][0]
    bb=after['blocks'][1]
    at_end=p._decode_block(after,bb,4)
    assert at_end['rachis_arc_length_mm']==pytest.approx(8)
    assert at_end['left_extent_mm']==pytest.approx([3])
    assert at_end['retention_assumption_exceeded']


def test_export_templates_and_hashes(fixture):
    root,_,_=fixture; o,c=budget_config(fixture); b=p.sample_forecast(o,c)
    b['summaries']=p.summarize_forecast(b,dict(quantiles=[.5]))
    out=p.export_run(b,root/'export'); manifest=read_json(out/'manifest.json')
    assert manifest['p3_light_coupling']=='none' and manifest['p3_environment_paths']==[]
    assert 'n_max_drawn' in rows(out/'trajectories.csv')[0]
    assert {x['event_kind'] for x in rows(out/'events.csv')}=={'leaf','truss','terminal'}
    assert all(file_hash(out/name)==sha for name,sha in manifest['output_hashes'].items())
    blank=p.templates(root/'templates'); fields=read_json(blank/'d8_d10_parameters.json')
    assert fields['light_response']['coefficients']['exponential']['c_DLI'] is None and fields['axis']['node_budget']['pmf'] is None


@pytest.fixture(scope='module')
def fitted(fixture):
    root,_,_=fixture
    obs,plan,treatments,evidence,_=g.synthetic_fixture(root/'calibration',replicates=3)
    plan['calibration_clock_reference']=dict(kind='fixed_setpoint',time_basis='calendar_day',temperature_c=20,
        source_kind='user_assumed',source_ref='SYNTHETIC fixed calibration setpoint')
    plan['engine_bindings']=[dict(target_id='length',family='existing',coordinate='D_length_mm',role='D',kind='physical_location',unit='mm')]
    # Actual synthetic target identifier is preserved rather than assumed.
    plan['engine_bindings'][0]['target_id']=plan['targets'][0]['id']
    return g.fit_growth_parameters(obs,evidence,plan,treatments)['parameter_set']


def test_frozen_calibration_clock_and_beta_guard(fixture,fitted):
    _,o,c=fixture; c=deepcopy(c)
    c['environment_scenario']['values']={'ppfd_umol_m2_s':200.}
    c['clock']=clock()
    out=g.apply_parameter_set(fitted,c,c['environment_scenario']['values'])
    assert out['calibration']['applied_features'] and p.environment_audit(out)['light_used']
    c['clock']['knots'][1]['multiplier']=.8
    with pytest.raises(StudyError,match=r'm\(T_ref\)'): g.apply_parameter_set(fitted,c,c['environment_scenario']['values'])
    c['clock']={'kind':'calendar'}
    c['parameter_particles'][0]['families']['existing']['growth_curve']='determinate_beta'
    with pytest.raises(StudyError,match='Beta-coordinate'): g.apply_parameter_set(fitted,c,c['environment_scenario']['values'])


@pytest.mark.parametrize('location',['stop','clock','alias','missing_indicator'])
def test_d9_indirect_light_paths_refused(fixture,location):
    _,o,c=fixture; c=deepcopy(c); c.update(environment_profile='d9',light_response=light_response())
    if location=='stop':
        ap=c['parameter_particles'][0]['axes']['stem']; ap.pop('stop_probability')
        ap['stop_logit']=dict(intercept=0,coefficients={'dli_mol_m2_day':0},standardization={'dli_mol_m2_day':dict(center=0,scale=1)})
    elif location=='clock':
        c['clock']=clock(); c['clock'].update(input_metric='dli_mol_m2_day',input_unit=DLI_UNIT)
    else:
        f=c['parameter_particles'][0]['families']['interval']
        metric='DLI' if location=='alias' else 'dli_mol_m2_day_missing'
        f.update(features=[metric],coefficients=[[1],[0],[0]],standardization={metric:dict(center=0,scale=1)})
    with pytest.raises(StudyError): p.sample_forecast(o,c)


def test_d9_fitted_legacy_response_refused(fixture,fitted):
    _,o,c=fixture; c=deepcopy(c)
    c.update(environment_profile='d9'); c['environment_scenario']['values']={'ppfd_umol_m2_s':200.}
    with pytest.raises(StudyError,match='D9'): g.apply_parameter_set(fitted,c,c['environment_scenario']['values'])


def test_retention_disabled_and_truss_unavailable(fixture):
    _,o,c=fixture; b=p.sample_forecast(o,c)
    assert all('retention_assumption_exceeded' not in s for s in p.decode_trajectory(b['trajectories'][0],[30]))
    summaries=p.summarize_forecast(b,dict(quantiles=[.5],output_days=[7]))
    truss=next(r for r in summaries if r['quantity']=='new_truss_count')
    assert truss['value'] is None and truss['reason']=='truss_rule_unavailable'


def test_budget_missing_observed_count_not_visible_block_count(fixture):
    o,c=budget_config(fixture); del o['axes']['stem']['observed_node_count']
    assert p.sample_forecast(o,c)['status']=='unavailable'


def test_beta_dli_update_preserves_remaining_curve(fixture):
    o,c=beta_config(fixture); c['light_response']=light_response()
    b=p.sample_forecast(o,c); folder,assoc=event_history(fixture,day=7)
    after=p.update_forecast(b,folder,assoc,None)['bank']['trajectories'][0]
    old=p.decode_trajectory(b['trajectories'][0],[11]); new=p.decode_trajectory(after,[4])
    for a,z in zip(old,new):
        if a['existence']!='appeared': continue
        assert z['rachis_arc_length_mm']==pytest.approx(a['rachis_arc_length_mm'])
        assert z['left_extent_mm']==pytest.approx(a['left_extent_mm'])
        assert z['right_extent_mm']==pytest.approx(a['right_extent_mm'])


def test_evaluation_exports_run_dependency_audit(fixture):
    root,_,_=fixture; o,c=budget_config(fixture); c['light_response']=light_response()
    b=p.sample_forecast(o,c); folder,assoc=event_history(fixture)
    plan=dict(train_plant_ids=['other'],test_plant_ids=[o['plant_id']],split_provenance='synthetic',interval_quantiles=[.1,.9],
        targets=[dict(plant_id=o['plant_id'],forecast_origin=o['observed_at'],observed_at=assoc['observed_at'],
                      kind='event',event_kind='truss',truss_observable='visible_bud',node_rank=3,parent_stem_id='stem',visibility='confirmed')])
    result=p.evaluate_forecasts([b],folder,plan)
    out=p.export_run(result,root/'evaluation'); manifest=read_json(out/'manifest.json')
    assert manifest['p3_light_coupling']=='size_target_dli' and manifest['light_used']
    assert manifest['p3_environment_paths'][0]['run_id']==b['run_id']


def test_legacy_golden_numerical_payload(fixture):
    root,o,_=fixture; c=read_json(root/'inputs/model.json')
    bank=p.sample_forecast(o,c)
    values=dict(states=[p.decode_trajectory(t,[0,7,14,21,30]) for t in bank['trajectories']],
        events=[[{k:v for k,v in e.items() if k not in ('event_kind','node_rank')} for e in t['events']] for t in bank['trajectories']],
        summaries=[{k:v for k,v in r.items() if k not in {'ensemble_weight','existence_mass','computable_mass','available_mass','not_present_mass','existence_unknown_mass','computational_unavailable_mass','support_denominator','available_fraction_of_ensemble','computational_reasons'}} for r in p.summarize_forecast(bank,dict(quantiles=[.1,.5,.9])) if r['quantity']!='new_truss_count'])
    # Keep provenance hashes, normalize only the test-specific absolute directory.
    for states in values['states']:
        for state in states:
            state.pop('source_row', None)  # Additive P3 area-review row lineage, not a model value.
            if 'provenance' in state:
                state['provenance']={Path(k).name:v for k,v in state['provenance'].items()}
    # Frozen from the pre-D8 source, before implementation; added output fields excluded.
    assert digest(values)=='e4a861974b972e11fe278cff039e9ab56c9ba7a127cc413d3fab1eaa872b616a'


def test_stopped_apex_conflicting_budget_unavailable(fixture):
    o,c=budget_config(fixture,[dict(n=2,p=1)])
    o['axes']['stem']['apex_status']='stopped'
    assert p.sample_forecast(o,c)['status']=='unavailable'


def test_beta_unknown_birth_not_invented():
    v=dict(area_x_max_cm2=10,area_a_e_dev_days=10,area_a_m_over_a_e=.5,beta_birth_values={'area':None})
    assert p._beta_value(v,'area',3,5) is None
