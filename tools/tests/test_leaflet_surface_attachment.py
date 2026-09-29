"""Attaching an existing partial-surface run: identity, staleness, reprojection and export boundary."""
from copy import deepcopy
import json

import numpy as np
from PIL import Image
import pytest

from tools import editor_point_review as review_tool
from tools import groimp_bridge
from tools import rebuild_leaf_edit_session as tool
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case  # noqa: F401  (fixture)
from tools.tests.test_rebuild_leaf_edit_session import prepared  # noqa: F401  (fixture)

KEY = 'O3D|L3D'


def patch_run(folder, depth_sha256, points_mm, identity=('O3D', 'L3D'), extra_record=None):
    """A stand-in for a tools.sam_supported_leaf_patches output directory."""
    folder.mkdir(parents=True)
    (folder / 'leaf_0').mkdir()
    centre = np.mean(points_mm, axis=0)
    vertices = np.vstack([points_mm, centre])
    faces = [[0, 1, 3], [1, 2, 3], [0, 3, 2]]
    common.write_json(folder / 'leaf_0' / 'patch.json', dict(
        schema_version='visible-landmark-patch-1', organ_id=identity[0], leaflet_id=identity[1],
        coordinate_frame='board', vertices_mm=vertices.tolist(), faces=faces,
        physical_landmarks=[dict(point_id=f'b{i}', xyz_mm=list(p)) for i, p in enumerate(points_mm)],
        source_images=['photo_0.png', 'photo_1.png'], proposed_faces=4, retained_faces=len(faces),
        interpolated_patch_area_mm2=12.5, all_source_pose_gates_passed=False,
        geometry_source='landmark_interpolation_clipped_to_mask', complete_leaf=False,
        measured_curvature=False, validated_metric=False, suitable_for_ppfd=False))
    records = [dict(organ_id=identity[0], leaflet_id=identity[1], status='diagnostic_partial_patch',
                    url='leaf_0/index.html', faces=len(faces), validated_metric=False)]
    if extra_record:
        records.append(extra_record)
    common.write_json(folder / 'report.json', dict(records=records, depth_sha256=depth_sha256,
                                                   model=dict(model_name='mock-ellipse-not-a-model', is_mock=True),
                                                   inference_run=True, training_run=False, validated_metric=False))
    return folder


def triangulated(result):
    rows = [r for r in common.rows(result / 'editor_point_depths.csv') if r['z_board_mm'] != 'unavailable']
    points, seen = [], set()
    for row in rows:
        if row['point_id'] not in seen:
            seen.add(row['point_id'])
            points.append([float(row[f'{a}_board_mm']) for a in 'xyz'])
    return np.asarray(points)


def test_attached_surface_is_linked_reprojected_and_never_confused_with_observations(prepared):
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    first = tool.rebuild(session, path, context, out / 'first')
    depth_sha = common.file_hash(out / 'first' / 'editor_point_depths.csv')
    patches = patch_run(out / 'patches', depth_sha, triangulated(out / 'first'),
                        extra_record=dict(organ_id='O9', leaflet_id='B9', status='unavailable',
                                          reason='fewer_than_two_posed_views_with_three_existing_landmarks'))
    report = tool.rebuild(session, path, context, out / 'second', patches=patches)
    assert report['attached_surface_status'] == tool.SURFACE_CURRENT and report['attached_surface_count'] == 1
    attached = common.read_json(out / 'second' / 'leaflet_surfaces.json')
    surface = attached['surfaces'][0]
    assert surface['viewer_leaflet_id'] == 'L3D' and surface['identity_known_in_this_run'] is True
    assert surface['geometry_kind'] == 'interpolated_surface' and surface['complete_leaf'] is False
    assert surface['measured_curvature'] is False and surface['suitable_for_ppfd'] is False
    assert attached['unavailable'][0]['reason'].startswith('fewer_than_two_posed_views')
    assert attached['unavailable'][0]['identity_known_in_this_run'] is False
    extent = next(r for r in common.read_json(out / 'second' / 'leaflet_extents.json')['leaflets']
                  if r['viewer_leaflet_id'] == 'L3D')
    assert extent['surface_kinds'] == ['preview_boundary_patch', 'sam_clipped_partial_patch']
    assert extent['attached_surface_faces'] == 3
    html = (out / 'second' / 'labels/index.html').read_text(encoding='utf-8')
    assert '"geometry_kind": "interpolated_surface"' in html and 'showSurfaces' in html
    assert '복원된 점 3개' in html and '보간 부분 면 3개 삼각형' in html
    # Point reprojection does not depend on surfaces; the patch footprint is added on top.
    plain_html = (out / 'first' / 'labels/index.html').read_text(encoding='utf-8')
    assert '복원된 점 3개' in plain_html and '보간 부분 면 0개 삼각형' in plain_html
    with Image.open(out / 'second' / 'labels/photo_0000.jpg') as image:
        painted = np.array(image).astype(int)
    with Image.open(out / 'first' / 'labels/photo_0000.jpg') as before:
        plain = np.array(before).astype(int)
    greener = ((painted[:, :, 1] - plain[:, :, 1]) > 15).sum()
    assert greener > 500, 'the interpolated surface footprint is drawn only when a current patch is attached'


