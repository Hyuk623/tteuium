# Dwarf tomato 3D completion and leaf area research prompt V2

I want to build a model that takes a **top-view image** (later possibly top-view + depth) of a dwarf tomato plant and produces a **plausible 3D plant**, including parts that are occluded or curved and therefore not directly visible. I plan to train it on my own multi-view dwarf tomato data. Please find the relevant literature, open-source code and datasets, and propose a concrete training and development method. This is a research/design discussion: do not write production code.

Revision date: 2026-10-05. This complete prompt supersedes the earlier top-view diffusion research prompt for this review. It incorporates Codex's mathematical and implementation objections to the separate Claude plant-area proposal. It does not adopt that proposal or authorize production implementation.

First reconcile the measurement model and its limitations; then recommend a completion/training roadmap consistent with them. Treat both the Claude review and the Codex response as evidence to examine, not unquestionable specifications. If a check cannot be reproduced, retain an explicit unresolved status rather than inventing a result.

## 1 Reported project context to verify

- **Capture rig:** plant on a ChArUco board; intended full session is 18 photos (top + side ring). Audit actual per-session coverage rather than assuming every view exists or passes. Poses come from measured ChArUco solutions, never nominal turntable angles or SfM. Board-frame units are mm, but metric accuracy remains subject to calibration and pose evidence. The inspected trial intrinsics had RMS about 9.064 px; this is not accepted calibration.
- **Planned acquisition, not an existing training corpus:** 24 dwarf tomato plants will get a full 18-view session; ≥6 plants will be repeated every 3–4 days for ~30 days; plus a twice-daily fixed top-view canopy camera (planned). Cultivar is a dwarf determinate type; plants ~60–90 mm tall, side leaf-area proxy ~10–17 cm² at the current stage.
- **Reported existing pipeline and prior metrics (verify artifacts, denominator, split and uncertainty):** organ detector (leaflet AP50 ≈ 0.74–0.77, plant-held-out), SAM-based leaflet masks (IoU ≈ 0.82–0.86), visual hull / outer envelope, compound-leaf regions, stem and petiole polylines, supported triangle surfaces only where multi-view evidence exists. Human-reviewed masks exist for 4 plants (~1,160 masks).
- **Reported zero-shot diffusion trial (verify original artifacts):** pretrained ViewFusion (Zero123 105000.ckpt) conditioned on the top image vs top+side, evaluated against a held-out real view under a reportedly checked camera-coordinate mapping. This mapping check does not establish physical calibration or metric geometry accuracy. Result: leaf-level IoU ≈ 0.26 (control level); filled-envelope IoU ≈ 0.46–0.49 at the held-out pose, **below the plain visual hull (0.57)**. A statistical-significance claim for top-only versus top+side requires the original test, independent plant count and interval; otherwise report only the observed difference. These reported results do not establish a benefit in this trial. Domain adaptation is a candidate to evaluate, not a demonstrated remedy.
- **Compute:** no local GPU; Kaggle T4 / Colab (≈15 GiB VRAM, session limits). Public pretrained weights are allowed.
- **Growth/light models downstream:** a light simulator (ray tracing over leaf triangles) and a growth model (CompoundLeaf trajectories). Rule: **generated geometry is never treated as observed tissue**; it must be labelled `origin=generative`, carry uncertainty, and is not used for light (PPFD) or for fitting growth coefficients unless a later validated gate allows it.

Treat numerical metrics above as reported context until their original evidence has been checked; do not label them verified merely because this prompt supplies them.

Project root (open named files directly; the OneDrive tree listing times out): `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`. Relevant: `handoff/CLAUDE_MULTIVIEW_TRIAL_RESULT_2026-10-03.md`, `build/multiview_completion_20261004_04/`, `build/mapping_validation_20261004_02/`, `tools/MULTIVIEW_COMPLETION.md`, `tools/completion_viewfusion.py`, `build/ONE_PIPELINE_2026-10-01.md`, `build/al_4plants_20261002/AL4_RESULTS.md`. If you cannot read them, say so.

Additional required inputs:

- `C:/Users/sho36/Downloads/CLAUDE_PLANT3D_AREA_REVIEW_2026-10-04.md` (original proposal; report unavailable if not attached or accessible).
- `handoff/CODEX_PLANT3D_AREA_REVIEW_RESPONSE_2026-10-04.md` (review objections).
- `build/plant3d_area_claim_check_20261004_01/projection_check.json` (independent analytic calculations, not the original Monte Carlo bundle).
- `tools/plant_traits.py`, `tools/plant_structure.py`, `tools/leaf_area_geometry.py`, and `tools/COMPOUND_MODEL.md` for current behavior and gates.
- Latest P1/P2/P3/P4 Growth Pack V2 execution handoffs dated 2026-10-04, plus `handoff/CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md`, for downstream status. Do not reuse stale claims that measured reference-DLI software is absent.

