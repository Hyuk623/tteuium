"""Class-agnostic automatic mask drafts: filters, honesty of availability, and the HTTP route.

No model runs: the mock backend draws fixed shapes and a stub backend returns fixed masks.
"""
import json
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from tools import leaflet_segmenter as seg
from tools import rebuild_leaf_edit_session as rebuild_tool
from tools import serve_leaf_edit_session as serve_tool
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case  # noqa: F401  (fixture)
from tools.tests.test_rebuild_leaf_edit_session import prepared  # noqa: F401  (fixture)
from tools.tests.test_serve_leaf_edit_session import request, running


@pytest.mark.parametrize('batch', [None, 3])
def test_sam_automatic_limits_batch_memory_and_records_settings(monkeypatch, tmp_path, batch):
    captured = {}
    class Generator:
        def __init__(self, model, **settings):
            captured.update(settings)
        def generate(self, rgb):
            return [{'segmentation': np.ones(rgb.shape[:2], bool), 'predicted_iou': 0.9}]
    monkeypatch.setitem(sys.modules, 'sam2.automatic_mask_generator',
                        SimpleNamespace(SAM2AutomaticMaskGenerator=Generator))
    config = dict(backend='sam2', repository='unused', checkpoint='unused',
                  checkpoint_sha256='unused', model_config='unused')
    if batch is not None:
        config['points_per_batch'] = batch
    model = seg.Sam2Segmenter(config, tmp_path)
    model.predictor = SimpleNamespace(model=object())
    result = model.automatic(np.zeros((8, 9, 3), np.uint8))
    assert captured['points_per_batch'] == (1 if batch is None else batch)
    assert captured['points_per_side'] == 24
    assert model.loaded['automatic_settings'] == captured
    assert result[0].mask.shape == (8, 9)


class FixedAutomatic:
    """Returns caller-supplied whole-image masks, like an automatic generator would."""
    def __init__(self, builder, automatic=True):
        self.builder, self._automatic = builder, automatic

    def info(self):
        return dict(available=True, backend='fixed-automatic', model_name='fixed-automatic', is_mock=True,
                    automatic=self._automatic, class_agnostic=True)

    def predict(self, rgb, box, positive, negative):
        raise AssertionError('prompted prediction is not used by this test')

    def automatic(self, rgb):
        return [seg.MaskCandidate(m, s) for m, s in self.builder(rgb.shape[:2])]


def photo(tmp_path, size=(400, 300)):
    path = tmp_path / 'photo.png'
    Image.new('RGB', size, (20, 60, 30)).save(path)
    return path, common.file_hash(path)


def test_automatic_drafts_keep_small_and_overlapping_masks_but_drop_frame_sized_ones(tmp_path):
    path, sha = photo(tmp_path)
    def masks(shape):
        height, width = shape
        big = np.zeros(shape, bool); big[40:140, 40:190] = True            # a leaflet-sized mask
        overlap = np.zeros(shape, bool); overlap[100:200, 150:260] = True  # overlaps the first
        small = np.zeros(shape, bool); small[250:275, 300:330] = True      # small real leaflet (750 px)
        speckle = np.zeros(shape, bool); speckle[10:15, 10:18] = True      # 40 px: noise
        background = np.ones(shape, bool)                                  # whole frame
        return [(big, 0.9), (overlap, 0.8), (small, 0.5), (speckle, 0.4), (background, 0.95)]
    result = seg.propose_automatic(FixedAutomatic(masks), path, sha, 'photo.png')
    assert result['mode'] == 'automatic' and result['candidate_class'] == 'unclassified'
    assert [c['mask_area_px'] for c in result['candidates']] == [15000, 11000, 750]
    assert result['dropped'] == dict(too_small=1, too_large=1, no_outer_ring=0, truncated=0)
    assert result['filters']['overlapping_masks_kept_separate'] is True
    first, second = result['candidates'][0], result['candidates'][1]
    assert first['bbox_px'] == [40, 40, 190, 140] and second['bbox_px'] == [150, 100, 260, 200]
    assert first['bbox_px'][2] > second['bbox_px'][0], 'overlapping candidates stay separate'
    assert all(c['assigned_leaflet'] is None and c['assigned_class'] is None for c in result['candidates'])
    assert result['human_review'] == 'pending' and 'not botanical accuracy' in result['notice']
    assert seg.bbox_from_rings(first['rings']) == first['bbox_px']


