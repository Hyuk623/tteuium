# Addendum D: leaf library (2026-10-06) and the next C6 steps — B5 texture, view dependence, lighting

Date: 2026-10-06 13:45 KST. Author: Claude (chat), for the running Claude Code CLI session.
Applies on top of the Stage 1 prompt and Addenda A, B (B.1–B.3), C (C.1–C.3). Ownership unchanged: write only in `tomato3d/synth/`, `tests/test_synth_*.py`, `build/`. `data/raw/` is human-owned: read only.

## 0. Where we are (from `build/synthetic_dwarf_tomato_20261005_03/C6_REPORT.md`)
- B6 (leaf brightness) gave the largest gain so far: AP50 0.218 → **0.285** (B1 rule); 500–1500 px recall 0.43 → 0.54. Rendered leaf sRGB median is still **0.07 darker** than real (0.417 vs 0.486).
- B7 (diagnostic): facing leaflets (0–30°) are found at only 0.29, no better than oblique ones → **surface appearance is the main gap**. Edge-on leaflets (≥ 70°: recall 0.18; 49 % of leaflet-views ≥ 60°) are a secondary, geometric factor; 86 % of the thin-aspect tail is ≥ 60°.
- C6 0.285 (gate 0.59), C7 0.68 (gate 0.72): still failing. Next per B.3: B5.

## 1. New input: pooled leaf library (human-owned, read only)
`data/raw/leaf_library/leaf_lib_20261006/` — 46 original HEIC photos (`leaf_01.heic` … `leaf_46.heic`, byte-identical copies, sha256 in the CSV) and `leaf_library_capture.csv`:
`session_id,photo_file,source_filename,sha256,captured_at,level,content,attachment,pressed,condition,ruler_in_frame,quality_flags,rotation_series,rotation_step,uses,notes`

- **No `plant_id`, by the user's design.** This is a pooled library for leaf appearance and shape. It must never be required to map to a plant, and per-plant statistics must not be computed from it.
- All detached, `pressed=no`, `condition=mixed` at photo level. Classify each segmented leaflet yourself as `healthy / senescent / damaged` from colour (brown/yellow/necrotic fraction), store the fraction, and keep senescent ones out of healthy-leaf priors (tagged, not discarded).
- `quality_flags`: `hand_occlusion`, `tool_occlusion`, `on_ruler_overlap`, `no_ruler`, `no_leaf`. `uses` lists what each photo is good for: `texture;vein;brightness` (45 photos), `shape_contour;area` (29: ruler present, no occlusion), `compound_structure` (7), `view_dependence` (8). Respect `uses`; e.g. never take a contour from an occluded photo.
- **Two rotation series — the point of the last photos, stated by the user: the same leaf looks different depending on the angle it is seen and lit from.**
  - `rot_single_leaflet` (photos 39–42): one centre leaflet re-oriented between shots; no ruler (appearance only).
  - `rot_grid` (photos 43–46): one grid of ~28 leaflets on a sheet, the sheet rotated 4 ways under a fixed camera and fixed light. Every leaflet appears 4 times with a different light direction relative to its own veins and relief.
  - Match leaflets across the 4 grid shots by a rigid transform of the sheet (ruler / grid layout), not by appearance. Write `build/leaf_library_20261006_01/rotation_pairs.json` (leaflet id → 4 crops).

Add the library to `build/leaf_area_20261005_01`'s contour pool as `source='flattened_real_unpressed'` (C.1/C.2 terminology): near-flat, scaled where a ruler is present. Report counts by source and by condition. Use these leaflets toward the C.2 projected→flattened correction only where a leaflet is plausibly flat; record `pressed=no` with every value.

## 2. Next steps (one factor each, declared in `contract_amendments.json` before rendering; B1 rule + contract GT both reported; same 5 scenes × 12 views; B4a framing and B6 brightness kept)

