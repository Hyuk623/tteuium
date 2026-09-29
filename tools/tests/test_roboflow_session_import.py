"""Roboflow export labels into a prepared session: validated transform, provenance, scope and accounting.

Synthetic photos only. An export is accepted only when its pixels show an uncropped stretch of the
prepared frame at the same orientation; everything else keeps its 2D labels and stays out of geometry.
"""
import json
import shutil

import numpy as np
import pytest
from PIL import Image

from tools import roboflow_session_import as tool
from tools.leaf_light.common import file_hash, write_json

SIZE, EXPORT = 300, 64
needs_node = pytest.mark.skipif(not shutil.which('node'), reason='Node.js runs the editor import code')


def texture(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    small = Image.fromarray((rng.random((24, 24, 3)) * 255).astype('uint8'))
    return small.resize((SIZE, SIZE), Image.Resampling.BICUBIC)


def export_of(image: Image.Image, how: str = 'identity') -> Image.Image:
    if how == 'rot90':
        image = image.transpose(Image.Transpose.ROTATE_90)
    elif how == 'flip':
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif how == 'crop':
        image = image.crop((30, 30, SIZE, SIZE))
    return image.resize((EXPORT, EXPORT), Image.Resampling.BILINEAR)


@pytest.fixture
def world(tmp_path):
    """A prepared session (views 11-15) and a grouped package whose exports are variously transformed."""
    session = tmp_path / 'session'
    (session / 'images').mkdir(parents=True)
    frames, originals = [], {}
    for i, view in enumerate(('11', '12', '13', '14', '15')):
        name = f'dwt_09_20260920_{view}.png'
        texture(i).save(session / 'images' / name)
        originals[view] = texture(i)
        frames.append(dict(image_file=name, view_code=view, image_path=f'images/{name}',
                           sha256=file_hash(session / 'images' / name), pose_status='too_few_corners',
                           passes_pose_gate=False, source_path=f'photos\\260920\\dwt_09\\dwt_09_260920_{view}.heic'))
    capture = dict(plant_id='dwt_09', session_id='dwt_09_20260920',
                   intrinsics=dict(image_width_px=SIZE, image_height_px=SIZE), frames=frames)
    write_json(session / 'capture.json', capture)
    write_json(session / 'seed.backup.json', dict(plant_id='dwt_09', session_id='dwt_09_20260920', capture={},
                                                  variants={'__all__': dict(leaflets={}, boxes={})}))
    for name in ('intrinsics.json', 'annotations.source.json', 'session_report.json'):
        write_json(session / name, {})
    folder = tmp_path / 'package' / 'dwt_09' / '260920' / 'side'
    folder.mkdir(parents=True)
    plan = {'11': ('11', 'identity'), '12': ('12', 'rot90'), '13': ('13', 'flip'), '14': ('14', 'crop'),
            '15': ('11', 'identity')}  # view 15's export is really a photo of view 11
    images, annotations = [], []
    for n, (view, (source, how)) in enumerate(plan.items(), start=1):
        name = f'dwt_09_260920_{view}.jpg'
        export_of(originals[source], how).save(folder / name, quality=95)
        images.append(dict(id=n, file_name=name, width=EXPORT, height=EXPORT, extra=dict(name=name),
                           source_export=dict(archive='a.zip', split='train', image_id=100 + n)))
        annotations.append(dict(id=2 * n - 1, image_id=n, category_id=1, bbox=[10.5, 12.25, 20.0, 8.0],
                                segmentation=[[10.5, 12.25, 30.5, 12.25, 30.5, 20.25, 10.5, 20.25]],
                                source_export=dict(annotation_id=500 + n)))
        annotations.append(dict(id=2 * n, image_id=n, category_id=2, bbox=[5.0, 5.0, 3.0, 40.0],
                                segmentation=[[5.0, 5.0, 8.0, 5.0, 7.0, 45.0, 5.5, 44.0]]))
    images.append(dict(id=9, file_name='dwt_08_260920_11.jpg', width=EXPORT, height=EXPORT))  # another plant
    export_of(originals['11']).save(folder / 'dwt_08_260920_11.jpg')
    annotations.append(dict(id=99, image_id=9, category_id=1, bbox=[1, 1, 5, 5], segmentation=[]))
    write_json(folder / '_annotations.coco.json', dict(
        images=images, annotations=annotations,
        categories=[dict(id=0, name='tom-seg-bbox-side'), dict(id=1, name='compound_leaves'), dict(id=2, name='sub_stem')]))
    return dict(session=session, package=tmp_path / 'package', out=tmp_path / 'out', originals=originals)


def test_only_an_uncropped_same_orientation_stretch_is_accepted(world):
    reasons = {}
    for view in ('11', '12', '13', '14', '15'):
        check = tool.alignment(world['package'] / 'dwt_09' / '260920' / 'side' / f'dwt_09_260920_{view}.jpg',
                               world['session'] / 'images' / f'dwt_09_20260920_{view}.png')
        reasons[view] = (check['accepted'], check['reasons'])
    assert reasons['11'] == (True, [])
    assert not reasons['12'][0] and any(r.startswith('best_orientation_is_') for r in reasons['12'][1])
    assert not reasons['13'][0] and any(r.startswith('best_orientation_is_') for r in reasons['13'][1])
    assert not reasons['14'][0]  # a crop shifts and rescales the content
    assert not reasons['15'][0] and 'correlation_below_minimum' in reasons['15'][1]


def test_coordinates_scale_by_measured_sizes_and_round_trip():
    transform = tool.stretch_transform([64, 64], [300, 150])
    out = tool.convert_annotation(dict(bbox=[10.5, 12.25, 20.0, 8.0], segmentation=[[10.5, 12.25, 30.5, 20.25]],
                                       area=160.0), transform)
    assert out['bbox'] == [10.5 * 300 / 64, 12.25 * 150 / 64, 20.0 * 300 / 64, 8.0 * 150 / 64]
    assert out['segmentation'][0] == [10.5 * 300 / 64, 12.25 * 150 / 64, 30.5 * 300 / 64, 20.25 * 150 / 64]
    assert transform['scale_x'] != transform['scale_y'] and transform['coordinate_convention'] == 'pixel_edges'


@needs_node
def test_plant_import_keeps_every_label_and_its_provenance(world):
    before = {p: file_hash(p) for p in world['session'].rglob('*') if p.is_file()}
    report = tool.import_plant('dwt_09', world['package'], world['session'], world['out'])
    # Accounting closes: 10 labels for this plant, 2 mapped (view 11), 8 kept unmapped; other plant excluded.
    assert report['source_annotations'] == 11
    assert report['mapped_photos'] == 1 and report['mapped_annotations'] == 2
    unmapped = json.loads((world['out'] / 'unmapped_export_labels.json').read_text(encoding='utf-8'))['photos']
    assert {u['export_file']: u['reason'] for u in unmapped} == {
        'dwt_09_260920_12.jpg': 'alignment_rejected', 'dwt_09_260920_13.jpg': 'alignment_rejected',
        'dwt_09_260920_14.jpg': 'alignment_rejected', 'dwt_09_260920_15.jpg': 'alignment_rejected',
        'dwt_08_260920_11.jpg': 'different_plant'}
    assert sum(len(u['annotations']) for u in unmapped) == 9
    coco = json.loads((world['out'] / 'original_pixel_labels.coco.json').read_text(encoding='utf-8'))
    first = coco['annotations'][0]
    assert first['bbox'][0] == pytest.approx(10.5 * SIZE / EXPORT)
    assert first['provenance']['source_class_name'] == 'compound_leaves'
    assert first['provenance']['source_export'] == dict(annotation_id=501)
    assert coco['images'][0]['file_name'] == 'dwt_09_20260920_11.png'
    # The seed was built by the editor's own import: aliases applied, provenance and transform kept.
    seed = json.loads((world['out'] / 'seed_with_imports.backup.json').read_text(encoding='utf-8'))
    detections = seed['variants']['__all__']['membership']['detections']['dwt_09_20260920_11.png']
    assert sorted(d['class_name'] for d in detections) == ['compoundleaves', 'sub-stem']
    assert all(d['source']['transform']['type'] == 'uncropped_stretch' for d in detections)
    assert {d['source']['provenance']['source_class_name'] for d in detections} == {'compound_leaves', 'sub_stem'}
    assert seed['variants']['__all__']['leaflets'] == {}  # no identity is invented
    # Sources untouched, and a second run refuses to overwrite.
    assert before == {p: file_hash(p) for p in world['session'].rglob('*') if p.is_file()}
    with pytest.raises(tool.StudyError, match='not empty'):
        tool.import_plant('dwt_09', world['package'], world['session'], world['out'])


@needs_node
def test_repeating_the_import_on_its_own_output_adds_nothing(world, tmp_path):
    tool.import_plant('dwt_09', world['package'], world['session'], world['out'])
    capture = json.loads((world['session'] / 'capture.json').read_text(encoding='utf-8'))
    again = tool.seed_with_imports(world['out'] / 'seed_with_imports.backup.json',
                                   world['out'] / 'original_pixel_labels.coco.json', capture, None, tmp_path / 'again.json')
    assert again['imported'] == 0 and again['duplicates'] == 2


def test_a_session_of_another_plant_is_refused(world):
    with pytest.raises(tool.StudyError, match='belongs to dwt_09'):
        tool.import_plant('dwt_01', world['package'], world['session'], world['out'])


# --- F1 regression: a small centred crop keeps a high global correlation but is not an uncropped stretch ---
def detailed(seed: int, size: int = 1512) -> Image.Image:
    rng = np.random.default_rng(seed)
    layers = [Image.fromarray((rng.random((n, n, 3)) * 255).astype('uint8')).resize((size, size), Image.Resampling.BICUBIC)
              for n in (20, 60)]
    return Image.blend(layers[0], layers[1], 0.5)


@pytest.mark.parametrize('crop, accepted', [((0, 0, 0, 0), True), ((10, 10, 10, 10), False), ((20, 20, 20, 20), False),
                                            ((15, 0, 0, 0), False), ((0, 0, 0, 12), False)])
def test_centred_or_one_sided_crop_is_rejected_and_jpeg_control_passes(tmp_path, crop, accepted):
    original = detailed(3)
    original.save(tmp_path / 'original.png')
    left, top, right, bottom = crop
    fixture = original.crop((left, top, original.width - right, original.height - bottom)).resize((640, 640), Image.Resampling.BILINEAR)
    fixture.save(tmp_path / 'export.jpg', quality=90)
    result = tool.alignment(tmp_path / 'export.jpg', tmp_path / 'original.png')
    assert result['accepted'] is accepted, result['reasons']
    if not accepted:
        assert result['reasons'] and result['max_corner_shift_export_px'] > tool.MAX_CORNER_SHIFT_PX or \
            any(r.startswith('best_offset') for r in result['reasons'])
    else:
        assert result['max_corner_shift_export_px'] < 0.2


def test_centred_crop_is_caught_by_the_corner_check_not_the_global_one(tmp_path):
    original = detailed(5)
    original.save(tmp_path / 'original.png')
    original.crop((10, 10, original.width - 10, original.height - 10)).resize((640, 640), Image.Resampling.BILINEAR).save(tmp_path / 'e.jpg', quality=95)
    result = tool.alignment(tmp_path / 'e.jpg', tmp_path / 'original.png')
    assert result['identity_correlation'] > tool.MIN_ALIGNMENT_CORRELATION and result['best_offset_export_px'] == [0, 0]
    assert result['reasons'] == ['corner_shift_indicates_crop_or_rescale']


def test_featureless_corners_fail_closed(tmp_path):
    flat = Image.new('RGB', (1512, 1512), (90, 140, 60))
    flat.paste(detailed(7, 500), (506, 506))
    flat.save(tmp_path / 'original.png')
    flat.resize((640, 640), Image.Resampling.BILINEAR).save(tmp_path / 'e.jpg', quality=95)
    result = tool.alignment(tmp_path / 'e.jpg', tmp_path / 'original.png')
    assert not result['accepted'] and 'corner_check_inconclusive' in result['reasons']
