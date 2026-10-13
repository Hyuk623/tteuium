# Density-acclimation + time-series protocol — 18 plants, 2 spacings (2026-10-09)

Decided 2026-10-09 (user): 18 plants besides the 4 destructive ones; **fertilizer is excluded from this cohort**
(deferred to a later sowing, after the nutrient contract runs). This experiment measures the one input the
published dwarf-tomato FSP model names as its missing piece — leaf and leaflet angle as a function of planting
density (Butturini et al. diaf024: one fixed 70° for all densities, named as the cause of their density-dependent
bias) — and doubles as the weekly time series that steps 4–5 (growth fitting, per-leaf calibration) need.

**The plants are the independent unit. Nothing here is destroyed.**

## 1. Design

| block | layout | pitch | n | position classes |
|---|---|---|---|---|
| dense | 3 × 3 square | pots touching (pitch = pot outer diameter) | 9 | 1 interior, 4 edge, 4 corner |
| sparse | 3 × 3 square | 2 × pot outer diameter | 9 | same |

The 3 × 3 square is mandatory: its centre plant is a TRUE interior plant — the closed-canopy case the 4-plant
arrangement series cannot produce. Record the pot outer diameter once; both pitches derive from it.

## 2. Assignment — before anything is placed

Number the 18 pots, then assign to blocks and grid cells by a recorded random draw (lots, or a shuffle with the
seed written down). **Never pick by eye** — choosing "even-looking" plants per block is the selection bias the
capture pack already bans. Record every assignment in `1_assignment.csv` with the randomization note.
Mark every pot's orientation once, aligned to the board, and never rotate a pot afterwards.

## 3. What stays constant for the whole run (record once, then do not touch)

- Nutrition and watering: identical for all 18, recipe written in `0_constants.csv`. Fertilizer is NOT a
  variable in this cohort.
- Lamp positions and settings; the blocks' locations in the room; camera and exposure per the capture pack's
  setup section (tripod, locked manual exposure, board in frame).
- Pots are never moved between blocks, never re-spaced, never rotated. A plant that dies or breaks is recorded
  (`status` in `1_assignment.csv`) and its cell left empty — not replaced mid-run.

## 4. Weekly capture (the time series)

Once per week, same weekday, per plant: **1 top + 1 side** — deliberately the product's own two-view input —
plus **1 block overview** per block. Side views of inner plants are taken from outside the block (no pot moves);
occluded is fine, that is the data. One row per shutter press in `2_weekly_photo.csv` (entry_time + EXIF
matching, as in the capture pack; never type filenames). ~40 photos/week, 15–20 minutes.

Repeat-noise: in week 1 only, re-take one top and one side without touching anything (2 extra photos) — the
free noise floor any later per-leaf comparison threshold is declared against.

## 5. The acclimation measurement (once, later)

After visible acclimation has had time to develop (≥ 3–4 weeks; decide the date in advance and log it, not after
looking at the plants), one fuller session: for each block, the interior plant and two randomly pre-drawn edge
plants get the capture pack's 5-photo set (top + 4 sides, walking the camera around — pots still never rotate).
These are the photos the density-vs-angle analysis runs on. Everything else stays weekly 2-view.

## 6. What this experiment feeds

- diaf024's gap: leaf/leaflet elevation angle per density (the conference-relevant measurement).
- C5 closed-canopy reference: the interior plants' visible fractions vs the same plants' sparse-block twins.
- Steps 4–5: weekly per-plant time series for growth fitting and the leaf-ID tracking trial.
- Addendum E: any one plant here satisfies E's "not destroyed, re-shootable" requirement.
- O-cell re-anchoring: sowing dates of these 18 (record in `1_assignment.csv`) give `plant_age_days` as
  user_measured.

## 7. Stop rules

Photographs are never processed before A5 and A7 are fixed (code review). If a block must be physically moved
(force majeure), the move is logged and the acclimation clock restarts from the move date.
