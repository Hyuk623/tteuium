# P1 numbers that are generator-relative, not plant-verified (caveat, 2026-10-12)

Author: Claude Code (P1 session). Source: the top→3D session's generator audit, `handoff/TOP_TO_3D_EXECUTION_2026-10-12.md`
§T0 and `build/topview_20261012_01/t0_calibration.json` (`generator_audit`). Referenced from
`handoff/P1_EXECUTION_2026-10-11.md` and `handoff/P1_INVENTORY_2026-10-11.md` (appended pointers; nothing above edited).

## The audit finding
The synthetic generator run `build/synthetic_dwarf_tomato_20261008_07/O-mature` conflicts with measured plant facts:
- leaflet true length/width ratio p10/p50/p90 **0.89 / 1.19 / 1.51**, only **16 %** inside the measured **1.4–1.7**
  (library contours are already-foreshortened top-view masks, and `leaflet_width_scale` 1.2–1.5, `user_assumed`,
  widens them; the pair was tuned to match the TOP PROJECTION, so the 3-D leaflet is wrong while the projection looks
  right);
- **6–8 compounds** per plant against a real **4–5** (`user_stated`);
- `rachis_droop_deg` is one continuous droop (no flat/bent mixture); the roll is not a curl measurement.

P1's synthetic packages, its occlusion-completion candidates and its side-geometry validation all use this generator
and these O-mature scenes (and the R.1 side scenes built from the same generator).

## P1 numbers to read as generator-relative

| P1 number | where | why it is generator-relative |
|---|---|---|
| Optical leaflet surfaces of the fixtures (129 / 45 `supported` truth leaflets) and their one-sided areas | `build/p1_state_*` fixtures, `optical_surfaces/` | they ARE the generator meshes (wrong 3-D aspect) |
| Occlusion completion: 5 → 10 of 14 compounds kept at coverage ≥ 0.98; candidate shapes | P1 fixes A4, `completion_report.csv` | candidates are generator compounds (pool donors and `build_compound`); a real leaflet of L/W 1.4–1.7 may not be reachable by them |
| Tracking: 0 wrong links, 0 fragments; 126 / 220 cross-axis pairs blocked | P1, side-shoot and truss fixtures | 6–8 compounds of generator shape per plant; a real 4–5-compound plant differs in crowding (could be easier or harder - untested) |
| Area check "observed visible area = truth" (57/59, 31/31) | `compare_observation.csv` | raster vs raster of the same meshes: tests the pipeline's bookkeeping, not plant realism (unaffected as a software check) |
| Truth-relative area/angle errors of the top-view proxies (blade azimuth top proxy minus truth) | `compare_observation.csv` | the error depends on leaflet shape and droop of the generator |
| `segment_index` / truss fixtures, side-shoot fixtures | `_13`, `_03` packages | structure is declared, not shaped: unaffected as software checks; any area/geometry number in them is generator-relative |

## Appear little affected - but NOT verified
- **A3 side-on angle rule** (R.1 150 scenes: median 5.9°, p90 13.7° vs first view 14.5° / 52.9°). It measures compound
  insertion / rachis angles from projected points, which depend mostly on compound direction, not on leaflet aspect.
  The droop distribution (single continuous droop) does enter θ and α, so the error figures describe the generator's
  droop range. **Not verified on real plants**; the 52 real side photos have no direction labels or points yet (R.5).
- Real-photo rim scale and camera pose (T6, side rim pose): independent of the generator (real photos, measured
  60 mm rim).

## What would make these plant-verified
Generator leaflet shape fixed against measured flattened leaflets (destructive capture protocol exists) and a
bend-type mixture from `data/records/leaf_bend/` (absent), or real labelled observations (top masks, side points)
replacing the fixture truth.
