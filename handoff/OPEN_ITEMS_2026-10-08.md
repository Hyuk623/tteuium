# Open items (2026-10-08)

A snapshot of everything still outstanding on the synthetic-generator track and around it, so nothing is carried only
in conversation. Status as of 12:30 KST. Current best C6: **B5a 0.328** (scene-bootstrap CI [0.263, 0.420]) against
the gate **0.59**.

---

## 1. In flight

| | state |
|---|---|
| **G.2** — contour pool D, three cells, 15 scenes | run folder `build/synthetic_dwarf_tomato_20261008_06/` created 03:25; `generator_config.json` and `views.json` written; no scenes rendered yet. Declared in `handoff/CLAUDE_CODE_CLI_ADDENDUM_G2_DECLARATION_2026-10-08.md` |

G.2 bundles the two renderer defects that would otherwise confound it (A1 texture/contour pairing, A2 texture-bank
solidity floor) as their own cell, and pins `leaflet_contours_sha256` / `texture_bank_sha256` (A4).

## 1.5 Plant supply — ANSWERED 2026-10-09 (user_stated)

**18 plants are available in addition to the 4 destructive-measurement plants** (22 total). This was the open
decision gating the density-acclimation experiment, the closed-canopy C5 extension, and the fertilizer
experiment's feasibility. Allocation CONFIRMED 2026-10-09: **2 spacings x 9 plants in 3x3 blocks** (pots touching vs 2x pitch),
**fertilizer excluded from this cohort** (deferred to a later sowing after the nutrient contract runs).
Protocol: `data/records/density_timeseries_20261009/PROTOCOL.md` + 3 CSV templates. Feeds: diaf024's
density-angle gap, closed-canopy C5 (true interior plants), the steps-4/5 weekly time series, Addendum E's
non-destroyed plant, and O's age re-anchoring (sowing dates recorded).

## 2. Waiting on the user (physical / manual)

| | detail | blocks |
|---|---|---|
| ~~**Ruler re-run**~~ **DONE 2026-10-08 (I.4b)** | re-run at 3.11 cm by recomputing from the I.4 cache; the rule declared 2026-10-07 was not changed and now **passes**: library median disagreement +3.89 % → **+0.22 %**, median abs 0.89 %. Width scale **adopted on the library set**, uncertainty **±1.12 % → ±2.23 % on area** (supersedes ±1.2/±2.4, which were the 3.0 cm values). `build/local_queue_20261008_01/`, `C6_REPORT.md` → Addendum I.4b | **did not unblock C2/C4 in cm²** — see the new row below |
| **Ruler flat in frame, re-shoot** | the real blocker, now visible: with the scale adopted it covers only **25 of 236 library components (11 %)** — 13 of 51 library photos have both edges on paper and in frame, 12 of those carry a component; the 117 dwt_1xx plant photos have the ruler vertical beside the pot and **0 of 117** have both scales readable. Arithmetic cannot fix this | C2 and C4 in cm²; the library's `pending` scales. Already required by the new capture PROTOCOL (ruler flat, ticks and full width both readable) |
| **4 plants, destructive** | capture **all four intact first**; plant 1 sequential compound-by-compound defoliation with a fixed camera; plants 2-3 position-labelled dismantling; **plant 4 held in reserve**. Protocol: Addendum I Part 2 | real visible-fraction ground truth, real C5, class-specific contours (F.2/F.7), the projected→flattened correction |
| **Addendum E capture** — *deferred 2026-10-08* | 6 real photos at matched elevation and in-frame plant size + labelling under the written rule. Pack already built at `build/paired_control_20261006_01/` (E1-E6, shoot sheet, overlays, labelling rule v1). **Removed from the 4-plant session**: shot later, separate session, on a plant that will **not** be destroyed, **after G.2 settles the baseline** — E compares against a synthetic set G.2 may replace, and E must stay re-shootable | separates "rendering" from "GT and scoring"; settles the one caveat left on I.3. Now also blocked on G.2 |
| **Leaflet count sheet** | `build/synthetic_dwarf_tomato_20261005_03/leaflet_count_sheet.csv`, 117 rows, `counted_leaflets` still **0/117**. ~1 h of counting | would restore C3 from `report_only` to a real gate (it would then count true leaflets, not accepted masks) |
| **4-plant capture pack** | ready: `data/records/destructive_capture_20261008/` — `PROTOCOL.md`, `SCHEMA.md`, 7 CSV headers. Waiting on plant selection and the session | all three purposes above |

