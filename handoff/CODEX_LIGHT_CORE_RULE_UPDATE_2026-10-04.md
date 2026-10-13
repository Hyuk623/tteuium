# Light calculation ownership update

Date: 2026-10-04, Asia/Seoul.

The user explicitly revoked the calculation-core ownership restriction after reviewing the P2 blocked report, then requested a rewritten light-simulator prompt. In this context the revocation applies to the light calculation core and its relevant tests, not every project's ownership rules.

## Work brief and decision

Previously Codex could edit only the tools adapter and had to wait for Claude Code to implement the actual-path callback in `tomato3d/light/raytrace.py::direct_light`. That ownership dependency is revoked.

Codex may now implement and validate the required light calculation changes directly in `tomato3d/light/` and the relevant light tests under `tests/`, together with its existing `tools/` scope. No separate Claude core-owner approval or delivery is required for this work. Existing core behavior, the actual-path diagnostic contract, scientific evidence requirements and focused regression checks still apply.

Update the parent rules and project AGENTS/CONVENTIONS/CLAUDE entry points consistently. Preserve historical handoff reports and append a superseding notice. Write a new English P2 prompt incorporating the latest lamp placement supplied by the user. This coordination turn changes rules and prompts, not calculation code.

Other ownership boundaries, human configuration/observations, the OneDrive no-concurrent-edit rule, and D1-D10 remain in force. Cross-project linking stays deferred. The prior `blocked` record is historical; this update removes its ownership dependency but does not claim the missing callback exists or automatically change another chat's goal status.

## Verification

Check that all entry points describe the same scoped exception and that the replacement prompt explicitly instructs Codex to implement the producer and consumer integration. Verify referenced files and the three-lamp placement arithmetic. Append LOG/TODO updates. Do not send messages to another chat or run the simulator from this prompt-writing task.
