"""Physical boundary, schedule, optional-hook and transaction failure gates."""
from copy import deepcopy
import shutil
import uuid
import numpy as np
import pytest
from tools.vtc_growth_io import ROOT,ContractError,read_json,digest
from tools.vtc_development import parameters
from tools.fsp_extensions import piecewise_schedule,hook_settings,rigid_about_anchor,photon_factor,validate_extensions
from tools.fsp_extensions_acceptance import extension,plate
from tools.fsp_observation_intake import metric_points
from tools.fsp_nutrient_transaction import begin,finalize


def schedule():
    def r(a,z,**kw):return dict(start=a,end=z,source_kind='synthetic_assumed',**kw)
    a,b,c='2026-10-11T23:30:00+09:00','2026-10-12T00:00:00+09:00','2026-10-12T01:00:00+09:00'
    return dict(start=a,end=c,interpolation='piecewise_constant',max_step_s=7200,
        lights={'L1':[r(a,b,fraction=1),r(b,c,fraction=0)],'L2':[r(a,c,fraction=.25)]},
        environment=[r(a,c,temp_c=24,co2_ppm=400)])


def test_midnight_staggered_lamps_exact_integrals_and_refinement():
    s=schedule();lamps=[dict(lamp_id='L1'),dict(lamp_id='L2')];coarse=piecewise_schedule(s,lamps)
    assert [r['duration_s'] for r in coarse]==[1800,3600]
    s['max_step_s']=600;fine=piecewise_schedule(s,lamps)
    for name,expected in [('L1',1800),('L2',1350)]:
        for result in (coarse,fine):assert sum(r['duration_s']*r['source_fractions'][name] for r in result)==expected
    assert sum(r['duration_s'] for r in fine)==5400


@pytest.mark.parametrize('fault',['gap','overlap','missing_lamp','naive_time','fraction','interpolation','zero_step','environment_gap'])
def test_schedule_refuses_ambiguous_boundaries(fault):
    s=schedule();lamps=[dict(lamp_id='L1'),dict(lamp_id='L2')]
    if fault=='gap':s['lights']['L1'][1]['start']='2026-10-12T00:01:00+09:00'
    if fault=='overlap':s['lights']['L1'][1]['start']='2026-10-11T23:59:00+09:00'
    if fault=='missing_lamp':s['lights'].pop('L2')
    if fault=='naive_time':s['start']='2026-10-11T23:30:00'
    if fault=='fraction':s['lights']['L1'][0]['fraction']=1.1
    if fault=='interpolation':s['interpolation']='linear'
    if fault=='zero_step':s['max_step_s']=0
    if fault=='environment_gap':s['environment'][0]['end']='2026-10-12T00:30:00+09:00'
    with pytest.raises((ContractError,ValueError)):piecewise_schedule(s,lamps)


def test_units_and_anchor_area_preservation():
    assert metric_points([[1000,2,3]],'mm','plant_local_mm')==metric_points([[1,.002,.003]],'m','plant_local_m')
    with pytest.raises(ContractError):metric_points([[1,2,3]],'px','image_px')
    triangles=[[[1,2,3],[2,2,3],[1,3,3]]];rotation=[[0,-1,0],[1,0,0],[0,0,1]]
    result=np.array(rigid_about_anchor(triangles,[1,2,3],rotation))
    assert result[0,0]==pytest.approx([1,2,3])
    assert np.linalg.norm(np.cross(result[0,1]-result[0,0],result[0,2]-result[0,0]))/2==pytest.approx(.5)
    with pytest.raises(ContractError):rigid_about_anchor(triangles,[1,2,3],[[2,0,0],[0,1,0],[0,0,1]])


def test_photon_energy_conversion():
    assert photon_factor(550)==pytest.approx(4.597640974,rel=1e-6)
    assert photon_factor(600)/photon_factor(400)==pytest.approx(1.5)