**D0 — measure view dependence on real leaves (no render).** From `rot_grid`, per leaflet: mean brightness, local contrast (vein/relief visibility, e.g. high-pass energy inside the mask), and their spread across the 4 rotations. Report the distribution of the **rotation-induced change** (max−min over the 4 shots, relative). This is the target the renderer must reproduce: a uniform-albedo, smooth leaf under soft light changes ~0 when rotated; a real rugose leaf under directional light changes a lot. Store as `addendum_d/D0_view_dependence_real.json`.

**B5a — albedo texture (vein pattern, colour variation).** Build leaflet albedo textures from library crops (`uses` contains `texture`, healthy only by default) plus rig-photo crops (`source='rig_photo_crop'`, as in B.3). Remove shading before using a crop as albedo (divide by a low-pass illumination estimate); keep vein colour contrast. Re-calibrate so the **rendered leaf median matches real 0.486** (the B6 residual of −0.07 is closed here, not in a separate step). Report C6/C7 and the rendered leaf sRGB p10/50/90 beside real.

**B5b — relief (normal/bump) with directional light, as one coupled step.** A normal map has almost no visible effect under the current soft light, and hard light on a smooth leaf adds only flat shading; the two are a single factor for appearance. Derive normal/height maps from the library crops (shape-from-shading on de-lit crops is sufficient; state the method), add one directional key light whose elevation/softness is matched to the rig photos' measured shadow sharpness (`real_camera_stats_1280.json` and the rig photos; state the measurement), keep the fill. **Validate against D0 before scoring C6:** render a flat test leaflet with the texture, rotate it 4 ways under the same light as `rot_grid`, and compare the rotation-induced brightness/contrast change with D0. If the synthetic change is far below D0's, fix the relief/light first. Then report C6/C7.

**B3 — camera artifacts and background (only if B5a/B5b leave a gap).** Measured noise/sharpness ranges are already in `real_camera_stats_1280.json`. Add the rig background (wire grid, surroundings) as a backdrop texture taken from real rig photos. Same reporting.

**Geometry (later, only if a gap remains after B5/B3).** B7 shows edge-on leaflets are a secondary loss. Do not change leaf-angle distributions yet; when you do, it is a generator change and gets a new run folder and contract.

## 3. Rules (unchanged, restated)
- Detector frozen (sha256 `609fd7ae…`); no training or fine-tuning on synthetic; no threshold changes after seeing results.
- First step reaching C6 ≥ 0.59 and C7 ≥ 0.72 stops and reports before the 100-scene run. Report after every step that moves C6 by ≥ 0.03.
- Heavy rendering on Kaggle; local peak RAM < 6 GB (log it).

## 4. Tests (`tests/test_synth_*.py`)
- Library CSV loader rejects a photo missing from disk or a sha256 mismatch, and never requires `plant_id`.
- A leaflet from a photo whose `uses` lacks `shape_contour` is never emitted as a contour.
- `rot_grid` matching recovers a known 90° sheet rotation on a synthetic test sheet.
- De-lighting: a synthetic albedo under a known illumination gradient is recovered within tolerance.

## 5. Report
Append to `C6_REPORT.md` and `c6_steps.csv` (`D0`, `B5a`, `B5b`, `B3` rows). Korean 5-line summary in your reply: library counts (by use/condition), D0 result, C6/C7 after each step, next decision for the user.

---

## Revision D.1 (2026-10-06, after B5a and the first B5b relief validation)

### D.1.0 Why this revision

`addendum_d/B5b_relief_validation.json` (9 combinations: `key_light_size_m` 0.03/0.1/0.3 x `bump_strength` 0/0.5/1.0)
reports rotation-induced change of **brightness 0.0025-0.0051** and **contrast 0.0055-0.0366**, against the D0 target
of **0.15** and **0.19**. That is 30-50x short, and on those numbers B5b fails its own pre-check.

