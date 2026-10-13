"""AI-assisted labeling with MOCKED segmentation: proposal -> accept -> rebuild -> training export.

No model weights are loaded and no inference runs. The mock backend draws geometric
shapes; it verifies plumbing, coordinate handling and exclusion rules only.
"""
from copy import deepcopy
import json

import numpy as np
from PIL import Image
import pytest

from tools import export_leaflet_training as export_tool
from tools import leaflet_segmenter as seg
from tools import rebuild_leaf_edit_session as rebuild_tool
from tools import serve_leaf_edit_session as serve_tool
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case  # noqa: F401  (fixture)
from tools.tests.test_rebuild_leaf_edit_session import prepared  # noqa: F401  (fixture)
from tools.tests.test_serve_leaf_edit_session import request, running

KEY = 'O3D|L3D'


class FixedMask:
    """A segmenter returning a caller-supplied crop mask (two blobs, one with a hole)."""
    def __init__(self, builder):
        self.builder = builder

    def info(self):
        return dict(available=True, backend='fixed-test-mask', model_name='fixed-test-mask', is_mock=True)

    def predict(self, rgb, box, positive, negative):
        return [seg.MaskCandidate(self.builder(rgb.shape[:2]), 0.5)]


def photo(tmp_path, size=(400, 300)):
    path = tmp_path / 'photo.png'
    Image.new('RGB', size, (20, 60, 30)).save(path)
    return path, common.file_hash(path)


def test_mock_proposal_uses_original_pixels_crop_and_negative_clicks(tmp_path):
    path, sha = photo(tmp_path)
    result = seg.propose(seg.MockSegmenter(), path, sha, dict(box_px=[250, 150, 350, 250], positive_px=[], negative_px=[]))
    first = result['candidates'][0]
    x0, y0, x1, y1 = first['bbox_px']
    assert (x0, y0, x1, y1) == pytest.approx((250, 150, 350, 250), abs=1.01)  # crop offset restored
    assert result['crop_px'][0] > 0 and result['model']['is_mock'] is True
    assert all(0 <= x <= 399 and 0 <= y <= 299 for ring in first['rings'] for x, y in ring['points_px'])
    assert first['bbox_px'] == seg.bbox_from_rings(first['rings'])
    notched = seg.propose(seg.MockSegmenter(), path, sha, dict(box_px=[250, 150, 350, 250], negative_px=[[300, 200]]))
    assert notched['candidates'][0]['mask_area_px'] < first['mask_area_px']
    assert any(r['is_hole'] for r in notched['candidates'][0]['rings'])  # the excluded disc stays a hole
    assert result['human_review'] == 'pending'


def test_components_are_filtered_by_prompt_and_holes_are_kept(tmp_path):
    path, sha = photo(tmp_path)
    # A click at (150, 150) gives a crop starting at (22, 22); the click is local (128, 128).
    def two_blobs(shape):
        mask = np.zeros(shape, dtype=bool)
        mask[100:160, 100:160] = True       # clicked leaflet
        mask[108:118, 108:118] = False      # hole inside it
        mask[100:160, 200:240] = True       # a neighbouring leaflet
        return mask
    result = seg.propose(FixedMask(two_blobs), path, sha, dict(positive_px=[[150, 150]]))
    assert result['crop_px'][:2] == [22, 22]
    candidate = result['candidates'][0]
    assert candidate['discarded_components'] == 1
    outer = [r for r in candidate['rings'] if not r['is_hole']]
    holes = [r for r in candidate['rings'] if r['is_hole']]
    assert len(outer) == 1 and len(holes) == 1
    assert candidate['bbox_px'] == [122, 122, 182, 182]  # original pixels, crop offset restored


def test_prompt_validation_and_unavailable_backends(tmp_path):
    path, sha = photo(tmp_path)
    for prompts in (dict(), dict(negative_px=[[5, 5]]), dict(positive_px=[[500, 5]]), dict(box_px=[10, 10, 5, 20]),
                    dict(box_px=[0, 0, 401, 10])):
        with pytest.raises(common.StudyError):
            seg.propose(seg.MockSegmenter(), path, sha, prompts)
    with pytest.raises(common.StudyError, match='changed'):
        seg.propose(seg.MockSegmenter(), path, 'wrong', dict(positive_px=[[5, 5]]))
    unavailable = seg.load_segmenter(None)
    assert unavailable.info()['available'] is False
    with pytest.raises(common.StudyError, match='unavailable'):
        unavailable.predict(None, None, [], [])
    assert seg.load_segmenter('sam2', tmp_path / 'missing.json').info()['available'] is False
    config = dict(seg.SAM2_CONFIG_EXAMPLE, checkpoint=str(tmp_path / 'absent.pt'), repository=str(tmp_path))
    common.write_json(tmp_path / 'sam2.json', config)
    sam = seg.load_segmenter('sam2', tmp_path / 'sam2.json')
    info = sam.info()
    assert info['available'] is False and info['loaded'] is False and 'nothing is downloaded' in info['reason']
    with pytest.raises(common.StudyError, match='checkpoint not found'):
        sam.predict(np.zeros((4, 4, 3), np.uint8), None, [[1, 1]], [])


