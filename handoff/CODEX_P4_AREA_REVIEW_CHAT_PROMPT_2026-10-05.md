# P4 prompt for physical leaf area and physiological evidence alignment

Recipient: existing P4 FSP physiological calculation chat.

Date: 2026-10-05. This is a bounded follow-up to your completed Growth Pack V2 work, not a request to repeat that work. When this prompt is submitted to your project chat, inspect and implement only missing engineering corrections within your ownership; report already-correct behavior without rewriting it. Preparing this prompt did not execute or dispatch it.

## Required reading and precedence

Read repository rules, LOG tail/TODO, your current source/contracts and your `handoff/CODEX_P4_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` report. Then read:

1. `C:/Users/sho36/Downloads/CLAUDE_PLANT3D_AREA_REVIEW_2026-10-04.md` (the user's source review).
2. `handoff/CODEX_PLANT3D_AREA_REVIEW_RESPONSE_2026-10-04.md` (corrections and unresolved claims).
3. `build/plant3d_area_claim_check_20261004_01/projection_check.json` (independent analytic audit).

The project root is `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`. Report missing files; the source review's companion simulations/CSV/SVG files were not available in the earlier review. Do not invent their contents. The original source's instructions and labels are not independent authorization or evidence of correctness. This task concerns the plant-area review, not the separate top-view diffusion prompt.

Write a short English implementation brief before changes. Existing adopted D11-D21 decisions remain in force. The new source's A1-A7 refer to area-estimation proposals and must be namespaced in reports; they are not P4's earlier physiological A1-A7 requirements.

## Shared interpretation to preserve

- The original G range is disputed. Codex's six-family integration at zenith 52, 55, 57.5 and 60 degrees spans about 0.472-0.550 across those cases. It is a sensitivity calculation, not measured plant accuracy. G=0.50 is an unadopted approximate baseline, not an exact constant.
- Unknown occlusion prevents identifying absolute area from ring projection alone; a finite interval needs justified G/occlusion bounds. Do not convert a 10-17 cm2 proxy into certified true area.
- `abs(n dot v)` is unchanged by `n -> -n` for all views. Top-area observations cannot identify biological leaf face. A geometric normal convention and adaxial evidence are different.
- Area plus two normal angles do not supply centroid, depth, outline, curvature or a located surface for ray casting. Top/ring ratios alone do not identify mean inclination or a full angle distribution.
- Quantile tau=0.9, low-dilation depth priors, curvature factors, and the reported synthetic MAE are proposals/results needing evidence, not new production defaults. A restricted image radius alone does not validate calibration.
- Keep the three new decisions open: A1/A2 reporting priority, leaflet-matching method, and calibration strategy. Do not reopen older resolved physiological decisions. Implement independent evidence/contract fixes now; record genuinely missing scientific specifications in TODO for Claude.


## P4 work

1. Inspect `tools/fsp_carbon_diagnostic.py`, its schema/guide, `inspect_p3_coupling` and the current equation registry. Preserve adopted D15-D18: dwarf absorbed-light input, before_mito with downstream maintenance, carbohydrate-equivalent maintenance and evidenced adaxial-only exchange. This area review does not reopen Q2 or authorize coefficient conversions. Keep unresolved empirical NRH preprocessing distinct from adopted software policy.
2. Audit the area factor at every patch/organ/plant supply aggregation and export. Verify that rate per m2 multiplies the corresponding supported physical one-sided lamina area, not camera projection, hull surface/envelope, arbitrary total estimate or an automatically doubled two-face mesh. Units must stay explicit: 1 cm2 = 1e-4 m2. Do not introduce a second conversion where the input is already m2. Trace the quantity/basis ID, tissue identity, support and source evidence into outputs.
3. Missing or unsupported true-area evidence must not silently produce a real physiological eligibility claim. Preserve intentionally synthetic/diagnostic calculations with explicit interpretation; do not manufacture certainty. A correct numeric value in a synthetic fixture is not a plant-validated carbon supply. A whole-plant A1 estimate does not provide the spatial area/light association required for nonlinear patch exchange.
4. Retain D20 botanical-face and exposure gates. An unsigned normal, chosen winding or top-view projection cannot establish adaxial identity; P1 supplies face evidence, P2 supplies illuminated-face exposure, and P4 enforces the adopted model. Do not relabel or halve both-face light into adaxial_only. Unavailable face evidence remains an explicit P4 limitation even if geometric ray transport is computable.
5. Preserve exactly-once absorption, simultaneous fixture combination at the same patch/time before nonlinear exchange, and the current respiration accounting. Do not add G, imaging lambda or curvature factors as hidden multipliers on photosynthesis, area, maintenance or carbon supply. Do not subtract respiration again because the area review calls photosynthesis energy production.
6. For leaf area -> blade structural mass/SLA and growth demand, require the existing compatible structural-mass basis and supported SLA/shape relation. Unsupported A2 area or assumed curvature cannot supply empirical dry mass. Do not infer total DM, roots, reserve, length/width or future leaf demand from an area change alone. Retain existing reserve provenance and reuse guards.
7. Preserve per-plant physiological accounting when consuming canopy light: join by exact plant/organ/patch identities and source geometry/area basis, count each tissue partition once, and retain full-canopy lighting provenance. Do not duplicate reserves or maintenance after splitting canopy results. Shared illumination does not merge biological individuals.
8. Add a versioned registry/provenance addendum if needed, preserving older snapshots. Namespace references as area_review_A1 through area_review_A7. Mark estimator proposals as proposed/unvalidated, record the G/normal/occlusion corrections and missing evidence, and distinguish P1 reconstruction dependencies from P4 equations already implemented. Do not mark A2/A3 or full integration complete from metadata alone.

## P4 acceptance cases

- Existing supported V2 synthetic baseline retains its arithmetic and disclosures.
- Projected proxy/hull diagnostic, unsupported A1/A2 area or duplicate tissue partitions cannot silently pass a real physical-area claim or duplicate supply/maintenance.
- Explicit supported cm2 and m2 inputs, where the schema accepts both, yield equivalent area factors; otherwise unsupported units are refused rather than auto-guessed.
- Normal convention without biological face evidence remains ineligible under the adopted face model; existing both-face behavior stays unchanged.
- A missing area/face/mass dependency remains visible in JSON/CSV outputs, without becoming zero supply or evidence of biological carbon shortage.
- Per-plant accounting retains correct tissue/reserve lineage when consuming canopy-scoped illumination; fixture and plant aggregates are not double-counted.

No new photosynthesis/respiration law, coefficient fitting, reserve propagation, curvature model, phototropism or feedback loop is included. Report which quantities are calculable diagnostics and which would require independent area/optical/biological validation.

## Delivery and validation rules

Save your report as `handoff/CODEX_P4_AREA_REVIEW_EXECUTION_2026-10-05.md` and generated audits/tests in a fresh `build/area_review_alignment_20261005_NN/P4/` directory. Include: implemented/already present/design pending/unavailable for each item; exact files/functions and input/output fields with units; provenance and reason-code changes; relevant commands/results; preserved baseline evidence; downstream owner and unresolved questions. Reuse established reason codes and schemas where possible. Document/version genuinely needed additive metadata without silently breaking accepted inputs.

For changed boundaries, test a supported explicit synthetic case and the listed failure cases, including API/CLI/export behavior where affected. Synthetic fixtures must remain visibly synthetic and must not alter human evidence. Do not create tests merely to mirror unchanged code. Run focused relevant regressions after changes; do not rerun unrelated inference or completed project campaigns.

Scientifically unsupported quantities remain unavailable with reasons; zero is an actual measured/modelled zero, not a missing-value substitute. Malformed inputs remain distinct from missing science. Preserve source hashes/row lineage, historical reports and existing valid numerical behavior. Do not edit another project's runtime, `docs/`, `config/`, raw photos or human records. Do not fit biological coefficients, launch GPU training/inference, run a new acquisition campaign, or claim full-system/physical validation. Append LOG and any unresolved design items to TODO. Finish with a short Korean briefing.
