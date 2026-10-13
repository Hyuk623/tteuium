# Petiole sensitivity adjustment

User requested sensitivity control for petiole segmentation. Added an offline editor at `build/sam_trial_20260919/petiole_tuner/index.html`, generated from actual SAM 2.1 Tiny predictions for IMG_7924 / left_petiole / guided. Open the HTML directly in a browser; no GPU, server or upload is needed for adjustment.

## Controls and meaning

- Sensitivity 0–100 maps to a raw-logit threshold `(50 - sensitivity) * 0.08`. Pixels are selected with strict `logit > threshold`. Higher sensitivity includes more uncertain pixels. This slider scale is an implementation convention, not biological or accuracy calibration.
- Default 50 uses threshold 0, exactly the original SAM decision. All three default masks match the previous organ trial byte-for-byte.
- Minimum disconnected-component area removes components smaller than the selected number of original-resolution pixels. Zero disables it. Connectivity is 8-neighbor; holes are not filled and thin branches are not eroded.
- Optional seed filtering keeps only components containing at least one original positive prompt. Disconnected visible portions require their own positive points. No missing prompt point is snapped onto the mask; missing include points and empty results are shown as warnings.
- Candidate selector exposes all three model masks. Displayed confidence belongs to the unadjusted candidate; it is never presented as accuracy for the adjusted mask.
- Export restores the full original 3024 x 3024 image coordinates, independent of preview zoom. PNG is binary RGB (0/255); the paired settings JSON carries threshold, filters, points, candidate, crop, image hash, logits hash and unreviewed status.

This is threshold/postprocessing of a cached prediction, not new SAM prompting, semantic petiole recognition, complete cleanup, frontend integration with the existing annotator, or internode measurement. Connected false-positive branches may persist. One include point is outside the default guided candidate, and the viewer correctly warns about it.

## Files and validation

- `tools/sam_leaf_trial.py`: added optional `--save-logits`; regular runs retain the original binary behavior.
- `tools/sam_mask_tuner.py`, `.html`, `.js`: validated payload builder, Korean review UI, threshold/filter/export logic.
- `tools/tests/test_sam_mask_tuner.py`, `sam_mask_tuner.test.cjs`: four Node regressions exposed through pytest. Combined targeted suite: six pytest items passed.
- `build/sam_trial_20260919/run04_petiole_logits/`: original crop-sized float32 score rasters, masks and provenance. `petiole_sensitivity_prompts.json` retains the existing prompts unchanged.
- Browser checked default, sensitivity 25 and 75, 50-pixel component filter, seed-only filter, and reset. Default area 10,058 pixels; sensitivity 25 selects 6,664; sensitivity 75 with min-area 50 and seed filter selects 17,562. These area changes are not measured accuracy improvements.
- Full-image export coordinates and JSON provenance were regression-tested. Actual download-button file saving was not exercised during browser QA.

Rebuild into a new directory:

```powershell
python -m tools.sam_mask_tuner --run build/sam_trial_20260919/run04_petiole_logits --case-id left_petiole --trial-id guided --out build/sam_trial_20260919/new_petiole_tuner
python -m pytest -q tools/tests/test_sam_leaf_trial.py tools/tests/test_sam_trial_bundle.py tools/tests/test_sam_mask_tuner.py
```

The previous Colab ZIP/notebook remains the original reproducible trial. This offline editor is a separate deliverable, not a claim that new Colab GPU execution occurred. Official threshold behavior: [SAM image predictor](https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py).

## User preference update

The user judged sensitivity **20** appropriate. Rebuilt `petiole_tuner/index.html` and `petiole_tuner_20/index.html` with starting value 20 and reset-to-20, plus a separate SAM-reference-50 button. Filters remain off. The raw SAM reference and original masks are unchanged. Sensitivity 20 corresponds to threshold +2.4 and selects 6,265 pixels in candidate 3 for this specific example. Browser startup at 20 was verified. Rebuild this preference with `--initial-sensitivity 20`; the generic builder defaults to the SAM reference when no explicit preference is supplied. This is a user-selected setting, not a measured optimum or universal petiole threshold.
