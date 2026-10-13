# Document 06 only: implementation and handoff

## Scope and ownership

The user's latest scope override is **Document 06 only**. Do not start Document 05 clustering from this handoff. The initial 06-then-05 brief is superseded by this scope. The user separately requested paint/erase brush editing; that is included.

Codex implemented this explicitly requested task. Claude Code remains the lead for follow-up work through **2026-09-26 18:00 Asia/Seoul**. No automatic resumption, training, inference, remote service, new model download, or clustering was started.

References: `C:/Users/sho36/Downloads/06_instance_multiview_codex_handoff.pdf`, the user's approved implementation plan and subsequent scope override. Document 05 is a deferred reference, not part of delivery.

## Implemented in the existing application

- `tools/instance_workflow.py`: immutable run snapshots, original observation-to-identity adapter, reference validation/template, cached sensitivity comparisons, development-parameter freeze, source-hash checks, staleness checks and CLI.
- `tools/instance_evidence.py`: one-to-one mask metrics and finite, chunked 2 mm multi-view voxel evidence. No clustering code remains here.
- `tools/instance_workflow_defaults.json`: the approved sensitivity/voxel/pilot settings. No Document 05 parameter grid is exposed.
- `tools/instance_workflow.js`: a Document 06 panel in the existing editor, preserving its current mask UI and legacy paired-view/identity/membership tools.
- `tools/serve_leaf_edit_session.py`: two additional job operations, `sensitivity_sweep` and `instance_fusion`, using the current token/origin checks and result directory. `instance_clustering` is rejected. Completed runs are discoverable after restart.
- `tools/leaf_point_annotator.html`: exported the existing `adoptLeafletDetection` hook; the identity implementation itself is reused.
- `tools/leaflet_mask_batch.py` / `.js`: paint, erase, original-pixel brush radius, stroke undo, explicit save and saved-edit undo for **both leaflet and compound masks**. Brush edits do not call SAM.

The existing mask batch and single-image segmentation interfaces remain available. Research runs process leaflet observations only; compound boxes remain contextual ROIs, not membership rules or a set of separate leaflet instances.

## Brush use

1. Select the class, photo and observation in the existing mask panel.
2. Save the sensitivity preview or restore the saved setting before editing.
3. Click **브러시·점·윤곽 수정**. Choose **브러시 칠하기** or **브러시 지우기**.
4. Adjust the radius (original-image pixels), then drag on the right-hand image.
5. Click **브러시 수정 저장**. Saving leaves the observation edited/unconfirmed. Acceptance remains a separate action.
6. **마지막 붓질 취소** removes an unsaved stroke. **되돌리기** restores the previous saved state, including after reload.

Rasters are stored losslessly as foreground intervals in the optional `manual_raster` field. Existing items acquire its default only in memory until a real save. Existing undo entries without that field remain readable. Paint/erase preserves untouched fragments and holes. Contour edits apply a delta to the current raster; sensitivity/candidate changes intentionally replace the edited raster, with the existing warning and undo history. Original boxes are unchanged.

The brush preview is a canvas rendering; the saved binary raster is authoritative. Radius is clipped to the existing cached crop, and invalid/out-of-crop input is rejected. This tool does not infer hidden leaf areas or distinguish overlapping leaves automatically.

## Document 06 web workflow

Open the **06 · 마스크 비교 / 동일 소엽 연결 / 진단용 3D 근거** panel below the mask panel.

