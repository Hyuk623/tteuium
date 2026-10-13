# Addendum C: flattened leaf capture (non-destructive) — leaflet -> compound -> leaflet re-analysis

Date: 2026-10-05 22:45 KST. Author: Claude (chat), for the running Claude Code CLI session.
Applies on top of the Stage 1 prompt, Addendum A (A.1–A.4) and Addendum B (B.1). Ownership unchanged: write only in `tomato3d/synth/`, `tests/test_synth_*.py` and `build/`. `data/raw/` is human-owned (the user puts photos there; you read only).

## 0. Why
The user has decided **no destructive sampling**. Flattened-leaf photos replace it: they give real leaflet contours (today `leaflet_contours.json` holds 15 `human_full` + 180 `geometric_proxy`) and real leaf area in cm² as ground truth for P1 area estimation, without cutting the plant.

**User decision: shoot both levels.** Pipeline: **C1 leaflet contours → C2 compound assembly → C3 leaflet re-analysis in compound context.**

## 1. Capture (user task; you only read and validate)
Folder: `data/raw/<plant_id>/<plant_id>_leaf_<YYYYMMDD>/`. Ruler or printed grid visible in **every** photo; camera roughly perpendicular; white backing sheet **under** the leaf, clear sheet pressed **on top**.

| File | Content |
|---|---|
| `L01_compound.jpg` | the whole compound leaf, flattened, in one frame |
| `L01_T.jpg` | terminal leaflet |
| `L01_P1L.jpg`, `L01_P1R.jpg`, … | lateral leaflet pairs, numbered **from the petiole outward**, L/R as seen with the adaxial surface up and the petiole toward the bottom of the frame |
| `L01_I1.jpg`, … | intercalary leaflets, numbered from the petiole outward |

- Compound leaves keep the existing convention: `L01`, `L02`, … bottom → top of the plant.
- Two sources, both allowed, recorded in `attachment`:
  - `attached` — leaf still on the plant, pressed in place (healthy leaves; the time series).
  - `detached` — a leaf that fell or was already being removed (free; good for contours). Never detach a leaf for this.
- `condition ∈ {healthy, senescent, damaged}`. Senescent/damaged leaflets may be used for contour statistics only if tagged; they must not set the healthy-leaf shape priors.

`leaf_area_capture.csv` (human-written, one row per photo):
`plant_id,session_id,photo_file,compound_id,leaflet_id,level,attachment,condition,grid_pitch_mm,captured_at,pressed,notes`
- `level ∈ {compound, leaflet}`; `leaflet_id` empty when `level=compound`.
- `pressed ∈ {yes,no}` — whether a clear sheet flattened it. Unpressed areas are underestimates; flag them.
- `notes`: record any petiole/leaflet damage caused by pressing, with the compound id.

## 2. Processing (new `tomato3d/synth/leafarea.py`, outputs under `build/leaf_area_<YYYYMMDD>_01/`)

**C1 — leaflet contours.** Rectify each leaflet photo by the grid/ruler (homography; px/mm from the grid pitch), segment the leaflet against the white backing, emit a closed contour in mm and `area_mm2`. Write to `leaflets.json` with `plant_id, compound_id, leaflet_id, position (T/P1L/…/I1), area_mm2, length_mm, width_mm, contour_mm, attachment, condition, pressed, source_photo, sha256`. Tag every entry `source='flattened_real'` — it is a new contour class beside `human_full` and `geometric_proxy`; do not overwrite the existing file, write a new one and let the generator read both.

**C2 — compound assembly.** From `L01_compound.jpg`, rectify the same way, then fit the compound skeleton: rachis polyline, petiole length, each leaflet's insertion point along the rachis (as a fraction of rachis length), insertion angle, and leaflet orientation. Match each leaflet in the compound photo to its C1 contour by position order, not by appearance. Emit `compounds.json`: `rachis_length_mm, petiole_length_mm, n_pairs, n_intercalary, terminal_fraction, per-leaflet {leaflet_id, insertion_fraction, insertion_angle_deg, azimuth_side}`. These are exactly the generator ranges currently guessed in `generator_config.json` — report observed vs configured side by side.

**C3 — leaflet re-analysis in compound context.** For each leaflet, compare its clean C1 contour with the same leaflet as it appears in the compound photo: overlap fraction with neighbouring leaflets, visible fraction, and apparent-vs-true area ratio (a measure of out-of-plane curl that pressing did not remove). Emit `leaflet_in_compound.csv`.

**QA, reported every run:** `sum(C1 leaflet areas)` vs `compound leaf area measured in the compound photo`. The compound figure should be the larger by roughly the rachis/petiole area; if the leaflet sum exceeds it, the match in C2 or a segmentation is wrong — list the compound ids and do not silently accept them.

## 3. Use
- Generator: replace `geometric_proxy` contours with `flattened_real` ones where available; set compound ranges from C2; use C3 overlap statistics instead of assumed values. This is a generator change, so it belongs in a **new run folder** with its contract declared before rendering, not retrofitted into `_02`/`_03`.
- P1: `area_mm2` per leaflet and per compound is the ground truth for area estimation from photos. Keep `attachment`, `condition` and `pressed` with every number so unpressed/senescent values can be excluded.

