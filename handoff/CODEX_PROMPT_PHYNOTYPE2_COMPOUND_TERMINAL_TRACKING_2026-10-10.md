# CODEX PROMPT - phynotype2: compound-leaf and terminal-leaflet tracking from top-view RGB, with generator candidates for unclear regions

Date: 2026-10-10. Author: Claude (specification). Implementer: Codex. Status: **specification, not yet implemented.**
Korean explanation for the human: `docs/phynotype2_복엽_터미널리프_추적설계_2026-10-10.md`.
This prompt is self-contained; you should not need `docs/` to implement it. If you do, report the gap in
`handoff/TODO.md` instead of guessing.

## 0. Binding rules (read first)

- Location: **all new code lives in `phynotype2/`** (user decision 2026-10-10). Tests in `phynotype2/tests/`.
  Run outputs in `build/phynotype2_<YYYYMMDD>_<NN>/`. Do not write under `data/` (human-owned; `data/records/` is
  human-written ground truth, read only). Do not edit `tomato3d/`, `tools/`, `config/`, `docs/`.
- `tomato3d/synth/` (the virtual-plant generator) and `tools/` modules are **imported read-only**. If a needed change
  can only be made inside them, stop and write it in `handoff/TODO.md`.
- `tomato3d/track/link.py` stays an unopened stub. Do not call or fill it.
- A value that cannot be measured is `unavailable` (string) - never 0, never imputed, never a dropped row.
- No magic numbers: every threshold/weight lives in `phynotype2/tracking_config_template.json` (section 9).
  **A null threshold is loaded but inactive**; the step it controls routes everything to human review.
- Tabular data CSV, metadata/config JSON. Lengths carry units in names (`_mm`, `_px`); angles `_deg` in files,
  `_rad` in code. English in code/comments/handoff.
- Inputs are never modified; every output row carries the sha256 of the source file it came from.
- **Generated geometry is never an observation.** It is never written as ground truth, never counted as a new leaf,
  never sets `first_observed_at`, never sets P3 `geometry_status = observed_axis` or `identity_status = confirmed`.

## 1. Scope

In scope:
1. Per capture: separate compound leaves and their **terminal leaflet** (the unpaired leaflet at the distal end of
   the rachis); link each terminal leaflet to its compound.
2. Across captures of one plant: keep a persistent `track_id` per compound leaf; the terminal leaflet is carried by
   its compound's track.
3. Where a compound is unclear (overlap, occlusion, segmentation failure): produce **sets of candidate full shapes**
   with the existing generator, conditioned on what is observed, keeping observed parts verbatim.
4. Re-evaluate earlier candidates when later captures show the region better.
5. Hand tracks + candidates to the next stage (structure update) through the contract in section 7.

Out of scope: persistent IDs of non-terminal leaflets (they may appear as anonymous observation instances only),
structure update, growth/emergence forecasting, training any new model.

Input assumptions: top-view RGB of one plant per photo-set, **two captures per day** (user decision 2026-10-10).
Side views, depth and the ChArUco board may be absent and must not be required. Existing multi-view/board sessions
are optional validation material only.

## 2. Existing code: reuse vs extend (verified against source 2026-10-10)

