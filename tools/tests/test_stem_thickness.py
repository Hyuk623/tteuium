"""Stem diameter: the medial distance transform reads a strip's width; partly hidden or mixed outlines are not used."""
import numpy as np

from tools import stem_thickness as st


def test_medial_width_of_a_straight_strip():
    m = np.zeros((200, 200), np.uint8)
    m[20:180, 90:110] = 1  # 20 px wide
    w, xy = st.medial_widths(m)
    assert abs(np.median(w) - 20) <= 1.5 and np.allclose(np.median(xy[:, 0]), 99.5, atol=1)


def test_medial_width_follows_a_bent_strip():
    import cv2
    m = np.zeros((300, 300), np.uint8)
    cv2.polylines(m, [np.array([[50, 250], [150, 150], [150, 30]], np.int32)], False, 1, thickness=16)
    w, _ = st.medial_widths(m)
    assert abs(np.median(w) - 16) <= 2  # a whole-polygon PCA width would mix the two directions


def _samples(d):
    return dict(z=np.linspace(0, 30, len(d)), d=np.asarray(d, float))


def test_only_steady_photos_give_the_diameter():
    samples = {'p_21.png': _samples([5.0] * 40), 'p_27.png': _samples([5.2] * 40),
               'p_24.png': _samples([2.0] * 20 + [5.0] * 20)}  # half hidden by leaves
    r = st._summary([], samples)
    assert r['status'] == 'measured' and r['steady_photos'] == 2 and abs(r['diameter_mm'] - 5.1) < 1e-6
    assert r['per_photo_width']['24']['used'] is False and r['steady_spread_pct'] < 5


def test_no_steady_photo_is_unreliable_not_a_number():
    r = st._summary([], {'p_21.png': _samples([2.0] * 20 + [6.0] * 20)})
    assert r['status'] == 'unreliable' and 'diameter_mm' not in r
