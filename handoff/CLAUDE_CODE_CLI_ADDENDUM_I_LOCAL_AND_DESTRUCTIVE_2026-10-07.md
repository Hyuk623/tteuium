# Addendum I: work available without GPU, and the destructive measurement of 4 plants (2026-10-07)

Two parts. **Part 2 is the urgent one**: four plants can be destroyed, the specimens are irreversible, and what is
photographed *before* cutting cannot be recovered afterwards.

---

# Part 1 — Local work, no GPU, no rendering

Detector frozen; no training on synthetic; no contract or GT change. All of this runs on CPU.

## I.1 Noise floor, cheap version (do first)

H.1 wants 25 fresh scenes on GPU. A weaker but immediate version needs no rendering: the B5a images already exist.

- Re-score the existing **B5a 60 views** locally with the frozen detector and **cache the detections to disk**
  (they have been recomputed three times now and never kept). ~60 images on CPU.
- **Bootstrap over the 5 scenes** (1000 resamples with replacement) and over the 60 views separately. Report AP50
  median and 2.5-97.5 % interval under both GT rules, and the per-scene AP50 spread.
- Do the same for **B4a** from `eval_B4a_B1rule_pergt.json` and for **B5c** (run `_04`).
- **Deliverable: the smallest C6 difference distinguishable from noise at n = 5 scenes.** Then put every earlier
  delta beside it — B6 +0.067, B5a +0.043, B5c -0.072, F.11a +0.031 — and mark each `supported` / `within noise` /
  `unresolved`. Do not revise any earlier decision; report and stop.

With 5 scenes the interval will be wide; that is the finding, not a failure. It tells us whether H.1's 25-scene
render is needed and how many scenes the 100-scene run really needs.

## I.2 Projection bias — the C.2 correction, measured at last

G.1 found detached blades are more convex than in-situ rig masks, so rig-mask solidity is lowered by **curl and
foreshortening as well as lobing**. Filter D removes the solidity floor and admits those contours; the generator then
applies `leaflet_roll_deg` 10-60 and `leaflet_bend_deg` 0-45 on top of them. **Curl would be counted twice.**

Measure it now, no render: compare, on the same normalised-contour pipeline,

- the 1163 rig-mask contours (projected, in situ),
- the 61 `flattened_real_unpressed` library contours,
- the 9 detached blades from `leaf_47...51` (flat, occlusion-free),

reporting solidity, aspect and normalised perimeter for each population. The systematic offset between projected and
flat **is** the projected-to-flattened correction that has been `uncorrected` since Addendum C. State it as a
distribution, not a single factor, and say whether it is large enough to matter for G.2.

## I.3 Acceptance curve (D.3.3), now known to be possible

`build/leaflet_mask_batch_*/<plant>/items/` holds **292 candidate items for dwt_01 alone**, against 268 accepted —
so **rejected candidates were kept**. Compute the **acceptance rate as a function of visible area, solidity and
aspect** across all four plants. That is the empirical answer to "what would a human have labelled", which F.11
could only approximate with a threshold taken from the accepted set's 1st percentile.

Report only. Do not change the B1 rule (G.3).

## I.4 Ruler scale, by width not by ticks

Tick detection failed (2 of 4 hand-checked). The ruler's **short-edge width** is a known constant: fit the two long
edges as straight lines, take their separation, and divide by the measured width. No tick counting.

This unblocks three stalled items at once: C2 top-view envelope in cm², C4 leaf area in cm², and the leaf library's
`pending` scale. **Ask the user for the ruler's measured width before implementing.**

## I.5 Addendum E shoot sheet

Produce the E.1 pack — 4 failing + 2 control B5a views, the per-view sheet (`camera_elevation_deg`,
`plant_bbox_frac_height`, GT size distribution) and the detection-overlay images. Local, no render. It is what the
user needs in hand before any photography, and E is still the experiment that separates "rendering" from
"GT and scoring".

---

# Part 2 — Destructive measurement of 4 plants

## I.6 Before anything is cut

**Capture all four plants intact, first, in full.** The rig set and the 9-photo generator set (Addendum A: top +
4 side + 4 level), ruler in every frame, nothing touched. If a protocol flaw appears later, the intact state is the
only thing that cannot be re-created. Record plant IDs and sha256 as in Addendum A.

## I.7 What the four plants must buy, in priority order

