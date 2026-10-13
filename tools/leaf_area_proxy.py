"""Image proxies for whole-plant leaf area (and the top-view area that light interception needs), 2026-10-01.

    python -X utf8 -m tools.leaf_area_proxy --run build/pipeline_<ts> --out build/leaf_area_proxy_<date>

User goal: total leaf area per plant for all 24 plants without reviewing every leaf, calibrated non-destructively on a
few plants (ruler length x width per leaflet, coefficient k from a few leaflets flattened on the board). This tool makes
the IMAGE side: for every posed photo of a plant, the accepted leaflet masks are converted from pixels to mm^2 with the
depth of the leaf itself, taken from the S3 visual hull (hull voxels that project inside the mask; their 20th depth
percentile = the visible front surface), so near and far leaves get their own scale:  area_mm2 = area_px * (Z / f)^2.

Per photo: projected leaf area (cm^2), number of masks, view group. Per plant: mean / max over side photos, top photo
area (from above: the area that intercepts light from overhead lamps), hull volume. These are PROXIES: occluded leaf parts
are missing in every single photo and a leaflet seen edge-on looks small; the calibration on measured plants absorbs the
average effect. validated_metric stays false until that calibration exists.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json
from tools.plant_structure import Cameras

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
FRONT_PERCENTILE = 20


def masks_by_photo(pc: dict) -> tuple[Path, dict]:
    exp = sorted((ROOT / pc['batch'] / 'exports').glob('accepted_*'))[-1]
    out = {}
    for o in read_json(exp / 'accepted.json')['observations']:
        if o['review'] == 'accepted_by_user' and o.get('organ_class', 'leaflet') == 'leaflet':
            out.setdefault(o['image_file'].lower(), []).append(o)
    return exp, out


def plant(run: Path, plant_id: str, config: Path = CONFIG) -> dict:
    cfgs = read_json(config)['plants']
    pc = cfgs[plant_id]
    session = ROOT / (pc.get('pose_session') or (pc['capture'] + '/edit_session'))
    cams = Cameras(read_json(session / 'capture.json'))
    sdir = Path(run) / plant_id / 'structure'
    H = np.loadtxt(sdir / 'hull_voxels.csv', delimiter=',', skiprows=1, usecols=(0, 1, 2))
    structure = read_json(sdir / 'structure.json')
    exp, masks = masks_by_photo(pc)
    f = float(cams.K[0, 0])
    rows = []
    for key in sorted(k for k in cams.frames if cams.posed(k)):
        obs = masks.get(key, [])
        if not obs:
            continue
        px = np.round(cams.project(key, H)).astype(int)
        depth = cams.depth(key, H)
        W, Hh = cams.size
        ok = (px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < Hh) & (depth > 0)
        total, used, no_depth = 0.0, 0, 0
        for o in obs:
            m = np.asarray(Image.open(exp / o['mask_file'])) > 0
            inside = ok.copy()
            inside[ok] = m[px[ok, 1], px[ok, 0]]
            if inside.sum() < 5:
                no_depth += 1
                continue
            z = float(np.percentile(depth[inside], FRONT_PERCENTILE))
            total += m.sum() * (z / f) ** 2
            used += 1
        frame = cams.frames[key]
        code = frame.get('view_code') or key[-6:-4]
        rows.append(dict(photo=code, group='top' if code.startswith('0') else 'side' if code.startswith('2') else 'middle',
                         pose_status=frame.get('pose_status'), masks=len(obs), masks_used=used, masks_without_depth=no_depth,
                         projected_leaf_area_cm2=round(total / 100.0, 2)))
    side = [r['projected_leaf_area_cm2'] for r in rows if r['group'] == 'side']
    top = [r['projected_leaf_area_cm2'] for r in rows if r['group'] == 'top']
    return dict(plant_id=plant_id, accepted_export=str(exp.relative_to(ROOT)).replace('\\', '/'), accepted_sha256=file_hash(exp / 'accepted.json'),
                hull_cm3=structure['hull']['occupancy_cm3'], hull_views=len(structure['views_used']), photos=rows,
                side_mean_cm2=round(float(np.mean(side)), 2) if side else None, side_max_cm2=round(float(np.max(side)), 2) if side else None,
                side_photos=len(side), top_cm2=round(float(np.mean(top)), 2) if top else None, top_photos=len(top))


def run(run_dir: Path, out: Path, plants=None, config: Path = CONFIG) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    plants = plants or list(read_json(config)['plants'])
    res = dict(schema='leaf-area-proxy-1', run=str(run_dir), front_percentile=FRONT_PERCENTILE, plants=[plant(Path(run_dir), p, config) for p in plants],
               validated_metric=False, note='proxies for whole-plant leaf area; calibrate on non-destructively measured plants before reporting cm2 of leaf')
    out.mkdir(parents=True)
    write_json(out / 'leaf_area_proxy.json', res)
    with open(out / 'per_photo.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['plant_id'] + list(res['plants'][0]['photos'][0]))
        w.writeheader()
        for p in res['plants']:
            for r in p['photos']:
                w.writerow(dict(plant_id=p['plant_id'], **r))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--plant', nargs='*')
    a = ap.parse_args()
    r = run(a.run, a.out, a.plant)
    for p in r['plants']:
        print(p['plant_id'], 'side mean', p['side_mean_cm2'], 'cm2 over', p['side_photos'], 'photos | top', p['top_cm2'], '| hull', p['hull_cm3'], 'cm3',
              [(x['photo'], x['projected_leaf_area_cm2'], f"{x['masks_used']}/{x['masks']}") for x in p['photos']])


if __name__ == '__main__':
    main()
