"""Addendum D: pooled leaf library (``data/raw/leaf_library/<session>/``, read only).

No ``plant_id`` by design: the library is pooled appearance/shape data and is never mapped to a
plant. Every photo is checked against its CSV row (file present, sha256). Leaflets are segmented
against the white sheet, classified ``healthy / senescent / damaged`` from colour (fractions kept),
and emitted as contours only from photos whose ``uses`` contains ``shape_contour``.

D0 (view dependence): the ``rot_grid`` series shows one sheet of leaflets rotated under a fixed
camera and light. Leaflets are matched across shots by a similarity transform of the whole sheet
(centroid layout), never by appearance; per leaflet, brightness and local contrast (high-pass
energy inside the eroded mask) are measured raw and normalised by the surrounding paper.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

CSV_NAME = "leaf_library_capture.csv"
REQUIRED = ("session_id", "photo_file", "sha256", "level", "uses", "quality_flags", "rotation_series", "rotation_step")
OCCLUSION_FLAGS = {"hand_occlusion", "tool_occlusion", "on_ruler_overlap", "no_leaf"}
PRM = dict(max_side_px=3024, min_saturation=45, min_leaflet_px=1500, highpass_sigma_px=6.0, paper_ring_px=25,
           senescent_hue_max=28, senescent_fraction=0.15, damaged_fraction=0.12,
           match_max_dist_rel=0.08, leaf_hue_min=20, leaf_hue_max=95,
           min_green_fraction=0.6, min_median_value_rel=0.12,
           necrotic_value_rel_max=0.18)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_library(session_dir: Path) -> dict[str, Any]:
    """Validate the CSV against files. Never requires ``plant_id``."""
    session_dir = Path(session_dir)
    rows, problems = [], []
    with (session_dir / CSV_NAME).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            return dict(rows=[], problems=[dict(problem="missing_columns", columns=missing)])
        for i, r in enumerate(reader, start=2):
            p = session_dir / r["photo_file"]
            if not p.is_file():
                problems.append(dict(row=i, photo=r["photo_file"], problem="missing_file"))
                continue
            if r["sha256"] and _sha256(p) != r["sha256"].lower():
                problems.append(dict(row=i, photo=r["photo_file"], problem="sha256_mismatch"))
                continue
            r = dict(r, row=i, path=str(p), uses_set=set(filter(None, r["uses"].split(";"))),
                     flags_set=set(filter(None, r["quality_flags"].split(";"))))
            rows.append(r)
    return dict(rows=rows, problems=problems)


def contour_allowed(row: dict[str, Any]) -> bool:
    """Contours only from photos meant for shape and free of occlusion flags."""
    return "shape_contour" in row["uses_set"] and not (row["flags_set"] & OCCLUSION_FLAGS)


def read_bgr(path: Path, max_side_px: int) -> np.ndarray:
    from tomato3d.synth.capture import read_heic_rgb

    rgb = read_heic_rgb(Path(path))
    s = max_side_px / float(max(rgb.shape[:2]))
    if s < 1:
        rgb = cv2.resize(rgb, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def segment_leaflets(bgr: np.ndarray, prm: dict[str, Any] = PRM) -> list[np.ndarray]:
    """One boolean mask per leaflet (connected chromatic region >= min size, holes filled)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = ((hsv[:, :, 1] >= prm["min_saturation"]) & (hsv[:, :, 2] >= 30)).astype(np.uint8)
    blue = (hsv[:, :, 0] >= 95) & (hsv[:, :, 0] <= 130)             # tweezers/scissors handles
    m[blue] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    out = []
    h, w = m.shape
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < prm["min_leaflet_px"]:
            continue
        x, y, bw, bh = st[i, :4]
        if x <= 1 or y <= 1 or x + bw >= w - 1 or y + bh >= h - 1:   # desk edge, cut-off objects
            continue
        comp = (lab == i).astype(np.uint8)
        hue = float(np.median(hsv[:, :, 0][comp.astype(bool)]))
        if not prm["leaf_hue_min"] <= hue <= prm["leaf_hue_max"]:      # wood, skin, blue tools
            continue
        cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        filled = np.zeros_like(comp)
        cv2.drawContours(filled, cs, -1, 1, -1)
        out.append(filled.astype(bool))
    return out


