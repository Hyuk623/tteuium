"""Board poses from ArUco MARKER corners for photos whose ChArUco corners are too few (2026-10-01).

    python -X utf8 -m tools.marker_pose_rescue --plant dwt_01 --out build/pose_rescue_<date>

The ChArUco pose needs >= 6 interpolated chessboard corners, which need two neighbouring markers each; side photos at
~50 deg elevation often show 5-9 markers but only 2-4 such corners and fail. Every marker's own 4 corners have known
board coordinates (same board object, same sheet->board map), so a PnP on marker corners (RANSAC, SQPnP, then LM on the
inliers) recovers those photos. It is still a BOARD pose (CONVENTIONS 3.1 spirit: no nominal angle, no leaf points).

Checked 2026-10-01 on photos that already had a ChArUco pose: camera centres agree within 2-19 mm and 0.3-3.6 deg; both
kinds of pose leave ~5-10 px residuals over the whole board (the existing gate of 1 px was never met), so a rescued pose
is of the same quality class as the existing ones, not better. Acceptance (POLICY): >= MIN_INLIERS inlier corners,
inlier RMS <= MAX_RMS_PX, and the S3 view-selection rule (silhouette explained >= 80 %) still applies downstream.

Output: a COPY of the edit session with the rescued poses added (pose_status 'solved_marker_corners', pose_source
recorded), so the original capture stays untouched; plus rescue.json with every photo's numbers.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
POLICY = dict(min_markers=4, min_inliers=12, max_rms_px=4.0, ransac_px=6.0)
POSE_STATUS = 'solved_marker_corners'


def board_and_markers():
    from tomato3d.config import get_settings
    from tomato3d.io.schemas import BoardSpec
    from tomato3d.calib.board import build_charuco_board, sheet_to_board_mm
    spec = BoardSpec.model_validate_json(get_settings().board_spec_path.read_text(encoding='utf-8'))
    board = build_charuco_board(spec)
    obj = {int(i): sheet_to_board_mm(np.asarray(c, float).reshape(-1, 3), spec) for i, c in zip(np.array(board.getIds()).ravel(), board.getObjPoints())}
    return board, obj, spec


def detector(board):
    p = cv2.aruco.DetectorParameters()
    p.adaptiveThreshWinSizeMin, p.adaptiveThreshWinSizeMax, p.adaptiveThreshWinSizeStep = 3, 63, 6
    p.minMarkerPerimeterRate = 0.01
    p.polygonalApproxAccuracyRate = 0.05
    p.perspectiveRemovePixelPerCell = 8
    p.perspectiveRemoveIgnoredMarginPerCell = 0.2
    p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    return cv2.aruco.ArucoDetector(board.getDictionary(), p)


def marker_pose(gray: np.ndarray, det, obj: dict, K, D) -> dict:
    best = None
    for img in (gray, cv2.createCLAHE(3.0, (16, 16)).apply(gray)):
        c, ids, _ = det.detectMarkers(img)
        if ids is not None:
            keep = [k for k, i in enumerate(ids.ravel()) if int(i) in obj]
            if best is None or len(keep) > len(best[2]):
                best = (c, ids, keep)
    if best is None or len(best[2]) < POLICY['min_markers']:
        return dict(status='too_few_markers', markers=0 if best is None else len(best[2]))
    c, ids, keep = best
    o = np.concatenate([obj[int(ids.ravel()[k])] for k in keep]).astype(np.float64)
    im = np.concatenate([c[k].reshape(-1, 2) for k in keep]).astype(np.float64)
    ok, r, t, inl = cv2.solvePnPRansac(o, im, K, D, reprojectionError=POLICY['ransac_px'], iterationsCount=2000,
                                       confidence=0.999, flags=cv2.SOLVEPNP_SQPNP)
    if not ok or inl is None or len(inl) < POLICY['min_inliers']:
        return dict(status='rejected', reason='too few RANSAC inliers', markers=len(keep), inliers=0 if inl is None else int(len(inl)))
    inl = inl.ravel()
    r, t = cv2.solvePnPRefineLM(o[inl], im[inl], K, D, r, t)
    pr = cv2.projectPoints(o[inl], r, t, K, D)[0].reshape(-1, 2)
    rms = float(np.sqrt(np.mean(np.sum((pr - im[inl]) ** 2, 1))))
    allp = cv2.projectPoints(o, r, t, K, D)[0].reshape(-1, 2)
    rms_all = float(np.sqrt(np.mean(np.sum((allp - im) ** 2, 1))))
    res = dict(markers=len(keep), marker_ids=sorted(int(ids.ravel()[k]) for k in keep), points=len(o), inliers=int(len(inl)),
               rms_inliers_px=round(rms, 3), rms_all_px=round(rms_all, 3), rvec_rad=r.ravel().tolist(), tvec_mm=t.ravel().tolist())
    res['status'] = 'accepted' if rms <= POLICY['max_rms_px'] else 'rejected'
    if res['status'] == 'rejected':
        res['reason'] = f'inlier RMS {rms:.2f} px > {POLICY["max_rms_px"]}'
    return res


def angles(r, t, centre_xy=(95.0, -57.0)):
    R = cv2.Rodrigues(np.asarray(r, float))[0]
    C = -R.T @ np.asarray(t, float).ravel()
    return round(math.degrees(math.atan2(C[1] - centre_xy[1], C[0] - centre_xy[0])), 1), \
        round(math.degrees(math.atan2(C[2], math.hypot(C[0] - centre_xy[0], C[1] - centre_xy[1]))), 1)


def rescue(plant: str, out: Path, config: Path = CONFIG) -> dict:
    out = Path(out) / plant
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    pc = read_json(config)['plants'][plant]
    return rescue_session(ROOT / pc['capture'] / 'edit_session', out / 'edit_session', plant)


def rescue_session(src: Path, dst: Path, plant: str | None = None) -> dict:
    """Copy the edit session `src` to `dst` with marker-corner poses added; rescue.json goes next to `dst`.
    Used by tools.plant_auto right after S0 (2026-10-01), so new plants get the extra poses without a separate step."""
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise StudyError(f'Output exists: {dst}')
    cap = read_json(src / 'capture.json')
    K = np.array(cap['intrinsics']['camera_matrix'], float)
    D = np.array(cap['intrinsics']['dist_coeffs'], float)
    board, obj, spec = board_and_markers()
    det = detector(board)
    rows, rescued = [], 0
    for f in cap['frames']:
        row = dict(view=f['view_code'], existing=f.get('pose_status'))
        g = np.asarray(Image.open(src / f['image_path']).convert('L'))
        m = marker_pose(g, det, obj, K, D)
        row.update({k: v for k, v in m.items() if k not in ('rvec_rad', 'tvec_mm')})
        if 'rvec_rad' in m:
            row['azimuth_deg'], row['elevation_deg'] = angles(m['rvec_rad'], m['tvec_mm'])
            if f.get('rvec_rad') is not None:
                R1, R0 = cv2.Rodrigues(np.array(m['rvec_rad']))[0], cv2.Rodrigues(np.array(f['rvec_rad'], float))[0]
                C1, C0 = -R1.T @ np.array(m['tvec_mm']), -R0.T @ np.array(f['tvec_mm'], float)
                row['vs_charuco'] = dict(centre_mm=round(float(np.linalg.norm(C1 - C0)), 1),
                                         angle_deg=round(math.degrees(math.acos(min(1, max(-1, (np.trace(R1 @ R0.T) - 1) / 2)))), 2))
        if f.get('pose_status') != 'solved' and m.get('status') == 'accepted':
            f.update(pose_status=POSE_STATUS, rvec_rad=m['rvec_rad'], tvec_mm=m['tvec_mm'], reprojection_error_px=m['rms_inliers_px'],
                     passes_pose_gate=False, pose_source=dict(method='aruco marker corners, RANSAC SQPnP + LM on inliers',
                                                              policy=POLICY, markers=m['marker_ids'], inliers=m['inliers'], points=m['points']))
            row['rescued'] = True
            rescued += 1
        rows.append(row)
    # copy of the session (images by copy, OneDrive-safe), with the rescued poses; the original is not modified
    shutil.copytree(src, dst)
    write_json(dst / 'capture.json', cap)
    doc = dict(schema='marker-pose-rescue-1', plant=plant or cap.get('plant_id'), source_capture=str(src / 'capture.json'),
               source_capture_sha256=file_hash(src / 'capture.json'), policy=POLICY, rescued=rescued,
               posed_before=sum(r['existing'] == 'solved' for r in rows), posed_after=sum(r['existing'] == 'solved' or r.get('rescued', False) for r in rows),
               photos=rows, note='rescued poses are board poses from marker corners; same 5-10 px quality class as the ChArUco ones')
    write_json(dst.parent / 'rescue.json', doc)
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--plant', nargs='+', required=True)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    for p in a.plant:
        d = rescue(p, a.out)
        print(p, 'posed', d['posed_before'], '->', d['posed_after'], [(r['view'], r.get('azimuth_deg')) for r in d['photos'] if r.get('rescued')])


if __name__ == '__main__':
    main()
