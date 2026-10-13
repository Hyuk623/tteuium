# Claude Code — next session prompt (2026-10-10, consolidated)

Paste this file to Claude Code. It is the single paste target for this session. It inlines and corrects two
earlier notes, which stay in handoff/ as reference (handoff is append-only):
- `R_DECISIONS_2026-10-10.md` — N/O verdicts and the R.1 go-ahead (Tasks 1-2, unchanged).
- `CLAUDE_CODE_CLI_PROMPT_S_GENERATOR_FIXED_TERMINAL_2026-10-10.md` — generator extension (Task 3, CORRECTED:
  adds `width_scale` for the terminal leaflet, key-set-preserving provenance, documented pin semantics).

Ownership (CONVENTIONS): you write tomato3d/, tests/, build/, handoff/ (append-only). Codex owns tools/ and
phynotype2/. config/ and data/records/ are human. Read `handoff/R_SESSION_STATE_2026-10-10.md` first.

## Order
1. Task 1 — write the N/O records (bookkeeping; unblocks R).
2. Task 2 — R.1: 5 pilot scenes -> cy check -> 145 scenes -> package -> launch the Kaggle render.
3. Task 3 — generator extension, done WHILE Kaggle renders. Safe: the render package carries its own tomato3d
   snapshot, and the extension must be bit-identical at `fixed=None` (proven by test). Capture the regression
   hashes BEFORE editing compound_leaf.py.
4. Back to Task 2 — finalize + COCO export when the render returns.
LOG one line per task.

---

## Task 1 — N/O records (verdicts exactly as pre-declared)
Numbers come from `build/synthetic_dwarf_tomato_20261008_07/NO_analysis.json`; re-read them while writing.
Write the N/O rows into the c6_steps.csv, the C6_REPORT sections and the LOG close named in R_SESSION_STATE and
NOP_SESSION_STATE_2026-10-09 section 4.
- N-delight (specular de-light): C6 0.2807 vs G2-a 0.2752, delta +0.0055 [-0.0063, 0.0073] -> within noise;
  geometry identical to G2-a (verified). Specular highlights are not a C6 cause. Close N.
- O-mature (snapshot age + compound cap): realism correction NOT achieved.
  - rank ratio p50 1.859 (G2-a 1.731; band 1.0-1.2) -> declared reading "ratio >= 1.6: age/cap are not what sets
    the taper; report, no second change".
  - lt150 GT share 0.1634 (band <= 0.15) -> not passed.
  - C6 0.3089, delta vs G2-a +0.0337 [-0.0166, 0.0877] -> within noise, as pre-committed (no gain claimed).
- POST-HOC (label it so; not a result): ratio by drawn cap — cap 6: 1.351 (n=6), cap 7: 1.704 (n=2),
  cap 8: 2.165 (n=7). O draws 6-8 compounds per plant; real plants carry ~4-5. A lead for a future DECLARED
  cell only.
- C6 factor queue: N dead, O no gain -> P (curl) next, then A3 chroma.

## Task 2 — R.1 on the O-mature config
Run commands: R_SESSION_STATE, section "To run R.1". Before generating:
- Add an amendment entry to R_contract.json (do not rewrite earlier entries): "generator = O-mature
  (config sha a3bd428c...); O realism bands not met (rank ratio 1.859, lt150 0.163); compounds per plant 6-8 vs
  real ~4-5, so the box-count distribution differs from real; the synthetic set is judged only by the R.5 real
  held-out rule."
- Add `capture_rotation: "clockwise_assumed_unverified"` to the manifest. Rotation direction is not blocking:
  training labels are camera-relative, so only the quadrant converter depends on it. If the user later reports
  counter-clockwise, flip the converter sign and re-derive quadrants from stored predictions — no relabeling,
  no retraining.
- `compound_unclear` export is approved, with one rule: the synthetic unclear (within 10 deg of a bin edge) and
  the real `unclear` (human judgment) are different definitions. Exclude them from direction accuracy on both
  sides and report the unclear fraction separately for synthetic and real in R.5.
Keep the declared pre-render cy check (failure -> a declared amendment of `look_at_target.height_fraction`,
never a silent change). If `cli finalize` refuses the side manifest, write the short side finalize described in
R_SESSION_STATE.

---

## Task 3 — generator extension: pin the observed terminal leaflet (consumer: Codex, phynotype2)

### Why
phynotype2 builds candidate interiors for unclear compounds during top-view tracking
(`handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md`, section 6) and must keep a visible
terminal leaflet fixed while everything else varies. Verified against source on 2026-10-10:
`sample_interior` (compound_leaf.py:52) draws `terminal_rel_length` and each leaflet's `contour_index` and
`width_scale` internally, and `build_compound` (compound_leaf.py:205) has no override path. Chaining the private
functions (`_events`, `derive`, `interpret`) from outside would duplicate generator internals — not allowed.
Filtering free samples for a matching terminal would waste almost all of them.

### Already provided — reuse unchanged
| need | provided by |
|---|---|
| interior from skeleton conditions (attachment, direction, axis length, left/right extents, mm) | `build_compound` |
| per-seed variety: pair count, spacing, droop, bend/roll/twist, contours | `sample_interior` |
| reject-and-redraw with a rejection log | attempt loop / `CompoundRejected` |
| reproducibility: seed, attempt, params, config hash | `interior["attempt"]`, `interior["params"]` |
| leaflet meshes | `triangulate_contour`, `surface_points` |

