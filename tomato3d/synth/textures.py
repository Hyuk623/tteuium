"""Addendum D step B5a: leaflet albedo texture bank from real crops.

Sources (tagged per texture):

* ``library_crop`` - healthy leaflet components of the pooled leaf library whose photo ``uses`` contains
  ``texture`` and carries no occlusion flag (one shot per rot_grid leaflet);
* ``rig_photo_crop`` - accepted human-reviewed leaflet masks on the 3024 px rig photos that look whole
  (human ``full`` or the geometric proxy: low contact, solid, single component, off the border).

Each crop is rotated so the leaflet's principal axis is horizontal with the wider (base) end on the
left, de-lit (shading divided out, vein contrast kept), normalised to a mean sRGB of 0.5, and the area
outside the (4 px eroded) leaflet is set to the leaflet's mean colour so lookups near the outline never hit the sheet.
Texture space: ``s`` along the midrib (0 base .. 1 tip), ``t`` across, centred at 0.5; ``aspect`` =
height / width of the aligned crop.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.synth.images import imread, imwrite

TEX_SIZE = (512, 256)            # width, height of every texture image
MEAN_SRGB = 0.5
#: Real rig leaf colour (BGR median of 30 rig photos, addendum_b/real_camera_stats_1280.json); every texture's mean
#: chromaticity is moved here so library photos (warmer light) and rig crops share the rig colour.
RIG_LEAF_BGR = (99.26, 147.29, 125.22)
EDGE_ERODE_PX = 4


def align_crop(bgr: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) < 200:
        return None
    pts = np.c_[xs, ys].astype(np.float64)
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    ang = np.degrees(np.arctan2(vt[0][1], vt[0][0]))
    h, w = mask.shape
    diag = int(np.ceil(np.hypot(h, w)))
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), ang, 1.0)
    M[:, 2] += [diag / 2 - c[0], diag / 2 - c[1]]
    img = cv2.warpAffine(bgr, M, (diag, diag), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))
    m = cv2.warpAffine(mask.astype(np.uint8), M, (diag, diag), flags=cv2.INTER_NEAREST) > 0
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    img, m = img[y0:y1, x0:x1], m[y0:y1, x0:x1]
    widths = m.sum(axis=0)
    half = len(widths) // 2
    if widths[half:].sum() > widths[:half].sum():          # wider half = base -> left
        img, m = img[:, ::-1], m[:, ::-1]
    return np.ascontiguousarray(img), np.ascontiguousarray(m)


def specular_mask(bgr: np.ndarray, mask: np.ndarray, rule: dict[str, Any]) -> np.ndarray:
    """Cell N (2026-10-08): specular-highlight pixels inside the leaflet = HSV value >= ``v_min`` AND saturation
    <= ``s_max`` (OpenCV 0-255 scales), grown by ``dilate_px`` to take the soft halo. ``delight`` only divides out
    low-frequency shading, so these high-frequency blobs survive it and end up in the albedo."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    spec = (hsv[:, :, 2] >= rule["v_min"]) & (hsv[:, :, 1] <= rule["s_max"]) & mask
    d = int(rule.get("dilate_px", 0))
    if d > 0 and spec.any():
        spec = cv2.dilate(spec.astype(np.uint8), np.ones((2 * d + 1,) * 2, np.uint8)).astype(bool)
    return spec & mask


def repair_specular(bgr: np.ndarray, mask: np.ndarray, rule: dict[str, Any]) -> tuple[np.ndarray, dict[str, float]]:
    """Inpaint the specular pixels from the surrounding *leaf* pixels (cv2.inpaint, Telea, ``inpaint_radius_px``).

    Everything outside the leaflet is set to the leaflet's median colour first, so the fill never draws on the paper;
    the outside is restored afterwards. Returns the repaired crop and the specular fraction before / after (share
    of leaflet pixels flagged by :func:`specular_mask`)."""
    mask = mask.astype(bool)
    spec = specular_mask(bgr, mask, rule)
    n = max(1, int(mask.sum()))
    before = float(spec.sum()) / n
    if not spec.any():
        return bgr.copy(), dict(specular_fraction_before=before, specular_fraction_after=before)
    work = bgr.copy()
    med = np.median(bgr[mask & ~spec], axis=0) if (mask & ~spec).any() else np.median(bgr[mask], axis=0)
    work[~mask] = med.astype(np.uint8)
    fixed = cv2.inpaint(work, spec.astype(np.uint8), float(rule["inpaint_radius_px"]), cv2.INPAINT_TELEA)
    out = bgr.copy()
    out[mask] = fixed[mask]
    after = float(specular_mask(out, mask, rule).sum()) / n
    return out, dict(specular_fraction_before=before, specular_fraction_after=after)


