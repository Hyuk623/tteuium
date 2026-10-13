"""Diagnostic camera poses for photos the ChArUco board could not pose, from a sparse feature map.

    python -X utf8 -m tools.feature_pose_candidate --session build/new_captures_20260920/dwt_01/edit_session \\
        --out build/feature_pose_<date>/dwt_01 [--self-check]

The photos that do have a measured ChArUco pose are matched to each other with classical SIFT features; every
mutual match is triangulated with those fixed poses into a sparse 3D map in the board frame (millimetres). A photo
without a pose is then located against that map with RANSAC PnP, keeping held-out map points aside to measure the
result. The user stated (2026-09-23) that the plants stand in a controlled setting and do not move between photos,
so plant texture as well as the rigid background may be matched; a moving plant would break this.

Limits, enforced here:

* a measured ChArUco pose is never re-estimated, replaced or averaged; it only ever supplies map geometry;
* no bundle adjustment and no scale of its own: the board's scale is inherited through the posed photos;
* every result is a candidate, `validated_metric=false`, `suitable_for_ppfd=false`, and carries its own pose source
  so it can never be mistaken for a measured pose;
* `--self-check` re-solves each posed photo from a map built without it and reports the error against its measured
  pose. That measured error, not the fit residual, says whether these candidates are worth anything.
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json, write_rows
from tools.side_pose_candidate import DEFAULT_POLICY, PNP_MINIMUM_POINTS, _residuals, geometry_checks, partition

SCHEMA = 'feature-pose-candidate-1'
MAP_SCHEMA = 'feature-map-1'
POSE_SOURCE = 'feature_map_pnp_diagnostic'
#: Feature matching always leaves some wrong matches, so the held-out set is judged by the share of points that
#: agree with the pose, not by their median error (a landmark clicked by a person has no such outliers).
#: Calibrated on the photos whose measured pose is known (dwt_02, 2026-09-23): a correct solution there keeps
#: only 6-20 % of its held-out matches within 4 px, because most SIFT matches are wrong whatever the pose. The
#: bar is therefore set just under the weakest correct case, and two further checks carry the decision: enough
#: RANSAC inliers, and agreement with the direction the photo was taken from.
FEATURE_POLICY = dict(max_fit_error_px=4.0, min_holdout_points=20, min_holdout_inlier_fraction=0.05,
                      holdout_inlier_px=4.0, min_inliers=8)
#: SIFT features kept per photo (strongest first); per simulated view when simulating.
MAX_FEATURES = 20000
MAX_FEATURES_PER_SIMULATION = 3000
#: Lowe ratio for a match to count, in both directions.
RATIO = 0.8
#: A triangulated point must reproject within this many pixels in both photos and lie in front of both cameras.
#: The reference poses themselves are 3-9 px off (they fail the 1 px gate), so a tighter gate would throw away
#: correct matches and keep only points that happen to agree with the pose error.
MAX_TRIANGULATION_ERROR_PX = 8.0
#: Rays closer to parallel than this give an ill-conditioned depth.
MIN_RAY_ANGLE_DEG = 3.0
#: Affine simulation (ASIFT-style) for the large tilt between the side ring and the oblique ring.
#: Tilts t are simulated by blurring and subsampling one axis; each tilt is repeated at rotations of 72/t degrees.
AFFINE_TILTS = (1.0, 1.4142135623730951, 2.0)
#: Simulated images are matched at this longest side (pixels); keypoints are scaled back to original pixels.
AFFINE_WORK_PX = 1600
#: Map points must sit inside this box around the posed photos' view (mm), which rejects sky/floor matches.
MAP_BOUNDS_MM = ((-600.0, 900.0), (-700.0, 600.0), (-200.0, 600.0))


def load_grey(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert('L'))


def features(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sift = cv2.SIFT_create(nfeatures=MAX_FEATURES)
    kp, desc = sift.detectAndCompute(image, None)
    if desc is None:
        return np.zeros((0, 2)), np.zeros((0, 128), np.float32)
    return np.array([k.pt for k in kp], float), desc.astype(np.float32)


def mutual_matches(a: np.ndarray, b: np.ndarray) -> list[tuple[int, int]]:
    """Ratio test in both directions; only matches that agree both ways are kept."""
    if not len(a) or not len(b):
        return []
    # approximate nearest neighbours: exact search over 20k x 20k descriptors is far too slow here
    matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=64))
    forward = {m.queryIdx: m.trainIdx for m, n in matcher.knnMatch(a, b, k=2) if m.distance < RATIO * n.distance}
    backward = {m.queryIdx: m.trainIdx for m, n in matcher.knnMatch(b, a, k=2) if m.distance < RATIO * n.distance}
    return [(i, j) for i, j in forward.items() if backward.get(j) == i]


def affine_features(image: np.ndarray, tilts=AFFINE_TILTS, work_px: int = AFFINE_WORK_PX):
    """SIFT over simulated viewpoints: the same surface seen from a very different direction still matches.

    Plain SIFT tolerates roughly 30 degrees of viewpoint change; the side ring is about 50 degrees from the
    oblique ring, which is why plain matching finds almost nothing there. Each simulated view is a tilt
    (anisotropic blur and subsampling) at several in-plane rotations, as in the ASIFT method; keypoints are
    carried back to original pixel coordinates by the inverse of the simulating transform.
    """
    scale = min(1.0, work_px / max(image.shape[:2]))
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else image
    sift = cv2.SIFT_create(nfeatures=MAX_FEATURES_PER_SIMULATION)
    points, descriptors = [], []
    for tilt in tilts:
        phis = [0.0] if tilt == 1.0 else list(np.arange(0.0, 180.0, 72.0 / tilt))
        for phi in phis:
            warped, inverse = simulate(small, tilt, phi)
            kp, desc = sift.detectAndCompute(warped, None)
            if desc is None:
                continue
            xy = np.array([k.pt for k in kp], float)
            back = (np.hstack([xy, np.ones((len(xy), 1))]) @ inverse.T) / scale
            points.append(back)
            descriptors.append(desc.astype(np.float32))
    if not points:
        return np.zeros((0, 2)), np.zeros((0, 128), np.float32)
    return np.vstack(points), np.vstack(descriptors)


def simulate(image: np.ndarray, tilt: float, phi_deg: float):
    """One simulated view and the 2x3 transform that maps its pixels back to the input image."""
    h, w = image.shape[:2]
    out, A = image, np.array([[1.0, 0, 0], [0, 1.0, 0]])
    if phi_deg:
        R = cv2.getRotationMatrix2D((0, 0), phi_deg, 1.0)
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
        turned = corners @ R[:, :2].T
        R[:, 2] = -turned.min(axis=0)
        size = np.ceil(turned.max(axis=0) - turned.min(axis=0)).astype(int)
        out = cv2.warpAffine(out, R, tuple(size), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        A = np.vstack([R, [0, 0, 1]])[:2]
    if tilt != 1.0:
        out = cv2.GaussianBlur(out, (0, 0), sigmaX=0.8 * np.sqrt(tilt * tilt - 1), sigmaY=0.01)
        out = cv2.resize(out, (0, 0), fx=1.0 / tilt, fy=1.0, interpolation=cv2.INTER_NEAREST)
        A = np.array([[1.0 / tilt, 0, 0], [0, 1.0, 0]]) @ np.vstack([A, [0, 0, 1]])
    full = np.vstack([A, [0, 0, 1]])
    return out, np.linalg.inv(full)[:2]


class FeatureStore:
    """SIFT (optionally affine-simulated) features per photo, computed once and kept in a cache directory.

    Holding every photo's simulated descriptors in memory is what exhausted this machine, so only the few
    photos a step needs are resident.
    """

    def __init__(self, frames, folder: Path, affine: bool, keep: int = 4):
        self.frames, self.folder, self.affine, self.keep = frames, Path(folder), affine, keep
        self.folder.mkdir(parents=True, exist_ok=True)
        self.resident: dict[str, tuple] = {}

    def path(self, name: str) -> Path:
        return self.folder / f'{Path(name).stem}{"_affine" if self.affine else ""}.npz'

    def __getitem__(self, name: str):
        if name in self.resident:
            return self.resident[name]
        cache = self.path(name)
        if not cache.exists():
            image = self.frames.image(name)
            xy, desc = affine_features(image) if self.affine else features(image)
            np.savez_compressed(cache, xy=xy.astype(np.float32), desc=desc.astype(np.float32))
            del image
        with np.load(cache) as data:
            value = (data['xy'].astype(float), data['desc'].astype(np.float32))
        if len(self.resident) >= self.keep:
            self.resident.pop(next(iter(self.resident)))
        self.resident[name] = value
        return value


class ExtendedFrames:
    """The measured frames plus inferred poses, for the second round only.

    A measured ChArUco pose is never overwritten: an inferred pose is added only for a photo that had none.
    """

    def __init__(self, frames, inferred: dict):
        self.base, self.inferred = frames, inferred
        self.session, self.capture, self.intrinsics = frames.session, frames.capture, frames.intrinsics
        self.K, self.D, self.frames = frames.K, frames.D, frames.frames

    def posed(self):
        return self.base.posed() + sorted(self.inferred)

    def unposed(self):
        return [n for n in self.frames if n not in self.posed()]

    def rt(self, name):
        if name in self.base.posed():
            return self.base.rt(name)
        r, t = self.inferred[name]
        return np.asarray(r, float).reshape(3, 1), np.asarray(t, float).reshape(3, 1)

    def image(self, name):
        return self.base.image(name)

    def normalised(self, name, pixels):
        return self.base.normalised(name, pixels)

    def centre(self, name):
        r, t = self.rt(name)
        return (-cv2.Rodrigues(r)[0].T @ t).ravel()


class Frames:
    def __init__(self, session: Path):
        self.session = Path(session)
        self.capture = read_json(self.session / 'capture.json')
        self.intrinsics = self.capture['intrinsics']
        self.K = np.array(self.intrinsics['camera_matrix'], float)
        self.D = np.array(self.intrinsics['dist_coeffs'], float)
        self.frames = {f['image_file']: f for f in self.capture['frames']}

    def posed(self):
        return [n for n, f in self.frames.items() if f.get('pose_status') == 'solved' and f.get('rvec_rad')]

    def unposed(self):
        return [n for n, f in self.frames.items() if n not in self.posed()]

    def rt(self, name):
        f = self.frames[name]
        return np.array(f['rvec_rad'], float).reshape(3, 1), np.array(f['tvec_mm'], float).reshape(3, 1)

    def image(self, name):
        return load_grey(self.session / self.frames[name]['image_path'])

    def normalised(self, name, pixels):
        return cv2.undistortPoints(np.asarray(pixels, float).reshape(-1, 1, 2), self.K, self.D).reshape(-1, 2)

    def centre(self, name):
        r, t = self.rt(name)
        R = cv2.Rodrigues(r)[0]
        return (-R.T @ t).ravel()


def build_map(frames: Frames, feats: dict, use: list[str], pair_matches: dict | None = None) -> dict:
    """Triangulate mutual matches between posed photos with their fixed poses.

    pair_matches: matches computed once and reused, so the self-check does not redo them per photo."""
    xyz, desc, provenance = [], [], []
    by_feature: dict[str, dict[int, int]] = {}
    pairs = []
    for a, b in combinations(sorted(use), 2):
        m = pair_matches[(a, b)] if pair_matches is not None else mutual_matches(feats[a][1], feats[b][1])
        if len(m) < 8:
            pairs.append(dict(a=a, b=b, matches=len(m), kept=0, reason='too few mutual matches'))
            continue
        ia, ib = np.array([i for i, _ in m]), np.array([j for _, j in m])
        ra, ta = frames.rt(a)
        rb, tb = frames.rt(b)
        Pa = np.hstack([cv2.Rodrigues(ra)[0], ta])
        Pb = np.hstack([cv2.Rodrigues(rb)[0], tb])
        X = cv2.triangulatePoints(Pa, Pb, frames.normalised(a, feats[a][0][ia]).T, frames.normalised(b, feats[b][0][ib]).T)
        X = (X[:3] / X[3]).T
        keep = np.ones(len(X), bool)
        for name, r, t, idx in ((a, ra, ta, ia), (b, rb, tb, ib)):
            R = cv2.Rodrigues(r)[0]
            depth = (X @ R.T + t.ravel())[:, 2]
            err = _residuals(X, feats[name][0][idx], r, t, frames.intrinsics)
            keep &= (depth > 0) & (err <= MAX_TRIANGULATION_ERROR_PX)
        da = X - frames.centre(a)
        db = X - frames.centre(b)
        cosang = np.abs(np.sum(da * db, 1) / (np.linalg.norm(da, axis=1) * np.linalg.norm(db, axis=1) + 1e-9))
        keep &= np.degrees(np.arccos(np.clip(cosang, 0, 1))) >= MIN_RAY_ANGLE_DEG
        for i, (lo, hi) in enumerate(MAP_BOUNDS_MM):
            keep &= (X[:, i] >= lo) & (X[:, i] <= hi)
        pairs.append(dict(a=a, b=b, matches=len(m), kept=int(keep.sum())))
        for n in np.flatnonzero(keep):
            point = len(xyz)
            xyz.append(X[n])
            desc.append(feats[a][1][ia[n]])
            provenance.append(dict(photos=[a, b], feature_index=[int(ia[n]), int(ib[n])]))
            by_feature.setdefault(a, {})[int(ia[n])] = point
            by_feature.setdefault(b, {})[int(ib[n])] = point
    if not xyz:
        raise StudyError('No map point survived: the posed photos share no usable matches')
    return dict(xyz=np.array(xyz), desc=np.array(desc, np.float32), provenance=provenance, pairs=pairs,
                photos=sorted(use), by_feature=by_feature)


def direction_of(name: str) -> str | None:
    """Capture label digit: 11 and 21 were taken from the same direction; 01/03 are top views."""
    code = Path(name).stem[-2:]
    return code[1] if code[0] in '12' else None


def label_check(frames: Frames, name: str, centre: np.ndarray, posed: list[str], window_deg: float = 30) -> dict:
    """Compare the solved direction with the photos whose capture label says the same direction.

    The capture label is not a measured angle and never enters the fit; it only flags a result that
    disagrees with how the photograph was taken.
    """
    az = lambda c: float(np.degrees(np.arctan2(c[1], c[0])) % 360)
    elev = lambda c: float(np.degrees(np.arctan2(c[2], np.hypot(c[0], c[1]))))
    mine = direction_of(name)
    same = [p for p in posed if mine and direction_of(p) == mine]
    out = dict(capture_direction=mine, same_direction_photos=same,
               solved_azimuth_deg=round(az(centre), 1), solved_elevation_deg=round(elev(centre), 1))
    if same:
        deltas = [abs((az(centre) - az(frames.centre(p)) + 180) % 360 - 180) for p in same]
        out.update(azimuth_difference_deg=round(min(deltas), 1), agrees_with_capture_label=bool(min(deltas) <= window_deg))
    if Path(name).stem[-2:] in ('01', '03'):
        out.update(expected='top view', agrees_with_capture_label=bool(elev(centre) >= 60))
    return out


def candidate_photos(name: str, photos: list[str]) -> list[str]:
    """Match against the photos taken from the same and neighbouring directions, plus the top views.

    This is the capture order, not a measured angle: it only decides which photographs are compared first,
    never the geometry. Every mapped photo is still used when nothing shares a direction.
    """
    mine = direction_of(name)
    if mine is None:
        return photos
    near = {str((int(mine) - 2) % 8 + 1), mine, str(int(mine) % 8 + 1)}
    chosen = [p for p in photos if direction_of(p) in near or Path(p).stem[-2:] in ('01', '03')]
    return chosen or photos


def solve(frames: Frames, feats: dict, name: str, fmap: dict, policy: dict) -> dict:
    """Locate one photo against the map.

    The query is matched to each mapped photo separately rather than to one descriptor per 3D point: the same place
    looks different from another direction, so a point stays findable through whichever photo resembles this one.
    """
    hits: dict[int, int] = {}
    per_photo = {}
    for other in candidate_photos(name, fmap['photos']):
        table = fmap['by_feature'].get(other, {})
        if not table:
            continue
        m = mutual_matches(feats[name][1], feats[other][1])
        kept = 0
        for i, j in m:
            point = table.get(int(j))
            if point is None:
                continue
            kept += 1
            hits.setdefault(int(i), point)
        per_photo[other] = dict(matches=len(m), with_3d=kept)
    result = dict(schema_version=SCHEMA, pose_source=POSE_SOURCE, image_file=name,
                  map_photos=fmap['photos'], map_points=int(len(fmap['xyz'])), matches=len(hits),
                  matches_per_photo=per_photo, policy=policy, validated_metric=False, suitable_for_ppfd=False,
                  note='diagnostic candidate from image features; never a measured ChArUco pose')
    if len(hits) < max(PNP_MINIMUM_POINTS, policy['min_fit_points'] + policy['min_holdout_points']):
        return dict(result, status='insufficient_matches')
    pairs = sorted(hits.items())
    pixels = np.array([feats[name][0][i] for i, _ in pairs])
    points = np.array([fmap['xyz'][j] for _, j in pairs])
    split = dict(policy, min_holdout_points=max(policy['min_holdout_points'], len(pairs) // 5))
    fit_ids, hold_ids = partition([(int(i), int(j)) for i, j in pairs], split)
    index = {(int(i), int(j)): n for n, (i, j) in enumerate(pairs)}
    fit = np.array([index[k] for k in fit_ids])
    hold = np.array([index[k] for k in hold_ids])
    checks = geometry_checks(points[fit], policy)
    result.update(geometry=checks, fit_points=len(fit), holdout_points=len(hold))
    if checks['degeneracy_reasons']:
        return dict(result, status='degenerate_geometry')
    ok, rvec, tvec, inliers = cv2.solvePnPRansac(points[fit], pixels[fit], frames.K, frames.D,
                                                 reprojectionError=policy['ransac_reprojection_px'],
                                                 iterationsCount=policy['ransac_iterations'],
                                                 confidence=policy['ransac_confidence'], flags=cv2.SOLVEPNP_SQPNP)
    if not ok or inliers is None or len(inliers) < policy['min_fit_points']:
        return dict(result, status='no_solution')
    inl = fit[inliers.ravel()]
    rvec, tvec = cv2.solvePnPRefineLM(points[inl], pixels[inl], frames.K, frames.D, rvec, tvec)
    R = cv2.Rodrigues(rvec)[0]
    if np.any((points[inl] @ R.T + tvec.ravel())[:, 2] <= 0):
        return dict(result, status='points_behind_camera')
    fit_err = _residuals(points[inl], pixels[inl], rvec, tvec, frames.intrinsics)
    hold_err = _residuals(points[hold], pixels[hold], rvec, tvec, frames.intrinsics) if len(hold) else np.array([])
    centre = (-R.T @ tvec).ravel()
    label = label_check(frames, name, centre, fmap['photos'], policy.get('max_direction_difference_deg', 30))
    agree = float(np.mean(hold_err <= policy['holdout_inlier_px'])) if len(hold_err) else 0.0
    passes = (float(np.sqrt((fit_err ** 2).mean())) <= policy['max_fit_error_px']
              and len(hold) >= policy['min_holdout_points']
              and agree >= policy['min_holdout_inlier_fraction']
              and len(inl) >= policy.get('min_inliers', 0)
              and label.get('agrees_with_capture_label', True))
    return dict(result, status='solved', inliers=len(inl), rvec_rad=rvec.ravel().tolist(), tvec_mm=tvec.ravel().tolist(),
                camera_centre_board_mm=centre.round(2).tolist(),
                fit_rms_px=round(float(np.sqrt((fit_err ** 2).mean())), 3),
                holdout_median_px=round(float(np.median(hold_err)), 3) if len(hold_err) else None,
                holdout_max_px=round(float(hold_err.max()), 3) if len(hold_err) else None,
                holdout_inlier_fraction=round(agree, 3), holdout_inlier_px=policy['holdout_inlier_px'],
                capture_label_check=label,
                meets_policy=bool(passes), geometry_warnings=checks['geometry_warnings'])


def run(session: Path, out: Path, self_check: bool = True, policy: dict | None = None, affine: bool = False) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists; choose a new directory: {out}')
    policy = dict(DEFAULT_POLICY, **FEATURE_POLICY, **(policy or {}))
    frames = Frames(session)
    posed, unposed = frames.posed(), frames.unposed()
    if len(posed) < 2:
        raise StudyError('At least two photos with measured poses are needed to build a map')
    feats = FeatureStore(frames, out.parent / ('features_affine' if affine else 'features'), affine)
    pair_matches = {(a, b): mutual_matches(feats[a][1], feats[b][1]) for a, b in combinations(sorted(posed), 2)}
    fmap = build_map(frames, feats, posed, pair_matches)
    candidates = [solve(frames, feats, name, fmap, policy) for name in unposed]
    # Second round: photos that passed may carry the map to their neighbours (side to side is a much smaller
    # viewpoint change than side to oblique). Their own pose is inferred, so anything solved through them is
    # marked as such and judged against a tighter held-out error.
    accepted = [c for c in candidates if c['status'] == 'solved' and c['meets_policy']]
    second = []
    if accepted:
        extended = ExtendedFrames(frames, {c['image_file']: (np.array(c['rvec_rad']), np.array(c['tvec_mm'])) for c in accepted})
        use = posed + [c['image_file'] for c in accepted]
        matches2 = dict(pair_matches)
        for a, b in combinations(sorted(use), 2):
            if (a, b) not in matches2:
                matches2[(a, b)] = mutual_matches(feats[a][1], feats[b][1])
        map2 = build_map(extended, feats, use, matches2)
        # The held-out median is no longer part of the decision, so tighten what is: twice the agreeing share,
        # more inliers, and a narrower direction window (2026-09-24).
        tight = dict(policy, max_holdout_error_px=policy['max_holdout_error_px'] / 2,
                     min_holdout_inlier_fraction=policy['min_holdout_inlier_fraction'] * 2,
                     min_inliers=policy.get('min_inliers', 0) * 2, max_direction_difference_deg=15)
        for name in [c['image_file'] for c in candidates if c not in accepted]:
            c = solve(extended, feats, name, map2, tight)
            c.update(round=2, map_contains_inferred_poses=True,
                     inferred_map_photos=[a['image_file'] for a in accepted],
                     note=c['note'] + '; solved against a map that includes inferred poses, so its error compounds')
            second.append(c)
    checks = []
    if self_check:
        for name in posed:
            others = [p for p in posed if p != name]
            if len(others) < 2:
                continue
            sub = build_map(frames, feats, others, pair_matches)
            c = solve(frames, feats, name, sub, policy)
            if c['status'] == 'solved':
                r, t = frames.rt(name)
                R = cv2.Rodrigues(r)[0]
                truth = (-R.T @ t).ravel()
                got = np.array(c['camera_centre_board_mm'])
                angle = np.degrees(np.arccos(np.clip((np.trace(cv2.Rodrigues(np.array(c['rvec_rad']))[0] @ R.T) - 1) / 2, -1, 1)))
                c.update(measured_centre_board_mm=truth.round(2).tolist(),
                         centre_error_mm=round(float(np.linalg.norm(got - truth)), 2),
                         rotation_error_deg=round(float(angle), 3))
            checks.append(c)
    out.mkdir(parents=True)
    write_json(out / 'feature_map.json', dict(schema=MAP_SCHEMA, photos=fmap['photos'], points=int(len(fmap['xyz'])),
                                              pairs=fmap['pairs'], bounds_mm=[list(b) for b in MAP_BOUNDS_MM],
                                              parameters=dict(max_features=MAX_FEATURES, ratio=RATIO,
                                                              max_triangulation_error_px=MAX_TRIANGULATION_ERROR_PX,
                                                              min_ray_angle_deg=MIN_RAY_ANGLE_DEG),
                                              capture=str(Path(session) / 'capture.json'),
                                              capture_sha256=file_hash(Path(session) / 'capture.json')))
    write_rows(out / 'map_points.csv', [dict(x_mm=round(float(x), 2), y_mm=round(float(y), 2), z_mm=round(float(z), 2),
                                             photo_a=p['photos'][0], photo_b=p['photos'][1])
                                        for (x, y, z), p in zip(fmap['xyz'], fmap['provenance'])],
               ('x_mm', 'y_mm', 'z_mm', 'photo_a', 'photo_b'))
    report = dict(schema=SCHEMA, plant_id=frames.capture.get('plant_id'), session_id=frames.capture.get('session_id'),
                  posed_photos=posed, unposed_photos=unposed, map_points=int(len(fmap['xyz'])),
                  candidates=candidates, second_round=second, self_check=checks, policy=policy, affine_simulation=affine,
                  pose_source=POSE_SOURCE, validated_metric=False, suitable_for_ppfd=False,
                  expected_error_note='self-check on this session says what a passing candidate is worth; read '
                                      'centre_error_mm there before using any candidate',
                  limits='candidates only; measured ChArUco poses untouched; accuracy is the self-check error, '
                         'and the reference poses themselves fail the 1 px gate')
    write_json(out / 'feature_poses.json', report)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--session', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--no-self-check', action='store_true')
    ap.add_argument('--affine', action='store_true', help='simulate tilted viewpoints (slower; needed side <-> oblique)')
    a = ap.parse_args()
    r = run(a.session, a.out, not a.no_self_check, affine=a.affine)
    solved = [c for c in r['candidates'] if c['status'] == 'solved']
    round2 = [c for c in r.get('second_round', []) if c['status'] == 'solved']
    print(json.dumps(dict(map_points=r['map_points'], unposed=len(r['unposed_photos']), solved=len(solved),
                          meets_policy=sum(c['meets_policy'] for c in solved),
                          round2_solved=len(round2), round2_meets_policy=sum(c['meets_policy'] for c in round2),
                          self_check=[dict(photo=c['image_file'], status=c['status'],
                                           centre_error_mm=c.get('centre_error_mm'),
                                           rotation_error_deg=c.get('rotation_error_deg')) for c in r['self_check']]),
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
