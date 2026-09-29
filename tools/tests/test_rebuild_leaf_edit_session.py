"""Edited identities, deleted observations and unvalidated cameras survive rebuild."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools import prepare_leaf_edit_session as prepare_tool
from tools import rebuild_leaf_edit_session as tool
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case


@pytest.fixture
def prepared(fragment_case):
    capture_path, annotation_path, out = fragment_case
    capture = common.read_json(capture_path)
    intrinsics_path = capture_path.with_name('intrinsics.json')
    common.write_json(intrinsics_path, capture['intrinsics'])
    board = prepare_tool.get_settings().board_spec_path
    capture.update(plant_id='P', session_id='S', validated_metric=False,
                   intrinsics_path=str(intrinsics_path), intrinsics_sha256=common.file_hash(intrinsics_path),
                   board_spec_sha256=common.file_hash(board))
    for frame in capture['frames']:
        frame['board_evidence'] = dict(source_image_sha256=frame['sha256'], detection_status='no_board_detected',
                                       detected_marker_ids=[], detected_corner_ids=[], markers=[], corners=[])
    common.write_json(capture_path, capture)
    session = out.parent / 'editor'
    prepare_tool.prepare(capture_path, annotation_path, session)
    seed = common.read_json(session / 'seed.backup.json')
    backup = deepcopy(seed)
    backup['capture'] = tool.compact_capture(backup['capture'])
    backup_path = out.parent / 'edited.json'
    common.write_json(backup_path, backup)
    return session, backup_path, annotation_path, out, seed, backup, capture


def test_rebuild_executes_edited_pixels_and_preserves_sparse_interior_points(prepared):
    session, path, context, out, _, backup, capture = prepared
    leaf = backup['variants']['__all__']['leaflets']['O3D|L3D']
    leaf['pts']['b0']['photo_0.png'][0] += 3.
    leaf['pts']['i0'] = {'photo_0.png': [800., 600.]}
    common.write_json(path, backup)
    original_hashes = [common.file_hash(p) for p in (path, context, session / 'seed.backup.json')]
    report = tool.rebuild(session, path, context, out)
    assert report['modeled_leaflets'] == 1 and report['editor_observations'] == 7
    point_rows = common.rows(out / 'editor_point_depths.csv')
    assert len(point_rows) == 7
    interior = next(row for row in point_rows if row['point_kind'] == 'interior')
    assert interior['depth_status'] == 'fewer_than_two_solved_views'
    assert interior['z_board_mm'] == 'unavailable'
    assert {row['validated_metric'] for row in point_rows} == {'False'}
    assert {row['passes_pose_gate'] for row in point_rows} == {'False'}
    assert {r['point_id'] for r in common.rows(out / 'preview/points.candidate.csv')} == {'b0', 'b1', 'b2'}
    observed = common.read_json(out / 'annotations.edited.json')['leaflets'][0]['observations'][0]
    assert observed['boundary_xy_px'][0] == leaf['pts']['b0']['photo_0.png']
    assert [common.file_hash(p) for p in (path, context, session / 'seed.backup.json')] == original_hashes
    with pytest.raises(common.StudyError, match='already exists'):
        tool.rebuild(session, path, context, out)


def test_deleted_point_and_deleted_identity_never_return_from_seed(prepared):
    _, _, context_path, _, seed, backup, capture = prepared
    leaf = backup['variants']['__all__']['leaflets']['O3D|L3D']
    del leaf['pts']['b1']['photo_1.png']
    context = common.read_json(context_path)
    annotation, rows, report = tool.convert(backup, seed, context, capture)
    assert annotation['leaflets'] == [] and len(rows) == 5
    assert report['leaf_status'][0]['complete_solved_views'] == 1
    del backup['variants']['__all__']['leaflets']['O3D|L3D']
    annotation, rows, report = tool.convert(backup, seed, context, capture)
    assert annotation['leaflets'] == [] and rows == []
    assert report['deleted_seed_identities'] == ['O3D|L3D']
    assert annotation['two_d_only_candidates'][0]['leaflet_id'] == 'F2D'


def test_latest_context_downgrade_prevents_stale_seed_mesh_and_point_depth(prepared):
    _, _, context_path, _, seed, backup, capture = prepared
    context = common.read_json(context_path)
    old = context['leaflets'].pop()
    context['two_d_only_candidates'].append(old)
    annotation, rows, report = tool.convert(backup, seed, context, capture)
    assert annotation['leaflets'] == []
    assert {v['leaflet_id'] for v in annotation['two_d_only_candidates']} == {'F2D', 'L3D'}
    assert report['leaf_status'][0]['context_kind'] == 'two_d_only_candidates'
    assert all(r['z_board_mm'] is None for r in tool.point_depths(rows, capture))
    assert {r['depth_status'] for r in tool.point_depths(rows, capture)} == {'context_physical_correspondence_unresolved'}


def test_explicit_physical_points_keep_depth_without_polygon_correspondence(prepared):
    _, _, context_path, _, seed, backup, capture = prepared
    context = common.read_json(context_path)
    region = context['leaflets'].pop()
    context['two_d_only_candidates'].append(region)
    context['physical_point_candidates'] = [dict(organ_id='O3D', leaflet_id='L3D', observations=[
        dict(image_file=entry['image_file'], label_image_size_px=entry['label_image_size_px'],
             points=[dict(point_id='b0', xy_px=entry['boundary_xy_px'][0])]) for entry in region['observations']])]
    annotation, rows, _ = tool.convert(backup, seed, context, capture)
    assert not annotation['leaflets']
    depths = tool.point_depths(rows, capture)
    assert all(r['z_board_mm'] is not None for r in depths if r['point_id']=='b0')
    assert all(r['z_board_mm'] is None for r in depths if r['point_id']!='b0')


def test_partial_metadata_and_newly_editable_context_are_respected(prepared):
    _, _, context_path, _, seed, backup, capture = prepared
    context = common.read_json(context_path)
    leaf = backup['variants']['__all__']['leaflets']['O3D|L3D']
    leaf['outline_completeness'] = 'partial_observed_patch'
    leaf['identity_history'] = [{'source_leaf_key': 'another|id'}]
    annotation, _, _ = tool.convert(backup, seed, context, capture)
    assert annotation['leaflets'][0]['outline_completeness'] == 'partial_observed_patch'
    assert annotation['leaflets'][0]['identity_history'] == leaf['identity_history']
    # A context-only identity explicitly added to the editor replaces that context entry.
    new = deepcopy(leaf)
    new.update(organ_id='O2D', leaflet_id='F2D')
    backup['variants']['__all__']['leaflets']['O2D|F2D'] = new
    annotation, _, _ = tool.convert(backup, seed, context, capture)
    assert annotation['two_d_only_candidates'] == []
    assert [v['leaflet_id'] for v in annotation['leaflets']].count('F2D') == 1


def test_split_identity_mapping_is_unique_and_order_independent(prepared):
    _, _, context_path, _, seed, backup, capture = prepared
    base = backup['variants']['__all__']['leaflets'].pop('O3D|L3D')
    for organ in ('split1', 'split2'):
        leaf = deepcopy(base)
        leaf.update(organ_id=organ, leaflet_id='unavailable')
        backup['variants']['__all__']['leaflets'][organ + '|unavailable'] = leaf
    context = common.read_json(context_path)
    annotation, _, report = tool.convert(backup, seed, context, capture)
    assert len({l['leaflet_id'] for l in annotation['leaflets']}) == 2
    backup['variants']['__all__']['leaflets'] = dict(reversed(list(backup['variants']['__all__']['leaflets'].items())))
    assert tool.convert(backup, seed, context, capture)[2]['identity_mapping'] == report['identity_mapping']


@pytest.mark.parametrize('mutation', ['pose', 'quality', 'photo', 'identity'])
def test_changed_capture_or_source_fails_before_output(prepared, mutation):
    session, path, context, out, _, backup, _ = prepared
    if mutation == 'pose':
        backup['capture']['frames'][0]['tvec_mm'][0] += 1.
    elif mutation == 'quality':
        backup['capture']['quality']['max_point_error_px'] += 100
    elif mutation == 'identity':
        backup['plant_id'] = 'another'
    else:
        (session / 'images/photo_0.png').write_bytes(b'changed image')
    common.write_json(path, backup)
    with pytest.raises(common.StudyError):
        tool.rebuild(session, path, context, out)
    assert not out.exists()


def test_exact_point_depth_is_independent_of_boundary_completeness(prepared):
    _, _, context_path, _, seed, backup, capture = prepared
    leaf = backup['variants']['__all__']['leaflets']['O3D|L3D']
    leaf['pts']['i0'] = {f['image_file']: [800., 600.] for f in capture['frames'][:2]}
    leaf['pts']['i1'] = {'photo_2.png': [800., 600.]}
    _, rows, _ = tool.convert(backup, seed, common.read_json(context_path), capture)
    depths = tool.point_depths(rows, capture)
    for r in depths:
        if r['point_id'] == 'i0':
            np.testing.assert_allclose([r['x_board_mm'], r['y_board_mm'], r['z_board_mm']], [0., 0., 100.], atol=1e-7)
            assert not r['validated_metric']
        if r['point_id'] == 'i1':
            assert r['z_board_mm'] is None and r['source_view_count'] == 1


def test_inactive_point_gate_is_not_reported_as_passed(prepared):
    _, _, context_path, _, seed, backup, capture = prepared
    capture['quality']['max_point_error_px'] = None
    _, rows, _ = tool.convert(backup, seed, common.read_json(context_path), capture)
    depths = tool.point_depths(rows, capture)
    assert depths and all(r['passes_point_gate'] is None and not r['point_gate_active'] for r in depths)


@pytest.mark.parametrize('physical_only', [False, True])
def test_preview_to_original_scaling_does_not_invalidate_unchanged_points(prepared, physical_only):
    _, _, context_path, _, seed, backup, capture = prepared
    context = common.read_json(context_path)
    capture['intrinsics'].update(image_width_px=3024, image_height_px=3024)
    leaf = context['leaflets'][0]
    for observation in leaf['observations']:
        observation['label_image_size_px'] = [1500, 1500]
        observation['boundary_xy_px'] = [[584, 794], [523, 559], [558, 620]]
    if physical_only:
        context['leaflets'] = []
        context['two_d_only_candidates'].append(leaf)
        context['physical_point_candidates'] = [dict(organ_id='O3D', leaflet_id='L3D', observations=[
            dict(image_file=o['image_file'], label_image_size_px=o['label_image_size_px'],
                 points=[dict(point_id=f'b{i}', xy_px=xy) for i, xy in enumerate(o['boundary_xy_px'])])
            for o in leaf['observations']])]
    for document in (seed, backup):
        points = document['variants']['__all__']['leaflets']['O3D|L3D']['pts']
        for observation in leaf['observations']:
            for i, xy in enumerate(observation['boundary_xy_px']):
                points[f'b{i}'][observation['image_file'].lower()] = (
                    np.asarray(xy) * np.array([3024, 3024]) / [1500, 1500]).tolist()
    _, rows, _ = tool.convert(backup, seed, context, capture)
    assert rows and all(r['context_depth_restriction'] is None for r in rows)