| Need | Reuse (import read-only) | Extension in phynotype2 |
|---|---|---|
| Mask storage | `tools.leaflet_mask_batch.pack_mask/unpack_mask` (lossless interval encoding) | none |
| Human review decisions | `threshold-decision-log-1` documents, loader pattern of `tools.cross_view_identity_import.load_decisions` (latest answer per `object_id` wins), collection by `tools.threshold_decisions` (fits thresholds only from >= `MIN_DECISIONS_PER_CLASS` decisions) | new `decision_detail.kind` values (sections 5.5, W5) |
| Review page pattern | `tools.cross_view_candidates` (local HTML, no server, saves one JSON) | new page for cross-capture questions |
| Image-feature mask matching | `tools.leaflet_chain_match` (SIFT + RANSAC homography per mask pair, mutual best) - pose-free | applied to consecutive captures; its accuracy on growing leaves is **unmeasured** - treat as one cue |
| Compound interior generator | `tomato3d.synth.compound_leaf.build_compound(cfg, compound, contours, seed, plant_id)` | adapter that builds the `compound` dict from observations (section 6.3) |
| Leaflet mesh | `tomato3d.synth.leaflet_surface.triangulate_contour`, `surface_points`; `normalize_contour` for observed outlines | none |
| Contour pool | `tomato3d.synth.contours.load_pool(paths)` | none |
| Generator ranges | `tomato3d.synth.config.load_generator_config`, `range_of`, `make_rng` | **do not** call `apply_measured_range` (it rewrites ranges as `measured_range`); conditioning is done by rejection/scoring, not by editing the config |
| Rendering | `tomato3d.synth.raster` (needs a board-posed `RenderGeometry`) - **not usable** without a board | own minimal top-view rasteriser (orthographic, z-buffer by triangle depth), section 6.4 |
| Downstream consumer | `tools.compound_growth.OBS_COLUMNS`, P3 association statuses in `tools.probabilistic_compound_growth` | mapping table only (section 7.6); no edits |

Facts about the generator that bound what candidates mean:
- `build_compound` needs `compound_id`, `attachment_mm` (3-vector), `direction_unit` (3-vector),
  `rachis_arc_length_mm`, `left_extent_mm`, `right_extent_mm`; it samples the interior (pairs, terminal length,
  droop, bend/roll/twist, contour per leaflet) and **rejects/redraws** samples breaking the length/extent contract.
  It returns `rachis_points_mm` and `leaflets[]` with `tag` (`T` = terminal, `P<i><L|R>`, `I<j>`), `kind`,
  `length_mm`, `base_mm`, `heading`, `left`, `up`, angles, `contour_index`, and `params`.
- It needs the `tomato_synth` environment (L-Py/PlantGL). Run the adapter only there.
- **Every range in `tomato3d/synth/generator_config_template.json` is `source_kind = user_assumed`**, and the
  generator's realism gate (C6) has not been passed. Candidates are hypotheses with assumed priors - report this in
  every candidate manifest (`prior_status = "user_assumed_unvalidated"`).

## 3. Frames, scale and capture metadata

### 3.1 Plant image frame (2-D)
Per capture, a similarity transform image px -> plant frame mm: origin at the pot centre, +X toward the pot
orientation mark, +Y 90 deg counter-clockwise seen from above, units mm at the **pot-rim plane**.
- Pot centre and px/mm from the pot rim (ellipse fit or human 3-point click). Pot rim diameter comes from a human
  constant (`pot_rim_inner_diameter_mm`); if absent, `scale_status = unavailable` and all `_mm` fields are
  `unavailable` (pixel fields still produced).
- Rotation from the orientation mark (human click or detector); if absent, `rotation_status = unavailable` and
  azimuth cues are disabled for that capture pair (section 5.2).
- Leaves sit above the rim plane, so `_mm` values are **rim-plane-projected** and biased; never call them true sizes.
Table `frame_transforms.csv`: `plant_id, capture_id, image_sha256, center_x_px, center_y_px, mm_per_px,
rotation_deg, scale_status, rotation_status, method, reviewer, note`. Status values: `measured`, `human_clicked`,
`unavailable`.

### 3.2 Captures
`captures.csv`: `plant_id, capture_id, image_file, image_sha256, captured_at (ISO 8601 with offset),
time_since_lights_on_min, photoperiod_phase (am|pm|unavailable), camera_setup_id, plant_roi_status, note`.
`time_since_lights_on_min` is needed because AM/PM captures differ in leaf posture; if lighting times are not
recorded it is `unavailable`, never guessed from the clock.

## 4. Per-capture observations, terminal leaflet and membership

