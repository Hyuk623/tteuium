"""Explicit P1-format side-axis fixtures and actual native acceptance executions."""
from __future__ import annotations
import argparse
import json
import shutil
from copy import deepcopy
from pathlib import Path
import numpy as np
from tools.vtc_growth_io import ROOT, fresh_build, rows, read_json, write_json, write_csv, sha
from tools.fsp_axes import SCHEMA, AXIS_COLUMNS


def parameter(value, unit: str) -> dict:
    return dict(value=value,unit=unit,source_kind='user_assumed',source_ref='P4 side-shoot conditional contract section 2; synthetic acceptance',cultivar='unfitted_hypothesis',uncertainty='not calibrated')


def fixture(out: Path, shift_mm: tuple=(0.,0.,100.)) -> tuple[Path, dict]:
    """Reassign two known synthetic compounds; never edit a producer package in place."""
    out=fresh_build(out);package=out/'p1'
    source=ROOT/'build/fsp_integration_20261011_p1_fixture_01';shutil.copytree(source,package)
    scenario=read_json(ROOT/'build/fsp_integration_20261011_light_02/isolated/scenario.json')
    pid='fixture_a#2';cid=scenario['captures_by_instance'][pid]
    scenario.update(light_only=False,freeze_geometry=False,intervals=5,nutrient_ledger_required=False)
    scenario.pop('nutrient_scenarios',None)
    scenario['environment']=[deepcopy(scenario['environment'][0]) for _ in range(5)]
    vv=rows(package/'mtg_vertices.csv');pv=[v for v in vv if v['plant_instance_id']==pid]
    main=next(v for v in pv if v['class']=='Axis')
    compounds=sorted((v for v in pv if v['class']=='CompoundLeaf'),key=lambda v:int(v['rank']))
    selected=compounds[-2:];side_compounds={v['vertex_id'] for v in selected}
    by={v['vertex_id']:v for v in pv};side_ids=set()
    for v in pv:
        a=v
        while a['class'] not in ('Plant','Axis','CompoundLeaf'):a=by[a['complex_id']]
        if a['vertex_id'] in side_compounds:side_ids.add(v['vertex_id'])
    node=deepcopy(main);node.update(vertex_id='fixture_a/M/N1',**{'class':'Metamer'},scale='3',complex_id=main['vertex_id'],parent_id='unavailable',rank='1',rank__status='synthetic_truth')
    node['base_xyz_mm']=node['tip_xyz_mm']=compounds[0]['base_xyz_mm'];node['length_mm']='0';vv.append(node)
    compounds[0]['complex_id']=node['vertex_id']
    side=deepcopy(main);side.update(vertex_id='fixture_a/S1',parent_id=node['vertex_id'],order='1',edge_type='+')
    side['base_xyz_mm']=node['base_xyz_mm'];side['tip_xyz_mm']=json.dumps((np.array(json.loads(main['tip_xyz_mm']))+np.array(shift_mm)).tolist())
    vv.append(side)
    hidden=scenario['organ_initialization']
    template=deepcopy(hidden[pid+'|'+main['vertex_id']])
    for v in (node,side):hidden[pid+'|'+v['vertex_id']]=deepcopy(template)
    for rank,v in enumerate(selected,1):v.update(complex_id=side['vertex_id'],rank=str(rank),order='1')
    ranks={v['vertex_id']:i+1 for i,v in enumerate(selected)}
    for v in pv:
        if v['vertex_id'] not in side_ids:continue
        a=v
        while a['class']!='CompoundLeaf':a=by[a['complex_id']]
        hidden[pid+'|'+v['vertex_id']]['true_leaf_order']=ranks[a['vertex_id']]
        for key in ('base_xyz_mm','tip_xyz_mm'):
            v[key]=json.dumps((np.array(json.loads(v[key]))+np.array(shift_mm)).tolist())
        v['order']='1';v['order__status']='synthetic_truth'
    write_csv(package/'mtg_vertices.csv',vv)
    # Explicit transformed synthetic surfaces; refresh all rows referring to each file.
    manifests=rows(package/'optical_surface_manifest.csv');modified={}
    for m in manifests:
        if m['plant_instance_id']!=pid or m['vertex_id'] not in side_ids:continue
        path=m['surface_file']
        if path not in modified:modified[path]=rows(package/path)
        for r in modified[path]:
            if r['external_leaflet_id']!=m['external_leaflet_id']:continue
            for i in range(3):
                for k,delta in zip('xyz',shift_mm):r[f'v{i}_{k}_mm']=float(r[f'v{i}_{k}_mm'])+delta
    for name,table in modified.items():write_csv(package/name,table)
    for m in manifests:
        if m['surface_file'] in modified:m['surface_sha256']=sha(package/m['surface_file'])
    write_csv(package/'optical_surface_manifest.csv',manifests)
    ph=scenario['plant_initialization'][pid];count=len(compounds)-2
    def axis(aid: str,vertex: str,order: int,leaves: int) -> dict:
        return dict(plant_instance_id=pid,axis_id=aid,axis_vertex_id=vertex,order=order,parent_axis_id='M' if order else '',parent_node_id=node['vertex_id'] if order else '',parent_rank=1 if order else 0,
            stage='substem' if order else 'main',source_kind='synthetic_assumed',source_ref='explicit transformed P1-format fixture; no natural branching evidence',registration_leaf_ids=[v['vertex_id'] for v in selected] if order else [],
            parameters=dict(SUBSTEM_SINK_SCALE=parameter(1.,'dimensionless'),APPLY_DETERMINATE_STOP=parameter(True,'boolean')),
            initialization=dict(thermal_dd=206.3+37.9*(leaves+.9),produced=leaves,leaf_order=leaves,truss_count=0,axis_leaf_count=leaves,apex_stopped=False,stem_mass_gDM=.02,stem_width_m=.002,
                source_kind='user_assumed',source_ref='explicit fixture mass and age supplement; not derived from photos'))
    aa=[axis('M',main['vertex_id'],0,count),axis('S1',side['vertex_id'],1,2)]
    scenario.update(axis_contract=SCHEMA,topology_scope='provided_axes',topology_completeness='unavailable',axes=aa)
    write_csv(package/'axes.csv',[{k:cid if k=='capture_id' else a[k] for k in AXIS_COLUMNS} for a in aa],AXIS_COLUMNS)
    manifest=read_json(package/'p1_manifest.json');manifest.update(fixture_note='Consumer side-axis fixture of declared exchange columns; not a completed P1 axes exporter',files={})
    write_json(package/'p1_manifest.json',manifest)
    write_json(out/'scenario.json',scenario)
    return package,scenario


