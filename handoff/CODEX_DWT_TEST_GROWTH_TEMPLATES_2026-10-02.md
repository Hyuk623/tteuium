# Existing growth JSON templates for dwt_test

The user requests uploading the previously used manual growth JSON format directly to the existing Drive T1, T2 and T3 folders. Reuse the structure in `tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json`, not that plant's observed values.

Create editable templates under a fresh `build/` output directory. Preserve compound leaf entries, unfolding counts, growth-shoot counts, truss counts and the Korean input guide. Use folder identifiers T1/T2/T3 without mapping them to existing dwt_01/02/03 plants. Capture dates and counts remain null; compound_leaves remains an empty, unfilled array. No photo-based count inference or ground-truth claim. Add guides clarifying unknown versus measured zero and how to add compound leaves.

Validate strict JSON, schema keys and empty biological fields. Upload one new JSON to each existing folder without changing photos, Colab inputs or existing records. Verify cloud filenames, parent folders and uploaded content. No training, inference or notebook execution.

Completed: created and validated T1_growth.json, T2_growth.json and T3_growth.json in build/dwt_test_growth_templates_20261002_204605; uploaded to the corresponding Drive folders and read back all three documents to verify identity, parents and unfilled counts/date. These are blank human-entry templates, not completed ground truth. No photos or experimental jobs changed.

User correction: delete only the three blank Drive templates uploaded above, then upload the existing dwt_t1.json, dwt_t2.json and dwt_t3.json from tomato_photos_by_view_/dwt_test to their corresponding T1/T2/T3 folders, preserving original filenames and bytes. Do not modify human records or any photos. This supersedes the blank-template delivery. Verify uploaded content and removal of the earlier Drive IDs.

User explicitly corrected the preservation instruction: fix T2/T3 plant IDs and copied capture date before upload. Applied dwt_t2/dwt_t3 and 2026-10-02 (same capture batch as T1); backed up all three source JSONs under build\dwt_test_json_replace_20261002_210617. Other observations and counts preserved.

Replacement completed: deleted the exact three earlier blank-template Drive IDs and uploaded corrected source files under their original dwt_t1/2/3.json names to T1/T2/T3. All three cloud readbacks match local bytes and destination parents. T1 observations preserved; T2/T3 observation counts still unfilled.
