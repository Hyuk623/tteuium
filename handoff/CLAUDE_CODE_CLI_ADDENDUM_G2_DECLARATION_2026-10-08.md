# Addendum G.2 declaration: contour pool D, with the two renderer defects that would otherwise confound it (2026-10-08)

**Declared before rendering.** Detector frozen (sha256 `609fd7ae…`); no training on synthetic; no threshold changed
after a score is seen. New run folder `build/synthetic_dwarf_tomato_<date>_06/` with its own
`contract_amendments.json`. `_05` stays reserved for F.3.

Carried forward from B5a: B4a framing (focal x1.4713), B6/B5a brightness (`leaf_srgb_mean` 0.304-0.543),
`texture_bank_v2` albedo. **B5c mesh relief is not carried** (-0.072, supported by I.1).

**Status of the baseline, stated plainly:** I.1 found B5a's gain over B6 (+0.044) is **within scene-level noise**
(95 % CI [-0.038, +0.147]; it clears only the view-level interval, and 12 views of one plant are not independent).
B5a remains the carry-forward configuration because nothing is better, **not because its advantage is established**.
Do not describe B5a as the proven best anywhere in this run's reports.

---

## G.2.0 Why three cells and not one

Addendum G's finding stands: the pool filter `contour_min_solidity = 0.85` kept the roundest 195 of 1163 real
contours, and G.1 selected filter **D** (no solidity floor; `contact_fraction <= 0.239`, `dominant_fraction >= 0.9943`
from the 19 human-visibility masks) giving **621** contours, normalised-perimeter p50 2.06 -> 2.45 against a real 2.63.

But the 2026-10-07 code review found two renderer defects that would make a pool change unmeasurable:

- **A1 — texture and outline come from different leaflets.** `compound_leaf.py:78` draws `contour_index` uniformly;
  `scene.py:132-137` picks the texture by `sha256(leaflet_id)`, independently; `scene.py:141` lays the contour over
  the texture at the *texture's* aspect; `textures.py:78-80` fills everything outside the texture's own leaflet mask
  with `leaf_mean`. **Wherever the drawn contour extends past the texture's silhouette the surface is flat mean
  colour** — no veins, no margin detail, exactly at the lobe tips and margins. Reviewer estimate on moderately lobed
  shapes: median ~6 %, p90 ~19 % of leaflet area.
- **A2 — the texture bank re-implements the refuted solidity floor**, hard-coded at `textures.py:138`
  (`contact <= 0.05 and solidity >= 0.85 and dominant >= 0.98`), in no config and no amendment. The 60 rig-crop
  textures are therefore the roundest masks.

Pool D's whole point is lobed outlines. Under A1 + A2 those lobes would be rendered as flat fill over round textures,
and G's declared falsification test (rendered perimeter must move toward real) would be measuring the fill, not the
pool. **Fixing a defect that makes a measurement impossible is not adding a factor** — but it does change the
renderer, so it gets its own cell rather than being folded in silently.

## G.2.1 The three configurations

| cell | contour pool | renderer | purpose |
|---|---|---|---|
| **G2-0** | current (195) | B5a as-is | the existing B5a baseline, re-rendered on the new scene set for a like-for-like comparison |
| **G2-a** | current (195) | **A1 + A2 fixed** | isolates the renderer fix alone |
| **G2-b** | **D (621)** | A1 + A2 fixed | isolates the pool change **on a renderer that can show it** |

Report all three. `G2-b` minus `G2-a` is the Addendum G test; `G2-a` minus `G2-0` is the cost of the defects.

### The A1 fix
Pair each leaflet's contour with the texture built from the **same mask** (`mask_id` is present on `rig_photo_crop`
entries). Where a contour has no same-mask texture, fall back to warping `t` by the texture's per-column half-width so
the outline always lands inside the textured region. **Report the flat-fill fraction per leaflet** (mean, p90) for
every cell — it is the number that says whether the fix worked.

