"""r03 lessons must change observed calculations without importing generated tissue."""
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from tools import detected_leaf_area as da, plant_structure as ps, plant_traits as pt
from tools.leaf_light import common
from tools.tests.test_detected_leaf_area import batch
from tools.tests.test_leaf_area_compare import setup


def selection(root: Path, target: str, out: Path) -> Path:
    item = common.read_json(root/'items'/f'{target}.json')
    evidence = out/'review.json'
    common.write_json(evidence, {'decision': 'non-leaf object'})
    path = out/'selection.json'
    common.write_json(path, dict(schema='observed-leaf-selection-1', plant_id='p', session_id='s',
        origin='observed_annotation_review', evidence=dict(path=str(evidence), sha256=common.file_hash(evidence)),
        excluded_items=[dict(item_id=target, item_sha256=common.file_hash(root/'items'/f'{target}.json'),
                             image_file=item['image_file'], image_sha256=item['image_sha256'], reason='reviewed non-leaf object')]))
    return path


def test_excluded_first_reference_is_not_replaced(batch, tmp_path):
    policy = selection(batch, 'leaf_10', tmp_path)
    before = {p: common.file_hash(p) for p in batch.rglob('*') if p.is_file()}
    report = da.run(batch, tmp_path/'out', selection_path=policy)
    assert all(r['relative_area'] is None for r in report['rows'][:3])
    assert report['rows'][0]['observation_status'] == 'excluded_by_observation_review'
    assert report['rows'][1]['reference_label_id'] == 'leaf_10'
    assert report['rows'][-1]['relative_area'] == 1
    assert all(common.file_hash(p) == h for p, h in before.items())


def test_exclusion_keeps_other_leaf_measurements_and_original_coordinates(batch, tmp_path):
    policy = selection(batch, 'leaf_2', tmp_path)
    rows = da.run(batch, tmp_path/'out', selection_path=policy)['rows']
    assert [r['area_px2'] for r in rows] == [4, None, 2, 9]
    assert [r['relative_area'] for r in rows] == [1, None, .5, 1]
    with pytest.raises(common.StudyError, match='original-resolution'):
        da.pixel_area(dict(image_size_px=[4000,3000]), 'mask', np.ones((256,256), bool), [10,10,850,850])


@pytest.mark.parametrize('field,value', [('session_id','foreign'),('origin','generative'),('item_hash','0'*64),('image_file','foreign.png')])
def test_selection_rejects_stale_foreign_or_generated_decisions(batch, tmp_path, field, value):
    path = selection(batch, 'leaf_2', tmp_path)
    policy = common.read_json(path)
    if field in ('session_id','origin'):
        policy[field] = value
    else:
        policy['excluded_items'][0]['item_sha256' if field == 'item_hash' else field] = value
    common.write_json(path, policy)
    with pytest.raises(common.StudyError):
        da.run(batch, tmp_path/'out', selection_path=path)


def test_projected_area_exclusion_does_not_count_stem_or_keep_old_calibration(tmp_path, monkeypatch):
    from tools import leaf_area_compare as ac
    study, case = setup(tmp_path, monkeypatch)
    root = Path(case['batch'])
    item = common.read_json(root/'items/i.json')
    image = Path(case['capture']).parent/'frame.png'
    item.update(image_sha256=common.file_hash(image), image_path='frame.png')
    common.write_json(root/'items/i.json', item)
    policy = selection(root, 'i', tmp_path)
    doc = common.read_json(study)
    doc['cases'][0]['mask_selection'] = str(policy)
    common.write_json(study, doc)
    result = ac.run(study, tmp_path/'out')['cases'][0]
    assert result['photos'][0]['status'] == 'no_masks'
    assert result['mask_selection']['excluded'] == {'i':'reviewed non-leaf object'}
    assert result['total_tissue_area_cm2'] is None
    base = dict(area_method='undistorted_pixel_footprint_v2', calibration_hash='c',
                capture_style='s', grouping_policy_hash='g', integration_policy_hash='i')
    assert pt.area_calibration_contract(base) != pt.area_calibration_contract(dict(base, mask_selection_hash=result['mask_selection_hash']))


