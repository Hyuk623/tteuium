# Implementation brief: reviewed vein landmarks and 3D bridge

User authorized the 2026-09-30 plan: automatic vein-junction candidates, human leaflet/point confirmation, then existing triangulation. Extend the current Python lab, initially all 268 accepted dwt_01 observations. Preserve frozen masks/photos, source hashes and old outputs. No training, learned inference, pose estimation or GitHub push.

Implement Otsu/manual threshold skeleton graphs, connected junction clusters with on-skeleton representatives, branch topology and local image descriptors, sigma 1/2/3 comparison, top-three point proposals, and explicit one-to-many conflicts. Reuse human cross-view decisions with same/different/conflict handling. Add two-image review, manual point movement/deletion/undo, independent identity and point confirmation, immutable saves and stale-input checks. Integrate the original-pixel point contract and tools.leaf_light.reconstruction.triangulate; retain capture quality gates, with strict and explicitly diagnostic modes. No complete surface from vein-only samples; existing boundary observations remain required for the surface engine.

Code stays under tools/ and tools/tests/. Source masks are leaf references, not vein ground truth. Validate synthetic branching/holes/coordinate mapping, matching ambiguity, negative identity constraints, confirmed-only exports, source/config staleness, original triangulation gates and actual web controls. Write actual coverage/results and remaining human review needs here on completion.


## Completion record — 2026-10-01 Asia/Seoul

Implemented in the existing preprocessing lab, with no trained-model execution. The review-to-triangulation workflow is available at http://127.0.0.1:8834/ (PID 11144 at delivery). Existing 8832/8833 services and their files were left intact.

### Delivered components

- `tools/vein_landmarks.py`: zero-padded Zhang–Suen skeletonization (implemented locally because scikit-image is absent), Otsu/manual threshold, connected junction-pixel groups with representatives on the actual skeleton, traced graph edges, endpoint/near-boundary flags, cyclic neighbouring-branch signatures. Disconnected lines and holes are not connected. A closed loop without junctions supplies no junction match.
- Local original-photo intensity patches are normalized and compared under rotations and reflection. These are grayscale descriptors derived from original RGB, not a learned Re-ID embedding. Node degree, neighbouring degrees and cyclic branch order are soft ranking terms. Angles/lengths are not hard matching gates. Top three candidates per reference junction are retained, including shared-target ambiguity. Scores are uncalibrated rankings, never correctness probabilities.
- `tools/vein_correspondence.py`: frozen human identity/camera context, distinct photo observations/physical leaflet IDs/physical point IDs, separate identity and point review, immutable proposal and review snapshots, negative identity constraints, original-pixel validation, distortion-aware diagnostic epipolar curves, and existing `tools.leaf_light.reconstruction.triangulate` reuse. Strict and diagnostic modes preserve the original pose/reprojection/parallax gates. An unobserved coordinate can remain null in a pending/rejected record; confirmed records require two observations.
- `tools/vein_review.js`, integrated into the existing HTML/server: side-by-side original/evidence crops, sigma 1/2/3 overlay, zoom, candidate lines, independent leaflet confirmation, point selection/movement, confirm/pending/reject/delete/undo/restore, explicit save and strict/diagnostic calculation. Shift-click uses the clicked original-pixel position without snapping. Existing physical point IDs can be reused from other reviewed pairs. A click or pending candidate is never automatically accepted.
- `tools/vein_surface_bridge.py`: optional adapter to the existing surface engine. Requires separately human-reviewed boundary-point and visible-contour CSVs with explicit matching leaflet IDs and reviewer attestation. Interior point CSVs intentionally have no fabricated boundary count. The adapter obtains this count from the supplied boundary set, preserves its organ ID, rejects ID collisions, and checks whole projected triangle footprints against at least two visible masks (including holes). Every face remains interpolation; `validated_metric=false`, `suitable_for_ppfd=false`.

### Actual dataset run