The value is in **identity-preserving** measurement, not in sample size. Nothing here needs four plants' worth of
leaf-area statistics.

### Plant 1 — sequential defoliation (the highest-value, hardest to repeat)

This is the one measurement that converts several open questions into facts. Remove **one compound leaf at a time**,
re-shooting the standard view set after each removal.

- Work from the top down. After each removal, re-shoot the same views from the same camera position.
- The pixel difference between consecutive images is exactly the region that compound occupied in the intact image —
  **per-organ visible masks with no cross-view matching at all**, which is precisely the step that failed on dwt_01.
- Then flatten and photograph each removed compound with a ruler, and each of its leaflets individually.

What this yields, none of which exists today:

| | why it matters |
|---|---|
| real **visible fraction** per organ (visible / true area) | the real-world equivalent of the synthetic amodal masks; sets the contour filter properly instead of the 19 human labels and the weak `contact_fraction` (Addendum G) |
| real **C5 occlusion** distribution | C5 has been report-only for want of this |
| real GT scored on the **same basis** as synthetic GT | the asymmetry F.11 chased and could not settle |
| true leaf area in cm² | C4 |

Cost: compound-level, not leaflet-level. ~8 compounds x one view set = ~8 extra captures. Per-leaflet defoliation
(~40 removals) is **not** worth it; within-compound structure comes from the detached photographs.

### Plants 2 and 3 — position-labelled compound dismantling

The class data the Claude review §4 specifies. One plant carries 6-9 compounds, so two plants give 12-18 — far above
the five the review asked for.

1. Photograph each compound **spread flat, base and terminal both visible, every attachment point visible**, ruler in
   frame but not crossing a blade. Assign a `compound_id`.
2. Label each station along the rachis from the base: index, side (L/R), class **by position** (main pair /
   interjected / terminal).
3. Detach blade by blade keeping the label; photograph each blade alone on white.
4. One row per blade: `plant_id, compound_id, station_index, side, class_by_position, photo_file`.

This gives fitting **and** leave-compound-out validation, which the current classifier has none of — its three
interjected training blades all came from `leaf_51`.

It also settles, by counting rather than assuming: main leaflets per compound (5-7, F.12), interjected pairs per
compound, terminal presence, and the interjected/main size ratio with a real denominator.

### Plant 4 — hold in reserve

**Do not cut the fourth.** Process plants 1-3 first. Protocols fail in ways that only appear during analysis — a
missed label field, a camera that moved, a flattening step that tore blades. The fourth plant is the retry, and it
costs nothing to keep.

## I.8 Rules for the capture

- **Ruler in every frame**, never crossing a blade outline (the `leaf_49` mistake).
- **Fixed camera** between consecutive defoliation shots — a tripod and manual exposure lock. Hand-held drift is what
  invalidated the D0 brightness target and left the dwt_101 azimuths assumed.
- Photograph **blades flat but unpressed** unless the user decides otherwise; record `pressed=no` either way.
- `NaN` for anything not visible. Never zero, never silently normalised.
- Raw files are human-owned: copy into `data/raw/<plant_id>/`, sha256 recorded, originals untouched.

## I.9 Output

Part 1 to `build/local_queue_20261007_01/`, with `I1`-`I3` rows in `c6_steps.csv` marked `diagnostic` and an
Addendum I section in `C6_REPORT.md`. Part 2 produces raw captures plus a capture CSV per plant; no analysis is
authorized here beyond recording what was captured.

Korean 5-line summary in your reply, ending with the I.1 noise floor and which earlier conclusions it does not support.

---

## I.4 revision — ruler width supplied, with a mandatory cross-check (2026-10-07)

**The user states the ruler's short-edge width is 3 cm.** Record it as `source_kind: user_stated`,
`ruler_short_edge_width_cm = 3.0`, not `user_assumed`.

**Open ambiguity, confirm before adopting:** the ruler in the photographs is transparent plastic with a metal strip
along one long edge. 3 cm may be the plastic alone or the whole ruler including that strip. The two long edges a
line fit will find are the outermost ones, so if 3 cm refers to the plastic only, every derived cm² is wrong by the
square of the ratio. **Ask the user which it is, and do not implement until they answer.**

**Mandatory cross-check — the width scale is not adopted on its own.** A direct check failed here on three library
photos: crude tick detection gave 94 px, 127 px and no result, confirming that tick spacing is unreliable but also
meaning the width value has not been independently verified.

