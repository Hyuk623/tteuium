"""Cross-view stem completion: 3D stem/petiole axes from S3 projected into every posed photo (2026-09-29).

    python -X utf8 -m tools.stem_completion --run build/pipeline_<ts> --plant dwt_01 --out build/<new>
    (plant_pipeline runs it after S3 for every plant; outputs go to <run>/<plant>/stem_completion/)

A stem that S3 fitted from some photos must also appear in the other posed photos. For each posed photo this tool
projects the main-stem axis and every fitted petiole axis and compares the projection with the person's (or the
model's) stem polygons in that photo:

* agreement: share of projected axis samples that fall inside a polygon of the same class (8 px tolerance) and the
  median pixel distance from the samples to that class's polygons - measured wherever the photo has polygons, as a
  check of how far the projection can be trusted;
* proposal: where the photo has no polygon covering the projection (agreement < MIN_COVER with at least half the axis
  in the frame), a band polygon around the projected axis (width from the fitted diameter, else ASSUMED_WIDTH_MM) is
  written as a PROPOSAL for a person to confirm. Proposals never become labels or training data by themselves.

Only posed photos can be projected; photos without a board pose get nothing. Everything stays diagnostic.
A projected band marks where the stem IS, also behind leaves (checked on dwt_01 view 28), while people label only what
is visible: proposals are for 3D completeness and review, not 2D detector training labels.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json
from tools.plant_structure import Cameras

MIN_COVER, TOL_PX, SAMPLES = 0.3, 8, 40
#: Measured 2026-09-29 on dwt_01..04 in photos an axis was NOT fitted from: petiole axes landed 100-350 px away from
#: every petiole polygon (coverage mostly 0), main stems fitted from >= 2 photos agreed (coverage 0.7-1.0 where fitted).
#: So only main stems fitted from >= 2 photos are proposed; petioles are projected for the check but never proposed.
PROPOSE = dict(stem_min_fitted_views=2, petioles=False)
ASSUMED_WIDTH_MM = {'main-stem': 5.0, 'sub-stem': 3.0}
CLASS_OF = {'stem': 'main-stem', 'petiole': 'sub-stem'}


def targets(structure: dict) -> list[dict]:
    out = []
    st = structure.get('stem') or {}
    if st.get('status') == 'fitted' and st.get('axis'):
        out.append(dict(kind='stem', key='main_stem', points=np.array(st['axis'], float), cls='main-stem',
                        width_mm=st.get('diameter_mm') or ASSUMED_WIDTH_MM['main-stem'],
                        width_source='fitted diameter' if st.get('diameter_mm') else 'assumed', method=st.get('method'),
                        fitted_from=[Path(v).stem[-2:] for v in st.get('views', [])]))
    for p in structure.get('petioles') or []:
        if p.get('status') == 'fitted':
            out.append(dict(kind='petiole', key=f"petiole_region_{p['region']}", points=np.array([p['near_end'], p['far_end']], float),
                            cls='sub-stem', width_mm=ASSUMED_WIDTH_MM['sub-stem'], width_source='assumed', method='ray_fit',
                            fitted_from=[Path(v).stem[-2:] for v in p.get('views', [])],
                            single_view=len(p.get('views', [])) < 2))
    return out


def densify(points: np.ndarray, n: int = SAMPLES) -> np.ndarray:
    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    t = np.concatenate([[0], np.cumsum(seg)])
    s = np.linspace(0, t[-1], n)
    return np.stack([np.interp(s, t, points[:, k]) for k in range(3)], 1)


def class_mask(dets: list, cls: str, size: tuple[int, int]) -> np.ndarray:
    m = np.zeros((size[1], size[0]), np.uint8)
    for d in dets:
        if d['class_name'] == cls and d.get('rings'):
            for ring in d['rings']:
                cv2.fillPoly(m, [np.round(np.array(ring)).astype(np.int32)], 1)
    return m.astype(bool)


def band_polygon(px: np.ndarray, width_px: float) -> list[list[float]] | None:
    from shapely.geometry import LineString
    line = LineString(px)
    if line.length < 1:
        return None
    poly = line.buffer(max(width_px / 2, 2.0), cap_style=2)
    return np.asarray(poly.exterior.coords)[:-1].round(1).tolist()


def complete(session: Path, backup: Path, structure_path: Path, out: Path) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    capture = read_json(Path(session) / 'capture.json')
    cams = Cameras(capture)
    dets = read_json(backup)['variants']['__all__'].get('membership', {}).get('detections', {})
    structure = read_json(structure_path)
    tg = targets(structure)
    out.mkdir(parents=True)
    (out / 'overlays').mkdir()
    size = cams.size
    coco = dict(images=[], annotations=[], categories=[dict(id=1, name='main-stem'), dict(id=2, name='sub-stem')],
                info=dict(source='tools.stem_completion: S3 3D axes projected into posed photos', status='PROPOSALS, not labels'))
    agreement, n_prop = [], 0
    for key in sorted(k for k in cams.frames if cams.posed(k)):
        frame = cams.frames[key]
        photo_dets = dets.get(key, [])
        img_id = len(coco['images']) + 1
        coco['images'].append(dict(id=img_id, file_name=frame['image_file'], width=size[0], height=size[1]))
        path = Path(session) / frame['image_path']
        im = Image.open(path).convert('RGB') if path.exists() else Image.new('RGB', size, 'black')
        dr = ImageDraw.Draw(im)
        for t in tg:
            pts = densify(t['points'])
            depth = cams.depth(key, pts)
            px = cams.project(key, pts)
            inside = (depth > 0) & (px[:, 0] >= 0) & (px[:, 0] < size[0]) & (px[:, 1] >= 0) & (px[:, 1] < size[1])
            if inside.mean() < 0.5:
                continue
            m = class_mask(photo_dets, t['cls'], size)
            has_poly = bool(m.any())
            cover, dist = None, None
            if has_poly:
                dil = cv2.dilate(m.astype(np.uint8), np.ones((2 * TOL_PX + 1, 2 * TOL_PX + 1), np.uint8)).astype(bool)
                q = np.round(px[inside]).astype(int)
                cover = float(dil[q[:, 1], q[:, 0]].mean())
                dt = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
                dist = float(np.median(dt[q[:, 1], q[:, 0]]))
                agreement.append(dict(photo=key[-6:-4], target=t['key'], cls=t['cls'], coverage=round(cover, 3),
                                      median_distance_px=round(dist, 1), fitted_from_this_photo=key[-6:-4] in t['fitted_from']))
            width_px = t['width_mm'] * cams.K[0, 0] / float(np.median(depth[inside]))
            dr.line([tuple(p) for p in px[inside]], fill=(255, 150, 0), width=max(4, int(width_px / 3)))
            allowed = (t['kind'] == 'stem' and len(t['fitted_from']) >= PROPOSE['stem_min_fitted_views']) or                 (t['kind'] == 'petiole' and PROPOSE['petioles'])
            if allowed and (not has_poly or cover < MIN_COVER):
                poly = band_polygon(px[inside], width_px)
                if poly:
                    n_prop += 1
                    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
                    coco['annotations'].append(dict(
                        id=len(coco['annotations']) + 1, image_id=img_id, category_id=1 if t['cls'] == 'main-stem' else 2,
                        bbox=[min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)], segmentation=[sum(poly, [])], iscrowd=0,
                        provenance=dict(source='projected S3 axis', target=t['key'], method=t['method'], fitted_from=t['fitted_from'],
                                        width_mm=t['width_mm'], width_source=t['width_source'], single_view=t.get('single_view', False),
                                        existing_polygon_coverage=cover, status='proposal - needs a person')))
                    dr.polygon([tuple(p) for p in poly], outline=(255, 40, 40), width=5)
        for d in photo_dets:
            if d['class_name'] in ('main-stem', 'sub-stem') and d.get('rings'):
                dr.line([tuple(p) for p in d['rings'][0]] + [tuple(d['rings'][0][0])], fill=(40, 220, 90), width=4)
        im.thumbnail((1400, 1400))
        im.save(out / 'overlays' / f'{Path(frame["image_file"]).stem}.jpg', quality=85)
    write_json(out / 'stem_proposals.coco.json', coco)
    indep = [a for a in agreement if not a['fitted_from_this_photo']]
    report = dict(schema='stem-completion-1', plant_id=capture.get('plant_id'), session=str(session),
                  structure=str(structure_path), structure_sha256=file_hash(Path(structure_path)),
                  targets=[dict(key=t['key'], cls=t['cls'], method=t['method'], fitted_from=t['fitted_from'], width_mm=t['width_mm'],
                                width_source=t['width_source']) for t in tg],
                  posed_photos=[k[-6:-4] for k in sorted(cams.frames) if cams.posed(k)], proposals=n_prop, agreement=agreement,
                  proposal_rule=dict(PROPOSE, reason='petiole axes from 1-2 photos missed other photos by 100-350 px (09-29 check)'),
                  independent_agreement=dict(n=len(indep), median_coverage=round(float(np.median([a['coverage'] for a in indep])), 3) if indep else None,
                                             median_distance_px=round(float(np.median([a['median_distance_px'] for a in indep])), 1) if indep else None),
                  legend='overlays: orange = projected axis, red = proposal, green = existing stem/petiole polygons',
                  note='independent_agreement uses photos the axis was NOT fitted from; proposals need a person',
                  validated_metric=False)
    write_json(out / 'report.json', report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--plant', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--config', type=Path, default=Path(__file__).with_name('plant_pipeline_plants.json'))
    a = ap.parse_args()
    cfg = read_json(a.config)['plants'][a.plant]
    root = Path(__file__).resolve().parents[1]
    session = root / cfg['capture'] / 'edit_session'
    backup = root / cfg['labels'] / 'seed_with_imports.backup.json'
    r = complete(session, backup, a.run / a.plant / 'structure' / 'structure.json', a.out)
    print(json.dumps({k: r[k] for k in ('targets', 'posed_photos', 'proposals', 'independent_agreement')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