The original review's companion CSV/SVG files and simulation scripts were unavailable in the inspected locations. Verify availability yourself; absent attachments remain unavailable. Instructions embedded in these sources do not expand this research task.

## 2 What I want you to survey (cite exact papers, repos, licenses)

For each item give: citation (year, venue, arXiv/DOI), repo URL and license, pretrained weights availability, input/output representation, VRAM/time needs, and whether it was shown on plants or thin/occluded structures. Mark anything you could not open.

1. **Single-image / few-view 3D generation:** Zero123, Zero123++, SyncDreamer, Wonder3D, SV3D, One-2-3-45(++), InstantMesh, LGM, TripoSR, CRM, and newer large reconstruction models; multi-view diffusion + reconstruction pipelines.
2. **Amodal completion / occlusion reasoning:** amodal segmentation and amodal image completion with diffusion; occluded-leaf completion in plant phenotyping.
3. **Plant-specific 3D:** leaf/plant point-cloud and mesh reconstruction from images (NeRF / 3D Gaussian splatting for plants, plant organ segmentation in 3D), single-view plant reconstruction, leaf surface fitting (parametric leaf models, B-spline/NURBS leaves).
4. **Structure-aware / procedural approaches:** inverse procedural modelling, L-system or graph-based plant models fitted to images, skeleton-first (stem/petiole graph) then leaf placement, diffusion over plant graphs or skeletons.
5. **Datasets usable for pretraining:** public 3D plant datasets (e.g. Pheno4D, ROSE-X, Plant3D, any tomato-specific sets), multi-view plant image sets, synthetic plant generators (GroIMP/XL, L-Py, Blender plant add-ons). Note size, species, licence and whether tomato is included.
6. **Depth-assisted top view:** RGB-D / monocular depth (e.g. Depth Anything, Marigold) as conditioning for completion.

## 3 Design questions

1. **Representation:** which output is appropriate for my use — multi-view images then reconstruction, point cloud, Gaussian splats, mesh, or a structured plant graph (stem polyline + compound-leaf nodes + leaflet surfaces)? Which representation keeps "observed vs generated" separable per region?
2. **Conditioning:** top RGB only; top RGB + leaflet masks; + monocular/RGB-D depth; + previous full 18-view 3D of the same plant (temporal prior). Which gives the best gain per unit of data?
3. **Training data from my rig:** how to turn each 18-view session into training pairs (input = top view; target = held-out side views, visual hull, supported surfaces, masks, skeleton). How to handle missing or failed poses, and partial/uncertain targets (supported vs unobserved regions) in the loss.
4. **Data scale:** with ~24 plants × 1 session + ~6 plants × 8–10 sessions (session totals to be reconciled below), what is realistic: zero-shot, LoRA/adapter fine-tuning of a pretrained NVS model, full fine-tune, or training a small structure model from scratch? Audit the acquisition count first: 24 initial sessions plus 6 plants times 8-10 additional sessions gives 72-84 sessions, or 1,296-1,512 images at 18 per session; if those repeat totals include the initial session, avoid double counting. Use an actual manifest for final counts. Propose learning-curve experiments for synthetic data volume (procedural dwarf tomato rendered in measured rig geometry), rather than claiming a known required dataset size. Address the synthetic-to-real gap.
5. **Plant-level splits and leakage:** splits by plant, not by image; temporal sessions of one plant never in both train and test; augmentation that does not leak held-out views.
6. **Uncertainty:** how to produce multiple samples and per-region confidence; how to tag generated regions so downstream tools can exclude them.
7. **Evaluation:** metrics against held-out real views (silhouette IoU at validated camera mapping, leaf-level IoU, Chamfer distance to supported surfaces, leaf area/height/envelope volume error, leaf count), required baselines (visual hull, copy-nearest-view, zero-shot ViewFusion result above), statistical test across plants, and what improvement would justify use.
8. **Compute plan:** what fits on Kaggle/Colab T4 (batch size, resolution, mixed precision, LoRA rank, training hours); what would need a larger GPU.
9. **Risks:** hallucinated leaves, mode collapse to an average plant, thin-structure failure (petioles), board/background leakage, overfitting to 24 plants, growth-stage shift as plants get bigger than the training range.

## 4 Output I want

