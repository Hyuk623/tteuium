"""Oriented leaflet boxes from human-accepted masks, for a rotated-box (OBB) detector trial (user decision 2026-09-25).

    python -X utf8 -m tools.leaflet_obb_dataset --out build/leaflet_obb_<date>/upload/dataset

Each accepted leaflet mask of dwt_01/dwt_02 becomes the minimum-area rotated rectangle around its largest outline
(ultralytics OBB format: class + 4 normalised corners). The rectangle's long side is the leaflet's axis in the photo,
which the tip-direction task can reuse. Rejected masks are left out (a rejection says the draft was wrong, not where
the leaflet is), so a few real leaflets are unlabelled -- counted in index.json. Split as the SAM trial: dwt_01 and
the odd views of dwt_02 train, the even views of dwt_02 validate.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = {'dwt_01': ('build/new_captures_20260920/dwt_01/edit_session', 'build/leaflet_mask_batch_20260922/dwt_01',
                      'build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260924_231659_618535'),
           'dwt_02': ('build/new_captures_20260920/dwt_02/edit_session', 'build/leaflet_mask_batch_20260922/dwt_02',
                      'build/leaflet_mask_batch_20260922/dwt_02/exports/accepted_20260924_231624_807db7'),
           'dwt_03': ('build/new_captures_20260921/dwt_03/edit_session', 'build/leaflet_mask_batch_20260925_tuned/dwt_03',
                      'build/leaflet_mask_batch_20260925_tuned/dwt_03/exports/accepted_20260927_180537_994cba'),
           'dwt_04': ('build/new_captures_20260921/dwt_04/edit_session', 'build/leaflet_mask_batch_20260925_tuned/dwt_04',
                      'build/leaflet_mask_batch_20260925_tuned/dwt_04/exports/accepted_20260927_180653_457bce')}
STORE_PX = 1536


def build(out: Path) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    rows = []
    for plant, (session, batch_root, export) in EXPORTS.items():
        acc = read_json(ROOT / export / 'accepted.json')
        by_photo = defaultdict(list)
        for ob in acc['observations']:
            by_photo[ob['image_file']].append(ob)
        rejected = defaultdict(int)
        for f in (ROOT / batch_root / 'items').glob('*.json'):
            it = read_json(f)
            if it['review'] == 'rejected':
                rejected[it['image_file']] += 1
        for photo, obs in sorted(by_photo.items()):
            stem = Path(photo).stem
            view = int(stem.rsplit('_', 1)[-1])
            split = 'val' if plant == 'dwt_02' and view % 2 == 0 else 'train'
            (out / split / 'images').mkdir(parents=True, exist_ok=True)
            (out / split / 'labels').mkdir(parents=True, exist_ok=True)
            img = Image.open(ROOT / session / 'images' / photo).convert('RGB')
            W, H = img.size
            lines, axes = [], []
            for ob in obs:
                m = (np.asarray(Image.open(ROOT / export / ob['mask_file'])) > 0).astype(np.uint8)
                cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not cs:
                    continue
                rect = cv2.minAreaRect(max(cs, key=cv2.contourArea))
                pts = cv2.boxPoints(rect) / [W, H]
                lines.append('0 ' + ' '.join(f'{v:.5f}' for v in np.clip(pts, 0, 1).ravel()))
                (w, h), ang = rect[1], rect[2]
                axes.append(round(float(ang if w >= h else ang + 90) % 180, 1))
            img.thumbnail((STORE_PX, STORE_PX))
            img.save(out / split / 'images' / f'{stem}.jpg', quality=92)
            (out / split / 'labels' / f'{stem}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
            rows.append(dict(plant=plant, photo=stem, split=split, leaflets=len(lines), rejected_unlabelled=rejected.get(photo, 0),
                             long_axis_deg=axes))
    write_json(out / 'data.yaml.json', dict(train='train/images', val='val/images', nc=1, names=['leaflet']))
    doc = dict(schema='leaflet-obb-dataset-1', photos=rows, note='minAreaRect of accepted masks; long_axis_deg in image frame, 0-180')
    write_json(out / 'index.json', doc)
    return dict(out=str(out), train=sum(r['leaflets'] for r in rows if r['split'] == 'train'),
                val=sum(r['leaflets'] for r in rows if r['split'] == 'val'),
                rejected_unlabelled=sum(r['rejected_unlabelled'] for r in rows))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, type=Path)
    print(json.dumps(build(ap.parse_args().out), ensure_ascii=False))


if __name__ == '__main__':
    main()
