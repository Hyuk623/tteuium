"""Heavy-compute offload: a packed job run 'remotely' comes back as PC cache hits, and tampering is refused."""
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools import offload_job as oj, offload_remote as orm, organ_prelabel, leaflet_segmenter as seg
from tools.leaf_light import common
from tools.leaflet_segmenter import MaskCandidate


class Scores:
    calls = 0

    def __init__(self, *a, **k):
        self.config = dict(backend='sam2', model_name='fixture', checkpoint_sha256='x', model_config='c')

    def info(self):
        return dict(available=True, backend='sam2', model_name='fixture', model_config='c', checkpoint_sha256='x', is_mock=False)

    def predict_logits(self, rgb, box, positive, negative):
        Scores.calls += 1
        a = np.full(rgb.shape[:2], -8., np.float32)
        a[5:25, 5:25] = 8
        return [MaskCandidate(a > 0, .9, a)]


def fake_prelabel(models, images, out, *a, **k):
    out = Path(out); out.mkdir(parents=True)
    coco = dict(images=[], annotations=[], categories=[dict(id=2, name='leaflet'), dict(id=4, name='main_stem')], info={})
    for n, p in enumerate(images, 1):
        coco['images'].append(dict(id=n, file_name=Path(p).name, width=80, height=80))
        coco['annotations'].append(dict(id=2 * n - 1, image_id=n, category_id=2, bbox=[10., 10., 30., 30.], score=.9))
        coco['annotations'].append(dict(id=2 * n, image_id=n, category_id=4, bbox=[40., 5., 8., 60.], score=.8,
                                        segmentation=[[40., 5., 48., 5., 48., 65., 40., 65.]]))
    common.write_json(out / 'prelabels.coco.json', coco)
    return dict(out=str(out), images=len(images), boxes=len(coco['annotations']), per_class={'leaflet': len(images)})


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    session = tmp_path / 'session'
    (session / 'images').mkdir(parents=True)
    frames = []
    for code in ('24', '25'):
        name = f'dwt_77_20261001_{code}.png'
        Image.new('RGB', (80, 80), '#2f6a2a' if code == '24' else '#336d2e').save(session / 'images' / name)
        frames.append(dict(image_file=name, image_path=f'images/{name}', sha256=common.file_hash(session / 'images' / name),
                           view_code=code, observed_view_group='side', pose_status='solved', passes_pose_gate=False))
    common.write_json(session / 'capture.json', dict(plant_id='dwt_77', session_id='dwt_77_20261001', frames=frames,
                                                     intrinsics=dict(image_width_px=80, image_height_px=80)))
    weights = tmp_path / 'w'; weights.mkdir()
    det = weights / 'det.pt'; det.write_bytes(b'detector')
    ckpt = weights / 'sam.pt'; ckpt.write_bytes(b'sam')
    (weights / 'sam2pkg' / 'sam2').mkdir(parents=True); (weights / 'sam2pkg' / 'sam2' / 'sam2_image_predictor.py').write_text('')
    cfg = tmp_path / 'sam.json'
    common.write_json(cfg, dict(backend='sam2', model_name='fixture', checkpoint=str(ckpt), checkpoint_sha256=common.file_hash(ckpt),
                                model_config='c', repository=str(weights / 'sam2pkg')))
    monkeypatch.setattr(oj, 'pc_signature', lambda c: dict(model='fixture-signature'))
    monkeypatch.setattr(organ_prelabel, 'run', fake_prelabel)
    monkeypatch.setattr(seg, 'Sam2Segmenter', Scores)
    monkeypatch.setattr(seg, 'load_segmenter', lambda b, c: Scores())
    from tools import plant_auto
    monkeypatch.setattr(plant_auto, 'labels_from_prelabels', _labels_no_node(plant_auto.labels_from_prelabels))
    job = tmp_path / 'job'
    oj.pack({'dwt_77': session}, job, [det], cfg)
    return tmp_path, session, job, weights


def _labels_no_node(real):
    def wrapped(pre, capture, session, out, growth, seed=True):
        return real(pre, capture, session, out, growth, seed=False)  # Node.js is not needed for this check
    return wrapped


def test_remote_sam_results_are_pc_cache_hits(setup, monkeypatch):
    tmp, session, job, weights = setup
    from tools import leaflet_mask_batch as lmb
    monkeypatch.setattr(lmb.Batch, 'model_signature', lambda self: dict(model='fixture-signature'))
    result = orm.run(job, [weights], tmp / 'remote_out')
    assert result['plants']['dwt_77']['status'] == 'done' and result['plants']['dwt_77']['masks']['ready'] == 2
    remote_calls = Scores.calls
    rec = oj.import_result(job, tmp / 'remote_out', 'dwt_77', session, tmp / 'labels', tmp / 'batch')
    assert Scores.calls == remote_calls, 'the PC reused the remote SAM results instead of recomputing'
    assert rec['cache_entries_copied'] == 2 and rec['auto_accept'] == {'accepted': 2}


def test_tampered_or_foreign_results_are_refused(setup, monkeypatch):
    tmp, session, job, weights = setup
    from tools import leaflet_mask_batch as lmb
    monkeypatch.setattr(lmb.Batch, 'model_signature', lambda self: dict(model='fixture-signature'))
    orm.run(job, [weights], tmp / 'remote_out')
    coco = tmp / 'remote_out' / 'dwt_77' / 'prelabel' / 'prelabels.coco.json'
    coco.write_text(coco.read_text().replace('0.9', '0.1'))
    with pytest.raises(common.StudyError, match='changed or missing'):
        oj.import_result(job, tmp / 'remote_out', 'dwt_77', session, tmp / 'labels', tmp / 'batch')
    other = tmp / 'other_out'
    shutil.copytree(tmp / 'remote_out', other)
    r = json.loads((other / 'result.json').read_text()); r['job_id'] = 'someone-else'
    (other / 'result.json').write_text(json.dumps(r))
    with pytest.raises(common.StudyError, match='another job'):
        oj.import_result(job, other, 'dwt_77', session, tmp / 'labels2', tmp / 'batch2')


def test_weights_are_accepted_only_by_hash(tmp_path):
    (tmp_path / 'a').mkdir(); (tmp_path / 'a' / 'det.pt').write_bytes(b'other bytes')
    with pytest.raises(common.StudyError, match='not found'):
        orm.find_weights([dict(name='det.pt', sha256=common.file_hash(tmp_path / 'a' / 'det.pt')[:-1] + '0')], [tmp_path])
