# 2026-09-28: ONLY the fold that holds out dwt_01, weights saved for a fair photo-only auto validation on dwt_01
# (user: no base models; build on the tuned results). Original header: Four plants, leave-one-plant-out (all human-accepted leaflet masks, 1,156): PART selects SAM or OBB so the two run
# on separate GPU sessions. Each fold trains on three plants and scores the held-out one; then one final model on
# all four plants is saved for use on new captures. Resumes from results.json.
import glob, json, os, subprocess, sys, shutil, math, random, time
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics", "hydra-core", "iopath"], check=True)
import numpy as np, torch, torch.nn.functional as F
from PIL import Image

WORK = "/kaggle/working"; NL = chr(10); dev = "cuda"
RESULT = f"{WORK}/results.json"
res = json.load(open(RESULT)) if os.path.exists(RESULT) else {}
def save(): json.dump(res, open(RESULT, "w"), indent=1)
print("GPU", torch.cuda.get_device_name(0)); random.seed(0); np.random.seed(0); torch.manual_seed(0)
def find(name, schema=None):
    hits = [p for p in glob.glob(f"/kaggle/input/**/{name}", recursive=True)
            if schema is None or json.load(open(p)).get("schema") == schema]
    assert hits, f"{name} {schema} not found"; return hits[0]
CROPS = os.path.dirname(find("index.json", "sam-finetune-dataset-1"))
OBB = os.path.dirname(find("index.json", "leaflet-obb-dataset-1"))
CKPT = find("sam2.1_hiera_tiny.pt"); SAMPKG = os.path.dirname(os.path.dirname(find("sam2_image_predictor.py")))
PART = "sam"
PLANTS = ["dwt_01", "dwt_02", "dwt_03", "dwt_04"]
FOLDS = [(("dwt_02", "dwt_03", "dwt_04"), "dwt_01")]   # (train plants, held-out); None = final
def iou(a, b):
    u = (a | b).sum(); return float((a & b).sum() / u) if u else 0.0
def summary(v):
    v = np.array(v); return dict(n=len(v), median=round(float(np.median(v)), 4), ge50=round(float((v >= .5).mean()), 4),
                                 ge75=round(float((v >= .75).mean()), 4), ge90=round(float((v >= .9).mean()), 4))

# ---------------- A. SAM
sys.path.insert(0, SAMPKG)
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
rows = json.load(open(f"{CROPS}/index.json"))["rows"]
def crop(r):
    return (np.asarray(Image.open(f"{CROPS}/images/{r['id']}.jpg").convert("RGB")),
            np.asarray(Image.open(f"{CROPS}/masks/{r['id']}.png")) > 0, np.array(r["box_xyxy"], np.float32))
for tr, te in (FOLDS if PART == "sam" else []):
    key = f"sam_heldout_{te}" if te else "sam_final_all"
    if key in res: continue
    model = build_sam2("configs/sam2.1/sam2.1_hiera_t.yaml", CKPT, device=dev); pred = SAM2ImagePredictor(model)
    def forward(img, box, grad):
        pred.set_image(img)
        _, _, _, ub = pred._prep_prompts(None, None, box[None], None, normalize_coords=True)
        with torch.set_grad_enabled(grad):
            sp, de = model.sam_prompt_encoder(points=None, boxes=ub, masks=None)
            hr = [f[-1].unsqueeze(0) for f in pred._features["high_res_feats"]]
            low, score, _, _ = model.sam_mask_decoder(image_embeddings=pred._features["image_embed"][-1].unsqueeze(0),
                image_pe=model.sam_prompt_encoder.get_dense_pe(), sparse_prompt_embeddings=sp, dense_prompt_embeddings=de,
                multimask_output=True, repeat_image=False, high_res_features=hr)
            return pred._transforms.postprocess_masks(low, pred._orig_hw[-1])[0], score[0]
    TEST = [r for r in rows if r["plant"] == te]; TRAIN = [r for r in rows if r["plant"] in tr]
    def evaluate():
        model.eval(); out = []
        for r in TEST:
            img, gt, box = crop(r)
            with torch.no_grad(): lg, sc = forward(img, box, False)
            out.append(iou((lg[int(sc.argmax())] > 0).cpu().numpy(), gt))
        return summary(out)
    base = evaluate() if TEST else None
    for p in model.parameters(): p.requires_grad = False
    params = list(model.sam_mask_decoder.parameters()) + list(model.sam_prompt_encoder.parameters())
    for p in params: p.requires_grad = True
    opt = torch.optim.AdamW(params, 1e-5, weight_decay=1e-4)
    for ep in range(8):
        model.train(); random.shuffle(TRAIN)
        for i, r in enumerate(TRAIN):
            img, gt, box = crop(r)
            if random.random() < .5: img, gt, box = img[:, ::-1].copy(), gt[:, ::-1].copy(), np.array([img.shape[1] - box[2], box[1], img.shape[1] - box[0], box[3]], np.float32)
            lg, sc = forward(img, box, True); t = torch.from_numpy(gt.astype(np.float32)).to(dev)[None].expand_as(lg); pr = lg.sigmoid()
            bce = F.binary_cross_entropy_with_logits(lg, t, reduction="none").mean((1, 2))
            dice = 1 - (2 * (pr * t).sum((1, 2)) + 1) / (pr.sum((1, 2)) + t.sum((1, 2)) + 1); k = int((bce + dice).argmin())
            with torch.no_grad():
                inter = ((pr > .5) & (t > .5)).sum((1, 2)).float(); uni = ((pr > .5) | (t > .5)).sum((1, 2)).float()
            ((bce[k] + dice[k] + .05 * F.mse_loss(sc, inter / uni.clamp(min=1))) / 4).backward()
            if (i + 1) % 4 == 0: opt.step(); opt.zero_grad()
    res[key] = dict(train=list(tr), held=te, n_train=len(TRAIN), base=base, tuned=evaluate() if TEST else None); save()
    torch.save({k: v for k, v in model.state_dict().items() if k.startswith(("sam_mask_decoder", "sam_prompt_encoder"))},
               f"{WORK}/sam2_tiny_decoder_tuned_heldout_{te}.pt")
    print(key, res[key], flush=True)
    del model, pred; torch.cuda.empty_cache()

