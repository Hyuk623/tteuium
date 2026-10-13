# Claude review of the F.2 / F.7 results handoff (2026-10-07)

Reviewing `handoff/CLAUDE_CODE_F2_F7_RESULTS_HANDOFF_2026-10-07.md` and the two analysis runs. **This review
authorizes nothing**: no F.3, no rendering, no bank rebuild, no contract or GT change. It corrects the record,
states what the photographs support, and says what evidence is still missing.

The analysis itself is sound and its self-limiting language is correct. My disagreements are about what the numbers
can be used for, not about how they were produced.

## 1. Correction to Addendum F — my error, and what is actually wrong in the generator

**F.0, F.6 and F.7 state that the generator has "no interjected-leaflet class at all". That is false.** Verified in
the code and in both configs:

- `tomato3d/synth/compound_leaf.py` carries `intercalary_count` and `intercalary_rel_size`, tags them `I1…In`,
  and places them in `intercalary_gaps` — **the positions between consecutive main pairs. The alternation F.6
  describes is already modelled.**
- Run `_04` and B5a: `intercalary_count` **0–1** (integer), `intercalary_rel_size` **0.12–0.25** (length relative to
  the terminal leaflet), both `source_kind: user_assumed`.
- `tomato3d/synth/leafarea.py` already classifies a contour as intercalary by area (`intercalary_rel_area = 0.35`).

So the real deviations from the user's stated anatomy are narrower and more specific than F.6 claimed:

| | user-stated anatomy | generator |
|---|---|---|
| interjected count | 2–3 **pairs** (4–6 blades) | **0–1 single blade** |
| arrangement | paired, left and right at the same station | one side only |
| size | length ratio 0.29–0.52 to the **adjacent main** (n=2, Claude) | 0.12–0.25 of the **terminal** |
| outline | simpler, shallower-lobed than a main leaflet | **shared contour pool, no class distinction** |

The size rows use different denominators and are not directly comparable; that comparison needs the terminal length,
which has not been measured. **F.6's "the generator makes about half the leaflets" and F.7's "no interjected class"
are corrected by this section.** The count and pairing gaps are real; the "class does not exist" claim was wrong.

## 2. The classifier: not wrong, but not usable downstream

The four classification tables (library 140/8/88, flattened 44/1/16, SAM 860/11/292, bank 83/2/30) should not be
carried into any decision, for one structural reason the handoff states but does not press:

**All three interjected training blades come from `leaf_51`.** Leave-photo-out removes the entire interjected class,
so there is no held-out test of any kind. What the threshold separates is demonstrably `leaf_51`'s blades from
`leaf_47/50`'s blades. Anything systematic about that one photograph — scale, focus, segmentation behaviour,
specimen age — is inside the class definition. A fit with one specimen group per class and no validation cannot
support a population claim, however stable the number looks.

**The sensitivity analysis is the decisive evidence against using the counts.** Unknown-band factors 0 / 0.5 / 1 / 1.5
give **13 / 7 / 2 / 1** interjected texture candidates. A thirteen-fold swing driven by a policy knob is what a
**continuum** looks like when a threshold is slid along it. Two genuinely separate populations would hold their count
across reasonable bands. On present evidence the metric is a rough candidate selector, which is the handoff's own
item 2 — I am answering it: **it does not distinguish anatomical class, and should not be described as doing so.**

The resolution-stability table (64/128/256 → 89/91/96 main) measures representation stability, which is necessary and
not sufficient; it says the metric is reproducible, not that it is correct. The handoff says this; it is right.

Consequences:

- Do not state or imply "two interjected textures contaminated B5a". The honest statement is that **the bank's class
  composition is unknown**, and that it cannot be determined by shape alone from current data.
- The 88 / 16 / 292 / 30 `unknown` counts are the most informative cells in those tables. They are large because the
  question is genuinely unresolved, not because the classifier is weak.
- Keep the tables as provenance. Do not derive generator parameters, GT rules or contamination claims from them.

## 3. What the photographs do and do not support

**Supported.** `leaf_51` shows three small blades with simple, shallow margins; `leaf_47/50` show larger, deeply lobed
blades. A visible size and margin difference between two sets of detached blades is real. The compound photographs
show a rachis carrying blades of two visibly different sizes, which is *consistent with* alternation.

