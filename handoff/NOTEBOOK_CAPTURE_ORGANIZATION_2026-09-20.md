# Notebook capture organization

## User request

Inspect the notebook open in the side browser and prepare tomato capture-data organization using `dwt_00_xxxxxx`: dwarf tomato prefix, individual plant number, and capture date in that order.

## Plan and boundaries

- Inspect the existing notebook UI before choosing the deliverable or editing it.
- Use zero-padded two-digit plant numbers and provisionally interpret the six-digit date as YYMMDD, consistent with the user's earlier capture names. State this interpretation in the user-facing result.
- Distinguish a stable plant ID (`dwt_01`) from its dated capture session (`dwt_01_260920`).
- Preserve existing photos, labels, source names and notebook sources. Do not rename/move photos or upload local files without a corresponding request.
- Prepare a concise Korean organization template suitable for the notebook, maintaining the current requested 25-view layout as a plan rather than asserting each existing session has 25 valid photographs.
- Inspect browser availability; record any access failure honestly and prepare a local deliverable if the notebook cannot be edited.

No model inference, reconstruction, or PPFD simulation is part of this task.

## Outcome

Inspected the visible Gemini Notebook titled Tomato Modeling (Korean UI): source documents and a Studio panel with Add note were present. Attempting Add note timed out; subsequent DOM and screenshot calls also timed out, so remote note creation is unverified. No successful paste or upload occurred. Avoid claiming the notebook was updated. Created a Korean paste-ready Markdown artifact under build/notebook_capture_organization_20260920, including stable plant IDs, YYMMDD session IDs, planned 25-view naming, original/converted provenance, a session template and a Notebook prompt. No source photographs were renamed or moved.

## User-requested retry

Retry the same notebook with a fresh browser binding, inspect for a partially created note before writing, and save the prepared capture organization as a notebook note. Verify persistence through the visible UI; do not duplicate or claim success from an attempted click.

Retry outcome: the existing tab remains visible in inventory, but selecting it timed out on the browser control focus command. Creating a fresh same-notebook tab failed to attach; final inventory still contains only the original tab. No text was entered and remote persistence remains unverified. User-side browser refresh/reopen is needed before further UI work.

## Completed after user refresh

The refreshed notebook became accessible through the documented DOM browser interface. Studio contained one empty New note from the earlier attempt. Reused that empty note, titled it '드워프 토마토 촬영데이터 정리 — dwt_00_YYMMDD', and filled naming rules, per-session record template, planned 25-view filename examples, manifest fields, and the Notebook analysis prompt. Verified the entered body in the UI and closed the note; Studio then displayed the saved title. No duplicate note, source conversion, photo upload, file rename, or model run was performed.