## 4. Tests (`tests/test_synth_*.py`)
Grid rectification recovers a known pitch within 1 %; a synthetic leaflet of known area round-trips within 2 %; a compound whose leaflet sum exceeds its compound area is reported, not accepted; missing `grid_pitch_mm` or a photo absent from the CSV is reported `incomplete`, never guessed.

## Revision C.1 (2026-10-05 22:48 KST, user decision) — scope limit

Addendum C as written has no bound and would ask for >1000 photos. The user has approved this scope instead. Treat it as the full requirement; anything beyond it is optional.

| Purpose | Scope | When |
|---|---|---|
| Leaflet contour library (C1) | **3–5 plants, ~100 leaflet photos in total** | once |
| Compound structure (C2) | **10–15 compound leaves**, from the same plants as C1 | once, same session |
| P1 area ground truth | **compound-level photo only (1 per compound)**, across as many plants as convenient; no leaflet photos | repeating, with the capture days |
| Shed / already-removed leaves | whatever appears, compound + leaflets if quick | opportunistic, free |

Consequences for the processing code:
- The leaflet-level steps (C1, C3) run on whatever leaflet photos exist. A compound with no leaflet photos is **normal, not incomplete**: run C2 on it, take its total area, and mark its per-leaflet entries `leaflet_photos_absent`. Never block or report `incomplete` for a missing leaflet photo.
- The QA check (leaflet sum vs compound area) applies only to compounds that have a full leaflet set; skip it silently otherwise.
- Report coverage in every run: number of plants, compounds and leaflets with each photo level, so the user can see when the one-off library is finished.
- Contours are a shape library, not a per-plant record: the generator samples from the pooled `flattened_real` set and must not require a contour for the specific plant being generated.

## Revision C.2 (2026-10-05 22:52 KST, user decision) — use the existing accepted masks first; no open-internet leaflet data

**No open/internet leaflet datasets.** Public tomato leaf datasets are standard cultivars; this crop's leaflets are small, round and strongly rugose. Importing that shape distribution would push C6 further from the real photos, which is the opposite of what Addendum B is trying to fix. Do not add any external leaflet source, and if one is ever considered it needs the user's explicit approval plus a recorded licence.

**Source already in hand.** The reviewed leaflet masks the user accepted are real leaflets of this crop: 1,163 accepted masks across 4 plants (`build/leaflets5_20260929/sam2_config_v5_4plants.json`; dwt_01 268 over 14 photos, dwt_02 248 over 16 photos, dwt_03/dwt_04 counted from the v5 training set — their `exports/` folders are empty, so locate the manifest the v5 training actually used and record its path and sha256). The generator currently uses only 15 of them (`human_full`) plus 180 `geometric_proxy`.

Order of work, replacing §2's implied order:
1. **C0 — harvest the existing masks.** Convert every accepted leaflet mask into a contour and add it to the generator's contour pool as `source='accepted_mask_projected'`. These are *projected* outlines: the leaf was photographed at an angle and was curled, so each is a foreshortened, curl-shrunk version of the true planar shape. Record per contour: plant_id, photo, view code, mask area px, and whatever viewing geometry the photo's board pose gives. This step needs **no new photography** and should run first.
2. **C1/C2 flattening, reduced to ~30–40 leaflet photos** (from 3–5 plants; the ~100 in Revision C.1 is superseded). Their purpose is no longer to be the contour library but to be the **reference that calibrates C0**: for leaflets photographed both ways, compare the flattened contour with the projected one and fit the correction (area ratio and shape distortion as a function of viewing angle and curl). Apply that correction to the whole `accepted_mask_projected` pool.
3. Compound structure (C2) and P1 area ground truth stay as in Revision C.1.

Report: how many contours came from each source, the fitted correction with its uncertainty, and how the corrected pool's shape statistics compare with the flattened reference. If fewer than ~15 leaflets have both a flattened and a projected contour, say so and treat the correction as provisional rather than applying it silently.

## Revision C.3 (2026-10-05 23:00 KST, user correction) — pose is not required to use a mask

C.2 step C0 implied every accepted mask needs the photo's board pose. It does not. The generator sets leaflet size from its own parameters; what a contour contributes is **shape and aspect ratio**, both scale-free. Requiring pose would discard most of the pool — in the 2026-09-27 pipeline run only 8 photos (dwt_03) and 4 (dwt_04) met the pose policy.

Harvest every accepted leaflet mask, in two tiers, and record `pose_available` and `scale_available` on each contour:

- **Tier A — mask + board pose + scale.** Contour in mm, plus the viewing angle of the leaf surface. Used to fit the angle-dependent part of the projected→flattened correction, and to check contour area in mm² against the flattened reference.
- **Tier B — mask only (no pose, no scale).** Normalised contour: resample the outline, align to the leaflet's own principal axis, scale to unit area. Keeps shape and aspect ratio, drops size. Goes into the generator's shape pool exactly like Tier A, with `scale_available=false`. **This is the majority of the 1,163 and must not be dropped.**

Correction accordingly:
- With enough Tier A pairs, fit the correction as a function of viewing angle and apply it per contour.
- Tier B gets the **distribution-level** correction only: shift the pooled Tier-B shape statistics (aspect ratio, boundary curvature, solidity) toward the flattened reference, and state in the report that it is a pooled correction, not per-contour.
- Never drop a contour for missing pose or scale; report the tier counts.
