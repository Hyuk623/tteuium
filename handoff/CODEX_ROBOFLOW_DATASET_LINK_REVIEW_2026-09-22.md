# Roboflow Shared Dataset Inspection

Date: 2026-09-22
Status: inspection in progress.

## Request and scope

The user supplied a Roboflow dataset link after discussing the side model's low-looking training-summary metrics. Inspect the linked content to establish what the export contains, its class mapping, label geometry, split counts, and whether it includes evidence clarifying the metric scale or bbox-versus-mask evaluation. The URL's access token must not be copied into this handoff, scripts, or reports.

Download only the explicitly shared export when available, preserve its original bytes under `build/roboflow_dataset_review_20260922/`, and inspect it without executing archive contents. Preserve all existing photos, labels, model settings and source code. No inference, training, evaluation jobs, uploads or remote edits are authorized by this inspection.

## Intended checks

- Identify dataset/project/version and export format from actual files.
- Count images and labels per split, inspect exact class names and malformed/missing labels.
- Distinguish rectangle-only labels from traced polygons; inspect representative image overlays if available.
- Check repeated image identifiers/hashes and plant/session identifiers across splits where exposed; distinguish leakage evidence from speculation.
- Determine whether any training/evaluation artifact explains the saved metric values. Do not assume a dataset export includes model weights, prediction outputs or evaluation results.
- Save reproducible observations and limitations here, plus redacted JSON/CSV audit artifacts in the build directory.

## Outcomes

Pending inspection.

The user supplied a second dataset link during inspection. Preserve it separately as `shared_dataset_02.zip` and compare both exports. The first download succeeded and is a ZIP archive; no archive code has been executed.

## User-directed organization (2026-09-22)

The user then requested grouping the same plant together. Create a new derived package at `build/roboflow_dataset_review_20260922/by_plant/`, arranged as `<plant_id>/<session_date>/<middle|side>/`. Each view folder must contain the exported images and a COCO annotations file for those images. Preserve original downloaded ZIPs, image bytes, bbox/polygon coordinates, class names and annotation content. Use the export's original photo name (`images[].extra.name`) when unambiguous; retain the Roboflow filename and source split in provenance.

COCO image/annotation IDs are only unique inside their original split, so remap them deterministically within each output file and keep an ID mapping CSV. Preserve separate middle/side category dictionaries; their numeric class IDs and class spellings differ. This organization does not allocate new training/validation/test splits or silently change the existing remote dataset. Record source split membership in the manifest so future plant-level evaluation splits can be designed explicitly.

Verify every output image hash against its ZIP member, every annotation's class/bbox/segmentation against its source, image/annotation referential integrity, and complete one-to-one coverage of both exports. No model execution or label repair.

## Completed findings and grouped package

Both links downloaded successfully. They contain COCO Segmentation datasets, not model evaluation reports or weights:

| Link order / local archive | Dataset | Version | Images (train / valid / test) | Annotations |
| --- | --- | --- | --- | ---: |
| First / `shared_dataset.zip` | `tom_middle_seg_bbox` | 1, named `2026-09-22 12:35am` | 22 / 6 / 3 | 805 |
| Second / `shared_dataset_02.zip` | `tom_side_seg_bbox` | 1, named `2026-09-21 8:42pm` | 22 / 6 / 3 | 937 |

Both exports contain 640 x 640 stretched, auto-oriented images with EXIF orientation stripped, and report no augmentation. The only non-image members are three COCO annotation files and two README text files. Consequently, these archives do not resolve the earlier training-summary metric scale, evaluation split or bbox/mask metric distinction. The middle export is a different project; the side model's earlier training metrics must not be attributed to it.

### Label geometry

| Class meaning | Middle export name / count / geometry | Side export name / count / geometry |
| --- | --- | --- |
| Compound leaf | `compond_leaf`: 105, all rectangles | `compound_leaves`: 105, all rectangles |
| Leaflet | `leaflet`: 604, all rectangles | `leaflet`: 677, all rectangles |
| Main stem | `main_stem`: 27, all nonrectangular polygons | `main_stem`: 28, all nonrectangular polygons |
| Sub-stem | `sub_stem`: 47, all nonrectangular polygons | `sub_stem`: 88, all nonrectangular polygons |
| Shoot | `shoot`: 22; 21 rectangles + 1 nonrectangular polygon | `growth_shoot`: 39; 31 rectangles + 8 nonrectangular polygons |

