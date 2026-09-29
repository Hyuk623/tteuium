"""Document 06 numerical contracts; synthetic geometry is not research evidence."""
from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np
import pytest

from tools import instance_evidence as ev
from tools import instance_workflow as workflow
from tools.leaf_light import common
from tools.leaf_light.reconstruction import project
from tools.tests.test_leaflet_extent import cameras, tight_box, INTRINSICS, LEAF_BOX_MM


@pytest.fixture
def settings():
    return common.read_json(workflow.DEFAULTS)


def synthetic():
    frames = cameras([420, 0, 320], [0, 420, 300])
    capture = dict(intrinsics=INTRINSICS, frames=frames, quality=dict(contour_tolerance_px=0, min_ray_angle_deg=2))
    observations, masks = [], {}
    for i, frame in enumerate(frames):
        frame['passes_pose_gate'] = False
        box = tight_box(frame)
        x, y, x1, y1 = [box[k] for k in ('x_min_px', 'y_min_px', 'x_max_px', 'y_max_px')]
        crop = [int(x)-3, int(y)-3, int(np.ceil(x1))+3, int(np.ceil(y1))+3]
        mask = np.zeros((crop[3]-crop[1], crop[2]-crop[0]), np.uint8)
        hull = cv2.convexHull(np.floor(project(LEAF_BOX_MM, frame, INTRINSICS)-crop[:2]+.5).astype(np.int32))
        cv2.fillConvexPoly(mask, hull, 1)
        obs = dict(id=str(i), source_annotation_id=i, image_file=frame['image_file'], image_size_px=[1280, 960],
                   source_bbox_xywh_px=[x, y, x1-x, y1-y], crop_px=crop,
                   review='accepted', leaf_key='L01', visibility='full', identity_review='confirmed')
        observations.append(obs); masks[str(i)] = mask.astype(bool)
    return capture, observations, masks


def test_one_to_one_missing_merge_split_and_empty(settings):
    a = np.zeros((20, 20), bool); a[2:6, 2:6] = True
    b = np.zeros_like(a); b[10:14, 10:14] = True
    r = ev.mask_metrics([a|b], [a, b], settings)
    assert (r['tp'], r['fp'], r['fn'], r['merged_instance_count']) == (1, 0, 1, 1)
    r = ev.mask_metrics([a, a], [a], settings)
    assert r['tp'] == 1 and r['fp'] == 1 and r['split_instance_count'] == 1
    r = ev.mask_metrics([np.zeros_like(a)], [a], settings)
    assert r['fn'] == 1 and r['precision'] is None and r['recall'] == 0
    assert ev.mask_metrics([], [], settings)['recall'] is None


def test_projection_crop_offsets_and_partial_unknown():
    capture, observations, masks = synthetic()
    obs, frame = observations[0], capture['frames'][0]
    points = np.array([[0, 0, 60], [80, 0, 60]], float)
    vote = ev.observation_votes(points, obs, masks[obs['id']], frame, INTRINSICS, 0)
    assert vote.tolist() == [1, -1]
    assert ev.observation_votes(points, dict(obs, visibility='partial'), masks['0'], frame, INTRINSICS, 0).tolist() == [1, 0]


def test_bounded_diagnostic_strict_gate_and_source_immutability(settings):
    capture, obs, masks = synthetic(); before = deepcopy(obs)
    strict = ev.fuse(capture, obs, masks, settings)
    assert strict['status'] == 'unavailable_no_qualified_poses' and not strict['voxels']
    result = ev.fuse(capture, obs, masks, settings, 'diagnostic')
    accepted = [v for v in result['voxels'] if v['state'] == 'supported']
    assert accepted and all(v['support_views'] == 2 for v in accepted)
    assert all((v['z_mm']/2-.5).is_integer() for v in accepted)
    assert any(v['state'] == 'excluded' for v in result['voxels'])
    assert obs == before and result['suitable_for_ppfd'] is False and result['validated_metric'] is False


def test_routes_deduplicate_and_conflicting_identity_remains_ambiguous(settings):
    capture, obs, masks = synthetic()
    a = ev.fuse(capture, obs, masks, settings, 'diagnostic')
    b = ev.fuse(capture, obs+[dict(obs[0], routes=['global', 'vertical'])], masks, settings, 'diagnostic')
    assert a == b
    second = [dict(o, id=o['id']+'x', source_annotation_id=o['source_annotation_id']+100, leaf_key='L02') for o in obs]
    masks.update({o['id']+'x': masks[o['id']] for o in obs})
    result = ev.fuse(capture, obs+second, masks, settings, 'diagnostic')
    assert all(v['ambiguous'] for v in result['voxels'] if v['state'] == 'supported')


def test_unposed_partial_single_view_and_no_silent_coarsening(settings):
    capture, obs, masks = synthetic()
    result = ev.fuse(capture, [obs[0], dict(obs[1], visibility='partial')], masks, settings, 'diagnostic')
    assert not result['voxels'] and result['extents'][0]['status'] == 'unbounded_single_view'
    capture['frames'][1]['pose_status'] = 'failed'
    result = ev.fuse(capture, obs, masks, settings, 'diagnostic')
    assert any(e['reason'] == 'missing_measured_pose' for e in result['exclusions'])
    with pytest.raises(common.StudyError, match='not coarsened'):
        list(ev.voxel_chunks([0,0,0], [100,100,100], 2, 64, 10))


def test_noisy_pose_or_merged_mask_does_not_promote_to_measurement(settings):
    capture, obs, masks = synthetic()
    capture['frames'][1]['tvec_mm'][0] += 2
    masks['0'][:] = True
    result = ev.fuse(capture, obs, masks, settings, 'diagnostic')
    assert result['validated_metric'] is False
    assert all(v['support_views'] <= 2 for v in result['voxels'])


def test_identity_join_follows_split_without_copying_mask_or_count_prior():
    item = dict(source_annotation_id=7, image_file='photo.png')
    leaf = dict(leaflet_id='lf1', organ_id='compound1', membership_review={'state':'unconfirmed'},
                bboxes={'photo.png': {'source_detection': {'source_annotation_id':7}}},
                view_status={'photo.png': {'identity_review':'confirmed', 'visibility':'full'}})
    backup = {'variants': {'__all__': {'leaflets': {'old': leaf}}}}
    assert workflow.identity_for(item, backup)['compound_leaf_id'] is None
    backup['variants']['__all__']['leaflets']['new'] = backup['variants']['__all__']['leaflets'].pop('old')
    assert workflow.identity_for(item, backup)['leaf_key'] == 'new'
    del leaf['bboxes']['photo.png']
    assert workflow.identity_for(item, backup)['leaf_key'] is None


def test_reference_requires_independent_review_and_fixture_exclusion():
    with pytest.raises(common.StudyError, match='independent'):
        workflow.validate_reference({'schema_version': 'instance-visible-reference-1'}, {'plant_id':'dwt_01','session_id':'S'})
    with pytest.raises(common.StudyError, match='fixtures'):
        workflow.check_research_path(Path('build/sensitivity_web_fixture_20260922'))
    assert workflow.backup_digest({'variants': {}, 'saved_at': 'a'}) == workflow.backup_digest({'variants': {}, 'saved_at': 'b'})
