# Addendum F: compound leaf structure — interjected leaflets (2026-10-06)

F.1 and F.2 are **local, no rendering, run now in parallel with B5c**. F.3 is a generator change and waits for B5c
to finish. Detector stays frozen (sha256 `609fd7ae…`); no training on synthetic; no threshold changed after results
are seen.

## F.0 Why

**User observation (domain fact, treat as given):** a dwarf tomato compound leaf is **2–3 pairs of main leaflets plus
one terminal leaflet (5–7 main leaflets)**, and in addition carries **several much smaller interjected leaflets along
the rachis** ("소소엽"). Evidence: the leaf library's `compound_structure` photos — `leaf_03, leaf_04, leaf_08,
leaf_12, leaf_19, leaf_24, leaf_25` (`data/raw/leaf_library/leaf_lib_20261006/`). Whole compounds there span roughly
3.5–5 cm by the ruler in frame.

**The generator has neither.** `ranges.leaflet_pairs` is 1–3 (so 3–7 leaflets per compound, counting the terminal) and
there is **no interjected-leaflet class at all**.

**Measured on B5a, 729 instances (5 views × 5 scenes), visible area vs amodal area:**

| visible size | n | visible fraction p10 / p50 / p90 | share below 0.3 | amodal p50 |
|---|---|---|---|---|
| `<150 px` | 250 | 0.03 / **0.29** / 0.98 | **51 %** | 184 px |
| `150–500` | 241 | 0.24 / 0.65 / 0.99 | 16 % | 523 px |
| `500–1500` | 203 | 0.44 / 0.74 / 1.00 | 6 % | 1125 px |
| `>1500` | 35 | 0.76 / 0.93 / 1.00 | 0 % | 2298 px |

**Half of the synthetic instances in the worst-performing bucket are fragments of larger leaflets** (less than 30 % of
the leaflet visible), with a median true size of 184 px. The real GT's small masks, by the observation above, include
**whole interjected leaflets** — complete small leaf shapes, not crescents.

A detector trained on real photographs has learned that a small object is a *complete tiny leaflet*. The synthetic set
offers it a *sliver*. That is a structural mismatch, not a rendering one, and it accounts for two things appearance
work never explained: recall `<150 px` **went down** 0.11 → 0.08 across B6→B5a while `>1500` rose 0.49 → 0.79, and B7
found facing leaflets no easier than oblique ones.

## F.1 — Confirm it cheaply first (local, no render)

Do not change the generator on the strength of F.0 alone. Compare **mask shape** between the two sides:

- **Real:** the 1163 accepted masks, resized to 512 px the way B0 did (`INTER_NEAREST` for masks). Take the
  `<150 px` and `150–500 px` buckets.
- **Synthetic:** B5a `visible_mask.png`, same buckets.
- **Per mask:** solidity (area / convex-hull area), min-area-rect aspect ratio, normalised perimeter
  (`perimeter² / 4πarea`). Report full distributions, not single numbers.
- **Synthetic only, as the internal check:** split the `<150 px` bucket by visible fraction (`<0.3` vs `>0.7`) and
  report solidity for each. If low visible fraction is what drives low solidity, this split will show it; that
  validates the metric before it is used across the two sides.

**Decision, declared now.** If real small masks are clearly more solid and less convoluted than synthetic small masks,
and the synthetic internal split explains it, the fragment-vs-organ reading is confirmed and F.2 proceeds. **If the two
distributions largely overlap, say so and stop** — the interjected-leaflet hypothesis is then not supported by shape,
and F.3 does not proceed on this ground. Report either way.

## F.2 — Measure the parameters; assume nothing (local, no render)

From the 7 `compound_structure` photos, plus any further destructive-measurement photos the user supplies, record per
compound:

- number of main leaflet pairs; whether a terminal leaflet is present;
- **number of interjected leaflets**;
- each interjected leaflet's position along the rachis, as a **fraction of rachis length from the base**;
- its length as a **ratio to the nearest main leaflet**;
- whether its outline shape differs from a main leaflet's (same normalised-contour metrics as F.1) — this decides
  whether F.3 needs a separate shape family or can reuse the existing contour pool.

**Ratios and fractional positions need no scale, so do those first.** Ruler scale is still `pending` (Addendum D.2.5);
absolute mm only if and when it is solved — do not block on it.

**n = 7 compounds is thin.** Mark every range derived here `source_kind: measured_small_n`, never `user_assumed` and
never `measured`, record `n` beside each value, and state in the report what further photographs would firm it up.

Output `build/compound_structure_20261006_01/interjected_leaflets.csv` and one figure showing a labelled rachis per
photo.

## F.3 — Generator change (new run folder; starts only after B5c finishes)

1. `ranges.leaflet_pairs` **1–3 → 2–3** (user-stated).
2. **New organ class: interjected leaflets**, parameterised from F.2 — count per compound, length ratio to the
   adjacent main leaflet, fractional position along the rachis — carrying the same roll / bend / twist treatment,
   albedo texture and relief settings as main leaflets. Reuse the existing contour pool unless F.2 showed the outline
   genuinely differs.
3. New run folder `build/synthetic_dwarf_tomato_<date>_05/` with its own `contract_amendments.json`. Carry over B4a
   framing, B6/B5a brightness and albedo, and whatever B5c settles on.
4. Regenerate visible and amodal masks; report **C1–C4** as well as C6/C7. C3 (leaflets per photo) and C4 (visible
   area distribution) will both move by construction — the question is whether they move **toward** the real values,
   so report the real figure beside each.
5. **Declare the expected direction before rendering:** the median visible fraction of the synthetic `<150 px` bucket
   should rise from 0.29 toward 1.0 as that bucket fills with whole small leaflets instead of fragments. Report that
   number next to C6. If C6 rises while the visible fraction does not, the gain came from somewhere else and the
   explanation in F.0 is wrong — say so.

## F.4 — GT consequence (report only)

If F.1 confirms the split, the synthetic GT contains a class of object — heavily occluded fragments with visible
fraction below 0.3 — that the real, human-accepted GT largely does not. Report what C6 would be with synthetic GT
restricted to visible fraction ≥ 0.3, **as a diagnostic only, never as a C6 pass**. The proper fix is an acceptance
rule measured from the real review (Addendum D.3.3's acceptance curve), not a filter chosen because it raises the
score; say that in the report.

## F.5 — Output

`build/compound_structure_20261006_01/` (F.1 shape comparison, F.2 measurements and figure), `F1` and `F2` rows in
`c6_steps.csv` marked `diagnostic`, and an Addendum F section in `C6_REPORT.md`. **No contract change and no generator
change in F.1/F.2.** Korean 5-line summary in your reply, ending with whether F.1 confirms the split and therefore
whether F.3 is authorised.

---

## F.6 — Confirmed compound structure (user, 2026-10-06). Treat as given.

The user photographed a whole compound leaf held at the base and identified each attachment position. **Leaflet
classes alternate along the rachis:**

```
base ─1─ 2 ─3─ 4 ─5─ 6 ── terminal
     main sub main sub main sub    main
