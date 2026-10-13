"""External boundary corruption, default-off and missing-science refusals."""
from copy import deepcopy
import time
import uuid
import pytest
from tools.vtc_growth_io import ROOT, ContractError, write_json, write_csv, sha, read_json, digest
from tools.tomato_fsp_native_boundary import validate_options, submit_light


def option():
    return dict(schema_version='fsp-native-boundary-1',enabled=True,basis='absorbed_photon_flux',unit='umol/s',
        area_basis='one_sided_lamina_full_outline',transport_authority='external_once',nrh_basis='fixture_black_absorbed_equivalence',
        configuration_sha256='a'*64,timeout_s=30,source_kind='fixture_truth',source_ref='engineering fixture only')


def test_disabled_metadata_does_not_modify_state():
    state=[dict(organ_id='L',parent_id='P',x_m=1,y_m=2,z_m=3),dict(organ_id='P')]
    geo=dict(triangles_mm={'L':[[[1000,2000,3000],[1001,2000,3000],[1000,2001,3000]]]})
    req=dict(imported_shape_api=dict(schema_version='fsp-imported-anchor-1',enabled=False,anchors=[dict(
        organ_id='L',parent_id='P',frame='plant_local_m',anchor_m=[1,2,3],reference_geometry_sha256=digest(geo['triangles_mm']['L']),source_kind='fixture_truth',source_ref='fixture')]),
        resource_hook=dict(schema_version='fsp-native-resource-hook-1',enabled=False,quantity_basis='EC_equivalent_not_element_resolved'))
    old=deepcopy((req,state,geo));validate_options(req,state,geo);assert (req,state,geo)==old
    req['imported_shape_api']['anchors'][0]['parent_id']='ghost'
    with pytest.raises(ContractError,match='anchor_parent'):validate_options(req,state,geo)


@pytest.mark.parametrize('fault',['real_growth','incident','unit','authority','config','timeout','DLI','shape','nutrient'])
def test_unreviewed_or_ambiguous_modes_refused(fault):
    r=dict(native_boundary=option(),fixture=True,integration_contract='fsp-integration-1')
    if fault=='real_growth':r['fixture']=False
    if fault=='incident':r['native_boundary']['basis']='incident_photon_flux'
    if fault=='unit':r['native_boundary']['unit']='W'
    if fault=='authority':r['native_boundary']['transport_authority']='native_and_external'
    if fault=='config':r['native_boundary']['configuration_sha256']='unknown'
    if fault=='timeout':r['native_boundary']['timeout_s']=0
    if fault=='DLI':r['native_boundary']['reference_dli']=10
    if fault=='shape':r['imported_shape_api']=dict(schema_version='fsp-imported-anchor-1',enabled=True)
    if fault=='nutrient':r['resource_hook']=dict(schema_version='fsp-native-resource-hook-1',enabled=True)
    with pytest.raises(ContractError):validate_options(r,[],{})


@pytest.fixture
def exchange():
    p=ROOT/'build'/('native_boundary_test_'+uuid.uuid4().hex);p.mkdir()
    write_csv(p/'boundary_0_geometry.csv',[dict(state=0,organ_id='p|L',vertex=0,x_m=0,y_m=0,z_m=.1)])
    leaf=dict(organ_id='p|L',plant_instance_id='p',area_m2=.01)
    write_csv(p/'boundary_0_leaves.csv',[leaf])
    deadline=int(time.time()*1000)+30000
    request=dict(schema_version='fsp-native-boundary-1',interval=0,coordinate_frame='canopy_m',
        geometry_sha256=sha(p/'boundary_0_geometry.csv'),leaves_sha256=sha(p/'boundary_0_leaves.csv'),
        configuration_sha256='a'*64,input_hash='b'*64,engine_hash='c'*64,predecessor_sha256='b'*64,deadline_epoch_ms=deadline)
    write_json(p/'boundary_0_request.json',request)
    source=p/'fixture.json';write_json(source,dict(source_kind='fixture_truth',flux=2))
    code=ROOT/'tools/tomato_fsp_native_boundary.py'
    response=dict(schema_version='fsp-native-light-response-1',request_sha256=sha(p/'boundary_0_request.json'),
        configuration_sha256='a'*64,basis='absorbed_photon_flux',unit='umol/s',transport_count=1,source_kind='fixture_truth',
        source_ref='explicit interface fixture',source_files={str(source):sha(source)},code_files={str(code):sha(code)},
        expires_epoch_ms=deadline,leaves=[dict(leaf,absorbed_umol_s=2)])
    return p,response


