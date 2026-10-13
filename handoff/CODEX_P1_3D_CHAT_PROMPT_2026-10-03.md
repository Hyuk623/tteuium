# P1 3D reconstruction continuation prompt

Target chat: **3d구현**

Date: 2026-10-03. This is a paste-ready continuation prompt for the named project chat.

Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.
All paths below are relative to this root unless stated otherwise.

Read the parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, the last five lines of `handoff/LOG.md`, and `handoff/TODO.md` first. Create an English work brief before implementation. Respect file ownership and active OneDrive edits: Codex owns `tools/` and `tools/tests/`; protected core changes belong to Claude Code. Do not edit human configuration, observations or `docs/`. Record specification conflicts for Claude rather than inventing a scientific decision.

Read [the integration decisions](CLAUDE_FOUR_PROJECT_INTEGRATION_DECISIONS_2026-10-03.md), including D1-D10. The latest explicit decisions take precedence over older proposals; the Science review was not adopted in full. Inspect current source and execution records before repeating work.

Shared boundaries:
- P3 owns realized growth increments and future geometry. P4 is a read-only carbon diagnostic at runtime.
- Cross-project linking remains deferred under D3. Continue this project's own work; do not launch an end-to-end pipeline.
- An explicitly selected, frozen and hashed calibration pack may be applied before P3 runs under D5; never fit or apply it implicitly at runtime.
- The first later synthetic pass requires numerical P1-P2-P3 results. P4 may be unavailable with reasons under D6.
- Round-trip checks apply to reversible units, frames, IDs and representations. Light transport, aggregation, photosynthesis and forecasting require forward correctness checks, not inversion.
- Preserve source samples, complete shapes, identity, uncertainty, missingness and provenance. Follow each producer's actual missing-value contract rather than replacing unknown values with zero.

Continue work already authorized in this chat. A missing prerequisite should block only dependent work. Do not treat this prompt as permission for new private-data uploads, paid services, training or cross-chat messaging. Finish with an English handoff and a Korean explanation, distinguishing implemented software, synthetic evidence, scientific assumptions and remaining dependencies.

## Objective and source documents

Complete the current observation and image-completion work while preserving a trustworthy future geometry interface. D8-D10 change P3; they do not authorize P1 to predict new leaves or install growth equations.

Read:
- [Detection and diffusion handoff](CLAUDE_DETECTION_DIFFUSION_HANDOFF_2026-10-03.md).
- [Leaf area handoff](CODEX_LEAF_AREA_QUICK_HANDOFF_2026-10-03.md).
- [Four-project environment and IO inventory](CLAUDE_FOUR_PROJECT_ENV_IO_HANDOFF_2026-10-03.md).

## Required work

1. Audit the current observation baseline. Keep saved-mask pixel area, explicit bounding-box proxies, dimensionless first-label area ratios, projected metric area and actual tissue surface area distinct. The first saved label is the reference; do not substitute another leaf silently. Per-photo detections are not unique physical leaves.
2. Preserve measured geometry and the recorded camera/board frame. Camera pose must follow the existing ChArUco contract; nominal turntable angles and generated views cannot supply measured poses or metric scale.
3. Inspect the existing completion runner, request preparer and packager in `tools/multiview_completion.py`, `tools/completion_viewfusion.py` and `tools/completion_package.py`. Continue that implementation rather than adding a second pipeline.
4. Keep completion output typed as `novel_view_rgb`, with `origin=generative`, `validated_metric=false` and `suitable_for_ppfd=false`. Generated pixels are visual hypotheses, not measured hidden anatomy, new growth observations or accepted optical meshes.
5. Review the two trial arms for a common target/evaluation contract. The prior handoff reports different target azimuths and failed pose gates. Do not score unmatched views as a controlled comparison or leak side-image information into the top-only arm. If the scientific evaluation rule is still unspecified, request an exact Claude contract and continue independent packaging checks.
6. Reuse the existing permission for public pretrained models in this comparison. Resolve the pending GPU destination/private-photo transfer choice only if it remains unanswered. Do not reopen an already settled permission. Validate the isolated runtime, checkpoint compatibility and actual memory requirements before the bounded trial. Preserve every declared seed and genuine failures.
7. Inventory the existing geometry export fields needed later: plant/source/instance identity, compound and leaflet associations, capture timestamp, units, coordinate frame, area basis, geometry hash, visibility, confidence and optical eligibility. Report missing fields or associations without fabricating them.
8. For future canopy composition, preserve source identity and invertible instance transforms. Distinguish duplicate placements of one source plant. Splitting a canopy must recover each instance's mapping and supported geometry; it cannot reconstruct information lost by aggregation. Review the existing contract now; do not implement a cross-project adapter under this task.

## Validation and delivery

Use focused existing tests and fresh generated outputs under `build/`. Verify immutable source inputs, reference-label behavior, held-out image isolation, bundle hashes and availability flags. Claim an actual model trial only after genuine candidate bundles have been returned and inspected. Visual plausibility does not validate metric or optical accuracy.

Deliver a new English P1 continuation report in `handoff/` with changed files, commands, evidence paths, input/output fields and units, actual trial status, unmet geometry gates and the exact remaining owner dependencies. Append a LOG entry and update relevant TODO items. Do not claim integration readiness while accepted geometry is missing.

