# Multiview completion prompt integration review

Date: 2026-10-03. User request: read and revise the supplied diffusion prompt for the existing 3D program; review the prompt only, without implementation.

## Reviewed artifact and scope

Revised `handoff/CLAUDE_MULTIVIEW_DIFFUSION_COMPLETION_PROMPT_2026-10-03.md` in place as explicitly requested. Original SHA256: `3CF70250554276FA7C16A694EEE63CA6B293C7F9AA0C430DA6F2AEFD9F79D2CB`. This note preserves the review rationale; existing LOG history remains intact.

Inspected working agreements, current handoffs and source interfaces using read-only file access. No Python module or test was executed; no pipeline, model, renderer or light solver ran. No production code, config, observations, images or weights were changed. The external architecture list was retained as a future research checklist; this review did not verify checkpoint availability, licences or performance.

## Findings and changes

| Finding | Source evidence | Prompt correction |
|---|---|---|
| The original task mixed specification with adapter/notebook implementation | Original Task and Deliver sections | Current work is documentation only; future implementation scope is stated separately. |
| No precise attachment point to the S0-S8 program | `tools/plant_pipeline.py`, S3 `s3` and S8 `s8`; `tools/plant_auto.py` | Saved-input candidate branch, default off; no replacement of source masks, S3 structure or S8 traits. |
| The observed surface comparison is not a mesh-import interface or single-view reconstructor | `tools/leaf_surface_compare.py::run`, `compare_patch`, `load_support` | Keep confirmed-point/local-chart baseline separate; propose an imported-hypothesis adapter and viewer payload. |
| Generated geometry cannot obtain supported observed area merely by using the CSV shape | `tools/compound_surface.py::audit_surface` | Separate hypothesis validation; retain confirmed identity/topology and at-least-two-real-view support requirements. |
| Pose availability differs across consumers | `tools/plant_structure.py::Cameras.BOARD_POSE_STATUSES`; `leaf_surface_compare.compare_patch` | Preserve actual `solved`/`solved_marker_corners` provenance and report consumer compatibility; no status relabelling. |
| Proposed provenance join was underspecified and generic generated enum would be invalid | `tomato3d/io/schemas.py::LEAF_SURFACES_CSV_COLUMNS`, `GEOMETRY_SOURCES`, `NORMAL_CONVENTIONS`; `compound_surface.KEY` | Exact existing face key and column contract; generative `assumed` faces with mandatory sidecar, isolated variants and unknown normals when appropriate. |
| Metric conversion and observed/generated composition were not executable contracts | Existing board-mm triangles and calibrated projections | Require camera/depth/scale mapping, anchor preservation and explicit duplicate/seam/full-surface policy; retain unavailable metric export if not identifiable. |
| Top-only leakage can enter through caches and fitted checkpoints | Original split intent plus S3/S8 dependencies | Audit full conditioning dependency closure, upstream model training splits and evaluation-only poses; add same-input top-only baseline. |
| Parseable geometry or a viewer toggle can be mistaken for optical acceptance | `tools/plant_light_bridge.py::audit` and its `surface_gate` delegation | Require candidate sidecar and separate diagnostic eligibility; never promote review flags to bypass bridge checks. |
| Public model suggestions may conflict with project restrictions | `handoff/CLAUDE_TO_CODEX_MASTER_HANDOFF_2026-10-03.md`, standing model-use rules | Explicit compatibility/availability gate; no inference exception inferred from listing a model. |

## Remaining design decisions

Claude still needs to assess an actually usable and permitted backend, exact supported conditioning, candidate representation, geometry-to-board conversion, observed/candidate composition and statistical/physical acceptance policies. A visibility-aware hypothesis evaluator and viewer payload are proposed additions, not features proved to exist in current code.

Missing reviewed correspondences, curved-fit contract and independent references remain the existing evidence gaps. Generative completion may explore missing structure but cannot replace those observations or establish physical accuracy. No change to the source reconstruction contract or optical eligibility was made.

## Verification

Document verification checks local source references, the exact triangle schema/enums and function names, the stated pose-status difference, prompt scope and preservation of top-only/optical restrictions. This is static document/source consistency review, not software test execution or scientific validation. See the session LOG for the completed check result.
