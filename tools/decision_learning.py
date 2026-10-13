"""Learn the person's own review decisions so new plants need fewer of them (user, 2026-09-29).

    python -X utf8 -m tools.decision_learning --out build/decision_models_<date>

Two decision types have enough human answers to learn from:

* mask review (S2): accept / reject for every SAM draft of a leaflet box - features the editor already stored with the
  draft (SAM scores, candidate disagreement, outside-box fraction, components, holes, crop-edge touch, overlap with
  neighbouring masks) plus box geometry and overlap with the other boxes of the photo;
* cross-view pairs (S4): same / different for two masks in two photos - co-occurrence shares from the candidate
  generator plus mask sizes, view codes and how many masks each side holds.

Evaluation is leave-one-plant-out. For each decision the model may answer automatically only above a probability
threshold chosen on the training plants for 95 % precision; the rest go to the person. Reported per held-out plant:
AUC, the share of items the model could decide, and the precision it actually reached there. Final models (all plants)
and thresholds are saved for the pipeline; a person's review always overrides them.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np

from tools.leaf_light.common import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
TARGET_PRECISION = 0.95
#: Code review 2026-09-30: score_sel is the score of the DEFAULT candidate (the one a new plant gets), not of the
#: candidate a person later picked (11 % of reviews changed it); neighbor_overlap_max was dropped because the editor
#: never computes it (always missing).
MASK_FEATURES = ['score_max', 'score_sel', 'score_spread', 'candidate_disagreement', 'outside_bbox_fraction', 'components',
                 'holes', 'crop_edge_touch', 'area_px_log', 'fill_ratio', 'box_w_log', 'box_h_log',
                 'box_aspect', 'box_area_frac', 'max_box_overlap', 'boxes_in_photo', 'view_side', 'view_top']
XVIEW_FEATURES = ['share_ab', 'share_ba', 'share_min', 'share_max', 'share_mean', 'n_a', 'n_b', 'area_a_log', 'area_b_log',
                  'area_ratio_log', 'same_view_group', 'view_code_gap', 'feature_pose']


def _iou_frac(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])); iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    return ix * iy / max(a[2] * a[3], 1e-9)


def mask_rows(cfg: dict) -> list[dict]:
    rows = []
    for plant, pc in cfg['plants'].items():
        for row in batch_features(ROOT / pc['batch'], plant):
            if row['review'] in ('accepted', 'rejected') and row['review_source'] not in ('auto', 'auto_model'):
                rows.append(row)
    return rows


def batch_features(batch: Path, plant: str) -> list[dict]:
    """Features of every generated mask of a batch (reviewed or not), as the review model sees them."""
    rows = []
    items = [read_json(f) for f in sorted((Path(batch) / 'items').glob('*.json'))]
    boxes = {}
    for it in items:
        boxes.setdefault(it['image_file'], []).append((it['id'], it['source_bbox_xywh_px']))
    for it in items:
        if it['generation'] != 'ready' or not it.get('cache_key'):
            continue
        try:
            meta = read_json(Path(batch) / 'cache' / it['cache_key'] / 'result.json')
        except OSError:
            continue
        rows.append(_row(plant, it, meta['scores'], meta.get('default_candidate'), meta.get('risk') or {}, boxes))
    return rows


def _row(plant: str, it: dict, scores, default_candidate, risk: dict, boxes: dict) -> dict:
    """Feature row of one reviewed draft: SAM scores + editor risk signals of the draft as FIRST shown, box geometry."""
    sc = [s for s in scores if s is not None]
    d = default_candidate if isinstance(default_candidate, int) and default_candidate < len(scores) and scores[default_candidate] is not None \
        else int(np.argmax(sc))
    x, y, w, h = it['source_bbox_xywh_px']
    W, H = it['image_size_px']
    others = [b for i, b in boxes[it['image_file']] if i != it['id']]
    area = float(risk.get('area_px') or 0)
    return dict(plant=plant, id=it['id'], label=1 if it['review'] == 'accepted' else 0, review=it['review'],
                review_source=it.get('review_source') or 'human',
                reason=it.get('reject_reason') or ('partial' if it.get('visibility') == 'partial' else None),
                edited=bool(it.get('changed')),
                score_max=max(sc), score_sel=float(scores[d]), score_spread=max(sc) - min(sc),
                candidate_disagreement=risk.get('candidate_disagreement', np.nan),
                outside_bbox_fraction=risk.get('outside_bbox_fraction', np.nan), components=risk.get('components', np.nan),
                holes=risk.get('holes', np.nan), crop_edge_touch=float(bool(risk.get('crop_edge_touch'))),
                area_px_log=math.log1p(area), fill_ratio=area / max(w * h, 1.0), box_w_log=math.log(max(w, 1)),
                box_h_log=math.log(max(h, 1)), box_aspect=max(w, h) / max(min(w, h), 1), box_area_frac=w * h / (W * H),
                max_box_overlap=max([_iou_frac(it['source_bbox_xywh_px'], b) for b in others], default=0.0),
                boxes_in_photo=len(others) + 1, view_side=float(it.get('view_group') == 'side'),
                view_top=float(it.get('view_group') == 'top'))


def redraft_rows(cfg: dict, redraft: Path) -> list[dict]:
    """Human-reviewed rows whose draft features come from a re-draft (tools kernel tomato-mask-redraft-run: SAM v5,
    each plant drafted by the held-out model that never saw it, box prompt, default sensitivity, editor functions).
    Labels and box geometry come from the reviewed batch items; nothing of the person's later editing enters a feature."""
    drafts = read_json(Path(redraft))['drafts']
    rows = []
    for plant, pc in cfg['plants'].items():
        items = [read_json(f) for f in sorted((ROOT / pc['batch'] / 'items').glob('*.json'))]
        boxes = {}
        for it in items:
            boxes.setdefault(it['image_file'], []).append((it['id'], it['source_bbox_xywh_px']))
        for it in items:
            dr = drafts.get(it['id'])
            if dr and it['review'] in ('accepted', 'rejected') and (it.get('review_source') or 'human') not in ('auto', 'auto_model'):
                rows.append(_row(plant, it, dr['scores'], dr['default_candidate'], dr['risk'], boxes))
    return rows


