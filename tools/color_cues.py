"""Image-intrinsic colour and brightness cues for leaflet detections and masks (2026-10-04).

Handoff: handoff/CLAUDE_CODE_COLOR_CUE_DETECTION_PROMPT_2026-10-03.md. No learned model and no new labels: every function
here is photometric or morphological and keeps the original pixel grid. Formulas are reused from the existing helpers
instead of copied:

* chromatic coordinates r, g, b = channel / (R + G + B): ``tools.leaf_preprocess_lab.colour_ratios`` on stored 8-bit
  values (basis ``stored``) or on linearised sRGB (basis ``linear``, ``tools.leaf_preprocess_lab.linear_rgb``);
* grayworld: ``tools.rgb_ratio_batch.grayworld``; Lab-L CLAHE and gauss5: ``tools.preprocess_study.process_rgb``.

New here: ExG = 2g - r - b, ExR = 1.4r - g, ExG - ExR, Lab L*/a* in CIE units, HSV hue/saturation, a white balance
from the ChArUco board's white marker margins (detected markers, no pose needed), two vegetation masks
(ExG - ExR > 0, Otsu on ExG), mask trimming that can only remove pixels, per-mask colour features and a
leave-one-plant-out parameter selector that never reads the held-out plant.

Vegetation masks are evidence for filtering, never ground truth. Everything is opt-in: nothing in the pipeline calls
this module unless a flag asks for it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np

from tools import leaf_preprocess_lab as lab

ROOT = Path(__file__).resolve().parents[1]
NORMALIZATIONS = ('none', 'grayworld', 'board_wb', 'clahe', 'gauss5')
VEG_METHODS = ('exgr_zero', 'exg_otsu')
EXG_RANGE = (-1.0, 2.0)          # ExG = 2g - r - b with r + g + b = 1 lies in [-1, 2]
CLIPPED_8BIT = 250               # a white-balance sample with any channel at/above this is saturated
DARK_8BIT = 40                   # ... and one whose brightest channel is below this is too dark to carry colour
#: White-margin ring sampled around each detected marker, in marker half-widths (marker edge = 1.0). The square edge
#: sits at square_size / marker_size; the ring keeps a safety gap on both sides.
WB_RING_INNER = 1.10
WB_RING_OUTER_GAP = 0.08         # stay this far (marker half-widths) inside the square edge
WB_MIN_PIXELS = 200
#: A vegetation mask covering more than this share of the photo is degenerate (2026-10-04: Otsu on ExG split the
#: board's black/white squares instead of plant/background in 20-23 of 62 photos; the plant fills ~5 % of a frame).
VEG_DEGENERATE_FRACTION = 0.5


# ---------------------------------------------------------------------------------------------------------------- maps
def chromatic(rgb: np.ndarray, basis: str = 'stored') -> tuple[np.ndarray, np.ndarray]:
    """H x W x 3 float32 fractions channel/(R+G+B) and the H x W validity mask (sum > 0)."""
    if basis == 'stored':
        frac, valid = lab.colour_ratios(np.asarray(rgb, np.float32))
    elif basis == 'linear':
        frac, valid = lab.colour_ratios(lab.linear_rgb(rgb))
    else:
        raise ValueError(f'unknown basis {basis!r}')
    return frac.astype(np.float32, copy=False), valid


def vegetation_indices(rgb: np.ndarray, basis: str = 'stored') -> dict[str, np.ndarray]:
    """ExG, ExR and ExG - ExR from chromatic coordinates; 0 where R+G+B = 0 (recorded in 'valid')."""
    frac, valid = chromatic(rgb, basis)
    r, g, b = frac[..., 0], frac[..., 1], frac[..., 2]
    exg = 2 * g - r - b
    exr = 1.4 * r - g
    return dict(r=r, g=g, b=b, exg=exg, exr=exr, exgr=exg - exr, valid=valid)


def lab_lightness_a(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """CIE L* (0..100) and a* from OpenCV's 8-bit Lab (L scaled by 255/100, a offset by 128)."""
    lab8 = cv2.cvtColor(np.ascontiguousarray(rgb, np.uint8), cv2.COLOR_RGB2LAB)
    return lab8[..., 0].astype(np.float32) * (100.0 / 255.0), lab8[..., 1].astype(np.float32) - 128.0