### 4.1 Observation instances (input layer)
Segmenter-agnostic: masks may come from a future top-view detector, SAM-assisted boxes, or human drawing.
`observations.csv`: `plant_id, capture_id, obs_id, obs_class (compound_leaf|terminal_leaflet|leaflet|stem|other),
mask_ref (file#key, packed mask), area_px, bbox_xyxy_px, source (model id+sha256 | human), source_score,
review_state (accepted|edited|rejected|unreviewed), touches_other_mask (bool), touches_image_border (bool),
plant_attribution (this_plant|neighbor|uncertain)`.
- Neighbour leaves intrude in dense blocks: only `plant_attribution = this_plant` enters tracking; `uncertain` goes
  to review. No automatic attribution rule is declared yet (null threshold).
- Only `accepted`/`edited` masks are used. Unreviewed masks may be used for proposals shown to a person, never for
  confirmed rows.

### 4.2 Terminal leaflet identification
A terminal leaflet is the distal, unpaired leaflet of a compound. Evidence, in order of authority:
1. human label (`terminal_leaflet` class or review decision);
2. detector class `terminal_leaflet`, if a reviewed model exists;
3. geometric proposal: within one compound mask, the leaflet instance farthest from the compound's attachment side
   along the compound's principal axis and without a mirror-side partner at the same axial station. Proposal only.
`terminal_status` per compound per capture: `observed_confirmed`, `observed_proposed`, `not_visible`
(compound visible but rachis tip hidden), `undetermined` (conflicting evidence). Never infer a terminal leaflet
from the generator.

### 4.3 Membership
`memberships.csv`: `plant_id, capture_id, child_obs_id, parent_obs_id (or unassigned), membership_status
(confirmed|proposed|unassigned), evidence (human|containment|adjacency), containment_fraction, reviewer`.
A terminal leaflet with containment in two compound masks, or in none, is `unassigned` - never assigned by nearest
centroid. Only `confirmed` memberships are passed downstream as membership.

## 5. Cross-capture association

### 5.1 Unit and memory
Association unit = compound leaf. Each plant keeps a track bank: every track not `removal_confirmed`, with its last
accepted observation, best (largest unoccluded) observation, terminal outline if any, and history. A new capture is
matched against **all** live tracks, not only those seen in the previous capture (so reappearance is possible).

### 5.2 Pair cues (all reported; none silently dropped)
For each (live track, compound observation) pair, `match_candidates.csv` stores:
- `d_azimuth_deg`: wrap-safe difference of the compound's terminal (or distal-end) azimuth around the pot centre;
  `unavailable` if either capture lacks rotation.
- `d_radial_mm` / `d_radial_px`: change of distal-end distance from the centre (growth makes this asymmetric:
  report signed).
- `d_base_azimuth_deg`: azimuth of the compound's proximal end (closest point to centre).
- `shape_terminal`: outline distance between terminal leaflets after `normalize_contour` (scale/rotation removed),
  `unavailable` if either terminal is not observed.
- `shape_compound`: outline descriptor distance of compound masks (report the descriptor name/version).
- `feature_inliers`: `tools.leaflet_chain_match`-style SIFT+RANSAC inlier count between the two masks.
- `order_consistency`: whether assigning this pair preserves the cyclic azimuth order of already-confirmed tracks
  (bool/unavailable).
- `dt_h`, `same_phase` (am-am / pm-pm), `gap_captures` (captures since the track was last observed).
No combined weight is fixed by this prompt. Config field `association.weights` is null at start.

### 5.3 Assignment
Per plant per capture: Hungarian assignment on a cost matrix augmented with "no match" rows/columns
(`association.no_match_cost`, null at start). While any required weight/threshold is null, the solver still runs to
**rank proposals**, but every link is written as `proposed` and sent to review. A link becomes `confirmed` only by
(a) a human decision, or (b) an automatic rule whose thresholds were fitted from >= `MIN_DECISIONS_PER_CLASS`
human decisions per class (via `tools.threshold_decisions`) and recorded with its fit manifest.
Also report, per observation, the margin between best and second-best cost; a small margin is `ambiguous`
(threshold null -> all to review).

