"""Addendum C (rev. C.1-C.3): flattened-leaf capture and the accepted-mask contour pool.

Steps
-----
* **C0** - harvest every accepted leaflet mask as ``accepted_mask_projected`` contours, Tier A
  (board pose -> viewing angle, approximate mm scale) and Tier B (shape only). Never dropped for a
  missing pose (rev. C.3).
* **C1** - leaflet photos: rectify by a printed checkerboard grid of pitch ``grid_pitch_mm``
  (homography), segment the leaflet against the white backing, contour in mm and ``area_mm2``.
  ``source='flattened_real'``.
* **C2** - compound photos: rectify, segment, skeletonise; rachis = longest skeleton path from the
  petiole end (petiole toward the bottom of the frame); leaflets = mask minus rachis; insertion
  fraction/angle/side per leaflet; leaflets matched to C1 by **position order** only.
* **C3** - per leaflet: apparent area in the compound photo vs C1 true area, merged-component flag.
* **QA** - for compounds with a full leaflet set only: sum of C1 leaflet areas must not exceed the
  compound area; offenders are listed, never accepted.
* **Correction** - projected -> flattened: per-contour (Tier A, viewing angle) when >= the configured
  number of human-paired contours exists, else provisional; Tier B gets a pooled (distribution-level)
  aspect correction only.

Everything under ``data/`` is read only. Scale comes only from a detected grid; a ruler-only photo is
reported ``scale_unavailable``, never guessed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.synth.images import imread, imwrite

LEAF_SESSION_RE = re.compile(r"^(?P<plant>.+)_leaf_(?P<date>\d{8})$")
LEAF_COLUMNS = ("plant_id", "session_id", "photo_file", "compound_id", "leaflet_id", "level", "attachment",
                "condition", "grid_pitch_mm", "captured_at", "pressed", "notes")
LEVELS = {"compound", "leaflet"}
ATTACHMENTS = {"attached", "detached"}
CONDITIONS = {"healthy", "senescent", "damaged"}
LEAFLET_ID_RE = re.compile(r"^(T|P\d+[LR]|I\d+)$")

#: Processing constants (run-level; recorded in every output).
DEFAULTS = dict(px_per_mm=8.0, grid_patterns=[(9, 6), (7, 5), (6, 4), (5, 4), (4, 3)], max_side_px=2400,
                min_saturation=60, min_component_mm2=4.0, rachis_dt_percentile=25.0, rachis_dilate=1.6,
                qa_tolerance_rel=0.02, min_pairs_for_correction=15, intercalary_rel_area=0.35)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- capture validation
def discover_leaf_sessions(raw_dir: Path) -> list[Path]:
    raw_dir = Path(raw_dir)
    if not raw_dir.is_dir():
        return []
    out = []
    for plant_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        for s in sorted(p for p in plant_dir.iterdir() if p.is_dir()):
            m = LEAF_SESSION_RE.match(s.name)
            if m and m.group("plant") == plant_dir.name:
                out.append(s)
    return out


def validate_leaf_session(session_dir: Path) -> dict[str, Any]:
    """Rows usable for processing + problems. A compound without leaflet photos is normal (rev. C.1)."""
    session_dir = Path(session_dir)
    csv_path = session_dir / "leaf_area_capture.csv"
    res: dict[str, Any] = dict(session_id=session_dir.name, plant_id=session_dir.parent.name, rows=[], problems=[])
    if not csv_path.is_file():
        res["problems"].append(dict(problem="incomplete", reason="missing leaf_area_capture.csv"))
        res["status"] = "incomplete"
        return res
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in LEAF_COLUMNS if c not in (reader.fieldnames or [])]
        rows = list(reader)
    if missing_cols:
        res["problems"].append(dict(problem="incomplete", reason="missing columns", columns=missing_cols))
        res["status"] = "incomplete"
        return res
    listed = set()
    for i, r in enumerate(rows, start=2):
        name = (r.get("photo_file") or "").strip()
        listed.add(name)
        issue = None
        if not (session_dir / name).is_file():
            issue = "missing_file"
        elif r["level"] not in LEVELS:
            issue = "unknown_level"
        elif r["level"] == "leaflet" and not LEAFLET_ID_RE.match(r.get("leaflet_id") or ""):
            issue = "bad_leaflet_id"
        elif r["attachment"] not in ATTACHMENTS:
            issue = "unknown_attachment"
        elif r["condition"] not in CONDITIONS:
            issue = "unknown_condition"
        elif r["pressed"] not in ("yes", "no"):
            issue = "unknown_pressed"
        else:
            try:
                if float(r["grid_pitch_mm"]) <= 0:
                    issue = "incomplete_grid_pitch"
            except (TypeError, ValueError):
                issue = "incomplete_grid_pitch"
        if issue:
            res["problems"].append(dict(row=i, photo=name, problem="incomplete" if issue.startswith("incomplete")
                                        else issue, reason=issue))
            continue
        res["rows"].append(dict(r, row=i, sha256=_sha256(session_dir / name), path=str(session_dir / name)))
    photos = {p.name for p in session_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic")}
    for extra in sorted(photos - listed):
        res["problems"].append(dict(photo=extra, problem="incomplete", reason="photo_not_in_csv"))
    res["status"] = "ok" if not res["problems"] else "incomplete"
    return res


# --------------------------------------------------------------------------- image IO / rectification
def read_photo(path: Path, max_side_px: int) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() == ".heic":
        from tomato3d.synth.capture import read_heic_rgb

        bgr = cv2.cvtColor(read_heic_rgb(path), cv2.COLOR_RGB2BGR)
    else:
        bgr = imread(path, cv2.IMREAD_COLOR)
    s = max_side_px / float(max(bgr.shape[:2]))
    return cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else bgr


def find_grid(gray: np.ndarray, patterns) -> tuple[np.ndarray, tuple[int, int]] | None:
    """Inner corners of a printed checkerboard (largest pattern that is found)."""
    for cols, rows in patterns:
        ok, corners = cv2.findChessboardCornersSB(gray, (cols, rows), flags=cv2.CALIB_CB_NORMALIZE_IMAGE)
        if ok:
            return corners.reshape(-1, 2), (cols, rows)
    return None


def rectify(bgr: np.ndarray, pitch_mm: float, px_per_mm: float, patterns) -> dict[str, Any]:
    """Homography from the grid to a metric plane; the whole photo is warped into it."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    found = find_grid(gray, patterns)
    if found is None:
        return dict(status="scale_unavailable", reason="no checkerboard grid detected")
    corners, (cols, rows) = found
    obj = np.array([[i * pitch_mm, j * pitch_mm] for j in range(rows) for i in range(cols)], np.float64)
    H_mm, _ = cv2.findHomography(corners.astype(np.float64), obj, cv2.RANSAC, 2.0)
    h, w = gray.shape
    img_corners = cv2.perspectiveTransform(np.array([[[0, 0], [w, 0], [w, h], [0, h]]], np.float64), H_mm)[0]
    lo = img_corners.min(axis=0)
    hi = img_corners.max(axis=0)
    span = (hi - lo) * px_per_mm
    if not np.all(np.isfinite(span)) or span.max() > 20000:
        return dict(status="scale_unavailable", reason="degenerate grid homography")
    S = np.array([[px_per_mm, 0, -lo[0] * px_per_mm], [0, px_per_mm, -lo[1] * px_per_mm], [0, 0, 1]])
    H = S @ H_mm
    out = cv2.warpPerspective(bgr, H, (int(math.ceil(span[0])), int(math.ceil(span[1]))), flags=cv2.INTER_LINEAR,
                              borderValue=(255, 255, 255))
    reproj = cv2.perspectiveTransform(corners[None].astype(np.float64), H_mm)[0]
    resid = float(np.sqrt(np.mean(np.sum((reproj - obj) ** 2, axis=1))))
    pitch_est = float(np.median(np.linalg.norm(np.diff(reproj.reshape(rows, cols, 2), axis=1), axis=2)))
    return dict(status="ok", image=out, H=H, pattern=[cols, rows], grid_rms_mm=resid, pitch_check_mm=pitch_est,
                px_per_mm=px_per_mm)


