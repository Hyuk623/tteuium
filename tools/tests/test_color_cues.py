"""Colour cues (tools.color_cues) and the arm logic of tools.color_cue_eval, on synthetic inputs."""
import cv2
import numpy as np
import pytest

from tools import color_cues as cc
from tools import color_cue_eval as ce


# ------------------------------------------------------------------------------------------- vegetation index math
def test_indices_on_pure_colours():
    rgb = np.array([[[0, 200, 0], [100, 100, 100], [0, 0, 0], [200, 50, 50]]], np.uint8)
    ix = cc.vegetation_indices(rgb)
    # pure green: r=0 g=1 b=0 -> ExG = 2, ExR = -1, ExG-ExR = 3
    assert ix['exg'][0, 0] == pytest.approx(2.0)
    assert ix['exr'][0, 0] == pytest.approx(-1.0)
    assert ix['exgr'][0, 0] == pytest.approx(3.0)
    # grey: r=g=b=1/3 -> ExG = 0, ExR = 1.4/3 - 1/3
    assert ix['exg'][0, 1] == pytest.approx(0.0, abs=1e-6)
    assert ix['exr'][0, 1] == pytest.approx(0.4 / 3, abs=1e-6)
    # black is undefined, never vegetation
    assert not ix['valid'][0, 2]
    # red: r=0.667 g=0.167 b=0.167 -> ExG = -0.5
    assert ix['exg'][0, 3] == pytest.approx(2 / 6 - 4 / 6 - 1 / 6, abs=1e-6)
    veg, info = cc.vegetation_mask(rgb, 'exgr_zero')
    assert veg.tolist() == [[True, False, False, False]] and info['threshold'] == 0.0


def test_linear_basis_uses_linearised_srgb():
    rgb = np.array([[[50, 150, 50]]], np.uint8)
    s = cc.chromatic(rgb, 'stored')[0][0, 0]
    l = cc.chromatic(rgb, 'linear')[0][0, 0]
    assert s[1] == pytest.approx(150 / 250)
    assert l[1] > s[1]  # linearisation expands the green dominance


def test_lab_and_hsv_units():
    L, a = cc.lab_lightness_a(np.array([[[0, 200, 0], [255, 255, 255]]], np.uint8))
    assert a[0, 0] < -40 and abs(a[0, 1]) <= 1 and L[0, 1] == pytest.approx(100, abs=0.5)
    h, s = cc.hue_saturation(np.array([[[0, 200, 0]]], np.uint8))
    assert h[0, 0] == pytest.approx(120, abs=2) and s[0, 0] == pytest.approx(1.0)


def test_otsu_separates_two_populations():
    rng = np.random.default_rng(0)
    img = np.full((40, 40, 3), (120, 110, 100), np.uint8)
    img[:, 20:] = (40, 160, 40)
    img = np.clip(img + rng.integers(-6, 7, img.shape), 0, 255).astype(np.uint8)
    veg, info = cc.vegetation_mask(img, 'exg_otsu')
    assert veg[:, 20:].all() and not veg[:, :20].any()
    assert cc.EXG_RANGE[0] < info['threshold'] < cc.EXG_RANGE[1]


def test_normalisations_keep_grid_and_board_wb_neutralises_a_tint():
    side = 60
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), 3, side)
    page = np.full((400, 400), 220, np.uint8)            # unsaturated paper white
    page[170:170 + side, 170:170 + side] = np.where(marker > 0, 220, 20)
    rgb = np.repeat(page[..., None], 3, 2)
    tinted = cc.apply_gains(rgb, [1.0, 0.85, 0.7])   # warm light on a white sheet
    ratio = 1.5  # square edge at 1.5 marker half-widths: white margin around the marker
    r = cc.board_white_gains(tinted, ratio)
    assert r['n_markers'] == 1 and r['gains'] is not None
    fixed = cc.normalize(tinted, 'board_wb', r['gains'])
    margin = fixed[170 - 8:170 - 3, 180:220].reshape(-1, 3).astype(float)
    assert np.ptp(margin.mean(0)) < 3
    for m in cc.NORMALIZATIONS:
        out = cc.normalize(tinted, m, r['gains'])
        assert out.shape == tinted.shape and out.dtype == np.uint8
    with pytest.raises(ValueError):
        cc.normalize(tinted, 'board_wb', None)


def test_grayworld_with_photo_gains_matches_whole_photo():
    rng = np.random.default_rng(1)
    rgb = rng.integers(0, 255, (30, 30, 3)).astype(np.uint8)
    whole = cc.normalize(rgb, 'grayworld')
    crop = cc.normalize(rgb[5:15, 5:15], 'grayworld', cc.grayworld_gains(rgb))
    assert np.array_equal(whole[5:15, 5:15], crop)


