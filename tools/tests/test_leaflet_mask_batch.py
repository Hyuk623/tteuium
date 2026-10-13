"""Mask observations remain separate from physical identity and source boxes."""
from copy import deepcopy
import json
from pathlib import Path
import threading

import numpy as np
from PIL import Image
import pytest

from tools import leaflet_mask_batch as mod
from tools.leaf_light import common
from tools.leaflet_segmenter import MaskCandidate


class Scores:
    def __init__(self):
        self.calls = 0
        self.fail = False

    def info(self):
        return dict(available=True, backend='fixture', is_mock=True, model_name='fixture')

    def predict_logits(self, rgb, box, positive, negative):
        self.calls += 1
        if self.fail:
            raise RuntimeError('deliberate failure')
        h, w = rgb.shape[:2]
        a = np.full((h, w), -8., np.float32)
        a[20:70, 20:70] = 8
        a[35:40, 35:40] = -8  # hole
        a[90, 90] = 8  # single-pixel disconnected region, lost by polygon-only storage
        a[21, 72] = 1  # appears at sensitivity 50 but not 20
        b = a.copy(); b[20:30] = -8
        return [MaskCandidate(a > 0, .9, a), MaskCandidate(b > 0, .6, b)]


@pytest.fixture
def batch(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    session, labels = tmp_path/'session', tmp_path/'labels'
    session.mkdir(); labels.mkdir()
    Image.new('RGB', (120, 120), '#376f2d').save(session/'photo.png')
    common.write_json(session/'capture.json', dict(frames=[dict(image_file='photo.png', image_path='photo.png', sha256=common.file_hash(session/'photo.png'))]))
    transform = dict(type='uncropped_stretch', original_size_px=[120, 120], export_size_px=[60, 60], scale_x=2, scale_y=2)
    coco = dict(images=[dict(id=1, file_name='photo.png', width=120, height=120, extra=dict(view_group='middle', transform=transform))],
                categories=[dict(id=1, name='leaflet'), dict(id=2, name='main_stem')],
                annotations=[dict(id=1, image_id=1, category_id=1, bbox=[15., 15., 70., 70.], source_export={'annotation_id': 42}),
                             dict(id=2, image_id=1, category_id=1, bbox=[25., 25., 70., 70.]),
                             dict(id=3, image_id=1, category_id=2, bbox=[30., 30., 8., 80.])])
    common.write_json(labels/'original_pixel_labels.coco.json', coco)
    common.write_json(labels/'mapping_report.json', dict(plant_id='dwt_01', session=str(session), photos=[dict(prepared_frame='photo.png', mapped=True, alignment=dict(accepted=True))]))
    common.write_json(labels/'input_hashes.json', {str(session/'capture.json'): common.file_hash(session/'capture.json')})
    mod.prepare('dwt_01', labels, session, tmp_path/'batch')
    result = mod.Batch(tmp_path/'batch', Scores())
    return result, labels, session


def action(batch, name, **kwargs):
    identity = batch.manifest['ids'][0]
    return batch.review(identity, dict(action=name, revision=batch.item(identity)['revision'], **kwargs))


def test_preserve_source_pixels_fragments_and_cached_threshold(batch):
    b, labels, session = batch
    before = common.file_hash(labels/'original_pixel_labels.coco.json')
    b.run()
    assert b.status()['total'] == 2 and b.status()['generation'] == {'ready': 2}
    identity = b.manifest['ids'][0]
    item = b.item(identity)
    assert item['prompts']['positive_px'] == []
    mask, meta = b.mask(item)
    assert mask[90, 90] and not mask[36, 36] and not mask[21, 72]
    assert meta['crop_px'] == [0, 0, 120, 120]
    calls = b.segmenter.calls
    action(b, 'select', sensitivity=50)
    mask, _ = b.mask(b.item(identity))
    assert mask[21, 72] and mask[90, 90] and not mask[36, 36]
    action(b, 'select', candidate=1)
    assert b.segmenter.calls == calls
    assert b.item(identity)['source_bbox_xywh_px'] == [15., 15., 70., 70.]
    assert common.file_hash(labels/'original_pixel_labels.coco.json') == before


def test_individual_accept_hold_undo_and_export(batch):
    b, _, _ = batch
    b.run()
    assert b.export()['count'] == 0
    accepted = action(b, 'accept', active_seconds=3)
    assert accepted['review'] == 'accepted'
    exported = b.export()
    data = common.read_json(Path(exported['manifest']))
    record = data['observations'][0]
    full = np.array(Image.open(Path(exported['path'])/record['mask_file']))
    assert full.shape == (120, 120) and full[90, 90] and not full[36, 36]
    assert record['source_annotation']['source_export']['annotation_id'] == 42
    assert not record['identity_confirmed'] and not record['depth_confirmed']
    assert b.status()['unchanged_acceptance_fraction'] == 1
    action(b, 'defer'); assert b.export()['count'] == 0
    action(b, 'undo'); assert b.export()['count'] == 1
    action(b, 'select', sensitivity=50); assert b.export()['count'] == 0
    action(b, 'reject'); assert b.item(b.manifest['ids'][0])['review'] == 'rejected'


def test_restart_resume_stop_and_failed_accounting(batch):
    b, _, _ = batch
    b.stop_event.set(); b.run()
    assert b.status()['generation'] == {'pending': 2}
    b.stop_event.clear()
    b._generate(b.manifest['ids'][0])
    b.segmenter.fail = True
    b.run()
    assert b.status()['generation'] == {'ready': 1, 'failed': 1}
    reopened = mod.Batch(b.root, Scores())
    reopened.run()
    assert reopened.segmenter.calls == 0
    reopened.run(retry_failed=True)
    assert reopened.segmenter.calls == 1 and reopened.status()['generation'] == {'ready': 2}


def test_prompt_changes_one_item_only_and_review_conflict(batch):
    b, _, _ = batch
    b.run(); before = b.item(b.manifest['ids'][1])
    old = b.item(b.manifest['ids'][0])
    action(b, 'refine', positive_px=[[30, 30]], negative_px=[[60, 60]])
    assert b.segmenter.calls == 3
    assert b.item(b.manifest['ids'][1]) == before
    assert b.item(old['id'])['cache_key'] != old['cache_key']
    with pytest.raises(ValueError, match='reload'):
        b.review(old['id'], dict(action='accept', revision=old['revision']))
    action(b, 'undo')
    assert b.item(old['id'])['cache_key'] == old['cache_key']


def test_contour_edit_preserves_unrepresented_tiny_component(batch):
    b, _, _ = batch
    b.run()
    original = b.detail(b.manifest['ids'][0])
    rings = deepcopy(original['rings'])
    rings[0]['points_px'][0][0] += 1
    action(b, 'contour', rings=rings)
    mask, _ = b.mask(b.item(original['id']))
    assert mask[90, 90] and not mask[36, 36]
    action(b, 'undo')
    assert b.detail(original['id'])['rings'] == original['rings']


def test_unverified_mapping_retains_all_items_as_errors(batch):
    b, labels, session = batch
    report = common.read_json(labels/'mapping_report.json')
    report['photos'][0]['alignment']['accepted'] = False
    common.write_json(labels/'mapping_report.json', report)
    mod.prepare('dwt_01', labels, session, b.root.parent/'invalid')
    invalid = mod.Batch(b.root.parent/'invalid', Scores())
    invalid.run()
    assert invalid.status()['total'] == 2 and invalid.status()['generation'] == {'failed': 2}
    assert invalid.segmenter.calls == 0


def test_changed_source_cannot_be_accepted(batch):
    b, _, session = batch
    b.run()
    Image.new('RGB', (120, 120), 'black').save(session/'photo.png')
    with pytest.raises(ValueError, match='Source image changed'):
        action(b, 'accept')


def test_original_coordinate_restore_for_offset_crop():
    mask = np.zeros((10, 12), bool); mask[2:7, 3:9] = True
    rings = mod.raster_rings(mask, [100, 200, 112, 210])
    points = np.asarray(rings[0]['points_px'])
    assert points[:, 0].min() == 103 and points[:, 1].min() == 202
    assert np.array_equal(mod.render_rings(rings, mask.shape, [100, 200, 112, 210]), mask)


def test_model_change_clears_acceptance_and_overlap_only_ranks(batch):
    b, _, _ = batch
    b.run()
    detail = b.detail(b.manifest['ids'][0])
    assert detail['result']['risk']['neighbor_overlap_max'] == 1
    action(b, 'accept')
    b.segmenter.config = {'different_model_setting': True}
    b.run()
    assert b.segmenter.calls == 4
    assert b.status()['review'] == {'unreviewed': 2}
    assert b.export()['count'] == 0


def test_writer_lease_prevents_concurrent_process_style_review(batch):
    b, _, _ = batch
    b.run()
    second = mod.Batch(b.root, Scores())
    with b.writer():
        assert second.status()['job']['running'] is True
        with pytest.raises(ValueError, match='처리 중'):
            action(second, 'accept')


def test_batch_endpoints_keep_existing_token_rules(batch, monkeypatch):
    from tools.serve_leaf_edit_session import handler_for, ThreadingHTTPServer
    from tools.tests.test_serve_leaf_edit_session import request
    from types import SimpleNamespace
    b, _, _ = batch
    b.run()
    service = SimpleNamespace(mask_batch=b, token='private-test-token')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    port = server.server_port
    headers = {'X-Local-Token': service.token, 'Origin': f'http://127.0.0.1:{port}', 'Content-Type': 'application/json'}
    try:
        assert request(port, 'GET', '/api/mask-batch/status')[0] == 403
        code, result = request(port, 'GET', '/api/mask-batch/status', headers=headers)
        assert code == 200 and json.loads(result)['total'] == 2
        item = b.item(b.manifest['ids'][0])
        payload = json.dumps(dict(id=item['id'], revision=item['revision'], action='accept'))
        assert request(port, 'POST', '/api/mask-batch/review', payload, {**headers, 'Origin': 'http://evil.invalid'})[0] == 403
        assert request(port, 'POST', '/api/mask-batch/review', payload, headers)[0] == 200
        assert request(port, 'POST', '/api/mask-batch/review', payload, headers)[0] == 400
        assert request(port, 'GET', '/api/mask-batch/mask/'+item['id'], headers=headers)[0] == 200
    finally:
        server.shutdown(); server.server_close()


def test_audit_accounts_for_all_items_and_detects_cache_changes(batch):
    b, _, _ = batch
    b.run()
    report = b.audit()
    assert report['observed_item_count'] == 2 and report['generation_complete']
    assert not report['human_review_complete']
    assert report['changed_inputs'] == [] and report['invalid_cache_items'] == []
    assert len(common.rows(b.root/'processing.csv')) == 2
    item = b.item(b.manifest['ids'][0])
    (b.root/'cache'/item['cache_key']/'logits.npz').write_bytes(b'changed')
    assert b.audit()['invalid_cache_items'] == [item['id']]


def test_compound_aliases_prepare_separately_and_target_one_box(batch):
    b, labels, session = batch
    coco = common.read_json(labels/'original_pixel_labels.coco.json')
    for number, name in enumerate(('compond_leaf', 'compound_leaves', 'compoundleaf'), 10):
        coco['categories'].append(dict(id=number, name=name))
        coco['annotations'].append(dict(id=number, image_id=1, category_id=number, bbox=[10, 10, 90, 90]))
    common.write_json(labels/'original_pixel_labels.coco.json', coco)
    preserved = {p.name: p.read_bytes() for p in (b.root/'items').glob('*.json')}
    manifest = mod.prepare('dwt_01', labels, session, b.root.parent/'compound', 'compoundleaves')
    compound = mod.Batch(b.root.parent/'compound', Scores())
    assert len(manifest['ids']) == 3 and manifest['defaults']['sensitivity'] == 50
    assert all(compound.item(i)['organ_class'] == 'compoundleaves' for i in manifest['ids'])
    selected = manifest['ids'][1]
    compound.run(identity=selected)
    assert compound.status()['generation'] == {'pending': 2, 'ready': 1}
    assert compound.segmenter.calls == 1
    assert preserved == {p.name: p.read_bytes() for p in (b.root/'items').glob('*.json')}
    compound.review(selected, dict(action='accept', revision=compound.item(selected)['revision']))
    exported = common.read_json(Path(compound.export()['manifest']))
    assert exported['organ_class'] == 'compoundleaves'
    assert exported['observations'][0]['organ_class'] == 'compoundleaves'
    assert not exported['observations'][0]['identity_confirmed']
    with pytest.raises(ValueError, match='Unknown observation'):
        compound.start(identity='not_in_this_class')


def test_binary_preview_is_exact_and_read_only_without_model(batch):
    b, _, _ = batch
    b.run()
    identity = b.manifest['ids'][0]
    before = (b.root/'items'/f'{identity}.json').read_bytes()
    calls = b.segmenter.calls
    b.segmenter = None
    raw = b.preview_logits(identity)
    n, h, w, revision = map(int, np.frombuffer(raw, dtype='<u4', count=4))
    scores = np.frombuffer(raw, dtype='<f4', offset=16).reshape(n, h, w)
    for candidate in range(n):
        for sensitivity in (0, 20, 49, 50, 51, 100):
            expected, _ = b.mask(b.item(identity), candidate, sensitivity)
            assert np.array_equal(scores[candidate] > mod.threshold(sensitivity), expected)
    assert revision == b.item(identity)['revision']
    assert before == (b.root/'items'/f'{identity}.json').read_bytes()
    assert calls == 2


def test_http_class_routing_preview_and_review_are_isolated(batch):
    from tools.serve_leaf_edit_session import handler_for, ThreadingHTTPServer
    from tools.tests.test_serve_leaf_edit_session import request
    from types import SimpleNamespace
    b, labels, session = batch
    b.run()
    coco = common.read_json(labels/'original_pixel_labels.coco.json')
    coco['categories'].append(dict(id=9, name='compoundleaves'))
    coco['annotations'].append(dict(id=9, image_id=1, category_id=9, bbox=[10, 10, 90, 90]))
    common.write_json(labels/'original_pixel_labels.coco.json', coco)
    mod.prepare('dwt_01', labels, session, b.root.parent/'compound', 'compoundleaves')
    compound = mod.Batch(b.root.parent/'compound', Scores())
    compound.run()
    service = SimpleNamespace(mask_batch=b, compound_mask_batch=compound, token='test-class-token')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    port = server.server_port
    headers = {'X-Local-Token': service.token, 'Origin': f'http://127.0.0.1:{port}',
               'Content-Type': 'application/json'}
    identity = compound.manifest['ids'][0]
    route = '/api/mask-batch/logits/'+identity+'?organ_class=compoundleaves'
    before = {p.name: p.read_bytes() for p in (b.root/'items').glob('*.json')}
    try:
        assert request(port, 'GET', route)[0] == 403
        status, raw = request(port, 'GET', route, headers=headers)
        assert status == 200 and raw == compound.preview_logits(identity)
        status, raw = request(port, 'GET', '/api/mask-batch/status?organ_class=compoundleaves', headers=headers)
        result = json.loads(raw)
        assert status == 200 and result['total'] == 1
        assert result['available_classes'] == ['leaflet', 'compoundleaves']
        assert request(port, 'GET', '/api/mask-batch/status?organ_class=unknown', headers=headers)[0] == 400
        payload = dict(id=identity, revision=compound.item(identity)['revision'], action='select',
                       sensitivity=71, candidate=0, organ_class='leaflet')
        assert request(port, 'POST', '/api/mask-batch/review', json.dumps(payload), headers)[0] == 400
        payload['organ_class'] = 'compoundleaves'
        assert request(port, 'POST', '/api/mask-batch/review', json.dumps(payload), headers)[0] == 200
        assert compound.item(identity)['sensitivity'] == 71
        assert before == {p.name: p.read_bytes() for p in (b.root/'items').glob('*.json')}
    finally:
        server.shutdown(); server.server_close()


def test_browser_threshold_matches_numpy_at_exact_float32_boundary():
    import shutil
    import subprocess
    if not shutil.which('node'):
        pytest.skip('Node required for browser threshold contract')
    module = Path(mod.__file__).with_name('mask_preview_math.js')
    cases = []
    for sensitivity in (0, 1, 20, 33, 49, 50, 51, 99, 100):
        cut = np.float32(mod.threshold(sensitivity))
        values = np.array([np.nextafter(cut, np.float32(-np.inf)), cut,
                           np.nextafter(cut, np.float32(np.inf)), -10, 10], dtype=np.float32)
        cases.append(dict(sensitivity=sensitivity, values=values.tolist(),
                          expected=(values > mod.threshold(sensitivity)).astype(int).tolist()))
    js = """const fs=require('fs'), m=require(process.argv[1]);
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(cases.map(c=>Array.from(m.raster(Float32Array.from(c.values),1,1,c.values.length,0,c.sensitivity).mask))));"""
    result = subprocess.run(['node', '-e', js, str(module)], input=json.dumps(cases),
                            text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == [c['expected'] for c in cases]


def test_rejection_reason_and_partial_visibility_are_recorded_and_undoable():
    from tools import leaflet_mask_batch as mb
    assert mb.REJECT_REASONS == ('duplicate_box', 'box_misses_leaf', 'false_positive')
    assert 'reject_reason' in mb.MUTABLE and 'visibility' in mb.MUTABLE


def _auto_labels(tmp_path, plant='dwt_77', schema='plant-auto-labels-1'):
    session, labels = tmp_path/'s_auto', tmp_path/'l_auto'
    session.mkdir(); labels.mkdir()
    Image.new('RGB', (120, 120), '#376f2d').save(session/'photo.png')
    common.write_json(session/'capture.json', dict(frames=[dict(image_file='photo.png', image_path='photo.png', sha256=common.file_hash(session/'photo.png'))]))
    coco = dict(images=[dict(id=1, file_name='photo.png', width=120, height=120,
                             extra=dict(view_group='middle', transform=dict(type='original_pixels', original_size_px=[120, 120])))],
                categories=[dict(id=1, name='leaflet')], annotations=[dict(id=1, image_id=1, category_id=1, bbox=[15., 15., 70., 70.])])
    common.write_json(labels/'original_pixel_labels.coco.json', coco)
    common.write_json(labels/'mapping_report.json', dict(schema_version=schema, plant_id=plant, session=str(session),
                                                         photos=[dict(prepared_frame='photo.png', mapped=True, alignment=None)]))
    common.write_json(labels/'input_hashes.json', {str(session/'capture.json'): common.file_hash(session/'capture.json')})
    return labels, session


def test_photo_only_auto_labels_prepare_and_auto_accept_is_marked_and_overridable(tmp_path, monkeypatch):
    """User 2026-09-28: model-drafted labels (original pixels, any plant) run through SAM and are accepted as 'auto';
    a person's later review replaces the auto decision."""
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    labels, session = _auto_labels(tmp_path)
    manifest = mod.prepare('dwt_77', labels, session, tmp_path/'batch_auto')
    assert manifest['label_source'] == 'auto'
    b = mod.Batch(tmp_path/'batch_auto', Scores())
    b.run()
    assert b.auto_accept() == {'accepted': 1}
    item = b.item(b.manifest['ids'][0])
    assert item['review'] == 'accepted' and item['review_source'] == 'auto'
    assert b.auto_accept() == {'skipped': 1}, 'already reviewed items are never touched again'
    action(b, 'reject', active_seconds=1)
    item = b.item(b.manifest['ids'][0])
    assert item['review'] == 'rejected' and item['review_source'] == 'human'


def test_human_label_batches_refuse_auto_accept_and_unlisted_plants_need_auto_labels(tmp_path, monkeypatch, batch):
    b, _, _ = batch
    b.run()
    with pytest.raises(common.StudyError):
        b.auto_accept()
    labels, session = _auto_labels(tmp_path, schema='roboflow-session-import-1')
    with pytest.raises(common.StudyError):
        mod.prepare('dwt_77', labels, session, tmp_path/'refused')
