# P1 side-photo rim points, camera pose, focal cross-check, generator caveat: execution report (2026-10-12)

Author: Claude Code (P1 session). Implements `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SIDE_RIM_POSE_2026-10-12.md` (Y0-Y6).
Korean companion: `_KO.md`. Command log: `build/p1_side_rim_pose_cli_log_20261012.txt`.

## 0. Read / missing
Read: `handoff/TOPVIEW_P1_CROSS_BENEFIT_2026-10-12_KO.md`; `P1_SEGMENT_TRUSS_EXECUTION_2026-10-12.md` (+`_KO`) §8-9;
the corrected T6 §3 of `CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md`; `TOP_TO_3D_EXECUTION_2026-10-12.md` §T0;
`MTG_CONVENTION_2026-10-10.md` A3/A5; `docs/정의집_토마토_2026-10-11.md` §2 (already corrected by its author);
`tomato3d/cli/rim_points_tool.py`; `CONVENTIONS.md`; LOG tail. Nothing missing. Untouched as instructed:
`tomato3d/topview/`, `tomato3d/synth/pairs.py`, `tools/`, `config/`, `data/records/`.

## 1. Per item

| Item | Result |
|---|---|
| **Y0 sign** | **Done** (fixed earlier the same day, kept): `potscale.py` docstring + `PLANE_NOTE` say a rim-plane scale **OVERestimates** leaves above the rim (bias d/(d-h)); template README fixed; P1 report §9 appended. No correction factor, no assumed leaf height. **Camera distance d per capture** is now recorded in `camera_poses.csv` (`camera_distance_mm` + sd) and in `pot_rim_scale.json`. |
| **Y1 side tool** | **Done.** `rim_points_tool --views side [--stem side_090]`: same refusals (raw sha256, HEIC `ispe` = JPG size, no `irot`/EXIF rotation). Built for the 52 side photos as four self-contained pages (13 photos, ~16 MB each): `build/rim_click_side_20261012_02/side_{000,090,180,270}/index.html`; each saves `rim_points_side_<az>.csv`. **`RIM_POINTS_COLUMNS` unchanged** (the photo is identified by plant + sha256); the records folder may now hold several `rim_points*.csv` files, read together, a photo in one file only. Old records parse unchanged (tested). Verified in the in-app browser: 13 photos, 3024 px decoded, side-view title/help, per-page save name; one autosave slot per page (`_01` superseded: its four pages shared one slot). |
| **Y2 focal basis** | **Neither basis closes the self-check; crop offset unknown → poses `approximate`.** `f_px` width basis 5824, diagonal basis 6057.3 (EXIF: 5.96 mm, 35 mm-eq 52, frame 4032×3024; stored 3024×3024 crop, principal point ASSUMED at the stored centre). On the 13 top photos the two-axis self-check passes on **1 of 13** (dwt_113) on either basis; on the other 12 the residuals exceed 2 σ of the click uncertainty (ratio up to −0.119 ± 0.014, orthogonality up to −0.099 ± 0.019). The two bases are **indistinguishable** on these near-frontal views (4 % in f moves the residual by < 0.003); the focal implied by the rim itself is ill-conditioned (2 993-29 762 px, sd up to 21 606). So the 12 % comes from something other than the basis - the unrecorded crop offset (principal point) and/or systematic click error with 2 points per side. Every pose that fails is published with `pose_status = approximate` and that reason. The oblique side photos are the discriminating test once clicked (synthetic: a 15 % wrong focal fails the check at 25° elevation, passes at 85°). |
| **Y3 side scale + pose** | **Code done; 0 of 52 side gaps closed - no side rim records yet** (human item 1). For a side photo: rim homography → pose → **vertical** scale on the pot axis at the rim centre (`scale_convention = pot_rim_pose_vertical_axis`, `scale_plane = pot_axis_vertical`, MC sd incl. the focal-basis spread when the check does not single one out); published **only for a validated pose** (validator-enforced). **Upright-ruler cross-check: not identifiable from one photo.** Scaling the ruler's position and length about the camera centre leaves its image unchanged (depth-length ambiguity; tested), so ticks cannot test the scale without one absolute anchor. Ticks are recorded; `scale_cross_check` stays `unavailable`, `scale_sources` 1. `camera.ruler_vertical_fit(..., z0_mm=)` is ready for an anchor once decided (user decision, §3). |
| **Y4 pose table** | **Done.** `camera_poses.csv` in the real package (65 rows: 13 top + 52 side): status validated/approximate/unavailable + reason, f and basis (both bases listed), principal point + its source, rim-implied focal ± sd, self-check residuals ± sd, rotation, translation, camera centre in the rim frame, distance ± sd, tilt. Validator `check_camera_poses`. **Not Q2**: `recon`/`fuse3d` untouched. |
| **Y5 generator caveat** | **Done.** `handoff/P1_GENERATOR_CAVEAT_2026-10-12.md` (which P1 numbers are generator-relative: fixture optical surfaces, occlusion-completion 5→10/14 and candidate shapes, tracking metrics on 6-8-compound plants, truth-relative proxy errors; software-only checks unaffected; A3 side angles appear little affected but **unverified**); dated pointers appended to `P1_EXECUTION_2026-10-11.md` and `P1_INVENTORY_2026-10-11.md`. |
| **Y6 real audit** | **Done.** `build/p1_state_20261012_14` (supersedes `_12`). Gap counts before → after: audit rows 273 → 273; **scale gaps 104 → 104** (52 side: "no rim edge points for this side photo" + tool command; 52 level: rim edge-on); Codex `audit_p1_package` 117 → 117 (104 scale + 13 optical). New: segment `P1.3_side_rim_pose` = unavailable ("0 of 52 side captures have a vertical scale; 1 of 65 poses validated"). Truss fixture rebuilt `build/p1_state_20261012_15` (supersedes `_13`; Codex fixture_ready true). |

