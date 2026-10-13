# Brief: automatic leaflet bbox and landmark drafts — Claude Code, 2026-09-20

Documentation-first brief for `handoff/CLAUDE_AUTO_BBOX_LANDMARK_PROMPT_2026-09-20.md`, per the
workflow in `AGENTS.md` (2026-09-20). Written **before** implementation; outcomes are appended at the
end of this file afterwards. Preparing this brief authorizes nothing: no training, no inference, no
model download, no PPFD simulation in this turn.

## 1. Request

Let the application propose (a) leaflet bboxes per photograph and (b) physical landmark candidates,
and propose (c) cross-view point matches, with the human correcting and confirming. Reuse the
existing proposal review and reconstruction paths; never let a draft become reviewed ground truth.

## 2. Inspected current behavior (verified in code today)

- `tools/leaf_point_annotator.html`: prompted single-leaflet segmentation (`proposals` state machine
  `proposed|edited|accepted|rejected`), vertex editing, accept -> `bboxes[photo]` + `regions[photo]`
  with no overwrite, manual `b*`/`i*` points with meanings, per-photo visibility/identity review,
  geometry-only cross-view identity candidates, undo through the existing history.
- `tools/leaflet_segmenter.py`: backends `unavailable` (default), `sam2` (lazy, checkpoint hash
  verified), `mock`. Only **prompted** `predict(box, positive, negative)` exists; there is no batch or
  automatic entrypoint, and no landmark extraction.
- `tools/serve_leaf_edit_session.py`: `/api/segmenter`, `/api/segment` (one prompt), `/api/rebuild`,
  `--patches` pass-through (added by Codex today, verified present).
- `tools/rebuild_leaf_edit_session.py`: accepted regions never enter triangulation; attached partial
  surfaces carry a depth-hash freshness contract; cuboids stay diagnostic.
- Local assets: `build/sam_trial_20260919/vendor/sam2/sam2/automatic_mask_generator.py` exists, so
  `SAM2AutomaticMaskGenerator` is available for a later authorized trial. Nothing is executed now.
- No trained tomato leaflet **detector** exists in this project. Automatic masks are class-agnostic.

## 3. Intended changes

1. **Automatic bbox drafts (class-agnostic).**
   - `leaflet_segmenter`: add `automatic(image, settings)` to the backend protocol.
     `Sam2Segmenter` gains an (unexecuted) `SAM2AutomaticMaskGenerator` path; `MockSegmenter` returns
     deterministic blobs; `UnavailableSegmenter` reports `automatic=false` with a reason.
   - Batch entrypoint over the current or explicitly selected photographs, returning per-mask
     candidates with rings, original-pixel bbox, area, model score, photo hash and settings.
   - Every candidate is an **unassigned draft**: it may be a lobe, a whole compound leaf, several
     leaflets or background. It carries no leaflet identity until a human assigns one. Small
     components are kept; overlapping candidates are never merged.
2. **Landmark candidates, separate from accepted points.**
   - Derived geometrically from an accepted/selected region ring with an explicitly named method
     (principal-axis extremum, convexity apex, inferred centerline). Stored as
     `landmark_candidates`, never as `b*`/`i*`; existing points are never moved or renamed.
   - Semantics are proposals (`distal_tip`, `lobe_apex`, `attachment_candidate`, `unknown`) and a
     guessed midrib is flagged `inferred`.
3. **Cross-view point-match proposals.**
   - Restricted to one confirmed-or-selected leaflet's own observations. Uses the existing measured
     poses: epipolar distance plus triangulation residual against the current gates; no SfM.
   - Reports `ambiguous` (several candidates within tolerance), `no_pose`, `no_candidates`,
     `high_residual` instead of forcing a match. A `point_id` is assigned only on acceptance.
4. **Review UI.** Separate lists for bbox drafts, landmark candidates and match candidates, so
   accepting an outline never implies identity or landmarks. Draft boxes/points are editable and
   deletable, undo applies, coordinates stay original pixels, and only accepted observations reach
   the rebuild.

## 4. Execution restrictions

No training, no inference, no weight download, no uploads, no PPFD run. Tests use deterministic mock
or fixed-mask backends. `config/`, `docs/`, `tomato3d/`, `tests/` untouched; existing user labels,
backups and results preserved; calibration and quality gates unchanged.

## 5. Validation plan

Deterministic tests (Node + pytest) for: overlapping leaflet candidates staying separate; small
components retained; background/wrong candidate rejectable; assignment to a leaflet never overwriting
an existing box/region; landmark candidates never becoming `b*` without acceptance and never moving
existing points; ambiguous/no-pose/high-residual match reporting; `point_id` assigned only on accept;
original pixel coordinates preserved through zoom and backup round-trip; undo for every new action;
automatic backend reported unavailable when no model is configured; stale-surface behavior unchanged.
Real-model accuracy (bbox precision/recall, landmark error, match correctness, correction time) is
**not** measured in this turn and requires a separately authorized trial.

