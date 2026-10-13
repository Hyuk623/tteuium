"""Boundary tests and deliberate corruption of actual native V3 evidence."""
from __future__ import annotations
import shutil
import uuid
from pathlib import Path
import pytest
from tools.vtc_development import demo, prepare, verify_prepared
from tools.vtc_development_io import MODE, load_package, validate_outputs
from tools.vtc_growth_io import ROOT, ContractError, read_json, write_json, rows, write_csv, sha


@pytest.fixture
def inputs() -> Path:
    return demo(ROOT/'build'/('vtc_dev_test_'+uuid.uuid4().hex),intervals=3,rays=1000)


@pytest.mark.parametrize('key,value',[
 ('mode','phase1_leaflet_subset_v1'),('dt_s',3600),('frame','board_mm'),
 ('run_status','accepted_for_domain'),('biological_validation','validated'),
 ('physiology_temperature_response',True),('physiology_co2_response',True),
 ('nutrient_feedback_enabled',True),('initialization_route','unknown'),('intervals',0),
 ('light_ratio_role','multiply_leaflets'),('fixture','yes'),('freeze_at',999),
])
def test_incompatible_request_rejected(inputs: Path,key: str,value: object) -> None:
    r=read_json(inputs/'request.json');r[key]=value;write_json(inputs/'request.json',r)
    with pytest.raises(ContractError):load_package(inputs)


@pytest.mark.parametrize('key,value',[
 ('PHYLLOCHRON_DD',0),('PAIRS',[0,2]),('CADENCE',[2,1]),('SP_STOP_RULE','stop_at_first_truss'),
 ('MAINT',[0]*12),('MAX_MASS',[1]*12),('FLOWERS',2.5),('SLA_M2_G',float('inf')),
])
def test_science_parameter_bounds(inputs: Path,key: str,value: object) -> None:
    r=read_json(inputs/'request.json');r['parameters'][key]['value']=value
    # JSON's permissive Infinity is deliberately rejected by the number validator.
    import json
    (inputs/'request.json').write_text(json.dumps(r),encoding='utf-8')
    with pytest.raises(ContractError):load_package(inputs)


def test_borrowed_values_never_measured(inputs: Path) -> None:
    r=read_json(inputs/'request.json');r['parameters']['AMAX']['source_kind']='measured';write_json(inputs/'request.json',r)
    with pytest.raises(ContractError,match='promoted'):load_package(inputs)


def test_freeze_pointer_and_parameter_integrity(inputs: Path) -> None:
    out=ROOT/'build'/('vtc_dev_prepared_'+uuid.uuid4().hex);prepare(inputs,out)
    (inputs/'light_ratio_latest.txt').write_text('missing.csv\n',encoding='utf-8')
    assert verify_prepared(out)[0]['mode']==MODE
    with (out/'working/parametersMicroTom.rgg').open('a') as stream:stream.write('\n// deliberate corruption\n')
    with pytest.raises(ContractError,match='parameters changed'):verify_prepared(out)


@pytest.fixture
def native() -> tuple[Path,dict,dict]:
    evidence=ROOT/'build/vtc_dev_v3_delivery_sufficient'
    if not (evidence/'results/manifest.json').exists():pytest.skip('actual V3 evidence not yet available')
    prepared,pkg=verify_prepared(evidence)
    out=ROOT/'build'/('vtc_dev_corrupt_'+uuid.uuid4().hex);out.mkdir();shutil.copytree(evidence/'working',out/'native')
    return out/'native',prepared,pkg


@pytest.mark.parametrize('name,column,value',[
 ('states.csv','parent_id','missing'),('states.csv','mass_gDM','-1'),
 ('states.csv','length_m','NaN'),('flux.csv','allocated_gC','10'),
 ('ledger.csv','reserve_end_gC','99'),('consumed.csv','x_m','99'),
])
def test_rehashed_native_corruption_rejected(native: tuple[Path,dict,dict],name: str,column: str,value: str) -> None:
    folder,prepared,pkg=native;table=rows(folder/name);table[-1][column]=value;write_csv(folder/name,table)
    done=read_json(folder/'completion.json');done['files'][name]=sha(folder/name);write_json(folder/'completion.json',done)
    with pytest.raises(ContractError):validate_outputs(pkg,folder,prepared['binding'])


def test_duplicate_birth_rejected(native: tuple[Path,dict,dict]) -> None:
    folder,prepared,pkg=native;table=rows(folder/'events.csv');table.append(dict(table[0]));write_csv(folder/'events.csv',table)
    done=read_json(folder/'completion.json');done['files']['events.csv']=sha(folder/'events.csv');write_json(folder/'completion.json',done)
    with pytest.raises(ContractError,match='duplicate'):validate_outputs(pkg,folder,prepared['binding'])