```

- positions **1, 3, 5** carry **main leaflet (소엽) pairs**; the **terminal** leaflet is also a main leaflet
  -> **3 pairs + terminal = 7 main leaflets**;
- the positions **between** them (2, 4, 6) carry **interjected leaflet (소소엽) pairs** -> **2–3 pairs = 4–6**;
- **total 11–13 leaflets per compound.**

Measured from the two user photographs (ruler in frame, 147.5 and 140 px/cm):

| | length | area |
|---|---|---|
| main leaflet, large | 1.95 cm | 1.07 cm² |
| main leaflet, smaller | 1.08 cm | 0.44 cm² |
| interjected leaflet | 0.56 cm | 0.05–0.10 cm² |
| whole compound | ~4.9 cm across | — |

Length ratio interjected / adjacent main **0.29–0.52**; area ratio **0.10–0.24**. Outline differs as well: main
leaflets are deeply lobed and serrated (the largest carries its own basal lobe), interjected ones are much simpler,
shallower-lobed, nearer an ellipse, and relatively wider (aspect 0.66 vs 0.52). F.2 must check this on all 7 compound
photos rather than taking these two as the range — `n` is 2 here.

**The generator produces about half the leaflets per compound.** `ranges.leaflet_pairs` 1–3 gives 3–7 leaflets
counting the terminal; scene_0000 realised 9 compounds / 45 leaflets = **5.0 per compound** against a real 11–13.
A 9-compound plant would carry ~100–117 real leaflets against 45 synthetic.

### Consequences to carry into F.3

1. **Model the alternation explicitly**, not as "a few extra small leaflets": interjected pairs sit at the positions
   *between* consecutive main pairs, so their fractional rachis positions follow from the main pairs' and are not an
   independent random draw.
2. **C3 is affected, not only C6.** Real median is 19 accepted leaflet masks per photo; a generator making half the
   leaflets cannot reach that whatever the appearance. Report C3 beside C6 in F.3 even though C3 is `report_only`.
3. **Occlusion density changes.** Twice the leaflets means substantially more mutual occlusion, so F.3 will add
   *both* whole small leaflets *and* more occluded fragments. This makes F.3's declared falsification test the
   decisive one: **the median visible fraction of the `<150 px` bucket must rise from 0.29.** If C6 rises while that
   figure does not, the gain is not from modelling interjected leaflets and F.0's explanation is wrong — say so
   rather than claiming the step worked.
4. Do **not** reuse the existing contour pool unchanged for interjected leaflets if F.2 confirms the outline differs.
   The pool's 1163 contours come from SAM masks on rig photos and are therefore weighted toward large main leaflets.

---

## F.7 — Two leaflet classes, and the existing data mixes them

The user supplied five ruler photographs (2026-10-06, to be added to the library as F.8 says) showing main and
interjected leaflets separately and side by side. **The two classes are told apart by margin complexity, not by size.**

| | margin | tip | length | area |
|---|---|---|---|---|
| **main leaflet (소엽)** | deeply lobed, clearly serrated; the largest carry their own basal lobe | pointed | 1.0–2.0 cm | 0.4–1.1 cm² |
| **interjected leaflet (소소엽)** | nearly entire, only shallow undulation | blunt / rounded | 0.4–0.8 cm | ~0.1–0.35 cm² |

Measured on the user's photographs (shape metrics are scale-invariant and are the reliable ones; absolute sizes are
approximate, `n` is 3 interjected and 2 main):

| metric | interjected | main |
|---|---|---|
| solidity (area / convex hull) | 0.87 – 0.96 | 0.75 |
| **normalised perimeter** (`perimeter² / 4πarea`) | **1.1 – 2.0** | **4.4** |
| aspect (short / long) | 0.57 – 0.98 | 0.52 – 0.83 |

**Normalised perimeter separates them cleanly and does not depend on scale**, so it works even where the size ranges
overlap — which they do, since a small main leaflet and a large interjected leaflet can be the same size. A
size-only classifier would mislabel exactly those. Use margin complexity as the primary feature and size only as a
secondary one; fit the threshold on the user's labelled photographs and report where it falls and how many components
sit near it.

### The contamination to measure and report

Every existing artefact pools the two classes:

| artefact | n | what it holds now | risk |
|---|---|---|---|
| library components | 236 | classified healthy / damaged / non-leaf only | no main-vs-interjected label |
| flattened contours `library_flattened_real_unpressed_contours.json` | 61 | one pool | mixed |
| SAM contour pool `c0_accepted_mask_contours.json` | 1163 | one pool | likely mostly main; unverified |
| texture bank `texture_bank_v2` | 115 (55 library + 60 rig) | one bank | **already used in B5a** |

Required, in F.2 and reported in `C6_REPORT.md`:

1. **Classify every component** of all four artefacts as `main` / `interjected` / `unknown`, by the margin metric
   above, and report the counts for each artefact. `unknown` is a legitimate outcome near the threshold — do not
   force a label.
2. **Say whether B5a's texture bank mixed them**, and how many of its 115 crops are interjected. An interjected
   leaflet's near-entire margin and smoother surface applied as the albedo of a deeply lobed main leaflet is a real
   error in a step already run. **Report it; do not rebuild the bank inside F** — that is a separate factor with its
   own step and declaration.
3. **The generator must draw from the matching class per position** once F.3 lands: main contours at main positions,
   interjected contours at interjected positions. If the interjected pool turns out too small to draw from, say so
   and propose how to grow it rather than falling back on scaled-down main contours.

## F.8 — New photographs to add to the library (user)

Five ruler photographs from 2026-10-06 are **not yet in the library** and F.2 should use them. Add them to
`data/raw/leaf_library/leaf_lib_20261006/` as `leaf_47 … leaf_51`, byte-identical copies with sha256 recorded, and
append rows to `leaf_library_capture.csv` with the existing columns:

| file | content | uses |
|---|---|---|
| main, main, interjected in a row, ruler | leaflets, mixed classes | `shape_contour;area;class_reference` |
| whole compound held at the base, ruler | compound | `compound_structure;shape_contour;class_reference` |
| interjected cluster on the ruler | leaflets, interjected | `shape_contour;area;class_reference` |
| three main leaflets, ruler | leaflets, main | `shape_contour;area;texture;class_reference` |
| three interjected leaflets, ruler | leaflets, interjected | `shape_contour;area;texture;class_reference` |

Add `leaflet_class` as a new column (`main` / `interjected` / `mixed` / `unknown`), left blank for the existing 46
rows until F.2 fills them. `class_reference` marks the photographs where the user labelled the classes directly —
these are the ground truth the margin threshold is fitted on, and they must never be used both to fit and to report
accuracy without saying so.

## F.9 — Run order

Nothing here changes the contract or the generator except F.3.

| | when | needs |
|---|---|---|
| **F.1** shape confirmation (real vs synthetic small masks) | now, local | nothing |
| **F.2** parameter + class measurement (7 compound photos + the 5 new ones) | now, local | F.8 photos added |
| **F.7** contamination report | with F.2 | — |
| **B5c** render and scoring (Addendum D.2) | already running | — |
| **E** paired real control | after the user's capture | rig capture |
| **F.3** generator change, new run folder `_05` | after B5c finishes **and** F.1 confirms | F.1, F.2 |

If F.1 does not confirm the fragment-vs-organ split, **F.3 does not run on that ground** — report and stop, as F.1 says.

---

## F.10 — Scope limit (user, 2026-10-06)

**This addendum covers the main-leaflet / interjected-leaflet distinction and nothing else.**

Two further differences between real plants and the generator were observed today and are **deliberately out of
scope**. Do not model them, do not add them to the generator, and do not report them as blockers for F:

- **growing apex tissue** — the young, pale, tightly folded leaves at the shoot tip, which have no flat blade and no
  clear outline;
- **trichomes** — the dense hairs that soften a real leaflet's edge, most visible on young tissue.

Both are recorded so they are not lost, and both wait until C6 is settled. If F.1 or F.2 runs into them (for example a
library component that is apex tissue rather than a leaflet), label it `unknown` and exclude it with a count in the
report — do not classify it as main or interjected, and do not start modelling it.

---

## F.8 revision — the five photographs are already in place (2026-10-06)

Copied into `data/raw/leaf_library/leaf_lib_20261006/` and verified byte-identical. **PNG, not HEIC** — they came
through the chat, so the loader must accept both extensions in this session folder.

| file | sha256 | content | `leaflet_class` | `uses` |
|---|---|---|---|---|
| `leaf_47.png` | `5722da0300c6a4d72852f85d50f16bf84652f639f5b64f0e7a280e0265972126` | main, main, interjected in a row; ruler | `mixed` | `shape_contour;area;class_reference` |
| `leaf_48.png` | `fa5569869691954d9e71d37cc11a0b5d511f0957232e51cfc26481d73ddf77a5` | whole compound held at the base; ruler; the user labelled positions 1/3/5 + terminal as main, the rest interjected | `mixed` | `compound_structure;shape_contour;class_reference` |
| `leaf_49.png` | `caf77006ef96c011282bb03de6aceebb48b521ef85271887375f11c0c509c564` | interjected cluster lying on the ruler | `interjected` | `shape_contour;area;class_reference` |
| `leaf_50.png` | `70270fe38008455c76840e6d7b5d69ab4ea48101fba583c468840bc83142ccbd` | three main leaflets; ruler | `main` | `shape_contour;area;texture;class_reference` |
| `leaf_51.png` | `f6816a68bc1a80b6dc653cc9e3a9c435f8642d42c735b0695ebe299a4ac174e7` | three interjected leaflets; ruler | `interjected` | `shape_contour;area;texture;class_reference` |

Append these five rows to `leaf_library_capture.csv` with the existing columns plus the new `leaflet_class` column
(blank for the existing 46 rows until F.2 fills them), `session_id = leaf_lib_20261006`, `pressed = no`,
`ruler_in_frame = yes`, `source_filename` = the chat upload, and `captured_at` = 2026-10-06.

`leaf_49` is partly **on top of the ruler**, so its leaflets sit over printed scale lines — segment it with care and
flag it if the margin metric is affected. `leaf_48` is held by a hand at the base; add `hand_occlusion` to its
`quality_flags` and do not take a contour from the occluded end.

These five are the **class ground truth** the margin threshold is fitted on (F.7). Fitting and reporting accuracy on
the same five photographs is circular — either hold some out, or state plainly that the quoted separation is a fit,
not a validation.

---

## F.11 — F.1b: the thin small masks are edge-on, not occluded (measured 2026-10-06)

F.1 was right to stop: the fragment-vs-organ reading is not supported. But F.1's internal split reported only
solidity and perimeter, and the discriminating metric turned out to be the one it left out — **aspect**. Re-split on
the same B5a data (`build/f1b_aspect_20261006_01/F1b_aspect_split.json`, 668 small instances, view angle joined from
`addendum_b/B7_view_angle.json`):

**By visible fraction — no effect.** aspect p50: `vis<0.3` 0.342 (n 301), `0.3–0.7` 0.333 (n 144), `vis>0.7` **0.263**
(n 223). The *whole* ones are if anything the thinnest. Occlusion does not make them thin.

**By view angle — a clean monotone effect.** aspect p50: `<30°` **0.606** (n 39), `30–60°` 0.455 (n 175),
`≥60°` **0.250** (n 454).

**Cross table — decisive.**

| | n | aspect p50 |
|---|---|---|
| whole & facing | 15 | **0.800** |
| whole & edge-on | 172 | **0.202** |
| fragment & facing | 19 | 0.323 |
| fragment & edge-on | 172 | 0.278 |

**454 of the 668 synthetic `<150 px` instances (68 %) are viewed at ≥ 60°; only 39 (5.8 %) are near-facing.** The
synthetic small bucket is not made of small leaves — it is made of **ordinary leaves seen nearly edge-on**, which are
both small in area and thin.

Real accepted masks, measured the same way (`build/f1b_aspect_20261006_01/real_aspect_tail.json`):

| real masks | n | aspect p1 | p5 | p10 | p50 | share < 0.25 | share < 0.30 |
|---|---|---|---|---|---|---|---|
| `<150 px` | 123 | 0.197 | 0.261 | 0.292 | 0.467 | 4.9 % | 13.0 % |
| `150–500` | 563 | 0.231 | 0.286 | 0.329 | 0.531 | 2.0 % | 6.6 % |
| all | 1163 | 0.237 | 0.298 | 0.338 | 0.554 | **1.5 %** | 5.3 % |

**The real GT has almost no thin slivers; the synthetic GT is full of them.** Note why the B1 rule missed this: an
edge-on leaflet is thin but **convex**, so its solidity is 0.81 — well above the 0.434 floor. Area and solidity cannot
exclude it; only aspect can. That is a gap in the B1 rule as written, not in its implementation.

### F.11a — Re-score B5a with an aspect floor (diagnostic, no render)

Re-run the B5a scoring with the existing B1 GT rule **plus** a minimum aspect, aspect defined exactly as in `run_F1.py`
(`cv2.minAreaRect` short/long on the largest connected component of the visible mask).

- Primary: **`min_aspect = 0.24`** — the 1st percentile of all 1163 real accepted masks (0.237, rounded). It comes from
  the real distribution, in the same way the B1 area and solidity floors did; it is **not** chosen by looking at C6.
- Sensitivity: also report `0.20` and `0.30`. If the three disagree wildly, say so.
- Report per setting: AP50 and recall by size under both the contract GT and the B1 rule, GT count before and after,
  how many GT were removed, and **the view-angle distribution of the removed GT** (expectation: predominantly ≥ 60°;
  if not, the explanation above is wrong and that must be said).

**This is a diagnostic. It is never a C6 pass and the aspect floor is not adopted into the contract on this result.**
C6 remains the unfiltered number against 0.59. Mark the `c6_steps.csv` rows `diagnostic`.

### F.11b — What each outcome means (declared before running)

- **AP50 rises to ≥ 0.45** — the GT asymmetry is a large term. The next step is **not** to adopt the filter but to
  settle it with **Addendum E**: photograph a matched real view and see whether thin edge-on leaflets are present and
  whether the reviewer accepts or rejects them. Only the real review decides what the GT rule should be.
- **AP50 moves < 0.05** — the asymmetry is not the main term. Thin instances are being missed but are too few to
  matter in AP, and the gap is elsewhere. Drop this line of enquiry and say so.
- **In between** — report and ask.

Either way, the open structural question from F.6 (generator makes ~5 leaflets per compound against a real 11–13)
stands on its own and is unaffected by this diagnostic.

---

## F.12 — Correction to F.6: "5–7 per compound" counts MAIN leaflets only (user, 2026-10-06)

F.6 wrote the structure from a single photograph as "3 pairs + terminal = 7 main". The user's general figure is
**2–3 pairs + 1 terminal = 5–7 leaflets per compound, and that number counts 소엽 (main leaflets) only.**

**Interjected leaflets (소소엽) are additional and are never included in a "leaflets per compound" figure.** Wherever
a leaflet count per compound appears — in the generator config, in C3, in F.2's measurements, in any report table —
it must say which class it counts. Write them separately and never as one total:

| | per compound |
|---|---|
| main leaflets (소엽) | **5–7** (2–3 pairs + terminal) |
| interjected leaflets (소소엽) | additional, 2–3 pairs = 4–6 (n = 1 compound; F.2 must widen this) |

Consequences:

- `ranges.leaflet_pairs` 2–3 governs **main** pairs only. F.3's interjected leaflets need their **own** count
  parameter; do not widen `leaflet_pairs` to cover both.
- The generator currently realises ~5.0 leaflets per compound. Against **main-only 5–7 that is roughly correct** —
  the shortfall F.6 claimed is therefore **not** in the main leaflets but in the missing interjected class. F.6's
  "the generator makes about half the leaflets" stands only for the *total* including interjected; restate it that
  way and correct the F.6 table, which conflated the two.
- Every count reported for C3 must state the class basis. Real C3 (median 19 accepted masks per photo) is a count of
  *accepted masks*, which may contain both classes — F.2's classification is what will say in what proportion.
