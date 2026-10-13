# Top view -> 3D: real-photo link, sign fix, compound-level masks - execution (2026-10-12)

Executes `handoff/CLAUDE_CODE_CLI_PROMPT_TOPVIEW_REAL_LINK_2026-10-12.md` (X0-X5). Implementer: Claude Code, top->3D
session. Korean summary: `TOPVIEW_REAL_LINK_EXECUTION_2026-10-12_KO.md`. Outputs: `build/topview_20261012_02/`,
`build/topview_confirm_20261012_01/`.

## 0. Read / missing
Read: `TOPVIEW_P1_CROSS_BENEFIT_2026-10-12_KO.md`; my `TOP_TO_3D_EXECUTION_2026-10-12.md` (+_KO); P1_SEGMENT_TRUSS
execution sections 8-9; corrected T6 section 3 of `CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md` (now says
OVERestimates); MTG_CONVENTION section headers A3/A4/A5 (sections 14-16; nothing in them changes this work);
DETECTOR_POLICY; `docs/정의집_토마토_2026-10-11.md` section 2 (mm row already corrected by the definitions author);
CONVENTIONS; LOG tail; the parallel P1 prompt (`..._P1_SIDE_RIM_POSE_...`) for its file scope. Not edited:
`tomato3d/state/potscale.py`, `tomato3d/cli/rim_points_tool.py` (P1 session; imported read-only), config/,
data/records/, docs/, tools/. Nothing missing.

