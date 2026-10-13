# P1 trusses, `segment_index` and the confirmed axis policies: execution report (2026-10-12)

Author: Claude Code. Implements `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md` (T1–T5). Korean
companion: `handoff/P1_SEGMENT_TRUSS_EXECUTION_2026-10-12_KO.md`. Command log: `build/p1_truss_cli_log_20261012.txt`.

## 0. Files read / scope note
Read: `CONVENTIONS.md`, last 40 LOG lines, `handoff/MTG_CONVENTION_2026-10-10.md` §15 A4,
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md`, `docs/정의집_토마토_2026-10-11.md` (§0, §0-1, §1-1; read-only),
`handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md` §3 and §6, `handoff/CODEX_CLI_PROMPT_P4_SUBSTEM_TRUSS_2026-10-12.md`.
**Not run: T6** (pot-rim scale reference). It was appended to the prompt file after the prompt was handed to this
session (LOG 2026-10-12, "Pot scale CONFIRMED … Appended work order T6"); it is a separate piece of work (new pot
field, per-pot rim derivation from images, real-audit rerun) and is waiting for the user's go-ahead.

## 1. Per item

| Item | Result |
|---|---|
| **T1 Amendment A5** | **Done.** `MTG_CONVENTION` §16 appended (nothing above edited): 16.1 the three A4 proposals confirmed (numbering = registration order, tie → lower node; tie rank 1 = basal leaf; order-2 notation `S1.1` reserved, code still forbids); 16.2 side shoots bear trusses, sympodial continuation = one axis (closes the §15.5 S-axis-continuation item); 16.3 `segment_index` definition and 1-based rule; 16.4 `Truss` row in the scale table (scale 3 beside CompoundLeaf, no leaves, never an `axis_shoot`, id `<plant>/F<serial>`); 16.5 registry; 16.6 open items. |
| **T2 Schema** | **Done.** `p1_state_v1` **revision 4** (additive; the version string is unchanged because Codex compares it for equality). `segment_index` (+ `__status`) as an MTG value attribute on every row with `axis`; `identity_manifest.csv` `segment_index`; `axes.csv` `segment_index`, `segment_index__status`, `truss_count`; vertex class `Truss`; new table `trusses.csv`. Validators (`schema.check_segments`, `check_trusses`, `check_axes`): segment ≥ 1; equal to 1 + trusses below the node on that axis (so it starts at 1, never decreases, and the node after a truss is one higher); a truss carries no rank and no `leaf_unfolded`, is scale 3 and on a stated axis; organs repeat their compound's index; an Axis row = 1 + its trusses; `axes.csv` apical index = `truss_count` + 1; order 2 or an `S1.1` code rejected **with the reserved spelling named in the message** (schema, side-shoot registry, truss registry). Revision ≤ 3 headers still validate (tested on `build/p1_state_20261012_03`). Packages of revision ≤ 3 carry `numbering_basis`/`tie_rule` `proposed:…`; new ones carry `user_stated:…`. |
| **T3 Truss registry** | **Done.** `tomato3d/state/trusses.py::read_registry` for `data/records/trusses/truss_registry.csv` (read-only; absent today): `plant_id, axis, above_rank, first_observed, note` exactly. Rejects order-2/unknown axis codes, two trusses above one rank on one axis, non-integer `above_rank`, non-ISO dates, primes, and rows whose date goes backwards for a plant (row order = truss serial, so appending must keep it stable). `check_against_axes`: a truss on `S<k>` needs that side shoot registered no later than the truss. Template (header + one marked example row + README): `build/truss_registry_template/`. `segment_index` is **derived** (`apply_segments`): registry + ranks only; no registry → `unavailable` (absence of a record is not "no truss"); unplaced truss → that axis's leaves `unavailable`; a snapshot uses only trusses recorded by its capture (no look-ahead). |
| **T4 Propagate** | **Done.** Ingest: obs class `truss` already exists; truss observations are never tracked (`ingest.trackable`, test). Track: identity rows carry `segment_index` (set after the update by `fill_identity_segments`; the tracker never sets it). Update: `SnapshotInputs.trusses_now` → `Truss` vertices + segments; `record_status` lets a fixture's leaf records carry `synthetic_truth`. Package: `trusses.csv`, `axes.csv` A5 columns, segment `P1.4_trusses`, P2 field map (3 new rows), P2 dry-read section `axes_and_trusses`. **Column agreement with P4:** Codex's LOG line of 2026-10-12 (P4 producer alignment) already reads the canonical `segment_index`, `Truss` (scale 3) → native `TrussAxis`, `trusses.csv truss_vertex_id`, and "axis apical index = 1 + truss count" — the same spellings and rule as shipped; recorded in LOG. |
| **T5 Run** | **Done.** `prepare --mode fixture-truss` (side-shoot plant `fx_ss0` + two registry trusses) → `build/p1_state_20261012_05`; validates; collect exit 0; P2 dry-read ok; replay 54/54 identical; Codex `audit_p1_package` fixture_ready **true**, 0 gaps. |

## 2. Results — `build/p1_state_20261012_05` (evidence `synthetic_fixture`)

| | |
|---|---|
| Trusses | `fx_ss0/F0001` on **M** directly above main rank 4, recorded 2026-10-09 (before c0) → emergence (unavailable, c0]; `fx_ss0/F0002` on **S1** directly above S1 rank 3, recorded at c2 → emergence (c1, c2]. 4 `trusses.csv` rows. |
| Main stem continues as M | M leaves rank 1–4 = segment 1, rank 5–6 = **segment 2**; axis stays `M`, ranks unbroken; S2 sits in the axil of main rank 5 (segment 2). |
| Substem truss | S1 apical segment 1 at c0/c1 → **2 at c2** (`axes.csv truss_count` 0 → 1; `change_log.csv` records the change); its three leaves stay segment 1 (no leaf above the truss yet). |
| Snapshot vs truth | 31/31 compound rows: snapshot `segment_index` = truth `segment_index`; 73 of 76 snapshot rows carry an index (the 3 without are the Plant rows). |
| Ranks in the snapshot | `fixture_leaf_records`: each tracked compound's truth rank + unfolded flag joined through the fixture truth join, status `synthetic_truth` — it stands in for the human leaf record a real plant needs. Without ranks there is no segment index. |
| No invention | Axes `M`, `S1`, `S2` only; no truss geometry (every geometric value of a Truss row is `unavailable` with reason "human registry record only"). |

Real audit under A5 code: `build/p1_state_20261012_06` (capture_tz Asia/Seoul as stated by the user): no truss
registry → every `segment_index` `unavailable`, `P1.4_trusses = unavailable`, `audit_gaps.csv` gains
`truss_registry` for each of the 13 plants (182 gap rows). Codex audit unchanged: real_ready false, 130 gaps.

## 3. Commands and exit codes (`build/p1_truss_cli_log_20261012.txt`)
```
python -X utf8 -m pytest -q tests/                                                               415 passed, 1 skipped
python -X utf8 -m pytest -q tools/tests/test_tomato_fsp_pipeline.py                              28 passed (read-only)
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode fixture-truss --out build/p1_state_20261012_05   0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261012_05                   0
python -X utf8 -m tomato3d.cli.run_p1 collect --package build/p1_state_20261012_05               0
python -X utf8 -m tomato3d.cli.run_p1 compare-observation --package build/p1_state_20261012_05   0
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261012_05                0 (54/54 identical)
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode real --out build/p1_state_20261012_06 --capture-tz Asia/Seoul --capture-tz-ref '…'   0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261012_06                   3 (valid, partial)
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261012_06                0
python -X utf8 flow/check_flow.py --md                                                           0
```
New tests: `tests/test_state_trusses.py` (28). Updated: `tests/test_state_axes.py` (numbering/tie now `user_stated`).
Code version `p1code-9b37c3a166ae6a60` (`trusses.py` added to the hashed set); earlier packages report themselves
stale by design.

## 4. Producer → P4/P3 fields
- `axes.csv` (fsp-axes-1 exchange block + `segment_index`, `segment_index__status`, `truss_count`): apical segment of
  each axis at each capture = `truss_count` + 1; `unavailable` without a registry, never defaulted to 1.
- `trusses.csv`: `truss_vertex_id, axis_id, axis_vertex_id, parent_rank` (= `above_rank` on the bearing axis),
  `segment_index` (segment the truss closes), `first_observed_*`, `emergence_interval_*`, `source_kind/ref`,
  `registry_ref`.
- `mtg_vertices.csv`: `Truss` rows (scale 3, complex = bearing axis vertex) and `segment_index` (+ status) on Axis,
  CompoundLeaf, Truss and organ rows; `identity_manifest.csv` `segment_index`.
- Not P1 products: truss cadence, the stop decision, hidden apex state (`axis_leaf_count`, `produced` …).

## 5. Not done / open
- **T6 (pot-rim scale) not run** — appended to the prompt after hand-off; awaiting the user. When run it needs a
  per-pot rim detector on the top photos (none exists) and the 60 mm value entering through a human record in
  `data/records/` (agents may not write there).
- Open (user): whether code may allow `order = 2`. The flow rows Codex handed over
  (`handoff/FSP_EXTENSION_SIDESHOOT_FLOW_ROWS_2026-10-12.csv`) were already all in `flow/flow_map.csv` (0 new).
- P3 V2 now has both P1 prerequisites; `P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md` (Codex) is still absent.
- No edits to `tools/`, `config/`, `data/records/`, `docs/`.


## 6. T6 — pot-rim scale reference (appended 2026-10-12, run at the user's instruction)

The user then pointed this session at the prompt file itself, so T6 was run (LOG claim + result). Measured
reference (user, caliper, `measured`): square cells, **60 mm outer top edge across the flats**, 70 mm deep.

| T6 item | Result |
|---|---|
| **1 Field** | **Done.** Human record `data/records/pots/pot_spec.csv` (read-only; template `build/pot_records_template/`): `pot_type, shape, plant_ids, pot_rim_outer_edge_mm, pot_rim_inner_diameter_mm, pot_depth_mm, source_kind, method, measured_date, note`. Square → `pot_rim_outer_edge_mm` required and the round field blank; round → the reverse; **both on one row is rejected**. `pot_depth_mm` is recorded only, never a scale source. Every mm scale names its `scale_convention` (`pot_rim_outer_edge_square` / `pot_rim_inner_diameter_round` / `synthetic_ortho_camera_declared`) in `captures.csv` and `frame_transforms.csv`. The template's example row carries the user's caliper value for the human to confirm; nothing was written to `data/records/`. |
| **2 Per pot** | **Done (derivation); no inputs yet.** `tomato3d/state/potscale.py`: points clicked on the four FLAT outer rim edges of each top photo (`data/records/pots/rim_points.csv`, keyed by plant and the photo's sha256) → a line per side → their intersections = corners of the across-flats square (chamfers excluded) → homography image px → rim plane (origin at the pot centre, right-handed seen from above; rotation about Z unknown, no orientation mark). `mm_per_px` = local scale at the pot centre; the full homography goes to `frame_transforms.csv`. Validator: a real-photo scale must be `pot_rim:` from the plant's own record; another pot's rim is never borrowed and an image-wide scale is rejected. **No rim detector exists** (translucent rim on white paper, often under leaves and the ruler), so the points are a human record; none exist yet. |
| **3 Plane** | **Done.** `scale_plane = rim_plane`; the caveat (leaves above the rim are nearer the camera → a rim scale underestimates them; not a true size; no correction factor) is carried in `pot_rim_scale.json` and the module docstring. |
| **4 Cross-check** | **Done.** Ticks of the ruler lying on the rim (in every real top photo: `ruler_plane = pot_rim`), clicked with their readings, are measured through the rim homography: ≤ 2 % → `accepted_within_2pct`; > 5 % → `stopped_over_5pct` (scale `unavailable`, reported, never averaged); in between → `flagged_2_to_5pct` (reported; the rule names no action for that band). Only the rim → `scale_sources = 1`, `none_single_source`. Thresholds in `p1_config.json pot_scale` with T6 as source. |
| **5 Real audit** | **Rerun:** `build/p1_state_20261012_10`. **Scale gaps closed: 0 of 117.** Remaining, by exact input: 13 top captures — `data/records/pots/pot_spec.csv` absent (then also `rim_points.csv` for each photo); 104 level/side captures — the rim is seen edge-on, no rim-plane square exists (out of T6's scope; ruler scale I.4 still pending). The 13 optical-surface gaps (Q2) are untouched. Codex audit: 130 gaps (117 scale + 13 optical), unchanged. Once both records exist, at most the 13 top captures can close. |
| **6 Uncertainty** | **Done.** Each rim point carries the annotator's `click_uncertainty_px` (required); per side the larger of that and the line-fit residual RMS is used and propagated by a seeded Monte Carlo (`monte_carlo_draws` 400, a computational choice) to `mm_per_px_sd`, and to every area as `*_area_mm2_sd` (= 2·area·sd/scale). Validators reject a real-photo mm scale or mm² area without its uncertainty; `update.area_rows` writes no mm² value without one. Synthetic fixtures declare an exact camera (`sd = 0`, `synthetic_ortho_camera_declared`, plane `synthetic_camera`). |

Schema: `p1_state_v1` **revision 5** (additive; version string unchanged): `captures.csv` + `mm_per_px_sd`,
`scale_convention`, `scale_sources`, `scale_cross_check`, `scale_plane`; `frame_transforms.csv` + `mm_per_px_sd`,
`scale_convention`, `rim_homography_px_to_mm`; `areas.csv` + `visible_projected_area_mm2_sd`,
`completed_projected_area_mm2_sd`. Revision ≤ 4 headers still validate; Codex's acceptance rows (all new cells
`unavailable`, synthetic) still pass. The real input snapshot now also hashes the human records the build reads
(side-shoot, truss, pot) when present, so replay names a record that appears or changes.

**Packages under the final code (`p1code-a06d089648e8bbe8`, revision 5):** truss fixture
`build/p1_state_20261012_09` (supersedes `_05`; same truss results; collect 0, replay 54/54, Codex fixture_ready
true) and real audit `build/p1_state_20261012_10` (supersedes `_06`; run/collect 3 = valid partial, replay 0).
`_07`/`_08` were built before the input-snapshot fix and are superseded records.

Tests for T6: `tests/test_state_potscale.py` (26): a known perspective homography is recovered exactly (scale at the
centre, centre, virtual corners, orientation); uncertainty scales with the stated click uncertainty and the fit
residual wins over an optimistic click; missing inputs → `unavailable` with the reason; out-of-order sides
rejected; the three ruler bands; record rules; validators; real wiring (top solved, level gap, no borrowed rim);
input snapshot hashes a new record. Commands in `build/p1_truss_cli_log_20261012.txt`.

**To close the 13 top-view gaps (human):** copy `build/pot_records_template/` to `data/records/pots/`, confirm the
pot row (60 mm outer edge, square, `measured`), and click ≥ 2 (better 3+) points on each flat rim edge of the 13 top
photos (+ two ruler ticks for the cross-check) with a click uncertainty in px; then rerun
`prepare --mode real` + `run`.

Full suite after T6: `tests/` **441 passed, 1 skipped** (T6 adds 26); `tools/tests/test_tomato_fsp_pipeline.py` 28 passed (read-only).


## 7. Rim-point clicking tool (2026-10-12, user accepted the offer)

`python -X utf8 -m tomato3d.cli.rim_points_tool --package build/p1_state_20261012_10 --out build/rim_click_20261012_02`
→ open `build/rim_click_20261012_02/index.html` in a browser (works from the file; the photos load by relative
path). Thirteen real top photos; the person clicks the FLAT parts of the four outer rim edges (the chamfered corners
are skipped: the side lines are extended and intersected) and optional ruler ticks, enters initials and a click
uncertainty in px, and saves `rim_points.csv` in exactly `potscale.RIM_POINTS_COLUMNS` for
`data/records/pots/`. Live preview (fitted lines, corner square, scale, ruler disagreement, per-side residual) is
computed by `rim_core.js`, which equals `potscale.py` (node parity test, 1e-6); the record's values still come from
the P1 run. Work is kept in the browser (localStorage) and can be re-imported from the CSV.

Pixel grid: the page shows the decoded JPG copies; the builder checked for all 13 that the raw HEIC still has the
package sha256, that its primary size (`ispe`) is 3024×3024 like the JPG, and that neither has a rotation (`irot` 0,
no EXIF orientation). Pixel content was not compared (no HEIC decoder here); the page says so. Clicks use fractional
canvas coordinates; verified in the in-app browser: 10 synthetic clicks recorded with correct sides, and with zoom a
click lands within 0.42 px of its target. Test server origin (localhost:8837) cleared afterwards; port 8821 untouched.
`build/rim_click_20261012_01` is superseded (integer click coordinates). Tests: `tests/test_rim_points_tool.py` (2);
full `tests/` 443 passed, 1 skipped.


**Update (same day):** the user reported the photos did not show. A page opened as a saved snapshot (e.g. the app's file preview) does not load neighbouring files, so `_02` showed no photo there. `build/rim_click_20261012_03/index.html` (17 MB) embeds the original JPG bytes (same pixel grid) and the preview code; verified on localhost: 13 photos listed, 3024×3024 decoded and drawn. The app's file preview refuses a file this large, so open it in Chrome/Edge (double-click in Explorer). `_01`/`_02` superseded.


## 8. Real audit with the user's pot records (2026-10-12)

The user clicked the 13 top photos with the tool (flat rim sides, chamfers skipped; 2 points per side, dwt_101 side 1: 3; click uncertainty 4 px; no ruler ticks) and instructed this session in chat ('직접 올려') to place the files: `data/records/pots/rim_points.csv` (= the saved `rim_points (10).csv`, byte-identical) and `data/records/pots/pot_spec.csv` (= the template row: square, `dwt_1*`, 60 mm outer edge, 70 mm deep, measured). `build/p1_state_20261012_11`: **13 of 117 scale gaps closed** - every top capture solved, `pot_rim_outer_edge_square`, `rim_plane`, `none_single_source`; mm_per_px 0.0332-0.0493 (median 0.0401), 1-sigma 0.16-0.23 %, perspective anisotropy 1.2-4.5 %. Remaining 104 scale gaps = level/side views (rim edge-on). Codex audit 130 -> 117 gaps (104 scale + 13 optical). run/collect 3 (valid, partial), replay 17/17; the input snapshot now lists both pot records. A visual check of the fitted squares over the 13 photos matched the rim outlines. With 2 points per side the line-fit residual cannot flag a misplaced click, and no ruler cross-check exists yet (both optional, see section 7).


## 9. CORRECTION - direction of the rim-plane bias (2026-10-12)

Sections 6 (T6.3) and 8 said a rim-derived scale *underestimates* leaves above the rim, repeating the T6 prompt. That is the wrong direction. A leaf above the rim is nearer the camera, so it is magnified in the photo; multiplying its pixels by the rim's mm/px gives a size too LARGE by Z_rim / Z_leaf. Fixed in `potscale.py` (docstring, `PLANE_NOTE`), the template README and the test; packages rebuilt: real `build/p1_state_20261012_12` (supersedes `_11`, same 13 solved scales, corrected note; replay 17/17) and truss fixture `build/p1_state_20261012_13` (supersedes `_09`; replay 54/54). The opposite case is a plant part BEHIND a reference plane (e.g. the stem 30 mm behind the pot's front face in a level view): smaller in the photo, so a front-face scale underestimates it.

Size of the effect (estimate, not applied): the HEIC EXIF gives the camera (iPhone 16, 5.96 mm, 35 mm-equivalent 52 mm, EXIF frame 4032x3024; the stored photo is a 3024x3024 crop). With f = 5824-6057 px (width- vs diagonal-based equivalence; the crop keeps the pixel scale - unverified) the 13 top views put the camera 193-299 mm above the rim (median ~240). A leaf 20 mm above the rim then reads x1.09 in length (x1.19 in area), 50 mm above x1.26 (x1.59). No correction factor is applied (T6 rule); a correction needs each organ's height above the rim (from side views) and a verified focal length.
