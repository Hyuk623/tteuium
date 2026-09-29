# Brief: JSON references for the three-route 3D calculator — Claude Code, 2026-09-20

Documentation-first brief (per `AGENTS.md`) for
`handoff/CLAUDE_JSON_REFERENCE_FOR_THREE_ROUTE_3D_2026-09-20.md`. Written before implementation;
outcomes appended afterwards. No solver change, no learning, no PPFD in this work.

## 1. Request

Implement only the data-reference layer: a versioned reconstruction request that references the human
growth JSON, the immutable annotation snapshot and the capture/calibration registry; a count and
parent-identity review from the growth record; and unique observation collection across the global,
vertical (01/03 → 2X → 1X) and circumferential (11 → … → 18 → 11) review routes, feeding the existing
calculator. No parallel application, no second editable copy of the labels.

## 2. Inspected state (verified today)

- `capture.json` frames already carry `view_code` (`01`, `03`, `11`–`18`, `21`–`28`),
  `observed_view_group` (`top`/`oblique`/`side`) and `nominal_polar_deg`. The three routes are
  therefore derivable from existing capture labels; **no new per-image route metadata is needed**.
- `convert()` rows already carry `plant_id`, `session_id`, `organ_id`, `leaflet_id`,
  `viewer_leaflet_id`, `point_id`, `image_file`, original pixels, visibility and identity-review
  state. The scoped physical-point key exists in the data; only the grouping layer is missing.
- The closest existing manifest is `edit_session/session_report.json` (capture/annotation/annotator/
  calibration paths and hashes for a prepared session). The request extends it by adding the growth
  record, quality/mode selection and the output destination, rather than duplicating it.
- Growth records: `tomato_photos_organized_/260920/dwt_<n>/260920/dwt_<n>_260920.json` —
  `compound_leaves[].{compound_leaf_id, leaflet_count, is_unfolding}`, `growth_shoot_count`,
  `truss_count`, with `null` meaning not entered. dwt_01 = 8/9/9, dwt_02 = 7/7/5. No coordinates.
- Neither new session has leaflet labels yet, so the count review will report zero reviewed
  identities against the recorded counts. That is a finding, not a failure to fix by inventing labels.

## 3. Intended changes

1. **`tools/reconstruction_request.py`** (new)
   - `write_request` / `load_request`: schema `reconstruction-request-1`; every path resolved
     **relative to the manifest file**, never the shell working directory; `sha256` recorded per
     reference; identity (`plant_id`, `session_id`, capture date) cross-checked against the
     referenced capture and growth record.
   - Findings before any calculation, each with a code: missing file, unreadable JSON, unrecorded
     hash, changed hash (needs an explicit refreshed snapshot), identity mismatch, unknown schema.
     `require_ready` raises rather than silently using stale or inconsistent inputs.
   - `review_counts(growth, leaflets)`: recorded `leaflet_count` per compound leaf against the unique
     reviewed leaflet identities assigned to that parent; separate buckets for unconfirmed identities,
     unknown parents and `null` counts. Findings only — never merges, deletes or invents a label, and
     `growth_shoot_count` is never added to a leaflet count.
   - `route_membership(capture)` and `collect_observations(rows, capture, route=…)`: physical-point
     key `(plant_id, session_id, organ_id, leaflet_id, point_id)`; one saved observation reached
     through several routes is collapsed to one with the routes recorded; contradictory coordinates
     for the same point/image are kept and reported, never averaged or silently chosen; per-
     observation eligibility (`solved pose` vs `unposed_no_triangulation_ray`, visibility) is decided
     per point, independently of whole-leaf bbox eligibility.
2. **Rebuild integration**: `--request` loads the manifest, reports findings first, writes
   `reference_review.json` and `route_observations.csv` beside the existing outputs, and adds
   `reference_status`, `reference_findings`, `growth_review` and `route_summary` to the report. The
   solver, its inputs and the baseline outputs are unchanged.
3. **Server**: `--request` pass-through so the browser rebuild button carries it.
4. **Viewer**: a count/association review block and a route summary in `labels/index.html`.

## 4. Execution restrictions

