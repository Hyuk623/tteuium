# Declared side-shoot science and IO contract

Version `fsp-axes-1`; written before implementation, 2026-10-12. Owner: Codex under the user's explicit assignment to select and document conditional laws. This extends V3 and the staged pipeline; it does not replace the single native state-advance authority. Scope: observed/declared order-1 axes only. `topology_scope=provided_axes`, `topology_completeness=unavailable`. No bud activation, side-shoot emergence probability, pruning response or inferred missing axes.

## 1. Inspected behavior, sources and restrictions

V3 currently has one active-apex controller per plant and one shared reserve. Its graph Axis vertices are successive sympodial segments, not botanical side shoots. The P1 consumer currently requires exactly one Axis and assigns all organs to it. Its final-stop validator currently rejects all later births on a plant. Those are the specific behaviors to change. Legacy requests without `axis_contract` retain their input format and numerical law.

Read: CONVENTIONS, AGENTS, latest 40 LOG lines, V3 science/IO contract, pending decisions, staged execution report and MTG convention through section 13. Amendment A4 was absent at initial inspection. Neither named claude.ai document (`정의집_토마토_2026-10-11`, `논문확인_MicroTom_2026-10-10`) is available as a local file in the supplied workspace roots; access is not assumed. The explicit definitions in the user's assignment are the interim normative source. Reconcile with A4 before delivery and record the actual version consumed.

Carvalho et al. 2011, DOI 10.1186/1746-4811-7-18, https://pmc.ncbi.nlm.nih.gov/articles/PMC3146949/, is the primary reference for Micro-Tom developmental context. It does not supply a fitted side-shoot allocation multiplier or establish this model's axis-specific timing. Existing borrowed Merlice timing and V3 conditional programs retain their provenance. No Micro-Tom quantitative validation is claimed.

No edits to tomato3d/, tests/, tools/microtom_*, config/, data/records/, docs/ or original VTC. New generated files go under fresh build folders. Parallel P1 and forecast owners receive the exchange contract through handoff/LOG.md, not simultaneous source edits.

## 2. Selected conditional science contract (forecast consumer input)

Every parameter record has `value,unit,source_kind,source_ref,cultivar,uncertainty`. Numeric topology definitions below have `source_kind=user_stated`, `source_ref=user side-shoot assignment 2026-10-12`: main order 0, side order 1; registration after two visible leaves; `axis_shoot` becomes `substem` after both are fully expanded. This is an observation classification, not an automatic age threshold. Leaf ranks follow the unfolding rule independently within each axis. Main sympodial continuations stay M; side sympodial continuations stay their declared S identifier. New side axes are never generated.

1. **Carbon**: one shared plant reserve across all axes. Gross assimilation enters that pool; maintenance of each tissue is charged once. Demand uses the unchanged age-target curve and is charged once. Default `SUBSTEM_SINK_SCALE=1.0`, unit dimensionless, `source_kind=user_assumed`, `source_ref=this contract section 2 / explicit user selection`, cultivar `unfitted_hypothesis`, uncertainty `not calibrated; no dominance at unity`. M and the common root compartment have scale 1.0 by definition. S scales must be positive. Allocation is capped weighted demand-proportional: `a_i=min(d_i,lambda*d_i*s_axis)` with lambda chosen so summed allocation equals `min(available,sum(d_i))`. Saturated demands are removed and the remaining budget is redistributed. This cap prevents a sink weight from creating excess target mass; unity recovers V3. Unspent carbon stays in the same plant reserve. No cross-plant transfer or axis reserve. Other-cultivar dominance values are candidates only, none is enabled.
2. **Light**: every substem leaflet uses the same native optical polygon path. Shading follows geometry. Per-axis absorbed flux and leaflet gross assimilation are source-attribution diagnostics only; they do not imply axis-local photosynthate ownership. Plant-level fixed NRH and the selected incident/absorbed basis are unchanged.
3. **Apex**: each declared axis owns independent clock, produced-event count, leaf order, truss count, current sympodial segment, last stem and apex. `SP_STOP_RULE=two_successive_trusses` reuses the existing conditional program on that axis only; it must be explicitly enabled per axis with `APPLY_DETERMINATE_STOP=true`. `false` means declaration-only apex (no new organ initiation), while existing tissue still expands; it is not an indeterminate replacement law. This deliberately avoids inventing a second biological program. Main stop never terminates a live S apex. The initial `apex_stopped` boolean is supplied, never inferred from missing leaves. Whether actual Micro-Tom substems bear trusses remains an open human decision. Leaf ranks of generated primordia are model true-order labels; observed unfolding ranks stay producer evidence, not an asserted observed unfolding event.
4. **Nutrients**: prescribed water/element accounting remains per plant, growth feedback disabled. No per-axis nutrient ledger, uptake differences or joint nutrient allocation law.
5. **Birth/demand**: initial observed axes bring their existing organs and explicit sizes, mass, maximum mass and age; no silent mass-from-area or age-from-date conversion. The registration pair must be present in the selected MTG. Axis/compound/attachment/apex nodes are massless. Shared root mass is imported exactly once. Each side's explicit structural hidden compartment is imported once. Generated tissues start at zero mass, use the shared tissue parameter curves, and intercept light only after funded emergence at a later interval.

