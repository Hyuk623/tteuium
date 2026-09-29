# Tomato organ segmentation (5 classes) on all plants' human labels, side + middle pooled.
# Leave-one-plant-out: 4 folds say how well a model trained on the other plants labels a NEW plant; then one final
# model on all plants for pre-labelling new captures. Results accumulate in results.json (re-push resumes).
import glob, json, os, subprocess, sys, shutil
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics"], check=True)
import torch
from ultralytics import YOLO

WORK = "/kaggle/working"; NL = chr(10)
RESULT = f"{WORK}/results.json"
res = json.load(open(RESULT)) if os.path.exists(RESULT) else {}
print("GPU", torch.cuda.get_device_name(0))
hits = [p for p in glob.glob("/kaggle/input/**/index.json", recursive=True) if json.load(open(p)).get("schema") == "organ-detector-dataset-1"]
assert hits, "organ-detector-dataset-1 index.json not found under /kaggle/input"
ROOT = os.path.dirname(hits[0]); idx = json.load(open(hits[0])); CLASSES = idx["classes"]

# Labels live next to images (<plant>/labels/*.txt); the input mount is read-only, so copy to working.
DATA = f"{WORK}/data"
if not os.path.exists(DATA):
    shutil.copytree(ROOT, DATA)
def listfile(name, plants):
    paths = [f"{DATA}/{r['image']}" for r in idx["images"] if r["plant"] in plants]
    assert paths and all(map(os.path.exists, paths)), "missing images for " + name
    p = f"{WORK}/{name}.txt"; open(p, "w").write(NL.join(paths) + NL); return p
def yaml(name, train, val):
    p = f"{WORK}/{name}.yaml"
    open(p, "w").write(NL.join([f"train: {listfile(name + '_train', train)}", f"val: {listfile(name + '_val', val)}",
                                f"nc: {len(CLASSES)}", f"names: {json.dumps(CLASSES)}"]) + NL)
    return p

ARGS = dict(imgsz=1280, epochs=120, patience=30, batch=4, degrees=15, fliplr=0.5, mosaic=1.0, close_mosaic=15, workers=2, seed=0, verbose=False)
plants = sorted({r["plant"] for r in idx["images"]})
runs = [(f"lopo_{p}", [q for q in plants if q != p], [p]) for p in plants] + [("final_all", plants, plants)]
for name, train, val in runs:
    if name in res: print("skip", name); continue
    m = YOLO("yolo11s-seg.pt")
    m.train(data=yaml(name, train, val), project=f"{WORK}/runs", name=name, exist_ok=True, **ARGS)
    best = f"{WORK}/runs/{name}/weights/best.pt"
    v = YOLO(best).val(data=f"{WORK}/{name}.yaml", imgsz=1280, batch=4, split="val", verbose=False)
    per = {CLASSES[i]: dict(box_map50=round(float(v.box.ap50[k]), 4), mask_map50=round(float(v.seg.ap50[k]), 4))
           for k, i in enumerate(v.box.ap_class_index)}
    res[name] = dict(train=train, val=val, box_map50=round(float(v.box.map50), 4), mask_map50=round(float(v.seg.map50), 4),
                     box_map=round(float(v.box.map), 4), mask_map=round(float(v.seg.map), 4), per_class=per,
                     note="final_all validates on its own training plants (sanity only)" if name == "final_all" else "held-out plant")
    json.dump(res, open(RESULT, "w"), indent=1); print(name, res[name]["box_map50"], res[name]["mask_map50"], flush=True)
    shutil.copy(best, f"{WORK}/{name}_best.pt")
    shutil.rmtree(f"{WORK}/runs/{name}/weights", ignore_errors=True)
    del m; torch.cuda.empty_cache()
lo = [res[k] for k in res if k.startswith("lopo_")]
res["lopo_mean"] = dict(box_map50=round(sum(r["box_map50"] for r in lo) / len(lo), 4), mask_map50=round(sum(r["mask_map50"] for r in lo) / len(lo), 4))
json.dump(res, open(RESULT, "w"), indent=1)
shutil.rmtree(DATA, ignore_errors=True)
print(json.dumps(res, indent=1))
