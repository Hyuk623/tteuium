# Authorized dwt_01 growth record correction

The user explicitly requests updating the saved JSON from the confirmed chat values. Target: tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json. Before editing, preserve an exact byte backup under build/ and record hashes. Apply L01/L02/L03 leaflet counts 8/9/9, all is_unfolding=false, compound_leaf_count=3, unfolding_compound_leaf_count=0, growth_shoot_count=3, truss_count=0, notes="". Preserve plant/date, guides and unrelated fields. Do not modify dwt_02, photographs, mapping, labels or calibration. Validate strict JSON, unique leaf IDs and count consistency afterward. Record actual outcomes below.

## Completed at 19:19 KST

- Original byte backup: `build/growth_json_correction_20260920/191908953/dwt_01_260920.before.json`.
- Before SHA-256: `31f75ada8602fd7c6730b44fa79c64f9933b4955affae5ce21e847e9651e9756`.
- Corrected file SHA-256: `dc2d3507597d672188c819e76949e4ad94b24523bcbb2462a2295f554ad0af0f`.
- Changed only the three numeric leaflet tokens, the unfolding total, and the added growth_shoot_count. All other text/fields were preserved by a targeted patch.
- Strict JSON parsing, unique IDs, compound-leaf entry count and unfolding-count consistency pass for both plants. All 36 image hashes still match their mapping. dwt_02 hash remains `a0a5ed73b78fc5800a50eb5bc697d647f4bb4ed1723f22c56e3376aea0a2e72c`.
- Audit: `build/photo_handoff_review_20260920/audit.json` (2026-09-20 19:19:23 KST).

Earlier handoff statements that dwt_01 is invalid or waiting for save/sync are superseded. This corrects the user's manual record; it does not independently verify counts from photographs or improve geometric calibration.