Schema `p1_state_v1` **revision 6** (additive): table `camera_poses.csv`; convention `pot_rim_pose_vertical_axis`,
plane `pot_axis_vertical`; config `pot_scale.pose_self_check_k_sigma = 2` (statistical band, `computational_choice`).

### Top-view pose table (`_14/camera_poses.csv`, f basis shown = the one used)

| plant | status | d mm (± sd) | tilt ° | ratio res. ± sd | orth res. ± sd |
|---|---|---|---|---|---|
| dwt_101 | approximate | 278.3 ± 2.8 | 31.8 | +0.017 ± 0.021 | −0.099 ± 0.019 |
| dwt_102 | approximate | 272.1 ± 1.0 | 8.2 | +0.015 ± 0.007 | +0.026 ± 0.008 |
| dwt_103 | approximate | 257.4 ± 2.1 | 30.9 | −0.119 ± 0.014 | −0.025 ± 0.018 |
| dwt_104 | approximate | 242.9 ± 0.6 | 9.4 | −0.016 ± 0.005 | +0.006 ± 0.006 |
| dwt_105 | approximate | 230.1 ± 1.1 | 19.9 | −0.028 ± 0.010 | +0.035 ± 0.009 |
| dwt_106 | approximate | 249.3 ± 0.7 | 5.4 | −0.005 ± 0.005 | −0.019 ± 0.007 |
| dwt_107 | approximate | 241.4 ± 0.6 | 7.1 | −0.011 ± 0.005 | +0.015 ± 0.006 |
| dwt_108 | approximate | 268.4 ± 0.8 | 7.3 | +0.025 ± 0.006 | +0.010 ± 0.007 |
| dwt_109 | approximate | 240.9 ± 0.5 | 1.6 | +0.018 ± 0.005 | +0.001 ± 0.007 |
| dwt_110 | approximate | 200.8 ± 0.3 | 1.1 | +0.006 ± 0.003 | +0.011 ± 0.004 |
| dwt_111 | approximate | 231.0 ± 0.6 | 7.3 | +0.018 ± 0.005 | +0.006 ± 0.005 |
| dwt_112 | approximate | 222.2 ± 0.8 | 17.0 | −0.002 ± 0.008 | −0.025 ± 0.008 |
| dwt_113 | **validated** (width) | 261.3 ± 1.0 | 11.2 | +0.001 ± 0.008 | +0.003 ± 0.009 |

