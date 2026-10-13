# Stage 2 — Current plant structure update: implementation contract for Codex

Date: 2026-10-10
Author: Claude Code
Status: **Specification only. Not an implementation authorization.**
Requested by: `handoff/PROMPT_STRUCTURE_UPDATE_SPEC_2026-10-10.md`
Korean companion: `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10_KO.md`

Scope: take the per-organ tracking output of phynotype2 and maintain a dated MTG snapshot of the
current plant structure. Stage 1 (capture/calibration) is upstream; new-organ and growth prediction
is Stage 3 and out of scope here.

---

## 0. Files read, and files that do not exist

Read in the order the request gave:

| # | File | Size | Read |
|---|---|---|---|
| 1 | `../공통규약.md` (parent folder, outside the project) | 7,511 B | full — path exists, contrary to the request's caveat |
| 2 | `CONVENTIONS.md` | 9,000 B | full |
| 3 | `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md` | 17,600 B / 397 lines | full |
| 4 | `handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md` | 28,823 B / 366 lines | full |
| 5 | `handoff/MTG_CONVENTION_2026-10-10.md` | 9,122 B / 138 lines | full |
| 6 | `handoff/CLAUDE_CODE_CLI_PROMPT_MTG_AMEND_2026-10-10.md` | 4,757 B / 65 lines | full |
| 7 | `docs/복엽구조_형태_2026-10-10.md` | 6,354 B / 96 lines | full |
| 8 | `docs/phynotype2_복엽_터미널리프_추적설계_2026-10-10.md` | 9,187 B / 137 lines | full |
| 9 | `phynotype2/README.md` | 1,955 B / 34 lines | full |
| 10 | `handoff/TOMATO_3D_PHENOTYPING_ALGORITHM_SKELETON_2026-09-15.md` | 29,489 B | partial (superseded-vocabulary section) |
| 11 | `tomato3d/` — `graph/{nodes,connectivity,skeleton,keypoints}.py`, `track/link.py`, `organ/*`, `pheno/measure.py`, `synth/{leafarea,leafarea_inputs,compound_leaf,structure,leaflet_surface,contours}.py`, `io/{schemas,tables}.py`, `calib/{board,pose}.py`, `mask/silhouette.py` | — | full or symbol-level, per module |
| 12 | `tools/` — `plant_structure.py`, `leaf_area_geometry.py`, `multiview_plant.py`, `multiview_completion.py`, `leaflet_chain_match.py`, `cross_view_candidates.py`, `compound_growth.py`, `probabilistic_compound_growth.py`, and 10 further leaf-area/extent modules | — | headers + symbol outlines |
| 13 | `data/records/` — `env_light_20261010/`, `plant_registry/`, `compound_bend_types_20261010/`, `density_timeseries_20261009/`, `destructive_capture_20261008/` | — | headers and row counts only; never written |
| 14 | `handoff/LOG.md` | — | recent entries |

**Named in the request but absent from disk** (nothing was substituted silently):

