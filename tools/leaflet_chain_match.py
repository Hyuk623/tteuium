"""Pose-free cross-view leaflet matching from image features (user idea 2026-09-27, after the Alocasia farm dedupe).

    python -X utf8 -m tools.leaflet_chain_match --plant dwt_03 --out build/leaflet_chains_<date>/dwt_03 [--evaluate]

Every human-accepted leaflet mask of every photo takes part, posed or not. SIFT keypoints of each photo (half
resolution) are assigned to the mask they fall in; for every photo pair, mutual ratio-test matches are counted per
mask pair, and a homography with RANSAC keeps the matches consistent with one (near-planar) leaflet surface. A mask
pair counts when its inliers reach MIN_INLIERS and each is the other's best partner. Pairs are joined into chains
(union-find); a chain with two masks of one photo contradicts itself and is flagged, not merged. Colour similarity
(HSV histogram, as in the Alocasia dedupe) is reported per pair as a second opinion; it does not decide.

--evaluate scores the pairs against the person's same/different decisions saved for this plant
(threshold-decision-log-1 'match' records). Output: pairs.json, chains.json, report.json. Proposals only.
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
SCALE = 0.5
MAX_FEATURES, RATIO = 12000, 0.8
MIN_MATCHES, MIN_INLIERS, RANSAC_PX = 6, 8, 6.0


def ring_distance(a: str, b: str) -> tuple[str, int]:
    """Photos 11-18 and 21-28 are two rings of 8 positions 45 deg apart; 01/03 are top views."""
    if a[0] == b[0] and a[0] in '12':
        d = abs(int(a[1]) - int(b[1])) % 8
        return ('same_ring', min(d, 8 - d))
    if {a[0], b[0]} == {'1', '2'}:
        d = abs(int(a[1]) - int(b[1])) % 8
        return ('cross_ring', min(d, 8 - d))
    return ('top', -1)


def photo_features(batch, items):
    """SIFT on one photo at half resolution, each keypoint tagged with the accepted mask it lies in (-1: none)."""
    img = Image.open(batch.session / items[0]['image_path']).convert('RGB')
    W, H = img.size
    w, h = int(W * SCALE), int(H * SCALE)
    lab = np.full((H, W), -1, np.int32)
    area = np.full((H, W), np.inf)
    hsv = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2HSV)
    hists = {}
    for k, it in enumerate(items):
        m, meta = batch.mask(it)
        x0, y0 = meta['crop_px'][:2]
        full = np.zeros((H, W), bool)
        full[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = m
        a = full.sum()
        take = full & (a < area)
        lab[take], area[take] = k, a
        px = hsv[full]
        hh = cv2.calcHist([px.reshape(-1, 1, 3)], [0, 1], None, [18, 8], [0, 180, 0, 256]).ravel()
        hists[k] = hh / max(hh.sum(), 1)
    small = np.asarray(img.convert('L').resize((w, h), Image.BILINEAR))
    lab_s = cv2.resize(lab.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    sift = cv2.SIFT_create(nfeatures=MAX_FEATURES)
    kp, desc = sift.detectAndCompute(small, ((lab_s >= 0) * 255).astype(np.uint8))
    if desc is None:
        return np.zeros((0, 2)), np.zeros((0, 128), np.float32), np.zeros(0, int), hists
    xy = np.array([k.pt for k in kp])
    owner = lab_s[np.clip(xy[:, 1].astype(int), 0, h - 1), np.clip(xy[:, 0].astype(int), 0, w - 1)]
    return xy, desc.astype(np.float32), owner, hists


def mutual(a, b):
    if len(a) < 2 or len(b) < 2:
        return []
    fl = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=64))
    f = {m.queryIdx: m.trainIdx for m, n in fl.knnMatch(a, b, k=2) if m.distance < RATIO * n.distance}
    g = {m.queryIdx: m.trainIdx for m, n in fl.knnMatch(b, a, k=2) if m.distance < RATIO * n.distance}
    return [(i, j) for i, j in f.items() if g.get(j) == i]


def build(plant: str, out: Path, evaluate: bool = False) -> dict:
    from tools.leaflet_mask_batch import Batch
    cfg = read_json(CONFIG)['plants'][plant]
    b = Batch(ROOT / cfg['batch'])
    accepted = [b.item(i) for i in b.manifest['ids'] if b.item(i)['review'] in ('accepted', 'accepted_by_user')]
    by_photo = defaultdict(list)
    for it in accepted:
        by_photo[it['image_file']].append(it)
    feats = {}
    for photo, items in sorted(by_photo.items()):
        feats[photo] = (items,) + photo_features(b, items)
    pairs = []
    for pa, pb in combinations(sorted(feats), 2):
        ia, xa, da, oa, ha = feats[pa]
        ib, xb, db, ob, hb = feats[pb]
        kind, dist = ring_distance(pa[-6:-4], pb[-6:-4])
        per = defaultdict(list)
        for i, j in mutual(da, db):
            if oa[i] >= 0 and ob[j] >= 0:
                per[(oa[i], ob[j])].append((xa[i], xb[j]))
        scored = {}
        for (ma, mb), m in per.items():
            if len(m) < MIN_MATCHES:
                continue
            A = np.array([p for p, _ in m], np.float32); B = np.array([q for _, q in m], np.float32)
            Hm, inl = cv2.findHomography(A, B, cv2.RANSAC, RANSAC_PX)
            n = int(inl.sum()) if inl is not None else 0
            if n >= MIN_INLIERS:
                scored[(ma, mb)] = n
        best_a, best_b = {}, {}
        for (ma, mb), n in scored.items():
            if n > best_a.get(ma, (0, None))[0]: best_a[ma] = (n, mb)
            if n > best_b.get(mb, (0, None))[0]: best_b[mb] = (n, ma)
        for (ma, mb), n in scored.items():
            if best_a[ma][1] == mb and best_b[mb][1] == ma:
                colour = float(cv2.compareHist(ha[ma].astype(np.float32), hb[mb].astype(np.float32), cv2.HISTCMP_BHATTACHARYYA))
                pairs.append(dict(a=ia[ma]['id'], b=ib[mb]['id'], photo_a=pa[-6:-4], photo_b=pb[-6:-4], ring=kind, ring_distance=dist,
                                  inliers=n, colour_distance=round(colour, 3)))
    # chains
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x
    for p in pairs:
        parent[find(p['a'])] = find(p['b'])
    photo_of = {it['id']: it['image_file'][-6:-4] for it in accepted}
    groups = defaultdict(list)
    for m in list(parent):
        groups[find(m)].append(m)
    chains = []
    for n, (root, ms) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1])), 1):
        photos = [photo_of[m] for m in ms]
        chains.append(dict(chain=f'C{n:03d}', masks=sorted(ms), photos=sorted(photos), conflict=len(set(photos)) < len(photos),
                           posed_photos=None))
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'pairs.json', pairs)
    write_json(out / 'chains.json', chains)
    report = dict(plant=plant, accepted_masks=len(accepted), photos=len(feats), pairs=len(pairs),
                  chains=len(chains), chains_conflict=sum(c['conflict'] for c in chains),
                  masks_in_chains=sum(len(c['masks']) for c in chains if not c['conflict']),
                  pairs_by_ring={k: sum(1 for p in pairs if (p['ring'], p['ring_distance']) == k) for k in
                                 sorted({(p['ring'], p['ring_distance']) for p in pairs})},
                  parameters=dict(scale=SCALE, max_features=MAX_FEATURES, ratio=RATIO, min_matches=MIN_MATCHES,
                                  min_inliers=MIN_INLIERS, ransac_px=RANSAC_PX))
    report['pairs_by_ring'] = {f'{k[0]}:{k[1]}': v for k, v in report['pairs_by_ring'].items()}
    if evaluate:
        report['evaluation'] = evaluate_against_decisions(plant, pairs)
    write_json(out / 'report.json', report)
    return report


def evaluate_against_decisions(plant, pairs):
    """Person's same/different answers on cross-view 'match' questions vs this method's pairs."""
    ours = {frozenset((p['a'], p['b'])): p['inliers'] for p in pairs}
    rows = []
    for f in glob.glob(str(ROOT / 'build' / '**' / 'decisions' / '*.json'), recursive=True):
        try:
            d = read_json(Path(f))
        except Exception:
            continue
        det = d.get('decision_detail') or {}
        if d.get('plant_id') != plant or det.get('kind') != 'match' or d.get('decision') not in ('same', 'different'):
            continue
        ids = [g['mask_ids'][0] for g in det.get('masks', []) if g.get('mask_ids')]
        if len(ids) == 2:
            rows.append((frozenset(ids), d['decision']))
    tp = sum(1 for k, v in rows if v == 'same' and k in ours)
    fn = sum(1 for k, v in rows if v == 'same' and k not in ours)
    fp = sum(1 for k, v in rows if v == 'different' and k in ours)
    tn = sum(1 for k, v in rows if v == 'different' and k not in ours)
    return dict(decisions=len(rows), same_found=tp, same_missed=fn, different_wrongly_paired=fp, different_correctly_apart=tn)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--plant', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--evaluate', action='store_true')
    a = ap.parse_args()
    print(json.dumps(build(a.plant, a.out, a.evaluate), ensure_ascii=False))


if __name__ == '__main__':
    main()