def make_texture(bgr: np.ndarray, mask: np.ndarray, delight_sigma_rel: float = 0.25,
                 specular_rule: dict[str, Any] | None = None) -> dict[str, Any] | None:
    from tomato3d.synth.leaflib import delight

    al = align_crop(bgr, mask)
    if al is None:
        return None
    img, m_full = al
    h, w = m_full.shape
    m = cv2.erode(m_full.astype(np.uint8), np.ones((2 * EDGE_ERODE_PX + 1,) * 2, np.uint8)).astype(bool)
    if m.sum() < 100:
        return None
    specular: dict[str, float] = {}
    if specular_rule is not None:                                        # cell N: repair before de-lighting
        img, specular = repair_specular(img, m_full, specular_rule)
    lit = delight(img, m, sigma_px=max(3.0, delight_sigma_rel * min(h, w))).astype(np.float64) / 255.0
    mean = lit[m].mean(axis=0)
    target = np.asarray(RIG_LEAF_BGR) / np.mean(RIG_LEAF_BGR)
    gain = np.clip(target / (mean / mean.mean()), 1 / 1.3, 1.3)        # rig chromaticity (bounded), contrast kept
    lit *= gain[None, None]
    lit *= MEAN_SRGB / max(float(lit[m].mean()), 1e-6)
    leaf_mean = lit[m].mean(axis=0)
    f = lit.copy()
    f[~m] = leaf_mean                                                    # outside the leaflet: its mean colour
    tex = cv2.resize(np.clip(f * 255, 0, 255).astype(np.uint8), TEX_SIZE, interpolation=cv2.INTER_AREA)
    sil = cv2.resize(m.astype(np.uint8) * 255, TEX_SIZE, interpolation=cv2.INTER_AREA) >= 255   # fully textured texels
    return dict(texture=tex, aspect=float(h) / float(w), height=height_map(img, m), silhouette=sil, **specular)


def height_map(img: np.ndarray, m: np.ndarray) -> np.ndarray:
    """B5b relief from shading: band-pass luminance of the *photographed* (lit) crop treated as height.

    Shape-from-shading in its simplest form: under roughly overhead light, brighter mid-frequency shading
    = raised blade between veins, darker = vein grooves / folds. Band 1-8 % of the crop width; z-scored
    inside the leaflet, mapped to 0.5 +- 0.25 (clipped at 2 sigma); flat (0.5) outside the leaflet.
    """
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float64)
    w = g.shape[1]
    s1, s2 = max(1.0, 0.01 * w), max(2.0, 0.08 * w)
    mf = m.astype(np.float64)

    def masked_blur(sig):                                     # normalised convolution: no paper in the blur
        return cv2.GaussianBlur(g * mf, (0, 0), sig) / np.maximum(cv2.GaussianBlur(mf, (0, 0), sig), 1e-6)

    band = masked_blur(s1) - masked_blur(s2)
    z = np.zeros_like(band)
    if m.any():
        z[m] = (band[m] - band[m].mean()) / max(band[m].std(), 1e-6)
    hgt = 0.5 + 0.25 * np.clip(z, -2, 2) / 2
    hgt[~m] = 0.5
    return cv2.resize((hgt * 255).astype(np.uint8), TEX_SIZE, interpolation=cv2.INTER_AREA)


