# Claude Code CLI prompt — Addendum M: the small-sliver GT tail, then L.2 (2026-10-08)

Paste the block below. Context: G.2 is done and verified. Both live explanations for the C6 gap died — the A1/A2
renderer fix removed flat fill (0.298 → 0.013) with no C6 change, and pool D failed its declared falsification
(rendered normP moved away from real) and was not adopted. The verification pass found the strongest remaining
real-vs-synthetic difference in the **GT composition**: synthetic GT is 19.9 % (G2-b 22.9 %) instances below
150 px against real 10.0 %, and those synthetic smalls are slivers (aspect p50 0.311 vs 0.472, normP 3.31 vs
2.46) — the Addendum L taper plus occlusion fragmentation, landing exactly where detection collapses (I.3).
Addendum M measures how much of the C6 gap that tail explains, then runs L.2, which attacks it.

---

## Paste from here

Standing corrections (post-G.2): the honest C6 baseline is **0.287 on 15 scenes** (B1 rule, G2-0); the historical
0.328 was the 5 easy pilot seeds and may only be cited as the pilot-subset value. Pool D is rejected; the A1/A2
renderer fix is kept as correct behaviour with no C6 value; B5a geometry carries forward. The detector
(sha256 609f…) and SAM v5 are frozen; the B1 GT rule, every C-gate bound, and `leaflet_roll_deg`/`bend` are
untouched. One factor per cell. Scenes are the independent unit.

### M.1 — declared report-only diagnostic: score both domains with GT restricted to ≥150 px

No rendering and no new photographs: cached G2-0 detections for the synthetic side; for the real side, the
existing detector evaluation on the dwt_01–04 photo set (re-run the frozen detector on CPU over the 62 photos if
its predictions are not cached). Compute AP50 under the B1 rule twice per domain: **all GT** (the existing
numbers: real ≈ 0.73 at 512, G2-0 0.287) and **GT restricted to area ≥150 px at 512**, with the SAME restriction
rule applied to both domains (drop the GT entry; a prediction matching only a dropped GT does not count as FP for
the restricted score — state the exact handling in the contract before scoring).

Declare in `build/size_tail_20261008_01/M_contract.json` BEFORE any restricted score is seen:

- gap_all = AP50_real_all − AP50_synth_all (≈ 0.443 today); gap_ge150 = the restricted difference.
- **Reading A (composition dominates):** gap_ge150 < 0.5 × gap_all → more than half the gap lives in the small
  tail; L.2 is the right next factor and its C6 effect should be visible.
- **Reading B (appearance/shape still dominates):** gap_ge150 ≥ 0.75 × gap_all → the tail explains little; L.2
  remains justified on realism grounds (user_stated profile, diaf024) but must NOT be sold as a C6 fix, and the
  remaining-factor list (A3 chroma, specular blotches, I.2 curl) moves up.
- Between the two bounds: report as partial, no strong claim either way.

Report per plant/scene with the I.1 scene bootstrap beside the pooled number. This restricted score is
**report-only, forever** — it never replaces C6, and no threshold moves because of it.

### M.2 — run Addendum L, now unblocked

Execute `handoff/CLAUDE_CODE_CLI_PROMPT_L_RANK_SIZE_PROFILE_2026-10-08.md` as written (L.1 read-only diagnosis
and baseline first, then the L.2 growth-saturation cell in its own run folder), with two updates that Appendix
L.A and G.2 verification add:

1. The rank-size target sharpens to **ratio ≈ 1.0–1.2** (user_stated whole-plant visual match).
2. A second declared outcome joins the cell contract: **the synthetic lt150 GT share moves from ~20 % toward the
   real 10 %** — state the pass band before rendering.
3. If M.1 returned Reading B, add to the L.2 report in advance: "L.2 is a realism correction; no C6 gain is
   predicted" — and then report whatever C6 does without reinterpretation.

L.2 renders 15 scenes (same seeds as G.2 for pairing), one factor, C1–C4 beside the result, and the rule from the
L prompt stands: a C1/C2 excursion is the finding, not something to compensate in the same cell.

### Do not

- Do not change the B1 rule, any gate bound, the detector, SAM, roll/bend, or the pool (D stays rejected; 195
  stays current).
- Do not treat the ≥150 px restricted score as a new gate or quote it as "C6".
- Do not fold M.1 and L.2 into one report section — the diagnostic is domain comparison, the cell is a factor.
- Do not re-open G.2 or its cells; `_06` is closed and read-only.

Record: `M1` row(s) in `c6_steps.csv` marked `diagnostic`, `L1`/`L2` rows per the L prompt, report sections in
`C6_REPORT.md` (M.1 after the G.2 section; L separate), one `handoff/LOG.md` line per task.
