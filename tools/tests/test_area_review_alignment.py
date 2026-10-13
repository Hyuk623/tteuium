"""Explicitly synthetic S8 and export boundary regressions; no physical validation."""
from copy import deepcopy
import subprocess
import sys

import numpy as np
import pytest

from tools import plant_traits as pt
from tools.plant_pipeline import Plant
from tools.leaf_light.common import digest, read_json, rows, write_json
from tools.tests.test_leaf_area_geometry import POLICY, K, D, hull


def synthetic_s8(tmp_path, monkeypatch, *, unknown=False, grouping=True, policy=True):
    session = tmp_path/'capture'/'edit_session'; session.mkdir(parents=True)
    structure = tmp_path/'structure'; structure.mkdir()
    batch = tmp_path/'batch'; batch.mkdir(); write_json(batch/'manifest.json', {'fixture_only': True})
    frames = [dict(image_file='top.png', view_code='20', pose_status='solved', rvec_rad=[0.,0.,0.],
                   tvec_mm=[0.,0.,0.]),
              dict(image_file='ring.png', view_code='00', pose_status='solved', rvec_rad=[0.,0.,0.],
                   tvec_mm=[100.,0.,0.])]
    if unknown:
        frames.append(dict(image_file='unknown.png', view_code='21', pose_status='failed'))
    capture = dict(data_kind='synthetic', session_id='synthetic_s8', intrinsics=dict(camera_matrix=K.tolist(),
        dist_coeffs=D.tolist(), image_width_px=200, image_height_px=200), frames=frames)
    write_json(session/'capture.json', capture)
    write_json(structure/'structure.json', dict(hull=dict(voxel_mm=1, occupancy_cm3=.4, dilation_px=30),
                                               views_used=['top.png','ring.png']))
    np.savetxt(structure/'hull_voxels.csv', hull(), delimiter=',', header='x,y,z', comments='')
    masks = {'top.png': [((90,92,110,108), np.ones((16,20),bool), True)],
             'ring.png': [((145,96,155,104), np.ones((8,10),bool), True)]}
    monkeypatch.setattr(pt, 'batch_masks', lambda _: masks)
    cfg = dict(capture=str(session.parent), labels=str(tmp_path/'labels'), batch=str(batch))
    if policy:
        cfg.update(area_policy=POLICY, capture_style='synthetic_test_only')
    if grouping:
        cfg['view_grouping'] = dict(centre_board_mm=[0.,0.,-300.], top_elevation_gt_deg=80., source='synthetic_fixture')
    plant = Plant('synthetic_p', cfg, {}, tmp_path/'out')
    plant.structure = structure
    plant.s8()
    return plant, read_json(plant.out/'traits.json')


def test_actual_s8_forwards_policies_and_separates_grouping_integration(tmp_path, monkeypatch):
    plant, result = synthetic_s8(tmp_path, monkeypatch)
    a = result['aggregation_audit']
    assert result['schema'] == 'plant-traits-2'
    assert result['leaf_area_proxy_cm2'] == pytest.approx(4.)
    assert result['top_leaf_area_cm2'] == pytest.approx(16.)
    assert result['legacy_leaf_area_proxy_cm2'] == pytest.approx(12.8)
    assert result['legacy_top_leaf_area_cm2'] == pytest.approx(3.2)
    assert a['legacy_measured']['groups']['ring']['mean_cm2'] == pytest.approx(3.2)
    assert a['footprint_code']['groups']['ring']['mean_cm2'] == pytest.approx(16.)
    assert a['footprint_measured']['groups']['ring']['images'] == ['ring.png']
    assert result['top_photos'] == 1
    assert result['top_to_ring_diagnostic']['value'] == pytest.approx(4.)
    assert result['top_to_ring_diagnostic']['mean_inclination_deg'] is None
    assert result['area_provenance']['data_kind'] == 'synthetic'
    assert not result['validated_metric']


def test_unknown_pose_is_not_silently_claimed_complete(tmp_path, monkeypatch):
    _, result = synthetic_s8(tmp_path, monkeypatch, unknown=True)
    assert result['aggregation_status'] == 'incomplete'
    assert result['aggregation_audit']['footprint_measured']['unknown_group_images'] == ['unknown.png']
    assert result['leaf_area_proxy_cm2'] == pytest.approx(4.)  # partial-group diagnostic retained
    assert result['top_to_ring_diagnostic']['value'] is None
    assert len(result['area_provenance']['frames']) == 3
    assert result['area_provenance']['true_area_interval_cm2'] is None


def test_grouping_only_does_not_silently_switch_integrator(tmp_path, monkeypatch):
    _, result = synthetic_s8(tmp_path, monkeypatch, policy=False)
    assert result['schema'] == 'plant-traits-1'
    assert result['leaf_area_proxy_cm2'] == pytest.approx(12.8)
    assert result['area_provenance']['measured_grouping_status'] == 'not_enabled_without_area_policy'


