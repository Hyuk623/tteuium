from copy import deepcopy

import pytest

from tools.tests.test_empirical_light_field import setup_field
from tools.empirical_light_field import freeze
from tools.empirical_growth_boundary import export, RULE
from tools.empirical_growth_consumer import validate
from tools.leaf_light.common import StudyError, digest, file_hash, read_json, rows, write_json, write_rows
from tools.tomato_fsp_canopy import assemble_canopy


def ref(path):
    return dict(path=str(path),sha256=file_hash(path))


@pytest.fixture
def boundary_input(setup_field):
    root, config, config_path, _ = setup_field
    config['empirical_contract']['direction_bars'][0]['fixture_id'] = 'LED-01'
    write_json(config_path,config)
    grid=rows(root/'grid.csv')
    for row in grid: row['ppfd_umol_m2_s']=100.
    write_rows(root/'grid.csv',grid,list(grid[0]))
    field=freeze(root/'grid.csv',config_path,root/'boundary_field')
    states=[]
    for name,xyz in [('one',[[200,180,100],[220,180,100],[200,200,100]]),
                     ('two',[[300,180,100],[340,180,100],[300,220,100]])]:
        states.append(dict(surface_id=name,plant_instance_id='P',source_plant_id='source',
            producer_vertex_id=name,organ_id='P|'+name,triangles_mm=[xyz],geometry_source='synthetic_truth',
            face_convention='triangle_winding_geometric_normal',provenance='fixture'))
    snapshot=assemble_canopy(states,{'P':dict(rotation=[[1,0,0],[0,1,0],[0,0,1]],translation_mm=[0,0,0],provenance='fixture')})
    snapshot_path=root/'snapshot.json';write_json(snapshot_path,snapshot)
    registration=root/'registration.json'
    write_json(registration,dict(from_frame='canopy_m',to_frame='grow_mm',rotation=[[1,0,0],[0,1,0],[0,0,1]],
        translation_mm=[0,0,0],source_kind='fixture_truth',source_ref='Explicit co-registered metric fixture'))
    interval=dict(interval_id='i0',start_at='2026-10-13T00:00:00+09:00',end_at='2026-10-14T00:00:00+09:00',
        snapshot_ref=ref(snapshot_path),registration_ref=ref(registration),expected_geometry_hash=snapshot['geometry_hash'],
        absorptance_by_surface={sid:dict(normal=.8,opposite=.8,source_kind='fixture_truth',source_ref='synthetic grey material') for sid in ('one','two')},
        segments=[dict(start_at=a,end_at=b,fixture_fractions={'LED-01':f},source_kind='fixture_truth',source_ref='synthetic clock windows')
            for a,b,f in [('2026-10-13T00:00:00+09:00','2026-10-13T06:00:00+09:00',0),
                          ('2026-10-13T06:00:00+09:00','2026-10-13T20:00:00+09:00',1),
                          ('2026-10-13T20:00:00+09:00','2026-10-14T00:00:00+09:00',0)]])
    request=dict(schema_version='empirical-growth-request-1',run_id='fixture-boundary',
        field_ref=ref(root/'boundary_field/field.json'),configuration_ref=ref(config_path),fixture_ids=['LED-01'],
        transport_contract=dict(interpretation=RULE,source_kind='fixture_truth',source_ref='conditional fixture contract',
            field_light_basis='incident',already_canopy_shaded=False,canopy_shading_passes=1,
            canopy_scattering='not_modelled_transmission_only',
            quadrature='triangle_centroid_area_weighted',local_field_approximation_acknowledged=True),
        off_period_ambient='excluded_unmeasured',diffuse_fractions=[.5,.6,.7],leaf_transmittance=.1,
        leaf_transmittance_source_ref='synthetic grey material',
        quadrature=dict(bar_samples=5,dome_mu_samples=8,dome_phi_samples=16,max_pairs_per_chunk=7,max_total_pairs=1000000),
        intervals=[interval])
    path=root/'request.json';write_json(path,request)
    context=dict(schema_version='empirical-native-context-1',run_id=request['run_id'],configuration_sha256=field['configuration_sha256'],
        intervals=[dict(interval_id='i0',start_at=interval['start_at'],end_at=interval['end_at'],geometry_hash=snapshot['geometry_hash'],
                        namespace_hash=digest(snapshot['identity_map']),registration_sha256=file_hash(registration))])
    return root,path,request,config_path,context