def apply_mask_model(batch_dir: Path, model_path: Path, plant: str = '') -> dict:
    """Accept the unreviewed masks the learned review model is confident about (review_source 'auto_model');
    everything else stays for a person. Never rejects: the model could not reject at the target precision."""
    import joblib
    from tools import leaflet_mask_batch as lmb
    bundle = joblib.load(model_path)
    rows = [r for r in batch_features(batch_dir, plant) if r['review'] == 'unreviewed']
    if not rows:
        return dict(candidates=0)
    X = np.array([[r.get(f, np.nan) for f in bundle['features']] for r in rows], float)  # older models list dropped features
    p = bundle['model'].predict_proba(X)[:, 1]
    confident = {r['id'] for r, pi in zip(rows, p) if pi >= bundle['auto_positive']}
    counts = lmb.Batch(Path(batch_dir)).auto_accept(only=confident, source='auto_model')
    return dict(candidates=len(rows), confident=len(confident), threshold=bundle['auto_positive'], **counts,
                left_for_person=len(rows) - counts.get('accepted', 0))


def xview_rows(cfg: dict) -> list[dict]:
    from tools.cross_view_identity_import import load_decisions
    rows = []
    for plant, pc in cfg['plants'].items():
        src = [ROOT / p for p in pc.get('decisions', [])] + [Path(p) for p in glob.glob(str(Path(cfg['downloads']) / f'cross_view_decisions_{plant}_*.json'))]
        src = [p for p in src if p.exists()]
        if not src:
            continue
        batch = ROOT / pc['batch']
        area = {}
        for f in (batch / 'items').glob('*.json'):
            it = read_json(f)
            x, y, w, h = it['source_bbox_xywh_px']
            area[it['id']] = w * h
        for d in load_decisions(src):
            dd = d['decision_detail']
            if dd['kind'] != 'match' or d['decision'] not in ('same', 'different') or len(dd['masks']) != 2:
                continue
            a, b = dd['masks']
            s = d.get('scores') or {}
            sab, sba = float(s.get('share_ab', np.nan)), float(s.get('share_ba', np.nan))
            aa = sum(area.get(m, 0) for m in a['mask_ids']); ab = sum(area.get(m, 0) for m in b['mask_ids'])
            va, vb = str(a['view']), str(b['view'])
            rows.append(dict(plant=plant, id=d['object_id'], label=1 if d['decision'] == 'same' else 0,
                             share_ab=sab, share_ba=sba, share_min=min(sab, sba), share_max=max(sab, sba), share_mean=(sab + sba) / 2,
                             n_a=len(a['mask_ids']), n_b=len(b['mask_ids']), area_a_log=math.log1p(aa), area_b_log=math.log1p(ab),
                             area_ratio_log=abs(math.log1p(aa) - math.log1p(ab)), same_view_group=float(va[:1] == vb[:1]),
                             view_code_gap=abs(int(va) - int(vb)) if va.isdigit() and vb.isdigit() else np.nan,
                             feature_pose=float('feature_pose' in str(d.get('rule_id'))),
                             masks_a=list(a['mask_ids']), masks_b=list(b['mask_ids'])))
    return rows


