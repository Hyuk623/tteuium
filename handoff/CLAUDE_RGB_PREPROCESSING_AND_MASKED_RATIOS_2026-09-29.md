# Claude Code handoff: RGB preprocessing and masked channel ratios

Date: 2026-09-29

## User request and scope

The user now explicitly requests an English Markdown handoff to Claude. This supersedes the earlier instruction to keep this experiment independent and not hand it off. The historical independent-work notes remain valid descriptions of what was done at the time.

Reuse the implemented local comparison tool. This handoff documents the current implementation and proposes integration points; it does not claim that the main annotation/reconstruction application has already been integrated. No training, learned inference, automatic segmentation, landmark confirmation, reconstruction or GroIMP execution was performed for this experiment.

The latest masking clarification is explicit: apply the existing reviewed mask for **selected leaflet annotation 368**, not a whole-plant mask. Applying this mask does not detect a new leaf or validate a prediction against independent ground truth.

All paths below are relative to the existing `Tomato 3D phenotyping analysis` project. Preserve original images, annotations, mask files, camera calibration and geometry.

## Implemented files

| File | Responsibility |
|---|---|
| `tools/leaf_preprocess_lab.py` | Preparation, numerical processing, local HTTP service and derived saves |
| `tools/leaf_preprocess_lab.html` | Korean comparison interface |
| `tools/leaf_preprocess_lab.js` | Controls, full-photo/channel/mask switching, explicit save |
| `tools/tests/test_leaf_preprocess_lab.py` | Focused numerical, preservation and API tests |
| `build/rgb_preprocess_lab_20260929/` | Pilot snapshot, comparison tables and generated results |

## Workflow A: photometric comparison inside a reviewed leaflet ROI

```text
Original photograph + reviewed mask
  -> original-pixel crop with surrounding context
  -> exposure / gamma / local contrast / denoise controls
  -> original versus processed image comparison
  -> generic line-evidence overlay
  -> human preference and explicit derived save
```

- Crops include 40 pixels of context where the image bounds permit it. No geometric warp or resampling is applied to the stored crop. Browser zoom is display-only.
- Record the crop offset: `x_original = x_crop + offset_x_px`, likewise for Y.
- Exposure uses linearized RGB; gamma adjusts midtones; CLAHE changes the Lab lightness channel; bilateral filtering is optional. These are diagnostic image treatments, not recovery of missing detail.
- The source image is treated as sRGB when linearizing. The phone's actual processing/tone mapping is not known.
- RGB channel ratios in this **crop-analysis route** are computed from original, linearized RGB, independently of exposure controls.
- Generic Gaussian/Hessian ridge evidence can show veins, folds, shadows or other lines. It is not a verified midrib, anatomical classifier or physical landmark.
- The provisional combined feature is 0.7 brightness evidence plus 0.3 chromatic evidence. Per-image 99th-percentile normalization is a display convention, not confidence.
- Dark/clipped source regions and neighborhoods too close to mask boundaries are excluded from line evidence. Brightness/combined analysis also excludes newly dark/clipped processed regions. Exclusion does not remove original observations.
- Report clipping, dark-pixel fraction, usable region and local contrast as descriptive diagnostics only. More contrast or more lines does not prove better 3D reconstruction.
- User preference states: unreviewed / easier / similar / harder. There is no automatic best-setting selection.

## Workflow B: full-photograph scalar R/G/B fraction maps

```text
Original full RGB photograph
  -> S = R + G + B, using float32 arithmetic
  -> R/S or G/S or B/S
  -> fixed grayscale display
  -> optional unchanged reviewed leaflet mask
```

**This route uses the stored 8-bit RGB channel values directly. It does not linearize or apply exposure/gamma/CLAHE first.** Do not silently equate these ratios with Workflow A's linear-RGB ratios. Preserve and expose the numerical basis when integrating them.

For each channel:

- Divide by the same RGB sum. Cast before summation to avoid uint8 overflow.
- Display 0 as black and 1 as white; no per-image min-max normalization. Equal R/G/B gives approximately 1/3 for each channel.
- `R+G+B=0` is undefined: numeric NaN, magenta in the diagnostic PNG. Other low-light or clipped pixels are still shown in this full-image route; their values are not confidence or reliable material-colour measurements.
- A bright pixel means a larger channel fraction, not higher absolute illumination or detection accuracy.
- No colour-threshold segmentation, board rejection or organ classification is performed.

Relevant functions: `full_channel_fraction(rgb, channel)` for red/green/blue; compatibility wrapper `full_green_fraction(rgb)`; `apply_reviewed_mask(display, mask)` for RGBA masking.

## Existing-mask application and the current example

The mask is applied **after** calculating each full-image ratio. It does not change the RGB denominator or the retained ratio values.

| Field | Value |
|---|---|
| Plant / session | `dwt_01` / `dwt_01_20260920` |
| Photograph | `dwt_01_20260920_18.png` |
| Observation / annotation | `dwt_01_a368` / `368` |
| Lab sample | `sample_003` |
| Full image size | 3024 x 3024 pixels |
| Reviewed mask foreground | 45,507 pixels |
| Scope | This selected leaflet only |

The same reviewed raster mask is used for all three channels. Keep disconnected visible components and holes unchanged. RGBA alpha is 255 inside and 0 outside. RGB values under transparent pixels may remain present; consumers must honor alpha. Numeric masked arrays contain NaN outside the mask and wherever the ratio is undefined. Full dimensions and original pixel coordinates are retained.

