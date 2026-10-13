
## Revision B.2 (2026-10-05 23:10 KST, user decision) — B0 refuted the resolution hypothesis; reorder to B4 first

**B0 result (dwt_01, 268 accepted leaflets, held-out weights `full_lopo_dwt_01.pt`):** AP50 0.695 / 0.742 / 0.746 / 0.734 at 3024 / 1536 / 1024 / 512 px. Real photos stay **above the 0.59 gate at 512 px**. Resolution is not the cause, so **B2 as written is not expected to move C6 and is demoted** — do not spend a Kaggle render on it until the size gap below is closed. The B2 declaration and its 1280 px geometry stay recorded in `contract_amendments.json`; mark it `superseded_by: B4` rather than deleting it.

**What B0 actually exposed — leaflet pixel size, not image size.** At the same 512 px:

| | real (dwt_01) | synthetic (`_02` pilot) |
|---|---|---|
| median leaflet area | 463 px | 113–151 px |
| leaflets < 150 px | 16 of 268 (6 %) | 731 of 1468 (50 %) |
| recall in the < 150 px bin | 0.69 | 0.08 |

The detector handles small leaflets on real photos; it does not see the synthetic ones. The synthetic plant occupies far less of the frame than a real plant does, so every leaflet lands in a size regime that is rare in real photos. **C4 "passing" at 151 px is misleading: it passed because the C4 band is the real p10–p90, and 151 px sits on the p10 edge while the real median is 463 px.**

**New order: B1 (done) → B4 → B3 → B5; B2 only if B4 leaves a residual gap.**

### B4 (now the main step) — leaflet pixel size toward the real median
Declare in `contract_amendments.json` before rendering, as usual. Two separable causes; test them in this order and report C6 after each:

- **B4a — framing.** Measure what fraction of the frame the plant occupies in real rig photos vs in the `_02` renders (plant bounding box area / image area, median over views). If the synthetic plant is smaller in frame, fix the camera distance / sensor framing so the synthetic fraction matches the real median. This is a view/camera change, not a generator change, so it needs no new generator version and no new contour work.
- **B4b — leaflet scale in the generator.** If framing alone does not bring the median leaflet area near 463 px at 512, raise the leaflet scale (generator 0.4) so the **synthetic median leaflet area approaches the real median, not the real p10**. C1–C3 must stay inside their ranges; if raising leaflet size pushes C2 (envelope) or C3 out, report the conflict and stop rather than trading one gate for another.

Report for B4: median and p10/p50/p90 of synthetic visible leaflet area at 512 px beside the real values, the plant-in-frame fraction before and after, AP50/recall by size bin, and which of B4a/B4b produced the change.

### Also record
- `C4` should be read against the real **median**, not only the p10–p90 band. Add `C4_median_ratio = synthetic_median / real_median` as a reported statistic in the `_03` contract amendments (report-only, not a new gate — thresholds are not changed after seeing results).
- B1 is kept: AP50 0.1715 → 0.2105 and SAM median IoU 0.5505 → 0.6234 under the declared rule (GT 1468 → 1144). Apply the B1 rule in every later step and keep reporting both.

## Revision B.3 (2026-10-05 23:55 KST, user decision) — B4a changed little; the gap is appearance. New order: B6 → B7 → B5. B4b dropped.

**B4a outcome.** Framing fixed (plant-in-frame 0.054 → 0.113; real 0.116) and median leaflet area 151 → 280 px, yet AP50 moved only 0.211 → 0.218. **B4b (further leaflet enlargement) is dropped**: the large, nearly unoccluded synthetic leaflets — the ones geometrically closest to real — already fail at recall 0.40 where real photos reach 0.96, so size is not the binding constraint. Keep the B4a framing; record B4b as `dropped`, with this reason.

**Shape was measured, not assumed** (real = 1,163 accepted masks via `build/leaf_area_20261005_01/c0_accepted_mask_contours.json`; synthetic = 1,478 per-leaflet regions from the B4a `visible_mask.png` instance maps):

| statistic (p10 / p50 / p90) | real | synthetic |
|---|---|---|
| aspect (minAreaRect short/long) | 0.354 / 0.562 / 0.799 | 0.200 / 0.475 / 0.845 |
| solidity | 0.623 / 0.821 / 0.913 | 0.588 / 0.795 / 0.904 |

Medians and solidity agree, so occlusion and leaf arrangement do **not** explain C6. One real difference remains: the synthetic aspect p10 (0.200) sits well below the real p10 (0.354), i.e. the synthetic set has a tail of near-edge-on leaflets that real photos do not have. Secondary, to be quantified in B7, not assumed.

### New order, replacing B.2's: **B6 → B7 → B5**, then reassess.

**B6 — leaf brightness (do first; one generator parameter).** `addendum_b/real_camera_stats_1280.json` measures real leaf BGR median (99, 147, 125) ≈ sRGB mean **0.49** over 30 photos, while generator 0.2.0 uses `leaf_srgb_mean` **0.14–0.30**. The v2 "darker colour" change went the wrong way against this measurement and may itself have cost C6. Set the leaf albedo so rendered leaf pixels match the measured real distribution (match the median and report p10/p90), re-render the 5 pilot scenes, and report C6/C7 under both GT rules. Declare in `contract_amendments.json` first, as always. If C6 moves materially, say so before going further.

**B7 — leaflet surface angle (diagnostic, report-only, no re-render).** Nothing in the pipeline has ever computed the angle between a leaflet's surface and the viewing direction; `leaflet_index.json` carries only length and contour index, and `visible_fraction` measures occlusion alone. From the scene meshes and each view's camera, compute per leaflet-view the angle between the leaflet surface normal and the camera axis, then report: the synthetic angle distribution; recall as a function of that angle; and how much of the synthetic aspect p10 tail is explained by near-edge-on leaflets. Real photos have no 3D, so compare through the aspect/solidity proxy above rather than claiming a real angle distribution. This step does not move C6 by itself — it decides whether a later geometry step is needed.

**B5 — leaf surface texture (vein, serration, rugosity).** **Not blocked on the Addendum C flattened photos.** The existing rig photos are 3024 px and show the leaf surface directly; crop vein/serration/rugosity patches from reviewed-mask regions there, tag `source='rig_photo_crop'`, and build the albedo/normal maps from them. Flattened photos, when they arrive, replace these crops rather than gate them. Re-render and report as usual.

Stop rule unchanged: first step reaching C6 ≥ 0.59 and C7 ≥ 0.72 stops and reports before the 100-scene run.