def segment_leaf(bgr: np.ndarray, min_saturation: int, min_area_px: int, *, largest_only: bool) -> np.ndarray:
    """Leaf pixels against white backing and a black/white grid: chromatic (saturated) pixels."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = (hsv[:, :, 1] >= min_saturation) & (hsv[:, :, 2] >= 25)
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= min_area_px]
    if not keep:
        return np.zeros(mask.shape, bool)
    if largest_only:
        keep = [max(keep, key=lambda i: stats[i, cv2.CC_STAT_AREA])]
    out = np.isin(labels, keep).astype(np.uint8)
    cs, _ = cv2.findContours(out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(out)
    cv2.drawContours(filled, cs, -1, 1, thickness=-1)
    return filled.astype(bool)


def shape_stats(points: np.ndarray) -> dict[str, float]:
    """Scale-free shape statistics: aspect (minor/major), solidity, mean |turning| per unit perimeter."""
    p = np.asarray(points, float)
    c = p - p.mean(axis=0)
    _, sv, _ = np.linalg.svd(c, full_matrices=False)
    proj = c @ np.linalg.svd(c, full_matrices=False)[2].T
    aspect = float(np.ptp(proj[:, 1]) / max(np.ptp(proj[:, 0]), 1e-9))
    area = abs(0.5 * float(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1))))
    hull = cv2.contourArea(cv2.convexHull(p.astype(np.float32)))
    d1 = np.roll(p, -1, axis=0) - p
    ang = np.arctan2(d1[:, 1], d1[:, 0])
    turn = np.abs((np.diff(np.r_[ang, ang[0]]) + np.pi) % (2 * np.pi) - np.pi)
    perim = float(np.linalg.norm(d1, axis=1).sum())
    return dict(aspect=aspect, solidity=float(area / hull) if hull > 0 else 0.0,
                curvature=float(turn.sum() / perim * math.sqrt(max(area, 1e-9))))


# --------------------------------------------------------------------------- C1
def process_leaflet(row: dict[str, Any], prm: dict[str, Any]) -> dict[str, Any]:
    base = dict(plant_id=row["plant_id"], session_id=row["session_id"], compound_id=row["compound_id"],
                leaflet_id=row["leaflet_id"], position=row["leaflet_id"], attachment=row["attachment"],
                condition=row["condition"], pressed=row["pressed"], source_photo=row["photo_file"],
                sha256=row["sha256"], source="flattened_real")
    bgr = read_photo(Path(row["path"]), prm["max_side_px"])
    rect = rectify(bgr, float(row["grid_pitch_mm"]), prm["px_per_mm"], prm["grid_patterns"])
    if rect["status"] != "ok":
        return dict(base, status=rect["status"], reason=rect["reason"])
    ppm = rect["px_per_mm"]
    mask = segment_leaf(rect["image"], prm["min_saturation"], int(prm["min_component_mm2"] * ppm ** 2),
                        largest_only=True)
    if not mask.any():
        return dict(base, status="segmentation_failed")
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float) / ppm
    centred = c - c.mean(axis=0)
    _, _, vt = np.linalg.svd(centred, full_matrices=False)
    proj = centred @ vt.T
    from tomato3d.synth.leaflet_surface import normalize_contour

    norm = normalize_contour(c, 64)
    return dict(base, status="ok" if row["pressed"] == "yes" else "unpressed_underestimate",
                area_mm2=float(mask.sum() / ppm ** 2), length_mm=float(np.ptp(proj[:, 0])),
                width_mm=float(np.ptp(proj[:, 1])), contour_mm=np.round(c, 2).tolist(),
                points=np.round(norm["points"], 5).tolist(), grid_rms_mm=rect["grid_rms_mm"],
                grid_pattern=rect["pattern"], **{f"shape_{k}": v for k, v in shape_stats(c).items()})


# --------------------------------------------------------------------------- C2
def zhang_suen(mask: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning (numpy; opencv-contrib ximgproc is not in every environment)."""
    img = np.pad(mask.astype(np.uint8), 1)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            P = [np.roll(np.roll(img, dy, 0), dx, 1) for dy, dx in
                 ((1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1))]
            p2, p3, p4, p5, p6, p7, p8, p9 = P
            B = sum(P)
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c1, c2 = p2 * p4 * p6, p4 * p6 * p8
            else:
                c1, c2 = p2 * p4 * p8, p2 * p6 * p8
            rm = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & (c1 == 0) & (c2 == 0)
            if rm.any():
                img[rm] = 0
                changed = True
    return img[1:-1, 1:-1].astype(bool)


