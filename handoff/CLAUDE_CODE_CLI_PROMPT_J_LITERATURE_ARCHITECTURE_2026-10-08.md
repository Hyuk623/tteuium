# Claude Code CLI prompt — Addendum J: literature architecture audit of the generator (2026-10-08)

Paste the block below into the CLI. Everything above the paste line is context for whoever is pasting.

Source paper: Butturini et al., *in silico Plants* 2026, 8, diaf024 (first dwarf-tomato FSP model; cv.
'Heartbreakers F1 Twiggy Red'). Full extraction and the two companion papers are in
`handoff/PRIOR_ART_DWARF_TOMATO_FSP_2026-10-08.md` — read it first; do not re-derive it.

Why this exists: the paper publishes a complete architectural parameter set for a dwarf tomato. Our generator was
built without one. Some of what they publish is **structure** (rules the species follows) and some is **numbers**
(values fitted to their cultivar). Structure transfers; numbers do not — our plants are an unknown cultivar sold as
"앉은뱅이 토마토", and Barbosa et al. 2019 showed blade shape is genotype-dependent. The task is therefore an
audit and a set of declared proposals, not a parameter import.

---

## Paste from here

Standing corrections, so these are not rediscovered:

- The generator **does** have an interjected-leaflet class (`intercalary_count` 0–1, `intercalary_rel_size`
  0.12–0.25, `intercalary_gaps` between main pairs). Any claim it is absent is wrong.
- "5–7 leaflets per compound" counts **main** leaflets only (F.12).
- Normalised perimeter (perimeter²/area) is genotype-dependent and NOT influenced by irradiance (Barbosa 2019).
  No light-condition handling on any shape parameter.
- Leaflet length:width ratio is worth under ±1 % of assimilation in the published FSP scenarios, while contour
  shape reaches +5.6 % and curvature −4.9 %. Aspect matters for the C6 detector gate (an instrument), not for the
  carbon model (the product). Do not let the gate set modelling priority.
- **G.2 is in flight**: `build/synthetic_dwarf_tomato_20261008_06/` has three generated cells awaiting the Kaggle
  render. Addendum J must not touch that folder, its configs, or any input it pins by hash.

### Task J.1 — audit, read-only, runnable now

Compare the generator's realised architecture against the published set. For each row: our current value and its
`source_kind`, the published value, where ours comes from in code, and a verdict
(`matches` / `differs` / `absent_in_generator` / `absent_in_paper`).

| published parameter | value (Twiggy Red) |
|---|---|
| phyllotactic angle φ | 137° |
| branch angle to vertical | 30° |
| leaf inclination angle β_leaf | 70° (single value, all densities) |
| max phytomers, main stem / branch | 10 / 4 (determinate caps) |
| first two true leaves | same rank; later leaves alternate |
| leaflet number | increases with leaf rank (their Fig. 4) |
| leaflet length:width, rank 1 / rank ≥2 | 1 / 2 |
| interjected leaflets | present in the plant, EXCLUDED from their model, "semi-random locations" |

Measure the realised values from generated scenes (a fresh 5-scene smoke run in a NEW folder,
`build/lit_audit_20261008_01/`), not from reading defaults — a default and a realised distribution can differ.
Output: `J1_architecture_audit.csv` + a short `J1_REPORT.md` section per row. No generator change in J.1.

### Task J.2 — proposals, written not implemented

For every `absent_in_generator` or `differs` row, write a proposal with three fields: the change, the cell it
would occupy (one factor per cell, Addendum-style, with a falsification condition stated in advance), and which
C1–C4 statistic it should move. Expected proposals, to be confirmed or corrected by J.1:

1. **Phyllotaxis 137°** — adopt as structure if the generator has no explicit phyllotactic angle, or places
   compounds by a different rule. Species-level botany, lowest-risk import.
2. **Rank structure** — first two leaves at the same rank; leaflet count increasing with rank instead of a
   rank-independent draw; determinate caps (≈10 main / 4 side) as plausibility bounds for how many compounds a
   scene plant may carry. Check each against C3 (real leaflets per photo 8–30) on the smoke run.
3. **Rank-1 leaves rounder** — adopt the rank-dependence only; take the VALUES from our own position-labelled
   photography when it exists (`data/records/destructive_capture_20261008/`), never LW=1/2 from the paper.
4. **Interjected placement** — the paper's "semi-random locations" phrasing supports F.3's direction
   (0–1 singles → 2–3 pairs, already declared, runs after G.2 in folder `_05`). Fold any placement refinement into
   F.3; do not open a second cell for the same factor.
5. **Coussement et al. 2018 parametric leaflet model** — their shape model, chosen for minimal parameters. Propose
   only as a POST-G.2 comparison cell against the contour pool (parametric vs sampled contours), not as a
   replacement while G.2 is testing pool D.

### Task J.3 — provenance for literature values

`source_kind` currently has no literature category, and silently filing a different-cultivar value as
`user_assumed` would launder it. Propose, via `contract_amendments.json` in the audit folder (and a line in
`handoff/LOG.md` for the human to approve, since the contract vocabulary is a human decision): a new kind
`literature_other_cultivar` carrying `citation` and `cultivar` fields. Until approved, every J.2 proposal lists
its value as PENDING with the citation attached — nothing enters a generator config.

### Do not

- Do not adopt **β_leaf = 70°**: it is the paper's own self-identified weakness (one angle for all densities,
  named as the likely cause of their −19.6 % PBIAS at 80 plants m⁻²), it is another cultivar, and our own B7/F.11
  work shows view/angle statistics interact with the detector. Leaf angle stays as-is pending our own measurement.
- Do not adopt **LW = 1 / 2**: our measured flattened-real aspect p50 0.702 (LW ≈ 1.42) and filter-D 0.585
  (LW ≈ 1.71) contradict LW = 2, and Barbosa says shape is genotype-bound. Structure yes, numbers no.
- Do not change `leaflet_roll_deg` / `leaflet_bend_deg` (G.2.3 pre-commitment), and note the published
  static-vs-dynamic sign flip for upward curl: a static light gain is not evidence a curl setting is right.
- Do not touch `build/synthetic_dwarf_tomato_20261008_06/` (G.2), `config/`, `data/records/`, the frozen detector,
  the B1 GT rule, or any C-gate threshold.
- Do not implement any J.2 proposal in this run. J is an audit and a queue, so that G.2's comparison stays clean.

Record when done: `build/lit_audit_20261008_01/{J1_architecture_audit.csv,J1_REPORT.md,contract_amendments.json}`,
a `J1` row in `build/synthetic_dwarf_tomato_20261005_03/c6_steps.csv` marked `diagnostic`, and one line in
`handoff/LOG.md`.
