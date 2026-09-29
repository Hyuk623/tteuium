"""Integration checks for static geometry/lighting case comparison."""
from copy import deepcopy
from pathlib import Path

import pytest

from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS
from tools.canopy_light import run, validate_plan
from tools.leaf_light.common import ROOT, read_json, rows, write_json, write_rows


def inputs(folder: Path) -> Path:
    scene = read_json(ROOT / 'tests/fixtures/light/light_scene.example.json')
    scene['fixtures'] = [scene['fixtures'][0]]
    fixture = scene['fixtures'][0]
    fixture['emitting_center_grow_mm']['value'] = [300,200,500]
    fixture['emitting_length_mm']['value'] = 40
    fixture['emitting_width_mm']['value'] = 40
    fixture['emitter_grid'] = [2,2]
    scene['simulation']['triangle_subdivisions'] = 2
    scene['plants'] = [scene['plants'][0]]
    scene['plants'][0]['board_origin_grow_mm']['value'] = [300,200,0]
    scene['scenarios'] = [dict(scenario_id='raised',description='SYNTHETIC lamp height test',
        fixture_overrides=[dict(fixture_id=fixture['fixture_id'],emitting_center_grow_mm=[300,200,800])])]
    write_json(folder/'scene.json',scene)
    geometry=[]
    for organ,z in [('lower_leaf',100),('upper_leaf',200)]:
        corners=[[-40,-40,z],[40,-40,z],[40,40,z],[-40,40,z]]
        for i,ids in enumerate([(0,1,2),(0,2,3)]):
            row=dict(plant_id='DT-001',session_id='synthetic',geometry_variant_id='v25',geometry_source='assumed',
                organ_class='leaf',organ_id=organ,leaflet_id='unavailable',triangle_id=f'{organ}_{i}',normal_convention='unknown')
            row.update({f'v{k}_{axis}_mm':corners[index][j] for k,index in enumerate(ids) for j,axis in enumerate('xyz')})
            geometry.append(row)
    write_rows(folder/'geometry.csv',geometry,LEAF_SURFACES_CSV_COLUMNS)
    single=dict(case_id='single',data_kind='synthetic',scene='scene.json',geometry='geometry.csv',
        geometry_variant_id='v25',plot_area_m2=1,height_split_board_mm=150,
        instances=[dict(plant_id='DT-001',source_plant_id='DT-001')])
    pair=deepcopy(single); pair['case_id']='pair'
    placement=deepcopy(scene['plants'][0]); placement['board_origin_grow_mm']['value']=[420,200,0]
    pair['instances'].append(dict(plant_id='copy_2',source_plant_id='DT-001',placement=placement))
    plan=dict(schema_version='canopy-light-1',cases=[single,pair],light_criteria={})
    write_json(folder/'plan.json',plan)
    return folder/'plan.json'


def test_single_and_canopy_retrace_lights_and_preserve_unavailable_growth(tmp_path):
    plan=inputs(tmp_path)
    before=(tmp_path/'geometry.csv').read_bytes()
    report=run(plan,tmp_path/'result')
    result=rows(tmp_path/'result/comparison.csv')
    assert len(result)==4
    single=next(r for r in result if r['case_id']=='single' and r['scenario_id']=='as_built')
    raised=next(r for r in result if r['case_id']=='single' and r['scenario_id']=='raised')
    assert float(single['upper_ppfd_umol_m2_s']) > float(raised['upper_ppfd_umol_m2_s'])
    assert float(single['lower_ppfd_umol_m2_s']) < float(single['upper_ppfd_umol_m2_s'])
    assert single['lower_area_mm2']=='6400.0'
    assert single['plants_per_m2']=='1.0'
    assert next(r for r in result if r['case_id']=='pair')['plants_per_m2']=='2.0'
    assert all(r['growth_prediction']=='unavailable' and r['agronomic_optimum']=='unavailable' for r in result)
    assert report['growth_prediction']=='unavailable'
    assert report['cases'][1]['provenance']['instances'][1]['copied_template'] is True
    assert (tmp_path/'geometry.csv').read_bytes()==before


@pytest.mark.parametrize('change',[{'plot_area_m2':0},{'height_split_board_mm':None},{'case_id':'../escape'},
                                  {'data_kind':'observed_geometry'}])
def test_invalid_case_does_not_silently_create_results(tmp_path,change):
    plan=read_json(inputs(tmp_path)); plan['cases'][1].update(change)
    with pytest.raises(ValueError): validate_plan(plan)


def test_duplicate_placement_and_unknown_source_are_rejected(tmp_path):
    path=inputs(tmp_path); plan=read_json(path)
    plan['cases'][1]['instances'][1].pop('placement')
    write_json(path,plan)
    with pytest.raises(ValueError,match='same board origin'): run(path,tmp_path/'bad')
    plan['cases'][1]['instances'][1]['source_plant_id']='missing'
    write_json(path,plan)
    with pytest.raises(ValueError,match='Missing source'): run(path,tmp_path/'bad2')


def test_explicit_light_criteria_do_not_become_agronomic_optimum(tmp_path):
    path=inputs(tmp_path); plan=read_json(path)
    plan['light_criteria']={'minimum_lower_leaf_ppfd_umol_m2_s':0,'maximum_upper_leaf_ppfd_umol_m2_s':1e9}
    write_json(path,plan); run(path,tmp_path/'result')
    assert all(r['light_criteria_status']=='meets_light_criteria' for r in rows(tmp_path/'result/comparison.csv'))
    assert all(r['agronomic_optimum']=='unavailable' for r in rows(tmp_path/'result/comparison.csv'))
