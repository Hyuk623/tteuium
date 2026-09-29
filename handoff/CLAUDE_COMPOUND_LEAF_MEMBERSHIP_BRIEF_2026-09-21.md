# Brief: compound-leaf membership in the existing editor — Claude Code, 2026-09-21

Documentation-first brief for `handoff/CLAUDE_COMPOUND_LEAF_MEMBERSHIP_2026-09-21.md`. Written before
implementation; outcomes are appended in section 6. No training, inference, model download,
reconstruction run or PPFD in this work.

## 0. Ownership note

`tools/` is Codex's column under `CONVENTIONS.md` §1. The user explicitly asked Claude Code to carry out
this Codex-written handoff, whose named integration points are `tools/leaf_point_annotator.html` and
`tools/reconstruction_request.py`; the previous Claude hybrid/reference-layer tasks were done the same
way. The last `tools/` edits are from 2026-09-20 20:48 and today's Codex entries are photo
organisation only, so no concurrent edit is in progress. Every changed file is listed in `LOG.md`.

## 1. Request

Let leaflets seen in crowded photographs be associated with their parent compound leaves, using the
user's separately annotated `sub-stem` object per compound leaf as the attachment evidence, and review
the result against the growth JSON counts without letting the counts decide anything.

## 2. Inspected state (verified today)

- **Editor state** lives per photo combination in `store.variants[variant]` = `{leaflets, boxes,
  proposals, identity_decisions, auto_drafts}`. Leaflet records are keyed `organ_id|leaflet_id`; the
  "new label" path creates `leaf_NNN|unavailable`. `organ_id` is the parent compound leaf field.
- **Undo** is a whole-state JSON snapshot per variant (`pushHistory`/`undo`), so multi-record changes
  are atomic under undo if they happen after one `pushHistory`.
- **Live references to a leaflet key** outside the record: `ui.leafKey`, `proposals[].target_leaf_key`
  and `accepted_into.leaf_key`, `auto_drafts[].assigned_to`, `identity_decisions[]`
  (`source_leaf_key`, `candidate_leaf_key`), `ui.matchResult`, `ui.matchPoints`. Point provenance,
  landmark candidates, view status and observation/identity history live inside the record.
- **Box classes** are only `flower`, `bud`, `truss`. None of the five detector classes
  (`compoundleaves`, `leaflet`, `sub-stem`, `main-stem`, `growth-shoot`) has a place in the editor, and
  no Roboflow export or API response exists in the repository. Masks exist only as accepted leaflet
  regions (`regions[key].rings[].points_px`).
- **Remote sync** pushes/pulls only `leaflets, boxes, proposals, identity_decisions`.
- **Growth JSON** (`dwt_01_260920.json`): `compound_leaves[].{compound_leaf_id, leaflet_count,
  is_unfolding}`, `growth_shoot_count`. No positions. dwt_01 L01=8, L02=9, L03=9.
- **`review_counts`** counts distinct identity-confirmed leaflets per `organ_id`, skips
  `leaflet_id == 'unavailable'`, lists unconfirmed separately. The rebuild feeds it from the backup via
  `reviewed_leaflets`.
- Coordinates: points use OpenCV pixel centres; boxes use continuous pixel edges `[0, W]`.

## 3. Intended changes

### 3.1 Relationship metadata (`vstate().membership`, schema `compound-leaf-membership-1`)

- `detections[image_key][]`: imported detector observations, read-only except their object link.
  `annotation_id`, exact `class_name` (one of the five), `bbox` and/or `rings` in original pixel edges,
  image size, source (`format`, file, source annotation id, import time), `object_id` (a growth-shoot
  bbox and mask of one organ share one object), `coordinate_convention='original_pixel_edges'`.
- `parents[parent_id]`: explicit reviewed anchors — `compound_observations[image_key]` (one compound
  bbox per parent per photo; one compound bbox belongs to one parent) and `substems[image_key][]`
  (a sub-stem object belongs to one parent; a parent may have several visible fragments per photo),
  with `state='confirmed'`, source method and history. A class label alone never creates a relationship.
- `candidates[id]`: membership proposals for one leaflet observation — candidate parents with evidence
  and a heuristic score (`heuristic_score_is_not_probability=true`), `state` in
  `proposed | ambiguous | kept_unresolved | accepted | rejected | superseded`, history.
