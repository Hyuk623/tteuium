# Addendum G.2 — pre-render note: a third confound the declaration does not cover (2026-10-08)

Written **before the Kaggle render**, from the generated geometry only, so that it cannot be a post-hoc
explanation of whatever AP50 comes back. All three cells are generated: 15 scenes, 180 views each,
`render 0.0` in every `generate.log`.

## 1. G2-0 and G2-a are geometrically identical — verified, not assumed

Their `realism_prelim.csv` match to every digit:

| | G2-0 | G2-a | G2-b |
|---|---|---|---|
| C1 median height (mm) | 69.1544544226195 | 69.1544544226195 | 70.59985479094604 |
| C2 median envelope (cm²) | 35.78789630085 | 35.78789630085 | 35.6449872929 |
| C3 median leaflets/photo | 26.0 | 26.0 | 26.0 |
| C4 median visible leaflet area (px) | 310.5 | 310.5 | **261.0** |
| C5 median occlusion fraction | 0.36413043478260865 | 0.36413043478260865 | **0.34430817409540815** |
| fully hidden leaflet-views | 367 | 367 | **331** |

So the A1+A2 fixes are appearance-only, as intended: **any C6 difference between G2-0 and G2-a is appearance, with
geometry held exactly fixed.** That is a clean contrast and needs no caveat. (All of C1–C4 pass in all three cells;
C6/C7 are `pending` on the render.)

## 2. The confound: pool D changes leaflet SIZE, not only shape

G2-b's median visible leaflet area is **261.0 px vs 310.5 px, −16 %**, and its occlusion is *lower* (0.344 vs
0.364) with *fewer* fully hidden leaflet-views (331 vs 367). The blades are smaller in projection, not merely
differently shaped.

This matters because I.3 measured, on the 1281 real dwt_01–04 candidates, that detection and acceptance collapse
with area and with nothing else: acceptance 0.57 in the smallest area decile (<126 px at 512 px), 0.83 in the
second, 0.91–0.99 above, and **flat in solidity (0.86–0.96) and aspect (0.86–0.94)**. The scoring code already has
a `recall_lt150` bucket for exactly this boundary.

**So pool D can lower C6 through the size channel alone, with its shape being more real, not less.** The
declaration's falsification test (G.2.3) only asks whether the rendered `norm_perimeter` p50 moves toward the real
2.63. That test can pass while AP50 falls, and the fall would then be read as the pool change "not working" when
the cause is that smaller blades are harder to detect.

## 3. Declared reading rule — fixed now, before any AP50 is seen

When the render is evaluated, report for each cell the AP50 **and** `recall_lt150` / `recall_150_500` /
`recall_500_1500` / `recall_gt1500` side by side, then read G2-b vs G2-a as follows:

- **(a)** `norm_perimeter` p50 moves toward real **and** AP50 rises → the Addendum G pool explanation holds. No
  size caveat needed.
- **(b)** `norm_perimeter` p50 moves toward real **and** AP50 falls, **with the fall concentrated in the small-area
  buckets** (`recall_lt150` and `recall_150_500` drop while the two large buckets hold within the I.1 noise floor,
  0.029 median at n = 5, and 15 scenes here) → **the pool's shape is better and its size is the problem.** Report
  it that way. The follow-up is a declared `leaflet_length_mm` / scale cell, **not** a retreat to the old 195-contour
  pool and **not** a roll/bend retune (which G.2.3 already forbids inside this step).
- **(c)** `norm_perimeter` p50 does **not** move toward real → the Addendum G explanation is wrong, exactly as
  G.2.3 says, whatever AP50 does. Say so.
- **(d)** AP50 falls with the drop spread evenly across area buckets → not a size effect; the pool change is simply
  worse. Report it as such.

**Do not choose among (a)–(d) after seeing AP50 by picking whichever reading is kinder.** The bucket pattern decides,
and the thresholds above are fixed as of this file.

## 4. What this note does not claim

- It does not predict which of (a)–(d) will happen. The size drop is measured; its effect on AP50 is not.
- −16 % in the median says nothing about the tail. The number that matters for (b) is the share of leaflet-views
  that cross below ~126–150 px, which needs the per-leaflet visible areas, not the median. **Compute that share
  per cell when the render is finalized** and put it in the report next to the bucket recalls.
- I.3's acceptance curve is about the real SAM review set, not about detector AP50 on synthetic images. The two
  are different measurements on different data; the shared mechanism (small masks are hard) is an inference, which
  is why it is written as a reading rule rather than a prediction.
- Nothing here changes any configuration, the pool, the GT rule, the gate, or `leaflet_roll_deg`.
