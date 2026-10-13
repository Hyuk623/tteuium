"""Colour-cue experiment runner (2026-10-04, handoff CLAUDE_CODE_COLOR_CUE_DETECTION_PROMPT_2026-10-03).

    python -X utf8 -m tools.color_cue_eval wb --out build/color_cues_<date>_NN            # board white-balance gains
    python -X utf8 -m tools.color_cue_eval bundle --out build/color_cues_<date>_NN        # Kaggle code dataset + kernel
    python -X utf8 -m tools.color_cue_eval evaluate --out build/color_cues_<date>_NN      # arms A-G, LOPO, reports

Inference (detector v4 LOPO + SAM v5 held-out, step_0, no training) runs on Kaggle (kernel written by `bundle`, source
build/color_cues_*/kernel/infer.py); everything else is local and reads the kernel's raw output from <out>/kout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from tools import color_cues as cc
from tools.leaf_light.common import file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
PLANTS = ('dwt_01', 'dwt_02', 'dwt_03', 'dwt_04')
PHOTOS = ROOT / 'build' / 'split_exp_20260930' / 'upload' / 'photos'      # = Kaggle dolgfish/tomato-split-exp-photos
POSE_SESSION = ROOT / 'build' / 'pose_rescue_20261001'                     # <plant>/edit_session/board_spec.snapshot.json


def photo_paths(plants=PLANTS) -> dict[str, Path]:
    return {p.stem: p for plant in plants for p in sorted((PHOTOS / plant).glob('*.jpg'))}


def wb(out: Path) -> dict:
    """Board white-balance gains for every photo of the four plants (input of the Kaggle kernel and of evaluate)."""
    out.mkdir(parents=True, exist_ok=True)
    rows = {}
    for plant in PLANTS:
        spec = POSE_SESSION / plant / 'edit_session' / 'board_spec.snapshot.json'
        ratio = cc.board_spec_ratio(spec)
        for stem, path in photo_paths([plant]).items():
            rgb = np.asarray(Image.open(path).convert('RGB'))
            r = cc.board_white_gains(rgb, ratio, read_json(spec)['aruco_dict'])
            rows[stem] = dict(plant=plant, photo_sha256=file_hash(path), grayworld_gains=cc.grayworld_gains(rgb), **r)
            print(stem, r['gains'], r['n_markers'], r['n_pixels'], file=sys.stderr, flush=True)
    res = dict(schema='board-wb-gains-1', basis='linear sRGB von Kries, gains keep the mean of the channel medians',
               sampling='white margin between each detected ArUco marker and its square edge (marker homography)',
               ring_marker_halfwidths=[cc.WB_RING_INNER, 'square/marker - %.2f' % cc.WB_RING_OUTER_GAP],
               rejects=dict(clipped_8bit=cc.CLIPPED_8BIT, dark_8bit=cc.DARK_8BIT, vegetation='ExG-ExR > 0'),
               min_pixels=cc.WB_MIN_PIXELS, photos=rows)
    write_json(out / 'wb_gains.json', res)
    return res


BUNDLE_FILES = ('tools/color_cues.py', 'tools/leaf_preprocess_lab.py', 'tools/preprocess_study.py', 'tools/rgb_ratio_batch.py',
                'tools/leaf_light/__init__.py', 'tools/leaf_light/common.py')
CODE_DATASET = 'dolgfish/tomato-color-cues-code'
KERNEL_ID = 'dolgfish/tomato-color-cues-infer'
KERNEL_DATASETS = ['dolgfish/tomato-organ-v4', 'dolgfish/tomato-leaflets-v5', 'dolgfish/tomato-split-exp-photos',
                   'dolgfish/tomato-al-4plants', 'dolgfish/tomato-leaflets-4plants', 'dolgfish/tomato-mask-redraft', CODE_DATASET]


def bundle(out: Path) -> dict:
    """Kaggle code dataset (colour helpers + gains) and kernel metadata; the kernel source is <out>/kernel/infer.py."""
    import shutil
    up = out / 'code_upload'
    if up.exists():
        shutil.rmtree(up)
    for f in BUNDLE_FILES:
        (up / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, up / f)
    shutil.copy2(out / 'wb_gains.json', up / 'wb_gains.json')
    write_json(up / 'dataset-metadata.json', dict(title='tomato color cues code', id=CODE_DATASET, licenses=[dict(name='CC0-1.0')]))
    manifest = dict(schema='color-cues-bundle-1', files={f: file_hash(ROOT / f) for f in BUNDLE_FILES},
                    wb_gains=file_hash(out / 'wb_gains.json'), kernel=file_hash(out / 'kernel' / 'infer.py'),
                    kernel_id=KERNEL_ID, datasets=KERNEL_DATASETS)
    write_json(out / 'bundle_manifest.json', manifest)
    write_json(out / 'kernel' / 'kernel-metadata.json', dict(
        id=KERNEL_ID, title='tomato color cues infer', code_file='infer.py', language='python', kernel_type='script',
        is_private=True, enable_gpu=True, machine_shape='NvidiaTeslaT4', enable_tpu=False, enable_internet=True,
        dataset_sources=KERNEL_DATASETS, kernel_sources=[], competition_sources=[], model_sources=[]))
    return manifest


# ============================================================================================ local scoring of the arms
AL4_RESULTS = ROOT / 'build' / 'al_4plants_20261002' / 'kout' / 'results.json'
CONF_OUT = 0.25
FRONT_PCT = 20                      # S8: 20th depth percentile of the hull voxels behind a mask
IOU_MATCH = 0.5
VIEW_GROUP = {'0': 'top', '1': 'middle', '2': 'side'}
JUDGE_COLOUR = ['green_fraction_exgr_zero', 'mean_a', 'exg_contrast']   # arm F: the three cues the handoff names
#: acceptance rules of the handoff (also used as constraints on the TRAINING plants during LOPO selection)
MAX_AP_DROP, MAX_REMOVED_INSIDE, MAX_PLANT_WORSENING_PP = 0.01, 0.02, 2.0
#: error attribution: an unmatched prediction with < this share of its pixels on human leaflets is a false positive;
#: one covering >= this share of each of two or more human masks is a merged box
FP_INSIDE_MAX, MERGE_COVER_MIN = 0.2, 0.2
#: arm E: a colour proposal is a leaflet candidate only if its vegetation component is at most this share of the frame
#: (largest human leaflet mask 111k px = 1.2 %) and its vegetation mask is not degenerate in that photo
PROP_MAX_FRACTION = 0.02
EXGR_Q = (-2.4, 3.0)                # ExG - ExR range for the uint8 map previews (ExG in [-1,2], ExR in [-1,1.4])


def stem_of(name: str) -> str:
    return Path(name).stem


class Cams:
    """Board poses of the plant's pose session; as build/al_4plants_20261002/kernel/train.py (tools.plant_structure)."""
    OK = ('solved', 'solved_marker_corners')

    def __init__(self, cap: dict):
        import cv2
        self.cv2 = cv2
        i = cap['intrinsics']
        self.K, self.D = np.array(i['camera_matrix'], float), np.array(i['dist_coeffs'], float)
        self.W, self.H = i['image_width_px'], i['image_height_px']
        self.frames = {stem_of(f['image_file']): f for f in cap['frames']
                       if f.get('pose_status') in self.OK and f.get('rvec_rad') is not None}

    def proj(self, ph: str, X: np.ndarray):
        f = self.frames[ph]
        r, t = np.array(f['rvec_rad'], float), np.array(f['tvec_mm'], float)
        px = self.cv2.projectPoints(X, r, t, self.K, self.D)[0].reshape(-1, 2)
        z = (X @ self.cv2.Rodrigues(r)[0].T + t)[:, 2]
        return px, z


