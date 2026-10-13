"""Synthetic contracts; no recorded measurements or configuration are edited."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools import p2_lamp_calibration as cal
from tools.leaf_light import common
from tools.tests.test_ppfd_validation import scene_file, point, SENSOR


def fixture(folder):
    folder.mkdir(parents=True)
    scene_file(folder, emitting_center_grow_mm=[0.,0.,300.], emitting_length_mm=100., emitting_width_mm=40.,
               photon_flux_umol_s=50., half=60.)
    pts = [point(x,0,70,point_id=f'p{i}',split_role='calibration' if i < 3 else 'validation')
           for i,x in enumerate((-100.,0.,100.,150.))]
    rig = dict(surface_id='wall',kind='rectangle',role='rig',center_x_mm=250.,center_y_mm=0.,center_z_mm=200.,
        normal_x=-1.,normal_y=0.,normal_z=0.,width_axis_x=0.,width_axis_y=1.,width_axis_z=0.,
        width_mm=600.,height_mm=400.,reflectance=.5,transmittance=0.,geometry_status='assumed',
        geometry_source='synthetic test',optics_status='assumed',optics_source='synthetic test',note='')
    readings=[]
    for p in pts:
        r = {c:'' for c in cal.pv.READING_COLUMNS}
        r.update(point_id=p['point_id'],split_role=p['split_role'],ppfd_umol_m2_s=200.,
                 stage='empty_rig',all_fixtures_full_output='yes',ambient_condition='excluded_dark',
                 disturbed='no',sensor_moved_leaves='no')
        readings.append(r)
    for name, records, columns in [('rig.csv',[rig],cal.pv.RIG_SURFACE_COLUMNS),
        ('points.csv',pts,cal.pv.POINT_COLUMNS),('readings.csv',readings,cal.pv.READING_COLUMNS),
        ('sensors.csv',[dict(SENSOR,sensing_width_mm=60,sensing_height_mm=60)],cal.pv.SENSOR_COLUMNS)]:
        common.write_rows(folder/name,records,columns)
    plan=dict(schema_version=cal.SCHEMA,source_kind='synthetic_test_only',source_ref='explicit software fixture',
        bounds=dict(photon_flux_scale=[.1,5.],effective_reflectance_grey=[0.,.8]),reflectance_grid=[0.,.4,.8],
        offset_axis=None,offset_grid_mm=None,solver=dict(coarse_rays=200000,final_rays=4800000,
            seeds=[123,456],max_depth=8,max_native_jobs=42,timeout_s=120),wavelength_nm=550,
        wavelength_source='assumed synthetic monochromatic conversion',variants=[dict(variant_id='synthetic',
            provenance='synthetic only',conditional_reasons=['synthetic_scene_not_real_measurement'],
            scene='scene.json',rig_surfaces='rig.csv',points='points.csv',readings='readings.csv',sensors='sensors.csv',
            fit_surface_ids=['wall'],enclosure_surface_ids=['wall'],disc_segments=None)])
    common.write_json(folder/'plan.json',plan)
    return folder/'plan.json'


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    p=fixture(tmp_path/'inputs'); cal.freeze(p,tmp_path/'frozen')
    return tmp_path


def test_freeze_retains_absolute_blockers_and_budget(prepared):
    data=cal.load_frozen(prepared/'frozen')
    assert data['max_planned_native_jobs']==42
    assert data['variants'][0]['absolute_blockers']
    assert data['variants'][0]['scene_data']['fixtures'][0]['distribution']['half_intensity_half_angle_deg']['value']==60


def test_freeze_refuses_changed_sources(prepared):
    p=prepared/'inputs'/'points.csv';p.write_text(p.read_text()+'\n')
    with pytest.raises(common.StudyError,match='source changed'):cal.load_frozen(prepared/'frozen')


@pytest.mark.parametrize('change,match',[
    (lambda p:p['solver'].update(max_native_jobs=1),'budget'),
    (lambda p:p['bounds'].update(half_intensity_half_angle_deg=[1,2]),'only flux'),
    (lambda p:p['variants'][0]['points_data'][0].update(split_role='validation'),'calibration points'),
    (lambda p:p['variants'][0]['readings_data'][0].update(split_role='validation'),'split mismatch'),
    (lambda p:p['variants'][0]['rig_data'][0].update(transmittance=.1),'opaque'),
    (lambda p:p['solver'].update(seeds=[1,1]),'distinct'),
    (lambda p:p.update(reflectance_grid=[0.,.4,.9]),'bounds'),
])
def test_preflight_refuses_incomplete_or_unsafe_plan(prepared,change,match):
    p=cal.load_frozen(prepared/'frozen');change(p)
    with pytest.raises(common.StudyError,match=match):cal.validate_plan(p)


class FakeEvaluator:
    """Only exercises optimizer/split logic; this is never evidence of native transport."""
    calls=[]
    def __init__(self,*args):pass
    def __call__(self,variant,points,rho,offset,scale,rays,seed,control='full'):
        self.calls.append((tuple(p['split_role'] for p in points),rays,control))
        return np.array([100.+rho*(10.+int(p['point_id'][1:])*20.) for p in points])*scale


def test_heldout_values_cannot_change_fit(prepared):
    a=cal.run(prepared/'frozen',prepared/'run1',evaluator_factory=FakeEvaluator)
    p=common.read_json(prepared/'inputs'/'plan.json')
    values=common.rows(prepared/'inputs'/'readings.csv');values[-1]['ppfd_umol_m2_s']=9999
    common.write_rows(prepared/'inputs'/'readings.csv',values,cal.pv.READING_COLUMNS)
    cal.freeze(prepared/'inputs'/'plan.json',prepared/'frozen2')
    b=cal.run(prepared/'frozen2',prepared/'run2',evaluator_factory=FakeEvaluator)
    assert a['variants'][0]['fitted_parameters']==b['variants'][0]['fitted_parameters']
    assert a['variants'][0]['validation']!=b['variants'][0]['validation']
    assert all(set(roles)=={'calibration'} for roles,rays,_ in FakeEvaluator.calls if rays==200000)
    assert a['physical_accuracy_validated'] is False


def test_zero_unknown_and_negative_are_not_interchangeable():
    with pytest.raises(common.StudyError,match='zero illumination'):cal.fit_scale([0,0],[1,2],[0,5])
    with pytest.raises(common.StudyError,match='invalid model'):cal.fit_scale([np.nan,0],[1,2],[0,5])
    assert cal.fit_scale([1,2],[0,0],[0,5])==0
    assert cal.metrics([1,2],[0,0])['rms_percent_of_mean'] is None


def test_photon_watt_roundtrip():
    for wavelength in (400,550,700):
        factor=cal.photon_factor(wavelength)
        assert (73./factor)*factor==pytest.approx(73.,abs=1e-12,rel=1e-12)


def test_fit_export_keeps_fitted_scene_and_uncertainty(prepared):
    report=cal.run(prepared/'frozen',prepared/'fit',evaluator_factory=FakeEvaluator)
    common.write_json(prepared/'evidence.json',{'source_kind':'synthetic_test_only'})
    contract=dict(frame_id='synthetic',coordinate_frame='grow_mm_z_up',height_basis='synthetic_floor',
        time_support=dict(start_at='2026-10-13T00:00:00+09:00',end_at='2026-10-14T00:00:00+09:00',
                          source_ref=dict(path='evidence.json',sha256=common.file_hash(prepared/'evidence.json'))))
    common.write_json(prepared/'contract.json',contract)
    cal.export_reference(prepared/'fit'/'fit.json','synthetic',prepared/'contract.json',prepared/'field')
    data=common.read_json(prepared/'field'/'frozen_prediction.json')
    from tools.reference_dli_frozen import read_prediction
    provenance,row=read_prediction(prepared/'field'/'frozen_prediction.json',
        dict(frame_id='synthetic',coordinate_frame='grow_mm_z_up',height_basis='synthetic_floor',position_mm=[0.,0.,70.]),{})
    assert provenance['source_kind']=='fitted' and row['point_id']=='p1'
    assert data['uncertainty']['systematic_status']=='unavailable'
    scene=common.read_json(prepared/'field'/'scene.json')
    assert scene['fixtures'][0]['photon_flux_umol_s']['status']=='fitted'
