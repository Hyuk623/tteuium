"""Learned review decisions: only confident masks are accepted automatically; the rest stays for a person."""
import joblib
import numpy as np
from PIL import Image

from tools import decision_learning as dl
from tools import leaflet_mask_batch as mod
from tools.leaf_light import common
from tools.tests.test_leaflet_mask_batch import Scores


class Picky:
    """Confident only about the first item (by box x)."""
    def predict_proba(self, X):
        p = np.where(X[:, dl.MASK_FEATURES.index('box_w_log')] > 0, 0.2, 0.2)
        p[0] = 0.99
        return np.stack([1 - p, p], 1)


def _batch(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    session, labels = tmp_path / 's', tmp_path / 'l'
    session.mkdir(); labels.mkdir()
    Image.new('RGB', (120, 120), '#376f2d').save(session / 'photo.png')
    common.write_json(session / 'capture.json', dict(frames=[dict(image_file='photo.png', image_path='photo.png',
                                                                  sha256=common.file_hash(session / 'photo.png'))]))
    coco = dict(images=[dict(id=1, file_name='photo.png', width=120, height=120,
                             extra=dict(view_group='middle', transform=dict(type='original_pixels', original_size_px=[120, 120])))],
                categories=[dict(id=1, name='leaflet')],
                annotations=[dict(id=1, image_id=1, category_id=1, bbox=[15., 15., 70., 70.]),
                             dict(id=2, image_id=1, category_id=1, bbox=[20., 20., 60., 60.])])
    common.write_json(labels / 'original_pixel_labels.coco.json', coco)
    common.write_json(labels / 'mapping_report.json', dict(schema_version='plant-auto-labels-1', plant_id='dwt_77', session=str(session),
                                                           photos=[dict(prepared_frame='photo.png', mapped=True, alignment=None)]))
    common.write_json(labels / 'input_hashes.json', {str(session / 'capture.json'): common.file_hash(session / 'capture.json')})
    mod.prepare('dwt_77', labels, session, tmp_path / 'batch')
    b = mod.Batch(tmp_path / 'batch', Scores())
    b.run()
    return tmp_path / 'batch'


def test_model_accepts_only_confident_masks_and_leaves_the_rest(tmp_path, monkeypatch):
    batch = _batch(tmp_path, monkeypatch)
    rows = dl.batch_features(batch, 'dwt_77')
    assert len(rows) == 2 and all(r['review'] == 'unreviewed' for r in rows)
    assert set(dl.MASK_FEATURES) <= set(rows[0])
    joblib.dump(dict(model=Picky(), features=dl.MASK_FEATURES, auto_positive=0.9, auto_negative=-0.01), tmp_path / 'm.joblib')
    r = dl.apply_mask_model(batch, tmp_path / 'm.joblib', 'dwt_77')
    assert r['confident'] == 1 and r['accepted'] == 1 and r['left_for_person'] == 1
    items = [common.read_json(f) for f in sorted((batch / 'items').glob('*.json'))]
    assert sorted((i['review'], i.get('review_source')) for i in items) == [('accepted', 'auto_model'), ('unreviewed', None)]


def test_training_rows_exclude_automatic_answers(tmp_path, monkeypatch):
    batch = _batch(tmp_path, monkeypatch)
    mod.Batch(batch).auto_accept(only={'dwt_77_a1'}, source='auto_model')
    cfg = dict(plants={'dwt_77': dict(batch=str(batch))})
    monkeypatch.setattr(dl, 'ROOT', tmp_path.anchor and tmp_path)  # batch path above is absolute
    assert dl.mask_rows(cfg) == [], 'a model answer must never become a training label'


def test_score_sel_is_the_default_candidate_even_after_a_person_picked_another(tmp_path, monkeypatch):
    batch = _batch(tmp_path, monkeypatch)
    it = common.read_json(next((batch / 'items').glob('*.json')))
    meta = common.read_json(batch / 'cache' / it['cache_key'] / 'result.json')
    other = (meta['default_candidate'] + 1) % len(meta['scores'])
    it['selected_candidate'] = other
    common.write_json(batch / 'items' / f"{it['id']}.json", it)
    row = next(r for r in dl.batch_features(batch, 'dwt_77') if r['id'] == it['id'])
    assert row['score_sel'] == meta['scores'][meta['default_candidate']]
    assert 'neighbor_overlap_max' not in dl.MASK_FEATURES