def hue_saturation(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Hue in degrees (0..360) and saturation (0..1) from OpenCV's 8-bit HSV."""
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb, np.uint8), cv2.COLOR_RGB2HSV)
    return hsv[..., 0].astype(np.float32) * 2.0, hsv[..., 1].astype(np.float32) / 255.0


# ------------------------------------------------------------------------------------------------------- normalisation
def board_spec_ratio(spec_path: Path | None = None) -> float:
    """square_size_mm / marker_size_mm of a board spec JSON (default: the session's configured board)."""
    spec = json.loads(Path(spec_path or ROOT / 'config' / 'board_spec.json').read_text(encoding='utf-8'))
    return float(spec['square_size_mm']) / float(spec['marker_size_mm'])


def board_white_gains(rgb: np.ndarray, square_to_marker: float, aruco_dict: str = 'DICT_4X4_50') -> dict:
    """Per-channel gains (linear sRGB) that make the board's white marker margins neutral.

    Uses the ArUco markers the photo itself shows, so no pose is needed: for each detected marker the white margin
    between the marker edge and its square edge is sampled through the marker's homography. Saturated, too dark and
    green (ExG - ExR > 0, leaves over the board) samples are dropped. Gains keep the mean of the three channel
    medians, so overall brightness is unchanged. Returns gains None when fewer than WB_MIN_PIXELS samples survive.
    """
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, aruco_dict)),
                                  cv2.aruco.DetectorParameters())
    gray = cv2.cvtColor(np.ascontiguousarray(rgb, np.uint8), cv2.COLOR_RGB2GRAY)
    corners, ids, _ = det.detectMarkers(gray)
    outer = square_to_marker - WB_RING_OUTER_GAP
    g = np.linspace(-outer, outer, 41)
    uu, vv = np.meshgrid(g, g)
    ring = (np.maximum(np.abs(uu), np.abs(vv)) >= WB_RING_INNER)
    unit = np.c_[uu[ring], vv[ring]].astype(np.float32)
    H, W = rgb.shape[:2]
    samples = []
    for c in (corners or []):
        quad = c.reshape(4, 2).astype(np.float32)
        hom = cv2.getPerspectiveTransform(np.float32([[-1, -1], [1, -1], [1, 1], [-1, 1]]), quad)
        pts = cv2.perspectiveTransform(unit[None], hom)[0]
        xi, yi = np.round(pts[:, 0]).astype(int), np.round(pts[:, 1]).astype(int)
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        samples.append(rgb[yi[ok], xi[ok]])
    n_markers = 0 if ids is None else int(len(ids))
    if not samples:
        return dict(gains=None, n_markers=n_markers, n_pixels=0, reason='no markers detected')
    px = np.concatenate(samples).astype(np.uint8)
    keep = (px.max(1) < CLIPPED_8BIT) & (px.max(1) >= DARK_8BIT)
    veg = vegetation_indices(px[None])['exgr'][0] > 0
    px = px[keep & ~veg]
    if len(px) < WB_MIN_PIXELS:
        return dict(gains=None, n_markers=n_markers, n_pixels=int(len(px)), reason='too few white-margin samples')
    med = np.median(lab.linear_rgb(px[None])[0], axis=0)
    gains = med.mean() / np.maximum(med, 1e-6)
    return dict(gains=[float(x) for x in gains], n_markers=n_markers, n_pixels=int(len(px)),
                median_linear=[float(x) for x in med], reason=None)


def apply_gains(rgb: np.ndarray, gains: Iterable[float]) -> np.ndarray:
    """Von Kries white balance in linear sRGB, re-encoded to 8-bit sRGB on the same grid."""
    return lab.encode_rgb(lab.linear_rgb(rgb) * np.asarray(list(gains), np.float32))


