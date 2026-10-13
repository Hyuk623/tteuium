# P1 prompt for growth observation readiness

Recipient: existing P1 3D reconstruction chat. Date: 2026-10-04.

Review your current P1 outputs against the growth Science handoff and deliver a focused observation-readiness report. This task supports later growth work; it does not authorize a new GPU run, training, remote upload, capture campaign or cross-project adapter.

## Read first

Read the repository working rules, the last five LOG lines and current TODO, then:

- [Science review](CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md).
- [User decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including the 2026-10-04 growth Science addendum.
- [Prompt scope and ownership](CODEX_GROWTH_SCIENCE_CHAT_PROMPTS_INDEX_2026-10-04.md).
- [P1 non-GPU handoff](CODEX_P1_NON_GPU_STATUS_HANDOFF_2026-10-04.md) and [latest trial result](CLAUDE_MULTIVIEW_TRIAL_RESULT_2026-10-03.md). Later trial addenda supersede older pending-GPU statements; inspect current artifacts before making claims.

## Decisions you must preserve

Question 1 is accepted: P3 DLI is incident light at one declared reference plane/position over a complete local day, used at whole-plant model scope. This is not tissue absorbed light or an average reconstructed from leaf area. Question 3 is accepted: P3 DLI coefficients are separate by growth-curve family. Question 2, P4 exchange/respiration/light-face semantics, remains undecided.

The optional reanchor-weight, transient-posture and truss-observable proposals are not adopted. P1 does not choose them. P3 owns realized growth, P4 remains diagnostic and cross-project linking remains deferred.

## Work

1. Write a brief before work and inspect actual current observation outputs. Build a table of field, producer file/function, unit, support, identity, timestamp/frame, evidence artifact and availability for:
   - Plant instance, compound leaf, leaflet/organ and capture/session identities.
   - Observed rachis length, left/right extent arrays and station definitions, supported leaf area and its basis.
   - Attachment, direction, local frame and scale/pose provenance.
   - Measurement confidence/error information actually present, and whether shared pose/scale error can be distinguished from organ-specific error.
2. Separate measured, derived, generated and unavailable information. Per-photo ratios do not establish physical leaf area; generated RGB views do not establish metric optical surfaces. Provisional camera mapping results do not automatically pass geometry or biological gates.
3. For G08, state which data are missing for repeatability-based measurement covariance. For G06, inventory photoperiod-phase metadata if already available; do not invent phase offsets or fit a posture model.
4. For G07, inventory existing dated event records and their actual observation definitions. Do not select visible_bud, infer flowering stage from an image label, or equate visible-leaf count with cumulative node rank.
5. Check whether organ identities and source provenance survive current per-plant/canopy representation and any existing split. Report gaps without implementing a new integration adapter or silently merging measurements.
6. Translate the Science observation requests into a **missing-data checklist**, explicitly labelled as a proposed measurement plan. Do not perform experiments or edit human ground-truth records.

## Deliverable and acceptance

Save `handoff/CODEX_P1_GROWTH_SCIENCE_READINESS_2026-10-04.md` in English with the field table, available evidence, missing inputs, downstream limitations and exact owner of each follow-up. Include stable source/artifact references. If audit tables are generated, use CSV for tabular data and JSON for metadata under a fresh `build/` directory.

This is a read-only implementation audit plus documentation. Verify referenced files and actual schema meanings; do not run unrelated inference or tests. Explicitly report whether P1 can supply supported physical area and longitudinal identity now, without turning absence into zero. Append the outcome to LOG and any actual design questions to the Codex-to-Claude TODO queue. Do not edit P3/calibration/P4 code, biological coefficients, `docs/`, human configuration or observations.