## 3. Versioned input and identity

Optional scenario/request keys: `axis_contract="fsp-axes-1"`, `topology_scope="provided_axes"`, `topology_completeness="unavailable"`, `axes=[...]`. Presence requires a complete declared-axis list for each selected plant, including M. Absent keys retain legacy mode. A side-axis package must never silently fall back to legacy single-axis interpretation.

Each axes record:

```json
{
  "plant_instance_id": "fixture_a#2",
  "axis_id": "S1",
  "axis_vertex_id": "source/S1",
  "order": 1,
  "parent_axis_id": "M",
  "parent_node_id": "source/M/N1",
  "parent_rank": 1,
  "stage": "axis_shoot",
  "source_kind": "user_assumed",
  "source_ref": "explicit synthetic fixture; not a plant observation",
  "registration_leaf_ids": ["source/S1/C1", "source/S1/C2"],
  "parameters": {
    "SUBSTEM_SINK_SCALE": {"value": 1.0, "unit": "dimensionless", "source_kind": "user_assumed", "source_ref": "section 2", "cultivar": "unfitted_hypothesis", "uncertainty": "not calibrated"},
    "APPLY_DETERMINATE_STOP": {"value": true, "unit": "boolean", "source_kind": "user_assumed", "source_ref": "same conditional V3 program per axis", "cultivar": "unfitted_hypothesis", "uncertainty": "substems bearing trusses unresolved"}
  },
  "initialization": {
    "thermal_dd": 300.0, "produced": 2, "leaf_order": 2,
    "truss_count": 0, "axis_leaf_count": 2, "apex_stopped": false,
    "stem_mass_gDM": 0.02, "stem_width_m": 0.002,
    "source_kind": "user_assumed", "source_ref": "explicit fixture hidden state"
  }
}
```

All example numbers above are synthetic declarations (`source_kind=user_assumed`), not defaults or Micro-Tom measurements. For M use order 0, `axis_id=M`, empty parent fields, `parent_rank=0`, `stage=main`, empty registration list. S IDs match `S[1-9][0-9]*` and are immutable per plant. Each source axis maps to one selected MTG Axis vertex. Parent node must be a declared main-axis Metamer/Attachment with matching rank and a compound leaf axil. Cross-plant, duplicate, cyclic, higher-order and missing-parent references reject preparation/publication.

Producer exchange target: `axes.csv` keyed `(plant_instance_id,capture_id,axis_id)` with `axis_vertex_id,order,parent_axis_id,parent_node_id,parent_rank,stage,source_kind,source_ref`; additional producer evidence columns are retained. Selected MTG parent/complex paths must agree. P1 observations and physiology supplements stay separate. If the exporter is not ready, a fixture of this explicit exchange format will be used and labelled; no real-producer completion claim. A4 column differences require an explicit adapter and final contract addendum, never guessed values.

Native state `axis_id` is logical M/S1 only in versioned axis mode, scoped by plant_instance_id; `developmental_axis_id` preserves the actual graph segment vertex, including sympodial continuations. `parent_rank` is the side attachment rank (0 for M) on states, events and mesh records. Generated S organ IDs include S1 in their namespace. Legacy axis_id remains the existing graph ID. Native controls and mesh attachment preserve the declared graph parent.

## 4. Output and acceptance plan

Native `axis_flux.csv` rows per interval/plant/logical axis contain absorbed_umol_s, gross_gC, maintenance_gC, demand_gC, allocated_gC, structural_gC and growth_resp_gC. Roots are attributed to M for exhaustive bookkeeping, explicitly not an anatomical root ownership claim. These sum to the existing plant ledger where corresponding columns exist, and to organ flux for demand/allocated/absorbed totals. No axis carbon balance equation pretends local gross must equal local growth. Carbon closure remains at plant scope.

