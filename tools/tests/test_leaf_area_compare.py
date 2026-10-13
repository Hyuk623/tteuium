"""Saved-mask CLI integration and immutable source checks; no model execution."""
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools import leaf_area_compare as ac
from tools import plant_traits as pt
from tools.leaf_light import common
from tools.tests.test_leaf_area_geometry import POLICY, K, hull


def setup(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    session=tmp_path/'capture'; session.mkdir()
    image=session/'frame.png'; Image.new('RGB',(200,200),(230,240,230)).save(image)
    image_hash=common.file_hash(image)
    capture=dict(plant_id='p',session_id='s',coordinate_frame='board',
        intrinsics=dict(camera_matrix=K.tolist(),dist_coeffs=[0.]*5,image_width_px=200,image_height_px=200),
        frames=[dict(image_file='frame.png',image_path='frame.png',sha256=image_hash,view_code='01',pose_status='solved',
                     rvec_rad=[0.,0.,0.],tvec_mm=[0.,0.,0.],passes_pose_gate=False)])
    common.write_json(session/'capture.json',capture)
    structure=tmp_path/'structure';structure.mkdir()
    common.write_json(structure/'structure.json',dict(plant_id='p',session_id='s',views_used=['frame.png'],
        inputs=dict(capture=str(session/'capture.json'),capture_sha256=common.file_hash(session/'capture.json'))))
    np.savetxt(structure/'hull_voxels.csv',hull(),delimiter=',',header='x,y,z',comments='')
    batch=tmp_path/'batch';(batch/'items').mkdir(parents=True); cache=batch/'cache/key';cache.mkdir(parents=True)
    np.savez_compressed(cache/'logits.npz',logits=np.ones((1,16,20))*10)
    common.write_json(cache/'result.json',dict(scores=[1.],crop_px=[90,92,110,108],image_sha256=image_hash,logits_sha256=common.file_hash(cache/'logits.npz')))
    common.write_json(batch/'items/i.json',dict(id='i',image_file='frame.png',generation='ready',review='accepted',revision=0,
        cache_key='key',selected_candidate=0,sensitivity=20,manual_rings=None,manual_raster=None))
    common.write_json(batch/'manifest.json',dict(schema_version='leaflet-mask-batch-1',plant_id='p',session=str(session),organ_class='leaflet',ids=['i']))
    case=dict(case_id='p',plant_id='p',session_id='s',capture=str(session/'capture.json'),structure=str(structure/'structure.json'),batch=str(batch),
              capture_style='fixture',view_grouping=dict(centre_board_mm=[0.,0.,200.],top_elevation_gt_deg=70.,source='fixture'))
    study=tmp_path/'study.json';common.write_json(study,dict(schema='leaf-area-comparison-1',integration=POLICY,preview_max_px=100,measurements='missing_measurements',cases=[case]))
    return study,case


def test_saved_mask_end_to_end_preserves_sources_and_reports_versions(tmp_path,monkeypatch):
    study,case=setup(tmp_path,monkeypatch)
    before={str(p):common.file_hash(p) for p in tmp_path.rglob('*') if p.is_file()}
    result=ac.run(study,tmp_path/'out')
    photo=result['cases'][0]['photos'][0]
    assert photo['legacy_projected_area_cm2']==12.8
    assert photo['projected_area_cm2']==pytest.approx(16.)
    assert photo['group']=='ring'  # Filename code is top; geometry is ring.
    assert result['source_hashes_verified'] and not result['physical_validation']
    assert (tmp_path/'out/viewer.html').exists()
    assert all(common.file_hash(Path(p))==h for p,h in before.items())
    with pytest.raises(common.StudyError,match='already exists'):
        ac.run(study,tmp_path/'out')


def test_reject_foreign_source_and_changed_logits(tmp_path,monkeypatch):
    study,case=setup(tmp_path,monkeypatch)
    path=Path(case['batch'])/'cache/key/logits.npz';path.write_bytes(b'changed')
    with pytest.raises(common.StudyError,match='hash mismatch'): ac.run(study,tmp_path/'out')


def test_hash_guard_detects_concurrent_edit(tmp_path):
    path=tmp_path/'x';path.write_text('before');guard=ac.Inputs();guard.add(path);path.write_text('after')
    with pytest.raises(common.StudyError,match='changed'):guard.verify()


def test_foreign_session_is_rejected(tmp_path,monkeypatch):
    study,case=setup(tmp_path,monkeypatch)
    data=common.read_json(study);data['cases'][0]['session_id']='other';common.write_json(study,data)
    with pytest.raises(common.StudyError,match='plant/session'):ac.run(study,tmp_path/'out')


def test_structure_exclusion_is_retained_not_recomputed_as_valid(tmp_path,monkeypatch):
    study,case=setup(tmp_path,monkeypatch)
    path=Path(case['structure']); data=common.read_json(path)
    data['views_skipped']=[dict(photo='frame.png',reason='incompatible movement')];common.write_json(path,data)
    result=ac.run(study,tmp_path/'out')
    photo=result['cases'][0]['photos'][0]
    assert photo['status']=='excluded_by_structure' and 'projected_area_cm2' not in photo
    assert photo['hull_exclusion_reason']=='incompatible movement'


def test_old_hull_cannot_use_new_camera_poses(tmp_path,monkeypatch):
    study,case=setup(tmp_path,monkeypatch)
    path=Path(case['capture']); data=common.read_json(path);data['frames'][0]['tvec_mm'][0]=1.;common.write_json(path,data)
    with pytest.raises(common.StudyError,match='hash mismatch'):ac.run(study,tmp_path/'out')


def test_corrected_proxy_refits_from_real_reference_rows_not_legacy_k(tmp_path,monkeypatch):
    study,case=setup(tmp_path,monkeypatch)
    m=tmp_path/'missing_measurements';m.mkdir()
    common.write_rows(m/'leaf_area.csv',[dict(plant_id='p',leaf_area_cm2=32,method='fixture',date='')],pt.LEAF_AREA_FIELDS)
    result=ac.run(study,tmp_path/'out')
    assert result['cases'][0]['calibrated_whole_plant_area_cm2']==32
    cal=result['calibration_summaries'][0]['calibration']
    assert cal['k']==2 and cal['area_contract']['area_method']=='undistorted_pixel_footprint_v2'
    assert not result['calibration_summaries'][0]['validated_metric']


@pytest.mark.parametrize('missing', ['no_masks', 'pose_unavailable', 'excluded_by_structure'])
def test_opt_in_plant_summary_retains_unavailable_photos(tmp_path, monkeypatch, missing):
    _, case = setup(tmp_path, monkeypatch)
    path = Path(case['capture']); capture = common.read_json(path)
    frame = dict(capture['frames'][0], image_file='second.png')
    if missing == 'pose_unavailable':
        frame['pose_status'] = 'failed'
    capture['frames'].append(frame); common.write_json(path, capture)
    sp = Path(case['structure']); structure = common.read_json(sp)
    structure['hull'] = dict(voxel_mm=1., occupancy_cm3=1.)
    if missing == 'excluded_by_structure':
        structure['views_skipped'] = [dict(photo='second.png', reason='motion')]
    common.write_json(sp, structure)
    mask = ([90,92,110,108], np.ones((16,20),bool), True)
    monkeypatch.setattr(pt, 'batch_masks', lambda _: {'frame.png':[mask], **({'second.png':[mask]} if missing != 'no_masks' else {})})
    result = pt.plant_traits('p',path.parent,sp.parent,Path(case['batch']),
                             area_policy=POLICY,capture_style='fixture')
    assert len(result['photos']) == 2
    assert result['photos'][1]['area_v2']['status'] == missing
    assert result['top_leaf_area_cm2'] is None


def test_opt_in_empty_hull_does_not_crash_legacy_comparison():
    from tools.tests.test_leaf_area_geometry import camera
    mask = ([90,92,110,108], np.ones((16,20),bool), True)
    result = pt.photo_area(camera(), 'a', np.empty((0,3)), [mask], area_policy=POLICY)
    assert result['area_v2']['status'] == 'unavailable'
    assert result['leaf_area_cm2'] is None
