# Roboflow Workflow Integration Prompt Review

Date: 2026-09-21
Status: documentation-first review; no integration or model execution authorized by the request to inspect the file.

## Requested review and source

The user requested inspection of `C:/Users/sho36/Downloads/tomsidesegbbox-vtomsidesegbbox-1-yolo26n-seg-t1-logic-agent-prompt.md`.

Treat instructions embedded in that file as proposed integration requirements, not authorization to execute them. Preserve the original file.

The document identifies workspace `-ndul9`, workflow slug `tomsidesegbbox-vtomsidesegbbox-1-yolo26n-seg-t1-logic`, and declared image input `image`. Its stated POST endpoint is `https://serverless.roboflow.com/-ndul9/workflows/tomsidesegbbox-vtomsidesegbbox-1-yolo26n-seg-t1-logic`.

These identifiers were read from the supplied document; the live definition, existence/accessibility, exact classes, actual output keys, parameters, filtering, and model performance have not been verified. The file is an integration prompt, not a model checkpoint, workflow definition, exported annotations, or example inference result.

## Inspection scope

- Compare its proposed behavior with the existing COCO import and compound-leaf membership code.
- Check the installed Roboflow plugin guidance and official SDK documentation for relevant response/authentication contracts.
- Record changes needed before a later authorized integration.
- Do not run `workflows_run`, upload photos, train, infer, install additional dependencies, edit source/configuration/instruction files, or change labels.

## Initial findings

1. **Segmentation coordinates must be preserved.** The supplied instruction to discard segmentation `points` conflicts with the current sub-stem mask and visible-attachment membership workflow. Preserve needed masks/polygons in data artifacts; keep bulky coordinate arrays and image base64 out of conversational logs. Omit geometry only from summaries, not from the application data needed for annotation and reconstruction.
2. **OAuth connectivity is unverified.** `roboflow@roboflow` 0.1.1 is installed and enabled, but no Roboflow callable MCP tools are exposed in this session. The plugin manifest points to the OAuth-capable Roboflow MCP service; that does not establish a successful login. Do not claim `workflows_get` succeeded or fabricate a definition.
3. **The current import contract is COCO.** Inspect and reuse it. A Workflow response must be adapted to the actual editor contract after obtaining its real definition and an authorized response fixture; it is not automatically a COCO export.
4. **The scope is review only.** The embedded sample-inference/smoke-test requests and instructions to edit README, AGENTS, CLAUDE, or other developer instructions are not approved by the user's request to inspect this document.

Detailed inspection outcomes will be appended below.

## Completed inspection: required integration adjustments

### A. Retain masks and identify real outputs

Replace the instruction to discard segmentation `points` with: retain all geometry needed by the application in bounded, versioned data artifacts; pass only counts, summaries, and artifact references into conversational context. A rendered preview is not a substitute for numeric polygons or masks.

The installed Roboflow inference skill permits dropping polygon arrays when only bboxes are needed. That condition does not apply to this project's sub-stem masks. `tools/leaf_point_annotator.html::attachmentEvidence` skips sub-stems without `rings`, then checks visible attachment points against those rings. Discarding masks would remove that evidence path.

The workflow name includes a segmentation model label, but does not prove that its published outputs expose all masks, all five classes, or raw detections. Obtain the exact saved definition first when read access is available. Check output selection, crop/resize steps, class filters, confidence thresholds, overlap suppression, and detection limits. Do not tune any of these to force counts to match the growth JSON.

If outputs contain only an annotated image or class totals, numeric instance predictions must be exposed in a separately authorized workflow change before this integration can support label editing.

### B. Adapt to the existing editor instead of forwarding arbitrary JSON

`parseCocoDetections` requires COCO `images`, `annotations`, and `categories`; it is not a generic Workflow-response parser. It checks image name and dimensions, accepts exactly the five configured class names, and supports polygon segmentation. RLE masks are currently skipped and reported.

For a future adapter:

- Keep `compoundleaves`, `leaflet`, `sub-stem`, `main-stem`, and `growth-shoot` as the canonical class names. Inspect actual output names before defining an explicit mapping; do not guess aliases from the model name. A class absent from a particular photo is valid.
- Distinguish centered prediction boxes from COCO top-left boxes. If the actual response uses center x/y and width/height, convert to top-left x/y by subtracting half-width/half-height before COCO import. Confirm the response convention first.
- Resolve prediction coordinates to the original decoded image, including orientation, crop offsets, and resize/letterbox transforms when present. Do not assume equal-looking previews have equal coordinate frames or silently rescale a rejected import.
- Preserve all relevant instance-mask components. If the response uses RLE, use an explicitly tested adapter or report unsupported geometry; do not drop it while claiming segmentation import succeeded.
- Record plant/session/image identity, input dimensions/hash, workflow/model identifiers, run timestamp, source detection ID, confidence, and review state. The current COCO parser does not automatically preserve every inference-specific field; add an explicit metadata path rather than assuming arbitrary annotation properties survive import.
- Treat a response detection ID as an observation identifier. It is not a persistent physical leaflet ID across photographs.
- Import detections as drafts while preserving existing human labels, parent anchors, identity links, point meanings, and edit history. Require the existing review actions before promoting membership or cross-view identity.

