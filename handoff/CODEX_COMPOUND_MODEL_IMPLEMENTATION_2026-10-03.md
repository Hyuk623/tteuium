# Compound calculation model implementation

## Request and inspected behavior

The user explicitly requested execution here of CLAUDE_COMPOUND_GROWTH_MODEL_PROMPT_2026-10-03.md. Codex implements permitted tools and tests. No remote job, cross-owner edit, invented observation or biological calibration is authorized. The existing plant_light_bridge is present and will be reused unchanged. Existing structure files contain proposed compound names and fitted visible petiole segments, not confirmed temporal compound identities or whole rachises. These cannot silently initialize a complete observed growth state.

## Implementation contract

Add tools/compound_surface.py for read-only face auditing, one-sided supported area and eligibility; reuse triangle_areas_mm2 and full raster footprint support. Preserve existing reconstruction and require explicit local patch connectivity for folded surfaces rather than flattening them into one chart. Detect duplicate faces and ambiguous intersections, retain per-face reasons and partial completeness. No automatic surface approval.

Add tools/compound_growth.py for explicit CSV observation/axis/extent inputs, immutable source manifests, legacy structure input audit, signed observed-state extraction, persistence and recent-change forecasting, chronological evaluation, new-build exports and an inspectable view. Existing geometry coordinates are board mm; stable frame evidence is required across dates. The recent-change model uses rigid rotation between directed axes, separate parent translation and local shape/extent rates, with a caller-supplied maximum horizon. It is a short-horizon kinematic baseline, not an agronomic law. Missing rates or invalid future dimensions are unavailable, never invented/clipped. Caller-supplied frame/identity evidence and source hashes remain visible.

No new biological curve form, thresholds or growth coefficients will be selected by Codex. A reviewed fitted biological candidate and calibrated uncertainty remain unavailable pending Claude specification and measured data. This is an explicit contract gap in the executable workflow, not a fabricated fitted model. Light study preparation delegates to the existing bridge and gates; forecast envelopes never enter optical transport. Real extraction is attempted read-only against an explicit saved T1 structure, without assigning dates or promoting proposed names.

## Validation

Meaningful tests cover surface area and gaps, duplicates/intersections, full mask support, curved mesh convergence, signed direction, wraparound, axis rotation and parent translation, unequal intervals, missing/ambiguous identity and history, forecast horizon limits, topology/physical consistency, chronological evaluation and plant-group split leakage. Run CLI help, a synthetic end-to-end bundle/forecast/evaluation, the existing light-bridge tests, and a real-input blocker audit. Hash source files before/after. Generated files only under fresh build directories. No changes to legacy source arrays, docs, config, tomato3d, or tests.

## Delivery

Pending implementation and verification.

## Delivery and verified limits

Implemented tools/compound_surface.py, tools/compound_growth.py, tools/compound_growth.html, tools/COMPOUND_MODEL.md and two tests under tools/tests/. Existing modules were imported unchanged; the plant_light_bridge appeared in current files and was reused rather than duplicated.

Final command: python -X utf8 -m pytest tools/tests/test_compound_growth.py tools/tests/test_compound_surface.py tools/tests/test_plant_light_bridge.py tools/tests/test_growth_simulator.py tools/tests/test_plant_traits.py -q. Result: 102 passed in 14.36 seconds, including 36 new tests. Both CLI help commands passed.

End-to-end outputs: build/compound_model_20261003_02/ (the earlier _01 results predate explicit synthetic/reference-status metadata and are superseded for delivery). Reproducer: python -X utf8 build/compound_model_20261003_01/reproduce.py build/<fresh_directory>. It creates synthetic inputs with test-fixture helpers, exercises CLI extraction/forecast/evaluation/surface audit/light preparation and audits the explicit saved real T1 structure read-only.

Synthetic surface: two 50 mm2 triangles plus a reversed duplicate produce 1.0 cm2 supported area; duplicate is excluded with provenance. Synthetic known rotation/elongation has near-roundoff recent-change tip error versus approximately 3.017 mm persistence error at one day. This is one deterministic software fixture, not a biological performance estimate. The reviewed_growth option explicitly returns unavailable; it is not a fitted model.

Real T1: five petiole/region candidates inspected, no confirmed whole-compound forecast state. Source structure and capture hashes unchanged. Missing capture timestamp, confirmed temporal identity, full rachis/attachment, extents, comparable tissue area and stable-frame evidence remain blockers. Capture board/calibration evidence is retained as diagnostic provenance. No dates, IDs or full leaf surfaces were created from legacy proposals.

Existing GroIMP bridge produced a prepared synthetic study through prepare-light, with no native execution. Derived supported surfaces have pending review and partial completeness; no optical gate was promoted. Forecast extent bars are display-only. Browser verification on http://127.0.0.1:8854/recent_forecast/viewer.html confirmed synthetic labeling, one/two-day control updates and no browser errors. Screenshot: build/compound_model_20261003_02/viewer_check.jpg. A hidden localhost-only viewer server remains available; its PID is recorded in that build folder.

Outstanding scientific requirements are explicit: Claude-reviewed fitted growth-law contract/parameters, calibrated prediction intervals, real independent temporal targets and physical light validation. The tools do not infer causal phototropism, parent rotation separately from compound rotation, missing leaf tissue, or a biological curve from the synthetic fixture. Local patch support is conservative interpolation; no new denoising or curvature prior was invented. The executable observation-based baselines are delivered, while full calibrated growth remains unvalidated.