#: The rig-crop rule used for texture_bank / texture_bank_v2 (B5a), formerly hard-coded here (Addendum G.2 A2): it
#: re-implements the 0.85 solidity floor refuted in Addendum G. Kept only so those banks stay reproducible.
LEGACY_B5A_RIG_RULE = dict(kind="geometric", max_contact=0.05, min_solidity=0.85, min_dominant=0.98,
                           exclude_border=True, human_full_always=True, exclude_human_partial=True)


def _rig_selected(c: dict[str, Any], rule: dict[str, Any]) -> bool:
    if rule.get("exclude_human_partial") and c.get("human_visibility") == "partial":
        return False
    if rule.get("human_full_always") and c.get("human_visibility") == "full":
        return True
    return (c["contact_fraction"] <= rule["max_contact"] and c["solidity"] >= rule["min_solidity"]
            and c["dominant_fraction"] >= rule["min_dominant"]
            and not (rule.get("exclude_border") and c["touches_border"]))


def build_bank(out_dir: Path, library_dir: Path, rig_sources: dict[str, Path], rig_images: dict[str, Path],
               c0_pool: Path, *, max_rig: int | None, seed: int, rig_rule: dict[str, Any] | None = None,
               pool_mask_ids: list[str] | None = None, specular_rule: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write ``out_dir/tex_XXX.png`` (+ ``_h`` height, ``_m`` silhouette) and ``bank.json``; return the manifest.

    Rig crops are chosen either by ``rig_rule`` (thresholds on the c0 pool metrics) or, when ``pool_mask_ids`` is
    given, exactly as the contour pool of the same cell (Addendum G.2 A2), so every pool contour has a texture built
    from the same mask. ``max_rig=None`` keeps every selected mask. ``specular_rule`` (cell N) repairs specular
    highlights in every crop before de-lighting and records the per-texture fractions.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []

    def add(bgr, mask, source, ref):
        t = make_texture(bgr, mask, specular_rule=specular_rule)
        if t is None:
            return
        stem = f"tex_{len(entries):03d}"
        imwrite(out_dir / f"{stem}.png", t["texture"])
        imwrite(out_dir / f"{stem}_h.png", t["height"])
        imwrite(out_dir / f"{stem}_m.png", t["silhouette"].astype(np.uint8) * 255)
        spec = {k: round(t[k], 5) for k in ("specular_fraction_before", "specular_fraction_after") if k in t}
        entries.append(dict(file=f"{stem}.png", height_file=f"{stem}_h.png", mask_file=f"{stem}_m.png",
                            aspect=t["aspect"], source=source, **ref, **spec,
                            sha256=hashlib.sha256((out_dir / f"{stem}.png").read_bytes()).hexdigest(),
                            height_sha256=hashlib.sha256((out_dir / f"{stem}_h.png").read_bytes()).hexdigest()))

    comps = json.loads((Path(library_dir) / "library_components.json").read_text(encoding="utf-8"))["records"]
    for r in comps:
        if (r["condition"] != "healthy" or r["level"] != "leaflet" or "texture" not in r["uses"] or r["quality_flags"]
                or (r["rotation_series"] == "rot_grid" and not r["component_id"].startswith("leaf_43"))):
            continue
        crop = imread(Path(library_dir) / r["crop"], cv2.IMREAD_COLOR)
        mask = ~np.all(crop >= 250, axis=2)
        add(crop, mask, "library_crop", dict(component_id=r["component_id"], photo=r["photo"]))
    pool = json.loads(Path(c0_pool).read_text(encoding="utf-8"))["contours"]
    if pool_mask_ids is not None:
        wanted = set(pool_mask_ids)
        whole = [c for c in pool if c["mask_id"] in wanted]
        missing = wanted - {c["mask_id"] for c in whole}
        if missing:
            raise ValueError(f"{len(missing)} pool masks are not in the c0 pool, e.g. {sorted(missing)[:3]}")
    else:
        whole = [c for c in pool if _rig_selected(c, rig_rule or LEGACY_B5A_RIG_RULE)]
    if max_rig is None or max_rig >= len(whole):
        pick = sorted(whole, key=lambda c: c["mask_id"])
    else:
        rng = np.random.default_rng(seed)
        pick = [whole[i] for i in rng.choice(len(whole), size=max_rig, replace=False)]
    for c in pick:
        export = Path(rig_sources[c["plant_id"]])
        mask_full = imread(export / f"{c['mask_id']}.png", cv2.IMREAD_GRAYSCALE) > 0
        img = imread(Path(rig_images[c["plant_id"]]) / c["image_file"], cv2.IMREAD_COLOR)
        ys, xs = np.nonzero(mask_full)
        pad = 10
        y0, y1 = max(0, ys.min() - pad), min(img.shape[0], ys.max() + pad)
        x0, x1 = max(0, xs.min() - pad), min(img.shape[1], xs.max() + pad)
        add(img[y0:y1, x0:x1], mask_full[y0:y1, x0:x1], "rig_photo_crop",
            dict(mask_id=c["mask_id"], plant_id=c["plant_id"], image_file=c["image_file"]))
    bank = dict(texture_size=list(TEX_SIZE), mean_srgb=MEAN_SRGB, n=len(entries),
                rig_selection=dict(pool_mask_ids=len(pool_mask_ids)) if pool_mask_ids is not None else
                dict(rule=rig_rule or LEGACY_B5A_RIG_RULE, max_rig=max_rig, seed=seed),
                rig_selected=len(pick),
                by_source={s: sum(e["source"] == s for e in entries) for s in ("library_crop", "rig_photo_crop")},
                **(dict(specular_rule=specular_rule, specular_fraction=dict(
                    before_mean=round(float(np.mean([e["specular_fraction_before"] for e in entries])), 5),
                    after_mean=round(float(np.mean([e["specular_fraction_after"] for e in entries])), 5)))
                   if specular_rule is not None and entries else {}),
                textures=entries)
    (out_dir / "bank.json").write_text(json.dumps(bank, indent=1), encoding="utf-8")
    return bank


# ----------------------------------------------------------------------------------- texture placement (G.2 A1)
def texture_silhouette(tex: dict[str, Any]) -> np.ndarray:
    """Fully textured texels of a bank texture (H, W bool).

    Banks built since G.2 store the eroded leaflet mask (``mask_file``). Older banks (texture_bank, _v2) do not; there
    the flat fill is recovered from the image: the fill is one constant colour (the leaflet mean), so texels within 2
    levels of the most frequent colour that connect to the image border are fill.
    """
    if tex.get("mask_path") and Path(tex["mask_path"]).exists():
        return imread(Path(tex["mask_path"]), cv2.IMREAD_GRAYSCALE) > 127
    img = imread(Path(tex["path"]), cv2.IMREAD_COLOR)
    vals, counts = np.unique(img.reshape(-1, 3), axis=0, return_counts=True)
    fill = vals[int(np.argmax(counts))].astype(int)
    near = (np.abs(img.astype(int) - fill[None, None]).max(axis=2) <= 2).astype(np.uint8)
    _, lab = cv2.connectedComponents(near, connectivity=4)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]).tolist()) - {0}
    return ~np.isin(lab, list(border))


