"""Organ hierarchy and 3D viewer for one plant (pipeline stage S7).

    python -m tools.plant_hierarchy --session <edit_session> --backup <identities backup> \\
        --batch <mask batch or omit> --structure <S3 out> [--growth <growth.json>] --out <new folder>

Builds plant > main stem > petiole > compound leaf > leaflet from what earlier stages established, and says
`unavailable` with a reason for everything they did not. A leaflet is included only when its physical identity was
confirmed by a human in at least two posed photos; its 3D region is the hull voxels inside its accepted mask in every
one of those photos and seen by at least one of their cameras. Compound membership of a leaflet is the hull region
most of its voxels fall in, reported as a proposal (the editor's reviewed membership is not required yet).

The leaflet blade direction (azimuth/elevation of base -> tip) needs reviewed tip/base points, which do not exist yet;
it is reported as unavailable, while the leaflet's position around the stem (azimuth of its centroid) is given.
Output: hierarchy.json and viewer.html (local file, no network).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from tools.cross_view_candidates import mask_voxels, read_hull, zbuffer
from tools.leaf_light.common import StudyError, file_hash, read_json, write_json
from tools.plant_structure import Cameras, plain

SCHEMA = 'plant-hierarchy-1'
MAX_VIEW_POINTS = 15000


def leaflet_regions(cams, backup, batch, H, views):
    state = backup['variants']['__all__']
    if batch is None:
        return [], 'no mask batch: leaflet regions need accepted masks'
    by_source = {}
    for i in batch.manifest['ids']:
        it = batch.item(i)
        if it['review'] in ('accepted', 'accepted_by_user'):
            by_source[(it['image_file'].lower(), str(it['source_annotation_id']))] = it
    zb = {}
    out = []
    for key, leaf in sorted(state.get('leaflets', {}).items()):
        obs = []
        for image_key, box in sorted(leaf.get('bboxes', {}).items()):
            st = leaf.get('view_status', {}).get(image_key, {})
            if st.get('identity_review') != 'confirmed' or image_key.lower() not in views:
                continue
            it = by_source.get((image_key.lower(), str((box.get('source_detection') or {}).get('source_annotation_id'))))
            obs.append(dict(photo=image_key, visibility=st.get('visibility', 'unknown'), mask=it['id'] if it else None))
        usable = [o for o in obs if o['mask']]
        entry = dict(leaf_key=key, photos=[o['photo'] for o in obs], visibility={o['photo']: o['visibility'] for o in obs},
                     review=leaf.get('cross_view_review'))
        if len(usable) < 2:
            entry.update(status='unavailable', reason='fewer than two confirmed posed photos with an accepted mask')
            out.append(entry)
            continue
        inside_all = np.ones(len(H), bool)
        seen_any = np.zeros(len(H), bool)
        for o in usable:
            v = o['photo'].lower()
            if v not in zb:
                zb[v] = zbuffer(cams, v, H)
            seen, pi = zb[v]
            item = batch.item(o['mask'])
            raw = np.zeros(len(H), bool)
            raw[mask_voxels(batch, item, np.ones(len(H), bool), pi)] = True
            vis = np.zeros(len(H), bool)
            vis[mask_voxels(batch, item, seen, pi)] = True
            inside_all &= raw
            seen_any |= vis
        sel = np.flatnonzero(inside_all & seen_any)
        if not len(sel):
            entry.update(status='unavailable', reason='masks share no seen hull voxels')
            out.append(entry)
            continue
        X = H[sel]
        entry.update(status='region', voxels=int(len(sel)), centroid_mm=X.mean(0).round(1).tolist(),
                     extent_p5_p95_mm=(np.percentile(X, 95, 0) - np.percentile(X, 5, 0)).round(1).tolist(), _idx=sel)
        out.append(entry)
    return out, None


def azimuth_around(stem, X):
    if stem.get('status') != 'fitted':
        return None
    ax = np.array(stem['axis'])
    P, u = ax[0], (ax[-1] - ax[0]) / np.linalg.norm(ax[-1] - ax[0])
    w = np.asarray(X) - P
    w = w - (w @ u) * u
    return round(float(np.degrees(np.arctan2(w[1], w[0])) % 360), 1), round(float(np.linalg.norm(w)), 1)


#: A mutual cross-view match joins a proposed leaflet only at this share or above. On dwt_01 every reviewed pair
#: at >= 0.45 was judged the same leaflet (7/7); 0.31-0.34 was mixed (2 same / 3 different).
PROPOSAL_MIN_SHARE = 0.45


def proposed_regions(cams, batch, H, candidates_path, min_share: float = PROPOSAL_MIN_SHARE):
    """Leaflets proposed from S4 match candidates before any human decision (user request 2026-09-24).

    Mutual matches at >= min_share are joined (union); a group holding two masks of one photo contradicts itself
    and is not drawn. The 3D region follows the confirmed-leaflet rule. Everything here is a proposal."""
    if batch is None or not candidates_path or not Path(candidates_path).exists():
        return [], 'no S4 candidates'
    cand = read_json(candidates_path)
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            a = parent[a]
        return a

    used = 0
    for it in cand['items']:
        if it['kind'] != 'match' or (it.get('score') or 0) < min_share:
            continue
        a, b = it['masks'][0][0], it['masks'][1][0]
        parent[find(a)] = find(b)
        used += 1
    groups = {}
    for m in list(parent):
        groups.setdefault(find(m), []).append(m)
    zb, out = {}, []
    for n, masks in enumerate(sorted(groups.values(), key=lambda g: sorted(g)), 1):
        items = [batch.item(m) for m in sorted(masks)]
        photos = [i['image_file'].lower() for i in items]
        entry = dict(key=f'P{n:02d}', masks=[i['id'] for i in items], photos=photos,
                     feature_pose=any(cams.frames[v].get('pose_status') == 'feature_diagnostic' for v in photos))
        if len(set(photos)) < len(photos):
            entry.update(status='conflict', reason='two masks of one photo in the same group')
            out.append(entry)
            continue
        inside_all, seen_any = np.ones(len(H), bool), np.zeros(len(H), bool)
        for v, item in zip(photos, items):
            if v not in zb:
                zb[v] = zbuffer(cams, v, H)
            seen, pi = zb[v]
            raw = np.zeros(len(H), bool)
            raw[mask_voxels(batch, item, np.ones(len(H), bool), pi)] = True
            vis = np.zeros(len(H), bool)
            vis[mask_voxels(batch, item, seen, pi)] = True
            inside_all &= raw
            seen_any |= vis
        sel = np.flatnonzero(inside_all & seen_any)
        if not len(sel):
            entry.update(status='unavailable', reason='masks share no seen hull voxels')
        else:
            entry.update(status='region', voxels=int(len(sel)), centroid_mm=H[sel].mean(0).round(1).tolist(), _idx=sel)
        out.append(entry)
    return out, f'{used} mutual matches at share >= {min_share} joined into {len(out)} groups; proposals, not decisions'


def build(session: Path, backup_path: Path, structure: Path, out: Path, batch_root: Path | None = None,
          growth_path: Path | None = None, proposals: Path | None = None, extra_poses: Path | None = None) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists; choose a new directory: {out}')
    capture = read_json(Path(session) / 'capture.json')
    cams = Cameras(capture)
    backup = read_json(backup_path)
    H, lab, struct = read_hull(structure)
    batch = None
    if batch_root and Path(batch_root).exists():
        from tools.leaflet_mask_batch import Batch
        batch = Batch(Path(batch_root))
    growth = read_json(growth_path) if growth_path else None
    views = struct['views_used']
    leaflets, leaflet_note = leaflet_regions(cams, backup, batch, H, views)
    if extra_poses:
        from tools.cross_view_candidates import add_feature_poses
        add_feature_poses(cams, capture, extra_poses)
    proposed, proposal_note = proposed_regions(cams, batch, H, proposals)
    for pr in proposed:
        if pr['status'] == 'region':
            votes = Counter(int(x) for x in lab[pr['_idx']] if x >= 0)
            k, nv = votes.most_common(1)[0] if votes else (None, 0)
            pr.update(compound_region=k, compound_share=round(nv / max(sum(votes.values()), 1), 2) if k is not None else None)
    stem = struct['stem']
    regions = {r['region']: r for r in struct['compound_regions']}
    petioles = {p['region']: p for p in struct['petioles']}
    recorded = {e['compound_leaf_id']: e.get('leaflet_count') for e in (growth or {}).get('compound_leaves', [])}
    compounds = {k: dict(region=k, proposed_name=r['proposed_name'], name_status='proposal (height order)' if r['proposed_name'] else 'unnamed',
                         recorded_leaflet_count=recorded.get(r['proposed_name']), median_z_mm=r['median_z_mm'], voxels=r['voxels'],
                         petiole=petioles.get(k, dict(status='unavailable', reason='no sub-stem polygon assigned to this region')),
                         leaflets=[]) for k, r in regions.items()}
    unassigned = []
    for lf in leaflets:
        if lf['status'] != 'region':
            unassigned.append({k: v for k, v in lf.items() if k != '_idx'})
            continue
        votes = Counter(int(x) for x in lab[lf['_idx']] if x >= 0)
        k, n = votes.most_common(1)[0] if votes else (None, 0)
        az = azimuth_around(stem, lf['centroid_mm'])
        rec = {kk: vv for kk, vv in lf.items() if kk != '_idx'}
        rec.update(compound_region=k, compound_share=round(n / max(sum(votes.values()), 1), 2) if k is not None else None,
                   azimuth_around_stem_deg=az[0] if az else None, distance_from_stem_mm=az[1] if az else None,
                   blade_direction=dict(status='unavailable', reason='needs reviewed tip and base points in two posed photos'),
                   membership_status='proposal from hull region')
        (compounds[k]['leaflets'] if k in compounds else unassigned).append(rec)
    comp_list = sorted(compounds.values(), key=lambda c: -c['median_z_mm'])
    for c in comp_list:
        c['proposed_leaflets'] = sum(p['status'] == 'region' and p.get('compound_region') == c['region'] for p in proposed)
        c['leaflets_with_region'] = len(c['leaflets'])
        c['coverage'] = f"{len(c['leaflets'])}/{c['recorded_leaflet_count']}" if c['recorded_leaflet_count'] else None
    hierarchy = dict(schema=SCHEMA, plant_id=backup['plant_id'], session_id=capture.get('session_id'),
                     inputs=dict(backup=str(backup_path), backup_sha256=file_hash(backup_path), structure=str(structure),
                                 growth=str(growth_path) if growth_path else None),
                     growth_reference=dict(compound_leaf_count=(growth or {}).get('compound_leaf_count'), leaflets=recorded,
                                           growth_shoot_count=(growth or {}).get('growth_shoot_count')) if growth else 'unavailable (no growth record)',
                     stem=stem, compound_leaves=comp_list, unassigned_leaflets=unassigned, leaflet_note=leaflet_note,
                     proposed_leaflets=[{k: v for k, v in p.items() if k != '_idx'} for p in proposed], proposal_note=proposal_note,
                     counts=dict(confirmed_leaflets=len(leaflets), with_region=sum(l['status'] == 'region' for l in leaflets),
                                 recorded_total=sum(v for v in recorded.values() if v) if recorded else None,
                                 proposed_leaflets=sum(p['status'] == 'region' for p in proposed)),
                     validated_metric=False, suitable_for_ppfd=False,
                     limits='poses fail the 1 px gate; names and memberships are proposals; blade directions need tip/base points')
    hierarchy = plain(hierarchy)
    out.mkdir(parents=True)
    write_json(out / 'hierarchy.json', hierarchy)
    step = max(1, len(H) // MAX_VIEW_POINTS)
    scene = dict(plant=backup['plant_id'], hull=dict(points=np.round(H[::step], 1).ravel().tolist(), labels=lab[::step].tolist()),
                 regions=[dict(region=c['region'], name=c['proposed_name']) for c in comp_list],
                 stem=stem.get('axis') if stem.get('status') == 'fitted' else None,
                 petioles=[dict(region=p['region'], a=p['near_end'], b=p['far_end']) for p in struct['petioles'] if p.get('status') == 'fitted'],
                 leaflets=[dict(key=l['leaf_key'].split('|')[0], points=np.round(H[l['_idx']], 1).ravel().tolist()) for l in leaflets if l['status'] == 'region'],
                 proposed=[dict(key=p['key'], feature_pose=p['feature_pose'], points=np.round(H[p['_idx']], 1).ravel().tolist())
                           for p in proposed if p['status'] == 'region'],
                 summary=dict(confirmed=len(leaflets), recorded=hierarchy['counts']['recorded_total'],
                              proposed=hierarchy['counts']['proposed_leaflets']))
    template = Path(__file__).with_name('plant_viewer.html').read_text(encoding='utf-8')
    (out / 'viewer.html').write_text(template.replace('__DATA__', json.dumps(plain(scene), ensure_ascii=False)), encoding='utf-8')
    return hierarchy


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for a in ('session', 'backup', 'structure', 'out'):
        ap.add_argument('--' + a, required=True, type=Path)
    ap.add_argument('--batch', type=Path)
    ap.add_argument('--growth', type=Path)
    ap.add_argument('--proposals', type=Path, help='S4 candidates.json: draw mutual matches as proposed leaflets')
    ap.add_argument('--extra-poses', type=Path, help='feature_poses.json used by those candidates')
    a = ap.parse_args()
    h = build(a.session, a.backup, a.structure, a.out, a.batch, a.growth, a.proposals, a.extra_poses)
    print(json.dumps(h['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