def add_geometry(rows: list[dict], cfg: dict) -> list[dict]:
    """Two-photo geometry from the board poses (tools.xview_geometry) for each cross-view row, from the reviewed masks."""
    from tools import leaflet_mask_batch as lmb
    from tools import xview_geometry as xg
    from tools.plant_structure import Cameras
    by_plant = {}
    for r in rows:
        by_plant.setdefault(r['plant'], []).append(r)
    for plant, rs in by_plant.items():
        pc = cfg['plants'][plant]
        session = ROOT / pc['capture'] / 'edit_session'
        capture = read_json(session / 'capture.json')
        cams, photos = Cameras(capture), xg.Photos(session, capture)
        batch = lmb.Batch(ROOT / pc['batch'])
        cache = {}

        def union(ids):
            key = tuple(sorted(ids))
            if key not in cache:
                m, img = None, None
                for i in ids:
                    it = batch.item(i)
                    part, meta = batch.mask(it)
                    x0, y0 = meta['crop_px'][:2]
                    full = np.zeros((cams.size[1], cams.size[0]), bool)
                    h, w = min(part.shape[0], full.shape[0] - y0), min(part.shape[1], full.shape[1] - x0)
                    full[y0:y0 + h, x0:x0 + w] = part[:h, :w]
                    m = full if m is None else m | full
                    img = it['image_file'].lower()
                cache[key] = (img, m)
            return cache[key]
        for r in sorted(rs, key=lambda r: r['masks_a'][0]):  # photo a in order keeps the image cache warm
            (ia, ma), (ib, mb) = union(r['masks_a']), union(r['masks_b'])
            r.update(xg.pair_features(cams, photos, ia, ma, '|'.join(sorted(r['masks_a'])), ib, mb, '|'.join(sorted(r['masks_b']))))
    return rows


def _model():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, random_state=0)


def _thresholds(p: np.ndarray, y: np.ndarray, target: float = TARGET_PRECISION) -> tuple[float, float]:
    """Lowest p for auto-'1' and highest p for auto-'0' that keep precision >= target on these samples."""
    hi, lo = 1.01, -0.01
    for t in sorted(set(np.round(p, 4))):
        sel = p >= t
        if sel.sum() >= 5 and y[sel].mean() >= target:
            hi = t; break
    for t in sorted(set(np.round(p, 4)), reverse=True):
        sel = p <= t
        if sel.sum() >= 5 and (1 - y[sel]).mean() >= target:
            lo = t; break
    return float(hi), float(lo)