**The comparison is not valid as run.** No result row carries `roll_deg` or `roughness`, and `_leaf_mesh`'s signature
defaults to `roll_deg=0.0`, so the sweep rendered a **flat** test leaflet. The generator uses
`leaflet_roll_deg` 10-60 and `leaflet_bend_deg` 0-45. On a flat plane only the bump map can produce any
view-dependent change, so a near-zero result was structurally guaranteed and says nothing about the generator's
actual leaflets. `relief_check.run` now accepts `rolls=` and `roughnesses=`; the sweep must be re-run before any
conclusion about relief is recorded.

### D.1.1 User decision 1 — validate at the generator's roll, not at the paper condition

D0 was measured on **detached leaflets lying on a sheet** (`pressed=no`), which are flatter than leaflets on a plant.
The user's decision: **treat D0's numbers as a magnitude target only** — "a real leaf changes about this much when the
light direction relative to its surface changes, a smooth uniform leaf changes ~0" — and validate at the roll the
generator actually uses, not at a roll that reproduces the paper condition.

Consequence that **must be written into `C6_REPORT.md` next to every D0-vs-B5b comparison**: the two sides are not
condition-matched (real = detached leaflet on paper; synthetic = plant-like roll 10-60 deg). The target is a magnitude,
not a calibration. Do not report it as a calibrated match, and do not later reuse these numbers as if conditions agreed.

### D.1.2 Re-run the validation sweep (`relief_check`, Kaggle GPU)

Stage 1 — 27 combinations, `roughness` fixed at 0.5:
- `rolls = (10, 35, 60)` — the generator's `leaflet_roll_deg` min / mid / max.
- `bump_strengths = (0.0, 0.5, 1.0)`
- `light_sizes = (0.03, 0.1, 0.3)`
- same 12 textures, 4 rotations, 256 px, 32 samples, `bump_distance_m` 0.0005 as before.

Stage 2 — take the best stage-1 combination and sweep `roughnesses = (0.35, 0.5, 0.7)` on it only (3 more).

**`bump_strength=0.0` at each roll is the control and must be reported on its own line.** It separates the two
mechanisms: how much of D0's magnitude macro curvature alone already produces, and how much the bump map adds on top.
Write both into the report. If curvature alone already reaches the target, B5b's relief maps are not the binding factor
and that is the finding.

Keep every result row carrying `roll_deg`, `roughness`, `bump_strength`, `key_light_size_m`, `bump_distance_m`, `n`.
Overwrite `addendum_d/B5b_relief_validation.json` only after moving the current file to
`addendum_d/B5b_relief_validation_flat_superseded.json` (it is evidence of the flat-leaf run; keep it, and say in
the report that it was run at roll 0).

### D.1.3 Pass / fail line, decided in advance

Using the 4-shot D0 medians (brightness 0.15, contrast 0.19), the line is **half the target**:

- **pass** — `brightness_change_p50 >= 0.075` and `contrast_change_p50 >= 0.095` for at least one combination.
  Pick that combination (prefer the smallest `bump_strength` that passes), write the chosen
  `key_light_size_m` / `bump_strength` / `roughness` into the B5b generator config, render the 5 pilot scenes, score C6/C7.
- **fail** — no combination reaches both. Then **stop raising `bump_strength`** and go to B5c (mesh-level relief) below.
  This is pre-approved by the user: do not pause to ask, record the decision and continue.

Also report the shots 0-2 variant of D0 (brightness 0.14, contrast 0.12) beside the 4-shot one, since the shot-3
orientation ambiguity is already noted in `C6_REPORT.md`. The pass/fail line uses the 4-shot numbers.

### D.1.4 B5c — mesh-level relief (only on a B5b fail; pre-approved)

A bump map perturbs shading normals without changing the silhouette or casting self-shadows. If that cannot reach the
target, the relief has to exist in the surface itself.

**This is a generator geometry change: new run folder `build/synthetic_dwarf_tomato_20261006_04/`, new
`contract_amendments.json` declaration before rendering, B4a framing + B6 brightness + B5a albedo all kept.**

