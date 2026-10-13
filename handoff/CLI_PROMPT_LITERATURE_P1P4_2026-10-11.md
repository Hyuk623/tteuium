# CLI prompt — apply 4 papers to P1–P4 (2026-10-11)

Paste to Claude Code (or Codex for the parts in its folders). Read first: `CONVENTIONS.md` (ownership:
`tomato3d/`, `tests/` = Claude Code; `tools/`, `phynotype2/` = Codex; `config/`, `data/records/`, `docs/` = human),
`handoff/MTG_CONVENTION_2026-10-10.md` + `handoff/CLAUDE_CODE_CLI_PROMPT_MTG_AMEND_2026-10-10.md`, last 30 lines of
`handoff/LOG.md`. Korean source note with the full verification: claude.ai project doc `논문활용_P1-P4_2026-10-11`.

## Sources (all verified against the PDFs, 2026-10-11)
| key | paper | material | use |
|---|---|---|---|
| Chen2014 | Chen et al., J Exp Bot 65:6399, doi:10.1093/jxb/eru356 | cv. Pannovy, indeterminate, side shoots removed daily, greenhouse 22/18 and 32/28 °C | leaf parameter set, sensitivity design, Qt/Q0 |
| Smolenova2025 | Smoleňová et al., in silico Plants 7:diaf022, doi:10.1093/insilicoplants/diaf022 | Merlice, Brioso, Moneymaker, Gardener's Delight | height extraction, 4-parameter height model, Bayesian updating |
| Kanahama1993 | Kanahama, J Japan Soc Hort Sci 62:377 | wild L. pimpinellifolium, main shoot, mature leaves | phyllotaxis by cumulative-angle regression |
| Reinhardt2005 | Reinhardt et al., Development (tomato meristem ablation) | cv. Moneymaker, primordia | 137° at initiation; post-meristematic distortion; spiral reversal after damage |

**Binding rule:** none of these is Micro-Tom. Import structures, definitions and procedures; never import a
coefficient as a Micro-Tom value. Any literature number that enters a file carries
`source_kind = literature_other_cultivar` (or `literature_wild_species`) and the source key above.

---

## P1 — geometry (MTG attributes; Claude Code writes the convention amendment, Codex the observers)
1. Add to the MTG convention (append as amendment A2; do not rewrite earlier sections):
   - CompoundLeaf `insertion_angle_deg`: angle between the stem axis (above the node) and the petiole, 0–180°
     (Chen2014 "leaf angle"). Source: side view or 3D only; **top view alone → `unavailable`**.
   - CompoundLeaf `rachis_bend_alpha_deg` = [α1, α2, α3]: bend between consecutive rachis segments, segment
     boundaries at the lateral-pair nodes (Chen2014 Fig. 1B). `rachis_curvature_deg` = α1+α2+α3 (derived).
     Keep the existing θ (base vs distal direction) as a separate derived value; state how θ relates to Σα.
     If the compound has ≠ 3 pairs, store one α per segment and record the count.
   - CompoundLeaf `petiole_base_azimuth_deg` (insertion direction around the stem) and
     `blade_azimuth_deg` (direction of the laminae/terminal leaflet) as **two different fields**.
     Note in the text: Reinhardt2005 supports "apparent divergence can change after initiation"; the separation
     itself is a design rule, not a direct result of that paper.
   - Plant `phyllotaxis_mean_divergence_deg`, `phyllotaxis_handedness` (left|right|unknown) with status `derived`.
2. Phyllotaxis estimator (Codex, `tools/phyllotaxis_fit.py`): input = consecutive main-stem compounds with
   `petiole_base_azimuth_deg` and true leaf order; fit cumulative angle y = a + b·leaf_index (Kanahama1993).
   Output b (mean divergence), handedness, residual SD, n. Rules: needs ≥ 5 consecutive leaves with known order,
   otherwise `unavailable`; exclude the first→second true-leaf interval (154.7° in Kanahama1993) **only when the
   true leaf index is known** — MTG rank 1 (lowest leaf at the reference capture) is not necessarily true leaf 1.
   Tests: synthetic spirals with known b and handedness, missing leaves, reversed order.
3. phynotype2 association prior (Codex, spec note only unless the tracker already has a prior hook): next compound
   azimuth = previous + b in the plant's handedness; prior width from the observed range 119.3–154.7°
   (Kanahama1993), not a narrow ±σ around 135°. Use only as a tie-breaker, never to override image evidence.
4. Side-view height (Claude Code, `tomato3d/` if a side pipeline exists, else spec): Smolenova2025 Fig. 5 order —
   white balance from a background patch → plant+pot+support mask → mask cleaning → support removal. Our
   backgrounds differ (paper, ruler, box), so report mask quality per image. Declare the height definition first:
   `height_top_leaf_mm` (soil → highest leaflet, what images give) vs `stem_length_mm` (model). Never mix them.

