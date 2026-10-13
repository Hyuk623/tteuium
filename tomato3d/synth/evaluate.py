"""C6/C7: the frozen detector v4 and leaflet-tuned SAM2 v5 on synthetic (and control real) photos.

Nothing here trains or adapts a model. Runs in the project environment (torch, ultralytics, a SAM2
package) or on Kaggle (Addendum B); not in tomato_synth.

* C6 detector leaflet AP50: the rule of ``build/organ_detector_v4_20260929/kernel_template.py``
  (``predict(imgsz=1280, conf=0.01, iou=0.6, max_det=600)``, greedy box matching at IoU >= 0.5,
  101-point interpolated AP). Ground truth: one box per leaflet whose visible mask passes the GT rule.
* C7 SAM IoU: box prompt = ground-truth box, highest-scoring of SAM's three candidates, mask IoU
  against the visible mask; median over instances.
* Addendum B diagnostics: recall by visible-area bin and by visible fraction (synthetic: visible /
  amodal pixels), false positives = unmatched leaflet predictions with conf >= ``fp_conf``, and
  confusions = other-class predictions (conf >= ``fp_conf``) overlapping a GT leaflet at IoU >= 0.5.

``python -X utf8 -m tomato3d.synth.evaluate --out <run> --detector <pt> --sam-config <json> [--scenes ...]``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.synth.images import imread

DET_ARGS = dict(imgsz=1280, conf=0.01, iou=0.6, max_det=600)
AREA_BINS = ((0, 150, "lt150"), (150, 500, "150_500"), (500, 1500, "500_1500"), (1500, float("inf"), "gt1500"))
VIS_BINS = ((0.0, 0.5, "vis_lt05"), (0.5, 0.9, "vis_05_09"), (0.9, 1.01, "vis_gt09"))


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def ap50(preds: dict[str, list[tuple[list[float], float]]], gts: dict[str, list[list[float]]]) -> dict[str, Any]:
    """Box AP50 (101-point) with greedy matching, as in the organ detector v4 kernel.

    Also returns ``matched``: per image, which GT boxes were matched by any prediction.
    """
    n = sum(len(v) for v in gts.values())
    P = sorted([(s, k, b) for k, ps in preds.items() for b, s in ps], key=lambda t: -t[0])
    used = {k: [False] * len(v) for k, v in gts.items()}
    tp, unmatched_conf = [], []
    for s, k, b in P:
        best, j = 0.0, -1
        for jj, gb in enumerate(gts.get(k, [])):
            o = _iou(b, gb)
            if o > best and not used[k][jj]:
                best, j = o, jj
        if best >= 0.5:
            used[k][j] = True
            tp.append(1)
        else:
            tp.append(0)
            unmatched_conf.append(s)
    if not tp or n == 0:
        return dict(ap50=0.0, recall_max=0.0, gt=n, matched=used, unmatched_conf=unmatched_conf)
    tp = np.array(tp)
    ctp = np.cumsum(tp)
    rec, prec = ctp / n, ctp / np.arange(1, len(tp) + 1)
    ap = np.mean([prec[rec >= t].max() if (rec >= t).any() else 0 for t in np.linspace(0, 1, 101)])
    return dict(ap50=round(float(ap), 4), recall_max=round(float(rec[-1]), 4), gt=n, matched=used,
                unmatched_conf=unmatched_conf)


def detect(model, bgr: np.ndarray) -> list[tuple[int, list[float], float]]:
    r = model.predict(bgr, verbose=False, **DET_ARGS)[0]
    return [(int(c), b.tolist(), float(s)) for b, s, c in
            zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), r.boxes.cls.cpu().numpy())]


def score(dets: dict[str, list], gts: dict[str, list[dict]], names: dict[int, str], *, fp_conf: float) -> dict[str, Any]:
    """C6 + Addendum B diagnostics. ``gts[img]`` items: ``box``, ``area_px``, optional ``vis_frac``."""
    leaf = next(k for k, v in names.items() if v == "leaflet")
    preds = {k: [(b, s) for c, b, s in d if c == leaf] for k, d in dets.items()}
    res = ap50(preds, {k: [g["box"] for g in v] for k, v in gts.items()})
    flat = [(g, res["matched"][k][i]) for k, v in gts.items() for i, g in enumerate(v)]
    out = dict(ap50=res["ap50"], recall_max=res["recall_max"], gt=res["gt"])
    for lo, hi, tag in AREA_BINS:
        sel = [m for g, m in flat if lo <= g["area_px"] < hi]
        out[f"recall_{tag}"] = round(float(np.mean(sel)), 4) if sel else None
        out[f"n_{tag}"] = len(sel)
    for lo, hi, tag in VIS_BINS:
        sel = [m for g, m in flat if g.get("vis_frac") is not None and lo <= g["vis_frac"] < hi]
        out[f"recall_{tag}"] = round(float(np.mean(sel)), 4) if sel else None
        out[f"n_{tag}"] = len(sel)
    out["fp_count"] = int(sum(1 for s in res["unmatched_conf"] if s >= fp_conf))
    conf_by_class: dict[str, int] = {}
    for k, d in dets.items():
        for c, b, s in d:
            if c == leaf or s < fp_conf:
                continue
            if any(_iou(b, g["box"]) >= 0.5 for g in gts.get(k, [])):
                conf_by_class[names[c]] = conf_by_class.get(names[c], 0) + 1
    out["confusions_by_class"] = conf_by_class
    out["predictions_by_class"] = {names[c]: int(sum(1 for d in dets.values() for cc, _, s in d
                                                     if cc == c and s >= fp_conf)) for c in names}
    out["per_gt"] = [dict(image=k, instance=g.get("instance"), area_px=g["area_px"], vis_frac=g.get("vis_frac"),
                          matched=bool(res["matched"][k][i])) for k, v in gts.items() for i, g in enumerate(v)]
    return out


def load_sam2(config: dict[str, Any], base: Path | None = None):
    """SAM2ImagePredictor from a ``sam2_config_*.json`` (repository, runtime, checkpoint, model_config)."""
    def path(key):
        p = Path(config[key])
        return p if p.is_absolute() or base is None else base / p

    for key in ("runtime", "repository"):
        if config.get(key) and path(key).exists():
            sys.path.insert(0, str(path(key)))
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    device = config.get("device") or ("cuda" if torch.cuda.is_available() else "cpu")
    model = build_sam2(config["model_config"], str(path("checkpoint")), device=device, apply_postprocessing=False)
    return SAM2ImagePredictor(model, max_hole_area=0, max_sprinkle_area=0)


def sam_ious(predictor, rgb: np.ndarray, gts: list[dict]) -> list[float]:
    import torch

    out = []
    with torch.inference_mode():
        predictor.set_image(rgb)
        for g in gts:
            masks, scores, _ = predictor.predict(box=np.asarray(g["box"], np.float32), multimask_output=True)
            best = np.asarray(masks[int(np.argmax(scores))], bool)
            union = (best | g["mask"]).sum()
            out.append(float((best & g["mask"]).sum() / union) if union else 0.0)
    return out


def mask_aspect(m: np.ndarray) -> float | None:
    """minAreaRect short/long side of the largest connected component (as in run_F1.py)."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n <= 1:
        return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    cs, _ = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    (_, _), (w, h), _ = cv2.minAreaRect(max(cs, key=cv2.contourArea))
    return float(min(w, h) / max(w, h)) if max(w, h) > 0 else None


