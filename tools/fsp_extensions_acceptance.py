"""Execute explicit optical/schedule/hook fixtures using the authoritative pipeline."""
from __future__ import annotations
import argparse
from copy import deepcopy
from pathlib import Path
from tools.vtc_growth_io import ROOT,fresh_build,read_json,write_json,rows,write_csv,sha
from tools.tomato_fsp_pipeline import prepare_run,run


def material(a: float,r: float,t: float) -> dict:
    return dict(absorptance=a,reflectance=r,transmittance=t,scattering='lambertian_reflection_straight_transmission',
                source_kind='synthetic_assumed',source_ref='engineering limit fixture; not measured leaf optics',uncertainty='unavailable',domain='grey monochromatic 550 nm fixture')


def extension() -> dict:
    return dict(schema_version='fsp-extensions-1',wavelength_nm=550.,materials=dict(black=material(1,0,0),clear=material(0,0,1),reflector=material(0,1,0),mixed=material(.5,.2,.3)),leaf_material='black',nonleaf_material='black',objects=[],max_depth=8)


def plate(key: str,z_m: float,mat: str,wide: bool=False) -> dict:
    x0,x1,y0,y1=(-2,2,-2,2) if wide else (-.1,.35,-.15,.3)
    return dict(object_id='scene:'+key,role='shelf',material=mat,frame='object_local_m',dynamic=False,
        source_kind='synthetic_assumed',source_ref='explicit two-triangle optical fixture',
        transform=[[1,0,0,0],[0,1,0,0],[0,0,1,z_m],[0,0,0,1]],
        triangles_m=[[[x0,y0,0],[x1,y0,0],[x1,y1,0]],[[x0,y0,0],[x1,y1,0],[x0,y1,0]]])


def execute_optics(out: Path,rays: int=4800000,names: tuple|None=None,seed: int=5000) -> dict:
    out=fresh_build(out);package=ROOT/'build/fsp_integration_20261011_p1_fixture_01'
    base=read_json(ROOT/'build/fsp_integration_20261011_light_02/isolated/scenario.json')
    results={}
    for name in names or ('black','clear_leaf','mixed_leaf','reflecting_leaf','shade','clear_plate','reflector_floor','black_floor','dark'):
        s=deepcopy(base);s.update(rays=rays,seed=seed);s['extensions']=extension();e=s['extensions']
        if name in ('clear_leaf','mixed_leaf','reflecting_leaf'):e['leaf_material']={'clear_leaf':'clear','mixed_leaf':'mixed','reflecting_leaf':'reflector'}[name]
        if name=='shade':e['objects']=[plate('upper',.4,'black')]
        if name=='clear_plate':e['objects']=[plate('upper',.4,'clear')]
        if name.endswith('_floor'):e['objects']=[plate('floor',-.03,'reflector' if name=='reflector_floor' else 'black',True)]
        if name=='dark':s['lamps'][0]['power_umol_s']=0
        scenario=out/(name+'.json');write_json(scenario,s);folder=out/name
        prepare_run(package,scenario,folder);print(name,'prepared',flush=True)
        result=run(folder,180);print(name,result['status'],flush=True)
        results[name]=dict(status=result['status'],exit_code=result['native_execution']['exit_code'],run=str(folder),collection_sha256=sha(folder/'collection.json'))
        write_json(out/'executed.json',results)
    return results


def execute_schedule(out: Path,rays: int=4800000) -> dict:
    import shutil
    out=fresh_build(out);package=out/'p1';shutil.copytree(ROOT/'build/fsp_integration_20261011_p1_fixture_01',package)
    at='2026-10-11T21:30:00+09:00';caps=rows(package/'captures.csv')
    for c in caps:c['capture_time']=at
    write_csv(package/'captures.csv',caps)
    base=read_json(ROOT/'build/fsp_integration_20261011_controls_01/no_nutrient/scenario.json')
    base.update(start_time=at,rays=rays);base['extensions']=extension()
    def row(a,z,**kw):return dict(start=a,end=z,source_kind='synthetic_assumed_explicit_clock',**kw)
    end='2026-10-12T02:15:00+09:00'
    schedule=dict(start=at,end=end,interpolation='piecewise_constant',max_step_s=86400,
        lights={'L1':[row(at,'2026-10-11T22:15:00+09:00',fraction=1.),row('2026-10-11T22:15:00+09:00','2026-10-12T00:15:00+09:00',fraction=0.),row('2026-10-12T00:15:00+09:00',end,fraction=.5)]},
        environment=[row(at,'2026-10-11T23:15:00+09:00',temp_c=26,co2_ppm=400),row('2026-10-11T23:15:00+09:00',end,temp_c=22,co2_ppm=400)])
    results={}
    for name,step in [('coarse',86400),('refined',1800)]:
        s=deepcopy(base);s['extensions']['schedule']=dict(schedule,max_step_s=step);file=out/(name+'.json');write_json(file,s)
        folder=out/name;prepare_run(package,file,folder);print(name,'prepared',flush=True);r=run(folder,300);print(r['status'],flush=True)
        results[name]=dict(status=r['status'],run=str(folder));write_json(out/'executed.json',results)
    return results


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['optics','schedule','hooks','intake','planes']);p.add_argument('--out',type=Path,required=True);p.add_argument('--rays',type=int,default=4800000);a=p.parse_args()
    print({'optics':execute_optics,'schedule':execute_schedule,'hooks':execute_hooks,'intake':execute_intake,'planes':execute_planes}[a.mode](a.out,a.rays))


