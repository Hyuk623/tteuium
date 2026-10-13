"""Photometric invariants, source protection and derived-save semantics."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest
from PIL import Image

from tools import leaf_preprocess_lab as lab


def test_identity_is_bit_exact_and_changes_do_not_modify_original():
    rng = np.random.default_rng(41)
    rgb = rng.integers(0, 256, (61, 75, 3), dtype=np.uint8)
    snapshot = rgb.copy()
    assert np.array_equal(lab.enhance(rgb, lab.DEFAULTS), rgb)
    for preset in lab.PRESETS:
        assert lab.enhance(rgb, preset['settings']).shape == rgb.shape
    assert np.array_equal(rgb, snapshot)


def test_ratios_cancel_common_linear_gain_and_reject_zero():
    x = np.array([[[0.2, 0.3, 0.1], [0, 0, 0]]], dtype=np.float32)
    a, valid = lab.colour_ratios(x)
    b, _ = lab.colour_ratios(x * 0.4)
    assert np.allclose(a, b)
    assert valid.tolist() == [[True, False]]
    assert np.isfinite(a).all()


def test_dark_pixels_cannot_become_valid_by_brightening():
    rgb = np.zeros((65, 65, 3), np.uint8)
    mask = np.ones((65, 65), bool)
    result = lab.analyze(rgb, mask, dict(lab.DEFAULTS, ev=2, gamma=0.5))
    assert not result['valid'].any()
    assert result['evidence'].max() == 0
    assert np.isfinite(result['evidence']).all()


def test_new_clipping_is_not_treated_as_usable_brightness_evidence():
    rgb = np.full((65, 65, 3), 190, np.uint8)
    mask = np.ones((65, 65), bool)
    result = lab.analyze(rgb, mask, dict(lab.DEFAULTS, ev=2))
    assert result['stats']['processed_clipped_percent'] == 100
    assert not result['valid'].any()
    ratios = lab.analyze(rgb, mask, dict(lab.DEFAULTS, ev=2, feature='ratio'))
    assert ratios['valid'].any()  # original ratios are not altered by the exposure control


def test_ridges_are_visible_inside_mask_and_outside_is_excluded():
    rgb = np.full((120, 120, 3), 85, np.uint8)
    rgb[:, 58:62] = [170, 180, 150]
    mask = np.zeros((120, 120), bool); mask[10:110, 10:110] = True
    mask_before = mask.copy()
    result = lab.analyze(rgb, mask, dict(lab.DEFAULTS, feature='brightness'))
    assert result['evidence'][35:85, 56:64].max() > 0.5
    assert result['evidence'][~mask].max() == 0
    assert not result['valid'][10:15].any()
    assert np.array_equal(mask, mask_before)


@pytest.mark.parametrize('cfg', [{'ev':float('nan')}, {'gamma':0}, {'width':500}, {'feature':'unknown'}, {'other':1}])
def test_settings_bounds(cfg):
    with pytest.raises(ValueError):
        lab.settings(cfg)


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    # Isolate the lab while exercising real source hashing, crops and saves.
    monkeypatch.setattr(lab, 'assert_build', lambda path: path.resolve())
    src = tmp_path / 'session'; src.mkdir()
    y, x = np.indices((120, 140))
    rgb = np.stack([40+x, 60+y, np.full_like(x, 70)], axis=2).astype(np.uint8)
    image = src / 'photo.png'; Image.fromarray(rgb).save(image)
    mask = np.zeros((120, 140), np.uint8); mask[45:80, 70:100] = 255; mask[55:59, 80:83] = 0
    export = tmp_path / 'export'; export.mkdir()
    Image.fromarray(mask).save(export / 'mask.png')
    lab.write_json(src / 'capture.json', dict(frames=[dict(image_file='photo.png',image_path='photo.png',sha256=lab.sha(image))]))
    obs = dict(id='obs1',plant_id='dwt_test',source_annotation_id=9,image_file='photo.png',image_sha256=lab.sha(image),
        image_size_px=[140,120],mask_file='mask.png',mask_area_px=int((mask>0).sum()),review='accepted_by_user',
        image_provenance=dict(view_group='side'))
    accepted=export/'accepted.json'
    lab.write_json(accepted,dict(schema_version='accepted-leaflet-masks-1',observations=[obs]))
    root=tmp_path/'run'
    doc=lab.prepare([accepted],[src],root)
    return lab.Lab(root),rgb,mask,doc


def test_crop_roundtrip_and_mask_holes_preserved(pilot):
    app,rgb,mask,doc=pilot
    item=doc['samples'][0]; x0,y0,x1,y1=item['crop_xyxy_px']
    image,cutmask=app.load(item['id'])
    assert np.array_equal(image,rgb[y0:y1,x0:x1])
    assert np.array_equal(cutmask,mask[y0:y1,x0:x1]>0)
    assert item['transform']['offset_x_px']==x0 and item['transform']['scale_x']==1
    assert not cutmask[56-y0,81-x0]


def test_saves_are_new_and_not_accepted_landmarks(pilot):
    app,_,_,doc=pilot
    source_hashes={p:lab.sha(__import__('pathlib').Path(p)) for p in doc['sources']}
    first=app.save('sample_000',lab.DEFAULTS,'unreviewed','test fixture')
    second=app.save('sample_000',dict(lab.DEFAULTS,ev=0.5),'easier','human preference only')
    assert first['path']!=second['path']
    assert not second['record']['physical_point_identity_confirmed']
    assert not second['record']['new_depth_information']
    assert not second['record']['suitable_for_ppfd']
    assert all(lab.sha(__import__('pathlib').Path(p))==h for p,h in source_hashes.items())


def test_source_edit_blocks_save(pilot):
    app,*_=pilot
    r=app.samples['sample_000']
    __import__('pathlib').Path(r['source_mask']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):
        app.save('sample_000',lab.DEFAULTS,'unreviewed','')


def test_http_blocks_foreign_requests_and_roundtrips_preview(pilot):
    app,*_=pilot
    server=ThreadingHTTPServer(('127.0.0.1',0),lab.handler(app))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}'
    data=json.dumps(dict(sample_id='sample_000',settings=lab.DEFAULTS)).encode()
    try:
        for extra in ({}, {'X-Lab-Token':app.token,'Origin':'https://example.com'}):
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(urllib.request.Request(url+'/api/save',data,extra))
            assert exc.value.code==403
        req=urllib.request.Request(url+'/api/render',data,{'X-Lab-Token':app.token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as response: result=json.load(response)
        assert result['images']['original'].startswith('data:image/png;base64,')
        assert result['settings']==lab.DEFAULTS
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)


def test_full_green_fraction_uses_whole_stored_rgb_without_mask():
    rgb = np.array([[[0, 255, 0], [255, 0, 0], [0, 0, 0]],
                    [[100, 100, 100], [10, 20, 30], [20, 40, 60]]], dtype=np.uint8)
    before = rgb.copy()
    ratio, display = lab.full_green_fraction(rgb)
    assert ratio.shape == rgb.shape[:2] and display.shape == rgb.shape
    np.testing.assert_allclose(ratio[0, :2], [1, 0])
    assert np.isnan(ratio[0, 2])
    np.testing.assert_allclose(ratio[1], [1/3, 1/3, 1/3])
    np.testing.assert_array_equal(display[0, 2], [255, 0, 255])
    np.testing.assert_array_equal(rgb, before)


@pytest.mark.parametrize('channel,index', [('red',0),('green',1),('blue',2)])
def test_full_channel_fraction(channel, index):
    rgb = np.array([[[60, 120, 20], [0, 0, 0]]], dtype=np.uint8)
    ratio, display = lab.full_channel_fraction(rgb, channel)
    assert ratio[0,0] == pytest.approx(float(rgb[0,0,index]) / 200)
    assert np.isnan(ratio[0,1])
    assert display.shape == rgb.shape
    np.testing.assert_array_equal(display[0,1], [255,0,255])


def test_reviewed_mask_preserves_channel_values_and_holes():
    rgb = np.arange(27, dtype=np.uint8).reshape(3,3,3)
    mask = np.ones((3,3), bool); mask[1,1] = False
    before = rgb.copy()
    result = lab.apply_reviewed_mask(rgb, mask)
    np.testing.assert_array_equal(result[...,:3], before)
    np.testing.assert_array_equal(result[...,3], mask.astype(np.uint8)*255)
    assert result[1,1,3] == 0
    np.testing.assert_array_equal(rgb, before)
    with pytest.raises(ValueError):
        lab.apply_reviewed_mask(rgb, np.ones((2,2), bool))