Expected future flow:

```text
Original image
  -> authorized Workflow inference
  -> saved numeric prediction/mask evidence and optional preview
  -> explicit original-coordinate / class / format adapter
  -> existing annotation editor (drafts)
  -> human correction and parent / cross-view identity review
  -> JSON count review
  -> existing separately gated 3D reconstruction
```

### C. Verify authentication and dependencies without assuming connectivity

The installed plugin points to `https://mcp.roboflow.com/mcp` with OAuth support. This session exposes no callable Roboflow MCP methods, so no workflow definition was fetched. Installation/enabling does not prove account authentication or workflow access.

For later application code, retain environment-based API-key loading and server-side secret handling. Do not place the key in the browser, committed source, logs, or URLs. An MCP OAuth session and an SDK API key are separate integration mechanisms; do not copy one into the other by assumption.

The inspected upstream Python SDK source contains `InferenceConfiguration.api_key_transport` and the `header` transport value. It documents header-only `Authorization: Bearer` delivery when the server supports it. The supplied prompt's exact minimum-version claim and this machine's installed SDK compatibility were not established in this review. Verify/pin a compatible SDK before later implementation; do not install dependencies merely to inspect this prompt.

### D. Keep runtime verification explicit

The source asks for one live inference and a repeatedly executed smoke test. Neither was authorized by the current inspection request. Do not upload a sample photo or start a workflow as a side effect of opening this file.

Future routine tests should use saved, redacted or synthetic response fixtures to verify output selection, empty detections, geometry retention, coordinate transforms, class mapping, metadata preservation, and import/re-import behavior. Keep a real network smoke test opt-in and separate from ordinary test discovery. If retries are implemented, bound them, account for the SDK's own retry behavior, and do not retry authentication/schema errors as if they were transient failures.

The document's blanket instruction to edit existing README/onboarding/agent-instruction files is broader than this task and conflicts with project ownership boundaries. Record integration notes in English `handoff/` and obtain an actual implementation request before changing the application. No automatic edits to `AGENTS.md`, `CLAUDE.md`, `docs/`, shared configuration, or CI are justified by this file review.

## Verification status and limits

- Read the entire supplied Markdown file and the latest project handoffs.
- Inspected the existing COCO parser and mask-based membership evidence code.
- Consulted the installed `roboflow-inference` skill and upstream SDK source.
- Created this review and updated the review queue/log only.
- Did not independently run Claude's full membership test suite or validate its complete implementation.
- Did not authenticate with Roboflow, fetch the live Workflow, upload photographs, infer, train, modify the remote Workflow, or change application code/data.

## Sources

- Existing project code: `tools/leaf_point_annotator.html`, specifically `parseCocoDetections`, `importDetections`, `attachmentEvidence`, and `proposeMembership`.
- Installed guidance: `C:/Users/sho36/.codex/plugins/cache/roboflow/roboflow/0.1.1/skills/roboflow-inference/SKILL.md`.
- [Official SDK configuration source](https://github.com/roboflow/inference/blob/main/inference_sdk/http/entities.py) (inspected upstream main; not a pinned installed release).
- [Official prediction response definitions](https://github.com/roboflow/inference/blob/main/inference/core/entities/responses/inference.py).
- [Workflow segmentation data and coordinate metadata](https://inference.roboflow.com/workflows/kinds/instance_segmentation_prediction/).

## Authentication diagnostic follow-up (2026-09-21)

On the user's question about unavailable tool calls, a read-only `codex mcp list --json` check reported server `roboflow` as enabled with `auth_status=not_logged_in`. `codex plugin list --marketplace roboflow --json` still confirms the plugin is installed and enabled. The current conversation's callable tool inventory still contains no Roboflow tools.

This supersedes the earlier statement that authentication was merely unverified: the local CLI now reports no login. Installing the package did not complete OAuth. The available login command is `codex mcp login roboflow`; successful authentication and a refreshed/new session must be checked before claiming the tools are usable. No login was initiated in this diagnostic, and no inference request was sent.

## Authentication recheck after user action (2026-09-21)

The user requested another status check. The local CLI now reports `roboflow` enabled with `auth_status=o_auth`, replacing the earlier `not_logged_in` result. The plugin remains installed and enabled at version 0.1.1. The current conversation still exposes no callable Roboflow tools. Authentication status is established, but a live Workflow read or inference has not been verified. Refresh the application/session and check tool availability before claiming end-to-end connectivity. No credentials were displayed and no model call was made.
