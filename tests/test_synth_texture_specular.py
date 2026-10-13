"""Cell N (2026-10-08): specular-highlight detection and inpaint repair in the texture bank build."""

from __future__ import annotations

import cv2
import numpy as np

from tomato3d.synth.textures import make_texture, repair_specular, specular_mask

RULE = dict(v_min=225, s_max=64, dilate_px=2, inpaint_radius_px=5)


def _leaf_with_blob():
    img = np.full((300, 400, 3), 255, np.uint8)
    mask = np.zeros((300, 400), np.uint8)
    pts = np.array([[60, 150], [120, 95], [220, 105], [340, 145], [220, 195], [120, 205]], np.int32)
    cv2.fillPoly(mask, [pts], 1)
    m = mask.astype(bool)
    img[m] = (60, 140, 90)
    for x in range(90, 330, 30):                                   # veins: dark lines, high-frequency contrast
        cv2.line(img, (x, 110), (x + 20, 190), (40, 100, 60), 2)
    img[m] = cv2.GaussianBlur(img, (0, 0), 1.0)[m]
    cv2.circle(img, (200, 150), 9, (250, 252, 250), -1)            # one near-white, desaturated blotch
    return img, m


def test_specular_mask_flags_only_the_blotch():
    img, m = _leaf_with_blob()
    spec = specular_mask(img, m, RULE)
    assert spec.any() and spec.sum() < 0.05 * m.sum()
    ys, xs = np.nonzero(spec)
    assert abs(xs.mean() - 200) < 3 and abs(ys.mean() - 150) < 3    # centred on the blotch, nowhere else
    assert not specular_mask(img, m, dict(RULE, v_min=256)).any()


def test_repair_removes_blotch_and_keeps_vein_contrast():
    img, m = _leaf_with_blob()
    fixed, info = repair_specular(img, m, RULE)
    assert info["specular_fraction_before"] > 0 and info["specular_fraction_after"] == 0.0
    assert np.array_equal(fixed[~m], img[~m])                       # outside the leaflet untouched
    g0 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(float)
    g1 = cv2.cvtColor(fixed, cv2.COLOR_BGR2GRAY).astype(float)
    far = m & (np.hypot(*np.meshgrid(np.arange(400) - 200, np.arange(300) - 150)) > 25)
    assert np.array_equal(g0[far], g1[far])                         # pixels away from the blotch unchanged
    hp = lambda g: (g - cv2.GaussianBlur(g, (0, 0), 6.0))[far].std()
    assert abs(hp(g1) - hp(g0)) < 0.01 * hp(g0)                     # vein contrast kept (blur tails only)
    assert abs(float(fixed[m].mean()) - float(img[m & ~specular_mask(img, m, RULE)].mean())) < 3.0


def test_make_texture_records_fractions_and_is_unchanged_without_rule():
    img, m = _leaf_with_blob()
    plain = make_texture(img, m)
    assert "specular_fraction_before" not in plain
    fixed = make_texture(img, m, specular_rule=RULE)
    assert fixed["specular_fraction_before"] > 0 and fixed["specular_fraction_after"] == 0.0
    assert fixed["texture"].shape == plain["texture"].shape and fixed["aspect"] == plain["aspect"]
    assert np.array_equal(fixed["silhouette"], plain["silhouette"])
    # the bright blotch is gone from the albedo: the texture's brightest texel is darker than before
    assert cv2.cvtColor(fixed["texture"], cv2.COLOR_BGR2GRAY).max() < cv2.cvtColor(plain["texture"], cv2.COLOR_BGR2GRAY).max()
