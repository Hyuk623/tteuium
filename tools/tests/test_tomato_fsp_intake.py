"""Revision-7 producer plane checks and conditional completion evidence."""
from copy import deepcopy
import shutil
import uuid
import pytest
from tools.vtc_growth_io import ROOT,read_json,write_json,write_csv,rows,sha,ContractError
from tools.tomato_fsp_io import audit_p1_package
from tools.tomato_fsp_intake import plane_evidence,validate_completion


def test_actual_revision7_packages_distinguish_scale_from_optical_readiness():
    fixture=audit_p1_package(ROOT/'build/p1_state_20261013_02')
    real=audit_p1_package(ROOT/'build/p1_state_20261013_03')
    assert fixture['schema_revision']==real['schema_revision']==7
    assert fixture['fixture_ready'] and not real['real_ready']
    assert any(x.startswith('optical_surface_unavailable:') for x in real['missing'])
    assert any(v['scale_reference_plane']=='pot_rim' and v['scale_status']=='solved' for v in real['scale_plane_evidence'].values())
    assert 'frame_transforms.csv' in real['source_hashes']


def test_legacy_fixture_frame_header_is_not_silently_upgraded():
    p=ROOT/'build/p1_state_20261011_01';before=sha(p/'frame_transforms.csv')
    result=audit_p1_package(p)
    assert result['fixture_ready'] and result['source_hashes']['frame_transforms.csv']==before
    assert all(v['scale_reference_plane']=='unavailable' for v in result['scale_plane_evidence'].values())


@pytest.mark.parametrize('fault',['plane','offset','missing','unit'])
def test_plane_frame_corruption(fault):
    src=ROOT/'build/p1_state_20261013_02';out=ROOT/'build'/('plane_test_'+uuid.uuid4().hex);shutil.copytree(src,out)
    c=rows(out/'captures.csv');a=rows(out/'areas.csv');f=rows(out/'frame_transforms.csv')
    if fault=='plane':f[0]['scale_reference_plane']='pot_rim';f[0]['scale_reference_plane_offset_mm']='0'
    if fault=='offset':f[0]['scale_reference_plane_offset_mm']='-10'
    if fault=='unit':c[0]['frame']='plant_local_m';write_csv(out/'captures.csv',c)
    if fault=='missing':(out/'frame_transforms.csv').unlink()
    else:write_csv(out/'frame_transforms.csv',f)
    with pytest.raises(ValueError):audit_p1_package(out)


@pytest.fixture
def completion():
    p=ROOT/'build'/('completion_test_'+uuid.uuid4().hex);p.mkdir()
    write_csv(p/'identity_manifest.csv',[dict(plant_instance_id='p',capture_id='c',organ_id='observed')])
    for name in ('captures.csv','mtg_vertices.csv','areas.csv','optical_surface_manifest.csv','canopy_placement.json','mesh.csv'):
        (p/name).write_text('explicit fixture\n',encoding='utf-8')
    source=dict(source_kind='fixture_truth',source_ref='completion engineering fixture')
    m=dict(schema_version='fsp-p1-completion-1',producer_version='fixture',scale_assumptions=[source],depth_assumptions=[source],posture_assumptions=[source],
        simulation_identity_map={'p|L':'observed'},observation_links=[dict(simulation_organ_id='p|L',plant_instance_id='p',capture_id='c',observed_organ_id='observed',source_ref='fixture')],
        files={q.name:sha(q) for q in p.iterdir()})
    write_json(p/'completion_manifest.json',m)
    s=dict(captures_by_instance={'p':'c'},simulation_identity_map=m['simulation_identity_map'])
    return p,m,s,[dict(plant_instance_id='p',vertex_id='L',**{'class':'Leaflet'})],[dict(surface_file='mesh.csv')]


def test_completion_preserves_evidence(completion):
    p,m,s,v,g=completion;old=deepcopy(m)
    result=validate_completion(p,s,v,g)
    assert result['geometry_status']=='conditional_completion' and read_json(p/'completion_manifest.json')==old


@pytest.mark.parametrize('fault',['mesh','link','duplicate','source','omitted_file','mapping'])
def test_completion_refuses_unbound_geometry_and_observations(completion,fault):
    p,m,s,v,g=completion
    if fault=='mesh':(p/'mesh.csv').write_text('changed',encoding='utf-8')
    if fault=='link':m['observation_links'][0]['observed_organ_id']='absent'
    if fault=='duplicate':m['observation_links']*=2
    if fault=='source':m['depth_assumptions']=[{'value':10}]
    if fault=='omitted_file':m['files'].pop('mesh.csv')
    if fault=='mapping':s['simulation_identity_map']={}
    write_json(p/'completion_manifest.json',m)
    with pytest.raises(ContractError):validate_completion(p,s,v,g)


def test_explicit_synthetic_completion_prepares_frozen_native_inputs():
    from tools.tomato_fsp_acceptance import scenario_fixture
    from tools.tomato_fsp_pipeline import prepare_run
    from tools.fsp_observation_intake import inspect_route
    out=ROOT/'build'/('completion_pipeline_'+uuid.uuid4().hex);out.mkdir()
    p=out/'producer_fixture';shutil.copytree(ROOT/'build/fsp_integration_20261011_p1_fixture_01',p)
    path=scenario_fixture(p,out/'scenario',intervals=1,rays=1000)
    s=read_json(path);s.update(observation_route='conditional_completion',allow_conditional_surfaces=True)
    v=rows(p/'mtg_vertices.csv');mapping={r['plant_instance_id']+'|'+r['vertex_id']:r['vertex_id'] for r in v if r['class'] in ('CompoundLeaf','Leaflet')}
    s['simulation_identity_map']=mapping
    assumption=dict(source_kind='fixture_truth',source_ref='Explicit synthetic fixture completion manifest; no real observations or geometric inference')
    audit=audit_p1_package(p)
    manifest=dict(schema_version='fsp-p1-completion-1',producer_version='consumer_completion_contract_fixture',simulation_identity_map=mapping,
        scale_assumptions=[assumption],depth_assumptions=[assumption],posture_assumptions=[assumption],files=audit['source_hashes'],
        observation_links=[dict(simulation_organ_id=r['plant_instance_id']+'|'+r['vertex_id'],plant_instance_id=r['plant_instance_id'],capture_id=r['capture_id'],observed_organ_id=r['vertex_id'],source_ref='synthetic identity row, not measured') for r in v if r['class'] in ('CompoundLeaf','Leaflet')])
    write_json(p/'completion_manifest.json',manifest);write_json(path,s)
    ready=inspect_route(p,'conditional_completion',s)
    assert ready['fixture'] and ready['simulation_status']=='ready_conditionally'
    # Explicit route wins over the scenario field; truth must never become observed.
    assert inspect_route(p,'observed_metric',s)['simulation_status']=='unavailable'
    prepare_run(p,path,out/'run')
    g=read_json(out/'run/native/inputs/integration_geometry.json')
    assert g['completion']['manifest_sha256']==sha(p/'completion_manifest.json')
    assert g['completion']['geometry_status']=='conditional_completion'
    assert sha(out/'run/p1/completion_manifest.json')==sha(p/'completion_manifest.json')