## 6. Outcomes (after implementation)

### Delivered

- `tools/leaflet_segmenter.py`: `propose_automatic()` plus an `automatic()` backend method.
  `MockSegmenter` returns deterministic discs; `Sam2Segmenter.automatic` wires
  `SAM2AutomaticMaskGenerator` (**code path only, never executed here**; the vendored repo does
  contain `automatic_mask_generator.py`); `UnavailableSegmenter` reports `automatic=false`.
  Filters: keep >= 400 px masks (small real leaflets survive), drop masks covering > 60 % of the
  frame (background), keep overlapping masks separate, cap at 60 and report every dropped count.
  `mask_rings(..., keep_all=True)` was added because an automatic mask *is* the candidate and has
  no prompt to select a component with.
- `tools/serve_leaf_edit_session.py`: `POST /api/segment_automatic` (1-8 photographs, same token +
  Origin + loopback checks, serialized, writes nothing, 503 with a reason when the backend cannot).
- `tools/leaf_point_annotator.html`:
  - `auto_drafts` state (`draft|assigned|rejected`) with batch IDs, model provenance and history.
    A draft is `unclassified`, has no leaflet identity, is drawn amber, and is never exported.
    Assigning writes one leaflet's bbox + region (no overwrite, visibility/identity untouched);
    per-draft reject and whole-batch reject never touch assigned labels; undo covers everything.
  - `landmark_candidates` per leaflet/photo derived from an accepted region with the method
    recorded (`principal_axis_extremum`, `convex_hull_extremum`, `inferred_centerline`). Axis ends
    are proposed as `tip_or_attachment_unknown` because an outline cannot say which end is the tip;
    the guessed midrib is `inferred` and cannot be accepted as an observation. Accepting writes
    `pts[point_id]` only for a free ID and records `point_provenance`.
  - `proposePointMatches()` restricted to one leaflet, using epipolar distance + triangulation
    residual + parallax against the existing gates, reporting `eligible|ambiguous|rejected` with
    reasons, and `unavailable` for same photo / missing pose / no candidates. `acceptPointMatch()`
    writes the same `point_id` in both photos and stores the metrics and the status at acceptance.
  - Panels for each stage, drawing of drafts and candidates, help text, lazy AI-status refresh.
- `tools/rebuild_leaf_edit_session.py`: counts `auto_mask_drafts_by_state`,
  `landmark_candidates_by_state` and `accepted_point_observations_by_source`; keeps candidate lists
  out of the annotation payload; drafts never become observations.

### Validation executed

- `python -m pytest tools/tests -q`: **164 passed, 1 skipped** (baseline this turn: 154+4=158).
  New: `tools/tests/leaf_annotator_auto.test.cjs` (9 Node cases), `tools/tests/test_automatic_masks.py` (4).
- Mutation checks, each caught by the new tests: assignment overwriting an existing box; landmark
  acceptance overwriting a point; accepting the inferred midrib; ambiguity not flagged; bulk reject
  touching assigned drafts; and the epipolar, residual and parallax gates dropped individually.
  Two of these (parallax, epipolar) initially escaped and the tests were strengthened until they failed.
- Server: `/api/segment_automatic` verified over real HTTP (403 without token, 503 unavailable,
  200 with mock, 400 for unknown photo / too many photos / missing list), nothing written.
- Browser (port 8836, mock backend, storage cleared afterwards): the endpoint returned 3
  unclassified candidates for IMG_7919.png in ~2 s; `addAutoDrafts` stored them with saved labels
  unchanged; the panel listed them with assign/reject controls. **A screenshot of the new panel was
  not captured** — the tab stopped responding during the check, so no visual confirmation is claimed.
- One earlier full-suite run showed a single failure in
  `test_serve_leaf_edit_session.py::test_rejects_foreign_origin_missing_token_bad_body_and_path_escape`
  while a browser session and a local server were running in parallel; it passes in isolation and in
  two subsequent clean full runs. Treat it as interference, not a verified defect.
- 645 protected files unchanged.

### Not done / still required

- No real detector or segmentation model was run; **no accuracy, precision/recall, landmark error or
  time saving is measured**. That needs a separately authorized trial on reviewed photographs.
- Landmark candidates are geometry over an outline, not botany: they cannot distinguish tip from
  attachment, and a mask that covers several leaflets produces meaningless axis ends.
- Cross-view matching uses geometry only; appearance matching remains unimplemented, so ambiguous
  cases stay ambiguous by design.
- Automatic drafts are only as good as the backend; with `--segmenter mock` they are test shapes.
