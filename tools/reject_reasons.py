"""Give each already-rejected leaflet mask one of the user's four reasons (2026-09-27), and apply saved answers.

    python -X utf8 -m tools.reject_reasons page --out build/reject_reasons_<date>     # local review page
    python -X utf8 -m tools.reject_reasons apply --plant dwt_01 --batch <batch> --decisions <reject_reasons_*.json>

Reasons: occluded (the visible part is a correct mask -> re-accepted with visibility 'partial'), duplicate_box,
box_misses_leaf, false_positive (these stay rejected, now with a reason). A box that sits >= 70 % inside an accepted
box of the same photo is pre-selected as duplicate_box; everything else starts unanswered. Answers go through
Batch.review, so they are in each item's history and can be undone in the editor.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from tools.leaf_light.common import StudyError, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
REASONS = {'occluded': '가려짐', 'duplicate_box': '복수 박스', 'box_misses_leaf': '잎을 다 못 담음', 'false_positive': '오탐'}


def contained(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max((a[2] - a[0]) * (a[3] - a[1]), 1)


def thumb(batch, it) -> str:
    img = Image.open(batch.session / it['image_path']).convert('RGB')
    x0, y0, x1, y1 = it['prompts']['box_px']
    pad = max(x1 - x0, y1 - y0) * 0.6
    c = (int(max(0, x0 - pad)), int(max(0, y0 - pad)), int(min(img.width, x1 + pad)), int(min(img.height, y1 + pad)))
    t = img.crop(c)
    try:
        m, meta = batch.mask(it)
        cx0, cy0 = meta['crop_px'][:2]
        full = np.zeros((img.height, img.width), bool)
        full[cy0:cy0 + m.shape[0], cx0:cx0 + m.shape[1]] = m
        t = Image.composite(Image.new('RGB', t.size, (255, 0, 255)), t, Image.fromarray((full[c[1]:c[3], c[0]:c[2]] * 110).astype(np.uint8)))
    except Exception:
        pass
    ImageDraw.Draw(t).rectangle([x0 - c[0], y0 - c[1], x1 - c[0], y1 - c[1]], outline=(255, 214, 0), width=5)
    t.thumbnail((360, 360))
    buf = io.BytesIO(); t.save(buf, 'JPEG', quality=78)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def page(out: Path) -> dict:
    from tools.leaflet_mask_batch import Batch
    cfg = read_json(CONFIG)
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    items = []
    for plant, pc in cfg['plants'].items():
        b = Batch(ROOT / pc['batch'])
        all_items = [b.item(i) for i in b.manifest['ids']]
        acc = [it for it in all_items if it['review'] == 'accepted']
        for it in all_items:
            if it['review'] != 'rejected':
                continue
            same = [a for a in acc if a['image_file'] == it['image_file']]
            dup = max([contained(it['prompts']['box_px'], a['prompts']['box_px']) for a in same], default=0)
            items.append(dict(plant=plant, id=it['id'], photo=it['image_file'][-6:-4], img=thumb(b, it),
                              reason=it.get('reject_reason') or ('duplicate_box' if dup >= 0.7 else None), suggested=dup >= 0.7))
    tpl = Path(__file__).with_name('reject_reasons.html').read_text(encoding='utf-8')
    (out / 'review.html').write_text(tpl.replace('__DATA__', json.dumps(dict(items=items, reasons=REASONS), ensure_ascii=False)), encoding='utf-8')
    return dict(page=str(out / 'review.html'), items=len(items), suggested_duplicates=sum(i['suggested'] for i in items))


def apply(plant: str, batch_root: Path, decisions: list[Path]) -> dict:
    from tools.leaflet_mask_batch import Batch
    b = Batch(Path(batch_root))
    answers = {}
    for f in sorted(decisions, key=lambda p: p.stat().st_mtime):   # later files win
        d = read_json(f)
        if d.get('schema') != 'reject-reasons-1':
            continue
        answers.update({k: v for k, v in d['answers'].items() if k.startswith(plant + '_')})
    done = dict(reaccepted_partial=0, reason_set=0, unchanged=0, skipped=[])
    for identity, reason in sorted(answers.items()):
        if identity not in b.manifest['ids'] or reason not in REASONS:
            done['skipped'].append(identity); continue
        it = b.item(identity)
        if it['review'] != 'rejected':
            done['unchanged'] += 1; continue                         # decided again in the editor since: keep that
        if reason == 'occluded':
            try:
                b.review(identity, dict(revision=it['revision'], action='accept', visibility='partial', active_seconds=0))
                done['reaccepted_partial'] += 1
            except StudyError as e:                                    # e.g. empty mask: keep rejected, record why
                b.review(identity, dict(revision=it['revision'], action='reject', active_seconds=0))
                done['skipped'].append(f'{identity}: {e}')
        elif it.get('reject_reason') != reason:
            b.review(identity, dict(revision=it['revision'], action='reject', reason=reason, active_seconds=0))
            done['reason_set'] += 1
        else:
            done['unchanged'] += 1
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p1 = sub.add_parser('page'); p1.add_argument('--out', required=True, type=Path)
    p2 = sub.add_parser('apply'); p2.add_argument('--plant', required=True); p2.add_argument('--batch', required=True, type=Path)
    p2.add_argument('--decisions', nargs='+', required=True, type=Path)
    a = ap.parse_args()
    print(json.dumps(page(a.out) if a.cmd == 'page' else apply(a.plant, a.batch, a.decisions), ensure_ascii=False))


if __name__ == '__main__':
    main()