def evaluate(rows: list[dict], features: list[str]) -> dict:
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import cross_val_predict
    plants = sorted({r['plant'] for r in rows})
    X = np.array([[r[f] for f in features] for r in rows], float)
    y = np.array([r['label'] for r in rows])
    groups = np.array([r['plant'] for r in rows])
    out = {}
    for held in plants:
        tr, te = groups != held, groups == held
        if len(set(y[tr])) < 2 or te.sum() == 0:
            continue
        # thresholds from out-of-fold predictions on the training plants only (nested: the held-out plant never tunes them)
        inner = cross_val_predict(_model(), X[tr], y[tr], groups=groups[tr], cv=_group_cv(groups[tr]), method='predict_proba')[:, 1]
        hi, lo = _thresholds(inner, y[tr])
        m = _model().fit(X[tr], y[tr])
        p = m.predict_proba(X[te])[:, 1]
        auto1, auto0 = p >= hi, p <= lo
        yt = y[te]
        out[held] = dict(n=int(te.sum()), positives=int(yt.sum()), auc=round(float(roc_auc_score(yt, p)), 3) if len(set(yt)) == 2 else None,
                         thresholds=dict(auto_positive=round(hi, 3), auto_negative=round(lo, 3)),
                         auto_positive=dict(n=int(auto1.sum()), precision=round(float(yt[auto1].mean()), 3) if auto1.any() else None),
                         auto_negative=dict(n=int(auto0.sum()), precision=round(float((1 - yt[auto0]).mean()), 3) if auto0.any() else None),
                         to_person=int((~auto1 & ~auto0).sum()),
                         automated_share=round(float((auto1 | auto0).mean()), 3))
    tot = sum(v['n'] for v in out.values())
    out['overall'] = dict(n=tot, automated_share=round(sum(v['automated_share'] * v['n'] for v in out.values()) / max(tot, 1), 3),
                          auto_positive_precision=_pooled(out, 'auto_positive'), auto_negative_precision=_pooled(out, 'auto_negative'))
    return out


def _pooled(out, key):
    vals = [(v[key]['n'], v[key]['precision']) for k, v in out.items() if k != 'overall' and v[key]['precision'] is not None]
    n = sum(a for a, _ in vals)
    return round(sum(a * b for a, b in vals) / n, 3) if n else None


def _group_cv(groups):
    from sklearn.model_selection import LeaveOneGroupOut
    return list(LeaveOneGroupOut().split(np.zeros(len(groups)), groups=groups))


def train_final(rows, features, path: Path) -> dict:
    import joblib
    from sklearn.model_selection import cross_val_predict
    X = np.array([[r[f] for f in features] for r in rows], float)
    y = np.array([r['label'] for r in rows])
    groups = np.array([r['plant'] for r in rows])
    oof = cross_val_predict(_model(), X, y, groups=groups, cv=_group_cv(groups), method='predict_proba')[:, 1]
    hi, lo = _thresholds(oof, y)
    m = _model().fit(X, y)
    joblib.dump(dict(model=m, features=features, auto_positive=hi, auto_negative=lo, target_precision=TARGET_PRECISION), path)
    return dict(path=str(path), auto_positive=round(hi, 3), auto_negative=round(lo, 3), n=len(rows))


def build(out: Path, config: Path = CONFIG, redraft: Path | None = None) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    cfg = read_json(config)
    masks, pairs = (redraft_rows(cfg, redraft) if redraft else mask_rows(cfg)), xview_rows(cfg)
    report = dict(schema='decision-learning-1', target_precision=TARGET_PRECISION,
                  data=dict(mask_reviews=len(masks), mask_accepted=sum(r['label'] for r in masks),
                            xview_pairs=len(pairs), xview_same=sum(r['label'] for r in pairs)),
                  mask_review=evaluate(masks, MASK_FEATURES), xview=evaluate(pairs, XVIEW_FEATURES) if len(pairs) >= 20 else None,
                  final=dict(mask_review=train_final(masks, MASK_FEATURES, out / 'mask_review.joblib'),
                             xview=train_final(pairs, XVIEW_FEATURES, out / 'xview.joblib') if len(pairs) >= 20 else None),
                  mask_features_from=str(redraft) if redraft else 'the reviewed batches\' own cached drafts',
                  note='automatic answers only above the thresholds; everything else stays a human task; a human answer '
                       'always overrides a model answer; trained on human reviews only (review_source auto excluded)')
    write_json(out / 'report.json', report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--redraft', type=Path, help='redraft.json from the tomato-mask-redraft-run kernel (features from SAM v5 drafts)')
    a = ap.parse_args()
    r = build(a.out, redraft=a.redraft)
    print(json.dumps({k: r[k] for k in ('data', 'mask_review', 'xview')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
