# P2 V2 alignment execution

Date: 2026-10-04. Work is in progress; no completion claim.

Implementation brief and reference-channel evidence: CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md. This report will record D19/D20 and P2-a through P2-h, changed consumer guidance and unchanged physical transport. D15-D18 supersede active guidance that P4 question 2 is undecided: the dwarf-source route consumes absorbed PPFD with before_mito and evidenced adaxial_only exposure, while P4 owns face/physiology refusal and coefficient-basis issues. P2 must not clip, halve or relabel physical light to satisfy that policy.

## Interim stage 02

D19 is published and imported. P2-a through P2-h now have standalone measured-channel implementation and focused tests; whole-package acceptance is still pending. The channel report records 105 passing current tests, two 11.52 mol/m2/day synthetic CLI results, one truthful simulation refusal, blank real templates and the measurement checklist. Stage evidence: `build/technical_review_fixes_20261004_01/P2/reference_stage_02_verification.json`; all 21 protected hashes match. D20, existing package integration, bounded P3 compatibility and the final requirement-by-requirement audit remain incomplete. This entry is progress, not delivery completion.

## Final bounded V2 delivery, 2026-10-04

The final section of CODEX_REFERENCE_DLI_CHANNEL_EXECUTION_2026-10-04.md supersedes the interim status and contains APIs, fields, all nine source acceptance results, exact commands, current artifact paths and physical limitations. This P2 scope is delivered; simulation execution and full-system/biological use remain explicitly deferred.

| Item | Status | Evidence |
|---|---|---|
| D19 | Done | Single `DLI_UNIT='mol/m2/day'` in common; P2 imports, canonical round trip and named legacy refusal. Shared-file SHA256 remains `320775dfb182b4fb78c5aa77619a7dab7258a7a3c0f11f32d2f157ba4585825a` |
| P2-a | Done | Distinct interval mean / instantaneous adapters, explicit support/gap policy and transition-inside-interval tests |
| P2-b | Done | Cosine metadata false/unknown preserved; every affected row flagged; leveling evidence required |
| P2-c | Done | Every route reports asserted_not_measured absent qualifying daytime off measurements; contradiction refused |
| P2-d | Done | Error/gradient-derived finite radius, explicit local survey support; flat/underdetermined/outside support refused |
| P2-e | Done | Explicit plant association and all-location survey/uniformity test; package/canopy-copy scope retained |
| P2-f | Done | All selected dates retained; declared spread/tolerance test; variable horizon unavailable; supported multi-day mean tested |
| P2-g | Done | Aware UTC reconstruction, actual 23/25-hour days or explicit refusal |
| P2-h | Done | Producer/package consumer tissue separation plus current P3 reverse-basis refusal |
| D20 | Done | Actual transport sides + reviewed biological mapping, fixture/time aggregation and independent/P4 metadata gate tests |
| Active P4 guidance | Done | D15-D20 absorbed / before_mito / evidenced adaxial_only; P4 owns both-face refusal and coefficient-basis issue, no extra absorptance |
| Existing transport | Retained | No light-core numeric edits; exact five-table historical and fresh parity; existing Native unavailable behavior and budgets |
| Route B execution | Deferred as requested | Interface/readiness delivered, no PPF invented, fit/trace never run |
| P3 non-single-day use | Explicit schema limitation | Producer modes delivered; bounded mapper refuses fake representative-day conversion |

### D20 fields and identity contract

`tools/light_face_evidence.py::bind_face_mappings` consumes optional reviewed `face_mappings` request entries keyed by snapshot/instance/session/organ/leaflet/original triangle, with exact geometry hash, reviewer, evidence path/hash and normal_biological_face. `classify_face` only labels actual strictly positive normal/opposite incident PPFD. It never changes photon values. Full-output, scheduled real-fixture and re-summed all rows are classified separately. Same-face fixtures preserve normal sums; opposite-face fixtures produce both. Zero, unknown exposure and absent mapping produce unavailable enums with reasons. No user/source mesh-normal label alone establishes a biological face.

Added nullable sample columns: `normal_biological_face` (adaxial/abaxial), `illuminated_faces` (adaxial_only/abaxial_only/both), `face_mapping_id`, `face_source_ref` (`face_mappings.json#id`). Nullable strings use the existing unavailable token with field-specific availability reasons; required identity sentinel semantics are unchanged. `face_mappings.json` binds reviews; `reference_channel.json` and its copied directory bind reference evidence. The independent consumer verifies original request, source hashes, geometry, enum semantics and actual side sums, including after rehashed output tampering. Native supplies no face samples. No two-sided physiological model or source-basis relabel was implemented.

Actual direct-path tests call the existing solver and then the current P4 `_combined_face` metadata gate only: opposite faces are refused as two_sided_exchange_unavailable; same-face metadata passes with unchanged summed PPFD. No P4 exchange or P3 forecast was executed. The reference mapper passes actual produced data to current P3 `_validate_d9` without changing its runtime or frozen model fields.

### Preserved core callback contract

`tomato3d.light.raytrace.direct_light(receivers, fixtures, occluders, leaf_transmittance, settings, *, diagnostic_callback=None, diagnostic_max_paths_per_chunk=None) -> DirectLight` remains unchanged. Synchronous `direct-angular-1` paths include fixture ID, global receiver index, stable supplied-emitter index, receiver/emitter/expected counts, half-open path_start/path_stop, attenuated/cosine-weighted incident PPFD in umol/m2/s before area, and receiver-to-emitter grow-frame unit vectors (opposite photon travel). Validity and missing reasons are explicit; unavailable fixture inventory emits a fixture_unavailable event, not an empty zero inventory. All dark/unknown paths are accounted for. Receiver-major contiguous ranges support duplicate/gap checks. Buffers/mappings are borrowed/read-only until callback return; copy to retain. Exceptions abort; positive chunk budget is mandatory when enabled; disabled calls allocate no diagnostic buffers. No alternative tracer or lamp-center direction is used.

F/M/B stay area-weighted unnormalized actual-path moments in umol/s; sum before normalization/rotation, retain B under opposite-direction cancellation, and keep observed axes separate. New reference/face metadata does not alter shading, self-triangle exclusion, leaf crossing counts, optics, supported one-sided area, schedules, background or native/direct separation.

### Verified delivery

175 unique passing cases across the current reports; read-only `verify_delivery.py` verifies the full evidence inventory. Six fresh packages (unannotated/annotated main and two splits each) and three standalone reference artifacts validate. All 21 protected hashes match. The delivered annotated package has 1,344 samples / 1,080 features / 14 intervals / 48 dose rows, numerically identical to the historical Growth Science package. Actual angular inventory reports 56 receivers, 224 paths per fixture, chunks <=127 and 10,752 accumulator bytes. Numerical tolerances and resource evidence are in the channel report/completion audit.

Deliverable root: `build/light_growth_v2_20261004_02/`; current standalone A/C/B artifacts `_06`, `_05`, `_07`; real blank templates/checklist `_02`. Technical evidence: `build/technical_review_fixes_20261004_01/P2/completion_audit.json`, `delivery_checks.json`, JUnit and reproducible read-only audit script. Final source hashes are in that JSON. Historical packages/hashes and interim failed/passing reports remain intact; new code never rewrites old artifact hashes to pass.

Physical/reference/optical inputs remain unverified and are listed in the channel report. The user-confirmed three REF-30-40 lamps, 16-hour daily lighting and 100% output setting are preserved; start/end clock times are not inferred. The Korean checklist does not claim meter arrival or completed measurement. Coordination owns the shared technical roll-up; this task did not edit it or message other chats.