Top-view projection is NOT a generator job: phynotype2 implements its own (tomato3d.synth.raster needs a
board-posed camera).

### API
```
build_compound(cfg, compound, contours, seed, plant_id, fixed=None)
sample_interior(cfg, compound, n_contours, seed, attempt, fixed=None)

fixed = {
    "terminal_rel_length": float,     # optional
    "contour_index": {"T": int},      # optional
    "width_scale":   {"T": float},    # optional
}
```
Whitelist only. Any other key or tag (pairs, intercalaries, bend/roll/twist, ...) -> ValueError. New keys need
a new declared prompt.

Correction vs the Codex table and Prompt S: `width_scale` is included because `flat_outline` is
`base + length*c_x*heading + length*width_scale*c_y*left`. Pinning length and contour without `width_scale`
does not fix the outline.

### Semantics (write into the docstring — the consumer depends on them)
- `terminal_rel_length` pins the TRUE midrib length of the terminal leaflet, laid flat before bend/roll, as a
  fraction of the whole compound axis (`rachis_arc_length_mm` = rachis + terminal). It is not a projected
  length. The consumer de-projects (phynotype2 section 6.3) and records that step as assumed.
- Pinning it also fixes the size scale of every lateral leaflet (pair size = terminal x taper ramp;
  intercalary = intercalary_rel_size x terminal). Lateral variety then comes from pair count, `pair_taper`,
  asymmetry, positions and `width_scale`. Document this; do not decouple it.
- The terminal's bend/roll/twist stay sampled: a single top view cannot identify them, and their effect on the
  projected outline is candidate diversity that phynotype2 scores.

### Rules
1. Draw everything exactly as today, then overwrite only the pinned values. The RNG call sequence is unchanged,
   so for the same (seed, attempt) every non-pinned value equals the unpinned draw.
2. Pins hold on every attempt of the resample loop.
3. `fixed=None` reproduces today's output INCLUDING dict key sets (scene JSON and parameter hashes must not
   move). Provenance keys are added only when `fixed` is given:
   - `params["fixed_from_observation"]` = the pinned dict;
   - `params["fixed_outside_prior"]` = pinned names outside their config range (`terminal_rel_length` vs its
     range, `width_scale` vs `leaflet_width_scale`);
   - the T leaflet gets `pinned_fields` = list of its pinned field names.
4. Out-of-prior pins: never clamp, never edit config; flag them (rule 3). The observation outranks the
   user_assumed prior, but it must stay visible.
5. `contour_index` outside `[0, n_contours)` -> ValueError (invalid, not out-of-prior).
6. Bud (`rachis_arc_length_mm < min_compound_rachis_mm`) with a `terminal_rel_length` pin -> ValueError (a bud's
   terminal is the whole axis). `contour_index` / `width_scale` pins on T stay valid for buds.
7. If the pins make `check_contract` fail on every attempt, raise `CompoundRejected` with the log. No fallback to
   unpinned sampling.

### Tests (`tests/test_compound_fixed.py`, tomato_synth env)
- Capture first: with the CURRENT code, hash the interiors of >= 20 (seed, compound) cases and save them to
  `tests/data/compound_fixed_regression.json`. Then edit. The test asserts `fixed=None` matches those hashes.
- Pins honoured on the accepted attempt and on every rejected attempt; T `length_mm` equals
  `terminal_rel_length * rachis_arc_length_mm` (float tolerance).
- Free values equal the unpinned draw for the same (seed, attempt).
- `flat_outline` of T reproduces the pinned contour x `width_scale`.
- Errors: unknown key/tag, bad contour index, bud + terminal pin. Out-of-prior: flagged, not clamped.
- Existing synth, raster and sideview tests still pass.

### The generator must not
- generate whole plants, render with Blender, or add textures;
- choose or score candidates (phynotype2's job; it never settles on one);
- predict growth or the 12 h change (the P3 stage; the generator only makes "possible shapes at this instant");
- edit any config range or call `apply_measured_range` (it would relabel assumptions as measured);
- change existing call sites (they keep `fixed=None`; grep for them first).

### Limit (copy into the docstring and into the Codex note)
Every generator range is `source_kind = user_assumed`, and the generator has not passed C6. Candidates are
hypotheses consistent with the observation, not estimates. The consumer keeps
`prior_status = "user_assumed_unvalidated"`.

### Last step: note for Codex (new file; do not edit Codex's files)
Write `handoff/NOTE_TO_CODEX_GENERATOR_FIXED_API_2026-10-10.md` with the final signature, the semantics above,
the test file name, and two fixes for phynotype2 section 6.4:
(a) replace "the adapter chooses contour_index" with a call to `build_compound(..., fixed=...)` that pins
`contour_index` AND `width_scale` (plus `terminal_rel_length` when the terminal is observed); never chain private
generator functions; keep recording `terminal_contour_source = observed_match` per candidate as already specified;
(b) the top-view projection is orthographic but the photos are perspective (hand-held phone, 2x): the error is
small near the frame centre and grows toward the edges — record it as an assumption in scoring.

---

## Out of scope this session
- Prompt P (curl, the next C6 factor) and Prompt Q2 (board-free 3D): separate runs when the user says go.
- Labeling the 52 real side photos: human work.
- Anything in tools/, phynotype2/, config/, data/records/.
