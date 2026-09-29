# Organ detector v4, arm full (user 2026-09-29: small organs; masks reviewed to the end).
# Same labels in three image variants (full photo / plant window / 2x2 tiles of the window); this kernel trains one.
# Leave-one-plant-out: each fold's weights are SAVED (lesson of 09-28: no held-out model was kept), predictions of the
# held-out plant are mapped back to the full photo and scored against the full-photo labels, so the arms compare.
# patience=0 (lesson of 09-28: val mAP is ~0 for the first ~30 epochs), mosaic off and scale 0.25 (mosaic halves
# petioles that are 33 px at 1280 already). last.pt is kept, not best.pt (best is picked on the held-out plant).
# Resumes from results_<arm>.json.
import glob, json, os, subprocess, sys, shutil
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics"], check=True)
import numpy as np, torch
from ultralytics import YOLO

ARM = "full"; EPOCHS = 150
WORK = "/kaggle/working"; NL = chr(10)
RESULT = f"{WORK}/results_{ARM}.json"
res = json.load(open(RESULT)) if os.path.exists(RESULT) else {}
print("GPU", torch.cuda.get_device_name(0), ARM, flush=True)
hits = [p for p in glob.glob("/kaggle/input/**/index.json", recursive=True) if json.load(open(p)).get("schema") == "organ-detector-dataset-2"]
assert hits, "organ-detector-dataset-2 not found"
SRC = os.path.dirname(hits[0]); idx = json.load(open(hits[0])); CLASSES = idx["classes"]; NC = len(CLASSES)
DATA = f"{WORK}/data"
if not os.path.exists(os.path.join(DATA, ARM)):
    shutil.copytree(os.path.join(SRC, ARM), os.path.join(DATA, ARM))
rows = [r for r in idx["images"] if r["variant"] == ARM]
plants = sorted({r["plant"] for r in rows})
imgs = {p: [f"{DATA}/{r['image']}" for r in rows if r["plant"] == p] for p in plants}
assert all(os.path.exists(i) for v in imgs.values() for i in v), "image list mismatch"
photos = {(m["plant"], m["photo"]): m for m in idx["photos"]}


def yaml(name, train, val):
    for s, ps in (("train", train), ("val", val)):
        open(f"{WORK}/{name}_{s}.txt", "w").write(NL.join(sum((imgs[p] for p in ps), [])) + NL)
    y = f"{WORK}/{name}.yaml"
    open(y, "w").write(NL.join([f"train: {WORK}/{name}_train.txt", f"val: {WORK}/{name}_val.txt", f"nc: {NC}",
                                f"names: {json.dumps(CLASSES)}"]) + NL)
    return y


AUG = dict(degrees=15, fliplr=0.5, mosaic=0.0, scale=0.25, translate=0.1)
ARGS = dict(imgsz=1280, epochs=EPOCHS, patience=0, batch=4, workers=2, verbose=False, **AUG)


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


#: Large or long organs are cut by tile edges; their pieces are joined by union (checked on the labels themselves:
#: union lifts the ceiling of compound leaves/main stems, but merges neighbouring leaflets, which keep weighted fusion).
UNION_CLASSES = ("compound_leaf", "main_stem")


def ios(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    m = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ix * iy / m if m > 0 else 0.0


def merge(preds, thr=0.55):
    """Boxes of overlapping tiles, per class: union for UNION_CLASSES, score-weighted fusion for the rest."""
    out = []
    for c in range(NC):
        cl, union = [], CLASSES[c] in UNION_CLASSES
        for b, s in sorted([(b, s) for ci, b, s in preds if ci == c], key=lambda t: -t[1]):
            for k in cl:
                if union and (iou(k["box"], b) > thr or ios(k["box"], b) > 0.5):
                    k["items"].append((b, s)); bb = k["box"]
                    k["box"] = [min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3])]; break
                if not union and iou(k["box"], b) > thr:
                    k["items"].append((b, s)); w = np.array([x[1] for x in k["items"]])
                    k["box"] = list((np.array([x[0] for x in k["items"]]) * w[:, None]).sum(0) / w.sum()); break
            else:
                cl.append(dict(box=list(b), items=[(b, s)]))
        out += [(c, k["box"], float(max(x[1] for x in k["items"]))) for k in cl]
    return out