### The A2 fix
Take the rig-crop selection rule from `generator_config.json`, using **the same filter as the contour pool** for that
cell (so G2-b's bank is built under D). Record the rule in the amendment with a `source_kind`. Rebuilding the bank is
part of this step and changes `texture_bank_sha256`; record the new hash.

### A4 — pin what is being compared
`leaflet_contours.json` is currently read by `cli.py:349` and pinned by nothing: it appears zero times in
`stage1_contract.json` and `contract_amendments.json`, and `cmd_generate` checks only `generator_config_sha256`.
**Record `leaflet_contours_sha256` and `texture_bank_sha256` in the amendment and in every `c6_steps.csv` row, and
have `cmd_generate` refuse when either differs from the declared value.** Without this there is nothing tying a C6
row to the pool it was rendered from.

## G.2.2 Scenes — 15, not 5

I.1 measured the scene-level noise floor at **0.029** (median half-width, n = 5), with per-comparison half-widths from
0.010 to **0.092**, and per-scene AP50 ranging 0.228-0.511 within one configuration. **Five scenes cannot resolve the
effect sizes this project is chasing.**

- Render each cell on **the same 15 scenes**: the 5 pilot scenes (`seed_base 20262005`) plus **10 fresh seeds**
  (declare the new base).
- Report **both**: the 5-pilot subset, for continuity with every earlier row in `c6_steps.csv`, and the full 15, which
  is what the decision uses.
- Report the paired scene bootstrap 95 % interval for every difference, by the I.1 method, and the noise floor at
  n = 15 beside the n = 5 figure.

Cost is about 15 scenes x 3 cells on the GPU; at the measured ~60 s/scene that is roughly 45 minutes.

## G.2.3 What to report

For every cell: **C1-C4** as well as C6/C7, with the real figure beside each; the flat-fill fraction; the rendered
silhouettes' `norm_perimeter`, `aspect` and `solidity` distributions beside real; FP count; and one rendered plant
crop comparable to `build/d0_check_20261006_01/synth_plant_crops.png` so the lobing is visible and not only tabulated.

### Declared falsification for the pool change (G2-b vs G2-a)
The rendered silhouettes' `norm_perimeter` p50 must move toward the real 2.63 (pool p50 goes 2.06 -> 2.45).
**If C6 rises while the rendered perimeter has not moved toward real, the Addendum G explanation is wrong — say so
rather than claiming the step worked.**

### Declared check for curl double-counting (I.2)
I.2 measured, on the 64-point normalised pipeline, that the D pool is already foreshortened relative to flat blades:
**aspect median offset -0.116** (CI [-0.21, -0.035]) against the 61 flattened library contours, while G.2's own shift
(current -> D) is only **-0.058** — the projection bias is about **twice** the change the step itself makes, in the
same direction. The generator then applies `leaflet_roll_deg` 10-60 and `leaflet_bend_deg` 0-45 on top, so curl is
counted twice. The flattened library contours are themselves unpressed, so the true offset is larger than measured.

- **Report the rendered leaflet aspect distribution against real for every cell.**
- **Pre-committed response:** if G2-b's rendered aspect median falls more than 0.05 below G2-a's *and* below real,
  that is curl double-counting; report it as the finding and **do not** retune `leaflet_roll_deg` inside this step —
  a roll/bend change is a separate declared factor with its own cell.

## G.2.4 What this run does NOT do

- No **F.3** (intercalary count/pairing) — it is a separate factor and comes after G.2.
- No change to the **B1 GT rule**, including `min_solidity` 0.434. I.3 found its re-derivation basis has changed (see
  below) but changing a scoring rule mid-stream breaks comparability with every earlier row. G.3 still owns it.
- No change to `leaflet_roll_deg` / `leaflet_bend_deg` (see the pre-committed response above).
- No change to `leaf_chroma_r/g` handling (code review A3: since B5a, leaflet chromaticity comes from the constant
  `RIG_LEAF_BGR` in `textures.py:33`, not from the per-scene measured ranges, which still change `config_hash`).
  Record it as a known gap; it is a separate appearance factor.
- No re-selection of the B5c relief configuration. The code review found `relief_check.py:133` mirrors the metric mask
  and `rolls` still defaults to `(0.0,)`, so the D.2 selection stands on an attenuated measurement — but B5c is
  already rejected on C6, which is the number that matters. Fix `relief_check` before it is ever used as a gate again.

## G.2.5 Two closed questions, recorded so they are not reopened

- **The GT-asymmetry hypothesis is dead.** I.3 recovered all 1281 SAM candidates (1163 accepted, 118 rejected) and the
  rejection reasons are **box/mask errors only**: `box_misses_leaf` 56, `duplicate_box` 49, `false_positive` 13.
  Acceptance is flat in solidity (0.86-0.96) and flat in aspect (0.86-0.94). **Humans never rejected a mask for being
  a thin sliver.** The scarcity of slivers in the real GT is therefore not a human filter.
  *Caveat to carry:* I.3 measures acceptance among *proposals*. If the box detector never proposed edge-on slivers,
  they are absent from the candidate set, and "real plants do not present them" cannot be distinguished from "the
  proposal stage dropped them". Addendum E would settle it.
- **F.11a's aspect floor is statistically supported** (+0.031, CI [+0.017, +0.037]) but remains below the 0.05
  decision line declared in F.11b, so the branch stays closed. Both statements are true; record both.

## G.2.6 Output

`build/synthetic_dwarf_tomato_<date>_06/`, `G2-0` / `G2-a` / `G2-b` rows in `c6_steps.csv` carrying
`leaflet_contours_sha256` and `texture_bank_sha256`, and an Addendum G.2 section in `C6_REPORT.md` with the three-cell
table, both scene subsets, the bootstrap intervals, the flat-fill fractions and the falsification verdicts.
Korean 5-line summary in your reply, ending with the G2-b vs G2-a difference, its interval, and whether the
perimeter falsification passed.
