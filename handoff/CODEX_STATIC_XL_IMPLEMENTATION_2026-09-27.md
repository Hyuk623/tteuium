# Static XL/GroIMP structure export implementation

## Authorized scope
Implement the user's approved file-first pipeline. Read existing per-plant hierarchy, structure and annotation backup snapshots; retain IDs, proposed versus confirmed relationships and diagnostic status. Generate standalone static Model.rgg files, mapping tables, input hashes and Korean opening instructions under build/. Preserve source data and the existing web application. No training, radiation, growth simulation, API orchestration or Document 05 work.

## Implementation and validation
Add tools/groimp_structure_export.py and focused tests. Reuse the existing geometry loader/exporter for optional leaf triangles. Scope identities by plant/session. Unknown locations remain metadata only; centres/axes are display aids, never leaf surfaces. Verify backup hashes before export. Test synthetic units, identities, relationships, missing data and immutable output paths, then export pipeline_20260927_202748 for dwt_01 through dwt_04. Compile and load generated RGG in the installed GroIMP where possible, test reset/save/reopen, and report programmatic versus visual verification accurately.

## Outcome
Implementation in progress. Actual results will be appended here.

## Completion — 2026-09-28

Implemented `tools/groimp_structure_export.py`, `tools/groimp_static_verify.py` and `tools/tests/test_groimp_structure_export.py`. Added the shared `mm_to_m` conversion to the existing OBJ bridge. Existing application, source annotations and pipeline snapshots were preserved. No training, segmentation inference, reconstruction, radiation or growth model was executed.

### Delivered behavior

- Reads the user-selected run, verifies each recorded annotation-backup SHA-256 and plant/session identity, and records the hierarchy, structure, status and optional geometry hashes. Missing or changed inputs fail the affected export. The existing run has no historical structure hash; this limitation is explicit rather than fabricated.
- Exports scoped biological/observation IDs and separate registered, confirmed, unassigned and proposed relationships. Growth JSON counts remain reference metadata. Growth-shoot nodes represent actual photo observations, not inferred unique shoots.
- Static modules: Plant, MainStem, CompoundLeaf, SubStem, Leaflet, GrowthShoot and organizational Group. Existing S7 centres are position markers; existing axes are display lines; optional leaf triangles are actual supplied meshes. Region proposals remain distinct from confirmed biological parent IDs.
- Optional mesh identity must map unambiguously to an existing leaflet. Mesh source and unavailable review status are retained. No filled cuboids, invented leaves, dimensions or optical parameters.
- `showCandidates=false` initially hides candidate geometry. Candidate nodes/relations remain inspectable. Recompilation rebuilds the same snapshot without duplicate organs. The `report` method exposes identities, statuses and metadata; no growth method exists.
- Writes standalone Model.rgg, organs.csv, relationships.csv, coordinates.csv, structure_snapshot.json, export.json and Korean opening instructions. New output folders only. Export manifests remain immutable generation records; subsequent runtime checks have separate verification.json records.

### Artifacts and actual validation

Final four-plant export: `build/groimp_static_20260928/` (start with `사용안내.md`). Runtime evidence: `build/groimp_static_verification_20260928/<plant>/`. Each contains saved.gsz, reopened.gsz, CLI logs and verification.json.

| Plant | Leaflet nodes | Diagnostic centres | Visible by default | Runtime result |
|---|---:|---:|---|---|
| dwt_01 | 7 reviewed identities | 6 | Six centres + main-stem axis | passed |
| dwt_02 | 14 identity proposals | 14 | Main-stem axis | passed |
| dwt_03 | 5 identity proposals | 5 | Main-stem axis | passed |
| dwt_04 | 2 identity proposals | 2 | Metadata tree only | passed |

Real-data exports contain **zero leaf meshes**. MainStem nodes may have unavailable geometry (dwt_04). These counts are not new biological measurements. Confirmed dwt_01 cross-view identity does not confirm compound membership or metric geometry.

Installed Java 21 / GroIMP 2.2.1 actually loaded, compiled, reinitialized, saved and reopened all four exports through GroIMP's CLI. Compared persisted graph nodes, metadata, parent relationships and geometry against Python snapshots. All passed; coordinate transport error is below 0.001 mm. This is transport precision, not reconstruction accuracy. GUI visual inspection remains false.

Synthetic test: `build/groimp_static_synthetic_20260928_v2/DT-001/`, runtime evidence `build/groimp_static_verification_20260928/synth_v2/`. One stem, confirmed/unassigned/proposed parent states and four open triangles were compiled, reset, saved and reopened. Actual PolygonMesh vertices were retrieved through GroIMP's public getter; organ IDs and coordinates passed comparison. Earlier trial directories are debugging artifacts, not deliverables or research data.

Focused regression command: `python -m pytest tools/tests/test_groimp_structure_export.py tools/tests/test_groimp_bridge.py -q` — **8 passed**. Coverage includes backup hash rejection, missing inputs, scoped IDs, mm-to-m transport, no count-generated organs, relationship preservation, optional meshes, unknown mesh identity and runtime graph mismatch detection.

### Reproduction

Run from the project root, choosing fresh output directories:

```powershell
python -m tools.groimp_structure_export --run build/pipeline_20260927_202748 --out build/xl_new
python -m tools.groimp_static_verify --project build/xl_new/dwt_01 --core ../groimp/core.jar --out build/xl_check_new/dwt_01
```

Repeat verification for dwt_02/03/04. `--plant` can be repeated to select plants. Optional surfaces require both `--geometry <existing CSV>` and `--variant <existing variant>`. Source hashes are rechecked after reading. No API service is needed.

GroIMP CLI does not reliably handle quoted directory names containing spaces. The verifier uses Windows short directory paths and explicitly fails if unavailable. CLI model commands are asynchronous, so it waits for each report/save rather than treating process exit code alone as success. Compilers that fail to expose all expected node counts cannot pass validation.

### User steering — Colab fallback

The user requested Colab linkage if local CPU capacity is insufficient. Current static export/verification completed locally; no cloud upload or execution was needed. For subsequent compute-heavy reconstruction/radiation work, prepare a Colab runner with an immutable input bundle, pinned dependencies, input hashes and an explicit Windows-to-Colab path map. Preserve original source paths as provenance rather than silently replacing them. Return new derived outputs with the same plant/session/organ identities, parameters and diagnostic flags, then validate them locally before use. Do not interpret this conditional fallback as authorization to retrain models or publish private photos. GPU availability and CPU/memory bottlenecks must be checked for the actual algorithm; a GPU alone does not accelerate arbitrary Python or Java work. Colab execution and a portable runner are **not yet implemented or tested**.

### Follow-up boundary

Keep `validated_metric=false` and `suitable_for_ppfd=false`. This implementation transports S7 snapshots and does not repair S6 or claim S6 supplied those centres. Next approved sequence remains simple-source light checks, physical PPFD comparison, then canopy layouts. Growth grammars need the separate time-series/model work. The GroIMP GUI should still be checked by a user for presentation and ease of selection; no visual verification is claimed.