def test_same_response_retry_idempotent_and_conflict_refused(exchange):
    p,r=exchange
    assert submit_light(p,0,r)['status']=='submitted'
    old=sha(p/'boundary_0_ready.csv')
    assert submit_light(p,0,r,now_ms=r['expires_epoch_ms']+100)['status']=='already_submitted'
    assert sha(p/'boundary_0_ready.csv')==old
    r['leaves'][0]['absorbed_umol_s']=3
    with pytest.raises(ContractError,match='conflicting'):submit_light(p,0,r)


@pytest.mark.parametrize('fault',['geometry','stale','configuration','owner','area','negative','missing','duplicate','basis','unit','source','expired','second_shading','frame'])
def test_response_corruption_never_publishes_ready(exchange,fault):
    p,r=exchange
    if fault=='geometry':(p/'boundary_0_geometry.csv').write_text('changed',encoding='utf-8')
    if fault=='stale':r['request_sha256']='d'*64
    if fault=='configuration':r['configuration_sha256']='d'*64
    if fault=='owner':r['leaves'][0]['plant_instance_id']='other'
    if fault=='area':r['leaves'][0]['area_m2']=.02
    if fault=='negative':r['leaves'][0]['absorbed_umol_s']=-1
    if fault=='missing':r['leaves']=[]
    if fault=='duplicate':r['leaves']*=2
    if fault=='basis':r['basis']='incident_photon_flux'
    if fault=='unit':r['unit']='mol/m2/day'
    if fault=='source':r['source_files']={str(p/'fixture.json'):'d'*64}
    if fault=='expired':r['expires_epoch_ms']=0
    if fault=='second_shading':r['shading_multiplier']=.5
    if fault=='frame':
        q=read_json(p/'boundary_0_request.json');q['coordinate_frame']='canopy_mm';write_json(p/'boundary_0_request.json',q)
    with pytest.raises(ContractError):submit_light(p,0,r)
    assert not (p/'boundary_0_ready.csv').exists()


@pytest.mark.parametrize('fault',['none','time','engine','authority','consumed','flux','response_value'])
def test_output_checks_actual_consumption_and_response(exchange,fault):
    from tools.vtc_growth_io import rows
    from tools.tomato_fsp_native_boundary import validate_output
    from tools.fsp_extensions import boundary_time
    p,response=exchange
    req=dict(native_boundary=option(),run_id='fixture',start_time='2026-10-13T06:00:00+09:00',dt_s=86400)
    pkg=dict(request=req,source_hashes={'fixture':'f'*64});binding=dict(engine_hash='c'*64)
    r=read_json(p/'boundary_0_request.json');r.update(run_id='fixture',input_hash=digest(pkg['source_hashes']),predecessor_sha256=digest(pkg['source_hashes']),interval_start=boundary_time(req,0).isoformat(),interval_end=boundary_time(req,1).isoformat())
    if fault=='time':r['interval_end']=r['interval_start']
    if fault=='engine':r['engine_hash']='d'*64
    write_json(p/'boundary_0_request.json',r);response['request_sha256']=sha(p/'boundary_0_request.json')
    submit_light(p,0,response)
    if fault=='response_value':response['leaves'][0]['absorbed_umol_s']=3;write_json(p/'boundary_0_response.json',response)
    audit=dict(interval='0',request_sha256=sha(p/'boundary_0_request.json'),response_sha256=sha(p/'boundary_0_response.json'),light_sha256=sha(p/'boundary_0_light.csv'),transport_authority='external_once',native_growth_authority='native_once')
    if fault=='authority':audit['transport_authority']='twice'
    data={'boundary_audit.csv':[audit],'consumed.csv':rows(p/'boundary_0_geometry.csv'),'flux.csv':[dict(interval='0',organ_id='p|L',absorbed_umol_s='2')]}
    if fault=='consumed':data['consumed.csv'][0]['z_m']='.2'
    if fault=='flux':data['flux.csv'][0]['absorbed_umol_s']='4'
    if fault=='none':validate_output(pkg,p,data,1,binding)
    else:
        with pytest.raises(ContractError):validate_output(pkg,p,data,1,binding)
