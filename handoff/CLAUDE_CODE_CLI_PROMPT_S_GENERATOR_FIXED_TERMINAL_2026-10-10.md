# Prompt S — generator extension: pin observed terminal leaflet in build_compound

Paste to Claude Code. tomato3d/synth/ and tests/ are Claude Code's column; Codex (phynotype2) consumes
this API and must not copy generator internals (_events, derive, interpret).

## Why
phynotype2 spec section 6.4 assumed an adapter could choose `contour_index` for the visible terminal
leaflet. Verified 2026-10-10: `sample_interior` (compound_leaf.py:52) draws `terminal_rel_length` and every
leaflet's `contour_index` internally, and `build_compound` (compound_leaf.py:205) has no override path.
Filtering many free samples for a matching terminal wastes almost all of them. Add a narrow override.

## Change (minimal)
1. `sample_interior(cfg, compound, n_contours, seed, attempt, fixed=None)` and
   `build_compound(cfg, compound, contours, seed, plant_id, fixed=None)`.
2. Allowed keys (whitelist; any other key -> ValueError):
   - `terminal_rel_length`: float
   - `contour_index`: {"T": int}  (only the terminal tag in this version)
3. Apply AFTER the normal draw, overwriting only the pinned values. The RNG call sequence must stay
   exactly as today, so for the same (seed, attempt) every NON-pinned parameter equals the unpinned draw.
4. Pinned values hold across all resample attempts (the attempt loop redraws only the free values).
5. `fixed=None` must reproduce current behaviour bit-for-bit. `config_hash` is unaffected (fixed is a call
   argument, not config).
6. Provenance in the returned interior:
   `params["fixed_from_observation"] = {key: value, ...}` and the T leaflet gets
   `contour_source = "observed"` (others `"sampled"`).
7. Out-of-prior values: if a pinned `terminal_rel_length` lies outside the config range, do NOT clamp and
   do NOT touch the config; record `params["fixed_outside_prior"] = ["terminal_rel_length"]`. Observation
   outranks the (user_assumed) prior, but it must stay visible.
8. Bud case: if the compound is a bud (`rachis_arc_length_mm < min_compound_rachis_mm`) and `fixed` pins
   terminal values, raise a clear error — a bud has no separate terminal to pin.
9. If pinned values make `check_contract` fail on every attempt, the existing `CompoundRejected` is raised
   with the rejection log; no silent fallback to unpinned sampling.

## Tests (tests/test_compound_fixed.py)
- regression: for >= 20 (seed, compound) cases, `fixed=None` output equals the pre-change output
  (store a hash of the interior before editing).
- pin honoured: T contour_index and terminal_rel_length equal the pinned values on the accepted attempt
  and on every recorded rejected attempt.
- free values unchanged: for a fixed (seed, attempt), all non-pinned params equal the unpinned draw.
- unknown key -> ValueError; bud + pin -> error; out-of-prior pin -> flagged, not clamped.
- existing synth + raster tests still pass.

## Do not
- Change any range in the config or call apply_measured_range (it would relabel assumptions as measured).
- Add whole-plant, Blender, texture, selection/scoring, or growth logic — those belong to phynotype2 / P3.
- Change scene.py call sites (they keep fixed=None).
LOG one line on completion, naming the commit/files and the regression-hash result.
