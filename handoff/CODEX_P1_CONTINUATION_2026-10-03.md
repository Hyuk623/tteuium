# P1 observation and completion continuation

Date: 2026-10-03. English work brief and append-only delivery record for CODEX_P1_3D_CHAT_PROMPT_2026-10-03.md.

## Request and inspected state

Audit the existing detection baseline and optional completion implementation, verify immutable inputs and trial isolation, inventory future geometry fields and review reversible canopy identity/placement contracts. Preserve D1-D10: P3 owns growth, P4 is diagnostic, and cross-project linking remains deferred. No protected core, human config, raw observations or design documents will be edited.

The current completion packages remain unexecuted. Public-model permission is settled, but the GPU destination/upload answer is still missing. An existing newer CLAUDE_CODE_MULTIVIEW_TRIAL_PROMPT_2026-10-03.md specifies common targets and unavailable metrics. It leaves the ring poses as examples and the validated image mapping undefined; no scientific acceptance or pose repair will be invented. Current source already contains verify_arm_isolation and matching tests; preserve and extend that implementation rather than replace it. The verifier currently checks target/condition names but does not verify all archive member hashes. Candidate import checks target IDs without checking their camera metadata against the frozen request.

## Intended work and validation

Strengthen existing packaging integrity checks and target provenance retention with focused negative tests. Audit saved per-photo ratios against their first manifest labels and source hashes. Produce fresh build evidence for archive checks, comparison availability, geometry field/unit/missingness inventory and source/instance transform contracts. Review actual source and saved geometry outputs; do not fabricate confirmed associations or accepted surfaces. Record exact owner dependencies in TODO and this report. Run focused completion/detection tests and existing relevant transform/split tests only as justified by this audit.

The actual GPU runtime, checkpoint load and trial remain dependent on the user's destination answer. No local heavyweight install, model download, upload, paid service, training, cross-chat message or P1-P2-P3 integration is implied by this work. Synthetic fixtures will be labelled as such. Full completion requires genuine returned model output; independent audit delivery does not close that requirement.

## Updated evidence discovered during continuation

The initial brief above reflected the older _01 status. Current filesystem and remote evidence supersede it. The user selected **Claude Code as the uploader**. Claude Code had already prepared `build/multiview_completion_20261003_02/evaluation_contract.json`, matching `_prepared_04` and `_execution_package_03` artifacts, a Kaggle launcher and returned failures. No further public-model or uploader-selection question is needed. This Codex task made only read-only remote status/output requests; it did not upload, launch, cancel or restart a job and did not edit Claude's `_02/kaggle` files.

The common target contract now exists: T_eval uses image 13 camera pose only, and four constant ring targets use polar 60 degrees, azimuth 0/90/180/270 degrees and radius 1.5 model units. Both arms retain seeds 42/43, 50 DDIM steps, eta 0, guidance 3 and 1,800 seconds per arm. Target and condition pose gates remain false. Image 13 pixels/masks stay local; the common target pose is explicitly permitted by the newer Claude contract. The ring constants are declared diagnostic assumptions, not measured cameras. Silhouette IoU and boundary F-score remain unavailable without a validated original-camera mapping; ring targets have no observed metric reference. The earlier unmatched-target concern is resolved for these packages, not for historical _01 archives.

## Changed software and focused verification

- `tools/completion_package.py`: added `verify_archive` and invoked it from the existing `verify_arm_isolation`. It verifies every declared member hash, exact inventory, safe/unique archive paths, request linkage, condition inventory, declared input hashes and source/dependency identities without extraction. Matching file names alone no longer pass a modified archive.
- `tools/multiview_completion.py`: candidate import now checks declared target camera metadata and pose-gate flags against the frozen request, in addition to target IDs and existing generative/metric/optical restrictions.
- `tools/completion_viewfusion.py`: carries the declared target pose gate into generated view provenance. The runtime loader itself was not changed during this continuation.
- `tools/tests/test_multiview_completion.py`: added negative coverage for changed image bytes, extra files, duplicate ZIP members, escaping paths and changed/missing target provenance; positive import preserves false pose gates.

Fresh evidence root: `build/p1_continuation_20261003_01/` (E below).

Commands actually run:

```text
python -X utf8 -m pytest tools/tests/test_multiview_completion.py tools/tests/test_completion_viewfusion.py tools/tests/test_detected_leaf_area.py tools/tests/test_relative_leaf_area.py -q --junitxml=build/p1_continuation_20261003_01/focused_tests.junit.xml
python -X utf8 -m pytest tools/tests/test_light_growth_bridge.py::test_transform_points_vectors_and_second_moment_roundtrip tools/tests/test_light_growth_bridge.py::test_complete_direct_package_and_split -q --junitxml=build/p1_continuation_20261003_01/transform_tests.junit.xml
python -X utf8 build/p1_continuation_20261003_01/audit_delivery.py
python -X utf8 build/p1_continuation_20261003_01/geometry_inventory.py
python -X utf8 build/p1_continuation_20261003_01/check_numpy_checkpoint_alias.py
```

