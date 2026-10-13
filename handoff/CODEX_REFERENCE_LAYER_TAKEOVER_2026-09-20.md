# Codex takeover: JSON reference-layer verification

User asked Codex to continue Claude's reference-layer mutation/full-test work. Latest Claude completion reports 213 tests passed, 1 skipped and 16 caught mutations, but an additional full-suite process was still running at initial inspection and then exited. This task independently verifies current code, resolves relevant failing checks, and records outcomes. Do not rerun historical mutation loops on shared source files. Preserve parallel side-conversation artifacts, human records, captures and annotations; no model inference/training or PPFD.

Start with the focused reference/hybrid tests and the current full tools suite. Inspect failures before repeating. Mutation spot checks, if needed, must be isolated from shared source files. Do not claim Claude's historical test results as independently reproduced.

## Resume after Claude session limit

User supplied Claude's exhausted-session notice after asking Codex to wait; continuation resumes now. Initial independent full-suite result was 212 passed, 1 skipped, 1 failed: an unauthenticated mock-segmentation POST aborted its TCP connection (WinError 10053) instead of returning the expected 403. Inspect and reproduce before changing behavior; do not weaken authentication or hide failures with retries. Also complete isolated reference-layer verification and preserve concurrent side-conversation artifacts.

## Completion: independent verification

- Initial full tools suite: 212 passed, 1 skipped, 1 failed in 69.99 s. Failure was WinError 10053 while an unauthenticated mock `/api/segment` POST awaited its expected 403 response (`test_server_segment_endpoint_requires_token_and_writes_nothing`). No authentication changes or retry masking were introduced.
- Focused retry prompted by that failure: failing endpoint test plus all 14 reference tests, **15 passed in 6.87 s**.
- Final full tools suite: **213 passed, 1 skipped in 62.05 s** (`python -m pytest tools/tests -q --tb=short`). The connection failure did not recur; its underlying intermittent cause is not established or claimed fixed.
- Independent mutation spot checks: **4/4 caught** by assertions. Cases: ignore changed reference hash; merge local point IDs across leaflets; accept unposed observations as rays; count unconfirmed identities as confirmed. Each ran in a separate interpreter using mutated module text in memory. Shared application source was never modified. Evidence: build/reference_layer_takeover_20260920/mutations.json and individual logs; reproduction: python build/reference_layer_takeover_20260920/mutation_check.py. This does not independently reproduce Claude's historical 16-mutation count.
- The initial mutation-results classifier missed pytest's shortened `E assert` format for two expected assertion failures. Saved logs were inspected and classification corrected without rerunning or changing tests; all four failures were intentional assertion detections, not import/syntax errors.
- Read-only load_request checks of build/reconstruction_requests_20260920/dwt_01.json and dwt_02.json both report ready with no reference findings. This checks these manifests and their referenced files, not completeness of labels or metric accuracy. Evidence: saved_requests.json.

## Preservation and handback

No application/test-source changes, human JSON changes, session regeneration, model inference/training, PPFD execution or live-editor restart were performed. Only this handoff, TODO/LOG appendices and isolated build verification artifacts were written. Do not restore historical mutant files over current code on Claude resume.

Reference layer verification is complete for this takeover. If the HTTP connection error recurs, retain the failure details and investigate connection teardown with unread rejected POST bodies and Windows network conditions; this is a hypothesis, not an established diagnosis. No repeating mutation/full-suite loop is needed solely because Claude resumes at 23:30.

Separate side-conversation work progressed while these tests ran: the latest LOG now reports six user-confirmed dwt_01 correspondence pairs in build/dwt01_rgb_multiview_20260920/confirmed/. The reference manifests checked here still point to their original snapshots. Do not summarize the whole workspace as having no labels; inspect the intended snapshot before a future reconstruction. No side-conversation results were changed or merged by this verification.

Full three-route UI/fusion work and independent geometry validation remain separate from this completed reference-layer test task. Importer F1 remains a known separate open item. Passing software tests does not establish validated dimensions or PPFD readiness.
