"""Frozen self-supervised appearance features for cross-view leaflet proposals (Stage 5, 2026-09-30).

    python -X utf8 -m tools.xview_appearance extract --out build/xview_appearance_<date>      # all configured plants
    python -X utf8 -m tools.xview_appearance evaluate --features build/xview_appearance_<date>

Encoder: public DINOv2 ViT-S/14 (facebookresearch/dinov2 via torch.hub), frozen. No tomato model is trained here, so
this is a ranking baseline, not a trained re-identification model: after excluding the evaluation plant dwt_02 only
70 answered pairs on 3 plants remain, too few independent identities to fit a metric head.

Per human-accepted observation (photo-level, not a physical leaflet):
* masked crop: the mask's bounding box plus 15 % context, pixels outside the mask set to mid grey; the original crop
  (with context) is embedded too, kept as a second vector;
* each crop is embedded at 224 px in 8 poses (4 rotations x mirror) and averaged, because the same leaflet is seen at
  different roll angles from different photos; the CLS token is L2-normalised.

Scores are cosine similarities of mask-set means. Evaluation uses only human answers: 'same' pairs are positives and
'different' pairs negatives; unresolved pairs are unknown and never negatives. Thresholds (the unmatched cut of the
one-to-one assignment) are chosen on the development plant dwt_01 only.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
ENCODER = dict(repo='facebookresearch/dinov2', name='dinov2_vits14', input_px=224, poses=8)
CONTEXT = 0.15
ROLES = {'dwt_03': 'train', 'dwt_04': 'train', 'dwt_01': 'development', 'dwt_02': 'evaluation'}
TIE_DELTA = 0.02
MIN_DEV_PAIRS = 30


def _encoder():
    import torch
    m = torch.hub.load(ENCODER['repo'], ENCODER['name'], trust_repo=True)
    m.eval()
    return m


def crops(photo: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    m = int(max(y1 - y0, x1 - x0) * CONTEXT)
    y0, x0 = max(0, y0 - m), max(0, x0 - m)
    y1, x1 = min(photo.shape[0], y1 + m), min(photo.shape[1], x1 + m)
    ctx = photo[y0:y1, x0:x1]
    masked = ctx.copy()
    masked[~mask[y0:y1, x0:x1]] = 128
    return masked, ctx


def _square(a: np.ndarray, size: int) -> np.ndarray:
    h, w = a.shape[:2]
    s = max(h, w)
    canvas = np.full((s, s, 3), 128, np.uint8)
    canvas[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = a
    return np.asarray(Image.fromarray(canvas).resize((size, size), Image.BICUBIC))


def embed(model, images: list[np.ndarray]) -> np.ndarray:
    import torch
    mean, std = np.array([0.485, 0.456, 0.406]), np.array([0.229, 0.224, 0.225])
    out = []
    for a in images:
        sq = _square(a, ENCODER['input_px'])
        poses = [np.rot90(sq, k) for k in range(4)] + [np.rot90(sq[:, ::-1], k) for k in range(4)]
        x = torch.tensor(np.stack([(p / 255.0 - mean) / std for p in poses]).transpose(0, 3, 1, 2), dtype=torch.float32)
        with torch.no_grad():
            f = model(x).numpy()
        f = f / np.linalg.norm(f, axis=1, keepdims=True)
        v = f.mean(0)
        out.append(v / np.linalg.norm(v))
    return np.array(out, np.float32)


def extract(out: Path, plants: list[str] | None = None, config: Path = CONFIG) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    cfg = read_json(config)['plants']
    model = _encoder()
    out.mkdir(parents=True)
    prov = dict(schema='xview-appearance-1', encoder=ENCODER, context=CONTEXT, background='mid grey outside the mask',
                trained=False, plants={})
    for plant in plants or list(cfg):
        pc = cfg[plant]
        session = ROOT / pc['capture'] / 'edit_session'
        frames = {f['image_file']: f for f in read_json(session / 'capture.json')['frames']}
        exp = sorted((ROOT / pc['batch'] / 'exports').glob('accepted_*'))[-1]
        obs = [o for o in read_json(exp / 'accepted.json')['observations'] if o['review'] == 'accepted_by_user']
        ids, photos, masked_f, ctx_f = [], [], [], []
        by_photo = defaultdict(list)
        for o in obs:
            by_photo[o['image_file']].append(o)
        for img, os_ in sorted(by_photo.items()):
            photo = np.asarray(Image.open(session / frames[img]['image_path']).convert('RGB'))
            pairs = [crops(photo, np.asarray(Image.open(exp / o['mask_file'])) > 0) for o in os_]
            masked_f.append(embed(model, [p[0] for p in pairs]))
            ctx_f.append(embed(model, [p[1] for p in pairs]))
            ids += [o['id'] for o in os_]
            photos += [img] * len(os_)
        np.savez(out / f'{plant}.npz', ids=np.array(ids), photos=np.array(photos), masked=np.concatenate(masked_f), context=np.concatenate(ctx_f))
        prov['plants'][plant] = dict(role=ROLES.get(plant), export=str(exp.relative_to(ROOT)).replace('\\', '/'),
                                     accepted_sha256=file_hash(exp / 'accepted.json'), observations=len(ids))
        print(plant, len(ids), flush=True)
    write_json(out / 'features.json', prov)
    return prov


def load(features: Path, plant: str) -> dict:
    z = np.load(Path(features) / f'{plant}.npz')
    return dict(ids=list(z['ids']), photos=list(z['photos']), masked=z['masked'], context=z['context'])


def set_vector(F: dict, ids, kind='masked') -> np.ndarray | None:
    pos = {k: i for i, k in enumerate(F['ids'])}
    rows = [F[kind][pos[i]] for i in ids if i in pos]
    if not rows:
        return None
    v = np.mean(rows, 0)
    return v / np.linalg.norm(v)


def assign(S: np.ndarray, cut: float) -> tuple[list[tuple[int, int, float]], list[dict]]:
    """One-to-one assignment with an unmatched option (a pair is kept only if its similarity >= cut) plus flags:
    'tie' when a row's runner-up is within TIE_DELTA of its assigned score, 'contested' when another row's best column
    is the same one. Nothing is forced: rows and columns may stay unmatched."""
    from scipy.optimize import linear_sum_assignment
    if S.size == 0:
        return [], []
    r, c = linear_sum_assignment(-S)
    pairs = [(i, j, float(S[i, j])) for i, j in zip(r, c) if S[i, j] >= cut]
    flags = []
    best_col = S.argmax(1)
    for i, j, s in pairs:
        f = []
        row = np.sort(S[i])[::-1]
        if len(row) > 1 and row[0] - row[1] <= TIE_DELTA:
            f.append('tie')
        if (best_col == j).sum() > 1:
            f.append('contested')
        flags.append(dict(row=i, col=j, score=round(s, 4), flags=f))
    return pairs, flags


def cycles(links: dict) -> list[tuple]:
    """Contradictory cycles across three photos: a~b and b~c assigned, but a is assigned to some c' != c."""
    bad = []
    for (pa, pb), m in links.items():
        for (pb2, pc), m2 in links.items():
            if pb2 != pb or pc == pa:
                continue
            m3 = links.get((pa, pc)) or {v: k for k, v in links.get((pc, pa), {}).items()}
            for a, b in m.items():
                c = m2.get(b)
                if c is not None and a in m3 and m3[a] != c:
                    bad.append((a, b, c, m3[a]))
    return bad


