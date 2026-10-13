"""Input contracts and independent checks for returned native development states."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from tools.vtc_growth_io import require, read_json, rows, sha, number, identifier, aware, ratio_table

MODE='vtc_development_v3'
OUTPUTS=('states.csv','events.csv','flux.csv','ledger.csv','meshes.csv','consumed.csv','apices.csv','edges.csv','sensors.csv')
KINDS=['Plant','Axis','Apex','Attachment','CompoundLeaf','Root','Internode','Petiole','RachisSegment','Leaflet','TrussAxis','Flower']
TABLES={
 'plants.csv':'plant_instance_id,source_plant_id,x_m,y_m,z_m,reserve_gC,provenance',
 'environment.csv':'interval,start_time,light_hours,temp_day_c,temp_night_c,co2_ppm,source_kind',
 'lamps.csv':'lamp_id,x_m,y_m,z_m,power_umol_s,source_kind',
 'light_input.csv':'reference_ppfd_umol_m2_s,source_kind,measured_at',
}
PARAMS=set('GERMINATION_DD PHYLLOCHRON_DD BASE_C FIRST_LEAVES CADENCE SP_STOP_RULE FLOWERS PAIRS EMERGENCE_DAYS CARBON_FRACTION EFFICIENCY AMAX ALPHA THETA INTERNODE_CAP_M STEM_WIDTH_M SLA_M2_G LEAF_LW PETIOLE_M RACHIS_M RACHIS_WIDTH_M TRUSS_M FLOWER_M DIVERGENCE_DEG COMPOUND_INSERTION_DEG TOTAL_BEND_DEG BASAL_LEAFLET_ANGLE_DEG MIDDLE_RAMP MAX_MASS MID_DD K MAINT'.split())
PARAMS.update(('GRID_X','GRID_Y','GRID_Z','GRID_SPACING'))
BASE_PARAMS=PARAMS.copy()
PARAMS.update(('CURVE_RATIO','BENT_FRACTION','AREA_CORRECTION'))


def load_package(folder: Path) -> dict:
    req=read_json(folder/'request.json')
    for key,value in dict(schema_version='vtc-development-3',mode=MODE,frame='plant_local_mm',
        run_status='assumption_conditioned',biological_validation='not_established',nutrient_feedback_enabled=False,
        physiology_temperature_response=False,physiology_co2_response=False,light_ratio_role='comparison_only').items():
        require(req.get(key)==value,f'unsupported {key}; no subset fallback')
    from tools.fsp_extensions import interval_seconds,boundary_time,validate_extensions,HOOKS
    require(req.get('dt_s')==86400 or (req.get('integration_contract')=='fsp-integration-1' and req.get('fixture') is True and req.get('dt_s')==43200),'unsupported dt_s; half-day is fixture refinement only')
    require(not req.get('schedule_intervals') or req.get('extensions',{}).get('schedule'),'schedule needs extension contract')
    require(type(req['fixture']) is bool,'fixture flag required')
    require(req['initialization_route'] in ('seed','stage2_observation_fixture','stage2_observation_conditioned','p1_conditioned'),'unsupported initialization route; no seed substitution')
    if req['initialization_route']=='p1_conditioned':require(req.get('integration_contract')=='fsp-integration-1','missing integration contract')
    n=req['intervals'];require(type(n) is int and 1<=n<=365,'interval count must be 1..365')
    require(type(req['freeze_at']) is int and -1<=req['freeze_at']<n,'freeze boundary invalid')
    start=aware(req['start_time'])
    for k in ('run_id','scenario_id'):identifier(req[k])
    require(BASE_PARAMS<=set(req['parameters'])<=PARAMS,'parameter registry incomplete or unknown fields')
    par=req['parameters']
    for k,p in par.items():
        require(p.get('source_kind') in ('user_assumed','synthetic_assumed','literature_other_cultivar'),'coefficient cannot be promoted to measured')
        require(all(p.get(f) for f in ('unit','source_ref','cultivar','uncertainty')),'parameter provenance incomplete')
        if k=='SP_STOP_RULE':require(p['value']=='two_successive_trusses','unsupported stop rule');continue
        if k in HOOKS:continue
        vals=p['value'] if isinstance(p['value'],list) else [p['value']]
        require(bool(vals),'empty parameter')
        for v in vals:number(v,k,None if k in ('GRID_X','GRID_Y','GRID_Z') else 0)
    for k in ('MAX_MASS','MID_DD','K','MAINT'):require(len(par[k]['value'])==len(KINDS),'organ coefficient coverage')
    for k in ('CARBON_FRACTION','EFFICIENCY','THETA'):require(0<par[k]['value']<=1,'fraction out of range')
    for k in ('PHYLLOCHRON_DD','SLA_M2_G','LEAF_LW','INTERNODE_CAP_M'):require(par[k]['value']>0,'positive parameter required')
    for k in ('FIRST_LEAVES','FLOWERS','EMERGENCE_DAYS'):require(type(par[k]['value']) is int and par[k]['value']>0,'integer parameter required')
    for k in ('PAIRS','CADENCE'):
        require(all(type(x) is int and (1 if k=='PAIRS' else 0)<=x<=20 for x in par[k]['value']),'rank/cadence value invalid')
    require(par['CADENCE']['value'][-1]==0,'conditional stop cadence must end in zero')
    for i in range(5):require(par['MAX_MASS']['value'][i]==par['MAINT']['value'][i]==0,'aggregate tissue double counting')
    for i in range(5,len(KINDS)):
        require(par['MAX_MASS']['value'][i]>0 and par['MID_DD']['value'][i]>0 and par['K']['value'][i]>0,'missing tissue demand')
        require(par['MAINT']['value'][i]>0,'unimplemented tissue maintenance cannot be silently zero')
    runtime=req['runtime']
    require(type(runtime['rays']) is int and 1<=runtime['rays']<=100000000,'invalid rays')
    require(type(runtime['seed']) is int and 0<=runtime['seed']<=2147483647,'invalid seed')
    require(0<number(runtime['balance_tolerance_gC'],'tolerance')<=1e-6,'unsafe tolerance')
    tables={k:rows(folder/k,h) for k,h in TABLES.items()}
    plants=tables['plants.csv'];require(bool(plants),'empty plant inventory')
    require(type(req.get('receiver_index',-1)) is int and -1<=req.get('receiver_index',-1)<len(plants),'receiver index invalid')
    require(type(req.get('receiver_day',-1)) is int and -1<=req.get('receiver_day',-1)<n,'receiver freeze day invalid')
    require((req.get('receiver_index',-1)<0)==(req.get('receiver_day',-1)<0),'receiver diagnostic requires index and day')
    require(len({p['plant_instance_id'] for p in plants})==len(plants),'duplicate plant ID')
    for p in plants:
        for k in ('plant_instance_id','source_plant_id'):identifier(p[k])
        for k in ('x_m','y_m','z_m'):number(p[k],k)
        number(p['reserve_gC'],'initial reserve',0);require(p['provenance'],'missing initial-state provenance')
    env=tables['environment.csv'];require(len(env)==n,'climate coverage')
    for i,e in enumerate(env):
        require(e['interval']==str(i) and aware(e['start_time'])==boundary_time(req,i),'environment timing mismatch')
        require(0<=number(e['light_hours'],'hours')<=interval_seconds(req,i)/3600,'photoperiod invalid')
        for k in ('temp_day_c','temp_night_c','co2_ppm'):number(e[k],k)
        require(e['source_kind'],'environment evidence missing')
    require(bool(tables['lamps.csv']),'lamps missing')
    require(len({l['lamp_id'] for l in tables['lamps.csv']})==len(tables['lamps.csv']),'duplicate lamp')
    for lamp in tables['lamps.csv']:
        identifier(lamp['lamp_id'])
        for k in ('x_m','y_m','z_m'):number(lamp[k],k)
        number(lamp['power_umol_s'],'power',0);require(lamp['source_kind'],'lamp provenance missing')
    validate_extensions(req,tables)
    from tools.fsp_axes import validate_records,enabled
    validate_records(req,{p['plant_instance_id'] for p in plants})
    require(not enabled(req) or req['initialization_route']=='p1_conditioned','declared axes require explicit P1 initialization')
    require(len(tables['light_input.csv'])==1,'one reference light required')
    light=tables['light_input.csv'][0];number(light['reference_ppfd_umol_m2_s'],'reference light',0)
    require(light['source_kind'] in ('user_assumed','synthetic_assumed','measured'),'light evidence invalid')
    if light['source_kind']=='measured':require(not req['fixture'],'fixture cannot establish measured light');aware(light['measured_at'])
    pointer=(folder/'light_ratio_latest.txt').read_text(encoding='utf-8-sig').strip()
    require(pointer and '\n' not in pointer and '\r' not in pointer and not Path(pointer).is_absolute(),'one relative pointer required')
    target=(folder/pointer).resolve();ratios=ratio_table(target)
    names=[*TABLES,'request.json','light_ratio_latest.txt']
    if req['initialization_route']!='seed':
        if req['initialization_route']=='p1_conditioned':
            from tools.tomato_fsp_io import validate_native_inputs as validate_initial
        else:
            from tools.vtc_development_observation import validate_initial
        names+=validate_initial(folder,req,plants)
        tables['initial_state.csv']=rows(folder/'initial_state.csv')
    hashes={name:sha(folder/name) for name in names};hashes['resolved_ratio_target']=sha(target)
    result=dict(request=req,tables=tables,source_hashes=hashes,ratio_target=str(target),ratios=ratios)
    if req.get('integration_contract')=='fsp-integration-1':
        result['integration_geometry']=read_json(folder/'integration_geometry.json')
        from tools.fsp_extensions import validate_scene_partition
        validate_scene_partition(req,result['integration_geometry'])
        from tools.tomato_fsp_native_boundary import validate_options
        validate_options(req,tables['initial_state.csv'],result['integration_geometry'])
        result['integration_shape_counts']={k:len(v)*3 for k,v in result['integration_geometry']['triangles_mm'].items()}
    elif any(k in req for k in ('native_boundary','imported_shape_api','resource_hook')):
        require(False,'boundary_requires_imported_integration')
    return result


def validate_outputs(pkg: dict, native: Path, binding: dict, checkpoint: bool=False) -> dict:
    from tools.fsp_extensions import interval_seconds,validate_native_optics,validate_hook_geometry,OUTPUTS as EXT_OUTPUTS
    req=pkg['request'];done=read_json(native/'completion.json');n=done['intervals'] if checkpoint else req['intervals']
    dt_days=req['dt_s']/86400
    integrated=req.get('integration_contract')=='fsp-integration-1'
    require(not checkpoint or (integrated and done.get('checkpoint') is True and 1<=n<=req['intervals']),'invalid checkpoint')
    require(done.get('mode')==MODE and done['run_id']==req['run_id'] and done['intervals']==n,'wrong mode/run/count')
    for k,v in binding.items():require(done[k]==v,'completion binding mismatch')
    names=set(OUTPUTS)|({'proposals.csv'} if integrated else set())
    if req.get('extensions'):names.update(EXT_OUTPUTS)
    from tools.fsp_axes import enabled,validate_axis_outputs,allocation_reference
    if enabled(req):names.add('axis_flux.csv')
    if checkpoint:names.remove('sensors.csv')
    from tools.tomato_fsp_native_boundary import files as boundary_files,validate_output as validate_boundary
    if req.get('native_boundary'):names.update(boundary_files(n))
    require(set(done['files'])==names,'native output manifest mismatch')
    for name in names:require(sha(native/name)==done['files'][name],f'native hash mismatch: {name}')
    data={name:rows(native/name) for name in names if name.endswith('.csv')}
    validate_boundary(pkg,native,data,n,binding)
    validate_native_optics(pkg,data,n)
    validate_hook_geometry(pkg,data)
    validate_axis_outputs(pkg,data,n)
    if req.get('light_only'):
        from tools.tomato_fsp_io import validate_light_only
        return validate_light_only(pkg,data,n)
    states=data['states.csv'];events=data['events.csv'];par={k:v['value'] for k,v in req['parameters'].items()}
    tol=req['runtime']['balance_tolerance_gC']
    def close(a: float,b: float,label: str,atol: float=tol) -> None:
        require(math.isclose(a,b,rel_tol=3e-7,abs_tol=atol),f'{label}: {a} != {b}')
    def f(row: dict,key: str) -> float:return number(row[key],key)
    smap={(int(s['day']),s['organ_id']):s for s in states};require(len(smap)==len(states),'duplicate organ state')
    days=defaultdict(dict)
    for (day,oid),s in smap.items():days[day][oid]=s
    require(set(days)==set(range(n+1)),'state coverage')
    plant_map={p['plant_instance_id']:p for p in pkg['tables']['plants.csv']}
    flux={(int(r['interval']),r['organ_id']):r for r in data['flux.csv']};require(len(flux)==len(data['flux.csv']),'duplicate flux')
    expected_flux={(day-1,oid) for day,ss in days.items() if day>0 for oid in ss}
    require(set(flux)==expected_flux,'dynamic flux inventory mismatch')
    lmap={(int(r['interval']),r['plant_instance_id']):r for r in data['ledger.csv']}
    require(len(lmap)==len(data['ledger.csv'])==n*len(plant_map),'plant ledger coverage')
    event_keys=[(e['organ_id'],e['event']) for e in events];require(len(set(event_keys))==len(event_keys),'duplicate birth/lifecycle event')
    emap={(e['organ_id'],e['event']):e for e in events}
    if req['initialization_route']!='seed':
        initial={s['organ_id']:s for s in pkg['tables']['initial_state.csv']}
        require(set(initial)==set(days[0]),'observation identity round-trip failed')
        for oid,row in initial.items():
            for key,value in row.items():
                if key in ('day',):continue
                if key in ('organ_id','parent_id','axis_id','developmental_axis_id','plant_instance_id','source_plant_id','class','provenance','segment_index'):
                    require(days[0][oid][key]==value,'observation identity/provenance changed')
                else:close(f(days[0][oid],key),number(value,key),'observation value round-trip')
    first_seen={};max_residual=0;birth_carbon=0
    imported={s['organ_id']:s for s in pkg['tables'].get('initial_state.csv',[])} if integrated else {}
    for day in range(n+1):
        if day>0:dt_days=interval_seconds(req,day-1)/86400
        require(set(days.get(day-1,{}))<=set(days[day]),'organ disappeared or renumbered')
        for oid,s in days[day].items():
            pid=s['plant_instance_id'];require(pid in plant_map and s['source_plant_id']==plant_map[pid]['source_plant_id'],'plant identity changed')
            require(s['class'] in KINDS,'unknown organ class');kind=KINDS.index(s['class'])
            require(s['provenance'] in ('model_generated','observation_fixture','observed','conditional_hidden_state'),'provenance promotion')
            for k in ('mass_gDM','max_mass_gDM','thermal_age_dd','length_m','width_m','area_m2'):require(f(s,k)>=0,'negative state')
            for k in ('x_m','y_m','z_m','tip_x_m','tip_y_m','tip_z_m','azimuth_deg','elevation_deg','rachis_bend_alpha_deg'):f(s,k)
            if s['parent_id']:
                require(s['parent_id'] in days[day],'orphan organ')
                require(days[day][s['parent_id']]['plant_instance_id']==pid,'cross-plant parent')
                seen={oid};parent=s['parent_id']
                while parent:
                    require(parent in days[day],'orphan ancestor')
                    require(parent not in seen,'topology cycle');seen.add(parent);parent=days[day][parent]['parent_id']
            else:require(kind==0,'only plant may lack parent')
            segment=s.get('developmental_axis_id',s['axis_id'])
            if segment:require(segment in days[day] and days[day][segment]['class']=='Axis','invalid axis')
            born=int(s['birth_day']);require(born<=day and (born>=0 or req['initialization_route']!='seed'),'invalid birth time')
            if oid not in first_seen:
                first_seen[oid]=day;require(born==day or (day==0 and req['initialization_route']!='seed'),'birth first-state mismatch')
                if day>0:
                    event=emap.get((oid,'initiation'));require(event is not None and int(event['day'])==day and event['parent_id']==s['parent_id'],'birth event missing')
                    close(f(s,'mass_gDM'),0,'zero-age birth cannot manufacture mass')
            if day>0:
                previous=days[day-1].get(oid)
                if previous:
                    for k in ('parent_id','axis_id','class','birth_day','true_leaf_order','source_plant_id','provenance'):require(s[k]==previous[k],'stable identity changed')
                    climate=pkg['tables']['environment.csv'][day-1];h=float(climate['light_hours'])
                    dd=max(0,(float(climate['temp_day_c'])*h+float(climate['temp_night_c'])*(24*dt_days-h))/(24*dt_days)-par['BASE_C'])*dt_days
                    close(f(s,'thermal_age_dd'),f(previous,'thermal_age_dd')+dd,'thermal age continuity')
                r=flux[day-1,oid];require(r['plant_instance_id']==pid,'flux owner mismatch')
                old=f(previous,'mass_gDM') if previous else 0
                for k in ('gross_gC','maintenance_gC','target_gDM','demand_gC','allocated_gC','structural_gC','growth_resp_gC','absorbed_umol_s'):require(f(r,k)>=-tol,'negative flux')
                close(f(r,'maintenance_gC'),old*par['MAINT'][kind]*dt_days,'maintenance once per tissue')
                s0=1/(1+math.exp(par['K'][kind]*par['MID_DD'][kind]));sig=1/(1+math.exp(-par['K'][kind]*(f(s,'thermal_age_dd')-par['MID_DD'][kind])))
                target=f(s,'max_mass_gDM')*max(0,min(1,(sig-s0)/(1-s0)))
                close(f(r,'target_gDM'),target,'age-dependent sink target')
                close(f(r,'demand_gC'),max(0,target-old)*par['CARBON_FRACTION']/par['EFFICIENCY'],'demand')
                close(f(r,'structural_gC'),f(r,'allocated_gC')*par['EFFICIENCY'],'funded structure')
                close(f(r,'growth_resp_gC'),f(r,'allocated_gC')*(1-par['EFFICIENCY']),'growth respiration')
                close(f(s,'mass_gDM'),old+f(r,'structural_gC')/par['CARBON_FRACTION'],'mass continuity')
                expected_gross=0
                if kind==9 and previous and f(previous,'area_m2')>0:
                    area=f(previous,'area_m2');q=f(r,'absorbed_umol_s')/area;a=par['ALPHA'];b=par['AMAX'];t=par['THETA']
                    expected_gross=(a*q+b-math.sqrt((a*q+b)**2-4*t*a*q*b))/(2*t)*area*float(pkg['tables']['environment.csv'][day-1]['light_hours'])*3600*12.011e-6
                else:close(f(r,'absorbed_umol_s'),0,'pre-emergence/nonleaf photons')
                close(f(r,'gross_gC'),expected_gross,'leaflet NRH exchange')
                if old==0 and f(s,'mass_gDM')>0:
                    birth_carbon+=f(r,'structural_gC')
                    ev=emap.get((oid,'funded_birth'));require(ev is not None and int(ev['day'])==day,'first funding event missing')
                    close(float(ev['structural_gC']),f(r,'structural_gC'),'funded birth carbon')
            rx=req.get('receiver_index',-1);rx_pid=pkg['tables']['plants.csv'][rx]['plant_instance_id'] if rx>=0 else None
            frozen=(req['freeze_at']>=0 and day>req['freeze_at']) or (pid==rx_pid and day>req['receiver_day'])
            if kind==9 and int(s['emergence_day'])>=0 and not frozen:
                sla=f(imported[oid],'area_m2')/f(imported[oid],'mass_gDM') if oid in imported else par['SLA_M2_G']
                close(f(s,'area_m2'),f(s,'mass_gDM')*sla,'mass-funded leaf area')
                if oid not in imported:close(f(s,'area_m2'),f(s,'length_m')*f(s,'width_m')/2,'polygon area (not rectangle)')
            if f(s,'mass_gDM')==0:close(f(s,'length_m')*f(s,'width_m'),0,'zero-mass optical tissue')
            if kind<5:close(f(s,'mass_gDM'),0,'aggregate double counting')
            if kind==6 and not frozen and oid not in imported:
                close(f(s,'length_m'),par['INTERNODE_CAP_M']*(f(s,'mass_gDM')/f(s,'max_mass_gDM'))**(1/3),'funded internode')
            if int(s['emergence_day'])>=0 and not (int(s['emergence_day'])==0 and req['initialization_route']!='seed'):
                ev=emap.get((oid,'emergence'));require(ev is not None and int(ev['day'])==int(s['emergence_day']),'emergence event missing')
                close(float(ev['structural_gC']),f(flux[int(ev['day'])-1,oid],'structural_gC'),'birth carbon transaction')
        if day==0:continue
        for pid in plant_map:
            i=day-1;l=lmap.get((i,pid));require(l is not None,'missing plant ledger')
            subset=[flux[i,oid] for oid,s in days[day].items() if s['plant_instance_id']==pid]
            start=float(plant_map[pid]['reserve_gC']) if i==0 else f(lmap[i-1,pid],'reserve_end_gC')
            close(f(l,'reserve_start_gC'),start,'reserve continuity')
            for k in ('gross_gC','maintenance_gC','structural_gC','growth_resp_gC'):close(f(l,k),sum(f(r,k) for r in subset),'plant sum '+k)
            budget=start+f(l,'gross_gC')-f(l,'maintenance_gC');total=sum(f(r,'demand_gC') for r in subset);funded=min(max(0,budget),total)
            if enabled(req):
                scales={a['axis_id']:a['parameters']['SUBSTEM_SINK_SCALE']['value'] for a in req['axes'] if a['plant_instance_id']==pid}
                expected=allocation_reference([f(r,'demand_gC') for r in subset],[scales[r['axis_id']] for r in subset],budget)
                for r,value in zip(subset,expected):close(f(r,'allocated_gC'),value,'axis-weighted capped sink allocation')
            else:
                for r in subset:close(f(r,'allocated_gC'),funded*f(r,'demand_gC')/total if total else 0,'sink allocation')
            close(f(l,'reserve_end_gC'),max(0,budget-funded),'reserve remainder')
            residual=budget-f(l,'structural_gC')-f(l,'growth_resp_gC')-f(l,'reserve_end_gC');max_residual=max(max_residual,abs(residual))
            close(f(l,'residual_gC'),residual,'carbon residual')
            require(abs(residual)<=tol and f(l,'deficit_gC')<=tol,'unfunded obligations; carbon deficit')
    mesh={(int(r['state']),r['organ_id'],int(r['vertex'])):tuple(f(r,k) for k in ('x_m','y_m','z_m')) for r in data['meshes.csv']}
    con={(int(r['state']),r['organ_id'],int(r['vertex'])):tuple(f(r,k) for k in ('x_m','y_m','z_m')) for r in data['consumed.csv']}
    require(len(mesh)==len(data['meshes.csv']) and len(con)==len(data['consumed.csv']),'duplicate mesh vertex')
    require(con=={k:v for k,v in mesh.items() if k[0]<n},'stale consumed native geometry')
    edges={(int(e['day']),e['parent_id'],e['child_id']) for e in data['edges.csv']}
    require(len(edges)==len(data['edges.csv']),'duplicate native graph edge')
    require(edges=={(day,s['parent_id'],oid) for day,ss in days.items() for oid,s in ss.items() if s['parent_id']},'actual native graph parent mismatch')
    for day,ss in days.items():
        children=defaultdict(list)
        for oid,s in ss.items():children[s['parent_id']].append(s)
        for oid,s in ss.items():
            if s['class']!='CompoundLeaf':continue
            if oid in imported:continue
            descendants=[];todo=list(children[oid])
            while todo:
                child=todo.pop();descendants.append(child);todo.extend(children[child['organ_id']])
            rank=int(s['true_leaf_order']);m=par['PAIRS'][min(rank-1,len(par['PAIRS'])-1)]
            blades=[c for c in descendants if c['class']=='Leaflet'];rach=[c for c in descendants if c['class']=='RachisSegment']
            require(len(blades)==2*m+1 and len(rach)==m,'rank-indexed compound inventory')
            require({(int(c['pair_index']),int(c['side'])) for c in blades}=={(i,side) for i in range(1,m+1) for side in (-1,1)}|{(m+1,0)},'terminal/pair identity mismatch')
            require(len([c for c in descendants if c['class']=='Petiole'])==1,'petiole inventory')
        shape_counts=pkg.get('integration_shape_counts',{})
        expected={(day,oid,i) for oid,s in ss.items() if f(s,'length_m')>0 and f(s,'width_m')>0 and s['class']!='Root' for i in range(shape_counts.get(oid,6))}
        require({k for k in mesh if k[0]==day}==expected,'funded mesh coverage')
        for oid,s in ss.items():
            if (day,oid,0) not in mesh:continue
            area=0
            for offset in range(0,shape_counts.get(oid,6),3):
                a,b,c=[mesh[day,oid,offset+j] for j in range(3)];u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
                cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];area+=math.sqrt(sum(t*t for t in cross))/2
            close(area,f(s,'area_m2') if oid in shape_counts else f(s,'length_m')*f(s,'width_m')/2,'actual native triangle area',1e-8)
            if s['class']=='CompoundLeaf':require(False,'compound envelope masquerading as mesh')
    stop_events=[e for e in events if e['event']=='determinate_stop']
    for e in stop_events:
        pid=days[int(e['day'])][e['organ_id']]['plant_instance_id']
        axis=days[int(e['day'])][e['organ_id']]['axis_id']
        require(not any(int(s['birth_day'])>int(e['day']) for s in days[n].values() if s['plant_instance_id']==pid and (not enabled(req) or s['axis_id']==axis)),'new organ after declared axis stop')
    if not checkpoint and req.get('native_boundary'):
        require(not data['sensors.csv'],'external_reference_sensor_grid_must_be_unavailable')
    if not checkpoint and not req.get('native_boundary'):
        sensors=data['sensors.csv']
        require(len(sensors)==16 and {(r['grid_row'],r['grid_col']) for r in sensors}=={(str(i),str(j)) for i in range(1,5) for j in range(1,5)},'sensor coverage')
        for s in sensors:require(f(s,'absorbed_umol_s')>=0,'negative sensor light');close(f(s,'area_m2'),.0004,'sensor area')
    if integrated:
        from tools.tomato_fsp_io import validate_integration_geometry
        validate_integration_geometry(pkg,data,n)
    if req['initialization_route']=='seed':
        # Independent developmental clock: verifies events without calling native code.
        clock=0.;produced=0;leaves=0;trusses=0;axis_leaves=0;stopped=False
        for day in range(1,n+1):
            dt_days=interval_seconds(req,day-1)/86400
            e=pkg['tables']['environment.csv'][day-1];h=float(e['light_hours'])
            clock+=max(0,(float(e['temp_day_c'])*h+float(e['temp_night_c'])*(24*dt_days-h))/(24*dt_days)-par['BASE_C'])*dt_days
            due=math.floor((clock-par['GERMINATION_DD'])/par['PHYLLOCHRON_DD'])
            if req['freeze_at']<0 or day-1<req['freeze_at']:
                while produced<due and not stopped:
                    produced+=1;target=par['FIRST_LEAVES'] if trusses==0 else par['CADENCE'][min(trusses-1,len(par['CADENCE'])-1)]
                    if axis_leaves<target:leaves+=1;axis_leaves+=1
                    else:
                        trusses+=1;stopped=trusses>1 and target==0;axis_leaves=0
            for pid in plant_map:
                ps=[s for s in days[day].values() if s['plant_instance_id']==pid]
                rx=req.get('receiver_index',-1)
                if rx>=0 and pid==pkg['tables']['plants.csv'][rx]['plant_instance_id'] and day>req['receiver_day']:
                    require({s['organ_id'] for s in ps}=={s['organ_id'] for s in days[req['receiver_day']].values() if s['plant_instance_id']==pid},'fixed receiver topology changed')
                    continue
                require(sum(s['class']=='CompoundLeaf' for s in ps)==leaves,'native compound schedule mismatch')
                require(sum(s['class']=='TrussAxis' for s in ps)==trusses,'native truss schedule mismatch')
                require(sum(s['class']=='Flower' for s in ps)==trusses*par['FLOWERS'],'flower unit inventory mismatch')
                require(sum(s['class']=='Root' for s in ps)==1,'root compartment inventory')
    return dict(software_status='verified_native_trajectory',run_status='assumption_conditioned',biological_validation='not_established',nutrient_feedback_enabled=False,
        intervals=n,initial_organs=len(days[0]),final_organs=len(days[n]),new_organs=len(days[n])-len(days[0]),determinate_stops=len(stop_events),
        max_carbon_residual_gC=max_residual,first_funded_tissue_carbon_gC=birth_carbon,spinup_30_executed=sum(interval_seconds(req,i) for i in range(n))>=30*86400 and req['initialization_route']=='seed',
        quantitative_light_sampling=req['runtime']['rays']>=4800000,overall_v3_acceptance='pending_cross_scenario_acceptance')
