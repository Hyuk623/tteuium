"""Pixel classes background / leaflet interior / boundary from human-accepted leaflet masks (user idea 2026-09-25).

    python -X utf8 -m tools.leaflet_piece_dataset --export <accepted_... of dwt_01> --export <... dwt_02> \\
        --out build/leaflet_pieces_<date>/dataset

The user's idea: cut the photo into small pieces, call each piece leaf interior / boundary / not leaf, and join the
interior pieces into leaflets. Measured on dwt_01/02 (2026-09-25): with perfect piece classes at 8-16 px every one
of 173 leaflets separates. This writes the training data for a model that predicts those classes.

Per photograph (at HALF resolution): image.jpg, classes.png (0 background, 1 interior, 2 boundary, 255 ignore) and
instances.png (16-bit leaflet ids, 0 none). Plant pixels that no accepted mask covers (rejected or unlabelled leaves,
stems) are IGNORE, never background: teaching them as background would teach the model to erase real leaves.
Split by photograph, the same rule as tools.sam_finetune_dataset: dwt_01 trains; the evaluation plant alternates
train/val by view code.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

SCHEMA = 'leaflet-piece-dataset-1'
SCALE = 0.5
#: Boundary band half-width in half-resolution pixels (a pixel is boundary when a different id lies this close).
BAND_PX = 3
#: Excess green threshold for 'plant' and its dilation (half-res px) before a pixel may count as background.
EXG_MIN, PLANT_DILATE = 0.06, 6


def build(exports: list[Path], out: Path, val_plant: str = 'dwt_02') -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    out.mkdir(parents=True)
    photos, sources = [], []
    for exp in map(Path, exports):
        acc = read_json(exp / 'accepted.json')
        session = Path(read_json(exp.parents[1] / 'manifest.json')['session'])
        sources.append(dict(export=str(exp), accepted_sha256=file_hash(exp / 'accepted.json'), count=acc['count']))
        by_photo = defaultdict(list)
        for ob in acc['observations']:
            by_photo[ob['image_file']].append(ob)
        for photo, obs in sorted(by_photo.items()):
            rgb = Image.open(session / 'images' / photo).convert('RGB')
            W, H = rgb.size
            w, h = int(W * SCALE), int(H * SCALE)
            inst = np.zeros((H, W), np.int32)
            area = np.full((H, W), np.inf)
            ids = []
            for n, ob in enumerate(sorted(obs, key=lambda o: o['id']), 1):
                m = np.asarray(Image.open(exp / ob['mask_file'])) > 0
                a = m.sum()
                take = m & (a < area)            # overlapping accepted masks: the smaller (front) one wins
                inst[take], area[take] = n, a
                ids.append(dict(n=n, id=ob['id'], box_px=[round(v * SCALE, 1) for v in ob['prompts']['box_px']]))
            inst = np.asarray(Image.fromarray(inst.astype(np.uint16)).resize((w, h), Image.NEAREST)).astype(np.int32)
            small = np.asarray(rgb.resize((w, h), Image.BILINEAR)).astype(np.float32)
            r, g, b = small[..., 0], small[..., 1], small[..., 2]
            plant = ndimage.binary_dilation((2 * g - r - b) / (r + g + b + 1e-6) > EXG_MIN, iterations=PLANT_DILATE)
            k = 2 * BAND_PX + 1
            hi = ndimage.maximum_filter(inst, size=k)
            lo = ndimage.minimum_filter(inst, size=k)
            boundary = (hi != lo) & (hi > 0)
            cls = np.full((h, w), 255, np.uint8)
            cls[(inst == 0) & ~plant] = 0
            cls[(inst > 0) & ~boundary] = 1
            cls[boundary] = 2
            stem = Path(photo).stem
            Image.fromarray(small.astype(np.uint8)).save(out / f'{stem}.jpg', quality=92)
            Image.fromarray(cls).save(out / f'{stem}_classes.png')
            Image.fromarray(inst.astype(np.uint16)).save(out / f'{stem}_instances.png')
            plant_id = obs[0]['plant_id']
            view = stem.rsplit('_', 1)[-1]
            split = 'train' if plant_id != val_plant else ('val' if int(view) % 2 == 0 else 'train')
            counts = {c: int((cls == v).sum()) for c, v in (('background', 0), ('interior', 1), ('boundary', 2), ('ignore', 255))}
            photos.append(dict(photo=stem, plant=plant_id, view=view, split=split, size=[w, h], leaflets=ids, pixels=counts))
    doc = dict(schema=SCHEMA, sources=sources, scale=SCALE, band_px=BAND_PX, exg_min=EXG_MIN, plant_dilate=PLANT_DILATE,
               classes={'0': 'background', '1': 'interior', '2': 'boundary', '255': 'ignore'}, val_plant=val_plant, photos=photos,
               note='accepted 2D masks only; plant pixels outside accepted masks are ignore, not background')
    write_json(out / 'index.json', doc)
    return dict(out=str(out), photos=len(photos), train=sum(p['split'] == 'train' for p in photos),
                val=sum(p['split'] == 'val' for p in photos), leaflets=sum(len(p['leaflets']) for p in photos))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--export', action='append', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--val-plant', default='dwt_02')
    a = ap.parse_args()
    print(json.dumps(build(a.export, a.out, a.val_plant), ensure_ascii=False))


if __name__ == '__main__':
    main()
