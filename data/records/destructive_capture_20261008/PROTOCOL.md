# Capture protocol — 4 plants: intact capture, then destructive measurement (2026-10-08)

A field document. Records go in `templates/` (seven CSVs); field definitions are in `SCHEMA.md`.
**One capture session serves three purposes at once:** the irreplaceable before-state for the destructive work,
and the C1/C2 real reference. (Addendum E was removed from this session on 2026-10-08 — see section 4.)

**The capture session and the cutting session are different days.** Verify the photographs first.

---

## 1. Choosing the plants

### The trap to avoid
**Three similar plants do not give three plants' worth of information.** I.1 measured per-scene AP50 ranging
**0.228-0.511** inside a single configuration — plant-to-plant variation dominates this system. Three plants from the
same sowing, the same shelf position and the same size are effectively one specimen group, and leave-compound-out
validation stays confounded. **Plants 2 and 3 must differ** in at least one of size, age or light position.

### By role

| | choose for |
|---|---|
| **Plant 1** — sequential defoliation | **visible mutual occlusion** (a sparse plant gives visible fraction ≈ 1 everywhere and teaches nothing — the whole measurement is visible ÷ true area); compounds still separable one at a time; structurally intact, no missing or broken compounds; stage close to what the generator makes (6-9 compounds, ~45 leaflets, ~10 cm, ~27 days) |
| **Plants 2-3** — position-labelled dismantling | many intact, healthy compounds; a **range from bottom to top** (old large to young small); **different from each other** |
| **Plant 4** — reserve | **as similar as possible to plant 1** — its protocol is the hardest and the most likely to need a redo. Do not cut it |

### Rules for all four
- **No flowering plants.** The generator has no truss parameters at all, and leaf arrangement changes at flowering.
- **Do not keep the best and cut the worst** (or the reverse). These measurements become the real reference
  distribution and every gate is calibrated against it; a biased pick shifts the reference itself. Choose close to
  at random within the constraints above.
- **Match the growth stage to the synthetic.** A much larger or older plant makes the measurements incomparable with
  what the generator produces, and F.3's parameters would be fitted to the wrong stage.
- **Check the plants are not needed elsewhere** — the 30-plant observation plan, the PPFD measurement (meter ~10/10),
  any time series.
- **One cultivar.** Mixing cultivars mixes leaf shape, which is the thing being modelled.
- **Senescent lower leaves are not a reason to exclude a plant.** Record condition per compound: usable for counts,
  excluded from the shape/texture reference. Record it **by eye** — the automatic condition classifier has already
  mislabelled dark photographs of healthy leaves as necrotic.

---

## 2. Setup

- **The rig**: same lights and same camera as the dwt_01-04 captures, ChArUco board in place.
- **Tripod, always.** Hand-held drift is what invalidated the D0 brightness target and left the dwt_101 azimuths
  assumed rather than measured.
- **Exposure locked, manual.** On auto, brightness changes as leaf area is removed and the defoliation comparison
  breaks. Manual focus too if available.
- **The ruler lies flat in frame**, never standing. Both its ticks and its width must be readable — that is what
  makes the scale cross-checkable. Of the 117 dwt_101 plant photos, **0** had both, which is why C2 has no cm².
  **The ruler must not cross a leaf outline.**
- Width is **31.1 mm** outer metal edge to outer plastic edge (`user_measured`, 2026-10-08).

Fill `1_session.csv` once, before the first shot.

---

## 3. Intact capture — 5 photos per plant, all four plants

1. **Top, 1** — board, flat ruler and plant all in frame.
2. **Side, 4** — **rotate the pot, keep the camera fixed**, roughly 90° apart.

With the board in frame the **azimuths are measured, not assumed**, so the `capture_order_assumed` problem of the
dwt_101 set does not recur here.

Set at least one side view to a `camera_elevation_deg` from the Addendum E shoot sheet
(`build/paired_control_20261006_01/shoot_sheet.csv`) so it can serve E directly.