# ------------------------------------------------------------------------------------------- trimming never grows
@pytest.mark.parametrize('seed', range(5))
def test_trim_never_grows_and_is_monotone_in_radius(seed):
    rng = np.random.default_rng(seed)
    mask = rng.random((50, 60)) > 0.4
    veg = rng.random((50, 60)) > 0.7
    prev = None
    for r in (0, 1, 2, 4, 8):
        t = cc.trim_mask(mask, veg, r)
        assert not (t & ~mask).any()
        if prev is not None:
            assert not (prev & ~t).any()  # a larger radius keeps at least what a smaller one kept
        prev = t
    assert np.array_equal(cc.trim_mask(mask, np.ones_like(veg), 0), mask)


def test_crop_veg_uses_context_outside_the_window():
    veg = np.zeros((20, 20), bool)
    veg[10, 2] = True                       # vegetation just left of the mask window
    m = np.ones((5, 5), bool)               # window at x 4..8, y 8..12
    near = ce.crop_veg(veg, 4, 8, m, 2)     # dilation reaches x = 4
    assert near[:, 0].any() and not near[:, 2:].any()


def test_mask_features_and_components():
    m = np.zeros((20, 20), bool)
    m[2:8, 2:8] = m[12:18, 12:18] = True
    veg = np.zeros_like(m)
    veg[2:8, 2:8] = True
    maps = dict(exg=np.where(veg, 1.0, 0.0).astype(np.float32), exgr=np.zeros((20, 20), np.float32),
                a=np.full((20, 20), -10, np.float32), L=np.full((20, 20), 50, np.float32))
    f = cc.mask_features(m, veg, maps, 2)
    assert f['green_fraction'] == pytest.approx(0.5) and f['mean_a'] == -10 and f['mean_exg'] == pytest.approx(0.5)
    assert cc.large_components(m, 0.4) == 2 and cc.large_components(m, 0.6) == 0
    packed = cc.pack(m)
    assert np.array_equal(cc.unpack(packed['shape'], packed['bits']), m)


# ------------------------------------------------------------------------------------------- LOPO never uses the test plant
def test_lopo_select_never_reads_the_held_out_plant():
    plants = ['a', 'b', 'c', 'd']
    seen = []
    table = {0: dict(a=5, b=5, c=5, d=5), 1: dict(a=1, b=9, c=9, d=9), 2: dict(a=9, b=1, c=1, d=1)}

    def score(p, train):
        seen.append(tuple(train))
        return float(np.mean([table[p][x] for x in train]))
    sel = cc.lopo_select(score, [0, 1, 2], plants)
    for held, v in sel.items():
        assert held not in v['train_plants']
    assert all(len(set(t)) == 3 for t in seen)
    # changing the held-out plant's own numbers never changes its selection
    table[1]['a'] = -100
    assert cc.lopo_select(score, [0, 1, 2], plants)['a']['param'] == sel['a']['param']
    assert sel['a']['param'] == 2 and sel['a']['train_score'] == pytest.approx(1.0)


def test_lopo_ties_keep_the_conservative_first_setting():
    sel = cc.lopo_select(lambda p, train: 1.0, ['off', 'on'], ['a', 'b'])
    assert all(v['param'] == 'off' for v in sel.values())


