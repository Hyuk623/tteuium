# Prior art: a published dwarf-tomato FSP model, and what is left for this project (2026-10-08)

Source: Butturini, Smoleňová, Restina, Stolz, de Vries, Marcelis, "A functional–structural plant model for dwarf
tomato ideotype identification in vertical farming", *in silico Plants* 2026, 8, diaf024,
doi:10.1093/insilicoplants/diaf024, advance access 2025-12-22. Wageningen UR. Received from the user's professor.

**Read this before writing the conference framing.** It is the closest published work to this project's stated
goal and it is validated. The project's contribution has to be stated against it, not around it.

## What they built

- **First FSP model for dwarf tomato in vertical farming.** GroIMP 2.1.7, architecture encoded as a multiscale
  tree graph (MTG), light by Monte-Carlo spectral ray tracing (400–700 nm, 5 nm steps, up to 10 interactions).
  Runs in a **static** mode (leaf-level light at one instant) and a **dynamic** mode (growth over time).
- Cultivar *Solanum lycopersicum* 'Heartbreakers™ F1 Twiggy Red' (Prudac). Rockwool, vertical farm,
  LED 12 % blue / 9 % green / 79 % red / 2 % far-red, 230 µmol m⁻² s⁻¹, 22/19 °C, CO₂ 800 ppm.
- **Parameterized** at 35 and 65 plants m⁻², **validated** on a separate experiment at 50 and 80 plants m⁻²;
  3 × 3 plot with two border rows. Validated against fruit dry mass, total dry mass and leaf area index.
- Scenario analyses: ±2 °C, ±20 % PAR, and leaflet-morphology ideotypes.

## How they got the architecture — the part that matters most to us

**Photoneo MotionCam-3D Color** structured-light scans of **6 plants** at 35 plants m⁻² (DAT 42), each
reconstructed individually, encoded to MTG with PlantScan3D plus a custom Julia script, then merged into a single
**probabilistic average MTG per density** carrying a probability column = how often each element appeared across
the six plants.

**Plants were defoliated before 3D scanning "to ensure clear visibility of structural components."**

So the published model's architecture is (a) an average, not an individual, (b) obtained from a structured-light
scanner, and (c) obtained from plants that had to be taken apart to be scanned. Those three facts are where this
project's claim lives.

## Their leaflet-morphology result, and the one that contradicts a working assumption here

Changes vs baseline in net assimilation, static vs dynamic, at two densities:

| morphology | 50 plants m⁻² static | 50 dynamic | 95 static | 95 dynamic |
|---|---|---|---|---|
| curl **down** (90°, tip down) | −2.1 % | −4.0 % | −0.1 % | −4.9 % |
| curl **up** (90°, tip up) | +1.0 % | −1.4 % | +2.8 % | −1.7 % |
| shorter / longer (LW ratio halved / doubled) | <±1 % | ~+1–2 % | <±1 % | ~+1–2 % |
| different contour (diamond) | −0.5 % | 0.0 % | +0.3 % | **+5.6 %** |

Two readings to carry:

1. **Curl up helps in the static calculation and hurts in the dynamic one.** Our pipeline evaluates light at a time
   point, i.e. statically. **A curl/roll setting validated against a static light calculation can have the wrong
   sign for growth.** This is a direct caution for the `leaflet_roll_deg` / `leaflet_bend_deg` cell that G.2.3
   defers — do not let a static light gain justify a roll change.
2. **Contour shape is worth up to +5.6 %, but only in the dynamic mode at high density**; at 50 plants m⁻² it is
   ~0. Shape fidelity matters where canopies close. That supports spending effort on the contour pool (Addendum G)
   and says the payoff is density-dependent.

They state as a limitation that **in the dynamic calculations leaves were assumed flat**.

## Two things they left out that this project already treats

- **Interjected leaflets.** They model "only the primary leaflets"; additional smaller leaflets that "appear in
  semi-random locations" are excluded for simplicity. That is exactly the class of F.6 / F.7 / F.12 here. Our
  handling of it is an increment over the published model, not a detail.
