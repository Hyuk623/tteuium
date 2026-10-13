"""Automatic rim-line PROPOSALS for the side-photo pot-rim records (semi-automatic clicking).

Proposals only: they are written under ``build/`` and pre-filled into the clicking page
(``tomato3d.cli.rim_points_tool --prefill``); a person reviews, moves or deletes them and saves the record. Nothing
here writes ``data/records/``.

Revised 2026-10-13. The 2026-10-12 version claimed its front proposals lay on the OUTER top edge and that the person's
clicks were wrong; that claim was an ``np.convolve(mode="same")`` end artifact and is withdrawn (handoff
``P1_SIDE_RIM_POSE_EXECUTION_2026-10-12`` section 7). The pages built from it (``build/rim_click_side_20261012_03``)
are void. Every proposal now names the LINE it lies on (``potscale.EDGES``), from the geometry of a side photo (camera
in front, above the rim):

* FRONT side: the front wall's inner face is turned away from the camera, so the medium junction there is hidden; the
  sharp rim/soil line is the front INNER TOP edge (rim plane) - ``inner_top``. Proposed on the soil boundary itself
  (the strongest grey step within a few px of it). The outer top edge lies 8-20 px lower and is soft (measured
  2026-10-12 on the real photos); it is not proposed.
* LEFT / RIGHT sides: the strongest grey step outward of the soil boundary is the rim's outer silhouette against the
  paper - ``outer_top`` (checked on side_000 against a person's clicks: within ~10 px where both exist).
* BACK side: behind the plant; found in 1 of 52 real photos by a predicted-line search (2026-10-12), i.e. genuinely
  occluded by leaves. Proposed as ``side_occluded`` for the person to confirm (or replace by clicks where visible).
  Three lines + the occluded side are solved by ``camera.pose_from_lines`` with the focal fixed (approximate pose).

Method: the pot interior = the largest brown-or-dark, non-green region (soil, with its shadows); its convex hull ->
polygon; the 4 longest edges in order = the four sides seen from inside; profiles normal to each side; RANSAC line;
4 well-spread inliers per side with the side number (1-4, consecutive). Top photos are not supported (leaves overhang
the rim from above) - top records stay person-clicked.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from tomato3d.state import potscale as ps

METHOD = "auto:rim_auto_v2"
#: band searched outward from the soil boundary, as a fraction of the soil width (proposal heuristic, not a measurement)
SEARCH_FRACTION = 0.04
MIN_SEARCH_PX = 25
#: half band (px) around the soil boundary in which the front rim/soil step is taken
BOUNDARY_BAND_PX = 6
#: grey-level step (8-bit, smoothed) below which no edge is taken
MIN_STEP = 6.0
#: RANSAC inlier tolerance (px) and the inlier share a side needs to be proposed
RANSAC_TOL_PX = 4.0
MIN_INLIER_SHARE = 0.6
POINTS_PER_SIDE = 4
#: line proposed for each side position of a side photo (module docstring)
SIDE_EDGE = {"front": "inner_top", "left": "outer_top", "right": "outer_top"}


@dataclass
class SideProposal:
    side: int
    position: str  # front | back | left | right (image-based)
    points: np.ndarray  # (n, 2) px
    inlier_share: float
    proposed: bool
    note: str = ""
    edge: str = ""  # potscale.EDGES value of the proposed line
    occluded: bool = False  # proposed as side_occluded (the back side)


@dataclass
class PhotoProposal:
    status: str  # proposed | partial | none
    sides: list[SideProposal] = field(default_factory=list)
    reason: str = ""


def interior_mask(bgr: np.ndarray) -> np.ndarray | None:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(int)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    brown = (h >= 3) & (h <= 24) & (s >= 60) & (v <= 235)
    dark = (v <= 95) & ~((h >= 30) & (h <= 90) & (s >= 60))
    leaf = (h >= 25) & (h <= 95) & (s >= 50)
    m = ((brown | dark) & ~leaf).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None
    return (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)


def ordered_sides(hull: np.ndarray) -> tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray]:
    peri = cv2.arcLength(hull, True)
    poly = hull.reshape(-1, 2).astype(float)
    for eps in np.linspace(0.005, 0.06, 40):
        poly = cv2.approxPolyDP(hull, eps * peri, True).reshape(-1, 2).astype(float)
        if len(poly) <= 8:
            break
    edges = [(i, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    keep = sorted(sorted(edges, key=lambda e: -np.linalg.norm(e[2] - e[1]))[:4], key=lambda e: e[0])
    return [(a, b) for _, a, b in keep], poly


def _profile_points(gray: np.ndarray, a: np.ndarray, b: np.ndarray, centre: np.ndarray, r0: int, r1: int,
                    skip: int) -> np.ndarray:
    """Strongest grey step on profiles normal to side a-b, from ``r0`` to ``r1`` px outward (away from the centre);
    the first ``skip`` steps are ignored. The 'same' smoothing invents a step at both profile ends - those two steps
    are always ignored (the 2026-10-12 artifact)."""
    d = (b - a) / np.linalg.norm(b - a)
    n = np.array([-d[1], d[0]])
    if np.dot((a + b) / 2 - centre, n) < 0:
        n = -n
    length, pts = np.linalg.norm(b - a), []
    for t in np.linspace(0.1, 0.9, 40):
        p = a + d * t * length
        prof = []
        for r in range(r0, r1):
            x, y = (p + n * r).round().astype(int)
            if not (0 <= x < gray.shape[1] and 0 <= y < gray.shape[0]):
                break
            prof.append(float(gray[y, x]))
        if len(prof) < 10:
            continue
        g = np.abs(np.diff(np.convolve(prof, np.ones(3) / 3, mode="same")))
        g[:max(skip, 2)] = 0
        g[-2:] = 0
        r = int(np.argmax(g))
        if g[r] > MIN_STEP:
            pts.append(p + n * (r0 + r))
    return np.array(pts)


def outward_points(gray: np.ndarray, a: np.ndarray, b: np.ndarray, centre: np.ndarray, search: int) -> np.ndarray:
    """Outer silhouette: the strongest step 4..``search`` px outward of the soil boundary."""
    return _profile_points(gray, a, b, centre, 0, search, 4)


def boundary_points(gray: np.ndarray, a: np.ndarray, b: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """The rim/soil line itself: the strongest step within +-``BOUNDARY_BAND_PX`` of the soil boundary."""
    return _profile_points(gray, a, b, centre, -BOUNDARY_BAND_PX - 2, BOUNDARY_BAND_PX + 3, 0)


def ransac_inliers(pts: np.ndarray, tol: float = RANSAC_TOL_PX, iters: int = 300, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    best = np.zeros(len(pts), bool)
    for _ in range(iters):
        i, j = rng.choice(len(pts), 2, replace=False)
        d = pts[j] - pts[i]
        if np.linalg.norm(d) < 1e-6:
            continue
        nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
        inl = np.abs((pts - pts[i]) @ nrm) < tol
        if inl.sum() > best.sum():
            best = inl
    return best


def _positions(mids: dict[int, np.ndarray]) -> dict[int, str]:
    front = max(mids, key=lambda k: mids[k][1])
    back = min(mids, key=lambda k: mids[k][1])
    rest = sorted((k for k in mids if k not in (front, back)), key=lambda k: mids[k][0])
    out = {front: "front", back: "back"}
    if len(rest) == 2:
        out[rest[0]], out[rest[1]] = "left", "right"
    return out


def propose(bgr: np.ndarray, view: str) -> PhotoProposal:
    """Rim-line proposals for one SIDE photo (``view`` top -> none: not supported)."""
    if view != "side":
        return PhotoProposal("none", reason="top photos are not supported (leaves overhang the rim from above)")
    mask = interior_mask(bgr)
    if mask is None:
        return PhotoProposal("none", reason="no pot interior found")
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
    sides, poly = ordered_sides(hull)
    if len(sides) < 4:
        return PhotoProposal("none", reason="pot interior is not four-sided")
    gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    centre = poly.mean(axis=0)
    search = max(int(SEARCH_FRACTION * float(np.ptp(poly[:, 0]))), MIN_SEARCH_PX)
    pos = _positions({k: (a + b) / 2 for k, (a, b) in enumerate(sides, start=1)})
    out = PhotoProposal("proposed")
    for k, (a, b) in enumerate(sides, start=1):
        position = pos.get(k, "unknown")
        if position == "back":
            out.sides.append(SideProposal(k, position, np.zeros((0, 2)), 0.0, False,
                                          "back: behind the plant, found in 1 of 52 real photos - proposed as "
                                          "side_occluded (click it instead where it is visible)", "", True))
            continue
        edge = SIDE_EDGE.get(position, "")
        pts = boundary_points(gray, a, b, centre) if edge == "inner_top" else outward_points(gray, a, b, centre, search)
        if not edge or len(pts) < 6:
            out.sides.append(SideProposal(k, position, np.zeros((0, 2)), 0.0, False,
                                          "too few edge samples" if edge else "side position unknown", edge))
            continue
        inl = ransac_inliers(pts)
        share = float(inl.mean())
        good = pts[inl]
        good = good[np.argsort((good - good[0]) @ ((b - a) / np.linalg.norm(b - a)))]
        pick = good[np.linspace(0, len(good) - 1, min(POINTS_PER_SIDE, len(good))).round().astype(int)]
        ok = share >= MIN_INLIER_SHARE and len(good) >= 6
        out.sides.append(SideProposal(k, position, pick if ok else np.zeros((0, 2)), share, ok,
                                      "" if ok else f"inlier share {share:.2f}", edge))
    n_ok = sum(sp.proposed for sp in out.sides)
    n_occ = sum(sp.occluded for sp in out.sides)
    if n_ok + n_occ < 4 or n_ok < 3:
        out.status = "partial" if n_ok else "none"
    out.reason = "; ".join(f"side {sp.side} ({sp.position}): {sp.note}" for sp in out.sides if not sp.proposed)
    return out


def proposal_rows(plant_id: str, image_sha256: str, prop: PhotoProposal) -> list[list[str]]:
    """Rows in ``potscale.RIM_POINTS_COLUMNS``; click uncertainty blank (the person states it when saving)."""
    rows = []
    for sp in prop.sides:
        for x, y in sp.points:
            rows.append([plant_id, image_sha256, "rim_edge", str(sp.side), sp.edge, f"{x:.2f}", f"{y:.2f}", "", "",
                         METHOD, f"PROPOSAL {sp.position} {sp.edge} - review before use"])
        if sp.occluded:
            rows.append([plant_id, image_sha256, "side_occluded", str(sp.side), "", "", "", "", "", METHOD,
                         f"PROPOSAL {sp.position} side occluded - confirm or click it"])
    return rows


def write_proposals(path: Path, rows: Sequence[Sequence[str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(ps.RIM_POINTS_COLUMNS)
        w.writerows(rows)
    return path