def _longest_path(skel: np.ndarray, start: tuple[int, int]) -> list[tuple[int, int]]:
    """Geodesic farthest path on the 8-connected skeleton from ``start`` (BFS)."""
    from collections import deque

    ys, xs = np.nonzero(skel)
    nodes = set(zip(ys.tolist(), xs.tolist()))
    prev = {start: None}
    q = deque([start])
    last = start
    while q:
        cur = q.popleft()
        last = cur
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nb = (cur[0] + dy, cur[1] + dx)
                if nb != cur and nb in nodes and nb not in prev:
                    prev[nb] = cur
                    q.append(nb)
    path = []
    node = last
    while node is not None:
        path.append(node)
        node = prev[node]
    return path[::-1]


def process_compound(row: dict[str, Any], prm: dict[str, Any]) -> dict[str, Any]:
    base = dict(plant_id=row["plant_id"], session_id=row["session_id"], compound_id=row["compound_id"],
                attachment=row["attachment"], condition=row["condition"], pressed=row["pressed"],
                source_photo=row["photo_file"], sha256=row["sha256"], source="flattened_real")
    bgr = read_photo(Path(row["path"]), prm["max_side_px"])
    rect = rectify(bgr, float(row["grid_pitch_mm"]), prm["px_per_mm"], prm["grid_patterns"])
    if rect["status"] != "ok":
        return dict(base, status=rect["status"], reason=rect["reason"])
    ppm = rect["px_per_mm"]
    mask = segment_leaf(rect["image"], prm["min_saturation"], int(prm["min_component_mm2"] * ppm ** 2),
                        largest_only=True)
    if not mask.any():
        return dict(base, status="segmentation_failed")
    out = dict(base, status="ok", compound_area_mm2=float(mask.sum() / ppm ** 2))
    skel = zhang_suen(mask)
    ys, xs = np.nonzero(skel)
    if len(ys) < 10:
        return dict(out, status="skeleton_failed")
    start = (int(ys.max()), int(xs[np.argmax(ys)]))          # petiole toward the bottom of the frame
    path = np.array(_longest_path(skel, start), float)       # (y, x)
    dt = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)
    width_px = float(np.percentile(dt[path[:, 0].astype(int), path[:, 1].astype(int)], prm["rachis_dt_percentile"]))
    rachis = np.zeros(mask.shape, np.uint8)
    cv2.polylines(rachis, [path[:, ::-1].astype(np.int32)], False, 1, thickness=max(1, int(2 * width_px * prm["rachis_dilate"])))
    leaflets_mask = mask & ~rachis.astype(bool)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(leaflets_mask.astype(np.uint8), 8)
    seg_len = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    total = seg_len[-1]
    comps = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA] / ppm ** 2
        if area < prm["min_component_mm2"]:
            continue
        cy, cx = cents[i][1], cents[i][0]
        k = int(np.argmin((path[:, 0] - cy) ** 2 + (path[:, 1] - cx) ** 2))
        frac = float(seg_len[k] / total) if total > 0 else 0.0
        t = path[min(k + 3, len(path) - 1)] - path[max(k - 3, 0)]
        tangent = np.array([t[1], -t[0]], float)              # (x, up) with image y pointing down
        tangent /= max(np.linalg.norm(tangent), 1e-9)
        to_leaf = np.array([cx - path[k, 1], -(cy - path[k, 0])], float)
        side = "L" if (tangent[0] * to_leaf[1] - tangent[1] * to_leaf[0]) > 0 else "R"
        ang = math.degrees(math.acos(np.clip(np.dot(tangent, to_leaf / max(np.linalg.norm(to_leaf), 1e-9)), -1, 1)))
        comps.append(dict(component=i, area_mm2=float(area), insertion_fraction=frac, side=side,
                          insertion_angle_deg=ang))
    if not comps:
        return dict(out, status="no_leaflets_found")
    term = max(comps, key=lambda c: c["insertion_fraction"])
    term["leaflet_id"], term["azimuth_side"] = "T", "C"
    lateral = sorted([c for c in comps if c is not term], key=lambda c: c["insertion_fraction"])
    big = np.median([c["area_mm2"] for c in lateral]) if lateral else 0.0
    counters = dict(L=0, R=0)
    n_inter = 0
    for c in lateral:
        if big and c["area_mm2"] < prm["intercalary_rel_area"] * big:
            n_inter += 1
            c["leaflet_id"] = f"I{n_inter}"
        else:
            counters[c["side"]] += 1
            c["leaflet_id"] = f"P{counters[c['side']]}{c['side']}"
        c["azimuth_side"] = c["side"]
    first = min((c["insertion_fraction"] for c in lateral), default=term["insertion_fraction"])
    petiole_mm = first * total / ppm
    out.update(rachis_length_mm=float(total / ppm), petiole_length_mm=float(petiole_mm),
               n_pairs=int(min(counters["L"], counters["R"])), n_lateral_left=counters["L"],
               n_lateral_right=counters["R"], n_intercalary=n_inter,
               terminal_fraction=float(math.sqrt(term["area_mm2"]) / max(total / ppm, 1e-9)),
               leaflets=[{k: c[k] for k in ("leaflet_id", "insertion_fraction", "insertion_angle_deg",
                                            "azimuth_side", "area_mm2")} for c in [term] + lateral],
               rachis_width_px=width_px, grid_rms_mm=rect["grid_rms_mm"])
    return out


