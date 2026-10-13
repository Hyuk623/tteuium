# Claude handoff: fixed-mask leaf-vein evidence

## Read this distinction first

The user clarified that their positive assessments concerned **leaf veins / venation**, not specifically the midrib. Do not describe those assessments as successful main-vein identification, accepted midrib paths or recovered 3D curvature.

This handoff consolidates the work recorded in `CODEX_MIDRIB_WEB_START_2026-09-30.md`. Code names containing `midrib` are retained for compatibility; the batch output is continuous line evidence, not an anatomically classified vein network.

## Completed work and verified results

The existing Python preprocessing lab now supports all accepted middle/side observations and a linked results gallery. No separate annotation application was created.

| Item | Result |
| --- | --- |
| Plant | dwt_01 only |
| Input | 268 human-accepted photo-level masks across 14 photos |
| Expansion | Four starter observations plus 264 other labels |
| Fixed settings | Original Lab lightness, bright Gaussian-Hessian response, sigma = 2 original pixels |
| Candidate-evidence maps | 267 |
| Unavailable | 1: annotation 100, photo 24; no valid interior |
| Generation failures | 0 |
| Batch runtime | 12.347281 seconds, including batch source verification, excluding dataset preparation |
| Source integrity | 284 frozen source hashes checked; none changed |
| Validation | 34 targeted tests passed; JavaScript syntax check passed; gallery and annotation-1 browser integration checked |

These counts describe output generation, not detection accuracy. They are observations, not unique physical leaflets. New vein evidence remains unreviewed even though the enclosing leaf masks were accepted by a person.

## User feedback to preserve

| Annotation | User observation | Leaf-vein assessment | Gaussian preference |
| --- | --- | --- | --- |
| 127 | Faces right in the image | Captured well | Not specified |
| 90 | Leaf underside visible | Captured well | 2, most suitable |
| 211 | Leaf appears flat | Captured well | Not specified |
| 368 | No extra orientation note | Captured well | 2 |

The web interprets Gaussian 2 as sigma = 2 pixels. The chat feedback did not identify exact saved settings or path revisions. Other channel/contrast settings must not be inferred. Do not convert this qualitative feedback into acceptance of all generated paths. The earlier Codex UI smoke-test path in `build/midrib_web_20260930/midrib_reviews/20260930_221725_c31f202b` remains a software fixture, not a human reference.

## Implemented processing

```text
Human-accepted mask + original orientation-normalized RGB
  -> original-resolution crop with real surrounding image context
  -> original Lab lightness
  -> Gaussian-Hessian bright-line evidence, sigma 2
  -> exclude boundary/hole/invalid-pixel neighbourhoods
  -> continuous evidence + valid-area map + provenance
  -> original/overlay gallery and adjustable existing web lab
```

The helper uses a full square Gaussian support band of ceil(4*sigma), removes crop mean before derivative filtering, and normalizes responses by the 99th percentile within the usable region. Normalized values are not probabilities or absolute strengths comparable across images. Filters do not operate on a black-filled leaf cutout. No thresholded vein segmentation, branch graph, automatically guessed endpoints or anatomical main-vein classification was added.

The web can additionally compare original/processed brightness, stored-RGB channel fractions, sigma and bright/dark polarity. Those controls are available for review; the batch above used only the fixed settings in the results table. Optional user-anchored path tracing remains separate. A visible 2D line does not establish depth or surface curvature.

## Files and outputs

- `tools/leaf_preprocess_lab.py`: added `prepare --all-observations`; existing default sampling preserved; serves gallery artifacts and existing secured review APIs.
- `tools/leaf_preprocess_lab.html`, `.js`: automatic vein-evidence preview without anchors; optional midrib-path controls retained.
- `tools/leaf_vein_batch.py`: new reproducible batch command, reusing `tools/midrib_review.py::propose` without anchors and the existing ridge helper.
- `tools/tests/test_leaf_vein_batch.py`: multiple labels per photo, source-change rejection, flat-image unavailable status, coordinate provenance and immutable batch outputs.
- Dataset: `build/leaf_veins_dwt01_20260930/dataset.json`.
- Results: `build/leaf_veins_dwt01_20260930/veins/`.
- `summary.csv`: every observation's status, usable area, failure reason and runtime.
- `manifest.json`: settings, counts, source checks, tool hashes and limitation flags.
- `sample_*.png`: original and evidence overlay side by side.
- `sample_*.npz`: continuous evidence and valid-area arrays.
- `sample_*.json`: source observation, original-pixel crop mapping, settings and unreviewed state.
- `index.html`: gallery served through the existing lab.

Dataset SHA256: `c5e2c8ee01c01fc944318e68b6accf606c9212d70edb841e2f21c1c20c927162`.

## Open and reproduce

Gallery: http://127.0.0.1:8833/veins/

Adjustable review: http://127.0.0.1:8833/?annotation=1

Serve already-generated results from the project root; do not start a duplicate server if port 8833 is already serving this dataset:

```powershell
python -X utf8 -m tools.leaf_preprocess_lab serve --run build/leaf_veins_dwt01_20260930 --port 8833
```

For a new reproduction, use a new output directory. Existing outputs intentionally refuse overwrite:

```powershell
python -X utf8 -m tools.leaf_preprocess_lab prepare --accepted build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260929_092627_faeb15/accepted.json --session build/new_captures_20260920/dwt_01/edit_session --out build/leaf_veins_dwt01_NEW --all-observations
python -X utf8 -m tools.leaf_vein_batch --run build/leaf_veins_dwt01_NEW --sigma 2
python -m pytest tools/tests/test_leaf_vein_batch.py tools/tests/test_midrib_review.py tools/tests/test_leaf_preprocess_lab.py -q
node --check tools/leaf_preprocess_lab.js
```

The earlier four-sample dataset and review history under `build/midrib_web_20260930` remain separate and preserved.

## Follow-up for Claude

1. Inspect original/overlay pairs and distinguish real veins from folds, texture and reflections. Preserve observation IDs and record any human feedback against the exact settings/result revision.
2. Keep vein visibility, main-vein identification, cross-view physical landmarks and 3D surface reconstruction as separate stages. Do not derive physical point identity from line-array indices or uniformly sampled curves.
3. Treat low usable-area observations explicitly. Do not fill hidden veins or silently accept sparse responses as a complete vein network.
4. If extending to other plants, record a separate run and its purpose. This extension did not process dwt_02/03/04. The latest Claude LOG entry describes dwt_02 as a held-out-plant check, not an untouched test; do not overstate independence using older wording.
5. Establish reviewed vein references before reporting precision, recall or accuracy. Existing accepted masks validate leaf extent, not internal vein correctness.

Original photos, labels, masks, calibration and weights are preserved. No learned inference, training or GitHub push occurred. `main_vein_identified=false`, `validated_metric=false`, `suitable_for_ppfd=false`; independent vein accuracy and true 3D curvature remain unavailable. This document requests continuity/review, not an automatic model-training run.
