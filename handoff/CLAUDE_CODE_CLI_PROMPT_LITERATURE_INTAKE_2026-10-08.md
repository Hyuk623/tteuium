# Claude Code CLI prompt — literature intake 2026-10-08 (10 papers, one ordered task list)

Paste the block below. Context for the person pasting: ten papers were read on 2026-10-08. The full extraction
lives in `handoff/PRIOR_ART_DWARF_TOMATO_FSP_2026-10-08.md` (papers 5–10, with quotes and tables) and
`handoff/OPEN_ITEMS_2026-10-08.md` §5 (papers 1–4). A Korean summary for humans is in the claude.ai project doc
`논문정리_2026-10-08.md`. This prompt turns the intake into codebase actions, in order, without touching anything
in flight.

---

## Paste from here

Read `handoff/PRIOR_ART_DWARF_TOMATO_FSP_2026-10-08.md` first, in full. Do not re-derive or re-summarise the
papers; everything below assumes that file.

### Standing corrections (carry into every later prompt; do not relitigate)

1. Blade outline shape parameters are **genotype constants, not light-dependent** (Barbosa 2019: perimeter²/area
   unchanged by irradiance; EFD light effect small). No light-condition handling on any shape parameter; the real
   normalised-perimeter target p50 2.63 is a material constant.
2. **Leaflet aspect (length:width) is worth under ±1 % of assimilation** in the published FSP scenarios, while
   contour shape reaches +5.6 % and curvature −4.9 % (diaf024 Table). Aspect matters for the C6 detector gate
   only. A gate metric must not set modelling priority.
3. **Low-fidelity synthetic plant data actively degrades transfer to real data** (PlantMDE ablation: including
   Crops3D cost −10.27 % and −28.65 % on PlantStereo). This is the external justification for the C1–C7 realism
   gate and for not running Stage 1 at C6 = 0.328 vs the 0.59 gate. Cite it; never argue the gate is excess care.
4. **The independent unit of every accuracy claim is the plant/scene, never the view or the measurement**
   (Usenko: random-split R² 0.80 vs leave-experiment-out 0.52–0.56; our I.1). All evaluation splits are
   leave-plant-out (or leave-scene-out); if a random split is also reported, both numbers are shown.
5. The generator **has** an interjected-leaflet class (`intercalary_count` 0–1, `intercalary_rel_size` 0.12–0.25,
   `intercalary_gaps`); "5–7 per compound" counts **main** leaflets only (F.12).
6. Published rig provenance: Usenko = video SfM; Butturini = structured light on defoliated plants; S2SegNet =
   turntable + Kinect + Metashape; Zhu = 3× Kinect at 120°. **Our no-SfM, ChArUco-board-pose teacher is a
   deliberate difference, not an oversight.** SfM stays forbidden.

### Task 1 — run Addendum J (already written)

Execute `handoff/CLAUDE_CODE_CLI_PROMPT_J_LITERATURE_ARCHITECTURE_2026-10-08.md` exactly as written: J.1
read-only architecture audit in `build/lit_audit_20261008_01/` (realised values from a fresh 5-scene smoke run,
not config defaults), J.2 written proposals only (one factor per future cell, falsification declared), J.3 the
`literature_other_cultivar` source_kind proposal via contract amendments, human approval required. Its do-not
list is binding: no β_leaf 70° adoption, no LW 1/2, no roll/bend change, no touch of the in-flight G.2 folder.

### Task 2 — record the gate's external support (documentation only)

Append a short subsection to `build/synthetic_dwarf_tomato_20261005_03/C6_REPORT.md` titled "External support
for the realism gate (2026-10-08)": the PlantMDE Crops3D numbers (−10.27 % / −28.65 %, source: Zhuo & You,
Comput Electron Agric 239 (2025) 110925, their Table 3 and quoted diagnosis), two sentences max of framing,
and a pointer to `PRIOR_ART_DWARF_TOMATO_FSP_2026-10-08.md`. One `LIT` row in `c6_steps.csv` marked
`diagnostic`. No threshold, rule or config change — the gate values stay exactly as declared.

### Task 3 — write (not implement) the spectral-shape realism diagnostic proposal

From S2SegNet's structural prior: per-point neighbourhood covariance eigenvalues give linearity / planarity /
scattering; stems are linear, blades planar. Proposal file `build/lit_audit_20261008_01/PROPOSAL_spectral_shape_
diagnostic.md` specifying: sample points from generator meshes and from the real S8 visual-hull points; compute
the (linearity, planarity) distribution per population; report the comparison as a **report-only** statistic
alongside C5 (no gate, no bound). Declare before computing: what counts as a mismatch worth acting on, and that
the first run happens **after G.2 settles** in its own run folder. numpy-only (neighbourhood PCA); no new
dependency; the network itself is NOT adopted (single-stem prior, 81 % instance precision, below teacher-GT bar).

### Task 4 — pointers, one line each, no content changes

- `handoff/CLAUDE_SCIENCE_FSP_NUTRIENT_CONTRACT_PROMPT_2026-10-08.md` (if its run is ever prepared): note that a
  published fixed nutrient recipe for pot-grown dwarf tomato exists (Maree et al., Sensors 2025, Appendix A,
  EC 2.8 dS/m) as the citable baseline for step-3 fertiliser treatments.
- `data/tracks/` planning (step 5, when reached): the design to start from is board-pose-normalised 3-D position
  as the prior + growth-invariant appearance embedding for ambiguous cases, tracking **compound leaves** with
  leaflet identity inherited from `station_index`; plant 1's defoliation series is the free matcher-rejection
  test; synthetic growth sequences can supply identity-labelled training data for free (LeafTrackNet).

### Do not

- Do not touch `build/synthetic_dwarf_tomato_20261008_06/` (G.2 in flight), `config/`, `data/records/`, the
  frozen detector (sha256-pinned), the B1 GT rule, or any gate threshold.
- Do not add dependencies: no pretrained MDE backbone (PlantMDE stays a recorded option, decided after G.2),
  no graph-attention network, no Metashape/SfM anywhere.
- Do not implement Task 3's diagnostic in this pass, and do not fold any of this into the G.2 analysis.
- Do not import any numeric parameter from any of the ten papers into a generator config — J.3's provenance
  mechanism and human approval come first, always.

Record when done: `LIT` row(s) in `c6_steps.csv` (diagnostic), the Task 2 subsection, the Task 3 proposal file,
and one line per task in `handoff/LOG.md`.
