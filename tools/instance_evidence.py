"""Numerical helpers for diagnostic instance evidence, never measured leaf surfaces."""
from __future__ import annotations

from collections import defaultdict

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from tools.leaf_light.common import StudyError
from tools.leaf_light.common import digest
from tools.leaf_light.reconstruction import project
from tools.leaflet_extent import feasible_extent, ExtentStatus


def mask_metrics(predicted: list[np.ndarray], reference: list[np.ndarray], settings: dict,
                 ignore: np.ndarray | None = None) -> dict:
    """One-to-one matching; unmatched GT contributes zero to all-reference mean IoU/Dice."""
    shapes = {m.shape for m in predicted + reference}
    if len(shapes) > 1 or any(m.ndim != 2 for m in predicted + reference):
        raise StudyError('Mask dimensions differ')
    if ignore is not None and shapes and ignore.shape != next(iter(shapes)):
        raise StudyError('Ignore region dimensions differ')
    valid = ~ignore if ignore is not None else True
    p = [np.asarray(m, bool) & valid for m in predicted]
    g = [np.asarray(m, bool) & valid for m in reference]
    # Empty predictions are missing proposals, not extra false-positive instances.
    empty = sum(not m.any() for m in p)
    nonempty_indices = [i for i, m in enumerate(p) if m.any()]
    p = [p[i] for i in nonempty_indices]
    if any(not m.any() for m in g):
        raise StudyError('Reference instance has no evaluable visible pixels')
    intersection = np.array([[np.count_nonzero(a & b) for b in g] for a in p], dtype=float).reshape(len(p), len(g))
    pa = np.array([m.sum() for m in p], float)
    ga = np.array([m.sum() for m in g], float)
    union = pa[:, None] + ga[None, :] - intersection
    iou = np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)
    dice = np.divide(2 * intersection, pa[:, None] + ga[None, :], out=np.zeros_like(intersection),
                     where=(pa[:, None] + ga[None, :]) > 0)
    # Maximize valid match count before aggregate IoU; do not lose valid matches to sub-threshold pairs.
    eligible = iou >= settings['instance_iou_min']
    score = eligible * (min(len(p), len(g)) + 1) + iou
    pi, gi = linear_sum_assignment(-score)
    matched = [(int(a), int(b)) for a, b in zip(pi, gi) if eligible[a, b]]
    tp = len(matched)
    significant = intersection >= ga[None, :] * settings['merge_split_reference_fraction']
    return dict(predicted_instances=len(p), reference_instances=len(g), empty_predictions=empty,
                tp=tp, fp=len(p)-tp, fn=len(g)-tp,
                precision=tp/len(p) if p else None, recall=tp/len(g) if g else None,
                mean_iou_all_reference=float(sum(iou[a, b] for a, b in zip(pi, gi))/len(g)) if g else None,
                mean_dice_all_reference=float(sum(dice[a, b] for a, b in zip(pi, gi))/len(g)) if g else None,
                merged_instance_count=int((significant.sum(axis=1) >= 2).sum()),
                split_instance_count=int((significant.sum(axis=0) >= 2).sum()),
                merge_prediction_indices=[nonempty_indices[i] for i in np.flatnonzero(significant.sum(axis=1) >= 2)],
                split_reference_indices=[int(i) for i in np.flatnonzero(significant.sum(axis=0) >= 2)],
                matches=[dict(prediction_index=nonempty_indices[a], reference_index=b, iou=float(iou[a, b]),
                              dice=float(dice[a, b])) for a, b in matched],
                segmentation_matches=[dict(prediction_index=nonempty_indices[a], reference_index=int(b),
                    detected=bool(eligible[a,b]), iou=float(iou[a,b]), dice=float(dice[a,b])) for a,b in zip(pi,gi)])


def frame_eligible(frame: dict | None, mode: str) -> tuple[bool, str | None]:
    if frame is None or frame.get('pose_status') != 'solved' or frame.get('rvec_rad') is None or frame.get('tvec_mm') is None:
        return False, 'missing_measured_pose'
    if frame.get('pose_source', 'charuco_pnp') not in ('charuco_pnp', 'charuco', 'measured_charuco'):
        return False, 'non_charuco_pose_excluded'
    if not np.isfinite(np.r_[frame['rvec_rad'], frame['tvec_mm']]).all():
        return False, 'nonfinite_pose'
    if mode == 'strict' and frame.get('passes_pose_gate') is not True:
        return False, 'pose_quality_gate_failed'
    return True, None