# --------------------------------------------------------------------------- C3 + QA
def leaflet_in_compound(compounds: list[dict], leaflets: list[dict]) -> tuple[list[dict], list[dict]]:
    by_key = {(l["plant_id"], l["compound_id"], l["leaflet_id"]): l for l in leaflets if l.get("area_mm2")}
    rows, qa = [], []
    for c in compounds:
        if c.get("status") != "ok":
            continue
        expected = c.get("leaflets", [])
        present = [by_key.get((c["plant_id"], c["compound_id"], e["leaflet_id"])) for e in expected]
        for e, true in zip(expected, present):
            rows.append(dict(plant_id=c["plant_id"], compound_id=c["compound_id"], leaflet_id=e["leaflet_id"],
                             apparent_area_mm2=e["area_mm2"], true_area_mm2=true["area_mm2"] if true else None,
                             apparent_over_true=(e["area_mm2"] / true["area_mm2"]) if true else None,
                             visible_fraction=min(1.0, e["area_mm2"] / true["area_mm2"]) if true else None,
                             status="ok" if true else "leaflet_photos_absent"))
        if expected and all(present):
            s = float(sum(p["area_mm2"] for p in present))
            qa.append(dict(plant_id=c["plant_id"], compound_id=c["compound_id"], leaflet_sum_mm2=s,
                           compound_area_mm2=c["compound_area_mm2"],
                           status="qa_fail_leaflet_sum_exceeds_compound"
                           if s > c["compound_area_mm2"] * (1 + DEFAULTS["qa_tolerance_rel"]) else "ok"))
    return rows, qa


