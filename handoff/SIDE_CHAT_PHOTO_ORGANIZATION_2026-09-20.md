# Side conversation handoff: capture organization and manual growth metadata

Date: 2026-09-20. Scope: decisions and file operations in the photo-organization side conversation only. This document does not resume or change the main thread's modeling, SAM, server, or training tasks.

## 1. User-selected storage location

Use this root for future organized capture data:

`C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis/tomato_photos_organized_/`

The user moved the existing dataset here manually. Do not copy it again from Downloads or rearrange the current folders without a request.

Current observed structure:

```text
tomato_photos_organized_/
├── filename_mapping.csv
└── 260920/
    ├── dwt_01/
    │   └── 260920/
    │       ├── dwt_01_260920_01.heic
    │       ├── ... (18 photographs)
    │       └── dwt_01_260920.json
    └── dwt_02/
        └── 260920/
            ├── dwt_02_260920_01.heic
            ├── ... (18 photographs)
            └── dwt_02_260920.json
```

The originally discussed logical hierarchy was `dwt_XX/YYMMDD/`. The user subsequently introduced the outer date folder shown above. Preserve that existing layout; the extra date level was observed rather than silently normalized.

## 2. Capture set and naming rules

- One capture set contains 18 photos of one plant on one date.
- Plant identifier: `dwt_XX`, with a two-digit plant number.
- Date token: `YYMMDD`; JSON uses ISO `YYYY-MM-DD`.
- Photo filename: `dwt_XX_YYMMDD_ZZ.<actual image extension>`.
- JSON filename: `dwt_XX_YYMMDD.json`.
- The two-digit view code combines capture inclination and board-relative direction; it is not an ArUco marker ID.

| Input positions, in order | View type | Polar angle from vertical top view | Codes, in order |
|---|---|---|---|
| 1, 2 | top_view | 0 degrees | 01, 03 |
| 3 through 10 | side_view | 90 degrees | 11, 12, 13, 14, 15, 16, 17, 18 |
| 11 through 18 | middle_view | 45 degrees | 21, 22, 23, 24, 25, 26, 27, 28 |

Verify ordering before naming. Do not treat an arbitrary Drive listing order as capture order. Do not silently shift remaining codes when an expected view is missing. Preserve originals and do not overwrite existing files.

## 3. Board-relative direction numbers

The user supplied an annotated ChArUco board diagram. With its printed heading at the top:

```text
             6 ----- 5 ----- 4
             |               |
             7  plant center 3
             |               |
             8 ----- 1 ----- 2
```

Direction means observing the plant at the center from the numbered side of the physical board. It stays attached to the board, not to the rotated image display. These are capture labels, not measured camera poses.

Examples under the existing code table:

- `01`: top view referenced to board direction 1.
- `03`: top view referenced to board direction 3.
- `17`: side view at 90 degrees, from direction 7.
- `27`: middle/oblique view at 45 degrees, from direction 7.

The user described `27` as a side view in one example. The assistant explicitly pointed out the conflict with the earlier table: `27` is middle_view; `17` is side_view. No subsequent instruction swapped the first-digit assignments. Confirm if the user intends to change them; do not silently relabel existing photographs.

For an exactly vertical top view, the assistant proposed using the bottom edge of the camera image pointing toward the numbered board side to distinguish 01 and 03. This roll/orientation convention was proposed, not explicitly confirmed by the user; do not claim it was measured or enforced in the current files.

## 4. Work completed on the two supplied folders

Original inputs:

- `C:/Users/sho36/Downloads/01_260920-20260920T090000Z-1-001/01_260920/`
- `C:/Users/sho36/Downloads/02_260920-20260920T085945Z-1-001/02_260920/`

Each contained 18 photographs. Numeric filename order matched the embedded timestamps dated 2026-09-20.

- Plant 01: IMG_7980 through IMG_7999, with 7985 and 7993 absent from the supplied set. All 18 supplied files were ordered by their existing numbers/timestamps and mapped by input position. No files were synthesized for those numeric gaps.
- Plant 02: IMG_8002 through IMG_8019.
- All 36 inputs had `.JPG` filenames but HEIC container signatures. The organized copies use `.heic`; image bytes were not decoded, re-encoded, resized, or otherwise modified.
- Initial organized copies were created under `C:/Users/sho36/Downloads/tomato_photos_organized_260920/`. Original inputs were preserved.
- `filename_mapping.csv` records original paths, destination-relative paths, input positions, view types/codes, nominal polar angles, embedded timestamps, and SHA-256 hashes.
- The user then moved the organized dataset into the project location in section 1.
- No anatomical view classification was independently verified from decoded images; assigned views follow the user's input-order protocol.

## 5. Manual growth JSON contract

