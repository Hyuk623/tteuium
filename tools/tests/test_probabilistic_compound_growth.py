"""Growth mathematics and integration checks using labelled synthetic evidence."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import csv
import json
import subprocess
import sys

import numpy as np
import pytest

from tools import probabilistic_compound_growth as pcg
from tools import compound_growth as cg
from tools.leaf_light.common import StudyError, BUILD, read_json, write_json, file_hash, rows


@pytest.fixture(scope='module')
def fixture():
    root=BUILD/('growth_test_'+uuid4().hex)
    origin,model=pcg.synthetic_fixture(root/'inputs')
    model['computation']['sample_count']=4
    return root,origin,model


def deterministic(fixture,wait=.25,interval=10,stop=0):
    root,origin,config=fixture; c=deepcopy(config); p=c['parameter_particles'][0]
    p['plant_covariance']=np.zeros((3,3)).tolist()
    for f in p['families'].values():
        f['initial_covariance']=np.zeros((3,3)).tolist(); f['innovation_covariance']=np.zeros((3,3)).tolist()
    p['families']['residual']['mean'][0]=float(np.log(wait))
    p['families']['interval']['mean'][0]=float(np.log(interval))
    p['axes']['stem']['stop_probability']=stop
    return deepcopy(origin),c


def test_measured_origin_exact_and_immutable(fixture):
    _,origin,c=fixture; before=deepcopy(origin); bank=pcg.sample_forecast(origin,c)
    for tr in bank['trajectories']:
        s=pcg.decode_trajectory(tr,[0])[0]
        for k in ('rachis_points_mm','attachment_xyz_mm','axis_stations','left_extent_mm','right_extent_mm','supported_area_cm2'):
            assert s[k]==origin['blocks'][0][k]
        assert not s['eligible_state'] and not s['optical_eligible']
    assert origin==before


def test_material_attachment_and_saturation(fixture):
    origin,c=deterministic(fixture,stop=1); tr=pcg.sample_forecast(origin,c)['trajectories'][0]
    s=pcg.decode_trajectory(tr,[5])[0]; delta=3*(1-np.exp(-.1*5))
    assert s['attachment_xyz_mm']==pytest.approx([.2,0,5+delta/2])
    assert s['rachis_arc_length_mm']==pytest.approx(origin['blocks'][0]['rachis_arc_length_mm']+5*(1-np.exp(-.5)))
    assert s['supported_area_cm2']==pytest.approx(2+1-np.exp(-.5))


def test_residual_wait_and_multiple_within_day(fixture):
    origin,c=deterministic(fixture,wait=.2,interval=.3); c['computation']['max_events_per_axis']=200
    tr=pcg.sample_forecast(origin,c)['trajectories'][0]
    assert tr['valid']
    assert [e['appearance_elapsed_days'] for e in tr['events'][:3]]==pytest.approx([.2,.5,.8])
    future=tr['blocks'][1]
    before=next(s for s in pcg.decode_trajectory(tr,[.1]) if s['block_id']==future['block_id'])
    assert before['existence']=='not_yet_appeared' and before['rachis_points_mm'] is None
    pp_before=pcg._axis_points(tr,'stem',.2-1e-8)
    pp_at=pcg._axis_points(tr,'stem',.2)
    assert pp_before[-1]==pytest.approx(pp_at[-1],abs=1e-7)
    assert pp_at[-1]==pp_at[-2]


def test_stop_and_resource_limit(fixture):
    o,c=deterministic(fixture,stop=1); tr=pcg.sample_forecast(o,c)['trajectories'][0]
    assert tr['events'][0]['event_state']=='stopped' and tr['events'][0]['appearance_elapsed_days'] is None
    o,c=deterministic(fixture,wait=.1,interval=.1); c['computation']['max_events_per_axis']=2
    b=pcg.sample_forecast(o,c)
    assert all(not t['valid'] and 'resource limit' in t['status_reason'] for t in b['trajectories'])


def test_output_frequency_order_reproducibility(fixture):
    _,o,c=fixture; a=pcg.sample_forecast(o,c)
    other=deepcopy(c); other['computation']['output_days']=[0,1,2,7,30]
    b=pcg.sample_forecast(o,other)
    for x,y in zip(a['trajectories'],b['trajectories']):
        assert x['events']==y['events']
        assert pcg.decode_trajectory(x,[7])==pcg.decode_trajectory(y,[7])
        assert pcg.decode_trajectory(x,[7])==pcg.decode_trajectory(x,[0,7,30])[len(x['blocks']):2*len(x['blocks'])]
    original=deepcopy(o); original['blocks'].reverse()
    assert pcg.sample_forecast(original,c)['trajectories'][0]['events']==a['trajectories'][0]['events']


@pytest.mark.parametrize('field,value',[('stop_probability',-1),('stop_probability',1.1)])
def test_invalid_probabilities(fixture,field,value):
    _,o,c=fixture; c=deepcopy(c); c['parameter_particles'][0]['axes']['stem'][field]=value
    with pytest.raises(StudyError): pcg.sample_forecast(o,c)


@pytest.mark.parametrize('mutation',['covariance','unit','weight','seed','feature','rho','reference'])
def test_invalid_parameters(fixture,mutation):
    _,o,c=fixture; c=deepcopy(c); p=c['parameter_particles'][0]
    if mutation=='covariance': p['plant_covariance'][0][0]=-1
    if mutation=='unit': p['coordinates'][0]['unit']='mm'
    if mutation=='weight': p['weight']=.2
    if mutation=='seed': c['computation']['seed']=True
    if mutation=='feature': p['families']['residual']['features']=['imaginary']
    if mutation=='rho': p['families']['residual']['rho']=1
    if mutation=='reference': p['coordinates'][0]['reference']=0
    with pytest.raises(StudyError): pcg.sample_forecast(o,c)


def test_missing_parameters_and_disabled_flow(fixture):
    _,o,c=fixture
    b=pcg.sample_forecast(o,pcg.blank_model()); assert b['status']=='unavailable' and not b['trajectories']
    c=deepcopy(c); c['sampler']='flow_matching'
    assert pcg.sample_forecast(o,c)['status']=='unavailable'


def test_counts_without_spatial_geometry(fixture):
    o,c=deterministic(fixture); o['axes']['stem'].update(points_mm=None,frames=None,segments=[],apex_available=False)
    o['attachments']={}
    b=pcg.sample_forecast(o,c)
    assert all(t['valid'] for t in b['trajectories'])
    at=pcg.decode_trajectory(b['trajectories'][0],[7])
    assert any(s['state_source']=='predicted_future' and s['attachment_xyz_mm'] is None for s in at)
    summary=pcg.summarize_forecast(b,dict(quantiles=[.1,.9]))
    assert any(s['quantity']=='new_block_count' and s['value'] is not None for s in summary)


def test_area_basis_and_missing_rates(fixture):
    o,c=deterministic(fixture,stop=1); o['blocks'][0]['supported_area_cm2']=None; o['blocks'][0]['area_basis_id']=None
    c['parameter_particles'][0]['families']['existing']['constants'].pop('k_width')
    s=pcg.decode_trajectory(pcg.sample_forecast(o,c)['trajectories'][0],[7])[0]
    assert s['supported_area_cm2'] is None and s['left_extent_mm'] is None
    assert s['rachis_arc_length_mm'] is not None


def test_environment_clock_pauses_and_response(fixture):
    o,c=deterministic(fixture,wait=1)
    c['clock']=dict(kind='piecewise_constant',source_kind='user_assumed',source_ref='synthetic',intervals=[
        dict(start_day=0,end_day=5,multiplier=0),dict(start_day=5,end_day=30,multiplier=2)])
    tr=pcg.sample_forecast(o,c)['trajectories'][0]
    assert tr['events'][0]['appearance_elapsed_days']==pytest.approx(5.5)
    assert pcg.decode_trajectory(tr,[3])[0]['rachis_arc_length_mm']==o['blocks'][0]['rachis_arc_length_mm']
    c['clock']=dict(kind='piecewise_linear_response',source_kind='user_assumed',source_ref='synthetic response',
        input_metric='temperature_c',input_unit='deg C',target='development_clock',equation_version='piecewise_linear-1',applicability='synthetic only',
        knots=[dict(value=10,multiplier=0),dict(value=30,multiplier=2)],intervals=[dict(start_day=0,end_day=30,input_value=20)])
    assert pcg._clock(c,7)==7
    c['clock']['intervals'][0]['input_value']=31
    with pytest.raises(StudyError,match='domain'): pcg.sample_forecast(o,c)


def test_wrapped_and_signed_direction(fixture):
    o,c=deterministic(fixture); p=c['parameter_particles'][0]
    p['families']['residual']['mean'][1]=np.radians(359)
    p['families']['residual']['constants']['elevation_rad']['value']=-.4
    tr=pcg.sample_forecast(o,c)['trajectories'][0]; s=pcg.decode_trajectory(tr,[.25])[1]
    assert np.linalg.norm(s['direction_unit_xyz'])==pytest.approx(1)
    local=np.array(tr['axes']['stem']['frames'][-1]).T@s['direction_unit_xyz']
    assert np.arctan2(local[1],local[0])==pytest.approx(np.radians(-1))
    assert np.arcsin(local[2])==pytest.approx(-.4)


def later_observation(fixture,bank,days=2):
    root,_,_=fixture; target=root/('target_'+uuid4().hex); target.mkdir(parents=True)
    s=pcg.decode_trajectory(bank['trajectories'][0],[days])[0]; base=dict(plant_id=s['plant_id'],compound_leaf_id='L1',session_id='later')
    rr=dict(base,observed_at=s['target_at'],parent_stem_id='stem',identity_status='confirmed',review_source='synthetic',geometry_status='observed_axis',
            development_state='unfolding',first_observed_at=None,supported_area_cm2=s['supported_area_cm2'],area_basis_id=s['area_basis_id'],estimated_total_area_cm2=None,
            **dict(zip(('transverse_x','transverse_y','transverse_z'),s['transverse_unit_xyz'])))
    records={'observations':[rr], 'axes':[dict(base,station=x,**dict(zip(('x_mm','y_mm','z_mm'),v))) for x,v in zip(s['axis_stations'],s['rachis_points_mm'])],
             'extents':[dict(base,station=x,left_mm=l,right_mm=r) for x,l,r in zip(s['extent_stations'],s['left_extent_mm'],s['right_extent_mm'])]}
    manifest=read_json(root/'inputs/observations/observations.json')
    for name,cols in (('observations',cg.OBS_COLUMNS),('axes',cg.AXIS_COLUMNS),('extents',cg.EXTENT_COLUMNS)):
        p=target/(name+'.csv'); pcg._csv(p,records[name],cols); manifest['tables'][name]=dict(path=p.name,sha256=file_hash(p))
    write_json(target/'observations.json',manifest)
    associations=dict(observed_at=s['target_at'],records=[dict(observed_id='L1',predicted_id='L1',status='confirmed',source_ref='synthetic')])
    return target,associations


def test_reanchor_and_no_double_growth(fixture):
    o,c=deterministic(fixture,stop=1); bank=pcg.sample_forecast(o,c); original=deepcopy(bank)
    target,assoc=later_observation(fixture,bank)
    update=pcg.update_forecast(bank,target,assoc,None)
    assert update['parameter_update']=='unavailable' and bank==original
    new=update['bank']['trajectories'][0]
    assert pcg.decode_trajectory(new,[0])[0]['rachis_points_mm']==pcg.decode_trajectory(bank['trajectories'][0],[2])[0]['rachis_points_mm']
    assert pcg.decode_trajectory(new,[3])[0]['rachis_arc_length_mm']==pytest.approx(pcg.decode_trajectory(bank['trajectories'][0],[5])[0]['rachis_arc_length_mm'])
    assert update['bank']['available_horizon_days']==28
    with pytest.raises(StudyError): pcg.decode_trajectory(new,[30])
    assert pcg.update_forecast(bank,None,{},None)['bank']==bank


def test_likelihood_support_failure_and_posterior(fixture):
    o,c=deterministic(fixture,stop=1); bank=pcg.sample_forecast(o,c); target,assoc=later_observation(fixture,bank)
    model=dict(source_kind='user_assumed',source_ref='synthetic',fields=['rachis_arc_length_mm'],units={'rachis_arc_length_mm':'mm'},covariance=[[1]],numeric_tolerance=1e-9)
    result=pcg.update_forecast(bank,target,assoc,model)
    assert result['status']=='reweighted' and result['effective_sample_size']==pytest.approx(4)
    assoc['records'][0]['predicted_id']='nonexistent'
    assert pcg.update_forecast(bank,target,assoc,model)['status']=='update_incompatible'
    model['covariance']=[[0]]
    with pytest.raises(StudyError): pcg.update_forecast(bank,target,assoc,model)


def test_ambiguous_and_occluded_not_death(fixture):
    o,c=deterministic(fixture,stop=1); bank=pcg.sample_forecast(o,c); target,assoc=later_observation(fixture,bank)
    assoc['records']=[dict(status='occluded',predicted_id='L1',source_ref='synthetic')]
    # Empty new observation batch: non-detection contributes no negative evidence.
    manifest=read_json(target/'observations.json')
    for name,cols in (('observations',cg.OBS_COLUMNS),('axes',cg.AXIS_COLUMNS),('extents',cg.EXTENT_COLUMNS)):
        path=target/(name+'.csv'); pcg._csv(path,[],cols); manifest['tables'][name]['sha256']=file_hash(path)
    write_json(target/'observations.json',manifest)
    u=pcg.update_forecast(bank,target,assoc,None)
    assert len(u['bank']['trajectories'][0]['blocks'])==1
    assert u['bank']['trajectories'][0]['blocks'][0]['state_source']=='inferred_preexisting'


def test_evaluation_independence_missing_targets(fixture):
    o,c=deterministic(fixture,stop=1); bank=pcg.sample_forecast(o,c); target,assoc=later_observation(fixture,bank,7)
    plan=dict(train_plant_ids=['other_plant'],test_plant_ids=[o['plant_id']],split_provenance='synthetic frozen',interval_quantiles=[.1,.9],
        targets=[dict(plant_id=o['plant_id'],compound_leaf_id='L1',forecast_origin=o['observed_at'],target_at=assoc['observed_at'],association_status='confirmed')])
    e=pcg.evaluate_forecasts([bank],target,plan)
    assert e['metrics'] and e['status']=='evaluated_unaccepted'
    assert next(x['value'] for x in e['metrics'] if x['quantity']=='rachis_arc_length_mm' and x['metric']=='crps')==pytest.approx(0)
    assert len(e['baselines'])==2
    plan['train_plant_ids']=[o['plant_id']]
    with pytest.raises(StudyError): pcg.evaluate_forecasts([bank],target,plan)


def test_export_nulls_hashes_and_no_tissue(fixture):
    root,o,c=fixture; bank=pcg.sample_forecast(o,c); bank['summaries']=pcg.summarize_forecast(bank,dict(quantiles=[.1,.9]))
    out=pcg.export_run(bank,root/('export_'+uuid4().hex))
    manifest=read_json(out/'manifest.json')
    assert all(file_hash(out/name)==h for name,h in manifest['output_hashes'].items())
    data=rows(out/'block_states.csv'); assert all(r['optical_eligible']=='False' for r in data)
    assert any(r['supported_area_cm2']=='' for r in data)
    assert 'NaN' not in (out/'trajectory_parameters.json').read_text(encoding='utf-8')
    with pytest.raises(StudyError): pcg.export_run(bank,out)


def test_cli_extension_and_templates(fixture):
    root,_,_=fixture
    run=subprocess.run([sys.executable,'-X','utf8','-m','tools.compound_growth','probabilistic','--help'],capture_output=True,text=True)
    assert run.returncode==0 and 'forecast' in run.stdout
    out=pcg.templates(root/'blank')
    assert read_json(out/'model.json')['parameter_particles'] is None


def test_ambiguous_association_marginal_likelihood(fixture):
    o,c=deterministic(fixture,stop=1); bank=pcg.sample_forecast(o,c); target,assoc=later_observation(fixture,bank)
    assoc['records']=[dict(status='ambiguous',observed_id='L1',source_ref='synthetic',candidates=[
        dict(predicted_id='L1',probability=.4),dict(predicted_id='unknown',probability=.6)])]
    model=dict(source_kind='user_assumed',source_ref='synthetic',fields=['rachis_arc_length_mm'],units={'rachis_arc_length_mm':'mm'},covariance=[[1]],numeric_tolerance=1e-9)
    update=pcg.update_forecast(bank,target,assoc,model)
    assert update['status']=='reweighted'
    assert update['candidate_posteriors'][0]['candidates'][0]['posterior_probability']==pytest.approx(1)
    assert len({b['block_id'] for b in update['bank']['trajectories'][0]['blocks']})==len(update['bank']['trajectories'][0]['blocks'])
    assoc['records'][0]['candidates'][0]['probability']=None
    update=pcg.update_forecast(bank,target,assoc,model)
    assert update['parameter_update']=='unavailable'


def test_event_only_update_and_no_future_evidence(fixture):
    o,c=deterministic(fixture,wait=.25); bank=pcg.sample_forecast(o,c); target,assoc=later_observation(fixture,bank)
    model=dict(source_kind='user_assumed',source_ref='synthetic',fields=[],units={},covariance=[],numeric_tolerance=1e-9,
        events=[dict(parent_stem_id='stem',event_index=1,kind='interval',visibility='confirmed',last_absent_day=0,first_present_day=1)])
    assert pcg.update_forecast(bank,target,assoc,model)['status']=='reweighted'
    model['events'][0]['last_absent_day']=.5
    assert pcg.update_forecast(bank,target,assoc,model)['status']=='update_incompatible'
    model['events'][0]['first_present_day']=3
    with pytest.raises(StudyError,match='beyond update'): pcg.update_forecast(bank,target,assoc,model)


def test_joint_covariance_and_conditional_features(fixture):
    _,_,c=fixture; p=deepcopy(c['parameter_particles'][0]); p['coordinates']=[dict(name='azimuth_rad',unit='rad',transform='identity'),dict(name='elevation_rad',unit='rad',transform='identity')]
    p['families']={'joint':dict(mean=[0,0],features=['axis_length_mm'],standardization={'axis_length_mm':dict(center=10,scale=2)},
         coefficients=[[1],[2]],rho=.5,initial_covariance=[[1,.8],[.8,1]],innovation_covariance=[[1,.8],[.8,1]],constants={})}
    samples=[pcg._draw(p,'joint',{'axis_length_mm':12},np.zeros(2),None,pcg._rng(123,i))[0] for i in range(1000)]
    a=np.array([[s['azimuth_rad'],s['elevation_rad']] for s in samples])
    assert a.mean(axis=0)==pytest.approx([1,2],abs=.12)
    assert np.corrcoef(a.T)[0,1]>.7
    with pytest.raises(pcg.ScienceUnavailable): pcg._draw(p,'joint',{},np.zeros(2),None,pcg._rng(123))


def test_conditional_stop_and_external_fixed_light(fixture):
    o,c=deterministic(fixture); ap=c['parameter_particles'][0]['axes']['stem']
    ap.pop('stop_probability'); ap['stop_logit']=dict(intercept=100,coefficients={},standardization={})
    assert pcg.sample_forecast(o,c)['trajectories'][0]['events'][0]['event_state']=='stopped'
    c['light_features']=[dict(id='light1',plant_id=o['plant_id'],compound_leaf_id='L1',observed_at=o['observed_at'],area_basis_id='synthetic_patch',
        metric='absorbed_flux',unit='umol/s',backend='external_synthetic',source_ref='synthetic',value=2)]
    c['clock']=dict(kind='piecewise_linear_response',source_kind='user_assumed',source_ref='synthetic',input_metric='absorbed_flux',input_unit='umol/s',
        target='development_clock',equation_version='piecewise_linear-1',applicability='synthetic only',light_feature_id='light1',fixed_over_horizon=True,
        knots=[dict(value=0,multiplier=0),dict(value=4,multiplier=2)],intervals=[dict(start_day=0,end_day=30,input_value=2)])
    b=pcg.sample_forecast(o,c)
    assert b['light_used'] and not b['environment_used']
    c['clock']['input_unit']='umol/m2/s'
    with pytest.raises(StudyError,match='matching feature'): pcg.sample_forecast(o,c)


def test_frozen_run_tampering_is_detected(fixture):
    root,o,c=fixture; out=pcg.export_run(pcg.sample_forecast(o,c),root/('tamper_'+uuid4().hex))
    (out/'events.csv').write_text('corrupted\n',encoding='utf-8')
    with pytest.raises(StudyError,match='hash mismatch'): pcg._load_run(out)


def test_update_does_not_claim_new_measured_stem(fixture):
    o,c=deterministic(fixture,stop=1); b=pcg.sample_forecast(o,c); target,a=later_observation(fixture,b)
    u=pcg.update_forecast(b,target,a,None)
    assert u['next_origin']['axes']['stem']['points_mm'] is None
    assert u['bank']['trajectories'][0]['axes']['stem']['points_mm'] is not None
    with pytest.raises(StudyError,match='bounded continuation'): pcg.sample_forecast(u['next_origin'],u['bank']['config'])


def test_partial_output_does_not_claim_missing_environment_response(fixture):
    o,c=deterministic(fixture,stop=1)
    c['environment_scenario']['values']={'temperature_c':20}
    b=pcg.sample_forecast(o,c)
    assert not b['environment_used'] and b['environment_coupling']=='unavailable'
    c['clock']=dict(kind='piecewise_constant',source_kind='user_assumed',source_ref='synthetic',intervals=[dict(start_day=0,end_day=30,multiplier=2)])
    assert not pcg.sample_forecast(o,c)['environment_used']


def test_future_parameters_do_not_change_observed_geometry(fixture):
    o,c=deterministic(fixture); c['parameter_particles'][0]['families']['existing']['constants']['rotation_z_rad']['value']=3
    tr=pcg.sample_forecast(o,c)['trajectories'][0]
    assert pcg.decode_trajectory(tr,0)[0]['rachis_points_mm']==o['blocks'][0]['rachis_points_mm']
    assert np.linalg.norm(pcg.decode_trajectory(tr,7)[0]['direction_unit_xyz'])==pytest.approx(1)


def test_multiaxis_order_and_decode_without_rng(fixture,monkeypatch):
    o,c=deterministic(fixture)
    o['axes']['second']=deepcopy(o['axes']['stem']); a=o['axes']['second']; a['parent_stem_id']='second'
    a['points_mm']=(np.array(a['points_mm'])+[30,0,0]).tolist()
    c['parameter_particles'][0]['axes']['second']=deepcopy(c['parameter_particles'][0]['axes']['stem'])
    c['parameter_particles'][0]['axes']['second']['predecessor_id']=None
    first=pcg.sample_forecast(o,c)
    o['axes']=dict(reversed(list(o['axes'].items())))
    second=pcg.sample_forecast(o,c)
    assert first['trajectories'][0]['events']==second['trajectories'][0]['events']
    # Each trajectory can be evaluated out of sampling order with identical keyed randomness.
    assert pcg._trajectory(o,c,3)['events']==first['trajectories'][3]['events']
    def forbidden(*args,**kwargs): raise AssertionError('Decoder attempted RNG')
    monkeypatch.setattr(pcg,'_rng',forbidden)
    assert pcg.decode_trajectory(first['trajectories'][0],[7,14])


def test_new_observed_block_identity_and_horizon_count(fixture):
    o,c=deterministic(fixture,wait=.25); b=pcg.sample_forecast(o,c); target,assoc=later_observation(fixture,b)
    # A new observation without a supported predicted match remains explicitly unmatched.
    assoc['records']=[dict(observed_id='L1',status='unmatched',source_ref='synthetic')]
    u=pcg.update_forecast(b,target,assoc,None)
    assert u['associations'][0]['status']=='unmatched'
    summary=pcg.summarize_forecast(u['bank'],dict(quantiles=[.5],output_days=[0]))
    counts=[r for r in summary if r['quantity']=='new_block_count']
    assert len(counts)==1 and counts[0]['count']==0 and counts[0]['value']==1


def test_structure_hash_frame_and_attachment_guard(fixture):
    root,_,_=fixture; original=read_json(root/'inputs/structure.json'); oc=read_json(root/'inputs/origin.json')
    path=root/'inputs'/('bad_structure_'+uuid4().hex+'.json')
    bad=deepcopy(original); bad['frame_id']='other'; write_json(path,bad)
    with pytest.raises(StudyError,match='frame mismatch'): pcg.prepare_origin(root/'inputs/observations',path,oc)
    bad=deepcopy(original); bad['parent_axis_points']['sha256']='0'*64; write_json(path,bad)
    with pytest.raises(StudyError,match='hash mismatch'): pcg.prepare_origin(root/'inputs/observations',path,oc)
    oc['projection_tolerance_mm']=None
    origin=pcg.prepare_origin(root/'inputs/observations',root/'inputs/structure.json',oc)
    assert not origin['attachments']
    assert any(r['reason_code']=='projection_tolerance_unavailable_or_exceeded' for r in origin['availability'])


def test_canonical_tolerance_and_public_input_errors(fixture):
    _,o,c=fixture; c=deepcopy(c)
    tol=c['computation'].pop('numeric_tolerance'); c['computation']['numeric_tolerances']={'absolute':tol}
    assert pcg.sample_forecast(o,c)['status']=='assumption_conditioned'
    c['computation']['numeric_tolerance']=tol*2
    with pytest.raises(StudyError,match='Conflicting'): pcg.validate_model_config(c,o)
    with pytest.raises(StudyError): pcg.sample_forecast({}, {})
    with pytest.raises(StudyError): pcg.decode_trajectory({},[1])
