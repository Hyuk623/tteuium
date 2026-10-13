# Midrib starting workflow in the existing Python web lab

The user explicitly selected the existing Python web application rather than MATLAB. Extend tools/leaf_preprocess_lab.py, .html and .js. Reuse reviewed masks, original-pixel provenance, local-token API security and the numerical ridge/path helpers from tools/midrib_flow.py without invoking its SAM run function.

Initial scope: select a reviewed leaflet, mark a visible base and tip (optional intermediate anchors in path order), compare original or processed luminance and stored-RGB fractions, preview a Gaussian-Hessian bright/dark ridge path, undo/reset anchors, and explicitly save a new derived 2D record. No training, learned inference, 3D calculation, automatic physical ID assignment or original-label edits.

The mask stays fixed. Filters see real image context, not a black-filled background. Exclude a full Gaussian support band at mask boundaries/holes and invalid input pixels; do not silently snap anchors or bridge disconnected parts. Store coordinates in original pixels and explain unavailable paths. Base/tip identity comes from the user's visible clicks, not PCA extremes. Outputs remain candidates unless explicitly reviewed in 2D; no cross-view or anatomical accuracy is inferred.

Validate original-coordinate round trips, curved synthetic path recovery, holes/disconnected regions, invalid anchors, source immutability, derived save/history and stale UI results. Use existing prepared lab samples; no need to repeat SAM. Save numerical paths as CSV and source/settings/review metadata as JSON under a new build result folder. Inspect the running web UI when browser tools are available.

## Implemented and checked (2026-09-30)

The basic workflow is available at http://127.0.0.1:8832/?annotation=368. Start it from the project directory with:

```powershell
python -X utf8 -m tools.leaf_preprocess_lab serve --run build/midrib_web_20260930 --port 8832
```

This starter dataset contains four observations from **one plant, dwt_01**: annotations 127, 90, 211 and 368. It reuses the prepared samples from build/rgb_preprocess_study_ui_20260929. Ten unique original source hashes were checked; none changed. No SAM inference, training or 3D reconstruction was run.

### User workflow

Select a leaflet; click its visible base, optional intermediate anchors, and tip in order. Calculate a candidate; compare original/processed Lab lightness or original stored-RGB fractions, bright/dark ridges and Gaussian sigma (0.5–4 original pixels). Undo or reset incorrect anchors. Save explicitly as candidate, confirmed_2d or rejected. Confirmation is local 2D review only and does not establish physical landmark identity across views.

Added tools/midrib_review.py and tools/tests/test_midrib_review.py; extended the existing tools/leaf_preprocess_lab.py, .html and .js. The numerical module reuses bright_ridge and cheapest_path from tools/midrib_flow.py without changing that file or invoking its inference entry point. The existing secured POST interface now includes /api/midrib and /api/midrib/save.

The mask remains fixed. A full square Gaussian support band (ceil(4*sigma)) excludes mask boundaries, holes and invalid/clipped neighbourhoods. Filters use the real crop context. Anchors are never snapped and disconnected mask regions are not bridged. Constant-image derivative residuals are suppressed by subtracting the crop mean before derivative filtering, with a uniform-image regression test. Ridge normalization is display/path evidence, not an accuracy score. Graphs exceeding the explicit size limit return unavailable rather than silently downsampling.

Saved runs under build/midrib_web_20260930/midrib_reviews contain original/evidence images, a path overlay, original-pixel path.csv and review.json with observation/source hashes, settings, anchors, review state and software provenance. Input changes invalidate the displayed candidate and disable saving until recalculation; save rechecks the frozen source hashes. No original annotation or mask is overwritten.

### Validation and limits

- `python -m pytest tools/tests/test_midrib_review.py tools/tests/test_midrib_flow.py tools/tests/test_leaf_preprocess_lab.py -q`: **34 passed** (4.06 seconds).
- `node --check tools/leaf_preprocess_lab.js`: passed.
- Browser test on annotation 368: two anchor clicks, candidate calculation and explicit candidate save succeeded. The displayed path length was 215.9 pixels, which is a software check, not a validated anatomical length. Undo invalidated the path and disabled save. Final browser state was reset to zero anchors; the mask's usable interior was 74.6% with default sigma 2.
- UI smoke-test record: build/midrib_web_20260930/midrib_reviews/20260930_221725_c31f202b. Its note explicitly identifies unverified Codex test clicks. Exclude this record from human ground truth and research metrics. This early save preceded addition of path_overlay.png; subsequent saves include it.
- Anatomical midrib accuracy, cross-view point correspondence, physical length, 3D curvature and PPFD readiness remain unvalidated. Image ridges can follow side veins, highlights or folds; user review remains necessary.

## User visual feedback (2026-09-30)

Source: the user's chat review of the existing Python web results. The user subsequently clarified that all four assessments refer to leaf veins (venation), not specifically the midrib. This correction supersedes the earlier midrib interpretation. These are qualitative observation-level judgments, not independent quantitative accuracy measurements. They do not confirm identification of the main vein or an accepted midrib path.