def test_automatic_is_refused_when_the_backend_cannot_do_it(tmp_path):
    path, sha = photo(tmp_path)
    with pytest.raises(common.StudyError, match='automatic_masks_unavailable'):
        seg.propose_automatic(FixedAutomatic(lambda s: [], automatic=False), path, sha)
    with pytest.raises(common.StudyError, match='segmenter_unavailable'):
        seg.propose_automatic(seg.load_segmenter(None), path, sha)
    assert seg.load_segmenter(None).info()['automatic'] is False
    assert seg.MockSegmenter().info()['automatic'] is True
    with pytest.raises(common.StudyError, match='changed'):
        seg.propose_automatic(seg.MockSegmenter(), path, 'wrong-hash')
    masks = seg.propose_automatic(seg.MockSegmenter(), path, sha)
    assert masks['model']['is_mock'] is True and masks['candidates']


def test_http_route_requires_token_reports_unavailable_and_writes_nothing(prepared):
    session, backup_path, context, out, *_ = prepared
    before = sorted(p.name for p in session.rglob('*'))
    plain = serve_tool.EditService(session, context, out.parent / 'runs', backup_path)
    mock = serve_tool.EditService(session, context, out.parent / 'runs', backup_path, seg.MockSegmenter())
    body = json.dumps(dict(image_files=['photo_0.png'])).encode()
    for service, expected in ((plain, 503), (mock, 200)):
        with running(service) as port:
            origin = {'Origin': f'http://127.0.0.1:{port}', 'Content-Type': 'application/json'}
            assert request(port, 'POST', '/api/segment_automatic', body, origin)[0] == 403
            headers = {**origin, 'X-Local-Token': service.token}
            status, data = request(port, 'POST', '/api/segment_automatic', body, headers)
            assert status == expected
            if expected == 200:
                result = json.loads(data)
                photo = result['photos'][0]
                assert photo['image_file'] == 'photo_0.png' and photo['candidates']
                assert photo['candidate_class'] == 'unclassified' and photo['model']['is_mock'] is True
                too_many = json.dumps(dict(image_files=['photo_0.png'] * 9)).encode()
                assert request(port, 'POST', '/api/segment_automatic', too_many, headers)[0] == 400
                unknown = json.dumps(dict(image_files=['other.png'])).encode()
                assert request(port, 'POST', '/api/segment_automatic', unknown, headers)[0] == 400
                assert request(port, 'POST', '/api/segment_automatic', json.dumps(dict()).encode(), headers)[0] == 400
            else:
                assert '자동 제안을 사용할 수 없습니다' in json.loads(data)['error']
    assert sorted(p.name for p in session.rglob('*')) == before
    assert not list((out.parent / 'runs').iterdir())


def test_rebuild_counts_drafts_and_keeps_them_out_of_labels(prepared):
    session, path, context, out, _, backup, _ = prepared
    state = backup['variants']['__all__']
    leaf = state['leaflets']['O3D|L3D']
    state['auto_drafts'] = {
        'draft_a': dict(draft_id='draft_a', state='draft', image_key='photo_0.png', candidate_class='unclassified'),
        'draft_b': dict(draft_id='draft_b', state='assigned', image_key='photo_0.png', assigned_to='O3D|L3D'),
        'draft_c': dict(draft_id='draft_c', state='rejected', image_key='photo_1.png')}
    leaf['landmark_candidates'] = {'photo_0.png': [
        dict(candidate_id='lm1', state='candidate', method='principal_axis_extremum', xy_px=[700., 500.], inferred=False),
        dict(candidate_id='lm2', state='accepted', method='convex_hull_extremum', xy_px=[720., 520.], accepted_point_id='b0'),
        dict(candidate_id='lm3', state='rejected', method='inferred_centerline', xy_px=[730., 530.], inferred=True)]}
    leaf['point_provenance'] = {'b0': {'photo_0.png': dict(source='landmark_candidate', method='convex_hull_extremum')},
                                'b1': {'photo_1.png': dict(source='cross_view_match', method='epipolar_and_triangulation_residual')}}
    common.write_json(path, backup)
    baseline = rebuild_tool.rebuild(session, path, context, out / 'plain')
    report = rebuild_tool.rebuild(session, path, context, out / 'with_drafts')
    assert report['auto_mask_drafts_by_state'] == dict(draft=1, assigned=1, rejected=1)
    assert report['landmark_candidates_by_state'] == dict(candidate=1, accepted=1, rejected=1)
    assert report['accepted_point_observations_by_source'] == dict(landmark_candidate=1, cross_view_match=1)
    assert report['editor_observations'] == baseline['editor_observations'], 'drafts never become observations'
    keep = ('point_id', 'image_file', 'x_px', 'y_px', 'x_board_mm', 'z_board_mm')
    strip = lambda rows: sorted(tuple(r[k] for k in keep) for r in rows)
    assert strip(common.rows(out / 'with_drafts/editor_point_depths.csv')) == strip(common.rows(out / 'plain/editor_point_depths.csv'))
    annotations = json.dumps(common.read_json(out / 'with_drafts/annotations.edited.json'))
    assert 'landmark_candidates' not in annotations and 'lm1' not in annotations
