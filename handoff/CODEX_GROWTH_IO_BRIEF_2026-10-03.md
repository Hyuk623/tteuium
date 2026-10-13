# Codex handoff: 30-day CompoundLeaf forecast

Date: 2026-10-03. Purpose: concise environment/input/output summary. This brief does not start implementation, training or simulation.

Detailed proposed contract: [CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md](CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md). It is not a validated biological model or completed Claude review. Read repository working agreements before changes.

## Objective and current status

Forecast distributions of tomato CompoundLeaf appearance, attachment, direction, extent and growth over 30 days, starting from measured existing leaves.

- Existing: `tools/compound_growth.py` provides observed-state checks and persistence/recent-change baselines; `tools/monthly_growth.py` provides an adjustable assumption-based scenario.
- Proposed: stochastic L-system/graph grammar for events and topology, with correlated continuous growth parameters. No probabilistic implementation is claimed by this brief.
- Flow Matching: disabled until suitable longitudinal data and independent evaluation justify replacing the continuous sampler. It does not generate discrete organ topology or replace measured geometry.
- No supplied cultivar, sowing/transplant dates, growth history or future environment schedule. Keep unknown values explicit and assumptions adjustable; invent no defaults.

## Cultivation environment inputs

These field names already exist in the monthly scenario tool; they are reusable input vocabulary, not validated response laws for the proposed model.

| Field | Meaning | Unit |
| --- | --- | --- |
| `temperature_c` | Air temperature | deg C |
| `relative_humidity_pct` | Relative humidity | % |
| `ppfd_umol_m2_s` | Incident PPFD | umol m^-2 s^-1 |
| `photoperiod_h` | Daily lighting duration | h/day |
| `ec_ms_cm` | Nutrient-solution conductivity | mS/cm |
| `ph` | Nutrient-solution pH | dimensionless |
| `co2_ppm` | CO2 concentration | ppm |

Supply future values as a declared scenario. Environment values affect growth only through explicitly supplied response functions/coefficients. The existing monthly tool records them in manual mode; its optional response-table mode uses assumed multipliers. Do not automatically transfer that product rule to the new model. Calendar time is the proposed baseline; developmental-clock mapping is optional and explicit.

## Other inputs

| Group | Required content / availability |
| --- | --- |
| Origin and identity | Plant, parent-stem and confirmed compound IDs; observation time; stable coordinate frame; source hashes. |
| Existing measured blocks | Attachment and full supported axis points, direction, axis length, left/right extents and shape references. Preserve partial/missing evidence as such. |
| Parent geometry | Directed stem polyline, reviewed attachment correspondence and apex for future attachment XYZ. Missing geometry may permit event counts but not spatial placement. |
| Relations | Confirmed order/adjacency, spacing, relative direction and size. Visible neighbors are not automatically consecutive biological nodes. |
| Optional area | Supported tissue area and comparable coverage basis; estimated total area remains separate. |
| Biological parameters | Residual wait to next appearance, subsequent intervals, stopping probabilities; birth dimensions/directions; remaining expansion/rotation and rates; conditional coefficients and covariance. |
| Parameter evidence | Measured, user-assumed, literature-informed, fitted or unidentified; units, source and applicability. |
| Computation | `horizon_days=30`, explicit `sample_count`, `seed`, `output_days`, numerical tolerances. These are not biological coefficients. |
| Later updates | New observations, association evidence and supported error likelihoods; without a likelihood, re-anchor measurements without claiming Bayesian calibration. |

Units: positions/lengths in mm, area in cm2, time in calendar or explicitly labelled development days, internal angles in radians and directions as unit vectors. Missing values are null/unavailable, never silently zero. One snapshot cannot identify temporal growth rates.

## Proposed outputs

| Files | Content |
| --- | --- |
| `events.csv` | Per-trajectory appearance times, parent/temporary block IDs and appeared/beyond-horizon/stopped states. |
| `block_states.csv` | Time-indexed existence, attachment XYZ, direction, length, left/right extents and optional supported area; observed/predicted provenance. |
| `trajectories.csv`, `trajectory_parameters.json` | Joint sample identities, weights and decoder parameters; retain dependencies across blocks and dates. |
| `summary.csv` | Occurrence probabilities, count distributions and conditional geometry quantiles; do not replace multimodal distributions with a mean plant. |
| `update.json`, `associations.csv` | Confirmed/ambiguous/unmatched correspondences, discrepancies, updated weights or limitations, and new origin reference. Preserve previous forecasts. |
| `evaluation.csv` | Independent scores at supported horizons, including 7/14/21/30 days where targets exist; coverage and failures. |
| `manifest.json` | Input/config/code hashes, model/scenario versions, seeds, units, eligibility and limitations. |

Tables are CSV; configuration/provenance are JSON. Use fresh run directories under `build/`. Forecasts never become observed training ground truth. Future IDs are trajectory-local until supported observation association.

## Reuse, limits and checks

Reuse `tools.compound_growth` extraction/baselines and `tools.leaf_light.common` IO. Preserve `tools.compound_surface` and `tools.plant_light_bridge` eligibility gates. The detailed contract proposes only `tools/probabilistic_compound_growth.py` plus focused tests; inspect current source before adding it.

- Existing measured geometry must be identical at the origin; keep observations immutable.
- Future prediction unit is CompoundLeaf, not generated individual leaflets. The initial model covers provided axes and an explicit retained-leaf scenario, not unrestricted branching/death.
- Block envelopes are not tissue. Future blocks remain `optical_eligible=false` and `suitable_for_ppfd=false`; do not convert spatial probability into opacity.
- Check units/frames, identity, event ordering, within-day births, missing inputs, reproducible samples, output-step independence and update history.
- Evaluate chronologically with independent plant groups. Assumed distributions and synthetic tests do not establish real 30-day accuracy.
- No new UI, renderer, tissue reconstruction, physiology/yield model, cloud service or training campaign.

## Process environment variables

Shared configuration in `tomato3d/config.py` defines `TOMATO3D_DATA_ROOT`, `TOMATO3D_CONFIG_DIR`, `TOMATO3D_CAMERA_ID`, `TOMATO3D_LOG_LEVEL` and `TOMATO3D_MAX_WORKERS` for paths, camera identity, logging and worker count. These are not cultivation variables. They apply where code uses `get_settings()`; do not assume every standalone growth CLI consumes them directly. Keep protected source/configuration and human measurements read-only.
