# Instance workflow: import freshness and four-plant scope

## Authorized request
Resolve the dwt_01/dwt_02 prepared-import freshness blocker and the dwt_03/dwt_04 two-plant restriction in `tools.instance_workflow`.

## Inspected behavior
All recorded input hashes currently match except the human growth records for dwt_01 and dwt_02. The catch-all error incorrectly requests crop validation for these metadata changes. The fusion runner rejects dwt_03/dwt_04 even though the orchestrator supports them.

## Implementation boundary
Preserve original imports, hashes, labels, masks, identities and all previous runs. Classify only the explicitly declared growth reference in the imported seed as review-only metadata, verify its plant/date and import linkage, and snapshot current metadata with old/new hashes in each new run. All other changed or missing inputs remain blocking. Never reassign identities, synthesize geometry or force observed counts to match the growth record.

Allow instance fusion for the four authorized plants. Keep the original dwt_01 development / dwt_02 frozen evaluation protocol for sensitivity comparisons. Additional plants must not become evaluation data implicitly. Reuse the batch's recorded pilot photos for fusion when no plant-specific research pilot exists.

## Validation and restrictions
Test metadata-only refresh, wrong-plant/date records, missing/changed geometric inputs, source mutation during snapshot, four-plant fusion, pilot selection and preserved evaluation restrictions. Run a lightweight real-input preflight; do not run model training/inference, heavy fusion, the complete pipeline or change running servers. Preserve diagnostic and PPFD-ineligible status.

## Completed implementation

- `tools/instance_workflow.py`: four-plant fusion gate; existing two-plant sensitivity protocol retained; recorded batch pilot photos used for additional plants. Batch plant/session/class must match.
- Added role-specific import validation. Only the import seed's declared growth reference, with verified seed/COCO linkage and matching plant/capture date, may refresh in a derived run. The current reference is stored in `import_freshness.json` and the run manifest with original/current hashes. The original batch/import hashes and editor backup are not rewritten; no membership or count-driven geometry is changed.
- Changed images, labels, calibration, undeclared JSON or missing inputs still fail closed and identify the affected path. Snapshot-time changes fail; future growth edits mark derived runs stale.
- Strict/diagnostic geometry gates are unchanged. No full fusion, training, model inference, server restart or main-thread preprocessing change was performed.

### Validation

`python -m pytest tools/tests/test_instance_workflow.py tools/tests/test_instance_evidence.py tools/tests/test_serve_leaf_edit_session.py tools/tests/test_leaflet_mask_batch.py -q`

**57 passed.** Includes four-plant wrapper integration, refreshed metadata in saved results, wrong-plant/date and missing references, protected-input edits, source staleness, original batch preservation, additional-plant pilot selection and existing editor/mask compatibility. Geometry in wrapper tests is synthetic/mocked; these are not research reconstruction results.

Real-input preflight passed for all four plants: dwt_01 and dwt_02 each have one refreshed review-only growth reference; dwt_03 and dwt_04 have none. Hash checks covered 25/27/27/27 current sources respectively, including import-role provenance. Existing historical S6 failure reports are preserved and are not retroactively marked successful.

### Next use

The existing `tools.instance_workflow --operation instance_fusion ... --scope all --mode diagnostic` and pipeline S6 calls use these fixes without new flags. Use a new build output directory and the current reviewed backup; do not overwrite historical evidence. For dwt_03/dwt_04 the input restriction is resolved, but usable identities, visibility and camera poses are still needed to obtain supported geometry. Existing web processes load Python modules once; a later planned server restart is needed for their in-process workflow calls, while new CLI invocations use the fix immediately.

Real-input audit: build/instance_import_scope_check_20260929_161313/summary.json and per-plant reports. All four batches and their item files remained hash-identical during the preflight.