def depth_map(cams: Cams, hull: np.ndarray, ph: str, masks: list) -> tuple[np.ndarray, int]:
    """Per-pixel depth (mm, inf = no leaf) of the union of masks, each mask at the 20th depth percentile of the hull
    voxels projecting inside it (S8 pipeline_20261001_s8 / al_4plants train.py photo_area)."""
    px, depth = cams.proj(ph, hull)
    pi = np.round(px).astype(int)
    ok = (pi[:, 0] >= 0) & (pi[:, 0] < cams.W) & (pi[:, 1] >= 0) & (pi[:, 1] < cams.H) & (depth > 0)
    Z = np.full((cams.H, cams.W), np.inf, np.float32)
    used = 0
    for l, t, m in masks:
        h, w = m.shape
        sel = ok & (pi[:, 0] >= l) & (pi[:, 0] < l + w) & (pi[:, 1] >= t) & (pi[:, 1] < t + h)
        idx = np.flatnonzero(sel)
        idx = idx[m[pi[idx, 1] - t, pi[idx, 0] - l]]
        if idx.size < 5:
            continue
        z = np.float32(np.percentile(depth[idx], FRONT_PCT))
        x0, y0, x1, y1 = max(0, l), max(0, t), min(cams.W, l + w), min(cams.H, t + h)
        if x1 <= x0 or y1 <= y0:
            continue
        mm = m[y0 - t:y1 - t, x0 - l:x1 - l]
        view = Z[y0:y1, x0:x1]
        view[mm] = np.minimum(view[mm], z)
        used += 1
    return Z, used


def area_cm2(Z: np.ndarray, f_px: float) -> float:
    v = Z[np.isfinite(Z)].astype(np.float64)
    return round(float(((v / f_px) ** 2).sum()) / 100.0, 2)


def pair_inter(A, B) -> int:
    (la, ta, ma), (lb, tb, mb) = A, B
    x0, y0 = max(la, lb), max(ta, tb)
    x1, y1 = min(la + ma.shape[1], lb + mb.shape[1]), min(ta + ma.shape[0], tb + mb.shape[0])
    return int((ma[y0 - ta:y1 - ta, x0 - la:x1 - la] & mb[y0 - tb:y1 - tb, x0 - lb:x1 - lb]).sum()) if x1 > x0 and y1 > y0 else 0


def pair_iou(A, B) -> float:
    (la, ta, ma), (lb, tb, mb) = A, B
    x0, y0 = max(la, lb), max(ta, tb)
    x1, y1 = min(la + ma.shape[1], lb + mb.shape[1]), min(ta + ma.shape[0], tb + mb.shape[0])
    inter = int((ma[y0 - ta:y1 - ta, x0 - la:x1 - la] & mb[y0 - tb:y1 - tb, x0 - lb:x1 - lb]).sum()) if x1 > x0 and y1 > y0 else 0
    u = int(ma.sum()) + int(mb.sum()) - inter
    return inter / u if u else 0.0


def match(human: list, preds: list) -> tuple[np.ndarray, dict]:
    """IoU matrix (human x pred) and the Hungarian matches with IoU >= 0.5 (as train.py e2e)."""
    from scipy.optimize import linear_sum_assignment
    M = np.array([[pair_iou(H, Q) for Q in preds] for H in human]) if human and preds else np.zeros((len(human), len(preds)))
    got = {}
    if M.size:
        ri, ci = linear_sum_assignment(-M)
        got = {int(i): int(j) for i, j in zip(ri, ci) if M[i, j] >= IOU_MATCH}
    return M, got