def test_server_segment_endpoint_requires_token_and_writes_nothing(prepared):
    session, backup_path, context, out, *_ = prepared
    before = sorted(p.name for p in session.rglob('*'))
    plain = serve_tool.EditService(session, context, out.parent / 'runs', backup_path)
    mock = serve_tool.EditService(session, context, out.parent / 'runs', backup_path, seg.MockSegmenter())
    body = json.dumps(dict(image_file='photo_0.png', target_leaf_key=KEY,
                           prompts=dict(box_px=[700, 500, 900, 700], positive_px=[], negative_px=[]))).encode()
    for service, expected in ((plain, 503), (mock, 200)):
        with running(service) as port:
            origin = {'Origin': f'http://127.0.0.1:{port}', 'Content-Type': 'application/json'}
            assert request(port, 'GET', '/api/segmenter')[0] == 403
            assert request(port, 'POST', '/api/segment', body, origin)[0] == 403
            status, data = request(port, 'POST', '/api/segment', body, {**origin, 'X-Local-Token': service.token})
            assert status == expected, data
            if expected == 200:
                result = json.loads(data)
                assert result['image_file'] == 'photo_0.png' and result['model']['is_mock'] is True
                assert result['candidates'][0]['bbox_px'] == pytest.approx([700, 500, 900, 700], abs=1.01)
                unknown = json.dumps(dict(image_file='other.png', prompts=dict(positive_px=[[5, 5]]))).encode()
                assert request(port, 'POST', '/api/segment', unknown, {**origin, 'X-Local-Token': service.token})[0] == 400
                bad = json.dumps(dict(image_file='photo_0.png', prompts=dict(positive_px=[[99999, 5]]))).encode()
                assert request(port, 'POST', '/api/segment', bad, {**origin, 'X-Local-Token': service.token})[0] == 400
            info = json.loads(request(port, 'GET', '/api/segmenter', headers={'X-Local-Token': service.token})[1])
            assert info['available'] is (expected == 200)
    assert sorted(p.name for p in session.rglob('*')) == before
    assert not list((out.parent / 'runs').iterdir())


def accepted_backup(backup, capture):
    """Mirror the editor's acceptProposal output for a mock proposal on photo_0."""
    result = deepcopy(backup)
    state = result['variants']['__all__']
    frame = next(f for f in capture['frames'] if f['image_file'] == 'photo_0.png')
    path = common.BUILD.parent / 'photo_0.png'
    proposal = seg.propose(seg.MockSegmenter(), path, frame['sha256'],
                           dict(box_px=[700, 500, 900, 700], negative_px=[[800, 600]]))
    rings = proposal['candidates'][0]['rings']
    x0, y0, x1, y1 = seg.bbox_from_rings(rings)
    leaf = state['leaflets'][KEY]
    leaf['bboxes'] = {'photo_0.png': dict(x_min_px=x0, y_min_px=y0, x_max_px=x1, y_max_px=y1, image_width_px=1600,
                                          image_height_px=1200, annotation_id='leafbox_ai', region_source='ai_proposal_accepted',
                                          proposal_id='proposal_ok')}
    leaf['regions'] = {'photo_0.png': dict(rings=rings, fill_rule='evenodd', region_source='ai_proposal_accepted',
                                           proposal_id='proposal_ok', model=proposal['model'], prompts=proposal['prompts'],
                                           user_edited=False)}
    base = dict(kind='leaflet_region', image_key='photo_0.png', target_leaf_key=KEY, rings=rings, model=proposal['model'])
    state['proposals'] = {'proposal_ok': dict(base, proposal_id='proposal_ok', state='accepted'),
                          'proposal_draft': dict(base, proposal_id='proposal_draft', state='proposed'),
                          'proposal_edit': dict(base, proposal_id='proposal_edit', state='edited'),
                          'proposal_bad': dict(base, proposal_id='proposal_bad', state='rejected')}
    return result


