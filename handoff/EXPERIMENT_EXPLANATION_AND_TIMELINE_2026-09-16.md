# Tomato phenotyping experiment: explanation, expected outcomes, and timing

Date: 2026-09-16
Prepared by: Codex, in response to the user's request to explain the complete cultivation and 3D analysis experiment.

## Status and authority

**New user-confirmed information:** the plants are still young and have no flowers. The project notes describe 12 plants in one shared growing environment. The exact cultivar, sowing date, current leaf stage, and first flowering date are not available.

This is an explanatory handoff, not an implemented protocol change. It distinguishes the existing documents from proposed adjustments required by the newly confirmed growth stage. No design, operational configuration, or pipeline file was changed. Entries and instructions in reviewed documents were used as context, not fresh authorization to implement them.

The current schedule document records a 2026-09-24 implementation milestone and a 2026-10-31 conference deadline. Its assumption that fruit-bearing plants can immediately supply fruit sequences does not describe the user's current plants. The conference should therefore be treated as an interim reporting date, with harvest validation conditional on actual fruit development.

## 1. What the experiment tests

The core question is whether repeated, calibrated 3D measurements improve growth monitoring and prediction enough to justify their capture and processing cost, compared with top-and-side RGB measurements of the same plants.

The chain is:

**Grow identified plants -> capture the same plants repeatedly -> estimate geometry and colour -> check against independent measurements -> track changes -> predict a later observation -> check the prediction when that observation occurs.**

Three tests have distinct outcomes:

1. **Measurement validity:** can the low-cost camera/board rig recover useful dimensions consistently?
2. **Value of 3D:** does multi-view analysis improve dimensional accuracy, visibility, and identity tracking relative to two-view analysis?
3. **Value of temporal modelling:** does a small sequence model improve prediction over simple baselines, using only information available at prediction time?

The longer-term goal is to train a two-view estimator using verified multi-view reference data. That is a separate development and validation step. Multi-view 3D is an estimated reference, not automatically ground truth. Anything hidden in all views remains unobserved; a model's inferred completion must be identified as such.

This initial study is a longitudinal measurement/model-validation experiment. Twelve plants sharing one environment do not provide twelve independent environmental treatments. It cannot establish the effects of nutrient deficiency, light treatment, pruning, or fruit thinning without a separate treatment and reference-label design.

## 2. Existing acquisition setup

- Plant IDs remain stable across dates, for example DT-001 through DT-012.
- Existing cultivation notes specify dwarf cherry tomatoes, vermiculite, and bottom watering. The exact cultivar and suitability of the growing setup remain matters for the user/design owner.
- The operational board is the 7x7 ChArUco print, 190x190 mm on A4, with 190/7 mm cells. The 5x5 print is a spare with different geometry.
- The board and plant rotate together. The camera remains fixed for the side sequence and then moves to the overhead jig.
- The documented pilot uses 36 side images at 10-degree increments, plus five top images T0-T4. T0 is the future operational top view.
- The latest checklist adds one empty-rig image: **41 plant images plus one reference image = 42 files per full session**. Camera calibration images are additional and are not included in 42.
- A measured reference block checks geometric scale; a colour chart supports RGB consistency. Neither replaces manual validation of the plant/fruit traits.

Before repeated capture, measure the physical print, measure the reference block, and calibrate the camera using at least 20 board images spanning useful positions and orientations. Keep lens, zoom, focus, image resolution, exposure, and white balance consistent with the validated capture procedure. Preserve originals instead of using resized messenger exports.

One plant session consists of positioning the pot consistently, taking the side sequence after motion settles, taking T0-T4, checking sharpness and visible reference features, and recording measurements/events. The current settling interval is five seconds after rotation. A single empty-rig image does not by itself guarantee valid background subtraction for all camera poses.

## 3. What to record over time

