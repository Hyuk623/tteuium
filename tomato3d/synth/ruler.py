"""Ruler scale from the ruler's full short-edge width (Addendum I.4), with a tick-period cross-check.

The ruler is transparent plastic with a metal strip on one long edge; the user-stated width, 3.0 cm, runs from the
outer edge of the metal to the outer edge of the plastic, i.e. between the two outermost long edges. Steps:

1. Ruler axis: length-weighted mode of long LSD segment orientations (the long edges and grid lines run along it).
2. Rotate so the axis is horizontal; the ruler band is the densest cluster of long horizontal segments.
3. Each outer edge is localised column by column from the outer intensity transition to the background (searching
   inward from the paper, so a specular highlight inside the metal strip is never reached first), then fitted as a
   straight line with iterative 3-sigma clipping. Width = perpendicular separation of the two lines at the band
   centre; px/cm = width / 3.0.
4. Cross-check: the millimetre tick period along the tick edge, from the autocorrelation of the band just inside the
   plastic edge. Reported side by side; the width scale is adopted only where the two agree.
"""
from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

RULER_WIDTH_CM = 3.0
#: a straight outer edge carries the same-sign gradient on most ruler columns (true edges 0.62-1.0 on leaf_03/33;
#: a row of leaves beside the ruler 0.26-0.36)
COVERAGE_MIN = 0.55


def _long_segments(gray: np.ndarray, min_frac: float) -> np.ndarray:
    lines = cv2.createLineSegmentDetector().detect(gray)[0]
    if lines is None:
        return np.zeros((0, 4))
    L = lines.reshape(-1, 4)
    ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    return L[ln >= min_frac * max(gray.shape)]


def ruler_axis_deg(gray: np.ndarray) -> float | None:
    L = _long_segments(gray, 0.08)
    if len(L) < 3:
        return None
    ang = np.degrees(np.arctan2(L[:, 3] - L[:, 1], L[:, 2] - L[:, 0])) % 180
    ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    h = np.zeros(180)
    np.add.at(h, np.round(ang).astype(int) % 180, ln)
    h = h + np.roll(h, 1) + np.roll(h, -1)
    a0 = float(np.argmax(h))
    sel = np.abs(((ang - a0) + 90) % 180 - 90) < 2
    d = ((ang[sel] - a0 + 90) % 180) - 90
    return float((a0 + np.average(d, weights=ln[sel])) % 180)


def _rotate(img: np.ndarray, angle_deg: float):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    c, s = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * s + w * c), int(h * c + w * s)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    valid = cv2.warpAffine(np.full((h, w), 255, np.uint8), M, (nw, nh), flags=cv2.INTER_NEAREST) > 0
    return cv2.warpAffine(img, M, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), valid, M


