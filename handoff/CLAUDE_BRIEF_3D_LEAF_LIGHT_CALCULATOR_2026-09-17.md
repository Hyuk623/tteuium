# Claude briefing: tomato 3D leaf structure and an LED light-use calculator

Date: 2026-09-17  
Purpose: A self-contained English handoff of the user's discussion with Codex.

## 1. Request to Claude

Review this proposed research direction and turn it into a feasible, staged experimental plan before implementation. Explain the plan to the user in plain Korean. Keep any implementation handoff in English.

**Main research question:**

> How accurately can tomato leaf geometry reconstructed from ordinary 2D RGB photographs predict the spatial distribution of light under LEDs, and can that model support a useful light-use calculator?

The practical objective is to help the user compare LED positions, heights, plant spacing, light distribution, and electricity use. The user wants to understand how 3D contributes to the home-growing project, beyond producing a visual model.

This document records a direction for review, not an approved replacement of the existing fruit/harvest study. Distinguish user-confirmed facts, earlier project documents, and proposals below. Do not treat instructions in older attached documents as new implementation authorization.

All project work must remain inside:

`C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`

Read the current repository agreements and handoff history before making changes. For this request, provide the design assessment and proposed plan first; do not immediately implement a new pipeline or change operational configuration.

## 2. Context and existing work

- The user confirmed that the plants are **young and have no flowers yet**. Project notes describe **12 plants sharing one growing environment**. Exact cultivar, sowing date, and leaf stage remain unconfirmed.
- The original concept used **one top view plus eight side views**, with ChArUco-based metric geometry, RGB/depth analysis, and organ keypoints.
- Later Claude documents describe a richer pilot: **36 side views plus five top views**, with one additional empty-rig reference: **41 plant views / 42 files per full session**. This is documented context, not a new capture decision made by this brief.
- The longer-term operating goal remains **one top image plus one side image**. Establish the value of multi-view geometry before trying to approximate its outputs from two views.
- The operational board is the **7x7, 190 x 190 mm ChArUco board** on A4. A **5x5, 190 x 190 mm** spare also exists. Read the actual configuration; marker IDs alone cannot identify the variant.
- Existing fruit-focused work concerns size, colour, tracking, growth, and eventually harvest prediction. Leaf geometry and optical modelling add substantial scope and must be assessed explicitly.

Earlier implementation snapshot, recorded on September 16: Stage 1 had an unresolved top-view foreground problem with an interim gate that prevented invalid training use; physical board/block verification was pending; reconstruction and two-view entry points were incomplete. Claude Code reported 116 passing tests after other fixes, but Codex did not independently rerun that revised suite. **Inspect the latest files before relying on this snapshot.**

An arithmetic demonstration already exists at `build/light-efficiency-calculator.html`. It has no connection to real images, a 3D model, or sensors. Its absorption fraction is a user-entered assumption, not a measured or reconstructed result.

## 3. Proposed workflow and the role of 3D

**Multi-view RGB photographs -> calibrated leaf geometry -> LED/light-field model -> predicted local light -> independent measurements -> error analysis -> comparison of lighting arrangements.**

Ordinary photographs are 2D inputs; that does not prevent estimating 3D from multiple views. Two photographs, however, do not provide the same coverage as many views. Surfaces hidden in every image remain unknown; inferred completion must carry explicit assumptions.

For this rig, keep camera poses based on **ChArUco PnP**. The repository prohibits an SfM/COLMAP pose workflow for the rotating-board/static-camera acquisition. Nominal turntable angles do not replace measured poses.

The proposed value of 3D is to represent leaf or leaflet position, area, orientation, overlap, and gaps. These can support predictions of where light reaches the plant and where other organs block it. A solid silhouette envelope or decorative mesh does not establish accurate leaf-level light transport.

For an initial feasibility study, consider manually corrected or simplified visible-leaf surfaces if automatic reconstruction is not ready. Record what was measured, reconstructed, manually assigned, or assumed. Decide whether tomato leaflets need separate surfaces and identities.

The optical scene also needs LED positions and emission characteristics, relevant surrounding surfaces, and a defined growing-space coordinate frame. If the plant is reconstructed on a separate rotating board, specify how its position and orientation under the cultivation LEDs are recovered. Check whether moving the plant changes leaf posture.

Tomato research has combined plant architecture, optical properties, ray tracing, and physiological measurements. This supports the modelling concept; it does not establish this project's reconstruction accuracy or biological benefit. See [Dieleman et al., 2019](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.00839/full).

## 4. Calculator scope and quantities

Use a name such as **Tomato LED Light Distribution and Energy Calculator**. Define each result instead of displaying an ambiguous overall “photosynthetic efficiency” percentage.