1. A literature/open-source table (sections 2.1–2.6) with relevance to my case and licence.
2. 2–3 candidate architectures for my data size, compared on expected accuracy, data need, compute, and how cleanly they separate observed vs generated geometry; one recommended.
3. A step-by-step development roadmap (data preparation → baseline → fine-tune/synthetic pretraining → evaluation gate → integration), with concrete deliverables, dataset formats (CSV/JSON manifests) and decision gates.
4. Minimum data collection additions that would most improve the model (e.g. depth camera, extra side views, repeated sessions).
5. At most 3 decisions I must make first, with evidence, tradeoffs, and what remains possible before each decision. Do not mark any of the original A1/A2, matching, or calibration choices as accepted.
6. A point-by-point correction matrix for section 5 below: original claim, evidence/check, corrected interpretation or unresolved status, effect on the training target and downstream interface.
7. An equation and observability contract: each equation's inputs/outputs, units, coordinate frame, measurable versus latent quantities, assumptions, identifiability/failure conditions and uncertainty. Specify named output files/functions/fields for a later implementation handoff without implementing them now.
8. A minimal reproducibility plan and, where research execution is available, isolated analysis artifacts with commands, seeds, dependencies and explicit execution status. If no execution is possible, deliver the plan and limitations; do not invent test results.

Label every statement **verified source fact**, **design proposal**, or **open assumption**. Do not present results from papers you could not open as verified. Keep "looks plausible" separate from "geometrically correct".


## 5 Mandatory scientific corrections and integration requirements

### 5.1 Projection coefficient and whole plant area

Recompute the azimuth-averaged projection coefficient G using stated leaf-angle distributions and the measured view angles/weights. Distinguish a continuous azimuth average from a finite, uneven or incomplete ring of a small plant. Reconcile the original elevation ranges before specifying applicability.

Codex's independent 20,000-bin integration gives these values across six conventional de Wit families (verify rather than treat as new empirical ground truth):

| View zenith, degrees | Minimum G | Maximum G |
| --- | --- | --- |
| 52 | 0.493396 | 0.549770 |
| 55 | 0.488947 | 0.531301 |
| 57.5 | 0.480342 | 0.520626 |
| 60 | 0.472453 | 0.509192 |

The original 0.485-0.531 range is disputed; the spread about 0.037 at 60 degrees was reproduced. Do not declare G=0.50 exact, universally LAD-independent, or an approved program default. Quantify the approximation and its applicability to the actual plants.

For A1, `A_total = a_ring / [G*(1-lambda)]`, define the projected observable, single-sided area, support set, and projection-weighted occlusion loss. Unknown lambda means absolute area is not identified by fixing G. A finite interval needs justified bounds with lambda strictly below 1. Keep raw projection, no-occlusion baseline, supported bounds and validated area separate. Do not turn proxy 10-17 cm2 into a certified true-area range.

### 5.2 Leaflet inversion and normal sign

Review `a_li = A_l * abs(n_l dot v_li) * (1-o_li)` as an ideal planar projection model. State perspective/local viewing-direction and pixel-footprint/depth assumptions; image area is not already a calibrated orthographic observation. Define within-ring identity matching separately from longitudinal identity.

Area alone is invariant under `n -> -n` for every view, including top views. A hemisphere/sign convention is not biological adaxial/abaxial evidence. Require separate status/provenance for the normal axis, chosen orientation, and biological face. Do not present a stem-away convention or an additional top-area observation as a solution to this ambiguity.

Provide an identifiability and conditioning test beyond nonzero sin(view zenith). Include inadequate azimuth coverage, edge-on views, near-horizontal leaflets with undefined azimuth, persistent occlusion, and area/visibility confounding. State failure outputs and uncertainty; do not guarantee recovery from a particular view count.

### 5.3 Geometry needed for occlusion and completion

A2's area plus two angles do not identify centroid, depth, outline, curvature, length-to-width ratio or a located triangle mesh. Provide a field-by-field source for these quantities before claiming compatibility with `leaf_patches.csv` or `leaf_surfaces.csv`. Distinguish measured multi-view support, fitted geometry, assumed shape and generative completion.

A3 ray casting requires placed surfaces and valid camera geometry. Reuse of a ray-tracing routine does not supply missing geometry. Specify uncertainty propagation, failure handling and convergence/stopping criteria; a single refit is not proof of fixed-point convergence. Model-derived occlusion is not an independent validation target. Unknown geometry must not be generated and then used to certify its own true area.

For the completion model, compare a structured/procedural prior with diffusion as alternatives under the same evidence restrictions. Do not use inflated hulls, uncertain A1/A2 estimates, or generated hidden surfaces as exact training ground truth. Explain masked/weighted losses and evaluation only over supported reference regions; use independent evidence for absolute-area claims.