| Missing | Consequence for this spec |
|---|---|
| `phynotype2/SCHEMA.md`, `phynotype2/PROTOCOL.md` | `phynotype2/` holds only `README.md`. The tracking stage is **not implemented**. Its contract exists only as document #4. |
| `phynotype2/tracking_config_template.json` | Required by §9 of document #4 as the single home of every threshold; does not exist. |
| A phynotype2 `captures.csv` instance | The only `captures.csv` on disk is `build/observation_records_20261001/captures.csv` — a different, older file (`plant_id,captured_at,session_id,image_file`, 0 data rows, no `capture_id`). Not used. |
| `handoff/NOTE_TO_CODEX_GENERATOR_FIXED_API_2026-10-10.md` | Read `handoff/CLAUDE_CODE_CLI_PROMPT_S_GENERATOR_FIXED_TERMINAL_2026-10-10.md` instead; substitution recorded here. |
| `data/records/manual_events.csv`, `data/records/organ_label_map.csv` | **Blocks two mechanisms**: `removal_confirmed` (document #4 §5.4 admits no other evidence) and every human-label join. |
| `claude/MTG_기준_2026-10-10.md`, `claude/복엽구조_형태_2026-10-10.md` | The `claude/` directory does not exist. Document #5 cites both. The second resolves to `docs/복엽구조_형태_2026-10-10.md` (same basename, different directory) — path mismatch flagged, not assumed. |
| The 9 source photographs behind `compound_bend_types_20261010` | Only a contact-sheet PNG is on disk; `docs/복엽구조_형태_2026-10-10.md:4` says the photos exist "in chat only". |

---

## 1. Authority split — who is the source of what

The request assumes phynotype2 §7 is the single organ-level input. It is the single source of **track
identity**, not of everything identity-related. Bind these and nothing else:

| Concern | Sole authority | Notes |
|---|---|---|
| Track identity, track state, per-capture observed geometry | document #4 §7 (`tracks.csv`, `track_states.csv`, `events.csv`, `observed_geometry.csv`, `candidates.csv`) | Stage 2 never mints an organ id |
| Vertex identity, scales, connection symbols, rank/order semantics, candidate segregation | document #5 + #6 (MTG convention and its amendment) | |
| Capture-level frame, scale and time | document #4 §3 (`captures.csv`, `frame_transforms.csv`) | |
| Human organ labels | `organ_label_map.csv` (absent) | separate namespace, never merged into `track_id` |
| Units, `unavailable`, CSV/JSON split, `data/records/` read-only, folder ownership | document #3 + #2 | |

**`track_id` *is* the MTG `CompoundLeaf` `vertex_id`** — the same string, not a mapping
(document #4 §7.1). Grammar: `<plant_id>/C<4-digit serial>`, issued in creation order, never reused.
The terminal leaflet has no track of its own; its rows reuse the compound's `track_id` with
`part = terminal_leaflet`.

---

## 2. Inputs

Required, all produced by phynotype2 under `build/phynotype2_<YYYYMMDD>_<NN>/<plant_id>/`:

- `tracks.csv` — `plant_id, track_id, organ_class, created_capture_id, first_observed_at,
  last_observed_at, status (live|removal_confirmed|retired_merged_into:<id>), human_label, order,
  rank, rank__status, rachis_bend_type, …`
- `track_states.csv` — `plant_id, capture_id, track_id, state, obs_id, link_status (proposed|confirmed),
  unobserved_reason, gap_captures, emergence_interval_start, emergence_interval_end, evidence_ref,
  config_hash`. States: `continued, unobserved, reappeared, first_observed, removal_confirmed, ambiguous`.
- `observed_geometry.csv` — one row per (track, capture, part ∈ {compound, terminal_leaflet}):
  `mask_ref, area_px, area_rim_plane_mm2 (or unavailable), distal_xy_mm, proximal_xy_mm,
  axis_azimuth_deg, projected_axis_length_mm, terminal_status, …`
- `captures.csv` — `plant_id, capture_id, image_file, image_sha256, captured_at (ISO 8601 + offset),
  time_since_lights_on_min, photoperiod_phase (am|pm|unavailable), camera_setup_id, plant_roi_status, note`
- `frame_transforms.csv` — `center_x_px, center_y_px, mm_per_px, rotation_deg, scale_status,
  rotation_status, method, reviewer`
- `candidates.csv` + `candidate_sets/*.json` — generation candidates, never observations.

Optional, used **only if the file exists**: Stage-1 `poses.csv` / `session_manifest.json` for a
board session; side-view or board-free-3D (Q2) results; `data/records/*` ground truth.

Stage 2 **must not** require any of the optional inputs, and must not construct a step whose only
purpose is to consume a file that does not exist.

### Facts the design may rely on

1. The default top view is a hand-held phone photo — perspective, not orthographic; error grows
   toward the frame edge.
2. Leaf angle follows a daily cycle. Two captures at different `time_since_lights_on_min` must never
   have their angle or projected-area difference read as growth.
3. The six plants of other varieties are shading neighbours only (plant-scale MTG); they are never
   attached to the Micro-Tom track.
4. A board is not required. When two independent scale sources exist, cross-check them: **disagreement
   > 5 % ⇒ stop and report**, never average.

---

## 3. Coordinate frames and scale

Neither upstream document grants Stage 2 one authoritative frame, and the two frames are not
interchangeable. **The frame is a recorded per-capture value, never a global constant.**

| Frame token | Authoritative when | Produced by |
|---|---|---|
| `board_mm` | the capture contains a printed board of the variant declared in that session's manifest **and** `pose_status = solved` | Stage 1 `poses.csv` |
| `plant_local_mm` | board-free capture with a usable pot rim | `frame_transforms.csv` (document #4 §3.1) |
| `image_px` | neither of the above | always available |

Rules:

1. Every Stage-2 row carrying a coordinate, length, area or angle also carries its `frame` token
   explicitly. Never defaulted, never omitted, never inferred at read time.
2. `plant_local_mm` values are **rim-plane projections**. Document #4 §3.1 states the only published
   bias: leaves sit above the rim plane, so every `_mm` value is projected and biased, and must never
   be called a true size. No magnitude or direction is published — so no correction may be applied.
3. **No transform between `board_mm` and `plant_local_mm` exists.** It is not recoverable from
   anything on disk and not identifiable from one board-free top view. Do not write one.
4. Stage 1's "cross-date comparison needs no registration step" holds **only under its own premise**
   (a board rotating with the plant). For board-free capture it does not apply. The registration that
   board-free capture needs is already placed: `frame_transforms.csv` registers **each capture
   independently** to a physical reference on the plant. Stage 2 performs **no** pairwise cross-date
   alignment and contains no registration code.
5. `scale_status = unavailable` ⇒ no millimetre value is written anywhere, and no candidates are
   generated (`candidate_status = unavailable_no_scale`, document #4 §6.3).

**Today `scale_status` is `unavailable` for every plant**: no `pot_rim_inner_diameter_mm` has ever
been measured. Consequence: a conforming Stage-2 run currently emits **zero** physical-unit values.
That is the correct behaviour, not a defect.

---

## 4. Provenance and the three area kinds

Use the MTG convention's state vocabulary; add nothing. Every value carries `<attr>__status` with
one of: `observed`, `model_estimated`, `generated_candidate`, `unavailable`.

Never promote across these. A previous capture's `model_estimated` value does not become `observed`
when a new capture arrives; it is replaced only by a new `observed` value of its own capture.

Three distinct area quantities, never collapsed into one column:

| Column | Meaning | Unit | Preconditions |
|---|---|---|---|
| `visible_projected_area_px` | accepted-mask pixel count, as reviewed | px² | mask review state `accepted`; a declared `area_basis` |
| `visible_projected_area_rim_mm2` | the same area on the rim plane | mm² | `scale_status = solved` **only**; otherwise `unavailable` |
| `completed_projected_area_rim_mm2` + `…_interval_low/high` | occlusion-completed estimate | mm² | candidate set with `candidate_status = kept`; reported as an interval, never a point value |
| `true_surface_area_mm2` | real leaf surface | mm² | **not producible at this stage** — always `unavailable` (see §5 item 4) |

A compound leaf's outer envelope is **never** treated as opaque leaf area. Light computation consumes
per-leaflet surfaces only; the envelope is a bounding construct.

---

## 5. Identifiability from one top view — what the updater may write

Derived adversarially; the weaker verdict was taken wherever evidence was thin. `W` = writable now,
`—` = must be `unavailable`.

| # | Quantity | Verdict | W | Blocking reason |
|---|---|---|---|---|
| 1 | visible projected area, px² | identifiable | W | needs a declared `area_basis` + accepted mask |
| 2 | the same in mm² | not identifiable | — | no pot-rim diameter measured ⇒ `scale_status = unavailable` |
| 3 | occlusion-completed projected area | multiple candidates | — | no scale ⇒ no candidates generated at all |
| 4 | true leaf surface area | not identifiable | — | needs per-leaflet 3-D surface; no flattened reference photos exist |
| 5 | leaflet surface tilt (signed, + = up) | not identifiable | — | **undefined** in `docs/복엽구조_형태_2026-10-10.md`; sign degenerate in a near-vertical view |
| 6 | petiole insertion angle | not identifiable | — | **undefined** — no definition, symbol, reference plane or value anywhere |
| 7 | rachis bending angle θ | not identifiable | — | both documents state `rachis_bend_type = unknown` from top view |
| 8 | leaflet curvature | not identifiable | — | **undefined**; listed as an open item |
| 9 | organ height above the rim plane | not identifiable | — | one view is a cone; depth unbounded along the ray |
| 10 | attachment of a leaf with hidden petiole/stem | multiple candidates | — | contract already prescribes `unassigned`; human-label path blocked (`organ_label_map.csv` absent) |
| 11 | node rank of a new leaf | not identifiable | — | MTG convention: `rank = unavailable` whenever the stem position is not established — "always the case from top view alone" |
| 12 | growth vs diurnal movement | not identifiable | — | lights-on clock time is null ⇒ `time_since_lights_on_min = unavailable` |

Items 5, 6 and 8 are blocked on a **human definition**, not on data. Do not invent one; do not fit a
model to an undefined quantity.

`tomato3d/synth/leafarea.py::fit_correction` holds only the model **form**
`flat_aspect / projected_aspect = a + b·sin(camera_elevation)` (leafarea.py:420). **No fitted
coefficients exist on disk.** It may not be used as a correction, only as a future fitting target.

---

## 6. Outputs

Write under `build/structure_<YYYYMMDD>_<NN>/<plant_id>/`. A new run folder per run; old runs are kept
(document #4 §5.5). Never write into a phynotype2 run folder, `config/`, `data/records/`, `docs/`, or
`tomato3d/`.

```
build/structure_<YYYYMMDD>_<NN>/<plant_id>/
  manifest.json                 inputs with sha256, config hash, code version, upstream run id
  mtg_vertices.csv              one row per vertex per snapshot    (MTG convention schema + §7 additions)
  mtg_edges.csv                 `<` and `+` edges; `/` lives in mtg_vertices.complex_id
  structure_state.csv           per (capture_id, vertex_id) observed/estimated state
  area_estimates.csv            the four area columns of §4, each with its __status
  attachment_candidates.csv     competing parents when attachment is unknown
  change_log.csv                what this run changed versus the previous snapshot, and why
  unresolved.csv                every value left `unavailable`, with its blocking reason
```

Raw observation is **not** copied and **not** overwritten: `structure_state.csv` references upstream
rows by `(capture_id, track_id, part, obs_id)` and `mask_ref`. The dated estimate layer and the raw
observation layer stay in separate run folders, joined by id.

Required columns added by this stage (every one carries a `__status` sibling where it is a value):

- `mtg_vertices.csv`: `frame` (§3, mandatory), `snapshot_capture_id`, `vertex_id`, `scale`,
  `class`, `complex_id`, plus the convention's geometry attributes (`base_xyz_mm`, `tip_xyz_mm`,
  `length_mm`, `width_mm`, `area_mm2`, `azimuth_deg`, `elevation_deg` signed, `normal_xyz`).
- `structure_state.csv`: `plant_id, capture_id, vertex_id, part, upstream_track_state, link_status,
  time_since_lights_on_min, photoperiod_phase, frame, scale_status, evidence_ref`.
- `change_log.csv`: `plant_id, from_capture_id, to_capture_id, vertex_id, attr, old_value,
  old_status, new_value, new_status, rule_applied, evidence_ref`.

`elevation_deg` follows amendment A1.4: angle above the horizontal plane of the row's `frame`,
+ = upward, range −90..+90, computed `atan2(dz, hypot(dx, dy))`; never `abs()`.

---

## 7. Update and retention rules

1. **IDs are never renumbered or reused.** A correction re-runs from the affected capture forward into
   a new run folder.
2. **No status promotion.** `model_estimated → observed` is forbidden; so is filling an `unavailable`
   from a neighbouring capture, a model prior, or a generator range.
3. **Generated candidates never enter the main snapshot.** Each candidate set is a separate sub-MTG
   (`candidate_id`) rooted at the same `CompoundLeaf` `vertex_id`, with every value
   `generated_candidate` (document #5 §7). A candidate never sets `first_observed_at`, never counts as
   a new leaf, never becomes ground truth.
4. **Attachment abstention.** A child contained in two parent masks, or in none, is `unassigned`;
   write the competing parents to `attachment_candidates.csv` and leave the edge out of `mtg_edges.csv`.
5. **Rank.** `rank` and `order` are copied from upstream with their `__status`. Stage 2 never computes
   rank from a top view. Ranks are fixed at the plant's `rank_reference_capture_id` and never
   renumbered (amendment A1.1).
6. **Diurnal guard.** Comparing two captures requires `photoperiod_phase` equal and both
   `time_since_lights_on_min` present; otherwise the comparison is emitted with
   `comparison_status = unavailable_diurnal_confound` and no growth value is written.
7. **Scale cross-check.** Two independent scale sources differing by > 5 % ⇒ abort the run with a
   non-zero exit and a report row; never average, never pick one silently.
8. **Removal.** `removal_confirmed` is accepted only from upstream, which itself admits only
   `data/records/manual_events.csv` joined through `organ_label_map.csv`, or a destructive-protocol
   step. Absence of an observation is never removal. Both record files are missing today, so this
   state is currently unreachable — that is expected.

---

## 8. Independent verification

Each method is usable only when its artifact exists; none may be assumed.

| Method | What it checks | Status on disk |
|---|---|---|
| Destructive / caliper measurement | true length, width, surface area; attachment reality | protocol + schema exist (`data/records/destructive_capture_20261008/`), templates are headers only; **no measured rows** |
| `compound_bend_types_20261010` | rachis bend types, θ reference | 9 classified rows exist; the 9 source photos do not |
| Side-view photography with solved relative pose | tilt, insertion angle, θ, height | not on disk for the current plants |
| Board-free 3-D (Q2) | height, true area, attachment | result files not on disk |
| Later capture in which hidden region becomes visible | narrows occlusion candidates | reuse `candidate_reassessment.csv` (`verdict ∈ consistent|inconsistent|undecidable`) |

A verification claim must name the artifact and its sha256 in `manifest.json`, or not be made.

---

## 9. Codex implementation instructions

Code location (Codex's column): `phynotype2/structure/`.

```
phynotype2/structure/__init__.py
phynotype2/structure/io.py            read upstream run folder; write the output folder
phynotype2/structure/frames.py        frame token resolution and the > 5 % scale cross-check
phynotype2/structure/snapshot.py      build one dated MTG snapshot
phynotype2/structure/update.py        apply a new capture to the previous snapshot
phynotype2/structure/areas.py         the four area columns of §4
phynotype2/structure/cli.py           `python -m phynotype2.structure.cli`
phynotype2/structure/tests/           Codex-owned tests
```

Functions — exact names, inputs, outputs, units:

| Function | Signature | Returns |
|---|---|---|
| `load_upstream` | `(run_dir: Path, plant_id: str) -> UpstreamBundle` | validated tables; raises `UpstreamContractError` naming the missing column |
| `resolve_frame` | `(capture_id: str, bundle: UpstreamBundle) -> FrameDecision` | `frame` token, `mm_per_px` or `None`, `scale_status`, `method` |
| `cross_check_scale` | `(sources: list[ScaleSource]) -> ScaleVerdict` | agreement ratio; `status = agree|disagree_gt_5pct|single_source|unavailable` |
| `build_snapshot` | `(bundle: UpstreamBundle, capture_id: str, previous: Snapshot \| None) -> Snapshot` | vertices, edges, states; never mints an id |
| `update_structure` | `(previous: Snapshot, bundle: UpstreamBundle, capture_id: str) -> tuple[Snapshot, list[ChangeRow]]` | new snapshot + change log |
| `area_estimates` | `(bundle: UpstreamBundle, capture_id: str, frame: FrameDecision) -> list[AreaRow]` | the four columns, each with `__status` |
| `attachment_candidates` | `(bundle: UpstreamBundle, capture_id: str) -> list[AttachmentCandidateRow]` | competing parents; empty when attachment is observed |
| `write_run` | `(out_dir: Path, snapshot: Snapshot, changes, areas, unresolved, manifest) -> None` | publishes the folder as one set |

Units: lengths mm, areas mm² (physical) or px² (image), angles **degrees in files, radians in code**
with a `_rad` suffix. Every length variable name carries `_mm` or `_px`; every angle `_deg` or `_rad`.

Software pass criteria (all must hold; each is a test):

1. **Reproducibility** — same inputs + same config hash ⇒ byte-identical outputs, excluding the
   manifest timestamp.
2. **ID preservation** — no id in the output is absent from upstream `tracks.csv`; no id is reused or
   renumbered across two runs over the same captures.
3. **No status promotion** — for every `(vertex_id, attr)` pair, a run may not output `observed` where
   the previous snapshot had `model_estimated` or `generated_candidate` unless the current capture
   supplies its own observed row; a test asserts this over a two-capture fixture.
4. **Zero physical values without scale** — with `scale_status = unavailable` in the fixture, the count
   of non-`unavailable` `_mm`/`_mm2` cells in every output file is **0**.
5. **Candidate segregation** — no `candidate_id` row appears in `mtg_vertices.csv`/`mtg_edges.csv` of
   the main snapshot; a test greps the published files.
6. **Frame token present** — every row with a coordinate/length/area/angle has a non-empty `frame`
   from the §3 vocabulary; no defaulting.
7. **Diurnal guard** — a two-capture fixture with differing `photoperiod_phase` yields
   `comparison_status = unavailable_diurnal_confound` and no growth value.
8. **Scale disagreement aborts** — a fixture with two sources 6 % apart exits non-zero and writes no
   snapshot.
9. **Read-only inputs** — a test asserts the upstream run folder, `config/` and `data/records/` are
   byte-identical before and after a run.
10. **Coherent publish** — a failure mid-write leaves the previous run folder untouched and no partial
    output folder containing `manifest.json`.
11. **Unresolved accounting** — every `unavailable` cell in the snapshot has a matching row in
    `unresolved.csv` with a blocking reason.
12. **Non-ASCII paths** — the run works under a Korean path. Use `tomato3d.io.images.read_image` /
    `write_image` for any image IO; `cv2.imread`/`cv2.imwrite` fail silently on such paths.

Codex may **import** `tomato3d` but not modify it. Any needed change to `tomato3d/` goes to
`handoff/LOG.md` as a request to Claude Code.

---

## 10. Reuse of existing code

| Item | What it is | Verdict |
|---|---|---|
| `tomato3d/graph/{nodes,connectivity,skeleton,keypoints}.py` | stubs, 3 `NotImplementedError` each | **not reusable** — nothing implemented |
| `tomato3d/track/link.py`, `tomato3d/organ/*`, `tomato3d/pheno/measure.py` | stubs | **not reusable** |
| `tomato3d/io/schemas.py`, `io/tables.py` | the project's schema/CSV contract: `UNAVAILABLE`, `load_json_model`, `write_table`, strict models | **reusable as-is** — use for every table and the sentinel |
| `tomato3d/io/images.py` | Unicode-safe image IO (`read_image`, `write_image`) | **reusable as-is**; mandatory (pass criterion 12) |
| `tomato3d/synth/leafarea.py` (501 lines) | `rectify` (metric scale from a printed grid), `fit_correction` (model form only, no coefficients) | **partially reusable** — `rectify` for flattened reference photos; the correction may not be applied |
| `tomato3d/synth/structure.py`, `compound_leaf.py`, `leaflet_surface.py` | generator structure/surface parameterisation; every range `user_assumed`, realism gate C6 not passed | **candidate generation only** — never a measurement |
| `tomato3d/calib/{board,pose}.py` | board frame and PnP; `sheet_to_board_mm` is the only frame converter | **reusable as-is** for a board session; do not write a second converter |
| `tools/plant_structure.py` (739 lines) | existing plant structure assembly | **review before writing new code** — overlap must be judged by Codex, who owns it |
| `tools/leaf_area_geometry.py::view_geometry`, `tools/leaflet_chain_match.py`, `tools/cross_view_candidates.py` | per-view geometry, leaflet chaining, cross-view candidates | **reusable with care**, Codex-owned |

---

## 11. Contract change proposals

Do not edit document #3 or #4. These are proposals.

| id | Finding | Proposed change | Affected fields | Owner |
|---|---|---|---|---|
| a | Stage 1 carries no organ identity and no correspondence confidence. **phynotype2 §7 has no confidence field either** — the string `confidence` does not occur in the 366-line document; the superseded skeleton's `tracks.csv` had one and phynotype2 drops it. What exists: `link_status (proposed\|confirmed)` and a required best-vs-second-best cost margin **with no column or file named**. | Treat §7 as the sole source of *track identity and state*. Name the margin column and its file (proposal: `match_margin` in `match_candidates.csv`), and state in the Stage-2 contract that Stage 2 consumes `link_status` + `match_margin`, never a probability. | `tracks.csv`, `track_states.csv.link_status`, `match_candidates.csv` (+ `match_margin`), `association.ambiguity_margin` | human decides the field; Codex implements |
| b | The frame premise is broken for board-free capture; Stage 1 and `CONVENTIONS.md` both state the no-registration rule as a prohibition. | **Scope** the prohibition to board sessions rather than delete it; make `frame` a mandatory per-row token; keep per-capture registration in `frame_transforms.csv`; declare the frame of `config/capture_config.json`'s positions. | `mtg_vertices.frame`; `frame_transforms.*`; `capture_config.json` (frame declaration) | human (config/ and the rule) |
| c | `top_position` is a hard enum `Literal["T0".."T4"]` and `ImageEntry` *raises* when a top view lacks it — so a hand-held top view cannot be represented in `session_manifest.json`. | Stage 2 must not require `session_manifest.json` for a board-free capture; its capture key is `captures.csv`. Treat `top_position` as a **jig label**, not a view identity. Leaves the frozen validator untouched. | `session_manifest.json`: `top_view_method`, `top_view_count`, `top_view_positions_mm`, `operational_top_view`, `images[].top_position` | human enumerates; Claude Code owns `schemas.py` if a change is ordered |
| d | Three id schemes; only `session_id` has a grammar, and splitting it on `_` is ambiguous because `plant_id` may contain `-` and nothing constrains its character set. **`capture_id` has no grammar at all** — it appears as a column in 8 tables and is never defined. | **Define a mapping table, do not unify.** Keep `session_id` (frozen, a `poses.csv` column) and `capture_id` separate; parse `session_id` right-to-left; add a join table as Stage-2/phynotype2 output. Define `capture_id`'s grammar and `plant_id`'s character set. | `session_id`, `poses.csv` col 1, `capture_id` in 8 tables, new join table | human fixes the grammars |
| e | `time_since_lights_on_min` exists upstream but **no source for its value exists**: the lights-on clock time is null, and it cannot be back-filled for past captures. | Stage-2 state carries `time_since_lights_on_min` and `photoperiod_phase` copied verbatim from `captures.csv`, joined on `capture_id`. Columns required-present; `unavailable` allowed; never 0, never derived from `captured_at` or the `HHMM` tail of `session_id`. Record the lights-on time going forward as a new-captures-only field. | `captures.csv`, Stage-2 `structure_state.csv`, cues `dt_h`/`same_phase`/`gap_captures` | human supplies the time |
| f (new) | `removal_confirmed` and every human-label join depend on `data/records/manual_events.csv` and `organ_label_map.csv`; **neither exists**. | State both mechanisms as unreachable until the files exist; do not add a fallback. Human to decide whether and when to create them, with columns. | `track_states.state`, `tracks.human_label`, `organ_label_map.csv` | human |
| g (new) | `docs/복엽구조_형태_2026-10-10.md` defines **no** petiole insertion angle, leaflet surface tilt or leaflet curvature — identifiability items 5, 6, 8 have nothing to be identified against. | Obtain a human definition (reference plane/axis and sign) before any of the three is specified as an output. Until then they are `unavailable` by definition, not by measurement failure. | the three angle attributes of `mtg_vertices.csv` | human defines |

---

## 12. Decisions required from the human

Blocking (Stage 2 produces no physical-unit value until each is settled):

1. `pot_rim_inner_diameter_mm` per pot type — measured with a caliper, written into `config/`.
2. Lights-on clock time per day, recorded going forward.
3. Definitions for petiole insertion angle, leaflet surface tilt, leaflet curvature (item g).
4. `area_basis` for the mask convention (`green_only` vs `full_outline`).

Non-blocking but needed before the related output is trusted:

5. `capture_id` grammar and `plant_id` character set (item d).
6. Whether `manual_events.csv` / `organ_label_map.csv` will exist, and their columns (item f).
7. `rank_reference_capture_id` per plant.
8. The `frame` token vocabulary and the frame of `capture_config.json`'s positions (item b).

---

## 13. Out of scope

Stage-3 prediction; any code implementation; any edit to `config/`, `data/records/`, `docs/`,
`tools/`, `tomato3d/`, or to documents #3–#6. Side and depth captures are verification and
supporting evidence only — the stage's target is the top-view time series.

---
## Amendment L1 (2026-10-11, appended by Claude/claude.ai) — alignment with the literature prompt and the vtc fork

Sources: `CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md` (papers verified against PDFs),
`CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md` + Addendum A, and the read-only reference code
`Downloads\vtc-main` (diaf022 GroIMP). Spec owner reconciles; earlier text stands where not named here.

1. **Item g / human decision 3 is now two-thirds resolved.** Since this spec was written, MTG amendments
   A1/A2 define: petiole insertion angle = stem axis vs petiole, 0–180°, side view or 3D only (top view
   alone ⇒ `unavailable`); rachis bending = per-segment α1..α3 anchored to the P0–P3 vertices of A1;
   elevation sign + = up (atan2 convention). Identifiability rows for these two now have defined targets.
   Only **leaflet blade curl** remains undefined (human pending). Update §5/§12 accordingly.
2. **Two azimuth fields are now mandatory, with a verified justification.** `petiole_base_azimuth_deg`
   (insertion) and `blade_azimuth_deg` (lamina direction) are separate columns: Sarlikioti 2011 (mcr221)
   measured row-crop phyllotaxis ~160° vs nominal 137.5° because mature leaves rearrange — apparent blade
   direction is not insertion direction. Stage-2 state must carry both, each with its own status.
3. **New downstream consumer:** `tools/phyllotaxis_fit.py` (literature prompt, P1 item 2) consumes
   consecutive main-stem `petiole_base_azimuth_deg` + true leaf order (≥ 5 leaves, else `unavailable`).
   Stage-2 output must therefore expose, per compound: azimuth, azimuth_status, rank, rank__status —
   already present in §6; this note only binds the consumer.
4. **Side-view height, if used as supporting evidence:** declare which definition a value carries —
   `height_top_leaf_mm` (soil → highest leaflet; what images give) vs `stem_length_mm` — never mixed
   (diaf022 had exactly this mismatch between image and model).
5. The vtc fork (`build/vtc_microtom_20261011/`) does not change Stage-2 scope: it is a conditional
   simulation sandbox, not an observation source. Nothing from the fork enters `structure_state.csv`.

## Owner reconciliation of Amendment L1 (2026-10-11, Claude Code — appended, nothing above edited)

Every claim in L1 was checked against the files on 2026-10-11. The design content is accepted. Three
statements describe artifacts that do **not exist yet**; they stand as forward contracts, not as
current facts. Earlier text is reinstated wherever L1 relied on them.

| L1 item | Checked | Status today |
|---|---|---|
| 1 — "MTG A1/A2 define insertion angle, rachis α1..α3, elevation sign; item g two-thirds resolved" | `handoff/MTG_CONVENTION_2026-10-10.md` ends at `## 10`; no `## 11 Amendment` exists. The A2 field names (`insertion_angle_deg`, `rachis_bend_alpha_deg`, `petiole_base_azimuth_deg`, `blade_azimuth_deg`) occur only in `CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md` — the **instruction** to write A2 (P1 item 1, assigned to Claude Code). A1 exists as a standalone decision file, not merged into the convention either | **Not resolved yet.** §5 rows 5–7 and human decision 3 stand as written until A2 is appended. Elevation sign (+ = up) was already settled by A1.4 and was never counted as open |
| 2 — two azimuth fields, Sarlikioti justification | Design rule; the ~160° vs 137.5° figure is cited by the amendment author as verified against `mcr221.pdf`, not re-verified here | **Accepted** as a design rule |
| 3 — `tools/phyllotaxis_fit.py` consumes Stage-2 azimuth + rank | File does not exist; it is P1 item 2 of the literature prompt | **Forward contract.** Stage 2 exposes `azimuth`, `azimuth__status`, `rank`, `rank__status` regardless (already in §6) |
| 4 — height definitions never mixed | Design rule | **Accepted** |
| 5 — the fork `build/vtc_microtom_20261011/` is not an observation source | Folder does not exist | **Accepted**, vacuously true today |

Net effect on this spec: none of §5, §11 or §12 changes yet. When A2 is actually appended to the MTG
convention, rows 5–7 of §5 gain defined targets and human decision 3 shrinks to leaflet blade curl.

**Follow-up to the reconciliation note (2026-10-11, Claude Code):** MTG Amendment A2 has now been appended
to `handoff/MTG_CONVENTION_2026-10-10.md` (§12), with A1 incorporated by reference (§11). The angle targets
L1 relied on now exist as definitions: CompoundLeaf `insertion_angle_deg` (stem axis vs petiole, side view
or 3-D only), `rachis_bend_alpha_<i>_deg` with signed Σ = `rachis_curvature_deg` (downward-positive, θ
excludes the last bend), and the two azimuth fields with the azimuth reference defined in §12.1. Human
decision 3 shrinks to leaflet blade curl (§8.3). `tools/phyllotaxis_fit.py` and the vtc fork are still
planned, not present.

## Human decision update (2026-10-11, appended by Claude/claude.ai)
- §12 decision 4 **resolved**: `area_basis = full_outline` (user: "3은 원래 윤곽"). Masks for leaflet area
  follow the original outline including browned margins; §5 row 1 condition "needs a declared area_basis"
  is now satisfied by this value (mask acceptance still required). Source: MTG_CONVENTION §13.
- Leaflet blade curl (MTG 8.3) and θ flat/bent thresholds (MTG 8.4): **on hold** — keep `unavailable` /
  human label; do not introduce thresholds.
