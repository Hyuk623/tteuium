---
name: claude-review-integrate
description: Review Claude Code changes in the Tomato 3D phenotyping project, integrate them into the existing user workflow, verify preservation and behavior, and write an English handoff. Use when the user asks to check Claude's revision and connect it to existing work.
---

# Review Claude changes and integrate

Work in the Tomato 3D phenotyping analysis project. This skill defines a repeatable workflow; it does not schedule monitoring or authorize model execution, publication, or changes outside the requested scope.

## Establish the actual change

- User preference: before implementing, write or update an English Markdown brief in `handoff/` with the request, inspected status, intended changes, execution boundaries and validation. Proceed after documenting; this is not an extra permission gate. Append actual results afterward.

- Read the parent `공통규약.md`, project `AGENTS.md` and `CONVENTIONS.md`, the last five lines of `handoff/LOG.md`, and `handoff/TODO.md`. Follow current ownership and explicit user transfers.
- Find the newest relevant Claude handoff and read the files it names. Compare with the user's request and existing entrypoints. A completion claim or passing test count in a handoff is not independent verification.
- Use Git diff when available. Otherwise record source hashes and inspect contracts, tests, and generated artifacts; timestamps alone do not establish a change baseline.
- Check for ongoing edits before modifying shared files. Preserve other-agent changes and never restore an old snapshot over newer user work.

## Review the whole user path

Trace photo loading -> identity/bbox/segmentation labels -> saved snapshot -> server/CLI rebuild -> depth/partial surfaces -> linked photo/3D viewer -> export. Inspect only stages affected by this revision, including callers and consumers.

Look for disconnected options: a working CLI feature may still be absent from the browser rebuild route. Check preservation of original pixel coordinates, organ/leaflet/point IDs, occlusion and identity status, deletions, undo, saved browser work, and output freshness.

For geometry changes, retain measured ChArUco poses, explicit frames/units, and original quality gates. Cuboids are diagnostic extents, never leaf meshes or PPFD occluders. Contour indices are not physical correspondences. Interpolated patches are not measured curvature or complete leaves. Do not silently promote unreviewed labels or failed calibration.

## Integrate and verify

- Reuse existing functions and viewers. Make the smallest complete change connecting the requested behavior, not a parallel application.
- Respect the current session's training/inference/simulation restrictions. Saved outputs can be attached without invoking a model. Do not re-run SAM merely to regenerate a review artifact.
- Use an explicit backup, preserve input hashes, and write new results to an unused `build/` directory. Do not reload an editor with unsaved work or change its storage origin to demonstrate a fix.
- Run focused regression tests that exercise behavior and preservation, including the failure/stale path. For server changes, verify the actual request-to-result route, not only the helper function.
- Verify one applicable saved real-data snapshot without changing labels or gates. Inspect the corresponding output and source-photo overlays when geometry rendering changed.
- Distinguish tests run now from historical tests, and code integration from activation in an already-running server. Do not claim activation without checking the process and route actually serving the user.

## Finish

Write an English dated review/integration handoff with inspected changes, findings and fixes, exact reproduction commands, validation evidence, preserved inputs, remaining limitations, and any required server restart. Append the project LOG and relevant TODO items without rewriting history. Report the result briefly in Korean.

If invoked for review only, report actionable findings without implementing them. If integration is requested, continue through fixes and validation within authorized ownership. Do not send messages to Claude or other people merely because this skill is invoked.
