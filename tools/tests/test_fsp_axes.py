"""Failure gates and independent accounting checks for declared side axes."""
from copy import deepcopy
from pathlib import Path
import shutil
import uuid
import pytest
from tools.vtc_growth_io import ROOT,ContractError,rows,write_csv,write_json,read_json
from tools.fsp_axes_acceptance import fixture
from tools.fsp_axes import validate_records,allocation_reference
from tools.tomato_fsp_io import selected_package,make_native_inputs
from tools.vtc_development_io import load_package


@pytest.fixture(scope='module')
def example():
    folder=ROOT/'build'/('test_fsp_axes_'+uuid.uuid4().hex)
    package,scenario=fixture(folder)
    yield folder,package,scenario
    shutil.rmtree(folder)


def test_axis_import_keeps_attachment_and_single_root(example):
    folder,package,s=example
    selected=selected_package(package,s)
    native=make_native_inputs(selected,s,folder/'native_inputs')
    pkg=load_package(native);ss=pkg['tables']['initial_state.csv']
    assert {r['axis_id'] for r in ss}=={'M','S1'}
    assert sum(r['class']=='Root' for r in ss)==1
    axis=next(r for r in ss if r['organ_id'].endswith('|fixture_a/S1'))
    assert axis['parent_id'].endswith('|fixture_a/M/N1')
    assert len({r['organ_id'] for r in ss})==len(ss)


@pytest.mark.parametrize('fault',['duplicate','missing_parent','wrong_rank','wrong_axis','missing_registration','missing_source','higher_order','missing_flag','negative_scale','missing_mass','wrong_stage','no_contract'])
def test_invalid_axis_refuses_preparation(example,fault):
    _,package,source=example;s=deepcopy(source);side=s['axes'][1]
    if fault=='duplicate':s['axes'].append(deepcopy(side))
    elif fault=='missing_parent':side['parent_node_id']='missing'
    elif fault=='wrong_rank':side['parent_rank']=99
    elif fault=='wrong_axis':side['parent_axis_id']='S2'
    elif fault=='missing_registration':side['registration_leaf_ids'][0]='missing'
    elif fault=='missing_source':side['parameters']['SUBSTEM_SINK_SCALE'].pop('source_kind')
    elif fault=='higher_order':side['order']=2
    elif fault=='missing_flag':side['parameters'].pop('APPLY_DETERMINATE_STOP')
    elif fault=='negative_scale':side['parameters']['SUBSTEM_SINK_SCALE']['value']=-1
    elif fault=='missing_mass':side['initialization']['stem_mass_gDM']='unavailable'
    elif fault=='wrong_stage':side['stage']='emerging_inferred'
    elif fault=='no_contract':s.pop('axis_contract');s.pop('axes')
    with pytest.raises((ContractError,ValueError)):selected_package(package,s)


@pytest.mark.parametrize('budget',[0,.1,1,10,100])
def test_weighted_funding_is_bounded_and_conservative(budget):
    demand=[.2,1.,3.];a=allocation_reference(demand,[1.,3.,.2],budget)
    assert sum(a)==pytest.approx(min(budget,sum(demand)),abs=1e-12)
    assert all(0<=x<=d for x,d in zip(a,demand))


def test_weighted_funding_direction_and_saturation():
    assert allocation_reference([1,1],[1,3],1)==pytest.approx([.25,.75])
    assert allocation_reference([.1,1],[100,1],.8)==pytest.approx([.1,.7])
    assert allocation_reference([1,3],[1,1],2)==pytest.approx([.5,1.5])


def test_axis_flag_is_explicit_boolean(example):
    _,_,s=example;q=deepcopy(s);q['axes'][1]['parameters']['APPLY_DETERMINATE_STOP']['value']='false'
    with pytest.raises(ContractError):validate_records(q,set(q['captures_by_instance']))


def test_producer_axis_and_axis_state_column_mapping(example):
    folder,package,s=example;copy=folder/'producer_columns';shutil.copytree(package,copy)
    table=rows(copy/'axes.csv')
    for r in table:r['axis']=r.pop('axis_id');r['axis_state']=r.pop('stage')
    write_csv(copy/'axes.csv',table)
    q=deepcopy(s)
    for a in q['axes']:a['axis_state']=a.pop('stage')
    assert len(selected_package(copy,q)['axes'])==2
    table[1]['axis_id']='S2';table[0]['axis_id']='M';write_csv(copy/'axes.csv',table)
    with pytest.raises(ContractError,match='aliases disagree'):selected_package(copy,q)


@pytest.mark.parametrize('missing_parent',[False,True])
def test_a4_compound_axil_attachment_and_missing_node(example,missing_parent):
    folder,package,s=example;copy=folder/('a4_missing' if missing_parent else 'a4_parent')
    shutil.copytree(package,copy);q=deepcopy(s)
    vv=rows(copy/'mtg_vertices.csv');pid=q['axes'][1]['plant_instance_id']
    leaf=next(v for v in vv if v['plant_instance_id']==pid and v['class']=='CompoundLeaf' and v['rank']=='1')
    parent='missing' if missing_parent else leaf['vertex_id']
    q['axes'][1]['parent_node_id']=parent
    table=rows(copy/'axes.csv');table[1]['parent_node_id']=parent;write_csv(copy/'axes.csv',table)
    side=next(v for v in vv if v['plant_instance_id']==pid and v['vertex_id']==q['axes'][1]['axis_vertex_id'])
    side['parent_id']=parent;write_csv(copy/'mtg_vertices.csv',vv)
    if missing_parent:
        with pytest.raises(ContractError,match='side axis parent node missing'):selected_package(copy,q)
    else:
        selected=selected_package(copy,q)
        native=make_native_inputs(selected,q,folder/'a4_native_inputs')
        ss=load_package(native)['tables']['initial_state.csv']
        ax=next(r for r in ss if r['organ_id']==pid+'|'+side['vertex_id'])
        attachment=next(r for r in ss if r['organ_id']==ax['parent_id'])
        assert attachment['class']=='CompoundLeaf' and float(attachment['length_m'])==0