def predict_photo(model, plant):
    """Predictions for every held-out photo in ORIGINAL photo pixels, whatever the arm's image variant."""
    by = {}
    for r in [r for r in rows if r["plant"] == plant]:
        rr = model.predict(f"{DATA}/{r['image']}", imgsz=1280, conf=0.01, iou=0.6, max_det=600, verbose=False)[0]
        xy = rr.boxes.xyxyn.cpu().numpy(); s = rr.boxes.conf.cpu().numpy(); c = rr.boxes.cls.cpu().numpy().astype(int)
        ox, oy = r["offset"]; cw, ch = r["crop"]
        by.setdefault(r["photo"], []).extend(
            (int(ci), [float(ox + b[0] * cw), float(oy + b[1] * ch), float(ox + b[2] * cw), float(oy + b[3] * ch)], float(si))
            for b, si, ci in zip(xy, s, c))  # plain floats: numpy float32 is not JSON (v4 full run 1 failed here)
    return {k: (merge(v) if ARM == "tiles" else v) for k, v in by.items()}


def ap50(preds, plant):
    out = {}
    gts = {m["photo"]: [(g["cls"], g["xyxy"]) for g in m["gt"]] for (p, _), m in photos.items() if p == plant}
    for c in range(NC):
        P = sorted([(s, k, b) for k, ps in preds.items() for ci, b, s in ps if ci == c], key=lambda t: -t[0])
        G = {k: [b for ci, b in g if ci == c] for k, g in gts.items()}; n = sum(len(v) for v in G.values())
        if n == 0:
            continue
        used = {k: [False] * len(v) for k, v in G.items()}; tp = []
        for s, k, b in P:
            best, j = 0, -1
            for jj, gb in enumerate(G.get(k, [])):
                o = iou(b, gb)
                if o > best and not used[k][jj]:
                    best, j = o, jj
            if best >= .5:
                used[k][j] = True; tp.append(1)
            else:
                tp.append(0)
        if not tp:
            out[CLASSES[c]] = dict(ap50=0.0, recall_max=0.0, gt=n); continue
        tp = np.array(tp); ctp = np.cumsum(tp); rec = ctp / n; prec = ctp / np.arange(1, len(tp) + 1)
        ap = np.mean([prec[rec >= t].max() if (rec >= t).any() else 0 for t in np.linspace(0, 1, 101)])
        out[CLASSES[c]] = dict(ap50=round(float(ap), 4), recall_max=round(float(rec[-1]), 4), gt=n)
    out["mean_ap50"] = round(float(np.mean([v["ap50"] for v in out.values()])), 4)
    return out


for held in plants + [None]:
    key = f"lopo_{held}" if held else "final_all"
    if key in res:
        print("skip", key); continue
    tr = [p for p in plants if p != held]
    y = yaml(key, tr, [held] if held else plants)
    w = f"{WORK}/{ARM}_{key}.pt"
    if not os.path.exists(w):
        YOLO("yolo11s-seg.pt").train(data=y, project=f"{WORK}/runs", name=key, exist_ok=True, seed=0, **ARGS)
        shutil.copy(f"{WORK}/runs/{key}/weights/last.pt", w)
        shutil.rmtree(f"{WORK}/runs/{key}", ignore_errors=True); torch.cuda.empty_cache()
    if held:
        P = predict_photo(YOLO(w), held)
        json.dump(P, open(f"{WORK}/preds_{ARM}_{held}.json", "w"))
        res[key] = ap50(P, held)
        # what this arm could reach at best: its own labels as predictions, through the same mapping and merge
        G = {}
        for r in [r for r in rows if r["plant"] == held]:
            ox, oy = r["offset"]; cw, ch = r["crop"]
            for line in open(f"{DATA}/{r['image']}".replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt").read().split(NL):
                if line.strip():
                    v = line.split(); xy = np.array(v[1:], float).reshape(-1, 2)
                    G.setdefault(r["photo"], []).append((int(v[0]), [ox + xy[:, 0].min() * cw, oy + xy[:, 1].min() * ch,
                                                                     ox + xy[:, 0].max() * cw, oy + xy[:, 1].max() * ch], 1.0))
        res[key]["label_ceiling"] = ap50({k: (merge(v) if ARM == "tiles" else v) for k, v in G.items()}, held)
    else:
        res[key] = dict(weights=os.path.basename(w))
    json.dump(res, open(RESULT, "w"), indent=1); print(key, res[key].get("mean_ap50"), flush=True)

lo = [res[f"lopo_{p}"] for p in plants]
res["lopo_mean"] = {c: round(float(np.mean([r[c]["ap50"] for r in lo if c in r])), 4) for c in CLASSES}
res["lopo_mean"]["mean_ap50"] = round(float(np.mean([r["mean_ap50"] for r in lo])), 4)
json.dump(res, open(RESULT, "w"), indent=1); shutil.rmtree(DATA, ignore_errors=True)
print(json.dumps(res["lopo_mean"], indent=1))