- `key_map[]`: every leaflet key change (`from`, `to`, `action`, time).
- `growth_reference`: an in-editor copy of the growth counts, loaded read-only from the user's file.

On the leaflet record: `leaflet_uid` (stable physical identity, set once), `membership_origin_key`,
`membership_review` (`state`, `parent_id`, `source_method`, `candidate_id`, time) and
`membership_history[]`. Confirmed parent stays in `organ_id` — no competing parent field.

### 3.2 Behaviour

- **Import** detector annotations as COCO JSON (the common Roboflow export): exact class names only;
  images matched by file name (Roboflow's `extra.name` accepted as the original name); a size mismatch,
  unknown image, unknown class or RLE mask is skipped and reported, never rescaled; re-import never
  overwrites.
- **Anchors**: pick a parent (growth IDs offered when loaded), link the compound bbox and the sub-stem
  object(s) in each photo; unlink is explicit.
- **Proposals** for one leaflet observation. Evidence: a manually marked *visible attachment* point
  (existing point meaning `visible_attachment`) lying on a parent's linked sub-stem mask in the same
  photo; the same in other photos whose identity link is confirmed; compound-bbox overlap as supporting
  evidence only. Not used: nearest stem distance, leaflet bbox centre, mask crossings, connected
  foreground. A base touching two parents' sub-stems, or overlap-only evidence, is `ambiguous`. No
  evidence → no candidate, with the advice to inspect another view.
- **Actions** (each one `pushHistory`, so one undo): confirm (from a candidate or manually), keep
  unresolved, reject, unassign, reparent, split (existing per-photo split, now carrying that photo's
  candidates). Confirming a leaflet already confirmed elsewhere is refused — reparent is explicit.
- **Rekey**: confirming renames `leaf_003|unavailable` → `L01|leaf_003` (keeping a real `leaflet_id`
  when present). All live references above are updated in the same step, history is left as written,
  and the mapping is appended to `key_map` and the record. Coordinates, point IDs and point meanings
  are untouched.
- **Growth-shoot** bbox and mask of one organ are linked into one object and counted once, and never
  enter leaflet counts.
- **Review view**: focus a parent (its compound bbox, sub-stems and confirmed leaflets drawn, others
  faded or hidden), detections drawn in original pixels through the existing zoom transform, per-parent
  table of reference count / confirmed members / identity-confirmed members / unresolved candidates,
  never summed into one "exact" total while candidates remain.
- **Sync/backup**: `membership` travels in the backup automatically and is added to the remote payload.
  Old backups without it load unchanged and show everything as unresolved.
- **Mask refinement** is the existing AI region proposal/accept flow; it stays optional and is not a
  prerequisite for confirmation. No new model path.

### 3.3 Python

- `review_counts(growth, leaflets, membership=None)`: keeps its current counting rule and adds per
  parent `membership_confirmed_ids`, `membership_unreviewed_ids` (legacy records without a membership
  decision) and `unresolved_candidate_leaflets`, plus a non-blocking `leaflet_membership_unresolved`
  finding. Growth-shoot counts stay separate.
- `rebuild_leaf_edit_session.reviewed_leaflets` passes the membership state and the open candidates.

## 4. Execution restrictions

No training, inference, weight download, reconstruction or PPFD run. Photographs, growth JSONs,
calibration, `config/`, `docs/` and existing build outputs are read-only. Membership never changes a
coordinate, a pose, a gate result or `validated_metric`/`suitable_for_ppfd`. Counts never create,
delete or assign a label.

## 5. Validation plan

Deterministic Node tests with mocked detections covering the ten acceptance scenarios of the handoff,
Python tests for the count review extension, full `tools/tests` suite, and mutation checks that each
rule's test fails when the rule is removed.

## 6. Outcomes (completion report, 2026-09-21)

### 6.1 Implemented (as planned in section 3 unless noted)

- **`tools/leaf_point_annotator.html`** — new "복엽 소속" side section and a membership model block
  (`membershipState`, `parseCocoDetections`/`importDetections`, `linkDetectionObjects`,
  `addParent`/`linkCompoundAnchor`/`linkSubstem`/`unlinkAnchor`, `proposeMembership`,
  `keepCandidateUnresolved`/`rejectCandidate`, `confirmMembership`/`reparentMembership`/
  `unassignMembership`, `rekeyLeaf`, `moveMembershipView`, `adoptLeafletDetection`,
  `loadGrowthReference`, `membershipCounts`), plus `drawMembership` (detections drawn in original
  pixel edges through the existing zoom transform, parent focus with fade/hide).
  Existing functions touched: `moveLeafView` (split carries that photo's candidates and adopted
  detections), `nextOrganId` (never re-issues a renamed leaflet's name), `undo` (selection follows a
  reverted rename), remote sync push/pull (now carries `membership`), `drawBoxes`/`drawLeafBoxes`/
  leaf-mode overlay (focus fade), `updateLeafbar` (shows `L01/leaf_003`), help text.
- **`tools/reconstruction_request.py`** — `review_counts(..., membership=None)` adds per parent
  `membership_confirmed_ids`, `membership_unreviewed_ids`, `unresolved_candidate_leaflets`,
  `exact_total_claimed`, and non-blocking findings `leaflet_membership_unresolved` /
  `leaflet_membership_not_reviewed` (only when a membership block exists, so old backups keep their
  previous findings). The counting rule itself is unchanged. `summary()` adds `unresolved` per parent.
- **`tools/rebuild_leaf_edit_session.py`** — `reviewed_leaflets` passes `leaf_key` and
  `membership_state`; `attach_references` passes the backup's `membership` block.
- **`tools/editor_point_review.py`** — count table gains a "소속 미해결 후보" column and labels for
  the two new findings.

Relationship metadata (schema `compound-leaf-membership-1`) is as described in 3.1. Detections are
stored with `coordinate_convention='original_pixel_edges'`; leaflet points (pixel centres) are
converted with +0.5 px before the on-mask test. Attachment tolerance is `ATTACHMENT_TOLERANCE_PX = 6`
(an editor constant, recorded in every evidence entry). Heuristic weights: same-view attachment 3,
reviewed other-view attachment 2, bbox overlap = its fraction (≤1).

### 6.2 Validation

- `tools/tests/leaf_annotator_membership.test.cjs` (14 Node tests, mocked COCO detections) covers all
  ten acceptance scenarios of the handoff plus import rules, one-owner anchors, tip-vs-base semantics
  and other-view evidence. `test_reconstruction_request.py` gains 4 tests; one existing expectation
  was updated for the added `unresolved` field. Full `tools/tests`: **218 passed, 1 skipped**
  (baseline before this work: 213 passed, 1 skipped).
- **27 mutation checks, all caught**, each run on a scratch copy with an unmutated control that
  passes (an earlier run's Python results were void because the copy lacked `tomato3d/` and
  `build/`; corrected and rerun). One mutation (any marked point treated as a base) survived the first
  run; the missing test was added.
- **Real page smoke test** (served over localhost, demo photos): COCO import through the actual file
  control (6 imported, wrong-size photo and unknown image skipped and reported), parent registration,
  compound/sub-stem linking, growth-shoot bbox+mask merged to one object, manual confirmation
  (`leaf_001` → `L01/leaf_001`), focus rendering. This found a defect the Node tests missed — after
  undoing a confirmation the selection pointed at the vanished name — fixed, regression-tested and
  re-verified in the page. No console errors.

### 6.3 Not done / limits

- **No real detector data.** No Roboflow export or API output exists in the repository; nothing was
  imported for dwt_01–dwt_04. The COCO path is tested only with mocked files. If the user's export
  uses different file names, sizes or an RLE mask format, those items are skipped and reported, not
  guessed.
- Detections are selected from the side list, not by clicking on the photo. No side-by-side "hidden
  attachment" view beyond the existing two panes and the candidate's "반대쪽에 이 사진" button.
- No membership CSV export; membership lives in the editor backup JSON and in the rebuild's
  `reference_review.json`.
- Mask refinement is the existing optional AI region flow; nothing new, no inference run.
- Renaming a leaflet changes the backup, so an existing reconstruction request becomes
  `reference_hash_changed_since_snapshot` (the existing staleness mechanism) until refreshed. The
  hybrid frozen reference geometry, if any, keys points by organ/leaflet and would need re-freezing;
  not exercised on real data.
- Large mask imports enlarge each undo snapshot and may exceed the remote-sync document limit
  (the editor then says it saves locally only).
- Membership never touched coordinates, poses, gates, `validated_metric` or `suitable_for_ppfd`.