Public pipeline checkpoints carry axis inventory, parameter registry, axis ledgers, states/events/meshes and bindings. Python validates and publishes native output only. Replay starts from frozen inputs and is deterministic under the declared numerical comparison tolerance.

Required evidence: M+S1 exactly-once funding and conservation; 4.8-million-ray two-seed shading control; main stop with live S1 initiation and stopped-axis expansion; every-interval axis sums and nonunity sink-allocation direction; missing parent/duplicate rejection without publication; existing V3/integration/forecast consumer test counts. Fixture biology remains conditional. Final report: P4_SIDESHOOT_EXECUTION_2026-10-12.md. Existing eight-capability delivery continues separately, with unsupported terminal photon closure, developmental deformation and nutrient-growth feedback stated accurately.

## 5. Published prompt reconciliation
The original contract above was saved before code as P4_SIDESHOOT_SCIENCE_AND_IO_CONTRACT_2026-10-12.md. The subsequently saved reference work order names this RESOURCE_CONTRACT file; this copy is the canonical P3 entrypoint, preserving the original text and provenance. Source prompt P1 section 1 uses producer columns axis and axis_state. The consumer explicitly maps axis -> axis_id and axis_state -> stage; duplicate aliases must agree. Request records accept axis_state (preferred) or stage (legacy alias). Values remain axis_shoot/substem without automatic promotion. parent_rank is a signed integer because the MTG fixed-rank convention permits later-discovered lower ranks; M alone uses 0 for no attachment. Existing graph attachment and declared-node requirements are unchanged. A4 and the actual exporter still require final reconciliation when available.
For light-only runs, axis gross is an uncommitted diagnostic matching organ flux; plant carbon ledgers remain unchanged zero-flux ledgers. Plant/axis physiological sums are checked on growth runs. The legacy apices.csv name plant_thermal_dd carries the owning axis controller clock in fsp-axes-1; axis_id disambiguates it.

## 6. Amendment A4 attachment reconciliation (2026-10-12, before adapter change)
A4 section 15 was published during final delivery. Its producer parent_node_id names the main-stem CompoundLeaf vertex at the declared axil, whereas the original consumer fixture used a separate Metamer. The consumer will explicitly accept either representation: a main-axis CompoundLeaf with matching rank is the axil itself; a Metamer/Attachment still requires a compound leaf child. A4 CompoundLeaf is imported as a zero-length attachment at its observed base, so side-axis attachment never follows a leaf tip. No missing node is synthesized. Producer aliases must agree, and registration leaves remain declared on their owning axis. Main sympodial continuation remains M. A4 numbering order and first-two-leaf tie rules are proposals, not new consumer defaults; the importer preserves supplied stable IDs/ranks. Actual producer export testing remains separate from this explicit format fixture.

## 7. Substem trusses and explicit segments (2026-10-12, before implementation)
Source of applicability: user observation, 2026-10-12, "side shoots DO bear trusses" (`source_kind=user_stated`). This selects applicability to declared substems; it does not fit the conditional Carvalho-style V3 timing/cadence. Selected default APPLY_DETERMINATE_STOP=true for M and declared substems, still an explicit provenance-bearing `user_assumed` parameter in each request; false remains a per-axis override disabling initiation while existing tissue grows. Existing flags/provenance are never silently changed. SUBSTEM_SINK_SCALE remains 1.0, user_assumed, no dominance. Axis-specific timing, dominance, actual attachment/hidden state remain pending.

The user explicitly selected "allow the existing conditional program to generate new trusses" in this task. Such births are model-generated, assumption-conditioned predictions, never measurements. No side-axis emergence model is introduced. This differs from the earlier P3 V2 no-new-truss wording: that consumer must reconcile its issuance policy explicitly rather than relabel generated trusses as observed.

A5 was absent at this initial read; docs/정의집_토마토_2026-10-11.md and the user assignment supply the decision. Canonical producer column is segment_index (positive integer or unavailable) on axes and every MTG node. A supplied alias must agree if both are present. Native initial states preserve each imported value; absent values are exported as unavailable, never inferred from rank/age. Per-axis request records carry current segment_index and explicit truss_history references to imported truss nodes. Native successor segments increment only after a model-generated truss on a known segment; the truss belongs to the segment it terminates. Logical M/S identity and leaf ranks persist. If required axis/node segment metadata or history is unavailable, truss_rule_status=unavailable and new initiation is withheld on that axis while funded existing-tissue growth continues. Legacy non-axis V3 seed mode remains its existing explicitly model-generated program.

