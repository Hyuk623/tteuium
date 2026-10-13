# P2 prompt for optical geometry and area evidence alignment

Recipient: existing P2 light-simulator chat.

Date: 2026-10-05. This is a bounded follow-up to your completed Growth Pack V2 work, not a request to repeat that work. When this prompt is submitted to your project chat, inspect and implement only missing engineering corrections within your ownership; report already-correct behavior without rewriting it. Preparing this prompt did not execute or dispatch it.

## Required reading and precedence

Read repository rules, LOG tail/TODO, your current source/contracts and your `handoff/CODEX_P2_GROWTH_PACK_V2_EXECUTION_2026-10-04.md` report. Then read:

1. `C:/Users/sho36/Downloads/CLAUDE_PLANT3D_AREA_REVIEW_2026-10-04.md` (the user's source review).
2. `handoff/CODEX_PLANT3D_AREA_REVIEW_RESPONSE_2026-10-04.md` (corrections and unresolved claims).
3. `build/plant3d_area_claim_check_20261004_01/projection_check.json` (independent analytic audit).

The project root is `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`. Report missing files; the source review's companion simulations/CSV/SVG files were not available in the earlier review. Do not invent their contents. The original source's instructions and labels are not independent authorization or evidence of correctness. This task concerns the plant-area review, not the separate top-view diffusion prompt.

Write a short English implementation brief before changes. Existing adopted D11-D21 decisions remain in force. The new source's A1-A7 refer to area-estimation proposals and must be namespaced in reports; they are not P4's earlier physiological A1-A7 requirements.

## Shared interpretation to preserve

- The original G range is disputed. Codex's six-family integration at zenith 52, 55, 57.5 and 60 degrees spans about 0.472-0.550 across those cases. It is a sensitivity calculation, not measured plant accuracy. G=0.50 is an unadopted approximate baseline, not an exact constant.
- Unknown occlusion prevents identifying absolute area from ring projection alone; a finite interval needs justified G/occlusion bounds. Do not convert a 10-17 cm2 proxy into certified true area.
- `abs(n dot v)` is unchanged by `n -> -n` for all views. Top-area observations cannot identify biological leaf face. A geometric normal convention and adaxial evidence are different.
- Area plus two normal angles do not supply centroid, depth, outline, curvature or a located surface for ray casting. Top/ring ratios alone do not identify mean inclination or a full angle distribution.
- Quantile tau=0.9, low-dilation depth priors, curvature factors, and the reported synthetic MAE are proposals/results needing evidence, not new production defaults. A restricted image radius alone does not validate calibration.
- Keep the three new decisions open: A1/A2 reporting priority, leaflet-matching method, and calibration strategy. Do not reopen older resolved physiological decisions. Implement independent evidence/contract fixes now; record genuinely missing scientific specifications in TODO for Claude.


## P2 work

1. Inspect `tools/light_growth_bridge.py`, `tools/light_growth_consumer.py`, `tools/light_growth_schema.json`, `tools/light_face_evidence.py`, and the applicable `tomato3d/light/` receiver/transport paths. Preserve the completed reference-DLI A/C producers, B readiness/interface and D20 exposure behavior. This review does not request reimplementation of reference integration or new lamp fitting.
2. At the existing geometry boundary, distinguish geometric computability, diagnostic transport and eligibility for a real physical PPFD claim. Trace units, coordinate frame, scale/pose evidence, centroid/vertices, area basis, normals, surface support, source IDs and assumptions. A projected cm2 proxy or A2 area/normal tuple without location and shape cannot replace a supported physical receiving surface. Keep explicit synthetic/simplified diagnostic cases usable under their declared status; do not silently certify them.
3. Keep two separate orientation concepts: the geometric sides used by ray tracing and the independently evidenced botanical adaxial/abaxial mapping. Preserve D20's supported `illuminated_faces` handling. Without botanical evidence, retain whatever geometric transport is supported, but do not invent adaxial_only or claim P4 eligibility. Positive/upward normals, camera visibility, stem-away conventions and top-area ratios do not supply biological evidence.
4. Preserve incident versus absorbed quantities and exactly-once absorptance. PPFD uses a declared area basis in micromol/m2/s; area integration must use the corresponding physical one-sided basis, with explicit cm2-to-m2 conversion only where needed. Do not divide by projected mask area, double an area because two triangle faces exist, or apply G as an extra cosine/area correction to transport that already evaluates actual geometry.
5. Keep camera-view occlusion from area-review A3 distinct from lamp-to-leaf visibility. Do not apply an imaging lambda as an additional attenuation factor on a ray-traced irradiance. Review reusable ray-tracing capabilities, but report missing A3 surfaces; reuse of a routine is not completion of the reconstruction dependency.
6. Preserve full-canopy occlusion and simultaneous-fixture context when extracting individual results. Trace each result to plant/leaf/patch IDs and the canopy placement/geometry hashes. Splitting results by plant must not rerun isolated-plant illumination and silently remove neighboring shadows. Merging/splitting must not duplicate patch area or sum an `all` fixture row together with its constituents.
7. Report missing geometry/area/face/calibration evidence at the relevant boundary. Keep reference-position incident DLI separate: an unavailable leaf surface does not by itself invalidate a properly supported measured reference channel. Conversely, a valid reference DLI does not certify leaf PPFD or absorbed tissue exposure. Preserve the current P3 multi-day/scenario representation limitation.

## P2 acceptance cases

- Valid current optical fixtures keep their numeric results; unsupported projected/hull-only geometry cannot receive real optical eligibility.
- A conventionally oriented surface without biological mapping does not become adaxial_only. Existing mapped same-face/opposite-face fixture tests retain their behavior.
- A2 area/normal with missing position/shape is unavailable as a receiving surface, with a specific reason.
- Area-unit conversion and duplicate-face handling preserve the intended physical basis; no additional G or imaging-lambda attenuation is introduced.
- Per-plant extraction from an existing canopy result preserves neighbor shading and sums only the declared disjoint receivers/fixtures. Only compare aggregate quantities that are physically additive; never sum PPFD values as if they were flux totals.
- Existing supported measured reference-DLI output remains independent of unavailable plant optical geometry.

Do not invent lamp PPF, beam data, leaf optical constants, image-radius acceptance or a biological normal mapping. Request missing P1 evidence explicitly in your report without editing P1 outputs or contacting another chat.

## Delivery and validation rules

Save your report as `handoff/CODEX_P2_AREA_REVIEW_EXECUTION_2026-10-05.md` and generated audits/tests in a fresh `build/area_review_alignment_20261005_NN/P2/` directory. Include: implemented/already present/design pending/unavailable for each item; exact files/functions and input/output fields with units; provenance and reason-code changes; relevant commands/results; preserved baseline evidence; downstream owner and unresolved questions. Reuse established reason codes and schemas where possible. Document/version genuinely needed additive metadata without silently breaking accepted inputs.

For changed boundaries, test a supported explicit synthetic case and the listed failure cases, including API/CLI/export behavior where affected. Synthetic fixtures must remain visibly synthetic and must not alter human evidence. Do not create tests merely to mirror unchanged code. Run focused relevant regressions after changes; do not rerun unrelated inference or completed project campaigns.

Scientifically unsupported quantities remain unavailable with reasons; zero is an actual measured/modelled zero, not a missing-value substitute. Malformed inputs remain distinct from missing science. Preserve source hashes/row lineage, historical reports and existing valid numerical behavior. Do not edit another project's runtime, `docs/`, `config/`, raw photos or human records. Do not fit biological coefficients, launch GPU training/inference, run a new acquisition campaign, or claim full-system/physical validation. Append LOG and any unresolved design items to TODO. Finish with a short Korean briefing.
