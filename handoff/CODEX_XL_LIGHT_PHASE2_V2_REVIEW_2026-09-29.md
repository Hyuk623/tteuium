# Codex review: XL light Phase 2 v2

Date: 2026-09-29
Request: Check Claude's latest Phase 2.

Scope: inspect the v2 handoff, implementation and saved four-plant outputs; run focused tests and bounded input probes. Preserve existing source/configuration/results. No training, remote push or full simulation rerun. Record confirmed findings and their effect on synthetic versus measured-scene use below.

## Outcome

The synthetic, display-only Phase-2 integration is supported by the saved artifacts and focused tests. The real-LightScene path is not ready to publish absolute PPFD. Do not describe all five preparation gaps as fully closed.

### Verified improvements

- All four pinned exports and all twelve generated RGG files match their recorded hashes; completion markers exist in all saved GroIMP logs.
- Each plant has 25 sensor rows. The current synthetic outputs correctly leave absolute predictions unavailable.
- PositionMarker and AxisSegment display geometry is replaced by non-optical nodes in the optical copy, with organ IDs retained. Optical/empty ratios differ from one only by floating-point roundoff (maximum about 4.4e-16); displayed ratios of 1.00000 are justified.
- Sensors are now horizontal Parallelograms rather than boxes. The saved runs compare these against the Python plane calculation.
- sensor_predictions.csv and validation.csv now exist. No measured validation scores were invented.
- Focused tests rerun: 23 passed. No GroIMP simulation was rerun in this review.

### F1 — High priority: partial measured status publishes absolute predictions

Locations: tools/groimp_light_scene.py:137–140 and :265.

`lamps_from_scene` checks only fixture centre and photon flux status. It ignores other inputs used to compute emitter positions, including length/width/orientation, and ignores plant origin/yaw status. Incomplete fixtures are skipped without preventing remaining fixtures from making the scene `measured`.

Reproduction: copied the existing example into an isolated build fixture, changed only lamp centre/flux statuses to measured, and left placement, dimensions and orientation assumed. The function returns `lamp_status=measured`. A mocked build then writes a numeric `predicted_ppfd_umol_m2_s` instead of unavailable. The mock sensor value is not a physical result.

Required correction: derive eligibility from all consumed physical inputs and missing fixtures; preserve each reason that prevents absolute reporting. Add regressions for mixed provenance and an incomplete additional lamp.

### F2 — High priority: unsupported LED distribution is only a note, not an output gate

Locations: tools/groimp_light_scene.py:135–136 and :265.

The input's directional cosine-power distribution is replaced by an isotropic PointLight. `distribution_note` says absolute values are not comparable, but does not prevent a numeric absolute prediction. The Python comparator also receives the isotropic replacement, so agreement between these two paths cannot detect the omitted original LED distribution.

The same bounded probe above retained cosine exponent approximately 1 and produced both the warning and a numeric absolute prediction. Until a matching distribution/aim/cutoff is implemented, explicitly mark this as an assumed surrogate and keep the contract absolute column unavailable (or reject this mode). Parameter-status validation alone does not solve this issue.

### F3 — Medium priority: acceptance formula allows an extra one percentage point

Locations: tools/groimp_light_scene.py:301 and :307.

The stated check is `3*sigma + 0.005`. The implementation divides error by `(sigma + 0.005)` and compares against 3, allowing `3*sigma + 0.015`. For sigma=0.01 and relative error=0.04, the code accepts even though the named threshold is 0.035. Align the equation with the stated criterion and add a boundary test. This is a criterion mismatch; it does not by itself invalidate the currently saved low-error synthetic runs.

### Remaining scope limits

- Sensor locations, size and normals are still a fixed board-plane grid; there is no measured-reading input in this tool. The CSV names are compatible, but measured sensor-position/orientation matching and validation are still pending.
- All four exports contain zero LeafSurface instances. There is no leaf shading or leaf PPFD result yet.
- The optical-copy regular expressions currently remove shader calls globally. Before Phase 3, scope those edits to display objects so real LeafSurface materials are preserved; do not treat this as tested mesh support.

## Evidence files

`build/phase2v2_codex_review_20260929/review_evidence.json` contains the four-plant artifact audit and the measured-status probe.
`mixed_status_probe.json` and `mock_gate_probe/` in that directory are synthetic review fixtures, not research or measured outputs. Their manifest uses mocked sensor transport and must never be aggregated into experiment results.

## Recommended handoff decision

Accept the corrected synthetic scene integration as a working Phase-2 prototype. Resolve F1–F3 before accepting measured-scene eligibility or the named numerical gate. Keep `validated_metric=false` and `suitable_for_ppfd=false`; continue real sensor/LED integration and reviewed leaf surfaces in their agreed stages. Source code was not changed during this review.
