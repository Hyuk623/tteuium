"""Leaflet bboxes feed a separate diagnostic extent; points stay independent and intact."""
from copy import deepcopy
import json

import numpy as np
import pytest

from tools import editor_point_review as review_tool
from tools import rebuild_leaf_edit_session as tool
from tools.leaf_light import common
from tools.leaf_light.reconstruction import project
from tools.leaflet_extent import ExtentStatus
from tools.tests.test_manual_leaf_preview_fragments import fragment_case  # noqa: F401  (fixture)
from tools.tests.test_rebuild_leaf_edit_session import prepared  # noqa: F401  (fixture)

KEY = 'O3D|L3D'
TRIANGLE_MM = np.array([[-15., 0., 100.], [15., 0., 100.], [0., 15., 100.]])


def box_around(frame, intrinsics, margin_px=30., points=TRIANGLE_MM):
    uv = project(points, frame, intrinsics) + 0.5
    return dict(annotation_id='leafbox_' + frame['image_file'].split('.')[0],
                x_min_px=float(uv[:, 0].min() - margin_px), y_min_px=float(uv[:, 1].min() - margin_px),
                x_max_px=float(uv[:, 0].max() + margin_px), y_max_px=float(uv[:, 1].max() + margin_px),
                image_width_px=intrinsics['image_width_px'], image_height_px=intrinsics['image_height_px'])


def add_boxes(backup, capture, statuses):
    leaf = backup['variants']['__all__']['leaflets'][KEY]
    frames = {f['image_file'].lower(): f for f in capture['frames']}
    for key, (visibility, review) in statuses.items():
        frame = frames[key]
        if frame.get('rvec_rad') is not None:
            box = box_around(frame, capture['intrinsics'])
        else:
            box = dict(annotation_id='leafbox_unposed', x_min_px=10., y_min_px=10., x_max_px=200., y_max_px=150.,
                       image_width_px=1600, image_height_px=1200)
        leaf.setdefault('bboxes', {})[key] = box
        leaf.setdefault('view_status', {})[key] = dict(visibility=visibility, identity_review=review)
    return leaf


def analyse(session, backup, context_path):
    """Convert/depth/extent path of rebuild without writing outputs."""
    common.write_json(session.parent / 'analysis.backup.json', backup)
    capture, seed, backup, context = tool.checked_inputs(session, session.parent / 'analysis.backup.json', context_path)
    _, rows, report = tool.convert(backup, seed, context, capture)
    depths = tool.point_depths(rows, capture)
    boxes = tool.leaflet_bbox_rows(backup, capture, report['identity_mapping'])
    extents = tool.leaflet_extents(boxes, depths, capture, report['leaf_status'])
    tool.relate_points(depths, boxes, extents)
    return depths, boxes, {e['editor_identity']: e for e in extents}


def test_full_confirmed_boxes_give_a_cuboid_linked_to_points_photos_and_calibration(prepared):
    session, path, context, out, _, backup, capture = prepared
    add_boxes(backup, capture, {'photo_0.png': ('full', 'confirmed'), 'photo_1.png': ('full', 'confirmed'),
                                'photo_2.png': ('full', 'confirmed')})
    backup['variants']['__all__']['leaflets'][KEY]['point_semantic_names'] = {'b0': 'distal_tip'}
    common.write_json(path, backup)
    hashes = [common.file_hash(p) for p in (path, context, session / 'seed.backup.json')]
    report = tool.rebuild(session, path, context, out)
    assert report['cuboids_available'] == 1 and report['leaflet_bbox_used_for_extent'] == 2
    assert report['input_files_changed'] is False and report['validated_metric'] is False
    assert report['calibration']['accepted_pose_count'] == 0
    extent = next(r for r in common.rows(out / 'leaflet_extents.csv') if r['editor_identity'] == KEY)
    assert extent['cuboid_status'] == ExtentStatus.OK and extent['geometry_status'] == 'partial_surface_available'
    assert extent['points_outside_feasible_region'] == 'none' and extent['validated_metric'] == 'False'
    lows = np.array([float(extent[f'cuboid_min_{a}_mm']) for a in 'xyz'])
    highs = np.array([float(extent[f'cuboid_max_{a}_mm']) for a in 'xyz'])
    assert np.all(TRIANGLE_MM >= lows - 1e-3) and np.all(TRIANGLE_MM <= highs + 1e-3)
    boxes = {r['image_file']: r for r in common.rows(out / 'leaflet_bbox_observations.csv')}
    assert boxes['photo_2.png']['used_for_extent'] == 'False'
    assert boxes['photo_2.png']['exclusion_reason'] == 'camera_pose_unavailable'
    assert boxes['photo_0.png']['coordinate_convention'] == 'original_pixel_edges'
    depths = [r for r in common.rows(out / 'editor_point_depths.csv') if r['organ_id'] == 'O3D']
    assert {r['inside_feasible_region'] for r in depths} == {'True'}
    assert {r['estimate_kind'] for r in depths} == {'triangulated_estimate'}
    b0 = next(r for r in depths if r['point_id'] == 'b0')
    assert b0['point_semantic_name'] == 'distal_tip' and b0['plant_id'] == 'P' and b0['variant_id'] == '__all__'
    assert float(b0['x_cuboid_local_mm']) == pytest.approx(float(b0['x_board_mm']) - lows[0], abs=1e-6)
    assert b0['all_contributing_views_identity_confirmed'] == 'True'
    meta = common.read_json(out / 'leaflet_extents.json')
    assert meta['method']['forbidden_inputs'].startswith('no near/far distance')
    assert meta['calibration']['intrinsics_sha256'] == capture['intrinsics_sha256']
    assert set(meta['calibration']['photo_sha256']) == {f['image_file'] for f in capture['frames']}
    html = (out / 'labels/index.html').read_text(encoding='utf-8')
    assert '이 사진의 소엽 박스' in html and '"cuboid_status": "bounded_feasible_region"' in html
    assert [common.file_hash(p) for p in (path, context, session / 'seed.backup.json')] == hashes


