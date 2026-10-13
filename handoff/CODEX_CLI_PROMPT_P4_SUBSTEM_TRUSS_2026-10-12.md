# Codex — P4: enable substem trusses and carry `segment_index` (2026-10-12)

Implementer: Codex (owns `tools/vtc_development*`, `tools/tomato_fsp_*`, `tools/fsp_axes*`). Follow-up to
`handoff/P4_SIDESHOOT_EXECUTION_2026-10-12.md`. Runs in PARALLEL with a Claude Code P1 task; a P3 prompt
consumes both.

## 0. Read first
`CONVENTIONS.md`, last 40 LOG lines, `handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md`,
`handoff/P4_SIDESHOOT_EXECUTION_2026-10-12.md`, `handoff/VTC_V3_PENDING_DECISIONS_2026-10-11.md`,
`handoff/MTG_CONVENTION_2026-10-10.md` §15 A4 and the new §16 A5 (being appended in parallel by Claude Code; if
A5 is absent, use `docs/정의집_토마토_2026-10-11.md` and say so).

## 1. The two user decisions that change your contract
1. **Micro-Tom side shoots DO bear trusses** (user observation 2026-10-12). This answers the pending item
   "actual Micro-Tom substem truss behavior" in `VTC_V3_PENDING_DECISIONS`. The same conditional determinate
   program therefore applies to declared side axes, not only to M. It is still a *conditional program selected
   from Carvalho-style priors*, not a fitted Micro-Tom law — keep every flag and `source_kind` as they are.
2. **A sympodial continuation is one axis, and every node carries `segment_index`** (1-based, incremented at
   each truss on that axis). Your native graph already keeps succession on one logical axis; this makes the
   segment counter explicit and exportable, which is what the two-successive-truss rule counts.

## 2. Work orders
**X1. Substem trusses.** Allow declared side axes to run the truss/stop program: `APPLY_DETERMINATE_STOP` is no
longer main-axis-only, and its default for a declared substem follows the same selected program as M. State the
default you choose in the contract and in the pending-decisions register; a per-axis override stays available.
Record in the contract that the user's observation is the source (`source_kind = user_stated`).
**X2. `segment_index`.** Accept it on every imported axis/node, carry it through committed states, events,
inventories and meshes, and export it per organ. Derive nothing: if the producer does not supply it, the field is
`unavailable` and the axis's truss-count rule reports `unavailable` rather than assuming segment 1.
**X3. Stop bookkeeping per axis.** The stop decision for an axis uses that axis's own truss history
(`segment_index` + truss events). A stopped M must not stop a live S1, and a stopped S1 must not stop M. When
every live axis of a plant has stopped, the plant initiates nothing new while existing organs keep growing.
**X4. Exchange columns.** Reconcile the `segment_index` and truss-node column spelling with the P1 owner through
LOG (they are adding it to `fsp-axes-1` in parallel); accept the producer alias with disagreement rejection, as
you already do for `axis`/`axis_state`.
**X5. Registers.** Move "substem truss applicability" from pending to selected in
`VTC_V3_PENDING_DECISIONS_2026-10-11.md` (append-only), citing the user observation; leave axis-specific timing,
dominance evidence and real attachment/hidden state pending.

## 3. Acceptance evidence (synthetic, 4.8M rays, label everything conditional)
1. A declared substem with a supplied truss history produces its own determinate stop; M keeps initiating.
2. Both axes stopped: zero new organs, existing organs still gain funded mass, carbon closure unchanged
   (residual at the current ~1e-17 gC scale).
3. `segment_index` round-trips producer → request → committed state → export; a missing value yields
   `unavailable`, never a default of 1.
4. Per-axis ledger sums still equal the plant ledger every interval.
5. Failure: a truss event on an axis with no matching node, or a decreasing `segment_index`, refuses to publish.
6. Regression: the existing focused suite still passes (report the unique count, do not add overlapping counts).

## 4. Rules and deliverables
Do not edit `tomato3d/`, `tests/`, `tools/microtom_*`, `config/`, `data/records/`, `docs/`, or the original VTC
(no LICENSE — local only). No emergence model, no fitted dominance coefficient, no nutrient-growth feedback.
Deliver: contract addendum, code under your claims, `handoff/P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md`, updated
pending-decisions register, flow rows handed to the P1 flow-map owner through LOG, LOG claim/result lines.
