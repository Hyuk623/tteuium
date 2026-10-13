"""Synthetic contract exercises; no observed plant measurements or new coefficients."""
from copy import deepcopy
import csv
import json
from pathlib import Path

import pytest
from tools import fsp_carbon_diagnostic as fsp
from tools.fsp_carbon_diagnostic_demo import synthetic_request
from tools.tests.test_fsp_carbon_diagnostic import run, inverse_setup, rehash_geometry
from tools.leaf_light import common


def supported_request():
    """Invented evidence declarations exercise the measured-input boundary only."""
    request = synthetic_request()
    ctx = request['light_series']['context']
    for patch in request['light_series']['patches']:
        patch['geometry_kind'] = 'measured_tissue'
        patch['area_evidence'] = dict(schema_version='p4-area-evidence-1', quantity='physical_one_sided_lamina',
            status='supported', unit='m2', value=patch['area_weight_m2'], spatial_support='located_tissue_partition',
            source_ref='invented_area_table', source_sha256=common.digest('invented_area_table'), source_row_id=patch['patch_id'],
            support_source_ref='invented_independent_support_review', tissue_partition_id='tissue_'+patch['patch_id'],
            partition_source_ref='invented_disjoint_partition_review', partition_sha256=common.digest('invented_partitions'),
            **{k:ctx[k] for k in ('plant_instance_id','area_basis_id','geometry_hash')},
            organ_id=patch['organ_id'],patch_id=patch['patch_id'])
        patch['biological_face_evidence'] = dict(kind='observed_anatomical_mapping',face='adaxial',
            plant_instance_id=ctx['plant_instance_id'],organ_id=patch['organ_id'],source_ref=patch['face_source_ref'],
            source_sha256=common.digest('invented_biological_mapping'))
    return request


