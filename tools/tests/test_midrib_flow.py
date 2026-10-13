"""Midrib flow: the bright-ridge path follows a bright line inside a leaf-shaped mask, not the straight chord."""
import cv2
import numpy as np

from tools import midrib_flow as mf


def _leaf(bent: bool):
    h, w = 160, 320
    rgb = np.full((h, w, 3), (60, 120, 50), np.uint8)
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, (160, 80), (140, 60), 0, 0, 360, 1, -1)
    xs = np.arange(30, 291)
    ys = (80 + (25 * np.sin((xs - 30) / 260 * np.pi) if bent else 0 * xs)).astype(int)
    for x, y in zip(xs, ys):
        cv2.circle(rgb, (int(x), int(y)), 2, (140, 200, 120), -1)  # a pale midrib, 4-5 px wide
    return rgb, mask.astype(bool), np.column_stack([xs, ys])


def test_bright_ridge_peaks_on_a_bright_line():
    rgb, _, line = _leaf(False)
    L = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[..., 0]
    r = mf.bright_ridge(L)
    assert r[80, 160] > 5 * np.median(r[20:40, 100:220])


def test_path_follows_a_curved_midrib_not_the_chord():
    rgb, mask, line = _leaf(True)
    res = mf.midrib(rgb, mask)
    assert res['status'] == 'proposed'
    path = np.array(res['path_px'])
    inner = path[(path[:, 0] > 90) & (path[:, 0] < 230)]
    truth = dict(zip(line[:, 0], line[:, 1]))
    err = np.abs([y - truth[x] for x, y in inner if x in truth])
    assert np.median(err) <= 3 and res['mean_ridge_on_path'] > res['mean_ridge_on_chord']


def test_thin_mask_is_unavailable_not_a_line():
    rgb = np.full((50, 50, 3), 100, np.uint8)
    mask = np.zeros((50, 50), bool); mask[24:27, 5:45] = True
    assert mf.midrib(rgb, mask)['status'] == 'unavailable'
