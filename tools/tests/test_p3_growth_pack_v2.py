"""V2/D19/D21 contracts on explicit synthetic records; no biological validation."""
from copy import deepcopy
import csv
import math
from pathlib import Path

import numpy as np
import pytest

from tools import probabilistic_compound_growth as p
from tools import growth_calibration as g
from tools import growth_day1 as day1
from tools.growth_observation_options import weighted_anchor, accumulate_corrections
from tools.leaf_light.common import DLI_UNIT, StudyError, read_json, write_json, file_hash, rows
from tools.tests.test_p3_growth_decisions import fixture, fitted, beta_config, budget_config, light_response, event_history
from tools.tests.test_probabilistic_compound_growth import later_observation


def displaced_observation(fixture,bank,day=2,delta_mm=4):
    folder,assoc=later_observation(fixture,bank,days=day)
    manifest=read_json(folder/'observations.json')
    path=folder/manifest['tables']['axes']['path']; rr=rows(path)
    points=np.array([[float(r[a+'_mm']) for a in 'xyz'] for r in rr])
    length=sum(np.linalg.norm(np.diff(points,axis=0),axis=1))
    points=points[0]+(points-points[0])*(length+delta_mm)/length
    for row,point in zip(rr,points):
        for a,v in zip('xyz',point): row[a+'_mm']=v
    p._csv(path,rr,tuple(rr[0])); manifest['tables']['axes']['sha256']=file_hash(path)
    write_json(folder/'observations.json',manifest)
    return folder,assoc


@pytest.mark.parametrize('omega',[0,.25,1])
def test_weighted_actual_update(fixture,omega):
    _,o,c=fixture; bank=p.sample_forecast(o,c); folder,assoc=displaced_observation(fixture,bank)
    pred=p.decode_trajectory(bank['trajectories'][0],[2])[0]['rachis_arc_length_mm']
    out=p.update_forecast(bank,folder,dict(assoc,reanchor_weight=omega),None)
    state=p.decode_trajectory(out['bank']['trajectories'][0],[0])[0]
    assert state['rachis_arc_length_mm']==pytest.approx(pred+omega*4)
    assert sum(np.linalg.norm(np.diff(state['rachis_points_mm'],axis=0),axis=1))==pytest.approx(state['rachis_arc_length_mm'])
    row=next(x for x in out['reanchor_corrections'] if x['quantity']=='rachis_arc_length_mm')
    assert row['applied_displacement']==pytest.approx(omega*4)
    if omega==1:
        default=p.update_forecast(bank,folder,assoc,None)
        assert [t['blocks'] for t in default['bank']['trajectories']]==[t['blocks'] for t in out['bank']['trajectories']]


def test_consecutive_cumulative_and_duplicate_safety(fixture):
    _,o,c=fixture; bank=p.sample_forecast(o,c); folder,assoc=displaced_observation(fixture,bank)
    first=p.update_forecast(bank,folder,dict(assoc,reanchor_weight=.5),None)
    replay=p.update_forecast(bank,folder,dict(assoc,reanchor_weight=.5),None)
    assert replay['reanchor_cumulative']==first['reanchor_cumulative']
    folder,assoc=displaced_observation(fixture,first['bank'],day=3,delta_mm=6)
    second=p.update_forecast(first['bank'],folder,dict(assoc,reanchor_weight=.5),None)
    row=next(r for r in second['reanchor_cumulative'] if r['quantity']=='rachis_arc_length_mm')
    assert row['cumulative_absolute_displacement']==pytest.approx(5)
    assert len(row['update_ids'])==2
    with pytest.raises(StudyError,match='follow origin'):
        p.update_forecast(second['bank'],folder,assoc,None)
    assert {r['unit'] for r in second['reanchor_cumulative']}<={'mm','cm2','rad'}


def test_weighted_beta_uses_same_remaining_increment(fixture):
    o,c=beta_config(fixture); tr=p.sample_forecast(o,c)['trajectories'][0]; block=tr['blocks'][1]
    pred=p._decode_block(tr,block,7); target=deepcopy(pred); target['rachis_arc_length_mm']+=4
    for omega in (0,.5,1):
        state,_=weighted_anchor(pred,target,dict(reanchor_weight=omega))
        rb=p._remaining(block,7,state)
        assert p._beta_value(rb['growth'],'length',state['rachis_arc_length_mm'],4)==pytest.approx(8+4*omega)


