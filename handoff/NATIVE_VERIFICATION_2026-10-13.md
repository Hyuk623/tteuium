# Native continuation verification follow-up

User request: verify the previously delivered native continuation. The earlier report retained incomplete final regression and timeout evidence. Inspect current source/claims; preserve the active Claude F10 engine revision and all flow files. No engine source edits are planned. Run sequentially: boundary/intake tests; a fresh native timeout attempt; affected V3/integration/forecast-consumer regression; independent revalidation of the five completed native runs, replay/off comparisons, carbon residuals and source/flow hashes. Use fresh build outputs, do not rerun interrupted folders. Any failed check is reported separately and never counted as success. Scientific E2/E6/E7 and real NRH gates remain unchanged.

Results will be appended after execution.

## Confirmed finding: boundary-timeout error propagation (P2)

A fresh current-engine run at build/native_verification_20261013_01/timeout used timeout_s=1 and no response. Native exported its actual geometry, leaf inventory and hash-bound request, then the CLI returned a Model prompt without the IllegalStateException text expected by tools/vtc_growth_bridge.py:99. The native throw is at tools/tomato_fsp_boundary_native.rgg:37. The Python controller therefore waited for its outer 180-second limit and reported only TimeoutError: GroIMP timeout (elapsed 180.2084 s), failing the intended specific-error acceptance.

Fail-closed publication was preserved: zero committed future checkpoints, zero native future checkpoints, no native/results package. Unflushed/truncated partial CSV output was quarantined and is not accepted state evidence. The failure does not establish a carbon/state advance; it establishes missing prompt error propagation. Exact evidence is timeout_finding.json plus native/groimp.log and native/execution.json. The verification driver exited 1 as intended for a failed acceptance.

Recommended correction after the active stable-engine F10 run: emit a flushed, request-bound terminal error artifact before throwing, and have the controller validate/read it (with an explicit boundary deadline watchdog as needed). Do not rely on an exception stack trace appearing in the headless CLI. Re-run missing-response/expired-response cases to prove immediate specific errors and zero future publication. No source patch was applied during this verification.