def voxel_chunks(low_mm: list, high_mm: list, spacing_mm: float, chunk_size: int,
                 maximum: int):
    """Board-anchored centres; independent regions share identical voxel IDs."""
    low = np.ceil(np.asarray(low_mm)/spacing_mm - .5).astype(np.int64)
    high = np.floor(np.asarray(high_mm)/spacing_mm - .5).astype(np.int64)
    counts = high-low+1
    count = int(np.prod(counts, dtype=object)) if np.all(counts > 0) else 0
    if count > maximum:
        raise StudyError(f'voxel_resource_limit: {count} > {maximum}; grid was not coarsened')
    for start in range(0, count, chunk_size):
        indices = np.arange(start, min(count, start+chunk_size))
        ijk = np.column_stack(np.unravel_index(indices, tuple(counts))) + low
        yield ijk, (ijk+.5)*spacing_mm


def observation_votes(points_mm: np.ndarray, observation: dict, mask: np.ndarray,
                      frame: dict, intrinsics: dict, tolerance_px: float) -> np.ndarray:
    """+1 support, -1 full-visible contradiction, 0 unknown/occluded/outside image."""
    pixels = project(points_mm, frame, intrinsics)
    rotation = cv2.Rodrigues(np.asarray(frame['rvec_rad'], float))[0]
    camera = points_mm @ rotation.T + np.asarray(frame['tvec_mm'])
    finite = np.isfinite(pixels).all(axis=1)
    indices = np.zeros_like(pixels, dtype=int)
    indices[finite] = np.floor(pixels[finite]+.5).astype(int)
    width, height = observation['image_size_px']
    valid = finite & (camera[:, 2] > 0) & (indices[:, 0] >= 0) & (indices[:, 0] < width) & (indices[:, 1] >= 0) & (indices[:, 1] < height)
    crop = observation['crop_px']; xy = indices - np.asarray(crop[:2])
    in_crop = valid & (xy[:, 0] >= 0) & (xy[:, 0] < mask.shape[1]) & (xy[:, 1] >= 0) & (xy[:, 1] < mask.shape[0])
    result = np.zeros(len(points_mm), np.int8)
    hit = np.zeros(len(points_mm), bool)
    hit[in_crop] = mask[xy[in_crop, 1], xy[in_crop, 0]]
    result[hit] = 1
    if observation['visibility'] == 'full':
        # Outside a full observed silhouette is contradiction; a disclosed pixel band is unknown.
        distance = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        band = np.zeros(len(points_mm), bool)
        band[in_crop] = distance[xy[in_crop, 1], xy[in_crop, 0]] <= tolerance_px
        result[valid & ~hit & ~band] = -1
    return result