1. **Vein ridges as displacement.** Raise the leaflet surface grid resolution, and displace it along its normal:
   a midrib ridge plus lateral veins branching from it, amplitude and spacing taken from the library height maps
   (`texture_bank_v2`) in mm. State the amplitude range and its source.
2. **Inter-vein rugosity (bullate bulges).** Tomato leaf blades bulge between veins. Add it as low-frequency
   displacement of the same surface, amplitude from the same height maps.
3. **Specular / sheen.** Real tomato leaves are waxy and show highlights; the current material is diffuse-dominant.
   Add a specular term and sweep it as part of the validation, not as a separate step.
4. **Re-validate against D0 exactly as in D.1.2 before scoring C6**, same pass line.

**Geometry changes the masks.** Displacement changes each leaflet's silhouette and visible area, so:
- regenerate visible and amodal masks (do not reuse B5a/B5b masks);
- re-check and report **C1-C4** as well as C6/C7. C2 (top envelope) and C4 (visible leaflet area) can move out of range,
  and a C6 gain bought by breaking a shape gate is not a pass. If a shape gate breaks, report and stop.

### D.1.5 B8 — contour serration diagnostic (no render, run alongside)

B5a lifted large leaflets to 0.70-0.79 but `<150 px` leaflets (23 % of GT) stay at **0.08 against real 0.69 at the same
512 px**. At that size surface texture is sub-pixel, so neither B5b nor B5c can be expected to fix that bucket. What
survives at small size is the silhouette, and real tomato leaflets are deeply serrated while synthetic ones are smooth.

Measure it, no rendering:
- **Metric:** scale-invariant contour roughness — normalised perimeter (`perimeter^2 / (4*pi*area)`) and the deviation
  of each contour from its own smoothed version (resample to a fixed point count, low-pass, report RMS radial deviation
  relative to the equivalent radius). Report the distribution, not a single number.
- **Three populations, same metric, same resampling:**
  1. real SAM-accepted masks (the 1163 pool),
  2. real library photo contours (`library_flattened_real_unpressed_contours.json`, 61) — these come from photographs
     of leaflets on paper, independent of SAM,
  3. synthetic leaflet silhouettes rasterised from the B5a scenes.
- **The sub-check that decides what to do:** compare (1) against (2). If the SAM-derived contours are themselves much
  smoother than the photo contours, then the pool the generator draws from has already lost the serration, and the fix
  is the contour source, not the generator. Say which of the two it is.

Output `addendum_d/B8_contour_serration.json` and one figure overlaying a few contours from each population at matched
scale. Report only; do not change the contour pipeline on this result without asking.

### D.1.6 Confirmed from the user's status, no action

- Background stays the **grey wall**; B3's backdrop is not taken up now. Recorded.
- Library **ruler scale stays `pending`** (auto tick detection matched only 2 of 4 hand-checked photos; unused).
  Library contours contribute **shape only**. B5/B5c do not need scale. Scale is needed again only for C4 leaf area —
  park it until then and keep `pressed=no` on every value.
- The 5 new texture tests (alignment, UV, height map, texture shipped with the job) are accepted.
- B5b masks verified identical to B5a: keep that check as an assertion, since B5c will deliberately break it.

### D.1.7 Report

Append `B5b` (with its chosen or failed config), `B5c` if reached, and `B8` rows to `c6_steps.csv`, and a D.1 section to
`C6_REPORT.md` including: the flat-leaf invalidation, the `bump_strength=0` control at each roll, the pass/fail
line and which side it fell on, and the B8 real-vs-real sub-check result. Korean 5-line summary in your reply.

---

## Revision D.2 (2026-10-06, after the B5c pre-check)

### D.2.0 The D0 brightness target is not valid; the pass line in D.1.3 was wrong

B5c reached contrast 0.13-0.23 against a real 0.187 while brightness stalled at 0.048-0.074 against a real 0.147.
That split is not a property of the renderer. Three findings from `addendum_d/D0_view_dependence_real.json`:

1. **The condition labels are wrong.** 22 of the 23 matched leaflets are labelled `damaged` with
   `necrotic_fraction` median ~0.98, but the crops (`build/d0_check_20261006_01/d0_rot_crops.png`, from
   `rotation_crops/`) show ordinary green leaflets. `params.necrotic_value_max = 70` is applied to the raw
   value channel while these photos are dark (leaflet 42-52, paper 190-217), so almost everything trips it.
   The threshold is applied **before** paper normalisation. See D.2.4.
2. **The camera was not fixed between the 4 shots.** Median area change of the *same* matched leaflet across the
   4 shots is **0.35**. A rigid rotation of the sheet cannot change a leaflet's imaged area by a third. The crops
   confirm it: shot 2 is visibly larger, and shot 3 of g00/g07 is visibly darker. Camera distance and exposure
   changed shot to shot. `paper` per shot (190 / 197 / 217 on g00) shows the same.
3. **That explains the split.** A change in camera distance and exposure moves the **global mean brightness** of
   a crop directly, while **local contrast inside the leaflet** is largely invariant to it. So D0's brightness
   figure measures how much the camera moved at least as much as how the leaf responds to light direction; its
   contrast figure is the sound one.

**Consequence: brightness is removed from the pass line.** The D.1.3 rule was wrong in a second way as well:
contrast was written as a floor (`>=`), but it is a quantity to **match** - overshooting it is not better. Under
`>=` with "prefer the smallest amplitude that passes", the rule would have selected the worst-matching combination.
Both errors are this addendum's, not the implementation's; nothing already run needs redoing.

### D.2.1 New pass rule for any relief/light validation (replaces D.1.3)

- **Criterion: match the real contrast distribution.** Compare the synthetic `(p10, p50, p90)` of
  `contrast_change` with D0's real `(0.106, 0.187, 0.299)` and take the mean absolute difference over the three
  percentiles ("triple MAD"). **Pass if `|p50 - 0.187| <= 0.047` (±25 %)**; among passing combinations pick the
  **smallest triple MAD**, not the smallest amplitude.
- **Brightness is report-only**, with the reason recorded (D.2.0). Do not fail a step on it and do not tune to it.
- The condition note stands: D0 = detached leaflets on paper, synthetic = plant-like roll; magnitude target, not
  a calibration.
- **Open risk to record:** contrast and brightness point in opposite directions here - the best contrast match is
  also the lowest relief amplitude, which produces the least brightness response. If the brightness target is ever
  re-measured on a fixed-camera capture, this choice must be revisited. Write that sentence into `C6_REPORT.md`.

### D.2.2 Selected B5c combination (computed from the existing sweep, no new renders)

Applying D.2.1 to `build/synthetic_dwarf_tomato_20261006_04/addendum/B5c_relief_validation.json` (roll 35, light 0.1 m):

| relief_amp_rel | roughness | specular | contrast p10 / p50 / p90 | triple MAD | brightness p50 |
|---|---|---|---|---|---|
| real (D0) | - | - | 0.106 / 0.187 / 0.299 | - | 0.147 |
| **0.015** | **0.25** | **0.5** | **0.114 / 0.182 / 0.294** | **0.0063** | 0.031 |
| 0.03 | 0.25 | 1.0 | 0.118 / 0.196 / 0.312 | 0.0111 | 0.040 |
| 0.03 | 0.25 | 0.5 | 0.120 / 0.209 / 0.309 | 0.0152 | 0.037 |

**Take `relief_amp_rel = 0.015`, `roughness = 0.25`, `specular = 0.5`, `leaf_mesh_grid_n = 48`** (the generator
value from `B5c_declaration.json`; 96 was the validation-only mesh). Record that the selection used the existing
sweep and that no combination was re-rendered to make it.

### D.2.3 Proceed with B5c in run `_04` (no further approval needed)

1. Write `leaf_relief_amplitude_rel`, `leaf_mesh_grid_n`, `leaf_specular`, `leaf_roughness` into
   `generator_config.json` (`--allow-config-change`, config change recorded as usual).