def test_actual_export_and_independent_consumer(boundary_input):
    root,path,_,config,context=boundary_input
    result=export(path,root/'export')
    assert len(result['rows'])==18 and len(result['interval_totals'])==6
    assert validate(root/'export/boundary.json',config,context,'absorbed')['valid']
    for row in result['interval_totals']:
        assert row['on_duration_s']==50400
        assert row['incident_dose_mol_m2']==pytest.approx(5.04,rel=1e-10,abs=1e-10)
        assert row['absorbed_dose_mol_m2']==pytest.approx(4.032,rel=1e-10,abs=1e-10)
    lit=[r for r in result['rows'] if r['output_fraction']==1 and r['diffuse_fraction']==.5]
    assert lit[1]['incident_umol_s']/lit[0]['incident_umol_s']==pytest.approx(4)
    assert all(r['absorbed_umol_s']==pytest.approx(.8*r['incident_umol_s']) for r in lit)


@pytest.mark.parametrize('key,value',[('field_light_basis','absorbed'),('already_canopy_shaded',True),
    ('canopy_shading_passes',2),('interpretation','unreviewed_default'),('local_field_approximation_acknowledged',False)])
def test_no_double_shading_or_absorption(boundary_input,key,value):
    root,path,req,_,_=boundary_input
    req['transport_contract'][key]=value;write_json(path,req)
    with pytest.raises(StudyError):export(path,root/'export')
    assert not (root/'export').exists()


@pytest.mark.parametrize('change',['gap','overlap','missing','partial_output','wrong_fixture'])
def test_schedule_failures(boundary_input,change):
    root,path,req,_,_=boundary_input;s=req['intervals'][0]['segments']
    if change=='gap':s[1]['start_at']='2026-10-13T07:00:00+09:00'
    elif change=='overlap':s[1]['start_at']='2026-10-13T05:00:00+09:00'
    elif change=='missing':s.pop()
    elif change=='partial_output':s[1]['fixture_fractions']['LED-01']=.5
    else:s[1]['fixture_fractions']={'LED-02':1}
    write_json(path,req)
    with pytest.raises(StudyError):export(path,root/'export')


@pytest.mark.parametrize('change',['above','outside','area','namespace','duplicate','normal'])
def test_geometry_failures_even_when_rehashed(boundary_input,change):
    root,path,req,_,_=boundary_input
    snapshot=read_json(root/'snapshot.json');s=snapshot['surfaces'][0]
    if change=='above':s['triangles_m'][0][0][2]=.151 # centroid is still below 150 mm
    elif change=='outside':s['triangles_m'][0][0][0]=.099
    elif change=='area':s['area_m2']*=2
    elif change=='namespace':s['organ_id']='foreign|one'
    elif change=='normal':s['face_convention']='botanical_upper_unverified'
    else:snapshot['surfaces'].append(deepcopy(s))
    if change in ('above','outside'):
        from tools.tomato_fsp_canopy import triangle_area
        s['area_m2']=triangle_area(s['triangles_m'][0]);snapshot['one_sided_areas_m2'][s['surface_id']]=s['area_m2']
    snapshot['geometry_hash']=digest([{k:s[k] for k in ('surface_id','triangles_m')} for s in snapshot['surfaces']])
    write_json(root/'snapshot.json',snapshot)
    req['intervals'][0]['snapshot_ref']=ref(root/'snapshot.json');req['intervals'][0]['expected_geometry_hash']=snapshot['geometry_hash']
    write_json(path,req)
    with pytest.raises(StudyError):export(path,root/'export')


def test_configuration_movement_rejected(boundary_input):
    root,path,req,config,_=boundary_input
    c=read_json(config);c['lamp']['height_above_board_cm']=31
    write_json(root/'changed.json',c);req['configuration_ref']=ref(root/'changed.json');write_json(path,req)
    with pytest.raises(StudyError,match='configuration_changed'):export(path,root/'export')


