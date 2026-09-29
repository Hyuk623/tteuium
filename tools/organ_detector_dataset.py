"""YOLO segmentation dataset of all plants' organ labels for retraining the organ detector (user request 2026-09-25).

    python -X utf8 -m tools.organ_detector_dataset --out build/organ_detector_<date>/dataset

Sources: the original-pixel COCO labels of every plant (human Roboflow labels) and, for dwt_01/dwt_02 leaflets, the
human-accepted mask outline instead of the Roboflow rectangle. Side and middle photos are pooled (the two Roboflow
projects were trained separately on 31 photos each). Class names are unified across plants. Images are stored at
1536 px; polygons are normalised, so the resize does not change them. Folds are leave-one-plant-out.
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
ALIASES = {'compond_leaf': 'compound_leaf', 'compound_leaves': 'compound_leaf', 'leaflet': 'leaflet', 'sub_stem': 'sub_stem',
           'main_stem': 'main_stem', 'shoot': 'growth_shoot', 'growth_shoot': 'growth_shoot'}
PLANTS = {
    'dwt_01': ('build/new_captures_20260920/dwt_01/edit_session', 'build/dwt_01_02_3d_20260922/dwt_01/labels/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260924_231659_618535'),
    'dwt_02': ('build/new_captures_20260920/dwt_02/edit_session', 'build/dwt_01_02_3d_20260922/dwt_02/labels/original_pixel_labels.coco.json',
               'build/leaflet_mask_batch_20260922/dwt_02/exports/accepted_20260924_231624_807db7'),
    'dwt_03': ('build/new_captures_20260921/dwt_03/edit_session', 'build/dwt_03_04_3d_20260922/dwt_03/original_pixel_labels.coco.json', None),
    'dwt_04': ('build/new_captures_20260921/dwt_04/edit_session', 'build/dwt_03_04_3d_20260922/dwt_04/original_pixel_labels.coco.json', None),
}
STORE_PX = 1536


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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, type=Path)
    print(json.dumps(build(ap.parse_args().out), ensure_ascii=False))


if __name__ == '__main__':
    main()
