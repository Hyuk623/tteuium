# Claude Code — fork the diaf022 GroIMP model for Micro-Tom (2026-10-11)

Goal: adapt the reference implementation `C:\Users\sho36\Downloads\vtc-main\vtc-main\tomatoFSPM_basic_isP`
(diaf022 / Smoleňová 2025, GroIMP 2.2.1) to our Micro-Tom setup in four steps: (1) determinate growth,
(1-2) compound-leaf structure, (2) start at sowing + 30 days, (3) DLI-based lamp light with a swappable
measured-distribution file. Work on a COPY at `build/vtc_microtom_20261011/`; never edit the original
download. GroIMP runs are manual (the human opens project.gs); your job is the code edits + the CSV flows +
a run guide `build/vtc_microtom_20261011/RUN_GUIDE_ko.md`. LOG one line per task.

Read first: `CONVENTIONS.md`, `handoff/MTG_CONVENTION_2026-10-10.md` (+A1/A2 amendments),
`handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md`, `data/records/env_light_20261010/`,
`data/records/plant_registry/`, claude.ai project docs `논문확인_MicroTom_2026-10-10`, `논문상세_Butturini_diaf024`.

## Verified code map (checked 2026-10-11 against the source)
- `rewrites.rgg` ~L62: generative rule is **indeterminate** — "truss every 4th phytomer" forever, no apex stop.
- `modules_organs.rgg` Apex ~L778: `numberVegPhyt = FINAL_VEG_PHYT_NUM`, `phylloAngle = PHYLLOTAXIS[cultivar]`.
- `modules_organs.rgg` `calcNrLeaflets()` ~L373: rank 1 → 1 pair, rank 2 → 2 pairs, rank ≥ 3 → `NR_LEAFLET_PAIRS`.
- `modules_organs.rgg` `calcAngle()` ~L355: insertion angle = Chen eq.(7); curvature = `LEAF_CURVE/segments`,
  uniform per segment, comment "hardcoded for 3 leaflet pairs + terminal leaflet".
- `modules_light.rgg`: sun (`DirectLight`, latitude 52°) + 72-light diffuse sky; no lamps.
- `parametersMerlice.rgg`: all coefficients (phyllochron 37.9 °Cd, FINAL_VEG_PHYT_NUM 8, MAX_LEN_INT 0.072 …).
- `main.rgg`: `run2update()` seed→transplant spin-up; `run2filePlantEval`/`run2fileLeafLight` CSV outputs.

**Binding:** every number you place in `parametersMicroTom.rgg` is `user_assumed` or
`literature_other_cultivar` until fitted to our records; write the source as an inline comment on each line,
and emit a `run_assumptions` block (sowing date, DLI source, parameter provenance) into both output CSVs.

## Task 1 — determinate (sp) growth switches
Sources in hand: Carvalho 2011 (Micro-Tom: first truss most often above leaf 9; **two successive trusses end
main-stem growth**; mutants flower at 10–13 leaves), Martí 2006 (d + mnt → genetic internode cap), diaf024
(a capped dwarf architecture: main-stem node cap, trusses ranks 6–10 — other cultivar, structure only).
We hold no dedicated determinate-vs-indeterminate comparison paper; the working comparison is
diaf022 (indeterminate Merlice, this code) vs diaf024 (capped dwarf). State that in the fork README.
Changes:
1. New cultivar `MICROTOM` (`parametersMicroTom.rgg`, cloned from Merlice, every line annotated).
2. Apex termination: add a `stopped` state; generative rule produces trusses until the sp stop condition
   (default: terminate after the 2nd successive truss — Carvalho; make the condition a parameter
   `SP_STOP_RULE` so it can be refitted). After stop: no new phytomers, existing organs keep growing.
3. `FINAL_VEG_PHYT_NUM[MICROTOM]`: prior 8 (first truss above leaf 9) — fit later from our 화방 sheet.
4. Truss cadence: "every 4th phytomer" is Merlice-specific; parameterize (`TRUSS_INTERVAL`), Micro-Tom
   prior unknown → fit from records.
5. `MAX_LEN_INT`: keep the logistic but cap must come from our calipers (genetic limit, Martí); do not reuse 0.072 m.
6. Side shoots: none exist in the code and none are added (`topology_scope = provided_axes`); note diaf024's
   ranks 1·2·7 / 30° as other-cultivar facts only.
7. `PHYLLOCHRON[MICROTOM]`: placeholder 37.9 flagged `literature_other_cultivar`; our thermal time is
   18.63 °Cd/day (T_base 5.7 assumption) — refit from the 관측기록 sheet once ≥ 3 capture dates exist.

## Task 1-2 — compound leaf / leaf structure
Sources: diaf024 (leaflet count rises with rank; 1st-order leaflets only; planar), Carvalho 2011 (typically
5 leaflets; leaves 1–2 have 3), our dissection 2026-10-10 (3 pairs + terminal + 1 intercalary pair +
secondary leaflets; middle pair largest; total 50.71 mm), Chen 2014 (α1:α2:α3; base-bend −6 %),
our bend types (flat / bent, `data/records/compound_bend_types_20261010/`).
Changes:
1. `calcNrLeaflets()` → rank-indexed table `NR_LEAFLET_PAIRS_BY_RANK[]` (prior: rank 1–2 → 1 pair,
   else 2 pairs = Carvalho's 5 leaflets; our dissected leaf had 3 pairs → the table is refitted from the
   C3/소엽 sheet, keep both candidates in comments).
2. Per-segment bending: replace the uniform `LEAF_CURVE/segments` with ratio parameters
   `CURVE_RATIO = [r1, r2, r3]` (reference 1:2:2, Chen) so bent-type leaves (base bend) are expressible;
   add `BENT_FRACTION` (share of bent-type compounds, from our side photos, currently unmeasured → 0 + flag).
