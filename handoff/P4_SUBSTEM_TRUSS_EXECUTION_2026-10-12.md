# P4 substem trusses and explicit segment delivery — 2026-10-12

Status: implemented and verified as an assumption-conditioned software model. Implementer: Codex. This is the completed follow-up to P4_SIDESHOOT_EXECUTION_2026-10-12.md; it does not implement Claude Code's P3 forecast work.

All execution counts and numerical residuals below have `source_kind=execution_result`, source ref `build/fsp_truss_20261012_delivery_01/acceptance.json` and its referenced native files/JUnit reports. Fixture dimensions, hidden clocks, masses and histories are `user_assumed` synthetic declarations, with refs in each frozen scenario/request. No number below is a fitted Micro-Tom parameter or measured growth result.

## Decisions and delivered behavior

The contract was appended before implementation: P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md section 7, then sections 7.1–7.3 reconcile the published P1 Amendment A5. A5 was absent initially; the supplied user decision and local definitions mirror were used until it arrived. A5 is now read and reconciled.

- **X1:** Substem truss applicability is selected from the user's observation (`source_kind=user_stated`, ref user decision 2026-10-12). The selected `APPLY_DETERMINATE_STOP=true` default is the same conditional program as M (`user_assumed`, contract section 7). Every axis request still explicitly supplies the provenance-bearing flag; omission is rejected, not silently defaulted. An explicit false disables new initiation while existing tissue grows. Shared CADENCE retains its existing source; no new cultivar timing or dominance coefficient was fitted.
- **User clarification:** The user explicitly authorized the existing conditional program to create new trusses. Births remain model-generated/assumption-conditioned. Declared axes remain the only axes; no side-shoot emergence model is added. P3 V2's earlier no-new-truss clause must be reconciled with this later authorization by the P3 owner.
- **X2:** Imported `segment_index` is preserved in native initial/committed states, events, organ inventories, meshes and consumed/flux records. Missing values stay `unavailable`; the axis reports `truss_rule_status=unavailable` and cannot initiate until its required history is supplied. Existing organs can still grow. A model-generated truss closes its current segment; the current axis counter increments for the next segment, including after a terminal truss. Immutable organ segment and current axis counter are separate exports.
- **X3:** Each declared axis uses its own supplied truss nodes/history, hidden controller state and subsequent truss events. Independent stop and continued existing-organ growth are verified below. The plant carbon pool, once-only funding, and per-axis attribution remain unchanged.
- **X4:** P1 `Truss` maps explicitly to native `TrussAxis`; `trusses.csv` is frozen and hash-bound. `truss_vertex_id`/`node_id`, `segment_index`/`sympodial_segment_index`, `axis`/`axis_id` and `axis_state`/`stage` aliases reject disagreement. The segment alias is consumer compatibility, not a claim that P1 emits it. P1 same-scale S Axis → M Axis edges are validated together with the exact `axes.csv parent_node_id` axil used for native attachment.
- **X5:** Substem truss applicability moved to selected in the append-only pending register. Axis timing, dominance evidence, real attachment/registration and hidden physiological state remain pending. Water/element accounting stays plant-level; nutrient-growth feedback stays disabled.

## Consumer input and output contract

Use `axis_contract=fsp-axes-1`, `topology_scope=provided_axes`, `topology_completeness=unavailable`. Axis records carry the selected producer `segment_index`, complete declared same-axis `truss_history` entries (`node_id`, `segment_index`), existing explicit initialization and per-axis parameter records. `prepare_run` reads producer segment/history into the frozen request and rejects disagreement with explicit request values. It never reconstructs missing segment values from rank, age or counts. When supplied, history must match actual selected Truss vertices and the explicit hidden truss count.

A5 Truss vertices intentionally lack geometry. Supply a separate initialization entry with `geometry_source_kind` (`user_assumed` or `supplement_provided`), `geometry_source_ref`, `base_xyz_m` and `tip_xyz_m`. No coordinates are inferred from leaf rank. The acceptance fixtures explicitly use zero-extent bookkeeping points, which cast no shadow; this is not an observed truss location. Missing geometry supplement rejects preparation.