## 2.5 G.2 — DONE 2026-10-08, verified (run `_06`, 3 cells x 15 scenes, Kaggle T4)

Both live explanations for the C6 gap are dead: the A1/A2 renderer fix removed flat fill (0.298 mean -> 0.013)
with **no C6 change** (-0.012, within noise), and pool D **failed its declared falsification** (rendered normP
p50 at 512: real 2.302, G2-a 2.464, G2-b 2.806 - moved AWAY from real; pool D not adopted). The honest baseline
is now **0.287 on 15 scenes** - the 0.328 chased since B5a was the 5 easy pilot seeds (reproduced to 0.0002 on
Kaggle, so continuity holds; the fresh 10 scenes simply score lower, exactly I.1's warning). B5a carries forward;
renderer fix kept as correct behaviour.

**Strongest live lead (verification finding, 2026-10-08):** GT composition, not appearance. Synthetic GT carries
2x the real share of <150 px instances (19.9 % vs 10.0 %; G2-b 22.9 %), and those synthetic smalls are extreme
slivers (aspect p50 0.311 vs real 0.472; normP 3.31 vs 2.46) - the taper (Addendum L: perpetual-juvenile top
leaflets) plus occlusion fragmentation. Detection collapses exactly there (I.3). Next steps, in order:
1. **declared report-only diagnostic**: re-score the cached detections of both domains with GT restricted to
   >=150 px, same rule both sides, to localise how much of the 0.287-vs-real gap is the small-sliver tail
   (cheap, no render, no gate change);
2. **L.2** (growth saturation), which now has two independent motivations and gains a second declared outcome:
   synthetic lt150 GT share moves from ~20 % toward the real 10 %.
Also recorded: FP rises with the fixes (250 -> 291 -> 315) and same-mask textures carry specular blotches - a new
appearance artifact tied to the open A3 chroma gap; C7 measured on synthetic for the first time: 0.62-0.67 vs the
0.72 gate, failing consistently with the sliver picture; aspect sits below real in every cell (0.451-0.485 vs
0.555), keeping I.2's curl concern alive behind the declared-factor wall.

**Unblocked by G.2:** Addendum E capture (was waiting on the baseline settling), G.3, F.3 (folder `_05`), the
25-scene noise run at the carried configuration (B5a), and the PlantMDE-as-component decision.

## 3. Declared and queued, not started

- **F.3** — intercalary count 0-1 single → 2-3 pairs (`source_kind: user_stated`), after G.2, new run folder `_05`,
  with the declared falsification (the `<150 px` bucket's median visible fraction must rise from 0.29) and C1-C4
  re-checked. **Note:** F.6's "the generator makes about half the leaflets" was corrected by F.12 — main-leaflet
  counts are roughly right; only the interjected class is short.
- **Class-specific interjected contours** — blocked on the position-labelled photography in §2.
- **G.3** — re-derive the B1 GT rule's `min_solidity` 0.434 under the scoring definition (I.3 found p01 0.271 /
  p05 0.439, i.e. the declared 1st-percentile rule behaves as ~p5). **Only after G.2**; changing a scoring rule
  mid-stream breaks comparability with every earlier row.
- **H.1 dedicated noise run** — partly absorbed by G.2's 15 scenes. A 25-scene run at whatever configuration G.2
  settles on is still wanted before the 100-scene Stage-1 run.
- **100-scene Stage-1 run** — only after the gate passes.

- **I.4b module change, handed to Claude Code** (`handoff/CLAUDE_CODE_CLI_PROMPT_I4B_SCALE_2026-10-08.md`).
  `tomato3d/` is Claude Code's column, so the I.4b work stayed in `build/`. Still hardcoding 3.0 cm:
  `ruler.RULER_WIDTH_CM`, the `ruler.py` module docstring, and `_tick_period`'s `expect = width_px / 30.0`;
  `leaflib.build_library` still emits `scale_status: ruler_present_scale_pending` with no scale source wired in.
  The prompt carries a stop condition: if re-measuring the 13 photos does not reproduce `px_per_cm_tick` from the
  I.4 cache, the Addendum I.4b numbers must be **withdrawn, not patched**.

## 4. Code-review findings not yet assigned to a step

From `CLAUDE_CODE_REVIEW_FULL_2026-10-07.md`. A1, A2, A4 are inside G.2; the rest are unassigned.

**Must be fixed before the §2 real captures are processed** — these are Stage-1 defects that the synthetic work has
been bypassing, and Addendum E and the defoliation both run real rig photographs through them:
- **A5** `mask/silhouette.py:218-231,291` — the segmenter has no colour polarity; with no plant in frame it labels the
  wall as plant and the quality gate passes.
- **A7** `calib/pose.py:83-101` — no per-frame reprojection gate; the planar-flip check is vacuous; six collinear
  corners give `solved` with 1e18 px error.
- **A6** `mask/silhouette.py:297-312` — the "rotation-consistency check" is a pixel-area CV: a constant wrong mask
  passes, a real plant may fail.

**Appearance / generator, each a separate declarable factor:**
- **A3** — since B5a, leaflet chromaticity comes from the constant `RIG_LEAF_BGR` (`textures.py:33`), not from the
  per-scene measured `leaf_chroma_r/g`, which still change `config_hash`.
- **B1** `contours.py:101` — the occlusion proxy sees only other *leaflet* masks (stems, rachis, pot never occlude).
- **B2** `leaflet_surface.py:58-61` — base/tip orientation flips on base-truncated masks; `widest_fraction` is
  computed and never read.
- **B3** `relief_check.py:133,74,156` — the metric mask is vertically mirrored and `rolls` still defaults to `(0.0,)`.
  Fix before `relief_check` is ever used as a gate again.
- **B6** `leafarea.py:345-349` — the intercalary rule assumes interjected leaflets are a minority; under the
  user-stated anatomy every blade is labelled a main pair.
- **B7** `compound_leaf.py:189-225` — rejection sampling biases realised interior parameters away from the declared
  ranges, unreported.
- **C2** — `config_hash` includes an absolute Windows path, so it is machine-dependent; `contour_points = 64` keeps
  lobes but removes serration (real normalised perimeter 2.63 → 1.99).
- **Missing tests** — the consolidated list in the review; none written yet.

## 5. Separate workstreams

- **Four-project code review** (`CODE_REVIEW_INDEX_2026-10-07.md`) — launch pack and frozen snapshot prepared under
  `build/code_review_20261007_01/`; **no review executed**. P1-P4 then the integration review.
- **FSP nutrient science contract** (`CLAUDE_SCIENCE_FSP_NUTRIENT_CONTRACT_PROMPT_2026-10-08.md`) — prompt written,
  not run.
- **PPFD meter** — arrival expected ~10/10; feeds the light-model validation.

- **Cultivar: unrecoverable, closed as `unknown`.** The plants are sold under the market name
  "앉은뱅이 토마토" and no cultivar, catalogue entry or seed lot could be found (user, 2026-10-08). The capture
  pack now records genotype by observation instead — `growth_habit`, `terminal_inflorescence`,
  `leaves_between_inflor`, `leaf_color`, `leaf_rugosity`, `bse_fuchsin_result` in `2_plant.csv`, with the
  diagnostic literature named in `SCHEMA.md`. **Rule: `variety_cultivar` is the literal string `unknown`; a
  guessed cultivar is forbidden**, so an inference is never later read as a measurement.

- **Literature, 2026-10-08 — four papers read, one usable finding, one dataset on hold.**
  - *Barbosa et al. 2019, Plant Cell Environ 42:1600* — normalised perimeter (perimeter²/area) is strongly
    **genotype-dependent and not influenced by irradiance**; elliptical-Fourier shape differences between light
    treatments were small, while SLA and the gas-exchange parameters did move. **Consequence for the FSP v1:
    light drives area and dry mass; blade outline shape parameters stay fixed across light conditions**, and the
    contour-pool target (real normalised perimeter p50 2.63) is a material constant, not something to retune per
    light condition — which supports reading the Addendum G pool bias as a sampling error.
  - *Martí et al. 2006, J Exp Bot 57:2037* — Micro-Tom's dwarfism is `sp` (determinate) + `d` (BR biosynthesis,
    co-segregating with dark-green rugose leaves) + a further internode-shortening mutation; GA3 alone barely
    elongates, GA3 + brassinolide >6x. Used only as the diagnostic basis for the phenotype columns above.
  - *Carvalho et al. 2011, Plant Methods 7:18* — Micro-Tom NIL collection. A materials catalogue for a future
    causal light→architecture experiment. No action.
  - *Maree et al. 2025, Sensors 25:4321* — 4th Autonomous Greenhouse Challenge, dwarf cherry tomato
    (Pick-&-Joy Red Cherry, 13 cm pots), 6 compartments, 56→20 plants/m² under algorithm control. Plant density,
    not climate, decided the outcome (best 0.34 EUR/m²/day at 39.7 pots/m², 45 kg/m²/year); high density produced
    stretching, thin stems, lower-leaf yellowing and intertwined plants; canopy height from an overhead RGBD
    camera relative to the pot top; light use efficiency 7.0-10.7 g FW/mol PAR. Their stated hardest problem is
    that a **top view alone cannot see the lower trusses**, and they name "crop models, different camera angles or
    plant sensors" as the remedy — i.e. this project's premise, measured.
    **Two public datasets, use ON HOLD by the user's decision 2026-10-08** (recorded so they are not re-researched):
    challenge data (climate, controls, weather, canopy images) `doi:10.4121/fa102772-32db-4b30-bace-12f2016722ce.v1`;
    **the 1-year-earlier preparatory dataset, which has destructive AND non-destructive crop measurements, canopy
    AND individual-plant images, under several deliberately varied lighting strategies**
    `doi:10.4121/e1ee9de9-6ce9-4502-a37c-34b5b1372bed.v1`. If ever used, scope limited to (i) citing the published
    pot-grown dwarf-tomato nutrient recipe (EC 2.8 dS/m, full composition in its Appendix A) for the step-3
    contract, (ii) an order-of-magnitude check on the carbon module against 7.0-10.7 g FW/mol PAR, and
    (iii) occlusion-geometry verification — **never parameter transfer**: different cultivar, density and climate.

