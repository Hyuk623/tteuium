"""Build a local attributed VTC fork and its bounded native leaflet mode.

No allocation or growth arithmetic runs in Python. The original NRH function is
copied byte-for-byte as a source fragment; new accounting executes in GroIMP.
"""
from __future__ import annotations

import difflib
import json
import math
import shutil
from pathlib import Path

from tools.vtc_growth_io import fresh_build, require, sha, write_json

DEFAULT_SOURCE = Path('C:/Users/sho36/Downloads/vtc-main/vtc-main/tomatoFSPM_basic_isP')

NATIVE = r'''
// Conditional VTC leaflet-subset mode. Original NRH: K. Smolenova / WUR,
// VTC 2022-2025, adapted from Jochem Evers FSPM_BASIC. See source_manifest.json.
// New conservative accounting: Codex 2026-10-11. Not biological validation.
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.math.BigInteger;

@NRH@

module Blade(int bid) extends Parallelogram;
module Probe(int pid) extends Parallelogram;
module Lamp extends LightNode;
LightModel lm = new LightModel(@RAYS@, @DEPTH@);
int n = @N@;
int countPlants = @NP@;
int countLeaves = @NL@;
int seed = @SEED@;
String runId = @RUN@;
String inputHash = @INPUT_HASH@;
String engineHash = @ENGINE_HASH@;
String[] leafIds = @LEAF_IDS@;
String[] plantIds = @PLANT_IDS@;
String[] compoundIds = @COMPOUND_IDS@;
int[] owner = @OWNER@;
double[] initialMass = @MASS@;
double[] mass = @MASS@;
double[] initialLength = @LENGTH@;
double[] initialWidth = @WIDTH@;
double[] len = @LENGTH@;
double[] wid = @WIDTH@;
double[] xx = @X@;
double[] yy = @Y@;
double[] zz = @Z@;
double[] age = @AGE@;
double[] potential = @POTENTIAL@;
double[] reserve = @RESERVE@;
double[] lightHours = @HOURS@;
double[] absorbed = new double[@NL@];
double amax = @AMAX@;
double alpha = @ALPHA@;
double theta = @THETA@;
double respiration = @RESP@;
double carbonFraction = @CF@;
double efficiency = @EFF@;
double molarCarbon = @MC@;
boolean freezeGeometry = @FREEZE@;
boolean measured = false;

protected void init()
[
    Axiom ==>
    @LAMPS@
    @BLADES@
    @PROBES@
    ;
    { println("PHASE1_READY " + runId); }
]

String fileHash(String name) {
    byte[] bytes = Files.readAllBytes(Paths.get(name));
    byte[] hashed = MessageDigest.getInstance("SHA-256").digest(bytes);
    String result = new BigInteger(1, hashed).toString(16);
    while (result.length() < 64) result = "0" + result;
    return result;
}

void exportGeometry(PrintWriter out, int state) {
    for (int j=0; j<countLeaves; j++) {
        out.println(state + "," + plantIds[owner[j]] + "," + compoundIds[j] + "," + leafIds[j] + "," + age[j] + "," + xx[j] + "," + yy[j] + "," + zz[j] + "," + len[j] + "," + wid[j] + "," + (len[j]*wid[j]) + "," + mass[j]);
    }
}

public void simulate() {
    if (measured) throw new IllegalStateException("fresh process required");
    measured = true;
    PrintWriter geometry = new PrintWriter(new FileWriter("geometry.csv"));
    PrintWriter organs = new PrintWriter(new FileWriter("organs.csv"));
    PrintWriter ledger = new PrintWriter(new FileWriter("ledger.csv"));
    PrintWriter sensors = new PrintWriter(new FileWriter("sensors.csv"));
    PrintWriter consumed = new PrintWriter(new FileWriter("consumed_geometry.csv"));
    geometry.println("state,plant_instance_id,compound_id,leaflet_id,age_days,x_m,y_m,z_m,length_m,width_m,area_m2,dry_mass_g");
    organs.println("interval,plant_instance_id,leaflet_id,absorbed_umol_s,gross_umol_CO2,leaf_resp_gC,net_gC,demand_gC,allocated_gC,growth_resp_gC,delta_dm_g");
    ledger.println("interval,plant_instance_id,reserve_start_gC,net_gC,leaf_resp_gC,allocated_gC,growth_resp_gC,structural_delta_gC,reserve_end_gC,unmet_deficit_gC,residual_gC");
    sensors.println("grid_row,grid_col,absorbed_umol_s,area_m2");
    consumed.println("interval,leaflet_id,length_m,width_m,area_m2");
    exportGeometry(geometry, 0);
    int step = 0;
    for (apply(n)) {
        for (Blade b : (* Blade *)) {
            double actualLength = b.getLength();
            double actualWidth = b.getAxis().length();
            consumed.println(step+","+leafIds[b.bid]+","+actualLength+","+actualWidth+","+(actualLength*actualWidth));
        }
        lm.setSeed(seed);
        lm.compute();
        for (Blade b : (* Blade *)) absorbed[b.bid] = lm.getAbsorbedPower(b).integrate();
        double[] gross = new double[countLeaves];
        double[] resp = new double[countLeaves];
        double[] net = new double[countLeaves];
        double[] demand = new double[countLeaves];
        double[] allocated = new double[countLeaves];
        double[] growthResp = new double[countLeaves];
        double[] delta = new double[countLeaves];
        for (int j=0;j<countLeaves;j++) {
            double area = len[j]*wid[j];
            gross[j] = calculatePS_Thornley(absorbed[j]/area, amax, alpha, theta)*area*lightHours[step]*3600;
            resp[j] = respiration*area*86400*molarCarbon*1e-6;
            net[j] = gross[j]*molarCarbon*1e-6 - resp[j];
            demand[j] = potential[j]*carbonFraction/efficiency;
        }
        for (int p=0;p<countPlants;p++) {
            double oldReserve=reserve[p], sumNet=0, sumResp=0, sumDemand=0;
            for (int j=0;j<countLeaves;j++) if (owner[j]==p) {
                sumNet+=net[j]; sumResp+=resp[j]; sumDemand+=demand[j];
            }
            double budget = oldReserve+sumNet;
            double deficit = Math.max(0,-budget);
            double funded = Math.min(Math.max(0,budget),sumDemand);
            double sumAllocated=0, sumGrowthResp=0, sumStructural=0;
            for (int j=0;j<countLeaves;j++) if (owner[j]==p) {
                allocated[j] = sumDemand>0 ? funded*demand[j]/sumDemand : 0;
                growthResp[j] = allocated[j]*(1-efficiency);
                delta[j] = allocated[j]*efficiency/carbonFraction;
                mass[j] += delta[j];
                age[j] += 1;
                if (!freezeGeometry) {
                    double scale=Math.sqrt(mass[j]/initialMass[j]);
                    len[j]=initialLength[j]*scale; wid[j]=initialWidth[j]*scale;
                }
                sumAllocated+=allocated[j]; sumGrowthResp+=growthResp[j];
                sumStructural+=delta[j]*carbonFraction;
            }
            reserve[p]=Math.max(0,budget-funded);
            double residual=oldReserve+sumNet-reserve[p]-sumStructural-sumGrowthResp;
            ledger.println(step+","+plantIds[p]+","+oldReserve+","+sumNet+","+sumResp+","+sumAllocated+","+sumGrowthResp+","+sumStructural+","+reserve[p]+","+deficit+","+residual);
        }
        for (int j=0;j<countLeaves;j++) {
            organs.println(step+","+plantIds[owner[j]]+","+leafIds[j]+","+absorbed[j]+","+gross[j]+","+resp[j]+","+net[j]+","+demand[j]+","+allocated[j]+","+growthResp[j]+","+delta[j]);
        }
        [ b:Blade ::> { b[length] = (float)len[b.bid]; b[axis] = new javax.vecmath.Vector3f((float)wid[b.bid],0,0); } ]
        derive();
        exportGeometry(geometry,step+1);
        println("PHASE1_INTERVAL " + (step+1));
        step++;
    }
    // Separate empty-scene comparison. Probes did not participate in plant runs.
    [ b:Blade ==> ; ]
    [ p:Probe ::> { p[length] = 0.02f; p[axis] = new javax.vecmath.Vector3f(0.02f,0,0); } ]
    derive();
    lm.setSeed(seed);
    lm.compute();
    for (Probe p : (* Probe *)) {
        sensors.println((p.pid/4+1)+","+(p.pid%4+1)+","+lm.getAbsorbedPower(p).integrate()+",0.0004");
    }
    geometry.close(); organs.close(); ledger.close(); sensors.close(); consumed.close();
    PrintWriter done = new PrintWriter(new FileWriter("completion.json"));
    done.println("{\"run_id\":\""+runId+"\",\"intervals\":"+n+",\"input_hash\":\""+inputHash+"\",\"engine_hash\":\""+engineHash+"\",\"files\":{");
    done.println("\"geometry.csv\":\""+fileHash("geometry.csv")+"\",\"organs.csv\":\""+fileHash("organs.csv")+"\",\"ledger.csv\":\""+fileHash("ledger.csv")+"\",\"sensors.csv\":\""+fileHash("sensors.csv")+"\",\"consumed_geometry.csv\":\""+fileHash("consumed_geometry.csv")+"\"}}");
    done.close();
    println("PHASE1_DONE " + runId);
    System.exit(0);
}
'''


