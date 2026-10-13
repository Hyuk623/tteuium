"""Real rig cameras: intrinsics + solved board poses from ``capture.json``, and the
distortion warp shared by every rendered layer.

Rendering happens in an undistorted *render space*: a square-pixel pinhole camera with the
same pose. One inverse map per intrinsics then warps RGB (Blender) and all masks/depth (own
rasteriser) into the real distorted image, so they stay pixel-aligned.

The trial intrinsics (RMS ~9 px) fold near the image border: there the forward OpenCV model
is not invertible. Output pixels whose inverse does not round-trip within
``distortion_inverse_tolerance_px`` are marked invalid in ``valid_mask``.

Pixel convention: OpenCV (integer coordinates at pixel centres). Board frame per
CONVENTIONS.md: origin at ChArUco corner 0, ``+Z`` up, mm. ``X_cam = R X_board + t``.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class RigView:
    view_id: str
    session_id: str
    capture_path: str
    image_file: str
    camera_matrix: tuple                     # 3x3, at the original resolution
    dist_coeffs: tuple
    image_size_px: tuple                     # (width, height) original
    rvec_rad: tuple
    tvec_mm: tuple
    reprojection_error_px: float
    camera_center_mm: tuple
    elevation_deg: float
    passes_pose_gate: bool

    @property
    def rotation(self) -> np.ndarray:
        return cv2.Rodrigues(np.asarray(self.rvec_rad, float))[0]

    @property
    def translation(self) -> np.ndarray:
        return np.asarray(self.tvec_mm, float)


def load_rig_views(capture_path: Path, max_reprojection_px: float,
                   look_at_board_mm: np.ndarray) -> list[RigView]:
    """Every frame with a solved pose and reprojection error <= ``max_reprojection_px``."""
    d = json.loads(Path(capture_path).read_text(encoding="utf-8"))
    intr = d["intrinsics"]
    views = []
    for f in d["frames"]:
        if f.get("rvec_rad") is None or f.get("reprojection_error_px") is None:
            continue
        if float(f["reprojection_error_px"]) > max_reprojection_px:
            continue
        R = cv2.Rodrigues(np.asarray(f["rvec_rad"], float))[0]
        center = -R.T @ np.asarray(f["tvec_mm"], float)
        rel = center - np.asarray(look_at_board_mm, float)
        elev = math.degrees(math.atan2(rel[2], math.hypot(rel[0], rel[1])))
        views.append(RigView(
            view_id=f"{d['session_id']}/{f['view_code']}", session_id=d["session_id"],
            capture_path=str(capture_path), image_file=f["image_file"],
            camera_matrix=tuple(map(tuple, intr["camera_matrix"])), dist_coeffs=tuple(intr["dist_coeffs"]),
            image_size_px=(int(intr["image_width_px"]), int(intr["image_height_px"])),
            rvec_rad=tuple(f["rvec_rad"]), tvec_mm=tuple(f["tvec_mm"]),
            reprojection_error_px=float(f["reprojection_error_px"]), camera_center_mm=tuple(center.tolist()),
            elevation_deg=float(elev), passes_pose_gate=bool(f.get("passes_pose_gate"))))
    return views


def scale_camera_matrix(K: np.ndarray, scale: float) -> np.ndarray:
    """Resize intrinsics with the pixel-centre convention: ``u' = (u + 0.5) s - 0.5``."""
    out = np.array(K, float).copy()
    out[0, 0] *= scale
    out[1, 1] *= scale
    out[0, 2] = (out[0, 2] + 0.5) * scale - 0.5
    out[1, 2] = (out[1, 2] + 0.5) * scale - 0.5
    return out