@pytest.mark.parametrize('case',['valid','missing','evidence_kind','zero','negative','unit','unidentified','cross'])
def test_covariance_opt_in_and_unavailable(fixture,case):
    _,o,c=fixture; tr=p.sample_forecast(o,c)['trajectories'][0]; pred=p.decode_trajectory(tr,[2])[0]
    target=deepcopy(pred); target['rachis_arc_length_mm']+=4
    record=dict(variance_state=3,variance_measurement=1,unit='mm^2',identifiable=True,source_kind='user_assumed',source_ref='SYNTHETIC')
    options=dict(reanchor_covariance=dict(mode='diagonal_variance',traits={'rachis_arc_length_mm':record}))
    if case=='missing': record.pop('source_ref')
    elif case=='evidence_kind': record['source_kind']='unsupported'
    elif case=='zero': record.update(variance_state=0,variance_measurement=0)
    elif case=='negative': record['variance_state']=-1
    elif case=='unit': record['unit']='cm2^2'
    elif case=='unidentified': record['identifiable']=False
    elif case=='cross': options['reanchor_covariance']['cross_covariance']=[[1,.2],[.2,1]]
    state,audit=weighted_anchor(pred,target,options); row=audit[0]
    if case=='valid':
        assert row['omega']==.75 and state['rachis_arc_length_mm']==pred['rachis_arc_length_mm']+3
    else:
        assert row['omega'] is None and row['reason_code']
        assert state['rachis_arc_length_mm']==pred['rachis_arc_length_mm']


def test_unsupported_geometry_is_explicit(fixture):
    _,o,c=fixture; tr=p.sample_forecast(o,c)['trajectories'][0]; pred=p.decode_trajectory(tr,[2])[0]
    target=deepcopy(pred); target['direction_unit_xyz']=[0,0,1]
    state,audit=weighted_anchor(pred,target,dict(reanchor_weight=.5))
    assert state['direction_unit_xyz']==pred['direction_unit_xyz']
    assert next(r for r in audit if r['quantity']=='direction_unit_xyz')['reason_code']=='reanchor_direction_correction_unsupported'


def posture_model(assoc,offset):
    return dict(source_kind='user_assumed',source_ref='SYNTHETIC',fields=['direction_tangent_1_rad'],
        units={'direction_tangent_1_rad':'rad'},covariance=[[.1]],numeric_tolerance=1e-9,
        posture_offset=dict(enabled=True,reference_phase='early_photoperiod',source_kind='user_assumed',source_ref='SYNTHETIC',
            observed_at=assoc['observed_at'],time_reference='declared_capture_phase',offsets={
                phase:dict(unit='rad',source_ref='SYNTHETIC',values={'direction_tangent_1_rad':value})
                for phase,value in [('early_photoperiod',0),('late_photoperiod',offset)]}))


def test_posture_likelihood_only_zero_disabled_and_wrapping(fixture):
    _,o,c=fixture; bank=p.sample_forecast(o,c)
    for i,tr in enumerate(bank['trajectories']): tr['blocks'][0]['growth']['rotation_z_rad']+=i/5
    original=deepcopy(bank); folder,assoc=later_observation(fixture,bank)
    assoc['capture_phase']='late_photoperiod'
    zero=posture_model(assoc,0); disabled=deepcopy(zero); disabled['posture_offset']=None
    a=p.update_forecast(bank,folder,assoc,zero); b=p.update_forecast(bank,folder,assoc,disabled)
    assert [t['weight'] for t in a['bank']['trajectories']]==[t['weight'] for t in b['bank']['trajectories']]
    changed=p.update_forecast(bank,folder,assoc,posture_model(assoc,.4))
    wrapped=p.update_forecast(bank,folder,assoc,posture_model(assoc,.4+2*math.pi))
    assert [t['weight'] for t in changed['bank']['trajectories']]!=[t['weight'] for t in a['bank']['trajectories']]
    assert [t['weight'] for t in changed['bank']['trajectories']]==pytest.approx([t['weight'] for t in wrapped['bank']['trajectories']])
    assert [t['blocks'] for t in changed['bank']['trajectories']]==[t['blocks'] for t in a['bank']['trajectories']]
    assert bank==original