1. Use **현재 세션 사진·라벨 불러오기** to load the existing prepared session through its original bootstrap. Browser-saved work is preserved; an initial seed is used only when there is no saved work.
2. Select a leaflet above and use **위에서 선택한 소엽 연결 보기**. Adopt its existing detection into a new or existing identity. Use **이 사진의 소엽 분리** for a mistaken link. These actions reuse the existing undo/history and move-with-observation behavior.
3. Set full/partial/unknown visibility separately. Confirm cross-view physical identity separately. Mask acceptance does not perform either action and does not confirm compound membership.
4. For the first real fusion pilot, the human should confirm up to five clearly identifiable leaflets per plant in views **24/25 for dwt_01** and **27/28 for dwt_02**. If the same leaf cannot be established, leave it unresolved. Side view **11** participates in visual review but has no geometric vote without a measured pose.
5. Run the cached sensitivity sweep, or strict/diagnostic evidence fusion. New runs go under the server's existing `editor_runs/run_.../result/` directory.
6. Open the result. Inspect CSV/JSON downloads, the original-photo/mask overlay, source annotation, identity, visibility, pose quality and actual detected ChArUco IDs. Supported/excluded/ambiguous candidate layers can be selected and rotated when candidates exist. Selecting a point filters its contributing observations and shows its reprojection.
7. **현재 수정 내용과 비교** checks whether the current backup, batch items, source images/calibration/cache/import files differ. Local mask edits and identity changes also mark the open result for rechecking. Recompute into a new run; previous outputs are preserved.

The UI currently reads research results from the existing application's job service. It is not a separate annotation application. The legacy paired-view screen remains available from the mask panel's existing toggle.

## Identifiers, references and metrics

Observation identity is the original photo/source annotation ID. Join accepted masks to editor boxes through `source_detection.source_annotation_id` and the photo name, never by box overlap or growth-count JSON. A split changes the resolved physical identity in the next snapshot; the mask stays attached to its original observation. Conflicting duplicate links are unresolved.

`leaf_key` is the existing editor's composite physical identity. In newly generated manifests `leaflet_id` uses this same canonical key; `editor_leaflet_id_raw` preserves the old component, which can literally be `unavailable` for legacy bbox-only identities. `compound_leaf_id` stays null unless the existing membership review is confirmed. Landmark `point_id` remains a separate existing concept.

Each run writes `reference_template.json`. Complete a separate version of that document using **independently human-reviewed visible masks**, then load it through the reference JSON field or `--reference`. Required metadata: schema `instance-visible-reference-1`, plant/session, nonempty version/reviewer, `independent_manual_review: true`, original image hashes, photo coverage, per-instance reference ID, visibility and `origin: independent_manual`. Rings use the existing original-pixel XOR raster convention for islands/holes. Keep incomplete/unreviewed photo coverage explicit. `ignore_rings` removes pixels from evaluation.

Generated masks, accepted masks, rectangular COCO polygons and growth-count JSON are not promoted to independent references. The snapshot includes the supplied reference version; no reference is auto-filled. A prediction must never be submitted as its own reference.

Sweeps use 0–100 in steps of 5 plus saved off-grid values. Prompts and the selected candidate remain fixed. Float32 threshold behavior matches `Batch.mask`; no cleanup, inference or save occurs. Manual edits are recorded but are not applied to the raw-logit threshold comparison. Candidate switching is not confounded with threshold variation.

Metrics include one-to-one TP/FP/FN, precision/recall at IoU >= 0.5, mean IoU/Dice across reference instances (unmatched instances contribute zero; sub-threshold assigned overlaps still contribute their measured IoU/Dice), per-reference visibility rows, and separate merge/split review flags. Matching prioritizes valid match count, then IoU. A merge flag means one prediction covers >=20% of each of at least two references; a split flag means at least two predictions each cover >=20% of a reference. Flags are not automatic correctness judgments.

Use dwt_01 for development, then freeze a completed development sweep with the UI or CLI. dwt_02 accuracy is unavailable until a matching, earlier frozen manifest is supplied. A freeze with no independent references is explicitly exploratory/unvalidated. This is a two-plant, **bbox-assisted** engineering comparison, not autonomous detector accuracy or generalization evidence. CSVs include availability/exclusion and coverage; unavailable accuracy is not zero accuracy.

## Geometry contract and limits