The example's pose status is `too_few_corners`, `passes_pose_gate=false`, and physical identity is not confirmed by this tool. Mask display does not alter those states or make the observation 3D/PPFD-ready.

## Data and artifact locations

Pilot manifest: `build/rgb_preprocess_lab_20260929/dataset.json`.

The pilot contains **8 image-level leaflet observations** across dwt_01/02 middle/side views. This is not a count of unique physical leaflets. Sampling uses mask-area quantiles with distinct photographs, not an accuracy-optimized or independent evaluation selection.

Reviewed source exports and sessions:

```text
build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260929_092627_faeb15/accepted.json
build/new_captures_20260920/dwt_01/edit_session
build/leaflet_mask_batch_20260922/dwt_02/exports/accepted_20260929_092727_139059/accepted.json
build/new_captures_20260920/dwt_02/edit_session
```

Within `build/rgb_preprocess_lab_20260929/`:

- `samples/`: unchanged source crops and corresponding mask snapshots.
- `preset_diagnostics.csv`: 8 observations x 6 presets = 48 descriptive comparisons.
- `selections/`: explicit crop-processing saves with settings, review state, provenance, PNGs and numeric evidence.
- `full_red_ratio_368.png/.npy`, `full_green_ratio_368.png/.npy`, `full_blue_ratio_368.png/.npy`: unmasked full-frame outputs.
- `masked_ratios_368/{red,green,blue}_ratio_masked.png/.npy`: full-frame masked outputs.
- `masked_ratios_368/manifest.json`: source observation, hashes, mask scope, formula and output PNG hashes. Its nested observation contains the older crop metadata for provenance; these masked full-frame files have **no crop transform** (`crop: null`).
- `사용안내.md`: initial Korean usage guide; this handoff describes subsequent full-frame/masking additions.

Exclude `selections/20260929_135810_1c230b2b/` from human preference or research metrics: it is an unreviewed UI verification save. Also exclude all `test_*` directories and browser screenshots from scientific metrics.

The initial `verification.json` records the earlier 14-test checkpoint. Later channel/mask changes reached 19 tests as recorded in LOG; do not treat that initial JSON as a current comprehensive test report.

## Running and interfaces

From the project root:

```powershell
python -X utf8 -m tools.leaf_preprocess_lab serve --run build/rgb_preprocess_lab_20260929 --port 8832
```

Reuse an existing server on this port; inspect its command line before replacing this tool's process. Do not interrupt another application.

Current example:

```text
http://127.0.0.1:8832/?annotation=368&full=1&mode=green&mask=reviewed
```

- Full view controls: original / red / green / blue, plus the reviewed-selected-leaflet mask checkbox.
- Full image endpoint: `/source/sample_003?mode=green&mask=reviewed`; `mask=none` preserves the unmasked view.
- Full-image requests allow only manifest-listed sample IDs. Source-photo hashes are checked; applying a mask also checks its recorded hash and dimensions.
- Existing POST endpoints `/api/render` and `/api/save` remain **crop-processing** operations, not full-frame export APIs. They require the local session token and enforce origin/Host restrictions.
- The lab binds only to `127.0.0.1`. Do not expose it publicly.
- Full-frame PNG/NPY exports were generated programmatically with the implemented functions. There is not yet a dedicated full-frame export CLI/button.

Recompute pilot descriptive comparisons without learned inference:

```powershell
python -X utf8 -m tools.leaf_preprocess_lab compare --run build/rgb_preprocess_lab_20260929
```

## Verification and limitations

Latest focused run: **19 tests passed**. Tests cover photometric bounds, source preservation, crop coordinates/holes, invalid settings, safe saves/API checks, known RGB fractions and mask-alpha behavior.

```powershell
python -X utf8 -m pytest tools/tests/test_leaf_preprocess_lab.py -q
```

Additional checks:

- Full-frame R/G/B HTTP outputs matched the formula-generated arrays.
- All three masked HTTP PNGs matched saved 3024 x 3024 RGBA files exactly.
- Twenty source hashes were checked again while preparing this handoff; none changed.
- Browser controls showed channel selection and the selected-mask state. The final masked-image screenshot attempt timed out; numerical endpoint verification succeeded. Do not claim a final masked screenshot was captured successfully.

These checks establish implementation behavior, not organ-detection accuracy. No independent segmentation IoU, precision/recall, anatomical midrib accuracy or 3D improvement was measured. The existing mask is an input; comparing it with its own masked output is not validation.

## Claude integration guidance

1. Inspect these files and preserve the two different ratio bases explicitly. Reuse the numerical helpers instead of replacing the original image or duplicating formulas.
2. If connecting to the existing labeling UI, use the photo-level observation ID and original pixel coordinates. Mask acceptance, cross-view identity and physical landmark confirmation remain distinct.
3. Keep this as an optional comparison layer. Original RGB remains authoritative for source data and biological colour observations; do not recalibrate cameras from enhanced images.
4. Before exporting additional full-frame selections, include source/mask hashes, formula basis, channel, alpha/NaN convention, dimensions and observation identity. Write new derived outputs only.
5. For future midrib work, use the earlier proposal in `CLAUDE_RGB_MIDRIB_TO_3D_FLOW_2026-09-29.md` as a proposal, not implemented functionality. Human-confirmed physical landmarks across views are still required; a ratio map alone supplies no depth.
6. Evaluate any proposed improvement with independent references and a held-out plant split. Do not silently expand this handoff into training, autonomous organ detection, whole-plant masking or 3D recomputation.

Immediate requested delivery is this handoff and a review entry in the shared queue. The core pipeline has not been modified or automatically connected by this documentation task.
