"""Ruler width scale (Addendum I.4) on a drawn ruler with known px/cm."""
import cv2
import numpy as np
import pytest

from tomato3d.synth import ruler


def _draw_ruler(px_per_mm=12.0, angle=8.0, metal_top=True, frame=(1400, 1400)):
    h, w = frame
    img = np.full((h, w), 225, np.uint8)
    width = 30 * px_per_mm
    y0, y1 = int(h / 2 - width / 2), int(h / 2 + width / 2)
    x0, x1 = 100, w - 100
    img[y0:y1, x0:x1] = 215                                          # plastic, slightly darker than paper
    cv2.line(img, (x0, y0), (x1, y0), 120, 2)
    cv2.line(img, (x0, y1), (x1, y1), 120, 2)
    m = int(3.5 * px_per_mm)
    my = (y0, y0 + m) if metal_top else (y1 - m, y1)
    img[my[0]:my[1], x0:x1] = 90                                     # metal strip
    img[my[0] + m // 3:my[0] + m // 2, x0:x1] = 200                  # specular highlight inside the strip
    for k in range(6):                                               # 1 mm long grid lines in the middle
        yy = int(h / 2 - 3 * px_per_mm + k * px_per_mm)
        cv2.line(img, (x0, yy), (x1, yy), 60, 1)
    tick_edge = y1 if metal_top else y0
    sgn = -1 if metal_top else 1
    for i in range(int((x1 - x0) / px_per_mm)):
        x = int(round(x0 + 20 + i * px_per_mm))
        if x >= x1 - 5:
            break
        ln = 3.0 if i % 10 == 0 else (2.0 if i % 5 == 0 else 1.2)
        cv2.line(img, (x, tick_edge + sgn * 2), (x, int(tick_edge + sgn * ln * px_per_mm)), 40, 1)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    img = cv2.warpAffine(img, M, (w, h), borderValue=225)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


@pytest.mark.parametrize("metal_top", [True, False])
def test_width_scale_recovered(metal_top):
    r = ruler.measure(_draw_ruler(metal_top=metal_top))
    assert r["status"] == "ok"
    assert r["px_per_cm_width"] == pytest.approx(120.0, rel=0.02)
    assert r["parallel_ok"]


def test_tick_cross_check_agrees_on_a_true_ruler():
    r = ruler.measure(_draw_ruler())
    assert r["tick"]["status"] == "readable"
    assert abs(r["width_vs_tick_pct"]) < 2.0


def test_cut_ruler_is_not_usable():
    img = _draw_ruler(angle=0.0)
    h = img.shape[0]
    cut = img[: int(h / 2 + 30 * 12 / 2 - 60)]                   # frame cuts through the plastic
    r = ruler.measure(cut)
    assert r["status"] != "ok"