def synthetic_gt(view_dir: Path, min_visible_px: int, rule: dict[str, Any] | None = None) -> list[dict]:
    """GT leaflets of one synthetic view; ``rule`` (Addendum B1) may add ``min_vis_frac``."""
    vis = imread(view_dir / "visible_mask.png")
    index = json.loads((view_dir.parent.parent / "leaflet_index.json").read_text(encoding="utf-8"))
    min_px = int((rule or {}).get("min_visible_px", min_visible_px))
    min_frac = float((rule or {}).get("min_vis_frac", 0.0))
    min_solidity = float((rule or {}).get("min_solidity", 0.0))
    min_aspect = float((rule or {}).get("min_aspect", 0.0))       # Addendum F.11 diagnostic only
    if rule and rule.get("area_reference_px"):          # rule area declared at another resolution
        min_px = int(round(min_px * (max(vis.shape) / float(rule["area_reference_px"])) ** 2))
    out = []
    for inst in np.unique(vis[vis > 0]):
        m = vis == inst
        area = int(m.sum())
        info = index[str(int(inst))]
        amodal_path = view_dir / "amodal" / f"{info['compound_id']}_{info['tag']}.png"
        amodal = int((imread(amodal_path) > 0).sum()) if amodal_path.exists() else area
        frac = area / max(1, amodal)
        if area < min_px or frac < min_frac:
            continue
        if min_solidity > 0:
            cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            hull = cv2.contourArea(cv2.convexHull(np.vstack(cs))) if cs else 0.0
            if hull <= 0 or area / hull < min_solidity:
                continue
        aspect = mask_aspect(m)
        if min_aspect > 0 and (aspect is None or aspect < min_aspect):
            continue
        ys, xs = np.nonzero(m)
        out.append(dict(aspect=aspect, box=[float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1)],
                        mask=m, area_px=area, vis_frac=frac, instance=int(inst)))
    return out


