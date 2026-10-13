"""Actual producer boundary, placement and transaction-failure checks."""
from __future__ import annotations
import shutil
import uuid
from pathlib import Path
from copy import deepcopy
import pytest
from tools.vtc_growth_io import ROOT,ContractError,read_json,write_json,rows,write_csv,sha
from tools.tomato_fsp_io import audit_p1_package,selected_package
from tools.tomato_fsp_canopy import rigid,assemble_canopy,split_by_instance
from tools.tomato_fsp_pipeline import commit_step,nutrient_prefix,verify_run

SOURCE=ROOT/'build/fsp_integration_20261011_p1_fixture_01'
SCENARIO=ROOT/'build/fsp_integration_20261011_scenario_01/scenario.json'


@pytest.fixture
def package() -> Path:
    if not SOURCE.exists():pytest.skip('actual producer-function fixture required')
    p=ROOT/'build'/('fsp_test_'+uuid.uuid4().hex);shutil.copytree(SOURCE,p);return p


def test_actual_producer_fixture_validates() -> None:
    if not SOURCE.exists():pytest.skip('producer fixture absent')
    r=audit_p1_package(SOURCE);assert r['fixture_ready'] and not r['real_ready']
    selected=selected_package(SOURCE,read_json(SCENARIO));scene=selected['canopy'];assert len(selected['placement'])==3
    output=[dict(surface_id=s['surface_id'],absorbed=1.) for s in scene['surfaces']]
    split=split_by_instance(output,scene['identity_map']);assert set(split)==set(selected['placement'])
    assert sum(map(len,split.values()))==len(output) and scene['roundtrip_max_error_mm']<1e-9


@pytest.mark.parametrize('rotation',[
 [[2,0,0],[0,1,0],[0,0,1]],[[-1,0,0],[0,1,0],[0,0,1]],[[1,.1,0],[0,1,0],[0,0,1]],[[float('nan'),0,0],[0,1,0],[0,0,1]],
])
def test_reject_nonrigid(rotation: list) -> None:
    with pytest.raises(ContractError):rigid(rotation,[0,0,0])


@pytest.mark.parametrize('field,value',[('frame','image_px'),('scale_source','unavailable'),('source_plant_id','wrong'),('capture_time','2026-10-11T06:00:00')])
def test_capture_boundary_failures(package: Path,field: str,value: str) -> None:
    r=rows(package/'captures.csv');r[0][field]=value;write_csv(package/'captures.csv',r)
    with pytest.raises((ValueError,KeyError)):selected_package(package,read_json(SCENARIO))


@pytest.mark.parametrize('field,value',[('area_convention','projected'),('frame','canopy_mm'),('surface_sha256','0'*64),('optical_readiness','unavailable')])
def test_optical_boundary_failures(package: Path,field: str,value: str) -> None:
    r=rows(package/'optical_surface_manifest.csv');r[0][field]=value;write_csv(package/'optical_surface_manifest.csv',r)
    with pytest.raises(ValueError):selected_package(package,read_json(SCENARIO))


def test_schema_mismatch(package: Path) -> None:
    r=read_json(package/'p1_manifest.json');r['schema']='unknown';write_json(package/'p1_manifest.json',r)
    with pytest.raises(ContractError,match='schema'):audit_p1_package(package)


def test_placement_not_applied_twice(package: Path) -> None:
    selected=selected_package(package,read_json(SCENARIO));scene=selected['canopy'];first=scene['surfaces'][0];p=selected['placement'][first['plant_instance_id']]
    import numpy as np
    r,t=rigid(p['rotation'],p['translation_mm']);assert np.allclose(first['triangles_m'],(np.asarray(first['triangles_mm'])@r.T+t)*.001)
    assert first['triangles_m']!=first['triangles_mm']


def test_wrong_native_mode_does_not_fallback() -> None:
    from tools.vtc_development_io import load_package
    from tools.vtc_development import demo
    p=demo(ROOT/'build'/('fsp_mode_'+uuid.uuid4().hex),3,1000);r=read_json(p/'request.json');r['mode']='phase1_leaflet_subset_v1';write_json(p/'request.json',r)
    with pytest.raises(ContractError,match='fallback'):load_package(p)


@pytest.fixture
def native_run() -> Path:
    p=ROOT/'build/fsp_integration_20261011_final_01'
    if not (p/'collection.json').exists():pytest.skip('final actual native integration evidence required')
    return p