- Implement the width method (fit the two long edges as straight lines, take their perpendicular separation,
  divide by 3.0 cm).
- **On every photograph where cm ticks are confidently readable**, also derive the scale from the ticks, and report
  the two side by side with their percentage disagreement across the whole set.
- **Adopt the width scale only if the two agree within a stated tolerance on the readable subset.** If they
  disagree systematically, the width value or the edge definition is wrong — report it and stop rather than
  propagating a scale error into C2 and C4.
- Report the per-photo scale, not one global value. The photographs were taken at different camera distances
  (confirmed for the `rot_grid` set and the dwt_101 side views), so a single px/cm is not valid across the library.

Only after the cross-check passes may `pending` scales be filled in anywhere.

### I.4 ambiguity resolved (user, 2026-10-07)

**3 cm is the full width including the metal strip** — outer edge of the metal to the outer edge of the plastic.
That is exactly what a fit of the two outermost long edges returns, so **no correction factor is needed**.
Record `ruler_short_edge_width_cm = 3.0`, `includes_metal_edge = true`, `source_kind: user_stated`. **I.4 is
unblocked.**

Two edge-detection cautions that remain, to be handled and reported, not assumed away:

- **The metal strip is specular.** Under a key light it blows out or throws a highlight band, and a naive edge fit can
  latch onto the highlight rather than the true edge. Fit the edge from the *outer* transition to the background,
  not from the brightest line, and report the per-photo residual of the line fit so a bad fit is visible.
- **The ruler has thickness.** Viewed obliquely, its top and bottom faces project to different lines, and the two
  detected edges may come from different faces — which inflates the width and therefore deflates px/cm. Report the
  camera obliquity proxy (the angle of the fitted edges against the ruler's tick direction) and flag photos where the
  two long edges are not parallel within a stated tolerance.

Both faults bias every derived cm² in the same direction, so the I.4 cross-check against tick-derived scale is what
catches them. Keep it.

---

## I.4 second revision — the ruler was re-measured: 31.1 mm (user, 2026-10-08)

The user re-measured the ruler's short edge, outer metal edge to outer plastic edge: **31.1 mm**. The earlier 3.0 cm
was a nominal/rounded figure. Record `ruler_short_edge_width_cm = 3.11`, `includes_metal_edge = true`,
**`source_kind: user_measured`** (a stronger provenance than the earlier `user_stated`), measured 2026-10-08, and keep
the 3.0 cm value in the record as superseded so the first I.4 run remains interpretable.

**The I.4 cross-check already predicted this.** The run reported the tick-implied edge-to-edge width as
**31.17 mm (sd 0.3)** over the 13 library photos where both scales were usable, and the width scale sitting
**+3.89 % above** the tick scale — consistent with dividing by 30.0 mm instead of 31.1 mm (3.11/3.00 = +3.67 %).
The method was right; only the constant was wrong. That is the cross-check doing its job, and it is why the declared
tolerance must not be relaxed in future.

### Re-run I.4 with 3.11 cm

Expected: the median signed disagreement moves from +3.89 % to roughly **+0.2 %**, inside the declared tolerance
(median |d| <= 2 %, |median signed| <= 1 %), and the width scale is adopted.

**Do not treat the re-run as confirmation on its own.** The median now agrees close to tautologically, because
31.1 mm is within 0.07 mm of the tick-implied 31.17 mm. **The part of the cross-check that still carries information
is the spread**, which recentring does not change: p10-p90 was [2.3, 4.61] %, i.e. about **±1.2 % around the median**.
Report that spread as the per-photo scale uncertainty, and carry **±2.4 % onto every area** (it enters squared).
Every cm² value filled from this scale gets that uncertainty attached.

### Only then fill the pending scales
Once the re-run passes, fill the `pending` scales in the leaf library, and derive C2 (top-view envelope) and C4
(leaflet area) in cm², each carrying the ±2.4 % area uncertainty.

**One limitation to state in the report:** all 13 photos with both scales are library photos. Of the 117 plant
photos, **0** have both (the ruler stands vertically beside the pot, so its ticks and its width are not both readable).
The plant-photo scale is therefore used **without any per-photo cross-check**; the library's ±1.2 % is the best
transferable estimate and must be labelled as transferred, not measured on those photos.

Also still true from the first run: report the scale **per photo**, never one global px/cm — camera distance varied
between captures (confirmed for the `rot_grid` set and the dwt_101 side views).