Historical truss references must resolve to same-axis truss nodes and matching segment indices, increasing within each axis; supplied history counts must agree with the explicit hidden truss_count. No missing truss node is created to repair an input. Decreasing per-axis leaf/node segment history or a conflicting alias rejects before publication. The native stop rule uses the owning axis's supplied history and subsequent native truss events. Independent stop state never transfers between axes; all stopped axes means no initiation, not zero growth.

Validation will cover side-only stop with live M, both stopped with growth, exact initial segment round trip and generated-segment progression, unavailable input, every-interval axis sums and carbon residuals, missing-node/decreasing-history failures, and the existing focused suite. Exact A5 spelling/availability reconciliation will be appended on delivery. All engineering fixture numbers have synthetic/assumed provenance and are not cultivar calibration.

### 7.1 Producer exchange and counter semantics
The P1 revision-4 schema now names the class `Truss`, table `trusses.csv`, and node reference `truss_vertex_id`; these are accepted and frozen by the consumer, with explicit mapping to native TrussAxis. The optional node_id alias must agree with truss_vertex_id. Canonical segment_index is retained; the compatibility normalizer also accepts sympodial_segment_index with disagreement rejection (not a claim that P1 emits that alias). Main-axis producer parent fields marked unavailable explicitly map to empty native parent fields; side attachments never get that normalization.

An imported organ's segment_index never changes. Native-generated successors receive the incremented segment. The current axis counter, including the increment after a terminal truss, is exported separately as apices.csv axis_segment_index and committed axis_inventory.csv segment_index. This keeps each truss in the segment it closes while retaining the producer's apical counter convention (1 + trusses). No missing imported index is calculated from that formula by this consumer. Imported Plant/Root compartments have unavailable segment attribution. The native program still uses the shared provenance-bearing CADENCE request parameter; no cultivar-specific per-axis timing has been fitted.

### 7.2 A5 text reconciliation (2026-10-12)
A5 section 16 is now published and read. It confirms Truss / truss_vertex_id / segment_index and the apical counter semantics above. Producer-derived status remains producer evidence; this consumer does not recompute missing values. A5 deliberately supplies no truss geometry. For those logical nodes, native initialization requires an explicit separate geometry supplement (geometry_source_kind=user_assumed or supplement_provided, geometry_source_ref, base_xyz_m and tip_xyz_m); it never locates a truss from a leaf rank or substitutes zero coordinates silently. A zero-extent bookkeeping point may be explicitly declared in a synthetic supplement; it casts no shadow. Such coordinates are assumptions, not P1 measurements. Known supplied P1 fixture geometry remains supported. This distinction is required for later P3 package preparation.

### 7.3 Actual delivered P1 multiscale edge reconciliation
Read-only inspection of build/p1_state_20261012_05 shows each S Axis parent_id points to the main Axis vertex, while axes.csv parent_node_id identifies the exact main CompoundLeaf axil. Both are explicit producer declarations. The consumer accepts that same-scale MTG edge only when it names the declared parent axis, validates the declared axil node/rank as before, and uses axes.csv's node for the native graph edge. A directly supplied node edge is also supported. An unrelated or absent MTG parent still rejects. This is a representation adapter, not an inferred attachment.

### 7.4 Verified delivery and downstream boundary
A5 and the actual P1 fixture build/p1_state_20261012_05 are now consumed successfully, using its explicitly selected fixture_truth/c2 route and separately declared hidden physiology and unlocated-truss geometry. Snapshot geometry is not substituted silently. The completed report is P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md; independent source/hash/output evidence is build/fsp_truss_20261012_delivery_01/acceptance.json. Execution results (source_kind=execution_result; those refs): 219 unique focused passing cases; seven native runs/fifteen intervals at 4,800,000 rays; maximum carbon residual 2.3418766925686896e-17 gC. These are software evidence, not cultivar fitting. P3 must reconcile its older no-new-truss clause with the user's explicit later authorization of conditional truss generation. Shared CADENCE is unchanged; axis-specific fitted timing remains unavailable.
