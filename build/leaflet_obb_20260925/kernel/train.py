# Leaflet rotated boxes (OBB) from human-accepted masks: dwt_01 + dwt_02 odd views train, dwt_02 even views validate.
# Reports OBB mAP and how well the predicted long axis matches the mask's long axis (the leaflet direction in the photo).
import glob, json, os, subprocess, sys, shutil, math
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics"], check=True)
import numpy as np, torch
from ultralytics import YOLO

WORK = "/kaggle/working"; NL = chr(10)
print("GPU", torch.cuda.get_device_name(0))
hits = [p for p in glob.glob("/kaggle/input/**/index.json", recursive=True) if json.load(open(p)).get("schema") == "leaflet-obb-dataset-1"]
assert hits, "leaflet-obb-dataset-1 not found"
SRC = os.path.dirname(hits[0]); DATA = f"{WORK}/data"
if not os.path.exists(DATA): shutil.copytree(SRC, DATA)
Y = f"{WORK}/obb.yaml"
open(Y, "w").write(NL.join([f"path: {DATA}", "train: train/images", "val: val/images", "nc: 1", "names: ['leaflet']"]) + NL)
res = {}
m = YOLO("yolo11s-obb.pt")
m.train(data=Y, imgsz=1280, epochs=150, patience=30, batch=4, degrees=180, shear=5, perspective=0.0005, flipud=0.5, fliplr=0.5,
        project=f"{WORK}/runs", name="obb", exist_ok=True, seed=0, workers=2, verbose=False)
best = f"{WORK}/runs/obb/weights/best.pt"; shutil.copy(best, f"{WORK}/leaflet_obb_best.pt")
v = YOLO(best).val(data=Y, imgsz=1280, batch=4, verbose=False)
res["obb_map50"], res["obb_map50_95"] = round(float(v.box.map50), 4), round(float(v.box.map), 4)

def axis(poly):  # long-axis angle (0-180) and centre of a 4-corner box
    p = np.asarray(poly, float).reshape(4, 2); e1, e2 = p[1] - p[0], p[2] - p[1]
    e = e1 if np.hypot(*e1) >= np.hypot(*e2) else e2
    return math.degrees(math.atan2(e[1], e[0])) % 180, p.mean(0), min(np.hypot(*e1), np.hypot(*e2))
errs, found, total = [], 0, 0
model = YOLO(best)
for img in sorted(glob.glob(f"{DATA}/val/images/*.jpg")):
    lab = img.replace("/images/", "/labels/").replace(".jpg", ".txt")
    r = model.predict(img, imgsz=1280, conf=0.25, verbose=False)[0]
    H, W = r.orig_shape
    preds = [axis(q) for q in r.obb.xyxyxyxy.cpu().numpy()] if r.obb is not None else []
    for line in open(lab).read().split(NL):
        if not line.strip(): continue
        gt = np.array(line.split()[1:], float).reshape(4, 2) * [W, H]
        ga, gc, gs = axis(gt); total += 1
        near = [(np.hypot(*(pc - gc)), pa) for pa, pc, _ in preds]
        near = [x for x in near if x[0] < 0.5 * gs]
        if near:
            found += 1; pa = min(near)[1]; d = abs(pa - ga) % 180; errs.append(min(d, 180 - d))
e = np.array(errs)
res["axis"] = dict(gt_leaflets=total, matched_by_centre=found, median_axis_error_deg=round(float(np.median(e)), 2) if len(e) else None,
                   within_15deg=round(float((e <= 15).mean()), 4) if len(e) else None, within_30deg=round(float((e <= 30).mean()), 4) if len(e) else None,
                   note="axis is undirected (0-180): tip vs base still needs the petiole side")
json.dump(res, open(f"{WORK}/results.json", "w"), indent=1)
shutil.rmtree(DATA, ignore_errors=True); shutil.rmtree(f"{WORK}/runs/obb/weights", ignore_errors=True)
print(json.dumps(res, indent=1))