No solver, pose, gate or schema rewrite. Growth JSON, `tomato_photos_organized_/`, `config/` and
`docs/` are read-only here. Writes stay under `build/`. Counts never create geometry; referencing a
JSON never creates depth or validates a pose. Outputs stay `validated_metric=false`,
`suitable_for_ppfd=false`.

## 5. Validation plan

Deterministic tests: references load without modifying any source; missing, malformed, unresolved-
relative, identity-mismatched and stale-hash cases each produce their own reported finding; a
manifest is resolved relative to its own location from a different working directory; an observation
reached through several routes is counted once and route count does not change weight; `b1` on two
different leaflets stays two physical points; count mismatches produce findings while labels and
depths stay byte-identical; visible points on a partially occluded leaflet stay assessable while
hidden points stay unobserved; identical observations and poses give identical depths whichever route
is selected; count-only and navigation-only changes leave geometry hashes unchanged while
identity/coordinate and calibration changes mark dependent outputs stale through the existing
mechanism; the real editor → server → rebuild → viewer path carries the option. Mutation runs must
show each of these tests failing when the corresponding rule is removed.

## 6. Outcomes (completion report, 2026-09-20)

### 6.1 What was implemented

- **`tools/reconstruction_request.py`** (new, schema `reconstruction-request-1`)
  - `write_request` / `load_request` / `require_ready`: the manifest names the human growth record,
    the prepared session, the immutable annotation snapshot, the annotation context, capture,
    calibration, optional board spec, exported observation CSVs, quality settings, reconstruction
    mode, optional frozen reference geometry and the output destination. Every path is stored and
    resolved **relative to the manifest's own directory**; a `sha256` is recorded per reference.
  - Findings, each with a code and a plain-language detail, produced **before any calculation**:
    `reference_file_missing`, `reference_not_readable_json`, `reference_hash_not_recorded`,
    `reference_hash_changed_since_snapshot`, `plant_identity_mismatch`, `session_identity_mismatch`,
    `capture_date_mismatch`, `unknown_request_schema`, `reference_missing_from_request`.
    `require_ready` raises rather than using stale or inconsistent inputs; a changed hash needs an
    explicitly refreshed snapshot.
  - `review_counts`: recorded `leaflet_count` per compound leaf against the distinct **confirmed**
    reviewed identities labelled for that parent, with unconfirmed identities listed separately.
    Codes: `more_reviewed_leaflets_than_recorded`, `fewer_reviewed_leaflets_than_recorded`,
    `growth_leaflet_count_not_recorded`, `parent_not_in_growth_record`,
    `compound_leaf_entry_count_differs`. `growth_shoot_count` is never added to a leaflet count, and
    the result carries `labels_changed=false`, `geometry_changed=false`.
  - `route_membership` / `route_images`: the three routes are derived from the capture labels already
    in `capture.json` (`view_code`, `observed_view_group`) — global, vertical (01/03 → 2X → 1X) and
    circumferential (side ring 11 → … → 18 → 11, then the oblique ring). No new per-image metadata.
  - `collect_observations`: physical-point key `(plant_id, session_id, organ_id, leaflet_id,
    point_id)`, so `b1` on two leaflets stays two points. One saved observation is counted once
    however many routes reach it (`routes_reached` records them, `duplicate_observations_collapsed`
    counts re-offers); contradictory coordinates for one photograph are kept, reported and made
    ineligible instead of averaged or silently chosen; eligibility is decided per point
    (`unposed_no_triangulation_ray`), independently of whole-leaf bbox rules, so visible points on a
    partially occluded leaflet stay assessable.
  - CLI: `write` and `check`.
- **`tools/rebuild_leaf_edit_session.py`**: `--request` resolves and refuses the references *before*
  the conversion runs, then writes `reference_review.json` and `route_observations.csv` beside the
  existing outputs and adds `reference_status`, `reference_findings`, `reference_finding_counts`,
  `growth_review`, `route_summary`, `reference_note` to the report. The solver, its inputs and every
  geometry output are untouched.
- **`tools/editor_point_review.py`**: a count/association review table (recorded vs reviewed vs
  unconfirmed, with the finding) and a route table (photos, unique physical points, unique
  observations, collapsed re-offers, points with two or more eligible views) in `labels/index.html`,
  stating that counts are a review reference and that route count never adds weight.