# ------------------------------------------------------------------------------------------- arms on a synthetic photo
class FakeStore:
    """Two detections and one colour proposal on a 3024 px frame, no board pose (no area)."""
    LEAF = 1

    def __init__(self, with_proposal=True):
        m1 = np.zeros((100, 100), bool); m1[10:90, 10:90] = True
        m2 = np.zeros((100, 100), bool); m2[20:60, 20:60] = True
        pm = np.zeros((80, 80), bool); pm[5:75, 5:75] = True
        self._m = {'m0': (100, 100, m1), 'm1': (400, 400, m2), 'p0': (1000, 1000, pm)}
        self.plant_of = {'x_21': 'dwt_01'}
        hm = np.zeros((100, 100), bool); hm[10:90, 10:90] = True
        self._human = [(100, 100, hm), (1000, 1000, pm.copy())]
        draft = dict(scores=[0.9, 0.8, 0.7], default_candidate=0, risk={})
        self._rec = dict(
            detections={'none': [[1, [110, 110, 190, 190], 0.9], [1, [420, 420, 460, 460], 0.5], [0, [0, 0, 5, 5], 0.3]]},
            masks={'none': [dict(det_index=0, box=[110, 110, 190, 190], score=0.9, mask='m0', draft=draft,
                                 mask_colour=dict(green_fraction_exgr_zero=0.9)),
                            dict(det_index=1, box=[420, 420, 460, 460], score=0.5, mask='m1', draft=draft,
                                 mask_colour=dict(green_fraction_exgr_zero=0.05))]},
            proposals=[dict(id='p0', mask='p0', uncovered=1.0, component_px=5000, box=[1005, 1005, 1075, 1075], draft=draft,
                            veg_method='exgr_zero'),
                       dict(id='p0', mask='p0', uncovered=1.0, component_px=5000, box=[1005, 1005, 1075, 1075], draft=draft,
                            veg_method='exg_otsu'),          # degenerate vegetation mask in this photo: never a candidate
                       dict(id='p0', mask='p0', uncovered=1.0, component_px=9_000_000, box=[0, 0, 3024, 3024], draft=draft,
                            veg_method='exgr_zero')]         # whole-frame component: never a candidate
            if with_proposal else [])

    def rec(self, ph):
        return self._rec

    def mask(self, ph, k):
        l, t, m = self._m[k]
        return l, t, m.copy()

    def human(self, ph):
        return self._human

    def human_union(self, ph):
        hu = np.zeros((3024, 3024), bool)
        for l, t, m in self._human:
            ce.paste(hu, l, t, m)
        return hu

    def veg_mask(self, ph, key):
        v = np.zeros((3024, 3024), bool)
        v[100:200, 100:200] = True
        return v

    def side_posed(self, plant):
        return []

    def veg_info(self, ph):
        return {'none|exgr_zero': dict(fraction=0.05, degenerate=False), 'none|exg_otsu': dict(fraction=0.9, degenerate=True)}


class FakeJudge:
    def __init__(self, p):
        self.p = p

    def prob(self, rows, exclude, colour):
        return np.full(len(rows), self.p), 0.5


def _run(a, judge_p=0.0, store=None):
    return ce.run_photo(store or FakeStore(), FakeJudge(judge_p), 'x_21', a, frozenset({'dwt_01'}))


def test_default_arm_reproduces_baseline_masks_and_detections():
    r = _run(ce.BASELINE)
    assert r['n_masks'] == 2 and r['removed_px'] == 0 and r['props'] == dict(candidates=0, accepted=0, matched=0)
    assert [b for b, s in r['leaf_dets']] == [[110, 110, 190, 190], [420, 420, 460, 460]]
    assert ce.arm() == ce.BASELINE and ce.arm_key(ce.BASELINE) == '{}'
    for f in ('wb', 'bundle', 'evaluate'):
        assert callable(getattr(ce, f))


def test_proposals_are_tagged_and_excluded_unless_the_judge_accepts():
    a = ce.arm(prop=(0.5, 400))
    rejected = _run(a, judge_p=0.1)
    assert rejected['props']['candidates'] == 1 and rejected['props']['accepted'] == 0 and rejected['n_masks'] == 2
    accepted = _run(a, judge_p=0.9)
    assert accepted['props']['accepted'] == 1 and accepted['n_masks'] == 3 and accepted['props']['matched'] == 1
    origins = [it['origin'] for it, _ in accepted['_judge_items']]
    assert origins.count('color_proposal') == 1
    # proposals never enter the detector AP
    assert len(accepted['leaf_dets']) == len(rejected['leaf_dets']) == 2
    # the human proposal leaflet is only found when the proposal is accepted
    assert sum(v >= 0.5 for v in accepted['e2e']) == 2 and sum(v >= 0.5 for v in rejected['e2e']) == 1


def test_fp_filter_drops_low_green_detections_from_masks_and_ap():
    r = _run(ce.arm(fp=('exgr_zero', 0.3)))
    assert r['n_masks'] == 1 and [b for b, s in r['leaf_dets']] == [[110, 110, 190, 190]]


def test_trim_counts_removed_pixels_inside_human_masks():
    r = _run(ce.arm(trim=('none', 'exgr_zero', 0)))
    # m0 sits inside the vegetation square entirely; m1 (outside it) is removed completely, and lies on no human mask
    assert r['removed_px'] == 40 * 40 and r['removed_in_human_px'] == 0


def test_degenerate_vegetation_mask_is_flagged():
    board = np.zeros((40, 40, 3), np.uint8)
    board[:, :20] = (30, 34, 30)        # dark squares with a faint green cast
    board[:, 20:] = (200, 200, 200)
    veg, info = cc.vegetation_mask(board, 'exg_otsu')
    assert info['degenerate'] == (veg.mean() > cc.VEG_DEGENERATE_FRACTION)
    ok, info2 = cc.vegetation_mask(board, 'exgr_zero')
    assert 'fraction' in info2 and info2['degenerate'] is False
