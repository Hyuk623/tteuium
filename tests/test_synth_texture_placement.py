"""Addendum G.2 A1: texture placement keeps the leaflet outline on textured texels; flat-fill measurement."""

from __future__ import annotations

import cv2
import numpy as np

from tomato3d.synth.leaflet_surface import normalize_contour
from tomato3d.synth.textures import (TEX_SIZE, contour_profile, flat_fill_fraction, hash_uv, make_texture,
                                     silhouette_profile, texture_silhouette, warp_uv)
from tomato3d.synth.images import imwrite


def _ellipse_texture():
    w, h = TEX_SIZE
    sil = np.zeros((h, w), np.uint8)
    cv2.ellipse(sil, (w // 2, h // 2), (int(0.48 * w), int(0.30 * h)), 0, 0, 360, 1, -1)
    return sil.astype(bool)


def _lobed_contour(n=64):
    a = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    r = 1.0 + 0.25 * np.cos(7 * a)                                    # deep lobes
    pts = np.c_[300 + 160 * r * np.cos(a), 200 + 70 * r * np.sin(a)]
    return normalize_contour(pts, n)["points"]


def test_warp_keeps_lobed_outline_on_texture_where_b5a_mapping_does_not():
    sil, c = _ellipse_texture(), _lobed_contour()
    aspect = 0.5                                                      # crop height / width, as in the bank
    old = flat_fill_fraction(c, lambda q: hash_uv(q, aspect), sil)
    cp, tp = contour_profile(c), silhouette_profile(sil)
    new = flat_fill_fraction(c, lambda q: warp_uv(q, cp, tp), sil)
    assert old > 0.05
    assert new < 0.02


def test_silhouette_recovered_from_flat_fill_colour(tmp_path):
    w, h = TEX_SIZE
    sil = _ellipse_texture()
    rng = np.random.default_rng(0)
    img = np.empty((h, w, 3), np.uint8)
    img[:] = (90, 140, 120)                                          # constant fill = leaflet mean
    noise = rng.integers(40, 200, size=(h, w, 3)).astype(np.uint8)
    img[sil] = noise[sil]
    imwrite(tmp_path / "t.png", img)
    rec = texture_silhouette(dict(path=str(tmp_path / "t.png"), mask_path=None))
    assert (rec ^ sil).mean() < 0.01


def test_same_mask_texture_has_little_fill():
    img = np.full((300, 400, 3), 255, np.uint8)
    mask = np.zeros((300, 400), np.uint8)
    pts = np.array([[60, 150], [100, 110], [120, 80], [150, 112], [220, 100], [250, 70], [270, 118], [340, 145],
                    [220, 195], [120, 205]], np.int32)
    cv2.fillPoly(mask, [pts], 1)
    img[mask.astype(bool)] = (60, 140, 90)
    t = make_texture(img, mask.astype(bool))
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = normalize_contour(max(cs, key=cv2.contourArea).reshape(-1, 2), 64)["points"]
    cp, tp = contour_profile(c), silhouette_profile(t["silhouette"])
    best = min(flat_fill_fraction(c, lambda q, fx=fx, fy=fy: warp_uv(q, cp, tp, flip_x=fx, flip_y=fy), t["silhouette"])
               for fx in (False, True) for fy in (False, True))
    assert best < 0.02
