"""Calculate image-space first-label area ratios from saved detections, without inference.

python -m tools.detected_leaf_area --batch build/.../masks --out build/fresh_ratios
Use --mode bbox explicitly for box occupancy ratios instead of visible-mask ratios.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json, write_rows
from tools.leaflet_mask_batch import Batch
from tools.relative_leaf_area import GROUP, normalize
from tools.leaf_mask_selection import load_selection

EXTRA = ('organ_class', 'source_annotation_id', 'generation', 'review', 'visibility',
         'observation_status', 'manual_edit_present', 'image_sha256', 'exclusion_reason')
COLUMNS = (*GROUP, 'label_id', 'area_px2', 'reference_label_id', 'reference_area_px2',
           'relative_area', 'ratio_status', *EXTRA)


def pixel_area(item: dict, mode: str, mask: np.ndarray | None = None,
               crop_px: list | None = None) -> float:
    """Count original-resolution foreground or explicitly selected box occupancy."""
    width_px, height_px = item['image_size_px']
    if width_px <= 0 or height_px <= 0:
        raise StudyError('Invalid original image size')
    if mode == 'bbox':
        box = np.asarray(item['source_bbox_xywh_px'], dtype=float)
        if box.shape != (4,) or not np.isfinite(box).all():
            raise StudyError('Invalid original-pixel box')
        x_px, y_px, w_px, h_px = box
        if not (0 <= x_px <= x_px+w_px <= width_px and
                0 <= y_px <= y_px+h_px <= height_px):
            raise StudyError('Box outside original image')
        return float(w_px*h_px)
    if mode != 'mask':
        raise StudyError('Unknown detection area mode')
    if (crop_px is None or len(crop_px) != 4 or
            any(type(v) is not int for v in crop_px)):
        raise StudyError('Original-pixel crop required')
    x0, y0, x1, y1 = crop_px
    if (mask is None or mask.dtype != np.bool_ or
            mask.shape != (y1-y0, x1-x0) or
            not (0 <= x0 < x1 <= width_px and 0 <= y0 < y1 <= height_px)):
        raise StudyError('Mask must match the original-resolution crop')
    return float(np.count_nonzero(mask))


def run(batch_path: Path, out: Path, mode: str = 'mask', selection_path: Path | None = None) -> dict:
    if mode not in ('mask', 'bbox'):
        raise StudyError('Choose mask or bbox')
    hashes: dict[str, str] = {}

    def track(path: Path, expected: str | None = None) -> Path:
        path = path.resolve()
        actual = file_hash(path)
        if (expected is not None and actual != expected) or (
                str(path) in hashes and hashes[str(path)] != actual):
            raise StudyError(f'Source hash mismatch: {path}')
        hashes[str(path)] = actual
        return path

    root = batch_path.resolve()
    track(root/'manifest.json')
    batch = Batch(root)
    manifest = batch.manifest
    capture = read_json(track(batch.session/'capture.json'))
    if capture.get('plant_id') != manifest['plant_id'] or not capture.get('session_id'):
        raise StudyError('Batch/capture identity mismatch')
    selection = load_selection(selection_path, batch, capture, track)
    organ = manifest.get('organ_class', 'leaflet')
    if organ not in ('leaflet', 'compoundleaves'):
        raise StudyError('Expected a leaf detection batch')
    if manifest.get('source_coco'):
        track(Path(manifest['source_coco']), manifest.get('source_coco_sha256'))
    records, provenance = [], {}
    image_sizes: dict[str, tuple[int, int]] = {}
    scope = 'detected_visible_mask' if mode == 'mask' else 'detected_bbox'
    for identity in manifest['ids']:
        track(root/'items'/f'{identity}.json')
        item = batch.item(identity)
        if item['id'] != identity or item['plant_id'] != manifest['plant_id']:
            raise StudyError('Detection identity mismatch')
        if item.get('organ_class', organ) != organ:
            raise StudyError('Mixed organ classes')
        key = item['image_file']
        if not isinstance(key, str) or not key:
            raise StudyError('Explicit image identity required')
        record = dict(plant_id=manifest['plant_id'], session_id=capture['session_id'],
                      capture_date=capture.get('capture_date'),
                      area_method=f'saved_{organ}_{mode}_pixels', area_scope=scope,
                      view_id=key, label_id=identity, area_px2=None)
        status = 'available'
        if identity in selection['excluded']:
            status = 'excluded_by_observation_review'
        elif item.get('mapping_error'):
            status = 'mapping_error'
        elif item.get('review') == 'rejected':
            status = 'rejected'
        elif mode == 'mask' and (item.get('generation') != 'ready' or not item.get('cache_key')):
            status = 'mask_unavailable'
        else:
            image_path = (batch.session/item['image_path']).resolve()
            if not image_path.is_relative_to(batch.session.resolve()):
                raise StudyError('Image outside batch session')
            track(image_path, item['image_sha256'])
            if key not in image_sizes:
                with Image.open(image_path) as picture:
                    if picture.getexif().get(274, 1) != 1:
                        raise StudyError('Original image orientation is not normalized')
                    image_sizes[key] = picture.size
            if list(image_sizes[key]) != item['image_size_px']:
                raise StudyError('Detection/original image size mismatch')
            if mode == 'mask':
                cache = root/'cache'/item['cache_key']
                meta = read_json(track(cache/'result.json'))
                if meta.get('image_sha256') != item['image_sha256']:
                    raise StudyError('Mask belongs to another image')
                track(cache/'logits.npz', meta['logits_sha256'])
                mask, meta = batch.mask(item)
                record['area_px2'] = pixel_area(item, mode, mask, meta['crop_px'])
            else:
                record['area_px2'] = pixel_area(item, mode)
            if record['area_px2'] == 0:
                status = 'empty'
        records.append(record)
        provenance[(key, identity)] = dict(
            organ_class=organ, source_annotation_id=item.get('source_annotation_id'),
            generation=item.get('generation'), review=item.get('review'), visibility=item.get('visibility'),
            observation_status=status,
            manual_edit_present=item.get('manual_rings') is not None or item.get('manual_raster') is not None,
            image_sha256=item.get('image_sha256'), exclusion_reason=selection['excluded'].get(identity))
    result = [dict(r, **provenance[(r['view_id'], r['label_id'])])
              for r in normalize(records, area_column='area_px2')]
    for code in (__file__, Batch.__module__.replace('.', '/')+'.py',
                 'tools/relative_leaf_area.py', 'tools/leaf_mask_selection.py', 'tools/leaf_light/common.py'):
        path = Path(code)
        track(path if path.is_absolute() else Path(__file__).resolve().parents[1]/path)
    for name, expected in hashes.items():
        if file_hash(Path(name)) != expected:
            raise StudyError(f'Source changed during calculation: {name}')
    folder = output_dir(out)
    write_rows(folder/'relative_detected_leaf_areas.csv', result, COLUMNS)
    report = dict(schema='detected-leaf-area-1', batch=str(root), mode=mode,
                  mask_selection=selection,
                  source_hashes=hashes, source_hashes_verified=True,
                  formula='relative_area = area_px2 / reference_area_px2',
                  reference_rule='first manifest label per image; unavailable references are not replaced',
                  area_units='original-image pixel squared', ratio_units='dimensionless',
                  identity_scope='per-image annotation; no inferred cross-view physical identity',
                  physical_validation=False, new_inference=False,
                  limitation='Visible image-area ratio includes viewpoint, depth, occlusion and detection errors. '
                             'BBox mode measures box occupancy, not leaf tissue. No metric area or 3D is inferred.',
                  rows=result)
    write_json(folder/'audit.json', report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('mask', 'bbox'), default='mask')
    parser.add_argument('--selection', type=Path, help='Hashed observed-annotation exclusion policy; source labels stay unchanged.')
    args = parser.parse_args()
    report = run(args.batch, args.out, args.mode, args.selection)
    print(dict(rows=len(report['rows']), computed=sum(r['ratio_status']=='computed' for r in report['rows']),
               mode=report['mode'], ratio_units=report['ratio_units']))


if __name__ == '__main__':
    main()