def test_hook_exact_segments_null_fraction_and_reporting_basis():
    p=parameters();p['CURVE_RATIO']=dict(value=[1,2,2])
    with pytest.raises(ContractError):hook_settings(p)
    p['CURVE_RATIO']['by_segment_count']={'1':[1],'2':[1,3]}
    p['BENT_FRACTION']=dict(value=None)
    h=hook_settings(p);assert h['curves']['2']==[.25,.75];assert h['fraction'] is None
    p['BENT_FRACTION']['value']=.5
    with pytest.raises(ContractError):hook_settings(p)
    p['BENT_FRACTION']['templates']=dict(flat_total_bend_deg=0,bent_total_bend_deg=-20)
    assert hook_settings(p)['bent']==-20
    p['AREA_CORRECTION']=dict(value=1.25)
    with pytest.raises(ContractError):hook_settings(p)


@pytest.mark.parametrize('fault',['fractions','negative','source','nonblack_growth','deformation','nutrients'])
def test_optics_and_science_gates(fault):
    ext=extension();req=dict(extensions=ext,parameters=parameters(),light_only=True)
    if fault=='fractions':ext['materials']['black']['reflectance']=.1
    if fault=='negative':ext['materials']['black']['transmittance']=-.1
    if fault=='source':ext['materials']['black'].pop('source_ref')
    if fault=='nonblack_growth':req['light_only']=False;ext['leaf_material']='mixed'
    if fault=='deformation':ext['imported_deformation']={'enabled':True}
    if fault=='nutrients':ext['nutrient_coupling']={'enabled':True}
    with pytest.raises(ContractError):validate_extensions(req,{})


@pytest.fixture
def transaction():
    folder=ROOT/'build'/('test_fsp_tx_'+uuid.uuid4().hex)
    proposal=dict(schema_version='fsp-resource-protocol-fixture-1',fixture=True,interval_start='2026-10-12T00:00:00+09:00',interval_end='2026-10-13T00:00:00+09:00',
        predecessor_sha256='a'*64,model_sha256='b'*64,parameter_sha256='c'*64,plants={'p1':dict(carbon_gC=1.,water_ml=10.,elements_mg={'N':2.})})
    tx=begin(folder,proposal);binding={k:proposal[k] for k in ('predecessor_sha256','model_sha256','parameter_sha256','interval_start','interval_end')}
    response=dict(transaction_id=tx,binding=binding,expires_at='2026-10-12T01:00:00+09:00',available={'p1':dict(carbon_gC=.5,water_ml=5.,elements_mg={'N':1.})})
    actual=dict(transaction_id=tx,binding=binding,used={'p1':dict(carbon_gC=.3,water_ml=3.,elements_mg={'N':.4})})
    yield folder,proposal,response,actual
    shutil.rmtree(folder)


def test_transaction_conserves_unused_and_retry_once(transaction):
    folder,p,r,a=transaction
    done=finalize(folder,r,a,'2026-10-12T00:30:00+09:00')
    assert done['native_handshake'] is False
    assert done['balances']['p1']['returned_unused']['elements_mg']['N']==pytest.approx(.6)
    assert begin(folder,p)==digest(p)
    assert finalize(folder,r,a,'2026-10-12T03:00:00+09:00')==done
    a['used']['p1']['carbon_gC']=.1
    with pytest.raises(ContractError):finalize(folder,r,a,'2026-10-12T00:30:00+09:00')


@pytest.mark.parametrize('fault',['carbon','element','zero_available','cross_plant','stale','timeout','partial','real'])
def test_transaction_refuses_invalid_publish(transaction,fault):
    folder,p,r,a=transaction;now='2026-10-12T00:30:00+09:00'
    if fault=='carbon':a['used']['p1']['carbon_gC']=.6
    if fault=='element':a['used']['p1']['elements_mg']['N']=1.1
    if fault=='zero_available':r['available']['p1']['elements_mg']['N']=0.
    if fault=='cross_plant':r['available']['p2']=r['available'].pop('p1')
    if fault=='stale':r['transaction_id']='0'*64
    if fault=='timeout':now='2026-10-12T01:01:00+09:00'
    if fault=='partial':(folder/'.commit_partial').mkdir()
    if fault=='real':
        p['fixture']=False
        with pytest.raises(ContractError):begin(folder,p)
        return
    with pytest.raises(ContractError):finalize(folder,r,a,now)
    assert not (folder/'committed').exists()
