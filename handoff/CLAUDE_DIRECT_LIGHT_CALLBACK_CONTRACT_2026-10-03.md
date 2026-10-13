# Core-owner request: actual direct-light contribution callback

Date: 2026-10-03. **Proposed interface; not implemented or adopted by the protected core.**
Companion: `CODEX_ANGULAR_CALLBACK_EXECUTION_2026-10-03.md`.

## Current producer and exact requested extension

Current public API, verified by inspection and a fresh signature audit:

```python
direct_light(receivers, fixtures, occluders, leaf_transmittance, settings) -> DirectLight
```

`DirectLight` contains `fixture_ids` and three arrays shaped `(fixture, receiver)`:
`ppfd_umol_m2_s`, `unoccluded_ppfd_umol_m2_s`, `upper_side_ppfd_umol_m2_s`.
There is no callback or diagnostic return. Preserve this API's existing calls and return.

Requested additive signature (core owner may return a different explicit compatible contract for adapter review):

```python
def direct_light(
    receivers, fixtures, occluders, leaf_transmittance, settings, *,
    diagnostic_callback: Callable[[Mapping[str, Any]], None] | None = None,
    diagnostic_max_paths_per_chunk: int | None = None,
) -> DirectLight: ...
```

When callback is None, retain the current path and allocate no diagnostic arrays. When supplied, require an explicit positive integer chunk limit; reject bool. Invoke synchronously; propagate callback exceptions and abort the diagnostic run. Do not catch and silently lose a chunk. Do not import `tools/` into the core to implement this protocol. Core owns its annotations/documentation/tests.

Emit **the existing** `shaded_per_emitter`, `direction` and normal-side classification after the existing calculation. Do not reproduce transport in tools, infer lamp-center directions, or recompute attenuation. The existing `upper[f]` is `where(cos_incidence > 0, shaded_per_emitter, 0).sum(axis=1)`, with the strict `> 0` convention, including two-sided receivers.

## Inventory and chunk contract

Version string: `direct-angular-proposal-1`. This deliberately names an unadopted protocol.
For each invocation, the caller freezes the ordered fixture inventory from the resolved fixture states. Each fixture maps to its emitter array length E, or None if `state.emitters is None`. S is the total receiver count in that invocation, never a chunk-local count or organ-local count. The bridge's full-scene call currently uses supported optical leaf quadrature receivers and positive one-sided area weights.

For a known fixture with E emitters, emit all S*E paths, **including numerical zeros and unknown attenuation**. Stable emitter index is the unchanged index in `state.emitters.positions_grow_mm`. Stable flat path index is `receiver_index * E + emitter_index`; its identity is scoped by the frozen run/snapshot/fixture, not stable across unrelated emitter resampling. A future reflected/path-branching backend needs an explicitly extended protocol.

Each `kind="paths"` mapping contains:

| Key | Type / shape | Meaning |
|---|---|---|
| protocol | str | Exact version above |
| fixture_id | str | Real fixture ID; never `all` / `__all__` |
| receiver_count | integer S | Complete invocation inventory |
| emitter_count | integer E > 0 | Complete fixture inventory |
| expected_path_count | integer S*E | Includes dark and unknown paths |
| path_start, path_stop | integers | Half-open flat path interval, K=stop-start |
| receiver_index | integer array (K,) | `arange(start,stop)//E`, global within invocation |
| emitter_index | integer array (K,) | `arange(start,stop)%E` |
| incident_ppfd_umol_m2_s | float array (K,) | Existing attenuated receiver-cosine-weighted contribution; before multiplying one-sided receiver area; not absorbed light |
| ppfd_valid | bool array (K,) | True for finite nonnegative contributions, including actual zero; False requires NaN |
| missing_reason | sequence (K,) | None iff PPFD valid; otherwise nonempty specific reason such as `leaf_transmittance_unavailable` |
| arrival_unit_grow_xyz | float array (K,3) | Unit vector from receiver toward the actual emitter; opposite photon travel; grow frame |
| direction_valid | bool array (K,) | True requires finite unit vector; False allowed only for known zero PPFD with vector [0,0,0] |
| direction_missing_reason | sequence (K,) | None iff direction valid; otherwise nonempty reason, e.g. `coincident_receiver_emitter` |

For an unknown fixture, emit exactly one mapping with `kind="fixture_unavailable"`, `protocol`, `fixture_id`, `receiver_count=S`, `emitter_count=None`, `expected_path_count=None` and a nonempty `missing_reason` derived from the actual resolved missing inputs. Do not emit an empty emitter array or zero path count to represent missing lamp data. All its receiver scalar/directional results remain unknown. This is an explicit unknown inventory, not a complete numerical zero.

Chunks are contiguous and ascending **per fixture** from 0 to S*E. Fixtures may interleave. No gaps, repeats, backwards chunks or changed counts. The collector verifies the next expected flat index on every call, and all final cursors against the inventories. This also detects an entirely omitted fixture. Chunks may cross receiver boundaries. No global path bitmap is required.

Arrays are borrowed read-only and valid only until callback return; the producer may reuse their buffers immediately afterward. Retaining paths requires explicit copies by the receiver. The supplied tools collector instead synchronously reduces them and keeps no borrowed views. Callback code must not mutate producer arrays. Producer must document and test this lifetime. No asynchronous callbacks or unordered parallel delivery in this version.

## Passive owned implementation available now

`tools/light_direction_diagnostics.py::DirectionCollector` implements this proposed receiving contract:

