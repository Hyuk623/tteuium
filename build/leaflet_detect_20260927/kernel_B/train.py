# Leaflet-only detector, one member of a weighted late-fusion ensemble (user, 2026-09-27).
# MEMBER = B : model yolo11m-seg.pt, image variant full, imgsz 1280.
# Leave-one-plant-out: each fold trains on three plants, saves the held-out plant's predictions (normalised xyxy on
# that variant's image, conf >= 0.01) for the local fusion step, and records ultralytics val. Then a final model on
# all plants. Resumes from results.json.
import glob, json, os, subprocess, sys, shutil
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics"], check=True)
import torch
from ultralytics import YOLO

MEMBER, MODEL, VARIANT, IMGSZ = "B", "yolo11m-seg.pt", "full", 1280
WORK = "/kaggle/working"; NL = chr(10)
RESULT = f"{WORK}/results_{MEMBER}.json"
res = json.load(open(RESULT)) if os.path.exists(RESULT) else {}
print("GPU", torch.cuda.get_device_name(0), MEMBER, MODEL, VARIANT, IMGSZ)
hits = [p for p in glob.glob("/kaggle/input/**/index.json", recursive=True) if json.load(open(p)).get("schema") == "leaflet-detect-dataset-1"]
assert hits, "leaflet-detect-dataset-1 not found"
SRC = os.path.dirname(hits[0]); DATA = f"{WORK}/data"
if not os.path.exists(DATA): shutil.copytree(os.path.join(SRC, VARIANT), DATA)
PLANTS = sorted(os.listdir(DATA))
imgs = {p: sorted(glob.glob(f"{DATA}/{p}/images/*.jpg")) for p in PLANTS}
assert all(imgs.values()), "missing images"
def yaml(name, train, val):
    for s, ps in (("train", train), ("val", val)):
        open(f"{WORK}/{name}_{s}.txt", "w").write(NL.join(sum((imgs[p] for p in ps), [])) + NL)
    y = f"{WORK}/{name}.yaml"
    open(y, "w").write(NL.join([f"train: {WORK}/{name}_train.txt", f"val: {WORK}/{name}_val.txt", "nc: 1", "names: ['leaflet']"]) + NL)
    return y
ARGS = dict(imgsz=IMGSZ, epochs=200, patience=0, batch=4 if "m-" not in MODEL else 2, degrees=15, fliplr=0.5, mosaic=1.0,
            close_mosaic=15, workers=2, seed=0, verbose=False)
for held in PLANTS + [None]:
    key = f"lopo_{held}" if held else "final_all"
    if key in res: continue
    train = [p for p in PLANTS if p != held]; val = [held] if held else PLANTS
    y = yaml(key, train, val)
    YOLO(MODEL).train(data=y, project=f"{WORK}/runs", name=key, exist_ok=True, **ARGS)
    best = f"{WORK}/runs/{key}/weights/best.pt"
    v = YOLO(best).val(data=y, imgsz=IMGSZ, batch=2, verbose=False)
    entry = dict(box_map50=round(float(v.box.map50), 4), box_map50_95=round(float(v.box.map), 4))
    if held:
        m = YOLO(best); preds = {}
        for img in imgs[held]:
            r = m.predict(img, imgsz=IMGSZ, conf=0.01, iou=0.6, max_det=600, verbose=False)[0]
            preds[os.path.basename(img)[:-4]] = [[*map(float, b), float(s)] for b, s in zip(r.boxes.xyxyn.cpu().numpy(), r.boxes.conf.cpu().numpy())]
        json.dump(preds, open(f"{WORK}/oof_{MEMBER}_{held}.json", "w"))
    else:
        shutil.copy(best, f"{WORK}/leaflet_{MEMBER}_final.pt")
    res[key] = entry; json.dump(res, open(RESULT, "w"), indent=1); print(key, entry, flush=True)
    shutil.rmtree(f"{WORK}/runs/{key}", ignore_errors=True); torch.cuda.empty_cache()
shutil.rmtree(DATA, ignore_errors=True)
print(json.dumps(res, indent=1))
