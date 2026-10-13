# Geometric check of Codex's assistant landmark hypotheses (Claude, 2026-10-02)

Input: `CLAUDE_ASSISTANT_LANDMARK_SEARCH_METHOD_2026-10-02.md` (7 pending pairs: xv_004 127/167 V01-V03+TIP, xv_001 99/121 V01-V02+TIP).
Output: `build/landmark_hypothesis_check_20261002/` (`check.py`, `diagnostics.json`, `xv001_heldout_172.png`, `ui_127_167_pending_rows.jpg`).
Read-only: no review, mask, camera, gate or tools/ file changed; nothing confirmed.

## UI readback (the step Codex could not finish)

Live 8834 server: 127 + comparison 167 lists `AI_20261002_V01/V02/V03/TIP · 보류`, leaflet ID xv_004; 99 + 121 lists V01/V02/TIP, xv_001.
Quirk: after choosing the comparison photo, the first click on "두 사진 열기" sometimes does nothing; a second click opens the pair.

## Geometry (original cameras; rescued session has identical poses for photos 24/25/28)

Board reprojection RMS of photos 24/25/28 is 8.0-8.6 px, so every epipolar distance below about 16 px (0.4-15.5 px here) is inside pose noise.
The epipolar line of each interior point crosses 73-194 px of the other view's mask within 8 px, so the epipolar check leaves the match
almost unconstrained along the leaf. Small epipolar distance is not support for these pairs.

Held-out view for xv_001: triangulate from 99/121, project into 172 (photo 28, same leaflet group), 300 draws with 8 px noise on both clicks:

| Point | Distance to 172 visible mask | Share of noisy draws inside mask |
|---|---:|---:|
| V01 | 8.9 px | 0.20 |
| V02 | 50.0 px | 0.00 |
| TIP | 21.4 px | 0.00 |

All three land at the lower-left end of the 172 leaflet, so the leaflet region is consistent, but V02 and TIP are not supported at point level
(or are occluded in 172 - the mask is the visible part only). For the TIP hypotheses the epipolar line misses the other view's mask by more than 8 px
(extent 0 px in the right view for both pairs). xv_004 has no third identity-linked view, so its points have no independent check.

## Consequences

- Nothing here can confirm a point; a person still decides. V01 (xv_001) is the only hypothesis the held-out view does not contradict.
- Even with all seven accepted, each pair has one boundary point; the surface needs >= 3 noncollinear boundary points, so no partial surface is possible yet.
- Pose noise (~8 px) is the limit on any geometric screening; the pilot's pose gate (1.0 px) fails for every photo, not only this pair.
- The per-leaf surface track needs per-point human review, which conflicts with the 10-01 goal (whole-plant area + PPFD/DLI, minimal review).
  The whole-plant S8 path does not depend on it. Whether to continue this track is the user's call.
