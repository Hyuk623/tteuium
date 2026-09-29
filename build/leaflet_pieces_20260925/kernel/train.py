# Tomato leaflet separation: piece classes (background / interior / boundary) vs SAM 2.1 tiny, base and fine-tuned.
# Same validation leaflets for both: dwt_02 photos with even view codes (117 human-accepted masks).
import glob, json, os, subprocess, sys, time, random
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "segmentation-models-pytorch", "hydra-core", "iopath"], check=True)
import numpy as np, torch, torch.nn.functional as F
from PIL import Image
from scipy import ndimage

WORK = "/kaggle/working"
RESULT = f"{WORK}/results.json"
res = json.load(open(RESULT)) if os.path.exists(RESULT) else {}
def save(): json.dump(res, open(RESULT, "w"), indent=1)
print("GPU", torch.cuda.get_device_name(0)); dev = "cuda"
torch.manual_seed(0); np.random.seed(0); random.seed(0)

def find(name):
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    assert hits, f"{name} not found under /kaggle/input"
    return hits
PIECES = [os.path.dirname(p) for p in find("index.json") if json.load(open(p))["schema"] == "leaflet-piece-dataset-1"][0]
CROPS = [os.path.dirname(p) for p in find("index.json") if json.load(open(p))["schema"] == "sam-finetune-dataset-1"][0]
CKPT = find("sam2.1_hiera_tiny.pt")[0]
SAMPKG = os.path.dirname(os.path.dirname(find("sam2_image_predictor.py")[0]))
print(PIECES, CROPS, CKPT, SAMPKG)

def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0

def summary(v):
    v = np.array(v)
    return dict(n=len(v), median=round(float(np.median(v)), 4), mean=round(float(v.mean()), 4),
                ge50=round(float((v >= .5).mean()), 4), ge75=round(float((v >= .75).mean()), 4), ge90=round(float((v >= .9).mean()), 4))