def fuse(capture: dict, observations: list[dict], masks: dict[str, np.ndarray], settings: dict,
         mode: str = 'strict') -> dict:
    if mode not in ('strict', 'diagnostic'):
        raise StudyError('Unknown fusion mode')
    frames = {f['image_file']: f for f in capture['frames']}
    groups, exclusions = defaultdict(list), []
    observed = {}
    for obs in observations:
        identity = (obs['image_file'], str(obs.get('source_annotation_id', obs['id'])))
        value = {k: v for k, v in obs.items() if k != 'routes'}
        if identity in observed:
            if observed[identity] != digest(value):
                raise StudyError('Conflicting duplicate observation; resolve routes first')
            continue
        observed[identity] = digest(value)
        reason = None
        if obs.get('review') != 'accepted': reason = 'mask_not_accepted'
        elif not obs.get('leaf_key') or obs.get('identity_review') != 'confirmed': reason = 'identity_not_confirmed'
        elif obs.get('visibility') not in ('full', 'partial'): reason = 'visibility_unknown'
        elif obs['id'] not in masks: reason = 'mask_unavailable'
        else:
            _, reason = frame_eligible(frames.get(obs['image_file']), mode)
        if reason:
            exclusions.append(dict(observation_id=obs['id'], reason=reason)); continue
        groups[obs['leaf_key']].append(obs)
    rows, extents = [], []
    quality = capture.get('quality', {})
    tolerance = quality.get('contour_tolerance_px')
    min_angle = quality.get('min_ray_angle_deg')
    if tolerance is None or min_angle is None:
        return dict(status='unavailable_quality_configuration', voxels=[], extents=[], exclusions=exclusions,
                    mode=mode, validated_metric=False, suitable_for_ppfd=False)
    for key, group in sorted(groups.items()):
        # Multiple observations claiming the same physical leaf in one photo need review, not extra votes.
        by_view = defaultdict(list)
        for obs in group: by_view[obs['image_file']].append(obs)
        unique = []
        for view, entries in by_view.items():
            if len(entries) > 1:
                exclusions.extend(dict(observation_id=o['id'], reason='duplicate_identity_in_view') for o in entries)
            else: unique.extend(entries)
        boxes = []
        for obs in unique:
            if obs['visibility'] == 'full':
                x, y, width, height = obs['source_bbox_xywh_px']
                boxes.append((frames[obs['image_file']], dict(x_min_px=x, y_min_px=y, x_max_px=x+width, y_max_px=y+height)))
        extent = feasible_extent(boxes, capture['intrinsics'])
        extents.append(dict(leaf_key=key, **extent))
        if extent['status'] != ExtentStatus.OK: continue
        centers = []
        for obs in unique:
            f = frames[obs['image_file']]
            rotation = cv2.Rodrigues(np.asarray(f['rvec_rad'], float))[0]
            centers.append(-rotation.T @ np.asarray(f['tvec_mm']))
        a, b = np.asarray(extent['halfspaces']['a']), np.asarray(extent['halfspaces']['b'])
        for ijk, xyz in voxel_chunks(extent['cuboid_min_mm'], extent['cuboid_max_mm'], settings['voxel_spacing_mm'],
                                     settings['chunk_size'], settings['max_candidate_voxels'] - len(rows)):
            votes = np.column_stack([observation_votes(xyz, o, masks[o['id']], frames[o['image_file']],
                                                       capture['intrinsics'], tolerance) for o in unique])
            inside = np.all(xyz @ a.T <= b + 1e-6, axis=1)
            for n, point in enumerate(xyz):
                support = np.flatnonzero(votes[n] == 1)
                contradiction = np.flatnonzero(votes[n] == -1)
                reason = None
                if not inside[n]: reason = 'outside_feasible_polytope'
                elif len(support) < settings['minimum_support_views']: reason = 'fewer_than_two_supporting_views'
                elif len(contradiction): reason = 'full_visibility_contradiction'
                else:
                    rays = point - np.asarray(centers)[support]
                    lengths = np.linalg.norm(rays, axis=1)
                    if np.any(lengths <= 1e-9): reason = 'at_camera'
                    else:
                        rays /= lengths[:, None]
                        angle = np.degrees(np.arccos(np.clip(np.abs(rays @ rays.T), 0, 1))).max()
                        if angle < min_angle: reason = 'insufficient_parallax'
                rows.append(dict(voxel_id=','.join(map(str, ijk[n])), leaf_key=key,
                    x_mm=float(point[0]), y_mm=float(point[1]), z_mm=float(point[2]),
                    support_ids=[unique[i]['id'] for i in support],
                    contradiction_ids=[unique[i]['id'] for i in contradiction],
                    unknown_ids=[unique[i]['id'] for i in np.flatnonzero(votes[n] == 0)],
                    support_views=len(support), state='supported' if reason is None else 'excluded',
                    exclusion_reason=reason, ambiguous=False))
    claims = defaultdict(set)
    for row in rows:
        if row['state'] == 'supported': claims[row['voxel_id']].add(row['leaf_key'])
    for row in rows:
        row['ambiguous'] = row['state'] == 'supported' and len(claims[row['voxel_id']]) > 1
    qualified = {o['image_file'] for o in observations if frame_eligible(frames.get(o['image_file']), mode)[0]}
    status = 'complete' if rows else 'unavailable_no_bounded_reviewed_instances'
    if not qualified: status = 'unavailable_no_qualified_poses'
    return dict(status=status, mode=mode, qualified_pose_count=len(qualified),
                voxels=rows, extents=extents, exclusions=exclusions, validated_metric=False, suitable_for_ppfd=False)

