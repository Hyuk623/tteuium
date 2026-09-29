"""Weighted late fusion of the leaflet detector members (user: 'each detection its own model, add them with weights').

    python -X utf8 -m tools.leaflet_fusion --oof build/leaflet_detect_20260927/kout --dataset build/leaflet_detect_20260927/upload/dataset

Inputs are the members' held-out predictions (oof_<member>_<plant>.json from the Kaggle kernels: normalised xyxy on
the member's image variant). They are mapped back to original photo pixels (the 'crop' variant through its plant
window), predictions centred in a greyed (uncertain) box are ignored, and boxes are fused per photo with weighted box
fusion: fused score = weighted mean score x (weight share of members that voted) ^ gamma.
Weights are chosen honestly: for each plant, the grid search runs on the other three plants and the chosen weights
are scored on that plant (nested leave-one-plant-out). Reports AP50 per member, per fixed weight set, and nested.
"""
from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from tools.leaf_light.common import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
IOU_FUSE = 0.55
WEIGHTS = [0, 1, 2]
GAMMAS = [0.0, 0.4]
VARIANT = {'A': 'full', 'B': 'full', 'C': 'crop'}


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def ap50(preds, gts):
    P = sorted([(s, k, b) for k, ps in preds.items() for b, s in ps], key=lambda t: -t[0])
    n = sum(len(v) for v in gts.values())
    used = {k: [False] * len(v) for k, v in gts.items()}
    tp = []
    for s, k, b in P:
        best, j = 0.0, -1
        for jj, g in enumerate(gts.get(k, [])):
            o = iou(b, g)
            if o > best and not used[k][jj]:
                best, j = o, jj
        if best >= 0.5:
            used[k][j] = True; tp.append(1)
        else:
            tp.append(0)
    if not tp or n == 0:
        return 0.0, 0.0
    c = np.cumsum(tp); rec = c / n; prec = c / np.arange(1, len(tp) + 1)
    return float(np.mean([prec[rec >= t].max() if (rec >= t).any() else 0 for t in np.linspace(0, 1, 101)])), float(rec[-1])


def wbf(members: dict, weights: dict, gamma: float):
    boxes = sorted([(b, s, m) for m, ps in members.items() if weights[m] > 0 for b, s in ps], key=lambda t: -t[1] * weights[t[2]])
    total = sum(w for w in weights.values() if w > 0)
    clusters = []
    for b, s, m in boxes:
        for cl in clusters:
            if iou(cl['box'], b) > IOU_FUSE:
                cl['items'].append((b, s, m))
                w = np.array([x[1] * weights[x[2]] for x in cl['items']])
                cl['box'] = list((np.array([x[0] for x in cl['items']]) * w[:, None]).sum(0) / w.sum())
                break
        else:
            clusters.append(dict(box=list(b), items=[(b, s, m)]))
    out = []
    for cl in clusters:
        voted = {x[2] for x in cl['items']}
        mean = sum(x[1] * weights[x[2]] for x in cl['items']) / sum(weights[x[2]] for x in cl['items'])
        out.append((cl['box'], mean * (sum(weights[m] for m in voted) / total) ** gamma))
    return out


def load(oof_dir: Path, dataset: Path):
    from tools.leaflet_mask_batch import Batch
    idx = read_json(dataset / 'index.json')
    window = {r['photo']: r['window'] for r in idx['photos']}
    cfg = read_json(CONFIG)['plants']
    gts, grey, size = defaultdict(list), defaultdict(list), {}
    for plant, pc in cfg.items():
        b = Batch(ROOT / pc['batch'])
        for i in b.manifest['ids']:
            it = b.item(i)
            stem = Path(it['image_file']).stem
            size[stem] = it['image_size_px']
            if it['review'] in ('accepted', 'accepted_by_user'):
                m, meta = b.mask(it)
                ys, xs = np.nonzero(m)
                x0, y0 = meta['crop_px'][:2]
                gts[(plant, stem)].append([x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1])
            elif it['review'] == 'rejected' and it.get('reject_reason') != 'false_positive':
                grey[(plant, stem)].append(it['prompts']['box_px'])
    preds = defaultdict(dict)   # member -> (plant, stem) -> [(box, score)]
    for f in sorted(Path(oof_dir).glob('oof_*_*.json')):
        _, member, plant = f.stem.split('_', 2)
        for stem, ps in read_json(f).items():
            W, H = size[stem]
            if VARIANT[member] == 'crop':
                X0, Y0, X1, Y1 = window[stem]
                conv = lambda q: [X0 + q[0] * (X1 - X0), Y0 + q[1] * (Y1 - Y0), X0 + q[2] * (X1 - X0), Y0 + q[3] * (Y1 - Y0)]
            else:
                conv = lambda q: [q[0] * W, q[1] * H, q[2] * W, q[3] * H]
            kept = []
            for q in ps:
                bx = conv(q[:4]); cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
                if any(g[0] <= cx <= g[2] and g[1] <= cy <= g[3] for g in grey[(plant, stem)]):
                    continue
                kept.append((bx, q[4]))
            preds[member][(plant, stem)] = kept
    return preds, gts


def run(oof_dir: Path, dataset: Path) -> dict:
    preds, gts = load(oof_dir, dataset)
    members = sorted(preds)
    plants = sorted({k[0] for k in gts})
    keys = {p: [k for k in gts if k[0] == p] for p in plants}
    def score(weights, gamma, plant_set):
        P, G = {}, {}
        for p in plant_set:
            for k in keys[p]:
                P[k] = wbf({m: preds[m].get(k, []) for m in members}, weights, gamma)
                G[k] = gts[k]
        return ap50(P, G)
    rep = dict(members=members, single={}, grid=[], nested={})
    for m in members:
        w = {x: int(x == m) for x in members}
        rep['single'][m] = {p: round(score(w, 0.0, [p])[0], 4) for p in plants}
        rep['single'][m]['mean'] = round(float(np.mean([rep['single'][m][p] for p in plants])), 4)
    combos = [dict(zip(members, c)) for c in itertools.product(WEIGHTS, repeat=len(members)) if sum(c) > 0]
    table = {}
    for w in combos:
        for g in GAMMAS:
            per = {p: score(w, g, [p])[0] for p in plants}
            table[(tuple(w.values()), g)] = per
            rep['grid'].append(dict(weights=w, gamma=g, per_plant={p: round(v, 4) for p, v in per.items()},
                                    mean=round(float(np.mean(list(per.values()))), 4)))
    for p in plants:
        others = [q for q in plants if q != p]
        best = max(table, key=lambda k: np.mean([table[k][q] for q in others]))
        rep['nested'][p] = dict(chosen_weights=dict(zip(members, best[0])), gamma=best[1], ap50=round(table[best][p], 4))
    rep['nested_mean'] = round(float(np.mean([v['ap50'] for v in rep['nested'].values()])), 4)
    rep['grid'].sort(key=lambda r: -r['mean'])
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--oof', required=True, type=Path)
    ap.add_argument('--dataset', required=True, type=Path)
    a = ap.parse_args()
    rep = run(a.oof, a.dataset)
    write_json(Path(a.oof) / 'fusion_report.json', rep)
    print(json.dumps(dict(single={m: v['mean'] for m, v in rep['single'].items()}, best_fixed=rep['grid'][0],
                          nested_mean=rep['nested_mean'], nested=rep['nested']), ensure_ascii=False))


if __name__ == '__main__':
    main()