## P2 — light
1. Sensitivity runs (whoever owns the light run): insertion angle and internode length at 70 / 85 / 100 / 115 / 130 %
   (Chen2014 design); phyllotaxis 135.3 / 137 / 144° on the same scene. Report per-leaflet absorbed-light
   **distribution** (mean, CV, quantiles per plant), not only plant totals — Chen2014: internode −30 % changed
   shoot dry mass −11.5 % with no change in Qt/Q0 or k.
2. Validation ratio (protocol for the human, write to `handoff/`): Chen2014 Qt/Q0 is a ratio, so the phone app can be
   used. Our plants are isolated pots, so canopy k from LAI is not well defined: define
   `below_plant_ratio` = reading at a fixed point under the plant / reading at the same height with the plant
   absent (or above it), same device, same height rule, ≥ 3 repeats. Compare with the model at the same points.

## P3 — growth and direction (candidates only; register, do not adopt)
1. Register as candidate model forms (in the forecast spec, not as calibrated laws):
   - phyllochron (°Cd) + internode logistic (maxlen, klen, tmlen) — Smolenova2025 Table 1. Micro-Tom internodes have
     a genetic upper limit (Martí 2006): maxlen must be fitted to our data, never set from the paper.
   - insertion angle vs leaf length θ = aθ·(1 − exp(−bθ·L)) — Chen2014 eq. 7; needs a side-view time series.
   - next-leaf azimuth = previous + b (P1 item 2), with the Kanahama range as uncertainty.
2. Calibration procedure (Smolenova2025): per-unit P-spline → mixed model → Bayesian optimization, time-ordered
   calibration/validation split. Their calibration was **per cultivar (BLUP)**; state whether we fit per plant
   (18 plants) or per group and why. Report the 30-day lesson (short windows failed to predict later growth)
   as a minimum-data warning. Parameter non-uniqueness is a general caution here: Brioso 48.0 vs 31.9 °Cd came from
   different data sources (image height vs single-rank destructive internodes), not a stated equifinality result.

## P4 — physiology
1. Leaflet-level photosynthesis is required (light-response non-linearity; Chen2014, also diaf024). P4 consumes the
   P2 per-leaflet distribution.
2. Fruit/truss allocation: flag as the weakest link (Smolenova2025 truss dry weight NRMSE 71 %, truss number 29.5 %).
   Micro-Tom sets fruit early and is determinate → separate uncertainty for fruit partitioning; validate first
   against organ dry mass from destructive sampling.
3. All P4 coefficients stay `literature_other_cultivar` until refitted to our organ dry mass / leaf area with the
   same time-ordered updating as P3.

## Out of scope / forbidden
- Using any listed number as a Micro-Tom default (144°, 137°, 135.3°, 154.7°, 30 % effects, 6 %, 11.5 %, NRMSE values).
- Measuring insertion angle from top views; mixing height definitions; editing `config/` or `data/records/`.

## Done when
- MTG amendment A2 appended; LOG line.
- `tools/phyllotaxis_fit.py` + tests pass (software only — no claim about real phyllotaxis until fitted on our plants).
- Light sensitivity spec and the `below_plant_ratio` protocol written to `handoff/`.
- P3/P4 candidate tables added to the forecast spec with source keys and `source_kind`.

---
## Addendum (2026-10-11, same day): Sarlikioti 2011 mcr221 verified
| key | paper | material | use |
|---|---|---|---|
| Sarlikioti2011 | Sarlikioti et al., Ann Bot 108:1065, doi:10.1093/aob/mcr221 | greenhouse high-wire row crop, 4.1 stems/m2, static 27-phytomer plants (no growth) | leaflet-level leaf representation; sensitivity scenario design |
Verified: leaf = rachis + midrib + 13 flat-polygon leaflets; leaflet angle gradient 35 deg (basal) -> 0 deg
(terminal), mean 22 deg; leaf elevation -23..+15 deg explicit distribution; measured row-crop phyllotaxis
~160 deg because mature leaves REARRANGE (nominal 137.5); phyllotaxis scenarios 110-180 deg had NO effect on
canopy light/photosynthesis; internode 7.45+-0.8 cm, 7->12 cm or leaf L:W x1.5 -> +6-10 % (summer only).
Apply: (P1) adopt the basal->terminal leaflet-angle gradient as a prior SHAPE (values from our Micro-Tom
measurements; 13 leaflets is a large-cultivar value, ours is 5-7); the rearrangement finding is the direct
justification for petiole_base_azimuth vs blade_azimuth as two fields (stronger than Reinhardt2005).
(P2) expected outcome of the phyllotaxis sensitivity run is "no effect" in row canopies - still run it, our
isolated-pot layout differs. Static model: no role in P3 growth. All numbers carry
source_kind = literature_other_cultivar.