- **Nutrition.** Their nutrient solution is fixed; fertilizer ratio and concentration are not model inputs. The
  project's step 3 (water and nutrient balance, root uptake, fertilizer response) is open ground with respect to
  this paper.

## Importable, because published and validated — propose, do not adopt silently

- **SLA as a linear function of planting density**, SLA = r₁·ρ + r₂, their eq. (3), with the stated rationale
  (SLA rises with shading/density). Compare with Barbosa et al. 2019, where SLA moved with irradiance while blade
  outline shape did not — the two agree and together argue that light should drive area and mass, not shape.
- **Coussement et al. (2018) geometric leaflet model**, chosen by them for minimal parameter requirements. Worth
  comparing against our contour-pool approach.
- Their parameter tables (max phytomers 10 main / 4 side, internode potential dry mass 203 mg, growth timings,
  maintenance-respiration and assimilate-requirement coefficients from Heuvelink 1995) are a published starting
  set for the carbon module.

## Where this project is still distinct — to be confirmed by the user, not assumed

Butturini predicts the **representative** plant at a density, from an averaged MTG built with a structured-light
scanner on defoliated plants. This project aims to predict **this individual plant's** leaves from **two ordinary
photographs** of an intact plant. Different input, different claim, and the per-individual claim is the one the
teacher–student design (36-view board turntable as teacher, 1 top + 1 side as product) exists to support.

**That distinction is only real if the per-individual result is demonstrated.** At present C6 is 0.328 against a
0.59 gate, so the claim is not yet earned. Framing the conference submission around individual-level prediction
commits to closing that gap or to reporting it honestly as unclosed.

## Their published parameter set — a starting point for our carbon and architecture modules

| symbol | meaning | value |
|---|---|---|
| φ | phyllotactic angle | 137° |
| β_branch | branch angle to vertical | 30° |
| **β_leaf** | **leaf inclination angle** | **70°, one value for every density** |
| T_base | base temperature | 5.7 °C |
| N_phytomers,max | max internodes, main stem | 10 |
| N_phytomers,side,max | max internodes, branch | 4 |
| LW1 / LW2 | leaflet length:width, rank 1 / rank ≥2 | 1 / **2** |
| w_str,int,max | potential internode dry mass | 203 mg |
| w_str,leaf1,max / leaf2,max | potential leaf dry mass, rank 1 / ≥2 | 111 / 547 mg |
| w_str,tru,max | potential truss dry mass | 488 mg |
| ψ | delay between fruit appearances | 42.4 °Cd |

Structure of the physiology, for comparison with our step 3: phytomer number is a **quadratic** function of plant
thermal time on the main stem and **linear** on branches, both capped; organ growth follows the **beta growth
function** (Yin et al. 2003); photosynthesis is **Thornley (1998)** with **Vanthoor (2011)** buffer feedback,
softened here from a binary switch to a gradual ramp between a minimum and maximum buffer threshold; maintenance
respiration is Q10 with an extra factor `(1 − e^(−f·RGR5))` using the 5-day mean relative growth rate as a proxy
for metabolic demand; 21.5 million rays per light simulation, ray depth 10.

**Roots are a carbon sink only — "their structure is not simulated, and they do not contribute to water or nutrient
uptake."** Flower and fruit abortion is not simulated either.

## Their validation, with the failure mode stated

| density (plants m⁻²) | variable | RMSE | PBIAS | NRMSE | rating |
|---|---|---|---|---|---|
| 35 / 65 | LAI | 0.1 / 0.2 | +4.4 / +0.4 | 8.5 % / 7.4 % | excellent |
| 35 / 65 | fruit dry mass | 1.3 / 0.8 g plant⁻¹ | −10.9 / −9.9 | 15.7 % / 17.4 % | good |
| 50 | fruit dry mass | 1.0 | −6.6 | 19.0 % | good |
| **80** | **fruit dry mass** | **1.3** | **−19.6** | **32.3 %** | **poor** |
| 35 / 65 | plant dry mass | 1.4 / 1.0 | −8.8 / −9.2 | 14.5 % / 15.4 % | good |