2. **Regenerate visible and amodal masks** - displacement changes the silhouettes; do not reuse B5a/B5b masks.
   The B5a==B5b mask assertion is expected to fail here and that is correct; scope it so it does not block.
3. Render the 5 pilot scenes on Kaggle, score with both the contract GT and the B1 rule.
4. **Report C1-C4 as well as C6/C7.** A C6 gain bought by pushing a shape gate out of range is not a pass: if any
   shape gate breaks, report and stop.
5. Append a `B5c` row to `c6_steps.csv` (replacing the current FAIL row, keeping the pre-check history in the
   report text) and a D.2 section to `C6_REPORT.md`.

### D.2.4 Fix the condition classifier (before it is trusted anywhere else)

The necrotic/damaged test thresholds the raw value channel, so it misclassifies any underexposed photo.

- **Normalise by the local paper brightness first** (the `paper_ring_px` ring is already measured per leaflet),
  then apply the necrotic/senescent thresholds to the normalised value. State the new thresholds and how they
  were chosen.
- **Re-run the classification** over the leaf library (236 components) and the 23 D0 leaflets. Report the
  before/after counts for both, and how many D0 leaflets remain `damaged`.
- **Check the blast radius on B5a:** the texture bank selected "healthy library leaflets"; report whether the
  corrected labels would change which of the 55 library crops qualify, and by how many.
- **Do not rebuild the texture bank in this run.** If the selection changes materially, that is a separate factor
  and gets its own step and declaration - B5c must stay a single-factor step.
- Add a test: a synthetic green leaflet rendered at two exposure levels gets the same condition label.

### D.2.5 Not now

The fixed-camera `rot_grid` re-shoot (tripod, manual exposure lock) is **deferred**, by the user's decision. Until
it exists, no brightness-based criterion may be introduced, and `C6_REPORT.md` must say the brightness target is
unvalidated rather than simply unmet.

---

## Revision D.3 (2026-10-06): B10 - is the remaining C6 gap appearance, or the GT size distribution?

Runs **in parallel with B5c**; entirely local, **no rendering, no Kaggle, no detector change**. It reuses the B5a
images and detections that already exist.

### D.3.0 Why

Five causes are ruled out (B0 resolution, B4a framing, aspect/solidity arrangement, B7 view angle, B8 serration), and
appearance work has moved C6 0.211 -> 0.285 -> 0.328. The remaining gap is concentrated by size: recall
`<150 px` 0.08, `150-500` 0.40, `500-1500` 0.70, `>1500` 0.79, against real 0.69 / 0.84 / 0.93 / 0.96.

One hypothesis is already eliminated. Measured on 24 B5a views (`rgb.png` + `visible_mask.png`): per-view spread of
per-leaflet mean luminance **32 / 255** (p10-p90 26-37), and leaflet-to-leaflet boundary `|dLum|` **median 12.3**
(p75 25.7, p90 44.3) with only **14.6 %** of boundary pixels below 3. Adjacent synthetic leaflets are **not** merging
into one blob; record this in `C6_REPORT.md` so it is not re-tested.

What has never been checked is whether the two sides are scored on the **same population**:

- real GT: `visible_leaflet_area_px` min 26.7, **p10 146.9**, median 406.5, p90 1186.6 -> about **10 %** below 150 px;
- synthetic GT: **23 %** below 150 px, and `C4_median_ratio` is **0.61** - synthetic leaflets are still 39 % smaller
  than real at the median.

So the synthetic set carries roughly twice the real share of leaflets in the single worst-performing bucket. Perfect
appearance would still be scored against that. The two sides also use different GT rules: real GT is
**human-accepted SAM masks**, synthetic GT is **every instance over `min_visible_px`** - a reviewer would plausibly
never have accepted a few-pixel sliver between leaves, while the rasteriser emits it.

### D.3.1 B10 - reweighting diagnostic

