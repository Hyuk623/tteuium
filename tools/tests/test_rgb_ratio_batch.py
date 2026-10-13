"""Masked ratio batch: both ratio bases stay distinct, grayworld equalises channel means, separability finds direction."""
import numpy as np

from tools import rgb_ratio_batch as rb


def test_bases_differ_and_are_fractions():
    rgb = np.array([[[200, 100, 50], [0, 0, 0]]], np.uint8)
    s, l = rb.ratios(rgb, 'stored'), rb.ratios(rgb, 'linear')
    assert np.allclose(s[0, 0], [200 / 350, 100 / 350, 50 / 350], atol=1e-6)
    assert np.isclose(np.nansum(l[0, 0]), 1.0) and not np.allclose(s[0, 0], l[0, 0])
    assert np.isnan(s[0, 1]).all() and np.isnan(l[0, 1]).all(), 'R+G+B=0 must stay undefined'


def test_grayworld_equalises_means_and_keeps_grid():
    rng = np.random.default_rng(1)
    rgb = (rng.random((20, 30, 3)) * [200, 120, 60]).astype(np.uint8)
    out = rb.grayworld(rgb)
    m = out.reshape(-1, 3).mean(0)
    assert out.shape == rgb.shape and np.ptp(m) < 1.5


def test_masks_remove_leaf_pixels_from_stem_polygons(tmp_path):
    from PIL import Image
    leaf = np.zeros((40, 40), bool); leaf[:, :20] = True
    Image.fromarray(leaf.astype(np.uint8) * 255).save(tmp_path / 'm.png')
    objs = [dict(cls='leaflet', mask_file=tmp_path / 'm.png'), dict(cls='main-stem', rings=[[[5, 5], [35, 5], [35, 35], [5, 35]]])]
    lm, sm = rb.masks_for(objs, (40, 40))
    assert lm.sum() == 800 and sm.any() and not (sm & lm).any()


def test_separability_learns_direction_on_other_plants():
    rows = []
    for p in ('a', 'b', 'c'):
        for i in range(10):
            for cls, r in (('leaflet', 0.30 + i * 0.001), ('main-stem', 0.40 + i * 0.001)):
                rows.append(dict(plant=p, cls=cls, variant='original', basis='stored', r_med=r, g_med=0.4, b_med=0.3, hue_med=80.0))
    res = rb.separability(rows)['results']['original|stored|r']
    assert res['higher'] == 'stem' and res['auc'] == 1.0
    assert all(v['balanced_accuracy'] == 1.0 and v['leaf_side'] == 'below' for v in res['lopo_threshold'].values())
