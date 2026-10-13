"""tools.ppfd_validation: contracts, adapter, python comparator, fit, comparison, staleness. No GroIMP run here.

Every reading written by these tests is a synthetic test fixture inside the pytest temp folder, never a measurement.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tomato3d.io.schemas import PPFD_READINGS_CSV_COLUMNS, LedFixture
from tomato3d.light.scene import build_emitters, load_scene
from tools import ppfd_validation as pv
from tools.leaf_light.common import StudyError, digest, file_hash, read_json, rows, write_json, write_rows

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SCENE = ROOT / 'tests' / 'fixtures' / 'light' / 'light_scene.example.json'
SENSOR = dict(sensor_id='q1', sensor_model='synthetic', serial_number='0', calibration_reference='synthetic',
              calibration_date='2026-10-01', sensing_shape='rectangle', sensing_width_mm='10', sensing_height_mm='10',
              sensing_diameter_mm='', angular_response='cosine_corrected', dimensions_status='measured',
              dimensions_source='synthetic test', probe_body_note='')


def iso_states(flux=1000.0, z_mm=500.0):
    em = SimpleNamespace(positions_grow_mm=np.array([[0.0, 0.0, z_mm]]), aim=np.array([0.0, 0.0, -1.0]),
                         axial_intensity_umol_s_sr=flux / (4 * math.pi), cosine_exponent=0.0, cos_cutoff=-1.0)
    return (SimpleNamespace(fixture_id='iso', emitters=em),)


def point(x, y, z, n=(0, 0, 1), **kw):
    return dict(dict(point_id=kw.pop('point_id', 'p'), stage='empty_rig', case_id='c', plant_id='', sensor_id='q1',
                     x_mm=str(x), y_mm=str(y), z_mm=str(z), normal_x=str(n[0]), normal_y=str(n[1]), normal_z=str(n[2]),
                     height_band='low', split_role='validation', position_status='measured',
                     position_source='synthetic', accessible='yes', note=''), **kw)


def scene_file(folder: Path, measured: bool = True, **fixture_update) -> Path:
    data = json.loads(EXAMPLE_SCENE.read_text(encoding='utf-8'))
    data['fixtures'] = data['fixtures'][:1]
    data['scenarios'] = []
    fx = data['fixtures'][0]
    fx['emitter_grid'] = [20, 2]
    fx['distribution']['half_intensity_half_angle_deg']['value'] = 45.0
    for k, v in fixture_update.items():
        if k == 'cutoff':
            fx['distribution']['cutoff_half_angle_deg'] = v
        elif k == 'half':
            fx['distribution']['half_intensity_half_angle_deg']['value'] = v
        else:
            fx[k]['value'] = v
    if measured:
        def mark(node):
            if isinstance(node, dict):
                if {'value', 'status', 'source'} <= set(node) and node['value'] is not None:
                    node['status'] = 'measured'; node['source'] = 'synthetic test fixture'
                for v in node.values():
                    mark(v)
            elif isinstance(node, list):
                for v in node:
                    mark(v)
        mark(data)
    path = folder / 'scene.json'
    write_json(path, data)
    return path


def study_folder(folder: Path, measured: bool = True, rig_extra=(), points=None, readings=None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    scene_file(folder, measured)
    write_rows(folder / 'lamp_conditions.csv', [dict(fixture_id='LED-front', output_setting='100', output_setting_unit='%',
               is_full_output='yes', spectrum_file='', spectrum_value_kind='', stabilization_min='30', status='measured',
               source='synthetic', note='')], pv.LAMP_CONDITION_COLUMNS)
    plate = dict(surface_id='plate', kind='occluder_plate', role='physical_occluder', center_x_mm='300', center_y_mm='130',
                 center_z_mm='200', normal_x='0', normal_y='0', normal_z='1', width_axis_x='1', width_axis_y='0',
                 width_axis_z='0', width_mm='300', height_mm='100', reflectance='0', transmittance='0',
                 geometry_status='measured', geometry_source='synthetic', optics_status='measured',
                 optics_source='synthetic', note='')
    write_rows(folder / 'rig_surfaces.csv', [plate, *rig_extra], pv.RIG_SURFACE_COLUMNS)
    write_rows(folder / 'sensors.csv', [SENSOR], pv.SENSOR_COLUMNS)
    if points is None:
        points = []
        for i, x in enumerate((100, 200, 300, 400, 500)):
            for j, z in enumerate((0, 100)):
                points.append(point(x, 130, z, point_id=f'e{i}{j}', split_role='calibration' if (i + j) % 2 else 'validation'))
        points += [point(300, 130, 0, point_id='o_in', stage='occluder', case_id='occ'),
                   point(1000, 130, 0, point_id='o_lit', stage='occluder', case_id='occ')]
        for p in points:
            if p['case_id'] == 'c':
                p['case_id'] = 'empty'
    write_rows(folder / 'measurement_points.csv', points, pv.POINT_COLUMNS)
    write_rows(folder / 'ppfd_readings.csv', readings or [], pv.READING_COLUMNS)
    write_json(folder / 'study.json', dict(
        schema_version=pv.STUDY_SCHEMA, study_id='synthetic_study', timezone='Asia/Seoul', scene='scene.json',
        lamp_conditions='lamp_conditions.csv', rig_surfaces='rig_surfaces.csv', sensors='sensors.csv',
        points='measurement_points.csv', readings='ppfd_readings.csv', spectrum=None,
        cases=[dict(case_id='empty', stage='empty_rig', session_id='s1', geometry_snapshot_date='2026-10-01'),
               dict(case_id='occ', stage='occluder', session_id='s1', geometry_snapshot_date='2026-10-01',
                    occluder_surface_ids=['plate'])],
        fit=dict(enabled_parameters=['photon_flux_scale'], bounds=dict(photon_flux_scale=[0.2, 5.0],
                 half_intensity_half_angle_deg=[30.0, 58.0]), half_angle_grid_step_deg=1.0,
                 min_points_above_parameters=1, profile_chi2_95=3.841458820694124),
        solver=dict(backend='groimp_cpu_lightmodel', rays=100000, max_depth=1, seed=5, convergence_rays=[1000, 2000],
                    convergence_seeds=[1, 2], max_local_native_jobs=2, numerical_convergence_rel_tol=None),
        python=dict(emitter_grid=[20, 2], sensor_samples=6, disc_segments=32, shadow_class_tolerance=0.02),
        sensitivity=dict(lamp_height_mm=[10], half_angle_deg=None, flux_rel=[0.05], sensor_tilt_deg=None, point_offset_mm=None),
        acceptance=dict(nrmse_max=None, abs_bias_max_umol_m2_s=None),
        inference=dict(min_independent_units_for_ci=None, bootstrap_resamples=None, bootstrap_seed=None)))
    return folder / 'study.json'


def reading(case, pid, rep, value, role, stage='empty_rig', **kw):
    base = dict(schema_version=pv.READINGS_SCHEMA, study_id='synthetic_study', run_id='r1', stage=stage, case_id=case,
                plant_id='', session_id='s1', geometry_snapshot_date='2026-10-01', sensor_id='q1', point_id=pid,
                repeat_id=str(rep), observed_at='2026-10-01T10:00:00+09:00', split_role=role,
                ppfd_umol_m2_s='' if value is None else str(value), all_fixtures_full_output='yes',
                ambient_condition='excluded_dark', led_stabilized_min='30', sensor_moved_leaves='no', disturbed='no',
                observer='synthetic', note='SYNTHETIC TEST FIXTURE')
    base.update(kw)
    return base


# ---------------------------------------------------------------- templates / audit
def test_templates_are_header_only_and_audit_lists_missing_inputs(tmp_path):
    out = tmp_path / 'tpl'
    pv.templates(out)
    for name in ('ppfd_readings.csv', 'measurement_points.csv', 'sensors.csv', 'rig_surfaces.csv'):
        assert rows(out / name) == []
    audit = pv.validate_inputs(out / 'study.json')
    names = ' '.join(m['input'] for m in audit['missing_physical_inputs'])
    assert audit['status'] == 'templates_only_no_measurements'
    assert 'LightScene' in names and 'quantum sensor' in names and 'independent PPFD readings' in names
    assert 'rays' in names and audit['validated_metric'] is False


def test_audit_flags_split_leakage_duplicates_and_naive_times(tmp_path):
    rd = [reading('empty', 'e00', 1, 10, 'validation'), reading('empty', 'e00', 1, 11, 'validation'),
          reading('empty', 'e00', 2, 12, 'calibration'), reading('empty', 'e10', 1, 5, 'calibration',
                                                                observed_at='2026-10-01T10:00:00')]
    audit = pv.validate_inputs(study_folder(tmp_path, readings=rd))
    text = ' | '.join(audit['issues'])
    assert 'duplicated repeat' in text
    assert 'repeats split across calibration and validation' in text
    assert 'timezone offset' in text
    assert audit['status'] == 'invalid'


def test_tomato3d_reading_adapter_keeps_old_contract(tmp_path):
    study = study_folder(tmp_path)
    pts = rows(tmp_path / 'measurement_points.csv')
    out = pv.to_tomato3d_readings([reading('empty', 'e00', 1, 10.5, 'validation')], pts, 'setup')
    assert list(out[0]) == list(PPFD_READINGS_CSV_COLUMNS) or set(out[0]) == set(PPFD_READINGS_CSV_COLUMNS)
    assert out[0]['split_role'] == 'evaluation' and out[0]['reading_id'] == 'empty:e00:1'
    assert study.is_file()


# ---------------------------------------------------------------- geometry, sensor, optics
def test_unit_normals_are_required_not_normalised():
    with pytest.raises(StudyError, match='unit vector'):
        pv.sensing_mesh(point(0, 0, 0, n=(0, 0, 2)), SENSOR, None)
    with pytest.raises(StudyError, match='not normalised silently'):
        pv.footprint_samples(point(0, 0, 0, n=(0, 0, 2)), SENSOR, 4)


def test_rectangle_and_disc_meshes_face_the_normal_and_keep_area():
    tris, area = pv.sensing_mesh(point(0, 0, 0, n=(0, 0, 1)), SENSOR, None)
    assert area == 100
    for t in tris:
        assert np.cross(t[1] - t[0], t[2] - t[0])[2] > 0
    disc = dict(SENSOR, sensing_shape='disc', sensing_diameter_mm='20')
    tris, area = pv.sensing_mesh(point(0, 0, 0, n=(0, 1, 0)), disc, 32)
    mesh_area = sum(np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) / 2 for t in tris)
    assert area == pytest.approx(math.pi * 100) and mesh_area == pytest.approx(area, rel=1e-9)
    assert all(np.cross(t[1] - t[0], t[2] - t[0])[1] > 0 for t in tris)
    with pytest.raises(StudyError, match='unsupported sensing shape'):
        pv.sensing_mesh(point(0, 0, 0), dict(SENSOR, sensing_shape='dome'), None)
    with pytest.raises(StudyError, match='disc_segments'):
        pv.sensing_mesh(point(0, 0, 0), disc, None)


def test_finite_area_cosine_response_front_tilted_edge_reversed():
    states = iso_states()
    sensor = dict(SENSOR, sensing_width_mm='30', sensing_height_mm='30')
    lamp = np.array([0, 0, 0.5])
    for c, n in (((0, 0, 0), (0, 0, 1)), ((300, 0, 0), (-math.sin(1.0), 0, math.cos(1.0)))):
        got = pv.python_point_ppfd(states, point(*c, n=n), sensor, 40)
        want = pv._analytic_sensor(lamp, 1000.0, None, None, np.array(c) / 1000, n, 0.03)
        assert got == pytest.approx(want, rel=2e-3)
    assert pv.python_point_ppfd(states, point(-300, 0, 0, n=(0, 1, 0)), sensor, 40) == 0.0  # edge-on
    assert pv.python_point_ppfd(states, point(0, 300, 0, n=(0, 0, -1)), sensor, 40) == 0.0  # reversed


def test_inverse_square_for_a_point_source():
    states = iso_states(z_mm=1000.0)
    near = pv.python_point_ppfd(states, point(0, 0, 500), SENSOR, 4)
    far = pv.python_point_ppfd(states, point(0, 0, 0), SENSOR, 4)
    assert near / far == pytest.approx(4.0, rel=1e-3)


def test_complete_and_partial_occlusion_classes():
    states = iso_states()
    sensor = dict(SENSOR, sensing_width_mm='30', sensing_height_mm='30')
    plate = pv.rig_surface_triangles(dict(surface_id='p', center_x_mm=0, center_y_mm=0, center_z_mm=250, normal_x=0,
                                          normal_y=0, normal_z=1, width_axis_x=1, width_axis_y=0, width_axis_z=0,
                                          width_mm=100, height_mm=100))
    assert pv.occlusion_class(states, point(0, 0, 0), sensor, [plate], 40, 0.02)[0] == 'shadow_interior'
    cls, frac = pv.occlusion_class(states, point(100, 0, 0), sensor, [plate], 40, 0.02)
    assert cls == 'shadow_edge' and 0.4 < frac < 0.6
    assert pv.occlusion_class(states, point(400, 0, 0), sensor, [plate], 40, 0.02)[0] == 'illuminated'
    assert pv.occlusion_class(states, point(0, 0, 0), sensor, [plate], 40, None)[0] == 'unclassified_tolerance_unset'


def test_surface_and_leaf_optics_must_be_admissible():
    with pytest.raises(StudyError):
        pv.surface_optics(dict(surface_id='w', reflectance='0.7', transmittance='0.4'))
    with pytest.raises(StudyError, match='A\\+R\\+T'):
        pv.make_job_rgg('', 10, 1, 1, leaves=[(dict(surface_id='t'), np.eye(3))], leaf_optics=(0.5, 0.1, 0.1))
    text = pv.make_job_rgg('', 10, 2, 3, rig=[dict(surface_id='w', center_x_mm=0, center_y_mm=0, center_z_mm=0, normal_x=0,
                           normal_y=0, normal_z=1, width_axis_x=1, width_axis_y=0, width_axis_z=0, width_mm=10, height_mm=10,
                           reflectance='0.2', transmittance='0')])
    assert 'rig0.setDiffuse(new Graytone(0.2))' in text and 'new LightModel(10, 2)' in text and 'setSeed(3L)' in text


# ---------------------------------------------------------------- adapter
def _fixture(**kw):
    def si(v):
        return dict(value=v, status='measured', source='synthetic')
    d = dict(fixture_id='bar', model_name='m', emitting_center_grow_mm=dict(value=(100.0, 200.0, 500.0), status='measured', source='s'),
             aim_tilt_deg=si(0.0), aim_azimuth_deg=si(0.0), long_axis_azimuth_deg=si(0.0), emitting_length_mm=si(300.0),
             emitting_width_mm=si(30.0), emitter_grid=(10, 1), photon_flux_umol_s=si(123.5), photon_band='PAR_400_700nm',
             distribution=dict(kind='cosine_power', half_intensity_half_angle_deg=si(60.0), cutoff_half_angle_deg=90.0),
             electrical_input_w=si(40.0), electrical_boundary='wall_plug_including_driver',
             schedule=[dict(start_hhmm='00:00', end_hhmm='24:00', output_fraction=1.0)])
    for k, v in kw.items():
        if k == 'cutoff':
            d['distribution']['cutoff_half_angle_deg'] = v
        elif k == 'half':
            d['distribution']['half_intensity_half_angle_deg'] = si(v)
        else:
            d[k] = si(v)
    return LedFixture.model_validate(d)


def test_adapter_preserves_photon_flux_mm_to_m_once_and_orientation():
    fx = _fixture()
    node, rec = pv.arealight_node(fx)
    assert 'setPower(123.5f)' in node  # photon flux written as is: no watt-to-photon conversion, no electrical watts
    assert '40.0' not in node
    assert rec['centre_grow_m'] == pytest.approx([0.1, 0.2, 0.5])
    assert rec['cos_exponent_m'] == pytest.approx(1.0) and rec['arealight_exponent'] == pytest.approx(0.0, abs=1e-12)
    assert 'Parallelogram(0.3f, 0.03f)' in node
    m = [float(v) for v in node.split('Matrix4d(')[1].split(')')[0].split(',')]
    rot = np.array(m).reshape(4, 4)
    assert rot[:3, 1] == pytest.approx([0, 0, -1])        # local +y (emitting side) = aim, straight down
    assert rot[:3, 3] == pytest.approx([-0.05, 0.2, 0.5])  # origin = centre - long axis * length / 2
    assert np.linalg.det(rot[:3, :3]) == pytest.approx(1.0)


def test_adapter_refuses_unrepresentable_distributions():
    assert not pv.adapter_support(_fixture(cutoff=60.0))[0]
    assert 'negative AreaLight exponent' in pv.adapter_support(_fixture(half=70.0))[1]
    assert 'zero-area' in pv.adapter_support(_fixture(emitting_width_mm=0.0))[1]


def test_directional_flux_normalisation_of_the_reference_model():
    fx = _fixture(half=45.0)
    em, _ = build_emitters(fx)
    th = np.linspace(0, math.pi / 2, 20001)
    per = em.axial_intensity_umol_s_sr * np.cos(th) ** em.cosine_exponent * 2 * math.pi * np.sin(th)
    total = float(np.sum((per[1:] + per[:-1]) / 2 * np.diff(th))) * len(em.positions_grow_mm)
    assert total == pytest.approx(123.5, rel=1e-6)


def test_full_day_schedule_is_accepted():
    assert _fixture().schedule[0].duration_hours == 24.0


# ---------------------------------------------------------------- spectra
def test_spectral_conversion_is_per_wavelength_and_band_limited():
    one = [dict(fixture_id='f', wavelength_low_nm='549.5', wavelength_high_nm='550.5', value='1', value_kind='per_nm',
                quantity='energy', unit='W')]
    want = 1 * 550e-9 / (pv.PLANCK_J_S * pv.LIGHT_M_S * pv.AVOGADRO) * 1e6
    assert pv.spectral_to_photon_umol(one) == pytest.approx(want, rel=1e-12)
    blue = [dict(one[0], wavelength_low_nm='449.5', wavelength_high_nm='450.5')]
    assert pv.spectral_to_photon_umol(blue) < pv.spectral_to_photon_umol(one)  # equal watts, fewer blue photons
    half = [dict(one[0], wavelength_low_nm='690', wavelength_high_nm='710', value='1')]
    assert pv.spectral_to_photon_umol(half) == pytest.approx(10 * 695e-9 / (pv.PLANCK_J_S * pv.LIGHT_M_S * pv.AVOGADRO) * 1e6)
    with pytest.raises(StudyError, match='straddling'):
        pv.spectral_to_photon_umol([dict(half[0], value_kind='bin_integrated')])
    with pytest.raises(StudyError, match='electrical'):
        pv.spectral_to_photon_umol([dict(one[0], quantity='electrical')])
    assert pv.spectral_to_photon_umol([dict(one[0], quantity='photon', value='2')]) == pytest.approx(2.0)


# ---------------------------------------------------------------- fit
def _calibration(tmp_path, scale=1.0, half=None, n_points=None):
    study = study_folder(tmp_path)
    scene = load_scene(tmp_path / 'scene.json')
    states = pv.python_states(scene, (20, 2), {'half_angle_deg': half} if half else None)
    pts = [p for p in rows(tmp_path / 'measurement_points.csv') if p['split_role'] == 'calibration' and p['case_id'] == 'empty']
    pts = pts[:n_points] if n_points else pts
    rd = [reading('empty', p['point_id'], 1, scale * pv.python_point_ppfd(states, p, SENSOR, 6), 'calibration') for p in pts]
    write_rows(tmp_path / 'ppfd_readings.csv', rd, pv.READING_COLUMNS)
    return study, read_json(study)


def test_fit_recovers_flux_scale_and_keeps_it_fitted(tmp_path):
    study, s = _calibration(tmp_path, scale=1.3)
    fit = pv.fit_empty_rig(tmp_path / 'ppfd_readings.csv', tmp_path / 'scene.json', s['fit'], tmp_path / 'measurement_points.csv',
                           tmp_path / 'sensors.csv', s['python'], tmp_path / 'rig_surfaces.csv')
    assert fit['status'] == 'fitted'
    assert fit['fitted_parameters']['photon_flux_scale']['value'] == pytest.approx(1.3, rel=1e-9)
    path = pv.fitted_scene(tmp_path / 'scene.json', fit, tmp_path / 'fitted.json')
    fx = load_scene(path).fixtures[0]
    assert fx.photon_flux_umol_s.status == 'fitted' and fx.aim_tilt_deg.status == 'measured'


def test_fit_recovers_half_angle_with_profile_interval(tmp_path):
    study, s = _calibration(tmp_path, scale=1.0, half=40.0)
    s['fit']['enabled_parameters'] = ['photon_flux_scale', 'half_intensity_half_angle_deg']
    fit = pv.fit_empty_rig(tmp_path / 'ppfd_readings.csv', tmp_path / 'scene.json', s['fit'], tmp_path / 'measurement_points.csv',
                           tmp_path / 'sensors.csv', s['python'], tmp_path / 'rig_surfaces.csv')
    hp = fit['fitted_parameters']['half_intensity_half_angle_deg']
    assert hp['value'] == pytest.approx(40.0) and hp['profile_interval_95'][0] <= 40 <= hp['profile_interval_95'][1]
    assert fit['status'] == 'fitted'


def test_fit_reports_insufficient_calibration_and_reflective_rig(tmp_path):
    study, s = _calibration(tmp_path / 'a', n_points=1)
    s['fit']['enabled_parameters'] = ['photon_flux_scale', 'half_intensity_half_angle_deg']
    a = tmp_path / 'a'
    fit = pv.fit_empty_rig(a / 'ppfd_readings.csv', a / 'scene.json', s['fit'], a / 'measurement_points.csv', a / 'sensors.csv',
                           s['python'], a / 'rig_surfaces.csv')
    assert fit['status'] == 'insufficient_calibration'
    b = tmp_path / 'b'
    wall = dict(rows(a / 'rig_surfaces.csv')[0], surface_id='wall', role='rig', reflectance='0.6')
    study_folder(b, rig_extra=[wall])
    shutil_rd = rows(a / 'ppfd_readings.csv'); write_rows(b / 'ppfd_readings.csv', shutil_rd, pv.READING_COLUMNS)
    fit = pv.fit_empty_rig(b / 'ppfd_readings.csv', b / 'scene.json', s['fit'], b / 'measurement_points.csv', b / 'sensors.csv',
                           s['python'], b / 'rig_surfaces.csv')
    assert fit['status'] == 'blocked_reflective_rig_not_in_fit_backend'


# ---------------------------------------------------------------- comparison
def _split(tmp_path, pts):
    split = pv.make_split_manifest(pts, None)
    write_json(tmp_path / 'split.json', split)
    return tmp_path / 'split.json'


def _preds(tmp_path, values):
    write_rows(tmp_path / 'pred.csv', [dict(case_id=c, point_id=p, predicted_ppfd_umol_m2_s=v, height_band=b)
                                       for (c, p, b), v in values.items()], ('case_id', 'point_id', 'predicted_ppfd_umol_m2_s', 'height_band'))
    return tmp_path / 'pred.csv'


def test_compare_excludes_calibration_and_weighs_points_equally(tmp_path):
    pts = [point(0, 0, 0, point_id='a', case_id='e'), point(0, 0, 0, point_id='b', case_id='e'),
           point(0, 0, 0, point_id='k', case_id='e', split_role='calibration')]
    rd = [reading('e', 'a', i, 100, 'validation') for i in range(1, 6)] + [reading('e', 'b', 1, 50, 'validation'),
          reading('e', 'k', 1, 1e6, 'calibration')]
    write_rows(tmp_path / 'r.csv', rd, pv.READING_COLUMNS)
    res = pv.compare_ppfd(_preds(tmp_path, {('e', 'a', 'low'): 110, ('e', 'b', 'low'): 40, ('e', 'k', 'low'): 0}),
                          tmp_path / 'r.csv', _split(tmp_path, pts))
    allm = res['metrics'][0]
    assert allm['n_points'] == 2 and allm['n_repeat_rows'] == 6
    assert allm['bias'] == pytest.approx(0.0) and allm['mae'] == pytest.approx(10.0)
    assert allm['nrmse'] == pytest.approx(10.0 / 75.0)
    assert res['n_calibration_rows_excluded'] == 1 and allm['acceptance'] == 'no_threshold_set'
    assert allm['ci95_rmse'].startswith('unavailable')


def test_compare_zero_ppfd_missing_and_disturbed_readings(tmp_path):
    pts = [point(0, 0, 0, point_id='z', case_id='e'), point(0, 0, 0, point_id='m', case_id='e')]
    rd = [reading('e', 'z', 1, 0, 'validation'), reading('e', 'm', 1, None, 'validation'),
          reading('e', 'm', 2, 30, 'validation', disturbed='yes')]
    write_rows(tmp_path / 'r.csv', rd, pv.READING_COLUMNS)
    res = pv.compare_ppfd(_preds(tmp_path, {('e', 'z', 'low'): 2, ('e', 'm', 'low'): 3}), tmp_path / 'r.csv', _split(tmp_path, pts))
    m = res['metrics'][0]
    assert m['n_points'] == 1 and m['mean_measured'] == 0.0 and m['nrmse'] is None  # zero is a value; NRMSE unavailable
    reasons = sorted(e['reason'] for e in res['excluded_repeats'])
    assert reasons == ['disturbed', 'reading_unavailable']


def test_compare_refuses_edited_split_and_role_mismatch(tmp_path):
    pts = [point(0, 0, 0, point_id='a', case_id='e')]
    write_rows(tmp_path / 'r.csv', [reading('e', 'a', 1, 5, 'validation')], pv.READING_COLUMNS)
    split = _split(tmp_path, pts)
    data = read_json(split); data['roles']['e:a'] = 'calibration'; write_json(split, data)
    with pytest.raises(StudyError, match='hash mismatch'):
        pv.compare_ppfd(_preds(tmp_path, {('e', 'a', 'low'): 5}), tmp_path / 'r.csv', split)
    split = _split(tmp_path, [dict(pts[0], split_role='calibration')])
    with pytest.raises(StudyError, match='split_role differs'):
        pv.compare_ppfd(_preds(tmp_path, {('e', 'a', 'low'): 5}), tmp_path / 'r.csv', split)


def test_cluster_ci_needs_declared_units_and_unavailable_prediction_stays_out(tmp_path):
    pts = [point(0, 0, 0, point_id=f'p{i}', case_id='e') for i in range(6)]
    rd = [reading('e', f'p{i}', 1, 100 + i, 'validation', session_id=f's{i % 3}') for i in range(6)]
    write_rows(tmp_path / 'r.csv', rd, pv.READING_COLUMNS)
    preds = {('e', f'p{i}', 'low'): 100 + 2 * i for i in range(5)}
    preds[('e', 'p5', 'low')] = 'unavailable'
    settings = dict(inference=dict(min_independent_units_for_ci=3, bootstrap_resamples=200, bootstrap_seed=1))
    res = pv.compare_ppfd(_preds(tmp_path, preds), tmp_path / 'r.csv', _split(tmp_path, pts), settings)
    assert res['unavailable_points'] == [dict(case_id='e', point_id='p5', reason='no absolute prediction')]
    ci = res['metrics'][0]['ci95_rmse']
    assert isinstance(ci, list) and ci[0] <= ci[1]
    settings['inference']['min_independent_units_for_ci'] = 4
    res = pv.compare_ppfd(_preds(tmp_path, preds), tmp_path / 'r.csv', _split(tmp_path, pts), settings)
    assert '3 independent units < 4' in res['metrics'][0]['ci95_rmse']


# ---------------------------------------------------------------- prepare / collect / run
def test_prepare_batches_independent_probes_blocks_display_occluder_and_gates_absolute(tmp_path):
    study = study_folder(tmp_path / 's', measured=False)
    out = pv.prepare(study, tmp_path / 's_prep')
    case = {c['case_id']: c for c in out['cases']}
    # stacked sensors (z=0 under z=100) shade each other: one job per point; floor-only occluder points batch
    assert case['empty']['batched_probes'] is False and len(case['empty']['jobs']) == 10
    assert case['occ']['batched_probes'] is True and case['occ']['jobs'] == ['probes']
    assert any('is assumed' in b for b in case['empty']['absolute_blockers'])
    text = (tmp_path / 's_prep' / 'occ' / 'probes' / 'Model.rgg').read_text(encoding='utf-8')
    assert 'RigSurface("plate:0")' in text and 'AreaLight' in text and 'PointLight' not in text
    # display-only object listed as an occluder is refused
    disp = dict(rows(tmp_path / 's' / 'rig_surfaces.csv')[0], surface_id='marker', role='display_only')
    study2 = study_folder(tmp_path / 'd', rig_extra=[disp])
    s2 = read_json(study2); s2['cases'][1]['occluder_surface_ids'] = ['marker']; write_json(study2, s2)
    out2 = pv.prepare(study2, tmp_path / 'd_prep')
    occ = next(c for c in out2['cases'] if c['case_id'] == 'occ')
    assert occ['status'] == 'blocked' and 'display' in occ['blockers'][0]
    full = (tmp_path / 'd_prep' / 'empty' / 'probe_e00' / 'Model.rgg').read_text(encoding='utf-8')
    assert 'marker' not in full


def _fake_execute(prepared: Path, execution: Path, fail_job=None, scale=1.0):
    """Stand-in for GroIMP: writes logs in the exact LEAF/PROBE format with python values (test only)."""
    jobs = read_json(prepared / 'jobs.json')
    execution.mkdir()
    runs = []
    for case in jobs['cases']:
        if case['status'] != 'prepared':
            runs.append(dict(case_id=case['case_id'], job=None, status='blocked', reason=';'.join(case['blockers'])))
            continue
        spec = read_json(prepared / case['case_id'] / 'job_specs.json')
        pyv = {r['point_id']: r['python_direct_ppfd'] for r in spec['python']}
        for js in spec['specs']:
            d = execution / case['case_id'] / js['job']
            d.mkdir(parents=True)
            if js['job'] == fail_job:
                (d / 'groimp.log').write_text('crash', encoding='utf-8')
                runs.append(dict(case_id=case['case_id'], job=js['job'], status='failed', reason='Incomplete GroIMP run',
                                 log_sha256=file_hash(d / 'groimp.log')))
                continue
            lines = []
            for pr in js['probes']:
                flux = pyv[pr['point_id']] * scale * pr['area_mm2'] / 1e6
                lines += [f'PROBE\t{pr["point_id"]}:0\t{flux / 2}', f'PROBE\t{pr["point_id"]}:1\t{flux / 2}']
            (d / 'groimp.log').write_text('\n'.join(lines + ['SANITY_DONE']), encoding='utf-8')
            runs.append(dict(case_id=case['case_id'], job=js['job'], status='completed', log_sha256=file_hash(d / 'groimp.log')))
    write_json(execution / 'execution.json', dict(prepared=str(prepared.resolve()), jobs_sha256=file_hash(prepared / 'jobs.json'),
                                                  runs=runs))


def test_collect_end_to_end_compare_and_error_propagation(tmp_path):
    study = study_folder(tmp_path / 's', measured=True)
    prepared = tmp_path / 'prep'
    pv.prepare(study, prepared)
    _fake_execute(prepared, tmp_path / 'exe')
    res = pv.collect(prepared, tmp_path / 'exe', tmp_path / 'col')
    occ = [r for r in res['predictions'] if r['case_id'] == 'occ']
    assert {r['occlusion_class'] for r in occ} == {'shadow_interior', 'illuminated'}
    assert all(r['absolute_status'] == 'available' for r in res['predictions'])
    lit = next(r for r in occ if r['point_id'] == 'o_lit')
    assert lit['predicted_ppfd_umol_m2_s'] == pytest.approx(lit['python_direct_ppfd_declared_inputs_umol_m2_s'])
    # failed job: kept visible, no number invented
    _fake_execute(prepared, tmp_path / 'exe2', fail_job='probes')
    res = pv.collect(prepared, tmp_path / 'exe2')
    failed = [r for r in res['predictions'] if r['case_id'] == 'occ']
    assert res['failures'] and failed and all(r['status'] == 'failed' and r['predicted_ppfd_umol_m2_s'] is None for r in failed)
    # changed log after execution -> refused
    log = tmp_path / 'exe' / 'occ' / 'probes' / 'groimp.log'
    log.write_text(log.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    with pytest.raises(StudyError, match='log changed'):
        pv.collect(prepared, tmp_path / 'exe')


def test_run_without_execute_preserves_inputs_and_detects_staleness(tmp_path):
    study = study_folder(tmp_path / 's', measured=False)
    before = {p.name: file_hash(p) for p in (tmp_path / 's').iterdir()}
    run_dir = tmp_path / 'run'
    manifest = pv.run(study, run_dir)
    assert {p.name: file_hash(p) for p in (tmp_path / 's').iterdir()} == before
    assert manifest['validated_metric'] is False and (run_dir / 'report.html').is_file()
    ready = read_json(run_dir / 'readiness.json')
    assert ready['canopy_comparison_ready'] is False and ready['suitable_for_ppfd'] is False
    assert rows(run_dir / 'missing_physical_inputs.csv')
    assert pv.stale(run_dir)['stale'] is False
    with pytest.raises(StudyError, match='already exists'):
        pv.run(study, run_dir)
    sensors = rows(tmp_path / 's' / 'sensors.csv'); sensors[0]['sensing_width_mm'] = '11'
    write_rows(tmp_path / 's' / 'sensors.csv', sensors, pv.SENSOR_COLUMNS)
    st = pv.stale(run_dir)
    assert st['stale'] is True and any('sensors.csv' in p for p in st['changed_sources'])


def test_plant_case_blocks_without_reviewed_surfaces_and_records_partial_geometry(tmp_path):
    study = study_folder(tmp_path / 's')
    s = read_json(study)
    s['cases'].append(dict(case_id='plant1', stage='plant', plant_id='P1', session_id='s1', geometry_snapshot_date='2026-10-01',
                           geometry='leaf_surfaces.csv', geometry_variant_id='v', surface_review='review.json'))
    write_json(study, s)
    pts = rows(tmp_path / 's' / 'measurement_points.csv') + [point(300, 130, 50, point_id='pl1', stage='plant', case_id='plant1')]
    write_rows(tmp_path / 's' / 'measurement_points.csv', pts, pv.POINT_COLUMNS)
    out = pv.prepare(study, tmp_path / 'prep')
    plant = next(c for c in out['cases'] if c['case_id'] == 'plant1')
    twin = next(c for c in out['cases'] if c['case_id'] == 'plant1__empty_twin')
    assert plant['status'] == 'blocked' and 'missing_leaf_triangle_file' in plant['blockers']
    assert twin['status'] == 'prepared'
    ready = pv.readiness({}, None, None, dict(cases=[dict(stage='plant', surface_evidence=dict(geometry_completeness='partial'))]))
    assert 'partial_plant_geometry' in ready['blocking_reasons'] and ready['validated_metric'] is False


def test_convergence_refuses_unbounded_local_sweeps(tmp_path):
    study = study_folder(tmp_path / 's')
    pv.prepare(study, tmp_path / 'prep')
    with pytest.raises(StudyError, match='exceed max_local_native_jobs'):
        pv.convergence(tmp_path / 'prep', 'empty', tmp_path / 'conv', [1000, 2000], [1, 2], 2)
    with pytest.raises(StudyError, match='must be declared'):
        pv.convergence(tmp_path / 'prep', 'empty', tmp_path / 'conv2', [1000], [1], None)


def test_sensitivity_uses_configured_deltas_only(tmp_path):
    study = study_folder(tmp_path / 's')
    s = read_json(study)
    out = pv.sensitivity(s, tmp_path / 's', tmp_path / 's' / 'scene.json')
    params = {r['parameter'] for r in out}
    assert params == {'lamp_height_mm', 'flux_rel'}
    flux = [r for r in out if r['parameter'] == 'flux_rel' and r['reference_ppfd'] > 0]
    assert all(r['relative_change'] == pytest.approx(0.05) for r in flux)