### 5.4 Track states per capture (contract vocabulary)
`track_states.csv`: one row per (live track, capture), including tracks with no observation.
| `state` | meaning | required evidence |
|---|---|---|
| `continued` | observed now and in the previous capture of this plant | confirmed link |
| `unobserved` | track alive, no observation now; `unobserved_reason` in `occluded`, `not_detected`, `out_of_frame`, `unknown` | `occluded` only with a human decision or a confirmed covering observation; default `unknown` |
| `reappeared` | observed now after >= 1 `unobserved` capture; `gap_captures` filled | confirmed link |
| `first_observed` | observation not linked to any existing track; new track opened | **not an emergence date**; `emergence_interval` = (previous capture time, this capture time] is reported as an interval only |
| `removal_confirmed` | track closed | only from `data/records/manual_events.csv` (`leaf_removed`, `organ_lost`) joined through `organ_label_map.csv`, or a destructive-protocol step record; never from absence |
| `ambiguous` | two or more competing links, or an unresolved split/merge | track keeps its last confirmed identity; no new ID is issued for the contested observation |
Columns: `plant_id, capture_id, track_id, state, obs_id (or unavailable), link_status (proposed|confirmed),
unobserved_reason, gap_captures, emergence_interval_start, emergence_interval_end, evidence_ref, config_hash`.

### 5.5 Split / merge and human correction
- Fragment suspect: two observations whose best match is the same track and whose union explains that track better
  than either alone -> `event_type = fragment_suspect`.
- Merge suspect: one observation that is the best match of two tracks -> `event_type = merge_suspect`.
- Neither is resolved automatically. Review decisions (work order W5) can declare `fragment_of`, `merged_of`, `not_leaf`,
  `neighbor_plant`, `same`, `different`, `terminal_is`, `membership`.
- **IDs are never renumbered.** A correction is an event (`events.csv`: `event_id, plant_id, capture_id,
  event_type, track_ids, obs_ids, decision_ref, created_at`). Event types also include `rename_same_organ`
  (with `previous_id`, `observed_id`, matching P3 lineage kind `same_organ_rename`) and `track_merge` (two tracks
  found to be one organ: the later ID is retired, pointing to the kept ID).
- A correction re-runs association from the affected capture forward into a **new run folder**; old runs are kept.

## 6. Unclear compounds: generator candidates

### 6.1 When a compound is "unclear"
Per (track, capture), `completion_needed = true` when any holds: `touches_other_mask`, `terminal_status` in
(`not_visible`, `undetermined`), visible area below `completion.visible_area_ratio_vs_best` times the track's best
earlier observation (null -> use human flag only), segmentation `review_state = edited` with a reviewer note
"incomplete", or a human flag. Reason codes are listed in the row.

### 6.2 Conditioning inputs (what the generator is told)
- The current visible compound mask (pixels that **must** be explained by every kept candidate).
- The terminal leaflet mask and normalized outline if observed (constrains terminal length and contour choice).
- The track's earlier observations: best earlier mask, its `dt_h` before this capture, earlier terminal outline.
- Plant frame transform (scale, rotation) from section 3.1.
Not inputs: other tracks' generated candidates, any forecast.

### 6.3 Building the `compound` dict (lift 2-D -> 3-D, explicitly assumed)
Sampled per candidate, each value tagged with its source:
- `attachment_mm`: (0, 0, z) on the stem axis; z sampled from the generator's stem ranges (assumed).
- `direction_unit`: azimuth from the observed proximal->distal axis (observed, with its angular spread);
  elevation from `leaf_elevation_deg` (generator range, user_assumed).
- `rachis_arc_length_mm`: observed projected axis length / cos(elevation), plus the hidden part implied by the
  earlier observation (if any); never shorter than the observed visible axis.
- `left_extent_mm`, `right_extent_mm`: max(observed lateral reach, earlier observation reach), widened by
  `completion.extent_slack_rel` (null -> use generator range).
If `scale_status = unavailable`, no candidates are generated (`candidate_status = unavailable_no_scale`).

### 6.4 Generate, project, score
1. For seeds `0..completion.n_samples-1` (null -> step disabled), call `build_compound` with the unmodified
   generator config and the pooled contours. If an observed terminal outline exists, choose `contour_index` by
   outline distance (report the distance) instead of uniform sampling - this is an adapter-side override recorded
   per candidate (`terminal_contour_source = observed_match`), not a config edit.