def nrh_fragment(source: Path) -> str:
    text = (source / 'photosynthesis.rgg').read_text(encoding='utf-8-sig')
    start = text.index('static double calculatePS_Thornley(')
    end = text.index('// Farquhar-von', start)
    return text[start:end].rstrip()


def create_fork(source: Path, target: Path) -> Path:
    target = fresh_build(target)
    original = target / 'upstream'
    # No old output or serialized graph state is used as run evidence.
    shutil.copytree(source, original, ignore=shutil.ignore_patterns('output'))
    originals = {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file() and 'output' not in p.relative_to(source).parts}
    for rel, value in originals.items(): require(sha(original / rel) == value, 'source copy changed')
    (target / 'phase1_template.rgg').write_text(NATIVE.replace('@NRH@', nrh_fragment(source)), encoding='utf-8')
    write_json(target / 'source_manifest.json', dict(source=str(source.resolve()), source_url='https://github.com/ksmolen2/vtc',
               attribution='Katarina Smolenova, WUR, 2022-2025; FSPM_BASIC adaptation from Jochem Evers',
               license_status='no_model_code_license_found; redistribution_unresolved', source_hashes=originals,
               selected_mode='phase1_leaflet_subset_v1', original_development_executed=False,
               modified_hashes={'phase1_template.rgg':sha(target/'phase1_template.rgg')},
               scientific_contract='handoff/PHASE1_VTC_PYTHON_SCIENCE_AND_IO_CONTRACT_2026-10-11.md'))
    (target/'SOURCE_DIFF.txt').write_text('New bounded entrypoint; original files unchanged.\n'+''.join(difflib.unified_diff([], (target/'phase1_template.rgg').read_text(encoding='utf-8').splitlines(True), fromfile='/dev/null', tofile='phase1_template.rgg')), encoding='utf-8')
    return target