def execute_hooks(out: Path,rays: int=4800000) -> dict:
    from tools.vtc_development import demo,prepare,collect
    from tools.vtc_growth_bridge import run as native_run
    out=fresh_build(out);results={}
    for name,factor in [('disabled',None),('hooks',1.),('report_only',1.25)]:
        inputs=demo(out/(name+'_inputs'),30,rays);req=read_json(inputs/'request.json')
        if factor is not None:
            metadata=dict(source_kind='synthetic_assumed',source_ref='explicit extension mechanics fixture; not fitted biology',cultivar='unvalidated_fixture',uncertainty='unavailable')
            req['parameters']['CURVE_RATIO']=dict(metadata,value=[2,1],by_segment_count={'1':[1]},unit='relative_bend_weights')
            req['parameters']['BENT_FRACTION']=dict(metadata,value=.5,templates=dict(flat_total_bend_deg=0,bent_total_bend_deg=20),unit='fraction')
            req['parameters']['AREA_CORRECTION']=dict(metadata,value=factor,area_basis='summed_one_sided_full_outline_lamina_m2',unit='dimensionless')
        write_json(inputs/'request.json',req);folder=out/name;prepare(inputs,folder)
        print(name,'prepared',flush=True);r=native_run(folder,java='C:/Program Files/Eclipse Adoptium/jre-21.0.12.101-hotspot/bin/java.exe',timeout_s=300);collect(folder)
        results[name]=dict(status=r['status'],exit_code=r['exit_code'],run=str(folder));write_json(out/'executed.json',results);print(name,r['status'],flush=True)
    return results


def execute_intake(out: Path,rays: int=4800000) -> dict:
    from datetime import timedelta
    from tools.vtc_growth_io import aware
    out=fresh_build(out)
    package=ROOT/'build/fsp_integration_20261011_p1_fixture_01'
    s=read_json(ROOT/'build/fsp_integration_20261011_light_02/isolated/scenario.json')
    s.update(observation_route='observed_metric',rays=rays)
    s['lamps'].append(dict(lamp_id='L2',x_m=.15,y_m=.1,z_m=.7,power_umol_s=300,source_kind='synthetic_assumed_staggered_second_lamp'))
    a=aware(s['start_time']);b=a+timedelta(minutes=30);c=b+timedelta(minutes=45)
    def row(x,y,**kw):return dict(start=x.isoformat(),end=y.isoformat(),source_kind='synthetic_assumed',**kw)
    s['extensions']=extension()
    s['extensions']['schedule']=dict(start=a.isoformat(),end=c.isoformat(),interpolation='piecewise_constant',max_step_s=86400,
        lights={'L1':[row(a,b,fraction=1),row(b,c,fraction=0)],'L2':[row(a,b,fraction=0),row(b,c,fraction=.5)]},
        environment=[row(a,c,temp_c=24,co2_ppm=400)])
    path=out/'scenario.json';write_json(path,s);folder=out/'run';prepare_run(package,path,folder);result=run(folder,600)
    return dict(status=result['status'],fixture=True,real_biological_validation=False)


def execute_planes(out: Path,rays: int=4800000) -> dict:
    from tools.vtc_development import demo,prepare,collect
    from tools.vtc_growth_bridge import run as native_run
    out=fresh_build(out);results={}
    for name in ('empty','absorbing_plane'):
        inputs=demo(out/(name+'_inputs'),1,rays);req=read_json(inputs/'request.json');req['extensions']=extension()
        if name=='absorbing_plane':req['extensions']['objects']=[plate('plane',.3,'black',True)]
        write_json(inputs/'request.json',req);folder=out/name;prepare(inputs,folder)
        r=native_run(folder,java='C:/Program Files/Eclipse Adoptium/jre-21.0.12.101-hotspot/bin/java.exe',timeout_s=300);collect(folder)
        results[name]=dict(status=r['status'],exit_code=r['exit_code'],run=str(folder));write_json(out/'executed.json',results);print(name,r['status'],flush=True)
    return results


if __name__=='__main__':main()