2. Mesh each leaflet (`triangulate_contour`, `surface_points`), place in the plant frame, project orthographically
   onto the top image (scale/rotation from 3.1), z-buffer by triangle depth -> candidate amodal mask, candidate
   visible mask given the other observed masks as occluders (treat other accepted masks as in front where they
   overlap the candidate; this is an assumption and is recorded).
3. Score components (all reported): `observed_coverage` (fraction of observed visible pixels covered by the
   candidate amodal mask), `background_violation` (fraction of candidate visible pixels on observed non-plant
   background), `terminal_outline_distance`, `earlier_shape_consistency` (vs best earlier observation, with `dt_h`).
4. Keep candidates passing hard checks: observed coverage == all observed pixels within the rasterisation tolerance
   `completion.coverage_tolerance_px` (null -> report only), and background violation <= its threshold (null ->
   report only). Keep up to `completion.max_kept` ranked candidates. **Do not select one.** A ranking is not a
   probability; `relative_weight` is written only if a calibration manifest exists, else `unavailable`.

### 6.5 Preserve observed parts
The final per-capture geometry is a union of labelled regions: `observed` (accepted mask pixels, verbatim),
`generated` (candidate pixels outside the observed mask), `conflict` (candidate disagrees with an observed
boundary - candidate discarded). Every downstream geometry carries `geometry_source` in
(`observed`, `generated_candidate`) at pixel/region level, never a mixed undeclared value.

### 6.6 Re-evaluation when later captures show more
For each earlier candidate set, when a later capture of the same track has newly visible area in the region that
was `generated`, write `candidate_reassessment.csv`: `plant_id, track_id, candidate_set_id, candidate_id,
later_capture_id, dt_h, newly_visible_px, iou_in_newly_visible_region, terminal_tip_error_mm (or unavailable),
verdict (consistent|inconsistent|undecidable), growth_confounded (bool: dt_h > completion.reassess_max_dt_h, null
-> always true)`. Earlier candidate files are never edited; the reassessment points at them. The later observation
replaces generated regions for that later capture only.

## 7. Output contract to the structure-update stage

Run folder `build/phynotype2_<YYYYMMDD>_<NN>/<plant_id>/`, plus `manifest.json` (inputs with sha256, config
hash, code version, generator config hash, `prior_status`).

7.1 `tracks.csv`: `plant_id, track_id, organ_class (compound_leaf), created_capture_id, first_observed_at,
last_observed_at, status (live|removal_confirmed|retired_merged_into:<id>), human_label (organ_label or unavailable),
order, rank, rank__status, rachis_bend_type, rachis_bend_type__status`. Rank/order/bend follow
`handoff/MTG_CONVENTION_2026-10-10.md` (rank 1 = lowest leaf of the plant at its rank reference capture; never
renumbered). From top view alone all three are `unavailable`/`unknown`; they are filled only from a human record
or a side-view reconstruction, with their status.
`track_id` format: `<plant_id>/C<4-digit serial>`; serials are issued in creation order and never reused.
This `track_id` is the CompoundLeaf `vertex_id` of the MTG convention (same string).
The terminal leaflet has no own track; its rows use `track_id` of its compound and `part = terminal_leaflet`.

7.2 `track_states.csv` (section 5.4). 7.3 `events.csv` (section 5.5).

7.4 `observed_geometry.csv`: one row per (track, capture, part in {compound, terminal_leaflet}):
`mask_ref, area_px, area_rim_plane_mm2 (or unavailable), distal_xy_mm, proximal_xy_mm, axis_azimuth_deg,
projected_axis_length_mm, terminal_status, membership_status, geometry_source = observed`.

7.5 `candidates.csv` + `candidate_sets/<candidate_set_id>.json`: `candidate_set_id, plant_id, track_id,
capture_id, completion_reasons, n_generated, n_kept, prior_status, generator_config_hash, contour_pool_sha256,
candidate_status (kept|rejected|unavailable_no_scale|disabled)`; per candidate: `candidate_id, seed, attempt,
compound_dict (with per-field source tags), params, amodal_mask_ref, generated_region_mask_ref, score components,
rank, relative_weight (or unavailable), mesh_ref (OBJ, plant frame mm)`.

