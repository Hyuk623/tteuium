# Claude handoff on assistant selected leaf vein correspondence candidates

Date: 2026-10-02. Author: Codex. Recipient: Claude Code.

## Delivered result

The user asked Codex to find points directly, then document how they were found. Seven cross-view point hypotheses were saved through the existing `Workflow.save` interface: four for annotations 127/167 (`xv_004`) and three for 99/121 (`xv_001`). These are seven pairs, comprising fourteen 2D observations, not fourteen physical landmarks. All are **pending**, with `human_confirmed=false`. There are zero newly confirmed correspondences and no new 3D points or surfaces from this search.

This work reused the existing application and classical image-processing functions. No new detector training, deep-learning inference, SIFT matching, pose fitting, camera replacement or quality-gate changes were performed. The exact original-pixel coordinates and uncertainties are available below and in the accompanying CSV/JSON.

## How the points were found

1. **Start from existing cross-view leaflet groups.** Open the original RGB crops and existing accepted-export masks for 127/167. Inspect the wider photos for context. Additional linked views 99/121/172 and 88/113/181 were visually considered; 99/121 was retained as a supplementary comparison. This was not a blind search proving a new biological identity. Group labels were reused from the frozen context; per-observation identity flags were not rewritten.
2. **Inspect visible anatomy before ranking points.** Compare the likely attachment direction, distal silhouette, folds and main visible vein route. Annotation 127 presents a narrow folded/oblique appearance, whereas 167 presents a broader dark surface. Similar-looking ridges may be folds or illumination, and the view difference prevents confident matching. Suspected tips were entered separately from graph junctions. Neither an image's left/right ordering nor a bbox corner was treated as a physical correspondence.
3. **Reuse the existing bright-ridge map.** `Workflow.extract` calls `midrib_review.propose` with `channel=original_l`, `polarity=bright`, `sigma_px=2`. In the current implementation, `original_l` is the original RGB crop converted to Lab L, not linear-RGB luminance or G/(R+G+B). Gaussian-derivative ridge evidence is normalized at the 99th percentile of the valid interior. Pixels near mask boundaries, holes and brightness-limit pixels are excluded using the full support radius `ceil(4*sigma)`, which is 8 pixels here. Images are not zero-filled before filtering. This pass did not apply SG, gamma, CLAHE or an exposure sweep.
4. **Turn ridges into graph candidates.** The null threshold selects Otsu within the valid response region. Zhang-Suen thinning yields a skeleton. Adjacent branching pixels are grouped; the representative is an actual skeleton pixel near the group's mean. Endpoints and junctions remain distinct. Disconnected lines and holes are not automatically connected. These are image-structure candidates, not anatomically verified veins.
5. **Rank cross-view junction hypotheses.** The existing descriptor uses a 17x17 original-image grayscale patch, resized to 9x9 and normalized by its mean and standard deviation. Four quarter-turn rotations and their reflected counterparts are compared. Ranking cost is the sum of patch distance, node-degree difference, neighbouring-degree difference and branch-order signature distance. Lower cost ranks first; it is not a confidence probability. The top three targets per source are retained. A target appearing for multiple sources is explicitly ambiguous. This is a local descriptor and graph heuristic, not full perspective or elastic registration.
6. **Select a small set visually and inspect geometry as a diagnostic.** Original RGB and numbered graph overlays were compared together. Existing measured cameras supplied epipolar distances as a secondary check. All selected interior candidates retain shared-target ambiguity. Small distance did not establish correspondence: the two 99/121 candidates have distances below 1 pixel, but the cameras still fail the existing pose gate. The 127/167 third interior candidate has degree/topology disagreement and a relatively high cost; retain it only as a weak alternative pending review, never as an anchor selected solely for geometric proximity.
7. **Preserve original coordinates and explicit uncertainty.** Crop coordinates were converted by adding the stored x/y offsets, without resizing or estimating depth. `Workflow.check_xy` checked every observation against the existing visible mask. The preliminary 121 tip click at crop (108,296) was outside that mask; after visual reinspection the adjacent boundary pixel (109,296) was chosen. This was one explicitly recorded correction, not general automatic snapping. Tip identity is still uncertain because a folded silhouette need not be the same anatomical boundary point in both views.
8. **Save as assistant proposals.** Use `state=pending`, assistant source metadata, candidate node IDs, match evidence and explanatory notes. Interior IDs start `AI_20261002_V`; tip hypotheses use `AI_20261002_TIP` and `boundary_reviewed=false`. Point IDs are scoped by physical leaflet ID; identical suffixes in xv_001 and xv_004 must not be merged. Existing same-group context was reused without claiming that these point matches were human-reviewed.

