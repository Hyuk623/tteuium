from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools.groimp_density import (SENSORS, prepare, surface_gate, sensor_triangles,
    validate_study, validate_ppfd, parse_log, make_rgg, verify_prepared)
from tools.tests.test_canopy_light import inputs as canopy_inputs
from tools.leaf_light.common import StudyError, file_hash, read_json, rows, write_json, write_rows
from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS


def density_inputs(folder: Path) -> Path:
    canopy_inputs(folder)
    scene=read_json(folder/'scene.json');scene['scenarios']=[]
    for key,value in [('absorptance',1.),('transmittance',0.),('reflectance',0.)]:
        scene['leaf_optics'][key]['value']=value
    write_json(folder/'scene.json',scene)
    geometry=rows(folder/'geometry.csv');
    for r in geometry:r['normal_convention']='adaxial_ccw'
    write_rows(folder/'geometry.csv',geometry,LEAF_SURFACES_CSV_COLUMNS)
    review=dict(geometry_sha256=file_hash(folder/'geometry.csv'),geometry_variant_id='v25',snapshot_date='2026-09-30',surface_kind='leaf_triangles',review_state='accepted',reviewer='synthetic_test_only',reviewed_at='2026-09-30',validated_metric=False)
    write_json(folder/'review.json',review)
    # Deliberately explicit synthetic lamp; not an actual LED equivalence claim.
    adapter=dict(scene_sha256=file_hash(folder/'scene.json'),review_state='accepted',reviewer='synthetic_test_only',
        coordinate_frame='grow_m',power_convention='photon_umol_s',empty_scene_validation='synthetic fixture only',
        header_rgg='module Lamp extends LightNode;',
        initialization_rgg='[Translate(0.3f,0.2f,0.5f) Lamp().(setLight(new PointLight().(setPower(1000f))))]',
        data_kind='synthetic_isotropic_surrogate',absolute_led_ppfd_valid=False)
    write_json(folder/'adapter.json',adapter)
    write_rows(folder/'sensors.csv',[dict(sensor_id='s1',x_mm=300,y_mm=200,z_mm=50,normal_x=0,normal_y=0,normal_z=1,width_mm=20,height_mm=20,height_group='lower')],SENSORS)
    original=read_json(folder/'plan.json')['cases']
    cases=[]
    for old in original:
        c={k:v for k,v in old.items() if k not in ('scene','plot_area_m2')}
        c.update(density_id=c['case_id'],snapshot_date='2026-09-30',surface_review='review.json')
        for item in c['instances']:
            item['source_session_id']='synthetic'
            item.setdefault('placement',deepcopy(scene['plants'][0]))
        cases.append(c)
    plan=dict(schema_version='groimp-density-flowering-1',co2_recorded=False,
        groimp_optical_transport='diffuse_reflection_and_transmission',
        plot_width_mm=600,plot_depth_mm=400,rays=200000,seed=42,max_depth=3,
        scene='scene.json',sensors='sensors.csv',lamp_adapter='adapter.json',cases=cases)
    write_json(folder/'density.json',plan)
    return folder/'density.json'


def test_reuses_geometry_and_fixed_lighting_and_preserves_inputs(tmp_path):
    path=density_inputs(tmp_path);before=file_hash(tmp_path/'geometry.csv')
    result=prepare(path,tmp_path/'prepared')
    assert result['status']=='prepared'
    assert [c['n_triangles'] for c in result['cases']]==[4,8]
    assert file_hash(tmp_path/'geometry.csv')==before
    assert result['cases'][1]['plants_per_m2']==pytest.approx(2/.24)
    text=(tmp_path/'prepared/single/leaves/Model.rgg').read_text()
    assert '0.26f' in text and 'leafOptics' in text
    assert 'setSeed(42L)' in text and 'PositionMarker' not in text


def test_gate_blocks_unreviewed_changed_and_missing_surface(tmp_path):
    path=density_inputs(tmp_path);plan=read_json(path);c=plan['cases'][0]
    review=read_json(tmp_path/'review.json');review['geometry_sha256']='wrong'
    write_json(tmp_path/'review.json',review)
    assert 'surface_review_hash_mismatch' in surface_gate(c,tmp_path)[0]
    write_rows(tmp_path/'geometry.csv',[],LEAF_SURFACES_CSV_COLUMNS)
    result=prepare(path,tmp_path/'empty')
    assert all(c['status']=='blocked' for c in result['cases'])
    assert not list((tmp_path/'empty').rglob('Model.rgg'))


def test_sensor_direction_and_area():
    s=dict(x_mm=10,y_mm=20,z_mm=30,normal_x=1,normal_y=0,normal_z=0,width_mm=20,height_mm=10)
    v=sensor_triangles(s)
    cross=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0])
    assert np.all(cross[:,0]>0)
    assert np.linalg.norm(cross,axis=1).sum()/2==pytest.approx(200)
    assert v.reshape(-1,3).min(0)[0]==10


def test_independent_sensor_matching_and_zero_denominator():
    p=dict(case_id='c',sensor_id='s',height_group='lower',snapshot_date='2026-09-30',predicted_ppfd_umol_m2_s=10,scene_sha256='scene',sensor_spec_sha256='sensor')
    m=dict(reading_id='r',case_id='c',sensor_id='s',date='2026-09-30',split_role='validation',ppfd_umol_m2_s=0,scene_sha256='scene',sensor_spec_sha256='sensor',sensor_model='meter',calibration_reference='certificate',all_fixtures_full_output='true')
    result=validate_ppfd([p],[m]);assert result['metrics'][0]['mae']==10
    assert result['metrics'][0]['nrmse'] is None
    m['split_role']='calibration';assert validate_ppfd([p],[m])['status']=='unavailable'
    m['scene_sha256']='other'
    with pytest.raises(StudyError,match='sha256'):
        validate_ppfd([p],[m])


def test_incomplete_and_malformed_results_are_not_success(tmp_path):
    log=tmp_path/'groimp.log';log.write_text('LEAF\tt1\t2\t1\n')
    with pytest.raises(StudyError,match='Incomplete'):parse_log(log)
    log.write_text('LEAF\tt1\t1\t2\nSANITY_DONE\n')
    with pytest.raises(StudyError,match='Invalid'):parse_log(log)


def test_fixed_lighting_cannot_be_overridden_per_density(tmp_path):
    path=density_inputs(tmp_path);plan=read_json(path);plan['cases'][0]['scenarios']=[]
    write_json(path,plan)
    with pytest.raises(StudyError,match='override'):prepare(path,tmp_path/'bad')


def test_prepared_coordinate_mutation_rejected(tmp_path):
    path=density_inputs(tmp_path);result=prepare(path,tmp_path/'prepared')
    (tmp_path/'prepared/single/triangles.csv').write_text('changed')
    with pytest.raises(StudyError,match='changed'):
        verify_prepared(tmp_path/'prepared',result)


def test_same_density_cannot_change_count_and_observed_copies_rejected(tmp_path):
    path=density_inputs(tmp_path);plan=read_json(path)
    plan['cases'][1]['density_id']=plan['cases'][0]['density_id']
    with pytest.raises(StudyError,match='different densities'):validate_study(plan)
    plan['cases'][1]['density_id']='pair';plan['cases'][1]['data_kind']='observed_geometry'
    with pytest.raises(StudyError,match='Copied template'):validate_study(plan)