def box_iou(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def ap50(dets: dict[str, list], gts: dict[str, list]) -> float:
    """Leaflet AP50 exactly as train.py ap50 (101-point interpolation, greedy matching in score order)."""
    P = sorted([(s, k, b) for k, ds in dets.items() for b, s in ds], key=lambda t: -t[0])
    n = sum(len(v) for v in gts.values())
    if n == 0 or not P:
        return 0.0
    used = {k: [False] * len(v) for k, v in gts.items()}
    tp = []
    for s, k, b in P:
        best, j = 0, -1
        for jj, gb in enumerate(gts.get(k, [])):
            o = box_iou(b, gb)
            if o > best and not used[k][jj]:
                best, j = o, jj
        tp.append(1 if best >= .5 else 0)
        if best >= .5:
            used[k][j] = True
    tp = np.array(tp)
    ctp = np.cumsum(tp)
    rec, prec = ctp / n, ctp / np.arange(1, len(tp) + 1)
    return float(np.mean([prec[rec >= t].max() if (rec >= t).any() else 0 for t in np.linspace(0, 1, 101)]))


def unpack_entry(z, key: str):
    l, t = (int(x) for x in z[f'{key}_lt'])
    return l, t, cc.unpack(z[f'{key}_shape'], z[f'{key}_bits'])


def paste(full: np.ndarray, l: int, t: int, m: np.ndarray, value=True) -> None:
    H, W = full.shape[:2]
    h, w = m.shape
    x0, y0, x1, y1 = max(0, l), max(0, t), min(W, l + w), min(H, t + h)
    if x1 > x0 and y1 > y0:
        full[y0:y1, x0:x1][m[y0 - t:y1 - t, x0 - l:x1 - l]] = value


class Store:
    """Kernel output + local inputs; per-photo vegetation masks cached under <out>/veg."""

    def __init__(self, out: Path):
        self.out = Path(out)
        inp = self.out / 'inputs'
        self.res = read_json(self.out / 'kout' / 'results.json')
        oidx = read_json(inp / 'organ' / 'index.json')
        self.classes = oidx['classes']
        self.LEAF = self.classes.index('leaflet')
        self.gt = {m['photo']: [g['xyxy'] for g in m['gt'] if g['cls'] == self.LEAF] for m in oidx['photos']}
        self.photos = {p: sorted(r['photo'] for r in oidx['images'] if r['variant'] == 'full' and r['plant'] == p) for p in PLANTS}
        self.plant_of = {ph: p for p, phs in self.photos.items() for ph in phs}
        self.crops = {p: self.res['plants'][p]['crops'] for p in PLANTS}
        self.wb = read_json(self.out / 'wb_gains.json')['photos']
        self.cams = {p: Cams(read_json(inp / 'al4' / f'capture_{p}.json')) for p in PLANTS}
        self.hull = {p: np.loadtxt(inp / 'al4' / f'hull_{p}.csv', delimiter=',', skiprows=1, usecols=(0, 1, 2), ndmin=2) for p in PLANTS}
        self.al4 = read_json(AL4_RESULTS)
        self.paths = photo_paths()
        self._human, self._masks, self._hu, self._veg = {}, {}, {}, {}

    @staticmethod
    def _evict(d: dict, keep: int = 18) -> None:
        """Bound the per-photo caches (this PC has little free memory): drop the oldest entries."""
        while len(d) >= keep:
            d.pop(next(iter(d)))

    def rec(self, ph: str) -> dict:
        return self.res['plants'][self.plant_of[ph]]['photos'][ph]

    def side_posed(self, plant: str) -> list[str]:
        return [ph for ph in self.photos[plant] if ph in self.cams[plant].frames and ph[-2:].startswith('2')]

    def human(self, ph: str) -> list:
        if ph not in self._human:
            f = self.out / 'kout' / 'masks' / f'human_{ph}.npz'
            if not f.exists():
                self._human[ph] = []
            else:
                z = np.load(f)
                keys = sorted({k.rsplit('_', 1)[0] for k in z.files}, key=lambda k: int(k[1:]))
                self._human[ph] = [unpack_entry(z, k) for k in keys]
        return self._human[ph]

    def masks(self, ph: str) -> dict:
        """{mask id: (left, top, shape, packed bits)} kept packed in memory; unpack with Store.mask."""
        if ph not in self._masks:
            self._evict(self._masks)
            z = np.load(self.out / 'kout' / 'masks' / f'{ph}.npz')
            self._masks[ph] = {k: (int(z[f'{k}_lt'][0]), int(z[f'{k}_lt'][1]), z[f'{k}_shape'], z[f'{k}_bits'])
                               for k in sorted({k.rsplit('_', 1)[0] for k in z.files})}
        return self._masks[ph]

    def mask(self, ph: str, key: str):
        l, t, shape, bits = self.masks(ph)[key]
        return l, t, cc.unpack(shape, bits)

    def human_union(self, ph: str) -> np.ndarray:
        if ph not in self._hu:
            self._evict(self._hu)
            hu = np.zeros((3024, 3024), bool)
            for l, t, m in self.human(ph):
                paste(hu, l, t, m)
            self._hu[ph] = cc.pack(hu)
        return cc.unpack(self._hu[ph]['shape'], self._hu[ph]['bits'])

    def veg(self, ph: str) -> dict:
        """{'<norm>|<method>': full-frame bool} for norms none/grayworld/board_wb; board_wb falls back to none (recorded)
        when the photo shows no board markers."""
        d = self.out / 'veg'
        d.mkdir(exist_ok=True)
        f = d / f'{ph}.npz'
        if not f.exists():
            rgb = np.asarray(Image.open(self.paths[ph]).convert('RGB'))
            store, info = {}, {}
            w = self.wb[ph]
            for norm in ('none', 'grayworld', 'board_wb'):
                g = dict(grayworld=w['grayworld_gains'], board_wb=w['gains']).get(norm)
                if norm == 'board_wb' and g is None:
                    info[norm] = 'fallback none (no board markers)'
                    im = rgb
                else:
                    im = cc.normalize(rgb, norm, g)
                    info[norm] = 'applied'
                for meth in cc.VEG_METHODS:
                    v, vi = cc.vegetation_mask(im, meth)
                    p = cc.pack(v)
                    store[f'{norm}|{meth}_shape'], store[f'{norm}|{meth}_bits'] = p['shape'], p['bits']
                    info[f'{norm}|{meth}'] = dict(vi, fraction=round(float(v.mean()), 5))
            store['info'] = np.array(json.dumps(info))
            np.savez_compressed(f, **store)
            self._preview(ph, rgb, store)
        if ph not in self._veg:
            self._evict(self._veg)
            z = np.load(f)
            keys = sorted({k.rsplit('_', 1)[0] for k in z.files if k != 'info'})
            self._veg[ph] = {k: (z[f'{k}_shape'], z[f'{k}_bits']) for k in keys}
        return self._veg[ph]

    def veg_mask(self, ph: str, key: str) -> np.ndarray:
        return cc.unpack(*self.veg(ph)[key])

    def veg_info(self, ph: str) -> dict:
        self.veg(ph)
        return json.loads(str(np.load(self.out / 'veg' / f'{ph}.npz')['info']))

    def _preview(self, ph: str, rgb: np.ndarray, store: dict) -> None:
        """PNG preview (quarter size): photo | ExG-ExR | vegetation ExG-ExR>0 | vegetation Otsu(ExG); and for the
        dwt_02 side photos the full-grid uint8 maps (ExG-ExR, a*, L*) as compressed arrays."""
        import cv2
        pv = self.out / 'previews'
        pv.mkdir(exist_ok=True)
        ix = cc.vegetation_indices(rgb)
        lo, hi = EXGR_Q
        q = np.clip(np.rint((ix['exgr'] - lo) / (hi - lo) * 255), 0, 255).astype(np.uint8)
        small = lambda a: cv2.resize(a, (a.shape[1] // 4, a.shape[0] // 4), interpolation=cv2.INTER_AREA)
        heat = cv2.cvtColor(cv2.applyColorMap(small(q), cv2.COLORMAP_VIRIDIS), cv2.COLOR_BGR2RGB)
        tiles = [small(rgb), heat]
        for meth in cc.VEG_METHODS:
            v = cc.unpack(store[f'none|{meth}_shape'], store[f'none|{meth}_bits'])
            tiles.append(np.repeat(small(v.astype(np.uint8) * 255)[..., None], 3, 2))
        Image.fromarray(np.hstack(tiles)).save(pv / f'{ph}_cues.png', optimize=True)
        if ph.startswith('dwt_02') and ph[-2:].startswith('2'):
            L, a = cc.lab_lightness_a(rgb)
            md = self.out / 'maps'
            md.mkdir(exist_ok=True)
            np.savez_compressed(md / f'{ph}_maps_u8.npz', exgr=q, a=np.clip(np.rint(a + 128), 0, 255).astype(np.uint8),
                                L=np.clip(np.rint(L * 2.55), 0, 255).astype(np.uint8),
                                scales=np.array(json.dumps(dict(exgr=f'value = {lo} + u8/255*{hi - lo}', a='a* = u8 - 128',
                                                                L='L* = u8 / 2.55'))))


# ------------------------------------------------------------------------------------------------------------ arms
def arm_key(arm: dict) -> str:
    return json.dumps({k: arm[k] for k in sorted(arm) if arm[k] not in (None, False, 'none')}, sort_keys=True) or '{}'


BASELINE = dict(variant='none', trim=None, fp=None, dup=None, split=None, prop=None, judge_colour=False)


def arm(**kw) -> dict:
    a = dict(BASELINE)
    bad = set(kw) - set(a)
    if bad:
        raise ValueError(f'unknown arm fields {bad}')
    a.update(kw)
    return a


def crop_veg(veg: np.ndarray, l: int, t: int, m: np.ndarray, radius_px: int) -> np.ndarray:
    """Vegetation dilated by radius_px, cut to the mask's window (dilation sees radius_px of context outside it)."""
    h, w = m.shape
    r = int(radius_px)
    big = cc.crop_view(veg, l - r, t - r, h + 2 * r, w + 2 * r)
    return cc.dilate(big, r)[r:r + h, r:r + w]


def judge_row(plant: str, ph: str, uid: str, box: list, draft: dict, boxes: list, colour: dict | None) -> dict:
    from tools import decision_learning as dl
    x0, y0, x1, y1 = box
    it = dict(id=uid, image_file=ph, source_bbox_xywh_px=[x0, y0, x1 - x0, y1 - y0], image_size_px=[3024, 3024],
              review='unreviewed', view_group=VIEW_GROUP.get(ph[-2], 'unknown'))
    row = dl._row(plant, it, draft['scores'], draft['default_candidate'], draft['risk'],
                  {ph: [(f'b{k}', [b[0], b[1], b[2] - b[0], b[3] - b[1]]) for k, b in enumerate(boxes)] + [(uid, it['source_bbox_xywh_px'])]})
    row.update({k: (colour or {}).get(k, np.nan) for k in JUDGE_COLOUR})
    return row


class Judge:
    """The mask judge (tools.decision_learning: HistGradientBoosting, auto-accept threshold for 95 % precision from
    inner leave-one-plant-out predictions) refit on the redraft rows of the allowed plants only."""

    def __init__(self, store: Store, out: Path):
        from tools import decision_learning as dl
        self.dl = dl
        cfg = read_json(dl.CONFIG)
        rows = dl.redraft_rows(cfg, ROOT / 'build' / 'mask_redraft_20260930' / 'kout' / 'redraft.json')
        kred = store.res.get('redraft', {})
        for r in rows:
            r.update({k: kred.get(r['id'], {}).get('colour', {}).get(k, np.nan) for k in JUDGE_COLOUR})
        self.rows = rows
        self.cache = {}

    def features(self, colour: bool) -> list[str]:
        return self.dl.MASK_FEATURES + (JUDGE_COLOUR if colour else [])

    def model(self, exclude: frozenset, colour: bool):
        key = (exclude, colour)
        if key not in self.cache:
            from sklearn.model_selection import cross_val_predict
            rows = [r for r in self.rows if r['plant'] not in exclude]
            feats = self.features(colour)
            X = np.array([[r[f] for f in feats] for r in rows], float)
            y = np.array([r['label'] for r in rows])
            g = np.array([r['plant'] for r in rows])
            inner = cross_val_predict(self.dl._model(), X, y, groups=g, cv=self.dl._group_cv(g), method='predict_proba')[:, 1]
            hi, _ = self.dl._thresholds(inner, y)
            self.cache[key] = (self.dl._model().fit(X, y), hi, feats)
        return self.cache[key]

    def prob(self, rows: list[dict], exclude: frozenset, colour: bool) -> tuple[np.ndarray, float]:
        m, hi, feats = self.model(exclude, colour)
        if not rows:
            return np.zeros(0), hi
        return m.predict_proba(np.array([[r[f] for f in feats] for r in rows], float))[:, 1], hi

    def lopo_report(self, colour: bool) -> dict:
        return self.dl.evaluate(self.rows, self.features(colour))


def run_photo(store: Store, judge: Judge | None, ph: str, a: dict, exclude: frozenset) -> dict:
    """Apply one arm to one photo. Returns small numbers only (cached by the caller)."""
    plant = store.plant_of[ph]
    rec = store.rec(ph)
    human = store.human(ph)
    hu = store.human_union(ph)
    vcache = {}

    def V(key):
        if key not in vcache:
            vcache[key] = store.veg_mask(ph, key)
        return vcache[key]
    dets = [(c, b, s) for c, b, s in rec['detections'][a['variant']]]
    drop = set()
    entries = [e for e in rec['masks'][a['variant']]]
    # C: false-positive filter on the vegetation overlap of the mask (original-photo vegetation, kernel features)
    if a['fp']:
        meth, tau = a['fp']
        for e in entries:
            gf = (e.get('mask_colour') or {}).get(f'green_fraction_{meth}')
            if gf is not None and gf < tau:
                drop.add(e['det_index'])
    kept = [e for e in entries if e['det_index'] not in drop and e['mask']]
    items = [dict(uid=e['mask'], det_index=e['det_index'], box=e['box'], score=e['score'], draft=e['draft'],
                  colour=e.get('draft_colour'), origin='detector', lt_m=store.mask(ph, e['mask'])) for e in kept]
    removed_px = removed_in_human_px = 0
    # B: trim to dilated vegetation
    if a['trim']:
        norm, meth, rad = a['trim']
        v = V(f'{norm}|{meth}')
        for it in items:
            l, t, m = it['lt_m']
            tm = m & crop_veg(v, l, t, m, rad)
            gone = m & ~tm
            removed_px += int(gone.sum())
            removed_in_human_px += int((gone & cc.crop_view(hu, l, t, *m.shape)).sum())
            it['lt_m'] = (l, t, tm)
    # D: duplicates (lower score overlapping kept masks) and veg-component split of merged masks
    if a['dup'] is not None:
        frac = a['dup']
        occ = np.zeros((3024, 3024), bool)
        keep2 = []
        for it in sorted(items, key=lambda x: -x['score']):
            l, t, m = it['lt_m']
            n = int(m.sum())
            ov = int((m & cc.crop_view(occ, l, t, *m.shape)).sum())
            if n and ov / n >= frac:
                drop.add(it['det_index'])
                continue
            paste(occ, l, t, m)
            keep2.append(it)
        items = keep2
    new_boxes = {}
    if a['split'] is not None:
        import cv2
        v = V('none|exgr_zero') if not a['trim'] else V(f"{a['trim'][0]}|{a['trim'][1]}")
        out = []
        for it in items:
            l, t, m = it['lt_m']
            mv = m & cc.crop_view(v, l, t, *m.shape)
            n_all = int(mv.sum())
            if n_all == 0 or cc.large_components(mv, a['split']) < 2:
                out.append(it)
                continue
            n, labs, st, _ = cv2.connectedComponentsWithStats(mv.astype(np.uint8), connectivity=8)
            parts = [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] >= a['split'] * n_all]
            rest = m & ~np.isin(labs, parts)  # pixels of the mask outside the large parts stay with the largest part
            biggest = max(parts, key=lambda k: st[k, cv2.CC_STAT_AREA])
            boxes = []
            for k in parts:
                pm = labs == k
                if k == biggest:
                    pm = pm | rest
                ys, xs = np.nonzero(pm)
                b = [float(l + xs.min()), float(t + ys.min()), float(l + xs.max() + 1), float(t + ys.max() + 1)]
                boxes.append(b)
                out.append(dict(it, uid=f"{it['uid']}s{k}", box=b, lt_m=(l, t, pm)))
            new_boxes[it['det_index']] = boxes
        items = out
    # E: colour proposals, only when the mask judge (refit without the excluded plants) accepts them
    props = dict(candidates=0, accepted=0)
    leaf_boxes = [it['box'] for it in items]
    if a['prop']:
        min_unc, min_px = a['prop']
        vinfo = store.veg_info(ph)
        cand = [p for p in rec['proposals'] if p['mask'] and p['uncovered'] >= min_unc and p['component_px'] >= min_px
                and p['component_px'] <= PROP_MAX_FRACTION * 3024 * 3024
                and not vinfo[f"none|{p['veg_method']}"].get('degenerate', vinfo[f"none|{p['veg_method']}"]['fraction'] > cc.VEG_DEGENERATE_FRACTION)]
        props['candidates'] = len(cand)
        rows = [judge_row(plant, ph, p['id'], p['box'], p['draft'], leaf_boxes, p.get('draft_colour')) for p in cand]
        pr, thr = judge.prob(rows, exclude, a['judge_colour'])
        for p, pi in zip(cand, pr):
            if pi < thr:
                continue
            l, t, m = store.mask(ph, p['mask'])
            if a['trim']:
                norm, meth, rad = a['trim']
                m = m & crop_veg(V(f'{norm}|{meth}'), l, t, m, rad)
            items.append(dict(uid=p['id'], det_index=None, box=p['box'], score=float(pi), draft=p['draft'],
                              colour=p.get('draft_colour'), origin='color_proposal', lt_m=(l, t, m)))
            props['accepted'] += 1
    # outputs
    preds = [it['lt_m'] for it in items if it['lt_m'][2].any()]
    origins = [it['origin'] for it in items if it['lt_m'][2].any()]
    Mx, got = match(human, preds)
    e2e = [float(Mx[i, got[i]]) if i in got else 0.0 for i in range(len(human))]
    best = Mx.max(0) if Mx.size else np.zeros(len(preds))
    props['matched'] = int(sum(1 for o, b in zip(origins, best) if o == 'color_proposal' and b >= IOU_MATCH))
    leaf_dets = []
    for k, (c, b, s) in enumerate(dets):
        if c != store.LEAF or k in drop:
            continue
        for bb in new_boxes.get(k, [b]):
            leaf_dets.append((bb, s))
    out = dict(e2e=e2e, leaf_dets=leaf_dets, removed_px=removed_px, removed_in_human_px=removed_in_human_px,
               human_px=int(hu.sum()), props=props, n_masks=len(preds),
               n_detector_masks=sum(1 for o in origins if o == 'detector'))
    if ph in store.side_posed(plant):
        cams, hull = store.cams[plant], store.hull[plant]
        Z, _ = depth_map(cams, hull, ph, preds)
        out['area_cm2'] = area_cm2(Z, float(cams.K[0, 0]))
    out['_judge_items'] = [(it, b >= IOU_MATCH) for it, b in zip([i for i in items if i['lt_m'][2].any()], best)]
    return out


class Evaluator:
    def __init__(self, store: Store, judge: Judge):
        self.s, self.judge = store, judge
        self.cache = {}
        self.truth = {}

    def photo(self, ph: str, a: dict, exclude: frozenset) -> dict:
        key = (ph, arm_key(a), exclude if a['prop'] else None)
        if key not in self.cache:
            r = run_photo(self.s, self.judge, ph, a, exclude)
            r.pop('_judge_items')
            self.cache[key] = r
        return self.cache[key]

    def human_area(self, plant: str) -> dict:
        if plant not in self.truth:
            cams, hull = self.s.cams[plant], self.s.hull[plant]
            self.truth[plant] = {ph: area_cm2(depth_map(cams, hull, ph, self.s.human(ph))[0], float(cams.K[0, 0]))
                                 for ph in self.s.side_posed(plant)}
        return self.truth[plant]

    def plant(self, plant: str, a: dict, exclude: frozenset) -> dict:
        phs = self.s.photos[plant]
        R = {ph: self.photo(ph, a, exclude) for ph in phs}
        ap = ap50({ph: R[ph]['leaf_dets'] for ph in phs}, {ph: self.s.gt.get(ph, []) for ph in phs})
        e2e = [v for ph in phs for v in R[ph]['e2e']]
        truth = self.human_area(plant)
        side = [ph for ph in self.s.side_posed(plant)]
        model_mean = float(np.mean([R[ph]['area_cm2'] for ph in side]))
        human_mean = float(np.mean([truth[ph] for ph in side]))
        per_photo = {ph: dict(model=R[ph]['area_cm2'], human=truth[ph], err_pct=100 * (R[ph]['area_cm2'] / truth[ph] - 1)) for ph in side}
        hum_px = sum(R[ph]['human_px'] for ph in phs)
        return dict(ap50=round(ap, 4), e2e_iou=round(float(np.mean(e2e)), 4) if e2e else None,
                    e2e_recall=round(float(np.mean([v >= IOU_MATCH for v in e2e])), 4) if e2e else None,
                    sam_iou=self.sam_iou(plant, a), area_model=round(model_mean, 2), area_human=round(human_mean, 2),
                    area_err_pct=round(100 * (model_mean / human_mean - 1), 2), per_photo=per_photo,
                    photo_err_spread_pp=round(float(np.std([v['err_pct'] for v in per_photo.values()])), 2),
                    removed_px=sum(R[ph]['removed_px'] for ph in phs),
                    removed_in_human_px=sum(R[ph]['removed_in_human_px'] for ph in phs), human_px=hum_px,
                    removed_in_human_frac=round(sum(R[ph]['removed_in_human_px'] for ph in phs) / max(hum_px, 1), 5),
                    proposals=dict(candidates=sum(R[ph]['props']['candidates'] for ph in phs),
                                   accepted=sum(R[ph]['props']['accepted'] for ph in phs),
                                   matched_human=sum(R[ph]['props']['matched'] for ph in phs)),
                    masks=sum(R[ph]['n_masks'] for ph in phs))

    def sam_iou(self, plant: str, a: dict) -> float:
        vals = []
        for r in self.s.crops[plant]:
            if a['trim']:
                norm, meth, rad = a['trim']
                k = f'{norm}|{meth}|{rad}'
                v = r['trim'].get(k, r['trim'].get(f'none|{meth}|{rad}'))
                vals.append(v[0])
            else:
                vals.append(r['iou'])
        return round(float(np.mean(vals)), 4)

    def judge_stats(self, plant: str, a: dict) -> dict:
        """Auto-accept share and precision of the judge (refit without this plant) on the arm's final masks;
        'correct' = the mask overlaps a human mask with IoU >= 0.5."""
        rows, ok = [], []
        for ph in self.s.photos[plant]:
            r = run_photo(self.s, self.judge, ph, a, frozenset({plant}))
            boxes = [it['box'] for it, _ in r['_judge_items'] if it['origin'] == 'detector']
            for it, good in r['_judge_items']:
                rows.append(judge_row(plant, ph, it['uid'], it['box'], it['draft'], [b for b in boxes if b != it['box']], it['colour']))
                ok.append(bool(good))
        p, thr = self.judge.prob(rows, frozenset({plant}), a['judge_colour'])
        acc = p >= thr
        ok = np.array(ok)
        return dict(masks=len(ok), auto_accept_rate=round(float(acc.mean()), 4) if len(ok) else None,
                    auto_accept_precision=round(float(ok[acc].mean()), 4) if acc.any() else None, threshold=round(thr, 4),
                    correct_share_all=round(float(ok.mean()), 4) if len(ok) else None)


def objective(ev: Evaluator, a: dict, train: list[str], held: str | None) -> float:
    """Mean |area error| over the training plants; inf if any training plant breaks the acceptance constraints
    relative to its own baseline. The judge used for proposals never sees the held-out plant or the scored plant."""
    errs = []
    for p in train:
        ex = frozenset({p, held}) if held else frozenset({p})
        r, b = ev.plant(p, a, ex), ev.plant(p, BASELINE, ex)
        if r['ap50'] < b['ap50'] - MAX_AP_DROP or r['removed_in_human_frac'] > MAX_REMOVED_INSIDE:
            return float('inf')
        errs.append(abs(r['area_err_pct']))
    return float(np.mean(errs))


def grids() -> dict[str, list[dict]]:
    """Candidate settings per arm; the first entry of each list is the most conservative (= off)."""
    trims = [(n, m, r) for n in ('none', 'grayworld', 'board_wb') for m in cc.VEG_METHODS for r in (0, 2, 4, 8, 16)]
    return dict(
        A=[arm(variant=v) for v in ('none', 'grayworld', 'board_wb', 'clahe', 'gauss5')],
        B=[BASELINE] + [arm(trim=t) for t in trims],
        C=[BASELINE] + [arm(fp=(m, tau)) for m in cc.VEG_METHODS for tau in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)],
        D=[BASELINE] + [arm(dup=f) for f in (0.9, 0.7, 0.5)] + [arm(split=f) for f in (0.4, 0.25)]
          + [arm(dup=f, split=s) for f in (0.7, 0.5) for s in (0.4, 0.25)],
        E=[BASELINE] + [arm(prop=(u, px)) for u in (0.9, 0.7, 0.5) for px in (5000, 1500, 400)],
        F=[BASELINE, arm(judge_colour=True)],  # judge features only; with E it changes which proposals pass
    )


def combine(parts: list[dict]) -> dict:
    a = dict(BASELINE)
    for p in parts:
        for k, v in p.items():
            if v != BASELINE[k]:
                a[k] = v
    return a


# ------------------------------------------------------------------------------------------------------- reporting
def baseline_check(store: Store, ev: Evaluator) -> dict:
    """Step 1.2: the kernel's baseline must reproduce AL4 step_0 (AL4_RESULTS.md) within rounding."""
    out, ok = {}, True
    tol = dict(ap50=0.002, sam_iou=0.002, e2e_iou=0.002, area_pct=0.5)
    for p in PLANTS:
        ref = store.al4['plants'][p]['steps']['step_0']
        truth = store.al4['plants'][p]['truth']['human_trait']
        r = ev.plant(p, BASELINE, frozenset({p}))
        got = dict(ap50=r['ap50'], sam_iou=r['sam_iou'], e2e_iou=r['e2e_iou'], area_model=r['area_model'], area_human=r['area_human'])
        want = dict(ap50=ref['uncorrected']['detector']['leaflet']['ap50'], sam_iou=ref['uncorrected']['sam_mean_iou'],
                    e2e_iou=ref['uncorrected']['end_to_end']['mean_iou_missed_as_zero'], area_model=ref['trait']['side_mean_cm2'],
                    area_human=truth['side_mean_cm2'])
        diffs = dict(ap50=abs(got['ap50'] - want['ap50']), sam_iou=abs(got['sam_iou'] - want['sam_iou']),
                     e2e_iou=abs(got['e2e_iou'] - want['e2e_iou']),
                     area_model_pct=100 * abs(got['area_model'] / want['area_model'] - 1),
                     area_human_pct=100 * abs(got['area_human'] / want['area_human'] - 1))
        within = (diffs['ap50'] <= tol['ap50'] and diffs['sam_iou'] <= tol['sam_iou'] and diffs['e2e_iou'] <= tol['e2e_iou']
                  and diffs['area_model_pct'] <= tol['area_pct'] and diffs['area_human_pct'] <= tol['area_pct'])
        ok &= within
        per = {ph[-2:]: v['model'] for ph, v in r['per_photo'].items()}
        out[p] = dict(reproduced=got, reference=want, abs_diff={k: round(v, 4) for k, v in diffs.items()}, within_tolerance=within,
                      per_photo_model=per, per_photo_reference=ref['trait']['per_photo'],
                      area_err_pct=r['area_err_pct'])
    return dict(schema='color-cues-baseline-check-1', tolerance=tol, all_within=ok, plants=out,
                reference=str(AL4_RESULTS.relative_to(ROOT)), reference_sha256=file_hash(AL4_RESULTS))


def attribution(store: Store, ph: str) -> list[dict]:
    """Step 1.3: split |model area| - |human area| of one posed photo (baseline masks) into components.
    Pixels: P = union of model leaflet masks, H = union of human masks. Each prediction is TP (Hungarian IoU >= 0.5),
    duplicate (unmatched, >= 50 % of it inside a human mask already matched by another prediction), merged (unmatched,
    covering >= 20 % of each of >= 2 human masks), false positive (unmatched, < 20 % of it on human leaflets) or partial.
    P-H pixels: (a) bleed if under a TP/partial mask, else (c) duplicate/merged, else (b) false positive.
    H-P pixels: (e) under-segmentation if in a matched human mask, else (d) missed leaflet.
    mm2: P-only pixels at the model depth, H-only pixels at the human depth, shared pixels give (f) depth assignment
    (model minus human depth^2); the components sum to model area - human area exactly."""
    plant = store.plant_of[ph]
    rec = store.rec(ph)
    preds = [store.mask(ph, e['mask']) for e in rec['masks']['none'] if e['mask']]
    human = store.human(ph)
    Mx, got = match(human, preds)
    matched_pred = set(got.values())
    kind = []
    inter = np.array([[pair_inter(H, Q) for Q in preds] for H in human]) if human and preds else np.zeros((len(human), len(preds)))
    hum_cov = inter / np.maximum(np.array([h[2].sum() for h in human], float), 1)[:, None] if len(human) else inter
    hu = store.human_union(ph)
    for j, Q in enumerate(preds):
        l, t, m = Q
        n = max(int(m.sum()), 1)
        inside = int((m & cc.crop_view(hu, l, t, *m.shape)).sum()) / n
        if j in matched_pred:
            kind.append('tp')
        elif inside < FP_INSIDE_MAX:
            kind.append('false_positive')
        elif (hum_cov[:, j] >= MERGE_COVER_MIN).sum() >= 2:
            kind.append('merged')
        elif any(i in got and got[i] != j and inter[i, j] / n >= 0.5 for i in range(len(human))):
            kind.append('duplicate')
        else:
            kind.append('partial')
    full = {k: np.zeros((3024, 3024), bool) for k in ('good', 'dupmerge', 'fp')}
    for (l, t, m), k in zip(preds, kind):
        paste(full['good' if k in ('tp', 'partial') else 'dupmerge' if k in ('duplicate', 'merged') else 'fp'], l, t, m)
    P = full['good'] | full['dupmerge'] | full['fp']
    matched_h = np.zeros((3024, 3024), bool)
    for i in got:
        paste(matched_h, *human[i])
    comp = {
        'a_background_bleed': P & ~hu & full['good'],
        'b_false_positive': P & ~hu & ~full['good'] & ~full['dupmerge'] & full['fp'],
        'c_duplicate_merged': P & ~hu & ~full['good'] & full['dupmerge'],
        'd_missed_leaflets': hu & ~P & ~matched_h,
        'e_under_segmentation': hu & ~P & matched_h,
    }
    sign = dict(a_background_bleed=1, b_false_positive=1, c_duplicate_merged=1, d_missed_leaflets=-1, e_under_segmentation=-1)
    rows = []
    cams = store.cams[plant]
    posed = ph in cams.frames
    if posed:
        f = float(cams.K[0, 0])
        Zp = depth_map(cams, store.hull[plant], ph, preds)[0]
        Zh = depth_map(cams, store.hull[plant], ph, human)[0]
        # the S8 area counts only pixels with a hull depth; attribution follows it
        wp = np.where(np.isfinite(Zp), (Zp / f) ** 2, 0.0)
        wh = np.where(np.isfinite(Zh), (Zh / f) ** 2, 0.0)
    for name, m in comp.items():
        mm2 = None
        if posed:
            mm2 = float((wp if sign[name] > 0 else wh)[m].sum()) * sign[name]
        rows.append(dict(plant=plant, photo=ph, component=name, pixels=int(m.sum()) * sign[name], mm2=None if mm2 is None else round(mm2, 2)))
    if posed:
        both = P & hu
        rows.append(dict(plant=plant, photo=ph, component='f_depth_assignment', pixels=0, mm2=round(float((wp[both] - wh[both]).sum()), 2)))
        rows.append(dict(plant=plant, photo=ph, component='total_model_minus_human', pixels=int(P.sum()) - int(hu.sum()),
                         mm2=round(float(wp.sum() - wh.sum()), 2)))
    else:
        rows.append(dict(plant=plant, photo=ph, component='total_model_minus_human', pixels=int(P.sum()) - int(hu.sum()), mm2=None))
    counts = {k: kind.count(k) for k in ('tp', 'partial', 'duplicate', 'merged', 'false_positive')}
    for k, v in counts.items():
        rows.append(dict(plant=plant, photo=ph, component=f'n_pred_{k}', pixels=v, mm2=None))
    rows.append(dict(plant=plant, photo=ph, component='n_human_missed', pixels=len(human) - len(got), mm2=None))
    return rows


def _full(entry) -> np.ndarray:
    l, t, m = entry
    f = np.zeros((3024, 3024), bool)
    paste(f, l, t, m)
    return f


def write_csv(path: Path, rows: list[dict]) -> None:
    import csv
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def plant_rows(arm_name: str, plant: str, r: dict, judge: dict | None) -> list[dict]:
    out = [dict(plant=plant, photo='ALL', arm=arm_name, metric=k, value=r[k]) for k in
           ('ap50', 'sam_iou', 'e2e_iou', 'e2e_recall', 'area_model', 'area_human', 'area_err_pct', 'photo_err_spread_pp',
            'removed_px', 'removed_in_human_px', 'removed_in_human_frac', 'masks')]
    out += [dict(plant=plant, photo='ALL', arm=arm_name, metric=f'proposals_{k}', value=v) for k, v in r['proposals'].items()]
    for ph, v in r['per_photo'].items():
        out += [dict(plant=plant, photo=ph, arm=arm_name, metric=f'area_{k}', value=round(x, 3)) for k, x in v.items()]
    if judge:
        out += [dict(plant=plant, photo='ALL', arm=arm_name, metric=f'judge_{k}', value=v) for k, v in judge.items()]
    return out


def accept(base: dict, cand: dict) -> dict:
    """The handoff's acceptance rules for making an arm the new default (held-out results per plant)."""
    mb = np.mean([abs(base[p]['area_err_pct']) for p in PLANTS])
    mc = np.mean([abs(cand[p]['area_err_pct']) for p in PLANTS])
    checks = dict(
        mean_abs_area_err_decreases=bool(mc < mb),
        dwt_02_abs_err_decreases=bool(abs(cand['dwt_02']['area_err_pct']) < abs(base['dwt_02']['area_err_pct'])),
        no_plant_worse_than_2pp=all(abs(cand[p]['area_err_pct']) - abs(base[p]['area_err_pct']) <= MAX_PLANT_WORSENING_PP for p in PLANTS),
        ap50_drop_le_001=all(cand[p]['ap50'] >= base[p]['ap50'] - MAX_AP_DROP for p in PLANTS),
        sam_iou_mean_not_lower=bool(np.mean([cand[p]['sam_iou'] for p in PLANTS]) >= np.mean([base[p]['sam_iou'] for p in PLANTS]) - 1e-9),
        e2e_iou_mean_not_lower=bool(np.mean([cand[p]['e2e_iou'] for p in PLANTS]) >= np.mean([base[p]['e2e_iou'] for p in PLANTS]) - 1e-9),
        removed_inside_le_2pct=all(cand[p]['removed_in_human_frac'] <= MAX_REMOVED_INSIDE for p in PLANTS))
    return dict(mean_abs_area_err_baseline=round(float(mb), 2), mean_abs_area_err=round(float(mc), 2), checks=checks,
                accepted=all(checks.values()))


def evaluate(out: Path, stop_on_mismatch: bool = True) -> dict:
    out = Path(out)
    store = Store(out)
    judge = Judge(store, out)
    ev = Evaluator(store, judge)
    log = lambda *a: print(*a, file=sys.stderr, flush=True)
    # ---- step 1: baseline reproduction
    bc = baseline_check(store, ev)
    write_json(out / 'baseline_check.json', bc)
    log('baseline within tolerance:', bc['all_within'])
    if not bc['all_within'] and stop_on_mismatch:
        raise SystemExit('baseline does not reproduce AL4 step_0; see baseline_check.json')
    # ---- step 1.3: error attribution (every photo; mm2 where the photo has a board pose)
    rows = []
    for p in PLANTS:
        for ph in store.photos[p]:
            rows += attribution(store, ph)
        log('attribution', p)
    write_csv(out / 'error_attribution.csv', rows)
    # ---- step 2 previews/vegetation for every photo (cached by Store.veg)
    for p in PLANTS:
        for ph in store.photos[p]:
            store.veg(ph)
    # ---- step 3: arms, LOPO selection
    G = grids()
    folds, held_results, arm_rows = {}, {}, []
    base = {p: ev.plant(p, BASELINE, frozenset({p})) for p in PLANTS}
    held_results['baseline'] = {p: dict(arm=BASELINE, **base[p]) for p in PLANTS}
    for p in PLANTS:
        arm_rows += plant_rows('baseline', p, base[p], ev.judge_stats(p, BASELINE))
    for name, grid in G.items():
        sel = cc.lopo_select(lambda a, train, _n=name: objective(ev, a, train, _held(train)), grid, PLANTS)
        folds[name] = {h: dict(arm=v['param'], train_plants=v['train_plants'], train_mean_abs_area_err=v['train_score'])
                       for h, v in sel.items()}
        held_results[name] = {}
        for h, v in sel.items():
            r = ev.plant(h, v['param'], frozenset({h}))
            held_results[name][h] = dict(arm=v['param'], **r)
            arm_rows += plant_rows(name, h, r, ev.judge_stats(h, v['param']))
        log('arm', name, {h: arm_key(v['param']) for h, v in sel.items()})
    # ---- G: forward selection over the per-fold choices of A-F, on the training plants only
    folds['G'], held_results['G'] = {}, {}
    for h in PLANTS:
        train = [p for p in PLANTS if p != h]
        cands = {n: folds[n][h]['arm'] for n in G if folds[n][h]['arm'] != BASELINE}
        if 'E' in cands:  # F only acts through proposals: offer E with the colour judge as well
            cands['E+F'] = combine([cands['E'], arm(judge_colour=True)])
        cur, cur_s, used = dict(BASELINE), objective(ev, BASELINE, train, h), []
        while True:
            trials = [(objective(ev, combine([cur, c]), train, h), n) for n, c in cands.items() if n not in used]
            if not trials:
                break
            s_, n_ = min(trials)
            if s_ >= cur_s:
                break
            cur, cur_s = combine([cur, cands[n_]]), s_
            used.append(n_)
        folds['G'][h] = dict(arm=cur, components=used, train_plants=train, train_mean_abs_area_err=cur_s)
        r = ev.plant(h, cur, frozenset({h}))
        held_results['G'][h] = dict(arm=cur, **r)
        arm_rows += plant_rows('G', h, r, ev.judge_stats(h, cur))
        log('G', h, used)
    write_csv(out / 'arm_results.csv', arm_rows)
    write_json(out / 'fold_thresholds.json', dict(
        schema='color-cues-folds-1', objective='mean |area error %| over the three training plants; a setting is excluded '
        'if any training plant loses > 0.01 leaflet AP50 or has > 2 % of its human-mask pixels removed; ties keep the '
        'earlier (more conservative) setting; the judge used for proposals is refit without the held-out and the scored plant',
        folds={n: {h: dict(v, arm_key=arm_key(v['arm'])) for h, v in f.items()} for n, f in folds.items()}))
    acc = {n: accept(base, {p: held_results[n][p] for p in PLANTS}) for n in held_results if n != 'baseline'}
    judge_lopo = dict(baseline=judge.lopo_report(False)['overall'], with_colour=judge.lopo_report(True)['overall'])
    summary = dict(schema='color-cues-summary-1', acceptance=acc, judge_lopo_on_reviewed_items=judge_lopo,
                   held_out={n: {p: {k: v for k, v in r.items() if k not in ('per_photo',)} for p, r in res.items()}
                             for n, res in held_results.items()})
    # ---- step 4b: dwt_test shift (no ground truth) for baseline and the best arm, refit on all four plants
    ranked = sorted([n for n in acc], key=lambda n: (not acc[n]['accepted'], acc[n]['mean_abs_area_err']))
    best = ranked[0]
    final = final_setting(ev, G, best)
    summary['best_arm'] = dict(name=best, accepted=acc[best]['accepted'], final_setting_all_plants=final, final_key=arm_key(final))
    write_json(out / 'summary.json', summary)
    shift = dwt_test_shift(out, {'baseline': BASELINE, f'{best}_final': final})
    write_csv(out / 'dwt_test_shift.csv', shift)
    return summary


def final_setting(ev: Evaluator, G: dict, name: str) -> dict:
    """The setting a new plant would get: chosen with the same objective on all four plants (no held-out plant)."""
    if name != 'G':
        return min(G[name], key=lambda a: (objective(ev, a, list(PLANTS), None), G[name].index(a)))
    cands = {n: final_setting(ev, G, n) for n in G}
    cands = {n: c for n, c in cands.items() if c != BASELINE}
    if 'E' in cands:
        cands['E+F'] = combine([cands['E'], arm(judge_colour=True)])
    cur, cur_s, used = dict(BASELINE), objective(ev, BASELINE, list(PLANTS), None), []
    while True:
        trials = [(objective(ev, combine([cur, c]), list(PLANTS), None), n) for n, c in cands.items() if n not in used]
        if not trials:
            return cur
        s_, n_ = min(trials)
        if s_ >= cur_s:
            return cur
        cur, cur_s = combine([cur, cands[n_]]), s_
        used.append(n_)


DWT_TEST = ROOT / 'build' / 'plants_dwt_test_20261002' / 'plants'
POST_HOC = ('trim', 'fp', 'dup', 'split')   # arms that act on existing masks; A (detector input) and E (SAM) need inference


def dwt_test_shift(out: Path, arms: dict[str, dict]) -> list[dict]:
    """Step 4b: baseline vs arm on the production masks of dwt_test T1-T3 (plant_auto, organ v4 + SAM v5, judge),
    without ground truth: number of masks, mask pixels (projected, no depth), pixels removed. Non-rejected masks are
    what S8 sums. Only post-hoc arms (B, C, D) can be applied without new inference; others are reported as such."""
    from tools import leaflet_mask_batch as lmb
    rows = []
    for t in ('dwt_t1', 'dwt_t2', 'dwt_t3'):
        batch = lmb.Batch(DWT_TEST / t / 'masks')
        items = [it for it in (read_json(f) for f in sorted((DWT_TEST / t / 'masks' / 'items').glob('*.json')))
                 if it['generation'] == 'ready' and it['review'] != 'rejected' and it.get('cache_key')]
        by = {}
        for it in items:
            by.setdefault(it['image_file'], []).append(it)
        ratio = cc.board_spec_ratio(batch.session / 'board_spec.snapshot.json') if (batch.session / 'board_spec.snapshot.json').exists() \
            else cc.board_spec_ratio()
        for img, its in sorted(by.items()):
            rgb = np.asarray(Image.open(batch.session / its[0]['image_path']).convert('RGB'))
            gains = dict(board_wb=cc.board_white_gains(rgb, ratio)['gains'], grayworld=cc.grayworld_gains(rgb))
            vegs, maps = {}, cc.feature_maps(rgb)
            def V(norm, meth):
                if (norm, meth) not in vegs:
                    g = gains.get(norm)
                    vegs[(norm, meth)] = cc.vegetation_mask(rgb if norm == 'none' or g is None else cc.normalize(rgb, norm, g), meth)[0]
                return vegs[(norm, meth)]
            masks = []
            for it in its:
                m, meta = batch.mask(it)
                l, t0 = meta['crop_px'][:2]
                masks.append(dict(id=it['id'], l=int(l), t=int(t0), m=m, score=float(max(s for s in meta['scores'] if s is not None))))
            for name, a in arms.items():
                if a['variant'] != 'none' or a['prop']:
                    rows.append(dict(plant=t, photo=Path(img).stem, arm=name, metric='not_computed',
                                     value='needs new inference (detector input / SAM proposals)'))
                    continue
                kept, removed = [], 0
                for e in masks:
                    m = e['m']
                    if a['fp']:
                        meth, tau = a['fp']
                        f = cc.mask_features(m, cc.crop_view(V('none', meth), e['l'], e['t'], *m.shape),
                                             {k: cc.crop_view(v, e['l'], e['t'], *m.shape, 0.0) for k, v in maps.items()}, 10)
                        if m.any() and f['green_fraction'] < tau:
                            removed += int(m.sum())
                            continue
                    if a['trim']:
                        norm, meth, rad = a['trim']
                        tm = m & crop_veg(V(norm, meth), e['l'], e['t'], m, rad)
                        removed += int((m & ~tm).sum())
                        m = tm
                    kept.append(dict(e, m=m))
                if a['dup'] is not None:
                    occ = np.zeros(rgb.shape[:2], bool)
                    k2 = []
                    for e in sorted(kept, key=lambda x: -x['score']):
                        n = int(e['m'].sum())
                        if n and (e['m'] & cc.crop_view(occ, e['l'], e['t'], *e['m'].shape)).sum() / n >= a['dup']:
                            continue
                        paste(occ, e['l'], e['t'], e['m'])
                        k2.append(e)
                    kept = k2
                n_split = 0
                if a['split'] is not None:
                    v = V(*(a['trim'][:2] if a['trim'] else ('none', 'exgr_zero')))
                    n_split = sum(1 for e in kept if cc.large_components(e['m'] & cc.crop_view(v, e['l'], e['t'], *e['m'].shape), a['split']) >= 2)
                union = np.zeros(rgb.shape[:2], bool)
                for e in kept:
                    paste(union, e['l'], e['t'], e['m'])
                for metric, value in (('masks', len([e for e in kept if e['m'].any()])), ('union_px', int(union.sum())),
                                      ('removed_px', removed), ('split_masks', n_split), ('proposals', 0)):
                    rows.append(dict(plant=t, photo=Path(img).stem, arm=name, metric=metric, value=value))
            print(t, img, file=sys.stderr, flush=True)
    return rows


def _held(train: list[str]) -> str:
    (h,) = set(PLANTS) - set(train)
    return h


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('wb', 'bundle', 'evaluate'):
        s = sub.add_parser(name)
        s.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    if a.cmd == 'wb':
        r = wb(a.out)
        print(json.dumps({k: v['gains'] for k, v in r['photos'].items()}, indent=0))
    elif a.cmd == 'bundle':
        print(json.dumps(bundle(a.out), indent=1))
    else:
        r = evaluate(a.out)
        print(json.dumps(r['acceptance'], indent=1))


if __name__ == '__main__':
    main()