**Top-view scale:** the leaves sit above the ruler plane, so a naive reading overestimates. With the board the
correction is computable — nothing to do while shooting except record **pot height and soil height** in
`2_plant.csv`.

Record one row per shutter press in `3_photo.csv`, and the ruler readings from the `level` photos in
`4_height_reading.csv`. **Do not type filenames** — record `entry_time` and match by EXIF afterwards.

**Before the first shutter press, fill what can be seen without cutting** in `2_plant.csv`: `leaf_color`,
`leaf_rugosity`, `terminal_inflorescence`, and the seed-provenance columns. The cultivar is unrecoverable (the
plants are sold as "앉은뱅이 토마토" with no cultivar name), so these observations are the only genotype evidence
there will be — see SCHEMA.md, "Why the phenotype columns exist". `variety_cultivar` is the literal string
`unknown`; do not write a guess into it, however much the plant resembles a known dwarf.

---

## 3.5 Arrangement series — the C5 real reference (same session, after the alone shots)

C5 (occlusion) has **no real reference at all** in `stage1_contract.json`; the canopy module's mutual-shading
prediction is currently unvalidated. This series supplies it, as a **paired** design: the same plants photographed
at neighbour counts 0 / 1 / 2, so plant-to-plant variation (per-scene AP50 0.228–0.511, I.1) cancels. It measures
**instantaneous mutual occlusion only** — not acclimation; leaf angles do not change in a photo session, so this
does NOT fill diaf024's density-acclimation gap and must not be reported as if it did.

1. **Alone** — the 5-photo set of section 3 (already counted there). This is the un-occluded reference.
2. **Pair** — two plants, pots touching, 5 photos (1 top + 4 side). Two sessions so all four plants are used;
   declare the pairing before shooting and record it in `group_id`.
3. **Quad, 2×2 square** — pots touching, 8 photos (1 top + 7 side, denser azimuths because occlusion is highest).
   The 2×2 square, never a row: in the square all four plants are symmetry-equivalent (2 neighbours at pitch d,
   1 at 1.41·d), so every plant is the same treatment — 4 replicates. A row would mix middle (2 neighbours) and
   end (1 neighbour) positions and halve the replication.
4. **Repeat-noise shots** — re-take ONE photo per arrangement without touching anything (3 extra photos total).
   The alone-vs-repeat difference is the free estimate of repeat noise that any occlusion falsification threshold
   has to be set against.

Rules that make or break the series: pot orientation marks fixed across all arrangements (SCHEMA rule 10); alone →
pair → quad order; pitch = pot outer diameter (pots touching), recorded; every plant is an edge plant here — say so
when reporting, this is a neighbour-count series, not a closed-canopy density series.

**How to get 4 side views of a GROUP without rotating any pot** (rule 10 forbids per-pot rotation): place the
group and the board together on one rigid tray and **rotate the tray as a unit** — relative geometry is preserved
exactly and the board still measures every azimuth. If no tray is available, walk the camera around the group
instead and accept the larger distance/framing scatter; never rotate individual pots.

After the destructive session provides each plant's true total leaf area, compute per plant and arrangement
f(p,a) = 1 − visible/total; the paired deltas Δf(p, alone→pair) and Δf(p, alone→quad) are what the canopy module
must predict. Declare the pass/fail threshold from the repeat-noise shots BEFORE computing the model's prediction.

---

## 4. Addendum E — 6 further photos — DEFERRED, not part of this session

**Decided 2026-10-08: E is not shot here.** It is shot later, in a separate session, on a plant that will **not**
be destroyed, after G.2 has settled the B5a baseline. Reasons: E's pass/fail rule compares the real set against a
synthetic set that G.2 may replace, so shooting it now risks spending the session on a control for a rendering
configuration that is about to change; and E must stay re-shootable, which a destroyed plant is not.

Two things still carry over into section 3 so E stays cheap later:

- Set at least one side view to a `camera_elevation_deg` from the shoot sheet
  (`build/paired_control_20261006_01/shoot_sheet.csv`). Costs nothing now, and if the baseline survives G.2
  unchanged, that view can serve E directly.