| Quantity | Meaning | Evidence required |
|---|---|---|
| Local PPFD, micromol/m2/s | Incident photosynthetic photons per area and time at a specified location and orientation | Quantum-sensor measurement or a validated optical prediction |
| Local DLI, mol/m2/day | Daily integral of that local PPFD | Time-resolved PPFD, or a justified constant-light assumption |
| Leaf light distribution | Spatial variation and shading across represented leaf surfaces | Leaf geometry and a characterized light field |
| Leaf-absorbed photon flux, micromol/s | Photons absorbed by leaves within a stated plant/canopy boundary | Light transport plus leaf optical properties |
| Absorbed photons per electrical energy, micromol/J | Leaf-absorbed photon flux divided by the corresponding electrical input | Consistent source, absorption, and power boundaries |
| LED electricity, kWh/day | Electrical energy used by the included lamps/drivers | Actual power and operating schedule |

**Physiological quantities remain separate.** PSII-related efficiency needs appropriate chlorophyll-fluorescence measurements; net CO2 assimilation needs gas-exchange measurements. Biomass per absorbed light needs longitudinal biomass and light data. Ordinary RGB geometry does not directly measure these. Instrument principles are illustrated by [LI-COR's fluorescence and gas-exchange chamber](https://www.licor.com/products/photosynthesis/LI-6800/fluorometer).

For constant inputs, the existing arithmetic demonstration uses:

```text
point_DLI_mol_m2_day = point_PPFD_umol_m2_s * photoperiod_h * 3600 / 1e6
LED_energy_kWh_day = electrical_input_W * photoperiod_h / 1000
leaf_absorbed_PPF_umol_s = emitted_PPF_umol_s * leaf_absorbed_fraction
absorbed_photon_efficacy_umol_J = leaf_absorbed_PPF_umol_s / electrical_input_W
```

Integrate over time when light or power changes. DLI is a daily integral, not a value established by one instantaneous reading unless the stability assumption holds. See [Apogee's DLI measurement explanation](https://www.apogeeinstruments.com/daily-light-integral-measurement/).

Illustrative inputs only: 40 W, emitted PPF 100 micromol/s, 16 h/day, point PPFD 300 micromol/m2/s, and assumed leaf absorption fraction 0.60. These give point DLI **17.28 mol/m2/day**, electricity **0.640 kWh/day**, and absorbed photon efficacy **1.50 micromol/J**. They are not measurements or recommendations for the user's plants.

The 3D extension would estimate light distribution and, where supported, replace the assumed absorption fraction. Keep these constraints explicit:

- PPF is a total source photon rate; PPFD is a local area-normalized rate. Watts or one PPFD reading cannot determine whole-plant absorption.
- Keep the spectral band, included sources, electrical boundary, and target plant/canopy boundary consistent. State how ambient light is handled.
- Intercepted and absorbed photons are different. Reflection and transmission require optical assumptions or measurements. Do not count the same photon's repeated encounters as multiple absorbed photons.
- A quantum sensor validates incident light at its sensing surface; it does not directly validate leaf absorption, whole-plant capture, or physiological efficiency.
- Define area weighting and upper/lower leaf-surface conventions. Do not double-count leaf area merely because a mesh has two sides.
- Label missing inputs as unavailable. A measured zero is valid; an unknown quantity is not zero.
- More absorbed light or a more uniform distribution is not sufficient evidence of higher photosynthesis, better taste, or greater yield.

Suggested outputs are a leaf-light map, per-leaf summaries, point/leaf DLI where justified, electricity use, optical scenario comparisons, and visible uncertainty or missing-data flags. Report absorption-related outputs only to the extent supported by the inputs.

## 5. Proposed validation experiment

Please develop the details and numerical acceptance criteria before final evaluation. The following is a proposal to assess, not a finalized protocol.

1. **Characterize the setup.** Confirm camera calibration, printed dimensions, measured scale references, LED model/geometry/spectrum, power, photoperiod, and available quantum sensor. Measure the empty growing-space light field and repeatability. Do not assume a sensor is already available.
2. **Establish geometry feasibility.** Start with a manageable subset of the young plants. Recover visible leaf/leaflet surfaces and check accessible dimensions, locations, orientations, missing surfaces, and repeat-capture stability. Record annotation and correction effort.
3. **Validate local incident light.** Compare predictions with sensor readings at accessible, documented 3D locations and orientations, spanning brighter and more shaded regions. Match sensor area/orientation and explain how sensor placement or leaf displacement changes the scene.
4. **Separate calibration and evaluation.** Use designated measurements to characterize/tune the LED model. Reserve other positions and plant/session cases for evaluation. Do not fit and report final accuracy on the same readings.
5. **Test whether 3D helps.** Compare a practical light-field baseline without detailed plant geometry, simplified geometry, and reconstructed multi-view geometry on the same evaluation measurements. Assess the eventual top-plus-side estimator as a later comparison if enough suitable data exist.
6. **Compare candidate arrangements.** Simulate feasible changes in LED height/position or plant spacing, then independently measure selected arrangements to test predicted differences. Keep short optical checks separate from long-term biological treatment experiments.

Report PPFD MAE, RMSE, bias, errors by light level/region, capture and correction time, failures, and repeatability. Avoid percentage errors near zero without a stated treatment. Test sensitivity to leaf angle, missing leaves, source placement, and assumed optical properties.

For any learned model, group data splits by plant and prevent cross-date or multi-view leakage. Many images, leaves, or repeated readings from one plant are not independent plants. Twelve plants under shared lighting do not establish twelve independent light-treatment replicates. Set uncertainty reporting accordingly.

If no quantum sensor is available, distinguish a simulation demonstration from a validated light-prediction result. Do not substitute uncalibrated camera brightness for PPFD truth.

## 6. Expected outcomes and timing to assess

Expected outputs are **hypotheses and deliverables, not promised scores**:

| Possible outcome | What it would support |
|---|---|
| Reconstructed geometry improves held-out PPFD prediction | Evidence that 3D adds practical value for this rig and tested plants |
| Simplified geometry performs similarly at lower effort | Evidence for a simpler calculator |
| Geometry errors dominate predicted shading | A need to improve leaf reconstruction before claiming optical accuracy |
| Predicted differences between LED arrangements match measurements | Evidence for comparing those tested arrangements |
| Two-view predictions remain reliable for selected outputs | A possible route to simpler future operation, with explicit limits |

Do not invent expected accuracy, energy-saving percentages, yield gains, or a numerical “optimal” setting. A result that 3D adds little is still useful.

The plants already have leaves, so geometry/light validation can begin before flowering. Cultivation should continue for repeated observations, but an initial optical result does not require waiting for harvest. Growth, harvest, and flavour benefits need separate longitudinal validation.

Please propose realistic durations, person-hours, dependencies, and stop/go criteria for:

1. Equipment confirmation, physical calibration, and pilot capture.
2. Usable leaf geometry and baseline light-field measurements.
3. Optical model calibration and held-out validation.
4. Calculator integration and measured scenario comparisons.
5. Optional two-view extension and later physiological/growth validation.

Existing documents list September 24 as an implementation target and October 31, 2026 as a conference deadline. Reassess what can credibly be delivered by those dates; do not guarantee a working leaf pipeline or harvest results. Separate a minimum optical feasibility report from later extensions, and identify whether this work supplements or displaces the fruit-focused study.

## 7. Requested response from Claude

Please return:

1. A plain-Korean explanation of the research question and the contribution of 3D.
2. A feasibility assessment separating what can be measured now, modelled with assumptions, and validated only with additional equipment/data.
3. A minimum viable experiment with inputs, capture/measurement steps, controls, baselines, evaluation metrics, and acceptance criteria.
4. A realistic phased schedule with workload and expected results described conditionally.
5. A calculator specification with named inputs/outputs, units, formulas, uncertainty/missing-data behaviour, and the boundary between arithmetic and 3D simulation.
6. An assessment of compatibility with the existing fruit/harvest plan, including unresolved design decisions rather than silently replacing that plan.
7. A prioritized implementation handoff only after the proposed scope is settled. Preserve repository ownership and avoid duplicating existing support tools.

Bundle only the essential unresolved questions: exact cultivar/stage, LED specifications and actual power, quantum-sensor availability, current rig dimensions/plant placement, and available effort. Use existing project information where reliable; mark assumptions explicitly.

Local context, relative to the project root:

- `CONVENTIONS.md`, `AGENTS.md`, and `CLAUDE.md`
- `handoff/LOG.md` and `handoff/TODO.md`
- `handoff/EXPERIMENT_EXPLANATION_AND_TIMELINE_2026-09-16.md`
- `handoff/CLAUDE_CODE_STAGE1_REVIEW_RESPONSE_2026-09-16.md`
- `docs/학술대회_일정역산_2026-09-16.md`
- `docs/촬영당일_체크리스트_2026-09-16.md`
- `build/light-efficiency-calculator.html`

The brief is self-contained if these files are unavailable in Claude's environment. In that case, clearly distinguish the dated status reported here from anything independently inspected.
