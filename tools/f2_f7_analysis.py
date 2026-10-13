"""Separate, read-only F.2/F.7 shape audit. No generator or detector execution.

Run: python -m tools.f2_f7_analysis --policy build/<run>/policy.json --out build/<run>
Photo annotations and measured tables are CSV. Policy/provenance are JSON.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


def sha(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def table(path: Path, rows: list[dict], fields=None) -> None:
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert('RGB'))


def resample(points: np.ndarray, n: int = 64) -> np.ndarray:
    p = np.asarray(points, float).reshape(-1, 2)
    loop = np.vstack([p, p[:1]])
    dist = np.r_[0., np.cumsum(np.linalg.norm(np.diff(loop, axis=0), axis=1))]
    good = np.r_[True, np.diff(dist) > 1e-12]
    dist, loop = dist[good], loop[good]
    if dist[-1] <= 0:
        raise ValueError('degenerate contour')
    t = np.linspace(0, dist[-1], n, endpoint=False)
    return np.stack([np.interp(t, dist, loop[:, j]) for j in (0, 1)], axis=1)


def metrics(points: np.ndarray, n: int = 64) -> dict:
    p = resample(points, n).astype(np.float32).reshape(-1, 1, 2)
    area = float(cv2.contourArea(p))
    hull = float(cv2.contourArea(cv2.convexHull(p)))
    per = float(cv2.arcLength(p, True))
    _, (w, h), _ = cv2.minAreaRect(p)
    if min(area, hull, w, h) <= 0:
        raise ValueError('zero area or span')
    return dict(norm_perimeter=per * per / (4 * math.pi * area), solidity=area / hull,
                aspect=min(w, h) / max(w, h), contour_points=n)


def largest(mask: np.ndarray) -> np.ndarray:
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        raise ValueError('empty mask')
    return max(cs, key=cv2.contourArea).reshape(-1, 2)


def fit_threshold(rows: list[dict]) -> dict:
    """Fit balanced error on labelled photos; no C6 inputs are accepted."""
    main = np.array([r['norm_perimeter'] for r in rows if r['label'] == 'main'])
    small = np.array([r['norm_perimeter'] for r in rows if r['label'] == 'interjected'])
    if not len(main) or not len(small):
        raise ValueError('both classes required')
    vals = np.unique(np.r_[main, small])
    candidates = (vals[:-1] + vals[1:]) / 2
    errors = np.array([((main < t).mean() + (small >= t).mean()) / 2 for t in candidates])
    best = candidates[np.isclose(errors, errors.min())]
    return dict(threshold=float(np.median(best)), balanced_error=float(errors.min()),
                n_main=len(main), n_interjected=len(small))


def classify(value: float, threshold: float, guard: float, reason: str = '') -> tuple[str, str]:
    if reason:
        return 'unknown', reason
    if abs(value - threshold) <= guard:
        return 'unknown', 'near_fitted_threshold'
    return ('main' if value > threshold else 'interjected'), 'shape_candidate_not_botanical_ground_truth'


def audit(policy_path: Path, out: Path) -> dict:
    policy = read_json(policy_path)
    root = Path(policy['project_root']).resolve()
    out = out.resolve()
    if not out.is_relative_to(root / 'build'):
        raise ValueError('output must stay under project build/')
    out.mkdir(parents=True, exist_ok=True)
    inputs: dict[str, str] = {}

    def source(rel: str) -> Path:
        p = (root / rel).resolve()
        if str(p) not in inputs:
            inputs[str(p)] = sha(p)
        return p

    source(str(policy_path.resolve()))
    lib_root = policy['library_root']
    records = read_json(source(f'{lib_root}/library_components.json'))['records']
    flat = read_json(source(policy['flattened']))['contours']
    sam_doc = read_json(source(policy['sam']))
    sam = sam_doc['contours']
    bank = read_json(source(policy['bank']))['textures']
    for rel in policy.get('protected', []):
        source(rel)
    for rel in policy.get('protected_dirs', []):
        for p in sorted((root / rel).rglob('*')):
            if p.is_file():
                source(str(p))
    reference_rows = []
    cards = []
    for r in policy['references']:
        img = rgb(source(r['photo']))
        x0, y0, x1, y1 = r['roi_xyxy']
        crop = img[y0:y1, x0:x1]
        hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
        mask = ((hsv[:, :, 1] >= policy['reference_min_saturation']) |
                (hsv[:, :, 2] < policy['reference_dark_value'])).astype(np.uint8)
        c = largest(mask)
        dense = metrics(c, 256)
        sh = metrics(c)
        row = dict(reference_id=r['id'], photo=Path(r['photo']).name, label=r['label'],
                   fit_eligible=r['fit_eligible'], quality_flags=r['quality_flags'],
                   roi_xyxy=';'.join(map(str,r['roi_xyxy'])), **sh,
                   norm_perimeter_256=dense['norm_perimeter'],
                   source_kind='measured_small_n', label_source='user_photo_labels;component_association_by_Codex')
        reference_rows.append(row)
        annotated = crop.copy()
        cv2.polylines(annotated, [c.astype(np.int32)], True, (255, 0, 180), 2)
        card = Image.new('RGB', (330, 300), 'white')
        card.paste(ImageOps.contain(Image.fromarray(annotated), (330, 240)), (0, 55))
        d = ImageDraw.Draw(card)
        d.text((5, 5), f"{r['id']} | {r['label']} | fit={r['fit_eligible']}", fill='black')
        d.text((5, 25), f"P64={sh['norm_perimeter']:.3f} / S={sh['solidity']:.3f}", fill='black')
        cards.append(card)
    table(out / 'class_reference_metrics.csv', reference_rows)
    sheet = Image.new('RGB', (330 * 4, 300 * math.ceil(len(cards)/4)), 'white')
    for i, card in enumerate(cards):
        sheet.paste(card, (330*(i%4), 300*(i//4)))
    sheet.save(out / 'reference_segmentation.png')
    fit_rows = [r for r in reference_rows if r['fit_eligible']]
    fitted = fit_threshold(fit_rows)
    folds = []
    for photo in sorted({r['photo'] for r in fit_rows}):
        train = [r for r in fit_rows if r['photo'] != photo]
        try:
            f = fit_threshold(train)
        except ValueError:
            folds.append(dict(held_out_photo=photo, status='unavailable_missing_training_class'))
            continue
        test = [r for r in fit_rows if r['photo'] == photo]
        folds.append(dict(held_out_photo=photo, status='ok', threshold=f['threshold'], n=len(test),
                          correct=sum(('main' if r['norm_perimeter'] >= f['threshold'] else 'interjected') == r['label'] for r in test)))
    thresholds = [f['threshold'] for f in folds if f['status'] == 'ok']
    # Explicit conservative photo-instability band, plus a declared 10% minimum; not a CI.
    guard = max(policy['minimum_guard_fraction'] * fitted['threshold'],
                max([abs(v-fitted['threshold']) for v in thresholds] or [0]))
    fitted.update(guard=guard, guard_method='max(10_percent_threshold,leave_photo_out_threshold_shift);heuristic_not_CI',
                  photo_folds=folds, score_meaning='training_fit_and_internal_photo_crosscheck_not_external_validation',
                  metric='64_equal_arclength_polygon_perimeter_squared/(4*pi*polygon_area)',
                  biological_accuracy='unavailable', source_kind='measured_small_n',
                  n_photos=len({r['photo'] for r in fit_rows}), n_independent_plants=None)
    save_json(out / 'classifier_policy.json', fitted)
    rows = []

    def add(artifact: str, identity: str, sh: dict, reason: str = '', **extra):
        label, status = classify(sh['norm_perimeter'], fitted['threshold'], guard, reason)
        row = dict(artifact=artifact, item_id=identity, leaflet_class=label, class_status=status,
                   **sh, **extra)
        rows.append(row)
        return row

    library_map = {}
    for r in records:
        arr = rgb(source(f"{lib_root}/{r['crop']}"))
        c = largest(~np.all(arr >= 250, axis=2))
        reason = ('compound_component_not_individual_leaflet' if r['level'] != 'leaflet' else
                  'non_leaf_or_unclassified' if r['condition'] in ('non_leaf','unclassified') else
                  'damaged_margin' if r['condition'] == 'damaged' else '')
        sh = metrics(c)
        sh['norm_perimeter_256'] = metrics(c, 256)['norm_perimeter']
        library_map[r['component_id']] = add('library_components', r['component_id'], sh, reason,
                                           photo=r['photo'], condition=r['condition'], source_representation='segmented_crop',
                                           projection_warning='unpressed;identity_and_full_boundary_unvalidated')
    for r in flat:
        cid = r['contour_id'].split('/')[-1]
        parent = library_map.get(cid)
        sh = metrics(np.array(r['points']))
        reason = '' if parent and parent['class_status'] in ('shape_candidate_not_botanical_ground_truth','near_fitted_threshold') else 'source_component_ineligible'
        row = add('flattened_contours', r['contour_id'], sh, reason, photo=r['photo'],
                  source_representation='stored_64_point_contour', projection_warning='unpressed;scale_pending')
        row['source_component_class'] = parent['leaflet_class'] if parent else 'unknown'
        if parent and row['leaflet_class'] != parent['leaflet_class']:
            row['leaflet_class'], row['class_status'] = 'unknown', 'source_vs_resampled_contour_disagreement'
    sam_map = {}
    for r in sam:
        reason = ('border_truncation' if r.get('touches_border') else
                  'multiple_components' if r.get('dominant_fraction',1) < policy['min_dominant_fraction'] else '')
        sh = metrics(np.array(r['points']))
        sam_map[r['mask_id']] = add('sam_contours', r['contour_id'], sh, reason,
                  photo=r['image_file'], source_representation='stored_64_point_projected_contour',
                  projection_warning='unknown_pose_curl_occlusion;shape_label_not_anatomical_confirmation')
    for r in bank:
        parent = library_map.get(r.get('component_id')) if r['source']=='library_crop' else sam_map.get(r.get('mask_id'))
        if not parent:
            raise ValueError(f"unmapped texture {r['file']}")
        source(str(Path(policy['bank']).parent / r['file']))
        row = dict(parent)
        row.update(artifact='texture_bank_v2', item_id=r['file'], parent_id=r.get('component_id') or r['mask_id'],
                   source_representation='source_contour_join_not_texture_rectangle', texture_source=r['source'])
        rows.append(row)
    table(out / 'artifact_classification.csv', rows)
    table(out / 'near_threshold.csv', [r for r in rows if abs(r['norm_perimeter']-fitted['threshold']) <= guard])
    summary = {}
    for name in ('library_components','flattened_contours','sam_contours','texture_bank_v2'):
        group = [r for r in rows if r['artifact']==name]
        summary[name] = dict(n=len(group), classes=dict(Counter(r['leaflet_class'] for r in group)),
                             statuses=dict(Counter(r['class_status'] for r in group)),
                             norm_perimeter_quantiles=np.quantile([r['norm_perimeter'] for r in group],[0,.1,.25,.5,.75,.9,1]).tolist(),
                             solidity_quantiles=np.quantile([r['solidity'] for r in group],[.1,.5,.9]).tolist(),
                             aspect_quantiles=np.quantile([r['aspect'] for r in group],[.1,.5,.9]).tolist())
    summary['texture_by_source'] = {s:dict(Counter(r['leaflet_class'] for r in rows if r['artifact']=='texture_bank_v2' and r['texture_source']==s)) for s in ('library_crop','rig_photo_crop')}
    summary['interpretation'] = 'All labels are morphology candidates. Main/interjected true contamination count is unvalidated; low perimeter can also be a main leaf seen folded/occluded. No bank rebuild or F3 authorisation.'
    summary['classifier'] = fitted
    save_json(out / 'F7_summary.json', summary)
    # Sensitivity to representation and the explicit guard; complete empirical distributions remain in CSV.
    sensitivity = []
    for factor in (0., .5, 1., 1.5):
        for artifact in ('library_components','flattened_contours','sam_contours','texture_bank_v2'):
            counts = Counter()
            for r in [r for r in rows if r['artifact']==artifact]:
                reason = '' if r['class_status'] in ('shape_candidate_not_botanical_ground_truth','near_fitted_threshold') else r['class_status']
                counts[classify(r['norm_perimeter'],fitted['threshold'],guard*factor,reason)[0]] += 1
            sensitivity.append(dict(artifact=artifact,guard_factor=factor,**{c:counts[c] for c in ('main','interjected','unknown')}))
    table(out / 'classification_sensitivity.csv', sensitivity)
    bank_candidates = [r for r in rows if r['artifact']=='texture_bank_v2' and r['leaflet_class']=='interjected']
    bank_cards=[]
    raw_bank={r['file']:r for r in bank}
    for r in bank_candidates:
        entry=raw_bank[r['item_id']]
        if entry['source']=='library_crop':
            path=source(f"{lib_root}/crops/{entry['component_id']}.png")
            im=Image.open(path).convert('RGB')
        else:
            rec=next(s for s in sam if s['mask_id']==entry['mask_id'])
            export=Path(sam_doc['sources'][rec['plant_id']]['export'])
            im=Image.open(source(str(export / f"{rec['mask_id']}.png"))).convert('RGB')
            bbox=im.getbbox()
            if bbox: im=im.crop(bbox)
        card=Image.new('RGB',(200,220),'white')
        card.paste(ImageOps.contain(im,(200,175)),(0,42))
        d=ImageDraw.Draw(card)
        d.text((3,3),f"{r['item_id']} P={r['norm_perimeter']:.2f}",fill='black')
        d.text((3,19),r['parent_id'],fill='black')
        bank_cards.append(card)
    if bank_cards:
        sheet=Image.new('RGB',(1000,220*math.ceil(len(bank_cards)/5)),'white')
        for i,card in enumerate(bank_cards): sheet.paste(card,((i%5)*200,(i//5)*220))
        sheet.save(out/'texture_interjected_candidates.png')
    checks={p:sha(Path(p))==digest for p,digest in inputs.items()}
    save_json(out/'input_provenance.json',dict(sha256_before=inputs,unchanged_after=checks,all_unchanged=all(checks.values())))
    if not all(checks.values()): raise RuntimeError('source changed during analysis')
    return summary


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    report=audit(args.policy,args.out)
    print(json.dumps({k:v for k,v in report.items() if k not in ('classifier','interpretation')},indent=2))


if __name__=='__main__': main()
