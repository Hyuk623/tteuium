# Organ boxes v3 = baseline recipe (yolo11s-seg, mild aug; LOPO leaflet box AP50 0.66) + 3 seeds + flip TTA + WBF
# (participation^gamma). v2's heavy rotation/shear/perspective hurt, so only the ensemble part is kept.
# Every single model is ALSO scored by ultralytics val, so a gap between that and the own AP50 evaluator exposes an
# evaluator problem (v2's dwt_01 fold fell to 0.21 while the baseline scored 0.65 there). Then 3 final models on all
# plants for pre-labelling. Resumes from results.json.
import glob, json, os, subprocess, sys, shutil
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics"], check=True)
import numpy as np, torch
from ultralytics import YOLO

WORK = "/kaggle/working"; NL = chr(10)
RESULT = f"{WORK}/results.json"; PRED = f"{WORK}/preds"; os.makedirs(PRED, exist_ok=True)
res = json.load(open(RESULT)) if os.path.exists(RESULT) else {}
print("GPU", torch.cuda.get_device_name(0))
hits = [p for p in glob.glob("/kaggle/input/**/index.json", recursive=True) if json.load(open(p)).get("schema") == "organ-detector-dataset-1"]
assert hits, "organ-detector-dataset-1 not found"
SRC = os.path.dirname(hits[0]); idx = json.load(open(hits[0])); CLASSES = idx["classes"]; NC = len(CLASSES)
DATA = f"{WORK}/data"
if not os.path.exists(DATA): shutil.copytree(SRC, DATA)
plants = sorted({r["image"].split("/")[0] for r in idx["images"]})
imgs = {p: [f"{DATA}/{r['image']}" for r in idx["images"] if r["plant"] == p] for p in plants}
def yaml(name, train, val):
    for s, ps in (("train", train), ("val", val)):
        open(f"{WORK}/{name}_{s}.txt", "w").write(NL.join(sum((imgs[p] for p in ps), [])) + NL)
    p = f"{WORK}/{name}.yaml"
    open(p, "w").write(NL.join([f"train: {WORK}/{name}_train.txt", f"val: {WORK}/{name}_val.txt", f"nc: {NC}", f"names: {json.dumps(CLASSES)}"]) + NL)
    return p
AUG = dict(degrees=15, fliplr=0.5, mosaic=1.0, close_mosaic=15)   # the baseline kernel's settings
SEEDS, VIEWS, GAMMA, IOU_FUSE = [0, 1, 2], ["orig", "h", "v"], 0.4, 0.55