3. Leaflet sizes: middle pair largest (our dissection) vs the code's uniform `lenLeaflet` — add a per-pair
   size ramp parameter (default off until fitted).
4. Intercalary + secondary leaflets: not representable; do NOT fake them — add an area-accounting note and
   an optional `AREA_CORRECTION` factor (default 1.0, flagged) instead of geometry.
5. Leaf insertion angle: keep eq.(7); `LEAF_ANGLE`/`K_LEAF_ANGLE` to be fitted from our side photos.
6. Do not adopt diaf024's "first two leaves share a rank"; our MTG ranks every leaf individually.

## Task 2 — start at sowing + 30 days
1. Keep the seed spin-up (simplest correct route): simulate from sowing with OUR climate
   (26/22 °C, 14/10 h → daily CSV generated by a small script `make_climate_csv.py` in the fork folder)
   for 30 days, then reset `time = 0` for outputs: add `DAYS_AT_START = 30` and report
   `days_after_sowing = DAYS_AT_START + time` in every CSV row.
2. `DELAY` (germination, 206.3 °Cd Merlice) stays a flagged other-cultivar value.
3. Write the declared assumption into the README and `run_assumptions`: "start = sowing + 30 d
   (user decision 2026-10-11); real sowing dates per plant are unrecorded — ask the human; the long-term
   plan remains initialization from the observed MTG (stage-2), this spin-up is interim."
4. Open item for the human: actual sowing date(s) — add a 파종일 column request for the 개체목록 sheet.

## Task 3 — DLI lamps + swappable measured distribution
1. Replace sun+sky with an indoor scene flag `LIGHT_SCENE = LAMPS`: keep the old code behind
   `LIGHT_SCENE = GREENHOUSE` (unchanged), add a lamp array above the tray plane.
2. Input flow (all file-driven, no code edits on remeasure):
   - `light_input.csv`: `reference_ppfd_umol_m2_s, source_kind, measured_at` → DLI = PPFD × 0.0504 (14 h).
     Until the meter arrives `source_kind = user_assumed` and absolute outputs are flagged conditional.
   - slot ratios: read `data/records/env_light_20261010/plant_slot_light_ratio_20261010.csv` via a
     **pointer file** `light_ratio_latest.txt` (one line, relative path). A new measurement = drop the new
     CSV in data/records and update the pointer. The loader validates the header, else aborts loudly.
   - per-plant target = reference × `ratio_now` of its slot (the 1.047 base-correction note applies if the
     reference is defined over the 3 trays only — read it from the env_light JSON).
3. Validation flow `run2fileLightCheck()`: virtual sensors at the 16 grid-cell centres (measurement height
   parameter, currently unrecorded → parameter + flag), output simulated values normalised by their 16-cell
   mean next to the measured `ratio_to_mean` → `output/light_validation.csv` with ratio RMSE and Pearson r.
   Ratios only; never print app values as µmol.
4. Lamp placement starts as a declared guess (uniform grid above trays) — the validation flow in 3 is
   exactly what will correct it when new measurements arrive.

## Out of scope / forbidden
- Editing the original `Downloads\vtc-main`; editing `config/`, `data/records/`, `tools/`, `phynotype2/`.
- Importing any Merlice/diaf024/Chen number as a Micro-Tom value without its flag.
- Carbon/photosynthesis coefficient refits (later, with organ dry-mass data) — structure only this round.

## Done when
- Fork builds in GroIMP 2.2.1 (human runs it; you provide RUN_GUIDE_ko.md with exact buttons).
- `parametersMicroTom.rgg` fully annotated; apex stop + rank leaflet table + segment-ratio bending in place.
- Climate CSV generator + light_input/pointer flow + `light_validation.csv` produced in a dry run with
  `user_assumed` reference values.
- README states the three declared assumptions (sowing+30 d, reference DLI, lamp placement) and the
  det-vs-indet source situation. LOG lines written.

---
## Addendum A (2026-10-11): Task 1-2 is the replacement for the Sarlikioti leaf representation
Decision (user): the literature leaf representation "13 leaflets per compound leaf, each a flat polygon"
(Sarlikioti 2011, large greenhouse cultivar) is NOT adopted as-is. The Micro-Tom leaf in this fork is:
1. Leaflet count: `NR_LEAFLET_PAIRS_BY_RANK[]` (Task 1-2.1) — prior Carvalho 2011 (ranks 1-2: 1 pair,
   else 2 pairs = 5 leaflets), to be fixed from the C3 / 소엽 sheet (our dissected leaf had 3 pairs + terminal
   + 1 intercalary pair). Never a fixed 13.
2. Rachis is NOT straight: per-segment bending `CURVE_RATIO = [r1, r2, r3]` (Task 1-2.2, Chen alpha ratios),
   expressing base-bent (구부러진) compounds; `BENT_FRACTION` splits flat vs bent types.
3. Leaflet sizes: middle pair largest (Task 1-2.3 ramp), not uniform.
4. Intercalary + secondary leaflets: `AREA_CORRECTION` flag only, no fake geometry (Task 1-2.4).
5. Each leaflet BLADE stays a flat polygon for v1 — same planar assumption as Sarlikioti — with the known
   limit recorded: Micro-Tom blades are rugose/curled (Marti 2006; our D.1 limit); blade curl is a separate
   pending criterion and must not be conflated with rachis bending.
6. Keep Sarlikioti's basal->terminal leaflet-angle gradient (35->0 deg) as the SHAPE of the leaflet-angle
   prior; values `literature_other_cultivar` until measured.