def evaluate(out: Path, detector: Path, sam_config: Path | None, scenes: list[str] | None, *,
             fp_conf: float, gt_rule: dict | None = None, rgb_dir: str | None = None) -> dict[str, Any]:
    from ultralytics import YOLO

    contract = json.loads((out / "stage1_contract.json").read_text(encoding="utf-8"))
    min_px = int(contract["min_visible_px"])
    rows = [json.loads(l) for l in (out / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("rgb") and (not scenes or r["scene_id"] in scenes)]
    model = YOLO(str(detector))
    names = {int(k): v for k, v in model.names.items()}
    predictor = load_sam2(json.loads(Path(sam_config).read_text(encoding="utf-8"))) if sam_config else None
    dets, gts, ious = {}, {}, []
    for r in rows:
        key = f"{r['scene_id']}/{r['view_id']}"
        vdir = out / Path(r["visible_mask"]).parent
        rgb_path = vdir / (rgb_dir or "rgb.png") if rgb_dir else out / r["rgb"]
        if not Path(rgb_path).exists():
            continue
        bgr = imread(rgb_path, cv2.IMREAD_COLOR)
        gt = synthetic_gt(vdir, min_px, gt_rule)
        if gt and bgr.shape[:2] != gt[0]["mask"].shape:
            raise SystemExit(f"{rgb_path}: image and mask sizes differ")
        gts[key] = gt
        dets[key] = detect(model, bgr)
        if predictor is not None and gt:
            ious += sam_ious(predictor, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), gt)
    s = score(dets, gts, names, fp_conf=fp_conf)
    iou_arr = np.array(ious)
    return dict(n_views=len(gts), scenes=sorted({k.split("/")[0] for k in gts}), min_visible_px=min_px,
                gt_rule=gt_rule, fp_conf=fp_conf, detector=dict(path=str(detector), sha256=sha256(detector),
                                                                class_names=names, **s),
                sam=dict(config=str(sam_config) if sam_config else None, n=int(len(iou_arr)),
                         median=float(np.median(iou_arr)) if len(iou_arr) else None,
                         ge50=float((iou_arr >= 0.5).mean()) if len(iou_arr) else None))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--detector", required=True)
    ap.add_argument("--sam-config")
    ap.add_argument("--scenes", nargs="*")
    ap.add_argument("--fp-conf", type=float, required=True)
    ap.add_argument("--gt-rule", help="JSON file with the declared GT rule (Addendum B1)")
    ap.add_argument("--rgb-name", help="alternative image file name inside each view dir (e.g. rgb_b3.png)")
    ap.add_argument("--name", default="evaluation")
    args = ap.parse_args(argv)
    out = Path(args.out)
    rule = json.loads(Path(args.gt_rule).read_text(encoding="utf-8")) if args.gt_rule else None
    result = evaluate(out, Path(args.detector), Path(args.sam_config) if args.sam_config else None, args.scenes,
                      fp_conf=args.fp_conf, gt_rule=rule, rgb_dir=args.rgb_name)
    try:
        import psutil

        mem = psutil.Process().memory_info()
        result["peak_ram_gb"] = round(getattr(mem, "peak_wset", mem.rss) / 1e9, 2)
    except ImportError:
        result["peak_ram_gb"] = None
    (out / f"{args.name}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    d = result["detector"]
    print(json.dumps(dict(ap50=d["ap50"], recall=d["recall_max"], gt=d["gt"], fp=d["fp_count"],
                          sam_median=result["sam"]["median"], n_views=result["n_views"], peak_ram_gb=result["peak_ram_gb"])))


if __name__ == "__main__":
    main()
