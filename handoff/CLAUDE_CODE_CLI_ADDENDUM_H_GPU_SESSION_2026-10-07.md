# Addendum H: what a long Kaggle GPU session should buy (2026-10-07)

Written after G.1. **Rendering is not the constraint** — 5 scenes x 12 views costs about 5 minutes of T4 time, and
seven single-factor steps over two days have consumed almost no GPU. The constraint is that we do not know the
**noise floor of C6**, and we have been reading deltas of 0.03-0.07 as if they were signal. H.1 fixes that first.
Do not fill GPU time for its own sake.

Detector frozen (sha256 `609fd7ae...`); no training on synthetic; no threshold changed after results are seen.
All of H is declared in `contract_amendments.json` **before** any rendering.

## H.0 Where G.1 leaves us

| pool | n | norm_perimeter p50 |
|---|---|---|
| all 1163 real | 1163 | **2.63** |
| current, as implemented | 195 | **2.06** |
| **D** (selected): no solidity floor, `contact <= 0.239`, `dominant >= 0.9943` | **621** | **2.45** |

D keeps 13 of the 15 `human_full` masks and moves the pool most of the way to real. Two G.1 findings must be
carried, not forgotten:

1. **The 0.85 floor was not refuted by the detached blades.** Main detached blades sit at 0.82-0.89, straddling it.
   The refutation rests on the `human_full` set (8 of 15 below 0.85, minimum 0.567). Addendum G.0 overstated this;
   the correct statement is that the floor is **unjustified**, not that it is disproved by leaf_47-51.
2. **`contact_fraction` is a weak occlusion test.** `human_full` contact spans 0.003-0.455 (7 of 15 above 0.10) and
   overlaps `human_partial` (0.052-0.397). D is the best available rule, not a good one. Say so in the report.

**New risk introduced by D, to be checked in H.2:** G.1 found detached blades are more convex than in-situ rig
masks, so a rig mask's low solidity comes from **curl and foreshortening as well as lobing**. Dropping the solidity
floor therefore admits contours that already encode curl, and the generator then applies `leaflet_roll_deg` 10-60 and
`leaflet_bend_deg` 0-45 **on top of them** — curl counted twice. This is the `uncorrected` projected-to-flattened
correction (Addendum C.2) surfacing as a concrete defect. H.2 must report the rendered leaflets' aspect and solidity
against real; if they drift away from real while the perimeter improves, double-counted curl is the cause.

## H.1 — Noise floor of C6 (first; ~30 min GPU)

Nothing in the B/F/G record has a confidence interval. B5c lost 0.072 and was rejected; F.11a gained 0.031 and was
rejected by a 0.05 rule; B5a gained 0.043 and was kept. **Those decisions assume a noise floor nobody has measured.**

- Render **25 scenes at fresh seeds** (not the pilot's `seed_base 20262005`; declare the new base) with the
  **unchanged B5a configuration** — same contour pool, same albedo, same brightness, B4a framing. Nothing is varied.
- Score C6 and C7 under both GT rules.
- Report, by **bootstrap over scenes** (1000 resamples of the 25 scenes with replacement): AP50 median and the
  2.5-97.5 % interval, and the same for the per-size-bin recalls. Also report the plain per-scene AP50 spread.
- **Deliverable: the smallest C6 difference that is distinguishable from noise at 5 scenes and at 25 scenes.**

Then restate every earlier step's delta beside that figure, in one table in `C6_REPORT.md`. Mark each earlier
conclusion `supported` / `within noise` / `unresolved`. Do not silently revise the earlier decisions; report which
ones the noise floor does not support and stop for the user.

## H.2 — Declared factorial sweep (~1 h GPU)

One factor at a time was the right discipline while each factor was a guess. We now have three changes with
independent evidence, and the interactions matter — G's bigger, lobed contours change what the interjected count
does. Run them as a **declared grid**, not sequentially.

Factors, 2 levels each, on the **5 pilot scenes** (seed_base 20262005, so results are comparable with B5a):

| factor | level 0 | level 1 |
|---|---|---|
| contour pool | current (195) | **D (621)** — G.2 |
| intercalary | `count` 0-1, single-sided | **2-3 pairs**, `source_kind: user_stated` (F.12, Claude review §5) |
| leaflet contour class | shared pool | shared pool *(held fixed — class-specific contours need the data in the Claude review §4)* |

That is **2 x 2 = 4 cells**, B5a being cell (0,0) and already measured. Three new renders, ~15 min. Spend the
remaining budget on H.1 and H.3, not on inventing a third factor without evidence.

**Anti-cherry-picking rules, declared now:**

- Report **all four cells**, with C1-C4 as well as C6/C7, whatever the outcome.
- The best cell is a **hypothesis, not a result**. It is confirmed only by H.3.
- No factor level may be added, dropped or retuned after seeing a cell's score.
- Each cell's delta is read against **H.1's noise floor**. A cell inside the noise band is reported as "no
  detectable effect", never as a small gain.

## H.3 — Confirmation on held-out scenes (~15 min GPU)

Take the best cell from H.2 and render **10 scenes at the H.1 fresh seeds** (held out from the sweep). Report C6/C7
with H.1's bootstrap interval.

- If the held-out estimate falls inside the sweep estimate's interval, the effect is confirmed and that configuration
  becomes the new baseline, replacing B5a.
- If it does not, report the shrinkage and treat the sweep result as overfitted to the 5 pilot scenes.

**Declared falsification for the D pool (from Addendum G):** the rendered silhouettes' `norm_perimeter` p50 must move
from the current value toward the real 2.63. Report pool-before 2.06, pool-after 2.45, rendered-after, and real,
together. **If C6 rises while the rendered perimeter has not moved toward real, the G.0 explanation is wrong — say
so.** Add the rendered aspect and solidity against real, per the curl risk in H.0.

Include one rendered plant crop comparable to `build/d0_check_20261006_01/synth_plant_crops.png`, so the lobing is
visible and not only tabulated.

## H.4 — Not in this session

- The 100-scene Stage-1 run. It comes after the gate passes, not before.
- Class-specific interjected contours (needs the position-labelled photography in the Claude review §4).
- Any change to the B1 GT rule, including `min_solidity` 0.434 — re-derivation waits until H.3 settles (G.3).
- Addendum E, which needs real photographs, not GPU.
- Higher-resolution rendering. B0 established that resolution is not the cause.

## H.5 — Budget and output

Roughly 30 min (H.1) + 15 min (H.2) + 15 min (H.3) of T4 time, plus upload and scoring. Well inside one session;
the rest of the quota is not needed and should not be spent.

Outputs: `build/synthetic_dwarf_tomato_<date>_06/` for the sweep and confirmation renders, `H1`/`H2`/`H3` rows in
`c6_steps.csv`, and an Addendum H section in `C6_REPORT.md` carrying the noise floor, the four-cell table, the
held-out confirmation and the earlier-steps reassessment. Korean 5-line summary in your reply, ending with the noise
floor and which earlier conclusions it does not support.
