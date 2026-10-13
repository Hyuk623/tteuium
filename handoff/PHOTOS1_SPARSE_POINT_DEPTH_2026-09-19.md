# Photos-1 sparse physical-point depth and photo review

Latest generated result: `build/photos1_manual3d_20260919/edited_roundtrip03/index.html`.
Local running URL: `http://127.0.0.1:8825/edited_roundtrip03/index.html`.
Source session: `edit_session03`; explicit context: `manual_candidates.review07.json`.

## Actual status

One plant, 18 photographs. Three coarse/partial surface candidates remain (A1, D1, D2), containing 13 landmarks and 26 source observations. B1 has five explicitly named physical landmark candidates (b0, b1, b2, b4, b5) with ten observations; missing b3 is not filled and no B1 surface is generated. Total independently computed points: 18, with 36 observations. Eleven independently observed 2D regions remain, including B1. These counts overlap by identity and must not be added as unique leaves.

The review07 visual audit supersedes review06's A2/B1/B2 surface candidates. A2/B2 remain 2D because physical correspondence is unresolved; B1 retains point-only depth. Small leaves are preserved as actual leaf regions. All labels and coordinates are unreviewed, metric-unvalidated and unsuitable for PPFD. No whole-plant reconstruction claim.

## Changes

- `tools/rebuild_leaf_edit_session.py`: identical preview-to-original arithmetic order prevents floating-point reassociation from falsely marking unchanged points as superseded; this affected old A2 saved-point export in roundtrip01. Historical run01 is unchanged. Reports now distinguish computed physical-point count from actual surface availability.
- `tools/editor_point_review.py` and `tools/editor_point_scene.html`: interactive 3D physical-point display integrated with saved-label photo gallery. Selecting a point selects its first source photograph; all original point IDs, including gaps, remain intact. Coordinates are never averaged, completed or meshed here. Missing, conflicting or nonfinite XYZ are excluded from the scene while photo records remain available.
- Partial/sparse preparation in `tools/prepare_leaf_edit_session.py` is available with `--include-partial`; current edit_session03 exposes A1, D1, D2 and B1. Two-dimensional polygon vertices are not converted to physical matches.

## Validation

30 tests passed via:
`python -m pytest -q tools/tests/test_rebuild_leaf_edit_session.py tools/tests/test_editor_point_review.py tools/tests/test_manual_leaf_preview.py tools/tests/test_prepare_leaf_edit_session.py`

Actual input hashes checked, source copies byte-compared, 18 full-resolution labeled JPEGs counted, B1 missing b3 verified, all generated executable gallery scripts passed Node syntax checks. `edited_roundtrip03/verification.json` records counts and tool hashes. Browser verification: selecting B1/b4 displayed IMG_7913, five saved points, actual marker/corner IDs, board height and camera depth; landing page correctly reports five point depths without a leaf surface. The result uses the prepared seed backup, not the user's browser-edited backup. No DL execution, calibration promotion, gate relaxation, core/config/docs changes.

## Reproduce

`python -m tools.rebuild_leaf_edit_session --session build/photos1_manual3d_20260919/edit_session03 --backup build/photos1_manual3d_20260919/edit_session03/seed.backup.json --context build/photos1_manual3d_20260919/manual_candidates.review07.json --out build/photos1_manual3d_20260919/<new-unused-run>`

For actual user revisions, supply the explicitly exported editor backup instead of seed.backup.json. Never overwrite an existing result or browser edits.

## Remaining work

Whole-plant coverage, unresolved cross-view leaf matches and observed stem/petiole geometry remain incomplete. The current 3D scene shows only supported candidate points. Trial cameras still fail operational quality gates. Keep the user-authorized diagnostic workflow and these flags rather than demanding a reshoot or silently upgrading accuracy.


## Follow-up: source-image correspondence extension

Latest result is now `edited_roundtrip05` with `manual_candidates.review09.json` and `edit_session05`. Re-inspected actual source crops for A2, B2, C1 and basal E1. Added only A2 b0/b5, B2 b0, C1 b0, and E1 b0 as unmeshed physical-point candidates. Historical coordinates/IDs stay unchanged; selection used visible semantic features, not fitting residuals. No withdrawn surface was reactivated. C1 fold silhouettes and E1 curled side lobes remain excluded.

Authoritative output checks: 23 physical points, 46 observations across 10 of 18 photos; three existing partial/coarse surfaces and eleven independent 2D regions. Five identities have point-only depth: B1=5, A2=2, B2=1, C1=1, E1=1. Exact input-copy hashes and all 18 labeled-photo outputs checked. Per-photo observed coverage is recorded in `edited_roundtrip05/photo_coverage.csv`; count/limitations are in `verification.json`. Browser selection of E1/b0 linked to IMG_7917 and actual board evidence. All numerical depths remain unvalidated. No source-code change or new DL run in this follow-up; previous 30-test result belongs to the preceding code change, not a newly executed suite.

The whole-plant goal is still incomplete: eight input photos have no physical point observations; unconfirmed small-leaf/overlapping-region identities, leaf surfaces, stem/petiole structure and metric validation remain. These are evidence gaps, not justification to manufacture missing surfaces. User-reviewed labels have not been supplied or substituted.


## Follow-up: third-view observations, review10

Latest generated result: `edited_roundtrip06`. Unlike previous seed round trips, this run uses the explicit assistant-revised backup `third_view_review10/third_view_revised.backup.json` with the unchanged `edit_session05` source session and `manual_candidates.review09.json` context. To reproduce, supply that revised backup to the rebuild CLI. Regenerating from the seed would lose the new observations.

Added A1/b0 at [493,493] and A2/b0 at [511,678] in IMG_7918's 1500-pixel preview coordinates, scaled by the existing exact original-pixel transformation. Original crops and grid evidence are preserved under third_view_review10. The initial attempt incorrectly assigned adjacent blades and produced large residuals; it is retained as rejected historical evidence (`third_view_candidates.backup.json`, `review.json`), not used in the published result. Tracing the shared compound-leaf rachis across IMG_7918/7919 corrected the identity assignment; pixels were then visually localized. This feedback-assisted revision is not independent validation or human ground truth.

The revised A1/b0 and A2/b0 each use three views (7918,7919,7927). Maximum reprojection errors are 3.43 and 11.11 px; all pose/metric flags remain unvalidated. A2 still fails the configured point gate. Do not describe matching two/three-view heights as proof of accuracy. Three-view point depths are displayed separately from partial surfaces, whose boundary support still comes from the two complete boundary views.

Output checks: 23 distinct physical points, 48 observations across 11 photos, three partial surface candidates. Source backup bytes match. Browser selection of A1/b0 shows three source images and links to IMG_7918 with both observed points and actual detected marker IDs. `additional_view_comparison.csv` and `verification.json` preserve this comparison and its limits. No new source-code or DL changes. Whole-plant coverage and validated geometry remain incomplete.