def _band(gray_r: np.ndarray, valid: np.ndarray) -> dict[str, Any] | None:
    """Densest cluster of long horizontal segments -> ruler band rows and column extent."""
    L = _long_segments(gray_r, 0.06)
    if len(L) == 0:
        return None
    ang = np.degrees(np.arctan2(L[:, 3] - L[:, 1], L[:, 2] - L[:, 0])) % 180
    L = L[np.abs(((ang + 90) % 180) - 90) < 1.5]
    if len(L) < 2:
        return None
    y = (L[:, 1] + L[:, 3]) / 2
    ln = np.abs(L[:, 2] - L[:, 0])
    o = np.argsort(y)
    y, ln, L = y[o], ln[o], L[o]
    gap = 0.035 * max(gray_r.shape)                      # < ~0.6 cm at typical framing; grid lines are <= 0.5 cm apart
    groups, cur = [], [0]
    for i in range(1, len(y)):
        if y[i] - y[i - 1] <= gap:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)
    g = max(groups, key=lambda idx: ln[idx].sum())
    x0 = float(np.percentile(np.minimum(L[g, 0], L[g, 2]), 10))
    x1 = float(np.percentile(np.maximum(L[g, 0], L[g, 2]), 90))
    # Row coherence of horizontal edges over the ruler's columns: straight long edges (outer edges, grid lines,
    # tick-tip rows) give peaks; leaf outlines and paper do not. Grow from the seed rows outward while the next
    # coherent row lies within ``grow_gap`` (inside the plastic, coherent rows are <= ~0.5 cm apart).
    gs = cv2.GaussianBlur(gray_r.astype(np.float32), (0, 0), 1.0)
    gy = cv2.Sobel(gs, cv2.CV_32F, 0, 1, ksize=3)
    xi0, xi1 = int(x0), int(x1)
    vb = valid[:, xi0:xi1]
    cols_ok = vb.mean(axis=1) >= 0.7                       # rows mostly inside the original frame
    gyb = np.where(vb, gy[:, xi0:xi1], 0.0)
    signed = gyb.sum(axis=1) / np.maximum(vb.sum(axis=1), 1)
    A = np.abs(signed) * cols_ok
    noise = np.median(A[cols_ok]) + 6 * 1.4826 * np.median(np.abs(A[cols_ok] - np.median(A[cols_ok])))
    peaks = np.flatnonzero((A > noise) & (A >= np.roll(A, 1)) & (A >= np.roll(A, -1)))
    if len(peaks) == 0:
        return None
    lo_y, hi_y = float(y[g].min()), float(y[g].max())
    # The seed is the ruler's block of evenly spaced long lines; their spacing sets the growth gap (6 spacings),
    # which only decides which straight edges belong to the ruler - the width itself is measured from the edges.
    sp = peaks[(peaks >= lo_y - 2) & (peaks <= hi_y + 2)]
    sp = sp[A[sp] >= 0.5 * A[sp].max()] if len(sp) else sp
    merged = []
    for p in sp:
        if merged and p - merged[-1] <= 4:
            continue
        merged.append(p)
    spacing = float(np.median(np.diff(merged))) if len(merged) >= 3 else None
    grow_gap = 6 * spacing if spacing else 0.05 * max(gray_r.shape)
    changed = True
    while changed:
        changed = False
        up = peaks[(peaks < lo_y) & (peaks >= lo_y - grow_gap)]
        dn = peaks[(peaks > hi_y) & (peaks <= hi_y + grow_gap)]
        if len(up):
            lo_y, changed = float(up.min()), True
        if len(dn):
            hi_y, changed = float(dn.max()), True

    # A real outer edge runs along nearly all ruler columns; a row of leaves lined up beside the ruler gives a
    # coherent peak from a minority of columns. Walk back inward past such low-coverage rows.
    def coverage(row):                                     # share of in-frame columns carrying the edge, same sign
        r = int(row)
        return float((gyb[r][vb[r]] * np.sign(signed[r]) >= 0.5 * A[r]).mean())
    inside = peaks[(peaks >= lo_y - 1) & (peaks <= hi_y + 1)]
    cov = {int(p): coverage(p) for p in inside}
    seed_lo, seed_hi = float(y[g].min()), float(y[g].max())
    for p in inside:                                       # top: first high-coverage peak from the outside
        if cov[int(p)] >= COVERAGE_MIN or p >= seed_lo:
            lo_y = float(p)
            break
    for p in inside[::-1]:
        if cov[int(p)] >= COVERAGE_MIN or p <= seed_hi:
            hi_y = float(p)
            break
    return dict(y_min=lo_y, y_max=hi_y, edge_coverage=[cov.get(int(lo_y)), cov.get(int(hi_y))], x0=x0, x1=x1, n_lines=len(g), seed_rows=[float(y[g].min()), float(y[g].max())],
                coherence_noise=float(noise), seed_line_spacing_px=spacing, grow_gap_px=grow_gap)


