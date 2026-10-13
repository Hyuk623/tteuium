# Four-project code review launch pack

Date: 2026-10-07. Status: launch pack prepared and snapshot verified. Actual project reviews have not been executed by this preparation.

User request: proceed with common review instructions, four independent project requests and one integration request. Inspect current code paths and contracts, freeze one source baseline including non-Git working files, and give each reviewer separate output paths. No production fixes, new scientific defaults, new conversations or cross-chat dispatch are included in preparation.

This checkout is not a Git repository. The review baseline will be a verified SHA-256 source snapshot under `build/code_review_20261007_01/`, with copied source/tests/configuration/contracts and a manifest. Existing raw data and generated evidence remain read-only references, not copied bulk data. The snapshot must be checked for copy consistency and changes during capture.

## Start here

Use four independent reviewer conversations, one per project, with the same baseline. Each request is self-contained with a link to the common instructions. This preparation has not created conversations or sent messages. Open an existing corresponding review conversation or manually start one, then provide the appropriate request file and local workspace access.

| Step | Request | Review output |
|---|---|---|
| Shared instructions | [Common contract](CODE_REVIEW_COMMON_2026-10-07.md) | Required format and baseline rules |
| P1 | [3D observations, geometry and synthetic evidence](CODE_REVIEW_P1_2026-10-07.md) | `build/code_review_20261007_01/P1/` |
| P2 | [Light transport and reference channels](CODE_REVIEW_P2_2026-10-07.md) | `build/code_review_20261007_01/P2/` |
| P3 | [Growth, direction and calibration](CODE_REVIEW_P3_2026-10-07.md) | `build/code_review_20261007_01/P3/` |
| P4 | [Carbon physiology and nutrient accounting](CODE_REVIEW_P4_2026-10-07.md) | `build/code_review_20261007_01/P4/` |
| After P1-P4 reports | [Integration review](CODE_REVIEW_INTEGRATION_2026-10-07.md) | `build/code_review_20261007_01/INTEGRATION/` |

Example launch message for P1 (replace P1 with P2, P3 or P4):

```text
Read handoff/CODE_REVIEW_P1_2026-10-07.md and its common instructions.
Perform the read-only review against the frozen source, verify its manifest,
and write the requested findings, coverage, boundary contracts and validation
under build/code_review_20261007_01/P1/. Do not implement fixes.
```

When all four reports are available, provide the integration request and their report paths to an independent integration reviewer. Missing or incomplete reports remain pending. Integration should produce one deduplicated repair order with a single owner per issue. Repairs and subsequent revalidation are a later task; this launch pack does not apply them.

## Baseline and evidence

- [Snapshot manifest](../build/code_review_20261007_01/snapshot_manifest.json): timestamp, identity, file hashes and exclusions.
- [Source inventory](../build/code_review_20261007_01/source_inventory.csv): primary routing and file sizes.
- `P1/scope.json` through `P4/scope.json` under the run directory: coverage starting points. Follow cross-project dependencies regardless of routing.
- [Preparation validation](../build/code_review_20261007_01/preparation_validation.json): six request documents, checked explicit source/contract references, and no missing references.
- `source/`: copied source, tests, configuration and contracts. Raw images, generated evidence, model assets and environments are not included. If reviewers use live external artifacts, record their hashes and distinguish them from the frozen code.
- Current `handoff/LOG.md` and `TODO.md` stay outside the snapshot as coordination records. This index also stays outside as the final preparation receipt. Do not mix later live changes into baseline findings.

The P1 request includes F2/F7 and October 7 synthetic-evidence review context. The P4 request includes the October 6 nutrient accounting implementation. Historical passing tests are references only. No production test suite, scientific experiment or actual code review was executed while preparing this pack.

## Preparation receipt

Captured and independently rechecked all **690 files / 8,200,145 bytes**. Every saved file matched its SHA-256; the source inventory and bytes were unchanged during capture. Primary routing: P1 297, P2 72, P3 25, P4 21, shared references 275. Counts describe files, not reviewed coverage.

Baseline ID: `sha256:c867b5ac085829283a2e457244d293508e51f362d50dd7b8aae0feafba00aea5`.

Validated six request documents and 56 explicit source/contract references with no missing paths. Recheck with `python -X utf8 build/code_review_20261007_01/validate_pack.py` and `python -X utf8 build/code_review_20261007_01/prepare_snapshot.py --verify`. The helper scripts and this receipt are preparation artifacts outside the frozen source.