| Annotation | User-reported appearance | Leaf-vein assessment | Preferred Gaussian setting |
| --- | --- | --- | --- |
| 127 | Leaf faces right in the image | Captured well | Not specified |
| 90 | The underside of the leaf is shown | Captured well | 2; reported as most suitable |
| 211 | Leaf appears flat | Captured well | Not specified |
| 368 | No additional orientation note | Captured well | 2 |

Interpret Gaussian 2 as the current web's Gaussian sigma=2 original pixels, pending association with an explicitly saved settings record. Other channel, polarity, exposure and contrast settings were not supplied in this feedback. Do not assume they were identical between observations.

Keep the user's flatness observation for 211 separate from the successful leaf-vein detection judgment: neither proves nor disproves actual 3D surface curvature. Visible leaf veins and image appearance alone do not establish leaf depth/curvature. The underside observation for 90 is user-reported, not an automatically classified leaf surface.

This feedback does not identify exact saved path revisions or anchor coordinates. Preserve it as chat-level human feedback; do not retroactively accept every candidate, the earlier Codex smoke-test path, or unrelated paths. Sigma=2 is a per-observation preference for 90 and 368, not a validated universal optimum. No source data, masks, path review states or program defaults were modified by this note.

## Extend leaf-vein candidates to other labels (2026-09-30, authorized)

The user requests applying the visually reviewed method to other labels. Start with all human-accepted dwt_01 observations in the same export, preserving dwt_02's frozen evaluation role. Reuse the existing web lab and numerical Gaussian-Hessian helper at sigma=2 original pixels, original Lab lightness, bright ridges. These are exploratory fixed settings; only sigma was explicitly preferred for labels 90 and 368. Generate continuous leaf-vein evidence maps without endpoint guesses, main-vein classification, automatic acceptance, training or learned inference. Record excluded areas, flat/insufficient evidence and all failures. Extend the lab's prepare command with an explicit all-observations option, preserving its default sampling. Save a new dataset and batch outputs under build; keep old four-sample results and review histories intact. Provide a contact gallery linked to each observation in the existing web. Verify preserved coordinate/hash contracts and counts, and test batch status handling. This does not establish botanical vein accuracy or 3D curvature.

## Leaf-vein expansion delivered (2026-09-30)

Applied the same fixed-mask numerical helper to all **268 human-accepted observations across 14 dwt_01 photos**, including the four starter observations (264 additional labels). This is one plant, not 268 physical leaflets. dwt_02/03/04 were not processed in this extension.

- Output: build/leaf_veins_dwt01_20260930; batch artifacts in its veins/ directory.
- Gallery: http://127.0.0.1:8833/veins/ ; adjustable existing lab: http://127.0.0.1:8833/?annotation=1 . Existing port 8832 and its four-observation history were retained.
- Settings: original Lab lightness, bright Gaussian-Hessian response, sigma=2 original pixels; no user anchors, guessed endpoints, skeleton threshold or main-vein classification.
- Results: 267 candidate-evidence maps, 1 unavailable (annotation 100, photo 24, no valid interior after mask/invalid-neighbourhood exclusion), 0 generation failures. Generation and source verification took 12.35 seconds, excluding dataset preparation. These are execution/coverage counts, NOT anatomical detection precision or success rates.
- All 284 frozen source hashes were checked and unchanged. Source dataset SHA256: c5e2c8ee01c01fc944318e68b6accf606c9212d70edb841e2f21c1c20c927162. Original photos, masks, annotations and previous reviews were preserved.
- Each observation has original/overlay PNG, continuous float response and valid-area NPZ, and JSON provenance. summary.csv includes every status, coverage, reason and runtime; manifest.json includes settings, source checks and tool hashes. Evidence is normalized per crop, not a calibrated probability or cross-image absolute strength.
- Extended prepare with --all-observations; default sampling stays unchanged. Added tools/leaf_vein_batch.py and tools/tests/test_leaf_vein_batch.py. Existing web wording now distinguishes automatic vein evidence from optional anchored midrib paths. No learned inference, training or 3D calculation.
- Validation: 34 tests passed (leaf_vein_batch, midrib_review, leaf_preprocess_lab), node --check passed. Browser verified the 268-item gallery and its annotation-1 link; the existing comparison screen selected label 1 and automatically displayed sigma=2 evidence (80.8% usable interior) with no clicks/anchors required. No result was accepted on the user's behalf.

Reproduction commands (use a fresh output directory for new runs):

```powershell
python -X utf8 -m tools.leaf_preprocess_lab prepare --accepted build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260929_092627_faeb15/accepted.json --session build/new_captures_20260920/dwt_01/edit_session --out build/leaf_veins_dwt01_20260930 --all-observations
python -X utf8 -m tools.leaf_vein_batch --run build/leaf_veins_dwt01_20260930 --sigma 2
python -X utf8 -m tools.leaf_preprocess_lab serve --run build/leaf_veins_dwt01_20260930 --port 8833
```

Small usable regions remain explicitly reported, even if a nonzero response exists. All new maps remain unreviewed; folds, reflection and texture may respond. No independent vein accuracy, main-vein identity, 3D curvature or PPFD readiness is established.
