# Claude Code — P1: the scale reference moves to the inner rim line, 10 mm below the rim (2026-10-13)

Implementer: **Claude Code, the P1 session** (owner of `tomato3d/state/potscale.py`, `schema.py`, `camera.py`,
`tomato3d/cli/rim_points_tool*`). Follows the rim-detection correction reported today (the "automatic found the
outer rim better" claim was withdrawn; `build/rim_click_side_20261012_03` and its proposals are **void**).

## 1. New measurements (user, 2026-10-13, caliper, `measured`)
| | value |
|---|---|
| Outer top edge, across flats | **60 mm** (already recorded) |
| **Inner top edge, across flats** | **59 mm** |
| **Medium surface below the rim** | **10 mm** |
| Wall taper | **none — the inner dimension does not change with depth** |

Cross-check that already passed: your own photometry put the outer rim 0.5–1.2 mm outside the soil boundary, and
60 − 59 = 0.5 mm per side. Caliper and image agree at the low end; the caliper is the authority.

## 2. The decision
**The inner line (the soil boundary) becomes the primary scale reference.** It is the sharpest line in both views
and it now has a measured length. The outer 60 mm stays as a cross-check, not as the primary.

**But the inner line is NOT in the rim plane.** The medium sits 10 mm below the rim and the walls are straight, so
the visible square is 59 mm **at a plane 10 mm below the rim** — further from the camera. The reference is therefore
the pair *(59 mm, plane = rim − 10 mm)*, and the two numbers must never travel apart.

**Why this matters more than the 1.1 % you were weighing.** A plane 10 mm further away yields a larger mm/px. At the
camera distances you measured (193–278 mm), treating the inner line as if it sat in the rim plane makes every real
length **3.6–5.2 % too large**, and areas **7–11 %** too large. That error would enter all 444 leaflet and 67
compound millimetre values from `build/topview_20261012_02/`.

## 3. Work orders
**R1. Record the measurements.** Add `pot_rim_inner_edge_mm`, `medium_surface_depth_below_rim_mm` and `wall_taper`
to the pot-spec schema and the `build/pot_records_template/` header, each with `source_kind`. Old records without
the new columns must still parse. Do not write into `data/records/` — the human copies the template. (The human
also still needs to replace the `EXAMPLE_square_cell` row in `data/records/pots/pot_spec.csv`; say so again.)

**R2. Make the reference plane explicit and mandatory.** Every solved scale carries `scale_reference` (which
feature) **and** `scale_reference_plane` (`pot_rim` | `medium_surface`) with the plane's offset from the rim. The
validator **rejects a millimetre value whose reference plane is unstated** — the whole point of this task is that a
length without its plane is now known to be wrong by about 4 %.

**R3. Re-derive the 13 top captures on the inner line** and report, per capture, the old and new mm/px, the change
in solved scale and the change in the leaflet/compound areas. Preserve the earlier package; publish the new one
beside it. If the re-derivation moves areas by more than the stated uncertainty, that is the result — report it.

**R4. Confirm the side records.** The user's clicked points on `side_000` (13 photos) are on the inner line, so
they become valid records under the new convention. Void `build/rim_click_side_20261012_03` in place with a reason.
For 090/180/270, pre-fill proposals from the soil boundary for human confirmation — but the back edge was found in
only 1 of 52 photos because leaves genuinely occlude it, so solve from three edges and report the fourth as
`occluded`, not as a detection failure.

**R5. Recompute `plane_bias`.** The reference plane dropped by 10 mm, so the overestimate for anything above it
grows. Keep the sign convention `overestimates_above_rim` (rename if the plane name makes it misleading), state the
magnitude as a function of leaf height and camera distance, and **introduce no correction factor** — leaf height is
still unmeasured. Illustration only, never written into a package: at d ≈ 230 mm, a leaf 20 mm above the rim is now
about +14 % in length and +31 % in area, up from +9.5 % / +20 % under the rim-plane reference.

## 4. Acceptance
Old pot records parse unchanged; a mm value without `scale_reference_plane` is refused (test it); the 13 top
captures re-derive with a reported before/after table; the three-edge side solve reports the fourth edge as
`occluded`; `rim_click_side_20261012_03` is marked void and nothing consumes it; full `tests/` passes with counts.

## 5. Deliverables
Code + tests, `handoff/P1_RIM_INNER_PLANE_EXECUTION_2026-10-13.md` (+ `_KO.md`) with the before/after scale table,
the new package under `build/`, flow rows + `check_flow.py --md`, LOG claim first and result last.