- Dataset: `build/leaf_veins_dwt01_20260930`, 268 photo-level observations, 14 photographs, dwt_01 only. These are not 268 biological leaves.
- Final graph artifact: `build/leaf_veins_dwt01_20260930/landmarks/graphs_1790781336321775600/`.
- Gaussian sigma 2, original Lab brightness, bright-ridge evidence; valid-mask interior; Otsu per observation.
- 7,006 junction candidates across 256 observations. Eleven further observations have endpoints/lines but no junctions; annotation 100 has no usable ridge evidence. All 268 observations have an explicit record. No candidate is an anatomical ground-truth label.
- Final graph run: 33.5293 seconds on local CPU, with tests running concurrently. Runtime is an engineering measurement, not a throughput guarantee.
- Current context SHA256: `a042e4a9372acf4d9a967dfe431d014b591ee7491d5cf913174827ce1c4c3628`.
- Final source verification: 317 frozen input hashes checked, including the original dataset sources and human-decision/camera references. No original photo, mask, label, calibration or weight was changed.
- Seven imported same-leaflet groups. Six pairwise different constraints, seven rejected multi-view sets; three excluded observations. A rejected three-view extension means “not all three are the same”, NOT that every constituent pair is different. The confirmed 127–167 pair remains allowed; assigning the rejected third observation into the same physical group is blocked.
- Actual 127–167 pilot: existing identity `xv_004`; 15/64 junction candidates respectively, thresholds 0.290196/0.309804. Both poses are available but fail the existing quality gate, so epipolar evidence is diagnostic. Real browser checks covered paired rendering, original-pixel selection, candidate line, sigma overlays, pending/delete/undo. No real point was saved as human-confirmed by Codex.
- Early ranking timing in `landmarks/ranking_pilot.json` used the pre-vectorized scorer (39.54 s for 251 possible comparison observations). Its first entry is the already human-linked 167 because confirmed identities are prioritized; this is NOT a same-leaflet accuracy result. The scorer was subsequently vectorized and tested. Do not mix that timing with the final extraction runtime.
- Earlier `landmarks/graphs` and other `graphs_*` folders are preserved development snapshots. Use the final folder above and its manifest; do not aggregate versions.

### Validation

54 tests passed in 11.15 s:

```powershell
python -m pytest tools/tests/test_vein_landmarks.py tools/tests/test_leaf_preprocess_lab.py tools/tests/test_midrib_review.py tools/tests/test_leaf_vein_batch.py -q
```

Includes synthetic Y junctions and original-coordinate offsets; rotation, intensity transformation and reflected patches; ambiguous repeated patterns; hole/gap preservation; absent evidence; strict-versus-diagnostic triangulation; original reprojection/parallax rejection; absent poses; point movement followed by new XYZ; source/settings staleness; per-pair and cross-pair many-to-one rejection; negative/transitive identity constraints; rejected triples preserving valid pairs; unobserved points; authenticated HTTP routes; separately reviewed boundaries producing four interpolated synthetic triangles without mutating inputs. Node syntax check and CLI help also passed.

Saved proposals contain graph coordinates, source observations, scoring terms and code hashes. Reviews record explicit identity state, point states, nullable observation coordinates, candidate-node provenance, immutable parent revision and UI edit history. Exports list contributing review hashes and per-photo reprojections. Previous exports remain on disk and are marked stale after point/identity/settings changes; source-mask, context or external identity-decision changes fail closed until a refreshed context is prepared. Source-code changes require a server restart. A refreshed context archives the previous one.

### Run / use

```powershell
# Only when a new context is required; --refresh-context archives the old one.
python -m tools.vein_correspondence prepare --run build/leaf_veins_dwt01_20260930 --refresh-context
python -m tools.vein_correspondence extract --run build/leaf_veins_dwt01_20260930
python -m tools.leaf_preprocess_lab serve --run build/leaf_veins_dwt01_20260930 --port 8834
```

In the existing page select a reference observation, open the “leaf-vein junction / other-view connection” section, select a comparison observation or rank suggestions, and open the pair. Inspect original and ridge views. Confirm the physical leaflet separately, select the same visible physical feature in both views, and confirm/pending/reject the point. Save explicitly, then request strict or diagnostic 3D calculation. Reuse the same physical point ID across additional views; a conflicting coordinate for the same photo/point is reported rather than silently averaged. Unseen features stay unobserved. Changing a point requires confirming/updating that row and saving before recalculation.

Derived artifacts are under `landmarks/proposals/`, `reviews/`, `current/`, and `exports/`. API routes extend the existing local-token protected server: `/api/vein/{candidates,pair,epiline,save,export,status}`. Existing preprocessing and midrib routes remain compatible. No separate annotation app was created.

For a later independently reviewed boundary set:

```powershell
python -m tools.vein_surface_bridge --run build/leaf_veins_dwt01_20260930 --export build/leaf_veins_dwt01_20260930/landmarks/exports/<run_id> --boundaries build/<reviewed>/points.csv --contours build/<reviewed>/contours.csv --reviewed-by <human_reviewer> --out build/<fresh_partial_surface_run>
```

