"""Cross-view leaflet candidates for human review (pipeline stage S4).

    python -m tools.cross_view_candidates --session <edit_session> --backup <editor backup> \\
        --batch build/leaflet_mask_batch_20260922/<plant> --structure <S3 out> \\
        [--decisions <folder or file> ...] --out <new folder>

Uses the human-accepted leaflet masks of the photos with a solved pose. Each mask is carried onto the visual hull
(S3) through a z-buffer, so a mask only claims the voxels its camera actually sees. Two masks from different photos
that claim mostly the same voxels are proposed as the same physical leaflet; one mask spread over two masks is a
merge suspect; two masks gathering on one mask are a duplicate suspect. These are proposals only.

It also asks, for every leaflet identity already confirmed in the backup, whether each of its photos shows the whole
leaflet or only part of it (the visibility Document 06 needs), because that is a human judgment.

Output: candidates.json and review.html. The page is a local file with no server or upload; it keeps progress in the
browser and saves the decisions as one JSON file (threshold-decision-log-1 records) that
`tools.cross_view_identity_import` reads. Pairs already decided in --decisions are not asked again.
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json
from tools.leaflet_mask_batch import Batch
from tools.plant_structure import Cameras, plain

SCHEMA = 'cross-view-candidates-1'
#: A mask must claim at least this many visible hull voxels to take part.
MIN_VOXELS = 30
#: Mutual best pair: both shares at least this.
MIN_MATCH_SHARE = 0.3
#: Merge / duplicate suspects: each involved share at least this.
MIN_SPLIT_SHARE = 0.2
#: z-buffer bin (px) and depth tolerance (mm) for "seen by this camera".
BIN_PX, DEPTH_TOL_MM = 12, 3.0
COLOURS = [(255, 60, 170), (60, 200, 255), (255, 210, 40), (120, 255, 120)]


def read_hull(structure: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    rows = list(csv.DictReader(open(Path(structure) / 'hull_voxels.csv', encoding='utf-8')))
    H = np.array([[float(r['x_mm']), float(r['y_mm']), float(r['z_mm'])] for r in rows])
    lab = np.array([int(r['compound_region']) for r in rows])
    return H, lab, read_json(Path(structure) / 'structure.json')


def zbuffer(cams, key, H):
    p = cams.project(key, H)
    d = cams.depth(key, H)
    pi = np.round(p).astype(int)
    k = (pi[:, 1] // BIN_PX) * 100000 + pi[:, 0] // BIN_PX
    order = np.lexsort((d, k))
    ks = k[order]
    first_idx = np.r_[0, np.flatnonzero(np.diff(ks)) + 1]
    first_depth = dict(zip(ks[first_idx], d[order][first_idx]))
    seen = d <= np.array([first_depth[x] for x in k]) + DEPTH_TOL_MM
    return seen, pi


def mask_voxels(batch, item, seen, pi):
    m, meta = batch.mask(item)
    x0, y0 = meta['crop_px'][:2]
    h, w = m.shape
    ok = seen & (pi[:, 0] >= x0) & (pi[:, 0] < x0 + w) & (pi[:, 1] >= y0) & (pi[:, 1] < y0 + h)
    idx = np.flatnonzero(ok)
    return idx[m[pi[idx, 1] - y0, pi[idx, 0] - x0]]


def load_decided(paths) -> set:
    from tools.cross_view_identity_import import load_decisions
    return {d['object_id'] for d in load_decisions([Path(p) for p in paths])} if paths else set()


def crop(session, batch, items, colours, cache):
    f = items[0]['image_file']
    if f not in cache:
        cache[f] = Image.open(Path(session) / items[0]['image_path']).convert('RGB')
    boxes = [it['prompts']['box_px'] for it in items]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    pad = max(x1 - x0, y1 - y0) * 0.45 + 40
    W, Hh = cache[f].size
    box = (int(max(x0 - pad, 0)), int(max(y0 - pad, 0)), int(min(x1 + pad, W)), int(min(y1 + pad, Hh)))
    c = cache[f].crop(box).convert('RGBA')
    ov = Image.new('RGBA', c.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    for it, col in zip(items, colours):
        m, meta = batch.mask(it)
        mx, my = meta['crop_px'][:2]
        layer = np.zeros((c.size[1], c.size[0]), bool)
        ys, xs = np.nonzero(m)
        xs, ys = xs + mx - box[0], ys + my - box[1]
        ok = (xs >= 0) & (xs < c.size[0]) & (ys >= 0) & (ys < c.size[1])
        layer[ys[ok], xs[ok]] = True
        edge = layer & ~ndimage.binary_erosion(layer, iterations=3)
        fill = Image.fromarray((layer * 60).astype(np.uint8))
        ov.paste(Image.new('RGBA', c.size, col + (255,)), (0, 0), fill)
        ov.paste(Image.new('RGBA', c.size, col + (255,)), (0, 0), Image.fromarray((edge * 255).astype(np.uint8)))
        b = it['prompts']['box_px']
        dr.rectangle([b[0] - box[0], b[1] - box[1], b[2] - box[0], b[3] - box[1]], outline=col + (255,), width=2)
    c = Image.alpha_composite(c, ov).convert('RGB')
    c.thumbnail((380, 380))
    buf = io.BytesIO()
    c.save(buf, 'JPEG', quality=80)
    return dict(view=Path(f).stem[-2:], img='data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(),
                ids=[it['id'] for it in items], sources=[it['source_annotation_id'] for it in items])


def add_feature_poses(cams, capture_frames: dict, path: Path | None) -> list[str]:
    """Photos posed from image features (tools.feature_pose_candidate) that met its policy, added for S4 only.

    They never enter the hull (S3 keeps the board-posed photos); here they only carry masks onto that hull.
    A user decision (2026-09-24, human-check page) allows them as diagnostic candidates; items that use one
    get their own rule id so their decisions can be told apart later."""
    if not path:
        return []
    added = []
    rep = read_json(path)
    for c in rep.get('candidates', []) + rep.get('second_round', []):
        key = c['image_file'].lower()
        if c.get('status') != 'solved' or not c.get('meets_policy') or key not in cams.frames or cams.posed(key):
            continue
        cams.frames[key] = dict(cams.frames[key], rvec_rad=c['rvec_rad'], tvec_mm=c['tvec_mm'],
                                pose_status='feature_diagnostic', pose_source=c.get('pose_source'))
        added.append(key)
    return added


def build(session: Path, backup_path: Path, batch_root: Path, structure: Path, out: Path, decisions=(),
          extra_poses: Path | None = None) -> dict:
    session, out = Path(session), Path(out)
    if out.exists():
        raise StudyError(f'Output exists; choose a new directory: {out}')
    capture = read_json(session / 'capture.json')
    cams = Cameras(capture)
    backup = read_json(backup_path)
    plant = backup['plant_id']
    H, lab, struct = read_hull(structure)
    batch = Batch(Path(batch_root))
    feature_views = add_feature_poses(cams, capture, extra_poses)
    posed = [v for v in struct['views_used']] + feature_views
    accepted = defaultdict(list)
    for i in batch.manifest['ids']:
        it = batch.item(i)
        if it['review'] in ('accepted', 'accepted_by_user') and it['image_file'].lower() in posed:
            accepted[it['image_file'].lower()].append(it)
    vox = {}
    for v in posed:
        if not accepted.get(v):
            continue
        seen, pi = zbuffer(cams, v, H)
        for it in accepted[v]:
            idx = mask_voxels(batch, it, seen, pi)
            if len(idx) >= MIN_VOXELS:
                vox[it['id']] = (v, set(idx.tolist()), it)
    decided = load_decided(decisions)
    # masks already linked to the same confirmed leaf need no question
    state = backup['variants']['__all__']
    linked = {}
    for key, leaf in state.get('leaflets', {}).items():
        for image_key, b in leaf.get('bboxes', {}).items():
            sid = str((b.get('source_detection') or {}).get('source_annotation_id'))
            linked[(image_key.lower(), sid)] = key
    same_leaf = lambda a, b: linked.get((vox[a][0], str(vox[a][2]['source_annotation_id']))) is not None and \
        linked.get((vox[a][0], str(vox[a][2]['source_annotation_id']))) == linked.get((vox[b][0], str(vox[b][2]['source_annotation_id'])))
    views = sorted({v for v, _, _ in vox.values()})
    items = []
    for ai, va in enumerate(views):
        for vb in views[ai + 1:]:
            A = [k for k in vox if vox[k][0] == va]
            B = [k for k in vox if vox[k][0] == vb]
            share = {(a, b): len(vox[a][1] & vox[b][1]) / len(vox[a][1]) for a in A for b in B}
            share.update({(b, a): len(vox[a][1] & vox[b][1]) / len(vox[b][1]) for a in A for b in B})
            best = lambda x, pool: max(pool, key=lambda y: share[(x, y)]) if pool else None
            for a in A:
                b = best(a, B)
                if b and best(b, A) == a and min(share[(a, b)], share[(b, a)]) >= MIN_MATCH_SHARE and not same_leaf(a, b):
                    items.append(dict(id=f'match_{a}_{b}', kind='match', masks=[[a], [b]],
                                      rule_id='cross_view_mask_cooccurrence' + ('_feature_pose' if {va, vb} & set(feature_views) else ''),
                                      score=round(min(share[(a, b)], share[(b, a)]), 3),
                                      scores=dict(share_ab=round(share[(a, b)], 3), share_ba=round(share[(b, a)], 3))))
            for src, pool in ((A, B), (B, A)):
                for a in src:
                    top = sorted(pool, key=lambda y: -share[(a, y)])[:2]
                    if len(top) == 2 and all(share[(a, y)] >= MIN_SPLIT_SHARE for y in top):
                        items.append(dict(id=f'merge_{a}', kind='merge', rule_id='mask_merge_suspect', masks=[[a], top],
                                          score=round(min(share[(a, y)] for y in top), 3), scores=dict(shares=[round(share[(a, y)], 3) for y in top])))
                gather = defaultdict(list)
                for a in src:
                    t = best(a, pool)
                    if t and share[(a, t)] >= MIN_MATCH_SHARE:
                        gather[t].append(a)
                for t, srcs in gather.items():
                    if len(srcs) >= 2:
                        srcs = sorted(srcs, key=lambda y: -share[(y, t)])[:3]
                        items.append(dict(id=f'dup_{t}_{vox[srcs[0]][0][-6:-4]}', kind='dup', rule_id='mask_duplicate_suspect', masks=[srcs, [t]],
                                          score=round(min(share[(y, t)] for y in srcs), 3), scores=dict(shares=[round(share[(y, t)], 3) for y in srcs])))
    for it in items:  # any item resting on a feature-posed photo is marked, not only matches
        if feature_views and not it['rule_id'].endswith('_feature_pose') and                 any(vox[m][0] in feature_views for g in it['masks'] for m in g):
            it['rule_id'] += '_feature_pose'
    seen_ids, uniq = set(), []
    for it in items:
        if it['id'] not in seen_ids and it['id'] not in decided:
            seen_ids.add(it['id']); uniq.append(it)
    # visibility questions for confirmed identities
    by_id = {it['id']: it for v in accepted.values() for it in v}
    by_source = {(it['image_file'].lower(), str(it['source_annotation_id'])): it for v in accepted.values() for it in v}
    vis_items = []
    for key, leaf in sorted(state.get('leaflets', {}).items()):
        obs = []
        for image_key, b in sorted(leaf.get('bboxes', {}).items()):
            st = leaf.get('view_status', {}).get(image_key, {})
            it = by_source.get((image_key.lower(), str((b.get('source_detection') or {}).get('source_annotation_id'))))
            if st.get('identity_review') == 'confirmed' and st.get('visibility', 'unknown') == 'unknown' and it:
                obs.append(it['id'])
        if obs and f'vis_{key.split("|")[0]}' not in decided:
            vis_items.append(dict(id=f'vis_{key.split("|")[0]}', kind='vis', rule_id='visibility_review', leaf_key=key, masks=[[m] for m in obs], score=None, scores={}))
    cache = {}
    for it in uniq + vis_items:
        panels = []
        for n, group in enumerate(it['masks']):
            its = [by_id.get(m) or vox[m][2] for m in group]
            cols = COLOURS[n:n + 1] * len(its) if len(its) == 1 else COLOURS[1:1 + len(its)] if it['kind'] == 'merge' else COLOURS[:len(its)]
            if it['kind'] == 'dup' and n == 1:
                cols = [COLOURS[3]]
            panels.append(crop(session, batch, its, cols, cache))
        it['panels'] = panels
    out.mkdir(parents=True)
    doc = plain(dict(schema=SCHEMA, plant=plant, session=capture.get('session_id'), views=views, feature_pose_views=feature_views,
                     parameters=dict(min_voxels=MIN_VOXELS, min_match_share=MIN_MATCH_SHARE, min_split_share=MIN_SPLIT_SHARE,
                                     bin_px=BIN_PX, depth_tol_mm=DEPTH_TOL_MM),
                     masks_used=len(vox), accepted_masks_in_posed_photos=sum(len(v) for v in accepted.values()),
                     already_decided=len(decided), items=uniq + vis_items,
                     note='proposals only; shares are voxel overlap fractions, not probabilities'))
    write_json(out / 'candidates.json', {**doc, 'items': [{k: v for k, v in it.items() if k != 'panels'} for it in doc['items']]})
    template = (Path(__file__).with_name('cross_view_review.html')).read_text(encoding='utf-8')
    (out / 'review.html').write_text(template.replace('__DATA__', json.dumps(doc, ensure_ascii=False)), encoding='utf-8')
    return dict(items=len(uniq), visibility_items=len(vis_items), masks_used=len(vox), already_decided=len(decided),
                feature_pose_views=feature_views)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for a in ('session', 'backup', 'batch', 'structure', 'out'):
        ap.add_argument('--' + a, required=True, type=Path)
    ap.add_argument('--decisions', nargs='*', type=Path, default=[])
    ap.add_argument('--extra-poses', type=Path, help='feature_poses.json; photos meeting its policy join as diagnostic views')
    a = ap.parse_args()
    print(json.dumps(build(a.session, a.backup, a.batch, a.structure, a.out, a.decisions, a.extra_poses)))


if __name__ == '__main__':
    main()