def gt_boxes(img):
    from PIL import Image
    W, H = Image.open(img).size; out = []
    for line in open(img.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt").read().split(NL):
        if not line.strip(): continue
        v = line.split(); xy = np.array(v[1:], float).reshape(-1, 2) * [W, H]
        out.append((int(v[0]), [*xy.min(0), *xy.max(0)]))
    return out
def predict(model, img, view):
    import cv2
    from PIL import Image
    a = np.asarray(Image.open(img).convert("RGB"))[:, :, ::-1]; H, W = a.shape[:2]
    b = a[:, ::-1] if view == "h" else a[::-1] if view == "v" else a
    r = model.predict(np.ascontiguousarray(b), imgsz=1280, conf=0.01, iou=0.6, max_det=600, verbose=False)[0]
    xy = r.boxes.xyxy.cpu().numpy(); s = r.boxes.conf.cpu().numpy(); c = r.boxes.cls.cpu().numpy().astype(int)
    if view == "h": xy[:, [0, 2]] = W - xy[:, [2, 0]]
    if view == "v": xy[:, [1, 3]] = H - xy[:, [3, 1]]
    return [(int(ci), [float(x) for x in bi], float(si)) for bi, si, ci in zip(xy, s, c)]
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0
def wbf(members, n):
    out = []
    for c in range(NC):
        boxes = sorted([(b, s, m) for m, ps in enumerate(members) for ci, b, s in ps if ci == c], key=lambda t: -t[1])
        clusters = []
        for b, s, m in boxes:
            for cl in clusters:
                if iou(cl["box"], b) > IOU_FUSE:
                    cl["items"].append((b, s, m)); w = np.array([x[1] for x in cl["items"]])
                    cl["box"] = list((np.array([x[0] for x in cl["items"]]) * w[:, None]).sum(0) / w.sum()); break
            else:
                clusters.append(dict(box=list(b), items=[(b, s, m)]))
        for cl in clusters:
            sc = np.mean([x[1] for x in cl["items"]]) * (len({x[2] for x in cl["items"]}) / n) ** GAMMA
            out.append((c, cl["box"], float(sc)))
    return out
def ap50(preds_by_img, gts_by_img):
    out = {}
    for c in range(NC):
        P = sorted([(s, k, b) for k, ps in preds_by_img.items() for ci, b, s in ps if ci == c], key=lambda t: -t[0])
        G = {k: [b for ci, b in g if ci == c] for k, g in gts_by_img.items()}; n = sum(len(v) for v in G.values())
        if n == 0: continue
        used = {k: [False] * len(v) for k, v in G.items()}; tp = []
        for s, k, b in P:
            best, j = 0, -1
            for jj, g in enumerate(G[k]):
                o = iou(b, g)
                if o > best and not used[k][jj]: best, j = o, jj
            if best >= .5: used[k][j] = True; tp.append(1)
            else: tp.append(0)
        tp = np.array(tp); ctp = np.cumsum(tp); rec = ctp / n; prec = ctp / np.arange(1, len(tp) + 1) if len(tp) else np.array([])
        ap = np.mean([prec[rec >= t].max() if (rec >= t).any() else 0 for t in np.linspace(0, 1, 101)]) if len(tp) else 0.0
        out[CLASSES[c]] = dict(ap50=round(float(ap), 4), recall_max=round(float(rec[-1]) if len(rec) else 0, 4), gt=n)
    out["mean_ap50"] = round(float(np.mean([v["ap50"] for v in out.values()])), 4)
    return out

for held in plants:
    key = f"lopo_{held}"
    if key in res: print("skip", key); continue
    Yp = yaml(key, [p for p in plants if p != held], [held])
    for sd in SEEDS:
        w = f"{WORK}/{key}_s{sd}.pt"
        if os.path.exists(w): continue
        YOLO("yolo11s-seg.pt").train(data=Yp, imgsz=1280, epochs=120, patience=30, batch=4, seed=sd, workers=2, project=f"{WORK}/runs",
                                 name=f"{key}_s{sd}", exist_ok=True, verbose=False, **AUG)
        shutil.copy(f"{WORK}/runs/{key}_s{sd}/weights/best.pt", w); shutil.rmtree(f"{WORK}/runs/{key}_s{sd}", ignore_errors=True)
        torch.cuda.empty_cache()
    ultra = {}
    for sd in SEEDS:
        v = YOLO(f"{WORK}/{key}_s{sd}.pt").val(data=Yp, imgsz=1280, batch=4, verbose=False)
        ultra[f"s{sd}"] = dict(box_map50=round(float(v.box.map50), 4),
                               leaflet_box_ap50=round(float(dict(zip(v.box.ap_class_index.tolist(), v.box.ap50.tolist())).get(CLASSES.index("leaflet"), 0)), 4))
    gts = {i: gt_boxes(i) for i in imgs[held]}
    cache = f"{PRED}/{key}.json"
    P = json.load(open(cache)) if os.path.exists(cache) else {}
    for sd in SEEDS:
        m = YOLO(f"{WORK}/{key}_s{sd}.pt")
        for v in VIEWS:
            if f"s{sd}_{v}" in P: continue
            P[f"s{sd}_{v}"] = {i: predict(m, i, v) for i in imgs[held]}
        json.dump(P, open(cache, "w"))
    arms = {"single_s0": [["s0_orig"]], "tta_s0": [["s0_orig", "s0_h", "s0_v"]], "seeds3": [[f"s{s}_orig" for s in SEEDS]],
            "seeds3_tta": [[f"s{s}_{v}" for s in SEEDS for v in VIEWS]]}
    res[key] = {"ultralytics_val": ultra}
    for arm, (members,) in arms.items():
        fused = {i: (P[members[0]][i] if len(members) == 1 else wbf([P[m][i] for m in members], len(members))) for i in imgs[held]}
        res[key][arm] = ap50(fused, gts)
    res[key]["gt_counts"] = {CLASSES[c]: sum(1 for g in gts.values() for ci, _ in g if ci == c) for c in range(NC)}
    json.dump(res, open(RESULT, "w"), indent=1)
    print(key, {a: res[key][a]["mean_ap50"] for a in arms}, flush=True)
ARMS = ["single_s0", "tta_s0", "seeds3", "seeds3_tta"]
res["lopo_mean"] = {a: round(float(np.mean([res[f"lopo_{p}"][a]["mean_ap50"] for p in plants])), 4) for a in ARMS}
res["lopo_mean_leaflet"] = {a: round(float(np.mean([res[f"lopo_{p}"][a]["leaflet"]["ap50"] for p in plants])), 4) for a in ARMS}
json.dump(res, open(RESULT, "w"), indent=1)
# final models on every plant, for pre-labelling new captures (ensemble of 3 seeds)
Yall = yaml("final_all", plants, plants)
for sd in SEEDS:
    w = f"{WORK}/final_all_s{sd}.pt"
    if os.path.exists(w): continue
    YOLO("yolo11s-seg.pt").train(data=Yall, imgsz=1280, epochs=120, patience=30, batch=4, seed=sd, workers=2, project=f"{WORK}/runs",
                                 name=f"final_s{sd}", exist_ok=True, verbose=False, **AUG)
    shutil.copy(f"{WORK}/runs/final_s{sd}/weights/best.pt", w); shutil.rmtree(f"{WORK}/runs/final_s{sd}", ignore_errors=True)
    torch.cuda.empty_cache()
res["final_models"] = [f"final_all_s{sd}.pt" for sd in SEEDS]
json.dump(res, open(RESULT, "w"), indent=1); shutil.rmtree(DATA, ignore_errors=True)
print(json.dumps({k: res[k] for k in ("lopo_mean", "lopo_mean_leaflet")}, indent=1))
