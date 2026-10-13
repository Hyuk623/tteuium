# Claude handoff: F.2 / F.7 separate analysis and original-photo evidence

Date: 2026-10-07. Paths below are relative to `Tomato 3D phenotyping analysis/`.

## Request to Claude

Review the completed diagnostic analysis against Addendum F, especially F.7 and F.12. Determine which anatomical claims the original photographs actually support, review the proposed class separation, and specify the remaining evidence needed for generator parameters. Preserve the distinction between a software-generated shape candidate and a reviewed anatomical label. Return a separate English handoff with a short Korean user summary.

The user authorized F.2/F.7 in separate files and explicitly named `data/raw/leaf_library/leaf_lib_20261006/` as the photo reference. This handoff does **not** authorize F.3, synthetic training, new rendering, detector inference, rebuilding the texture bank, changing the GT acceptance rule, or changing the scientific contract. F.1 did not confirm its fragment-vs-organ hypothesis. B5c finished and performed worse than B5a; it was not carried forward.

Read `CONVENTIONS.md`, the latest `handoff/LOG.md` entries and `handoff/TODO.md` first. Coordinate edits: this is a shared OneDrive checkout. Keep both existing analysis runs intact; save your review separately. Do not rerun the generators simply to read this handoff.

## Read these first

1. [Addendum F through F.12](CLAUDE_CODE_CLI_ADDENDUM_F_COMPOUND_STRUCTURE_2026-10-06.md).
2. [First analysis report](../build/compound_structure_f2_f7_20261006_01/REPORT_KO.html).
3. [Texture source review gallery](../build/compound_structure_f2_f7_20261006_02/REVIEW_KO.html): 115 cards; 32 priority items; source RGB, contour overlay, current texture and full-photo context links.
4. [All 51 original-photo previews](../build/compound_structure_f2_f7_20261006_02/RAW_PHOTOS_KO.html). These are derived browsing copies. The original HEIC/PNG files remain in the user-named raw folder.
5. [Latest machine-readable summary](../build/compound_structure_f2_f7_20261006_02/summary.json).

## Verified input identity and source context

- Raw folder: **46 HEIC + 5 PNG**, all decoded without modifying originals. The original capture CSV still has 46 rows. The five new photos are represented only in `build/compound_structure_f2_f7_20261006_01/leaf_library_capture_supplement.csv`; this supplement was not applied to the original CSV.
- Reproduced **236/236** existing eligible library component crops pixel-for-pixel from the original HEIC files using the existing classical segmentation implementation. This includes **55/55** library-derived B5a texture sources.
- The other **60** bank entries are joined to accepted masks and original rig RGB photos, with mask and photo hashes checked against the accepted export. No label or mask was changed.
- Capture metadata explicitly identifies `leaf_03` and `leaf_04` as **“compound fragment, senescent”**. Do not treat them as complete compounds for total-count or full-axis measurements.
- `leaf_17` is **“rachis/stem piece only”**, level `stem`, flag `no_leaf`. It is displayed in the photo gallery but excluded from leaf-component segmentation.
- Possible repeated subjects `leaf_03/04` and `leaf_24/25` were flagged from visual similarity only. This is not confirmed specimen identity. There are no established independent-compound IDs.

## F.7 results: candidate classification, not biological accuracy

All four artifacts were enumerated completely, without replacing their source labels:

| Artifact | n | Main candidate | Interjected candidate | Unknown |
|---|---:|---:|---:|---:|
| Library components | 236 | 140 | 8 | 88 |
| Flattened contour pool | 61 | 44 | 1 | 16 |
| SAM accepted-mask contour pool | 1163 | 860 | 11 | 292 |
| B5a texture bank v2 | 115 | 83 | 2 | 30 |

The two interjected-shaped texture candidates are:

- `tex_038.png` <- `leaf_43_c07` (library). Its full HEIC photo with the registered component marked is linked from the gallery.
- `tex_079.png` <- `dwt_02_a71` (rig). The original photo shows a small rounded visible blade; the accepted contour is nearly circular. This is not enough by itself to establish its anatomical class.

Do **not** report “exactly two true interjected leaflets contaminated B5a.” The confirmed anatomical count is unavailable. Nor does classification establish that a given texture was applied to a main-leaflet position in a specific rendered scene; that requires a separate source-to-generated-position trace. The bank was not rebuilt.

### Fitting and representation

- Primary metric: polygon perimeter squared divided by `4*pi*polygon_area`, after 64 equal-arclength contour samples. Solidity and min-area-rectangle aspect are also retained; size does not decide the class.
- Fit: **7 blade ROIs / 3 photos**, with 4 main blades from `leaf_47/50` and 3 interjected blades from `leaf_51`.
- Four other ROIs are diagnostic only: damaged `leaf_47` interjected blade, damaged top main blade in `leaf_50`, and two `leaf_49` regions crossed by ruler lines. `leaf_48` supplies compound context, not an isolated training contour.
- Fitted threshold: **1.29899**. Conservative unknown band: threshold +/- **0.12990**. The band is a heuristic safeguard (maximum of 10% of the threshold and leave-photo-out threshold shift), **not a confidence interval or an adopted biological rule**.
- Training classes separate, but there is no independent interjected validation: excluding `leaf_51` removes the entire interjected training class. Independent specimen counts are unknown. Do not describe the fit as 100% biological accuracy.
- Numbers are representation-specific. Do not directly compare this 64-point metric to the earlier F.7 numerical ranges measured with different contour processing. Ruler lines, damage, occlusion, curl and sampling density alter the metric.
- Unknown handling includes compound-level components, non-leaf/unclassified components, damaged boundaries, multiple components, threshold proximity and source/resampled-contour disagreement. No apex or trichome model was created.

### Resolution stability and sensitivity

Using native source-mask contours, refitting on the same reference blades at each resolution:

| Contour points | Main | Interjected | Unknown |
|---|---:|---:|---:|
| 64 | 89 | 2 | 24 |
| 128 | 91 | 3 | 21 |
| 256 | 96 | 3 | 16 |

The conservative combined rule requires agreement with the prior classification at **all** three resolutions and never promotes prior `unknown` automatically. It retains **83/2/30**. This is representation stability, not anatomical verification.

In the first run, unknown-band factors 0 / 0.5 / 1 / 1.5 produce **13 / 7 / 2 / 1** interjected texture candidates. The inferred mixture is sensitive to the uncertainty policy. Review the full distributions and individual sources, not only the headline count.

## F.2 results and unresolved anatomy

- Reviewed the seven specified compound photos plus `leaf_48`: **8 photos**, not 8 proven independent complete compounds.
- Labelled the visible rachis segments and **8 candidate blade chords on 5 photos**. Candidate projected blade-length / provisional adjacent-main-length ratios span **0.234–0.601**, with +/-5 px endpoint sensitivity recorded.
- These are provisional **2D endpoint-chord ratios**. Candidate class, adjacency, folding and actual full blade length are not established. They are marked `measured_small_n`, with sample counts and **`generator_parameter_eligible=False`**. Do not use this descriptive range as an F.3 prior.
- Anatomical main-pair counts, complete interjected counts, terminal presence and attachment fractions along the full rachis remain unavailable. The visible segment was not silently normalized as a complete rachis. `NaN` means unavailable, never zero or absence.
- User-provided `leaf_48` counts are retained separately from measurement. Per F.12, **5–7 refers to main leaflets only**; interjected leaflets have their own count. Never combine these into an ambiguously labelled “leaflets per compound” count.
- Intact blade-outline comparisons within the compound photos remain unavailable where individual boundaries overlap. Candidate markings are Codex proposals, not user-reviewed annotations.

## Concrete next review tasks