class CameraFixture:
    def posed(self, key): return True
    def centre(self, key): return np.array([0.,0.,100.]) if key.endswith('27.png') else np.array([100.,0.,0.])
    def project(self, key, points): return np.tile([5.,5.], (len(points),1))


def test_3d_regions_use_measured_ring_even_when_image_codes_disagree():
    cams = CameraFixture()
    views = ['plant_03.png','plant_27.png']
    dets = {v:[dict(class_name='compoundleaves',bbox=[0,0,10,10])] for v in views}
    for ds in dets.values(): ds[0]['bbox'] = dict(x_min_px=0,y_min_px=0,x_max_px=10,y_max_px=10)
    grouping = dict(centre_board_mm=[0,0,0], top_elevation_gt_deg=70, source='reviewed fixture')
    label, info, meta = ps.compound_regions(cams, views, dets, np.array([[0.,0.,1.],[1.,0.,1.]]), grouping)
    assert meta['reference_view'] == 'plant_03.png'
    assert meta['view_geometry']['plant_27.png']['group'] == 'top'
    assert meta['view_geometry']['plant_03.png']['group'] == 'ring'
    assert len(info) == 1 and np.all(label == 0)
    label, info, meta = ps.compound_regions(cams, views, dets, np.ones((2,3)))
    assert not info and np.all(label == -1)
    assert meta['status'] == 'unavailable_no_measured_ring_reference'


def test_plant_viewer_does_not_label_photo_03_as_top_from_filename():
    from tools.plant_site import camera
    frame = dict(view_code='03', pose_status='failed')
    assert camera(frame, Counter())['group'] == 'unavailable'
    assert camera(frame, Counter(), dict(group='ring'))['group'] == 'ring'


def test_cached_xyz_slice_projects_without_changing_coordinates():
    from tools.tests.test_plant_pipeline_tools import synthetic_cams
    cams = synthetic_cams()
    table = np.array([[0.,0.,50.,1.],[2.,1.,55.,2.]])
    before = table.copy()
    sliced = table[:,:3]
    assert not sliced.flags.c_contiguous
    key = next(iter(cams.frames))
    assert np.array_equal(cams.project(key,sliced), cams.project(key,sliced.copy()))
    assert np.array_equal(table,before)


def test_human_identity_cannot_follow_reused_region_numbers():
    names = {'0':dict(name='leaf_1',median_z_mm=50)}
    assert ps.reviewed_region_names(names,'new')[0] is None
    assert ps.reviewed_region_names(dict(region_assignment_hash='old',regions=names),'new')[0] is None
    assert ps.reviewed_region_names(dict(region_assignment_hash='new',regions=names),'new')[0] == names


def test_region_assignment_digest_accepts_numpy_values_from_real_runs():
    info = [dict(region=np.int64(1), voxels=np.int64(5), median_z_mm=np.float64(75.5),
                 centroid_mm=np.array([1.0, 2.0, 3.0]), boxes=[dict(view='a.png', box_index=np.int32(0))])]
    plain = [dict(region=1, voxels=5, median_z_mm=75.5, centroid_mm=[1.0, 2.0, 3.0], boxes=[dict(view='a.png', box_index=0)])]
    points, labels = np.array([[0., 0., 1.]]), np.array([1])
    grouping = dict(centre_board_mm=[0, 0, 0], top_elevation_gt_deg=70.0, source='test')
    assert ps.region_assignment_digest(grouping, points, labels, info) == ps.region_assignment_digest(grouping, points, labels, plain)
    assert ps.region_assignment_digest(grouping, points, labels, plain) == common.digest(
        dict(grouping=grouping, points_mm=[[0., 0., 1.]], labels=[1], regions=plain))
