"""Prepare, execute and collect explicitly selected native VTC development."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from tools.vtc_growth_io import ROOT, ContractError, require, sha, digest, fresh_build, read_json, write_json, rows, write_csv
from tools.vtc_growth_fork import DEFAULT_SOURCE, nrh_fragment
from tools.vtc_development_io import MODE, OUTPUTS, load_package, validate_outputs

CONTRACT=ROOT/'handoff/VTC_DEVELOPMENT_SCIENCE_AND_IO_CONTRACT_V3_2026-10-11.md'
NATIVE=ROOT/'tools/vtc_development_native.rgg'
KINDS=['Plant','Axis','Apex','Attachment','CompoundLeaf','Root','Internode','Petiole','RachisSegment','Leaflet','TrussAxis','Flower']


def parameters() -> dict:
    """Explicit conditional scenario registry; none of these are fitted values."""
    vals={
        'GERMINATION_DD':(206.3,'degree_day'), 'PHYLLOCHRON_DD':(37.9,'degree_day'),
        'BASE_C':(5.7,'degC'), 'FIRST_LEAVES':(9,'count'), 'CADENCE':([2,1,0],'leaves_between_trusses'),
        'SP_STOP_RULE':('two_successive_trusses','rule'), 'FLOWERS':(4,'count'), 'PAIRS':([1,1,2],'pairs_by_true_leaf_order_last_repeated'),
        'EMERGENCE_DAYS':(1,'day'),'CARBON_FRACTION':(.45,'gC/gDM'),'EFFICIENCY':(.75,'gC/gC'),
        'AMAX':(13.57,'umol_CO2/m2/s'),'ALPHA':(.048,'mol_CO2/mol_photon'),'THETA':(.92,'dimensionless'),
        'INTERNODE_CAP_M':(.012,'m'),'STEM_WIDTH_M':(.003,'m'),'SLA_M2_G':(.025,'m2/gDM'),
        'LEAF_LW':(2.,'length/width'),'PETIOLE_M':(.020,'m'),'RACHIS_M':(.035,'m'),'RACHIS_WIDTH_M':(.001,'m'),
        'TRUSS_M':(.025,'m'),'FLOWER_M':(.008,'m'),'DIVERGENCE_DEG':(137.5,'deg'),
        'COMPOUND_INSERTION_DEG':(80.,'deg'),'TOTAL_BEND_DEG':(20.,'deg'),'BASAL_LEAFLET_ANGLE_DEG':(35.,'deg'),
        'MIDDLE_RAMP':(.35,'dimensionless'),
        'GRID_X':(-.15,'m'),'GRID_Y':(-.15,'m'),'GRID_Z':(0.,'m'),'GRID_SPACING':(.10,'m'),
        'MAX_MASS':([0,0,0,0,0,.12,.03,.008,.012,.10,.012,.004],'gDM'),
        'MID_DD':([1,1,1,1,1,400,130,120,130,150,140,120],'degree_day'),
        'K':([0,0,0,0,0,.012,.025,.025,.025,.025,.025,.025],'1/degree_day'),
        'MAINT':([0,0,0,0,0,.0005,.0005,.0005,.0005,.0005,.0005,.0005],'gC/gDM/day'),
    }
    result={k:dict(value=v,unit=u,source_kind='user_assumed',source_ref='V3 explicit conditional hypothesis under user exception',cultivar='Micro-Tom_unfitted_hypothesis',uncertainty='unvalidated; requires measurement or review') for k,(v,u) in vals.items()}
    for key in ('GERMINATION_DD','PHYLLOCHRON_DD','AMAX','ALPHA','THETA'):
        result[key].update(source_kind='literature_other_cultivar',source_ref='VTC parametersMerlice.rgg',cultivar='Merlice')
    result['FIRST_LEAVES']['source_ref']='Earlier fork Carvalho2011 prior: first truss above leaf 9; applicability pending'
    result['PAIRS']['source_ref']='Earlier fork Carvalho2011 candidate; repeated final entry; not fitted'
    return result


def demo(out: Path, intervals: int=65, rays: int=300000, scenario: str='sufficient', seed: int=5000) -> Path:
    out=fresh_build(out)
    start=datetime.fromisoformat('2026-10-11T06:00:00+09:00')
    req=dict(schema_version='vtc-development-3',mode=MODE,run_id=out.name,scenario_id=scenario,
        initialization_route='seed',fixture=True,frame='plant_local_mm',start_time=start.isoformat(),dt_s=86400,intervals=intervals,
        parameters=parameters(),freeze_at=30 if scenario=='frozen' else -1,receiver_index=-1,receiver_day=-1,
        runtime=dict(rays=rays,seed=seed,balance_tolerance_gC=1e-9),run_status='assumption_conditioned',
        biological_validation='not_established',nutrient_feedback_enabled=False,
        optical_assumption='black_full_outline_diamond; hypothetical',physiology_temperature_response=False,physiology_co2_response=False,
        source_plant_scope='main_and_declared_sympodial_axes',light_ratio_role='comparison_only',
        seed_assumption='Explicit initial reserve; root compartment from day 0, no cotyledon or hypocotyl morphology; first true leaves funded after germination')
    write_json(out/'request.json',req)
    write_csv(out/'plants.csv',[dict(plant_instance_id=f'p{i}',source_plant_id=f'synthetic_p{i}',x_m=x,y_m=0,z_m=0,reserve_gC=.06 if scenario!='dark_empty' else 0,provenance='synthetic_assumed') for i,x in [(1,-.035),(2,.035)]])
    write_csv(out/'environment.csv',[dict(interval=i,start_time=(start+timedelta(days=i)).isoformat(),light_hours=14,temp_day_c=26,temp_night_c=22,co2_ppm=400,source_kind='user_assumed') for i in range(intervals)])
    power=0 if scenario.startswith('dark') else 20 if scenario=='limited' else 1200
    write_csv(out/'lamps.csv',[dict(lamp_id='L1',x_m=0,y_m=0,z_m=.6,power_umol_s=power,source_kind='synthetic_assumed_point_LED')])
    write_csv(out/'light_input.csv',[dict(reference_ppfd_umol_m2_s=300,source_kind='user_assumed',measured_at='')])
    write_csv(out/'ratios.csv',[dict(grid_row=r,grid_col=c,ratio_to_mean=1) for r in range(1,5) for c in range(1,5)])
    (out/'light_ratio_latest.txt').write_text('ratios.csv\n',encoding='utf-8')
    return out


def cultivar_module(registry: dict) -> str:
    lines=['// Conditional V3 cultivar parameters. All values have provenance; no fitted Micro-Tom data.']
    ints={'FIRST_LEAVES','FLOWERS','EMERGENCE_DAYS'}
    for k,p in registry.items():
        if k in ('CURVE_RATIO','BENT_FRACTION','AREA_CORRECTION'):continue
        v=p['value']; typ='int' if k in ints else 'String' if isinstance(v,str) else 'double'
        if isinstance(v,list):
            typ='int[]' if k in ('CADENCE','PAIRS') else 'double[]'
            literal='new '+typ+'{'+','.join(str(x) for x in v)+'}'
        else: literal=json.dumps(v)
        lines.append('// '+json.dumps({x:p[x] for x in p if x!='value'},ensure_ascii=True))
        lines.append(f'public static final {typ} {k} = {literal};')
    return '\n'.join(lines)+'\n'


def prepare(package_dir: Path, out: Path, source: Path=DEFAULT_SOURCE) -> dict:
    pkg=load_package(package_dir); out=fresh_build(out)
    frozen=out/'inputs';frozen.mkdir()
    for name in pkg['source_hashes']:
        if name!='resolved_ratio_target':
            shutil.copyfile(package_dir/name,frozen/name)
            require(sha(frozen/name)==pkg['source_hashes'][name], 'source changed while freezing: '+name)
    shutil.copyfile(pkg['ratio_target'],frozen/'ratios_frozen.csv')
    require(sha(frozen/'ratios_frozen.csv')==pkg['source_hashes']['resolved_ratio_target'],'ratio source changed while freezing')
    (frozen/'light_ratio_latest.txt').write_text('ratios_frozen.csv\n',encoding='utf-8')
    frozen_pkg=load_package(frozen)
    # Freeze exact source fragment and evidence; original files stay untouched.
    working=out/'working';working.mkdir()
    registry=pkg['request']['parameters']
    module=cultivar_module(registry);(working/'parametersMicroTom.rgg').write_text(module,encoding='utf-8')
    template=NATIVE.read_text(encoding='utf-8').replace('@NRH@',nrh_fragment(source)).replace('@PARAMETERS@',module)
    engine_hash=digest(dict(template=template,parameters=module,contract_sha256=sha(CONTRACT)))
    binding=dict(input_hash=digest(frozen_pkg['source_hashes']),engine_hash=engine_hash)
    req=pkg['request'];tab=pkg['tables']
    from tools.fsp_extensions import native_code
    extension_code,max_depth=native_code(req,tab,working)
    from tools.tomato_fsp_native_boundary import native_code as boundary_code
    boundary_extension=boundary_code(req)
    from tools.fsp_axes import native_setup,export_registry
    axis_code,axis_count,_=native_setup(req,tab['plants.csv'])
    binding['engine_hash']=digest(dict(base_engine_hash=engine_hash,extension_code=extension_code,axis_code=axis_code,boundary_code=boundary_extension))
    def arr(values: list, typ: str='double') -> str:return 'new '+typ+'[]{'+','.join(json.dumps(v) for v in values)+'}'
    mapping=dict(BOUNDARY_CODE=boundary_extension,AXIS_CODE=axis_code,NA=axis_count,EXTENSION_CODE=extension_code,MAX_DEPTH=max_depth,PLANT_IDS=arr([p['plant_instance_id'] for p in tab['plants.csv']],'String'),SOURCE_IDS=arr([p['source_plant_id'] for p in tab['plants.csv']],'String'),
        PX=arr([float(p['x_m']) for p in tab['plants.csv']]),PY=arr([float(p['y_m']) for p in tab['plants.csv']]),PZ=arr([float(p['z_m']) for p in tab['plants.csv']]),
        RESERVES=arr([float(p['reserve_gC']) for p in tab['plants.csv']]),NP=len(tab['plants.csv']),N=req['intervals'],SEED=req['runtime']['seed'],RAYS=req['runtime']['rays'],FREEZE_AT=req['freeze_at'],RECEIVER_INDEX=req.get('receiver_index',-1),RECEIVER_DAY=req.get('receiver_day',-1),
        HOURS=arr([float(e['light_hours']) for e in tab['environment.csv']]),TDAY=arr([float(e['temp_day_c']) for e in tab['environment.csv']]),TNIGHT=arr([float(e['temp_night_c']) for e in tab['environment.csv']]),
        RUN=json.dumps(req['run_id']),INPUT_HASH=json.dumps(binding['input_hash']),ENGINE_HASH=json.dumps(binding['engine_hash']),OBSERVATION='',OBS_MODE=str(req['initialization_route']!='seed').lower(),INTEGRATION_MODE=str(req.get('integration_contract')=='fsp-integration-1').lower(),LIGHT_ONLY=str(req.get('light_only',False)).lower(),PLACEMENTS='new double[0][0]',DT_DAYS=req['dt_s']/86400)
    if req['initialization_route']!='seed':
        from tools.vtc_development_observation import native_initialization
        mapping['OBSERVATION']=native_initialization(frozen_pkg,frozen)
    if req.get('integration_contract')=='fsp-integration-1':
        from tools.tomato_fsp_io import native_extension
        extension,placements=native_extension(frozen_pkg,frozen)
        mapping['OBSERVATION']+=extension;mapping['PLACEMENTS']=placements
    # Each emitted organ block has its own local scope. Keep methods comfortably
    # below the JVM 64 KiB bytecode limit, including multi-plant P1 imports.
    chunks=[];pending=[];size=0
    for line in mapping['OBSERVATION'].splitlines():
        pending.append(line);size+=len(line)
        if line=='}' and size>=8000:
            chunks.append('\n'.join(pending));pending=[];size=0
    if pending:chunks.append('\n'.join(pending))
    mapping['INITIALIZERS']='\n'.join(f'void initializePart{i}() {{\n{chunk}\n}}' for i,chunk in enumerate(chunks))
    mapping['OBSERVATION']='\n'.join(f'initializePart{i}();' for i in range(len(chunks)))
    mapping['LAMPS']='\n'.join(f'[ Translate({float(l["x_m"])}f,{float(l["y_m"])}f,{float(l["z_m"])}f) Lamp({i}).(setLight(new PointLight().(setPower({float(l["power_umol_s"])}f)))) ]' for i,l in enumerate(tab['lamps.csv']))
    for k,v in mapping.items():template=template.replace('@'+k+'@',str(v))
    require('@' not in template,'unresolved native token')
    (working/'Model.rgg').write_text(template,encoding='utf-8')
    originals={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file() and 'output' not in p.relative_to(source).parts}
    result=dict(schema_version='vtc-development-prepared-3',mode=MODE,run_id=req['run_id'],scenario_id=req['scenario_id'],binding=binding,
        frozen_hashes=frozen_pkg['source_hashes'],source_hashes=pkg['source_hashes'],model_hash=sha(working/'Model.rgg'),parameter_hash=sha(working/'parametersMicroTom.rgg'),
        contract_sha256=sha(CONTRACT),active_native_entrypoint='working/Model.rgg::simulate',source_url='https://github.com/ksmolen2/vtc',original_source_hashes=originals,
        original_source_path=str(source),attribution='K. Smolenova / WUR, FSPM_BASIC from Jochem Evers',license_status='unresolved_local_only',
        code_hashes={p.name:sha(p) for p in [Path(__file__),NATIVE,ROOT/'tools/vtc_development_io.py',ROOT/'tools/vtc_growth_bridge.py',ROOT/'tools/vtc_development_observation.py',ROOT/'tools/vtc_development_viewer.html',ROOT/'tools/fsp_extensions.py',ROOT/'tools/fsp_extensions_native.rgg',ROOT/'tools/fsp_axes.py',ROOT/'tools/fsp_axes_segments.py',ROOT/'tools/tomato_fsp_native_boundary.py',ROOT/'tools/tomato_fsp_boundary_native.rgg',ROOT/'tools/tomato_fsp_intake.py']})
    write_json(out/'prepared.json',result);write_json(out/'parameter_registry.json',registry)
    export_registry(out,req)
    if req.get('integration_contract'):
        result['auxiliary_hashes']={'initial_shapes.csv':sha(working/'initial_shapes.csv')}
        write_json(out/'prepared.json',result)
    if req.get('extensions'):
        result.setdefault('auxiliary_hashes',{})['extension_scene.csv']=sha(working/'extension_scene.csv')
        result['code_hashes']['fsp_extensions.py']=sha(ROOT/'tools/fsp_extensions.py')
        result['code_hashes']['fsp_extensions_native.rgg']=sha(ROOT/'tools/fsp_extensions_native.rgg')
        write_json(out/'prepared.json',result)
    return result


def verify_prepared(folder: Path) -> tuple[dict,dict]:
    prepared=read_json(folder/'prepared.json');require(prepared['mode']==MODE,'wrong mode')
    pkg=load_package(folder/'inputs')
    require(prepared['frozen_hashes']==pkg['source_hashes'],'frozen input changed')
    require(prepared['binding']['input_hash']==digest(pkg['source_hashes']),'input binding mismatch')
    require(sha(folder/'working/Model.rgg')==prepared['model_hash'],'native model changed')
    require(sha(folder/'working/parametersMicroTom.rgg')==prepared['parameter_hash'],'cultivar parameters changed')
    for name,h in prepared.get('auxiliary_hashes',{}).items():require(sha(folder/'working'/name)==h,'native auxiliary input changed')
    return prepared,pkg


def collect(folder: Path) -> dict:
    prepared,pkg=verify_prepared(folder);ex=read_json(folder/'execution.json')
    require(ex['status']=='verified' and ex['exit_code']==0,'verified native execution required')
    require(ex['prepared_sha256']==sha(folder/'prepared.json') and ex['log_sha256']==sha(folder/'groimp.log'),'execution binding mismatch')
    report=validate_outputs(pkg,folder/'working',prepared['binding'])
    require(not (folder/'results').exists(),'already published')
    stage=folder/'publication_partial';require(not stage.exists(),'partial publication exists');stage.mkdir()
    for name in (*read_json(folder/'working/completion.json')['files'],'completion.json'):shutil.copyfile(folder/'working'/name,stage/name)
    from tools.vtc_development_observation import derived_tables
    if not pkg['request'].get('integration_contract'):derived_tables(stage,pkg)
    from tools.fsp_extensions import reporting_area
    reporting_area(stage,pkg)
    from tools.fsp_axes import export_registry
    export_registry(stage,pkg['request'])
    from tools.fsp_extensions import boundary_time
    times=[dict(boundary=i,state_time=boundary_time(pkg['request'],i).isoformat(),elapsed_days=(boundary_time(pkg['request'],i)-boundary_time(pkg['request'],0)).total_seconds()/86400) for i in range(pkg['request']['intervals']+1)]
    write_csv(stage/'time_boundaries.csv',times)
    payload=json.dumps(dict(dt_days=pkg['request']['dt_s']/86400,elapsed_days=[t['elapsed_days'] for t in times],states=rows(stage/'states.csv'),meshes=rows(stage/'meshes.csv'),events=rows(stage/'events.csv'),ledger=rows(stage/'ledger.csv')),ensure_ascii=True).replace('</','<\\/')
    viewer=(ROOT/'tools/vtc_development_viewer.html').read_text(encoding='utf-8').replace('__DATA__',payload)
    (stage/'viewer.html').write_text(viewer,encoding='utf-8')
    report.update(mode=MODE,run_id=pkg['request']['run_id'],scenario_id=pkg['request']['scenario_id'],active_native_entrypoint=prepared['active_native_entrypoint'],binding=prepared['binding'],
        original_source_hashes=prepared['original_source_hashes'],artifact_hashes={p.name:sha(p) for p in stage.iterdir()},parameters=pkg['request']['parameters'])
    write_json(stage/'manifest.json',report);stage.rename(folder/'results');return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=[MODE])
    sub=parser.add_subparsers(dest='op',required=True)
    p=sub.add_parser('demo');p.add_argument('--out',type=Path,required=True);p.add_argument('--intervals',type=int,default=65);p.add_argument('--rays',type=int,default=300000);p.add_argument('--seed',type=int,default=5000);p.add_argument('--scenario',choices=['sufficient','limited','dark','dark_empty','frozen'],default='sufficient')
    p=sub.add_parser('audit');p.add_argument('--input',type=Path,required=True)
    p=sub.add_parser('prepare');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--java',default='java');p.add_argument('--timeout',type=float,default=1200)
    p=sub.add_parser('collect');p.add_argument('--run-dir',type=Path,required=True)
    p=sub.add_parser('observation-fixture');p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--day',type=int,default=30);p.add_argument('--intervals',type=int,default=5)
    a=parser.parse_args()
    try:
        if a.op=='demo':result={'inputs':str(demo(a.out,a.intervals,a.rays,a.scenario,a.seed))}
        elif a.op=='audit':result={'mode':MODE,'input_hashes':load_package(a.input)['source_hashes']}
        elif a.op=='prepare':result=prepare(a.input,a.out)
        elif a.op=='observation-fixture':
            from tools.vtc_development_observation import fixture_from_native
            result={'inputs':str(fixture_from_native(a.run_dir,a.out,a.day,a.intervals))}
        elif a.op=='run':
            from tools.vtc_growth_bridge import run
            require(read_json(a.run_dir/'prepared.json').get('mode')==MODE,'development requested but engine mode differs')
            result=run(a.run_dir,java=a.java,timeout_s=a.timeout)
        else:result=collect(a.run_dir)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ContractError,ValueError,KeyError,OSError) as e:parser.exit(1,f'{type(e).__name__}: {e}\n')


if __name__=='__main__':main()
