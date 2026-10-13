# Claude Code — P1: truss nodes, `segment_index`, and the confirmed axis policies (2026-10-12)

Implementer: Claude Code (P1 session, owns `tomato3d/`, `tests/`). Follow-up to
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md`. Runs in PARALLEL with a Codex P4 task; a P3 prompt consumes both.

## 0. Read first
`CONVENTIONS.md`, last 40 LOG lines, `handoff/MTG_CONVENTION_2026-10-10.md` §15 Amendment A4,
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md`, **`docs/정의집_토마토_2026-10-11.md`** (now on disk — the
decisions mirror; the MTG convention is still the binding contract), `handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md`
§6 (the consumer's attachment representation you must stay compatible with).

## 1. User decisions of 2026-10-12 to write into the contract
A4 left three items as proposals. The user has now confirmed them; they are no longer proposals:
1. **Side-shoot numbering** = registration (`axis_shoot`) order, `S1`, `S2`…; on a tie within one capture the
   lower attachment node is numbered first; a number once given is never changed.
2. **Rank 1 when the first two leaves expand in the same capture** = the basal leaf of the side axis.
3. **Order-2 side shoots**: notation reserved as the dotted axis path `S1.1`, `S1.2` (`order = 2`,
   `parent_axis = S1`, `parent_rank` = the rank on S1). Primes are NOT reused — prime count already means
   "which side shoot". **Code still forbids `order = 2`**; this prompt only records the reserved notation so a
   future change has one obvious spelling.

New decisions:
4. **Side shoots bear trusses** (user observation). The determinate program applies per axis, substems included.
5. **A sympodial continuation above a truss is ONE axis.** The axis id stays `M` (or `S1`), leaf ranks run on
   unbroken, the axis is never split. The truss is recorded at its node, and every node carries
   **`segment_index`** — 1-based, incremented at each truss on that axis — so "leaves between trusses" is
   countable without splitting. This is the counter the two-successive-truss stop rule needs.

## 2. Work orders
**T1. Amendment A5.** Append `## 16. Amendment A5 — trusses, segments and confirmed axis policies` to
`handoff/MTG_CONVENTION_2026-10-10.md` (append-only, nothing above rewritten): §1 items 1–5, the `segment_index`
definition and its 1-based rule, the truss vertex's place in the scale table (scale 3 beside CompoundLeaf, no
leaves, never an `axis_shoot`), and what stays open (whether code may allow `order = 2`).
**T2. Schema.** Add `segment_index` (int ≥ 1) to `axes.csv` rows and to every MTG/identity row that carries
`axis`; add the truss vertex type with `axis`, `parent_rank`, `segment_index`, `first_observed`, and a status.
Validators: `segment_index` starts at 1 on every axis and only ever increases along that axis; a truss node
forces the next node's `segment_index` to increment; no truss carries a leaf rank; `order = 2` still rejected,
now with an error message naming the reserved `S1.1` spelling.
**T3. Human truss registry.** Trusses have no detector and no synthetic source (verified 2026-10-12:
`tomato3d/synth/` contains no truss geometry), so they are human-recorded like side shoots. Define and read
`data/records/trusses/truss_registry.csv` (plant_id, axis, above_rank, first_observed, note) read-only, and ship
a header + one example row + README under `build/`. `segment_index` is DERIVED from this registry plus the leaf
ranks — never hand-entered, never guessed from a photo.
**T4. Propagate.** `segment_index` and truss nodes flow through ingest → track → update → package exactly like
`axis`; the P2 field map and the exchange columns Codex's adapter reads (`fsp-axes-1`) gain them. Coordinate the
exact column spelling with the P4 contract §6 and record the agreement in LOG.
**T5. Run.** Extend the synthetic fixture: one plant where M makes a truss after a few leaves and continues
(so `segment_index` reaches 2), one substem that also makes a truss. Full `run_p1.py` path into a new
`build/p1_state_*` package; validates; P2 dry-read passes. Report per item done / blocked.

## 3. Rules
No detector training, no generator truss geometry, no thresholds invented. Do not edit `tools/`, `config/`,
`data/records/`, `docs/` (the definitions mirror there is read-only for you), or Codex-claimed files. LOG claim
first, result last; update the P1 rows of `flow/flow_map.csv` (merge the pending Codex rows from
`handoff/FSP_EXTENSION_SIDESHOOT_FLOW_ROWS_2026-10-12.csv` while you are there) and rerun the checker.

## 4. Deliverables
Amendment A5, code + tests (full `tests/` suite passes, report counts), the truss registry template, the new
fixture package, `handoff/P1_SEGMENT_TRUSS_EXECUTION_2026-10-12.md` + `_KO.md`.

---

## T6 (added 2026-10-12) — the pot scale reference is now measured

The real-photo audit's 117 `scale` gaps exist because no metric reference was ever measured. The user has now
measured one with calipers.

**Measured value (`source_kind = measured`, user, 2026-10-12, caliper):** the pots are **square cells,
60 mm × 60 mm at the top rim, 70 mm deep**, and **60 mm is the OUTER top edge, across the flats** (not the
diagonal, not the inner wall).

1. **Field.** The existing `pot_rim_inner_diameter_mm` assumes a round pot and must not be filled with this
   number. Add `pot_rim_outer_edge_mm` (square cell, one side, top rim, across flats) and `pot_depth_mm`
   (70 mm, recorded only — not a scale source). Keep the round field for any future round pot; a row may carry
   one or the other, never both, and the validator says which convention produced a mm value.
2. **Per-pot, never global.** Top views are handheld perspective projections, so the rim's apparent size differs
   across the frame. Derive the scale **per pot from that pot's own rim** in that image; a single image-wide
   scale is rejected.
3. **Plane, stated plainly.** The rim is the reference plane. Leaves sit ABOVE it and are therefore nearer the
   camera, so a rim-derived scale **OVERestimates** leaf dimensions.
   (Corrected 2026-10-12 — this prompt originally said "underestimates", which was wrong. Pinhole: mm/px scales
   with camera distance, a leaf at height h is at d_rim - h, so the rim's mm/px applied to it gives too many mm.
   At d ~ 23 cm, h = 2 cm is about +9 % length / +19 % area, h = 5 cm about +26 % / +59 %. The error was mine, in
   this prompt; the sign is the only thing that changes, the rule below does not.) This is the existing `plant_local_mm`
   convention (definitions §2: "화분 테두리 평면 투영값… '실제 크기'라 부르지 않음") — keep that name and that
   caveat on every value; do not introduce a correction factor.
4. **Cross-check and the 5 % rule.** Where a second scale source exists (ruler, board), compare and apply the
   STAGE1 rule: agree within 2 % → accept; differ by more than 5 % → stop and report. With only the pot rim,
   report `scale_sources = 1` and no cross-check.
5. **Re-run the real audit** with this reference into a new `build/p1_state_*` package and report how many of
   the 117 scale gaps close and what remains (the 13 optical-surface gaps need Q2 and are NOT closed by this).
6. **Uncertainty.** Record the rim-detection uncertainty in pixels per pot and propagate it to the mm values;
   never publish an mm value without it.

Do not write into `data/records/` — the measurement enters through the normal human-record path, and this
prompt only defines the field, the derivation and the caveat.
