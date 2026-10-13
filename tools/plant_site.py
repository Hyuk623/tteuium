"""One self-contained 3D status page for every plant of a pipeline run (the 'dwarf tomato 3D' site format).

    python -X utf8 -m tools.plant_site --run build/pipeline_<ts> [--out build/pipeline_<ts>/site.html]

Reads only what the run already produced -- capture.json (cameras), S3 structure (hull, compound regions, stem,
petioles, overlays), S7 hierarchy (confirmed and proposed leaflets), the growth record and the imported labels --
and writes one HTML file with a plant switcher. Nothing is recomputed. Everything shown is diagnostic: the camera
poses fail the 1 px gate. Layout and wording follow the page published on 2026-09-22 for dwt_01/dwt_02
(user request 2026-09-25).
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import re
from collections import Counter
from html import escape
import os
from pathlib import Path
from urllib.parse import quote

import cv2
import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, read_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
TEMPLATE = Path(__file__).with_name('plant_site.html')
#: Hull points kept per plant (the page draws every one), coordinates stored as integers of COORD_SCALE mm.
MAX_HULL_POINTS, COORD_SCALE = 16000, 0.5
#: Overlay thumbnails: longest side and JPEG quality.
THUMB_PX, THUMB_Q = 720, 70
LABEL_KEYS = ('leaflet', 'compoundleaves', 'sub-stem', 'main-stem', 'growth-shoot')


def board_rect(spec_path: Path) -> list:
    from tomato3d.calib.board import build_charuco_board, sheet_to_board_mm
    from tomato3d.config import get_settings  # noqa: F401  (spec model lives with the settings)
    from tools.import_organized_capture import BoardSpec
    spec = BoardSpec.model_validate_json(Path(spec_path).read_text(encoding='utf-8'))
    board = build_charuco_board(spec)
    nx, ny = board.getChessboardSize()
    s = board.getSquareLength()
    sheet = np.array([[0, 0, 0], [nx * s, 0, 0], [nx * s, ny * s, 0], [0, ny * s, 0]], float)
    return np.round(sheet_to_board_mm(sheet, spec), 1).tolist()


def camera(frame: dict, labels: Counter, geometry: dict | None = None) -> dict:
    code = frame['view_code']
    geometry = geometry or dict(group='unavailable', grouping_source='reference_unavailable', elevation_deg=None)
    group = geometry['group']
    out = dict(view=code, group=group, pose=frame['pose_status'], reproj_px=frame.get('reprojection_error_px'),
               gate=bool(frame.get('passes_pose_gate')), markers=frame.get('n_markers_detected'),
               labels={k: labels.get(k, 0) for k in LABEL_KEYS}, view_geometry=geometry)
    if frame['pose_status'] in ('solved', 'solved_marker_corners') and frame.get('rvec_rad') is not None:
        R = cv2.Rodrigues(np.array(frame['rvec_rad'], float))[0]
        t = np.array(frame['tvec_mm'], float)
        out.update(centre_mm=np.round(-R.T @ t, 2).tolist(), axis=np.round(R.T @ [0, 0, 1], 4).tolist(),
                   up=np.round(-(R.T @ [0, 1, 0]), 4).tolist())
    return out


def thumb(path: Path) -> str:
    im = Image.open(path).convert('RGB')
    im.thumbnail((THUMB_PX, THUMB_PX))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=THUMB_Q)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def viewer_scene(path: Path) -> dict:
    m = re.search(r'const D = (\{.*?\});\n', path.read_text(encoding='utf-8'), re.S)
    return json.loads(m.group(1)) if m else {}


def plant_data(name: str, cfg: dict, run: Path, spec_rect: list) -> dict:
    session = ROOT / cfg['pose_session'] if cfg.get('pose_session') else ROOT / cfg['capture'] / 'edit_session'
    cap = read_json(session / 'capture.json')
    from tools.plant_structure import Cameras
    from tools.leaf_area_geometry import view_geometry
    cams = Cameras(cap)
    grouping = cfg.get('view_grouping', cap.get('view_grouping'))
    seed = read_json(ROOT / cfg['labels'] / 'seed_with_imports.backup.json')
    dets = seed['variants']['__all__'].get('membership', {}).get('detections', {})
    counts = {k.lower(): Counter(d['class_name'] for d in v) for k, v in dets.items()}
    growth_path = ROOT / cfg['growth'] if cfg.get('growth') else None
    growth = read_json(growth_path) if growth_path and growth_path.exists() else {}
    d = dict(plant=name, capture_date=cap.get('session_id', '').split('_')[-1], board_rect_mm=spec_rect,
             cameras=[camera(f, counts.get(f['image_file'].lower(), Counter()),
                             view_geometry(cams, f['image_file'].lower(), grouping)) for f in cap['frames']],
             growth=[dict(id=e['compound_leaf_id'], leaflets=e.get('leaflet_count'), unfolding=bool(e.get('is_unfolding')))
                     for e in growth.get('compound_leaves', [])],
             growth_shoots=growth.get('growth_shoot_count'))
    sdir = run / name / 'structure'
    if not (sdir / 'structure.json').exists():
        return dict(d, hull=None, stem=None, substems=[], views={}, confirmed=[], proposed=[], questions=0, feature_pose_views=[])
    st = read_json(sdir / 'structure.json')
    rows = list(csv.reader(open(sdir / 'hull_voxels.csv', encoding='utf-8')))[1:]
    H = np.array([[float(r[0]), float(r[1]), float(r[2])] for r in rows])
    lab = np.array([int(r[3]) for r in rows])
    regions = sorted(st['compound_regions'], key=lambda r: r['region'])
    colour = {r['region']: n for n, r in enumerate(regions)}           # colour slot A, B, C, ...
    step = max(1, len(H) // MAX_HULL_POINTS)
    hier = read_json(run / name / 'hierarchy' / 'hierarchy.json') if (run / name / 'hierarchy' / 'hierarchy.json').exists() else {}
    confirmed_by_region = Counter()
    for c in hier.get('compound_leaves', []):
        confirmed_by_region[c['region']] = len(c.get('leaflets', []))
    proposed_by_region = Counter(p.get('compound_region') for p in hier.get('proposed_leaflets', []) if p.get('status') == 'region')
    recorded = {g['id']: g for g in d['growth']}
    compounds = []
    for r in regions:
        rec = recorded.get(r.get('proposed_name'))
        compounds.append(dict(slot=colour[r['region']], name=r.get('proposed_name'), voxels=r['voxels'], z=r['median_z_mm'],
                              fragment=bool(r.get('fragment')), name_source=r.get('name_source', 'proposal'),
                              truth=rec['leaflets'] if rec else None, unfolding=bool(rec and rec['unfolding']),
                              confirmed=confirmed_by_region.get(r['region'], 0), proposed=proposed_by_region.get(r['region'], 0)))
    hull = dict(points=np.round(H[::step] / COORD_SCALE).astype(int).ravel().tolist(),
                labels=[colour.get(int(k), -1) for k in lab[::step]], coord_scale=COORD_SCALE, voxel_mm=st['hull']['voxel_mm'],
                volume_cm3=st['hull']['occupancy_cm3'], extent=st['hull']['extent_mm'],
                explained={Path(k).stem[-2:]: v for k, v in st['hull']['silhouette_explained_pct'].items()},
                views_used=[Path(v).stem[-2:] for v in st['views_used']], compounds=compounds,
                unassigned=int((lab < 0).sum()), naming_note=st['compound_region_meta'].get('naming'))
    stem = None
    if st['stem'].get('status') == 'fitted':
        s = st['stem']
        dist = s.get('ray_line_distance_mm') or s.get('slice_centre_distance_mm') or {}
        stem = dict(axis=s['axis'], diameter_mm=s.get('diameter_mm'), median_dist_mm=dist.get('median'),
                    p90_dist_mm=dist.get('p90'), views=[Path(v).stem[-2:] for v in s['views']], tilt_deg=s.get('tilt_deg'),
                    method=s.get('method', 'ray_fit'))
    else:
        stem = dict(unavailable=st['stem'].get('reason', 'not fitted'))
    substems = []
    for p in st['petioles']:
        if p.get('status') != 'fitted':
            continue
        a, b = np.array(p['near_end']), np.array(p['far_end'])
        u = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        substems.append(dict(slot=colour.get(p['region']), name=next((c['name'] for c in compounds if c['slot'] == colour.get(p['region'])), None),
                             near_end=p['near_end'], far_end=p['far_end'], two_view_end=np.round(a + u * (p['length_two_view_mm'] or 0), 2).tolist(),
                             length_two_view_mm=p['length_two_view_mm'], extent_any_view_mm=p['extent_any_view_mm'],
                             elevation_deg=p['elevation_deg'], median_dist_mm=p['ray_line_distance_mm']['median'],
                             near_end_to_stem_mm=p['near_end_to_stem_mm'], views=[Path(v).stem[-2:] for v in p['views']]))
    views = {}
    for f in sorted((sdir / 'overlays').glob('*.jpg')):
        code = f.stem[-2:]
        fr = next(x for x in cap['frames'] if x['view_code'] == code)
        views[code] = dict(img=thumb(f), reproj=round(fr.get('reprojection_error_px') or 0, 1))
    scene = viewer_scene(run / name / 'hierarchy' / 'viewer.html')
    q = lambda pts: np.round(np.array(pts, float) / COORD_SCALE).astype(int).tolist()
    confirmed = []
    by_key = {l['key']: l['points'] for l in scene.get('leaflets', [])}
    for c in hier.get('compound_leaves', []):
        for l in c.get('leaflets', []):
            key = l['leaf_key'].split('|')[0]
            if key in by_key:
                confirmed.append(dict(key=key, compound=c.get('proposed_name'), photos=[Path(v).stem[-2:] for v in l['photos']],
                                      voxels=l.get('voxels'), points=q(by_key[key])))
    pts_prop = {p['key']: p['points'] for p in scene.get('proposed', [])}
    names = {r['region']: r.get('proposed_name') for r in regions}
    proposed = [dict(key=p['key'], compound=names.get(p.get('compound_region')), photos=[Path(v).stem[-2:] for v in p['photos']],
                     feature_pose=p.get('feature_pose'), voxels=p.get('voxels'), points=q(pts_prop[p['key']]))
                for p in hier.get('proposed_leaflets', []) if p.get('status') == 'region' and p['key'] in pts_prop]
    s4 = read_json(run / name / 'candidates' / 'candidates.json') if (run / name / 'candidates' / 'candidates.json').exists() else {}
    return dict(d, hull=hull, stem=stem, substems=substems, views=views, confirmed=confirmed, proposed=proposed,
                questions=len(s4.get('items', [])), feature_pose_views=[Path(v).stem[-2:] for v in s4.get('feature_pose_views', [])])


def light_panel(run: Path, result: Path, out: Path) -> str:
    """Link an explicit immutable bridge result; never discover a newest run."""
    from tools.plant_light_bridge import stale
    from tools.leaf_light.common import BUILD
    manifest = read_json(result / 'manifest.json')
    if Path(manifest['run']).resolve() != run.resolve():
        raise StudyError('Light result belongs to another source run')
    if stale(result)['stale']:
        raise StudyError('Light result is stale; create a new bridge run')
    if not out.resolve().is_relative_to(BUILD.resolve()) or out.exists():
        raise StudyError('Linked site must be a new file under build/')
    url = quote(os.path.relpath(result / 'report.html', out.parent).replace('\\', '/'), safe='/.:')
    label = escape(f"{manifest['plant_id']} / {manifest['session_id']} — {manifest['status']}")
    return (f'<section class="light-connection" style="padding:16px;border:1px solid #a0b5a5;border-radius:10px">'
            f'<h3>Plant light connection</h3><p>{label}</p>'
            '<p>Physical validation pending. Surface geometry and input blockers are recorded separately.</p>'
            f'<a href="{escape(url, quote=True)}">Open source-linked light results</a></section>')


def build(run: Path, out: Path | None = None, config: Path | None = None,
          light_result: Path | None = None) -> Path:
    run = Path(run)
    if light_result is not None and out is None:
        raise StudyError('Supply a fresh --out when linking light results')
    panel = light_panel(run, light_result, Path(out)) if light_result is not None else ''
    cfg = read_json(config or CONFIG)
    spec_rect = None
    data = {}
    for name, pc in cfg['plants'].items():
        if not (run / name).exists():
            continue
        if spec_rect is None:
            sess = ROOT / pc['capture'] / 'edit_session'
            spec = Path(read_json(sess / 'capture.json')['board_spec_path'])
            spec_rect = board_rect(spec if spec.is_absolute() else sess / spec)
        data[name] = plant_data(name, pc, run, spec_rect)
    if not data:
        raise StudyError(f'No plant folders in {run}')
    doc = dict(run=run.name, plants=data)
    html = TEMPLATE.read_text(encoding='utf-8').replace('__DATA__', json.dumps(doc, ensure_ascii=False).replace('</', '<\\/'))
    if panel:
        html = html.replace('<div class="wrap">', '<div class="wrap">' + panel, 1)
    out = Path(out) if out else run / 'site.html'
    out.write_text(html, encoding='utf-8')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--light-result', type=Path, help='Explicit plant_light_bridge result; requires a fresh --out')
    a = ap.parse_args()
    out = build(a.run, a.out, light_result=a.light_result)
    print(json.dumps(dict(out=str(out), kb=out.stat().st_size // 1024)))


if __name__ == '__main__':
    main()