@pytest.mark.parametrize('bad',['reference','evidence','phase','time'])
def test_posture_missing_science_has_explicit_outcome(fixture,bad):
    _,o,c=fixture; bank=p.sample_forecast(o,c); folder,assoc=later_observation(fixture,bank)
    assoc['capture_phase']='late_photoperiod'; model=posture_model(assoc,.1)
    if bad=='reference': model['posture_offset']['offsets']['early_photoperiod']['values']['direction_tangent_1_rad']=.1
    elif bad=='evidence': model['posture_offset'].pop('source_ref')
    elif bad=='phase': assoc.pop('capture_phase')
    elif bad=='time': model['posture_offset']['observed_at']='2026-01-01T00:00:00Z'
    result=p.update_forecast(bank,folder,assoc,model)
    assert result['parameter_update']=='unavailable' and result['posture_diagnostics']['unavailable']
    assert [t['weight'] for t in result['bank']['trajectories']]==[t['weight'] for t in bank['trajectories']]


def test_truss_missing_semantics_preserves_leaf_terminal_and_weights(fixture):
    o,c=budget_config(fixture); declared=p.sample_forecast(o,c)
    c['parameter_particles'][0]['axes']['stem']['truss_rule'].pop('truss_observable')
    legacy=p.sample_forecast(o,c)
    assert all(t['valid'] for t in legacy['trajectories'])
    for a,b in zip(declared['trajectories'],legacy['trajectories']):
        assert a['weight']==b['weight'] and a['blocks']==b['blocks']
        assert [e for e in a['events'] if e['event_kind']!='truss']==b['events']
        assert any(x['reason_code']=='truss_observable_undeclared' for x in b['availability'])
    summary=p.summarize_forecast(legacy,dict(quantiles=[.5],output_days=[7]))
    truss=next(r for r in summary if r['quantity']=='new_truss_count')
    assert truss['value'] is None and truss['computable_mass']==0
    leaf=next(r for r in summary if r['target_id']=='L1' and r['quantity']=='rachis_arc_length_mm')
    assert leaf['existence_mass']==1


def test_mismatched_truss_evidence_does_not_condition(fixture):
    o,c=budget_config(fixture); bank=p.sample_forecast(o,c); folder,assoc=event_history(fixture)
    m=read_json(folder/'observations.json'); table=folder/m['event_observations']['path']; rr=rows(table)
    rr[0]['truss_observable']='first_open_flower'; p._csv(table,rr,tuple(rr[0])); m['event_observations']['sha256']=file_hash(table)
    write_json(folder/'observations.json',m)
    model=dict(source_kind='user_assumed',source_ref='SYNTHETIC',fields=[],units={},covariance=[],numeric_tolerance=1e-9)
    result=p.update_forecast(bank,folder,assoc,model)
    assert 'truss_observable_mismatch' in result['unavailable']
    assert [t['weight'] for t in result['bank']['trajectories']]==[t['weight'] for t in bank['trajectories']]


def test_support_separates_nonappearance_low_dli_and_terminal(fixture):
    o,c=beta_config(fixture); c['light_response']=light_response()
    c['light_response']['coefficients']['determinate_beta']['c_DLI']=math.log(.1)
    bank=p.sample_forecast(o,c)
    summary=p.summarize_forecast(bank,dict(quantiles=[.5],output_days=[0,7]))
    key='/'.join(bank['trajectories'][0]['blocks'][1]['block_id'].split('/')[1:])
    for row in summary:
        if row['quantity']=='rachis_arc_length_mm' and row['target_id']==key:
            assert row['ensemble_weight']==1 and row['computable_mass']==0 and row['available_mass']==0
            assert row['existence_mass']==(1 if row['horizon_days']==7 else 0)
    o,c=budget_config(fixture,[dict(n=2,p=1)]); bank=p.sample_forecast(o,c)
    summary=p.summarize_forecast(bank,dict(quantiles=[.5],output_days=[7]))
    plant=next(r for r in summary if r['quantity']=='new_block_count')
    assert plant['existence_mass']==0 and plant['computable_mass']==1
    assert next(r for r in summary if r['target_id']=='L1' and r['quantity']=='rachis_arc_length_mm')['existence_mass']==1


