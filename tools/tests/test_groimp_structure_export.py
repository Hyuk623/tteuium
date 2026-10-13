"""Static transport preserves identities, evidence limits and source snapshots."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools.groimp_structure_export import (attach_meshes, export_plant, load_snapshot,
    make_graph, points_m, render_rgg, scoped)
from tools.groimp_static_verify import validate_state
from tools.leaf_light import common
from tools.tests.test_canopy_light import inputs


def fixture_snapshot(folder, plant='DT-001'):
    folder.mkdir(parents=True,exist_ok=True)
    backup=folder/'backup.json'
    leaves={}
    regions=[]
    for i,name in enumerate(('lower_leaf','upper_leaf')):
        key=name+'|unavailable'
        leaves[key]=dict(organ_id=name,leaflet_id='unavailable',bboxes={'v1.png':{},'v2.png':{}},
            view_status={'v1.png':{'identity_review':'confirmed','visibility':'full'},
                         'v2.png':{'identity_review':'confirmed','visibility':'partial'}})
        regions.append(dict(leaf_key=key,status='region',centroid_mm=[12.3456,-23.4567,100+i*100],
                            compound_region=1,photos=['v1.png','v2.png']))
    leaves['lower_leaf|unavailable']['membership_review']=dict(state='confirmed',parent_id='L01')
    state=dict(leaflets=leaves,membership=dict(parents={},detections={}))
    common.write_json(backup,dict(plant_id=plant,capture={'session_id':'synthetic'},variants={'__all__':state}))
    structure=folder/'structure'; structure.mkdir()
    common.write_json(structure/'structure.json',{'plant_id':plant})
    h=dict(schema='plant-hierarchy-1',plant_id=plant,session_id='synthetic',
        inputs=dict(backup=str(backup.resolve()),backup_sha256=common.file_hash(backup),structure=str(structure.resolve())),
        stem=dict(status='fitted',axis=[[0,0,0],[0,0,200]]),growth_reference={'growth_shoot_count':99},
        compound_leaves=[dict(region=1,petiole={'status':'unavailable'},leaflets=regions)],proposed_leaflets=[])
    run=folder/'run'; (run/plant/'hierarchy').mkdir(parents=True)
    common.write_json(run/plant/'hierarchy/hierarchy.json',h)
    common.write_json(run/plant/'status.json',dict(plant=plant,stages={'S6':{'status':'failed'},'S7':{'status':'done'}}))
    return run


def test_snapshot_export_preserves_unknowns_and_inputs(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    run=fixture_snapshot(tmp_path/'source')
    snap=load_snapshot(run,'DT-001')
    manifest=export_plant(run,'DT-001',tmp_path/'output')
    graph=common.read_json(tmp_path/'output/structure_snapshot.json')
    leaves=[n for n in graph['nodes'] if n['module']=='Leaflet']
    assert [n['relation'] for n in leaves]==['confirmed','unassigned']
    assert all(n['identity']=='confirmed' for n in leaves)
    assert not any(n['module']=='GrowthShoot' for n in graph['nodes'])
    assert any(e['status']=='proposed' for e in graph['relations'])
    assert manifest['geometry_counts']=={'axis':1,'position':2}
    assert not manifest['suitable_for_ppfd'] and not manifest['groimp_open_verified']
    for path,digest in snap['source_hashes'].items():
        assert common.file_hash(Path(path))==digest
    assert 'LeafSurface(' not in (tmp_path/'output/Model.rgg').read_text().split('protected void init()')[1]


def test_hash_mismatch_blocks_export(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    run=fixture_snapshot(tmp_path/'source')
    (tmp_path/'source/backup.json').write_text('{}')
    with pytest.raises(ValueError,match='backup changed'):
        export_plant(run,'DT-001',tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_ids_scope_and_coordinate_conversion():
    assert scoped('p1','s','Leaflet','a/b')!=scoped('p2','s','Leaflet','a/b')
    assert '%2F' in scoped('p1','s','Leaflet','a/b')
    xyz=np.array([[12.345678,-22.2,123.45]])
    assert np.max(np.abs(np.array(points_m(xyz))*1000-xyz))<0.001
    with pytest.raises(ValueError,match='finite'):
        points_m([[0,float('nan'),0]])


def test_optional_open_meshes_and_unknown_identity(tmp_path):
    run=fixture_snapshot(tmp_path/'source')
    inputs(tmp_path)
    graph=make_graph(load_snapshot(run,'DT-001'))
    attach_meshes(graph,tmp_path/'geometry.csv','v25')
    assert sum(g['kind']=='leaf_mesh' for g in graph['geometry'])==4
    assert not any(g['kind']=='position' for g in graph['geometry'])
    assert all(g.get('source')=='assumed' for g in graph['geometry'] if g['kind']=='leaf_mesh')
    rgg=render_rgg(graph)
    assert 'setPolygons' in rgg and 'setAxis' in rgg
    broken=deepcopy(graph)
    broken['nodes']=[n for n in broken['nodes'] if n['original_id']!='lower_leaf|unavailable']
    with pytest.raises(ValueError,match='no existing organ'):
        attach_meshes(broken,tmp_path/'geometry.csv','v25')


def test_runtime_validator_rejects_missing_nodes_and_changed_parent(tmp_path):
    graph=make_graph(load_snapshot(fixture_snapshot(tmp_path/'source'),'DT-001'))
    with pytest.raises(ValueError,match='identities/counts'):
        validate_state({'organs':[],'visuals':[]},graph)
    state={'organs':[], 'visuals':[]}
    for n in graph['nodes']:
        row={k:n[k] for k in ('key','module','parent','original_id','relation','identity')}
        row['metadata']=dict(n['metadata'],proposed_relations=[e for e in graph['relations']
                          if e['child']==n['key'] and e['status']=='proposed'])
        state['organs'].append(row)
    state['organs'][-1]['parent']='wrong'
    with pytest.raises(ValueError,match='relationship mismatch'):
        validate_state(state,graph)


def test_missing_source_and_invalid_pair_fail(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    run=fixture_snapshot(tmp_path/'source')
    with pytest.raises(ValueError,match='together'):
        export_plant(run,'DT-001',tmp_path/'out',variant='x')
    (tmp_path/'source/structure/structure.json').unlink()
    with pytest.raises(FileNotFoundError):
        export_plant(run,'DT-001',tmp_path/'out')
    assert not (tmp_path/'out').exists()
