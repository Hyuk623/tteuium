# Actual direct-light diagnostic contract

Implemented protocol: `direct-angular-1`. This supersedes the unadopted `direct-angular-proposal-1`; old handoffs remain historical. All callback data come from existing attenuated transport arrays in `tomato3d/light/raytrace.py`.

```python
direct_light(receivers, fixtures, occluders, leaf_transmittance, settings, *,
    diagnostic_callback: Callable[[Mapping[str, Any]], None] | None = None,
    diagnostic_max_paths_per_chunk: int | None = None) -> DirectLight
```

Existing positional calls and the three `(fixture, receiver)` arrays in `DirectLight` are unchanged. A disabled callback creates no diagnostic arrays. An enabled callback requires an explicit positive integer limit (bool rejected), unique real fixture IDs, and nonempty known emitter arrays. Exceptions propagate, aborting the diagnostic run; no partial export is accepted.

Freeze fixture order and emitter inventory from the resolved input states before calling. S is the entire call's receiver count; E is a known fixture's actual emitter-array length. Fixture ID is never `all`. Emitter index is stable within this supplied array, not across emitter-grid changes. The existing direct backend has one path per receiver/emitter pair; reflected/branching paths require a different protocol.

## Known fixture event (`kind="paths"`)

| Field | Contract |
|---|---|
| `protocol`, `fixture_id` | Version above; actual fixture identity |
| `receiver_count`, `emitter_count`, `expected_path_count` | Integer S, E, S*E, including zero and unknown paths |
| `path_start`, `path_stop` | Contiguous ascending half-open flat interval; K=stop-start <= explicit limit |
| `receiver_index`, `emitter_index` | Integer arrays K; flat_index//E and flat_index%E; global receiver indices |
| `incident_ppfd_umol_m2_s` | Float K; attenuated receiver-cosine weighted PPFD, umol/m2/s, BEFORE area/absorptance |
| `arrival_unit_grow_xyz` | Float K by 3; unit receiver-to-emitter vector in grow frame, opposite photon travel |
| `ppfd_valid` | Bool K; true iff finite nonnegative p, including real zero; false requires NaN |
| `missing_reason` | K entries: None for valid p; otherwise `leaf_transmittance_unavailable` |
| `direction_valid` | Bool K; true for a unit geometric direction even when p unknown or zero |
| `direction_missing_reason` | None when valid; `coincident_receiver_emitter` otherwise; coincident direction is [0,0,0] with known zero p |

The producer emits each fixture sequentially in input order, receiver-major paths from 0 through S*E, including dark paths. The collector supports interleaved fixtures provided each fixture remains contiguous and ascending. Missing, duplicate, reordered or entirely omitted paths/fixtures fail closed; `finish` checks final cursors and fixture order. Zero-receiver core calls emit no known-path chunks; the supported-area bridge requires S>0 and positive weights.

## Unknown fixture event

Exactly one event with `kind="fixture_unavailable"`, protocol, fixture_id, receiver_count=S, emitter_count=None, expected_path_count=None and nonempty `missing_reason="fixture_inputs_unavailable:" + actual_missing_inputs`. No numeric zero inventory is manufactured. All receiver moments remain unknown; CSV unknown-path count is unavailable (the internal collector uses -1 as an inventory sentinel).

## Lifetime and budgets

Callbacks are synchronous; mappings and arrays are read-only and borrowed only until return. Copy any retained data. The producer currently copies bounded chunks to isolate solver buffers, even from a consumer deliberately resetting write flags; future buffer reuse is allowed. The collector immediately reduces arrays and retains no borrowed views. Normal-side parity uses strict dot(normal,u)>0, matching the existing two-sided leaf calculation.

Core transport still owns its original S*E arrays and ray-triangle chunk limit. Diagnostic chunks add O(K) temporary storage; the collector keeps O(fixtures*S) sums, normals/areas and reason references. `max_paths`, `max_chunk_paths`, `max_receiver_fixture_pairs` are mandatory positive collector budgets. The bridge uses its existing receiver/emitter budget for total known paths and accumulator pairs; diagnostic K is at most the minimum of that budget and the existing ray-triangle chunk budget. This bounds additional arrays; it does not claim the whole tracer has O(K) memory. Unknown inventories are never guessed to satisfy a budget.

`finish` compares received and positive-normal PPFD plus availability masks to the untouched same-call `DirectLight`: atol=1e-10, rtol=1e-9. It returns owned arrays for F (fixtures,S), M (fixtures,S,3), B (fixtures,S,6) ordered xx,xy,xz,yy,yz,zz. These are multiplied by supported one-sided receiver area and have umol/s units. Any unknown path invalidates all ten moments for that receiver/fixture. The first missing reason and unknown path count are retained; this is not an exhaustive path log.

F/M/B are summed and schedule-scaled before feature normalization. F=0 gives zero raw moments with all normalized channels unavailable. For F>0, mean=M/F, concentration=|M|/F and B/F remain defined even when M cancels; dominant=M/|M| is unavailable when |M|<=direction_degeneracy_tolerance*F (schema policy: 1e-12). Opposing illumination remains visible in B. Vectors rotate without translation; B'=R*B*R.T. Actual illumination is a diagnostic, never a predicted growth direction. Native scalar outputs cannot be combined with direct moments as one backend.