**User-given, not measured.** The alternation pattern, 5–7 main leaflets (main only, per F.12), and 2–3 interjected
pairs come from the user's own anatomical statement. The project treats that as given. It must not be re-described as
something these photographs measured — and it does not need to be: a user-stated anatomical fact is a legitimate
basis for a generator parameter, recorded as `user_stated`, which is a different and stronger provenance than
`user_assumed`.

**Not supported.** Counts per compound (fragments `leaf_03/04`, occlusion, no specimen IDs); the 0.234–0.601 chord
ratios as a generator prior (2D endpoint chords, class and adjacency unconfirmed, `generator_parameter_eligible=False`
is the correct marking); and the anatomical class of any individual texture or contour.

## 4. The evidence that would settle it

The circularity to break: **class must be established by position on the rachis, not by shape**, because shape is
exactly what is being learned. A protocol that satisfies this:

1. Photograph each intact compound spread flat, base and terminal both visible, every attachment point visible,
   ruler in frame but not crossing any blade. Assign a **compound ID**.
2. Label each attachment station along the rachis from the base: station index, side (L/R), and class **by position**
   (main pair station / interjected station / terminal).
3. Detach blade by blade, keeping the position label, and photograph each blade individually on white.
4. Record one row per blade: `compound_id, station_index, side, class_by_position, photo_file`.

Scale: **at least 5 different compounds**, so leave-compound-out validation is possible and the interjected class is
not one specimen group again. At 11–13 blades per compound that is ~55–65 labelled blades, of which ~20–30
interjected. Ratios need no ruler, so the ruler is only for absolute sizes.

This is the only item on the list that unblocks a class-specific contour model. Everything else in the F.2/F.7
backlog — human review of the 32 priority cards, the held-out reference set — depends on it.

## 5. Priority, and a narrower F.3 that does not need this

**Addendum G comes first.** G concerns the main leaflets, which are the bulk of every scene: 964 of 1163 real
contours (83 %) never reach the pool, the binding filter `contour_min_solidity = 0.85` rejects 8 of the 15 masks a
human labelled fully visible (minimum 0.567), and 221 rejects fail that filter **alone** with both occlusion tests
passing. That is a larger, better-evidenced and cheaper defect than the interjected class, and it is the reason the
rendered plants do not read as tomato.

Separately, **one part of F.3 does not depend on section 4 at all.** Interjected *count and pairing* follow from the
user's stated anatomy, not from the shape work:

- `intercalary_count` 0–1 single → **2–3 pairs**, `source_kind: user_stated`, with the F.12 wording (main-only counts
  stay separate), contours still shared.

That is a one-parameter structural test of the F.6 hypothesis, available without any of the photography in section 4.
It is **not authorized here** — it is a generator change, it belongs after G, and it needs its own declaration and
falsification condition (per F.3: the median visible fraction of the `<150 px` bucket must rise from 0.29, and C1–C4
must be re-checked). I note it so the two halves of F.3 are not treated as one blocked item.

## 6. Status for the F.3 decision

| | |
|---|---|
| **measured** | contour-pool composition and the solidity-filter failure (Addendum G); synthetic small-mask thinness is driven by view angle, not occlusion (F.11); representation-stable shape classification of four artifacts |
| **user-given** | compound alternation; 5–7 main leaflets per compound; 2–3 interjected pairs |
| **provisional** | interjected/main size ratios (n = 2 Claude blades, 8 Codex chords; both `measured_small_n`) |
| **unavailable** | anatomical class of any individual contour or texture; per-compound counts; attachment fractions; terminal length; the bank's class composition |
| **sufficient for F.3?** | **count and pairing: yes, from the user's statement. Class-specific contours: no — section 4 is required.** F.1 remains unconfirmed and nothing here passes C6. |

## 7. Agreed, no action

Accepted as stated and not re-litigated: `leaf_03/04` are senescent fragments and are excluded from whole-compound
totals; `leaf_17` is a stem piece; repeated-subject flags are visual only; zero human reviews have been entered and
the blank template is not a label set; `NaN` means unavailable; nothing shared was modified; the five new photos
remain in a supplement CSV rather than the original capture CSV. Keep both runs intact.