def execute(out: Path, mode: str, rays: int=4800000) -> None:
    from tools.tomato_fsp_pipeline import prepare_run,run,replay
    out=fresh_build(out)
    if mode=='shading':
        for geometry,shift in [('near',(0.,0.,60.)),('far',(300.,0.,60.))]:
            package,s=fixture(out/geometry,shift)
            for seed in (5000,5100):
                q=deepcopy(s);q.update(light_only=True,intervals=1,environment=s['environment'][:1],rays=rays,seed=seed)
                path=out/f'{geometry}_{seed}.json';write_json(path,q);folder=out/f'{geometry}_{seed}'
                prepare_run(package,path,folder);print(folder.name,run(folder,600)['status'],flush=True)
        return
    package,s=fixture(out/'fixture')
    for name in ('unity','weighted','main_stopped','axis_stop'):
        q=deepcopy(s);q['rays']=rays
        if name=='weighted':q['axes'][1]['parameters']['SUBSTEM_SINK_SCALE']['value']=3.
        # Deliberately scarce reserve exposes allocation competition under identical optics.
        q['plant_initialization']['fixture_a#2']['reserve_gC']=.003
        if name=='main_stopped':q['axes'][0]['initialization']['apex_stopped']=True
        if name=='axis_stop':
            a=q['axes'][0]['initialization'];a.update(truss_count=3,axis_leaf_count=0)
            # A pre-existing conditional history is declared, never presented as observed trusses.
        path=out/f'{name}.json';write_json(path,q);folder=out/name
        prepare_run(package,path,folder);print(name,run(folder,600)['status'],flush=True)
    print('replay',replay(out/'unity',out/'replay',600),flush=True)


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--mode',choices=['growth','shading'],default='growth');p.add_argument('--rays',type=int,default=4800000)
    a=p.parse_args();execute(a.out,a.mode,a.rays)


if __name__=='__main__':main()