| Timing | Record | Purpose |
|---|---|---|
| Every capture, provisionally every two days | Original images, camera/session metadata, plant height, canopy width, visible leaf/flower/fruit counts as applicable | Relate image-derived measurements to the same physical state |
| Daily quick observation | First visible bud, first open flower, fruit set, colour break, harvest, loss/removal | Date biological events between full capture sessions |
| Daily, three fixed times under the current manual plan | Air temperature and relative humidity | Environmental context and approximate daily summaries |
| Daily at the same time | Nutrient-solution EC, pH, water level; replenishment notes | Record management and solution conditions |
| At initial setup and after relevant changes | Shelf position, PPFD at plant/canopy position, lighting schedule | Explain positional and light-exposure differences |
| At harvest, retaining fruit identity | Caliper dimension, mass, and water-displacement volume when practicable | Independently validate fruit geometry and derived density |

Before flowering, fruit count is an observed zero, while per-fruit volume and time-to-harvest are not yet available. A missing observation must not be encoded as a measured zero. If an event is only checked every two days, record its observation interval rather than inventing an exact event time.

Three spot temperature readings do **not** establish the true daily maximum/minimum or night mean. GDD computed from those approximations must be labelled approximate; the standard max/min form needs actual extrema. See the [MRCC GDD definition](https://www.mrcc.purdue.edu/resources/growing-degree-day-description). Likewise, PPFD multiplied by photoperiod gives DLI only when the PPFD at the measurement location is sufficiently constant. Growing canopy height, shading, or changed positions can invalidate a one-time light measurement.

Mass divided by volume gives density; images alone do not independently measure mass. Fruit colour is an appearance/ripeness indicator, not a direct taste or sugar measurement. Claims about sweetness would require their own measurements and validation.

## 4. Processing and outputs

**Stage 1: camera geometry and foreground.** Detect ChArUco features, solve the pose of each view, check input/calibration compatibility, and separate the plant from non-plant regions. The board supplies metric geometry; the colour chart helps standardize appearance.

**Stage 2: 3D reconstruction.** The documented architecture combines silhouette-based volume constraints with scale-aligned monocular depth estimates. It does not estimate camera motion using SfM. Depth inferred from RGB is a model estimate and must be checked against known geometry. A silhouette envelope can contain empty spaces between leaves; its volume must not be labelled plant tissue volume or biomass.

**Organ analysis.** Associate visible fruit regions across views, recover dimensions where coverage supports them, and keep identity across dates. Whole-plant point clouds and individually reconstructed fruit surfaces have different validity requirements. An incomplete fruit surface should not silently become a measured closed volume through arbitrary hole filling. Manual correction is acceptable in a feasibility study if its extent and time are reported.

**Temporal analysis.** For each plant, and later each fruit, build a time series with measured or estimated traits, timestamps, observation status, and uncertainty. Use actual time intervals, including missed capture days.

**Prediction.** The more recent schedule proposes predicting the next fruit state, such as size and colour, before treating harvest date as a derived outcome. The earlier RNN memo still lists days-to-harvest as the primary target; these are different tasks and the owner must reconcile them. With the user's present non-flowering plants, the immediate data support geometry and vegetative growth observations. A vegetative next-state model would be a proposed additional scope, not an already approved replacement for the fruit model.

After fruit set, three or four observations can exercise the data/training pipeline. That does not establish useful predictive accuracy. A model trained only on early green fruit cannot be claimed to predict the later colour transition or harvest reliably without suitable training and validation examples.

## 5. Fair comparisons

The most interpretable comparison uses **the same plants, dates, target traits, and independent reference measurements**:

| Method | Inputs | Role |
|---|---|---|
| Simple temporal baseline | Latest observation, or a recent linear trend | Tests whether a learned sequence model is necessary |
| Two-view model | T0 plus one consistently selected side image; available past environmental context | Represents the intended simple capture workflow |
| Multi-view model | Matched multi-view measurements plus the same environmental context | Tests the incremental value of geometry/visibility |

Compare lengths with lengths and volumes with volumes. Raw 2D pixel area and 3D volume are different targets. If a 2D method estimates volume through a shape model, disclose that assumption. A predicted future 3D volume compared only with a later reconstructed volume measures agreement with the reconstruction pipeline, not independent physical truth.

Report dimensional errors in mm, volume errors in cubic centimetres and relative error where meaningful, count/identity errors, repeatability, failed-session rate, capture time, processing time, and correction time. Existing Stage 1 thresholds include pose-solved ratio at least 95% and mean reprojection error at most 1 px; these do not imply millimetre-level reconstruction accuracy. Physical-error acceptance limits still need to be set before judging the final evaluation data.

Keep all fruits and dates of a plant in one data split. The existing 8/2/2 plant split is an exploratory option, but two held-out plants provide a very uncertain performance estimate. Also report per-plant outcomes or use appropriately grouped resampling. Do not leak future measurements, held-out teacher labels, normalization statistics, or harvest mass into earlier predictions.

The document's optional six-plant 3D plus six-plant two-view arrangement saves capture work, but only the six fully captured plants support a paired 3D-versus-2D comparison. The other six do not automatically provide 3D training examples. Large frame counts and overlapping temporal windows are not independent biological replicates.

## 6. Expected results: hypotheses, not promised scores

| Result | Reasonable expectation to test | Outcome that would limit the claim |
|---|---|---|
| Reference dimensions and plant extent | Consistent calibrated geometry across captures | Board occlusion, unstable focus, foreground loss, or motion dominates errors |
| Fruit visibility and identity | More views may reveal fruit hidden in the operational pair and reduce duplicate counts | Fruit hidden in every view remains unknown; association can still fail |
| Shape/volume | Useful geometry when the relevant surface is sufficiently observed | Incomplete surfaces or noisy depth create biased volumes |
| Colour/ripening state | Standardized RGB may carry strong appearance information without much 3D benefit | Lighting or chart calibration variation resembles biological change |
| Next-observation forecast | A temporal model may use growth history better than a static image | With little data, persistence or a linear trend may outperform an RNN |
| Two-view operation | Selected visible traits may retain acceptable accuracy at much lower capture cost | Hidden-organ quantities may need lower confidence or abstention |

Multi-view tomato research provides a rationale for testing visibility and geometry, not a transferable performance guarantee. For example, [a multi-view fruit-tracking study](https://doi.org/10.1016/j.biosystemseng.2023.06.003) still reports degradation under occlusion. Its rig and data differ from this experiment.

Illustrative output format only: "Fruit F03: estimated current major axis 12.0 mm; predicted major axis at the next capture 12.8 mm; compare with the next observation." These numbers are invented solely to explain the output format. No forecast or accuracy result has yet been produced for the user's plants. Prediction intervals require their own calibration; they must not be invented.

Expected deliverables are a dated image dataset, independent measurements/events, validated example point clouds, measurement-error and repeatability plots, a view-count versus error/time comparison, growth trajectories, and a baseline-versus-model comparison when enough relevant observations exist. An honest result that 3D adds little for a particular task is useful evidence for a simpler product.

## 7. Duration and calendar

### Interim report: 45 elapsed days to 2026-10-31

This adapts the existing calendar to the user's current seedlings. It does not guarantee flowering, fruit set, successful reconstruction, or RNN performance on those dates.

| Window | Work | Evidence expected by its end |
|---|---|---|
| September 16-19 | Physical setup, print/block measurements, calibration, seedling pilot, foreground corrections | A demonstrated valid capture-and-measurement path or explicit remaining blockers |
| September 20-24 | Begin repeated capture; develop the reconstruction prototype in parallel | First usable reconstruction examples if quality permits; September 24 remains a target, not verified readiness |
| September 25-October 12 | Continue every-two-day capture and daily event/environment records | Vegetative trajectories, and flowering/fruit data only if actually observed |
| October 13-19 | Freeze an interim analysis set; compare 2D/3D measurements and repeatability | Physical-error and workload comparisons |
| October 20-26 | Fit simple baselines; evaluate a small sequence model only for adequately observed targets | Measured held-out errors, or an explicit insufficient-data result |
| October 27-31 | Prepare the conference report | Interim results, limits, and the continuation plan |

Freezing the interim analysis set is not stopping cultivation or subsequent recording. If fruit data arrive after the cutoff, retain them for the next analysis rather than retroactively changing the test set.

September 20 to October 12 inclusive at two-day intervals gives **12 capture dates**, not 11:
September 20, 22, 24, 26, 28, 30; October 2, 4, 6, 8, 10, 12.

For 12 plants receiving every full session, that is **144 plant-sessions and 6,048 image files** (5,904 plant views plus 144 empty-rig references). This count excludes initial calibration, repeatability captures, retries, and later continuation. The schedule document's 3.2-hour estimate per full capture day would imply **38.4 hours** for these 12 dates, before additional annotation and analysis. It is a planning estimate to replace with actual pilot timing.

The initial 36-view acquisition allows 12-, 18-, and 36-view subsets to be tested without new shooting. Eight equally spaced 45-degree side views cannot be selected exactly from a 10-degree grid; record approximate angles or acquire that condition separately. Choose a reduced count from measured error/time tradeoffs. Do not automatically equate more images with better results.

### Harvest-inclusive continuation: tied to first flowering

**Remaining time to flowering + a provisional 6-9 weeks after flowering + 1-2 weeks for analysis** is a conservative planning scenario, not a cultivar-specific forecast.

Relevant primary studies show why the event and endpoint matter: one Micro-Tom experiment reported breaker stage at roughly 30-35 days after anthesis ([Musseau et al., 2017](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2017.00988/full)); another reported approximately 53.4 days from anthesis to ripe fruit for its Micro-Tom control ([Carvalho et al., 2011, Table 3](https://link.springer.com/article/10.1186/1746-4811-7-18)). These are different endpoints and growing conditions. They do not identify the user's unnamed cultivar or guarantee its timing.

Illustrative calendar using the 6-9-week planning allowance:

| Hypothetical first open flower | Provisional harvest-observation window |
|---|---|
| September 25 | November 6-27 |
| October 1 | November 12-December 3 |
| October 10 | November 21-December 12 |

For an October 1 first flower, allowing another 1-2 weeks for analysis yields approximately **November 19-December 17**, or about **9-13 weeks from September 16**. These are conditional planning dates. Failed fruit set, a later first flower, and slow ripening extend them; faster development can shorten them. One harvested fruit is only a case study, so stop criteria also need enough independently tracked fruit/plant outcomes for the intended claim.

No actual harvest means no validated harvest-date prediction. Observations that end before harvest are incomplete follow-up, not zero remaining days and not fabricated harvest labels.

## 8. Current implementation and scope limits

The latest Claude Code response reports fixes for Unicode IO, image-resolution mismatch, and stale outputs, plus 116 passing tests. This explanatory session did not rerun those new tests. The top-view foreground problem remains open: the interim code withholds top masks and gates training use. The operational block height is still null and physical print verification is false in config. Inspection also found reconstruction and two-view model entry points still marked unimplemented.

Thus, the pipeline described above is the intended experiment, not a claim that every stage currently works. The first technical milestone is to demonstrate valid masks and real-image metric reconstruction while preserving the dated raw captures for later reprocessing.

Deficiency identification, elongation-disorder diagnosis, pruning/thinning locations, and improved flavour remain longer-term objectives. This initial cohort does not supply validated labels or intervention outcomes for all of them. If the conference remains fruit-only, the lack of current flowers is a substantial scope/schedule dependency to resolve with the design owner; a seedling measurement study is a proposed interim alternative.

## 9. Local source documents

- `docs/학술대회_일정역산_2026-09-16.md`
- `docs/학술대회_RNN_설계메모_2026-09-16.md`
- `docs/파일럿_촬영_프로토콜_2026-09-15.md`
- `docs/촬영당일_체크리스트_2026-09-16.md`
- `config/board_spec.json`, `config/capture_config.json`, `config/quality_thresholds.json`
- `handoff/CLAUDE_CODE_STAGE1_REVIEW_RESPONSE_2026-09-16.md`

Outstanding owner decisions: exact cultivar/age, how the current seedling cohort changes conference scope, the harvest endpoint, physical-error acceptance criteria, the capture allocation across 12 plants, and a valid top-view foreground method. The original design documents were left intact.


## Addendum: RGB-to-3D and photosynthesis-related feasibility

User follow-up, 2026-09-16: asked whether 3D reconstruction from 2D photos is possible and whether photosynthetic efficiency could be studied.

Ordinary RGB photographs can support 3D reconstruction. Image dimensionality (2D) is different from the number of views. A single image leaves major depth/occlusion ambiguities; two calibrated views constrain jointly visible corresponding features but do not reveal all hidden leaves; multiple overlapping views provide more constraints. Learned completion remains an estimate requiring metric and biological validation. The project's planned multi-view acquisition already uses 2D photos to estimate 3D.

A useful research direction to discuss is leaf-level light interception. Leaf positions, areas and surface orientations, together with the LED geometry and measured photon flux distribution, can support a light-distribution simulation. Absorbed light additionally depends on leaf optical properties. A whole-plant silhouette envelope is insufficient to accurately model light passing through gaps between leaves. Recover relevant leaf surfaces, or disclose simplified/manual leaf geometry and test its sensitivity.

This is a feasible modelling concept used in tomato research: [Integrating Morphological and Physiological Responses of Tomato Plants to Light Quality to the Crop Level by 3D Modeling](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.00839/full). Its findings are not performance estimates for this dwarf-tomato rig.

Keep the quantities separate: incident/absorbed light, PSII photochemical efficiency, net CO2 assimilation, and biomass gained per absorbed light are different outcomes. RGB shape/colour alone does not directly measure physiological efficiency. Chlorophyll fluorescence instruments support PSII-related measurements; gas exchange supports CO2 assimilation measurements. See [LI-COR's measurement principles](https://home.licor.com/env/support/LI-6800/topics/introduction.html). A physiological model can estimate assimilation only with additional parameters and validation; it does not turn ordinary RGB into a direct photosynthesis measurement.

Suggested bounded feasibility study for discussion: reconstruct visible leaf geometry, characterize the existing LED light field, simulate light distribution, and compare predicted PPFD against independent measurements at accessible matching locations/orientations. Then simulate alternative LED positions or plant spacing. If equipment is available, separately validate physiological response on matched leaves. Seedlings already have leaves, so the geometric/light-distribution study need not wait for fruit or harvest. Long-term growth or yield benefits still need longitudinal testing.

This direction would add leaf-geometry work to the current fruit-focused conference scope, and the top-mask/reconstruction limitations remain relevant. No scope change, treatment intervention, or software implementation was performed by this explanation.


## Addendum: interactive light-use calculator concept

User asked whether a light-efficiency calculator could be built around the 3D leaf/light-distribution study. A small in-conversation calculation example was created at `build/light-efficiency-calculator.html`; it is not connected to actual plant images, 3D reconstruction, or sensors. Every default is an illustrative input, and the whole-plant absorbed-photon fraction is explicitly an assumption.

The example distinguishes a point-level daily light integral from whole-lighting-system quantities:

- Point DLI = constant point PPFD * photoperiod_hours * 3600 / 1,000,000, in mol/m2/day.
- Daily LED electricity = actual input_power_W * photoperiod_hours / 1000, in kWh/day.
- Whole-plant absorbed photon flux = LED PPF * assumed_absorption_fraction, in micromol/s.
- Absorbed photons per electrical energy = absorbed photon flux / input_power_W, in micromol/J. This equals fixture photon efficacy multiplied by the fraction of emitted photons ultimately absorbed by leaves. It is not physiological photosynthetic efficiency.

Definitions: [MSU lighting efficacy explanation](https://www.canr.msu.edu/floriculture/uploads/files/lighting-efficacy.pdf) and [Apogee DLI measurement](https://www.apogeeinstruments.com/daily-light-integral-measurement/).

A real 3D extension would replace the absorption assumption with a validated optical model using leaf geometry/optical properties, luminaire position and emission distribution, and relevant reflective surfaces. Keep spectral bands and source boundaries consistent; do not count a reflected photon as newly emitted or repeatedly sum intercepted light as absorbed light. One PPFD value or rated watts alone cannot determine leaf-level illumination or whole-plant absorption. Simulations could compare leaf-area-weighted light distribution, absorbed photons per joule, and energy use for lighting arrangements; biological targets and photoperiod constraints require separate validation.

The live arithmetic was checked by executing the fragment script with DOM stubs: default values, changed absorption/power, zero photoperiod, blank inputs, negative PPFD, and out-of-range hours. No real plant performance, optimal setting, or physiological gain was computed. No project design/config/pipeline files were changed.
