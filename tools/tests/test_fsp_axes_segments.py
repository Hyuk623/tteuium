"""Explicit segment/history gates; independent of native timing implementation."""
from copy import deepcopy
import pytest
from tools.fsp_axes_segments import segment,prepare_segments,validate_truss_rows
from tools.vtc_growth_io import ContractError


@pytest.mark.parametrize('value',[None,'','unavailable'])
def test_missing_segment_is_unavailable(value):
    assert segment({'segment_index':value})=='unavailable'
    assert segment({})=='unavailable'


@pytest.mark.parametrize('value',[True,False,0,-1,'1.5','nan',1.0])
def test_invalid_segment_rejected(value):
    with pytest.raises(ContractError):segment({'segment_index':value})


def test_explicit_alias_and_conflict():
    assert segment({'sympodial_segment_index':'2'})==2
    assert segment({'sympodial_segment_index':'2','segment_index':2})==2
    with pytest.raises(ContractError):segment({'sympodial_segment_index':'2','segment_index':'3'})


def example():
    a=dict(plant_instance_id='p',axis_id='S1',axis_vertex_id='S1',initialization=dict(truss_count=2,apex_stopped=False))
    axis=dict(plant_instance_id='p',axis_id='S1',segment_index='3')
    vertices=[dict(plant_instance_id='p',vertex_id=oid,**{'class':kind},segment_index=str(seg),rank=str(rank))
        for oid,kind,seg,rank in [('S1','Axis',3,0),('T1','Truss',1,0),('T2','Truss',2,0),('C1','CompoundLeaf',1,1),('C2','CompoundLeaf',2,2)]]
    membership={('p',v['vertex_id']):'S1' for v in vertices}
    return [a],[axis],vertices,membership


def test_segment_metadata_preserved_not_mutated():
    args=example();old=deepcopy(args);result=prepare_segments(*args)
    assert args==old
    assert result[0]['segment_index']==3 and result[0]['truss_rule_status']=='available'
    assert result[0]['truss_history']==[dict(node_id='T1',segment_index=1),dict(node_id='T2',segment_index=2)]


@pytest.mark.parametrize('fault',['missing_node','wrong_axis','decreasing','gap','count','axis_mismatch','request_mismatch','duplicate'])
def test_bad_history_rejected(fault):
    aa,rr,vv,mm=example()
    aa[0]['truss_history']=[dict(node_id='T1',segment_index=1),dict(node_id='T2',segment_index=2)]
    if fault=='missing_node':aa[0]['truss_history'][0]['node_id']='ghost'
    elif fault=='wrong_axis':mm['p','T1']='M'
    elif fault=='decreasing':vv[-1]['segment_index']='1';vv[-2]['segment_index']='2'
    elif fault=='gap':vv[2]['segment_index']='3'
    elif fault=='count':aa[0]['initialization']['truss_count']=1
    elif fault=='axis_mismatch':vv[0]['segment_index']='2'
    elif fault=='request_mismatch':aa[0]['segment_index']=4
    elif fault=='duplicate':aa[0]['truss_history'][1]=aa[0]['truss_history'][0]
    with pytest.raises(ContractError):prepare_segments(aa,rr,vv,mm)


def test_missing_node_segment_disables_rule_without_imputation():
    aa,rr,vv,mm=example();vv[-1]['segment_index']='unavailable'
    result=prepare_segments(aa,rr,vv,mm)
    assert result[0]['segment_index']==3 and result[0]['truss_rule_status']=='unavailable'
    assert vv[-1]['segment_index']=='unavailable'


def test_producer_truss_table_alias_and_missing_node():
    _,_,vv,mm=example()
    rr=[dict(plant_instance_id='p',axis_id='S1',truss_vertex_id='T'+str(i),segment_index=i) for i in (1,2)]
    validate_truss_rows(rr,vv,mm)
    rr[0]['truss_vertex_id']='absent'
    with pytest.raises(ContractError,match='no matching'):validate_truss_rows(rr,vv,mm)


def test_producer_truss_table_disagreement():
    _,_,vv,mm=example()
    rr=[dict(plant_instance_id='p',axis_id='S1',truss_vertex_id='T'+str(i),segment_index=i) for i in (1,2)]
    rr[0]['node_id']='different'
    with pytest.raises(ContractError,match='aliases disagree'):validate_truss_rows(rr,vv,mm)


def test_multiscale_parent_axis_maps_to_declared_axil():
    import shutil,uuid
    from tools.vtc_growth_io import ROOT,rows,write_csv
    from tools.fsp_axes_acceptance import fixture
    from tools.tomato_fsp_io import selected_package,make_native_inputs
    out=ROOT/'build'/('test_segment_edge_'+uuid.uuid4().hex)
    try:
        package,q=fixture(out);side=q['axes'][1];main=q['axes'][0]
        vv=rows(package/'mtg_vertices.csv')
        for v in vv:
            if v['plant_instance_id']==side['plant_instance_id'] and v['vertex_id']==side['axis_vertex_id']:v['parent_id']=main['axis_vertex_id']
        write_csv(package/'mtg_vertices.csv',vv)
        aa=rows(package/'axes.csv');aa[0]['parent_axis_id']=aa[0]['parent_node_id']='unavailable';write_csv(package/'axes.csv',aa)
        selected=selected_package(package,q);native=make_native_inputs(selected,q,out/'native_inputs')
        s=next(s for s in rows(native/'initial_state.csv') if s['organ_id']==side['plant_instance_id']+'|'+side['axis_vertex_id'])
        assert s['parent_id']==side['plant_instance_id']+'|'+side['parent_node_id']
    finally:
        assert out.resolve().is_relative_to((ROOT/'build').resolve())
        if out.exists():shutil.rmtree(out)
