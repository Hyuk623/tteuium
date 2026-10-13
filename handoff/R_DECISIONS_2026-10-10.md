# Decisions for Claude Code — N/O records + Prompt R.1 (2026-10-10)

Read with handoff/R_SESSION_STATE_2026-10-10.md. Numbers below are copied from
build/synthetic_dwarf_tomato_20261008_07/NO_analysis.json; re-check them while writing.

## 1. Write the N/O records now — verdicts exactly as pre-declared
- N-delight (specular de-light): C6 0.2807 vs G2-a 0.2752, delta +0.0055 [-0.0063, 0.0073] -> within noise.
  Geometry identical to G2-a (verified). Specular highlights are NOT a C6 cause. Close N.
- O-mature (snapshot age + compound cap): realism outcomes FAILED their declared bands:
  - rank ratio p50 1.859 (G2-a 1.731; band 1.0-1.2) -> declared reading "ratio >= 1.6: age/cap are not
    what sets the taper; report, no second change".
  - lt150 GT share 0.1634 (band <= 0.15) -> not passed.
  - C6 0.3089, delta vs G2-a +0.0337 [-0.0166, 0.0877] -> within noise, as pre-committed (no gain claimed).
  Record O as "realism correction not achieved". Do NOT call it accepted-as-realistic.
- Post-hoc observation (label it POST-HOC, not a result): ratio by drawn cap — cap 6: 1.351 (n=6),
  cap 7: 1.704 (n=2), cap 8: 2.165 (n=7). Real dwt plants carry ~4-5 compounds; O draws 6-8/plant.
  This is a lead for a future DECLARED cell (lower cap matching real compound counts), nothing more.
- C6 factor queue after this: N dead, O no gain -> P (curl) next, then A3 chroma, as already ordered.

## 2. R.1 may proceed on the O-mature config (user decision)
The R prerequisite was "O-or-later". O did not pass its realism bands, but R uses compound-level boxes and
camera-relative direction labels, which do not depend on the rank-size taper; and the pre-registered R.5
rule (a synthetic-including model ships only if it beats real-only on the REAL held-out set) is the actual
protection. Proceed with O config sha a3bd428c..., and write this caveat into R_contract.json as an
amendment: "generator = O-mature; O realism bands not met (rank ratio 1.859, lt150 0.163); compounds per
plant 6-8 vs real ~4-5 — box-count distribution differs from real; judged only by R.5 real held-out eval."
Keep the declared pre-render cy check.

## 3. Capture rotation direction — not blocking
Keep the clockwise assumption. Training labels are camera-relative, so the rotation direction only enters
the quadrant converter (a pure function). If the user later reports counter-clockwise, swap the converter's
sign and re-derive quadrants from stored predictions — no relabeling, no retraining. Add a
`capture_rotation: "clockwise_assumed_unverified"` field to the manifest so this stays visible.

## 4. compound_unclear export — approved, with one rule
Exporting boundary-band compounds as `compound_unclear` (not dropped, not background) is accepted. Rule:
the synthetic unclear (angle within 10 deg of a bin edge) and the real `unclear` (human judgment) are
different definitions — exclude `compound_unclear` from direction accuracy on BOTH sides, and report the
unclear fraction separately for synthetic and real in R.5.

LOG one line when the N/O records are written and one when R.1 starts.
