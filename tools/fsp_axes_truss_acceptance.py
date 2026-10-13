"""Conditional segment/truss acceptance using explicit synthetic producer-format inputs."""
from copy import deepcopy
from pathlib import Path
import argparse
import shutil
from tools.vtc_growth_io import ROOT,read_json,write_json,rows,write_csv,fresh_build


def fixture(out):
    from tomato3d.state.schema import MTG_VERTICES_COLUMNS
    out=fresh_build(out);package=out/'p1'
    original=ROOT/'build/fsp_axes_20261012_growth_02/unity'
    shutil.copytree(original/'p1',package)
    s=read_json(original/'scenario.json');s['intervals']=3;s['environment']=s['environment'][:3]
    s['rays']=4800000;pid=s['axes'][0]['plant_instance_id']
    vv=rows(package/'mtg_vertices.csv');by={v['vertex_id']:v for v in vv if v['plant_instance_id']==pid}
    side=s['axes'][1];av=by[side['axis_vertex_id']]
    for v in vv:
        for k in MTG_VERTICES_COLUMNS:v.setdefault(k,'unavailable')
        if v['class']=='CompoundLeaf':v['leaf_unfolded']='true';v['leaf_unfolded__status']='synthetic_truth'
        if v['plant_instance_id']!=pid or v['class']=='Plant':continue
        a=v
        while a['class'] not in ('Axis','Plant'):a=by[a['complex_id'] if a['complex_id'] not in ('','unavailable') else a['parent_id']]
        aid='S1' if a['vertex_id']==side['axis_vertex_id'] else 'M'
        v['axis']=aid;v['leaf_unfolded']='true' if v['class']=='CompoundLeaf' else 'unavailable'
        v['segment_index']='4' if aid=='S1' else '1';v['segment_index__status']='synthetic_truth'
        if aid=='S1' and v['class']!='Axis':
            c=v
            while c['class']!='CompoundLeaf':c=by[c['complex_id']]
            v['segment_index']=str(int(c['rank'])+1)
        if v['class']=='Axis':v['parent_rank']='1' if aid=='S1' else '0';v['parent_rank__status']='synthetic_truth'
    history=[]
    for i in range(1,4):
        v=deepcopy(av);v.update(vertex_id=f'fixture_a/S1/HT{i}',complex_id=av['vertex_id'],parent_id='unavailable',scale='3',
            **{'class':'Truss'},rank='unavailable',rank__status='unavailable',parent_rank=str(i-1),parent_rank__status='synthetic_truth',
            segment_index=str(i),segment_index__status='synthetic_truth',length_mm='0',leaf_unfolded='unavailable')
        v['tip_xyz_mm']=v['base_xyz_mm'];vv.append(v)
        history.append(dict(node_id=v['vertex_id'],segment_index=i))
        s['organ_initialization'][pid+'|'+v['vertex_id']]=dict(mass_gDM=.001,max_mass_gDM=.002,thermal_age_dd=80,true_leaf_order=0,
            units={'mass':'gDM','age':'degree_day'},provenance='user_assumed:explicit synthetic truss hidden state')
    for a in s['axes']:
        a['segment_index']=4 if a['axis_id']=='S1' else 1
        a['truss_history']=history if a['axis_id']=='S1' else []
    side['initialization'].update(truss_count=3,axis_leaf_count=0)
    aa=rows(package/'axes.csv')
    for a in aa:a['segment_index']='4' if a['axis_id']=='S1' else '1'
    write_csv(package/'axes.csv',aa);write_csv(package/'mtg_vertices.csv',vv,MTG_VERTICES_COLUMNS)
    manifest=read_json(package/'p1_manifest.json');manifest['files']={};manifest['fixture_note']='Explicit A5 consumer fixture; supplied synthetic truss history/segments/geometry, not real or P1 exporter accuracy'
    write_json(package/'p1_manifest.json',manifest);write_json(out/'scenario.json',s)
    return package,s


def execute(out):
    from tools.tomato_fsp_pipeline import prepare_run,run
    out=fresh_build(out);package,s=fixture(out/'fixture')
    results=[]
    for name in ('side_stop','both_stopped','missing_segment','successor'):
        q=deepcopy(s);p=package
        if name=='both_stopped':
            for a in q['axes']:a['initialization']['apex_stopped']=True
        if name=='missing_segment':
            p=out/'missing_p1';shutil.copytree(package,p)
            vv=rows(p/'mtg_vertices.csv')
            for v in vv:
                if v['axis']=='S1':v['segment_index']=v['segment_index__status']='unavailable'
            write_csv(p/'mtg_vertices.csv',vv)
            aa=rows(p/'axes.csv');aa[1]['segment_index']='unavailable';write_csv(p/'axes.csv',aa)
            q['axes'][1]['segment_index']='unavailable'
            for e in q['axes'][1]['truss_history']:e['segment_index']='unavailable'
        if name=='successor':
            # M reaches its first truss then continues in segment 2; explicit conditional hidden clock/count.
            a=q['axes'][0]['initialization'];a.update(axis_leaf_count=9,leaf_order=9,produced=9,thermal_dd=206.3+37.9*9.9)
        path=out/(name+'.json');write_json(path,q)
        folder=out/name;prepare_run(p,path,folder);result=run(folder,600)
        print(name,result['status'],flush=True);results.append(dict(name=name,result=result))
    write_json(out/'execution_cases.json',results)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    execute(p.parse_args().out)


if __name__=='__main__':main()