**The bias is systematic, negative, and grows with density.** Their own diagnosis, quoted:

> "architectural acclimation to crowding is not yet represented beyond a density-driven change in SLA; **in
> particular, we used a single set of leaf and leaflet elevation angles for all densities.** If plants at high
> density deploy steeper leaves or altered leaflet orientation, the fixed-angle parameterization would underpredict
> light capture and downstream assimilate supply to fruits."

and, separately:

> "the FSP model does not currently account for such internode elongation" (shade avoidance at high density, which
> Karpe et al. 2024 observed but their own cultivar did not clearly show)

and:

> "Enhancements to leaf morphology representation, particularly in capturing the **curliness** of leaves, are also
> needed, as this feature remains challenging to model **and measure**."

## This is the opening, stated plainly

The published state of the art names three things it is missing, and all three are **measurements of intact
individual plants under different spacings**:

1. **leaf and leaflet elevation angle as a function of planting density** — currently one fixed 70°;
2. **internode elongation under crowding** — not represented at all;
3. **leaf curliness** — which they call hard to model *and to measure*.

An image-based per-individual phenotyping pipeline is an instrument for exactly these three. That is a sharper
claim than "we also built an FSP model", and it does not require out-competing a validated model: it supplies the
input that model says it lacks.

## What their scenario results say about where our effort is worth spending

Their leaflet morphology scenarios hold total leaf area, light input and plant dry mass constant, so the numbers
isolate shape:

- **Leaflet length:width ratio (1 vs 2 vs 4): under ±1 % in almost every case.**
- **Contour shape (baseline vs diamond): up to +5.6 %**, but only in the dynamic model at 95 plants m⁻²; ~0 at 50.
- **Curvature: up to −4.9 %**, and sign-flipping between static and dynamic for upward curl.

For the FSP, therefore, **aspect ratio is close to worthless and contour shape and curvature are where the
physiology is.** This reorders our own queue: the Addendum G contour-pool work sits on the high-value axis, while
F.11a's aspect floor (+0.031 AP50) buys detector score and almost no assimilation. **Said precisely:** aspect may
still matter for the C6 detector gate, which is a measurement instrument; it does not matter for the carbon model,
which is the product. Do not let a gate metric set the modelling priority.

## Related, same folder of material

Usenko, Helman, Giladi, "Using 3D reconstruction from image motion to predict total leaf area in dwarf tomato
plants" — 73 plants, 418 TLA measurements, cultivars Mohamed / Hahms Gelbe Topftomate / Red Robin, Canon
PowerShot SX70 HS video (40–60 s, 1920×1080), 500 frames per plant, **Meshroom SfM** terminated after the SfM step,
scale imposed from the pot as a reference object, Alpha Shape (α = 3) + XGBoost → **R² 0.80, MAE 489 cm²**
within experiment, falling to **R² 0.56, MAE 579 cm²** when training and testing on different experiments.
Their ground truth uses an **"onion" approach: sequential removal of leaf layers with a scan at each stage.**

Two consequences:

