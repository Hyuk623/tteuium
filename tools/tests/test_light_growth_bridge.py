"""Mathematical and consumer checks; synthetic results do not validate crop physics."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools import light_growth_bridge as bridge
from tools.leaf_light.common import StudyError, read_json, write_json, file_hash, write_rows


def sample(q=100., weight=.02, fixture='LED', sid='s', snapshot='g'):
    return dict(run_id='r', scenario_id='scenario', geometry_snapshot_id=snapshot,
        plant_instance_id='instance', source_plant_id='source', session_id='session',
        compound_id='compound', time_step_id='full_output', backend='direct', replicate='deterministic',
        sample_id=sid, organ_id='organ', leaflet_id='leaflet', fixture_id=fixture,
        quadrature_area_m2=weight, normal_side_ppfd_umol_m2_s=q,
        opposite_side_ppfd_umol_m2_s=0. if q is not None else None,
        received_ppfd_umol_m2_s=q, absorbed_ppfd_umol_m2_s=.8*q if q is not None else None,
        area_basis_id='basis')


def timing(end='2026-10-03T12:00:00+09:00'):
    return dict(start_at='2026-10-03T00:00:00+09:00', end_at=end, max_schedule_minutes=4000,
        snapshots=[dict(geometry_snapshot_id='g', valid_from='2026-10-03T00:00:00+09:00',
            valid_until=end, geometry_mode='held_current_geometry_scenario')])


def schedule(segments=None):
    return dict(timezone='Asia/Seoul', provenance={'source':'synthetic'}, fixed_optics_beam_spectrum=True,
        fixtures={'LED':segments if segments is not None else [dict(start_hhmm='00:00', end_hhmm='24:00', output_fraction=1.)]})


def dose(data, sched=None, interval=None):
    temporal = bridge.integrate_light_schedule(data, sched or schedule(), interval or timing())
    features = bridge.export_compound_light_features([], [], temporal, {})
    return temporal, bridge.integrate_dose(features, temporal)


def test_area_weighted_flux_quantiles_and_missingness():
    a = sample(q=100, weight=1, sid='a'); b = sample(q=0, weight=9, sid='b')
    result = bridge.aggregate_samples([a,b])
    assert result['received_umol_s'] == 100
    assert result['received_ppfd_umol_m2_s'] == 10
    assert result['received_p50_umol_m2_s'] == 0
    b['received_ppfd_umol_m2_s'] = None
    result = bridge.aggregate_samples([a,b])
    assert result['received_umol_s'] is None
    assert result['received_supported_subtotal_umol_s'] == 100
    with pytest.raises(StudyError, match='duplicate'):
        bridge.aggregate_samples([a,a])
    with pytest.raises(StudyError, match='positive_metric'):
        bridge.aggregate_samples([dict(a,quadrature_area_m2=None)])


def angular(qs, vectors):
    membership=[dict(sample_id='s',entity_id='c',quadrature_area_m2=2.,expected_paths=[['f',str(i)] for i in range(len(qs))])]
    paths=[dict(sample_id='s',fixture_id='f',path_id=str(i),incident_ppfd_umol_m2_s=q,
                arrival_unit_grow_xyz=u) for i,(q,u) in enumerate(zip(qs,vectors))]
    return bridge.compute_directional_features(paths,membership,{'c':{'grow':np.eye(3)}}), paths, membership


def test_single_asymmetric_opposing_and_zero_sources():
    result, _, _ = angular([3.], [[0,0,1]])
    assert result[0]['arrival_flux_umol_s'] == 6
    assert result[0]['dominant_arrival_z'] == 1
    result, _, _ = angular([3.,1.], [[1,0,0],[-1,0,0]])
    assert result[0]['directionality'] == .5
    result, _, _ = angular([3.,3.], [[1,0,0],[-1,0,0]])
    assert result[0]['direction_reason'] == 'direction_cancellation'
    assert result[0]['dominant_arrival_x'] is None
    assert result[0]['arrival_B_xx_umol_s'] == 12
    result, _, _ = angular([0.], [None])
    assert result[0]['arrival_flux_umol_s'] == 0
    assert result[0]['directionality'] is None


def test_angular_missing_paths_and_unknown_are_distinct():
    result, paths, members = angular([None,3.], [None,[0,0,1]])
    assert result[0]['direction_reason'] == 'unknown_path_contribution'
    with pytest.raises(StudyError,match='missing_angular'):
        bridge.compute_directional_features(paths[:1],members,{})
    with pytest.raises(StudyError,match='duplicate_or_foreign'):
        bridge.compute_directional_features(paths+paths,members,{})


def test_transform_points_vectors_and_second_moment_roundtrip():
    placement=dict(plant_id='p',board_origin_grow_mm=dict(value=[10,20,30],status='assumed',source='test'),
        board_yaw_deg=dict(value=90,status='assumed',source='test'),posture_since_capture='unchanged_checked')
    t=bridge.rigid_transform(placement)
    forward=np.array(t['T_board_to_grow']); inv=np.array(t['T_grow_to_board'])
    point=np.array([5,6,7,1]); np.testing.assert_allclose(inv@forward@point,point,atol=1e-10)
    m=np.array([2,0,0]); b=np.diag([2,0,0])
    r=bridge.transform_moments(2,m,b,forward[:3,:3])
    assert r['arrival_M_y_umol_s'] == pytest.approx(2)
    assert r['arrival_B_yy_umol_s'] == pytest.approx(2)
    with pytest.raises(StudyError,match='unsupported_placement'):
        bridge.rigid_transform(dict(placement,scale=2))


def test_constant_12h_dose_units_and_not_dli():
    temporal, rows = dose([sample()])
    assert len(temporal['intervals']) == 1
    assert len(rows) == 8  # four hierarchy levels, fixture and all
    for row in rows:
        assert row['incident_dose_mol_m2'] == pytest.approx(4.32)
        assert row['absorbed_dose_mol_m2'] == pytest.approx(3.456)
        assert row['absorbed_photons_mol'] == pytest.approx(3.456*.02)
        assert row['complete_local_day'] is False
        assert row['dli_mol_m2_day'] is None


def test_schedule_dimming_midnight_blackout_and_missing():
    s=schedule([dict(start_hhmm='22:00',end_hhmm='02:00',output_fraction=.5)])
    _, rows=dose([sample()],s,timing('2026-10-04T00:00:00+09:00'))
    assert rows[0]['incident_dose_mol_m2'] == pytest.approx(.72)
    assert rows[0]['complete_local_day']
    _, rows=dose([sample()],schedule([dict(start_hhmm='00:00',end_hhmm='24:00',output_fraction=0.)]))
    assert rows[0]['incident_dose_mol_m2'] == 0
    missing=schedule(); missing['fixtures']['LED']=None
    _, rows=dose([sample()],missing)
    assert rows[0]['incident_dose_mol_m2'] is None
    assert rows[0]['covered_seconds'] == 0
    with pytest.raises(StudyError,match='empty_schedule'):
        dose([sample()],schedule([]))


def test_fixture_schedules_and_native_restriction():
    s=schedule(); s['fixtures']['other']=[dict(start_hhmm='00:00',end_hhmm='06:00',output_fraction=.5)]
    _,rows=dose([sample(),sample(q=200,fixture='other')],s)
    allrow=next(r for r in rows if r['fixture_id']=='all')
    assert allrow['incident_dose_mol_m2'] == pytest.approx(6.48)
    native=dict(sample(fixture='all'),backend='native')
    temporal=bridge.integrate_light_schedule([native],s,timing())
    assert temporal['samples'][0]['received_ppfd_umol_m2_s'] is None


def test_geometry_changes_integrate_flux_and_keep_gaps():
    interval=timing(); interval['snapshots'][0]['valid_until']='2026-10-03T06:00:00+09:00'
    interval['snapshots'].append(dict(geometry_snapshot_id='g2',valid_from='2026-10-03T06:00:00+09:00',
        valid_until=interval['end_at'],geometry_mode='observed'))
    _,rows=dose([sample(weight=1),sample(weight=2,snapshot='g2')],interval=interval)
    assert rows[0]['incident_dose_mol_m2'] == pytest.approx(4.32)
    assert rows[0]['incident_photons_mol'] == pytest.approx(6.48)
    interval['snapshots'][1]['valid_from']='2026-10-03T07:00:00+09:00'
    temporal,rows=dose([sample(weight=1),sample(weight=2,snapshot='g2')],interval=interval)
    assert len(temporal['gaps'])==1
    assert rows[0]['incident_dose_mol_m2'] is None
    assert rows[0]['incident_supported_dose_mol_m2'] == pytest.approx(3.96)


def test_schedule_conflict_and_budget_rejection():
    s=schedule([dict(start_hhmm='00:00',end_hhmm='12:00',output_fraction=1),
        dict(start_hhmm='06:00',end_hhmm='18:00',output_fraction=1)])
    with pytest.raises(StudyError,match='overlapping_fixture'):
        dose([sample()],s)
    t=timing(); t['max_schedule_minutes']=10
    with pytest.raises(StudyError,match='schedule_scan_budget'):
        dose([sample()],interval=t)


def test_spatial_export_matches_actual_full_scene(tmp_path):
    from tools.hierarchical_light_demo import synthetic_inputs
    from tools.hierarchical_light import prepare_subset_cases, calculate_direct
    source=synthetic_inputs(tmp_path/'inputs')
    prepare_subset_cases(source,tmp_path/'prepared')
    calculate_direct(tmp_path/'prepared',tmp_path/'legacy')
    result=bridge.export_spatial_light(tmp_path/'prepared',tmp_path/'legacy',tmp_path/'spatial',
        snapshot=dict(geometry_snapshot_id='g',board_frame_ids={'P1':'board_P1','P2':'board_P2'}),
        run_id='synthetic',max_receiver_emitter_pairs=100000)
    assert result['scalar_parity']
    assert len(result['samples'])==64
    for row in result['samples']:
        assert row['normal_side_ppfd_umol_m2_s']+row['opposite_side_ppfd_umol_m2_s'] == pytest.approx(row['received_ppfd_umol_m2_s'])
        assert row['normal_convention']=='mesh_normal_no_botanical_side_claim'
    assert read_json(tmp_path/'spatial'/'spatial_manifest.json')['backend']=='direct'


def make_request(tmp_path):
    from tools.hierarchical_light_demo import synthetic_inputs
    from tools.hierarchical_light import prepare_subset_cases, calculate_direct
    source=synthetic_inputs(tmp_path/'inputs')
    prepare_subset_cases(source,tmp_path/'prepared')
    calculate_direct(tmp_path/'prepared',tmp_path/'legacy')
    t=timing(); snapshot=t['snapshots'][0]
    snapshot.update(prepared_run='prepared',full_scene_results='legacy',
        observed_at=t['start_at'],board_frame_ids={'P1':'board_P1','P2':'board_P2'})
    s=schedule(); s['fixtures']['synthetic_LED']=s['fixtures'].pop('LED')
    request=dict(schema_version='light-growth-1',run_id='synthetic_run',snapshots=[snapshot],
        interval={k:t[k] for k in ('start_at','end_at')},schedule=s,
        limits=dict(max_transport_calls=2,max_receiver_emitter_pairs=100000,max_schedule_minutes=4000))
    write_json(tmp_path/'request.json',request)
    return tmp_path/'request.json'


def test_complete_direct_package_and_split(tmp_path):
    request=make_request(tmp_path)
    audit=bridge.audit_growth_light_inputs(request)
    assert audit['input_ready'],audit
    bridge.build_package(request,tmp_path/'package')
    check=bridge.validate_growth_light_package(tmp_path/'package')
    assert check['valid'],check
    bridge.split_canopy_results(tmp_path/'package','P1',tmp_path/'split')
    check=bridge.validate_growth_light_package(tmp_path/'split')
    assert check['valid'],check
    assert read_json(tmp_path/'split'/'package.json')['context_geometry_hashes']==read_json(tmp_path/'package'/'package.json')['context_geometry_hashes']


def add_observations(tmp_path,request_path):
    from tools.compound_growth import OBS_COLUMNS,AXIS_COLUMNS,EXTENT_COLUMNS
    request=read_json(request_path)
    row=dict(plant_id='P1',compound_leaf_id='reviewed_C1',session_id='synthetic_session',observed_at=request['interval']['start_at'],
        parent_stem_id='stem',identity_status='confirmed',review_source='synthetic reviewed test',geometry_status='observed_axis',
        development_state='expanded',first_observed_at=request['interval']['start_at'],supported_area_cm2=1604.,
        area_basis_id='reviewed_metric_support',estimated_total_area_cm2=None,transverse_x=0.,transverse_y=1.,transverse_z=0.)
    write_rows(tmp_path/'observations.csv',[row],OBS_COLUMNS)
    axes=[dict(plant_id='P1',compound_leaf_id='reviewed_C1',session_id='synthetic_session',station=i,x_mm=x,y_mm=0.,z_mm=0.) for i,x in ((0,-200.),(1,200.))]
    write_rows(tmp_path/'axes.csv',axes,AXIS_COLUMNS); write_rows(tmp_path/'extents.csv',[],EXTENT_COLUMNS)
    tables={name:dict(path=name+'.csv',sha256=file_hash(tmp_path/(name+'.csv'))) for name in ('observations','axes','extents')}
    write_json(tmp_path/'history.json',dict(schema='compound-observations-1',data_kind='synthetic',reference_status='synthetic',
        frame_id='board_P1',coordinate_frame='board_mm',frame_stability='confirmed',frame_evidence='synthetic',tables=tables))
    write_json(tmp_path/'association_evidence.json',dict(kind='synthetic_review'))
    request.update(compound_history='history.json',associations=[dict(geometry_snapshot_id='g',plant_instance_id='P1',session_id='synthetic_session',
        compound_id='compound_1',compound_leaf_id='reviewed_C1',review_status='reviewed',evidence_path='association_evidence.json',
        evidence_sha256=file_hash(tmp_path/'association_evidence.json'),geometry_sha256=file_hash(tmp_path/'prepared'/'leaf_surfaces.csv'),
        area_basis_id='reviewed_metric_support',supported_area_m2=.1604,region_partition=dict(proximal_distal_boundary_mm=200.))])
    write_json(request_path,request)


def test_reviewed_observed_direction_area_and_regions(tmp_path):
    request=make_request(tmp_path); add_observations(tmp_path,request)
    bridge.build_package(request,tmp_path/'package')
    check=bridge.validate_growth_light_package(tmp_path/'package')
    assert check['valid'],check
    from tools.light_growth_consumer import load_tables
    tables=load_tables(tmp_path/'package')
    selected=[r for r in tables['compound_light_features.csv'] if r['level']=='compound' and r['compound_leaf_id']=='reviewed_C1' and r['time_step_id']=='full_output' and r['fixture_id']=='all']
    board=next(r for r in selected if r['quantity_frame']=='board')
    assert board['observed_rachis_x']==1.
    assert board['supported_area_cm2']==pytest.approx(1604.)
    left=next(r for r in selected if r['region_id']=='left'); right=next(r for r in selected if r['region_id']=='right')
    assert left['supported_area_m2']+right['supported_area_m2']==pytest.approx(board['supported_area_m2'])


@pytest.mark.parametrize('field,value,message',[
    ('area_basis_id','wrong','area_basis'),('geometry_sha256','wrong','geometry'),
    ('supported_area_m2',.5,'supported_area'),('review_status','pending','reviewed_association')])
def test_rejects_incompatible_review_associations(tmp_path,field,value,message):
    request=make_request(tmp_path); add_observations(tmp_path,request)
    raw=read_json(request); raw['associations'][0][field]=value; write_json(request,raw)
    with pytest.raises(StudyError,match=message): bridge.build_package(request,tmp_path/'package')


def test_independent_consumer_detects_missing_time_sample_after_rehash(tmp_path):
    from tools.light_growth_consumer import load_tables
    request=make_request(tmp_path); bridge.build_package(request,tmp_path/'package')
    folder=tmp_path/'package'; tables=load_tables(folder)
    rows=tables['light_samples.csv']; rows.pop()
    write_rows(folder/'light_samples.csv',rows,[c['name'] for c in bridge.SCHEMA['tables']['light_samples.csv']['columns']])
    package=read_json(folder/'package.json'); package['artifact_hashes']['light_samples.csv']=file_hash(folder/'light_samples.csv'); write_json(folder/'package.json',package)
    check=bridge.validate_growth_light_package(folder)
    assert not check['valid'] and 'missing_or_extra_time_samples' in check['errors'][0]


def test_native_scalar_package_retains_replicates_without_spatial_claims(tmp_path):
    from tools.hierarchical_light_demo import synthetic_inputs
    from tools.hierarchical_light import prepare_subset_cases, write_report
    from tools.light_growth_consumer import load_tables
    source=synthetic_inputs(tmp_path/'inputs',groups=())
    manifest=prepare_subset_cases(source,tmp_path/'prepared',backend='native')
    assert manifest['status']=='prepared'
    # Explicit test-only collector responses, no native execution or physical comparison.
    runs=[]
    for replicate,q in [('test_seed_1',100.),('test_seed_2',120.)]:
        values={case['case_id']:{tid:{'all':dict(received=q*t['area_m2'],absorbed=.8*q*t['area_m2'])}
            for tid,t in manifest['targets'].items() if set(t['triangles']).issubset(case['retained'])} for case in manifest['cases']}
        runs.append(dict(replicate=replicate,seed=1 if q==100 else 2,values=values))
    manifest['source_hashes'][str((tmp_path/'prepared'/'manifest.json').resolve())]=file_hash(tmp_path/'prepared'/'manifest.json')
    write_report(manifest,runs,tmp_path/'legacy')
    t=timing(); s=schedule(); s['fixtures']['synthetic_LED']=s['fixtures'].pop('LED')
    t['snapshots'][0].update(prepared_run='prepared',full_scene_results='legacy',board_frame_ids={'P1':'board_P1'})
    request=dict(schema_version='light-growth-1',run_id='native_test_only',snapshots=t['snapshots'],schedule=s,
        interval={k:t[k] for k in ('start_at','end_at')},limits=dict(max_transport_calls=1,max_receiver_emitter_pairs=10000,max_schedule_minutes=4000))
    write_json(tmp_path/'request.json',request)
    bridge.build_package(tmp_path/'request.json',tmp_path/'package')
    check=bridge.validate_growth_light_package(tmp_path/'package'); assert check['valid'],check
    tables=load_tables(tmp_path/'package')
    assert tables['light_samples.csv']==[]
    assert len(tables['light_intervals.csv'])==2
    assert sorted({r['incident_dose_mol_m2'] for r in tables['light_dose.csv']})==pytest.approx([4.32,5.184])
    for row in tables['compound_light_features.csv']:
        assert row['normal_side_ppfd_umol_m2_s'] is None
        assert row['received_p50_umol_m2_s'] is None
        assert row['arrival_flux_umol_s'] is None


def test_dst_day_and_subminute_geometry_refinement():
    s=schedule(); s['timezone']='America/New_York'
    t=timing(); t.update(start_at='2026-11-01T00:00:00-04:00',end_at='2026-11-02T00:00:00-05:00')
    t['snapshots'][0].update(valid_from=t['start_at'],valid_until=t['end_at'])
    _,rows=dose([sample()],s,t)
    assert rows[0]['covered_seconds']==25*3600
    assert rows[0]['complete_local_day']
    assert rows[0]['dli_mol_m2_day']==pytest.approx(9.)
    t=timing(); t['snapshots'][0]['valid_until']='2026-10-03T06:00:00.123+09:00'
    t['snapshots'].append(dict(t['snapshots'][0],geometry_snapshot_id='g2',valid_from=t['snapshots'][0]['valid_until'],valid_until=t['end_at']))
    _,rows=dose([sample(),sample(snapshot='g2')],interval=t)
    assert rows[0]['incident_dose_mol_m2']==pytest.approx(4.32)


def test_partial_regions_preserve_unequal_area_and_unknown():
    left=sample(q=100,weight=1,sid='left'); right=sample(q=20,weight=4,sid='right')
    boundary=sample(q=None,weight=2,sid='boundary')
    for row,xyz in [(left,[1,-1,0]),(right,[3,1,0]),(boundary,[2,0,0])]:
        row.update({f'position_board_{a}_mm':v for a,v in zip('xyz',xyz)})
    state=dict(direction_unit_xyz=[1,0,0],transverse_unit_xyz=[0,1,0],attachment_xyz_mm=[0,0,0],
               _region_partition=dict(proximal_distal_boundary_mm=2))
    base={}; regions=bridge._regions([left,right,boundary],base,state)
    regions={r['region_id']:r for r in regions}
    assert regions['left']['supported_area_m2']==1
    assert regions['right']['supported_area_m2']==4
    assert regions['lateral_unassigned']['supported_area_m2']==2
    assert regions['lateral_unassigned']['received_umol_s'] is None
    assert base['left_right_flux_difference_umol_s']==20
    assert base['left_right_mean_contrast']==pytest.approx(2/3)


@pytest.mark.parametrize('change', ['time','frame','partial_axis'])
def test_observation_clock_frame_and_partial_axis_gates(tmp_path,change):
    from tools.leaf_light.common import rows
    from tools.light_growth_consumer import load_tables
    from tools.compound_growth import OBS_COLUMNS
    request=make_request(tmp_path); add_observations(tmp_path,request)
    data=read_json(request)
    if change=='time': data['snapshots'][0]['observed_at']='2026-10-03T01:00:00+09:00'
    if change=='frame': data['snapshots'][0]['board_frame_ids']['P1']='wrong_frame'
    write_json(request,data)
    if change=='partial_axis':
        observations=rows(tmp_path/'observations.csv'); observations[0]['geometry_status']='partial_axis'
        write_rows(tmp_path/'observations.csv',observations,OBS_COLUMNS)
        history=read_json(tmp_path/'history.json'); history['tables']['observations']['sha256']=file_hash(tmp_path/'observations.csv')
        write_json(tmp_path/'history.json',history)
        bridge.build_package(request,tmp_path/'package')
        check=bridge.validate_growth_light_package(tmp_path/'package'); assert check['valid'],check
        selected=[r for r in load_tables(tmp_path/'package')['compound_light_features.csv'] if r['level']=='compound' and r['compound_leaf_id']=='reviewed_C1']
        assert selected and all(r['observed_rachis_x'] is None for r in selected)
        assert all(r['received_umol_s'] is not None for r in selected)
    else:
        with pytest.raises(StudyError,match='time_mismatch' if change=='time' else 'frame_mismatch'):
            bridge.build_package(request,tmp_path/'package')


def test_source_instance_observation_clocks_are_not_capture_dates():
    snapshot=dict(observed_at='2026-10-03T00:00:00+09:00',observed_at_by_instance={
        'P2':'2026-10-02T23:15:00+09:00','unknown':None})
    assert bridge._observed_at(snapshot,'P1')=='2026-10-03T00:00:00+09:00'
    assert bridge._observed_at(snapshot,'P2')=='2026-10-02T23:15:00+09:00'
    assert bridge._observed_at(snapshot,'unknown')==bridge.UNASSIGNED
    with pytest.raises(StudyError,match='timezone'):
        bridge._observed_at(dict(observed_at='2026-10-03'),'P1')


@pytest.mark.parametrize('mutation', ['board_area', 'board_flux', 'invented_direction'])
def test_consumer_rejects_inconsistent_frame_and_unsupported_channels(tmp_path, mutation):
    from tools.light_growth_consumer import load_tables
    request=make_request(tmp_path); bridge.build_package(request,tmp_path/'package')
    folder=tmp_path/'package'; tables=load_tables(folder)
    records=tables['compound_light_features.csv']
    row=next(r for r in records if r['quantity_frame']=='board' and r['region_id']=='whole_supported')
    if mutation=='board_area': row['supported_area_cm2'] *= 2
    elif mutation=='board_flux': row['received_umol_s'] += 1
    else: row['dominant_arrival_x']=1.
    path=folder/'compound_light_features.csv'
    write_rows(path,records,[c['name'] for c in bridge.SCHEMA['tables'][path.name]['columns']])
    # Model an internally wrong producer result, not a stale-file failure.
    package=read_json(folder/'package.json'); package['artifact_hashes'][path.name]=file_hash(path)
    write_json(folder/'package.json',package)
    check=bridge.validate_growth_light_package(folder)
    assert not check['valid'], 'Consumer accepted incompatible frame/channel quantities'


@pytest.mark.parametrize('mutation', ['region_mean','region_area','contrast','grow_axis','missing_region'])
def test_independent_region_and_observed_rotation_checks(tmp_path,mutation):
    from tools.light_growth_consumer import load_tables
    request=make_request(tmp_path); add_observations(tmp_path,request)
    bridge.build_package(request,tmp_path/'package')
    folder=tmp_path/'package'; tables=load_tables(folder)
    records=tables['compound_light_features.csv']
    if mutation.startswith('region_') or mutation=='missing_region':
        row=next(r for r in records if r['region_id']=='left')
        if mutation=='region_mean': row['received_ppfd_umol_m2_s']+=1
        elif mutation=='region_area': row['supported_area_m2']*=2
        else: records.remove(row)
    else:
        row=next(r for r in records if r['level']=='compound' and r['compound_leaf_id']=='reviewed_C1' and
            r['region_id']=='whole_supported' and r['quantity_frame']==('compound_local' if mutation=='contrast' else 'grow'))
        if mutation=='contrast': row['left_right_mean_contrast']=10.
        else: row['observed_rachis_x']=-1.
    path=folder/'compound_light_features.csv'
    write_rows(path,records,[c['name'] for c in bridge.SCHEMA['tables'][path.name]['columns']])
    package=read_json(folder/'package.json'); package['artifact_hashes'][path.name]=file_hash(path)
    write_json(folder/'package.json',package)
    check=bridge.validate_growth_light_package(folder)
    assert not check['valid'], 'Consumer accepted incorrect region or observed rotation'