def grayworld_gains(rgb: np.ndarray) -> list[float]:
    """The per-channel gains tools.rgb_ratio_batch.grayworld applies to this image (stored 8-bit basis)."""
    means = np.asarray(rgb, np.float32).reshape(-1, 3).mean(0)
    return [float(x) for x in means.mean() / np.maximum(means, 1e-6)]


def normalize(rgb: np.ndarray, method: str, gains: Iterable[float] | None = None) -> np.ndarray:
    """Photometric normalisation; same shape and pixel grid. 'board_wb' needs gains from board_white_gains.
    'grayworld' uses the image's own means unless gains (from grayworld_gains of the whole photo) are given, so a
    crop can carry its photo's normalisation."""
    if method == 'none':
        return rgb
    if method == 'grayworld':
        if gains is not None:
            x = np.asarray(rgb, np.float32) * np.asarray(list(gains), np.float32)
            return np.clip(np.rint(x), 0, 255).astype(np.uint8)
        from tools.rgb_ratio_batch import grayworld
        return grayworld(rgb)
    if method == 'board_wb':
        if gains is None:
            raise ValueError('board_wb needs gains (board_white_gains returned none for this photo)')
        return apply_gains(rgb, gains)
    from tools.preprocess_study import process_rgb
    if method == 'clahe':
        return process_rgb(np.ascontiguousarray(rgb, np.uint8), 'none', 'clahe15')
    if method == 'gauss5':
        return process_rgb(np.ascontiguousarray(rgb, np.uint8), 'gauss5', 'none')
    raise ValueError(f'unknown normalisation {method!r}')


# ------------------------------------------------------------------------------------------------------ vegetation mask
def vegetation_mask(rgb: np.ndarray, method: str = 'exgr_zero') -> tuple[np.ndarray, dict]:
    """Per-photo vegetation mask, no learned model. exgr_zero: ExG - ExR > 0 (Meyer & Neto 2008 zero threshold);
    exg_otsu: Otsu threshold on ExG over pixels with R+G+B > 0. Returns (bool mask, info with the threshold used, the
    covered fraction and a 'degenerate' flag when it exceeds VEG_DEGENERATE_FRACTION). The mask itself is unchanged;
    consumers decide what to do with a degenerate one."""
    veg, info = _vegetation_mask(rgb, method)
    frac = float(veg.mean()) if veg.size else 0.0
    return veg, dict(info, fraction=round(frac, 5), degenerate=frac > VEG_DEGENERATE_FRACTION)


def _vegetation_mask(rgb: np.ndarray, method: str) -> tuple[np.ndarray, dict]:
    ix = vegetation_indices(rgb)
    if method == 'exgr_zero':
        return (ix['exgr'] > 0) & ix['valid'], dict(method=method, index='ExG-ExR', threshold=0.0)
    if method == 'exg_otsu':
        lo, hi = EXG_RANGE
        q = np.clip(np.rint((ix['exg'][ix['valid']] - lo) / (hi - lo) * 255), 0, 255).astype(np.uint8)
        if q.size == 0:
            return np.zeros(rgb.shape[:2], bool), dict(method=method, index='ExG', threshold=None)
        t8, _ = cv2.threshold(q.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        t = lo + float(t8) / 255 * (hi - lo)
        return (ix['exg'] > t) & ix['valid'], dict(method=method, index='ExG', threshold=round(t, 5))
    raise ValueError(f'unknown vegetation method {method!r}')


# ----------------------------------------------------------------------------------------------- crop-local mask tools
def crop_view(full: np.ndarray, left: int, top: int, height: int, width: int, fill=False) -> np.ndarray:
    """The full-frame array under a crop-local mask placed at (left, top); outside the frame is `fill`."""
    out = np.full((height, width) + full.shape[2:], fill, full.dtype)
    H, W = full.shape[:2]
    x0, y0, x1, y1 = max(0, left), max(0, top), min(W, left + width), min(H, top + height)
    if x1 > x0 and y1 > y0:
        out[y0 - top:y1 - top, x0 - left:x1 - left] = full[y0:y1, x0:x1]
    return out


def disk(radius_px: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius_px + 1,) * 2)


