from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools import instance_workflow as w
from tools import leaflet_mask_batch as masks
from tools.leaf_light import common
from tools.tests.test_leaflet_mask_batch import batch, action  # noqa: F401


def test_brush_preserves_small_regions_and_undo_without_inference(batch):
    b, _, _ = batch; b.run(); identity = b.manifest['ids'][0]
    original = b.mask(b.item(identity))[0].copy(); calls = b.segmenter.calls
    action(b, 'brush', strokes=[dict(mode='paint', radius_px=2, points_px=[[100, 30], [105, 30]]),
                              dict(mode='erase', radius_px=2, points_px=[[25, 25]])])
    current = b.mask(b.item(identity))[0]
    assert current[30, 102] and not current[25, 25] and current[90, 90] and not current[36,36]
    assert b.item(identity)['review'] == 'edited' and b.segmenter.calls == calls
    reloaded = masks.Batch(b.root)
    assert np.array_equal(reloaded.mask(reloaded.item(identity))[0], current)
    action(b, 'accept'); exported = b.export()
    assert np.asarray(Image.open(Path(exported['path'])/f'{identity}.png'))[30,102] == 255
    action(b, 'undo'); action(b, 'undo')
    assert np.array_equal(original, b.mask(b.item(identity))[0])
    assert b.segmenter.calls == calls


def test_brush_original_coordinates_clipping_and_lossless_raster():
    base = np.zeros((30,40), bool);base[0,0] = True
    changed = masks.brush_mask(base,[100,200,140,230],[dict(mode='paint',radius_px=2,points_px=[[110,210]])])
    assert changed[10,10] and changed[0,0] and not changed[20,20]
    assert np.array_equal(masks.unpack_mask(masks.pack_mask(changed), changed.shape), changed)
    with pytest.raises(common.StudyError, match='inside'):
        masks.brush_mask(base,[100,200,140,230],[dict(mode='erase',radius_px=2,points_px=[[99,210]])])


def test_snapshot_cached_sweep_preserves_settings_and_stale_on_edits(batch, tmp_path):
    b, _, _ = batch; b.run(); action(b,'select',sensitivity=71)
    settings = common.read_json(w.DEFAULTS)
    cap = common.read_json(b.session/'capture.json')
    cap.update(plant_id='dwt_01', session_id='S')
    cap['frames'][0].update(view_code='11', pose_status='failed')
    backup = dict(plant_id='dwt_01', session_id='S', variants={'__all__':{'leaflets':{}}})
    out=tmp_path/'snapshot';out.mkdir()
    before = {p: common.file_hash(p) for p in (b.root/'items').glob('*.json')}
    obs, raster, sig, hashes = w.snapshot(b,backup,cap,out,'sensitivity_sweep','pilot',settings)
    assert len(obs)==2 and all(o['leaf_key'] is None for o in obs)
    calls = b.segmenter.calls
    result = w.sensitivity_sweep(out,obs,{},settings,True)
    assert 71 in result['sensitivity_values'] and result['evaluated_photos']==0
    assert result['metric_status'].startswith('unavailable') and b.segmenter.calls==calls
    assert before=={p:common.file_hash(p) for p in before}
    common.write_json(out/'manifest.json',dict(input_signature=sig,source_hashes=hashes))
    assert w.stale_reasons(out,b,backup)==[]
    action(b,'defer')
    assert 'items' in w.stale_reasons(out,b,backup)
    new = deepcopy(backup);new['variants']['__all__']['leaflets']={'other':{}}
    assert 'backup' in w.stale_reasons(out,b,new)


def test_reference_coverage_eval_and_dwt02_freeze_gate(batch,tmp_path):
    b,_,_=batch;b.run()
    settings = common.read_json(w.DEFAULTS)
    cap=common.read_json(b.session/'capture.json');cap.update(plant_id='dwt_01',session_id='S')
    cap['frames'][0].update(view_code='11',pose_status='failed')
    backup=dict(variants={'__all__':{'leaflets':{}}})
    out=tmp_path/'snap';out.mkdir()
    obs,_,_,_=w.snapshot(b,backup,cap,out,'sensitivity_sweep','pilot',settings)
    # Independently constructed visible reference, not a prediction used as target.
    reference=dict(schema_version='instance-visible-reference-1',plant_id='dwt_01',session_id='S',version='1',reviewer='synthetic test',
        independent_manual_review=True,photos=[dict(image_file='photo.png',image_sha256=cap['frames'][0]['sha256'],coverage='complete_visible',
        instances=[dict(reference_id='a',visibility='full',origin='independent_manual',rings=[dict(points_px=[[20,20],[69,20],[69,69],[20,69]])])])])
    checked=w.validate_reference(reference,cap)
    result=w.sensitivity_sweep(out,obs,checked,settings,True)
    assert result['evaluated_photos']==1 and all(r['fp']>=1 for r in result['comparison'])
    assert w.sensitivity_sweep(out,obs,checked,settings,False)['evaluated_photos']==0
    checked['photo.png']['coverage']='incomplete'
    assert w.sensitivity_sweep(out,obs,checked,settings,True)['evaluated_photos']==0


def test_freeze_is_versioned_and_cannot_overwrite(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    root=tmp_path/'runs';root.mkdir();dev=root/'dev';dev.mkdir()
    common.write_json(dev/'manifest.json',dict(plant_id='dwt_01',settings=common.read_json(w.DEFAULTS)))
    common.write_json(dev/'result.json',dict(operation='sensitivity_sweep',evaluated_photos=0))
    frozen=w.freeze_parameters(dev,root/'frozen.json')
    assert frozen['validation']=='exploratory_unvalidated' and frozen['settings_sha256']==common.digest(frozen['settings'])
    with pytest.raises(common.StudyError,match='already exists'):
        w.freeze_parameters(dev,root/'frozen.json')