The leaf rectangles are consistent with the user's stated bbox annotation approach. Being stored in a `segmentation` field does not turn them into traced leaf outlines. Preserve them as bbox observations; they are not sufficient as leaf surfaces for light interception. Nonrectangular stem polygons identify annotation type, not verified anatomical accuracy.

The two category-ID maps differ (for example, ID 2 is middle `leaflet` but side `growth_shoot`). Therefore the grouped package intentionally preserves separate COCO files per view. Class names are not silently corrected or unified. The side export contains 88 sub-stem annotations, whereas the previous project metadata reported 87: retain each source/version's counts rather than rewriting records to agree.

All 62 image references resolve to actual archive members of the declared size. The implemented structural checks found no duplicate IDs within a source split, missing image/category references, nonpositive boxes, absent/invalid polygon lists, zero signed-area polygons, or out-of-image geometry beyond a 0.02 px rounding tolerance. Every image has at least one annotation. This is not a complete topology, object-coverage, or label-accuracy certification; e.g. self-intersection and overlapping duplicate objects were not comprehensively evaluated.

Two representative validation-image overlays were visually inspected (middle `dwt_04_260920_24.jpg` and side `dwt_04_260920_18.jpg`). They show the expected leaf/compound boxes and stem/shot outlines. These are human-label overlays, not model predictions. Four review previews are saved in the build folder.

At 640 x 640, 37/47 middle sub-stem boxes and 41/88 side sub-stem boxes have a shorter side below 20 px. This flags fine-structure resolution for later inspection, not a proven cause of the earlier low-looking model metrics.

### Split observations

The archive image hashes and original source filenames have no exact repeats within either export. However, all four plant/session groups occur in multiple original splits. This is suitable to retain as source history for reconstruction, but it is not a plant-held-out evaluation split. It cannot establish generalization to unseen plants, and it does not explain a low metric by itself. No remote split was changed.

### User-requested output

Created `build/roboflow_dataset_review_20260922/by_plant/` with:

| Plant | Capture date (YYMMDD) | Middle | Side | Total |
| --- | --- | ---: | ---: | ---: |
| `dwt_01` | `260920` | 7 | 7 | 14 |
| `dwt_02` | `260920` | 8 | 8 | 16 |
| `dwt_03` | `260921` | 8 | 8 | 16 |
| `dwt_04` | `260920` | 8 | 8 | 16 |

Each `<plant>/<date>/<view>/` folder contains its images and `_annotations.coco.json`. `dwt_01_260920_15.jpg` (side) and `dwt_01_260920_26.jpg` (middle) are absent from these exports; nothing was fabricated to fill the gaps. No top-view images were provided by these links.

The package includes `README.md`, `manifest.json`, `image_provenance.csv`, and `annotation_id_map.csv`. Image filenames are restored from `extra.name`, while the original Roboflow filenames, original split and IDs are retained in provenance. Numeric IDs are made unique within each output COCO file; all other image and annotation fields are verified preserved after accounting for the documented remapping. These are local COCO IDs, not cross-view physical organ IDs.

An equivalent downloadable bundle is `build/roboflow_dataset_review_20260922/roboflow_middle_side_by_plant.zip`.

### Validation and reproduction

- Verified 62/62 image bytes against the original archive members by SHA-256.
- Verified 1,742/1,742 annotation records against their source, including bbox, polygons, class, area and any extra fields; only COCO IDs and additive provenance differ.
- Verified class dictionaries, image dimensions, image/annotation referential integrity, one-to-one coverage, and unique output IDs.
- Verified the final bundle CRC and each member against the corresponding grouped file.
- `audit_exports.py` reproduces the structural audit and previews; `group_by_plant.py` creates a fresh grouped package and refuses to overwrite an existing package. Both are inspection scripts in the build directory, not source-pipeline changes.
- Machine-readable audit: `audit_summary.json`, `image_inventory.csv`, `annotation_geometry.csv` in the parent build folder.

No inference, training, evaluation execution, uploads, original-label repair, remote changes, original-resolution coordinate conversion, or automatic same-leaf ID association was performed.