def canopy_request(plant='plant1'):
    req=supported_request()
    def rename(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='plant_instance_id':value[key]=plant
                else:rename(item)
        elif isinstance(value,list):
            for item in value:rename(item)
    rename(req)
    light=req['light_series']
    light.update(light_scope='canopy',canopy_provenance=dict(canopy_id='invented_canopy',
        plant_instance_ids=['plant1','plant2'],geometry_hash=common.digest('invented_full_canopy'),
        source_ref='invented_full_canopy_transport',source_sha256=common.digest('invented_light_table')))
    for sample in light['samples']:
        sample.update(canopy_id='invented_canopy',canopy_geometry_hash=light['canopy_provenance']['geometry_hash'])
    return req


def endpoint_evidence(req):
    for side in ('start','end'):
        req['p3_interval']['organ_states_'+side][0]['geometry_kind']='measured_tissue'
    rehash_geometry(req)
    for patch in req['light_series']['patches']:
        patch['area_evidence']['geometry_hash']=req['p3_interval']['geometry_hash_start']
    for side in ('start','end'):
        row=req['p3_interval']['organ_states_'+side][0]
        req['p3_interval']['area_evidence_'+side]={row['organ_id']:dict(schema_version='p4-area-evidence-1',quantity='physical_one_sided_lamina',status='supported',
            unit='cm2',value=row['supported_area_cm2'],spatial_support='organ_lamina',plant_instance_id='plant1',
            organ_id=row['organ_id'],area_basis_id=req['p3_interval']['area_basis_id'],
            geometry_hash=req['p3_interval']['geometry_hash_'+side],source_ref='invented_endpoint_'+side,
            source_sha256=common.digest('invented_endpoint_'+side),source_row_id=row['organ_id'],support_source_ref='invented_area_review')}


def test_supported_declaration_keeps_arithmetic_and_traceability():
    old=run(synthetic_request());new=run(supported_request())
    for component in ('supply','maintenance','demand','budget'):
        assert new['components'][component]['value_gC']==old['components'][component]['value_gC']
    assert new['diagnostic']['area_evidence_status']=='supported_declaration'
    assert new['diagnostic']['physical_area_validated'] is False
    assert new['diagnostic']['accepted_for_domain'] is False
    for row in new['components']['supply']['rows']:
        assert row['area_unit']=='m2' and row['area_support']['area_evidence']['source_row_id']==row['patch_id']
        assert row['light_sources'][0]['fixture_id']=='fixture1'


@pytest.mark.parametrize('quantity',['projected_proxy','hull_surface','hull_envelope','two_face_mesh','area_review_A1','area_review_A2'])
def test_unsupported_area_never_becomes_supply_or_shortage(quantity):
    req=supported_request();req['light_series']['patches'][0]['area_evidence']['quantity']=quantity
    result=run(req)
    assert result['diagnostic']['status']=='unavailable'
    assert result['components']['supply']['value_gC'] is None
    assert result['diagnostic']['sufficiency_ratio'] is None
    assert 'physical_area_unsupported' in result['diagnostic']['issue_codes']


@pytest.mark.parametrize('field',['area_evidence','source_sha256','source_row_id','support_source_ref','spatial_support','partition_source_ref'])
def test_real_area_missing_dependency_is_explicit(field):
    req=supported_request();patch=req['light_series']['patches'][0]
    (patch if field=='area_evidence' else patch['area_evidence']).pop(field)
    result=run(req)
    assert result['components']['supply']['status']=='unavailable'
    assert result['diagnostic']['area_evidence_status']=='unavailable'
    assert result['diagnostic']['physical_area_validated'] is False


@pytest.mark.parametrize('field',['tissue_partition_id','source_row_id'])
def test_duplicate_tissue_cannot_hide_behind_unique_patch_ids(field):
    req=supported_request();a,b=req['light_series']['patches']
    b['area_evidence'][field]=a['area_evidence'][field]
    result=run(req)
    assert 'duplicate_tissue_partition' in result['diagnostic']['issue_codes']
    assert result['components']['supply']['value_gC'] is None


@pytest.mark.parametrize('field',['plant_instance_id','organ_id','patch_id','area_basis_id','geometry_hash'])
def test_area_identity_exact(field):
    req=supported_request();req['light_series']['patches'][0]['area_evidence'][field]='other'
    assert 'area_identity_mismatch' in run(req)['diagnostic']['issue_codes']


@pytest.mark.parametrize('kind',[None,'unsigned_normal','winding','top_projection'])
def test_geometric_face_convention_is_not_biological_evidence(kind):
    req=supported_request();patch=req['light_series']['patches'][0]
    if kind is None:patch.pop('biological_face_evidence')
    else:patch['biological_face_evidence']['kind']=kind
    assert 'illuminated_faces_evidence_missing' in run(req)['diagnostic']['issue_codes']


def test_m2_supply_and_cm2_inverse_are_explicit_not_guessed():
    req=supported_request();inverse_setup(req);endpoint_evidence(req)
    result=run(req)
    assert result['components']['demand']['status']=='available'
    assert sum(p['area_weight_m2'] for p in req['light_series']['patches'])==req['p3_interval']['organ_states_start'][0]['supported_area_cm2']*1e-4
    req['light_series']['patches'][0]['area_weight_cm2']=50
    assert 'area_unit_incompatible' in run(req)['diagnostic']['issue_codes']
    req=supported_request();inverse_setup(req);endpoint_evidence(req)
    req['p3_interval']['organ_states_end'][0]['supported_area_m2']=.02
    endpoint_evidence(req)
    assert 'area_unit_incompatible' in run(req)['diagnostic']['issue_codes']


def test_unsupported_area_inverse_does_not_create_mass():
    req=supported_request();inverse_setup(req);endpoint_evidence(req)
    req['p3_interval']['area_evidence_end']['leaf'].update(area_method='area_review_A2',estimator_status='unvalidated')
    result=run(req)
    assert result['components']['demand']['value_gC'] is None
    assert 'physical_area_unsupported' in result['diagnostic']['issue_codes']


def test_canopy_keeps_plants_reserves_and_maintenance_separate():
    a,b=run(canopy_request()),run(canopy_request('plant2'))
    assert a['diagnostic']['reserve_provenance_chain_id']!=b['diagnostic']['reserve_provenance_chain_id']
    for comp in ('supply','maintenance','demand'):
        assert a['components'][comp]['value_gC']==b['components'][comp]['value_gC']
    for result,plant in [(a,'plant1'),(b,'plant2')]:
        assert {r['plant_instance_id'] for r in result['components']['supply']['rows']}=={plant}
        assert all(len(r['canopy_provenance']['plant_instance_ids'])==2 for r in result['components']['supply']['rows'])
    assert fsp.validate_diagnostic_table([a,b])['status']=='valid'


@pytest.mark.parametrize('mutation',['member','sample','source','patch'])
def test_canopy_mismatch_refused(mutation):
    req=canopy_request();light=req['light_series']
    if mutation=='member':light['canopy_provenance']['plant_instance_ids']=['plant2']
    if mutation=='sample':light['samples'][0]['canopy_geometry_hash']=common.digest('other')
    if mutation=='source':light['canopy_provenance'].pop('source_sha256')
    if mutation=='patch':
        light['patches'][0]['plant_instance_id']='plant2'
        with pytest.raises(common.StudyError,match='Patch context'):run(req)
        return
    assert run(req)['components']['supply']['status']=='unavailable'


def test_no_imaging_multiplier_and_canopy_fixtures_sum_once():
    req=canopy_request();baseline=run(req)
    for patch in req['light_series']['patches']:patch.update(G=.5,imaging_lambda=.3,curvature_factor=7)
    assert run(req)['components']['supply']['value_gC']==baseline['components']['supply']['value_gC']
    light=req['light_series'];light['fixture_ids'].append('fixture2')
    light['samples'] += [dict(row,fixture_id='fixture2') for row in deepcopy(light['samples'])]
    combined=run(req)
    single=canopy_request()
    for row in single['light_series']['samples']:row['ppfd_umol_m2_s']*=2
    assert combined['components']['supply']['value_gC']==run(single)['components']['supply']['value_gC']
    assert combined['components']['maintenance']['value_gC']==baseline['components']['maintenance']['value_gC']


def test_canopy_tags_cannot_silently_drop_full_canopy_provenance():
    req=canopy_request()
    req['light_series'].pop('light_scope');req['light_series'].pop('canopy_provenance')
    assert 'canopy_provenance_missing' in run(req)['diagnostic']['issue_codes']


@pytest.mark.parametrize('case',['supported','area_missing','face_missing','mass_missing','canopy'])
def test_cli_json_csv_dependencies_and_provenance(case,tmp_path,monkeypatch):
    req=canopy_request() if case=='canopy' else supported_request()
    if case=='area_missing':req['light_series']['patches'][0].pop('area_evidence')
    if case=='face_missing':req['light_series']['patches'][0].pop('biological_face_evidence')
    if case=='mass_missing':req['carbon_state']['organ_masses'][0].pop('source_ref')
    monkeypatch.setattr(common,'BUILD',tmp_path)
    path=tmp_path/'request.json';path.write_text(json.dumps(req),encoding='utf-8')
    assert fsp.main(['diagnose','--input',str(path),'--out',str(tmp_path/'out')])==0
    result=json.loads((tmp_path/'out/result.json').read_text(encoding='utf-8'))
    with (tmp_path/'out/diagnostics.csv').open(encoding='utf-8') as f:row=list(csv.DictReader(f))[0]
    assert row['area_evidence_status']==result['diagnostic']['area_evidence_status']
    assert json.loads(row['canopy_provenance_json'])==req['light_series'].get('canopy_provenance')
    if case.endswith('missing'):
        assert row['status']=='unavailable' and row['sufficiency_ratio']==''
    else:
        with (tmp_path/'out/component_fluxes.csv').open(encoding='utf-8') as f:flux=list(csv.DictReader(f))[0]
        assert json.loads(flux['area_support'])['area_evidence']['source_sha256']


def test_export_rejects_forged_area_provenance(tmp_path,monkeypatch):
    result=run(supported_request());result['components']['supply']['rows'][0]['area_support']['tissue_partition_id']='forged'
    monkeypatch.setattr(common,'BUILD',tmp_path)
    with pytest.raises(common.StudyError):fsp.export_diagnostic(result,tmp_path/'bad')
