"""Crops + human-accepted leaflet masks for fine-tuning SAM 2.1 (user decision 2026-09-24).

    python -X utf8 -m tools.sam_finetune_dataset --export build/leaflet_mask_batch_20260922/dwt_01/exports/<accepted_...> \\
        --export build/leaflet_mask_batch_20260922/dwt_02/exports/<accepted_...> --out build/sam_finetune_<date>/dataset

Each accepted mask (tools.leaflet_mask_batch export) becomes one square crop around its prompt box, the crop's
binary mask and the box in crop pixels. The box is the same prompt the editor gave SAM, so a model tuned on these
answers the editor's question. Split is by photograph, never by mask: every photo of dwt_01 trains; the photos of
the evaluation plant alternate train/val by view code, so val masks never share a photo with a training mask.
Rejected masks are not used (a rejection says the draft was wrong, not what the right mask is).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

SCHEMA = 'sam-finetune-dataset-1'
#: Crop side = this many times the longer box side, at least MIN_CROP_PX; crops are stored at most MAX_CROP_PX.
CROP_SCALE, MIN_CROP_PX, MAX_CROP_PX = 1.6, 256, 1024


def square_crop(box, size):
    x0, y0, x1, y1 = box
    side = max(MIN_CROP_PX, CROP_SCALE * max(x1 - x0, y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left, top = int(round(cx - side / 2)), int(round(cy - side / 2))
    return left, top, left + int(round(side)), top + int(round(side))


def cut(arr, crop):
    """Crop with zero padding outside the image."""
    left, top, right, bottom = crop
    h, w = arr.shape[:2]
    out = np.zeros((bottom - top, right - left) + arr.shape[2:], arr.dtype)
    sx0, sy0, sx1, sy1 = max(left, 0), max(top, 0), min(right, w), min(bottom, h)
    out[sy0 - top:sy1 - top, sx0 - left:sx1 - left] = arr[sy0:sy1, sx0:sx1]
    return out


def build(exports: list[Path], out: Path, val_plant: str = 'dwt_02') -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    (out / 'images').mkdir(parents=True)
    (out / 'masks').mkdir()
    rows, sources = [], []
    for exp in map(Path, exports):
        acc = read_json(exp / 'accepted.json')
        batch = exp.parents[1]
        session = Path(read_json(batch / 'manifest.json')['session'])
        sources.append(dict(export=str(exp), accepted_sha256=file_hash(exp / 'accepted.json'), count=acc['count']))
        images = {}
        for ob in acc['observations']:
            key = ob['image_file']
            if key not in images:
                images = {key: np.asarray(Image.open(session / 'images' / key).convert('RGB'))}
            rgb = images[key]
            mask = np.asarray(Image.open(exp / ob['mask_file'])) > 0
            box = ob['prompts']['box_px']
            crop = square_crop(box, rgb.shape[:2])
            img_c, m_c = cut(rgb, crop), cut(mask, crop)
            scale = min(1.0, MAX_CROP_PX / img_c.shape[0])
            if scale < 1:
                n = int(round(img_c.shape[0] * scale))
                img_c = np.asarray(Image.fromarray(img_c).resize((n, n), Image.BILINEAR))
                m_c = np.asarray(Image.fromarray(m_c.astype(np.uint8) * 255).resize((n, n), Image.NEAREST)) > 0
            b = [(box[0] - crop[0]) * scale, (box[1] - crop[1]) * scale, (box[2] - crop[0]) * scale, (box[3] - crop[1]) * scale]
            view = key.rsplit('_', 1)[-1].split('.')[0]
            split = 'train' if ob['plant_id'] != val_plant else ('val' if int(view) % 2 == 0 else 'train')
            Image.fromarray(img_c).save(out / 'images' / f"{ob['id']}.jpg", quality=92)
            Image.fromarray(m_c.astype(np.uint8) * 255).save(out / 'masks' / f"{ob['id']}.png")
            rows.append(dict(id=ob['id'], plant=ob['plant_id'], photo=key, view=view, split=split,
                             box_xyxy=[round(v, 2) for v in b], crop_xyxy_original=list(crop), scale=scale,
                             mask_area_px=int(m_c.sum()), edited=bool(ob.get('changed')),
                             sensitivity=ob.get('sensitivity'), candidate=ob.get('selected_candidate')))
    counts = {s: sum(r['split'] == s for r in rows) for s in ('train', 'val')}
    doc = dict(schema=SCHEMA, sources=sources, val_plant=val_plant, counts=counts, rows=rows,
               crop=dict(scale=CROP_SCALE, min_px=MIN_CROP_PX, max_px=MAX_CROP_PX),
               note='accepted 2D masks only; split by photograph; val = even view codes of the evaluation plant')
    write_json(out / 'index.json', doc)
    return dict(out=str(out), **counts, photos_val=sorted({r['photo'] for r in rows if r['split'] == 'val'}))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--export', action='append', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--val-plant', default='dwt_02')
    a = ap.parse_args()
    print(json.dumps(build(a.export, a.out, a.val_plant), ensure_ascii=False))


if __name__ == '__main__':
    main()
