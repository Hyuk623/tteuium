"""Absent reference inputs remain unavailable; tissue light cannot masquerade as a sensor record."""
import pytest

from tools import light_growth_bridge as bridge
from tools.light_growth_consumer import load_tables
from tools.leaf_light.common import read_json,write_json,write_rows,file_hash
from test_light_growth_bridge import make_request,sample,schedule,timing,dose


@pytest.mark.parametrize('mutation', ['capability','tissue_basis','fabricated_value','zero_value','other_basis',
                                    'interval','absorbed','wrong_unit','tissue_mean','partial_day'])
def test_consumer_rejects_reference_claims_even_after_rehash(tmp_path,mutation):
    request=make_request(tmp_path); folder=tmp_path/'package'
    bridge.build_package(request,folder)
    assert bridge.validate_growth_light_package(folder)['valid']
    path=folder/('capabilities.json' if mutation=='capability' else 'consumer_mapping.json')
    data=read_json(path)
    if mutation=='capability': data['reference_dli']='implemented'
    else:
        ref=data['growth']['reference_dli']
        changes={'fabricated_value':('value',5.),'zero_value':('value',0.),'other_basis':('basis_id','invented_sensor'),
            'interval':('applicability_interval',[0.,30.]),'absorbed':('quantity','absorbed'),
            'wrong_unit':('unit','mol/m2'),'tissue_mean':('spatial_basis','whole_plant_surface_average'),
            'partial_day':('time_basis','partial_day')}
        if mutation=='tissue_basis':
            ref['basis_id']=load_tables(folder)['light_dose.csv'][0]['area_basis_id']
        else:
            field,value=changes[mutation]; ref[field]=value
    write_json(path,data)
    package=read_json(folder/'package.json'); package['artifact_hashes'][path.name]=file_hash(path)
    write_json(folder/'package.json',package)
    result=bridge.validate_growth_light_package(folder)
    assert not result['valid'] and 'reference_dli' in result['errors'][0],result


@pytest.mark.parametrize('mode', ['complete','time_gap','unknown_schedule','zero'])
def test_existing_full_local_day_accounting_preserves_tissue_basis(mode):
    interval=timing('2026-10-04T00:00:00+09:00'); sched=schedule()
    if mode=='time_gap': interval['snapshots'][0]['valid_until']='2026-10-03T12:00:00+09:00'
    if mode=='unknown_schedule': sched['fixtures']['LED']=None
    if mode=='zero': sched['fixtures']['LED'][0]['output_fraction']=0.
    _,records=dose([sample(q=100.,weight=.02)],sched,interval)
    for row in records:
        assert row['area_basis_id']=='basis'
        if mode in ('time_gap','unknown_schedule'):
            assert row['dli_mol_m2_day'] is None and not row['complete_local_day']
        else:
            assert row['complete_local_day']
            assert row['dli_mol_m2_day']==pytest.approx(8.64 if mode=='complete' else 0.,abs=1e-10,rel=1e-9)
    fields={c['name']:c['unit'] for c in bridge.SCHEMA['tables']['light_dose.csv']['columns']}
    assert fields['dli_mol_m2_day']=='mol/m2/day' and fields['incident_dose_mol_m2']=='mol/m2'


def test_reference_unavailable_does_not_remove_patch_fixture_or_canopy_data(tmp_path):
    request=make_request(tmp_path); folder=tmp_path/'package'; bridge.build_package(request,folder)
    mapping=read_json(folder/'consumer_mapping.json')
    assert mapping['growth']['reference_dli']['value'] is None
    assert 'pending core hook' not in mapping['growth']['light_covariates']
    assert mapping['physiology']['select']=='time_step_id != full_output; fixture_id = all; direct backend only'
    assert 'D15-D20' in mapping['physiology']['face_policy']
    source=load_tables(folder)
    assert any(r['arrival_flux_umol_s'] is not None for r in source['light_samples.csv'])
    bridge.split_canopy_results(folder,'P1',tmp_path/'split')
    assert bridge.validate_growth_light_package(tmp_path/'split')['valid']
    split=load_tables(tmp_path/'split')
    for table,records in split.items():
        expected=source[table] if table=='light_intervals.csv' else [r for r in source[table] if r['plant_instance_id']=='P1']
        assert records==expected
    assert read_json(tmp_path/'split/consumer_mapping.json')==mapping