def silhouette_profile(sil: np.ndarray) -> dict[str, Any]:
    """Per texture column: first/last textured row as t in 0..1 (NaN where the column has no texel)."""
    h, w = sil.shape
    any_ = sil.any(axis=0)
    top = sil.argmax(axis=0).astype(float)
    bot = (h - 1 - sil[::-1].argmax(axis=0)).astype(float)
    cols = np.flatnonzero(any_)
    return dict(t_top=np.where(any_, (top + 0.5) / h, np.nan), t_bot=np.where(any_, (bot + 0.5) / h, np.nan),
                s0=float((cols.min() + 0.5) / w) if len(cols) else 0.0,
                s1=float((cols.max() + 0.5) / w) if len(cols) else 1.0)


def contour_profile(contour: np.ndarray, bins: int = 128) -> dict[str, np.ndarray]:
    """Lateral extent (y_min, y_max) of a normalised contour (x 0..1) at ``bins`` x positions."""
    c = np.asarray(contour, float)
    xs = (np.arange(bins) + 0.5) / bins
    lo, hi = np.full(bins, np.nan), np.full(bins, np.nan)
    p, q = c, np.roll(c, -1, axis=0)
    for i, x in enumerate(xs):
        cross = (p[:, 0] - x) * (q[:, 0] - x) <= 0
        dx = q[cross, 0] - p[cross, 0]
        ok = np.abs(dx) > 1e-12
        if not ok.any():
            continue
        f = (x - p[cross, 0][ok]) / dx[ok]
        y = p[cross, 1][ok] + f * (q[cross, 1][ok] - p[cross, 1][ok])
        lo[i], hi[i] = y.min(), y.max()
    good = np.flatnonzero(~np.isnan(lo))
    if len(good):                                            # tips: nearest measured column
        nearest = good[np.abs(np.arange(bins)[:, None] - good[None]).argmin(axis=1)]
        lo, hi = lo[nearest], hi[nearest]
    return dict(x=xs, y_min=lo, y_max=hi)


