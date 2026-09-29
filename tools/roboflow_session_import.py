"""Bring grouped Roboflow COCO labels for one plant into its prepared editor session.

The Roboflow export photos are auto-oriented and stretched copies of the originals. A label is moved
to original pixels only after the export photo is shown, from its pixels, to be an uncropped stretch of
the prepared frame at the same orientation; photos that fail keep their 2D labels in an unmapped file
and stay out of geometry. Nothing here creates a leaflet identity, a physical point or a pose.

  python -m tools.roboflow_session_import --plant dwt_01 \\
      --package build/roboflow_dataset_review_20260922/by_plant \\
      --session build/new_captures_20260920/dwt_01/edit_session \\
      --growth tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json \\
      --out build/dwt_01_02_3d_20260922/dwt_01

Outputs in --out: input_hashes.json, original_pixel_labels.coco.json, unmapped_export_labels.json,
mapping_report.json, mapping_table.csv, overlays/<frame>.jpg and seed_with_imports.backup.json (the
prepared seed plus the imported detections, made by the editor's own import code).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path, PureWindowsPath

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

# Acceptance rules for an export photo being an uncropped stretch of the prepared frame.
#: Minimum normalised correlation between the export and the prepared frame stretched to export size.
MIN_ALIGNMENT_CORRELATION = 0.90
#: The identity orientation must beat every other flip/rotation by at least this correlation margin.
MIN_ORIENTATION_MARGIN = 0.10
#: Integer offsets (export pixels) searched to detect a crop or shift; the best must be (0, 0).
SHIFT_SEARCH_PX = 3
#: Gaussian blur radius (export pixels) applied to both images before comparison (JPEG/resampling noise).
COMPARISON_BLUR_PX = 1.0
#: Side of each corner tile, as a fraction of the export width/height, for the local crop/scale check.
CORNER_TILE_FRACTION = 0.3
#: Largest allowed sub-pixel shift of any corner tile (export pixels). A symmetric crop or rescale moves
#: the corners apart even when the global correlation stays high; 30 verified exports measured <= 0.11 px,
#: a 10 px border crop of a 3024 px original measures ~1.5 px.
MAX_CORNER_SHIFT_PX = 0.5
#: Phase-correlation peak below which a corner tile is too featureless to judge (the check then fails).
MIN_CORNER_RESPONSE = 0.3
#: Grey-level standard deviation below which a corner tile has no texture to measure a shift from.
MIN_CORNER_TEXTURE_STD = 2.0
#: Largest allowed coordinate error after converting to original pixels and back (export pixels).
ROUND_TRIP_TOLERANCE_PX = 1e-9
EXPORT_NAME = re.compile(r'^(?P<plant>[A-Za-z0-9]+_\d+)_(?P<date>\d{6})_(?P<view>\d{2})\.jpe?g$', re.IGNORECASE)
NODE_HELPER = Path(__file__).with_name('annotator_import_coco.cjs')
OVERLAY_WIDTH_PX = 1512
CLASS_COLOURS = {'compond_leaf': (155, 227, 107), 'compound_leaves': (155, 227, 107), 'leaflet': (79, 209, 255),
                 'sub_stem': (255, 143, 208), 'main_stem': (201, 163, 107), 'shoot': (255, 209, 92),
                 'growth_shoot': (255, 209, 92)}


def _grey(image: Image.Image, size: tuple[int, int] | None = None) -> np.ndarray:
    image = image.convert('L')
    if size and image.size != size:
        image = image.resize(size, Image.Resampling.BILINEAR, reducing_gap=3.0)
    return np.asarray(image.filter(ImageFilter.GaussianBlur(COMPARISON_BLUR_PX)), dtype=float)


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a - a.mean(), b - b.mean()
    denominator = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / denominator) if denominator else 0.0


ORIENTATIONS = {'identity': lambda a: a, 'rot90': lambda a: np.rot90(a, 1), 'rot180': lambda a: np.rot90(a, 2),
                'rot270': lambda a: np.rot90(a, 3), 'flip_lr': np.fliplr, 'flip_ud': np.flipud,
                'transpose': lambda a: a.T, 'anti_transpose': lambda a: np.rot90(a, 2).T}


def corner_shifts(export: np.ndarray, stretched: np.ndarray) -> dict:
    """Sub-pixel shift of each corner tile of the export against the stretched original (phase correlation).

    A global correlation cannot see a small centred crop: the picture is the same, only slightly zoomed.
    The zoom moves the four corners outwards in opposite directions, which local shifts do show.
    """
    import cv2
    h, w = export.shape
    th, tw = int(h * CORNER_TILE_FRACTION), int(w * CORNER_TILE_FRACTION)
    window = cv2.createHanningWindow((tw, th), cv2.CV_64F)
    out = {}
    for name, (y, x) in dict(top_left=(0, 0), top_right=(0, w - tw), bottom_left=(h - th, 0),
                             bottom_right=(h - th, w - tw)).items():
        (dx, dy), response = cv2.phaseCorrelate(np.ascontiguousarray(stretched[y:y + th, x:x + tw]),
                                                np.ascontiguousarray(export[y:y + th, x:x + tw]), window)
        texture = float(min(stretched[y:y + th, x:x + tw].std(), export[y:y + th, x:x + tw].std()))
        out[name] = dict(dx=float(dx), dy=float(dy), response=float(response), texture_std=texture)
    return out


def alignment(export_path: Path, original_path: Path) -> dict:
    """Decide from pixels whether the export is an uncropped stretch of the original, same orientation."""
    with Image.open(export_path) as export_image, Image.open(original_path) as original_image:
        export_size, original_size = export_image.size, original_image.size
        export = _grey(export_image)
        stretched = _grey(original_image, export_size)
    scores = {}
    for name, turn in ORIENTATIONS.items():
        candidate = turn(stretched)
        scores[name] = _correlation(export, candidate) if candidate.shape == export.shape else None
    valid = {k: v for k, v in scores.items() if v is not None}
    best = max(valid, key=valid.get)
    others = [v for k, v in valid.items() if k != 'identity']
    margin = scores['identity'] - max(others) if scores['identity'] is not None and others else None
    s, h, w = SHIFT_SEARCH_PX, export.shape[0], export.shape[1]
    shifts = {}
    for dy in range(-s, s + 1):
        for dx in range(-s, s + 1):
            a = export[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)]
            b = stretched[max(0, -dy):h + min(0, -dy), max(0, -dx):w + min(0, -dx)]
            shifts[(dx, dy)] = _correlation(a, b)
    best_shift = max(shifts, key=shifts.get)
    reasons = []
    if best != 'identity':
        reasons.append(f'best_orientation_is_{best}')
    if scores['identity'] is None or scores['identity'] < MIN_ALIGNMENT_CORRELATION:
        reasons.append('correlation_below_minimum')
    if margin is None or margin < MIN_ORIENTATION_MARGIN:
        reasons.append('orientation_not_distinct')
    if best_shift != (0, 0):
        reasons.append(f'best_offset_{best_shift[0]}_{best_shift[1]}_export_px')
    corners = corner_shifts(export, stretched)
    corner_max = max(max(abs(c['dx']), abs(c['dy'])) for c in corners.values())
    if not all(np.isfinite([c['dx'], c['dy'], c['response']]).all() and c['response'] >= MIN_CORNER_RESPONSE
               and c['texture_std'] >= MIN_CORNER_TEXTURE_STD for c in corners.values()):
        reasons.append('corner_check_inconclusive')
    elif corner_max > MAX_CORNER_SHIFT_PX:
        reasons.append('corner_shift_indicates_crop_or_rescale')
    return dict(accepted=not reasons, reasons=reasons, export_size_px=list(export_size),
                original_size_px=list(original_size), identity_correlation=scores['identity'],
                orientation_scores=scores, orientation_margin=margin, best_offset_export_px=list(best_shift),
                corner_shifts_export_px=corners, max_corner_shift_export_px=corner_max,
                rules=dict(min_alignment_correlation=MIN_ALIGNMENT_CORRELATION,
                           min_orientation_margin=MIN_ORIENTATION_MARGIN, shift_search_px=SHIFT_SEARCH_PX,
                           comparison_blur_px=COMPARISON_BLUR_PX, corner_tile_fraction=CORNER_TILE_FRACTION,
                           max_corner_shift_px=MAX_CORNER_SHIFT_PX, min_corner_response=MIN_CORNER_RESPONSE,
                           min_corner_texture_std=MIN_CORNER_TEXTURE_STD))


def stretch_transform(export_size: list[int], original_size: list[int]) -> dict:
    sx, sy = original_size[0] / export_size[0], original_size[1] / export_size[1]
    return dict(type='uncropped_stretch', coordinate_convention='pixel_edges', scale_x=sx, scale_y=sy,
                export_size_px=list(export_size), original_size_px=list(original_size),
                formula='x_original = x_export * scale_x; y_original = y_export * scale_y')


def convert_annotation(annotation: dict, transform: dict) -> dict:
    """Scale bbox edges and polygon vertices; verify the round trip; keep everything else."""
    sx, sy = transform['scale_x'], transform['scale_y']
    out = json.loads(json.dumps(annotation))
    if annotation.get('bbox'):
        x, y, w, h = annotation['bbox']
        out['bbox'] = [x * sx, y * sy, w * sx, h * sy]
        back = [out['bbox'][0] / sx, out['bbox'][1] / sy, out['bbox'][2] / sx, out['bbox'][3] / sy]
        if max(abs(p - q) for p, q in zip(back, annotation['bbox'])) > ROUND_TRIP_TOLERANCE_PX:
            raise StudyError('bbox round trip exceeded tolerance')
    if isinstance(annotation.get('segmentation'), list):
        out['segmentation'] = []
        for ring in annotation['segmentation']:
            scaled = [v * (sx if i % 2 == 0 else sy) for i, v in enumerate(ring)]
            back = [v / (sx if i % 2 == 0 else sy) for i, v in enumerate(scaled)]
            if max((abs(p - q) for p, q in zip(back, ring)), default=0) > ROUND_TRIP_TOLERANCE_PX:
                raise StudyError('polygon round trip exceeded tolerance')
            out['segmentation'].append(scaled)
    if annotation.get('area') is not None:
        out['area'] = annotation['area'] * sx * sy
    return out


def frame_for(export_name: str, capture: dict, plant: str) -> tuple[dict | None, str | None]:
    """Resolve an export photo to a prepared frame by plant, date, view code and recorded source stem."""
    match = EXPORT_NAME.match(export_name)
    if not match:
        return None, 'export_name_not_parsed'
    if match['plant'] != plant or capture.get('plant_id') != plant:
        return None, 'different_plant'
    stem = f"{match['plant']}_{match['date']}_{match['view']}".lower()
    hits = [f for f in capture['frames'] if f.get('view_code') == match['view'] and
            PureWindowsPath(str(f.get('source_path') or '')).stem.lower() == stem]
    if len(hits) != 1:
        return None, 'no_frame_with_this_source' if not hits else 'several_frames_with_this_source'
    return hits[0], None


def draw_overlay(original_path: Path, export_path: Path, annotations: list[dict], converted: list[dict],
                 names: dict, out: Path) -> None:
    """Converted labels on the prepared original, beside the export with its own labels."""
    with Image.open(original_path) as original, Image.open(export_path) as export:
        scale = OVERLAY_WIDTH_PX / original.size[0]
        left = original.convert('RGB').resize((OVERLAY_WIDTH_PX, round(original.size[1] * scale)))
        right = export.convert('RGB').resize((OVERLAY_WIDTH_PX // 2, round(export.size[1] * OVERLAY_WIDTH_PX / 2 / export.size[0])))
        right_scale = right.size[0] / export.size[0]
    for image, records, factor in ((left, converted, scale), (right, annotations, right_scale)):
        draw = ImageDraw.Draw(image)
        for record in records:
            colour = CLASS_COLOURS.get(names[record['category_id']], (255, 255, 255))
            for ring in record.get('segmentation') or []:
                points = [(ring[i] * factor, ring[i + 1] * factor) for i in range(0, len(ring) - 1, 2)]
                if len(points) >= 2:
                    draw.line(points + [points[0]], fill=colour, width=2)
    canvas = Image.new('RGB', (left.size[0] + right.size[0], max(left.size[1], right.size[1])), (0, 0, 0))
    canvas.paste(left, (0, 0)); canvas.paste(right, (left.size[0], 0))
    canvas.save(out, quality=85)


def seed_with_imports(seed_path: Path, coco_path: Path, capture: dict, growth: Path | None, out: Path) -> dict:
    """Run the editor's own importDetections (via Node) so there is one detection schema."""
    node = shutil.which('node')
    if not node:
        raise StudyError('Node.js is required to build the seed with the editor import code')
    frames = [dict(key=f['image_file'].lower(), image_file=f['image_file'],
                   width=capture['intrinsics']['image_width_px'], height=capture['intrinsics']['image_height_px'])
              for f in capture['frames']]
    job = dict(seed=read_json(seed_path), coco=read_json(coco_path), coco_name=coco_path.name, frames=frames,
               growth=read_json(growth) if growth else None, growth_name=growth.name if growth else None)
    run = subprocess.run([node, str(NODE_HELPER)], input=json.dumps(job), capture_output=True,
                         encoding='utf-8', timeout=120)
    if run.returncode != 0:
        raise StudyError('Editor import failed: ' + run.stderr[-2000:])
    result = json.loads(run.stdout)
    backup = result['backup']
    backup['seed_derivation'] = dict(tool='tools.roboflow_session_import', base_seed=str(seed_path),
                                     base_seed_sha256=file_hash(seed_path), coco=str(coco_path),
                                     coco_sha256=file_hash(coco_path), growth_reference=str(growth) if growth else None)
    write_json(out, backup)
    return result['import']


