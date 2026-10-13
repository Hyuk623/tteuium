# Addendum G: the leaflet contour pool is 17 % of the real masks, selected for roundness (2026-10-07)

G.1 is **local, no rendering**. G.2 is a generator change in a new run folder. Detector stays frozen
(sha256 `609fd7ae…`); no training on synthetic; no threshold changed after C6 is seen.

**Priority: run G before F.3.** F.3 adds a missing organ class (interjected leaflets); G fixes the shape of the
leaflets that are already there, for 83 % of the pool. G is the larger and the better-evidenced defect.

## G.0 The finding

Rendered B5a plants do not read as tomato: the leaflets are smooth, entire-margined ovals with no lobing, attached
to the stem with no visible rachis (`build/d0_check_20261006_01/synth_plant_crops.png`). Real dwarf-tomato leaflets
are deeply lobed and serrated.

`build/synthetic_dwarf_tomato_20261005_03/contour_audit.csv`, 1163 rows:

| `selection` | n |
|---|---|
| `proxy_failed` | **964** |
| `geometric_proxy` | 180 |
| `human_full` | 15 |
| `human_partial` | 4 |

**Only 199 of 1163 real leaflet masks (17 %) reach the generator's contour pool.**

| solidity | p10 | p50 | p90 |
|---|---|---|---|
| the 199 in the pool | **0.855** | **0.891** | 0.931 |
| the 964 rejected | 0.606 | 0.797 | 0.902 |
| all 1163 real | 0.623 | 0.821 | 0.913 |

The binding filter is `constants.contour_min_solidity = 0.85` (`source_kind: user_assumed`, "user decision
2026-10-05"). **The pool is the roundest sixth of the real leaflets**, which is why the rendered plant looks like a
succulent.

**The filter does not measure what it was meant to measure.** Its purpose was "use only leaflets that are not
occluded". Solidity does not test occlusion; it tests convexity, and a fully visible lobed tomato leaflet is concave.

- Of the 964 rejected, **72 % fail solidity**, 73 % fail `contact_fraction > 0.10`, 11 % fail `dominant_fraction < 0.95`.
- **221 (23 %) fail solidity ALONE** — their contact and dominant-component tests both pass, i.e. the occlusion
  evidence says they are clean and they were discarded for being lobed.
- Decisive: of the **15 masks a human labelled `human_visibility = full`**, **8 are below 0.85** and the minimum is
  **0.567**. More than half of the known-unoccluded leaflets fail the filter.

This is the same metric failing in the opposite direction twice. The B1 GT rule used a solidity **floor** to exclude
thin slivers and could not, because an edge-on leaflet is convex (solidity 0.81, F.11). The contour filter uses a
solidity floor to exclude occluded masks and cannot, because a lobed leaflet is concave. **Solidity does not separate
"lobed" from "occluded".**

## G.1 Measure before changing anything (local, no render)

1. **Recompute the pool under candidate filters** from `contour_audit.csv` alone and report, for each, the pool size
   and the pool's solidity and normalised-perimeter distribution **beside the full 1163 distribution**. The target is
   representativeness, not size.
   - current — `solidity >= 0.85 AND contact <= 0.10 AND dominant >= 0.95` (= 199)
   - **A** — drop solidity: `contact <= 0.10 AND dominant >= 0.95`
   - **B** — `solidity >= 0.70` + the same two
   - **C** — `solidity >= 0.567` (the `human_full` minimum) + the same two
2. **Set the occlusion threshold from the occlusion evidence.** Report the `contact_fraction` and
   `dominant_fraction` distributions of the 15 `human_full` and 4 `human_partial` masks. Those 19 are the only direct
   evidence of what unoccluded looks like in this data; the contact threshold should come from them, not from 0.10 as
   assumed.
3. **Measure the true unoccluded shape distribution** from `data/raw/leaf_library/leaf_lib_20261006/leaf_47...51.png`
   (and the 7 `compound_structure` photos). These are detached leaflets on white paper - occlusion is zero by
   construction. Report their solidity and normalised perimeter. **If their solidity sits well below 0.85, the 0.85
   filter is refuted outright and that is the headline of G.1.** Note that `leaf_49` lies on the ruler and `leaf_48`
   is hand-held, per F.8.
4. **State which filter G.2 will use and why**, from 1-3, before rendering anything.

## G.2 The change (new run folder `_06`)

`_05` is reserved for F.3, so G.2 uses `build/synthetic_dwarf_tomato_<date>_06/` with its own
`contract_amendments.json`.

- Replace `contour_min_solidity` with an occlusion test that actually tests occlusion - `contact_fraction` and
  `dominant_fraction`, thresholds from G.1.2. If a shape test is still wanted, it is only to exclude non-leaf debris,
  and its threshold comes from G.1.3's unoccluded leaflets, never from a guessed value.
- **Carry forward: B4a framing (focal x1.4713), B6/B5a brightness and albedo (`leaf_srgb_mean` 0.304-0.543,
  `texture_bank_v2`). Do NOT carry B5c mesh relief** - it cost 0.072 AP50 and was rejected.
- Regenerate contours, meshes, visible and amodal masks. Report **C1-C4** as well as C6/C7, with the real figure
  beside each.
- **Falsification, declared before rendering:** the pool's normalised-perimeter p50 must move from the current pool's
  value toward the full-real value, and the rendered silhouettes' p50 with it. Report all three (pool before, pool
  after, rendered after) beside real. **If C6 rises while the perimeter distribution has not moved toward real, the
  explanation in G.0 is wrong - say so rather than claiming the step worked.**
- Also report, for one scene, a crop of the rendered plant comparable to `synth_plant_crops.png`, so the lobing is
  visible rather than only tabulated.

## G.3 Knock-on, noted not changed here

The B1 GT rule's `min_solidity = 0.434` was derived as the 1st percentile of the same real pool and shares the
metric's weakness. **Do not change it in G** - it is a scoring rule and changing it mid-stream breaks comparability
with every earlier step. Record that it is due for re-derivation once G.2's result is known.

## G.4 Output

`build/contour_pool_20261007_01/` (G.1 tables and the library measurements), `G1`/`G2` rows in `c6_steps.csv`, and an
Addendum G section in `C6_REPORT.md`. Korean 5-line summary in your reply, ending with which filter G.1 selected and
what the pool size became.
