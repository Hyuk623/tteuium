# Claude Code — P1: side-photo rim points, camera pose, focal cross-check, generator caveat (2026-10-12)

Implementer: **Claude Code, the P1 session** (owner of `tomato3d/` state·cli·calib and `tests/`). Source of this
prompt: `handoff/TOPVIEW_P1_CROSS_BENEFIT_2026-10-12_KO.md`. Runs in parallel with the top→3D session
(`CLAUDE_CODE_CLI_PROMPT_TOPVIEW_REAL_LINK_2026-10-12.md`): **do not touch `tomato3d/topview/` or
`tomato3d/synth/pairs.py`**, and do not touch Codex files (`tools/vtc_*`, `tools/tomato_fsp_*`, `tools/fsp_*`),
`tools/microtom_*`, `config/`, `data/records/`.

## 0. Read first (list what you read; say what is missing)
`handoff/TOPVIEW_P1_CROSS_BENEFIT_2026-10-12_KO.md`; `handoff/P1_SEGMENT_TRUSS_EXECUTION_2026-10-12.md` (+`_KO`) §8;
the **corrected** T6 §3 of `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md`;
`handoff/TOP_TO_3D_EXECUTION_2026-10-12.md` §T0 (generator audit); `handoff/MTG_CONVENTION_2026-10-10.md` A3/A5;
`docs/정의집_토마토_2026-10-11.md` §2; `tomato3d/cli/rim_points_tool.py` docstring; `CONVENTIONS.md`; last 40 LOG lines.

## 1. Binding correction (Y0) — same sign error, in P1's own words
The rim plane **OVERestimates** leaves above it (`bias = d_rim / (d_rim - h)`; at `d ≈ 23 cm`, `h = 2 cm` ≈ +9 %
length / +19 % area). Correct `tomato3d/state/potscale.py`, any package note or validator message, and the P1
report where the sign is stated the other way. Keep `plant_local_mm` and the caveat; **no correction factor** and
no assumed leaf height. Record, per capture, the camera distance `d` so the bias is computable once a real leaf
height exists.

## 2. Work orders
**Y1. Point tool for the 52 side photos.** Extend `tomato3d/cli/rim_points_tool` (`--views side`, default stays
top) to the 13 plants × 4 azimuths in `build/roboflow_upload_20261009/side_views`
(`dwt_1NN_side_{000,090,180,270}.jpg`, ≈25° elevation). Same pixel-grid refusals as today (raw sha256, HEIC `ispe`,
`irot` / EXIF rotation). Click targets: the visible flat outer rim edges **and ruler ticks where a ruler is in
frame** (ticks are what finally gives a second scale source). Keep `RIM_POINTS_COLUMNS` as it is if the capture is
already identified; if one new column is unavoidable, add exactly one, state it in the validator and in the
`build/pot_records_template/` header, and keep old records readable.

**Y2. Focal basis — close the 12 % self-check.** EXIF: 5.96 mm, 35 mm-equivalent 52 mm (2× zoom), stored 3024×3024
cropped from 4032×3024. Compute `f_px` on both bases (pre-crop width → ≈5824 px; diagonal → ≈6057 px), report which
one closes the two-axis self-check that is now off by up to 12 %, and **if neither closes it, say the crop offset is
unknown and keep every pose flagged `approximate`**. A pose whose self-check fails may not be published without
that flag.

**Y3. Side-view scale and pose.** Once rims are clicked, derive per-photo scale + camera pose for the side captures
and report: how many of the remaining **104** scale gaps close (up to 52 side views), what remains, whether a
vertical (height) scale now exists, and the uncertainty per photo. The 13 optical-surface gaps are Q2 and stay open.
Where a ruler tick record exists, apply the STAGE1 rule (≤2 % accept, >5 % stop and report) and raise
`scale_sources` to 2; with rim only it stays 1, no cross-check.

**Y4. Pose table as a declared artifact (Q2 input, not Q2).** Write the per-capture pose table (top + 4 sides per
plant) into the real package with status `approximate` / `validated` and its source. **Do not implement**
`recon` / `fuse3d` — board-free 3D (Q2) remains a separate decision.

**Y5. Generator caveat into the P1 record.** The top→3D session's audit found the generator's leaflet length/width
ratio is 1.19 against a measured 1.4–1.7 (only 16 % inside) and 6–8 compounds against a real 4–5. P1's synthetic
packages and the occlusion-completion candidates use the same generator and the same O-mature scenes. Append a
short, dated caveat to `handoff/P1_EXECUTION_2026-10-11.md` / `P1_INVENTORY_2026-10-11.md` (or a new short note doc
referenced from both) saying which P1 numbers are **generator-relative rather than plant-verified**, and which
appear little affected (A3 side angles, median 5.9° — unverified, say so).

**Y6. Re-run the real audit** into a new `build/p1_state_*` after Y1–Y3 and report the gap counts before/after.

## 3. Human items — state them in the report, do not do them
1. Click the rims (+ ruler ticks) on the 52 side photos with the extended tool.
2. `data/records/leaf_bend/` bend records — still the gate for `BENT_FRACTION`, P1's bend field and the top→3D T2.
3. `data/records/pots/pot_spec.csv` is still the template EXAMPLE row: `pot_type` `EXAMPLE_square_cell` → a real
   name and the `"EXAMPLE ROW …"` note removed. The measured values in it are already the user's caliper numbers.
4. R.5 side-view direction labels; plant_id ↔ slot map; measured PPFD and lamp geometry; sowing dates.

## 4. Acceptance and deliverables
Tests: side-view refusal cases, both focal bases, pose flagged `approximate` when the self-check fails, no mm
without its uncertainty, old rim records still parse. Full `tests/` suite with counts.
Deliver: code + tests, `handoff/P1_SIDE_RIM_POSE_EXECUTION_2026-10-12.md` (+ `_KO.md`) with commands, exit codes and
blocked items with owners, the new real package, `flow/flow_map.csv` rows + `check_flow.py --md` rerun, LOG claim
first and result line last.
