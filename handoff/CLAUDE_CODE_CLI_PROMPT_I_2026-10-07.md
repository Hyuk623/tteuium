# CLI prompt: Addendum I, local work (2026-10-07)

Read, in this order, then act:

1. `handoff/CLAUDE_CODE_CLI_ADDENDUM_I_LOCAL_AND_DESTRUCTIVE_2026-10-07.md` — the work. **Part 1 only** is yours.
2. `handoff/CLAUDE_CODE_CLI_ADDENDUM_H_GPU_SESSION_2026-10-07.md` — H.0 carries two corrections to Addendum G.
3. `handoff/CLAUDE_REVIEW_F2_F7_RESULTS_2026-10-07.md` — **overrides the earlier addenda wherever they conflict.**

Also read `CONVENTIONS.md`, the latest `handoff/LOG.md` entries and `handoff/TODO.md` first. Shared OneDrive
checkout; keep every existing analysis run intact.

## Standing corrections (a fresh session will not know these)

- **The generator already has interjected leaflets.** `compound_leaf.py` carries `intercalary_count` /
  `intercalary_rel_size` and places them between main pairs; B5a and `_04` use count 0–1 single-sided,
  `rel_size` 0.12–0.25 of terminal. Addendum F's "no class exists" wording is wrong — do not act on it.
- **"5–7 leaflets per compound" counts MAIN leaflets only** (F.12). The generator's realised ~5.0 is roughly correct
  on that basis. Never fold main and interjected into one "leaflets per compound" figure.
- **The F.2/F.7 classification tables are provenance only.** All three interjected training blades came from
  `leaf_51`, so there is no held-out validation, and the band sensitivity (13 / 7 / 2 / 1) indicates a continuum.
  Derive no parameter, GT rule or contamination claim from them. Never write "two interjected textures contaminated
  B5a".
- **B5c is rejected** (0.256 against B5a 0.328). The baseline is **B5a**: B4a framing ×1.4713, `leaf_srgb_mean`
  0.304–0.543, `texture_bank_v2`.
- **Addendum G.0 overstated one point.** The 0.85 solidity floor is **unjustified**, not disproved by
  `leaf_47…51` — detached main blades sit at 0.82–0.89. The refutation rests on the `human_full` set (8 of 15 below
  0.85, min 0.567). And `contact_fraction` is a weak occlusion test: `human_full` 0.003–0.455 overlaps
  `human_partial` 0.052–0.397.

## Do now — Addendum I Part 1, in this order

**All local. No rendering, no Kaggle, no GPU, no generator run.**

1. **I.1 noise floor (first, and report before continuing).** Re-score the existing B5a 60 views on CPU, **cache the
   detections to disk** this time, bootstrap over the 5 scenes and over the 60 views, and do the same for B4a (its
   per-GT file exists) and B5c. Deliver the smallest C6 difference distinguishable from noise at n = 5 scenes, then
   put B6 +0.067, B5a +0.043, B5c −0.072 and F.11a +0.031 beside it and mark each `supported` / `within noise` /
   `unresolved`. **Do not revise any earlier decision — report and stop at this point for the user.**
2. **I.2 projection bias.** Rig masks (1163) vs flattened library contours (61) vs the 9 detached blades, same
   normalised-contour pipeline, reporting solidity, aspect and normalised perimeter per population. State the
   projected-to-flattened offset as a distribution and say whether it is large enough to matter for G.2.
3. **I.3 acceptance curve.** `items/` holds the rejected candidates (292 for dwt_01 against 268 accepted). Compute
   acceptance rate as a function of visible area, solidity and aspect across all four plants. **Report only.**
4. **I.4 ruler scale by short-edge width.** Implement the two-long-edge fit. **Ask the user for the ruler's measured
   width first and stop until they answer** — do not guess 3 cm.
5. **I.5 Addendum E shoot sheet.** Produce the E.1 pack: 4 failing + 2 control B5a views, the per-view sheet and the
   detection-overlay images.

Output to `build/local_queue_20261007_01/`, `I1`–`I3` rows in `c6_steps.csv` marked `diagnostic`, and an Addendum I
section in `C6_REPORT.md`.

## Part 2 is the user's hands, not yours

Four plants will be destructively measured. **You do not perform or simulate it.** You may only prepare, under
`data/raw/`, the folder structure and empty capture-CSV templates the protocol needs:

- a per-plant capture CSV for the intact capture (Addendum A columns);
- a defoliation-sequence CSV for plant 1: `plant_id, step_index, removed_compound_id, photo_file, captured_at, notes`;
- a blade CSV for plants 2–3: `plant_id, compound_id, station_index, side, class_by_position, photo_file`.

Leave every data row empty. Do not invent IDs beyond the plant IDs the user gives you.

## Do not, in this run

- No **G.2**, no **F.3** (including the intercalary count change), no new run folder `_05` or `_06`.
- Do not rebuild the texture bank, change the GT acceptance rule, or change the B1 rule's `min_solidity` 0.434 —
  it is a scoring rule; changing it mid-stream breaks comparability with every earlier step (G.3). I.3 informs its
  future re-derivation; it does not authorize it.
- Do not touch `stage1_contract.json` or `contract_amendments.json`.
- `data/raw/` is human-owned: create the templates named above and nothing else; do not edit
  `leaf_library_capture.csv` (the `leaf_47…51` rows stay in the supplement CSV).
- Do not treat the blank human-review template as a label set. Zero human reviews have been entered.
- Do not re-run the generators or the detector merely to read these files.

## Report

Korean 5-line summary, ending with the I.1 noise floor and which earlier conclusions it does not support.