Native `apices.csv` exports the immutable apex `segment_index` and current `axis_segment_index`. Committed `axis_inventory.csv segment_index` exports that current counter; `organ_inventory.csv segment_index` exports each organ's immutable segment. States/events/meshes continue to carry `axis_id` and attachment `parent_rank`. A5 truss table `parent_rank` means above-rank on its bearing axis; it is not the side-axis attachment rank. P3 must preserve this distinction, parameter provenance and checkpoint immutability, and must not advance a produced checkpoint again.

Code: `tools/fsp_axes_segments.py` validates segment/history and exports current counters; `tools/fsp_axes.py` binds producer axes and native controllers; `tools/tomato_fsp_io.py` freezes/maps source records and explicit hidden geometry; `tools/vtc_development_observation.py` initializes native organ segments; `tools/vtc_development_native.rgg` performs native initiation and segment exports; `tools/vtc_development_io.py` preserves segment strings; `tools/vtc_development.py` binds source hashes; `tools/tomato_fsp_pipeline.py` commits axis/organ inventories. New tests are in `tools/tests/test_fsp_axes_segments.py`; native scenario helper is `tools/fsp_axes_truss_acceptance.py`.

## Native acceptance

Seven successful runs, fifteen intervals, each configured for **4,800,000 rays**. Native status verified, exit 0; every checkpoint `native_advance_count=1`. Independent consolidation verifies frozen models, completion/commit hashes, producer/request/state/export segments, per-axis sums and growth/stop assertions.

| Case | Artifact | Result |
|---|---|---|
| S1 stops; M lives | `build/fsp_truss_20261012_acceptance_04/side_stop` | S1 closes segment 4 and stops in interval 1; its two leaves stay two. M leaves increase 5 → 7 over three intervals. Existing tissue gains M 0.08997595796350054 gDM and S1 0.023815995740634373 gDM. S1's five new organs are its terminal truss and four flowers, not new leaves or a new axis. |
| Both axes stopped | `.../both_stopped` | Zero new organs over three intervals. Existing tissue gains M 0.09158296900263779 gDM and S1 0.024234063788075685 gDM. |
| Missing S1 segments | `.../missing_segment` | S1 states remain unavailable; zero S1 births, existing S1 tissue gains 0.02390859724330622 gDM. M continues. |
| Same-axis continuation | `.../successor` | M creates its first truss and segment-2 successor organs while remaining logical M. Its supplied hidden historical counters are explicit synthetic assumptions; observed inventory completeness is not claimed. |
| Exact producer columns | `build/fsp_truss_20261012_exchange_01/run` | Canonical A5 trusses.csv and main-axis unavailable-parent sentinel execute successfully. |
| Unlocated logical trusses | `build/fsp_truss_20261012_exchange_02/run` | Explicit separate geometry supplement accepted; no optical mesh for zero-extent trusses. Missing supplement rejects before publication. |
| Actual P1 delivery | `build/fsp_truss_20261012_producer_native_02/run` | Unmodified `build/p1_state_20261012_05`, explicit `fixture_truth` route, capture c2: M/S1/S2 imported with segments 2/2/1 and histories 1/1/0. One native interval completes; all three axes' existing tissue gains mass. |

Maximum absolute plant carbon residual: **2.3418766925686896e-17 gC**. Maximum axis-sum/plant-ledger discrepancy: **1.3877787807814457e-17 gC** across corresponding gross, maintenance, structural growth and growth respiration columns every interval. These are floating-point roundoff, with unchanged conservation tolerance. Demand/allocated attribution continues to pass the native collector's organ/axis checks.

Failure artifacts: `build/fsp_truss_20261012_failures_01/failures.json` rejects a missing truss node and a decreasing segment assignment; both record `published=false`. Independent unit cases also reject wrong-axis history, alias disagreement, duplicates, gaps and count mismatch. `build/fsp_truss_20261012_exchange_02/acceptance.json` records missing hidden geometry rejection without publication.

The delivered P1 snapshot reconstruction still lacks required leaf geometry; the attempted main route stopped before preparation. The successful run explicitly selects the fixture's separate truth route and a separate assumed physiology/geometry supplement. It verifies actual producer format interoperability, not reconstructed real-plant accuracy. Topology-only inspection of the snapshot is in `build/fsp_truss_20261012_producer_02`.

## Regression and reproducible commands

