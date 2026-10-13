# Claude Code CLI prompt — Addendum L: rank-size profile (upper leaves too small) (2026-10-08)

Paste the block below. Context: looking at the G2-0 scene_0000 mesh in 3-D, the user stated that on the real
plants **lower and upper leaves are similar in size** ("하단잎 크기와 상단 잎 크기를 비슷하게", `user_stated`
2026-10-08). The generator disagrees: measured over all 15 G2-0 scenes (pair + terminal blades, `leaflet_index`),
median length falls monotonically from 28.1 mm at rank 1 to 12.6 mm at rank 7 and 7.7 mm at rank 9 — a
bottom-to-top ratio of ~3.6 with no saturation anywhere.

---

## Paste from here

Standing corrections: G.2 is in flight — nothing in `build/synthetic_dwarf_tomato_20261008_06/` may change, and
Addendum L must NOT be folded into G.2's analysis (G.2's pre-render note already flags a *pool-driven* size
confound; this is a different, rank-structured size defect and the two must stay separable). One factor per cell;
declare before rendering; the frozen detector and all gates stay untouched.

### The diagnosis to verify first (L.1, read-only)

The taper is emergent, not a dial: compounds are born sequentially and grow at `rachis_rate_per_day` toward
`extent_target_mm` with no age at which growth completes, so upper (younger) compounds are always proportionally
smaller — a perpetual-juvenile profile. Verify by reading the realised age-vs-length relation out of the P3 model
outputs for a few scenes and confirming that essentially **no compound has reached its target length** at
snapshot time. If some have, the diagnosis is wrong — stop and report instead of proceeding.

Also report the per-rank profile per scene (p50 and p10–p90 by rank) into `build/rank_profile_20261008_01/`
so the baseline is on record before any change.

### The biological target (why "similar" is right)

- The material is a determinate dwarf photographed at a mature stage; on such a plant all but the newest leaves
  have finished expanding.
- diaf024 (Butturini et al.) gives rank ≥ 2 leaves a SINGLE potential dry mass (547 mg; only rank 1 differs at
  111 mg) and ends leaf growth at te = 464 °Cd — i.e. the published dwarf-tomato model also produces
  near-uniform mature sizes with only the newest ranks still small.
- The user's statement is the only material-specific source until the destructive session: the capture pack
  already records `rank_from_bottom`, `rachis_length_cm` and per-blade photos (`6_compound.csv`, `7_blade.csv`),
  so the REAL per-rank profile will be measured there. Design the change so its target can be re-anchored to that
  measurement when it exists.

### L.2 — the declared change (one factor, one cell, AFTER G.2 settles)

Introduce growth saturation, not a per-rank scale hack: a compound's length follows its existing growth law but
**completes** (reaches target) at a declared age, so at snapshot time all but the youngest `n_juvenile` compounds
sit at target length. Parameterise with at most two new values (e.g. completion age or rate scaling, and
`n_juvenile`), both `source_kind: user_stated` with this date, both listed in the cell's contract before any
render. Declared outcome measures, written before the run:

- per-rank p50 length ratio rank1 / rank(max−2) moves from ~3.6 into **1.0–1.5** (`user_stated` interim target;
  re-anchor to the destructive-session profile when measured);
- C1–C4 must stay in range — note C1/C2 WILL move (bigger upper leaves raise height and envelope), so this cell
  may require compensating nothing else: if C1 or C2 leaves its range, report it as the finding, do not retune a
  second factor in the same cell;
- declared side-channel check: `recall_lt150` — tiny top blades currently feed the smallest-area bucket where
  detection collapses (I.3: acceptance 0.57 below 126 px), so this change may move C6 for a size reason; report
  the bucket recalls beside AP50 exactly as the G.2 pre-render note prescribes, and do not attribute any C6 gain
  to "shape realism".

### Do not

- Do not touch G.2 cells, configs or analysis; do not run L.2 before G.2's result is recorded.
- Do not implement "similar" as a flat per-rank multiplier on lengths — that silently changes total leaf area and
  breaks the growth model's internal consistency; saturation is the mechanism.
- Do not alter leaflet counts, the contour pool, roll/bend, or any appearance factor in the same cell.
- Do not promote the 1.0–1.5 target to `user_measured` — it stays `user_stated` until the destructive session
  measures the real profile.

Record: baseline profile + diagnosis in `build/rank_profile_20261008_01/`, the L.2 cell contract when G.2 is
done, rows in `c6_steps.csv` (`L1` diagnostic now, `L2` when run), one line each in `handoff/LOG.md`.

---

## Appendix L.A — whole-plant visual match by the user (2026-10-08, user_stated)

Using the 3-D viewer's display-only sliders on G2-0 scene_0000, the user tuned the shape until "이 모습이 실제랑
가장 비슷해" (this looks most like the real plants). The settings, read off their screenshots (approximate — they
are slider positions, not measurements):

| display transform | value | what it says about the generator |
|---|---|---|
| lower-blade shrink toward top size | ~80 % | **near-uniform blade sizes across ranks** — confirms and sharpens L's direction; the interim ratio target 1.0–1.5 leans toward the low end |
| rachis stretch (spacing·length) | ~×1.38 | realised rachises are **too short / leaflets too bunched along the rachis** by roughly a third, at the stage the user compares against |
| horizontal push away from the stem | ~+11 mm | **a bare petiole segment exists on the real plants (~1 cm)** before the first leaflets; the generator attaches leaflets too close to the stem. New candidate factor: a petiole base segment (Coussement/diaf024 model both carry petioles) |
| compound clustering along the stem | ~50 % | **compound attachment heights are more bunched** than generated — internode spacing along the stem is too open / the plant too elongated |
| leaflet pairs shown / within-compound leaflet spread | 3 / 100 % | pair count and relative leaflet spacing are acceptable as generated |

Caveats, so this is not over-read: the transforms are compounded display operations on ONE scene, not parameter
measurements; the shrink and stretch interact (blade-to-rachis proportion is not independently pinned); and the
comparison is against the user's memory of the plants, not a photograph side by side. Treat each row as a
`user_stated` qualitative direction with an approximate magnitude.

Consequences for the queue (all post-G.2, each its own declared cell):
1. **L.2 stands, with the target sharpened** toward ratio ≈ 1.0–1.2.
2. **New candidate: petiole base segment** (+~10 mm bare petiole before the first station).
3. **New candidate: rachis length +~30–40 %** at the comparison stage — note this interacts with C2 (envelope)
   and C5 (occlusion), so its falsification must include both.
4. **New candidate: internode compression along the stem** (~half the vertical spread of compound attachments) —
   interacts with C1.
These are candidates, not commitments; the destructive session's `6_compound.csv` (rachis_length_cm, ranks) and
height readings measure 2–4 properly and must replace the slider-derived magnitudes before any cell runs.

---

**Status note (2026-10-08, Claude Code):** L.1 ran and its stop condition fired (`build/rank_profile_20261008_01/L1_REPORT.md`):
the lower ranks already sit at 92-93 % of their exponential asymptote, so saturation is not the mechanism and the taper is
the compound age distribution. **L.2 as written is retired.** Cell O (`build/synthetic_dwarf_tomato_20261008_07/O_contract.json`,
prompt `handoff/CLAUDE_CODE_CLI_PROMPT_NOP_2026-10-08.md`) supersedes it: older snapshot age + determinate compound cap,
no C6 claim (M.1 Reading B). The per-rank baseline (ratio 1.73) and the Appendix L.A target (1.0-1.2) carry over to O.
