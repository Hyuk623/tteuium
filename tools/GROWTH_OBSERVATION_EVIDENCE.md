# P3 observation evidence boundary

This additive contract is `p3-observation-evidence-1`. Existing
`compound-observations-1` and `growth-calibration-1` CSV columns remain valid.
No environment variable or new CLI is introduced. Existing import, forecast,
update, calibration audit/fit/validate and export commands consume the metadata.

## Manifest input

Optional `observation_evidence` contains `schema`, `sources`, and `records`.
`sources` maps identifiers to `{path, sha256}`; paths resolve relative to the
manifest. Every supplied source is hash-verified, and joins/claims are retained.
No P1 table is automatically adapted. The P1 `supported_area_cm2` diagnostic is
not sufficient evidence; its new area gate and reviewed organ association need
an explicit producer/consumer mapping or an independently reviewed measurement.

Observation records join exactly on `plant_id`, `organ_id` (the CSV's
`compound_leaf_id`), and `session_id`. Calibration records join on `plant_id`,
`organ_id`, `record_id`. Duplicate/orphan/wrong-plant joins are input errors.
`area`, `direction`, and, for calibration, `anchor_area` / `anchor_direction`
are optional per-trait objects. Unsupported declarations are not ignored.

Each supported area claim declares:

- `quantity: one_sided_physical_tissue`, `unit: cm2`, `scope: compound_leaf`.
- `method`, `method_version`, `calibration_hash`, `pose_hash`, `partition_hash`,
  `tissue_support_id`, `visibility_basis`, `canopy_placement_id`, `capture_phase`.
- `source_ref` naming a source, `source_row_id`, aware `observed_at` equal to the
  associated capture, `identity_scope: cross_date_same_organ`,
  `identity_source_ref`, `tissue_evidence_status: reviewed`.

Explicit synthetic tests also accept `tissue_evidence_status: synthetic_assumption`
and need not attach empirical source files. This is never real validation.
A bare legacy synthetic area retains its original software-fixture semantics.
A real legacy area without this evidence becomes unavailable, with its raw value
preserved. The old basis ID never established physical tissue validity.

Direction claims use `quantity: directed_whole_rachis`, `unit: unit_vector`, and
`scope: compound_leaf`, with the same provenance/identity declarations. The
existing measured whole-rachis axis contract remains accepted without new metadata.
A normal axis, botanical face, leaflet normal, top/ring ratio or mean inclination
is not this quantity. Calibration uses `directed_whole_rachis_angle`, `unit: rad`
and the plan's exact `angle_reference`, with current and anchor evidence; no
normal-to-angle conversion is supplied. Existing signed/circular angular math is
unchanged. Tissue-support/visibility fields describe the same observed support;
they do not certify a biological face or an optical receiver.

## Continuity and identity

Current and prior/anchor claims must match quantity, unit, scope, method/version,
calibration/pose/partition hashes, tissue support, visibility basis, capture phase
and canopy placement ID. The area basis must also match. A method switch, changed
support or missing side produces an unavailable comparison, without rescaling.
Comparability mappings for changed acquisition hashes are deliberately not
implemented: no approved mapping contract was supplied. Even a scientifically
legitimate change therefore needs review before this interface can compare it.
No historical series is overwritten or automatically concatenated.

Each source hash/row/trait may name only one current observation. A shared
calibration anchor may recur for the same organ, never another plant/organ.
Metadata cannot allocate one whole-plant row to multiple leaves.

Optional record `identity` declares `scope` and `change`. Confirmed associations
with a declared within-ring scope are unavailable; merged/split identities have
no supported trajectory mapping. Renaming an already measured organ needs
association `lineage={kind: same_organ_rename, previous_id, observed_id, plant_id,
source_ref}` with exact identities. Existing manually reviewed same-ID temporal
associations remain accepted. Duplicate predicted aliases and wrong-plant
associations are input errors. Occluded/missed observations retain prior event
semantics; no death, age or appearance is inferred.

## Outputs and unavailable behavior

- States retain `observation_evidence`, CSV `source_row` (table SHA256 and line),
  and all verified source hashes. Rejected values/geometry remain under
  `raw_observation_traits`, with `trait_unavailable` reasons; unrelated sizes stay.
- Updates retain valid prior predictions for blocked traits and label these with
  `retained_prediction_traits`, `trait_update_unavailable` and
  `reanchor_status: weighted_observation_anchor`. Their correction is unavailable,
  not measured zero. Retained trait provenance remains the prior provenance.
- `trait_diagnostics` lists excluded likelihood quantities. Supported coordinates
  use the corresponding covariance submatrix (marginal likelihood); no covariance
  is fitted. If every requested trait is unsupported, weights stay unchanged.
- State metadata JSON, trajectory bank JSON and update JSON preserve full evidence.
  Calibration `data_audit.json` retains record evidence. Validation adds
  `validation_observation_evidence.json` when present; tabular diagnostics remain
  CSV. Export manifests hash the new evidence helper as well as their entrypoint.
- Missing science is unavailable; malformed schemas, conflicting phases, duplicate
  joins/rows and hash mismatches raise `StudyError`. A genuine zero area remains 0.

Main reasons: `area_evidence_missing`, `{area,direction}_quantity_unsupported`,
`*_scope_unsupported`, `*_unit_mismatch`, `area_tissue_evidence_unavailable`,
`*_provenance_incomplete`, `*_source_evidence_unavailable`,
`*_capture_time_mismatch`, `*_capture_phase_mismatch`,
`*_comparison_evidence_missing`, `*_method_or_support_changed`,
`reanchor_area_basis_mismatch`, `temporal_identity_unconfirmed`,
`organ_lineage_evidence_missing`, `organ_lineage_mapping_unsupported`.
The existing endpoint-only and independent-unit calibration checks remain.

## Variance policy

`reanchor_covariance.traits.<trait>` retains the V2 unit-squared, identifiable,
finite nonnegative variance and source-kind/source-ref requirements. New optional
`evidence_kind` accepts `trait_measurement_variance` or `user_assumed_variance`.
Synthetic MAE, mask confidence, calibration RMS and generated/reconstruction
sample spread are rejected as measurement variance. Measured/fitted covariance
for observed data additionally requires `trait_measurement_variance` and
`repeat_measurement_source_ref`. This applies to the likelihood covariance model
as well. Explicit literature-informed/user-assumed V2 policies remain assumptions,
not empirical covariance. Missing evidence never creates an automatic 0/1 weight.

No growth coefficient, shape law, estimator, light-to-direction response, DLI
contract or posture-offset equation changes. Cross-phase comparisons with new
metadata still need supported comparability evidence; existing V2 enabled and
disabled posture behavior is preserved. Independent temporal identity, repeated
same-organ measurements and appropriate error evidence remain acquisition needs.

Record `measurement_role: repeatability` or `single_capture` cannot enter growth
calibration even when rows have different timestamps. The existing two-positive-
time identifiability gate also remains. The first observation of a newly generated
block has no past measured method to compare; it can anchor that block when the
current trait and area basis are supported, without becoming a measured growth
increment. A different-plant-only batch without applicable events does not advance
the forecast origin. Declared `identity.change: canopy_placement`, merged or split
changes remain unavailable without a separately specified mapping.