- Existing distortion-aware projection and full-visible bbox extent solver; board coordinates in estimated millimetres. No nominal camera angles, invented depth, SfM or side-pose replacement.
- Finite search bounds require confirmed identities and fully visible bboxes. Single-view, unbounded, incompatible or degenerate extents are explicit failures. Partial observations do not bound the complete leaf.
- Board-anchored `(i + 0.5) * 2 mm` voxel centres, processed in chunks of 8,192. A 500,000 candidate-row resource ceiling reports failure; it never silently coarsens the grid.
- Per-view support, contradiction and unknown are retained. Visible parts of partial masks support candidates; absence outside a partial mask is unknown. The existing contour tolerance is an unknown boundary band for full masks.
- At least two distinct eligible photos must support a retained candidate. Duplicate routes do not add votes. Contradictions and insufficient parallax are recorded. Physical-identity conflicts remain ambiguous.
- `voxels.csv` and `evidence.json` retain excluded candidates and reasons as well as supported candidates. No existing point, label or surface is deleted by pruning.
- Strict mode enforces the current pose gate. Diagnostic mode may use solved failed-gate ChArUco poses. Both retain `validated_metric=false` and `suitable_for_ppfd=false`.
- The viewer displays at most 20,000 evenly sampled candidate rows; full-resolution 2 mm evidence remains in the files. Display sampling does not change the computation.
- No complete leaf surface, leaf area, tissue volume, PPFD or growth estimate is produced.

No changed image export was imported. The previously reported centered-crop importer defect remains a prerequisite for future changed exports. Current runs additionally verify the prepared batch's import-source hashes, camera/session hashes, original photos and cached score hashes. The incomplete scratchpad hull generators are not used.

## Actual pilot results

Outputs: `build/instance_evidence_06_20260922_191449/`.

| Plant | Pilot photos | Leaflet observations | Review state at snapshot | Sweep time | Strict / diagnostic geometric candidates |
|---|---|---:|---|---:|---|
| dwt_01 | 11, 24, 25 | 59 | 54 unreviewed, 5 accepted | 9.75 s | 0 / 0 |
| dwt_02 | 11, 27, 28 | 40 | 40 unreviewed | 7.71 s | 0 / 0 |

The 99 observations are photo-level labels, not 99 physical leaflets. Saved sensitivities 31 and 71 were included in the dwt_01 sweep. No independent reference masks were supplied, so accuracy is unavailable for both plants. A dwt_01 exploratory settings freeze preceded the dwt_02 comparison.

Both strict pilots have zero qualified poses. Each diagnostic pilot has two eligible solved poses, but the imported handoff backups contain no confirmed physical-identity links for these masks; therefore no bounded reviewed instance is produced. No dummy 3D object was invented. Full runs over the remaining photos were not performed before human pilot review.

The actual web job `run_20260922_192503_49211afd` at dwt_01 also completed in approximately 4.97 s with explicit `unavailable_no_bounded_reviewed_instances`, zero identity confirmations and no candidates. Its existing result viewer showed the source mask, original annotation ID 88, failed pose gate and actual marker IDs.

The earlier plan's all-unreviewed starting state is outdated: the live dwt_01 batch now has 8 accepted, 1 rejected, 1 edited and 282 unreviewed observations; dwt_02 has 285 unreviewed. These were present before this implementation's pilot snapshot. Codex did not accept or edit real research masks in this task.

Before/after hash audits verified **723 existing input/state files unchanged**, including the user-modified masks, source labels, manifests and prepared-session JSON. See `preservation_before.json`, `preservation_after.json` and `final_source_audit.json`. Browser write tests used only the pre-existing `build/sensitivity_web_20260922/ui_fixture/` copy. Both that directory and `build/leaflet_mask_batch_20260922/ui_test_fixture/` are excluded from research operations.

## Reproducible commands

Run from `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`. Always use a fresh output directory. Replace the backup argument with an exported current editor backup if human identities have since been confirmed.