@pytest.mark.parametrize('key,value',[('geometry_hash','stale'),('namespace_hash','foreign'),
                                     ('registration_sha256','different'),('end_at','2026-10-15T00:00:00+09:00')])
def test_native_context_mismatch(boundary_input,key,value):
    root,path,_,config,context=boundary_input;export(path,root/'export')
    context['intervals'][0][key]=value
    with pytest.raises(StudyError,match='context_mismatch'):validate(root/'export/boundary.json',config,context)


def test_missing_absorption_cannot_feed_P4(boundary_input):
    root,path,req,config,context=boundary_input
    req['intervals'][0]['absorptance_by_surface']['one']=None;write_json(path,req)
    result=export(path,root/'export')
    assert all(r['absorbed_umol_s'] is None for r in result['rows'] if r['surface_id']=='one')
    assert validate(root/'export/boundary.json',config,context,'incident')['valid']
    with pytest.raises(StudyError,match='P4_absorbed_input_unavailable'):validate(root/'export/boundary.json',config,context,'absorbed')


def test_corrupt_dose_detected_with_updated_csv_hash(boundary_input):
    root,path,_,config,context=boundary_input;m=export(path,root/'export')
    m['rows'][1]['incident_dose_umol']+=100
    write_rows(root/'export/leaf_segments.csv',m['rows'],list(m['rows'][0]))
    m['artifact_hashes']['leaf_segments.csv']=file_hash(root/'export/leaf_segments.csv')
    write_json(root/'export/boundary.json',m)
    with pytest.raises(StudyError,match='schedule_integral'):validate(root/'export/boundary.json',config,context)


def test_interval_area_changes_are_integrated_separately(boundary_input):
    root,path,req,config,context=boundary_input
    s=read_json(root/'snapshot.json')
    for surface in s['surfaces']:
        v=surface['triangles_m'][0]
        v[1][0]=v[0][0]+2*(v[1][0]-v[0][0])
        surface['area_m2']*=2;s['one_sided_areas_m2'][surface['surface_id']]*=2
    s['geometry_hash']=digest([{k:x[k] for k in ('surface_id','triangles_m')} for x in s['surfaces']])
    write_json(root/'snapshot2.json',s)
    second=deepcopy(req['intervals'][0]);second['interval_id']='i1'
    for item in [second]+second['segments']:
        for key in ('start_at','end_at'):
            from datetime import timedelta,datetime
            item[key]=(datetime.fromisoformat(item[key])+timedelta(days=1)).isoformat()
    second['snapshot_ref']=ref(root/'snapshot2.json');second['expected_geometry_hash']=s['geometry_hash']
    req['intervals'].append(second);write_json(path,req)
    context['intervals'].append(dict(context['intervals'][0],interval_id='i1',start_at=second['start_at'],end_at=second['end_at'],geometry_hash=s['geometry_hash']))
    m=export(path,root/'export');assert validate(root/'export/boundary.json',config,context,'absorbed')['valid']
    totals=[r for r in m['interval_totals'] if r['surface_id']=='one' and r['diffuse_fraction']==.5]
    assert totals[1]['absorbed_dose_umol']==pytest.approx(2*totals[0]['absorbed_dose_umol'])
    assert totals[1]['absorbed_dose_mol_m2']==pytest.approx(totals[0]['absorbed_dose_mol_m2'])