def evaluate(features: Path, config: Path = CONFIG) -> dict:
    from sklearn.metrics import roc_auc_score
    from tools import decision_learning as dl
    cfg = read_json(config)
    rows = dl.xview_rows(cfg)
    F = {p: load(features, p) for p in cfg['plants'] if (Path(features) / f'{p}.npz').exists()}
    per = {}
    scored = []
    for r in rows:
        f = F.get(r['plant'])
        if not f:
            continue
        va, vb = set_vector(f, r['masks_a']), set_vector(f, r['masks_b'])
        ca, cb = set_vector(f, r['masks_a'], 'context'), set_vector(f, r['masks_b'], 'context')
        if va is None or vb is None:
            continue
        pos = {k: i for i, k in enumerate(f['ids'])}
        pa = f['photos'][pos[r['masks_a'][0]]]
        pb = f['photos'][pos[r['masks_b'][0]]]
        # rank of the answered partner among every observation of the other photo (retrieval view)
        others = [k for k, ph in zip(f['ids'], f['photos']) if ph == pb]
        sims = sorted(((float(va @ set_vector(f, [k])), k) for k in others), reverse=True)
        rank = next((n + 1 for n, (_, k) in enumerate(sims) if k in r['masks_b']), None)
        scored.append(dict(plant=r['plant'], label=r['label'], masked=float(va @ vb), context=float(ca @ cb), rank=rank,
                           candidates=len(others), photo_a=pa, photo_b=pb, a=r['masks_a'], b=r['masks_b']))
    for p in F:
        s = [x for x in scored if x['plant'] == p]
        y = np.array([x['label'] for x in s])
        d = dict(role=ROLES.get(p), pairs=len(s), same=int(y.sum()), different=int((1 - y).sum()))
        for k in ('masked', 'context'):
            d[f'auc_{k}'] = round(float(roc_auc_score(y, [x[k] for x in s])), 3) if len(set(y)) == 2 else None
        ranks = [x['rank'] for x in s if x['label'] == 1 and x['rank']]
        d.update({f'same_partner_in_top{k}': round(float(np.mean([q <= k for q in ranks])), 3) if ranks else None for k in (1, 3, 5)},
                 median_candidates_per_photo=int(np.median([x['candidates'] for x in s])) if s else None)
        per[p] = d
    # unmatched cut from dwt_01 only: the cut maximising F1 of 'same' answers among answered pairs
    dev = [x for x in scored if x['plant'] == 'dwt_01']
    cut = None
    # code review 09-30: 12 answered pairs gave a cut of 0.54 and thousands of links; below MIN_DEV_PAIRS no cut is set,
    # so no appearance-only link is proposed (ranking still works)
    if len(dev) >= MIN_DEV_PAIRS:
        best = -1
        for t in np.arange(0.30, 0.96, 0.01):
            tp = sum(x['masked'] >= t and x['label'] == 1 for x in dev); fp = sum(x['masked'] >= t and x['label'] == 0 for x in dev)
            fn = sum(x['masked'] < t and x['label'] == 1 for x in dev)
            f1 = 2 * tp / max(2 * tp + fp + fn, 1)
            if f1 > best:
                best, cut = f1, round(float(t), 2)
    # one-to-one proposals per photo pair, scored against human answers only (unknown pairs leave the denominator)
    answered = {(tuple(sorted(x['a'])), tuple(sorted(x['b']))): x['label'] for x in scored}
    answered.update({(k[1], k[0]): v for k, v in list(answered.items())})
    for p, f in F.items():
        by_photo = defaultdict(list)
        for k, ph in zip(f['ids'], f['photos']):
            by_photo[ph].append(k)
        phs = sorted(by_photo)
        tp = fp = proposed = unknown = 0
        flags = defaultdict(int)
        links = {}
        for i, a in enumerate(phs):
            for b in phs[i + 1:]:
                A, B = by_photo[a], by_photo[b]
                S = np.array([[float(set_vector(f, [x]) @ set_vector(f, [y])) for y in B] for x in A])
                pairs, fl = assign(S, cut if cut is not None else 1.1)
                links[(a, b)] = {A[x]: B[y] for x, y, _ in pairs}
                for q in fl:
                    for g in q['flags']:
                        flags[g] += 1
                for x, y, _ in pairs:
                    proposed += 1
                    lab = answered.get(((A[x],), (B[y],)))
                    if lab is None:
                        unknown += 1
                    elif lab == 1:
                        tp += 1
                    else:
                        fp += 1
        same_answers = sum(1 for x in scored if x['plant'] == p and x['label'] == 1)
        per[p].update(assignment=dict(cut_from_dwt_01=cut, proposed_links=proposed, answered_links=tp + fp,
                                      confirmed_link_precision=round(tp / (tp + fp), 3) if tp + fp else None,
                                      same_answers_recovered=round(tp / same_answers, 3) if same_answers else None,
                                      unknown_links=unknown, flags=dict(flags), contradictory_cycles=len(cycles(links))))
    doc = dict(schema='xview-appearance-eval-1', features=str(features), encoder=ENCODER, trained=False, per_plant=per,
               note='frozen public encoder, no fit on any plant except the dwt_01 unmatched cut; unresolved pairs are unknown, '
                    'not negatives; dwt_02 identity conflicts (a373-a156, a37-a174) are still open, so its numbers are coverage-limited',
               pairs=scored)
    write_json(Path(features) / 'evaluation.json', doc)
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('extract'); e.add_argument('--out', required=True, type=Path); e.add_argument('--plants', nargs='*')
    v = sub.add_parser('evaluate'); v.add_argument('--features', required=True, type=Path)
    a = ap.parse_args()
    if a.cmd == 'extract':
        extract(a.out, a.plants)
    else:
        d = evaluate(a.features)
        print(json.dumps(d['per_plant'], ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