- Keep `plant_bbox_frac_height` noted for every side view in `3_photo.csv` `notes`, so the later E session can
  reproduce the framing. The shoot sheet gives, per view, `camera_elevation_deg` and **`plant_bbox_frac_height`**
  (the plant's share of frame height), and **both must be matched** when E is finally shot — framing changes
  leaflet pixel size by up to 2x (B4a), so an unmatched framing destroys the experiment.
  `view_E*_synth.png` sits in the same folder to compare against.

**Azimuth does not need matching** — it is arbitrary on both sides.

`photo_kind = E` therefore stays unused in this session.

---

## 5. Stop. Check before cutting.

Review every photograph for focus, a cut-off ruler, an over-occluded board, and exposure jumps.
**A bad photograph can be retaken; a cut plant cannot.** Cutting begins only in a later session, once the captures
are confirmed good.

---

## 6. Destructive session (later)

**Plant 1 — sequential defoliation.** Remove **one compound leaf at a time**, top down, re-shooting the same view
set from the same camera position after each removal. The pixel difference between consecutive images is exactly the
region that compound occupied — **per-organ visible masks with no cross-view matching at all**, which is the step
that failed on dwt_01. Then flatten and photograph each removed compound with the ruler, and each of its leaflets.
Record in `5_defoliation_step.csv` (+ `3_photo.csv` with `photo_kind = defoliation_step` and the `step_index`).
Compound-level, not leaflet-level: ~8 extra captures, not ~40.

**Plants 2-3 — position-labelled dismantling.** Photograph each compound spread flat with base and terminal both
visible and every attachment point visible; assign a `compound_id`; label each station along the rachis by index,
side and **class by position**; then detach blade by blade keeping the label and photograph each blade alone on white.
Record in `6_compound.csv` and `7_blade.csv`.

**`class_by_position` is set by position on the rachis, never by shape.** Shape is what the generator is trying to
learn from these blades; labelling by shape would be circular.

**Lengths and areas are not typed** — they come from the photographs with the ruler in frame, which is faster and
more accurate, and carries a known ±1.12 % per-photo scale uncertainty (**±2.23 % on an area**), measured in I.4b on 2026-10-08 and superseding the ±1.2 / ±2.4 % quoted at the old 3.0 cm width.

**Genotype-proxy observations, while the plants are open.** Three cheap readings that no later session can recover,
each deciding one thing in the FSP (sources in SCHEMA.md):

1. **Does the main axis end in an inflorescence?** → `terminal_inflorescence`. Then count the leaves between two
   consecutive inflorescences → `leaves_between_inflor`, and set `growth_habit`. A determinate habit means stem
   length needs a termination point, so "more resource → more stem" is the wrong functional form.
2. **Leaf colour and blade rugosity**, confirmed against the detached blades rather than from across the room
   → `leaf_color`, `leaf_rugosity`. Dark-green + rugose indicates a BR-biosynthesis dwarf, i.e. an internode-length
   ceiling that light cannot lift — and a blade that is genuinely not flat, which the renderer currently assumes.
3. **Optional, plant 1 only, costs a dye:** infiltrate a detached terminal leaflet with 1 % fuchsin acid at
   0.027 MPa for 2 min → `bse_fuchsin_result`. **Dry patches = heterobaric** (bundle sheath extensions present),
   **uniform = homobaric**. Only needed before a light-treatment comparison; `not_tested` is an acceptable answer.

Do these **after** all photographs of that plant are taken — the dye and the handling destroy the blade.

---

## 7. One thing to know before the photographs are processed

The 2026-10-07 code review found three defects in the real-photo pipeline these captures will run through:
the silhouette segmenter has no colour polarity and can label the wall as plant (A5); `solve_pose` has no per-frame
reprojection gate and reports degenerate corner sets as solved (A7); the "rotation-consistency check" is a pixel-area
CV that a constant wrong mask passes (A6).

**Shoot now — the photographs are unaffected. Fix A5 and A7 before processing them.**