def test_excluded_frame_retains_legacy_diagnostic_but_not_v2_mean(tmp_path, monkeypatch):
    plant, _ = synthetic_s8(tmp_path, monkeypatch)
    st = read_json(plant.structure/'structure.json')
    st['views_skipped'] = [dict(photo='ring.png', reason='synthetic exclusion')]
    write_json(plant.structure/'structure.json', st)
    plant.s8()
    result = read_json(plant.out/'traits.json')
    assert result['leaf_area_proxy_cm2'] is None
    assert result['legacy_top_leaf_area_cm2'] == pytest.approx(3.2)
    assert result['aggregation_status'] == 'incomplete'
    assert result['aggregation_audit']['legacy_measured']['groups']['ring']['mean_cm2'] is None


def test_cli_summary_retains_hash_bound_provenance_without_physical_basis(tmp_path, monkeypatch):
    plant, result = synthetic_s8(tmp_path, monkeypatch)
    source = deepcopy(result)
    out = tmp_path/'summary'
    subprocess.run([sys.executable, '-X', 'utf8', '-m', 'tools.plant_traits', '--traits',
        str(plant.out/'traits.json'), '--out', str(out), '--measurements', str(tmp_path/'absent')],
        check=True, capture_output=True, text=True)
    exported = rows(out/'traits.csv')[0]
    evidence = read_json(out/exported['area_provenance_file'])['records'][exported['area_provenance_id']]
    assert digest(evidence) == exported['area_provenance_id']
    assert evidence['trait_digest'] == digest(source)
    assert evidence['area_provenance'] == source['area_provenance']
    assert evidence['area_basis_id'] is None and evidence['true_area_interval_cm2'] is None
    assert read_json(plant.out/'traits.json') == source


def test_legacy_summary_marks_missing_provenance_without_changing_numbers(tmp_path):
    out = pt.summarize([dict(plant_id='synthetic_p', leaf_area_proxy_cm2=12.8)], tmp_path/'out', tmp_path/'absent')
    assert out['rows'][0]['leaf_area_proxy_cm2'] == 12.8
    e = read_json(tmp_path/'out'/'traits_area_provenance.json')['records'].values()
    assert next(iter(e))['area_provenance_status'] == 'legacy_provenance_unavailable'


def test_null_grouping_threshold_keeps_all_views_explicitly_unknown(tmp_path, monkeypatch):
    plant, _ = synthetic_s8(tmp_path, monkeypatch)
    plant.cfg['view_grouping']['top_elevation_gt_deg'] = None
    plant.s8()
    result = read_json(plant.out/'traits.json')
    assert result['aggregation_status'] == 'incomplete'
    assert result['leaf_area_proxy_cm2'] is None and result['top_leaf_area_cm2'] is None
    assert len(result['aggregation_audit']['footprint_measured']['unknown_group_images']) == 2


def test_top_photo_count_follows_measured_group_and_preserves_legacy_count(tmp_path, monkeypatch):
    plant, _ = synthetic_s8(tmp_path, monkeypatch)
    plant.cfg['view_grouping']['top_elevation_gt_deg'] = 60.
    plant.s8()
    result = read_json(plant.out/'traits.json')
    assert result['top_photos'] == 2 and result['legacy_top_photos'] == 1
    assert result['leaf_area_proxy_cm2'] is None
    assert result['top_to_ring_diagnostic']['value'] is None


def test_area_angles_without_located_vertices_cannot_export_optical_geometry(tmp_path):
    from tools.tests.test_p1_area_evidence import fixture, audit
    data = fixture(tmp_path)
    data[0][0].update(area_cm2=.5, normal_zenith_deg=0., normal_azimuth_deg=0.)
    for vertex in range(3):
        for axis in 'xyz':
            data[0][0][f'v{vertex}_{axis}_mm'] = None
    data[3]['geometry_digest'] = digest(data[0])
    with pytest.raises(pt.StudyError, match='unavailable'):
        audit(tmp_path, data)


def test_normal_winding_does_not_create_botanical_face_evidence(tmp_path):
    from tools.tests.test_p1_area_evidence import fixture, audit, claim
    data = fixture(tmp_path)
    first = audit(tmp_path, data)
    row = data[0][0]
    for axis in 'xyz':
        a, b = f'v1_{axis}_mm', f'v2_{axis}_mm'
        row[a], row[b] = row[b], row[a]
    row['normal_convention'] = 'stem_away'
    data[3]['geometry_digest'] = digest(data[0])
    second = audit(tmp_path, data)
    assert claim(first)['downstream_supported_area_cm2'] == claim(second)['downstream_supported_area_cm2']
    assert second['area_evidence']['biological_face_status'] == 'unavailable'
    assert second['area_evidence']['illuminated_faces'] is None