def paper_value(bgr: np.ndarray, mask: np.ndarray, prm: dict[str, Any] = PRM) -> float | None:
    """Median HSV value of the paper in a ring around the leaflet (low-saturation pixels only)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    k = 2 * prm["paper_ring_px"] + 1
    ring = cv2.dilate(mask.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool) & ~mask.astype(bool)
    ring &= hsv[:, :, 1] < prm["min_saturation"]
    return float(np.median(hsv[:, :, 2][ring])) if ring.sum() >= 50 else None


def classify_condition(bgr: np.ndarray, mask: np.ndarray, prm: dict[str, Any] = PRM) -> dict[str, Any]:
    """healthy / senescent / damaged / non_leaf from colour, with value normalised by the local paper (rev. D.2.4).

    Thresholds on value are relative to the paper so an under-exposed photo is not read as necrotic. They were set
    from the leaf library (2026-10-06): the per-leaflet median V/paper of green tissue has p1 0.185 / median 0.295,
    so necrotic = brownish (hue < senescent_hue_max or unsaturated) AND V/paper < necrotic_value_rel_max (0.18,
    darker than the p1 of healthy tissue); non_leaf = green fraction < 0.6 or median V/paper < 0.12.
    """
    pv = paper_value(bgr, mask, prm)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[mask.astype(bool)]
    green = float(np.mean((hsv[:, 0] >= 25) & (hsv[:, 0] <= 95) & (hsv[:, 1] >= prm["min_saturation"])))
    if pv is None:
        return dict(condition="unclassified", reason="no paper around the leaflet", green_fraction=green,
                    senescent_fraction=None, necrotic_fraction=None, paper_value=None)
    v_rel = hsv[:, 2].astype(np.float64) / pv
    if green < prm["min_green_fraction"] or float(np.median(v_rel)) < prm["min_median_value_rel"]:
        return dict(condition="non_leaf", senescent_fraction=None, necrotic_fraction=None, green_fraction=green,
                    paper_value=pv)
    brownish = (hsv[:, 0] < prm["senescent_hue_max"]) | (hsv[:, 1] < prm["min_saturation"])
    necrotic = float(np.mean(brownish & (v_rel < prm["necrotic_value_rel_max"])))
    senescent = float(np.mean((hsv[:, 0] < prm["senescent_hue_max"]) & (v_rel >= prm["necrotic_value_rel_max"])))
    if necrotic >= prm["damaged_fraction"]:
        cond = "damaged"
    elif senescent >= prm["senescent_fraction"]:
        cond = "senescent"
    else:
        cond = "healthy"
    return dict(condition=cond, senescent_fraction=senescent, necrotic_fraction=necrotic, green_fraction=green,
                paper_value=pv)


def appearance(bgr: np.ndarray, mask: np.ndarray, prm: dict[str, Any] = PRM) -> dict[str, float]:
    """Brightness and local contrast inside the leaflet, raw and normalised by the paper around it."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
    inner = cv2.erode(mask.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    hp = g - cv2.GaussianBlur(g, (0, 0), prm["highpass_sigma_px"])
    ring = cv2.dilate(mask.astype(np.uint8), np.ones((2 * prm["paper_ring_px"] + 1,) * 2, np.uint8)).astype(bool) & ~mask
    hsv_v = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1]
    paper = ring & (hsv_v < prm["min_saturation"])
    pv = float(np.median(g[paper])) if paper.sum() > 50 else float("nan")
    b = float(g[inner].mean()) if inner.any() else float("nan")
    c = float(hp[inner].std()) if inner.any() else float("nan")
    return dict(brightness=b, contrast=c, paper=pv, brightness_rel=b / pv, contrast_rel=c / pv)


def _centroids(masks: list[np.ndarray]) -> np.ndarray:
    return np.array([[np.nonzero(m)[1].mean(), np.nonzero(m)[0].mean()] for m in masks])


def match_layout(ref: np.ndarray, other: np.ndarray, angle_deg: float, *, iters: int = 6,
                 max_dist_rel: float = PRM["match_max_dist_rel"]) -> dict[str, Any]:
    """Similarity transform mapping ``other`` centroids onto ``ref`` (initial rotation ``angle_deg``)."""
    a = math.radians(angle_deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    co, cr = other.mean(axis=0), ref.mean(axis=0)
    M = np.c_[R, cr - R @ co]
    scale_ref = float(np.median(np.linalg.norm(ref - cr, axis=1))) or 1.0
    pairs = []
    for _ in range(iters):
        moved = other @ M[:, :2].T + M[:, 2]
        d = np.linalg.norm(moved[:, None] - ref[None], axis=2)
        pairs = []
        used = set()
        for i in np.argsort(d.min(axis=1)):
            j = int(np.argmin(d[i]))
            if j in used or d[i, j] > max_dist_rel * scale_ref * 4:
                continue
            used.add(j)
            pairs.append((int(i), j))
        if len(pairs) < 3:
            break
        src = np.float32([other[i] for i, _ in pairs])
        dst = np.float32([ref[j] for _, j in pairs])
        M2, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)
        if M2 is None:
            break
        M = M2
    moved = other @ M[:, :2].T + M[:, 2]
    resid = [float(np.linalg.norm(moved[i] - ref[j])) for i, j in pairs]
    rot = math.degrees(math.atan2(M[1, 0], M[0, 0]))
    return dict(M=M.tolist(), rotation_deg=rot, pairs=pairs,
                residual_rel_median=float(np.median(resid) / scale_ref) if resid else None)