1. Inspect the **32 priority texture entries** (2 interjected candidates + 30 unknown) against the source context. Review main candidates too before making a population-wide accuracy claim. Record evidence, reviewer and unresolved cases; do not force a class.
2. Decide whether the metric can distinguish anatomical class under damage/occlusion/curl, or whether it is only a rough candidate selector. Propose a held-out, specimen-independent reference set, including intact interjected blades from multiple compounds. Preserve fit-versus-validation separation.
3. Review each provisional F.2 annotation. Confirm or reject candidate identity and adjacent-main association; identify real rachis origin, terminal attachment and attachment nodes only where visible. Exclude incomplete fragments from whole-compound totals.
4. If the photos cannot resolve these quantities, specify the minimum additional observations: unique compound IDs, a spread attached compound with visible base and terminal insertion, labelled attachment points on both sides, and intact individual reference blades. Ratios do not require a ruler; printed ruler lines must not cross the blade outline.
5. Correct the implementation description in your review: `tomato3d/synth/compound_leaf.py` already supports `intercalary_count`; the examined run `_04` uses 0–1, shared contours, and a size ratio to terminal length. Thus “no small-leaf code exists” is too broad. **The measured paired main/interjected alternation and separate class-specific contour model required by F.3 are not implemented.** This observation does not authorize generator edits.
6. Return an explicit conclusion: what is measured, user-given, provisional, unavailable, and sufficient/insufficient for a future F.3 decision. The F.1 hypothesis remains unconfirmed; this diagnostic does not pass C6 or independently authorize F.3.

The gallery's human fields are blank; **zero human reviews** have been entered. Browser local storage is only a convenience; the exported review CSV is the portable artifact. Never reinterpret machine candidates or an empty template as human-approved labels.

## Artifact and implementation index

First run: `build/compound_structure_f2_f7_20261006_01/`

- `artifact_classification.csv`, `near_threshold.csv`, `classification_sensitivity.csv`
- `class_reference_metrics.csv`, `classifier_policy.json`, `reference_segmentation.png`
- `compound_annotations.csv`, `candidate_annotations.csv`, `compound_measurements.csv`, `interjected_leaflets.csv`, `labelled_rachises.png`
- `F2_summary.json`, `F7_summary.json`, `shape_distributions.png`
- `leaf_library_capture_supplement.csv`, `input_provenance.json`, `F2_input_provenance.json`, `delivery_manifest.json`

Source review: `build/compound_structure_f2_f7_20261006_02/`

- `texture_evidence.csv`, `native_contour_metrics.csv`, `resolution_fit_policy.json`
- `human_review_blank.csv`, `cards/`, `raw_context/`, `raw_photos/`
- `raw_photo_inventory.csv`, `component_raw_registration.csv`, `raw_library_summary.json`
- `summary.json`, `input_provenance.json`, `raw_library_provenance.json`, `delivery_manifest.json`

Tools: `tools/f2_f7_analysis.py`, `tools/f2_compound_measurements.py`, `tools/f2_f7_report.py`, `tools/f2_f7_evidence.py`, `tools/f2_f7_raw_library.py`. All have `--help`. HEIC decoding uses the existing `C:/Users/sho36/miniforge3/envs/tomato_synth/python.exe`; no new dependency installation is needed. Other analysis ran with the existing Python 3.13 environment.

Validation already recorded: 10 analytical unit tests, CLI executions/help, JavaScript syntax, 115 cards / 55 registered HEIC context links / 51 original photos, 236 pixel-identical crops, blank human fields and 235 second-run output hashes. The evidence audit protects 676 input paths. Browser interaction was not tested; do not claim it was. No source photo, accepted mask, capture CSV, generator, configuration, original contour pool, bank, shared C6 report or shared c6_steps was changed. Separate step rows are diagnostic only.

For reproducibility, validate hashes before trusting historical counts if another session has advanced source artifacts. Preserve provenance; do not overwrite the evidence to make it match a newer run.