Distances are close to the earlier estimate (200-278 mm) but depend on the unverified focal/principal point; they
carry the `approximate` flag where the check fails.

## 2. Commands and exit codes (`build/p1_side_rim_pose_cli_log_20261012.txt`)
```
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode real --out build/p1_state_20261012_14 --capture-tz Asia/Seoul --capture-tz-ref '…'   0
python -X utf8 -m tomato3d.cli.run_p1 run --package build/p1_state_20261012_14          3 (valid, partial)
python -X utf8 -m tomato3d.cli.run_p1 collect --package build/p1_state_20261012_14      3
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261012_14       0 (17/17)
python -X utf8 -m tomato3d.cli.run_p1 prepare --mode fixture-truss --out build/p1_state_20261012_15   0
python -X utf8 -m tomato3d.cli.run_p1 run|collect --package build/p1_state_20261012_15  0
python -X utf8 -m tomato3d.cli.run_p1 replay --package build/p1_state_20261012_15       0 (54/54)
python -X utf8 -m tomato3d.cli.rim_points_tool --package build/p1_state_20261012_14 --out build/rim_click_side_20261012_02/side_<az> --views side --stem side_<az>   0 (x4)
python -X utf8 flow/check_flow.py --md                                                   0
```
Tests: new `tests/test_state_camera.py` (10); updated `tests/test_state_potscale.py`; full suite in §5.

## 3. Blocked items and owners
| Item | Owner |
|---|---|
| Click rims (+ optional upright-ruler ticks) on the 52 side photos with `build/rim_click_side_20261012_02/side_*/index.html`; save each `rim_points_side_<az>.csv` into `data/records/pots/` | **user** |
| **Decision: an anchor for the upright-ruler check** - (a) allow the ruler foot on the table + `pot_depth_mm` (70 mm) as the height of the table below the rim (T6 declared depth "recorded only"), or (b) locate the ruler from a second photo, or (c) leave side scales single-source | **user** |
| `data/records/pots/pot_spec.csv` still carries the template EXAMPLE row name/note (`EXAMPLE_square_cell`, "EXAMPLE ROW …"); values are the user's caliper numbers | **user** (agents do not edit `data/records/`) |
| `data/records/leaf_bend/` bend records (BENT_FRACTION, P1 bend field, top→3D T2) | user |
| R.5 side direction labels; plant_id ↔ slot; measured PPFD and lamp geometry; sowing dates | user |
| Principal point / crop offset of the stored photos (closes Y2 for the top views) - e.g. the un-cropped originals, or the side-photo focal estimates once clicked | user (originals) / P1 (re-run) |
| Q2 board-free 3-D (`recon`/`fuse3d`) using `camera_poses.csv` | separate decision |

## 4. Not done
No Q2, no correction factor, no assumed leaf height, no upright-ruler cross-check without an anchor, no change to
`tomato3d/topview/`, `tools/`, `config/`, `data/records/`.

## 5. Tests
Full `tests/`: **482 passed, 1 skipped** (390 s). `tools/tests/test_tomato_fsp_pipeline.py` (Codex, read-only): 28 passed.


## 6. Semi-automatic rim points for the side photos (2026-10-12, user request)