def test_hard_admissibility_raw_count_mass_and_order(fixture):
    o,c=budget_config(fixture); bank=p.sample_forecast(o,c)
    weights=np.arange(1,33,dtype=float); weights/=weights.sum()
    for tr,w in zip(bank['trajectories'],weights): tr['weight']=float(w)
    folder,assoc=event_history(fixture)
    model=dict(source_kind='user_assumed',source_ref='SYNTHETIC',fields=[],units={},covariance=[],numeric_tolerance=1e-9)
    out=p.update_forecast(bank,folder,assoc,model); d=out['conditioning_diagnostics']
    mask=np.array([tr['n_max_drawn']['stem']==4 for tr in bank['trajectories']])
    assert d['event_stage']=='hard_admissibility' and d['n_particles_rejected_by_events']==sum(~mask)
    assert d['event_rejected_prior_mass']==pytest.approx(sum(weights[~mask]))
    likelihood=np.linspace(.1,1,32)
    a=(weights*likelihood)*mask; b=(weights*mask)*likelihood
    assert a/a.sum()==pytest.approx(b/b.sum())


def test_failed_draw_is_unknown_existence_not_biological_absence(fixture):
    _,o,c=fixture; bank=p.sample_forecast(o,c)
    failed=bank['trajectories'][0]; failed.update(valid=False,status_reason='SYNTHETIC parameter failure')
    summary=p.summarize_forecast(bank,dict(quantiles=[.5],output_days=[7]))
    row=next(r for r in summary if r['target_id']=='L1' and r['quantity']=='rachis_arc_length_mm')
    assert row['not_present_mass']==0 and row['existence_unknown_mass']==1/32
    assert row['computable_mass']==row['available_mass']==row['existence_mass']==31/32


def test_full_subbase_validator_and_cross_meaning(fixture):
    _,o,c=fixture; c=deepcopy(c)
    c.update(environment_profile='d9',clock=p.normalized_temperature_clock(t_base_c=10,t_ref_c=20,m_max=2,lower_knot_c=5,
        upper_knot_c=40,intervals=[dict(start_day=0,end_day=30,input_value=7)],source_kind='user_assumed',source_ref='SYNTHETIC',applicability='synthetic'))
    assert p.validate_model_config(c,o)['status']=='assumption_conditioned'
    assert p._clock(c,30)==0
    c['clock']['knots'][0]['multiplier']=.1
    with pytest.raises(StudyError,match='normalization'): p.validate_model_config(c,o)
    for coordinate in ('left_target_mm','length_x_max_mm'):
        with pytest.raises(StudyError,match='meaning mismatch'): g._check_binding_meaning({'family':'anchored_expansion'},'D',coordinate)


def test_legacy_missing_unit_and_interval_mapping(fixture):
    _,o,c=fixture; c=deepcopy(c); c['light_response']={'kind':'size_target_dli','unit':'mol/m2/d'}
    result=p.sample_forecast(o,c)
    issue=result['availability'][0]
    assert issue['reason_code']=='legacy_dli_unit_spelling'
    fields={r['field'] for r in issue['fields']}
    assert {'light_response.basis_id','light_response.time_basis','applicability_interval.min','reference.position_mm','local_day.start_at'}<=fields
    c['light_response']=light_response(); c['dli_applicability_interval']=c['light_response'].pop('applicability_interval')
    assert p.sample_forecast(o,c)['trajectories']
    c['light_response']['applicability_interval']=dict(c['dli_applicability_interval'],max=29)
    with pytest.raises(StudyError,match='Conflicting'): p.sample_forecast(o,c)


def test_reverse_hashed_p2_manifest_and_domain_evidence(fixture,tmp_path):
    _,o,c=fixture; c=deepcopy(c); c['light_response']=light_response()
    path=tmp_path/'p2_manifest.json'; write_json(path,dict(status='available',patches=[dict(area_basis_id=c['light_response']['basis_id'])]))
    c['p2_tissue_manifest']=dict(path=str(path),sha256=file_hash(path))
    assert p.sample_forecast(o,c)['availability'][0]['reason_code']=='basis_collides_with_tissue_basis'
    write_json(path,dict(status='available',patches=[dict(area_basis_id='different_tissue')]))
    c['p2_tissue_manifest']['sha256']=file_hash(path)
    assert p.sample_forecast(o,c)['trajectories']
    c['light_response']['applicability_interval']['applicability_source_ref']='arbitrary_sensor_setup'
    assert p.sample_forecast(o,c)['availability'][0]['reason_code']=='dli_applicability_coefficient_domain_mismatch'