```powershell
python -m tools.instance_workflow --operation sensitivity_sweep --session build/new_captures_20260920/dwt_01/edit_session --backup build/dwt_01_02_3d_20260922/dwt_01/labels/seed_with_imports.backup.json --context build/new_captures_20260920/dwt_01/edit_session/annotations.source.json --batch build/leaflet_mask_batch_20260922/dwt_01 --out build/document06_next/dwt_01/sweep

python -m tools.instance_workflow --operation freeze_parameters --development-run build/document06_next/dwt_01/sweep --out build/document06_next/frozen_parameters.json

python -m tools.instance_workflow --operation sensitivity_sweep --session build/new_captures_20260920/dwt_02/edit_session --backup build/dwt_01_02_3d_20260922/dwt_02/labels/seed_with_imports.backup.json --context build/new_captures_20260920/dwt_02/edit_session/annotations.source.json --batch build/leaflet_mask_batch_20260922/dwt_02 --out build/document06_next/dwt_02/sweep --frozen build/document06_next/frozen_parameters.json

python -m tools.instance_workflow --operation instance_fusion --session build/new_captures_20260920/dwt_01/edit_session --backup build/dwt_01_02_3d_20260922/dwt_01/labels/seed_with_imports.backup.json --context build/new_captures_20260920/dwt_01/edit_session/annotations.source.json --batch build/leaflet_mask_batch_20260922/dwt_01 --out build/document06_next/dwt_01/diagnostic --mode diagnostic
```

Use `--mode strict` for the gated result and `--scope all` only after the pilot checks. Add `--reference path/to/independent_reference.json` when that human-reviewed material exists. Original server launch commands remain in `CLAUDE_LEAD_HANDOFF_UNTIL_2026-09-26_1800_KST.md`; no new service or port is required.

## Validation and next actions

Focused Python and Node validation covers original coordinates and crop offsets, distortion, strict gates, bounded/single-view/unposed/partial cases, duplicate routes, conflicts, noisy poses/merged masks, source preservation, cached thresholds, independent-reference guards, instance matching, parameter freeze, staleness, token/origin checks, brush raster persistence/undo, and legacy membership/identity behavior. Final test totals are appended below after the last run.

Browser verification on the isolated fixture: paint increased 21,065 to 22,765 pixels; reload retained the edit; undo restored 21,065. Erase/save/undo restored the same starting area. ID adoption, partial visibility, explicit confirmation, split (which reset identity confirmation), and four undo steps returned to the initial unlinked state. No console errors were observed. The real viewer displayed an explicit empty diagnostic result and its actual photo/mask evidence.

Human/Claude next: review visible masks and create an independent reference version; explicitly connect up to five clear leaflets per plant; verify full/partial status; rerun the pilot; inspect conflicts and reprojections before expanding. Biological accuracy and positive real-plant fusion remain **awaiting human evidence**, while the Document 06 software path is implemented. Document 05 remains deferred.

### Final verification

- Python: **47 passed**, covering the six focused test modules listed below.
- Node: **39 passed** for existing membership, leaflet/identity and AI proposal behavior.
- JavaScript syntax checks passed for both updated UI scripts.
- No server errors were logged during browser verification.
- `build/instance_evidence_06_20260922_191449/validation_summary.json` records the results.

```powershell
python -m pytest tools/tests/test_instance_workflow.py tools/tests/test_instance_evidence.py tools/tests/test_leaflet_mask_batch.py tools/tests/test_serve_leaf_edit_session.py tools/tests/test_threshold_decisions.py tools/tests/test_leaflet_extent.py -q
node --test tools/tests/leaf_annotator_membership.test.cjs tools/tests/leaf_annotator_leaflet.test.cjs tools/tests/leaf_annotator_ai.test.cjs
```

The live servers are refreshed at ports 8821 (dwt_01) and 8822 (dwt_02). The isolated 8823 fixture server is stopped after verification. Existing model configuration is retained; this implementation did not invoke inference.