def check_compound_sum(leaflet_areas_mm2: list[float], compound_area_mm2: float, tol_rel: float) -> str:
    return "qa_fail_leaflet_sum_exceeds_compound" if sum(leaflet_areas_mm2) > compound_area_mm2 * (1 + tol_rel) else "ok"


# --------------------------------------------------------------------------- correction
def fit_correction(pool: list[dict], flattened: list[dict], pairs: list[dict], min_pairs: int) -> dict[str, Any]:
    """Tier A per-contour (angle-dependent) when enough human pairs; Tier B pooled aspect shift."""
    ref = [shape_stats(np.asarray(l["contour_mm"])) for l in flattened
           if l.get("status") == "ok" and l.get("condition") == "healthy"]
    out: dict[str, Any] = dict(n_flattened_reference=len(ref), n_pairs=len(pairs))
    tier_b = [r for r in pool if r.get("tier") == "B"]
    pool_stats = [shape_stats(np.asarray(r["points"])) for r in pool]
    out["pool_shape_median"] = {k: float(np.median([s[k] for s in pool_stats])) for k in ("aspect", "solidity", "curvature")} if pool_stats else None
    if ref:
        out["reference_shape_median"] = {k: float(np.median([s[k] for s in ref])) for k in ("aspect", "solidity", "curvature")}
        tb = [shape_stats(np.asarray(r["points"]))["aspect"] for r in tier_b] or [s["aspect"] for s in pool_stats]
        out["tier_b_pooled"] = dict(kind="pooled distribution-level aspect scale (not per contour)",
                                    width_scale=out["reference_shape_median"]["aspect"] / float(np.median(tb)),
                                    status="provisional" if len(ref) < min_pairs else "applied")
    else:
        out["tier_b_pooled"] = dict(status="unavailable", reason="no flattened reference yet")
    if len(pairs) >= min_pairs:
        x = np.array([p["camera_elevation_deg"] for p in pairs])
        y = np.array([p["flat_aspect"] / p["projected_aspect"] for p in pairs])
        A = np.c_[np.ones_like(x), np.sin(np.radians(x))]
        coef = np.linalg.lstsq(A, y, rcond=None)[0]
        rng = np.random.default_rng(0)
        boot = [np.linalg.lstsq(A[i], y[i], rcond=None)[0] for i in (rng.integers(0, len(x), len(x)) for _ in range(500))]
        out["tier_a"] = dict(model="flat_aspect/projected_aspect = a + b*sin(camera_elevation)", a=float(coef[0]),
                             b=float(coef[1]), ci95=np.percentile(boot, [2.5, 97.5], axis=0).tolist(), status="applied")
    else:
        out["tier_a"] = dict(status="provisional", reason=f"{len(pairs)} paired contours < {min_pairs}")
    return out