def d0_rot_grid(rows: list[dict[str, Any]], out_dir: Path, prm: dict[str, Any] = PRM) -> dict[str, Any]:
    """D0: per-leaflet brightness/contrast across the 4 rot_grid shots, matched by sheet layout."""
    from tomato3d.synth.images import imwrite

    shots = sorted([r for r in rows if r["rotation_series"] == "rot_grid"], key=lambda r: int(r["rotation_step"]))
    data = []
    for r in shots:
        bgr = read_bgr(Path(r["path"]), prm["max_side_px"])
        masks = segment_leaflets(bgr, prm)
        data.append(dict(row=r, bgr=bgr, masks=masks, cent=_centroids(masks)))
    ref = data[0]
    matches = [dict(rotation_deg=0.0, pairs=[(i, i) for i in range(len(ref["masks"]))], residual_rel_median=0.0)]
    for k, d in enumerate(data[1:], start=1):
        # The sheet layout is near-symmetric under 180 deg, so layout residual alone is ambiguous.
        # Hypotheses are ranked by the consistency of matched leaflet areas under the transform
        # (one global scale must explain every pair) - a size check, not appearance matching.
        ref_area = np.array([m.sum() for m in ref["masks"]], float)
        oth_area = np.array([m.sum() for m in d["masks"]], float)
        cands = []
        for ang in (0, 90, 180, 270):            # rotation direction of the sheet is not assumed
            m = match_layout(ref["cent"], d["cent"], ang)
            if len(m["pairs"]) < 0.6 * len(ref["masks"]):
                continue
            lr = np.log([oth_area[i] / ref_area[j] for i, j in m["pairs"]])
            m["area_log_ratio_mad"] = float(np.median(np.abs(lr - np.median(lr))))
            m["hypothesis_deg"] = ang
            cands.append(m)
        if not cands:
            raise RuntimeError(f"rot_grid shot {k}: no layout hypothesis matched")
        cands.sort(key=lambda m: (m["area_log_ratio_mad"], m["residual_rel_median"] or 9))
        best = cands[0]
        best["alternatives"] = [dict(hypothesis_deg=c["hypothesis_deg"], area_log_ratio_mad=c["area_log_ratio_mad"],
                                     n_pairs=len(c["pairs"])) for c in cands[1:]]
        matches.append(best)
    leaflets = {}
    crops_dir = Path(out_dir) / "rotation_crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    for k, (d, m) in enumerate(zip(data, matches)):
        for i_other, j_ref in m["pairs"]:
            lid = f"g{j_ref:02d}"
            mask = d["masks"][i_other]
            ys, xs = np.nonzero(mask)
            x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
            crop = d["bgr"][y0:y1, x0:x1].copy()
            crop[~mask[y0:y1, x0:x1]] = 255
            name = f"{lid}_shot{k}.png"
            imwrite(crops_dir / name, crop)
            e = leaflets.setdefault(lid, dict(leaflet_id=lid, shots={}))
            e["shots"][str(k)] = dict(photo=d["row"]["photo_file"], crop=f"rotation_crops/{name}",
                                      area_px=int(mask.sum()), **appearance(d["bgr"], mask, prm),
                                      **classify_condition(d["bgr"], mask, prm))
    complete = [e for e in leaflets.values() if len(e["shots"]) == len(data)]
    stats = {}
    for key in ("brightness", "contrast", "brightness_rel", "contrast_rel"):
        ch = []
        for e in complete:
            v = np.array([e["shots"][str(k)][key] for k in range(len(data))], float)
            if np.all(np.isfinite(v)) and v.mean() > 0:
                ch.append(float((v.max() - v.min()) / v.mean()))
                e.setdefault("rotation_change_rel", {})[key] = ch[-1]
        stats[key] = dict(n=len(ch), p10=float(np.percentile(ch, 10)), p50=float(np.median(ch)),
                          p90=float(np.percentile(ch, 90))) if ch else None
    return dict(shots=[dict(photo=d["row"]["photo_file"], step=d["row"]["rotation_step"], n_leaflets=len(d["masks"]))
                       for d in data],
                matches=[dict(rotation_deg=m["rotation_deg"], n_pairs=len(m["pairs"]),
                              residual_rel_median=m["residual_rel_median"],
                              area_log_ratio_mad=m.get("area_log_ratio_mad"), alternatives=m.get("alternatives"))
                         for m in matches],
                n_complete=len(complete), rotation_change_rel=stats, params=prm, leaflets=leaflets)