def test_idempotent_commit_no_double_charge(native_run: Path) -> None:
    target=native_run/'committed/step_0001/checkpoint.json';before=sha(target)
    result=commit_step(native_run,native_run/'native/working/checkpoints/step_1')
    assert result['status']=='already_committed' and sha(target)==before


def test_required_nutrient_failure(native_run: Path) -> None:
    _,_,pkg=verify_run(native_run);s=read_json(native_run/'scenario.json');s['nutrient_scenarios'][next(iter(s['nutrient_scenarios']))]['events'][0]['water_ml']=100000
    with pytest.raises(ValueError):nutrient_prefix(s,pkg,1)


def test_nutrient_wrong_instance(native_run: Path) -> None:
    _,_,pkg=verify_run(native_run);s=read_json(native_run/'scenario.json');s['nutrient_scenarios'][next(iter(s['nutrient_scenarios']))]['plant_instance_id']='other'
    with pytest.raises(ContractError,match='identity'):nutrient_prefix(s,pkg,1)


@pytest.mark.parametrize('file,column,value',[('consumed.csv','x_m','99'),('proposals.csv','allocated_gC','999'),('ledger.csv','reserve_end_gC','999'),('states.csv','parent_id','absent')])
def test_rehashed_native_boundary_corruption(native_run: Path,file: str,column: str,value: str) -> None:
    from tools.vtc_development_io import validate_outputs
    _,prepared,pkg=verify_run(native_run);p=ROOT/'build'/('fsp_native_corrupt_'+uuid.uuid4().hex);shutil.copytree(native_run/'native/working/checkpoints/step_1',p)
    data=rows(p/file);data[-1][column]=value;write_csv(p/file,data)
    done=read_json(p/'completion.json');done['files'][file]=sha(p/file);write_json(p/'completion.json',done)
    with pytest.raises((ValueError,KeyError)):validate_outputs(pkg,p,prepared['binding'],checkpoint=True)


def test_partial_native_completion_not_accepted(native_run: Path) -> None:
    from tools.vtc_development_io import validate_outputs
    _,prepared,pkg=verify_run(native_run);p=ROOT/'build'/('fsp_native_partial_'+uuid.uuid4().hex);p.mkdir()
    shutil.copyfile(native_run/'native/working/checkpoints/step_1/completion.json',p/'completion.json')
    with pytest.raises(OSError):validate_outputs(pkg,p,prepared['binding'],checkpoint=True)


def test_comparison_capture_ids_are_instance_scoped(package: Path,native_run: Path) -> None:
    from tools.tomato_fsp_pipeline import compare_observation
    forecast=native_run/'committed/step_0003';before=sha(forecast/'checkpoint.json')
    for name in ('captures.csv','identity_manifest.csv','mtg_vertices.csv','areas.csv','optical_surface_manifest.csv'):
        table=rows(package/name)
        for row in table:
            if row['plant_instance_id'].startswith('fixture_a#'):row['capture_id']='shared_capture'
            if name=='captures.csv':row['capture_time']='2026-10-14T06:00:00+09:00' if row['plant_instance_id']=='fixture_a#1' else '2026-10-15T06:00:00+09:00'
        write_csv(package/name,table)
    out=ROOT/'build'/('fsp_compare_'+uuid.uuid4().hex)
    report=compare_observation(forecast,package,out);compared=rows(out/'comparison.csv')
    assert report['forecast_unchanged'] and not report['assimilation_applied']
    assert compared and {r['organ_id'].split('|')[0] for r in compared}=={'fixture_a#1'}
    assert sha(forecast/'checkpoint.json')==before


@pytest.mark.parametrize('dt,fixture,hours,reason',[(43200,False,7,'fixture refinement'),(3600,True,1,'unsupported dt_s'),(43200,True,14,'photoperiod')])
def test_refinement_boundary_rejects_unsupported_intervals(native_run: Path,dt: int,fixture: bool,hours: int,reason: str) -> None:
    from tools.vtc_development_io import load_package
    p=ROOT/'build'/('fsp_dt_'+uuid.uuid4().hex);shutil.copytree(native_run/'native/inputs',p)
    request=read_json(p/'request.json');request.update(dt_s=dt,fixture=fixture);write_json(p/'request.json',request)
    environment=rows(p/'environment.csv');environment[0]['light_hours']=hours;write_csv(p/'environment.csv',environment)
    with pytest.raises(ContractError,match=reason):load_package(p)