def _edge_points(gray_r: np.ndarray, valid: np.ndarray, band: dict, side: str, search_px: float):
    """Per column: outermost strong transition to the background, searched from the paper inward."""
    g = cv2.GaussianBlur(gray_r.astype(np.float32), (0, 0), 1.2)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    h = gray_r.shape[0]
    xs, ys = [], []
    y_edge = band['y_min'] if side == 'top' else band['y_max']
    lo = int(max(1, y_edge - search_px)); hi = int(min(h - 2, y_edge + search_px))
    for x in range(int(band['x0']), int(band['x1']), 2):
        col = np.abs(gy[lo:hi, x])
        if not valid[lo:hi, x].all() or col.size < 5:
            continue
        thr = 0.35 * col.max()
        if col.max() < 8:
            continue
        idx = np.flatnonzero(col >= thr)
        k = idx[0] if side == 'top' else idx[-1]          # outermost = first from paper side
        # walk to the local maximum of that peak, then parabolic sub-pixel refinement
        step = 1
        while 0 < k + step < col.size - 1 and col[k + step] > col[k]:
            k += step
        while 0 < k - step < col.size - 1 and col[k - step] > col[k]:
            k -= step
        if 0 < k < col.size - 1:
            a, b, c = col[k - 1], col[k], col[k + 1]
            off = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        else:
            off = 0.0
        xs.append(x); ys.append(lo + k + off)
    return np.array(xs, float), np.array(ys, float)


def _robust_line(x, y, n_iter=6):
    keep = np.ones(len(x), bool)
    for _ in range(n_iter):
        if keep.sum() < 10:
            return None
        p = np.polyfit(x[keep], y[keep], 1)
        r = y - np.polyval(p, x)
        s = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep])))
        new = np.abs(r) <= max(3 * s, 0.5)
        if (new == keep).all():
            break
        keep = new
    r = (y - np.polyval(p, x))[keep]
    return dict(slope=float(p[0]), intercept=float(p[1]), rms_px=float(np.sqrt(np.mean(r ** 2))),
                n_used=int(keep.sum()), n_total=len(x), inlier_frac=float(keep.mean()))


def _parabolic(v: np.ndarray, k: int) -> float:
    """Sub-sample offset of a peak at k, clamped to +-0.5."""
    if not 0 < k < len(v) - 1:
        return 0.0
    a, b, c = v[k - 1], v[k], v[k + 1]
    d = a - 2 * b + c
    return float(np.clip(0.5 * (a - c) / d, -0.5, 0.5)) if d != 0 else 0.0