SOURCE_LIBRARY = "flattened_real_unpressed"


def process_library(rows: list[dict[str, Any]], out_dir: Path, prm: dict[str, Any] = PRM) -> dict[str, Any]:
    """Segment every photo; leaflet records (condition, appearance, crop) + allowed contours."""
    from tomato3d.synth.contours import unit_area_points
    from tomato3d.synth.images import imwrite
    from tomato3d.synth.leaflet_surface import normalize_contour

    out_dir = Path(out_dir)
    (out_dir / "crops").mkdir(parents=True, exist_ok=True)
    records, contours = [], []
    for r in rows:
        if r["level"] not in ("leaflet", "compound"):
            continue
        bgr = read_bgr(Path(r["path"]), prm["max_side_px"])
        allowed = contour_allowed(r) and r["level"] == "leaflet" and \
            (r["rotation_series"] != "rot_grid" or str(r["rotation_step"]) == "0")
        for n, mask in enumerate(segment_leaflets(bgr, prm)):
            ys, xs = np.nonzero(mask)
            x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
            crop = bgr[y0:y1, x0:x1].copy()
            crop[~mask[y0:y1, x0:x1]] = 255
            cid = f"{Path(r['photo_file']).stem}_c{n:02d}"
            imwrite(out_dir / "crops" / f"{cid}.png", crop)
            cond = classify_condition(bgr, mask, prm)
            rec = dict(component_id=cid, photo=r["photo_file"], photo_sha256=r["sha256"], level=r["level"],
                       uses=sorted(r["uses_set"]), quality_flags=sorted(r["flags_set"]), pressed="no",
                       rotation_series=r["rotation_series"] or None, area_px=int(mask.sum()),
                       crop=f"crops/{cid}.png", **cond, **appearance(bgr, mask, prm))
            records.append(rec)
            if allowed and cond["condition"] != "non_leaf":
                cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
                norm = normalize_contour(c, 64)
                contours.append(dict(
                    contour_id=f"{SOURCE_LIBRARY}/{cid}", source=SOURCE_LIBRARY, plant_id=None, photo=r["photo_file"],
                    photo_sha256=r["sha256"], pressed="no", condition=cond["condition"],
                    senescent_fraction=cond["senescent_fraction"], necrotic_fraction=cond["necrotic_fraction"],
                    healthy_prior_eligible=cond["condition"] == "healthy",
                    scale_available=False,
                    scale_status="ruler_present_scale_pending" if r.get("ruler_in_frame") == "yes" else "no_ruler",
                    projection="near_flat_unpressed", orientation_method=norm["orientation_method"],
                    aspect=norm["aspect"], widest_fraction=norm["widest_fraction"], area_px=int(mask.sum()),
                    points=np.round(norm["points"], 5).tolist(),
                    points_unit_area=np.round(unit_area_points(norm["points"]), 5).tolist()))
    return dict(records=records, contours=contours)


def delight(bgr: np.ndarray, mask: np.ndarray, sigma_px: float) -> np.ndarray:
    """Albedo estimate: divide by a masked low-pass illumination estimate (per channel luminance),
    rescaled to the original mean so vein colour contrast is kept and smooth shading is removed."""
    img = bgr.astype(np.float64)
    m = mask.astype(np.float64)
    lum = img.mean(axis=2) * m
    num = cv2.GaussianBlur(lum, (0, 0), sigma_px)
    den = cv2.GaussianBlur(m, (0, 0), sigma_px)
    illum = np.where(den > 1e-6, num / np.maximum(den, 1e-6), 1.0)
    out = img / np.maximum(illum, 1e-6)[:, :, None]
    scale = img[mask].mean() / max(out[mask].mean(), 1e-9)
    out = out * scale
    out[~mask] = 255
    return np.clip(out, 0, 255).astype(np.uint8)


