# Review of Claude's new capture importer

Scope: read-only review requested by the user. Inspect CLAUDE_NEW_CAPTURE_IMPORT_BRIEF_2026-09-20.md, the importer, its tests and generated captures. Run focused deterministic tests and bounded reproductions using generated fixtures; no original edits, re-import, learned inference, server changes or PPFD. Verify delivered artifacts separately from claims about general input validation. Append findings and actual test outcomes below.

## Findings requiring correction

### R1 / P1 — Foreign calibration camera is not rejected

`tools/import_organized_capture.py:94` (`camera_profile`) checks that input photographs share their metadata and match the calibration resolution. It never compares their camera/lens/focal-length/zoom against a calibration camera profile. A synthetic set from an unrelated manufacturer, different lens, 2 mm focal length and 2x zoom is accepted with the existing iPhone trial intrinsics when dimensions are 3024 x 3024. The returned note falsely says EXIF agrees with the calibration profile. This contradicts the brief's claimed foreign-profile rejection and can corrupt all subsequent geometry. The existing calibration JSON has a camera_id but no comparable EXIF profile. Preserve diagnostic flags; explicitly report compatibility as unverified when evidence is unavailable, and require an explicit compatibility contract before claiming/relying on a match. Add a foreign-but-internally-uniform camera regression, not just mixed cameras within one set.

### R2 / P2 — Mapping selection is plant-only, allowing dates to mix

`mapping_rows` at line 50 filters only plant_id. A mapping containing dwt_01 / 2026-09-20 / 01 and dwt_01 / 2026-09-21 / 03 is accepted together. The session name at line 217 then takes only the first row's date. With existing files under those paths, the import loop would put different growth dates into one capture; full repeated code sets instead fail as duplicates without a way to choose the date. Validate one nonempty capture date and its path/name consistency, or provide an explicit session/date selector. Reject mixed dates before decode/output. Reproduction exercised the selector only; no mixed-date image import was run.

### R3 / P2 — Printed board caption is hardcoded as evidence

At line 224, every import writes `printed_caption_readable_in_top_views='7 x 5 squares, 38 mm; board 266 x 190 mm; A4 landscape'` regardless of the input photographs or configured board. The caption may be a valid manual observation for these particular two real sessions, but synthetic inputs with no printed caption also receive it. Move this observation into explicit per-session evidence with its source/reviewer, or leave it unavailable when not supplied. Do not populate new sessions with a fixed observed-caption claim. `confirmed_by_user=false` does not make a fabricated observation valid.

## Independently verified delivered artifacts

| Plant | Frames | Solved poses | Passed 1 px gate | Side poses solved |
|---|---:|---:|---:|---:|
| dwt_01 | 18 | 6 | 0 | 0 / 8 |
| dwt_02 | 18 | 8 | 0 | 0 / 8 |

- All 36 originals match the source hashes recorded in captures; all 36 working PNGs and all 36 prepared-session PNGs match their stored hashes.
- Prepared-session pose vectors equal their parent capture vectors.
- For all 14 solved views, board-evidence reprojection RMS agrees with the stored solve residual within 0.01 px. The focused synthetic regression also verifies the board-frame correction. This confirms coordinate consistency, not metric accuracy.
- Both captures retain validated_metric=false. No full/partial plant surface is claimed; these are prepared annotation inputs.
- Existing focused suite: `python -m pytest -q tools/tests/test_import_organized_capture.py` — **5 passed in 1.74 seconds**. Claude's full-suite 171 passed / 1 skipped is a historical claim, not independently rerun here.
- Read-only reproducer and result: `build/new_capture_import_review_20260920/review.py` and `review.json`. Run the script from the project root. It writes only its synthetic mapping and review report under build/.

## Review outcome

The new sessions were prepared and their stored geometry/evidence is internally consistent; the importer's claimed general safeguards need the three corrections above. No application code, original photos, human growth JSONs, thresholds or server settings were edited during this review. No learned inference, full re-import or PPFD was executed. Current side-view detection failure and calibration gate failures remain separate from the importer validation defects.

## User decision — R2 handled operationally

The user explicitly states that they will physically prevent different capture dates for the same plant from being mixed. Accept date isolation as a user-managed input condition: the selected input directory and mapping rows for a plant must represent one capture date. Folder separation alone does not alter the plant-only mapping selector; the supplied mapping must also remain date-isolated.

R2 is removed from the required code-change queue under this operating condition. The earlier reproduction remains a description of current behavior, not a claim that the code has been fixed. Do not implement additional date-selection/validation work or ask for the same decision again solely because of R2. Revisit only if the workflow later supplies combined-date mappings. R1 and R3 remain open.

