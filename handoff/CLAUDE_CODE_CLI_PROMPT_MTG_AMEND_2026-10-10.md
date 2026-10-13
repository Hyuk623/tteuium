# Claude Code — MTG convention amendment A1 (2026-10-10)

Paste to Claude Code. Edit target: `handoff/MTG_CONVENTION_2026-10-10.md` (+ its schema/CSV header if they
exist). handoff/ is append-only in spirit: do NOT rewrite earlier text silently — append a section
`## 11. Amendment A1 (2026-10-10)` and, where an earlier line is now wrong, mark it `[superseded by A1.x]`
in place. LOG one line when done.

## A1.1 Rank anchoring — DECIDED (user, 2026-10-10)
The anchoring rule in section 5 (Claude's reading) is accepted as written:
- ranks are fixed at the plant's rank reference capture (`rank_reference_capture_id`) and never renumbered;
- a lost leaf keeps its rank; the next leaf does not become rank 1;
- new leaves above take max rank + 1;
- a lower leaf discovered later gets 0, -1, ... (existing ranks never shift).
Remove the open sub-question from section 8 (mark it resolved, decision 8.1b). Note: the variety is Micro-Tom
(determinate, self-pruning), so the main stem stops adding ranks after a few trusses; the rule needs no change
for that.

## A1.2 Plant-level attributes (scale 1)
Add to the Plant vertex:
| attribute | type | source status | note |
|---|---|---|---|
| `variety` | `micro_tom` \| `other` | user_stated | the 18 dwarf plants = Micro-Tom (user, 2026-10-10); 6 front-row plants = other (name unrecorded) |
| `slot_id` | string, e.g. `T2-row1-L` | user_stated (once the plant-ID-to-pot table exists; until then `unavailable`) | key into `data/records/env_light_20261010/plant_slot_light_ratio_20261010.csv` |
| `light_ratio` | float | `app_ratio` (new status value: uncalibrated phone-app ratio, ratio-only use) | copied from that CSV's `ratio_now` (rule v3: grid row 1 = wall side); never an absolute PPFD |
| `light_ratio_source` | string | — | file name + rule version, so a later re-map is traceable |
Add `app_ratio` to the source-status vocabulary in section 6. Do not invent slot_id values; leave
`unavailable` until the user supplies the plant-ID-to-pot table.

## A1.3 Other-variety plants (occluders only)
The 6 `variety = other` plants get a **plant-level MTG only** (Plant vertex + one Axis vertex) with
`height_mm`, `crown_width_mm` (each with status; `unavailable` allowed) and `slot_id`. No compound/leaflet
vertices are required. Purpose: they enter light calculation as shading neighbours (front row, taller),
and they are excluded from trait measurement, generator calibration and FSP parameter fitting.
phynotype2 must never attach their leaves to Micro-Tom tracks (already stated in the env/light record).

## A1.4 Elevation sign — make it explicit
Section 5 geometry says `elevation_deg` is signed but does not say which way. Fix:
`elevation_deg` = angle of the organ direction above the horizontal plane of the file's `frame`
(**+ = upward, - = downward**, range -90..+90), computed as `atan2(dz, hypot(dx, dy))` — the same
convention as camera elevation in `tomato3d/synth/contours.py`. Before writing, grep the generator for how it
stores leaflet/rachis inclination; if it uses the opposite sign or a from-vertical angle, do not change the
generator — add a documented conversion in the convention and report the mismatch.

## A1.5 Bend-type measurement points reference MTG vertices
In the CompoundLeaf bend attributes, replace free-floating points P0..P3 with vertex references:
- P0 = base of the compound's Petiole vertex (its insertion on the stem node; use the Petiole class code
  already defined in section 4 — do not reuse leaflet tags like `P1L`);
- P1 = node of lateral pair 1 (the RachisSegment boundary carrying `P1L/P1R`);
- P3 = node of the last lateral pair;
- P2 = midpoint of the rachis path between P1 and P3 (derived, not stored).
`theta_deg` and `chord_over_path` are then derived from vertex geometry; store them with status
`derived` and keep `rachis_bend_type` as the human label (flat / bent / intermediate / unknown) until the
boundaries are set from the 7 example photos (`data/records/compound_bend_types_20261010/`).
If geometry for those vertices is `unavailable`, theta is `unavailable` (never guessed).

## Checks
- Re-render the worked example (section 10): add `variety micro_tom`, `slot_id unavailable`,
  `light_ratio unavailable` (dissected leaf's plant/pot not recorded).
- If `mtg_schema.json` / `mtg_vertices.csv` header / phynotype2 `tracks.csv` columns exist, add the new
  attributes there too; touch only files you own (tomato3d/, tests/, build/, handoff/). If a column must go into
  phynotype2/ (Codex), write it as a request in `handoff/NOTE_TO_CODEX_MTG_A1_2026-10-10.md` instead.
- No changes to config/ or data/records/.

## Out of scope
θ boundary values, leaflet-blade curl criterion, brown-margin area rule (pending user decisions).
