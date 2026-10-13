# Four chat prompts for the growth science review

Date: 2026-10-04. Author: Codex. Scope of this preparation: prompts and decision recording only.

The user requested separate prompts after reading [Claude Science review](CLAUDE_GROWTH_PACK_SCIENCE_REVIEW_FOR_CODEX_2026-10-04.md), accepting its section 4 decisions 1 and 3 as recommended and leaving decision 2 undecided. These refer to section 4, not the three source checks in section 5.

## Recorded decisions

| Item | User answer | Consequence |
|---|---|---|
| Question 1 | Adopt recommendation | P3 uses incident DLI at one declared reference position/plane, full local-day coverage, whole-plant model scope and a declared applicability interval. Its basis is distinct from P2 tissue area bases. |
| Question 2 | Undecided | Do not select before_mito versus net_leaf, the P4 light basis, or adaxial-only versus another face model as an adopted real-use policy. Preserve existing explicit modes and unresolved scientific gates. Source reading can proceed. |
| Question 3 | Adopt recommendation | Declare c_DLI per growth_curve, reject one shared binding across exponential and beta families, enforce applicability, and represent the specified low-DLI failures as structured unavailable outcomes. No numerical coefficients are supplied. |

Optional G03 reanchor weighting, G06 transient-posture correction and G07 truss_observable selection were not answered. Do not implement or select them through these prompts. Existing behavior is retained and its limits documented.

## Prompts to paste into the existing chats

| Chat | Prompt | Scope |
|---|---|---|
| P1 3d구현 | [P1 prompt](CODEX_P1_GROWTH_SCIENCE_CHAT_PROMPT_2026-10-04.md) | Observation support, identity, area, frame and uncertainty readiness; no new inference or capture campaign |
| P2 광시뮬레이터 | [P2 prompt](CODEX_P2_GROWTH_SCIENCE_CHAT_PROMPT_2026-10-04.md) | Reference DLI versus tissue light, complete-day semantics and directional provenance |
| P3 생장방향 | [P3 prompt](CODEX_P3_GROWTH_SCIENCE_CHAT_PROMPT_2026-10-04.md) | Decisions 1/3; F2, F3, F7-F9, F11; sole editor of growth calibration |
| P4 토마토 FSP | [P4 prompt](CODEX_P4_GROWTH_SCIENCE_CHAT_PROMPT_2026-10-04.md) | F1, F4-F6, F10; original-source checks; question 2 remains open |

These prompts are instructions for the recipient when the user submits them. Creating the files has not dispatched messages or executed their implementation tasks. D1-D10 remain effective; cross-project adapters and runtime feedback remain deferred.

## Ownership and verification

P3 alone edits `tools/probabilistic_compound_growth.py`, `tools/growth_calibration.py` and their schemas/tests/guides for this work. P4 alone edits `tools/fsp_carbon_diagnostic.py` and its schema/tests/guide, and creates the versioned equation registry. P1/P2 do not modify either owner's files. Shared LOG/TODO entries are append-only and each project writes a distinct execution report.

Existing K02 semantic protection is already implemented and verified; F9 extends it. Read [guard verification](CODEX_P3_SEMANTIC_GUARD_REVIEW_2026-10-04.md), not the earlier open-gap wording. The Science reviewer explicitly did not inspect several code ranges: each recipient must verify its actual functions before changing them.

Completion of this preparation: four English prompts and the decision addendum were saved. Reference/coverage verification is in `build/growth_science_chat_prompts_20261004_01/verification.json`. No implementation, model execution, new coefficient adoption or cross-chat dispatch occurred here.
