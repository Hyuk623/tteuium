"""Discriminating area-review boundaries; artificial geometry is never physical validation."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tomato3d.io.schemas import LEAF_PATCHES_CSV_COLUMNS, LEAF_SURFACES_CSV_COLUMNS
from tools import light_growth_bridge as bridge
from tools import hierarchical_light as hierarchy
from tools.leaf_light.common import file_hash, read_json, rows, write_json, write_rows
from tools.light_geometry_evidence import audit_surface, VERSION
from tools.light_growth_consumer import load_tables
from tools.tests.test_light_growth_bridge import make_request
from tools.tests.test_light_reference_faces import add_reference


def test_a2_missing_location_shape_and_cli(tmp_path):
    path=tmp_path/'a2.csv'
    write_rows(path,[dict(area_cm2=12.,normal_zenith_rad=.4,normal_azimuth_rad=.2)],
               ['area_cm2','normal_zenith_rad','normal_azimuth_rad'])
    report=audit_surface(path,'observed_geometry')
    assert report['geometric_computability']=='unavailable'
    assert set(report['reasons'])=={'receiving_surface_position_unavailable','receiving_surface_shape_unavailable'}
    assert report['physical_ppfd_eligibility']=='unavailable'
    # output_dir intentionally only permits build/: exercise CLI under its generated root.
    from tools.leaf_light.common import BUILD
    import uuid
    out=BUILD/('area_review_cli_test_'+uuid.uuid4().hex)
    run=subprocess.run([sys.executable,'-X','utf8','-m','tools.light_geometry_evidence',
        '--geometry',str(path),'--data-kind','observed_geometry','--out',str(out)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    assert read_json(out/'geometry_audit.json')==report


def test_rectangular_patch_area_units_and_unavailable_position(tmp_path):
    path=tmp_path/'patch.csv'
    item=dict(plant_id='P',session_id='s',geometry_variant_id='g',geometry_source='simplified',
        organ_id='leaf',centroid_x_mm=0.,centroid_y_mm=0.,centroid_z_mm=30.,area_mm2=1200.,
        normal_tilt_deg=0.,normal_azimuth_deg=0.,length_to_width_ratio=2.)
    write_rows(path,[item],LEAF_PATCHES_CSV_COLUMNS)
    report=audit_surface(path,'synthetic'); v=report['variants'][0]
    assert report['geometric_computability']=='available'
    assert v['receiver_triangle_count']==2
    assert v['one_sided_area_mm2']==pytest.approx(1200.,abs=1e-10,rel=1e-9)
    assert v['one_sided_area_m2']==pytest.approx(12.*1e-4,abs=1e-10,rel=1e-9)
    assert report['physical_ppfd_eligibility']=='unavailable'
    item['centroid_z_mm']='unavailable';write_rows(path,[item],LEAF_PATCHES_CSV_COLUMNS)
    assert 'receiving_surface_position_unavailable' in audit_surface(path,'synthetic')['reasons']
    item['centroid_z_mm']='not-a-number';write_rows(path,[item],LEAF_PATCHES_CSV_COLUMNS)
    assert audit_surface(path,'synthetic')['geometric_computability']=='invalid'


def test_duplicate_reversed_face_is_invalid_not_double_area(tmp_path):
    from tools.hierarchical_light_demo import synthetic_inputs
    source=synthetic_inputs(tmp_path/'inputs',groups=())
    path=source.parent/'leaf_surfaces.csv'; table=rows(path)
    copied=dict(table[0],triangle_id='other_id')
    for a in 'xyz': copied['v1_'+a+'_mm'],copied['v2_'+a+'_mm']=copied['v2_'+a+'_mm'],copied['v1_'+a+'_mm']
    table.append(copied);write_rows(path,table,LEAF_SURFACES_CSV_COLUMNS)
    report=audit_surface(path,'synthetic')
    assert report['geometric_computability']=='invalid' and report['reasons']==['duplicate_geometry_face']


@pytest.fixture
def package(tmp_path,monkeypatch):
    request=make_request(tmp_path)
    add_reference(tmp_path,request,monkeypatch)
    bridge.build_package(request,tmp_path/'package')
    return tmp_path


def test_export_geometry_unvalidated_reference_available_and_no_botanical_inference(package):
    folder=package/'package'; manifest=read_json(folder/'package.json')
    assert manifest['optical_geometry_contract']==VERSION
    assert bridge.validate_growth_light_package(folder)['valid']
    evidence=read_json(folder/'audit.json')['optical_geometry'][0]
    assert evidence['geometric_computability']=='available'
    assert evidence['physical_ppfd_eligibility']=='unavailable'
    assert evidence['data_kind']=='synthetic'
    assert evidence['surface_reviews'] and evidence['placements']
    samples=load_tables(folder)['light_samples.csv']
    assert all(r['illuminated_faces'] is None for r in samples)
    assert any(r['received_ppfd_umol_m2_s']>0 for r in samples)
    reference=read_json(folder/'consumer_mapping.json')['growth']['reference_dli']
    assert reference['status']=='available' and reference['value']==pytest.approx(11.52)
    # Reference arithmetic has no optical-geometry dependency even for unplaceable A2 data.
    bad=package/'a2.csv';write_rows(bad,[{'area_cm2':12}],['area_cm2'])
    assert audit_surface(bad,'observed_geometry')['geometric_computability']=='unavailable'
    from tools.reference_dli_consumer import validate_result
    assert validate_result(package/'reference_result/reference_dli.json')['valid']


@pytest.mark.parametrize('mutation',['physical_claim','geometry_claim','source_area','review_claim','downgrade'])
def test_rehashed_false_eligibility_or_area_is_rejected(package,mutation):
    folder=package/'package'; manifest=read_json(folder/'package.json')
    if mutation=='physical_claim':manifest['physical_validation']=True
    elif mutation=='downgrade':manifest.pop('optical_geometry_contract')
    else:
        audit=read_json(folder/'audit.json'); g=audit['optical_geometry'][0]
        if mutation=='geometry_claim':g['physical_ppfd_eligibility']='available'
        elif mutation=='review_claim':g['surface_reviews'][0]['review']['validated_metric']=True
        else:g['variants'][0]['one_sided_area_m2']*=2
        write_json(folder/'audit.json',audit)
        manifest['artifact_hashes']['audit.json']=file_hash(folder/'audit.json')
    write_json(folder/'package.json',manifest)
    check=bridge.validate_growth_light_package(folder)
    assert not check['valid'] and any('physical_ppfd_claim' in r or 'geometry_evidence_mismatch' in r or
                                    'missing_optical_geometry_contract' in r for r in check['errors'])


def test_canopy_split_preserves_neighbor_shadow_and_additive_flux(package,monkeypatch):
    folder=package/'package'
    # Any attempted transport during reporting-only extraction is a failure.
    import tomato3d.light.raytrace as transport
    def forbidden(*a,**k):raise AssertionError('split must not rerun isolated transport')
    monkeypatch.setattr(transport,'direct_light',forbidden)
    monkeypatch.setattr(bridge,'export_spatial_light',forbidden)
    all_samples=load_tables(folder)['light_samples.csv']
    for pid in ('P1','P2'):
        split=package/('split_'+pid);bridge.split_canopy_results(folder,pid,split)
        assert bridge.validate_growth_light_package(split)['valid']
        assert load_tables(split)['light_samples.csv']==[r for r in all_samples if r['plant_instance_id']==pid]
        assert read_json(split/'audit.json')['optical_geometry']==read_json(folder/'audit.json')['optical_geometry']
    full=[r for r in all_samples if r['time_step_id']=='full_output' and r['fixture_id']=='all']
    flux=lambda rs:sum(r['quadrature_area_m2']*r['received_ppfd_umol_m2_s'] for r in rs)
    assert sum(flux([r for r in full if r['plant_instance_id']==pid]) for pid in ('P1','P2'))==pytest.approx(flux(full),abs=1e-10,rel=1e-9)
    # Actual hierarchy result already computed with/without neighbor C, using identical target support.
    result=read_json(package/'legacy/results.json')
    target=next(r for r in result['tables']['leaflet_interactions'] if r['leaflet_id']=='target' and r['fixture_id']=='all' and r['quantity']=='received')
    assert target['shapley_C_umol_s']>0
    assert flux([r for r in full if r['leaflet_id']=='target'])==pytest.approx(target['full_umol_s'],abs=1e-10,rel=1e-9)


def test_hull_review_cannot_establish_optical_surface(tmp_path):
    from tools.hierarchical_light_demo import synthetic_inputs
    source=synthetic_inputs(tmp_path/'inputs',groups=())
    review=read_json(source.parent/'review.json');review.update(surface_kind='visual_hull',validated_metric=True,suitable_for_ppfd=True)
    write_json(source.parent/'review.json',review)
    audit=hierarchy.audit_inputs(source)
    assert not audit['transport_ready']
    assert any('not_accepted_leaf_triangles' in b for b in audit['transport_blockers'])
    assert audit['suitable_for_ppfd'] is False


@pytest.mark.parametrize('field',['leaf_area_proxy_cm2','hull_footprint_cm2','projected_area_cm2'])
def test_projection_proxy_is_missing_science_not_metric_surface(tmp_path,field):
    path=tmp_path/'proxy.csv';write_rows(path,[{field:17.}], [field])
    audit=audit_surface(path,'observed_geometry')
    assert audit['geometric_computability']=='unavailable'
    assert 'projected_area_not_physical_receiving_surface' in audit['reasons']
    assert audit['physical_ppfd_eligibility']=='unavailable'
