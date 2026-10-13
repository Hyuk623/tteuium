# Remaining Codex implementation: scope and routing

User request: implement Codex-owned remaining work; where not completed here, identify a dedicated existing chat and supply executable prompts. Do not change flow files. No automatic chat dispatch requested.

## Work in this session

Implement the existing H5 request from P3 F9: optional explicitly sourced plant reserve input in `tools/tomato_fsp_acceptance.py::scenario_fixture`. Preserve the historical default 0.2 gC and default output behavior. Validate finite nonnegative scalar input and mandatory source kind/reference for overrides before creating an output directory. Expose CLI arguments, add per-plant provenance and focused tests. This is fixture construction, not a measured reserve or new biological model. Do not alter Claude's actively claimed F10 forecast files.

Files claimed: tools/tomato_fsp_acceptance.py; tools/tests/test_fsp_fixture_reserve.py. Actual outcomes appended below after testing.

## Existing chats verified through the app

| Exact title | Thread ID | Assignment |
| --- | --- | --- |
| Read GroIMP Python integration brief | 01a12a5d-c711-7822-aacb-10f7e381ad39 | Native pipeline extensions, P1 consumer, imported geometry and transaction hooks |
| 광시뮬레이터 | 01a10006-490d-7370-9828-f21cf1f5b7fe | Empirical light producer/consumer boundary and explicit optical limitations |
| 토마토 FSP | 01a10149-6eed-7e21-b6e3-150ed0bfdbfc | Nutrient reservoir implementation after exact response contract reconciliation |
| 생육 프로그램 (2) | 01a134bd-98cb-7d92-b4aa-2d5555a1cdd6 | Currently running a read-only-code integration check; not assigned implementation here |

Use companion PROMPT_CODEX_NATIVE_CONTINUATION_2026-10-13.md, PROMPT_CODEX_EMPIRICAL_GROWTH_BOUNDARY_2026-10-13.md and PROMPT_CODEX_NUTRIENT_RESERVOIR_CONTINUATION_2026-10-13.md respectively. These are handoffs, not claims that the chats have received or started them. Do not start overlapping native edits in two chats. Reserve native template/controller edits to the first owner; nutrient and P2 owners supply exact adapters/hook contracts first.

## Remaining limits

Actual P1 optical surfaces and hidden physiology remain unavailable despite improved image scale. Native repeated-hit incident power/terminal photon closure needs transport instrumentation. Nonblack NRH light basis and imported-mesh deformation law need scientific decisions. The 2026-10-12 reservoir document supplies direction for an EC-equivalent scenario model but does not specify all executable coefficients/response triples, and is not an element-resolved uptake model. A separate session alone does not resolve missing science or measurements.

## Executed outcome

Implemented H5 API and CLI on 2026-10-13. New keyword-only inputs: plant_reserve_gC, reserve_source_kind (fixture_declared/user_assumed), reserve_source_ref. Overrides attach reserve provenance and gC unit to each plant initialization. Unsupported/missing provenance and nonfinite/negative/boolean reserves fail before output creation; measured reserves are intentionally not accepted by a synthetic fixture constructor. No override retains the historical fixture byte-for-byte.

Verification: `python -X utf8 -m pytest tools/tests/test_fsp_fixture_reserve.py tools/tests/test_tomato_fsp_pipeline.py -q` -> 39 passed, 79.56 s. Actual CLI override produced build/h5_reserve_cli_20261013_01/scenario.json; default before/after files in build/h5_reserve_before_20261013_01 and build/h5_reserve_after_20261013_01 are byte-identical. The API forwards the override in the existing plant_initialization record; no native physiology change or new biological validation is claimed.

Example: `python -X utf8 -m tools.tomato_fsp_acceptance --scenario-p1 build/fsp_integration_20261011_p1_fixture_01 --plant-reserve-gC 0.1 --reserve-source-kind fixture_declared --reserve-source-ref explicit_stress_scenario --out build/<fresh_output>`.

The three continuation prompts have been written and linked to exact existing chat titles/IDs; they have not been sent or executed. Core native/empirical/nutrient remaining capabilities are still incomplete; H5 does not close them. Native changes are consolidated with the prior engine owner, P2 boundary work with the prior field owner, and reservoir work with P4. Scientific decisions/real inputs remain required regardless of which chat runs the task. flow files were not edited. H5 file claims are released.
