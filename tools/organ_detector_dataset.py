"""YOLO segmentation dataset of all plants' organ labels for retraining the organ detector (user request 2026-09-25).

    python -X utf8 -m tools.organ_detector_dataset --out build/organ_detector_<date>/dataset [--v4]

Sources: the original-pixel COCO labels of every plant (human Roboflow labels) and the human-accepted leaflet mask
outline instead of the Roboflow rectangle. Side and middle photos are pooled. Class names are unified across plants.
Polygons are normalised, so a resize does not change them. Folds are leave-one-plant-out.

v4 (2026-09-29, user: small organs, tiles instead of shrinking; masks reviewed to the end):
* all four plants use their newest accepted-mask export (1,163 masks incl. 7 accepted as occluded/partial);
* leaflet boxes whose mask a person rejected as `false_positive` or `duplicate_box` are dropped (not a leaflet / a
  second box of one leaflet); `box_misses_leaf` keeps the person's box, because the leaflet is real;
* three image variants of the same labels, compared in training:
  full/    the whole photo at STORE_PX (as v3)
  window/  the square plant window (organ_prelabel.plant_window, the window used at inference) at STORE_PX
  tiles/   2 x 2 tiles of that window with TILE_OVERLAP overlap, each at STORE_PX (about twice the pixels per organ);
           a polygon cut by a tile edge is kept when at least TILE_KEEP of its area lies in the tile
Petioles are 33 px (median short side) at a 1280 input in full photos, 18 px at the 10th percentile, which is why the
tiles exist. Evaluation always happens on the full photo (tile predictions are mapped back), so the variants compare.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ['compound_leaf', 'leaflet', 'sub_stem', 'main_stem', 'growth_shoot']
ALIASES = {'compond_leaf': 'compound_leaf', 'compound_leaves': 'compound_leaf', 'compoundleaves': 'compound_leaf',
           'leaflet': 'leaflet', 'sub_stem': 'sub_stem', 'sub-stem': 'sub_stem', 'main_stem': 'main_stem',
           'main-stem': 'main_stem', 'shoot': 'growth_shoot', 'growth_shoot': 'growth_shoot', 'growth-shoot': 'growth_shoot'}
PLANTS = {
    'dwt_01': ('build/new_captures_20260920/dwt_01/edit_session', 'build/dwt_01_02_3d_20260922/dwt_01/labels/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260924_231659_618535'),
    'dwt_02': ('build/new_captures_20260920/dwt_02/edit_session', 'build/dwt_01_02_3d_20260922/dwt_02/labels/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260922/dwt_02/exports/accepted_20260924_231624_807db7'),
    'dwt_03': ('build/new_captures_20260921/dwt_03/edit_session', 'build/dwt_03_04_3d_20260922/dwt_03/original_pixel_labels.coco.json', None),
    'dwt_04': ('build/new_captures_20260921/dwt_04/edit_session', 'build/dwt_03_04_3d_20260922/dwt_04/original_pixel_labels.coco.json', None),
}
#: v4 inputs: (session, labels, newest accepted export, mask batch holding the review of every leaflet box)
PLANTS_V4 = {
    'dwt_01': ('build/new_captures_20260920/dwt_01/edit_session', 'build/dwt_01_02_3d_20260922/dwt_01/labels/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260929_092627_faeb15', 'build/leaflet_mask_batch_20260922/dwt_01'),
    'dwt_02': ('build/new_captures_20260920/dwt_02/edit_session', 'build/dwt_01_02_3d_20260922/dwt_02/labels/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260922/dwt_02/exports/accepted_20260929_092727_139059', 'build/leaflet_mask_batch_20260922/dwt_02'),
    'dwt_03': ('build/new_captures_20260921/dwt_03/edit_session', 'build/dwt_03_04_3d_20260922/dwt_03/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260925_tuned/dwt_03/exports/accepted_20260929_092816_35b47e', 'build/leaflet_mask_batch_20260925_tuned/dwt_03'),
    'dwt_04': ('build/new_captures_20260921/dwt_04/edit_session', 'build/dwt_03_04_3d_20260922/dwt_04/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260925_tuned/dwt_04/exports/accepted_20260929_092913_25d191', 'build/leaflet_mask_batch_20260925_tuned/dwt_04'),
}
DROP_REASONS = ('false_positive', 'duplicate_box')
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')


def plants_from_config(config: Path = CONFIG) -> dict:
    """Every plant of the pipeline config with human-reviewed masks, in the PLANTS_V4 layout (2026-09-29): a new
    plant joins the training data by being in the config and having an export of accepted masks - no code change.
    Uses each batch's newest exports/accepted_* folder; plants whose labels are model drafts (auto) are skipped,
    because training on the model's own answers would teach it nothing new."""
    cfg = read_json(config)
    out = {}
    for plant, pc in cfg['plants'].items():
        labels = ROOT / pc['labels']
        coco = labels / 'original_pixel_labels.coco.json'
        report = labels / 'mapping_report.json'
        batch = ROOT / pc['batch'] if pc.get('batch') else None
        if not (coco.exists() and batch and (batch / 'exports').exists()):
            continue
        if report.exists() and read_json(report).get('schema_version') == 'plant-auto-labels-1':
            continue
        exports = sorted((batch / 'exports').glob('accepted_*'))
        if not exports:
            continue
        out[plant] = (str(Path(pc['capture']) / 'edit_session'), str(coco.relative_to(ROOT)), str(exports[-1].relative_to(ROOT)),
                      str(batch.relative_to(ROOT)))
    return out