def native_fixture(root, req, context):
    import time
    snapshot=read_json(root/'snapshot.json');working=root/'native_working';working.mkdir()
    geometry_rows=[];leaves=[]
    for s in snapshot['surfaces']:
        leaves.append(dict(organ_id=s['organ_id'],plant_instance_id=s['plant_instance_id'],area_m2=s['area_m2']))
        for index,v in enumerate([v for t in s['triangles_m'] for v in t]):
            geometry_rows.append(dict(state=0,organ_id=s['organ_id'],vertex=index,x_m=v[0],y_m=v[1],z_m=v[2]))
    write_rows(working/'boundary_0_geometry.csv',geometry_rows,list(geometry_rows[0]))
    write_rows(working/'boundary_0_leaves.csv',leaves,list(leaves[0]))
    native=dict(schema_version='fsp-native-boundary-1',interval=0,run_id=req['run_id'],coordinate_frame='canopy_m',
        geometry_sha256=file_hash(working/'boundary_0_geometry.csv'),leaves_sha256=file_hash(working/'boundary_0_leaves.csv'),
        configuration_sha256=context['configuration_sha256'],input_hash='a'*64,engine_hash='b'*64,predecessor_sha256='a'*64,
        interval_start=req['intervals'][0]['start_at'],interval_end=req['intervals'][0]['end_at'],deadline_epoch_ms=int(time.time()*1000)+60000)
    write_json(working/'boundary_0_request.json',native)
    return working


def test_owner_protocol_response_submission_and_retry(boundary_input):
    from tools.empirical_native_response import response
    from tools.tomato_fsp_native_boundary import submit_light
    root,path,req,config,context=boundary_input
    req['leaf_transmittance']=0
    for x in req['intervals'][0]['absorptance_by_surface'].values():x.update(normal=1.,opposite=1.)
    write_json(path,req);export(path,root/'export')
    working=native_fixture(root,req,context)
    r=response(root/'export/boundary.json',config,context,working,0,.6,
        light_hours=14,nrh_basis='fixture_black_absorbed_equivalence',fixture=True,light_only=False)
    assert r['transport_count']==1 and r['basis']=='absorbed_photon_flux'
    assert sum(x['absorbed_umol_s'] for x in r['leaves'])==pytest.approx(.1)
    assert submit_light(working,0,r)['status']=='submitted'
    assert submit_light(working,0,r)['status']=='already_submitted'
    changed=deepcopy(r);changed['leaves'][0]['absorbed_umol_s']+=1
    with pytest.raises(ValueError,match='conflicting_retry'):submit_light(working,0,changed)


@pytest.mark.parametrize('change',['wrong_geometry','hours','real_growth','nonblack_growth','wrong_scenario'])
def test_native_response_gates(boundary_input,change):
    from tools.empirical_native_response import response
    root,path,req,config,context=boundary_input
    export(path,root/'export');working=native_fixture(root,req,context)
    if change=='wrong_geometry':
        p=working/'boundary_0_geometry.csv';data=rows(p);data[0]['x_m']=str(float(data[0]['x_m'])+.001)
        write_rows(p,data,list(data[0]));native=read_json(working/'boundary_0_request.json')
        native['geometry_sha256']=file_hash(p);write_json(working/'boundary_0_request.json',native)
    reasons={'wrong_geometry':'not_actual_native_consumed_mesh','hours':'native_light_hours_mismatch',
             'real_growth':'nrh_light_basis_unreviewed','nonblack_growth':'requires_black_optics',
             'wrong_scenario':'undeclared_direction_scenario'}
    with pytest.raises(StudyError,match=reasons[change]):
        response(root/'export/boundary.json',config,context,working,0,.9 if change=='wrong_scenario' else .6,
            light_hours=13 if change=='hours' else 14,nrh_basis='fixture_black_absorbed_equivalence',
            fixture=change!='real_growth',light_only=False)


def test_registration_rotation_preserves_area_and_geometric_faces(boundary_input):
    root,path,req,config,context=boundary_input
    reg=read_json(root/'registration.json')
    reg.update(rotation=[[1,0,0],[0,-1,0],[0,0,-1]],translation_mm=[0,400,200])
    write_json(root/'registration.json',reg)
    req['intervals'][0]['registration_ref']=ref(root/'registration.json')
    context['intervals'][0]['registration_sha256']=file_hash(root/'registration.json')
    for o in req['intervals'][0]['absorptance_by_surface'].values():o['opposite']=.2
    write_json(path,req);m=export(path,root/'export')
    assert validate(root/'export/boundary.json',config,context,'absorbed')['valid']
    for r in m['rows']:
        if r['output_fraction']==1:
            assert r['incident_normal_umol_s']==0
            assert r['absorbed_umol_s']==pytest.approx(.2*r['incident_umol_s'])
