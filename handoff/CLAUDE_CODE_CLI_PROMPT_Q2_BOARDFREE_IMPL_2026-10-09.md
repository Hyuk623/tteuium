# Prompt Q2 — Board-free 3D: implementation, calibrated on existing synthetic renders

Paste to Claude Code. Implements Prompt Q (same standing decisions: board dependence dropped,
dwt_01~04 droppable, boardfree_ namespace, C6/N/O/P untouched). Method choices below are fixed by a
2026-10-09 literature survey; the survey's accuracy numbers are ESTIMATES — phase QG exists to replace
them with measured ones before any real-photo claim.

## Method stack (fixed)
- Pose: VGGT-1B (fp16 autocast, weights fp32 — a cast to half trips a known dtype error in the camera
  head; input long side 518) AND Pi3X AND MASt3R-SfM, run independently. Trust a view only where all
  three agree within 5 deg relative rotation.
- Refine: bundle adjustment with soft rotation priors from recorded capture geometry
  (azimuth 0/90/180/270 sigma 10-15 deg; elevation 0/25/90 sigma 5 deg, tightened to 2-3 deg where the
  pot-rim ellipse gives a per-view elevation). Priors exist mainly to kill 90/180-deg azimuth flips from
  repetitive leaf texture, not to fine-tune. COLMAP's pose_prior_mapper takes position priors only, so
  add the rotation-prior residual in pycolmap/PyTorch BA directly (9 images — a small custom BA is fine).
- Constraints: SAM 2.1 plant/leaflet masks (downscale input to 1512 px to shrink the 1x->2x domain gap;
  compare against full-res on 20-30 hand-checked masks first). Use masks as silhouette carving of the
  point map + reprojection-IoU loss, NOT as final geometry.
- Scale: ruler endpoints triangulated in 3D (s1) vs pot-rim 3D circle fit against recorded pot dims (s2).
  Accept mean only if |s1-s2|/mean <= 2%; 2-5% investigate; >5% mark plant failed. Never average silently.
- Traits: per-leaflet 2D->3D label transfer (majority vote across views), B-spline/Bezier surface fit,
  area + inclination vs the pot axis (gravity). Leaflets with >30% template-completed area are excluded
  from measured stats and reported separately.
- Pins: record repo commit SHAs + checkpoint sha256 at first run (vggt, Pi3, mast3r, pycolmap version).
  Weights licenses are non-commercial (research OK); note in the run manifest.

## Phase QG — calibrate on EXISTING rendering assets (ground truth for free)
The synthetic generator + Kaggle renderer already produce views with exactly known camera poses and
known per-leaflet mesh geometry (e.g. the finalized N/O cell outputs, 180 views/cell, poses in the render
manifests under build/synthetic_dwarf_tomato_20261008_07 and its kaggle outputs).
1. From one finalized synthetic scene, select 9 rendered views matching the real protocol geometry
   (1 top el~90, 4 level el~0, 4 side el~25, az 0/90/180/270). If the existing ring lacks those
   elevations, render ONE extra 9-view job with the existing renderer/kernel pattern — no new assets.
2. Run the full stack (poses -> prior BA -> mask carving; masks here can come from the renderer's own
   ids, not SAM) on those 9 views.
3. Measure against ground truth and WRITE DOWN: per-view rotation/translation error (before/after BA,
   with/without priors), point-to-mesh distance stats, per-leaflet area error and inclination error from
   the surface fits, scale error (synthetic mm are known).
4. Gate G-QG: this phase cannot fail, it calibrates. Its output SETS the numeric gates for the real run
   (e.g. if synthetic-ideal leaf-area error is already 15%, do not promise better on real photos).
   If rotation agreement is impossible even on clean renders, the 9-view geometry itself is the problem —
   report and stop before touching real photos.

## Phase Q1 — real pilot, dwt_101 (Kaggle T4)
Inputs: build/roboflow_upload_20261009/{top_level_views,side_views}/dwt_101_*.jpg (9 views, 3024x3024,
EXIF-transposed; HEIC originals in data/raw/dwt_101/... if EXIF focal length is needed — check it
survived conversion, else read from the HEIC).
1. Preprocess: 1512 px copies; SAM plant + leaflet masks; background-removed copies.
2. Pose stack on two conditions (raw / background-removed); 3-way agreement table.
3. Prior BA; mask carving; LOO check: reconstruct from 8, reproject into the held-out view.
4. Dual scale.
Gate G0 (numbers refined by QG): all 9 views registered; 3-way rotation agreement <= 5 deg;
LOO plant-silhouette IoU >= 0.80; scale agreement <= 2%. On failure, retry in order: background-removed
input -> drop top view (8-view ring first, add top back) -> tighter priors. Log each retry.

## Phase Q2 — traits (only after G0)
Leaflet instances -> surface fits -> per-leaflet area/inclination, plant height/width (soil plane =
rim plane lowered by recorded soil depth), rachis topology (topology only; lengths flagged low-trust).
Report with the QG-calibrated error bars attached to every number.

## Kaggle T4 notes (from survey; verify and record actuals)
fp16 autocast only; 518 px; watch system-RAM peak while loading the ~5 GB checkpoint; expect seconds-level
inference for 9 views and minutes-level BA/MASt3R (36 pairs). Record real runtimes in the manifest.

## Do not
- Touch C6 rows, N/O/P cells, the frozen detector, or anything outside build/boardfree_*/.
- Promote any report-only check to a gate without the QG calibration in hand.
- Claim measurement-grade leaflet area/angle before Phase Q2 numbers carry QG error bars.
- Hardcode API keys anywhere; LOG one line per completed phase.
