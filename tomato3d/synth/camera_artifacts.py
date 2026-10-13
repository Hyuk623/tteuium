"""Addendum B3: camera artifacts measured on real rig photos and applied to synthetic renders.

Measurements (per image, at the evaluated resolution):

* ``noise_sigma`` - Immerkaer's fast noise estimate on the grey image (0-255 scale);
* ``leaf_sharpness`` - variance of the Laplacian inside the leaflet pixels;
* ``leaf_rgb`` - mean leaflet colour (0-255), and ``image_mean`` - mean grey level.

Application (post-process only): Gaussian blur chosen so the synthetic leaf sharpness reaches the
real median, Gaussian noise to the real noise level, and per-image exposure / white-balance gains
drawn from the real spread. JPEG is not applied: the originals are HEIC decoded to PNG, so no JPEG
quality can be measured from them.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

_IMMERKAER = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float64)


def noise_sigma(bgr: np.ndarray) -> float:
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
    h, w = g.shape
    conv = cv2.filter2D(g, -1, _IMMERKAER)[1:-1, 1:-1]
    return float(np.sqrt(np.pi / 2) * np.abs(conv).sum() / (6.0 * (w - 2) * (h - 2)))


def leaf_sharpness(bgr: np.ndarray, leaf_mask: np.ndarray) -> float:
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
    lap = cv2.Laplacian(g, cv2.CV_64F)
    inner = cv2.erode(leaf_mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    return float(lap[inner].var()) if inner.sum() > 50 else float("nan")


def measure(bgr: np.ndarray, leaf_mask: np.ndarray) -> dict[str, Any]:
    leaf = bgr[leaf_mask.astype(bool)]
    return dict(noise_sigma=noise_sigma(bgr), leaf_sharpness=leaf_sharpness(bgr, leaf_mask),
                leaf_bgr=leaf.mean(axis=0).tolist() if len(leaf) else None,
                image_mean=float(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).mean()))


def blur_for_sharpness(bgr: np.ndarray, leaf_mask: np.ndarray, target: float, sigmas=np.linspace(0, 3, 31)) -> float:
    """Smallest Gaussian sigma whose leaf sharpness is <= target (0 if already softer)."""
    for s in sigmas:
        img = bgr if s == 0 else cv2.GaussianBlur(bgr, (0, 0), float(s))
        if leaf_sharpness(img, leaf_mask) <= target:
            return float(s)
    return float(sigmas[-1])


def apply(bgr: np.ndarray, *, blur_sigma: float, noise: float, gain_bgr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    img = bgr.astype(np.float32)
    if blur_sigma > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur_sigma)
    img = img * np.asarray(gain_bgr, np.float32)[None, None]
    if noise > 0:
        img = img + rng.normal(0.0, noise, img.shape).astype(np.float32)
    return np.clip(img + 0.5, 0, 255).astype(np.uint8)