## 1. X0 - bias sign
`tomato3d/topview/measure2d.py` (module doc + header `plane_note`, which now carries `potscale.PLANE_NOTE` so there is
one wording) and `tomato3d/topview/geometry.py` (photo caveat) say OVERestimates, factor `Z_rim / Z_leaf > 1`. Every
mm row carries `scale_plane = rim_plane` and `plane_bias = overestimates_above_rim`; no correction factor, no assumed
leaf height. `build/topview_20261012_01/CORRECTION_2026-10-12.md` marks the two old JSON outputs (kept as the record
of that run; they held no mm). Grep: no `underestimat` left in `tomato3d/topview/`, `tests/test_topview*.py` (except
the guard test itself) or my execution reports - enforced by `test_no_underestimate_wording_in_topview`. Remaining
hits elsewhere are not this sign: `potscale.py:22` quotes the old wrong word inside its correction (P1 file);
`tomato3d/synth/leafarea.py` `unpressed_underestimate` is a different quantity (an unpressed leaflet's flat area).

Illustration only (never written to a package): length / area overestimate for a leaf `h` above the rim, from the 13
measured pot-centre depths (frame-width focal basis):

| h | length | area |
|---|---|---|
| 1 cm | +3.3 to +5.5 % | +6.7 to +11.2 % |
| 2 cm | +6.8 to +11.6 % | +14.1 to +24.4 % |
| 5 cm | +19.0 to +34.9 % | +41.6 to +82.1 % |

## 2. X1 - link to the pot record
New `tomato3d/topview/reallink.py`. A photo carries `plant_id` + the RAW sha256 only through `link_top_capture`:
raw HEIC sha256 == `captures.csv`, HEIC `ispe` == JPG size, no `irot` / EXIF rotation (same refusals as the rim tool;
`heic_geometry` imported from it). Linked file = the package copy `build/roboflow_upload_20261009/top_level_views/
<plant>_top.jpg`. The Roboflow download `IMG_8419.jpg` (sha `dbaba82d...`) is **refused**: same 3024 px size and
pixels that look like a re-encode (mean |diff| 0.44, p99 3, max 14 grey levels;
`build/topview_20261012_02/roboflow_jpg_vs_package.json`), but no hash ties it to the record. `dwt_113` = IMG_8419
re-run on its package copy (`71e6547b...`) linked to the HEIC `dd18df69...`. `measure_photo` without a link writes
`plant_id = unavailable` and no mm ("photo not linked to a capture record").

## 3. X2 - real mm for all 13 top captures
Package `build/p1_state_20261012_12`, records `data/records/pots/{pot_spec,rim_points}.csv`. **13/13 linked, 13/13
rim scale solved, 444/444 leaflets and 67/67 compounds carry mm; 0 unavailable.** Each mm value carries its 1-sigma
from the rim scale, propagated first-order (relative sd 0.16-0.23 %, x2 for areas; segmentation error NOT included).
Leaflet rim-plane area p10/p50/p90 22 / 58 / 139 mm^2, min-area-rect length 6.5 / 11.2 / 17.6 mm.

Per-photo camera pose from the rim homography + EXIF focal (iPhone 16, 35 mm-equivalent 52 mm, frame 4032 x 3024,
stored 3024 x 3024 crop), principal point assumed at the image centre -> `pose_status = approximate`, both focal
bases stored (`real_top/<plant>/pose.json`, `real_top/photos.csv`):

| | frame-width basis (5824 px) | frame-diagonal basis (6057 px) |
|---|---|---|
| pot-centre depth d | 193-269 mm | 201-278 mm |
| tilt from vertical | 1.0-30.8 deg, median 7.9 | 1.1-31.8 deg |
| two-axis self-check |r1|/|r2| | 0.89-1.03 (dwt_103 0.89) | same to 0.01 |

The focal basis does not move the self-check (both give 0.89 on dwt_103), so the 11 % miss is not the basis - the
crop offset / principal point is the likelier cause. The P1 session owns that question (its Y2) and the pose table
(Y4); when published it supersedes `pose.json`. The bias for a later leaf height is
`d / (d - h cos(tilt))` (`reallink.bias_factor`).

Detector provenance per photo (`build/topview_20261012_02/v4_split.json`, 64 px thumbnail identity vs the v4 COCO
export): train dwt_101/102/103/106/109/110; **dwt_104 test AND train, dwt_105 valid AND train** (uploaded twice, once
as `top_heic`); valid dwt_111; test dwt_113; not in v4 dwt_107/108/112. So 2 of the 4 "real reference" photos used for
the v4 real APs and for `measure_min_confidence` 0.25 were trained on - those numbers are partly in-sample (note added
to `topview_config.json`). Detections on train photos are optimistic; every row is a proposal anyway.

## 4. X3 - own-pot attribution
`tomato3d/topview/instances.py::attribute`, rule in the module doc. Compound `inside` = its mask reaches into the own
rim polygon; leaflet `inside` = centroid in the rim polygon or member of an inside compound; `outside` only with
positive evidence (centroid in a NEIGHBOUR pot's rim polygon, i.e. rim points clicked for another plant on the same
photo - none exist); everything else `ambiguous`, never silently assigned. Result: leaflets inside 442 / ambiguous 2 /
outside 0; compounds inside 66 / ambiguous 1. The 2 ambiguous leaflets and the 1 ambiguous compound are exactly the
known IMG_8419 (dwt_113) bottom-left neighbour case. Known limit (stated in code): a neighbour compound overhanging the
own rim polygon reads `inside`; only the human check catches it.

## 5. X4 - compound-level masks, membership, human check
- **Masks:** `compond_leaf` + leaflet boxes (same detector, `measure_min_confidence` 0.25 - derived for leaflets only,
  flagged `compound_threshold_note`) -> SAM 2.1 tiny box prompts. Persisted per instance as a lossless PNG cropped to
  its bbox + `masks_manifest.json` (offset, image size, pixel count, PNG sha256); `instances.load_mask` refuses a
  changed PNG.
- **Compute:** the local run was killed by system memory pressure (other sessions' forecast + tests running) after 3
  photos. SAM was therefore run on **Kaggle T4** (private dataset `dolgfish/tomato-topview-sam-job-20261012`: the 13
  linked copies + 511 boxes + SAM code + checkpoint; kernel `dolgfish/tomato-topview-sam-20261012` v1, COMPLETE,
  ~70 s total, torch 2.11 cu128, checkpoint sha256 checked in the kernel). No API key, pot record or mm left the PC.
  Locally `measure2d package --masks-from` reads the masks (`PrecomputedSeg`, box keys must match exactly) and does
  everything else. Check: the 3 photos finished on local CPU (`real_top_cpu_partial/`) vs Kaggle GPU -> per-instance
  mask IoU **1.0 on all 105 instances** (`cpu_vs_gpu_masks.json`).
- **Membership** (box majority, then mask majority, else ambiguous): 351 member / 91 ambiguous / 2 unassigned of 444;
  15 compounds received more than one `terminal_leaf` (`terminal_conflict`, the detector's known terminal-on-lateral
  confusion). Compounds per plant 3-7, mean 5.2 (67/13) - consistent with the user-stated 4-5 and unlike the
  generator's 6-8.
- **Human check:** `tomato3d/topview/confirm_tool.py` (+ `confirm_tool.html`) -> `build/topview_confirm_20261012_01/
  index.html` (7.3 MB, self-contained, half-resolution photos with mask overlays and the rim polygon) +
  `confirmations_template.csv` (511 rows, all `proposed`). Accept / reject / fix per instance (class, compound,
  attribution, mask ok); `confirm_tool check` validates a saved file (read-only proposal columns, allowed values,
  accept = unchanged, fix = changed, annotator required). The file is human-owned and stays under `build/`; the tool
  refuses any output path under `data/records/`. Page checked in Chrome by script (13/13 photos and all masks load,
  accept/fix/revert rules, 511-row CSV); a screenshot could not be taken (CDP capture timed out under memory load).

## 6. X5 - synthetic top camera from measurement
`tomato3d/synth/pairs.py`: `measured_top_block` (poses from `pose.json`, `source_kind = measured_approximate`) and
`_top_cameras` drawing one real pose per view (elevation = 90 - tilt, distance = camera -> rim-plane pot centre, look-at
= rim centre via `_top_target`; the real pot sits off the frame centre - not modelled, stated). Geometry
`build/topview_20261012_02/t2_geometry_measured.json` (frame-width basis; the diagonal ranges are in its note).
Old assumption 85 deg (+-3) / 270 mm: tilt 5 deg (2-8) is inside the measured 1.0-30.8; **270 mm is 0.8 mm above the
frame-width maximum (269.2) and inside the diagonal-basis range (201-278)** - i.e. at the far edge, not typical
(median depth ~240 mm). T2 stays gated: run without `--smoke-uncalibrated` exits 1 ("T2 gate closed: BENT_FRACTION is
unavailable"); a 1-scene smoke (`t2_smoke_measured_top/`, `not_for_training: true`) drew the dwt_103 pose (elevation
60.1 deg, 249 mm).

## 7. Commands and exit codes
| command | exit |
|---|---|
| `measure2d package ... --only dwt_113` (local CPU SAM) | 0 |
| `measure2d package ...` all 13, local CPU | killed by memory pressure (3 done) |
| `measure2d prepare-remote --package build/p1_state_20261012_12 --out .../kaggle/dataset` | 0 (13 photos, 511 boxes, 0 refused) |
| `kaggle datasets create` / `kaggle kernels push` / `kernels output` | 0 / 0 / 0 (status COMPLETE) |
| `measure2d package --masks-from kaggle/out_v1 --detections-from detections --heic-python ...` | 0 (13 linked, 444 leaflets with mm) |
| `confirm_tool build` / `confirm_tool check` (template) | 0 / 0 (511 proposed) |
| `pairs` without smoke / with `--smoke-uncalibrated` | 1 (gate) / 0 |
| `pytest tests/test_topview_reallink.py tests/test_topview.py` | 0 (17 + 13 passed) |
| full `tests/` (two halves, memory) | 0: 201 passed 1 skipped + 285 passed = **486 passed, 1 skipped** |

## 8. Tests (new: `tests/test_topview_reallink.py`, 17)
Grid refusals (size, irot, EXIF rotation, changed raw sha, unrelated download); no mm without plant_id + original hash;
linked photo -> rim mm with sd and the overestimate note; pose recovery from a known camera + bias factor + focal
bases; mask persistence round-trip + tamper refusal; run masks reload; remote masks reproduce the local run (and a
missing box refuses); compound -> leaflet membership (member / mask tie-break / ambiguous / unassigned / terminal
conflict); attribution keeps `ambiguous` and needs neighbour evidence for `outside`; confirmations stay `proposed`
until decided (accept-with-change refused, fix accepted); the confirm tool never writes under data/records; measured
top cameras; no "underestimate" wording.

## 9. Blocked / open, with owners
| item | owner |
|---|---|
| Human confirmation of the 511 proposals (`build/topview_confirm_20261012_01`) | **human** |
| Bend records `data/records/leaf_bend/` -> BENT_FRACTION -> T2 gate | **human** |
| R.5 side-view direction labels (T4) | **human** |
| Neighbour pot rims on photos where a neighbour intrudes (would turn `ambiguous` into `outside`) | human (optional; rim tool already records any plant_id per photo) |
| Focal basis / principal point, authoritative pose table | P1 session (Y2/Y4) |
| Compound confidence threshold (none derived; leaflet 0.25 reused) and a clean held-out reference set (v4 train/test leak) | user (C6-top step 0: >= 10 held-out real top labels) |
| Mask -> P1 observation ingest (confirmed rows -> `top_detection` / `human_top_labels`) | P1 owner, after human confirmation |