This optional adapter is tested synthetically only. There is currently no new human-confirmed real vein-point set or real reconstructed leaf surface from this feature. Independent vein accuracy, leaflet matching accuracy, point correspondence accuracy, 3D curvature accuracy and human correction time remain unavailable. Review records contain elapsed UI session time; that includes possible idle time and is not automatically a correction-time measurement. Leaflet identity verdicts and point verdicts must be analyzed separately against independent review references.

### Claude continuation

Use this implementation to collect real reviewed correspondences, starting with existing same-leaflet pairs. Review false junctions caused by wrinkles, shadows and texture; a repeatable sigma response is still only evidence. No complete plant reconstruction or PPFD-readiness claim is justified. All pipeline ownership boundaries remain unchanged.


## Completion audit follow-up — 2026-10-01

The prior turn made verified implementation progress. A requirement-by-requirement audit found a usability gap: a newly confirmed (previously unlinked) leaflet pair gets a pair-local suggested ID in another pair, and point-ID suggestions can include stale reviews. Extend ID suggestions using current human-reviewed links without automatically confirming a new pair. Preserve separate point/leaflet confirmation, reject conflicting ID ownership, and add current review-count/explicit correction-time summaries. Validate these cases, the existing end-to-end HTTP save/export contract, and source/decision invalidation before closing the implementation goal. No new human anatomy labels or model execution are authorized by this audit.


## Completion audit results — 2026-10-01

The implementation audit is complete. Newly reviewed physical leaflet IDs now carry across additional photo pairs as suggestions, without confirming a new pair automatically. Existing and locally reviewed ID ownership conflicts are rejected. Point-ID suggestions exclude stale point reviews; changing extraction settings does not erase a separately confirmed leaflet identity. An optional human-entered correction-time field is distinct from idle-inclusive UI elapsed time. The Korean status panel separately reports leaflet-pair verdicts, point-pair verdicts, stale pairs and explicitly entered correction time. Independent matching accuracies remain unavailable.

### Requirement coverage

| Requirement | Implementation and verification |
|---|---|
| Junction evidence and provenance | Skeleton graph, on-skeleton representative, original pixels, Otsu/manual threshold, sigma 1/2/3 overlays; synthetic Y, holes, rotations and brightness tests. Existing 268-observation extraction is preserved. |
| Cross-view proposals | Existing confirmed links prioritized; branch connectivity and original-image patch evidence; reflection, top-three candidates and repeated-target conflicts. Soft geometry remains diagnostic when poses fail quality gates. |
| Separate human decisions | Leaflet identity and point identity remain independent. Confirm/pending/reject, move/delete/undo, explicit save and unobserved coordinates use immutable review records. New ID reuse and ownership conflicts are covered by tests. |
| Existing 3D connection | Authenticated HTTP fixture verifies pair -> save -> diagnostic triangulation -> point edit -> stale export. Existing strict/diagnostic gates remain intact. The optional partial-surface adapter requires independently reviewed boundaries and labels faces as interpolation. |
| Preservation and limitations | All 317 frozen source hashes verified after the audit. No source photo, mask, calibration or weight changed; no new model execution. Real point matches were not fabricated. |

Validation: **56 tests passed in 8.71 seconds** using the four test modules in the earlier command. Node syntax validation passed after the final Korean summary rendering change. Existing server 8834 was restarted with the updated code (PID 32060 at verification); other servers were preserved. Browser verification reopened actual labels 127/167, showed the existing identity and failed-pose diagnostic notice, confirmed the correction-time field and Korean summary, and returned no browser console errors. Source context SHA256 remains `a042e4a9372acf4d9a967dfe431d014b591ee7491d5cf913174827ce1c4c3628`.

Current local review summary: zero newly saved vein-review pairs, zero confirmed real vein-point pairs, no reported correction time and no new real 3D export. The seven imported same-leaflet groups are prior identity evidence and are not counted as new vein-review records. Software integration is complete; independent human anatomical review and real reconstruction evaluation remain subsequent data work. The numerical graph algorithm was unchanged in this audit, so the previously recorded 7,006-candidate extraction was not rerun or overwritten. The final code revision is recorded by new proposal/export provenance when used.


## Photo navigation continuation — 2026-10-01

The user authorized board-guided whole-photo navigation after supplying the six-photo PDF, then requested an English handoff. See `CLAUDE_BOARD_VIEW_VEIN_NAVIGATION_2026-10-01.md` for implemented controls, API contracts, actual 127/167 browser checks, 59 passing tests, preserved source hashes and geometry limitations. This extends the existing 8834 lab; it does not establish new human correspondences or improve pose accuracy.
