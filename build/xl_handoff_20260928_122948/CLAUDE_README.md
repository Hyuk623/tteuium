# Static XL delivery to Claude

Source run: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis\build\pipeline_20260928_122948`

Delivery status: **runtime_verified**. This is transport status, not research completion.

| Plant | XL result | Upstream open stages | Limited sub-stem axes |
|---|---|---|---|
| dwt_01 | runtime_verified | S4, S5, S6 | 1 |
| dwt_02 | runtime_verified | S4, S5, S6 | 0 |
| dwt_03 | runtime_verified | S4, S5, S6 | 0 |
| dwt_04 | runtime_verified | S4, S5, S6 | 1 |

## Continue from this delivery

- Open `<plant>/export/Model.rgg`; use the organ mapping and metadata in that directory.
- Inspect `handoff.json` for exact source hashes, upstream failures, human tasks and per-plant evidence.
- If verified, inspect `<plant>/verification/verification.json` and its logs. GUI visual inspection remains unverified.
- Recompute after human edits into a NEW pipeline run and a NEW XL handoff directory; do not overwrite snapshots.
- Do not convert masks/hulls/markers into claimed leaf surfaces. Do not infer absent organs from growth counts.
- Preserve hull_trunk provenance, unknown diameter and single-view sub-stem limitations.
- Training, PPFD, growth rules, heavy-step Colab offload and remote Artifact publication are outside this operation.

## Errors

