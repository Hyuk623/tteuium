"""Boundary and real-engine evidence tests for the conditional VTC bridge."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from tools.vtc_growth_bridge import demo_inputs, prepare, verify_prepared, collect
from tools.vtc_growth_io import ROOT, ContractError, load_package, read_json, write_json, rows, write_csv, fresh_build, sha, validate_outputs


@pytest.fixture
def fixture_dir() -> Path:
    return demo_inputs(ROOT/'build'/('vtc_test_'+uuid.uuid4().hex))


def test_fixture_keeps_real_evidence_unavailable(fixture_dir: Path) -> None:
    p=load_package(fixture_dir)
    assert p['request']['biological_validation']=='not_established'
    assert p['request']['completeness']=='supported_leaf_subset'
    assert all('fixture' in row['geometry_source'] for row in p['tables']['leaflets.csv'])


@pytest.mark.parametrize('key,value',[
    ('frame','board_mm'),('dt_s',3600),('run_status','accepted_for_domain'),
    ('nutrient_feedback_enabled',True),('biological_validation','validated'),
    ('geometry_basis','compound_envelope'),('initialization_route','spinup_30_days'),
    ('observation_time','2026-10-11T06:00:00'),('fixture',False),
    ('light_ratio_role','multiply_leaflet'),('intervals',4),
])
def test_bad_request_is_rejected(fixture_dir: Path,key: str,value: object) -> None:
    r=read_json(fixture_dir/'request.json'); r[key]=value; write_json(fixture_dir/'request.json',r)
    with pytest.raises((ContractError,ValueError)): load_package(fixture_dir)


@pytest.mark.parametrize('column,value',[
    ('dry_mass_g',''),('length_mm','NaN'),('width_mm','-1'),
    ('geometry_source','measured'),('parent_id','unknown'),('age_days','31'),
    ('axis_id','other/A0'),('plant_instance_id','unknown'),
])
def test_unknown_geometry_mass_and_identity_rejected(fixture_dir: Path,column: str,value: str) -> None:
    table=rows(fixture_dir/'leaflets.csv');table[0][column]=value;write_csv(fixture_dir/'leaflets.csv',table)
    with pytest.raises(ContractError): load_package(fixture_dir)


def test_duplicate_identity_rejected(fixture_dir: Path) -> None:
    table=rows(fixture_dir/'leaflets.csv');table[1]['leaflet_id']=table[0]['leaflet_id'];write_csv(fixture_dir/'leaflets.csv',table)
    with pytest.raises(ContractError,match='duplicate leaflet'):load_package(fixture_dir)


@pytest.mark.parametrize('value',['-1','NaN','0','100'])
def test_ratio_never_repaired(fixture_dir: Path,value: str) -> None:
    table=rows(fixture_dir/'ratios.csv');table[0]['ratio_to_mean']=value;write_csv(fixture_dir/'ratios.csv',table)
    with pytest.raises(ContractError):load_package(fixture_dir)


def test_missing_parameter_is_not_defaulted(fixture_dir: Path) -> None:
    r=read_json(fixture_dir/'request.json');del r['parameters']['growth_efficiency'];write_json(fixture_dir/'request.json',r)
    with pytest.raises(KeyError):load_package(fixture_dir)


def test_output_cannot_replace_existing(fixture_dir: Path) -> None:
    with pytest.raises(ContractError,match='fresh output'):fresh_build(fixture_dir)
    with pytest.raises(ContractError,match='below project'):fresh_build(ROOT/'config'/'do_not_create')


def test_prepare_freezes_pointer_and_preserves_sources(fixture_dir: Path) -> None:
    source=load_package(fixture_dir)['source_hashes']
    fork=ROOT/'build/vtc_microtom_20261011'
    if not fork.exists():pytest.skip('local fork prerequisite absent')
    out=ROOT/'build'/('vtc_frozen_'+uuid.uuid4().hex)
    prepare(fixture_dir,fork,out)
    assert load_package(fixture_dir)['source_hashes']==source
    (fixture_dir/'light_ratio_latest.txt').write_text('does-not-exist.csv\n')
    _,p=verify_prepared(out)
    assert len(p['ratios'])==16
    table=rows(out/'inputs/leaflets.csv');table[0]['dry_mass_g']='99';write_csv(out/'inputs/leaflets.csv',table)
    with pytest.raises(ContractError,match='frozen input changed'):verify_prepared(out)


def test_collection_without_engine_never_publishes(fixture_dir: Path) -> None:
    fork=ROOT/'build/vtc_microtom_20261011'
    if not fork.exists():pytest.skip('local fork prerequisite absent')
    out=ROOT/'build'/('vtc_unrun_'+uuid.uuid4().hex);prepare(fixture_dir,fork,out)
    write_json(out/'execution.json',dict(status='failed',exit_code=0))
    with pytest.raises(ContractError,match='verified successful'):collect(out)
    assert not (out/'results').exists()


def test_observation_like_fixture_stays_fixture() -> None:
    out=demo_inputs(ROOT/'build'/('vtc_observed_fixture_'+uuid.uuid4().hex),'observation')
    p=load_package(out)
    assert p['request']['initialization_route']=='observation_fixture'
    assert all(r['geometry_source']=='observation_like_fixture' for r in p['tables']['leaflets.csv'])


@pytest.fixture
def native_evidence() -> tuple[Path,dict,dict]:
    """Integration evidence from a genuine local engine run, not mocked subprocess."""
    source=ROOT/'build/vtc_python_phase1_20261011_final_sufficient'
    if not (source/'results/manifest.json').exists():pytest.skip('run native acceptance suite first')
    target=fresh_build(ROOT/'build'/('vtc_native_test_'+uuid.uuid4().hex))
    shutil.copytree(source/'working',target/'native')
    return target/'native',load_package(source/'inputs'),read_json(source/'prepared.json')['binding']


def test_native_three_intervals_verified(native_evidence: tuple) -> None:
    native,package,binding=native_evidence
    report=validate_outputs(package,native,binding)
    assert report['software_status']=='passed'
    assert len(report['geometry_hashes'])==4
    assert report['full_v2_acceptance'].startswith('incomplete')


@pytest.mark.parametrize('filename,column,value',[
    ('ledger.csv','reserve_end_gC','99'),('ledger.csv','reserve_start_gC','99'),
    ('organs.csv','leaf_resp_gC','99'),('organs.csv','allocated_gC','99'),
    ('geometry.csv','dry_mass_g','99'),('geometry.csv','length_m','99'),
    ('geometry.csv','plant_instance_id','not-p1'),
    ('consumed_geometry.csv','length_m','99'),
    ('sensors.csv','area_m2','99'),
])
def test_rehashed_native_corruption_rejected(native_evidence: tuple,filename: str,column: str,value: str) -> None:
    native,package,binding=native_evidence
    data=rows(native/filename);data[0][column]=value;write_csv(native/filename,data)
    completion=read_json(native/'completion.json');completion['files'][filename]=sha(native/filename);write_json(native/'completion.json',completion)
    with pytest.raises(ContractError):validate_outputs(package,native,binding)


@pytest.mark.parametrize('key,value',[('run_id','old_run'),('intervals',2),('engine_hash','wrong'),('input_hash','wrong')])
def test_stale_completion_is_rejected(native_evidence: tuple,key: str,value: object) -> None:
    native,package,binding=native_evidence
    completion=read_json(native/'completion.json');completion[key]=value;write_json(native/'completion.json',completion)
    with pytest.raises(ContractError):validate_outputs(package,native,binding)
