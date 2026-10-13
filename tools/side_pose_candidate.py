"""Diagnostic side-camera pose from reconstructed leaflet landmarks (`leaflet_landmark_pnp`).

python -m tools.side_pose_candidate freeze --result build/.../result --out build/.../reference01
python -m tools.side_pose_candidate solve --reference build/.../reference01 --observations obs.json --out build/.../side01
python -m tools.side_pose_candidate readiness --result build/.../result --out build/.../readiness01

CONVENTIONS section 3.1 (ChArUco-only poses) remains the rule for the baseline. This module adds a
separately identified, opt-in diagnostic source for side views whose board pose is unavailable:
frozen reference XYZ from measured ChArUco views, manually confirmed side-image pixels, calibrated
3D->2D PnP. It never edits, averages or replaces a measured pose, never uses nominal angles, bbox
corners, contour indices or inferred midribs, and never takes scale from a bbox. A solved candidate
is internal consistency, not independent measurement of depth, scale or calibration.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

import cv2
import numpy as np

from tools.leaf_light.common import StudyError, digest, file_hash, output_dir, read_json, rows, write_json, write_rows

# The mathematical minimum for PnP is 4 points; these are the *experimental* requirements, which are
# deliberately stricter and are recorded with every candidate.
DEFAULT_POLICY = dict(min_fit_points=6, min_holdout_points=2, max_fit_error_px=2.0, max_holdout_error_px=2.0,
                      ransac_reprojection_px=4.0, ransac_iterations=5000, ransac_confidence=0.999,
                      min_extent_mm=5.0, min_planarity_ratio=0.02, min_collinearity_ratio=0.02, holdout_seed=20260920)
PNP_MINIMUM_POINTS = 4
CANDIDATE_SCHEMA = 'side-pose-candidate-1'
REFERENCE_SCHEMA = 'frozen-landmark-reference-1'
POSE_SOURCE = 'leaflet_landmark_pnp'


def _finite(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def freeze_reference(result: Path, out: Path) -> dict:
    """Snapshot triangulated landmarks and their provenance before any side solve."""
    result = result.resolve()
    capture = read_json(result / 'capture.json')
    depth_rows = rows(result / 'editor_point_depths.csv')
    points, skipped = [], []
    for row in depth_rows:
        xyz = [_finite(row.get(f'{axis}_board_mm')) for axis in 'xyz']
        key = (row.get('viewer_leaflet_id'), row.get('point_id'))
        if None in xyz:
            continue
        existing = next((p for p in points if (p['viewer_leaflet_id'], p['point_id']) == key), None)
        if existing is None:
            points.append(dict(viewer_leaflet_id=key[0], point_id=key[1], organ_id=row.get('organ_id'),
                               leaflet_id=row.get('leaflet_id'), xyz_board_mm=xyz, source_images=[row['image_file']],
                               point_semantic_name=row.get('point_semantic_name'),
                               depth_status=row.get('depth_status'), passes_point_gate=row.get('passes_point_gate'),
                               point_max_error_px=_finite(row.get('point_max_error_px')),
                               all_contributing_views_identity_confirmed=row.get('all_contributing_views_identity_confirmed')))
        elif existing['xyz_board_mm'] != xyz:
            skipped.append(dict(key=list(key), reason='conflicting coordinates for one identity'))
        elif row['image_file'] not in existing['source_images']:
            existing['source_images'].append(row['image_file'])
    frames = [dict(image_file=f['image_file'], pose_status=f['pose_status'], passes_pose_gate=f.get('passes_pose_gate'),
                   pose_source='charuco_board_pnp' if f['pose_status'] == 'solved' else None,
                   reprojection_error_px=f.get('reprojection_error_px')) for f in capture['frames']]
    folder = output_dir(out)
    reference = dict(schema_version=REFERENCE_SCHEMA,
                     reference_id='reference_' + digest(dict(points=points, capture=capture.get('session_id')))[:16],
                     created_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                     plant_id=capture.get('plant_id'), session_id=capture.get('session_id'),
                     source_result=str(result), depth_csv_sha256=file_hash(result / 'editor_point_depths.csv'),
                     capture_sha256=file_hash(result / 'capture.json'),
                     intrinsics=capture['intrinsics'], intrinsics_sha256=capture.get('intrinsics_sha256'),
                     board_variant_id=capture.get('board_variant_id'), quality=capture.get('quality'),
                     coordinate_frame=capture.get('coordinate_frame', 'board; millimetres'),
                     reference_points=points, reference_frames=frames, skipped=skipped,
                     reference_points_are_measurements=False, validated_metric=False, suitable_for_ppfd=False,
                     notice=('Frozen diagnostic landmarks triangulated from measured ChArUco views. Their own '
                             'uncertainty propagates into anything solved from them.'))
    write_json(folder / 'reference.json', reference)
    write_rows(folder / 'reference_points.csv', [dict(viewer_leaflet_id=p['viewer_leaflet_id'], point_id=p['point_id'],
               x_board_mm=p['xyz_board_mm'][0], y_board_mm=p['xyz_board_mm'][1], z_board_mm=p['xyz_board_mm'][2],
               source_images=';'.join(p['source_images']), passes_point_gate=p['passes_point_gate'],
               point_max_error_px=p['point_max_error_px']) for p in points],
               ('viewer_leaflet_id', 'point_id', 'x_board_mm', 'y_board_mm', 'z_board_mm', 'source_images',
                'passes_point_gate', 'point_max_error_px'))
    return reference


def partition(identities: list[tuple], policy: dict) -> tuple[list[tuple], list[tuple]]:
    """Deterministic fit/held-out split by physical point identity, recorded with its seed."""
    ordered = sorted(identities)
    generator = np.random.default_rng(policy['holdout_seed'])
    order = generator.permutation(len(ordered))
    holdout_size = min(policy['min_holdout_points'], max(0, len(ordered) - policy['min_fit_points']))
    held = {ordered[i] for i in order[:holdout_size]}
    return [i for i in ordered if i not in held], [i for i in ordered if i in held]


def geometry_checks(points_mm: np.ndarray, policy: dict) -> dict:
    """Coverage, planarity and collinearity of the fit points, before trusting any fit."""
    extent = points_mm.max(axis=0) - points_mm.min(axis=0)
    centred = points_mm - points_mm.mean(axis=0)
    singular = np.linalg.svd(centred, compute_uv=False) if len(points_mm) >= 3 else np.zeros(3)
    largest = float(singular[0]) if singular.size and singular[0] > 0 else 0.0
    planarity = float(singular[2] / singular[0]) if largest else 0.0
    collinearity = float(singular[1] / singular[0]) if largest else 0.0
    # Fatal: no spread at all, or points on one line - PnP is then unconstrained.
    # Not fatal but ambiguous: a near-planar set, which is normal for landmarks on one leaflet.
    # It gives a two-fold PnP ambiguity, so it is reported and forces validation before inclusion.
    reasons, warnings = [], []
    if float(np.linalg.norm(extent)) < policy['min_extent_mm']:
        reasons.append('insufficient_spatial_extent')
    if collinearity < policy['min_collinearity_ratio']:
        reasons.append('near_collinear_points')
    if planarity < policy['min_planarity_ratio']:
        warnings.append('near_planar_points_ambiguous_pnp')
    return dict(extent_mm=extent.tolist(), singular_values=[float(s) for s in np.atleast_1d(singular)],
                planarity_ratio=planarity, collinearity_ratio=collinearity,
                degeneracy_reasons=reasons, geometry_warnings=warnings)


def _residuals(points_mm: np.ndarray, pixels_px: np.ndarray, rvec, tvec, intrinsics: dict) -> np.ndarray:
    matrix = np.asarray(intrinsics['camera_matrix'], float)
    distortion = np.asarray(intrinsics['dist_coeffs'], float)
    projected = cv2.projectPoints(points_mm, rvec, tvec, matrix, distortion)[0].reshape(-1, 2)
    return np.linalg.norm(projected - pixels_px, axis=1)


def solve_side_pose(reference: dict, image_file: str, observations: list[dict], policy: dict | None = None,
                    diagnostic_override: bool = False) -> dict:
    """One side image: reference XYZ + confirmed pixels -> an explicitly diagnostic pose candidate."""
    policy = dict(DEFAULT_POLICY, **(policy or {}))
    intrinsics = reference['intrinsics']
    lookup = {(p['viewer_leaflet_id'], p['point_id']): p for p in reference['reference_points']}
    matched, unmatched = [], []
    seen = set()
    for entry in observations:
        key = (entry.get('viewer_leaflet_id'), entry.get('point_id'))
        pixel = [_finite(entry.get('x_px')), _finite(entry.get('y_px'))]
        if key in seen:
            raise StudyError(f'Duplicate observation for {key} in one image')
        seen.add(key)
        if key not in lookup or None in pixel:
            unmatched.append(dict(key=list(key), reason='no frozen reference point' if key not in lookup
                                  else 'non-finite pixel'))
            continue
        if not (0 <= pixel[0] < intrinsics['image_width_px'] and 0 <= pixel[1] < intrinsics['image_height_px']):
            unmatched.append(dict(key=list(key), reason='pixel outside the calibrated image'))
            continue
        matched.append((key, lookup[key]['xyz_board_mm'], pixel))
    candidate = dict(schema_version=CANDIDATE_SCHEMA,
                     candidate_id='side_' + digest(dict(image=image_file, keys=[list(k) for k, _, _ in matched],
                                                        reference=reference['reference_id']))[:16],
                     version=1, pose_source=POSE_SOURCE, plant_id=reference.get('plant_id'),
                     session_id=reference.get('session_id'), image_file=image_file,
                     reference_id=reference['reference_id'], reference_depth_csv_sha256=reference['depth_csv_sha256'],
                     reference_capture_sha256=reference['capture_sha256'],
                     intrinsics_sha256=reference.get('intrinsics_sha256'),
                     observations_sha256=digest(sorted([list(k) + p for k, _, p in matched])),
                     coordinate_frame=reference.get('coordinate_frame'), units='millimetres',
                     convention='world_to_camera rvec/tvec as cv2.solvePnP returns them',
                     algorithm='cv2.solvePnPRansac(SOLVEPNP_SQPNP) then cv2.solvePnPRefineLM on inliers only',
                     policy=policy, matched_point_count=len(matched), unmatched=unmatched,
                     created_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                     rvec_rad=None, tvec_mm=None, calculation_status='not_attempted',
                     quality_status='unavailable', validation='unavailable', diagnostic_inclusion='excluded',
                     inclusion_reason=None, freshness='current', alternative_solutions=[],
                     fit_point_ids=[], holdout_point_ids=[], inlier_point_ids=[], outlier_point_ids=[],
                     fit_rms_px=None, fit_max_px=None, holdout_rms_px=None, holdout_max_px=None,
                     geometry=None, pose_source_is_measured_board=False,
                     validated_metric=False, suitable_for_ppfd=False,
                     notice=('Diagnostic camera pose inferred from reconstructed landmarks. It is not a ChArUco '
                             'measurement, inherits the reference points uncertainty, and is excluded from the '
                             'baseline. Board marker detections are never attributed to this camera.'))
    if len(matched) < max(PNP_MINIMUM_POINTS, policy['min_fit_points']):
        candidate.update(calculation_status='insufficient_points',
                         inclusion_reason=f'{len(matched)} usable correspondences; '
                                          f'{max(PNP_MINIMUM_POINTS, policy["min_fit_points"])} required to fit')
        return candidate
    fit_keys, hold_keys = partition([k for k, _, _ in matched], policy)
    by_key = {k: (np.asarray(xyz, float), np.asarray(px, float)) for k, xyz, px in matched}
    fit_points = np.array([by_key[k][0] for k in fit_keys])
    fit_pixels = np.array([by_key[k][1] for k in fit_keys])
    candidate.update(fit_point_ids=[list(k) for k in fit_keys], holdout_point_ids=[list(k) for k in hold_keys])
    geometry = geometry_checks(fit_points, policy)
    candidate['geometry'] = geometry
    if geometry['degeneracy_reasons']:
        candidate.update(calculation_status='degenerate_point_distribution',
                         inclusion_reason=';'.join(geometry['degeneracy_reasons']))
        return candidate
    matrix = np.asarray(intrinsics['camera_matrix'], float)
    distortion = np.asarray(intrinsics['dist_coeffs'], float)
    try:
        solved, rvec, tvec, inliers = cv2.solvePnPRansac(
            fit_points, fit_pixels, matrix, distortion, flags=cv2.SOLVEPNP_SQPNP,
            reprojectionError=float(policy['ransac_reprojection_px']), iterationsCount=int(policy['ransac_iterations']),
            confidence=float(policy['ransac_confidence']))
    except cv2.error as exc:
        candidate.update(calculation_status='solver_error', inclusion_reason=str(exc))
        return candidate
    if not solved or inliers is None or len(inliers) < PNP_MINIMUM_POINTS:
        candidate.update(calculation_status='no_solution',
                         inclusion_reason='RANSAC found no consistent pose with enough inliers')
        return candidate
    inlier_index = sorted(int(i) for i in np.asarray(inliers).reshape(-1))
    # Refinement uses inliers of the FIT set only; held-out points never influence the pose.
    rvec, tvec = cv2.solvePnPRefineLM(fit_points[inlier_index], fit_pixels[inlier_index], matrix, distortion, rvec, tvec)
    rotation = cv2.Rodrigues(rvec)[0]
    if np.any((fit_points @ rotation.T + tvec.reshape(3))[:, 2] <= 0):
        candidate.update(calculation_status='points_behind_camera',
                         inclusion_reason='the solved camera places reference points behind itself')
        return candidate
    fit_residuals = _residuals(fit_points[inlier_index], fit_pixels[inlier_index], rvec, tvec, intrinsics)
    candidate.update(calculation_status='solved', rvec_rad=rvec.reshape(3).tolist(), tvec_mm=tvec.reshape(3).tolist(),
                     inlier_point_ids=[list(fit_keys[i]) for i in inlier_index],
                     outlier_point_ids=[list(k) for i, k in enumerate(fit_keys) if i not in inlier_index],
                     fit_rms_px=float(np.sqrt(np.mean(fit_residuals ** 2))), fit_max_px=float(fit_residuals.max()))
    try:
        count, rvecs, tvecs, errors = cv2.solvePnPGeneric(fit_points[inlier_index], fit_pixels[inlier_index],
                                                          matrix, distortion, flags=cv2.SOLVEPNP_SQPNP)
        candidate['alternative_solutions'] = [dict(rvec_rad=np.asarray(r).reshape(3).tolist(),
                                                   tvec_mm=np.asarray(t).reshape(3).tolist())
                                              for r, t in list(zip(rvecs, tvecs))[1:]]
    except cv2.error:
        candidate['alternative_solutions'] = []
    if hold_keys:
        hold_points = np.array([by_key[k][0] for k in hold_keys])
        hold_pixels = np.array([by_key[k][1] for k in hold_keys])
        held = _residuals(hold_points, hold_pixels, rvec, tvec, intrinsics)
        candidate.update(validation='available', holdout_rms_px=float(np.sqrt(np.mean(held ** 2))),
                         holdout_max_px=float(held.max()))
    else:
        candidate.update(validation='unavailable',
                         inclusion_reason=f'fewer than {policy["min_holdout_points"]} points could be held out')
    fit_gate, hold_gate = policy['max_fit_error_px'], policy['max_holdout_error_px']
    checks = {'fit_error': None if fit_gate is None else candidate['fit_rms_px'] <= fit_gate,
              'holdout_error': None if hold_gate is None or candidate['holdout_rms_px'] is None
              else candidate['holdout_rms_px'] <= hold_gate}
    candidate['policy_checks'] = checks
    candidate['quality_status'] = ('unavailable' if None in checks.values() else
                                   'meets_diagnostic_policy' if all(checks.values()) else 'fails_diagnostic_policy')
    candidate['geometry_warnings'] = geometry['geometry_warnings']
    if candidate['validation'] == 'available' and candidate['quality_status'] == 'meets_diagnostic_policy':
        candidate.update(diagnostic_inclusion='eligible', inclusion_reason='meets the recorded diagnostic policy')
    elif diagnostic_override:
        candidate.update(diagnostic_inclusion='included_by_explicit_override',
                         inclusion_reason='user override; quality/validation did not qualify it automatically')
    else:
        candidate.setdefault('inclusion_reason', 'did not meet the diagnostic policy')
        candidate['diagnostic_inclusion'] = 'excluded'
    return candidate


def readiness(result: Path, reference: dict | None = None) -> dict:
    """What is still missing before any side image can be solved."""
    result = result.resolve()
    capture = read_json(result / 'capture.json')
    depth_rows = rows(result / 'editor_point_depths.csv') if (result / 'editor_point_depths.csv').exists() else []
    posed = {f['image_file'] for f in capture['frames'] if f['pose_status'] == 'solved'}
    unposed = [f['image_file'] for f in capture['frames'] if f['pose_status'] != 'solved']
    per_leaflet = defaultdict(lambda: dict(points_with_xyz=set(), observed_in_unposed=set()))
    for row in depth_rows:
        entry = per_leaflet[row.get('viewer_leaflet_id')]
        if _finite(row.get('z_board_mm')) is not None:
            entry['points_with_xyz'].add(row.get('point_id'))
        if row['image_file'] not in posed:
            entry['observed_in_unposed'].add(row['image_file'])
    policy = DEFAULT_POLICY
    need = max(PNP_MINIMUM_POINTS, policy['min_fit_points']) + policy['min_holdout_points']
    leaflets = [dict(viewer_leaflet_id=key, reference_points=len(value['points_with_xyz']),
                     observed_in_unposed_images=sorted(value['observed_in_unposed']))
                for key, value in sorted(per_leaflet.items())]
    available = sum(item['reference_points'] for item in leaflets)
    return dict(schema_version='side-pose-readiness-1', plant_id=capture.get('plant_id'),
                session_id=capture.get('session_id'), source_result=str(result),
                posed_images=sorted(posed), unposed_images=sorted(unposed),
                reference_points_available=available, reference_points_needed_per_side_image=need,
                leaflets=leaflets,
                blocking=('no triangulated reference points exist yet; label leaflets and mark the same physical '
                          'points in at least two posed images first' if available == 0 else
                          f'{available} reference points exist; {need} confirmed observations of them are needed in '
                          'one side image' if available < need else
                          'enough reference points exist; confirm their pixels in a side image to solve it'),
                required_next_actions=[
                    'Label leaflets in the posed images ' + ', '.join(sorted(posed)),
                    'Mark the same physical point IDs (tip, visible attachment, distinctive lobe apex, vein junction) '
                    'in at least two posed images per point',
                    'Rebuild to triangulate them, then freeze a reference snapshot',
                    f'Mark at least {need} of those exact point IDs in one side image, then solve that side pose'],
                validated_metric=False)


def write_candidate(folder: Path, candidate: dict) -> None:
    write_json(folder / f'{candidate["candidate_id"]}.json', candidate)
    write_rows(folder / f'{candidate["candidate_id"]}_points.csv',
               [dict(role=role, viewer_leaflet_id=key[0], point_id=key[1])
                for role, keys in (('fit_inlier', candidate['inlier_point_ids']),
                                   ('fit_outlier', candidate['outlier_point_ids']),
                                   ('holdout', candidate['holdout_point_ids'])) for key in keys],
               ('role', 'viewer_leaflet_id', 'point_id'))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze = sub.add_parser('freeze', help='Freeze reference landmarks from a rebuild result')
    freeze.add_argument('--result', type=Path, required=True)
    freeze.add_argument('--out', type=Path, required=True)
    solve = sub.add_parser('solve', help='Solve one side image from confirmed observations')
    solve.add_argument('--reference', type=Path, required=True, help='Frozen reference directory or reference.json')
    solve.add_argument('--observations', type=Path, required=True,
                       help='JSON: {"image_file": ..., "observations": [{viewer_leaflet_id, point_id, x_px, y_px}]}')
    solve.add_argument('--out', type=Path, required=True)
    solve.add_argument('--policy', type=Path, help='JSON overriding the recorded acceptance policy')
    solve.add_argument('--diagnostic-override', action='store_true',
                       help='Include a candidate that did not qualify automatically; recorded as an override')
    ready = sub.add_parser('readiness', help='Report what is missing before a side solve')
    ready.add_argument('--result', type=Path, required=True)
    ready.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.command == 'freeze':
        reference = freeze_reference(args.result, args.out)
        print(json.dumps(dict(reference_id=reference['reference_id'], points=len(reference['reference_points']))))
    elif args.command == 'solve':
        path = args.reference if args.reference.is_file() else args.reference / 'reference.json'
        reference = read_json(path)
        request = read_json(args.observations)
        candidate = solve_side_pose(reference, request['image_file'], request['observations'],
                                    read_json(args.policy) if args.policy else None, args.diagnostic_override)
        folder = output_dir(args.out)
        write_candidate(folder, candidate)
        print(json.dumps({k: candidate[k] for k in ('candidate_id', 'calculation_status', 'quality_status',
                                                    'validation', 'diagnostic_inclusion', 'fit_rms_px',
                                                    'holdout_rms_px')}))
    else:
        report = readiness(args.result)
        if args.out:
            write_json(output_dir(args.out) / 'readiness.json', report)
        print(json.dumps({k: report[k] for k in ('plant_id', 'reference_points_available',
                                                 'reference_points_needed_per_side_image', 'blocking')},
                         ensure_ascii=False))


if __name__ == '__main__':
    main()
