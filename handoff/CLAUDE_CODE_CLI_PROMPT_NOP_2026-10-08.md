# Claude Code CLI prompt — cells N (specular de-light), O (mature snapshot + determinate cap), P (curl, declared) (2026-10-08)

Paste the block below. Context: decisions taken 2026-10-08 after M.1 (Reading B: the small-GT tail explains ~9 %
of the C6 gap — appearance/shape dominates) and L.1 (the taper is the age distribution; lower ranks are at 92–93 %
of their asymptote; saturation is NOT the mechanism; L.2 as written is retired). Decision record in
`handoff/LOG.md` 2026-10-08. Factor order: ① specular blotches ② aspect/curl ③ A3 chroma. The size cell (O) is a
**realism correction with no C6 claim**.

---

## Paste from here

Standing corrections (post-G.2/M.1/L.1): the C6 baseline is **0.287 on 15 scenes** (B1, G2-0); 0.328 is the easy
5-pilot subset and may only be cited as such. Pool D rejected (195 current); A1/A2 renderer fix kept as correct
behaviour; flat fill is 1–2 % and stays there. M.1's restricted score is report-only forever. The taper's cause is
the age distribution, not unfinished growth (L.1). Detector (609f…) and SAM v5 frozen; B1 rule, gate bounds, and
the contour pool untouched. One factor per cell; scenes are the independent unit; every contract and threshold is
written and logged BEFORE the first render or score of that cell.

Run folder `build/synthetic_dwarf_tomato_20261008_07/` with cells `N-delight` and `O-mature`, same 15 seeds as
G.2 (pilot 20262005+ and fresh 20264000+), 12 views, 512 px, 64 samples, one Kaggle batch. Cell P runs later, in
its own folder, only after N's evaluation is recorded.

### Cell N — remove the rig photos' specular blotches from the texture bank

G2-a's same-mask pairing is correct but carries the rig photos' specular highlights into the albedo (visible in
`G2_plant_crops.png`; FP rose 250 → 291 → 315 across G.2's cells). `delight()` divides out LOW-frequency
illumination, so high-frequency speculars survive it by design. Fix in the bank build, not per render:

1. Declare the specular rule in `N_contract.json` before building: the pixel test (high value + low saturation
   within the leaf mask — exact thresholds declared), and the repair (cv2 inpaint from surrounding leaf pixels —
   radius declared; cv2 is an existing dependency, nothing new).
2. The D.2 bank acceptance still binds: contrast distribution |p50 − 0.187| ≤ 0.047 after repair; a bank that
   fails it is rejected, not re-thresholded.
3. Geometry identical to G2-a (exact seed pairing, same plants — verify as G.2 did: C1–C5 must match G2-a to
   every digit). The ONLY change is the texture bank (new sha256 pinned in the cell contract).

Declared outcomes, before any score: specular-pixel fraction of the bank before/after (report); **FP@0.25 moves
back toward G2-0's 250** (declare the pass band); C6 paired delta N − G2-a with the scene bootstrap. If FP falls
but C6 does not move, say that: the blotches were an artifact, not the limiter.

### Cell O — mature snapshot age + determinate compound cap (the size cell; NO C6 claim)

Pre-commitment, written into the report before rendering: **"O is a realism correction; no C6 gain is
predicted"** (M.1 Reading B). C6 is still measured and reported, paired by seed (pairing is approximate — the
age change re-decodes the plants, as pool D did; say so).

1. `plant_age_days` range raised to the mature stage. Anchor it before choosing numbers: if sowing dates for the
   dwt_1xx or dwt_01–04 material exist in `data/records/` or session manifests, set the range from real
   sowing-to-capture ages (`user_measured`); otherwise declare a `user_stated` mature range and say in the
   contract that the destructive session's records re-anchor it.
2. Determinate cap on compounds per plant, so C3 (real 8–30 leaflets/photo) holds at the older age. Choose the
   cap from real observations if any count of compounds per real plant exists in the records (`user_measured`);
   otherwise declare the chosen value with its provenance explicitly as pending (the J.3
   `literature_other_cultivar` kind is NOT yet approved — do not use it silently) and put the choice in
   `handoff/LOG.md` for the human before rendering.
3. Declared outcomes: rank1 / rank(max−2) blade-length ratio from the L.1 baseline **1.73 → 1.0–1.2**
   (n_juvenile = 2 excluded); synthetic lt150 GT share **19.9 % → toward 10 %** (declare the pass band);
   C1/C2/C3 reported beside the result — an excursion (height will rise with age) is the finding, never
   compensated by a second change in the same cell.

### Cell P — curl/aspect (declared now; runs only after N's evaluation is recorded)

Grounding: every G.2 cell renders aspect p50 0.451–0.485 against real 0.555, and I.2 measured the mechanism —
the pool contours are PROJECTED (already foreshortened: aspect −0.116 vs flattened blades) and the generator
applies `leaflet_roll_deg` 10–60 and bend 0–45 on top, counting curl twice. The G.2.3 roll ban was scoped to
inside G.2; this is the separate declared cell it deferred to.

1. One parameterization, declared before render: reduce `leaflet_roll_deg` to a low range (e.g. 0–15) — the
   exact range and whether bend moves with it go in `P_contract.json` first, with `source_kind` for the choice.
2. Declared falsification: rendered aspect p50 must move from ~0.485 toward 0.555 by **at least half the gap**;
   if it does not, roll was not what holds aspect down and the I.2 de-projection route (flatten the pool
   contours before use) becomes the next candidate instead.
3. Declared readings: aspect moves AND C6 rises → curl was a C6 factor. Aspect moves and C6 does not →
   **curl is exonerated for C6** (then A3 chroma is next), and the aspect fix is kept or dropped on realism
   grounds alone, stated in advance which. Report bucket recalls beside AP50 as always.
4. Note for the record: diaf024's static-vs-dynamic sign flip concerns assimilation, not detection — any future
   FSP use of roll/bend must be re-grounded separately (D.1 relief line); nothing here feeds the FSP.

### Do not

- Do not change the B1 rule, gate bounds, detector, SAM, or the contour pool; `_06` stays read-only.
- Do not let O claim or imply a C6 improvement, whatever its delta shows; do not fold N and O into one verdict —
  different factors, different controls.
- Do not run P before N's evaluation is in `c6_steps.csv`; do not tune N's specular thresholds or P's roll range
  after a score is seen.
- Do not add dependencies.

Record: per-cell contract JSONs (before render), `N`/`O` (and later `P`) rows in `c6_steps.csv` with bank/config
sha256, sections in `C6_REPORT.md`, one `handoff/LOG.md` line per cell. Note in the L prompt's file that L.2 is
retired and cell O supersedes it.