## Exact saved hypotheses

The full ID prefix is `AI_20261002_`. All coordinates are original 3024x3024 image pixels. Costs and distances are printed rounded here; JSON preserves full precision. No rounding changed calculations.

| Pair | ID suffix | Left original pixel | Right original pixel | Graph nodes | Cost (lower first) | Diagnostic epipolar distance (px) |
|---|---|---|---|---|---:|---:|
| 127/167 | V01 | [1985, 1550] | [1200, 1839] | n0002 / n0037 | 0.399950 | 10.323040 |
| 127/167 | V02 | [1967, 1576] | [1160, 1800] | n0004 / n0017 | 0.684710 | 6.368244 |
| 127/167 | V03 | [1997, 1590] | [1162, 1852] | n0006 / n0046 | 2.351260 | 4.884077 |
| 127/167 | TIP | [1981, 1686] | [1119, 1826] | visual tip hypothesis | n/a | not calculated |
| 99/121 | V01 | [1855, 1394] | [1907, 1593] | n0007 / n0022 | 0.966525 | 0.711879 |
| 99/121 | V02 | [1844, 1404] | [1916, 1604] | n0008 / n0026 | 1.069858 | 0.398948 |
| 99/121 | TIP | [1878, 1510] | [1865, 1705] | visual tip hypothesis | n/a | not calculated |

All five interior pairs have `ambiguous_target=true`. TIP is a visual hypothesis with no graph ranking or epipolar-distance assessment in this delivery. Each pair has only one tentative boundary point, so even accepting all listed points would not satisfy the minimum three noncollinear boundary-point requirement for a partial surface.

## Files and integration

Run root: `build/leaf_surface_pilot_20261001/`.

- `assistant_search_20261002/selected_candidates.json`: full review records, observations, hashes, provenance and limitations.
- `assistant_search_20261002/selected_landmarks.csv`: fourteen original-pixel observations.
- `assistant_search_20261002/selected_landmark_hypotheses.png`: clean side-by-side original RGB comparison; question marks denote unconfirmed proposals.
- `assistant_search_20261002/graph_127.json`, `graph_167.json`, `graph_99.json`, `graph_121.json`: extracted graph candidates.
- `assistant_search_20261002/pair_sample_094_sample_117.json` and `pair_sample_080_sample_089.json`: ranking/context snapshots from before final review saving; their saved-review fields can therefore be older than the latest review records.
- `assistant_search_20261002/validation.json`: readback, coordinate/mask checks and source-hash checks.
- `landmarks/reviews/`: authoritative append-only review revisions used by the existing web application.

Source functions: `tools/vein_correspondence.py` (`extract`, `pair`, `check_xy`, `save`), `tools/vein_landmarks.py` (`graph`, `descriptor`, `propose_matches`), `tools/midrib_review.py` (`propose`). No source code was changed for this selection task.

If the existing service is not running, start it from the project root:

```powershell
python -m tools.leaf_preprocess_lab serve --run build/leaf_surface_pilot_20261001 --port 8834
```

Open `http://127.0.0.1:8834/?annotation=127`, choose comparison annotation 167, and open the two photographs. The saved pending IDs should load from the existing review storage. Repeat with annotation 99 and comparison 121. File/API readback was verified. The app page opened, but the browser-control tab binding disappeared before the final saved-point UI check; this delivery does not claim successful visual verification of those loaded rows.

## Verification and remaining work

Both latest review signatures match the current context. All fourteen coordinate observations lie inside their existing masks. Selected source photos, source masks, accepted-export manifests and local crop/mask hashes match their stored provenance. No human reference or original image was modified. No correction-time or accuracy number was inferred from the assistant's work duration.

Continue in the same web review flow: compare source RGB against the ridge overlay, confirm or reject anatomical correspondence separately from leaflet identity, and explicitly save any human decisions. Do not bulk-accept these seven proposals or relabel their source as human. Use a held-out third view for xv_001 only after independent point identification there. Candidate IDs are graph-revision-specific; do not blindly reuse node indices after mask or threshold changes.

For surfaces, obtain additional genuinely corresponding boundary points and reviewed internal points. Preserve original cameras and existing triangulation checks. Only confirmed points enter the current reconstruction bridge. Preserve earlier runs and recompute derived results after review changes instead of overwriting history. Existing completion-audit statements about current runs predate these new review revisions.

Current results remain `validated_metric=false`, `suitable_for_ppfd=false`. Independent physical-point matching accuracy, 3D accuracy, curvature, leaf area and PPFD suitability are unavailable. The tangible result is a small, traceable assistant shortlist for review, not proven matching or a completed leaf surface.