7.6 Mapping to the existing P3 consumer (no change to P3 code):
| phynotype2 | `tools.compound_growth` / P3 |
|---|---|
| `track_id` | `compound_leaf_id` |
| state `continued`/`reappeared` with `link_status = confirmed` | association `confirmed`, `identity_status = confirmed`, `identity_scope = cross_date_same_organ` |
| `unobserved` + reason `occluded` (human-confirmed) | `occluded` |
| `unobserved` + any other reason | `missed` |
| `first_observed` | `unmatched`; `first_observed_at` = capture time (not emergence) |
| `ambiguous` or `link_status = proposed` | `ambiguous` |
| `removal_confirmed` | no association status; passed as an event; the consumer must stop forecasting that ID |
| `fragment`/`merge` unresolved | identity `change` = `split`/`merged` -> P3 returns `organ_lineage_mapping_unsupported` (expected) |
| `rename_same_organ` event | lineage `kind = same_organ_rename` |
| any generated geometry | never `geometry_status = observed_axis` |
The design skeleton's `tracks.csv` vocabulary (`new, continued, reappeared, removed, ambiguous`) maps as
`new -> first_observed` (meaning changed: not emergence), `removed -> removal_confirmed` (evidence now required),
and has no equivalent of `unobserved` - phynotype2 output supersedes it for this stage; the skeleton file is not
edited.

## 8. Validation

8.1 Human ground truth (human writes; Codex supplies header-only templates in the run folder, never in `data/`):
`manual_track_labels.csv`: `plant_id, capture_id, obs_ref (image file + human polygon or obs_id),
human_organ_label, part (compound|terminal_leaflet), parent_human_label (for terminal), visibility
(full|partial|not_visible), labeled_by, labeled_at`. Human labels are a separate namespace, joined via
`organ_label_map.csv` rules (never merged into `track_id`).