# ------------------------------------------------------------------ A. piece classes
if "pieces" not in res:
    import segmentation_models_pytorch as smp
    from skimage.segmentation import watershed
    idx = json.load(open(f"{PIECES}/index.json"))
    def load(p):
        img = np.asarray(Image.open(f"{PIECES}/{p['photo']}.jpg").convert("RGB"))
        cls = np.asarray(Image.open(f"{PIECES}/{p['photo']}_classes.png"))
        ins = np.asarray(Image.open(f"{PIECES}/{p['photo']}_instances.png")).astype(np.int32)
        return img, cls, ins
    train = [load(p) for p in idx["photos"] if p["split"] == "train"]
    val = [(p, *load(p)) for p in idx["photos"] if p["split"] == "val"]
    MEAN, STD = np.array([0.485, 0.456, 0.406]) * 255, np.array([0.229, 0.224, 0.225]) * 255
    norm = lambda im: torch.from_numpy(((im - MEAN) / STD).transpose(2, 0, 1)).float()
    C = 512
    def sample(img, cls):
        h, w = cls.shape
        ys, xs = np.nonzero(cls == 1)
        k = np.random.randint(len(ys))
        y0 = int(np.clip(ys[k] - np.random.randint(C), 0, h - C)); x0 = int(np.clip(xs[k] - np.random.randint(C), 0, w - C))
        im, cl = img[y0:y0 + C, x0:x0 + C].astype(np.float32), cls[y0:y0 + C, x0:x0 + C]
        if random.random() < .5: im, cl = im[:, ::-1], cl[:, ::-1]
        if random.random() < .5: im, cl = im[::-1], cl[::-1]
        r = random.randint(0, 3); im, cl = np.rot90(im, r), np.rot90(cl, r)
        im = np.clip(im * random.uniform(.8, 1.2) + random.uniform(-15, 15), 0, 255)
        return norm(np.ascontiguousarray(im)), torch.from_numpy(np.ascontiguousarray(cl).astype(np.int64))
    model = smp.Unet("resnet34", encoder_weights="imagenet", classes=3).to(dev)
    counts = np.bincount(np.concatenate([c[c != 255].ravel() for _, c, _ in train]), minlength=3).astype(float)
    wts = torch.tensor((counts.sum() / (3 * counts)) ** .5, dtype=torch.float32, device=dev)
    print("class pixels", counts, "weights", wts)
    opt = torch.optim.AdamW(model.parameters(), 3e-4, weight_decay=1e-4)
    EPOCHS, PER, BS = 60, 24, 8
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-4, total_steps=EPOCHS * (len(train) * PER // BS))
    scaler = torch.amp.GradScaler()
    t0 = time.time()
    for ep in range(EPOCHS):
        model.train(); batch = [sample(im, cl) for im, cl, _ in train for _ in range(PER)]; random.shuffle(batch); tot = 0
        for i in range(0, len(batch) - BS + 1, BS):
            x = torch.stack([b[0] for b in batch[i:i + BS]]).to(dev); y = torch.stack([b[1] for b in batch[i:i + BS]]).to(dev)
            with torch.autocast("cuda", dtype=torch.float16):
                loss = F.cross_entropy(model(x), y, weight=wts, ignore_index=255)
            opt.zero_grad(); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step(); tot += loss.item()
        if ep % 10 == 9: print(f"pieces ep{ep+1} loss {tot / (len(batch) // BS):.4f} {time.time() - t0:.0f}s", flush=True)
    torch.save(model.state_dict(), f"{WORK}/pieces_unet_r34.pt")
    model.eval()

    def predict(img):
        h, w = img.shape[:2]; H, W = (h + 31) // 32 * 32, (w + 31) // 32 * 32
        x = torch.zeros(1, 3, H, W); x[0, :, :h, :w] = norm(img.astype(np.float32))
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            p = model(x.to(dev)).float().softmax(1)[0, :, :h, :w].cpu().numpy()
        return p
    def instances(p, min_px=40):
        interior = p.argmax(0) == 1
        seeds, n = ndimage.label(interior)
        sizes = ndimage.sum(np.ones_like(seeds), seeds, range(1, n + 1))
        for k, s in enumerate(sizes, 1):
            if s < min_px: seeds[seeds == k] = 0
        leafy = p[0] < .5                                           # interior or boundary
        return watershed(p[2], markers=seeds, mask=leafy)            # grow seeds across boundary pixels
    per_leaf, merged, pix = [], 0, []
    for meta, img, cls, ins in val:
        p = predict(img); lab = instances(p)
        known = cls != 255
        pix.append(dict(photo=meta["photo"], acc_known=float((p.argmax(0)[known] == cls[known]).mean()),
                        boundary_recall=float((p.argmax(0)[cls == 2] == 2).mean()), interior_recall=float((p.argmax(0)[cls == 1] == 1).mean())))
        for g in np.unique(ins[ins > 0]):
            t = ins == g
            cand = np.unique(lab[t]); cand = cand[cand > 0]
            best = max([iou(t, lab == c) for c in cand], default=0.0)
            per_leaf.append(best)
        for c in np.unique(lab[lab > 0]):
            m = lab == c; hit = [g for g in np.unique(ins[m]) if g > 0 and (ins[m] == g).sum() >= .5 * (ins == g).sum()]
            merged += len(hit) > 1
        Image.fromarray((np.stack([p[1], p[2], p[0]], -1) * 255).astype(np.uint8)).save(f"{WORK}/pieces_{meta['photo']}.png")
    res["pieces"] = dict(per_leaflet_iou=summary(per_leaf), instances_merging_two_leaflets=merged, pixels=pix, epochs=EPOCHS,
                         note="per GT leaflet: best IoU of any predicted instance (seeds = interior components, grown by watershed over boundary prob)")
    save(); print("pieces", res["pieces"]["per_leaflet_iou"], "merged", merged, flush=True)
    del model; torch.cuda.empty_cache()

# ------------------------------------------------------------------ B. SAM 2.1 tiny, box prompt
sys.path.insert(0, SAMPKG)
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
cidx = json.load(open(f"{CROPS}/index.json"))
def crop(r):
    return (np.asarray(Image.open(f"{CROPS}/images/{r['id']}.jpg").convert("RGB")),
            np.asarray(Image.open(f"{CROPS}/masks/{r['id']}.png")) > 0, np.array(r["box_xyxy"], np.float32))
VAL = [r for r in cidx["rows"] if r["split"] == "val"]; TRAIN = [r for r in cidx["rows"] if r["split"] == "train"]
model = build_sam2("configs/sam2.1/sam2.1_hiera_t.yaml", CKPT, device=dev)
pred = SAM2ImagePredictor(model)

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

def evaluate(tag):
    out = []
    model.eval()
    for r in VAL:
        img, gt, box = crop(r)
        with torch.no_grad():
            logits, score = forward(img, box, False)
        m = (logits[int(score.argmax())] > 0).cpu().numpy()          # the editor's top candidate at logit > 0
        out.append(iou(m, gt))
    res[tag] = dict(per_leaflet_iou=summary(out)); save(); print(tag, res[tag]["per_leaflet_iou"], flush=True)

if "sam_base" not in res: evaluate("sam_base")
if "sam_tuned" not in res:
    for p in model.parameters(): p.requires_grad = False
    params = list(model.sam_mask_decoder.parameters()) + list(model.sam_prompt_encoder.parameters())
    for p in params: p.requires_grad = True
    opt = torch.optim.AdamW(params, 1e-5, weight_decay=1e-4); ACC, EPOCHS = 4, 8; t0 = time.time()
    for ep in range(EPOCHS):
        model.train(); random.shuffle(TRAIN); tot = 0
        for i, r in enumerate(TRAIN):
            img, gt, box = crop(r)
            if random.random() < .5: img, gt, box = img[:, ::-1].copy(), gt[:, ::-1].copy(), np.array([img.shape[1] - box[2], box[1], img.shape[1] - box[0], box[3]], np.float32)
            logits, score = forward(img, box, True)
            t = torch.from_numpy(gt.astype(np.float32)).to(dev)[None].expand_as(logits)
            prob = logits.sigmoid()
            bce = F.binary_cross_entropy_with_logits(logits, t, reduction="none").mean((1, 2))
            dice = 1 - (2 * (prob * t).sum((1, 2)) + 1) / (prob.sum((1, 2)) + t.sum((1, 2)) + 1)
            k = int((bce + dice).argmin())                              # train the candidate closest to the human mask
            with torch.no_grad():
                inter = ((prob > .5) & (t > .5)).sum((1, 2)).float(); uni = ((prob > .5) | (t > .5)).sum((1, 2)).float()
            loss = bce[k] + dice[k] + 0.05 * F.mse_loss(score, inter / uni.clamp(min=1))
            (loss / ACC).backward(); tot += loss.item()
            if (i + 1) % ACC == 0: opt.step(); opt.zero_grad()
        print(f"sam ep{ep+1} loss {tot / len(TRAIN):.4f} {time.time() - t0:.0f}s", flush=True)
    torch.save({k: v for k, v in model.state_dict().items() if k.startswith(("sam_mask_decoder", "sam_prompt_encoder"))}, f"{WORK}/sam2_tiny_decoder_tuned.pt")
    evaluate("sam_tuned")
print(json.dumps(res, indent=1))