**219 unique passing tests**, zero failures/errors in the passing focused reports: 195 existing cases plus 24 new segment cases. JUnit `build/fsp_truss_20261012_regression_01.xml` contains 216 cases before the last three adapter cases; `build/fsp_truss_20261012_adapter_final.xml` contains the final affected 75 cases. Their union of `(classname,name)` identities is 219; overlapping runs are not added. Covered modules include V3, bridge, pipeline, axes/extensions, and read-only forecast environment/parameters/forecast/evaluation/fixes. The parallel P1 owner's counts are separate and are not included. This is the requested focused suite, not a claim to have run every unrelated repository test.

Commands below exited 0; native result manifests include the full Java/GroIMP command and hashes. Commands that create immutable output folders require a new destination when replayed. Build helper scripts preserve the exact additional fixtures used in this delivery.

```powershell
python -X utf8 -m tools.fsp_axes_truss_acceptance --out build/fsp_truss_20261012_acceptance_04
python -X utf8 build/fsp_truss_failures_20261012.py
python -X utf8 build/fsp_truss_exchange_20261012.py
python -X utf8 build/fsp_truss_unlocated_20261012.py
python -X utf8 build/fsp_truss_producer_v2_20261012.py
python -X utf8 build/fsp_truss_actual_native_v2_20261012.py
python -X utf8 -m pytest tools/tests/test_fsp_axes.py tools/tests/test_fsp_axes_segments.py tools/tests/test_tomato_fsp_pipeline.py -q --junitxml=build/fsp_truss_20261012_adapter_final.xml
python -X utf8 build/fsp_truss_delivery_20261012.py
```

The earlier full focused selection used the following eleven modules: test_vtc_development, test_vtc_growth_bridge, test_tomato_fsp_pipeline, test_fsp_axes, test_fsp_axes_segments, test_fsp_extensions, test_microtom_environment, test_microtom_parameters, test_microtom_forecast, test_microtom_forecast_eval and test_microtom_forecast_fixes (all under tools/tests; pytest exit 0, JUnit regression_01 above). The last affected run took 312.16 seconds. Earlier full run took 682.63 seconds.

Preliminary attempts are preserved: acceptance_01/_02 failed fixture status preparation; acceptance_03 is superseded by _04; producer_01 exposed the same-scale parent adapter issue and was corrected in producer_02; producer_native_01 rejected unavailable snapshot geometry and is not an issued success. Native sources in the first six final runs predate only the last actual-P1 parent-edge adapter change in fsp_axes.py; their exact frozen hashes are retained in the acceptance manifest. The final actual-P1 run matches the delivered native source hashes. Final affected regression covers that adapter. No failed or earlier issued artifact was overwritten.

Runtime: GroIMP 2.2.1, Temurin Java 21.0.12.1; core SHA256 `35c605d65d9b54fe64cdf93bf28ae44ae7a1b6ded03b461dedcb0156a5c22147`. Delivery manifest includes a ten-file source snapshot and source hashes. Original VTC remains local only with unresolved redistribution license.

## Owner handoff and limits

P1 A5 and the actual fixture exchange are reconciled. Flow rows for this task are supplied separately in `handoff/P4_SUBSTEM_TRUSS_FLOW_ROWS_2026-10-12.csv` for the P1 flow-map owner to upsert by path and rerun the checker; no simultaneous shared flow-map edit was made. Earlier side-axis flow rows have already been merged by P1.

P3 owner: use the resource contract sections 2 and 7.1–7.3, actual fixture and explicit supplements above. Reconcile new conditional truss generation with the older P3 restriction; do not label generated trusses observed. Axis-specific cadence draws require an explicit consumer/engine contract extension if different per-axis cadence is needed; the engine currently shares its existing CADENCE parameter. No P3 forecast issuance or new per-axis evaluation is claimed here.

Human/science owner: provide actual axis timing, mass/age/clock, attachment/registration, truss location, dominance evidence and real geometry/light. Repeated observations are still needed to test growth accuracy. No fitted Micro-Tom law, new side-axis emergence, per-axis nutrient uptake or nutrient-growth feedback was introduced. Protected paths and original VTC were not edited.

Final handoff check: `python -X utf8 flow/check_flow.py` exited 0 on the existing shared map; output is `build/fsp_truss_20261012_delivery_01/flow_check_existing_map.txt`. All twelve proposed upsert paths exist. This check does not claim the new rows have already been merged. `handoff_verification.json` records document hashes and the independently deduplicated 219 test identities.