## Additional risk-check scope

### User operational clarifications

The user states that photographs are taken using one lens and that physical landmark correspondences will be checked against the photo views. Accept these as workflow inputs. One-lens capture reduces lens-switching risk; it does not by itself establish that the earlier calibration used matching zoom/crop/focus/processing settings. Do not claim that the current photos used a different lens. R1 remains a limitation of automated compatibility checks, with this operational mitigation recorded.

Manual cross-view checking should preserve the same physical landmark (tip, visible attachment, distinctive vein junction) within the same leaflet ID. A shared view code or similarly placed screen coordinate is not physical correspondence. The user has not requested a new detector or additional enforcement here.

R3 concerns the importer writing the same observed-caption text for every input. It is not evidence that the user's actual board is wrong. Explain the distinction between measured/configured square size used for geometry and a hardcoded descriptive evidence string: changing the description alone does not change PnP geometry. The problem is that the evidence string can falsely suggest the board was checked for a future session. No new board-size confirmation or calibration-validity claim is inferred from this message.

The user requested checking possible problems after accepting operational date isolation. Review remaining geometry/provenance/quality behavior and current input status, without reopening R2, altering originals, running models or changing application code. Check inactive-null threshold handling with an in-memory configuration override and reassess manual JSON on disk. Separate observed current failures from future input edge cases and from conditions requiring manual labeling.

### Additional results

- **R4 / P2, conditional configuration defect:** import_capture line 157 converts max_mean_reprojection_error_px with float(). A permitted inactive null raises TypeError before import instead of leaving the gate inactive (CONVENTIONS section 3). Reproduced with an in-memory override only; config files untouched. Current value is 1.0, so this does not explain current pose failures. Reproducer: build/new_capture_import_review_20260920/check_risks.py; output: additional_risks.json.
- Current dwt_01 disk JSON still fails strict parsing. The user's intended correction is already known (8/9/9, unfolding 0, growth shoots 3); no further biological clarification is needed. Verify save/sync rather than asking for the values again. dwt_02 still parses with 3 compound leaves, unfolding 0 and growth shoots 2. Invalid dwt_01 metadata does not block this particular image importer because it does not read growth JSON; it will block a strict growth-record importer later.

### Practical consequences and priorities

1. Calibration compatibility (R1) and observed-board provenance (R3) are the remaining high-impact importer checks. Wrong intrinsics can distort position/shape; wrong physical board scale can bias all lengths even when reprojection looks acceptable. The current printed-caption observation is not evidence that another board was actually used; the defect is its unconditional reuse in software.
2. The actual 14 solved views all fail the 1 px gate. They can support diagnostic annotation/reconstruction experiments, but the quality flags must prevent validated lengths/areas or PPFD-ready claims. Board-frame coordinate consistency has already been verified and is not itself an outstanding defect.
3. All side captures have no measured pose. They can still provide manual appearance/identity context, but cannot presently add calibrated rays to triangulation. Leaves only visible in those views may have insufficient posed observations; report them as unavailable/partial rather than inventing depth or reusing nominal directions.
4. Same leaflet identity alone is not same physical point correspondence. Overlap/occlusion and similar leaflet shapes can create plausible but wrong triangulation. Retain manual review of physical landmarks, reprojection overlays and uncertainty; bbox volumes remain guides, not leaf surfaces or PPFD occluders. These are workflow risks, not newly reproduced code defects in the repaired labeling logic.
5. Preserve original-pixel coordinates when later cropping, resizing or converting images, and bind calibration to the actual processed image convention. Current imports preserve 3024-square dimensions and the reported orientation-1 inputs; no new current coordinate-conversion defect was established here.
6. The earlier CPU SAM automatic timeout is a separate known throughput issue. It does not invalidate manual labeling or prove segmentation accuracy, and this risk check did not rerun it.

No new application edits or original-data modifications were made. Date mixing remains accepted as operationally controlled and is not reopened.

## Saved dwt_01 correction completed — 2026-09-20 19:19 KST

The user explicitly authorized correction from chat. The saved dwt_01 JSON now parses and has leaflet counts 8/9/9, all is_unfolding=false, unfolding total 0, growth_shoot_count=3, truss_count=0. Original bytes backed up; dwt_02 and all photographs unchanged. Earlier invalid-file/save-pending statements in this document are historical and superseded. See CODEX_GROWTH_JSON_CORRECTION_2026-09-20.md for hashes, backup and validation.