def ruler_scale(bgr: np.ndarray, *, max_side_px: int = 1600, min_ticks: int = 15, merge_px: float = 4.0,
                min_period_px: float = 6.0) -> dict[str, Any]:
    """EXPERIMENTAL, NOT USED: px/mm from the millimetre ticks of a ruler in the photo.

    Manual check 2026-10-06 on 4 library photos: 2 correct (leaf_03, leaf_25 within 4 %), 2 wrong (leaf_01,
    leaf_15: another scale/grid on the ruler was taken). Library contours therefore keep scale_status
    'ruler_present_scale_pending'.

    Short parallel line segments (LSD) are grouped by orientation and by band across the ruler (each edge
    scale of a ruler is its own band). Both edges of one printed tick are merged. In each band the spacing
    mode is a candidate tick period; it is accepted as **1 mm** only if the long ticks of the same band are
    spaced 5x or 10x that period (half-cm / cm marks), which rejects inch scales and printed grids.
    Returned px/mm refers to the original photo resolution.
    """
    s = min(1.0, max_side_px / float(max(bgr.shape[:2])))
    img = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else bgr
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lines = cv2.createLineSegmentDetector().detect(g)[0]
    if lines is None or len(lines) < min_ticks:
        return dict(status="scale_unavailable", reason="too few line segments")
    L = lines.reshape(-1, 4)
    d = L[:, 2:] - L[:, :2]
    length = np.hypot(d[:, 0], d[:, 1])
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 180
    short = (length > 4) & (length < 0.06 * max(g.shape))
    cands = []
    for a0 in np.arange(0, 180, 2.0):
        sel = short & (np.abs(((ang - a0) + 90) % 180 - 90) < 3)
        if sel.sum() < min_ticks:
            continue
        tdir = np.array([math.cos(math.radians(a0)), math.sin(math.radians(a0))])
        axis = np.array([-tdir[1], tdir[0]])
        mid = (L[sel, :2] + L[sel, 2:]) / 2
        along, perp, ln = mid @ axis, mid @ tdir, length[sel]
        bw = 0.03 * max(g.shape)
        hist, edges = np.histogram(perp, bins=np.arange(perp.min() - bw, perp.max() + 2 * bw, bw))
        for k in np.argsort(hist)[::-1][:3]:                     # up to three bands per orientation
            if hist[k] < min_ticks:
                continue
            c = 0.5 * (edges[k] + edges[k + 1])
            band = np.abs(perp - c) < 1.5 * bw
            order = np.argsort(along[band])
            pa, pl = along[band][order], ln[band][order]
            ticks = []                                           # merge both edges of a printed tick
            for p_, l_ in zip(pa, pl):
                if ticks and p_ - ticks[-1][0][-1] < merge_px:
                    ticks[-1][0].append(p_)
                    ticks[-1][1].append(l_)
                else:
                    ticks.append(([p_], [l_]))
            pos = np.array([np.mean(t[0]) for t in ticks])
            tl = np.array([max(t[1]) for t in ticks])
            if len(pos) < min_ticks:
                continue
            diff = np.diff(pos)
            diff = diff[diff >= min_period_px]
            if len(diff) < min_ticks - 1:
                continue
            h2, e2 = np.histogram(diff, bins=np.arange(min_period_px, min(120, diff.max() + 2), 0.5))
            j = int(np.argmax(h2))
            period = 0.5 * (e2[j] + e2[j + 1])
            near = diff[np.abs(diff - period) < 0.25 * period]
            per = float(np.median(near))
            longp = np.sort(pos[tl > 1.4 * np.median(tl)])
            ld = np.diff(longp)
            ratio = None
            if len(ld) >= 2:
                for mult in (10.0, 5.0):
                    ok = np.abs(ld / per - mult) < 0.12 * mult
                    if ok.sum() >= 2:
                        ratio = mult
                        per = float(np.median(ld[ok]) / mult)            # refine with the long-tick spacing
                        break
            cands.append(dict(angle_deg=float(a0), band_center=float(c), period_px=per, n_spacings=int(len(near)),
                              spread_rel=float(np.std(near) / np.median(near)), long_tick_ratio=ratio))
    valid = [c for c in cands if c["long_tick_ratio"] and c["spread_rel"] <= 0.15]
    if not valid:
        return dict(status="scale_unavailable", reason="no tick set with a 5x/10x long-tick structure",
                    n_candidates=len(cands))
    best = max(valid, key=lambda c: c["n_spacings"])
    return dict(status="ok", px_per_mm=best["period_px"] / s, mm_per_px=s / best["period_px"], **best)
