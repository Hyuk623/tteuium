"""Reproducible actual-runtime scenario suite for conditional VTC development."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.vtc_growth_io import ROOT, fresh_build, read_json, write_json, rows, write_csv, sha, require, ContractError
from tools.vtc_development import demo,prepare,collect
from tools.vtc_growth_bridge import run
from tools.vtc_development_observation import fixture_from_native


def shift_fixture(folder: Path) -> None:
    """Declared canopy placement only, no biological state update."""
    state=rows(folder/'initial_state.csv')
    for s in state:
        if s['plant_instance_id']=='p1':
            for k,v in [('x_m',.07),('tip_x_m',.07),('z_m',.13),('tip_z_m',.13)]:s[k]=str(float(s[k])+v)
    write_csv(folder/'initial_state.csv',state);smap={s['organ_id']:s for s in state}
    vertices=rows(folder/'mtg_vertices.csv')
    for v in vertices:
        s=smap[v['vertex_id']]
        for name,keys in [('base_xyz_mm',('x_m','y_m','z_m')),('tip_xyz_mm',('tip_x_m','tip_y_m','tip_z_m'))]:v[name]=json.dumps([float(s[k])*1000 for k in keys])
    write_csv(folder/'mtg_vertices.csv',vertices)
    plants=rows(folder/'plants.csv');plants[0]['x_m']=str(float(plants[0]['x_m'])+.07);plants[0]['z_m']=str(float(plants[0]['z_m'])+.13);write_csv(folder/'plants.csv',plants)
    m=read_json(folder/'observation_manifest.json');m['transform_source']='synthetic_upper_plant_offset_x70mm_z130mm'
    m['files']={name:sha(folder/name) for name in m['files']};write_json(folder/'observation_manifest.json',m)


def execute(inputs: Path,out: Path,expected_failure: bool=False) -> dict:
    prepare(inputs,out)
    try:
        run(out,timeout_s=1200)
        result=collect(out)
        require(not expected_failure,'expected deficit unexpectedly passed')
        return dict(path=str(out),status='verified',new_organs=result['new_organs'],stops=result['determinate_stops'],max_residual_gC=result['max_carbon_residual_gC'])
    except ContractError as e:
        if not expected_failure:raise
        require('deficit' in str(e) and not (out/'results').exists(),'unexpected failure mechanism')
        return dict(path=str(out),status='expected_deficit_rejected',error=str(e))


def suite(out: Path) -> dict:
    out=fresh_build(out);reports={}
    def add(name: str,inputs: Path,fail: bool=False) -> None:
        reports[name]=execute(inputs,out/name,fail);write_json(out/'progress.json',reports)
        print(name+': '+reports[name]['status'],flush=True)
    for name,scenario,n,rays in [('sufficient','sufficient',65,300000),('limited','limited',65,300000),('frozen','frozen',65,300000),
        ('dark_funded','dark',20,100000),('dark_empty','dark_empty',65,10000),('dark_deficit','dark',65,100000),('three_pairs','sufficient',65,300000)]:
        inp=demo(out/(name+'_inputs'),n,rays,scenario)
        if name=='three_pairs':
            req=read_json(inp/'request.json');req['parameters']['PAIRS']['value']=[1,1,3];write_json(inp/'request.json',req)
        if name=='dark_funded':
            ps=rows(inp/'plants.csv')
            for p in ps:p['reserve_gC']=.2
            write_csv(inp/'plants.csv',ps)
        add(name,inp,name=='dark_deficit')
    add('replay',out/'sufficient/inputs')
    observation=fixture_from_native(out/'sufficient',out/'observation_inputs',30,8)
    add('observation',observation)
    for name,frozen,seed in [('feedback',False,5000),('feedback_frozen',True,5000),('feedback_seed',False,5100)]:
        inp=fixture_from_native(out/'sufficient',out/(name+'_inputs'),30,8);shift_fixture(inp)
        req=read_json(inp/'request.json');req.update(receiver_index=1,receiver_day=0,freeze_at=0 if frozen else -1)
        req['runtime'].update(rays=4800000,seed=seed);write_json(inp/'request.json',req)
        add(name,inp)
    return summarize(out)


def summarize(out: Path) -> dict:
    reports=read_json(out/'progress.json')
    for name,r in reports.items():
        if r['status']=='verified':
            from tools.vtc_development import verify_prepared
            from tools.vtc_development_io import validate_outputs
            prepared,pkg=verify_prepared(out/name);validate_outputs(pkg,out/name/'working',prepared['binding'])
    def total(name: str,day: int) -> float:return sum(float(s['mass_gDM']) for s in rows(out/name/'results/states.csv') if int(s['day'])==day)
    require(total('sufficient',65)>total('limited',65),'carbon causality failed')
    require(total('dark_funded',20)>0 and total('dark_empty',65)==0,'dark/reserve causality failed')
    # Native event/topology replay, numeric values allow floating summation noise only.
    a=rows(out/'sufficient/results/states.csv');b=rows(out/'replay/results/states.csv')
    amap={(x['day'],x['organ_id']):x for x in a};bmap={(x['day'],x['organ_id']):x for x in b};require(amap.keys()==bmap.keys(),'replay topology mismatch')
    maximum=max(abs(float(amap[k][f])-float(bmap[k][f])) for k in amap for f in ('mass_gDM','length_m','area_m2'))
    require(maximum<1e-10,'replay mismatch')
    ea=rows(out/'sufficient/results/events.csv');eb=rows(out/'replay/results/events.csv')
    require(len(ea)==len(eb),'replay event count mismatch')
    for x,y in zip(ea,eb):
        require(all(x[k]==y[k] for k in x if k!='structural_gC'),'replay event identity/time mismatch')
        require(abs(float(x['structural_gC'])-float(y['structural_gC']))<1e-10,'replay event carbon mismatch')
    light={}
    for name in ('feedback','feedback_frozen','feedback_seed'):
        flux=rows(out/name/'results/flux.csv');light[name]=[sum(float(r['absorbed_umol_s']) for r in flux if int(r['interval'])==i and r['plant_instance_id']=='p2') for i in range(8)]
    require(abs(light['feedback'][0]-light['feedback_frozen'][0])<1e-8,'initial feedback control differs')
    require(max(light['feedback_frozen'])-min(light['feedback_frozen'])<1e-8,'frozen receiver illumination changed')
    require(light['feedback'][-1]<light['feedback_frozen'][-1],'dynamic shading not demonstrated')
    effect=light['feedback_frozen'][-1]-light['feedback'][-1]
    seed_noise=max(abs(x-y) for x,y in zip(light['feedback'],light['feedback_seed']))
    require(effect>seed_noise,'feedback effect does not exceed observed seed variation')
    report=dict(status='software_scenario_checks_passed',mode='vtc_development_v3',biological_validation='not_established',
        scenarios=reports,final_mass_gDM={k:total(k,65) for k in ('sufficient','limited','dark_empty','frozen')},
        replay_max_numeric_difference=maximum,receiver_absorbed_umol_s=light,shading_effect_umol_s=effect,max_two_seed_difference_umol_s=seed_noise,
        acceptance_status='requires_execution_report_review',nutrient_feedback_enabled=False)
    write_json(out/'acceptance.json',report);return report


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);p.add_argument('--summarize-existing',action='store_true');a=p.parse_args()
    print(json.dumps(summarize(a.out) if a.summarize_existing else suite(a.out),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
