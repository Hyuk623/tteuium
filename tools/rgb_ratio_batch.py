"""Masked R/G/B fractions for every reviewed organ of every configured plant, under each preprocessing (2026-09-29).

    python -X utf8 -m tools.rgb_ratio_batch --out build/rgb_ratio_batch_<date> [--plants dwt_01 dwt_02]

Scales Codex's single-leaflet lab (tools/leaf_preprocess_lab.py, handoff CLAUDE_RGB_PREPROCESSING_AND_MASKED_RATIOS)
to all reviewed observations, reusing its numerical helpers instead of copying formulas:

* organs: reviewed leaflet masks (newest accepted export, review 'accepted_by_user') and the person's main-stem /
  sub-stem polygons (eroded 2 px, leaflet pixels removed). Photo-level observations - not unique physical organs.
* preprocessing variants: the lab's PRESETS through ``enhance`` (photometric only, same pixel grid) plus one Claude
  addition, ``grayworld`` (per-photo channel gains so the photo's mean R, G and B are equal; lighting normalisation).
* ratio bases, kept apart as the handoff requires: ``stored`` = channel/(R+G+B) of the stored 8-bit values
  (``full_channel_fraction``, Workflow B); ``linear`` = the same on linearised sRGB (``colour_ratios``, Workflow A).
  Masks are applied after the ratio is computed; undefined pixels (R+G+B=0) are NaN and skipped.

Outputs: observations.csv (one row per observation x variant x basis: median / p10 / p90 of r, g, b and hue),
separability.json (object-level leaf-vs-stem AUC per feature, pooled and per plant, plus a leave-one-plant-out
threshold test) and README.md. Original photos, masks and polygons are read only. Nothing here segments, classifies
or trains; the numbers describe how far colour alone separates what a person already labelled.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tools import leaf_preprocess_lab as lab
from tools.leaf_light.common import file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
STEM_CLASSES = ('main-stem', 'sub-stem')
SAMPLE = 3000  # pixels per observation (seeded), enough for stable medians
VARIANTS = [dict(id=p['id'], settings=p['settings']) for p in lab.PRESETS] + [dict(id='grayworld', settings=None)]
FEATURES = ('r', 'g', 'b', 'hue')


def grayworld(rgb: np.ndarray) -> np.ndarray:
    x = rgb.astype(np.float32)
    means = x.reshape(-1, 3).mean(0)
    return np.clip(np.rint(x * (means.mean() / np.maximum(means, 1e-6))), 0, 255).astype(np.uint8)


def variant_image(rgb: np.ndarray, v: dict) -> np.ndarray:
    return grayworld(rgb) if v['id'] == 'grayworld' else lab.enhance(rgb, v['settings'])


def ratios(rgb: np.ndarray, basis: str) -> np.ndarray:
    """H x W x 3 fractions, NaN where undefined."""
    if basis == 'stored':
        return np.dstack([lab.full_channel_fraction(rgb, c)[0] for c in ('red', 'green', 'blue')])
    frac, valid = lab.colour_ratios(lab.linear_rgb(rgb))
    frac[~valid] = np.nan
    return frac


def observations(plant: str, pc: dict) -> dict[str, list[dict]]:
    """{image_file: [dict(id, cls, mask bool HxW or loader)]} for reviewed leaflets and human stem polygons."""
    exp = sorted((ROOT / pc['batch'] / 'exports').glob('accepted_*'))[-1]
    acc = read_json(exp / 'accepted.json')
    per = {}
    for o in acc['observations']:
        if o.get('organ_class', 'leaflet') == 'leaflet' and o.get('review') == 'accepted_by_user':
            per.setdefault(o['image_file'], []).append(dict(id=o['id'], cls='leaflet', mask_file=exp / o['mask_file']))
    dets = read_json(ROOT / pc['labels'] / 'seed_with_imports.backup.json')['variants']['__all__']['membership']['detections']
    for img, ds in dets.items():
        for d in ds:
            if d['class_name'] in STEM_CLASSES and d.get('rings'):
                per.setdefault(img, []).append(dict(id=d.get('annotation_id') or f'{img}#{len(per.get(img, []))}',
                                                    cls=d['class_name'], rings=d['rings']))
    return dict(export=str(exp.relative_to(ROOT)), export_sha256=file_hash(exp / 'accepted.json'), per_image=per)


def masks_for(objs: list[dict], shape: tuple[int, int]) -> list[np.ndarray]:
    leafany = np.zeros(shape, bool)
    out = []
    for o in objs:
        if o['cls'] == 'leaflet':
            m = np.asarray(Image.open(o['mask_file'])) > 0
            if m.shape != shape:
                raise ValueError(f"mask {o['mask_file']} does not match the photo")
            leafany |= m
            out.append(m)
        else:
            out.append(None)
    for i, o in enumerate(objs):
        if o['cls'] != 'leaflet':
            m = np.zeros(shape, np.uint8)
            for ring in o['rings']:
                cv2.fillPoly(m, [np.round(np.array(ring)).astype(np.int32)], 1)
            out[i] = cv2.erode(m, np.ones((5, 5), np.uint8)).astype(bool) & ~leafany
    return out


def run(out: Path, plants: list[str] | None = None, config: Path = CONFIG) -> dict:
    out = Path(out)
    if out.exists():
        raise SystemExit(f'output exists: {out}')
    cfg = read_json(config)['plants']
    plants = plants or list(cfg)
    rng = np.random.default_rng(0)
    rows, sources = [], {}
    for plant in plants:
        pc = cfg[plant]
        session = ROOT / pc['capture'] / 'edit_session'
        frames = {f['image_file']: f for f in read_json(session / 'capture.json')['frames']}
        obs = observations(plant, pc)
        sources[plant] = dict(export=obs['export'], export_sha256=obs['export_sha256'], photos={})
        for img, objs in sorted(obs['per_image'].items()):
            if img not in frames:
                continue
            path = session / frames[img]['image_path']
            sources[plant]['photos'][img] = file_hash(path)
            rgb = np.asarray(Image.open(path).convert('RGB'))
            ms = masks_for(objs, rgb.shape[:2])
            picks = []  # sampled pixel coordinates per observation, fixed across variants
            for m in ms:
                ys, xs = np.nonzero(m)
                if len(ys) < 50:
                    picks.append(None)
                    continue
                k = rng.choice(len(ys), min(SAMPLE, len(ys)), replace=False)
                picks.append((ys[k], xs[k], int(len(ys))))
            for v in VARIANTS:
                im = variant_image(rgb, v)
                for basis in ('stored', 'linear'):
                    for o, pk in zip(objs, picks):
                        if pk is None:
                            continue
                        ys, xs, n_px = pk
                        sel = im[ys, xs][None]  # 1 x N x 3: ratios and hue only where sampled (same formulas)
                        px = ratios(sel, basis)[0]
                        hue = cv2.cvtColor(sel, cv2.COLOR_RGB2HSV)[0, :, 0].astype(np.float32) * 2
                        ok = ~np.isnan(px).any(1)
                        row = dict(plant=plant, image_file=img, observation=o['id'], cls=o['cls'], variant=v['id'], basis=basis,
                                   pixels=n_px, sampled=int(ok.sum()))
                        for k, name in enumerate('rgb'):
                            q = np.percentile(px[ok, k], [10, 50, 90])
                            row.update({f'{name}_p10': q[0], f'{name}_med': q[1], f'{name}_p90': q[2]})
                        row['hue_med'] = float(np.median(hue))
                        rows.append(row)
            print(plant, img, len(objs), file=sys.stderr, flush=True)
    out.mkdir(parents=True)
    with open(out / 'observations.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
    sep = separability(rows)
    write_json(out / 'separability.json', dict(schema='rgb-ratio-separability-1', sources=sources, **sep))
    return sep


def _auc(pos: np.ndarray, neg: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(np.r_[np.ones(len(pos)), np.zeros(len(neg))], np.r_[pos, neg]))


def separability(rows: list[dict]) -> dict:
    """Leaf vs stem (main + sub) per variant x basis x feature: pooled AUC (direction-free), per-plant AUC, and a
    leave-one-plant-out single threshold (direction and cut learned on the other plants, balanced accuracy reported)."""
    res = {}
    plants = sorted({r['plant'] for r in rows})
    for v in [x['id'] for x in VARIANTS]:
        for basis in ('stored', 'linear'):
            sub = [r for r in rows if r['variant'] == v and r['basis'] == basis]
            for feat in FEATURES:
                key = f'{feat}_med'
                leaf = np.array([r[key] for r in sub if r['cls'] == 'leaflet'])
                stem = np.array([r[key] for r in sub if r['cls'] in STEM_CLASSES])
                if not len(leaf) or not len(stem):
                    continue
                a = _auc(leaf, stem)
                per_plant, lopo = {}, {}
                for p in plants:
                    lp = np.array([r[key] for r in sub if r['plant'] == p and r['cls'] == 'leaflet'])
                    sp = np.array([r[key] for r in sub if r['plant'] == p and r['cls'] in STEM_CLASSES])
                    if len(lp) and len(sp):
                        per_plant[p] = round(_auc(lp, sp), 3)
                    lt = np.array([r[key] for r in sub if r['plant'] != p and r['cls'] == 'leaflet'])
                    st = np.array([r[key] for r in sub if r['plant'] != p and r['cls'] in STEM_CLASSES])
                    sign = 1.0 if _auc(lt, st) >= 0.5 else -1.0  # leaf side of the cut
                    cands = np.unique(np.r_[lt, st])
                    bal = [(np.mean(sign * lt >= sign * c) + np.mean(sign * st < sign * c)) / 2 for c in cands]
                    c = cands[int(np.argmax(bal))]
                    if len(lp) and len(sp):
                        lopo[p] = dict(cut=round(float(c), 4), leaf_side='above' if sign > 0 else 'below',
                                       balanced_accuracy=round(float((np.mean(sign * lp >= sign * c) + np.mean(sign * sp < sign * c)) / 2), 3))
                res[f'{v}|{basis}|{feat}'] = dict(
                    variant=v, basis=basis, feature=feat, n_leaf=len(leaf), n_stem=len(stem),
                    auc=round(max(a, 1 - a), 3), higher='leaf' if a >= 0.5 else 'stem', per_plant_auc=per_plant,
                    lopo_threshold=lopo,
                    lopo_mean_balanced_accuracy=round(float(np.mean([x['balanced_accuracy'] for x in lopo.values()])), 3) if lopo else None)
    ranked = sorted(res.values(), key=lambda x: -(x['lopo_mean_balanced_accuracy'] or 0))
    return dict(results=res, ranking=[dict(key=f"{x['variant']}|{x['basis']}|{x['feature']}", auc=x['auc'], higher=x['higher'],
                                           lopo_mean_balanced_accuracy=x['lopo_mean_balanced_accuracy']) for x in ranked],
                note='object level (median of each photo-level observation); leaf = reviewed leaflet masks, stem = main-stem + '
                     'sub-stem polygons. LOPO: cut and direction chosen on 3 plants, scored on the 4th. Describes colour only; '
                     'no segmentation or classification was run.')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--plants', nargs='*')
    ap.add_argument('--config', type=Path, default=CONFIG)
    a = ap.parse_args()
    r = run(a.out, a.plants, a.config)
    print(json.dumps(r['ranking'][:12], ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