8.2 Metrics (report per plant and pooled, stratified by `gap_captures`, `same_phase`, block density, dt_h):
- ID errors: identity switches (a GT organ's assigned track changes between captures), fragmentations
  (one GT organ -> two tracks), merges (two GT organs -> one track). Counts and per-organ-capture rates.
- Reconnection after occlusion: for GT organs with >= 1 unobserved capture, fraction re-linked to the same track
  on reappearance, by gap length.
- First-observed judgement: precision/recall of `first_observed` against GT "organ not present in any earlier
  GT capture of this plant". Explicitly NOT an emergence-date metric.
- Membership: confusion matrix of terminal->compound links (correct / wrong / unassigned), with abstention rate.
- Candidates vs later observations: IoU in newly visible region, terminal tip error (mm, rim-plane), and set
  coverage (any kept candidate consistent), against two baselines: (a) persistence = best earlier observed mask
  carried forward, (b) observed-only (no completion). Report growth-confounded rows separately.
- Standard MOT scores (HOTA/IDF1) may be reported for comparison only; no acceptance threshold is declared here.
No pass/fail number is set by this prompt. Thresholds are declared by the human before results are viewed.

8.3 Splits: plant-disjoint and time-forward. All captures of a plant stay in one split.

8.4 Test material, by what each can test:
- Week-1 repeat pair (re-take without touching): no change -> any switch is an error; noise floor of all cues.
- Plant 1 sequential defoliation (destructive protocol): same-day occlusion change with known removal ->
  reconnection, `removal_confirmed` path; no growth.
- Twice-daily series of the density cohort, once captured and labelled: the real test.
- dwt_01-04 (2026-09-20/21, board sessions): optional validation only, **pending user approval** (they were
  declared droppable on 2026-10-09).
- Generator-made synthetic sequences: software tests only, never accuracy claims.

## 9. Config template `phynotype2/tracking_config_template.json`
Every entry: `value` (null allowed), `unit`, `source_kind` (`user_stated`|`fitted`|`unset`), `source_ref`.
Required keys: `pot_rim_inner_diameter_mm`, `association.weights` (object of per-cue weights),
`association.no_match_cost`, `association.ambiguity_margin`, `association.max_gap_captures` (null = never drop),
`attribution.neighbor_rule`, `completion.visible_area_ratio_vs_best`, `completion.n_samples`,
`completion.max_kept`, `completion.coverage_tolerance_px`, `completion.background_violation_max`,
`completion.extent_slack_rel`, `completion.reassess_max_dt_h`. All null except where the user states a value.

## 10. Work orders (each: files, functions, inputs, outputs, pass criteria = software checks only)

W0 Skeleton: `phynotype2/schemas.py` (column tuples above, vocabularies, `UNAVAILABLE`), `phynotype2/config.py`
(load/validate template; null = inactive), validators that reject unknown states/statuses. Pass: unit tests for
every vocabulary and for null-threshold behaviour.

W1 Captures & frames: `phynotype2/frames.py::fit_rim(image) -> proposal`, `human_click_page(...)`,
`build_frame_transforms(...)`. Pass: synthetic ellipse fixtures recover centre/scale; missing diameter -> all mm
fields `unavailable`.

W2 Observation import: `phynotype2/observations.py::import_masks(source, ...)` from a leaflet-mask batch, a
Roboflow/COCO export, or human masks; plant attribution review page. Pass: round-trip with `pack_mask`, sha256 per
row, rejected masks excluded.

W3 Terminal & membership: `phynotype2/membership.py::propose_terminal(...)`, `assign_membership(...)`. Pass:
fixtures with two-compound containment -> `unassigned`; no geometric proposal written as `confirmed`.

W4 Association: `phynotype2/associate.py::pair_cues(...)`, `assign(...)`, `track_states(...)`. Pass: wrap-safe
azimuth tests; reappearance after 3 empty captures; null weights -> all links `proposed`; removal only from
records; IDs never renumbered across re-runs.

W5 Review loop: `phynotype2/review.py` page + `import_decisions(...)` using `threshold-decision-log-1` with new
kinds (`same`, `different`, `fragment_of`, `merged_of`, `terminal_is`, `membership`, `neighbor_plant`,
`not_leaf`, `occluded`). Pass: conflicting decisions reported, not merged; latest answer wins per object.

W6 Generator adapter (tomato_synth env): `phynotype2/completion.py::compound_dict_from_observation(...)`,
`generate_candidates(...)`, `rasterize_top(...)`, `score_candidate(...)`. Pass: on a synthetic plant whose full
masks are known, occluding part of one compound -> every kept candidate covers all observed pixels; generator
config file hash unchanged after the run; candidates never appear in `observed_geometry.csv`.

W7 Reassessment: `phynotype2/reassess.py`. Pass: earlier candidate files byte-identical after reassessment.

W8 Evaluation: `phynotype2/evaluate.py` computing section 8.2 from `manual_track_labels.csv`. Pass: hand-built
fixture with one known switch, one fragmentation, one reappearance gives exactly those counts.

W9 Export: `phynotype2/export.py` writing section 7 tables and the P3 mapping view (column names exactly
`tools.compound_growth.OBS_COLUMNS`). Pass: schema validators; generated rows are absent from the P3 view. Top-view
geometry has no measured height, so axis/extent tables P3 needs are written as `unavailable` where z is unknown;
if the P3 loader rejects the view, report its reason in handoff/TODO.md - do not fabricate z or edit P3.

## 11. Open items for the human (do not guess)
1. Pot orientation mark: does every pot carry one, and where? (rotation cue)
2. `pot_rim_inner_diameter_mm`: measured value per pot type.
3. Lights-on time per day (for `time_since_lights_on_min`).
4. Source of top-view masks until a reviewed top-view detector exists (human, SAM-assisted, or wait).
5. Whether dwt_01-04 may be used as optional validation.
6. Who writes `manual_track_labels.csv`, for which plants/captures, before evaluation is run.