def _tick_period(gray_r: np.ndarray, band: dict, y_tick_edge: float, inward: int, width_px: float) -> dict[str, Any]:
    """Millimetre period from the autocorrelation of the tick band along the ruler axis."""
    depth = 0.12 * width_px
    y0, y1 = sorted((y_tick_edge + inward * 0.02 * width_px, y_tick_edge + inward * depth))
    y0, y1 = int(max(0, y0)), int(min(gray_r.shape[0], y1))
    x0, x1 = int(band['x0']), int(band['x1'])
    if y1 - y0 < 3 or x1 - x0 < 50:
        return dict(status='unreadable', reason='tick band too small')
    prof = gray_r[y0:y1, x0:x1].astype(np.float64).mean(axis=0)
    prof = prof - cv2.GaussianBlur(prof.reshape(1, -1), (0, 0), max(3.0, width_px / 15)).ravel()
    prof = prof - prof.mean()
    n = len(prof)
    ac = np.correlate(prof, prof, 'full')[n - 1:]
    ac = ac / ac[0] if ac[0] > 0 else ac
    expect = width_px / 30.0                                 # 1 mm if the width scale is right
    lo, hi = int(max(3, 0.5 * expect)), int(min(n // 4, 1.6 * expect))
    if hi <= lo + 2:
        return dict(status='unreadable', reason='profile too short')
    k = lo + int(np.argmax(ac[lo:hi]))
    if not (0 < k < n - 1):
        return dict(status='unreadable', reason='no peak')
    period = k + _parabolic(ac, k)
    # refine on the 10 mm (cm tick) lag, ten times longer -> ten times finer
    k10 = int(round(10 * period))
    w = max(2, int(0.6 * period))
    if k10 - w >= 1 and k10 + w + 2 < n // 2:
        j = k10 - w + int(np.argmax(ac[k10 - w:k10 + w + 1]))
        p10 = (j + _parabolic(ac, j)) / 10
        peak10 = float(ac[j])
    else:
        p10, peak10 = None, None
    peak1 = float(ac[k])
    readable = peak1 >= 0.3 and p10 is not None and peak10 >= 0.2 and abs(p10 - period) / period < 0.05
    return dict(status='readable' if readable else 'unreadable', period_1mm_px=float(period),
                period_from_10mm_px=p10, ac_peak_1mm=peak1, ac_peak_10mm=peak10,
                px_per_cm=float(10 * (p10 if readable else period)), tick_band_rows=[y0, y1], columns=[x0, x1])


def _tick_obliquity(gray_r: np.ndarray, band: dict, rows: list[int]) -> float | None:
    """Median deviation of the printed ticks from perpendicular to the fitted edges (camera obliquity proxy)."""
    y0, y1 = rows
    x0, x1 = int(band['x0']), int(band['x1'])
    pad = max(2, (y1 - y0) // 2)
    crop = gray_r[max(0, y0 - pad):y1 + pad, x0:x1]
    if crop.size == 0:
        return None
    L = cv2.createLineSegmentDetector().detect(crop)[0]
    if L is None:
        return None
    L = L.reshape(-1, 4)
    d = L[:, 2:] - L[:, :2]
    ang = np.degrees(np.arctan2(np.abs(d[:, 1]), d[:, 0] * np.sign(d[:, 1] + 1e-9)))   # 90 = perpendicular
    ln = np.hypot(d[:, 0], d[:, 1])
    sel = (np.abs(ang - 90) < 20) & (ln >= 0.5 * (y1 - y0))
    return float(np.median(ang[sel] - 90)) if sel.sum() >= 10 else None


def measure(bgr: np.ndarray, *, work_side: int = 2000, parallel_tol_deg: float = 1.0) -> dict[str, Any]:
    """Per-photo ruler scale. Returns px/cm at the ORIGINAL resolution of ``bgr``."""
    s = min(1.0, work_side / float(max(bgr.shape[:2])))
    img = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else bgr
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    axis = ruler_axis_deg(gray)
    if axis is None:
        return dict(status='no_ruler_axis')
    gr, valid, M = _rotate(gray, axis)
    band = _band(gr, valid)
    if band is None:
        return dict(status='no_ruler_band', axis_deg=axis)
    span = band['y_max'] - band['y_min']
    search = max(5.0, 0.05 * span)
    fits = {}
    for side in ('top', 'bottom'):
        x, y = _edge_points(gr, valid, band, side, search)
        fits[side] = _robust_line(x, y) if len(x) >= 10 else None
    if fits['top'] is None or fits['bottom'] is None:
        return dict(status='edge_fit_failed', axis_deg=axis, band=band)
    xc = 0.5 * (band['x0'] + band['x1'])
    yt = fits['top']['slope'] * xc + fits['top']['intercept']
    yb = fits['bottom']['slope'] * xc + fits['bottom']['intercept']
    mean_slope = 0.5 * (fits['top']['slope'] + fits['bottom']['slope'])
    width_work = abs(yb - yt) * math.cos(math.atan(mean_slope))
    angle_between = abs(math.degrees(math.atan(fits['top']['slope']) - math.atan(fits['bottom']['slope'])))
    # Beyond each outer edge there must be paper: a ruler cut by the frame, or an edge that is really the inner side
    # of the metal strip, or a table edge, fails here and the photo is marked unusable rather than mis-scaled.
    paper = float(np.percentile(gr[valid], 75))
    m = max(4, int(0.06 * width_work))                      # ~1.8 mm of paper must be in frame beyond each edge
    xa, xb = int(band['x0']), int(band['x1'])
    beyond = {}
    for side, ye in (('top', yt), ('bottom', yb)):
        r0, r1 = (int(ye) - m, int(ye) - 2) if side == 'top' else (int(ye) + 3, int(ye) + m + 1)
        if r0 < 0 or r1 > gr.shape[0] or r1 <= r0 or valid[r0:r1, xa:xb].mean() < 0.95:
            beyond[side] = dict(ok=False, reason='frame_border')
            continue
        med = float(np.median(gr[r0:r1, xa:xb][valid[r0:r1, xa:xb]]))
        beyond[side] = dict(ok=med >= 0.8 * paper, median_rel_paper=round(med / paper, 3),
                            reason=None if med >= 0.8 * paper else 'not_paper_beyond_edge')
    # which side carries the metal strip: the darker band just inside each edge
    inner = max(3, int(0.06 * width_work))
    dark_top = float(np.median(gr[int(yt) + 2:int(yt) + 2 + inner, int(band['x0']):int(band['x1'])]))
    dark_bot = float(np.median(gr[int(yb) - 2 - inner:int(yb) - 2, int(band['x0']):int(band['x1'])]))
    metal_side = 'top' if dark_top < dark_bot else 'bottom'
    tick_side = 'bottom' if metal_side == 'top' else 'top'
    tick = _tick_period(gr, band, yb if tick_side == 'bottom' else yt, -1 if tick_side == 'bottom' else 1, width_work)
    px_per_cm_width = width_work / RULER_WIDTH_CM / s
    obliq = _tick_obliquity(gr, band, tick['tick_band_rows']) if 'tick_band_rows' in tick else None
    # Plastic beyond a frame cut looks like paper, so an edge is also required to have the printed tick band right
    # inside it on the tick side (presence only: the tick period is not used here).
    tick_present = tick.get('ac_peak_1mm', 0.0) >= 0.3
    status = ('ok' if beyond['top']['ok'] and beyond['bottom']['ok'] and tick_present else
              'edge_not_on_paper' if not (beyond['top']['ok'] and beyond['bottom']['ok']) else 'no_tick_band_at_edge')
    out = dict(status=status, beyond_edge=beyond, tick_band_present=tick_present, work_scale=s, axis_deg=axis, band=band, edges=fits, metal_side=metal_side,
               width_px=width_work / s, px_per_cm_width=px_per_cm_width,
               edge_angle_between_deg=angle_between, tick_vs_edge_deviation_deg=obliq, parallel_ok=angle_between <= parallel_tol_deg,
               max_edge_rms_px=max(fits['top']['rms_px'], fits['bottom']['rms_px']) / s,
               edge_inlier_frac_min=min(fits['top']['inlier_frac'], fits['bottom']['inlier_frac']),
               visible_length_px=(band['x1'] - band['x0']) / s, tick=tick, _rot=dict(M=M.tolist(), yt=yt, yb=yb, xc=xc))
    if tick.get('status') == 'readable':
        out['px_per_cm_tick'] = tick['px_per_cm'] / s
        out['width_vs_tick_pct'] = 100 * (px_per_cm_width - out['px_per_cm_tick']) / out['px_per_cm_tick']
    return out


def overlay(bgr: np.ndarray, res: dict[str, Any]) -> np.ndarray:
    """Draw the two fitted edges (and 1 cm marks from the width scale) back on the photo, for visual QA."""
    s = res['work_scale']
    img = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else bgr.copy()
    Minv = cv2.invertAffineTransform(np.array(res['_rot']['M']))
    b = res['band']
    for side, col in (('top', (0, 0, 255)), ('bottom', (255, 0, 0))):
        f = res['edges'][side]
        pts = np.array([[x, f['slope'] * x + f['intercept']] for x in (b['x0'], b['x1'])], np.float32)
        p = cv2.transform(pts[None], Minv)[0]
        cv2.line(img, tuple(map(int, p[0])), tuple(map(int, p[1])), col, 2)
    step = res['px_per_cm_width'] * s
    yt, yb = res['_rot']['yt'], res['_rot']['yb']
    x = b['x0']
    while x <= b['x1']:
        p = cv2.transform(np.array([[[x, yt], [x, yb]]], np.float32), Minv)[0]
        cv2.line(img, tuple(map(int, p[0])), tuple(map(int, p[1])), (0, 200, 255), 1)
        x += step
    return img