**Finding.** The user clicked the 13 `side_000` photos (`Downloads/rim_points_side_000.csv`, 2 points per side, 3 px).
Zoomed crops show those points on the **inner** rim edge (the soil boundary); the 60 mm caliper value is the **outer**
top edge, a light band ~40 px further out (front side). The automatic search found the outer line; the user agreed
("너가 더 잘 찾은거같아"). Those side_000 clicks are therefore **not** placed in `data/records/`. With them the poses gave 7
validated / 5 approximate / 1 unavailable (dwt_108: sides not numbered in order); the rim-implied focal over 12 photos
was 5751 +- 90 px (median 5957), closer to the width basis (5824) than the diagonal (6057) - provisional, since the
square was the inner one. Top photos: the person's top clicks sit ~13-16 px inside the outer silhouette (dwt_107,
dwt_110 crops; about 0.5-0.7 mm per side, i.e. up to ~2 % on the scale) - reported, not changed.

**Change.** `tomato3d/state/rim_auto.py` proposes OUTER-edge points (soil region -> 4 sides -> strongest outward step in
a band of 4 % of the soil width -> RANSAC line) for **front / left / right** of the side photos; the **back** edge (behind
leaves on side_000) is never proposed. Top photos are not supported (leaves overhang the rim from above; the search
lands on leaf edges). Proposals: `build/rim_auto_20261012_02/rim_points_side_<az>.proposal.csv` (+ `quality.json`): front
missing on 6 photos, right on 1, back on all 52 (for the person). The page gains `--prefill`: proposals show as hollow
squares; on saving, a kept proposal is marked `auto_proposal_kept (auto:rim_auto_v1)` in `note`, so the record says which
points a person placed. New pages (fresh autosave slot `rim_points_tool_v2_*`, so the inner-edge side_000 work does not
reload): `build/rim_click_side_20261012_03/side_{000,090,180,270}/index.html` (supersede `_02`). Checked in the in-app
browser: 8-12 prefilled points per photo, the empty side shown as `n: 0점`. Tests: `tests/test_state_rim_auto.py` (3).


## 7. CORRECTION (same day) - the "auto outer edge" was an artifact

Section 6 said the automatic search found the OUTER rim edge ~40 px outside the person's side_000 clicks. **That was
wrong.** `np.convolve(..., mode="same")` invents a step at the end of each profile; the "edge" was the end of the search
band (4 % of the soil width, 44-56 px), a fixed distance from the soil boundary - which is why it looked like a clean
parallel line. Fixed (profile ends ignored in `rim_auto.outward_points` / `refine_outward`); with the fix the side
proposals drop from 149 to 75 sides and none coincide with the earlier ones. Measured grey profiles below the front soil
boundary (dwt_113 / dwt_101 / dwt_110 side_000): the bright rim top ends **~8 / ~18 px** below the soil boundary, and on
dwt_110 it fades without a sharp line. So:
- the person's side_000 clicks ARE on the inner top edge (the sharp soil boundary); the outer top edge is only ~8-20 px
  (~0.5-1.2 mm, 1-4 % of the size) further out, and is soft;
- `build/rim_click_side_20261012_03` (pre-filled with the artifact points) and `build/rim_auto_20261012_02..04` are
  **invalid - do not use**; the "3-side pose validated on 4 of 12" check (scratch) used those points and is void;
- the 3-side pose + back-edge search (`complete_side`) found the back edge on 1 of 52 photos: the back rim is behind
  leaves; automatic completion of the side photos is not achievable here;
- top photos (after the fix): moving the person's lines outward to the silhouette changes the scale by median −1.1 %
  (−0.5 … −1.6 %), with noisy refined lines (residual up to 20 px, leaves/ruler) - records unchanged; top mm lengths may
  read ~1 % high (areas ~2 %).
**Way forward (needs one measurement):** the INNER top edge across the flats (caliper). The soil boundary is a sharp,
reliably detectable line; with the inner dimension the person's side_000 clicks become usable as they are, and the soil
boundary can be proposed automatically for the other azimuths. Nothing was written to `data/records/`.
