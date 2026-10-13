# Claude Code — P1 side shoots: modeling, detection, distinction, tracking (2026-10-12)

Implementer: Claude Code (P1 session). Scope: observed side shoots only — register, model, distinguish and track
them. No side-shoot *emergence* prediction, no engine (P4/P3) work, no training runs. Runs in PARALLEL with a
Codex P4 task; a later P3 prompt consumes both.

## 0. Read first (list files read; say which are missing)
`CONVENTIONS.md`, `CLAUDE.md`, last 40 lines of `handoff/LOG.md`, `handoff/MTG_CONVENTION_2026-10-10.md`
(§11 A1, §12 A2, §13, A3 if present), `handoff/P1_EXECUTION_2026-10-11.md`, `handoff/P1_INVENTORY_2026-10-11.md`,
`handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md` (§5, §7),
`handoff/DETECTOR_POLICY_2026-10-09.md`, claude.ai project doc `정의집_토마토_2026-10-11` §1-1 (axis/shoot
decisions of 2026-10-12 — the normative source for this prompt).

## 1. User decisions to implement (2026-10-12, all `user_stated`)
- A side shoot first appears with **two leaves together**. Register it as an `axis_shoot` (order-1 axis,
  `first_observed` = that capture; emergence interval = (previous capture, this capture]).
- `axis_shoot` becomes `substem` when its **first two leaves are fully expanded**. From then on its apex bundle
  is called `shoot′` (1st side shoot), `shoot″` (2nd), …; the main-stem apex bundle stays `shoot`.
- Rank rule identical on every axis: a leaf gets the next rank **when it has unfolded and is separately
  visible**. Ranks never renumbered. (Tie of the first two leaves in one capture: proposal = basal leaf of the
  side axis is rank 1 — implement as the default, flag `tie_rule = proposed`.)
- Storage columns, never prime characters in files: `axis` (`M`, `S1`, `S2`…), `order` (0/1), `parent_rank`
  (main-stem leaf rank at the attachment axil; `unavailable` without a human record or side view),
  `rank` (integer), `axis_state` (`axis_shoot` | `substem`). Display labels only: `1`, `1′`, `1″`.
- Prime count = which side shoot (S1 → `′`, S2 → `″`), NOT axis order. Numbering basis is still open
  (proposal: registration order, immutable; same capture → lower node first) — implement the proposal, flagged.
- Sympodial continuation (the axis taking over above a truss) is **main stem**, never a substem. A truss has no
  leaves, so the two-leaf rule already excludes it.
- Scope stays `topology_scope = provided_axes`; unobserved side shoots are not generated; `completeness =
  unavailable` unchanged.

## 2. Work orders
**S1. MTG amendment.** Append (never rewrite) `## Amendment A4 — axes and side shoots` to
`handoff/MTG_CONVENTION_2026-10-10.md`: everything in §1 above, the axis/leaf ID scheme
(`dwt_101/S1` axis vertex; compounds keep their track IDs and gain `axis`), and the open items (numbering
basis, tie rule, order-2 side shoots).
**S2. Schema.** Extend `tomato3d/state/schema.py` (+ tests): an `axes.csv` table (axis, order, parent_rank +
status, axis_state + state-change capture, first_observed, emergence interval) and the `axis` column on
`mtg_vertices.csv` / `identity_manifest.csv` rows. Validators reject prime characters in stored fields, an
order-1 axis without a registration record, and a leaf rank assigned to a not-yet-unfolded leaf.
**S3. Human registry ingest.** `manual_events.csv` does not exist; define and read
`data/records/side_shoots/side_shoot_registry.csv` (plant_id, axis, parent_rank, first_observed date,
axis_state, note — human-owned, read-only; ship a header template + one example row in `build/`, never write
into `data/records/`). This registry is the only source for `parent_rank` from top views.
**S4. Distinction.** In ingest/update: classify each observed leaf cluster as main-apex `shoot`, `axis_shoot`,
`substem` leaves, or truss, using the registry + the rules in §1; detector classes map `main_stem`→M,
`sub_stem`→S*, `growth_shoot`→shoot (side/middle Roboflow projects already carry these names; the top-view
detector still does not exist → real top-view detection stays `unavailable`, human boxes only).
**S5. Tracking.** Extend `tomato3d/track/link.py`: a compound belongs to one axis for life; side-shoot leaves are
small, clustered and often occluded near the main stem → association across axes is forbidden (a main-axis
track may never be re-assigned to S1), ambiguity → `ambiguous`, absence ≠ removal, new side-shoot leaves get new
IDs on their axis.
**S6. Fixtures + run.** Generator-based synthetic plant with one substem (2–3 leaves) and one axis_shoot:
truth export, ingest→track→update→package through `run_p1.py`; package validates; P2 dry-read (schema only).
Report per-item done/blocked. Real photos: registry-driven registration only; everything else stays audited as
missing input.

## 3. Rules
Do not edit `tools/microtom_*` (forecast session), Codex-claimed files (`vtc_*`, `tomato_fsp_*`), `config/`,
`data/records/`, `docs/`. No thresholds or angles invented; blade curl / θ limits stay on hold. LOG claim first,
result line last; update the P1 rows of `flow/flow_map.csv` and rerun the checker.

## 4. Deliverables
Code + tests (full `tests/` suite passes, report counts), amendment A4, registry template,
`handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md` + `_KO.md`, one synthetic package under `build/`.