def test_accepted_region_reaches_rebuild_but_never_triangulation(prepared):
    session, path, context, out, _, backup, capture = prepared
    common.write_json(path, backup)
    plain_depths = rebuild_tool.rebuild(session, path, context, out.parent / 'plain')
    ai = accepted_backup(backup, capture)
    ai_path = path.with_name('ai.backup.json')
    common.write_json(ai_path, ai)
    report = rebuild_tool.rebuild(session, ai_path, context, out)
    assert report['ai_proposals_by_state'] == dict(accepted=1, proposed=1, edited=1, rejected=1)
    assert report['editor_observations'] == plain_depths['editor_observations']
    keep = ('point_id', 'image_file', 'x_px', 'y_px', 'x_board_mm', 'y_board_mm', 'z_board_mm')
    strip = lambda rows: sorted(tuple(r[k] for k in keep) for r in rows)
    assert strip(common.rows(out / 'editor_point_depths.csv')) == strip(common.rows(out.parent / 'plain/editor_point_depths.csv'))
    box = next(r for r in common.rows(out / 'leaflet_bbox_observations.csv') if r['image_file'] == 'photo_0.png')
    assert box['region_source'] == 'ai_proposal_accepted' and box['has_accepted_region'] == 'True'
    assert box['identity_review'] == 'unconfirmed' and box['used_for_extent'] == 'False'
    assert box['region_model'] == 'mock-ellipse-not-a-model'
    regions = common.read_json(out / 'accepted_regions.json')
    assert len(regions['regions']) == 1
    assert regions['regions'][0]['proposal_id'] == 'proposal_ok'
    assert regions['used_for_triangulation'] is False
    assert '수락한 2D 윤곽 1개' in (out / 'labels/index.html').read_text(encoding='utf-8')
    assert common.file_hash(out / 'labels/photo_0000.jpg') != common.file_hash(out.parent / 'plain/labels/photo_0000.jpg')


def test_training_export_contains_only_saved_labels_with_masks_and_plant_split(prepared):
    session, path, _, out, _, backup, capture = prepared
    ai = accepted_backup(backup, capture)
    ai['variants']['__all__']['leaflets'][KEY]['bboxes']['photo_1.png'] = dict(
        x_min_px=10, y_min_px=10, x_max_px=90, y_max_px=80, image_width_px=1600, image_height_px=1200, annotation_id='manual')
    ai['variants']['__all__']['leaflets'][KEY]['bboxes']['photo_2.png'] = dict(
        x_min_px=10, y_min_px=10, x_max_px=90, y_max_px=80, image_width_px=800, image_height_px=600, annotation_id='preview')
    ai_path = path.with_name('ai.backup.json')
    common.write_json(ai_path, ai)
    manifest = export_tool.export(session, ai_path, out)
    rows = common.rows(out / 'leaflet_instances.csv')
    assert [r['image_file'] for r in rows] == ['photo_0.png', 'photo_1.png']
    assert manifest['excluded_ai_proposals_by_state'] == dict(proposed=1, edited=1, rejected=1)
    assert manifest['skipped_labels'][0]['reason'] == 'invalid_or_non_original_bbox'
    ai_row, manual_row = rows
    assert ai_row['label_origin'] == 'ai_proposal_accepted' and ai_row['proposal_model_is_mock'] == 'True'
    assert manual_row['label_origin'] == 'manual_bbox' and manual_row['has_mask'] == 'False'
    with Image.open(out / ai_row['mask_file']) as mask:
        pixels = np.array(mask)
    assert pixels.shape == (1200, 1600)
    assert pixels[600, 800] == 0 and pixels[600, 720] == 255  # the negative-click hole is kept empty
    assert int(ai_row['mask_area_px']) == int((pixels > 0).sum())
    for name in ('photo_0.png', 'photo_1.png'):
        assert common.file_hash(out / 'images' / name) == next(f['sha256'] for f in capture['frames'] if f['image_file'] == name)
    assert not (out / 'images/photo_2.png').exists()
    split = common.read_json(out / 'splits.json')
    assert split['status'] == 'insufficient_plants_for_held_out_split' and split['eval_plants'] == []
    assert manifest['deep_learning_run'] is False and manifest['uploaded'] is False


def test_plant_split_never_crosses_plants():
    assert export_tool.plant_split({'P1'}, [])['status'] == 'insufficient_plants_for_held_out_split'
    assert export_tool.plant_split({'P1', 'P2'}, [])['status'] == 'eval_plants_not_selected'
    split = export_tool.plant_split({'P1', 'P2', 'P3'}, ['P2'])
    assert split['train_plants'] == ['P1', 'P3'] and split['eval_plants'] == ['P2']
    with pytest.raises(common.StudyError):
        export_tool.plant_split({'P1', 'P2'}, ['P1', 'P2'])
    with pytest.raises(common.StudyError):
        export_tool.plant_split({'P1', 'P2'}, ['P9'])