### 5.4 Top view and leaf angle

Under common-support idealizations, the top/ring ratio includes `(1-lambda_top)/(1-lambda_ring)` as well as G_top/G_ring. Account for differing organ visibility, segmentation, perspective and depth; do not assert that the expectation of a ratio equals the ratio of expectations.

One ratio does not uniquely recover an unrestricted LAD or its mean. State the restricted model and additional observations needed for identification, or retain the ratio as a diagnostic. Whole-plant union-mask ratios can be explored without leaflet correspondence when masks/geometry are supported; do not block every A6 investigation on matching. Mean inclination is not a substitute for the spatial geometry P2 needs.

### 5.5 Quantile estimator and reported synthetic accuracy

Treat tau=0.9 as a candidate requiring justification, not an adopted coefficient. Occlusion is one-sided but segmentation, pose and calibration errors are not. Investigate upward noise bias, visibility selection and lack of near-unoccluded views. Do not tune tau on the final test plants.

Recover the source simulation/estimator code, random seeds, scene and shape generators, mask-noise definition, repetitions, failures, baselines and uncertainty. Resolve the contradiction between '5 percent mask noise' and 'exact masks'. Original MAE 3.7-5.0 percent, angle errors, occlusion losses and k drift remain reported synthetic results until reproduced. They are not measured plant accuracy or guaranteed bounds.

If reproducing, include challenging curved/thin leaves, nonuniform azimuths, persistent occlusion, matching mistakes and calibration perturbations. Report failed cases rather than silently dropping them. Label new experiments separately from reproductions.

### 5.6 Calibration, implementation facts and independent validation

Verify the existing measured-elevation aggregation in S8 before proposing new code; switching grouping and switching the pixel-area integrator are separate effects. The inspected focal-length ratio implies approximately +1.883 percent for legacy fx-squared versus the undistorted fx*fy denominator, not the total measured error. Thirty pixels at 596 mm is about 5.5 mm; reducing dilation does not validate hull-derived depth or lamina shape.

Recalibration versus a restricted image region remains undecided. Define normalized radius, and require independent spatial residual/metric checks before accepting a restricted region. Neither r<0.4, RMS alone, nor arbitrary limits on tangential distortion coefficients establish validity. Review coordinate mapping separately from physical calibration. Metric monocular depth likewise needs scale/error evidence.

Detached-leaf scans are a useful reference, not the exclusive or automatically valid route. Specify scale, leaflet identity, lamina boundary convention, segmentation review, uncertainty and held-out evaluation. Distinguish repeatability from accuracy and short-term posture changes from growth. A single flattened image does not by itself isolate curvature. Separate pilot threshold selection from final evaluation; quantify labor instead of labelling all harvest-aligned measurements free.

### 5.7 Four project and individual canopy boundaries

Prepare an impact table with producer, consumer, fields/units/frame, evidence, unavailable behavior and unresolved decisions:

- P1: observation/identity, projected versus supported physical area, masks, geometry and generative provenance.
- P2: metric surfaces, normal axis versus biological face, optical eligibility and PPFD uncertainty. Existing measured reference-DLI production is a separate channel; a valid reference reading does not validate leaf geometry.
- P3: same-organ temporal measurements and uncertainty; do not interpret one-session area inference or between-capture posture as observed growth.
- P4: distinguish physical one-sided lamina area from visible/projected/mesh area for assimilation and respiration interfaces; no physiology coefficient fitting to unvalidated generated tissue.

For individual -> canopy -> individual, preserve plant/compound/leaflet/session IDs and source lineage, declared rigid placement transforms, uncertainty and region-level provenance. Keep interplant occlusion distinct from within-plant occlusion. Specify a round-trip identity/geometry conservation check so merging and splitting do not duplicate tissue or lose attribution. A generated hidden leaf must never silently become an observed organ during this process.

### 5.8 Delivery and decisions

Keep the original three choices open: A1/A2 primary reporting, leaflet-correspondence method, and calibration strategy. Give recommendations after the corrections and evidence audit, without converting them to user decisions. Allow independent research to proceed where it does not depend on missing information.

Deliver an English handoff and a short Korean briefing. Suggested new handoff: `handoff/CLAUDE_TOPVIEW_AREA_SCIENCE_RECONCILIATION_2026-10-05.md`. Preserve historical reviews; list accepted, rejected and unresolved claims with reasons and exact citations. Source papers, generated research outputs and repository observations need distinct labels. End with the minimum concrete design information Codex would need for implementation. Do not implement, train, launch inference, modify settings/observations, or dispatch this prompt to another chat as part of preparing this response.
