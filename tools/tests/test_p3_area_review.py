"""Synthetic boundary evidence only; no estimator accuracy or real fitting claim."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from tools import compound_growth as o
from tools import probabilistic_compound_growth as p
from tools import growth_calibration as g
from tools import growth_observation_evidence as e
from tools.growth_observation_options import weighted_anchor, _weight
from tools.leaf_light.common import BUILD, StudyError, read_json, write_json, file_hash, rows, digest
from tools.tests.test_probabilistic_compound_growth import later_observation


@pytest.fixture
def scene():
    root = BUILD / ('test_area_review_' + uuid4().hex)
    origin, config = p.synthetic_fixture(root/'inputs')
    config['computation']['sample_count'] = 2
    return root, origin, config


def claim(at, **extra):
    return dict(quantity='one_sided_physical_tissue', unit='cm2', scope='compound_leaf',
        method='SYNTHETIC_TISSUE', method_version='1', calibration_hash='a'*64,
        pose_hash='b'*64, partition_hash='c'*64, tissue_support_id='synthetic_patch',
        visibility_basis='complete_synthetic', capture_phase='synthetic_phase',
        canopy_placement_id='synthetic_place', identity_scope='cross_date_same_organ',
        identity_source_ref='SYNTHETIC_ONLY', tissue_evidence_status='synthetic_assumption',
        source_ref='synthetic', source_row_id=at, observed_at=at, **extra)


def manifest_claim(path, changes=None, *, identity=None):
    m = read_json(path)
    r = rows(path.parent / m['tables']['observations']['path'])[0]
    c = claim(r['observed_at']); c.update(changes or {})
    item = dict(plant_id=r['plant_id'], organ_id=r['compound_leaf_id'], session_id=r['session_id'], area=c)
    if identity: item['identity'] = identity
    m['observation_evidence'] = dict(schema=e.SCHEMA, records=[item])
    write_json(path, m)
    return m, item


def matched(scene, changes=None):
    root, origin, config = scene
    origin['blocks'][0]['observation_evidence'] = dict(area=claim(origin['observed_at']))
    bank = p.sample_forecast(origin, config)
    folder, assoc = later_observation(scene, bank)
    manifest_claim(folder/'observations.json', changes)
    return bank, folder, assoc


@pytest.mark.parametrize('field,value,reason', [
    ('quantity','projected_proxy','area_quantity_unsupported'),
    ('quantity','hull_diagnostic','area_quantity_unsupported'),
    ('quantity','area_A2_candidate','area_quantity_unsupported'),
    ('scope','whole_plant','area_scope_unsupported'),
    ('scope','leaflet','area_scope_unsupported'),
    ('tissue_evidence_status','unreviewed','area_tissue_evidence_unavailable'),
    ('identity_scope','within_ring','temporal_identity_unconfirmed'),
])
def test_wrong_area_is_retained_raw_but_not_used(scene, field, value, reason):
    bank, folder, assoc = matched(scene, {field:value})
    states, _ = o.load_history(folder/'observations.json')
    assert states[0]['supported_area_cm2'] is None
    assert states[0]['raw_observation_traits']['supported_area_cm2'] > 0
    assert states[0]['trait_unavailable']['supported_area_cm2'] == reason
    assert states[0]['eligible_state'] and states[0]['rachis_arc_length_mm'] > 0
    result = p.update_forecast(bank, folder, assoc, None)
    current = p.decode_trajectory(result['bank']['trajectories'][0], [0])[0]
    previous = p.decode_trajectory(bank['trajectories'][0], [2])[0]
    assert current['supported_area_cm2'] == previous['supported_area_cm2']
    assert any(x['reason_code']==reason and x['applied_displacement'] is None
               for x in result['reanchor_corrections'] if x['quantity']=='supported_area_cm2')


@pytest.mark.parametrize('field', ['method','method_version','calibration_hash','pose_hash',
    'partition_hash','visibility_basis','tissue_support_id','canopy_placement_id'])
def test_changed_method_support_does_not_apply_increment(scene, field):
    bank, folder, assoc = matched(scene, {field:'changed'})
    result = p.update_forecast(bank, folder, assoc, None)
    assert any(r['reason_code']=='area_method_or_support_changed' for r in result['reanchor_corrections'])
    assert all(r['applied_displacement'] is None for r in result['reanchor_corrections']
               if r['quantity']=='supported_area_cm2')


def test_supported_area_zero_and_source_row_preserved(scene):
    bank, folder, assoc = matched(scene)
    m = read_json(folder/'observations.json'); path=folder/'observations.csv'
    rr=rows(path); rr[0]['supported_area_cm2']=0
    p._csv(path,rr,o.OBS_COLUMNS); m['tables']['observations']['sha256']=file_hash(path)
    write_json(folder/'observations.json',m)
    result=p.update_forecast(bank,folder,assoc,None)
    state=p.decode_trajectory(result['bank']['trajectories'][0],[0])[0]
    assert state['supported_area_cm2']==0
    assert state['source_row']['csv_line']==2
    assert state['observation_evidence']['area']['method']=='SYNTHETIC_TISSUE'
    assert not state['validated_growth']


def test_real_legacy_area_missing_does_not_remove_axis(scene):
    path=scene[0]/'inputs/observations/observations.json'
    m=read_json(path); m['data_kind']='observed'; write_json(path,m)
    state=o.load_history(path)[0][0]
    assert state['supported_area_cm2'] is None and state['eligible_state']
    assert state['trait_unavailable']['supported_area_cm2']=='area_evidence_missing'


def test_unsigned_direction_does_not_erase_valid_length_likelihood(scene):
    bank,folder,assoc=matched(scene)
    path=folder/'observations.json'; m=read_json(path)
    m['observation_evidence']['records'][0]['direction']={'quantity':'unsigned_normal_axis'}
    write_json(path,m)
    model=dict(source_kind='user_assumed',source_ref='SYNTHETIC ONLY',
        fields=['rachis_arc_length_mm','direction_tangent_1_rad'],
        units={'rachis_arc_length_mm':'mm','direction_tangent_1_rad':'rad'},
        covariance=[[1,.1],[.1,1]],numeric_tolerance=1e-9)
    result=p.update_forecast(bank,folder,assoc,model)
    assert result['status']=='reweighted'
    assert result['discrepancies'][0]['fields']==['rachis_arc_length_mm']
    assert result['trait_diagnostics'][0]['reason_code']=='direction_quantity_unsupported'
    state=p.decode_trajectory(result['bank']['trajectories'][0],[0])[0]
    assert state['rachis_arc_length_mm'] is not None
    assert state['direction_unit_xyz']==p.decode_trajectory(bank['trajectories'][0],[2])[0]['direction_unit_xyz']


def test_within_ring_identity_does_not_update_bank(scene):
    bank,folder,assoc=matched(scene)
    assoc['records'][0]['identity_scope']='within_ring'
    result=p.update_forecast(bank,folder,assoc,None)
    assert result['reason']=='temporal_identity_unconfirmed' and result['bank']==bank


@pytest.mark.parametrize('kind', sorted(e.NON_VARIANCE))
def test_diagnostic_not_variance(kind):
    record=dict(source_kind='measured',source_ref='synthetic',evidence_kind=kind,
        identifiable=True,unit='mm^2',variance_state=1,variance_measurement=1)
    w,reason=_weight(dict(reanchor_covariance=dict(mode='diagonal_variance',traits={'rachis_arc_length_mm':record})), 'rachis_arc_length_mm')
    assert w is None and reason=='reanchor_variance_quantity_unsupported'


def test_duplicate_canopy_source_and_wrong_plant(scene):
    root=scene[0]; source=root/'synthetic.csv'; source.write_text('id,value\nr1,1\n')
    records=[dict(plant_id='P1',compound_leaf_id='L1',session_id='s'),
             dict(plant_id='P2',compound_leaf_id='L2',session_id='s')]
    meta=dict(schema=e.SCHEMA,sources={'s':dict(path=str(source),sha256=file_hash(source))},records=[
        dict(plant_id=r['plant_id'],organ_id=r['compound_leaf_id'],session_id='s',
             area=dict(source_ref='s',source_row_id='r1')) for r in records])
    with pytest.raises(StudyError,match='reused'):
        e.attach_evidence(records,meta)
    meta['records']=meta['records'][:1]; meta['records'][0]['plant_id']='WRONG'
    with pytest.raises(StudyError,match='wrong-plant'):
        e.attach_evidence(records,meta)


def area_calibration(root):
    obs,plan,treatments,registry,ep=g.synthetic_fixture(root/'calibration',replicates=2)
    plan['targets'][0]['unit']='cm2'; plan['parameters']['D']['unit']='cm2'
    m=read_json(obs); path=obs.parent/'observations.csv'; rr=rows(path)
    for r in rr: r['unit']='cm2'
    g._csv(path,rr,tuple(rr[0])); m['observations']['sha256']=file_hash(path)
    m['observation_evidence']=dict(schema=e.SCHEMA,records=[dict(plant_id=r['plant_id'],organ_id=r['organ_id'],
        record_id=r['record_id'],area=claim(r['observed_at']),anchor_area=claim(r['origin_at'])) for r in rr])
    for meta,r in zip(m['observation_evidence']['records'],rr):
        meta['area']['capture_phase']=r['capture_phase']
        meta['anchor_area']['capture_phase']=r['capture_phase']
    write_json(obs,m)
    return obs,plan,treatments,registry,ep


def test_calibration_comparison_gate_and_supported_case(scene):
    obs,plan,tr,ev,ep=area_calibration(scene[0])
    assert g.audit_calibration_data(obs,tr,plan)['status']=='eligible'
    m=read_json(obs); m['observation_evidence']['records'][0]['area']['method_version']='2'
    write_json(obs,m)
    audit=g.audit_calibration_data(obs,tr,plan)
    assert not audit['eligible_targets']
    assert 'area_method_or_support_changed' in {r['reason_code'] for r in audit['missing_evidence']}
    result=g.fit_growth_parameters(obs,ev,plan,tr)
    assert result['status']=='unavailable'  # Audit refuses before fitting.


def test_cli_update_exports_trait_rejection(scene):
    bank,folder,assoc=matched(scene, {'quantity':'projected_proxy'})
    root=scene[0]; write_json(root/'bank.json',bank); write_json(root/'assoc.json',assoc)
    out=root/'cli_update'
    run=subprocess.run([sys.executable,'-X','utf8','-m','tools.probabilistic_compound_growth','update',
        '--run',str(root/'bank.json'),'--observations',str(folder),'--associations',str(root/'assoc.json'),
        '--out',str(out)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    result=read_json(out/'update.json')
    assert any(r['reason_code']=='area_quantity_unsupported' for r in result['reanchor_corrections'])
    for name,h in read_json(out/'manifest.json')['output_hashes'].items():
        assert file_hash(out/name)==h


def test_parameter_validation_refuses_proxy_without_running_fitter(scene):
    obs,plan,tr,registry,ep=area_calibration(scene[0])
    # Explicit synthetic parameter fixture, not a fitted biological parameter set.
    values={'D':24.,'k':.12,'light_beta':.25}
    particles=[dict(weight=1.,values=values)]
    frozen=dict(schema_version=g.SCHEMA,particles=particles,values=values,fit_plan=plan,
        plan_hash=digest(plan),parameter_set_id=digest([plan,values,particles]),accepted_for_domain=False,
        eligible_targets=['length'],training_record_ids=[],training_plants=plan['split']['train_plants'],
        training_units=plan['split']['train_units'],training_observed_until='2026-01-31T00:00:00+00:00',
        data_kind='synthetic')
    ep['plan_hash']=digest(plan)
    m=read_json(obs)
    for r in m['observation_evidence']['records']:
        r['area']['quantity']='area_A1_whole_plant_estimate'
    write_json(obs,m)
    result=g.validate_parameter_set(frozen,obs,ep)
    assert result['status']=='unavailable'
    assert all(r['value'] is None and r['reason']=='area_quantity_unsupported' for r in result['validation'])
    out=g.export_calibration(result,scene[0]/'validation_export')
    assert read_json(out/'validation_observation_evidence.json')


def test_real_area_and_single_time_cannot_enter_fit(scene):
    obs,plan,tr,registry,ep=area_calibration(scene[0])
    m=read_json(obs); m['data_kind']='observed'; m.pop('observation_evidence')
    plan['review']['status']='reviewed'; plan['targets'][0]['effect_interpretation']='observational_association'
    write_json(obs,m)
    audit=g.audit_calibration_data(obs,tr,plan)
    assert not audit['eligible_targets']
    assert 'area_evidence_missing' in {r['reason_code'] for r in audit['missing_evidence']}
    m['data_kind']='synthetic'; path=obs.parent/'observations.csv'
    rr=[r for r in rows(path) if float(r['elapsed_days'])==7]
    g._csv(path,rr,tuple(rr[0])); m['observations']['sha256']=file_hash(path); write_json(obs,m)
    assert 'endpoint_only_cannot_identify_dynamics' in {r['reason_code'] for r in g.audit_calibration_data(obs,tr,plan)['missing_evidence']}


def test_observed_variance_needs_repeat_evidence():
    r=dict(source_kind='measured',source_ref='study',unit='mm^2',identifiable=True,
           variance_state=1,variance_measurement=1)
    options=dict(observation_data_kind='observed',reanchor_covariance=dict(mode='diagonal_variance',traits={'rachis_arc_length_mm':r}))
    assert _weight(options,'rachis_arc_length_mm')==(None,'reanchor_variance_evidence_missing')
    r.update(evidence_kind='trait_measurement_variance',repeat_measurement_source_ref='independent_repeats')
    assert _weight(options,'rachis_arc_length_mm')==(.5,None)


def test_real_source_integrity_and_geometry_only_origin(scene):
    root,origin,config=scene
    path=root/'inputs/observations/observations.json'
    m,item=manifest_claim(path)
    source=root/'independent_synthetic_reference.csv'; source.write_text('row,value\nr1,2\n')
    m['data_kind']='observed'
    m['observation_evidence']['sources']={'synthetic':dict(path=str(source),sha256=file_hash(source))}
    item=m['observation_evidence']['records'][0]
    item['area']['tissue_evidence_status']='reviewed'
    write_json(path,m)
    state=o.load_history(path)[0][0]
    assert state['supported_area_cm2']==2 and state['observation_evidence']['area']['source_verified']
    assert str(source.resolve()) in state['provenance']
    source.write_text('changed')
    with pytest.raises(StudyError,match='hash mismatch'): o.load_history(path)
    # A caller cannot bypass area gating by supplying a prepared origin directly.
    clean_origin,clean_config=p.synthetic_fixture(root/'direct_api')
    clean_config['computation']['sample_count']=2
    clean_origin['blocks'][0]['data_kind']='observed'
    bank=p.sample_forecast(clean_origin,clean_config)
    assert p.decode_trajectory(bank['trajectories'][0],[0])[0]['supported_area_cm2'] is None


def test_recent_change_area_discontinuity_is_unavailable(scene):
    bank,folder,assoc=matched(scene, {'method':'changed'})
    current=o.load_history(folder/'observations.json')[0][0]
    previous=deepcopy(bank['origin']['blocks'][0])
    result=o.forecast_recent_change([previous,current],1)
    assert result['supported_area_cm2'] is None
    assert 'area_method_or_support_changed' in result['qc_flags']
    assert result['rachis_arc_length_mm'] is not None


def test_calibration_cli_audits_proxy_without_fitting(scene):
    obs,plan,tr,registry,ep=area_calibration(scene[0])
    m=read_json(obs); m['observation_evidence']['records'][0]['area']['scope']='whole_plant'; write_json(obs,m)
    root=scene[0]; write_json(root/'plan.json',plan); write_json(root/'treatments.json',tr)
    out=root/'cli_audit'
    run=subprocess.run([sys.executable,'-X','utf8','-m','tools.growth_calibration','audit',
        '--observations',str(obs),'--treatments',str(root/'treatments.json'),
        '--plan',str(root/'plan.json'),'--out',str(out)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    audit=read_json(out/'data_audit.json')
    assert audit['status']=='unavailable'
    assert 'area_scope_unsupported' in {r['reason_code'] for r in audit['missing_evidence']}
    assert audit['observation_evidence']


@pytest.mark.parametrize('quantity', ['unsigned_normal_axis','top_ring_ratio','mean_inclination'])
def test_unmapped_direction_is_per_trait_unavailable(scene, quantity):
    path=scene[0]/'inputs/observations/observations.json'
    m,item=manifest_claim(path)
    m['observation_evidence']['records'][0]['direction']={'quantity':quantity}
    write_json(path,m)
    state=o.load_history(path)[0][0]
    assert state['direction_unit_xyz'] is None and state['rachis_points_mm'] is None
    assert state['rachis_arc_length_mm']>0 and state['supported_area_cm2']==2
    assert state['raw_observation_traits']['direction_unit_xyz']


@pytest.mark.parametrize('change', ['merged','split','canopy_placement'])
def test_merge_split_needs_separate_lineage_model(scene,change):
    bank,folder,assoc=matched(scene)
    path=folder/'observations.json'; m=read_json(path)
    m['observation_evidence']['records'][0]['identity']={'scope':'cross_date_same_organ','change':change}
    write_json(path,m)
    result=p.update_forecast(bank,folder,assoc,None)
    assert result['reason']=='organ_lineage_mapping_unsupported' and result['bank']==bank


def test_renaming_needs_exact_lineage_and_plant(scene):
    bank,folder,assoc=matched(scene)
    path=folder/'observations.json'; m=read_json(path)
    for name,entry in m['tables'].items():
        table=folder/entry['path']; rr=rows(table)
        for r in rr: r['compound_leaf_id']='renamed'
        p._csv(table,rr,tuple(rr[0])); entry['sha256']=file_hash(table)
    m['observation_evidence']['records'][0]['organ_id']='renamed'; write_json(path,m)
    assoc['records'][0]['observed_id']='renamed'
    assert p.update_forecast(bank,folder,assoc,None)['reason']=='organ_lineage_evidence_missing'
    assoc['records'][0]['lineage']=dict(kind='same_organ_rename',previous_id='L1',observed_id='renamed',
        plant_id=bank['origin']['plant_id'],source_ref='SYNTHETIC same-organ review')
    result=p.update_forecast(bank,folder,assoc,None)
    assert result['status']=='reanchored_without_parameter_update'
    assert sum(b['source_compound_leaf_id']=='renamed' for b in result['bank']['trajectories'][0]['blocks'])==1
    assoc['plant_id']='another_plant'
    with pytest.raises(StudyError,match='plant differs'): p.update_forecast(bank,folder,assoc,None)


def test_malformed_evidence_schema_is_not_missing_science(scene):
    path=scene[0]/'inputs/observations/observations.json'; m=read_json(path)
    m['observation_evidence']={'schema':'unknown'}; write_json(path,m)
    with pytest.raises(StudyError,match='schema'): o.load_history(path)


def test_changed_anchor_together_still_splits_calibration_series(scene):
    obs,plan,tr,ev,ep=area_calibration(scene[0]); m=read_json(obs)
    first=m['observation_evidence']['records'][0]
    for key in ('area','anchor_area'): first[key]['partition_hash']='changed'
    write_json(obs,m)
    assert 'area_method_or_support_changed' in {r['reason_code'] for r in g.audit_calibration_data(obs,tr,plan)['missing_evidence']}


def test_first_observed_future_block_does_not_require_past_measured_method(scene):
    state=deepcopy(scene[1]['blocks'][0])
    state['observation_evidence']={'area':claim(state['observed_at'])}
    pred=deepcopy(state); pred.pop('observation_evidence'); pred.pop('data_kind')
    pred.update(state_source='predicted_future',source_compound_leaf_id=None)
    state['supported_area_cm2']=3
    result,audit=weighted_anchor(pred,state,{})
    assert result['supported_area_cm2']==3
    assert next(r for r in audit if r['quantity']=='supported_area_cm2')['reason_code'] is None


def test_repeatability_tag_cannot_supply_growth_series(scene):
    obs,plan,tr,ev,ep=area_calibration(scene[0]); m=read_json(obs)
    for r in m['observation_evidence']['records']: r['measurement_role']='repeatability'
    write_json(obs,m)
    assert 'repeatability_or_single_capture_is_not_growth' in {r['reason_code'] for r in g.audit_calibration_data(obs,tr,plan)['missing_evidence']}


def test_other_plant_only_does_not_advance_origin(scene):
    bank,folder,assoc=matched(scene)
    path=folder/'observations.json'; m=read_json(path)
    for entry in m['tables'].values():
        table=folder/entry['path']; rr=rows(table)
        for r in rr: r['plant_id']='another_plant'
        p._csv(table,rr,tuple(rr[0])); entry['sha256']=file_hash(table)
    m['observation_evidence']['records'][0]['plant_id']='another_plant'; write_json(path,m)
    assoc['records']=[]
    result=p.update_forecast(bank,folder,assoc,None)
    assert result['status']=='no_new_observations' and result['bank']==bank


def test_unavailable_direction_recent_change_retains_scalar_prediction(scene):
    bank,folder,assoc=matched(scene)
    current=o.load_history(folder/'observations.json')[0][0]
    previous=deepcopy(bank['origin']['blocks'][0])
    current['observation_evidence']['direction']={'quantity':'unsigned_normal_axis'}
    e.audit_state(current)
    result=o.forecast_recent_change([previous,current],1)
    assert result['direction_unit_xyz'] is None and result['rachis_points_mm'] is None
    expected=current['rachis_arc_length_mm']+(current['rachis_arc_length_mm']-previous['rachis_arc_length_mm'])/2
    assert result['rachis_arc_length_mm']==pytest.approx(expected)