@dataclass
class RenderGeometry:
    """Render-space pinhole + inverse distortion map for one intrinsics/output size."""

    out_size_px: tuple                       # (width, height) of the distorted output
    K_out: np.ndarray                        # real intrinsics scaled to out_size
    dist: np.ndarray
    K_render: np.ndarray                     # square-pixel pinhole of the render canvas
    render_size_px: tuple                    # (width, height)
    map_x: np.ndarray = field(repr=False)    # out pixel -> render pixel (float32)
    map_y: np.ndarray = field(repr=False)
    valid: np.ndarray = field(repr=False)    # bool, out pixels with a trustworthy inverse

    @property
    def key(self) -> str:
        body = json.dumps([self.out_size_px, np.round(self.K_out, 6).tolist(), np.round(self.dist, 9).tolist()])
        return hashlib.sha256(body.encode()).hexdigest()[:16]

    def warp(self, image: np.ndarray, *, nearest: bool, fill: float = 0) -> np.ndarray:
        """Render space -> distorted output; invalid pixels get ``fill``."""
        interp = cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR
        out = cv2.remap(image, self.map_x, self.map_y, interp, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=fill)
        out[~self.valid] = fill
        return out


def build_render_geometry(view: RigView, out_size_px: int, *, tolerance_px: float, iterations: int,
                          max_canvas_scale: float) -> RenderGeometry:
    """Compute the render canvas and the inverse distortion map for ``view``'s intrinsics."""
    w0, h0 = view.image_size_px
    scale = out_size_px / float(max(w0, h0))
    w, h = int(round(w0 * scale)), int(round(h0 * scale))
    K = scale_camera_matrix(np.asarray(view.camera_matrix), scale)
    dist = np.asarray(view.dist_coeffs, float)
    u, v = np.meshgrid(np.arange(w, dtype=np.float64), np.arange(h, dtype=np.float64))
    pts = np.stack([u.ravel(), v.ravel()], axis=1)[:, None]
    crit = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, int(iterations), 1e-10)
    norm = cv2.undistortPointsIter(pts, K, dist, None, None, crit)[:, 0]
    back, _ = cv2.projectPoints(np.c_[norm, np.ones(len(norm))], np.zeros(3), np.zeros(3), K, dist)
    err = np.linalg.norm(back[:, 0] - pts[:, 0], axis=1)
    valid = (err <= tolerance_px) & np.isfinite(norm).all(axis=1)
    f = 0.5 * (K[0, 0] + K[1, 1])
    rx, ry = norm[:, 0] * f, norm[:, 1] * f
    cap_x, cap_y = 0.5 * max_canvas_scale * w, 0.5 * max_canvas_scale * h
    cx0, cy0 = K[0, 2] - 0.5 * (w - 1), K[1, 2] - 0.5 * (h - 1)
    inside = (np.abs(rx + cx0) <= cap_x) & (np.abs(ry + cy0) <= cap_y)
    valid &= inside
    lo_x, hi_x = np.floor(rx[valid].min()) - 2, np.ceil(rx[valid].max()) + 2
    lo_y, hi_y = np.floor(ry[valid].min()) - 2, np.ceil(ry[valid].max()) + 2
    W, H = int(hi_x - lo_x) + 1, int(hi_y - lo_y) + 1
    K_r = np.array([[f, 0.0, -lo_x], [0.0, f, -lo_y], [0.0, 0.0, 1.0]])
    map_x = (rx - lo_x).reshape(h, w).astype(np.float32)
    map_y = (ry - lo_y).reshape(h, w).astype(np.float32)
    return RenderGeometry(out_size_px=(w, h), K_out=K, dist=dist, K_render=K_r, render_size_px=(W, H),
                          map_x=map_x, map_y=map_y, valid=valid.reshape(h, w))


def project_render(points_mm: np.ndarray, R: np.ndarray, t: np.ndarray, K_render: np.ndarray
                   ) -> tuple[np.ndarray, np.ndarray]:
    """Pinhole projection into render space: (pixels (N,2), camera depth z mm (N,))."""
    cam = np.asarray(points_mm, float) @ R.T + t[None]
    z = cam[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        uv = cam[:, :2] / z[:, None]
    px = uv * np.array([K_render[0, 0], K_render[1, 1]])[None] + K_render[:2, 2][None]
    return px, z