## 6. Closed — do not reopen

Each was tested and refuted or decided; reopening without new evidence wastes a cycle.

| | why it is closed |
|---|---|
| Resolution (B0) | real control holds 0.73 at 512 px |
| Framing (B4a), generator leaflet scale (B4b) | +0.007; B4b dropped |
| Arrangement / occlusion | real and synthetic aspect+solidity agree |
| View angle as the C6 cause (B7) | facing leaflets found no better than oblique |
| Silhouette serration (B8) | synthetic only ~10 % smoother than real photo contours |
| Fragment-vs-organ shape (F.1) | not supported; synthetic small masks are *not* less solid |
| **GT asymmetry (F.11, D.3)** | I.3: rejections are box/mask errors only (`box_misses_leaf` 56, `duplicate_box` 49, `false_positive` 13); acceptance flat in solidity (0.86-0.96) and aspect (0.86-0.94). **Humans never rejected a mask for being a sliver.** *Caveat:* I.3 measures acceptance among proposals, so "real plants do not present slivers" cannot yet be separated from "the box stage never proposed them" — Addendum E settles that |
| Aspect floor (F.11a) | statistically supported (+0.031, CI [+0.017, +0.037]) but below the declared 0.05 line; branch stays closed |
| Mesh relief (B5c) | −0.072, supported by I.1; not carried forward |
| dwt_101-113 ↔ dwt_01-04 ID mapping | **not mappable, and it does not matter.** C1-C4 are distribution statistics, so the two sets are independent samples of the same population; nothing currently needs a per-plant join. Recorded as closed, not pending. New destructive-capture plants get **new IDs**, reusing neither series |
| D0 brightness target | unvalidated, not merely unmet — the camera moved between the four `rot_grid` shots (same-leaflet area change median 0.35). No brightness-based criterion until a fixed-camera re-shoot exists |

## 7. One standing caution

**B5a is the carry-forward configuration because nothing is better, not because its advantage is established.**
I.1 put its gain over B6 at +0.044 with a scene-level 95 % CI of [−0.038, +0.147] — within noise. Every step so far
was measured on five plants, and per-scene AP50 inside one configuration ranges 0.228-0.511. Do not describe B5a as
the proven best in any report.