1. **Sequential defoliation is the published method for this measurement**, arrived at independently by two groups
   (Usenko's "onion"; Butturini defoliating before scanning). The plant-1 protocol in
   `data/records/destructive_capture_20261008/PROTOCOL.md` is therefore standard practice, and can be cited as such.
2. Their cross-experiment drop, R² 0.80 → 0.56, is the honest figure for how an image-based leaf-area model
   generalizes across growing conditions. **Any accuracy this project reports within one experiment should be
   expected to fall similarly across experiments**, and the conference text should say so rather than quote a
   single within-experiment number.

Further detail worth having:

- **Scale came from a known 15 cm pot diameter**: a plane was fitted to the colour-classified pot points, the pot
  top set to Z = 0, a circle fitted on that plane, and the cloud scaled by the ratio of 15 cm to the fitted
  diameter. Same idea as our ruler, with a different reference object.
- **Feature selection collapsed to three features.** After mutual information and Boruta, only **height, width and
  mesh surface area** survived; volume, aspect ratio, bounding-box area and volume, and component count were all
  dropped. Height was the single most predictive.
- **MAE 489 cm² is 31 % of the mean TLA** (combined mean 1573 cm², median 1317, range 150–6301). The headline
  R² = 0.80 is not a small error in absolute terms.
- Four mesh algorithms x seven regressors: Alpha shape was best overall, Poisson worst; the linear models
  (MLR, Lasso, Ridge, ENR) all landed at R² 0.61–0.72, i.e. within ~0.1 of XGBoost's 0.80.

### A leakage problem in their headline number — and the reason it matters to us

The 0.80 comes from a **random 70/30 split of 418 measurements taken from 73 plants**, i.e. about 5.7 rows per
plant, because the "onion" method measures the *same plant* at successive defoliation stages. A random row-wise
split therefore puts other stages of the same plant in both train and test. The independent unit is the **plant**,
not the measurement.

Their own cross-experiment results are consistent with this: R² falls from 0.80 to **0.52–0.56** the moment the
split is forced to be between experiments. They justify pooling with a t-SNE that shows no clustering by cultivar,
treatment or experiment — but a t-SNE showing no clusters does not establish that a model transfers, and their own
transfer test shows it does not.

**This is the same error class that Addendum I.1 corrected here**: scenes (plants) are the independent unit, not
views. Our per-scene bootstrap and the 0.029 noise floor exist precisely to avoid quoting a within-plant number as
if it generalized. When this project reports an accuracy, it must be from a **leave-plant-out** split, and the
conference text should give both numbers if a random split is also reported.

Note that Usenko uses SfM, which `TOMATO_3D_PHENOTYPING_ALGORITHM_SKELETON_2026-09-15.md` explicitly forbids here
(pose comes from the rotating ChArUco board). That remains a deliberate difference, not an oversight.

---

# Third paper: PlantMDE — single-image 3D plant phenotyping (2026-10-08)

Zhuo & You, "3D plant phenotyping from a single image: learning fine-scale organ morphology with monocular depth
estimation", *Computers and Electronics in Agriculture* 239 (2025) 110925. Cornell.

Where diaf024 is the closest prior art to our **model**, this is the closest prior art to our **product**: 3D plant
structure from a single ordinary RGB image, no multi-view rig.

## What they built

- **PlantMDE**, a monocular depth estimation model for plants, with a **organ-wise auxiliary loss** and an
  organ-wise evaluation metric (OW-PCC), on top of the general MDE lineage (Depth Anything, Marigold, DPT).
- **PlantDepth**, 32 751 RGB-D samples, 56 species, 8 sources — over an order of magnitude larger than the previous
  largest plant RGB-D set (PlantStereo, ~1 500). Much of it is **rendered from 3D plant models**, with multi-view
  sampling of camera position and radius; SAM supplies pseudo-segmentations where labels are missing.
- Downstream, used as a feature extractor, it cuts RMSE by **10.2 %** (Setaria biomass) to **29.5 %** (tomato
  height) and raises stress-classification accuracy by 12.1 % (water) and 19.2 % (nitrogen).

## The result that matters most here, and it is not about them

Their training-mix ablation (their Table 3) is the experiment this project is effectively running. **Crops3D was
the one source that made generalization worse**: including it cost **−10.27 %** on PlantStereo in one mix and
**−28.65 %** in another. Their explanation, quoted:

> "The RGB-D images from Crops3D are generated from high-sparse point clouds, resulting in incoherent structures
> and noisy textures. Such imperfections may confuse the model during training, hindering its ability to generalize
> well to real-world datasets like PlantStereo."

**Low-fidelity synthetic plant data did not merely fail to help — it actively degraded transfer to real data.**

That is external, quantitative support for the realism gate (C1–C7) and for refusing to run Stage 1 at
C6 = 0.328 against a 0.59 gate. It converts "we are being fussy about synthetic realism" into a published finding
with a number attached. **It should be cited wherever the gate discipline has to be justified.**

## Three places it is weak exactly where this project is strong

1. **No metric scale.** Quoted: "PlantMDE predicts zero-shot **relative** depth due to the use of scaled
   ground-truth and predictions during training. To enable metric depth estimation, PlantMDE can be further
   fine-tuned on specific datasets (thus no longer operating in the zero-shot setting)" — encoder frozen, decoder
   retrained, per domain, and it needs metric ground truth to do it. Our ChArUco board plus the ruler give metric
   scale directly, which is what the whole I.4 / I.4b line of work secures. An FSP needs cm², not relative depth.
2. **Occlusion.** Quoted: "fundamentally limited to reconstructing only the visible portions of a plant, and cannot
   recover structures that are fully occluded … particularly problematic in scenes with overlapping leaves or
   densely clustered organs". That is our C5 regime and the entire density question. They name **plant skeleton
   priors** as the fix they have not built, and note such priors "would require annotated plant skeleton datasets
   derived from manual labels, 3D scans, or synthetic generation" — which is what the teacher rig produces.
3. **Viewpoint.** Quoted: "optimized for near-top-down views commonly used in controlled environments, so that its
   performance may degrade substantially for horizon views". Our product is 1 top **+ 1 side**.

## The decision this raises — it is not "compete or ignore"

PlantMDE is a candidate **component** of the twoview inference step, not a rival to it: a depth prior that we would
pin, run frozen, and correct with the board's metric scale and the teacher's amodal masks. Conversely, the 36-view
board turntable produces exactly what its authors say the field lacks: metrically scaled, per-organ segmented,
occlusion-labelled plant data with both visible and amodal masks.

Against that: CONVENTIONS.md forbids new dependencies, and a pretrained MDE backbone is a large one with its own
frozen-artifact and provenance requirements (the detector is already pinned by sha256 for exactly this reason).
**Recorded as an open option, not adopted.** It should be decided after G.2 settles, not during it.

## How the three papers divide the ground

| | diaf024 (Butturini) | Usenko | PlantMDE (Zhuo & You) |
|---|---|---|---|
| output | organ-level FSP, growth and yield | total leaf area, one number | per-pixel depth, organ geometry |
| input | averaged MTG from 6 defoliated plants, structured-light scanner | 500 video frames per plant, SfM | one RGB image |
| scale | physical units throughout | imposed from a known 15 cm pot | relative; metric only after per-domain fine-tuning |
| individual or average | **average per density** | per plant | per image |
| occlusion | ray-traced within the canopy | ignored (whole-plant mesh features) | **named as the core limitation** |
| named gap | leaf/leaflet angle vs density; internode elongation; curliness | cross-experiment transfer (R² 0.80 → 0.55) | occlusion; skeleton priors; metric scale; side views |

**All four of those named gaps are the same gap seen from three directions: nobody has metric, per-organ, per-
individual structure for an intact plant under different spacings.** That is what this project's teacher rig is
for, and it is a more defensible claim than any one of the three alone.

---

# Fourth paper: LeafTrackNet — leaf identity over time (2026-10-08)

Liu et al., "LeafTrackNet: A deep learning framework for robust leaf tracking in top-down plant phenotyping",
*Computers and Electronics in Agriculture* 256 (2027) 112417. ATB Potsdam + BASF. Code and data public (GitHub).

This is prior art for **step 5 of this project** — comparing predicted growth against later photographs requires
knowing WHICH leaf is which across capture dates ("어떤 개체의 어떤 잎"), and `data/tracks/` exists for that but
nothing has been built.

## What they built

- **CanolaTrack**: 5 704 top-down RGB images, 31 840 leaf boxes with persistent identities, 184 canola plants,
  31 consecutive days, **Δt = 24 h**, pot rotation included — the largest leaf-tracking dataset to date (the
  alternatives: LeTra 9 plants, KOMATSUNA 10, MSU-PID 21).
- **LeafTrackNet**: YOLOv10 leaf detector + MobileNetV3-Large 128-d embedding trained with triplet loss where the
  positive pair is the SAME leaf at DIFFERENT time points (so the embedding learns growth-invariance); inference
  matches detections to a memory bank by cosine similarity + Hungarian assignment, EMA-smoothed (α = 0.5), tracks
  dropped after τa = 5 missed frames.
- HOTA 87.56 on CanolaTrack vs 76.5 (LeTra, IoU mask matching), 75.0 (Plant-Doctor, generic ReID), 67.7 (MOTRv2
  lineage); **identity switches 4 ± 1 vs 16–278** for the baselines.

## The design lesson that transfers

Their stated failure analysis: **geometric association (IoU, Kalman, centroid, mask overlap) breaks on plants**,
because leaves grow nonlinearly, deform, occlude each other, emerge and disappear, and pots get rotated — general
MOT assumes rigid motion and smooth trajectories, which plants violate. Appearance embeddings trained for
growth-invariance, plus a temporal memory, are what survived. At Δt = 24 h — a realistic monitoring cadence.

## Three ways our setting differs, two in our favour

1. **We have measured pose.** Their "rotational artifacts" are an unknown; our ChArUco board measures azimuth, so
   leaves can be matched in the PLANT frame, not the image frame. The right design for us is a hybrid: board-pose-
   normalised 3-D position as a strong prior + an appearance embedding for the ambiguous cases — not their
   appearance-only pipeline, and not geometric-only either.
2. **Our tracking unit is the compound leaf, not the leaflet.** Canola rosette leaves are singular; tomato leaflets
   within one compound are near-identical in appearance (an embedding's worst case) but rigidly co-located on the
   rachis. Track compounds; inherit leaflet identity from `station_index` within the compound.
3. **Against us**: our capture interval will be days, not 24 h, and dwarf tomato occlusion is heavier than early
   rosette canola. Expect their HOTA numbers to be an upper bound, not a forecast.

## A free test set we are already going to produce

Plant 1's sequential-defoliation series (same fixed camera, one compound removed per step, ~8 steps) is a small
identity-labelled sequence under OUR imaging conditions at zero extra cost: identities are trivially known, and
each step changes occlusion exactly the way a matcher must survive. It tests occlusion-change robustness only —
same-day, so no growth drift — but it is enough to reject a matcher before any multi-date annotation is spent.

**Status: recorded for step 5. Nothing to build now** — it becomes relevant at the first repeated-capture series,
after the current capture pack and G.2. The arrangement series (§3.5) does not need it (same-day, known plants).

---

# Fifth paper: S2SegNet — organ segmentation of tomato point clouds (2026-10-08)

Li et al., "S2SegNet: A semantic-instance joint segmentation network for point clouds of single-stem tomatoes",
*Computers and Electronics in Agriculture* 255 (2026) 112345. Tarim University + Zhejiang University.

Teacher-side prior art: stem/leaf semantic + per-leaf instance segmentation directly in the 3-D point cloud.

## What they did

- **Acquisition is a turntable teacher rig**: each plant on an electric turntable, Kinect v2, ~170 images/plant,
  **Metashape (SfM) multi-view reconstruction**, 4 sessions at 15–20-day intervals (seedling + growth stages),
  cv. Provençal large-fruited. 184 plant point clouds, expanded to 552 **by downsampling only** (their own
  limitation: no real added diversity). Per-point stem/leaf + leaf-instance labels in CloudCompare.
- **S2SegNet**: dual-neighbourhood graph attention (coordinate-based SGA + feature-similarity LDRA), a spectral
  shape descriptor from the neighbourhood covariance spectrum as structural prior, two-stage attention, gated
  fusion; joint semantic + instance heads; a single-stem-specific loss and stem-merging post-processing.
- Results: semantic F1 93.28 %, mIoU 87.65 %; **leaf instances mPre 81.33 %, mWCov 78.24 %**; stem instance
  mPre 100 % — which follows from the prior that there is exactly one stem.

## Why the network itself does not transfer

The single-stem assumption is baked into the loss and the post-processing, and their limitations section says it
plainly: "stem instantiation in scenarios with **multiple stems or multiple plants occluding each other** remains
challenging." Our material is a bushy, branched dwarf, and the §3.5 arrangement series is literally multiple
plants occluding each other — the case the paper names as unsolved. Their numbers are also from a large-fruited
single-stem cultivar with well-separated leaves, so 81 % instance precision is an upper bound, and 1-in-5 wrong
instances is below the bar for teacher ground truth (our C7 assisted-labelling gate exists because even SAM at
0.72 IoU needs human review).

## The one directly importable idea — no new dependency

The **spectral shape descriptor**: eigenvalues of the local neighbourhood covariance give
linearity / planarity / scattering, and stems are linear while blades are planar. That is classical geometry
(PCA per neighbourhood, a few lines of numpy), usable in OUR teacher pipeline as a cheap stem/leaf prior on hull
or cloud points before any 2-D mask projection — worth a declared diagnostic when the teacher 3-D stage is next
touched. Import the idea, not the network.

## Two protocol points worth keeping

1. **Cross-growth-stage evaluation** (train one stage, test the other) as an explicit generalization test — the
   same discipline as our scene-level independence and the Usenko cross-experiment critique, applied to time.
2. Third independent group converging on **turntable multi-view** for tomato 3-D (Usenko: video SfM; Butturini:
   structured light on a defoliated plant; here: turntable + Kinect + Metashape). The teacher design is standard
   practice; our board-pose variant (no SfM, pose from the ChArUco board) remains the deliberate difference.

**Status: recorded. Nothing to adopt now**; the eigenvalue stem/leaf prior is queued as a future teacher-side
diagnostic, not scheduled.

---

# Sixth paper: Zhu et al. — canopy traits, including the petiole angle, from consumer 3-D (2026-10-08)

Zhu et al., "A calculation method of phenotypic traits based on three-dimensional reconstruction of tomato
canopy", *Computers and Electronics in Agriculture* 204 (2023) 107515. Heilongjiang Bayi Agricultural University.

- **Rig**: three Kinect v2 at 120° around the plant (fixed triad — no turntable), cv. Dongnong 708, three growth
  stages. Registration ISS + ICP coarse then an improved 3D-NDT fine (avg error 0.027, beating plain NDT/ICP);
  AlphaShape canopy contour; skeleton extraction + DBSCAN for organ junctions.
- **Traits vs manual ground truth** (ruler, vernier caliper, electronic angle gauge, measured the day before/after):
  plant height r 0.9615 / 1.38 cm error; canopy width R² 0.809 / 1.92 cm (their weakest trait — and footprint-type
  width is also our weakest-defined gate, C2); **leafstalk (petiole) angle R² 0.922, mean error 5.1°,
  accuracy 91.76 %** — angle defined at the stem–petiole junction from the skeleton.

## Why this one matters despite the modest rig

It is the published feasibility figure for exactly the quantity diaf024 says it lacks (one fixed 70° leaf angle for
all densities, named as the cause of its density-dependent bias): **the leaf/petiole insertion angle can be
measured from consumer-grade 3-D with ~5° mean error against an angle gauge.** So the FSP's missing input is
measurable with hardware far below our teacher rig, and ±5° is the bar our board-based teacher should beat or at
least match when it reports angles. Their motivation sentence — the leafstalk angle "directly affected the spatial
distribution of crop canopy light" — is the same causal link our step 2 computes.

Also kept: their manual-GT protocol (electronic angle gauge on labelled petioles) is cheap and compatible with our
destructive session — compounds get removed anyway, so measuring each one's insertion angle by hand just before
removal would give us our own angle ground truth for free (~1 min per compound). Proposed to the user, not added.

Registration machinery (ISS/ICP/NDT) is not needed here — the board gives pose directly. Fourth independent group
on multi-view tomato 3-D; the no-SfM board-pose teacher remains our deliberate difference.

---

# Source check 2026-10-10 (Claude) - LeafTrackNet numbers and related tracking papers

Checked against the publicly retrievable original, arXiv:2512.13130 v1 (15 Dec 2025, the only version listed;
the HTML lists the journal as Computers and Electronics in Agriculture). The 2026-10-08 entry above (CEA 256 (2027)
112417) was written from a user-supplied PDF that is not in the repository; it could not be re-checked.
**Until that PDF is re-checked, treat the 2026-10-08 numbers as unverified and do not cite them.**

Differences between the 2026-10-08 note and arXiv v1 (Table 2, CanolaTrack test, mean +- SD of 3 runs):
- HOTA: LeafTrackNet 88.03 (note: 87.56); MOTRv2 78.30 (note: 67.7); LeTra* 67.02 (note: 76.5, and LeTra was
  adapted from masks to boxes); Plant-Doctor 59.74 (note: 75.0); BoT-SORT 33.32, ByteTrack 33.58 (not in note).
- Identity-switch counts are NOT reported in arXiv v1 ("4 +- 1 vs 16-278" in the note is unsupported).
- Embedding dimension is not stated in arXiv v1 (note: 128-d). Similarity threshold tau_s = 0.4, triplet margin 0.3,
  EMA alpha 0.5, track removal at age tau_a = 5, detector confidence 0.5. No position/motion cue is used at all.
- Plant-disjoint split: 147 train / 37 test plants. Occlusion/reappearance and pot rotation are shown only
  qualitatively (Fig. 3) and per-leaf for one plant; not quantified over the test set.
- Unmatched detections start new tracks; this is a tracker convention, not an emergence date.

Other sources checked:
- LeTra (Jurado-Ruiz et al., Plant Methods 2024, doi:10.1186/s13007-024-01138-x): Arabidopsis, top-down
  chlorophyll-fluorescence images (not RGB), 3 images/day (max gap ~8 h), 9 plants / 191 leaves; Mask R-CNN +
  greedy IoU > 0.15 to the next frame; unmatched query masks are carried forward. Mean HOTA 0.846; 161 or 162 of 191
  leaves tracked (abstract and results disagree). Authors state failure beyond ~3-4 missed frames because growth
  breaks overlap; merges/splits and rotation not addressed. Applies to near-continuous capture, not weekly.
- Heiwolt et al., arXiv:2209.11526 (statistical shape representations, Pheno4D tomato point clouds, ~2-day steps):
  boundary-outline PCA (23 PCs) + Mahalanobis + Hungarian; best sensitivity 0.754 (shape+location+rotation);
  location only 0.605. 3D-only; axis alignment failed for ~13% of leaves; only 68% of leaves gave clean outlines.
  Whether a "leaf" is a compound leaf or a leaflet is not stated.
- Pheno4D (Schunck et al., PLoS ONE 2021, doi:10.1371/journal.pone.0256340): 7 tomato plants, laser scanner,
  every-second-day labels with one label per leaf for the whole series; compound-vs-leaflet unit not stated.

Applicability to this project: none of the four tracks tomato compound leaves and leaflets as two linked levels
from weekly top-view RGB. Transfer is limited to (a) the matching machinery (embedding + memory + Hungarian with an
explicit no-match option), (b) the lesson that overlap-only matching degrades as the gap grows (LeTra), and
(c) outline-shape cues helping over location alone in tomato (Heiwolt; 3D, ~2-day gap). No performance number from
these papers is a target for this project.