def test_partial_unknown_unconfirmed_and_unposed_boxes_never_constrain_the_leaflet(prepared):
    session, _, context, _, _, backup, capture = prepared
    cases = [({'photo_0.png': ('full', 'confirmed'), 'photo_1.png': ('partial', 'confirmed')}, ExtentStatus.SINGLE),
             ({'photo_0.png': ('full', 'confirmed'), 'photo_1.png': ('unknown', 'confirmed')}, ExtentStatus.SINGLE),
             ({'photo_0.png': ('full', 'unconfirmed'), 'photo_1.png': ('full', 'confirmed')}, ExtentStatus.SINGLE),
             ({'photo_0.png': ('full', 'unconfirmed'), 'photo_1.png': ('full', 'unconfirmed')}, ExtentStatus.NONE),
             ({'photo_0.png': ('full', 'confirmed'), 'photo_2.png': ('full', 'confirmed')}, ExtentStatus.SINGLE)]
    for statuses, expected in cases:
        trial = deepcopy(backup)
        add_boxes(trial, capture, statuses)
        depths, boxes, extents = analyse(session, trial, context)
        assert extents[KEY]['cuboid_status'] == expected, statuses
        assert extents[KEY]['cuboid_min_mm'] is None
        reasons = ';'.join(r['exclusion_reason'] or '' for r in boxes)
        assert all(r['used_for_extent'] == (r['exclusion_reason'] is None) for r in boxes)
        assert ('partial' in reasons) == any(v == 'partial' for v, _ in statuses.values())
        # Points still carry their own depth: bbox eligibility never deletes them.
        assert all(r['z_board_mm'] is not None for r in depths if r['organ_id'] == 'O3D')
        assert {r['all_contributing_views_identity_confirmed'] for r in depths if r['organ_id'] == 'O3D'} == {
            all(review == 'confirmed' for key, (_, review) in statuses.items() if key != 'photo_2.png')
            and set(statuses) >= {'photo_0.png', 'photo_1.png'}}


def test_points_outside_the_box_region_are_reported_and_kept_unchanged(prepared):
    session, _, context, _, _, backup, capture = prepared
    baseline, _, _ = analyse(session, deepcopy(backup), context)
    leaf = add_boxes(backup, capture, {'photo_0.png': ('full', 'confirmed'), 'photo_1.png': ('full', 'confirmed')})
    frame = next(f for f in capture['frames'] if f['image_file'].lower() == 'photo_1.png')
    # Tighten the photo_1 box around b1/b2 only, so b0 falls outside it.
    leaf['bboxes']['photo_1.png'] = box_around(frame, capture['intrinsics'], margin_px=3., points=TRIANGLE_MM[1:])
    depths, boxes, extents = analyse(session, backup, context)
    extent = extents[KEY]
    assert extent['cuboid_status'] == ExtentStatus.OK
    assert extent['points_outside_feasible_region'] == ['b0']
    b0 = [r for r in depths if r['organ_id'] == 'O3D' and r['point_id'] == 'b0']
    assert {r['inside_feasible_region'] for r in b0} == {False}
    assert all(r['feasible_region_violation_mm'] > 0 for r in b0)
    assert {r['observation_inside_leaflet_bbox'] for r in b0 if r['image_file'] == 'photo_1.png'} == {False}
    before = {(r['point_id'], r['image_file']): (r['x_board_mm'], r['y_board_mm'], r['z_board_mm'], r['x_px'], r['y_px'])
              for r in baseline if r['organ_id'] == 'O3D'}
    after = {(r['point_id'], r['image_file']): (r['x_board_mm'], r['y_board_mm'], r['z_board_mm'], r['x_px'], r['y_px'])
             for r in depths if r['organ_id'] == 'O3D'}
    assert before == after