def test_calibration_legacy_science_result(fixture,fitted):
    c=deepcopy(fixture[2]); c['light_response']={'kind':'size_target_dli','unit':'mol/m2/d'}
    result=g.apply_parameter_set(fitted,c,c['environment_scenario']['values'])
    assert result['status']=='unavailable' and not result['calibration_applied']
    assert result['unavailable'][0]['reason_code']=='legacy_dli_unit_spelling'


def test_day1_history_pipeline_backfills_only_explicit_capture(tmp_path):
    origin,config=p.synthetic_fixture(tmp_path/'inputs')
    source=day1_file(tmp_path/'inputs/observations/day1.csv',[dict(plant_id=origin['plant_id'],
        capture_session_id=origin['session_id'],captured_at=origin['observed_at'],capture_phase='early_photoperiod',
        node_count=4,node_count_source_ref='SYNTHETIC counting rule',truss_observable='visible_bud',truss_visible_bud_count=0)])
    manifest_path=source.parent/'observations.json'; manifest=read_json(manifest_path)
    manifest['day1_protocol']=dict(path=source.name,sha256=file_hash(source)); write_json(manifest_path,manifest)
    cfg=read_json(tmp_path/'inputs/origin.json'); cfg['day1_axis_id']='stem'
    updated=p.prepare_origin(source.parent,tmp_path/'inputs/structure.json',cfg)
    assert updated['capture_phase']=='early_photoperiod' and updated['axes']['stem']['observed_node_count']==4
    assert updated['blocks'][0]['capture_phase']=='early_photoperiod'
    assert file_hash(source)==manifest['day1_protocol']['sha256']
    assert updated['blocks'][0].get('organ_born_dev') is None


def test_synthetic_reference_json_to_p3_validation_only(fixture,tmp_path):
    # Explicit bounded representation mapping; no producer/model integration run.
    _,o,c=fixture; c=deepcopy(c); light=light_response()
    position=dict(applicability_interval_mol_m2_day=[0,30],applicability_source_ref='synthetic_p3_coefficient_domain',
        position_mm=light['reference']['position_mm'],sensor_normal=light['reference']['normal_unit_xyz'],
        frame_id=light['reference']['frame_id'],coordinate_frame=light['reference']['coordinate_frame'])
    reference=dict(quantity='incident',model_scope='whole_plant',unit=DLI_UNIT,basis_id=light['basis_id'],
        value=11.52,time_basis='complete_local_day',applicability_interval=position['applicability_interval_mol_m2_day'],
        applicability_source_ref=position['applicability_source_ref'],fixed_over_horizon=True,local_day=light['local_day'])
    write_json(tmp_path/'reference_position.json',position); write_json(tmp_path/'reference_dli.json',reference)
    src=read_json(tmp_path/'reference_dli.json')
    light.update(value=src['value'],unit=src['unit'],time_basis=src['time_basis'],light_basis=src['quantity'],scope=src['model_scope'])
    light['applicability_interval'].update(min=src['applicability_interval'][0],max=src['applicability_interval'][1],applicability_source_ref=src['applicability_source_ref'])
    c['light_response']=light
    p._validate_d9(c,o)
    assert light['value']==11.52 and light['applicability_interval']['applicability_source_ref']==position['applicability_source_ref']
    light['applicability_interval'].pop('applicability_source_ref')
    result=p.validate_model_config(c,o)
    assert result['status']=='unavailable'


def test_hashed_domain_pointer_rejects_sensor_metadata(fixture,tmp_path):
    _,o,c=fixture; c=deepcopy(c); c['light_response']=light_response()
    path=tmp_path/'parameter_pack.json'; write_json(path,dict(coefficient_domain=dict(min=0,max=30,unit=DLI_UNIT),sensor=dict(model='SYNTHETIC')))
    ref=dict(path=str(path),sha256=file_hash(path),json_pointer='/coefficient_domain')
    c['light_response']['applicability_interval']['applicability_source_ref']=ref
    for binding in c['light_response']['coefficients'].values(): binding['applicability_source_ref']=deepcopy(ref)
    p._validate_d9(c,o)
    c['light_response']['applicability_interval']['applicability_source_ref']['json_pointer']='/sensor'
    assert p.validate_model_config(c,o)['unavailable'][0]['reason_code']=='dli_applicability_source_domain_mismatch'


