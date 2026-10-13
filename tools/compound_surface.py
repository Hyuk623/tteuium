"""Audit one-sided tissue surfaces; never repair or approve source geometry.

python -m tools.compound_surface --study build/.../surface_study.json --out build/new_audit
Local patch triangulation requires explicit tissue boundaries and holes. It is
interpolation, not evidence that tissue exists between arbitrary landmarks.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re
from typing import Any

import cv2
import numpy as np
from scipy.spatial import Delaunay
from shapely.geometry import Polygon

from tomato3d.light.geometry import triangle_areas_mm2
from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS
from tools.leaf_light.common import StudyError, digest, file_hash, number, output_dir, read_json, rows, write_json, write_rows
from tools.visible_leaf_patch import inside_mask

KEY = ('plant_id', 'session_id', 'geometry_variant_id', 'organ_id', 'leaflet_id', 'triangle_id')
AREA_BASIS_COLUMNS = (*KEY[:5], 'tissue_patch_id', 'data_kind', 'declared_area_basis_id',
                      'area_basis_id', 'downstream_supported_area_cm2', 'status', 'reasons')


def audit_area_evidence(context: dict | None, surface_rows: list[dict], records: list[dict],
                        support_views: dict, base: Path | None = None) -> dict:
    """Gate real area claims independently of diagnostic geometric support.

    A hash verifies evidence identity, not its scientific truth. No geometry,
    botanical face, exposure, covariance or missing observation is inferred.
    """
    context = context or {}
    if not isinstance(context, dict): raise StudyError('Area evidence must be an object')
    claims = context.get('patches', [])
    if not isinstance(claims, list): raise StudyError('Area patches must be a list')
    claim_map = {}
    patch_key = (*KEY[:5], 'tissue_patch_id')
    for claim in claims:
        if not isinstance(claim, dict): raise StudyError('Area patch claim must be an object')
        for group_name in ('identity', 'scale', 'pose', 'capture', 'area'):
            if claim.get(group_name) is not None and not isinstance(claim[group_name], dict):
                raise StudyError('Area evidence group must be an object: '+group_name)
        key = tuple(claim.get(k) for k in patch_key)
        if key in claim_map: raise StudyError('Duplicate area patch claim')
        claim_map[key] = claim
    groups = defaultdict(list)
    for record in records: groups[tuple(record.get(k) for k in patch_key)].append(record)
    if set(claim_map)-set(groups): raise StudyError('Area claim references absent patch identity')
    sources = context.get('sources', {})
    if not isinstance(sources, dict): raise StudyError('Area sources must be an object')
    verified, source_cache = {}, {}

    def source_ok(ref: Any) -> bool:
        if not isinstance(ref, str) or not ref.strip(): return False
        if ref in source_cache: return source_cache[ref]
        item = sources.get(ref)
        ok = False
        if isinstance(item, dict) and item.get('path') and re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', ''))):
            path = Path(item['path'])
            if not path.is_absolute():
                if base is None: return False
                path = base / path
            path = path.resolve()
            if path.is_file():
                actual = file_hash(path)
                if actual != item['sha256']: raise StudyError('Area evidence source hash mismatch: '+ref)
                verified[str(path)] = actual
                ok = True
        source_cache[ref] = ok
        return ok

    def finite(value: Any, lower: float, upper: float | None = None, positive: bool = False) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)): return False
        return bool(np.isfinite(value) and (value > lower if positive else value >= lower)
                    and (upper is None or value <= upper))

    def text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip()) and value not in ('unavailable', 'unknown')

    result = []
    used_basis = set()
    geometry_digest = digest(surface_rows)
    geometry_by_key = {tuple(r[k] for k in KEY): r for r in surface_rows}
    for key, faces in groups.items():
        claim = claim_map.get(key, {})
        why = []
        if context.get('schema') != 'p1-area-evidence-1': why.append('area_evidence_undeclared')
        kind = context.get('data_kind', 'unverified')
        if kind != 'observed': why.append('synthetic_not_real_area' if kind == 'synthetic' else 'real_observation_evidence_unavailable')
        if context.get('geometry_digest') != geometry_digest: why.append('area_geometry_binding_unavailable')
        if any(geometry_by_key[tuple(f[k] for k in KEY)].get('geometry_source') not in ('reconstructed', 'manual') for f in faces):
            why.append('physical_tissue_geometry_source_unavailable')
        identity = claim.get('identity') or {}
        partition_ref = context.get('partition_source_ref')
        partition_ok = source_ok(partition_ref)
        partition_hash = sources.get(partition_ref, {}).get('sha256') if isinstance(partition_ref, str) else None
        if (not partition_ok or identity.get('partition_sha256') != partition_hash or
                not text(identity.get('reviewer')) or not source_ok(identity.get('source_ref'))):
            why.append('partition_identity_review_unavailable')
        scale = claim.get('scale') or {}
        if (not finite(scale.get('square_size_mm'), 0, positive=True) or
                not finite(scale.get('calibration_residual_mm'), 0) or not source_ok(scale.get('source_ref'))):
            why.append('physical_scale_evidence_unavailable')
        pose = claim.get('pose') or {}
        views = support_views.get(key[-1], [])
        threshold = pose.get('max_reprojection_error_px')
        if (not source_ok(pose.get('source_ref')) or not finite(threshold, 0) or not views):
            why.append('pose_evidence_unavailable')
        else:
            for frame, _, _ in views:
                residual = frame.get('reprojection_error_px')
                if not finite(residual, 0): why.append('pose_evidence_unavailable')
                elif (residual > threshold or frame.get('pose_status') != 'solved' or
                      frame.get('passes_pose_gate') is not True): why.append('pose_evidence_rejected')
        capture = claim.get('capture') or {}
        try:
            at = datetime.fromisoformat(capture.get('captured_at', ''))
            aware = at.tzinfo is not None and at.utcoffset() is not None
        except (ValueError, TypeError): aware = False
        if (not aware or capture.get('capture_phase') not in ('early_photoperiod', 'late_photoperiod') or
                not source_ok(capture.get('source_ref')) or not source_ok(capture.get('schedule_source_ref'))):
            why.append('capture_time_phase_evidence_unavailable')
        area = claim.get('area') or {}
        if (area.get('quantity') != 'one_sided_physical_tissue' or
                not finite(area.get('coverage_fraction'), 0, 1, positive=True) or
                not text(area.get('occlusion_statement')) or not source_ok(area.get('source_ref'))):
            why.append('one_sided_area_evidence_unavailable')
        basis = claim.get('area_basis_id')
        if not text(basis): why.append('area_basis_id_undeclared')
        elif basis in used_basis: raise StudyError('Area basis must identify one explicit patch coverage')
        else: used_basis.add(basis)
        # Declared coverage must describe the entire submitted patch. A failing
        # face cannot silently alter that coverage while keeping its basis ID.
        if not all(f['eligible_supported_area'] for f in faces): why.append('patch_geometry_support_incomplete')
        reasons = sorted(set(why))
        result.append({**dict(zip(patch_key, key)), 'data_kind': kind,
                       'declared_area_basis_id': basis, 'area_basis_id': basis if not reasons else None,
                       'downstream_supported_area_cm2': sum(f['area_mm2'] for f in faces)/100 if not reasons else None,
                       'status': 'evidence_complete' if not reasons else 'unavailable', 'reasons': reasons})
    for path, expected in verified.items():
        if file_hash(Path(path)) != expected: raise StudyError('Area evidence changed during audit')
    return dict(schema='p1-area-evidence-audit-1', patches=result, source_hashes=verified,
                biological_face_status='unavailable', illuminated_faces=None,
                limitation='Evidence completeness only; no botanical face or illumination certification.')


def vertices(row: dict) -> np.ndarray:
    return np.array([[number(row[f'v{i}_{a}_mm'], f'v{i}_{a}_mm') for a in 'xyz'] for i in range(3)])


def local_patch_faces(points_mm: np.ndarray, boundary: list[int], holes: list[list[int]]) -> np.ndarray:
    """Triangulate one explicitly supplied local chart; discard faces across gaps.

    Call separately for folded/disconnected patches. Never infer boundaries or
    fill a hole. Boundary-crossing Delaunay faces are excluded, not clipped into
    invented observations; coverage can therefore be partial.
    """
    xyz = np.asarray(points_mm, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) < 3 or not np.isfinite(xyz).all():
        raise StudyError('Finite local patch points required')
    if np.linalg.matrix_rank(xyz - xyz.mean(axis=0)) < 2:
        raise StudyError('Collinear local patch')
    for ring in [boundary, *holes]:
        if len(ring) < 3 or len(set(ring)) != len(ring) or any(type(i) is not int or i < 0 or i >= len(xyz) for i in ring):
            raise StudyError('Invalid local patch ring')
    _, _, vt = np.linalg.svd(xyz - xyz.mean(axis=0))
    uv = (xyz - xyz.mean(axis=0)) @ vt[:2].T
    if len(np.unique(uv, axis=0)) != len(xyz):
        raise StudyError('Non-injective chart; split into smaller observed patches')
    region = Polygon(uv[boundary], [uv[h] for h in holes])
    if not region.is_valid or region.area <= 0:
        raise StudyError('Invalid boundary or holes')
    kept = [xyz[f] for f in Delaunay(uv).simplices if region.covers(Polygon(uv[f]))]
    return np.asarray(kept, dtype=float).reshape(-1, 3, 3)


def _plane_section(tri: np.ndarray, origin: np.ndarray, normal: np.ndarray, tol_mm: float) -> list[np.ndarray]:
    distances = (tri - origin) @ normal
    points = [v for v, d in zip(tri, distances) if abs(d) <= tol_mm]
    for i in range(3):
        j = (i + 1) % 3
        if distances[i] * distances[j] < 0:
            points.append(tri[i] + (tri[j] - tri[i]) * distances[i] / (distances[i] - distances[j]))
    return points


def intersecting_faces(a: np.ndarray, b: np.ndarray, tol_mm: float) -> bool:
    """Positive-area coplanar overlap or non-adjacent crossing, with explicit tolerance."""
    if np.any(a.max(axis=0) < b.min(axis=0) - tol_mm) or np.any(b.max(axis=0) < a.min(axis=0) - tol_mm):
        return False
    na, nb = np.cross(a[1]-a[0], a[2]-a[0]), np.cross(b[1]-b[0], b[2]-b[0])
    na /= np.linalg.norm(na); nb /= np.linalg.norm(nb)
    if np.all(np.abs((b-a[0]) @ na) <= tol_mm) and np.all(np.abs((a-b[0]) @ nb) <= tol_mm):
        axis = int(np.argmax(np.abs(na)))
        pa, pb = Polygon(np.delete(a, axis, axis=1)), Polygon(np.delete(b, axis, axis=1))
        return pa.intersection(pb).area / abs(na[axis]) > tol_mm ** 2
    cross = np.cross(na, nb)
    if np.linalg.norm(cross) <= np.finfo(float).eps:
        return False
    direction = cross / np.linalg.norm(cross)
    sa, sb = _plane_section(a, b[0], nb, tol_mm), _plane_section(b, a[0], na, tol_mm)
    if len(sa) < 2 or len(sb) < 2:
        return False
    ia, ib = np.array(sa) @ direction, np.array(sb) @ direction
    lo, hi = max(ia.min(), ib.min()), min(ia.max(), ib.max())
    if hi-lo <= tol_mm:
        return False
    common = [v for v in a if np.any(np.linalg.norm(b-v, axis=1) <= tol_mm)]
    if len(common) == 2:
        shared = np.array(common) @ direction
        if lo >= shared.min()-tol_mm and hi <= shared.max()+tol_mm:
            return False  # Legitimate adjacent folded triangles.
    return True


def audit_surface(surface_rows: list[dict], evidence: list[dict], policy: dict,
                  support_views: dict[str, list[tuple[dict, dict, np.ndarray]]] | None = None, *,
                  area_evidence: dict | None = None, evidence_base: Path | None = None) -> dict:
    """Return an audit; per-patch masks are already loaded/hashed by the CLI.

    The tissue_patch_id is an explicitly reviewed physical patch identity. All
    camera masks for it must refer to the same plant/session. Missing support is
    unavailable; no historical validation flag promotes it to measured tissue.
    """
    tol = number(policy.get('coordinate_tolerance_mm'), 'coordinate_tolerance_mm')
    min_area = number(policy.get('minimum_face_area_mm2'), 'minimum_face_area_mm2')
    minimum = policy.get('minimum_supported_views')
    limit = policy.get('maximum_pair_checks')
    if tol <= 0 or min_area < 0 or type(minimum) is not int or minimum < 2 or type(limit) is not int or limit < 1:
        raise StudyError('Explicit positive numerical policy and >=2 support views required')
    ev = {}
    for r in evidence:
        key = tuple(r[k] for k in KEY)
        if key in ev:
            raise StudyError('Duplicate face evidence')
        ev[key] = r
    seen, records, triangles = set(), [], []
    for r in surface_rows:
        key = tuple(r[k] for k in KEY)
        if key in seen:
            raise StudyError('Duplicate source face ID')
        seen.add(key)
        tri = vertices(r); area = float(triangle_areas_mm2(tri[None])[0]); why = []
        e = ev.get(key, {})
        if r.get('organ_class') != 'leaf': why.append('not_leaf_blade')
        if area <= min_area or area <= tol**2: why.append('degenerate_or_below_area_policy')
        patch = e.get('tissue_patch_id')
        if not patch or e.get('identity_status') != 'confirmed': why.append('unconfirmed_physical_patch')
        if e.get('support_kind') not in ('observed_supported', 'landmark_interpolated'):
            why.append('inferred_or_missing_support')
        if e.get('topology_review') != 'accepted' or not e.get('review_source'):
            why.append('topology_review_unavailable')
        views = (support_views or {}).get(patch, [])
        names = [frame['image_file'] for frame, _, _ in views]
        if len(names) != len(set(names)): raise StudyError('Duplicate support view')
        passed = sum(inside_mask(tri, frame, intr, mask) for frame, intr, mask in views)
        if len(views) < minimum: why.append('insufficient_visible_support')
        if passed < len(views): why.append('face_outside_visible_tissue')
        records.append({**dict(zip(KEY, key)), 'tissue_patch_id': patch, 'area_mm2': area,
                        'support_kind': e.get('support_kind'), 'supported_views': passed,
                        'reasons': why})
        triangles.append(tri)
    if set(ev)-seen: raise StudyError('Evidence references absent geometry')
    pairs, duplicates, intersections = 0, [], []
    truncated = False
    for i, a in enumerate(triangles):
        if records[i]['area_mm2'] <= max(min_area, tol**2): continue
        for j in range(i+1, len(triangles)):
            b = triangles[j]
            if records[j]['area_mm2'] <= max(min_area, tol**2): continue
            if tuple(records[i][k] for k in KEY[:3]) != tuple(records[j][k] for k in KEY[:3]):
                continue
            pairs += 1
            if pairs > limit:
                truncated = True; break
            distances = np.linalg.norm(a[:, None] - b[None, :], axis=2)
            if np.all(distances.min(axis=1) <= tol) and np.all(distances.min(axis=0) <= tol):
                duplicates.append([i, j])
                # Retain one only for the exact same reviewed tissue patch.
                if records[i]['tissue_patch_id'] and records[i]['tissue_patch_id'] == records[j]['tissue_patch_id']:
                    records[j]['reasons'].append('duplicate_physical_face')
                else:
                    for k in (i, j): records[k]['reasons'].append('ambiguous_coincident_tissue')
            elif intersecting_faces(a, b, tol):
                intersections.append([i, j])
                for k in (i, j): records[k]['reasons'].append('surface_intersection_requires_review')
        if truncated: break
    if truncated:
        for r in records: r['reasons'].append('intersection_audit_incomplete')
    for r in records:
        r['reasons'] = sorted(set(r['reasons'])); r['eligible_supported_area'] = not r['reasons']
    groups: dict[tuple, list] = defaultdict(list)
    for r in records: groups[tuple(r[k] for k in KEY[:4])].append(r)
    summary = []
    for group, rr in groups.items():
        kept = [r for r in rr if r['eligible_supported_area']]
        summary.append({**dict(zip(KEY[:4], group)), 'supported_area_cm2': sum(r['area_mm2'] for r in kept)/100 if kept else None,
                        'supported_faces': len(kept), 'input_faces': len(rr), 'total_area_cm2': None,
                        'geometry_status': 'supported_partial_interpolation' if kept else 'unavailable'})
    area_gate = audit_area_evidence(area_evidence, surface_rows, records, support_views or {}, evidence_base)
    patch_key = (*KEY[:5], 'tissue_patch_id')
    claims = {tuple(p[k] for k in patch_key): p for p in area_gate['patches']}
    for record in records:
        claim = claims[tuple(record[k] for k in patch_key)]
        record.update(eligible_real_area=claim['status'] == 'evidence_complete',
                      area_basis_id=claim['area_basis_id'], area_evidence_reasons=claim['reasons'])
    return dict(schema='compound-surface-audit-1', faces=records, compounds=summary, duplicate_pairs=duplicates,
                intersecting_pairs=intersections, audit_complete=not truncated, policy=policy,
                area_evidence=area_gate, diagnostic_support_is_real_area_acceptance=False,
                validated_metric=False, suitable_for_ppfd=False,
                limitation='Raster footprint checks at image resolution; partial supported area, not measured total tissue area.')


def audit_study(path: Path, out: Path) -> dict:
    study = read_json(path)
    if study.get('schema') != 'compound-surface-study-1': raise StudyError('Unknown surface study schema')
    base = path.resolve().parent
    sources = {str(path.resolve()): file_hash(path)}
    def source(name: str, expected: str) -> Path:
        p = (base/name).resolve()
        h = file_hash(p)
        if h != expected: raise StudyError('Source hash mismatch: '+str(p))
        sources[str(p)] = h
        return p
    geometry = source(study['geometry_csv'], study['geometry_sha256'])
    evidence_path = source(study['evidence_csv'], study['evidence_sha256'])
    geometry_rows = rows(geometry, LEAF_SURFACES_CSV_COLUMNS)
    face_evidence = rows(evidence_path, KEY)
    owners = defaultdict(set)
    for r in face_evidence: owners[r.get('tissue_patch_id')].add((r['plant_id'], r['session_id']))
    support = defaultdict(list)
    for v in study.get('visible_support', []):
        if v['visibility'] != 'visible': continue  # Occlusion does not contradict a surface.
        if not v.get('review_source'): raise StudyError('Visible masks require review provenance')
        capture_path = source(v['capture'], v['capture_sha256']); capture = read_json(capture_path)
        if owners[v['tissue_patch_id']] != {(capture['plant_id'], capture['session_id'])}:
            raise StudyError('Patch and camera identity mismatch')
        frames = [f for f in capture['frames'] if f['image_file'] == v['image_file']]
        if len(frames) != 1 or frames[0].get('pose_status') != 'solved': raise StudyError('Ineligible camera pose')
        mask_path = source(v['mask'], v['mask_sha256'])
        mask = cv2.imdecode(np.fromfile(mask_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        intr = capture['intrinsics']
        if mask is None or mask.shape != (intr['image_height_px'], intr['image_width_px']):
            raise StudyError('Mask must be in original calibrated pixel coordinates')
        support[v['tissue_patch_id']].append((frames[0], intr, mask != 0))
    area_evidence = None
    if study.get('area_evidence'):
        entry = study['area_evidence']
        area_path = source(entry['path'], entry['sha256'])
        area_evidence = read_json(area_path)
        if study.get('data_kind') == 'synthetic' or study.get('evidence_kind') == 'synthetic':
            area_evidence = {**area_evidence, 'data_kind': 'synthetic'}
    result = audit_surface(geometry_rows, face_evidence, study['policy'], dict(support),
                           area_evidence=area_evidence,
                           evidence_base=area_path.parent if area_evidence is not None else None)
    sources.update(result['area_evidence']['source_hashes'])
    result['source_hashes'] = sources
    result['code_hashes'] = {str(Path(__file__).resolve()): file_hash(Path(__file__))}
    for p, h in sources.items():
        if file_hash(Path(p)) != h: raise StudyError('Source changed during audit')
    folder = output_dir(out)
    write_json(folder/'audit.json', result)
    write_rows(folder/'compound_areas.csv', result['compounds'], (*KEY[:4], 'supported_area_cm2', 'supported_faces', 'input_faces', 'total_area_cm2', 'geometry_status'))
    kept = [r for r, a in zip(geometry_rows, result['faces']) if a['eligible_supported_area']]
    write_rows(folder/'supported_leaf_surfaces.csv', kept, LEAF_SURFACES_CSV_COLUMNS)
    eligible = [r for r, a in zip(geometry_rows, result['faces']) if a['eligible_real_area']]
    write_rows(folder/'downstream_leaf_surfaces.csv', eligible, LEAF_SURFACES_CSV_COLUMNS)
    area_rows = [{**p, 'reasons': '|'.join(p['reasons'])} for p in result['area_evidence']['patches']]
    write_rows(folder/'area_basis.csv', area_rows, AREA_BASIS_COLUMNS)
    # Review state stays pending: this file cannot bypass the existing GroIMP gates.
    write_json(folder/'surface_review.json', dict(geometry_sha256=file_hash(folder/'supported_leaf_surfaces.csv'),
               review_state='pending', geometry_completeness='partial', validated_metric=False, suitable_for_ppfd=False,
               diagnostic_support_only=True, area_evidence_audit='audit.json', area_basis_table='area_basis.csv'))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit_study(args.study, args.out)
    print({'status': 'audited', 'faces': len(result['faces']), 'validated_metric': False})


if __name__ == '__main__': main()
