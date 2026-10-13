"""Stem and petiole diameter from the person's 2D polygons with an OpenCV distance transform (2026-09-29).

    python -X utf8 -m tools.stem_thickness --run build/pipeline_<ts> [--plant dwt_01] --out build/<new>

For every posed photo with a main-stem (or sub-stem) polygon:

1. width in pixels: cv2.distanceTransform of the filled polygon gives, at each inside pixel, the distance to the edge;
   on the medial ridge (pixels that are a local maximum of that distance) twice the value is the local full width.
   The median over the ridge is the photo's width; the ridge's p25-p75 shows taper and bends. Unlike the old
   whole-polygon PCA estimate this follows a bent or branched outline.
2. width in millimetres: pixel width x depth / focal length, with the depth of the S3 3D axis at the point whose
   projection is nearest to the polygon (main stem: the fitted axis, either method; petiole: its near-far segment).
   A polygon whose nearest axis point projects more than MAX_AXIS_GAP_PX away is not converted (wrong organ or axis).

The photos are independent views, so their agreement (spread of the per-photo mm values) is the check. Values stay
diagnostic (validated_metric=false): the polygon is a person's outline at 3024 px, and a 5 mm stem is ~20-40 px wide.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json
from tools.plant_structure import Cameras

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
MAX_AXIS_GAP_PX = 60
MIN_RIDGE_PX = 5
AXIS_SAMPLES = 200
BAND_MM = 10.0
MAX_WIDTH_IQR = 0.25


def ring_mask(rings, size) -> np.ndarray:
    m = np.zeros((size[1], size[0]), np.uint8)
    for r in rings:
        cv2.fillPoly(m, [np.round(np.array(r)).astype(np.int32)], 1)
    return m


def medial_widths(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Full widths (px) along the medial ridge of a binary mask and the ridge pixel coordinates (x, y)."""
    dt = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    ridge = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)) - 1e-6) & (dt >= 1.0)
    ys, xs = np.nonzero(ridge)
    return 2.0 * dt[ys, xs], np.column_stack([xs, ys])


def _dense(points: np.ndarray, n: int = AXIS_SAMPLES) -> np.ndarray:
    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    t = np.concatenate([[0], np.cumsum(seg)])
    s = np.linspace(0, t[-1], n)
    return np.stack([np.interp(s, t, points[:, k]) for k in range(3)], 1)


def measure(cams: Cameras, key: str, rings, axis: np.ndarray) -> tuple[dict, dict]:
    """Per-photo row and per-ridge-pixel samples {z_mm, d_mm}: each ridge pixel is tied to the nearest projected 3D axis
    point (its height and depth), so a bent or tapering stem is compared at the same height across photos."""
    mask = ring_mask(rings, cams.size)
    w, xy = medial_widths(mask)
    row = dict(photo=key[-6:-4], ridge_px=int(len(w)))
    if len(w) < MIN_RIDGE_PX:
        return row | dict(status='unavailable', reason='polygon too small for a medial ridge'), {}
    pts = _dense(axis)
    depth = cams.depth(key, pts)
    px = cams.project(key, pts)
    px[depth <= 0] = np.inf
    dist = np.linalg.norm(xy[:, None, :] - px[None, :, :], axis=2)
    j = dist.argmin(1)
    gap = dist[np.arange(len(j)), j]
    keep = (gap <= MAX_AXIS_GAP_PX) & (j > 0) & (j < len(pts) - 1)  # on the axis, not beyond its ends
    row.update(width_px_median=round(float(np.median(w)), 2), on_axis_fraction=round(float(keep.mean()), 3))
    if keep.sum() < MIN_RIDGE_PX:
        return row | dict(status='not_converted', reason=f'fewer than {MIN_RIDGE_PX} ridge pixels lie within {MAX_AXIS_GAP_PX} px '
                                                         'of the projected 3D axis (polygon outside the fitted stretch)'), {}
    d_mm = w[keep] * depth[j[keep]] / cams.K[0, 0]
    z = pts[j[keep], 2]
    row.update(status='measured', z_mm=[round(float(z.min()), 1), round(float(z.max()), 1)],
               diameter_mm=round(float(np.median(d_mm)), 2),
               diameter_mm_p25_p75=[round(float(np.percentile(d_mm, q)), 2) for q in (25, 75)])
    return row, dict(z=z, d=d_mm)


