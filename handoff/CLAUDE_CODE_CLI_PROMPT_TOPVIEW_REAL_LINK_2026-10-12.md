# Claude Code — top view → 3D: real-photo link, sign fix, compound-level masks (2026-10-12)

Implementer: **Claude Code, the top→3D session** (owner of `tomato3d/topview/`, `tomato3d/synth/pairs.py`,
`tests/test_topview.py`). Source of this prompt: `handoff/TOPVIEW_P1_CROSS_BENEFIT_2026-10-12_KO.md` (the
cross-session review). Runs in parallel with a P1 session (`CLAUDE_CODE_CLI_PROMPT_P1_SIDE_RIM_POSE_2026-10-12.md`);
do not edit that session's files.

## 0. Read first (list what you read; say what is missing)
`handoff/TOPVIEW_P1_CROSS_BENEFIT_2026-10-12_KO.md`; your own `handoff/TOP_TO_3D_EXECUTION_2026-10-12.md` (+`_KO`);
`handoff/P1_SEGMENT_TRUSS_EXECUTION_2026-10-12.md` §8 and the **corrected** T6 §3 of
`handoff/CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md`; `handoff/MTG_CONVENTION_2026-10-10.md` A3/A4/A5;
`handoff/DETECTOR_POLICY_2026-10-09.md`; `docs/정의집_토마토_2026-10-11.md` §2; `CONVENTIONS.md`; last 40 LOG lines.

## 1. Binding correction (X0) — the bias sign was wrong, and it was wrong in my prompt
A rim-plane scale **OVERestimates** anything above the rim: mm/px grows with camera distance, a leaf at height `h`
sits at `d_rim - h`, so the rim's mm/px applied to it yields too many mm. Bias factor = `d_rim / (d_rim - h)`; at
`d ≈ 23 cm`, `h = 2 cm` ≈ +9 % length / +19 % area, `h = 5 cm` ≈ +26 % / +59 %.
- Fix every place that says the opposite: `tomato3d/topview/measure2d.py` lines 10 and 229,
  `tomato3d/topview/geometry.py` line 209, and anywhere else the string appears (grep), plus your execution report.
- Keep the name `plant_local_mm` and keep the caveat on every value. **Do not introduce a correction factor** and
  do not invent a leaf-height distribution to correct with. A sensitivity table at `h = 1 / 2 / 5 cm` is allowed in
  the report only, labelled illustration, never written into a package as a value.

## 2. Work orders
**X1. Re-link the real photo to the pot record.** Your T1 run used the Roboflow download `IMG_8419.jpg`
(sha256 `dbaba82d…`), which is neither the original HEIC (`dd18df69…`) nor carries a plant id, so the rim record
cannot be found and every mm stayed `unavailable`. Use the package's own decoded top copies
(`build/roboflow_upload_20261009/top_level_views`) whose sha256 matches `captures.csv`, and carry `plant_id`
(`IMG_8419` = **dwt_113**) on every measurement row. Apply the same pixel-grid refusals `rim_points_tool` already
makes (raw sha256, HEIC `ispe` size, `irot` / EXIF rotation); refuse and report rather than assume the Roboflow JPG
shares the coordinate system. **A row without `plant_id` + the original hash may not carry mm.**

**X2. Real mm for all 13 top captures.** Against `build/p1_state_20261012_12` (or the newest real package), use the
per-pot rim scale: leaflet px → mm with the scale's sd propagated, the rim-plane caveat and the overestimate sign on
every row, and the **per-photo camera distance `d`** (rim homography + focal length) stored so the bias magnitude is
computable later from a leaf height. Report how many leaflets got mm, how many stayed `unavailable`, and why.

**X3. Neighbour-plant attribution.** Using the pot centre and rim polygon from the record, flag each detection as
inside / outside / ambiguous for its own pot — the two bottom-left leaflets of IMG_8419 are the known case. An
ambiguous leaflet stays `ambiguous`; never silently assign it.

**X4. Compound-level masks (this is what opens P1's real-photo observation path).** Today `measure2d` finds leaflets
only, stores no mask, and has no human check — P1 tracks **compounds**. Extend it: `compond_leaf` boxes from the
same detector → SAM prompts → **persist the masks** (RLE or PNG + manifest), derive per-compound leaflet membership
from the `leaf` / `terminal_leaf` / `leaf2` boxes inside each compound, and add a human-confirmation page in the
style of `rim_points_tool` (accept / reject / fix per instance) that writes a human-owned CSV template under
`build/`, **never into `data/records/`**. Every row stays `proposed` until a human confirms it; detector boxes
remain suggestions (DETECTOR_POLICY).

**X5. Synthetic top camera from measurement instead of assumption.** The real top cameras are 19–28 cm away and
median 8° off vertical (1–31°). Replace `pairs.py`'s assumed 85° / 270 mm top camera with that measured
distribution, declared as such, and state that the old assumption falls inside the measured range. **T2 stays
gated** by the missing bend record (`data/records/leaf_bend/`) — do not open it.

## 3. Acceptance
Tests for: the refusal when a photo's grid cannot be shown identical; no mm without `plant_id` + original hash;
mask persistence round-trip; compound → leaflet membership; `ambiguous` attribution kept. Grep proves no
"underestimate" wording survives. Report test counts and run the full `tests/` suite.

## 4. Deliverables
Code + tests; `handoff/TOPVIEW_REAL_LINK_EXECUTION_2026-10-12.md` (+ `_KO.md`) with commands, exit codes and every
blocked item with its owner (bend record and R.5 side-view direction labels are **human**); `flow/flow_map.csv`
rows for the touched paths + `check_flow.py --md` rerun; LOG claim first, result line last.
