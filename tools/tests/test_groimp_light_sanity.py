"""Phase-1 light sanity: the project's direct-light code matches the analytic point-lamp integral (no GroIMP needed)."""
import math

import pytest

from tools import groimp_light_sanity as gls


@pytest.mark.parametrize('x', gls.XS_M)
def test_python_module_matches_analytic(x):
    a, p = gls.analytic(x), gls.python_module(x)
    assert abs(p['absorbed_umol_s'] - a['absorbed_umol_s']) / a['absorbed_umol_s'] < 1e-3


def test_top_face_below_the_lamp_follows_inverse_square():
    # a small plate straight under a point lamp: E ~ P / (4 pi H^2)
    top_ppfd = gls.analytic(0.0)['top_umol_s'] / gls.PLATE_M ** 2
    expected = gls.FLUX / (4 * math.pi * (gls.LAMP_HEIGHT_M - gls.THICK_M) ** 2)
    assert abs(top_ppfd - expected) / expected < 0.01


def test_rgg_names_every_receiver_once():
    receivers = '\n'.join(f'[ Translate({x}f, 0, 0) Receiver({i}).(setShader(BLACK)) ]' for i, x in enumerate(gls.XS_M))
    rgg = gls.RGG.format(flux=gls.FLUX, thick=gls.THICK_M, plate=gls.PLATE_M, rays=10, height=gls.LAMP_HEIGHT_M, receivers=receivers)
    assert all(f'Receiver({i})' in rgg for i in range(len(gls.XS_M))) and 'SANITY_DONE' in rgg and 'Lamp()' in rgg
