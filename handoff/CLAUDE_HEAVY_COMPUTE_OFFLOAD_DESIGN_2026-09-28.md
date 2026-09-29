# Heavy-compute offload (Kaggle / Colab, CPU or GPU): design

Claude Code, 2026-09-28. Status: **design only, not implemented.** Standing split applies: Kaggle upload and
collection = Claude; Colab upload and collection = Codex; either may read the other's results. XL files stay frozen
unless Codex decides otherwise.

## 1. What is heavy (measured on this PC)

PC: i7-1360P, 12 cores / 16 threads, 15.6 GB RAM, **2.5 GB free** while the editors, watcher and one auto run are
up. The bottleneck is memory and wall time, not core count.

| Step | Where | Measured / recorded | Memory |
|---|---|---|---|
| Model drafts (`organ_prelabel`: 3 detectors × 3 flips at 1280 + stem/petiole instance masks) | photo-only auto S1 | 1–3 min per photo → ~35 min per plant (auto validation run, 09-28 13:43–) | ~7 GB process |
| SAM leaflet masks (`leaflet_mask_batch run`) | S2 | ~3.5 s per box (L222) → ~15–25 min per plant | 2–3 GB |
| ChArUco import + poses | S0 | seconds | small |
| Visual hull, regions, stem (`plant_structure`) | S3 | ~30 s per plant (S3 `seconds`) | < 1 GB |
| S4–S7, site, XL export | — | seconds to a minute | small |
| SfM (`pycolmap`) | experiment | already on Kaggle CPU | — |

So only **S1 drafts and S2 SAM** need to leave the PC. Everything that reads the board or writes decisions stays
local.

## 2. Targets

| Backend | Hardware (free tier) | Use it for | Notes |
|---|---|---|---|
| Kaggle GPU (T4) | 1 GPU, 2 batch sessions, weekly GPU quota | default for S1+S2 | fastest; `machine_shape: NvidiaTeslaT4` required (P100 fails, see kaggle-gpu-kernel skill) |
| Kaggle CPU | 4 cores, ~30 GB RAM, no GPU quota used | when GPU quota or the 2-session limit is used up; several plants in one session | RAM is the gain over this PC; speed about like local |
| Colab CPU | 2 cores, ~12 GB (Codex's hosted run reported `cpu_count: 2`) | memory relief or running in parallel with the PC | slower per job than this PC; interactive, session can end; transfer-back needs care (09-28 download issue) |
| Local | this PC | fallback, small jobs | blocks the PC for ~1 h per plant |

Rule: Kaggle GPU → Kaggle CPU → Colab CPU → local. A CPU backend is worth it for RAM and parallel plants, not for
speed; say so in the run record.

## 3. Split the auto run into three phases with a file contract

```
Phase A (local)            Phase B (remote, heavy)                 Phase C (local)
photos → order/organise →  job bundle ──► drafts + SAM masks ──►   result bundle → labels (auto) →
ChArUco poses → session                                            mask batch (precomputed, auto) → S3–S7 (+XL)
```

- **Phase A** = `plant_auto` up to `prepare_leaf_edit_session` (unchanged).
- **Phase B** runs `organ_prelabel.run(models, images, out, sam_config=<SAM>)`, which already produces leaflet outlines
  from SAM per box, plus stem/petiole instance masks. No board, no human decision, no pipeline state is needed.
- **Phase C** = `labels_from_prelabels` + a new batch path that loads the remote leaflet masks as precomputed
  candidates (below) + the normal pipeline.

### Job bundle (`offload-job-1`, zip)

```
job.json          schema, job_id, plants[], backend request, created_at, requested_by
inputs/<plant>/images/*.png      prepared frames (edit_session/images), ~150 MB per plant
inputs/<plant>/frames.json       image_file, view_code, size, sha256 (from capture.json; no pose needed remotely)
models/models.json               detector weights and SAM checkpoint: path + sha256 (weights ride as a Kaggle dataset
                                 or Colab file, uploaded once and reused by hash)
code/                            organ_prelabel.py, leaflet_segmenter.py, leaf_light/common.py (pinned by sha256)
manifest.json                    sha256 of every file above
```

### Result bundle (`offload-result-1`, zip)

```
result.json        job_id, input manifest sha256, backend, hardware, versions, per-plant status, timings
<plant>/prelabels.coco.json      boxes + scores; leaflet polygons from SAM with sam_score; stem/petiole polygons
<plant>/overlays/*.jpg           for a person to glance at
manifest.json                    sha256 of every file
```

Local import refuses a result whose input manifest hash, plant set or file hashes do not match; outputs go to new
folders only (same rules as `colab_xl_bridge import`).

### Precomputed masks in the mask batch (Phase C, Claude)

Add `leaflet_mask_batch.prepare(..., precomputed=<prelabels.coco.json>)`: for each leaflet box with a remote
polygon, rasterise it into the item as `manual_raster`, `generation='ready'`, `generation_source='remote SAM
(<backend>, <checkpoint sha>)'`, then `auto_accept()` as now (`review_source='auto'`). Boxes without a polygon stay
`pending` and can still be generated locally. A person's edit still overrides.

## 4. Runners (same bundle, different transport)

| Runner | Owner | Transport | Poll / collect |
|---|---|---|---|
| `tools/offload_job.py pack / import` | Claude | builds the job bundle; imports and verifies the result | — |
| Kaggle runner | Claude | `kaggle datasets version` (job bundle) + `kaggle kernels push` (fixed kernel reading the bundle) | `kernels status` loop; `kernels output --page-size 200` with `PYTHONUTF8=1` |
| Colab runner | Codex | reuse `colab_xl_bridge` notebook pattern: Files-sidebar upload, run cell, visible-output content-addressed return (the 09-28 method) | notebook cell prints result hashes |

Kaggle kernel details: `enable_gpu` true with `machine_shape: NvidiaTeslaT4`, or false for CPU; recursive input
discovery + `assert`; all writes under `/kaggle/working`; per-plant results written as they finish so a re-push
resumes; one kernel handles several plants.

## 5. Integration

`plant_auto --offload kaggle-gpu|kaggle-cpu|colab|local` (default local):

1. Phase A locally, `offload_job pack`.
2. kaggle: push and wait (detached, status log); colab: stop with the Korean instruction "Codex/Colab: run this job",
   then resume with `plant_auto --resume <out> --result <zip>`.
3. Phase C locally.

`auto_run.json` records backend, hardware, timings, job/result hashes; STATUS keeps "자동, 사람 미확인".

## 6. Acceptance checks before use

- Same job on local and Kaggle: identical box sets within float tolerance (CPU vs GPU numerics), mask IoU ≥ 0.99 per
  item; record differences rather than hide them.
- Tampered result, wrong plant set, changed input image → import refuses.
- Resume after a killed session skips finished plants.
- Timings recorded per backend (no speed claims before they exist).

## 7. Not in scope

Training (already Kaggle), S0 pose solving, S3–S7, XL export, PPFD. No photos leave the PC except the prepared frames
inside a private Kaggle dataset or a Colab session the user owns.