def test_editing_a_correspondence_marks_the_attached_surface_stale_and_hides_it(prepared):
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    first = tool.rebuild(session, path, context, out / 'first')
    patches = patch_run(out / 'patches', common.file_hash(out / 'first' / 'editor_point_depths.csv'),
                        triangulated(out / 'first'))
    edited = deepcopy(backup)
    edited['variants']['__all__']['leaflets'][KEY]['pts']['b0']['photo_1.png'][0] += 9.
    common.write_json(path, edited)
    report = tool.rebuild(session, path, context, out / 'stale', patches=patches)
    attached = common.read_json(out / 'stale' / 'leaflet_surfaces.json')
    assert report['attached_surface_status'] == tool.SURFACE_STALE
    assert attached['surfaces'][0]['status'] == tool.SURFACE_STALE
    assert attached['patch_depth_sha256'] != attached['expected_depth_sha256']
    assert 'rebuilt from the current snapshot' in attached['stale_note']
    extent = next(r for r in common.read_json(out / 'stale' / 'leaflet_extents.json')['leaflets']
                  if r['viewer_leaflet_id'] == 'L3D')
    assert 'stale_partial_patch' in extent['surface_kinds']
    control = tool.rebuild(session, path, context, out / 'control')  # same edited points, no patch attached
    assert control['attached_surface_status'] == 'not_attached'
    with Image.open(out / 'stale' / 'labels/photo_0000.jpg') as image:
        painted = np.array(image).astype(int)
    with Image.open(out / 'control' / 'labels/photo_0000.jpg') as reference:
        plain = np.array(reference).astype(int)
    assert ((painted[:, :, 1] - plain[:, :, 1]) > 15).sum() == 0, 'a stale surface is never drawn on the photo'
    assert '보간 부분 면 0개 삼각형' in (out / 'stale' / 'labels/index.html').read_text(encoding='utf-8')


def test_attachment_requires_a_real_patch_report_and_stays_optional(prepared, tmp_path):
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    report = tool.rebuild(session, path, context, out / 'none')
    assert report['attached_surface_status'] == 'not_attached' and report['attached_surface_count'] == 0
    assert common.read_json(out / 'none' / 'leaflet_surfaces.json')['surfaces'] == []
    common.write_json(tmp_path / 'report.json', dict(records=[]))
    with pytest.raises(common.StudyError, match='depth_sha256'):
        tool.attach_surfaces(tmp_path, 'abc', [])


def test_surface_payload_carries_no_cuboid_and_groimp_export_states_its_limits(prepared, tmp_path):
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    tool.rebuild(session, path, context, out / 'first')
    patches = patch_run(out / 'patches', common.file_hash(out / 'first' / 'editor_point_depths.csv'),
                        triangulated(out / 'first'))
    tool.rebuild(session, path, context, out / 'second', patches=patches)
    attached = common.read_json(out / 'second' / 'leaflet_surfaces.json')
    payload = review_tool.surface_scene_payload(attached)
    serialized = json.dumps(payload)
    assert 'cuboid' not in serialized and payload['surfaces'][0]['geometry_kind'] == 'interpolated_surface'
    extents = common.read_json(out / 'second' / 'leaflet_extents.json')
    assert extents['used_as_surface'] is False and extents['suitable_for_ppfd'] is False
    # The GroIMP boundary transports light-pipeline leaf surfaces only; these files are not that format.
    for wrong in (out / 'second' / 'leaflet_surfaces.json', out / 'second' / 'leaflet_extents.json'):
        with pytest.raises(Exception):
            groimp_bridge.export(wrong, 'v25', tmp_path / ('obj_' + wrong.stem))
        assert not (tmp_path / ('obj_' + wrong.stem)).exists()