def import_plant(plant: str, package: Path, session: Path, out: Path, growth: Path | None = None) -> dict:
    package, session, out = Path(package).resolve(), Path(session).resolve(), Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise StudyError(f'Output directory is not empty; choose a new one: {out}')
    capture = read_json(session / 'capture.json')
    if capture.get('plant_id') != plant:
        raise StudyError(f'Prepared session belongs to {capture.get("plant_id")}, not {plant}')
    folders = sorted(p.parent for p in (package / plant).glob('*/*/_annotations.coco.json'))
    if not folders:
        raise StudyError(f'No grouped COCO folders for {plant} under {package}')
    (out / 'overlays').mkdir(parents=True)
    hashes = {str(p): file_hash(p) for p in [session / n for n in ('capture.json', 'seed.backup.json',
              'intrinsics.json', 'annotations.source.json', 'session_report.json')] + ([growth] if growth else [])}
    combined = dict(images=[], annotations=[], categories=[], info=dict(
        description=f'{plant}: human Roboflow labels converted to prepared original pixels',
        coordinates='original_pixel_edges', labels='human annotations, not model predictions'))
    category_ids: dict[str, int] = {}
    unmapped, rows, source_total = [], [], 0
    for folder in folders:
        coco_path = folder / '_annotations.coco.json'
        hashes[str(coco_path)] = file_hash(coco_path)
        coco = read_json(coco_path)
        names = {c['id']: c['name'] for c in coco['categories']}
        view_group = folder.name
        by_image: dict[int, list] = {}
        for a in coco['annotations']:
            by_image.setdefault(a['image_id'], []).append(a)
        source_total += len(coco['annotations'])
        for image in coco['images']:
            export_path = folder / image['file_name']
            hashes[str(export_path)] = file_hash(export_path)
            labels = by_image.get(image['id'], [])
            frame, reason = frame_for(image['file_name'], capture, plant)
            check = None
            if frame is not None:
                original = session / frame['image_path']
                if file_hash(original) != frame['sha256']:
                    raise StudyError(f'Prepared frame hash mismatch: {frame["image_file"]}')
                check = alignment(export_path, original)
                if [image['width'], image['height']] != check['export_size_px']:
                    check['accepted'] = False; check['reasons'].append('coco_size_differs_from_photo')
                if not check['accepted']:
                    reason = 'alignment_rejected'
            row = dict(plant_id=plant, view_group=view_group, export_file=image['file_name'],
                       prepared_frame=frame['image_file'] if frame else None,
                       view_code=frame['view_code'] if frame else None, labels=len(labels),
                       mapped=reason is None, reason=reason or '',
                       identity_correlation=check and check['identity_correlation'],
                       orientation_margin=check and check['orientation_margin'],
                       best_offset_export_px=check and check['best_offset_export_px'],
                       pose_status=frame and frame.get('pose_status'), passes_pose_gate=frame and frame.get('passes_pose_gate'))
            rows.append(dict(row, alignment=check))
            if reason:
                unmapped.append(dict(export_file=image['file_name'], view_group=view_group, reason=reason,
                                     alignment=check, image=image, annotations=labels, categories=coco['categories']))
                continue
            transform = stretch_transform(check['export_size_px'], check['original_size_px'])
            image_id = len(combined['images']) + 1
            combined['images'].append(dict(id=image_id, file_name=frame['image_file'], width=transform['original_size_px'][0],
                                           height=transform['original_size_px'][1],
                                           extra=dict(name=frame['image_file'], transform=transform,
                                                      export_file=image['file_name'], view_group=view_group,
                                                      source_export=image.get('source_export'))))
            converted = []
            for a in labels:
                name = names[a['category_id']]
                category = category_ids.setdefault(name, len(category_ids) + 1)
                record = convert_annotation(a, transform)
                record.update(id=len(combined['annotations']) + 1, image_id=image_id, category_id=category,
                              provenance=dict(source_class_name=name, source_category_id=a['category_id'],
                                              package_folder=str(folder.relative_to(package).as_posix()),
                                              package_annotation_id=a['id'], package_image_id=image['id'],
                                              source_export=a.get('source_export'), export_bbox=a.get('bbox'),
                                              transform=transform['type']))
                combined['annotations'].append(record); converted.append(dict(record, category_id=a['category_id']))
            draw_overlay(session / frame['image_path'], export_path, labels, converted, names,
                         out / 'overlays' / (Path(frame['image_file']).stem + '.jpg'))
    combined['categories'] = [dict(id=i, name=n, source='original Roboflow class name') for n, i in category_ids.items()]
    write_json(out / 'input_hashes.json', hashes)
    coco_out = out / 'original_pixel_labels.coco.json'
    write_json(coco_out, combined)
    write_json(out / 'unmapped_export_labels.json', dict(photos=unmapped, notice=(
        'Kept as 2D export labels only. They are excluded from geometry until their mapping is resolved.')))
    with open(out / 'mapping_table.csv', 'w', newline='', encoding='utf-8') as handle:
        fields = [k for k in rows[0] if k != 'alignment'] if rows else []
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows({k: v for k, v in r.items() if k != 'alignment'} for r in rows)
    imported = seed_with_imports(session / 'seed.backup.json', coco_out, capture, growth,
                                 out / 'seed_with_imports.backup.json')
    report = dict(schema_version='roboflow-session-import-1', plant_id=plant, session=str(session),
                  source_annotations=source_total, mapped_annotations=len(combined['annotations']),
                  unmapped_annotations=sum(len(u['annotations']) for u in unmapped),
                  mapped_photos=len(combined['images']), unmapped_photos=len(unmapped),
                  editor_import=imported, photos=rows,
                  validated_metric=False, suitable_for_ppfd=False,
                  notice=('Labels are human 2D observations. Mapping them creates no leaflet identity, parent '
                          'membership, physical point or pose; boxes are not leaf outlines.'))
    if report['mapped_annotations'] + report['unmapped_annotations'] != source_total:
        raise StudyError('Annotation accounting does not close')
    write_json(out / 'mapping_report.json', report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--plant', required=True)
    for key in ('package', 'session', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--growth', type=Path)
    args = parser.parse_args()
    report = import_plant(args.plant, args.package, args.session, args.out, args.growth)
    print(json.dumps({k: report[k] for k in ('plant_id', 'source_annotations', 'mapped_annotations',
                                             'unmapped_annotations', 'mapped_photos', 'unmapped_photos',
                                             'editor_import')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