0. **Emit `B5a/eval_B5a_B1rule_pergt.json`** in the same schema as `B4a/eval_B4a_B1rule_pergt.json`. Re-scoring the
   stored B5a images with the frozen detector is allowed; re-rendering is not.
1. **Measure both size distributions.** Compute the deciles of visible leaflet area (px at 512) for real (the 1163
   accepted masks, as resized in B0) and for synthetic B5a GT. Do not take the 10 % / 23 % figures above on trust -
   recompute and report both, plus the fraction below 150 px on each side. One figure overlaying the two histograms.
2. **Recompute AP50 on the unchanged B5a detections** under three variants, B1 rule throughout:
   - **W1 importance weighting** - bin GT by visible area using the real deciles as edges, weight synthetic GT so the
     per-bin mass matches real, recompute AP50.
   - **W2 resampling** - draw a synthetic GT subset whose size histogram matches real, recompute AP50 plainly;
     repeat 20 times with different seeds and report **median and p10-p90**. This is the variant the decision uses,
     because it carries an uncertainty band.
   - **W3 truncation control** - drop all GT below 150 px on both sides and recompute. A crude upper bound.
   Report all three beside the unweighted 0.328.
3. **These numbers are diagnostics and are never a C6 pass.** C6 remains the unweighted AP50 against 0.59. Write that
   sentence in the report next to every W row, and mark the `c6_steps.csv` rows `diagnostic`.

### D.3.2 Decision rule, declared before running

Using the **W2 median**:

- **>= 0.50** - the size distribution is the dominant remaining factor. Next step is **B4b revived** (generator
  leaflet scale, raising `C4_median_ratio` 0.61 -> ~1.0), not more appearance work. B4b was dropped in rev. B.3 on the
  grounds that "B4a already doubled leaflet size with almost no AP gain", but B4a changed **framing** - the whole
  scene including the background was scaled - not leaflet size relative to the plant. The two are different factors
  and the earlier reasoning conflated them; say so in the report.
- **<= 0.40** - the distribution is not the issue and small-scale appearance is confirmed. Stop adjusting
  distributions and go to B11.
- **between** - both contribute: report and ask the user before choosing.

### D.3.3 GT-rule asymmetry (same run)

The real GT is what a human accepted. If the mask review exports kept **rejected** candidates as well as accepted
ones, compute the **acceptance rate as a function of visible area** and report the curve. Where acceptance collapses
is the real GT's effective minimum size, and the synthetic `min_visible_px` should be set from that rather than from
the raw real p1. If rejections were not kept, say so plainly and skip this item - do not estimate it.

### D.3.4 False positives (same run)

AP50 is not only recall: B5a false positives rose **77 -> 113** while recall improved. Classify the B5a FPs by what
they sit on, using the existing `visible_mask.png` and `organ_mask.png`: background / board / pot or soil / stem /
on or between leaflets (split or merged detections). Report the counts. A large leaflet-adjacent share is a
**different** failure from "misses small leaflets" and would change the next step; say which it is.

### D.3.5 B11 - small-scale appearance diagnostic (only if D.3.2 selects it; no render)

For GT leaflets of **50-150 px**, measure real against synthetic at the same pixel scale:
local contrast against a 3 px ring just outside the mask; the hue and value difference between leaflet and that ring;
and the gradient magnitude along the mask boundary. At a 7 px radius neither texture nor veins survive, so these are
the only cues left - this says whether a small synthetic leaflet offers the detector less than a real one, and in
which channel. Real masks come from the 1163 pool resized to 512 px, the same path B0 used.

### D.3.6 Output

`addendum_d/B10_gt_size_reweight.json` (both distributions, W1/W2/W3, FP classification, acceptance curve or the
reason it was skipped), the distribution figure, `B10` rows in `c6_steps.csv` marked `diagnostic`, and a D.3 section
in `C6_REPORT.md`. **No contract change and no generator change in this step** - B10 only measures. Korean 5-line
summary in your reply, ending with which branch of D.3.2 the result selects.