# --------------------------------------------------------------------------- runners
def coverage(sessions: list[dict], leaflets: list[dict], compounds: list[dict]) -> dict[str, Any]:
    rows = [r for s in sessions for r in s["rows"]]
    return dict(plants=len({r["plant_id"] for r in rows}),
                compound_photos=sum(r["level"] == "compound" for r in rows),
                leaflet_photos=sum(r["level"] == "leaflet" for r in rows),
                compounds_with_leaflet_photos=len({(l["plant_id"], l["compound_id"]) for l in leaflets}),
                leaflets_ok=sum(l.get("status") == "ok" for l in leaflets),
                compounds_ok=sum(c.get("status") == "ok" for c in compounds),
                c1_target="30-40 leaflet photos from 3-5 plants (rev. C.2)",
                c2_target="10-15 compound leaves from the same plants (rev. C.1)")


def run_c0(out: Path) -> dict[str, Any]:
    from tomato3d.synth.contours import harvest_accepted
    from tomato3d.synth.leafarea_inputs import ACCEPTED_SOURCES, POSE_FILES, decision_files, look_at_board_mm

    recs, skipped = harvest_accepted(ACCEPTED_SOURCES, POSE_FILES, decision_files(), n_points=64, downscale=4,
                                     look_at_board_mm=look_at_board_mm())
    counts = dict(total=len(recs), tier_A=sum(r["tier"] == "A" for r in recs), tier_B=sum(r["tier"] == "B" for r in recs),
                  skipped=len(skipped), by_plant={p: sum(r["plant_id"] == p for r in recs) for p in ACCEPTED_SOURCES})
    doc = dict(created_at=_now(), source="accepted_mask_projected", counts=counts,
               sources={p: dict(export=str(v), accepted_json_sha256=_sha256(Path(v) / "accepted.json"))
                        for p, v in ACCEPTED_SOURCES.items()},
               pose_files={p: (dict(path=str(v), sha256=_sha256(v)) if v else None) for p, v in POSE_FILES.items()},
               note="projected outlines (angled, curled photos): foreshortened and curl-shrunk; correction_status "
                    "'uncorrected' until the flattened reference exists (Addendum C rev. C.2/C.3)",
               skipped=skipped, contours=recs)
    out.mkdir(parents=True, exist_ok=True)
    (out / "c0_accepted_mask_contours.json").write_text(json.dumps(doc), encoding="utf-8")
    return counts


def run_capture(out: Path, raw_dir: Path, prm: dict[str, Any]) -> dict[str, Any]:
    sessions = [validate_leaf_session(s) for s in discover_leaf_sessions(raw_dir)]
    leaflets, compounds = [], []
    for s in sessions:
        for r in s["rows"]:
            (leaflets if r["level"] == "leaflet" else compounds).append(
                (process_leaflet if r["level"] == "leaflet" else process_compound)(r, prm))
    rows, qa = leaflet_in_compound(compounds, leaflets)
    cov = coverage(sessions, leaflets, compounds)
    out.mkdir(parents=True, exist_ok=True)
    (out / "leaflets.json").write_text(json.dumps(dict(created_at=_now(), params=prm, leaflets=leaflets)), encoding="utf-8")
    (out / "compounds.json").write_text(json.dumps(dict(created_at=_now(), params=prm, compounds=compounds)), encoding="utf-8")
    with (out / "leaflet_in_compound.csv").open("w", encoding="utf-8", newline="") as f:
        cols = ["plant_id", "compound_id", "leaflet_id", "apparent_area_mm2", "true_area_mm2", "apparent_over_true",
                "visible_fraction", "status"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    report = dict(created_at=_now(), raw_dir=str(raw_dir), sessions=[{k: v for k, v in s.items() if k != "rows"}
                                                                    for s in sessions], coverage=cov, qa=qa,
                  status="pending_capture" if not sessions else "processed")
    (out / "capture_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("c0"); p.add_argument("--out", required=True)
    p = sub.add_parser("capture"); p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "c0":
        print(json.dumps(run_c0(Path(args.out))))
    else:
        from tomato3d.config import get_settings

        rep = run_capture(Path(args.out), get_settings().raw_dir, dict(DEFAULTS))
        print(json.dumps(dict(status=rep["status"], coverage=rep["coverage"], qa=len(rep["qa"]))))


if __name__ == "__main__":
    main()
