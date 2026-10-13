# CLI prompt: run Addendum G.1 (2026-10-07)

Read, in this order, then act:

1. `handoff/CLAUDE_REVIEW_F2_F7_RESULTS_2026-10-07.md` — Claude's review. **It overrides the earlier addenda
   wherever they conflict.**
2. `handoff/CLAUDE_CODE_CLI_ADDENDUM_G_CONTOUR_POOL_BIAS_2026-10-07.md`
3. `handoff/CLAUDE_CODE_CLI_ADDENDUM_F_COMPOUND_STRUCTURE_2026-10-06.md`, sections **F.11** and **F.12**

Also read `CONVENTIONS.md`, the latest `handoff/LOG.md` entries and `handoff/TODO.md` before editing anything.
This is a shared OneDrive checkout; keep the existing analysis runs intact.

## Corrections that override the earlier text

- **Addendum F sections F.0 / F.6 / F.7 claim the generator has no interjected-leaflet class. That is wrong.**
  `tomato3d/synth/compound_leaf.py` carries `intercalary_count` and `intercalary_rel_size` and places them in
  `intercalary_gaps` between consecutive main pairs, so the alternation F.6 describes is **already modelled**.
  B5a and run `_04` use `intercalary_count` 0–1 (single-sided) and `intercalary_rel_size` 0.12–0.25 of the terminal
  leaflet. The real gaps are **count, pairing, and the shared rather than class-specific contour pool**. Do not act
  on the "no class exists" wording anywhere it appears.
- **F.6's "the generator makes about half the leaflets" is corrected by F.12.** 5–7 per compound counts **main**
  leaflets only; the generator's realised ~5.0 per compound is roughly correct on that basis. Interjected leaflets
  are counted separately and are never folded into a "leaflets per compound" figure.
- **The F.2/F.7 classification tables are provenance only** (library 140/8/88, flattened 44/1/16, SAM 860/11/292,
  bank 83/2/30). All three interjected training blades come from `leaf_51`, so leave-photo-out deletes the entire
  class and there is no held-out validation; and the unknown-band sensitivity (13 / 7 / 2 / 1 candidates across band
  factors 0 / 0.5 / 1 / 1.5) indicates a continuum rather than two separable populations. **Do not derive generator
  parameters, GT rules, or any contamination claim from them.** The texture bank's class composition is unknown —
  never write "two interjected textures contaminated B5a".

## Do now — Addendum G, section G.1 only

**Local. No rendering, no Kaggle, no detector inference, no generator run.** Follow G.1 items 1–4 exactly as written,
including:

- the four candidate filters, each reported with pool size **and** the pool's solidity and normalised-perimeter
  distribution beside the full 1163 distribution (representativeness is the target, not pool size);
- the `contact_fraction` and `dominant_fraction` distributions of the **19** `human_full` / `human_partial` masks,
  which are what should set the occlusion threshold instead of the assumed 0.10;
- the unoccluded-blade measurement from `data/raw/leaf_library/leaf_lib_20261006/leaf_47…51.png` and the seven
  `compound_structure` photos, respecting the `leaf_49` on-ruler and `leaf_48` hand-occlusion caveats from F.8.

Output to `build/contour_pool_20261007_01/`.

**Finish by stating:** which filter G.1 selects and why; what the pool size becomes; the pool's normalised-perimeter
distribution beside the full 1163; and whether the `leaf_47…51` measurement refutes the 0.85 solidity floor outright.
**Then stop and report.** Add `G1` rows to `c6_steps.csv` marked `diagnostic` and an Addendum G section to
`C6_REPORT.md`.

## Do not, in this run

- Do not run **G.2** or any generator change, and do not create run folder `_05` or `_06`.
- Do not run **F.3** in any form, including the intercalary count/pairing change. It is a generator change, it comes
  after G, and it needs its own declaration and falsification condition.
- Do not rebuild the texture bank, change the GT acceptance rule, or change the B1 rule's `min_solidity` 0.434 —
  it is a scoring rule and changing it mid-stream breaks comparability with every earlier step (G.3).
- Do not touch `stage1_contract.json` or `contract_amendments.json`.
- Do not carry **B5c** forward anywhere: it scored 0.256 against B5a's 0.328 and is rejected. The baseline to carry
  is **B5a** (B4a framing ×1.4713, `leaf_srgb_mean` 0.304–0.543, `texture_bank_v2`).
- Do not re-run the generators or the detector merely to read these files.
- `data/raw/` is human-owned. The `leaf_47…51` rows stay in
  `build/compound_structure_f2_f7_20261006_01/leaf_library_capture_supplement.csv`; do not edit
  `leaf_library_capture.csv`.
- Do not treat the blank human-review template as a label set. Zero human reviews have been entered.

## Report

Korean 5-line summary in your reply, ending with the selected filter and the resulting pool size.