def test_actual_p2_reference_output_to_p3_validator_only(fixture,tmp_path):
    from tools.reference_dli_demo import create_inputs
    from tools.reference_dli import prepare_record,save_result
    inputs=tmp_path/'producer_inputs'; create_inputs(inputs)
    position=read_json(inputs/'reference_position.json')
    # Freeze an explicit absolute evidence reference before the producer runs.
    position['applicability_source_ref']['path']=str((inputs/'synthetic_evidence.json').resolve())
    write_json(inputs/'reference_position.json',position)
    record,audit=prepare_record(inputs/'reference_position.json',inputs/'schedule.json',route='spot_schedule',
        readings_path=inputs/'reference_readings.csv',survey_path=inputs/'spot_survey.csv')
    assert record['status']=='available' and record['value']==11.52
    save_result(record,audit,tmp_path/'producer_output')
    src=read_json(tmp_path/'producer_output/reference_dli.json')
    _,o,c=fixture; c=deepcopy(c); light=light_response(); day=src['days'][src['days_used'][0]['local_date']]
    light.update(value=src['value'],unit=src['unit'],basis_id=src['basis_id'],light_basis=src['quantity'],scope=src['model_scope'],
        time_basis=src['time_basis'],fixed_over_horizon=src['fixed_over_horizon'])
    light['reference'].update(position_mm=src['reference']['position_mm'],normal_unit_xyz=src['reference']['sensor_normal'],
        frame_id=src['reference']['frame_id'],coordinate_frame=src['reference']['coordinate_frame'])
    light['local_day'].update(start_at=day['start_at'],end_at=day['end_at'],timezone=src['timezone'],coverage=day['coverage_status'])
    light['applicability_interval'].update(min=src['applicability_interval'][0],max=src['applicability_interval'][1],applicability_source_ref=src['applicability_source_ref'])
    for binding in light['coefficients'].values(): binding['applicability_source_ref']=deepcopy(src['applicability_source_ref'])
    c['light_response']=light; p._validate_d9(c,o)  # No growth forecast or model integration.
    assert light['applicability_interval']['applicability_source_ref']==position['applicability_source_ref']
    light['value']=31
    with pytest.raises(p.ScienceUnavailable,match='outside_applicability'): p._validate_d9(c,o)


def day1_file(path,records):
    p._csv(path,records,day1.COLUMNS)
    return path


def test_day1_header_explicit_backfill_and_immutability(fixture,tmp_path):
    _,o,_=fixture
    path=day1_file(tmp_path/'day1.csv',[])
    assert day1.load_day1_protocol(path)['status']=='header_only'
    row=dict(plant_id=o['plant_id'],capture_session_id=o['session_id'],captured_at=o['observed_at'],capture_phase='early_photoperiod',
        node_count=4,node_count_source_ref='SYNTHETIC reviewed counting rule',truss_observable='visible_bud',truss_visible_bud_count=0)
    day1_file(path,[row]); sha=file_hash(path); result=day1.load_day1_protocol(path)
    record=result['records'][0]
    assert record['truss_visible_bud_count']==0 and record['sowing_date'] is None
    assert record['phase_meaning']=='2 h after actual lights-on' and record['source_row']==2
    origin=day1.backfill_origin(o,result,'stem')
    assert origin['axes']['stem']['observed_node_count']==4 and not record['organ_age_inferred']
    _,c=budget_config(fixture,[dict(n=2,p=.5),dict(n=4,p=.5)])
    assert all(t['n_max_drawn']['stem']==4 for t in p.sample_forecast(origin,c)['trajectories'])
    assert file_hash(path)==sha and 'observed_node_count' not in o['axes']['stem']


@pytest.mark.parametrize('field',['captured_at','node_count_source_ref','truss_observable'])
def test_day1_missing_science_and_incompatible_meaning(tmp_path,field):
    row=dict(plant_id='P',capture_session_id='s',captured_at='2026-10-04T08:00:00+09:00',capture_phase='early_photoperiod',
        node_count=0,node_count_source_ref='SYNTHETIC',truss_observable='visible_bud',truss_visible_bud_count=0)
    row[field]=None; path=day1_file(tmp_path/'day1.csv',[row])
    assert day1.load_day1_protocol(path)['records'][0]['status']=='unavailable'
    row['truss_observable']='first_open_flower'; day1_file(path,[row])
    assert 'day1_truss_observable_incompatible' in day1.load_day1_protocol(path)['records'][0]['availability']