STORE_PX = 1536
TILE_OVERLAP, TILE_KEEP = 0.2, 0.4


def mask_polygon(path: Path):
    m = (np.asarray(Image.open(path)) > 0).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 2.0, True).reshape(-1, 2)
    return c.astype(float).ravel().tolist() if len(c) >= 3 else None


def build(out: Path) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    rows, replaced = [], 0
    for plant, (session, coco_path, export) in PLANTS.items():
        coco = read_json(ROOT / coco_path)
        cats = {c['id']: ALIASES.get(c['name']) for c in coco['categories']}
        outlines = {}
        if export:
            for ob in read_json(ROOT / export / 'accepted.json')['observations']:
                poly = mask_polygon(ROOT / export / ob['mask_file'])
                if poly:
                    outlines[int(ob['source_annotation']['id'])] = poly
        (out / plant / 'images').mkdir(parents=True)
        (out / plant / 'labels').mkdir()
        for im in coco['images']:
            W, H = im['width'], im['height']
            lines = []
            for a in [a for a in coco['annotations'] if a['image_id'] == im['id']]:
                name = cats.get(a['category_id'])
                if name is None:
                    continue
                poly = a['segmentation'][0] if a.get('segmentation') else None
                if name == 'leaflet' and a['id'] in outlines:
                    poly, replaced = outlines[a['id']], replaced + 1
                if not poly:
                    x, y, w, h = a['bbox']
                    poly = [x, y, x + w, y, x + w, y + h, x, y + h]
                xy = np.clip(np.array(poly, float).reshape(-1, 2) / [W, H], 0, 1)
                lines.append(f"{CLASSES.index(name)} " + ' '.join(f'{v:.5f}' for v in xy.ravel()))
            stem = Path(im['file_name']).stem
            img = Image.open(ROOT / session / 'images' / im['file_name']).convert('RGB')
            img.thumbnail((STORE_PX, STORE_PX))
            img.save(out / plant / 'images' / f'{stem}.jpg', quality=92)
            (out / plant / 'labels' / f'{stem}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
            rows.append(dict(plant=plant, image=f'{plant}/images/{stem}.jpg', view_group=im.get('extra', {}).get('view_group'), labels=len(lines)))
    doc = dict(schema='organ-detector-dataset-1', classes=CLASSES, images=rows, leaflet_outlines_from_accepted_masks=replaced,
               folds={p: dict(val=p, train=[q for q in PLANTS if q != p]) for p in PLANTS},
               note='human labels only; dwt_01/02 leaflets use accepted mask outlines, the rest are Roboflow rectangles/polygons')
    write_json(out / 'index.json', doc)
    return dict(out=str(out), images=len(rows), labels=sum(r['labels'] for r in rows), outlines=replaced)


# ---------------- v4

_plants: dict = {}


def plant_labels(plant: str) -> tuple[list[dict], dict]:
    """Per photo: original-pixel polygons with class, after the v4 rules. Returns (photos, counts)."""
    session, coco_path, export, batch = (_plants or PLANTS_V4)[plant]
    coco = read_json(ROOT / coco_path)
    cats = {c['id']: ALIASES.get(c['name']) for c in coco['categories']}
    outlines = {}
    for ob in read_json(ROOT / export / 'accepted.json')['observations']:
        poly = mask_polygon(ROOT / export / ob['mask_file'])
        if poly:
            outlines[int(ob['source_annotation']['id'])] = poly
    reasons = {}
    for f in (ROOT / batch / 'items').glob('*.json'):
        it = read_json(f)
        if it['review'] == 'rejected':
            reasons[int(it['source_annotation_id'])] = it.get('reject_reason')
    counts = dict(outlines=0, dropped_false_positive=0, dropped_duplicate_box=0, kept_box_misses_leaf=0, unknown_class=0)
    photos = []
    for im in coco['images']:
        polys = []
        for a in [a for a in coco['annotations'] if a['image_id'] == im['id']]:
            name = cats.get(a['category_id'])
            if name is None:
                counts['unknown_class'] += 1
                continue
            if name == 'leaflet' and reasons.get(a['id']) in DROP_REASONS:
                counts['dropped_' + reasons[a['id']]] += 1
                continue
            if name == 'leaflet' and reasons.get(a['id']) == 'box_misses_leaf':
                counts['kept_box_misses_leaf'] += 1
            poly = a['segmentation'][0] if a.get('segmentation') else None
            if name == 'leaflet' and a['id'] in outlines:
                poly = outlines[a['id']]
                counts['outlines'] += 1
            if not poly:
                x, y, w, h = a['bbox']
                poly = [x, y, x + w, y, x + w, y + h, x, y + h]
            polys.append((CLASSES.index(name), np.array(poly, float).reshape(-1, 2)))
        photos.append(dict(file=im['file_name'], size=(im['width'], im['height']), polys=polys,
                           view_group=im.get('extra', {}).get('view_group'), path=ROOT / session / 'images' / im['file_name']))
    return photos, counts


def clip_polys(polys, box):
    """Polygons clipped to box (x0, y0, x1, y1), in box-relative pixels; a piece is kept when it holds at least
    TILE_KEEP of the polygon's area (thin stems: their area, not their length, is compared)."""
    from shapely.geometry import Polygon, box as sbox
    x0, y0, x1, y1 = box
    rect, out = sbox(x0, y0, x1, y1), []
    for c, xy in polys:
        if len(xy) < 3:
            continue
        p = Polygon(xy).buffer(0)
        if p.is_empty or p.area <= 0:
            continue
        cut = p.intersection(rect)
        if cut.is_empty or cut.area < TILE_KEEP * p.area:
            continue
        piece = max(getattr(cut, 'geoms', [cut]), key=lambda g: g.area)
        if piece.geom_type != 'Polygon':
            continue
        out.append((c, np.asarray(piece.exterior.coords)[:-1] - [x0, y0]))
    return out


def write_item(out: Path, variant: str, plant: str, name: str, rgb: np.ndarray, polys, extra: dict) -> dict:
    h, w = rgb.shape[:2]
    lines = [f"{c} " + ' '.join(f'{v:.5f}' for v in np.clip(xy / [w, h], 0, 1).ravel()) for c, xy in polys]
    img = Image.fromarray(rgb)
    img.thumbnail((STORE_PX, STORE_PX))
    d = out / variant / plant
    img.save(d / 'images' / f'{name}.jpg', quality=92)
    (d / 'labels' / f'{name}.txt').write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
    return dict(variant=variant, plant=plant, image=f'{variant}/{plant}/images/{name}.jpg', labels=len(lines), **extra)


def build_v4(out: Path) -> dict:
    from tools.organ_prelabel import plant_window
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    rows, counts, photos_meta = [], {}, []
    for plant in (_plants or PLANTS_V4):
        photos, counts[plant] = plant_labels(plant)
        for v in ('full', 'window', 'tiles'):
            (out / v / plant / 'images').mkdir(parents=True)
            (out / v / plant / 'labels').mkdir(parents=True)
        for ph in photos:
            rgb = np.asarray(Image.open(ph['path']).convert('RGB'))
            W, H = ph['size']
            stem = Path(ph['file']).stem
            X0, Y0, X1, Y1 = plant_window(rgb)
            photos_meta.append(dict(plant=plant, photo=stem, size=[W, H], window=[X0, Y0, X1, Y1], view_group=ph['view_group'],
                                    gt=[dict(cls=c, xyxy=[float(xy[:, 0].min()), float(xy[:, 1].min()), float(xy[:, 0].max()), float(xy[:, 1].max())])
                                        for c, xy in ph['polys']]))
            rows.append(write_item(out, 'full', plant, stem, rgb, ph['polys'], dict(photo=stem, offset=[0, 0], crop=[W, H])))
            win = (X0, Y0, X1, Y1)
            rows.append(write_item(out, 'window', plant, stem, np.ascontiguousarray(rgb[Y0:Y1, X0:X1]), clip_polys(ph['polys'], win),
                                   dict(photo=stem, offset=[X0, Y0], crop=[X1 - X0, Y1 - Y0])))
            side = X1 - X0
            t = int(round(side * (1 + TILE_OVERLAP) / 2))
            for i, ox in enumerate((X0, X1 - t)):
                for j, oy in enumerate((Y0, Y1 - t)):
                    box = (ox, oy, ox + t, oy + t)
                    rows.append(write_item(out, 'tiles', plant, f'{stem}_t{i}{j}', np.ascontiguousarray(rgb[oy:oy + t, ox:ox + t]),
                                           clip_polys(ph['polys'], box), dict(photo=stem, offset=[ox, oy], crop=[t, t])))
    doc = dict(schema='organ-detector-dataset-2', classes=CLASSES, variants=['full', 'window', 'tiles'], images=rows,
               photos=photos_meta, label_rules=dict(drop_leaflet_boxes_rejected_as=list(DROP_REASONS), keep='box_misses_leaf',
                                                    leaflet_polygon='accepted mask outline when accepted', tile_overlap=TILE_OVERLAP,
                                                    tile_keep_area_fraction=TILE_KEEP),
               counts=counts, folds={p: dict(val=p, train=[q for q in (_plants or PLANTS_V4) if q != p]) for p in (_plants or PLANTS_V4)},
               sources={p: dict(labels=v[1], export=v[2], batch=v[3]) for p, v in (_plants or PLANTS_V4).items()},
               note='human labels and human mask reviews only; evaluation must use photos[].gt on the full photo')
    write_json(out / 'index.json', doc)
    per = {v: sum(1 for r in rows if r['variant'] == v) for v in ('full', 'window', 'tiles')}
    return dict(out=str(out), images=per, labels={v: sum(r['labels'] for r in rows if r['variant'] == v) for v in per}, counts=counts)


#: Stem model (2026-09-29, user: small organs by their own model): only these classes, re-numbered 0..1.
STEM_CLASSES = ('main_stem', 'sub_stem')
STEM_GRID = 3


def build_stems(out: Path) -> dict:
    """Main stems and petioles only, full photo + 3 x 3 tiles of the plant window (about 2.5x the pixels of a full
    photo per stem at the same input size). Same label rules and full-photo evaluation boxes as v4."""
    from tools.organ_prelabel import plant_window
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    keep = {CLASSES.index(c): k for k, c in enumerate(STEM_CLASSES)}
    rows, photos_meta, counts = [], [], {}
    for plant in (_plants or PLANTS_V4):
        photos, _ = plant_labels(plant)
        for v in ('full', 'tiles3'):
            (out / v / plant / 'images').mkdir(parents=True)
            (out / v / plant / 'labels').mkdir(parents=True)
        counts[plant] = {c: 0 for c in STEM_CLASSES}
        for ph in photos:
            polys = [(keep[c], xy) for c, xy in ph['polys'] if c in keep]
            for c, _ in polys:
                counts[plant][STEM_CLASSES[c]] += 1
            rgb = np.asarray(Image.open(ph['path']).convert('RGB'))
            W, H = ph['size']
            stem = Path(ph['file']).stem
            X0, Y0, X1, Y1 = plant_window(rgb)
            photos_meta.append(dict(plant=plant, photo=stem, size=[W, H], window=[X0, Y0, X1, Y1], view_group=ph['view_group'],
                                    gt=[dict(cls=c, xyxy=[float(xy[:, 0].min()), float(xy[:, 1].min()), float(xy[:, 0].max()), float(xy[:, 1].max())])
                                        for c, xy in polys]))
            rows.append(write_item(out, 'full', plant, stem, rgb, polys, dict(photo=stem, offset=[0, 0], crop=[W, H])))
            side = X1 - X0
            t = int(round(side * (1 + 2 * TILE_OVERLAP) / STEM_GRID))
            starts = [int(round(X0 + k * (side - t) / (STEM_GRID - 1))) for k in range(STEM_GRID)]
            ystarts = [int(round(Y0 + k * ((Y1 - Y0) - t) / (STEM_GRID - 1))) for k in range(STEM_GRID)]
            for i, ox in enumerate(starts):
                for j, oy in enumerate(ystarts):
                    box = (ox, oy, ox + t, oy + t)
                    rows.append(write_item(out, 'tiles3', plant, f'{stem}_t{i}{j}', np.ascontiguousarray(rgb[oy:oy + t, ox:ox + t]),
                                           clip_polys(polys, box), dict(photo=stem, offset=[ox, oy], crop=[t, t])))
    doc = dict(schema='organ-detector-dataset-2', classes=list(STEM_CLASSES), variants=['full', 'tiles3'], images=rows,
               photos=photos_meta, counts=counts, label_rules=dict(source='v4 rules (plant_labels)', classes_kept=list(STEM_CLASSES),
                                                                   tile_grid=STEM_GRID, tile_overlap=TILE_OVERLAP, tile_keep_area_fraction=TILE_KEEP),
               folds={p: dict(val=p, train=[q for q in (_plants or PLANTS_V4) if q != p]) for p in (_plants or PLANTS_V4)},
               note='stem/petiole model; evaluation must use photos[].gt on the full photo')
    write_json(out / 'index.json', doc)
    return dict(out=str(out), images={v: sum(1 for r in rows if r['variant'] == v) for v in ('full', 'tiles3')}, counts=counts)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--v4', action='store_true', help='full / window / tiles variants from the reviewed masks')
    ap.add_argument('--stems', action='store_true', help='main stems and petioles only, full + 3x3 tiles')
    ap.add_argument('--from-config', action='store_true',
                    help='take every reviewed plant from tools/plant_pipeline_plants.json (newest accepted export) instead of the fixed list')
    a = ap.parse_args()
    if a.from_config:
        _plants.update(plants_from_config())
    print(json.dumps(build_stems(a.out) if a.stems else build_v4(a.out) if a.v4 else build(a.out), ensure_ascii=False))


if __name__ == '__main__':
    main()