```python
collector = DirectionCollector(
    fixture_inventory, unit_normals_grow, quadrature_area_m2,
    max_paths=existing_receiver_emitter_budget,
    max_chunk_paths=explicit_diagnostic_chunk_limit,
    max_receiver_fixture_pairs=explicit_accumulator_budget,
)
# NOT RUNNABLE UNTIL THE CORE OWNER ADOPTS THE CALLBACK:
result = direct_light(..., diagnostic_callback=collector,
                      diagnostic_max_paths_per_chunk=explicit_diagnostic_chunk_limit)
moments = collector.finish(result)
```

Constructor copies normals/area. Limits are mandatory, positive integers; no hidden defaults. Inventories are known before allocation of `(F,S)` accumulators. `max_paths` bounds known total receiver/emitter pairs; unknown inventories are explicitly unavailable rather than guessed. `max_receiver_fixture_pairs` bounds reduction storage; `max_chunk_paths` bounds diagnostic temporaries. The collector adds no rays or transport calls. It does not reduce the core's existing S*E work arrays or alter `max_ray_triangle_pairs_per_chunk`; the owner must separately measure core diagnostic overhead.

`finish` requires complete structural inventory and compares summed path PPFD to the **same call's** received and upper-side arrays, including exact NaN availability masks. Absolute tolerance is **1e-10**, relative tolerance **1e-9** (`abs(a-b) <= atol + rtol*abs(reference)`); IDs/counters/flags/missingness are exact. Unit norm and rotation numerical tests use the same tolerances. Direction degeneracy remains the schema's **1e-12** relative to F, applied by the existing normalizer. These are software tolerances, not measured accuracy thresholds.

`ReceiverMoments` returns owned arrays: fixture order, received/normal-side PPFD `(F,S)`, `flux_umol_s (F,S)`, `first_umol_s (F,S,3)`, `second_umol_s (F,S,6)` ordered xx,xy,xz,yy,yz,zz. Here F in shapes means fixture count. Values are unnormalized area-weighted sums `w_i * sum_j p_ij`, `w_i * sum_j(p_ij*u_ij)`, `w_i * sum_j(p_ij*u_ij*u_ij.T)`; all moment components have umol/s units. Every unknown path invalidates that receiver's F/M/B; no partial moments are returned as complete. Known normal-side PPFD can remain finite when only an opposite-side contribution is unknown, matching the core. `unknown_path_count` reports count per receiver (-1 for unknown fixture inventory); `first_missing_reason` preserves the first contributing unknown reason, not an exhaustive path log. Structurally complete streams may contain unknown transport values.

No production bridge call uses this collector yet. No dynamic monkeypatch, tracing local variables, alternate tracer, or guessed API call is installed. Existing export schema/consumer/capabilities retain their angular-unavailable behavior. Supplied-chunk tests cannot establish the producer contract.

## Core owner acceptance and return

1. Test callback off/on with identical inputs. All three returned DirectLight arrays must match within atol=1e-10, rtol=1e-9, with identical NaN masks and fixture/receiver order. Check original arrays are not mutated by chunk preparation.
2. On actual transport contributions, test scalar sum and positive-normal sum against existing outputs with those tolerances. Include a multi-emitter source where lamp-center approximation would visibly fail; single, asymmetric, and equal opposite fixtures; zero output/beam exclusion/coincident paths; known and unknown leaf transmittance.
3. Preserve physical leaf surface crossing deduplication, own-triangle exclusion, opaque background precedence, untouched original target/background geometry and existing resource checks. Unknown transmittance must affect only actually crossing illuminated paths; a definite opaque blocker still yields known zero.
4. Exercise chunk boundaries within a receiver, final partial chunks, buffer reuse, thrown callback errors, omission/duplicate detection, unknown fixture notification, and mandatory budget validation. Report disabled/enabled peak memory and runtime on declared S/E/triangle sizes; demonstrate bounded callback chunks without weakening existing transport budgets.
5. Rotate receiver/emitter/occluder geometry consistently, verify `M'=R*M`, `B'=R*B*R.T`; invert the rotation and translate the entire scene with no change to direction. These must be real producer tests; passive sink covariance is insufficient.
6. Return exact adopted signature/types, ownership/lifetime/order documentation, producer version/hash, executed test commands/results, numerical tolerances and scope limitations to Codex. Do not mark the whole direction-export objective complete after only the core change.

## Remaining Codex work after the producer exists

Wire the collector into the existing full-scene bridge call, keeping canopy shading/source IDs. Accumulate F/M/B per fixture, clock step, supported compound/region and named frame; scale all three by the same explicit fixture schedule fraction before combining real fixtures. Unknown schedule remains unknown; explicit zero output is zero. Sum raw moments before normalization; never sum `all` again. No second absorptance factor.

Use existing grow-to-board rotations and only reviewed whole-axis plus transverse evidence for compound-local frames. Translation is for points only. Keep observed rachis axis separate from arrival covariates and future growth. Preserve the existing mathematical distinction: at zero F all normalized channels unavailable; for equal opposing light retain B/F, zero mean/concentration, and unavailable dominant direction with cancellation reason. If a different cancellation representation is desired, version/document it instead of silently changing historical output.

Extend independent serialized consumer checks against explicit receiver moments and source/scaling/frame provenance, then enable only genuinely supported direct capabilities. Native spatial/side/angular remain unavailable. Add real path-to-export schedule/rotation/missingness tests and fresh preparation/calculation/export plus canopy splits under a new build directory after hashed source changes. Never alter old hashes or rebrand the current scalar package as angular evidence.

Real physical accuracy remains unverified until reviewed metric surfaces, lamp layout/photometry/optics, supported observations and independent calibration/validation exist. No P3/P4 linking, physiology, Native job, new inference/training or upload is part of this request.