# ---------------- B. OBB
from ultralytics import YOLO
allimgs = sorted(glob.glob(f"{OBB}/*/images/*.jpg"))
DATA = f"{WORK}/obbdata"
if not os.path.exists(DATA): shutil.copytree(OBB, DATA)
allimgs = sorted(glob.glob(f"{DATA}/*/images/*.jpg"))
def axis(poly):
    p = np.asarray(poly, float).reshape(4, 2); e1, e2 = p[1] - p[0], p[2] - p[1]
    e = e1 if np.hypot(*e1) >= np.hypot(*e2) else e2
    return math.degrees(math.atan2(e[1], e[0])) % 180, p.mean(0), min(np.hypot(*e1), np.hypot(*e2))
for tr, te in (FOLDS if PART == "obb" else []):
    key = f"obb_heldout_{te}" if te else "obb_final_all"
    if key in res: continue
    for s, pls in (("train", tr), ("val", (te,) if te else tr)):
        open(f"{WORK}/{key}_{s}.txt", "w").write(NL.join(i for i in allimgs if os.path.basename(i)[:6] in pls) + NL)
    Y = f"{WORK}/{key}.yaml"
    open(Y, "w").write(NL.join([f"train: {WORK}/{key}_train.txt", f"val: {WORK}/{key}_val.txt", "nc: 1", "names: ['leaflet']"]) + NL)
    YOLO("yolo11s-obb.pt").train(data=Y, imgsz=1280, epochs=150, patience=30, batch=4, degrees=180, fliplr=0.5, flipud=0.5,
                                 project=f"{WORK}/runs", name=key, exist_ok=True, seed=0, workers=2, verbose=False)
    best = f"{WORK}/runs/{key}/weights/best.pt"; v = YOLO(best).val(data=Y, imgsz=1280, batch=4, verbose=False)
    if te is None: shutil.copy(best, f"{WORK}/leaflet_obb_4plants.pt")
    m = YOLO(best); errs, total, found = [], 0, 0
    for img in [i for i in allimgs if te and os.path.basename(i).startswith(te)]:
        r = m.predict(img, imgsz=1280, conf=0.25, verbose=False)[0]; H, W = r.orig_shape
        preds = [axis(q) for q in r.obb.xyxyxyxy.cpu().numpy()] if r.obb is not None else []
        for line in open(img.replace("/images/", "/labels/").replace(".jpg", ".txt")).read().split(NL):
            if not line.strip(): continue
            ga, gc, gs = axis(np.array(line.split()[1:], float).reshape(4, 2) * [W, H]); total += 1
            near = [(np.hypot(*(pc - gc)), pa) for pa, pc, _ in preds]; near = [x for x in near if x[0] < .5 * gs]
            if near: found += 1; d = abs(min(near)[1] - ga) % 180; errs.append(min(d, 180 - d))
    e = np.array(errs)
    res[key] = dict(train=list(tr), held=te, obb_map50=round(float(v.box.map50), 4), obb_map50_95=round(float(v.box.map), 4),
                    matched=f"{found}/{total}", median_axis_error_deg=round(float(np.median(e)), 2) if len(e) else None,
                    within_30deg=round(float((e <= 30).mean()), 4) if len(e) else None)
    save(); print(key, res[key], flush=True)
    shutil.rmtree(f"{WORK}/runs/{key}", ignore_errors=True); torch.cuda.empty_cache()
shutil.rmtree(DATA, ignore_errors=True)
print(json.dumps(res, indent=1))
