"""Detection-only area ratios do not depend on physical measurements or poses."""
from copy import deepcopy

import numpy as np
import pytest
from PIL import Image

from tools import detected_leaf_area as da
from tools.leaf_light import common


@pytest.fixture
def batch(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    root, session = tmp_path/'batch', tmp_path/'session'
    (root/'items').mkdir(parents=True)
    (root/'cache').mkdir()
    session.mkdir()
    for name in ('a.png', 'b.png'):
        Image.new('RGB', (8, 8)).save(session/name)
    common.write_json(session/'capture.json', dict(plant_id='p', session_id='s'))
    ids = ['leaf_10', 'leaf_2', 'leaf_3', 'other_view']
    common.write_json(root/'manifest.json', dict(schema_version='leaflet-mask-batch-1',
                      plant_id='p', session=str(session), ids=ids, organ_class='leaflet'))
    for name, count in zip(ids, (4, 6, 2, 9)):
        folder = root/'cache'/name
        folder.mkdir()
        # Deliberately disconnected foreground; counting includes every component.
        mask = np.zeros((3, 3), bool)
        mask.ravel()[[0, 2, 6, 8, 1, 3, 5, 7, 4][:count]] = True
        np.savez(folder/'logits.npz', logits=np.where(mask[None], 10., -10.))
        image = 'b.png' if name == 'other_view' else 'a.png'
        image_hash = common.file_hash(session/image)
        common.write_json(folder/'result.json', dict(crop_px=[1, 1, 4, 4], scores=[1.],
                          image_sha256=image_hash, logits_sha256=common.file_hash(folder/'logits.npz')))
        common.write_json(root/'items'/f'{name}.json', dict(id=name, plant_id='p',
                          image_file=image, image_path=image, image_sha256=image_hash,
                          image_size_px=[8, 8], source_bbox_xywh_px=[1, 1, 3, 3],
                          generation='ready', review='unreviewed', visibility='partial',
                          cache_key=name, selected_candidate=0, sensitivity=50, manual_rings=None))
    return root


def change(batch, name, **fields):
    path = batch/'items'/f'{name}.json'
    item = common.read_json(path)
    item.update(fields)
    common.write_json(path, item)


def test_real_cache_counts_and_image_scoped_reference(batch, tmp_path):
    before = {str(p):common.file_hash(p) for p in tmp_path.rglob('*') if p.is_file()}
    report = da.run(batch, tmp_path/'result')
    rows = report['rows']
    assert [r['relative_area'] for r in rows] == [1., 1.5, .5, 1.]
    assert [r['area_px2'] for r in rows] == [4, 6, 2, 9]
    assert rows[1]['reference_label_id'] == 'leaf_10'
    assert rows[-1]['reference_label_id'] == 'other_view'
    assert rows[0]['review'] == 'unreviewed' and rows[0]['visibility'] == 'partial'
    assert all('area_cm2' not in r for r in rows)
    assert report['physical_validation'] is False and report['new_inference'] is False
    assert all(common.file_hash(da.Path(p)) == h for p,h in before.items())
    assert len(common.rows(tmp_path/'result/relative_detected_leaf_areas.csv')) == 4


@pytest.mark.parametrize('fields,status', [({'review':'rejected'}, 'rejected'),
    ({'generation':'pending'}, 'mask_unavailable'), ({'mapping_error':'bad'}, 'mapping_error')])
def test_unavailable_first_is_never_replaced(batch, tmp_path, fields, status):
    change(batch, 'leaf_10', **fields)
    rows = da.run(batch, tmp_path/'result')['rows']
    assert rows[0]['observation_status'] == status
    assert all(r['relative_area'] is None for r in rows[:3])
    assert rows[-1]['relative_area'] == 1.


def test_zero_reference_and_missing_later(batch, tmp_path):
    change(batch, 'leaf_10', manual_raster=dict(shape=[3,3], intervals=[]))
    change(batch, 'leaf_2', generation='failed')
    rows = da.run(batch, tmp_path/'result')['rows']
    assert rows[0]['area_px2'] == 0 and rows[0]['manual_edit_present']
    assert rows[1]['area_px2'] is None
    assert all(r['ratio_status'] == 'reference_zero' for r in rows[:3])


def test_bbox_explicit_and_independent_of_masks(batch, tmp_path):
    change(batch, 'leaf_10', generation='pending', cache_key=None)
    change(batch, 'leaf_2', source_bbox_xywh_px=[1,1,6,3])
    rows = da.run(batch, tmp_path/'boxes', mode='bbox')['rows']
    assert rows[1]['relative_area'] == 2.
    assert rows[0]['area_px2'] == 9
    assert all(r['area_scope'] == 'detected_bbox' for r in rows)


def test_corrupt_cache_refused(batch, tmp_path):
    (batch/'cache/leaf_10/logits.npz').write_bytes(b'changed')
    with pytest.raises(common.StudyError, match='hash mismatch'):
        da.run(batch, tmp_path/'result')
    assert not (tmp_path/'result').exists()


def test_geometry_validation_and_mask_holes():
    item = dict(image_size_px=[10,10], source_bbox_xywh_px=[0,0,3,3])
    mask = np.ones((3,3), bool)
    mask[1,1] = False
    assert da.pixel_area(item, 'mask', mask, [0,0,3,3]) == 8
    assert da.pixel_area(item, 'bbox') == 9
    with pytest.raises(common.StudyError, match='original-resolution'):
        da.pixel_area(item, 'mask', mask, [0,0,6,6])
    bad = deepcopy(item); bad['source_bbox_xywh_px'] = [9,0,3,3]
    with pytest.raises(common.StudyError, match='outside'):
        da.pixel_area(bad, 'bbox')