- **`tools/serve_leaf_edit_session.py`**: `--request` pass-through; the job summary reports
  `reference_status`, `reference_finding_counts` and `route_summary`.

### 6.2 Validation

`tools/tests/test_reconstruction_request.py` (14 tests). Full suite: **213 passed, 1 skipped**.
Covered: paths resolve from the manifest while the shell runs elsewhere and no referenced file is
modified; each unusable-reference case reports its own code and blocks; a count mismatch is a finding
while the labels and the depth table stay byte-identical; unconfirmed identities are listed but not
counted; an unlisted parent is reported; routes come from capture labels and order the navigation; an
observation reached through three routes stays one observation with three `routes_reached` entries; a
re-offered identical observation collapses while contradictory coordinates are kept and reported;
`b1` on two leaflets stays two physical points; an unposed view supplies no ray but stays available
for identity review; a partially occluded leaflet keeps assessable points; selecting a route only
narrows the photographs walked; a foreign or stale request stops the run before any output directory
is created; the browser → server → rebuild → viewer route carries the request.

**16 mutation runs, all caught**: manifest paths resolved against the shell; changed or unrecorded
hash accepted; identity mismatch ignored; a blocked request calculating anyway; unconfirmed
identities counted as reviewed; growth-shoot count folded into the leaflet count; unlisted parent not
reported; joining on `point_id` alone; one observation counted once per route; contradictory
coordinates overwritten; an unposed view treated as a triangulation ray; route selection widened to
every photograph; references checked only after calculating; the rebuild's session check dropped;
the server dropping the request.

### 6.3 Real data

```
python -m tools.reconstruction_request write --out build/reconstruction_requests_20260920/dwt_01.json \
    --plant dwt_01 --session dwt_01_20260920 --capture-date 2026-09-20 \
    --growth tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json \
    --prepared-session build/new_captures_20260920/dwt_01/edit_session \
    --annotation-snapshot build/new_captures_20260920/dwt_01/edit_session/seed.backup.json \
    --annotation-context build/new_captures_20260920/dwt_01/edit_session/annotations.source.json \
    --output build/reference_review_20260920/dwt_01
python -m tools.reconstruction_request check --request build/reconstruction_requests_20260920/dwt_01.json
python -m tools.rebuild_leaf_edit_session --session build/new_captures_20260920/dwt_01/edit_session \
    --backup  build/new_captures_20260920/dwt_01/edit_session/seed.backup.json \
    --context build/new_captures_20260920/dwt_01/edit_session/annotations.source.json \
    --out     build/reference_review_20260920/dwt_01 \
    --request build/reconstruction_requests_20260920/dwt_01.json
```

Both plants resolved `ready` with no reference findings, before and after the run — the growth
records and session inputs were read and left unchanged. Review results:

| | dwt_01 | dwt_02 |
|---|---|---|
| recorded leaflets (L01/L02/L03) | 8 / 9 / 9 | 7 / 7 / 5 |
| reviewed identities | 0 / 0 / 0 | 0 / 0 / 0 |
| finding per compound leaf | `fewer_reviewed_leaflets_than_recorded` | same |
| route photos global / vertical / circumferential | 18 / 18 / 16 | 18 / 18 / 16 |
| unique physical points, all routes | 0 | 0 |

Artifacts: `build/reference_review_20260920/<plant>/reference_review.json`,
`route_observations.csv`, `labels/index.html`. The zero counts are the true state — neither session
has any leaflet label yet — and the review reports them as findings rather than inventing leaflets or
geometry.

### 6.4 Limits and what is still open

This layer supplies counts, identities and provenance only: referencing JSON creates no depth,
validates no pose and never edits a human record. Nothing about the unvalidated calibration, the
failed 1 px pose gate or `validated_metric=false` changes. `route_observations.csv` lists saved
observations, not reconstructed coordinates; the depth tables remain the geometry outputs. The
growth records still hold no positions, so no spatial order may be read from them. Importer **F1**
remains open. `CLAUDE_THREE_ROUTE_LEAFLET_FUSION_2026-09-20.md` and
`CLAUDE_JSON_GUIDED_THREE_ROUTE_3D_IMPLEMENTATION_2026-09-20.md` ask for more than this focused task
(fusion behaviour and the full staged UI); only the reference layer they share is implemented here.