def dilate(mask: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0:
        return mask.astype(bool)
    return cv2.dilate(mask.astype(np.uint8), disk(radius_px)).astype(bool)


def trim_mask(mask: np.ndarray, veg: np.ndarray, radius_px: int) -> np.ndarray:
    """Arm B: mask AND (vegetation dilated by radius_px). Can only remove pixels, never add one."""
    if mask.shape != veg.shape:
        raise ValueError('mask and vegetation mask must have the same shape')
    out = mask.astype(bool) & dilate(veg, radius_px)
    assert not (out & ~mask.astype(bool)).any()
    return out


def large_components(mask: np.ndarray, min_fraction: float) -> int:
    """Number of 8-connected components holding at least min_fraction of the mask's pixels."""
    m = mask.astype(np.uint8)
    total = int(m.sum())
    if total == 0:
        return 0
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    return int(sum(1 for k in range(1, n) if stats[k, cv2.CC_STAT_AREA] >= min_fraction * total))


def mask_features(mask: np.ndarray, veg: np.ndarray, maps: dict[str, np.ndarray], ring_px: int) -> dict:
    """Colour features of one mask (all arrays crop-local, same shape): vegetation overlap ('green fraction'),
    mean ExG / ExG-ExR / a* / L* inside, and ExG contrast = mean ExG inside - mean ExG in a ring_px band outside."""
    m = mask.astype(bool)
    n = int(m.sum())
    if n == 0:
        return dict(pixels=0, green_fraction=np.nan, mean_exg=np.nan, mean_exgr=np.nan, mean_a=np.nan, mean_L=np.nan,
                    exg_contrast=np.nan)
    ring = dilate(m, ring_px) & ~m
    exg = maps['exg']
    return dict(pixels=n, green_fraction=float((m & veg).sum() / n), mean_exg=float(exg[m].mean()),
                mean_exgr=float(maps['exgr'][m].mean()), mean_a=float(maps['a'][m].mean()), mean_L=float(maps['L'][m].mean()),
                exg_contrast=float(exg[m].mean() - exg[ring].mean()) if ring.any() else np.nan)


def feature_maps(rgb: np.ndarray) -> dict[str, np.ndarray]:
    """Float32 maps used by mask_features (ExG, ExG-ExR, a*, L*); same grid as rgb."""
    ix = vegetation_indices(rgb)
    L, a = lab_lightness_a(rgb)
    return dict(exg=ix['exg'], exgr=ix['exgr'], a=a, L=L)


# ------------------------------------------------------------------------------------------------ LOPO selection
def lopo_select(score: Callable[[object, list[str]], float], params: Iterable, plants: Iterable[str]) -> dict:
    """Leave-one-plant-out parameter choice. For each held-out plant, the parameter minimising score(param, train)
    is chosen where train = the other plants; score never receives the held-out plant. Ties keep the earlier param
    (list params from the most conservative, e.g. 'off', first)."""
    plants, params = list(plants), list(params)
    out = {}
    for held in plants:
        train = [p for p in plants if p != held]
        vals = [(score(p, train), i) for i, p in enumerate(params)]
        best = min(vals, key=lambda v: (v[0], v[1]))
        out[held] = dict(param=params[best[1]], train_plants=train, train_score=float(best[0]))
    return out


# ------------------------------------------------------------------------------------------------ packing helpers
def pack(mask: np.ndarray) -> dict:
    """Bit-packed bool mask for npz storage (shape + packed bytes)."""
    m = np.asarray(mask, bool)
    return dict(shape=np.array(m.shape, np.int32), bits=np.packbits(m, axis=None))


def unpack(shape: np.ndarray, bits: np.ndarray) -> np.ndarray:
    h, w = (int(x) for x in shape)
    return np.unpackbits(bits, count=h * w).reshape(h, w).astype(bool)