def test_edits_removal_and_split_recalculate_depth_without_stale_xyz(prepared):
    session, _, context, _, _, backup, capture = prepared
    original, _, _ = analyse(session, deepcopy(backup), context)
    xyz = lambda rows, pid: next((r['x_board_mm'], r['y_board_mm'], r['z_board_mm']) for r in rows
                                 if r['organ_id'] == 'O3D' and r['point_id'] == pid)
    edited = deepcopy(backup)
    edited['variants']['__all__']['leaflets'][KEY]['pts']['b0']['photo_1.png'][0] += 12.
    moved, _, _ = analyse(session, edited, context)
    assert xyz(moved, 'b0') != xyz(original, 'b0') and xyz(moved, 'b1') == xyz(original, 'b1')
    removed = deepcopy(backup)
    del removed['variants']['__all__']['leaflets'][KEY]['pts']['b0']['photo_1.png']
    depths, _, _ = analyse(session, removed, context)
    rows = [r for r in depths if r['organ_id'] == 'O3D' and r['point_id'] == 'b0']
    assert len(rows) == 1 and rows[0]['z_board_mm'] is None
    assert rows[0]['depth_status'] == 'fewer_than_two_solved_views' and rows[0]['x_px'] is not None
    split = deepcopy(backup)
    leaves = split['variants']['__all__']['leaflets']
    source = leaves[KEY]
    leaves['leaf_009|unavailable'] = dict(organ_id='leaf_009', leaflet_id='unavailable', boundary_count=3, contours={},
        pts={pid: {'photo_1.png': obs.pop('photo_1.png')} for pid, obs in source['pts'].items()})
    depths, _, extents = analyse(session, split, context)
    assert all(r['z_board_mm'] is None for r in depths)
    assert {e['geometry_status'] for e in extents.values()} == {'image_points_without_depth'}


def test_bbox_only_and_preview_resolution_boxes_are_listed_without_geometry(prepared):
    session, _, context, _, _, backup, _ = prepared
    backup['variants']['__all__']['leaflets']['O9|B9'] = dict(
        organ_id='O9', leaflet_id='B9', pts={}, contours={}, boundary_count=6,
        bboxes={'photo_0.png': dict(annotation_id='leafbox_preview', x_min_px=10., y_min_px=10., x_max_px=60., y_max_px=90.,
                                    image_width_px=800, image_height_px=600)},
        view_status={'photo_0.png': dict(visibility='full', identity_review='confirmed')})
    depths, boxes, extents = analyse(session, backup, context)
    assert extents['O9|B9']['geometry_status'] == 'bbox_only'
    assert extents['O9|B9']['cuboid_status'] == ExtentStatus.NONE
    row = next(r for r in boxes if r['editor_identity'] == 'O9|B9')
    assert row['exclusion_reason'] == 'bbox_image_size_differs_from_calibrated_original'
    assert not [r for r in depths if r['organ_id'] == 'O9']
    bad = deepcopy(backup)
    bad['variants']['__all__']['leaflets']['O9|B9']['view_status']['photo_0.png']['visibility'] = 'mostly'
    with pytest.raises(common.StudyError, match='visibility'):
        analyse(session, bad, context)


def test_leaflet_scene_uses_only_this_photos_detected_marker_ids():
    frames = [dict(image_file='a.png', sha256='A', pose_status='solved', passes_pose_gate=False,
                   board_evidence=dict(source_image_sha256='A', detected_marker_ids=[3, 7])),
              dict(image_file='b.png', sha256='B', pose_status='failed', passes_pose_gate=False,
                   board_evidence=dict(source_image_sha256='OTHER', detected_marker_ids=[1, 2, 3]))]
    leaf = dict(viewer_leaflet_id='B1', organ_id='O', leaflet_id='B1', geometry_status='point_depth_available',
                cuboid_status=ExtentStatus.SINGLE, cuboid_detail='one view', cuboid_min_mm=None, cuboid_max_mm=None,
                feasible_vertices_mm=None, feasible_edges=None, feasible_fraction_of_cuboid=None,
                point_extent_status='sparse_points_only_not_leaf_boundary', point_extent_min_mm=[0, 0, 0],
                point_extent_max_mm=[1, 1, 1], triangulated_point_ids=['b0', 'b2'], image_point_ids=['b0', 'b2', 'i1'],
                points_outside_feasible_region=[], any_accepted_pose=False)
    boxes = [dict(viewer_leaflet_id='B1', image_file='a.png', visibility='full', identity_review='confirmed',
                  used_for_extent=True, exclusion_reason=None, x_min_px=1, y_min_px=2, x_max_px=30, y_max_px=40)]
    depths = [dict(viewer_leaflet_id='B1', image_file='b.png', point_id='i1')]
    payload = review_tool.leaflet_scene_payload(dict(frames=frames), [leaf], boxes, depths)[0]
    assert payload['photo_indices'] == [0, 1]
    photos = {p['image_file']: p for p in payload['photos']}
    assert photos['a.png']['detected_marker_ids'] == '3; 7'
    assert photos['b.png']['detected_marker_ids'] == 'unavailable'  # evidence belongs to another photo
    assert payload['boxes'][0]['rect_px'] == [1, 2, 30, 40] and payload['validated_metric'] is False
    assert json.dumps(payload)  # serialisable for the viewer