def hash_uv(uv: np.ndarray, aspect: float) -> np.ndarray:
    """B5a placement (pre-G.2): s = x, t = 0.5 + y / aspect, regardless of either silhouette."""
    uv = np.asarray(uv, float)
    return np.c_[uv[:, 0], 0.5 + uv[:, 1] / max(aspect, 1e-6)]


def warp_uv(uv: np.ndarray, cprof: dict[str, np.ndarray], tprof: dict[str, Any], *, flip_x: bool = False,
            flip_y: bool = False) -> np.ndarray:
    """G.2 A1 placement: the contour's cross-section at x is mapped linearly onto the texture silhouette's
    cross-section at the matching column, so the outline lands on textured texels (pattern kept along the midrib)."""
    uv = np.asarray(uv, float)
    bins = len(cprof["x"])
    x = np.clip(uv[:, 0], 0.0, 1.0)
    i = np.clip((x * bins).astype(int), 0, bins - 1)
    y0, y1 = cprof["y_min"][i], cprof["y_max"][i]
    frac = np.clip((uv[:, 1] - y0) / np.maximum(y1 - y0, 1e-9), 0.0, 1.0)
    if flip_y:
        frac = 1.0 - frac
    xs = 1.0 - x if flip_x else x
    s = tprof["s0"] + xs * (tprof["s1"] - tprof["s0"])
    tt, tb = tprof["t_top"], tprof["t_bot"]
    w = len(tt)
    j = np.clip((s * w).astype(int), 0, w - 1)
    valid = np.flatnonzero(~np.isnan(tt))
    if len(valid):
        j = valid[np.abs(j[:, None] - valid[None]).argmin(axis=1)]
    return np.c_[s, tt[j] + frac * (tb[j] - tt[j])]


def flat_fill_fraction(contour: np.ndarray, uv_fn, sil: np.ndarray, grid: tuple[int, int] = (160, 80)) -> float:
    """Share of the leaflet's area whose texture lookup lands outside the textured silhouette (flat mean fill)."""
    c = np.asarray(contour, float)
    x0, x1, y0, y1 = c[:, 0].min(), c[:, 0].max(), c[:, 1].min(), c[:, 1].max()
    gw, gh = grid
    poly = np.c_[(c[:, 0] - x0) / max(x1 - x0, 1e-9) * (gw - 1), (c[:, 1] - y0) / max(y1 - y0, 1e-9) * (gh - 1)]
    raster = np.zeros((gh, gw), np.uint8)
    cv2.fillPoly(raster, [np.round(poly * 8).astype(np.int32)], 1, shift=3)
    gy, gx = np.nonzero(raster)
    pts = np.c_[x0 + gx / (gw - 1) * (x1 - x0), y0 + gy / (gh - 1) * (y1 - y0)]
    inside = np.ones(len(pts), bool)
    if not inside.any():
        return float("nan")
    st = uv_fn(pts[inside])
    h, w = sil.shape
    off = (st[:, 0] < 0) | (st[:, 0] > 1) | (st[:, 1] < 0) | (st[:, 1] > 1)
    j = np.clip((st[:, 0] * w).astype(int), 0, w - 1)
    i = np.clip((st[:, 1] * h).astype(int), 0, h - 1)
    return float(np.mean(off | ~sil[i, j]))