Results: **55 focused tests passed** and **2 existing synthetic transform/split tests passed**. Test runs exercised supported software boundaries; they did not validate real anatomy or diffusion inference. The audit scripts write fresh evidence and are not new production pipelines. `audit_delivery.py` packages fresh directories and therefore is not overwrite-idempotent; choose a new evidence root to repeat it.

## Observation baseline audit

`E/observation_audit.json` verifies 4,021 distinct source/code hashes against the saved T1/T2/T3 audits. All match. The existing 1,318 CSV observations reproduce area division, match the actual first saved manifest label per photo, and contain 54 first-reference ratios equal to 1. Counts remain 435/489/394. No masks, detections, measured poses, board configuration or raw images were changed.

| Quantity | Unit and basis | Availability boundary |
| --- | --- | --- |
| Saved visible mask area | original-image pixel squared | observed visible foreground, includes occlusion/perspective limitations |
| Explicit bbox proxy | original-image pixel squared | rectangular box occupancy; no automatic mask fallback |
| First-label ratio | dimensionless | group-specific reference; missing/zero reference cannot be replaced |
| Distortion-aware projected area | cm2 | calibrated projection/depth estimate; not whole tissue surface |
| Supported surface area | cm2, one-sided supported triangles | evidence-supported patches only; no unseen tissue filling |
| Total actual tissue area | cm2 if independently supported | currently unavailable for these real plants |

Existing mask/bbox separation and invalid-reference tests passed. Per-photo annotation identities are not confirmed cross-view physical leaf identities. P1 still supplies no accepted real optical mesh or biological growth observation from generated pixels.

## Transfer packages and actual trial status

`E/existing_archive_audit.json` rechecks Claude's two `_execution_package_03` archives against the common contract, including their member hashes. `E/fresh_archive_audit.json` verifies repackaged current code in:

- `E/multiview_execution_package_04/execution_package.zip`
- `E/top_only_execution_package_04/execution_package.zip`

These use the existing immutable `build/multiview_completion_20261003_02/{arm}_prepared_04` inputs and targets. The new packages include the target-provenance fix and archive verifier. Original preparations and archives remain unchanged. The top-only archive excludes image 03 and derived assets; both exclude image 13 pixels, masks, evaluator snapshots and ratio CSVs. These new archives have not been uploaded by this task. Their code differs from the older remote trial, so do not attribute that trial to the updated code.

Read-only `kaggle kernels status dolgfish/tomato-viewfusion-trial-04` returned `COMPLETE`. Version 3 outputs were retrieved into `E/returned_v3/`; the first download's terminal encoding error was corrected by setting UTF-8 for the CLI process and rerunning the same read-only download. Retrieval then exited successfully. No job was restarted.

**Kernel completion was not model success.** Both returned arm statuses are `failed` at `torch.load(..., weights_only=True, mmap=True)`, naming `numpy.core.multiarray.scalar`. There are zero generated candidate bundles and no PNG outputs to inspect or import. The returned runtime records a Tesla T4 with 14.562 GiB VRAM and successful size/SHA256 verification of the 15,465,973,531-byte official checkpoint. Actual inference memory needs remain unmeasured: the tiny recorded GPU occupancy occurred before model transfer/sampling. Do not report it as required inference VRAM.

`E/trial_audit.json` retains runtime versions, checkpoint verification/probe, genuine arm errors, times and all downloaded file hashes. `E/comparison.csv` contains 20 failed run rows (two arms, two seeds, five targets) with empty metric values and false pose gates. These rows are scheduled samples that failed before generation, not 20 generated outputs. Visual review status: unavailable because no images were produced. No artificial candidate bundle, IoU, F-score, depth or surface was created to fill this gap.

## Checkpoint failure diagnosis for Claude Code

The returned launcher resolves each allowlisted global by importing its name, but registers only the object. Under NumPy 2, the scalar object's module is `numpy._core.multiarray`, whereas the checkpoint names `numpy.core.multiarray.scalar`. Registering the object alone therefore does not register the serialized old name. This is a supported explanation of the observed error, not proof that it is the only remaining checkpoint problem.

`E/check_numpy_checkpoint_alias.py` reproduced this exact namespace failure with a tiny locally generated scalar checkpoint. `E/numpy_alias_diagnostic.json` records that object-only allowlisting failed and explicit `(object, serialized_name)` registration succeeded while preserving `weights_only=True`. The fixture also explicitly permits its float64 dtype class. It does not contain model weights, callbacks, optimizer state or real images and does not establish full checkpoint or GPU compatibility.

Claude Code should apply the narrow alias correction in its runtime launcher and checkpoint probe, using an exact reviewed name list after the official checkpoint hash check:

```python
# Preserve the serialized name, even if the imported object's __module__ changed.
_safe.append((getattr(importlib.import_module(_mod), _attr), _name))
```

Then inspect any dynamically constructed dtype failure and permit only the specific audited dtype class required. Keep tensor-only loading; do not switch to an unrestricted loader to hide the failure. Record the compatibility shim/diff and exact package versions, and repeat the checkpoint probe before launching either arm. The PyTorch [serialization documentation](https://docs.pytorch.org/docs/2.14/notes/serialization.html) specifies explicit named tuples and notes that static global inspection does not enumerate dynamically built NumPy dtype classes. This correction still requires verification in the actual Kaggle runtime and against the official checkpoint.

## Future geometry interface inventory

`E/geometry_fields.csv` inventories 13 requirements with current producer fields, units, availability and limitations. `E/geometry_inventory_audit.json` records the inspected candidate headers and synthetic surface flags.

The P1 triangle table preserves `plant_id`, `session_id`, `geometry_variant_id`, `geometry_source`, `organ_id`, `leaflet_id`, `triangle_id`, nine vertex coordinates in mm and `normal_convention`. Capture/board-frame identity, geometry hash, visibility masks, patch support, quality evidence and optical acceptance need their sidecars; they are not all present in triangle rows. The inspected synthetic surface has `normal_convention=unknown`, `physical_validation=false` and `suitable_for_ppfd=false`.

Missing real prerequisites remain: reviewed compound/leaflet association, timezone-aware capture time for a valid temporal join, persistent board-frame identity and evidence, confirmed supported tissue geometry, area-basis identity, explicit normal/optical review, and independent accuracy evidence. A confidence score cannot be inferred from a review label or reprojection residual. Existing per-photo labels and partial petiole observations cannot supply those missing fields. Unknowns remain null/unavailable according to each producer's format, never zero.

The canopy contract is already implemented by `tools/canopy_light.py::materialize_case` and P2's `tools/light_growth_bridge.py`. P1 did not add a cross-project adapter. `E/canopy_contract_audit.json` independently checks the existing synthetic `_04` package and splits: `P1` and `P1_COPY` both map to source P1 while retaining distinct instance identities; per-instance sample subsets match exactly, inverse transforms pass at 1e-10, parent/context hashes match, and two referenced full triangle files still match their hashes. Synthetic evidence does not make real P1 geometry ready.

Splitting reports preserves full-canopy shading context; it does not rerun light transport or recover triangles from aggregated light summaries. Full source triangle files, per-instance ID mappings, frame transforms, weights and provenance must remain available. Point transforms include translation; direction/normal transforms use rotation. Unit/frame/ID round trips are appropriate, while light transport and aggregation require forward checks under D7.

## Requirement audit and remaining owners

| P1 item | Evidence and status |
| --- | --- |
| 1 Observation distinctions and first-label baseline | Audited; 1,318 rows, 54 references and 4,021 source hashes verified; focused regression coverage passed |
| 2 Measured geometry and frame preservation | No PnP/board/geometry/config changes; failed gates remain false; generated targets supply no measured scale |
| 3 Existing pipeline continuation | Existing three tools extended; no second reconstruction/completion pipeline |
| 4 Generative output type and eligibility | Existing rejection tests plus new target-provenance checks pass; no actual successful generated bundle yet |
| 5 Common target/evaluation contract | Current Claude `_02` contract and both archives verified; unavailable scientific metrics retained |
| 6 Runtime and bounded real trial | Actual returned attempts inspected, both checkpoint-load failures; user assigned upload to Claude Code; retry compatibility and successful inference remain incomplete |
| 7 Geometry field inventory | 13 fields/groups inventoried; missing real fields and acceptance gates explicitly recorded |
| 8 Canopy identity and reversibility review | Existing source/instance/transform/split contract reviewed and synthetic checks passed; no integration adapter implemented |

Remaining work is specific:

1. **Claude Code execution owner:** apply/record the runtime alias fix, check actual dtype/callback/checkpoint compatibility and memory, use the updated transfer code where appropriate, and run all declared seeds/targets within the frozen budgets. Upload is assigned to Claude Code; no need to ask the user again who uploads. Return genuine output/status/runtime files without removing failures.
2. **P1 Codex after successful returns:** validate target metadata and flags, import/evaluate/review each successful arm, and update comparison and visual notes. Existing unavailable mapping remains a scientific limit; any valid metric mapping or boundary tolerance requires an exact reviewed contract.
3. **Claude/scientific owner and human observations:** provide accepted real surface/identity/frame/time/area/normal evidence before claiming geometry integration readiness. No repeat search for the already-confirmed absent measurements or curved-fit contract.

This continuation delivers audited software and diagnostic evidence. It does not claim successful diffusion inference, real anatomy validation, accepted optical geometry, growth prediction or P1-P2-P3 integration. The full trial requirement remains incomplete pending the execution-owner retry and inspected results.