def _summary(rows: list[dict], samples: dict) -> dict:
    """Diameter by height band; photos are compared only inside bands two or more of them cover."""
    photos = [k for k, v in samples.items() if v]
    if not photos:
        return dict(status='unavailable', photos=0)
    zmin = min(float(samples[k]['z'].min()) for k in photos)
    zmax = max(float(samples[k]['z'].max()) for k in photos)
    profile = []
    for z0 in np.arange(np.floor(zmin / BAND_MM) * BAND_MM, zmax + 1e-9, BAND_MM):
        per = {k: float(np.median(samples[k]['d'][(samples[k]['z'] >= z0) & (samples[k]['z'] < z0 + BAND_MM)]))
               for k in photos if ((samples[k]['z'] >= z0) & (samples[k]['z'] < z0 + BAND_MM)).sum() >= MIN_RIDGE_PX}
        if per:
            v = list(per.values())
            profile.append(dict(z_mm=[round(float(z0), 1), round(float(z0 + BAND_MM), 1)], photos=len(v),
                                diameter_mm=round(float(np.median(v)), 2), min_mm=round(min(v), 2), max_mm=round(max(v), 2),
                                spread_pct=round(100 * (max(v) - min(v)) / float(np.median(v)), 1) if len(v) > 1 else None))
    shared = [b for b in profile if b['photos'] >= 2]
    # a round stem has one width from every side; a polygon whose width varies a lot along the stem is partly hidden
    # (narrow pieces) or includes something else (roots at the soil, a petiole base) - checked on dwt_02 24 and dwt_03 21/24
    iqr = {k: float(np.subtract(*np.percentile(samples[k]['d'], [75, 25]))) / float(np.median(samples[k]['d'])) for k in photos}
    steady = [k for k in photos if iqr[k] <= MAX_WIDTH_IQR]
    per_photo = {k[-6:-4]: dict(diameter_mm=round(float(np.median(samples[k]['d'])), 2), width_iqr_ratio=round(iqr[k], 2),
                                used=k in steady) for k in photos}
    if not steady:
        return dict(status='unreliable', photos=len(photos), steady_photos=0, per_photo_width=per_photo, profile=profile,
                    reason=f'every polygon varies by more than {MAX_WIDTH_IQR:.0%} (IQR/median) along the stem: occluded or mixed outline')
    vals = [float(np.median(samples[k]['d'])) for k in steady]
    return dict(status='measured', photos=len(photos), steady_photos=len(steady), diameter_mm=round(float(np.median(vals)), 2),
                diameter_basis=f'median of photos whose width varies <= {MAX_WIDTH_IQR:.0%} (IQR/median) along the polygon',
                steady_spread_pct=round(100 * (max(vals) - min(vals)) / float(np.median(vals)), 1) if len(vals) > 1 else None,
                check='independent steady photos agree within steady_spread_pct' if len(vals) > 1 else 'one steady photo: no cross-photo check',
                per_photo_width=per_photo, shared_bands=len(shared), profile=profile)


def _photos(cams, posed, dets, cls, axis):
    rows, samples = [], {}
    for k in posed:
        for j, d in enumerate(x for x in dets.get(k, []) if x['class_name'] == cls and x.get('rings')):
            row, smp = measure(cams, k, [d['rings'][0]], axis)
            rows.append(row | dict(polygon=j))
            if smp:
                prev = samples.get(k)
                samples[k] = smp if not prev else dict(z=np.r_[prev['z'], smp['z']], d=np.r_[prev['d'], smp['d']])
    return rows, samples


def plant(run: Path, plant_id: str, config: Path = CONFIG) -> dict:
    cfg = read_json(config)['plants'][plant_id]
    return measure_structure(ROOT / cfg['capture'] / 'edit_session', ROOT / cfg['labels'] / 'seed_with_imports.backup.json',
                             Path(run) / plant_id / 'structure' / 'structure.json')


def measure_structure(session: Path, backup: Path, spath: Path) -> dict:
    """Main-stem and petiole diameters for one plant (session with poses, the labels backup, S3 structure.json)."""
    capture = read_json(Path(session) / 'capture.json')
    cams = Cameras(capture)
    dets = read_json(backup)['variants']['__all__'].get('membership', {}).get('detections', {})
    structure = read_json(spath)
    out = dict(plant_id=capture.get('plant_id'), structure=str(spath), structure_sha256=file_hash(Path(spath)),
               labels_sha256=file_hash(Path(backup)), validated_metric=False)
    stem = structure.get('stem') or {}
    posed = sorted(k for k in cams.frames if cams.posed(k))
    if stem.get('status') == 'fitted':
        axis = np.array(stem['axis'], float)
        rows, samples = _photos(cams, posed, dets, 'main-stem', axis)
        out['main_stem'] = dict(axis_method=stem.get('method'), previous_diameter_mm=stem.get('diameter_mm'),
                                previous_method='whole-polygon PCA width (fit_stem)' if stem.get('method') == 'ray_fit' else None,
                                per_photo=rows, **_summary(rows, samples))
    else:
        out['main_stem'] = dict(status='unavailable', reason='no fitted main-stem axis in S3')
    pets = []
    for p in structure.get('petioles') or []:
        if p.get('status') != 'fitted':
            continue
        seg = np.array([p['near_end'], p['far_end']], float)
        rows, samples = _photos(cams, posed, dets, 'sub-stem', seg)
        rows = [r for r in rows if r.get('status') == 'measured']  # every sub-stem polygon is tried; keep those on this petiole
        pets.append(dict(region=p['region'], per_photo=rows, **_summary(rows, samples)))
    out['petioles'] = pets
    return out


def run(run_dir: Path, out: Path, plants: list[str] | None = None) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    plants = plants or list(read_json(CONFIG)['plants'])
    res = dict(schema='stem-thickness-1', run=str(run_dir), method=__doc__.split('\n\n')[1].strip(),
               max_axis_gap_px=MAX_AXIS_GAP_PX, validated_metric=False,
               plants={p: plant(Path(run_dir), p) for p in plants})
    out.mkdir(parents=True)
    write_json(out / 'stem_thickness.json', res)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--plant', nargs='*')
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    r = run(a.run, a.out, a.plant)
    for p, d in r['plants'].items():
        m = d['main_stem']
        print(p, 'main stem:', {k: m.get(k) for k in ('axis_method', 'previous_diameter_mm', 'status', 'diameter_mm', 'photos', 'steady_photos', 'steady_spread_pct', 'per_photo_width')}
              if m.get('status') == 'measured' else m, '| petioles:', [(q['region'], q.get('diameter_mm'), q.get('photos')) for q in d['petioles']])


if __name__ == '__main__':
    main()
