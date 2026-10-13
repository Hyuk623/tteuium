"""Addendum B step B7 (report-only): angle between each leaflet surface and the viewing direction.

For every leaflet-view: the area-weighted mean surface normal of the leaflet mesh (``meshes.obj``,
board frame) and the direction from the leaflet centroid to the camera centre. ``view_angle_deg`` =
arccos(|n . d|): 0 = facing the camera, 90 = edge-on (two-sided leaves). Joined with the per-GT
detector matches of an evaluation file and the visible-mask aspect (minAreaRect short/long).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.synth.images import imread


def leaflet_normals(obj_path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Leaflet object name (``plant__Lxx__TAG``) -> (unit mean normal, area-weighted centroid)."""
    verts, faces_by_obj, name = [], {}, None
    for line in Path(obj_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("o "):
            name = line[2:]
            faces_by_obj.setdefault(name, [])
        elif line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f ") and name is not None:
            faces_by_obj[name].append([int(x) - 1 for x in line.split()[1:4]])
    V = np.asarray(verts)
    out = {}
    for n, f in faces_by_obj.items():
        if n.count("__") != 2 or not f:
            continue
        F = np.asarray(f)
        a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        cr = np.cross(b - a, c - a)
        area = np.linalg.norm(cr, axis=1)
        # orient each triangle consistently with the first before averaging (two-sided surface)
        ref = cr[np.argmax(area)]
        cr = np.where((cr @ ref)[:, None] < 0, -cr, cr)
        nrm = cr.sum(axis=0)
        cen = ((a + b + c) / 3 * area[:, None]).sum(axis=0) / max(area.sum(), 1e-12)
        out[n] = (nrm / max(np.linalg.norm(nrm), 1e-12), cen)
    return out


def view_angles(run: Path, evaluation: Path) -> list[dict[str, Any]]:
    run = Path(run)
    views = {v["view_id"]: v for v in json.loads((run / "views.json").read_text(encoding="utf-8"))["views"]}
    ev = json.loads(Path(evaluation).read_text(encoding="utf-8"))["detector"]["per_gt"]
    match = {(g["image"], g["instance"]): g for g in ev}
    rows = []
    for r in [json.loads(l) for l in (run / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]:
        sdir = run / "scenes" / r["scene_id"]
        normals = leaflet_normals(sdir / "meshes.obj")
        index = json.loads((sdir / "leaflet_index.json").read_text(encoding="utf-8"))
        cam = np.asarray(views[r["view_id"]]["camera_center_mm"], float)
        vis = imread(run / r["visible_mask"])
        key = f"{r['scene_id']}/{r['view_id']}"
        for inst, info in index.items():
            nm = info["leaflet_id"].replace("/", "__")
            if nm not in normals:
                continue
            n, cen = normals[nm]
            d = cam - cen
            d /= np.linalg.norm(d)
            angle = float(np.degrees(np.arccos(np.clip(abs(float(n @ d)), 0, 1))))
            m = vis == int(inst)
            aspect = None
            if m.sum() >= 5:
                ys, xs = np.nonzero(m)
                (_, _), (w, h), _ = cv2.minAreaRect(np.c_[xs, ys].astype(np.float32))
                aspect = float(min(w, h) / max(w, h)) if max(w, h) > 0 else None
            g = match.get((key, int(inst)))
            rows.append(dict(image=key, instance=int(inst), view_angle_deg=angle, visible_px=int(m.sum()),
                             aspect=aspect, in_gt=g is not None, matched=g["matched"] if g else None))
    return rows


def summarize(rows: list[dict[str, Any]], real_aspect_p10: float) -> dict[str, Any]:
    ang = np.array([r["view_angle_deg"] for r in rows if r["visible_px"] > 0])
    gt = [r for r in rows if r["in_gt"]]
    bins = [(0, 30), (30, 50), (50, 70), (70, 90.01)]
    by_bin = {}
    for lo, hi in bins:
        sel = [r["matched"] for r in gt if lo <= r["view_angle_deg"] < hi]
        by_bin[f"{lo}-{int(hi)}"] = dict(n=len(sel), recall=round(float(np.mean(sel)), 4) if sel else None)
    tail = [r for r in rows if r["aspect"] is not None and r["aspect"] < real_aspect_p10]
    return dict(n_leaflet_views_visible=int(len(ang)),
                view_angle_p10_p50_p90=np.percentile(ang, [10, 50, 90]).round(1).tolist() if len(ang) else None,
                recall_by_view_angle=by_bin,
                aspect_tail=dict(threshold=real_aspect_p10, n=len(tail),
                                 share_with_angle_ge_60=round(float(np.mean([r["view_angle_deg"] >= 60 for r in tail])), 4)
                                 if tail else None,
                                 share_all_with_angle_ge_60=round(float(np.mean(ang >= 60)), 4) if len(ang) else None))


# --------------------------------------------------------------------------- Addendum D.1, B8 (report-only)
def _largest_contour(mask: np.ndarray) -> np.ndarray | None:
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    return c[:, 0, :].astype(np.float64) if len(c) >= 20 else None


def serration_metrics(contour: np.ndarray, n_points: int = 256, smooth_sigma_pts: float = 8.0) -> dict[str, float]:
    """Scale-invariant contour roughness: normalised perimeter and RMS radial deviation from a smoothed self."""
    from scipy.ndimage import gaussian_filter1d

    from tomato3d.synth.leaflet_surface import resample_closed

    c = np.asarray(contour, float)
    x, y = c[:, 0], c[:, 1]
    area = abs(0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    perim = float(np.linalg.norm(np.diff(np.vstack([c, c[:1]]), axis=0), axis=1).sum())
    r_eq = math.sqrt(area / math.pi) if area > 0 else float("nan")
    p = resample_closed(c, n_points)
    sm = np.c_[gaussian_filter1d(p[:, 0], smooth_sigma_pts, mode="wrap"), gaussian_filter1d(p[:, 1], smooth_sigma_pts, mode="wrap")]
    dev = np.linalg.norm(p - sm, axis=1)
    return dict(norm_perimeter=perim ** 2 / (4 * math.pi * area) if area > 0 else float("nan"),
                rms_dev_rel=float(np.sqrt(np.mean(dev ** 2)) / r_eq), r_eq_px=r_eq)


def matched_scale_contour(mask: np.ndarray, r_eq_target_px: float) -> np.ndarray | None:
    """Re-rasterise a mask so its equivalent radius is ``r_eq_target_px`` and re-extract the contour."""
    area = float(mask.sum())
    if area < 20:
        return None
    s = r_eq_target_px / math.sqrt(area / math.pi)
    ys, xs = np.nonzero(mask)
    crop = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8)
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
    small = cv2.resize(crop * 255, None, fx=s, fy=s, interpolation=interp) >= 128
    return _largest_contour(np.pad(small, 2))