def make_model(package: dict, template: str, binding: dict) -> str:
    req=package['request']; tab=package['tables']; plants=tab['plants.csv']; leaves=tab['leaflets.csv']
    owners={p['plant_instance_id']:i for i,p in enumerate(plants)}
    def arr(values: list, typ: str='double') -> str:
        return 'new '+typ+'[]{'+','.join(json.dumps(x,ensure_ascii=True) for x in values)+'}'
    xs=[]; ys=[]; zs=[]
    for l in leaves:
        p=plants[owners[l['plant_instance_id']]]; yaw=math.radians(float(p['yaw_deg']))
        x,y=float(l['x_mm']),float(l['y_mm'])
        xs.append((x*math.cos(yaw)-y*math.sin(yaw)+float(p['tx_mm']))*.001)
        ys.append((x*math.sin(yaw)+y*math.cos(yaw)+float(p['ty_mm']))*.001)
        zs.append((float(l['z_mm'])+float(p['tz_mm']))*.001)
    mapping=dict(RAYS=req['runtime']['rays'],DEPTH=req['runtime']['depth'],SEED=req['runtime']['seed'],
                 N=req['intervals'],NP=len(plants),NL=len(leaves),RUN=json.dumps(req['run_id']),
                 INPUT_HASH=json.dumps(binding['input_hash']),ENGINE_HASH=json.dumps(binding['engine_hash']),
                 LEAF_IDS=arr([l['leaflet_id'] for l in leaves],'String'),
                 PLANT_IDS=arr([p['plant_instance_id'] for p in plants],'String'),
                 COMPOUND_IDS=arr([l['compound_id'] for l in leaves],'String'),
                 OWNER=arr([owners[l['plant_instance_id']] for l in leaves],'int'),
                 MASS=arr([float(l['dry_mass_g']) for l in leaves]),
                 LENGTH=arr([float(l['length_mm'])*.001 for l in leaves]),WIDTH=arr([float(l['width_mm'])*.001 for l in leaves]),
                 X=arr(xs),Y=arr(ys),Z=arr(zs),AGE=arr([float(l['age_days']) for l in leaves]),
                 POTENTIAL=arr([float(l['potential_dm_g_day']) for l in leaves]),RESERVE=arr([float(p['reserve_gC']) for p in plants]),
                 HOURS=arr([float(e['light_hours']) for e in tab['environment.csv']]),FREEZE=str(req['freeze_geometry']).lower())
    for token,key in dict(AMAX='amax_umol_m2_s',ALPHA='alpha_mol_mol',THETA='theta',RESP='respiration_umol_m2_s',
                          CF='carbon_fraction_gC_gDM',EFF='growth_efficiency',MC='molar_carbon_g_mol').items():
        mapping[token]=req['parameters'][key]['value']
    mapping['LAMPS']='\n'.join(f'[ Translate({float(l["x_mm"])*.001}f,{float(l["y_mm"])*.001}f,{float(l["z_mm"])*.001}f) Lamp().(setLight(new PointLight().(setPower({float(l["power_umol_s"])}f)))) ]' for l in tab['lamps.csv'])
    # Parallelogram local +Z length, +X width; RL(-90) rotates the blade into XY.
    # In-plane yaw applies to blade as well as its supplied anchor.
    mapping['BLADES']='\n'.join(f'[ Translate({xs[j]}f,{ys[j]}f,{zs[j]}f) RH({float(plants[owners[l["plant_instance_id"]]]["yaw_deg"])}f) RL(-90) Blade({j}).(setLength({float(l["length_mm"])*.001}f),setAxis(new javax.vecmath.Vector3f({float(l["width_mm"])*.001}f,0,0)),setShader(BLACK)) ]' for j,l in enumerate(leaves))
    grid=req['comparison_grid']; spacing=grid['spacing_mm']*.001
    mapping['PROBES']='\n'.join(f'[ Translate({grid["origin_x_mm"]*.001+c*spacing}f,{grid["origin_y_mm"]*.001+r*spacing}f,{grid["height_mm"]*.001}f) RL(-90) Probe({r*4+c}).(setLength(0f),setAxis(new javax.vecmath.Vector3f(0,0,0)),setShader(BLACK)) ]' for r in range(4) for c in range(4))
    for key,value in mapping.items(): template=template.replace('@'+key+'@',str(value))
    require('@' not in template, 'unexpanded native template')
    return template