The user enters biological observations manually. Generate an editable blank template when requested; do not infer counts from photos or fill unknowns with zero.

| Field | Meaning |
|---|---|
| plant_id | Stable identifier, e.g. dwt_01 |
| capture_date | ISO capture date |
| compound_leaf_count | aa: total compound leaves, including unfolding compound leaves |
| compound_leaves | One entry per compound leaf, with compound_leaf_id, leaflet_count and is_unfolding |
| leaflet_count | bb: number of leaflets on that particular compound leaf; null if not known |
| is_unfolding | true if this compound leaf is still unfolding; false if already unfolded; null if unknown |
| unfolding_compound_leaf_count | cc: unfolding subset of aa, not an additional count |
| growth_shoot_count | Newly requested field: count of very young leaves/shoots whose growth has just begun, entered by the user |
| truss_count | dd: number of flower trusses |
| notes | Optional user notes |

`compound_leaf` describes a leaf's compound structure; it does not mean the leaf must be unfolding.

The user explicitly requested **growth_shoot_count in future generated JSON files**. Default it to null. Keep it as a separate observation; do not automatically add it to, or subtract it from, compound_leaf_count or unfolding_compound_leaf_count. Its finer botanical counting boundary has not been specified.

Future blank template:

```json
{
  "plant_id": "dwt_XX",
  "capture_date": "YYYY-MM-DD",
  "compound_leaf_count": null,
  "compound_leaves": [],
  "unfolding_compound_leaf_count": null,
  "growth_shoot_count": null,
  "truss_count": null,
  "notes": ""
}
```

Example of one manually added compound-leaf entry (not a real observation):

```json
{
  "compound_leaf_id": "L01",
  "leaflet_count": null,
  "is_unfolding": null
}
```

Validation when observations are complete:

- Counts must be nonnegative integers. Use null for unknown/unentered values, and 0 only for a confirmed absence.
- JSON numbers cannot have leading zeroes: write 3, 8, 9 rather than 03, 08, 09. String IDs such as "L01" retain their zeroes.
- Number of compound_leaves entries should equal compound_leaf_count; IDs must be unique.
- unfolding_compound_leaf_count must be between zero and compound_leaf_count, and agree with the number of true is_unfolding entries when all statuses are known.
- Empty arrays and null counts in a blank template mean unentered, not a measured zero.
- The original compact notation `XX_AA_BB,BB_CC_DD` was discussed as a possible summary, but is not required by the created templates. No placement of growth_shoot_count in that compact code has been agreed.

Two editable JSON templates with Korean `_input_guide` explanations were created at the user's request. User edits are authoritative observations to check, not values to silently repair. Existing files were not automatically patched when growth_shoot_count was subsequently requested for future templates.

## 6. Latest read-only verification while writing this handoff

Both plant folders contain exactly the 18 expected HEIC filenames/codes. All 36 image SHA-256 hashes still match filename_mapping.csv after the user's move.

### Plant 01

File: `tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json`

- User has entered compound_leaf_count = 3, apparent leaflet counts 08/09/09, apparent unfolding count 03, and truss_count = 0.
- **Not valid JSON:** leading-zero numeric values remain; a strict parser fails at line 9, column 25 on 08.
- All three current is_unfolding values are false, while the apparent total unfolding count is 3. This remains semantically inconsistent; the assistant must not choose the real biological value.
- growth_shoot_count is currently absent.
- These contents differ from an earlier inspection, when L02 was true. Use this latest observation rather than the earlier chat summary.

### Plant 02

File: `tomato_photos_organized_/260920/dwt_02/260920/dwt_02_260920.json`

- Strict JSON parse passes.
- compound_leaf_count = 3, with L01/L02/L03 leaflet counts 7/7/5.
- All is_unfolding values are false; unfolding_compound_leaf_count = 0. These counts are internally consistent.
- growth_shoot_count = 2; truss_count = 0.
- This is now filled in; the earlier statement that it was blank is superseded by this inspection.
- Internal consistency is not independent verification against the plant.

### Mapping path caveat

filename_mapping.csv still contains destination paths relative to the original root, such as `dwt_01/260920/...`. From its current location, the actual path has an additional `260920/` prefix. Image hashes match when resolved against `tomato_photos_organized_/260920/`. The CSV was not modified during this read-only check.

## 7. Scope boundaries and next handoff

This side conversation organized files, provided manual JSON templates, explained conventions, and inspected user edits. It did not modify program source, calibrations, accepted image annotations, models, or servers, and did not execute segmentation, reconstruction, training, or PPFD simulation.

Main-thread follow-up should read this file explicitly. Automatic transfer of the complete side-chat history was not established. Preserve current user data; apply the new storage root and growth_shoot_count default to future generation. Any correction of existing biological values or reorganization of folders requires the user's actual intended values/layout, not guesses.
