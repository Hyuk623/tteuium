"""Leaflet-only detection/segmentation dataset for all plants (user: 'all in on leaf detection', 2026-09-27).

    python -X utf8 -m tools.leaflet_detect_dataset --out build/leaflet_detect_<date>/upload/dataset

Ground truth = every human-accepted leaflet mask outline (including those accepted as 'partial' because occluded).
Rejected boxes that may still hold a real leaflet (no reason, occluded-but-rejected, box_misses_leaf, duplicate_box)
are painted grey (114) in the image, so the model is neither rewarded nor punished there; false_positive boxes are
left as they are (a true negative). Two image variants are written:
  full/  the whole photo at FULL_PX
  crop/  a square window around the plant's green pixels at CROP_PX (more pixels per leaflet)
Labels are ultralytics segmentation polygons, normalised to each variant. Folds are leave-one-plant-out.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tools.leaf_light.common import StudyError, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
FULL_PX, CROP_PX, GREY = 1536, 1536, (114, 114, 114)


def plant_window(rgb, pad=0.15):
    f = rgb.astype(np.float32)
    exg = (2 * f[..., 1] - f[..., 0] - f[..., 2]) / (f.sum(-1) + 1e-6)
    ys, xs = np.nonzero((exg > 0.06) & (f[..., 1] > 40))
    H, W = rgb.shape[:2]
    if len(xs) < 500:
        return 0, 0, W, H
    x0, x1, y0, y1 = np.percentile(xs, 0.5), np.percentile(xs, 99.5), np.percentile(ys, 0.5), np.percentile(ys, 99.5)
    side = max(x1 - x0, y1 - y0) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    X0, Y0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
    return X0, Y0, int(min(W, X0 + side)), int(min(H, Y0 + side))


def outline(batch, it):
    m, meta = batch.mask(it)
    x0, y0 = meta['crop_px'][:2]
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), 1.5, True).reshape(-1, 2).astype(float) + [x0, y0]
    return c if len(c) >= 3 else None


def build(out: Path) -> dict:
    from tools.leaflet_mask_batch import Batch
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    cfg = read_json(CONFIG)
    rows, grey_total = [], 0
    for plant, pc in cfg['plants'].items():
        b = Batch(ROOT / pc['batch'])
        by_photo = defaultdict(lambda: dict(acc=[], grey=[]))
        for i in b.manifest['ids']:
            it = b.item(i)
            if it['review'] in ('accepted', 'accepted_by_user'):
                by_photo[it['image_file']]['acc'].append(it)
            elif it['review'] == 'rejected' and it.get('reject_reason') != 'false_positive':
                by_photo[it['image_file']]['grey'].append(it)
        for photo, g in sorted(by_photo.items()):
            if not g['acc']:
                continue
            img = Image.open(b.session / g['acc'][0]['image_path']).convert('RGB')
            dr = ImageDraw.Draw(img)
            for it in g['grey']:
                dr.rectangle(it['prompts']['box_px'], fill=GREY)
            grey_total += len(g['grey'])
            polys = [p for p in (outline(b, it) for it in g['acc']) if p is not None]
            rgb = np.asarray(img)
            W, H = img.size
            X0, Y0, X1, Y1 = plant_window(rgb)
            stem = Path(photo).stem
            for variant, (ox, oy, w, h), px in (('full', (0, 0, W, H), FULL_PX), ('crop', (X0, Y0, X1 - X0, Y1 - Y0), CROP_PX)):
                (out / variant / plant / 'images').mkdir(parents=True, exist_ok=True)
                (out / variant / plant / 'labels').mkdir(parents=True, exist_ok=True)
                sub = img.crop((ox, oy, ox + w, oy + h))
                sub.thumbnail((px, px))
                sub.save(out / variant / plant / 'images' / f'{stem}.jpg', quality=92)
                lines = []
                for p in polys:
                    q = (p - [ox, oy]) / [w, h]
                    if (q.max(0) < 0).any() or (q.min(0) > 1).any():
                        continue
                    lines.append('0 ' + ' '.join(f'{v:.5f}' for v in np.clip(q, 0, 1).ravel()))
                (out / variant / plant / 'labels' / f'{stem}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
            rows.append(dict(plant=plant, photo=stem, leaflets=len(polys), greyed=len(g['grey']), window=[X0, Y0, X1, Y1]))
    doc = dict(schema='leaflet-detect-dataset-1', classes=['leaflet'], variants=['full', 'crop'], photos=rows,
               leaflets=sum(r['leaflets'] for r in rows), greyed_boxes=grey_total,
               note='GT = accepted mask outlines; rejected boxes except false_positive greyed out')
    write_json(out / 'index.json', doc)
    return dict(out=str(out), photos=len(rows), leaflets=doc['leaflets'], greyed=grey_total)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, type=Path)
    print(json.dumps(build(ap.parse_args().out), ensure_ascii=False))


if __name__ == '__main__':
    main()
