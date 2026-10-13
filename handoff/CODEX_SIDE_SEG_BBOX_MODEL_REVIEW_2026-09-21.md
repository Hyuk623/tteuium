# Side Segmentation / Bbox Model Inspection

Date: 2026-09-21
Status: read-only inspection in progress.

## User request

Inspect the user's Roboflow side-view segmentation/bbox model. Determine the actual project/model, task type, classes, dataset/version information, available evaluation metrics, and compatibility with the existing annotation workflow.

The supplied prompt identifies workspace `-ndul9` and workflow `tomsidesegbbox-vtomsidesegbbox-1-yolo26n-seg-t1-logic`, with display name `tom_side_seg_bbox vtom_side_seg_bbox-1-yolo26n-seg-t1 Logic`. These are lookup clues, not verified live model metadata. Do not infer that there are two separate models from the user's phrase, or that every class outputs both accurate masks and bboxes.

## Access and execution limits

- Roboflow plugin is installed; the previous CLI check reported OAuth authentication.
- No Roboflow tools are exposed to this conversation, so inspect the web UI through the supported browser interface if available.
- Do not launch inference, training, deployment, model evaluation jobs, Workflow edits, or photograph uploads.
- Preserve local labels, growth records, and code. Record observed facts separately from unverified expectations.

## Checks

- Distinguish a segmentation model's bbox output from a separate object-detection model.
- Confirm exact class names against `compoundleaves`, `leaflet`, `sub-stem`, `main-stem`, and `growth-shoot`.
- Report box and mask metrics separately when exposed; dataset evaluation is not evidence of 3D/PPFD accuracy.
- Check whether usable numeric masks are exposed rather than only preview images; retain original-coordinate/provenance requirements from CODEX_ROBOFLOW_WORKFLOW_PROMPT_REVIEW_2026-09-21.md.

Inspection outcomes will be appended below.

## Outcome and continuation

The current tool inventory still exposes no Roboflow MCP tools. The available browser opened `https://app.roboflow.com/` and reached the sign-in page, so no project or model metadata was visible. A focused Downloads filename check found the already supplied integration prompt, not a local model/evaluation artifact matching this model name.

The user selected: restart Codex and inspect through MCP. Stop the browser fallback and resume after the refreshed session exposes the authenticated Roboflow tools. The temporary login tab was closed. Do not treat this as authorization to run inference or training.

### Resume checklist

1. Discover the newly available Roboflow read-only tools and inspect their actual schemas.
2. Fetch the Workflow definition for `tomsidesegbbox-vtomsidesegbbox-1-yolo26n-seg-t1-logic` in workspace `-ndul9` without running it. Resolve the actual referenced model and dataset/version IDs from the definition; the workflow display name is not proof of them.
3. Read the linked project/model metadata: task type, exact classes, training status, dataset/version counts and splits, architecture, input size and preprocessing, and any existing box/mask precision, recall, and mAP results. Preserve metric definitions and evaluation split names as reported; mark absent metrics unavailable. Do not start an evaluation job.
4. Determine whether segmentation and bbox refer to outputs of one segmentation model or separate models. Do not infer this from the user's shorthand or the workflow name.
5. Check saved output declarations for numeric predictions/masks and retained coordinates. Do not claim actual runtime response validation without an authorized run or a supplied response fixture.
6. Append verified findings here and explain compatibility with the existing five-class annotation, parent-membership, and JSON review workflow. Keep 2D model evaluation separate from 3D/PPFD validation.

Status at handoff: model inspection is incomplete pending a refreshed MCP session. No model architecture, class set, dataset statistics, or accuracy has been verified live. No photographs, inference, training, code, configuration, or labels were changed by this task.

## API-key access authorized (2026-09-21)

The user explicitly authorized reading the Roboflow key from `C:/Users/sho36/OneDrive/작업물저장소/api.txt` to inspect the model. This supersedes waiting for the conversation's MCP tool registration. Read only the Roboflow-specific credential into process memory, authenticate only to documented Roboflow endpoints, and never print or persist the credential. Use the official MCP HTTP endpoint with documented `x-api-key` authentication where possible; discover tool schemas before metadata calls. If needed, use documented read-only Platform API requests. No inference, training, image uploads, or remote changes.

Store redacted metadata and a small reproducible inspection helper under `build/roboflow_side_model_review_20260921/`. Preserve previous history and append verified outcomes here.

## Verified API inspection outcome (2026-09-21)

Current status: read-only model identification and saved Workflow inspection completed through the official Roboflow MCP HTTP endpoint. The earlier access blocker above is historical. Native Roboflow tools still are not registered in this conversation, but the authorized API-key bridge works. The first Roboflow credential belongs to a different workspace; the second reaches the requested `-ndul9` workspace. No credential value is recorded here or in the artifacts.

### Model and dataset

| Item | Verified value |
| --- | --- |
| Project | `-ndul9/tom_side_seg_bbox` |
| Task | `instance-segmentation` |
| Model ID | `-ndul9/tom_side_seg_bbox-1-yolo26n-seg-t1` |
| Architecture | `yolo26n-seg` |
| Training | `finished`, job type `fine-tune` |
| Training ID | `53987dd107a0549fa9f4` |
| Dataset version | 1, ready |
| Version image count | 31: train 22, validation 6, test 3 |
| Preprocessing | Auto-orient; resize to 640 x 640 using `Stretch to` |
| Trained models returned for version 1 | One; no separate bbox-only model in this version's complete model list |

The saved Workflow invokes one instance-segmentation model. Its detections can provide boxes and mask geometry; this is not evidence of two independently trained bbox and segmentation models. Actual prediction payloads and mask quality have not been tested because no inference was run.

Project-level class counts returned by the API are annotation counts, not image counts, unique plant counts, or unique physical organ counts. They are not a verified version-specific class distribution:

| Actual Roboflow class | Reported annotations | Existing editor class / proposed import alias |
| --- | ---: | --- |
| `compound_leaves` | 105 | `compoundleaves` |
| `leaflet` | 677 | `leaflet` |
| `sub_stem` | 87 | `sub-stem` |
| `main_stem` | 28 | `main-stem` |
| `growth_shoot` | 39 | `growth-shoot` |
| `tom-seg-bbox-side` | 0 | Empty project category; do not map it silently to an organ |

There are five populated organ categories and one zero-count project category. The model's ordered class-index map was not returned, so do not invent class IDs or assume the zero-count category is part of its output head. Preserve the source class name alongside any explicit alias. No alias or importer change was implemented during this inspection.

The project also reports `unannotated=31`. Do not conclude that all 31 training-version images are unlabeled: project counts and the frozen version represent different fields/scopes, and image-level records were not inspected. Similarly, split totals alone do not establish whether photographs of the same plant/session leaked across splits.

### Available training metrics and limits

`trainings_get` returned the following saved training-summary values:

| API metric key | Value exactly as returned |
| --- | ---: |
| `map50` | 2.31 |
| `map5095` | 0.49 |
| `precision` | 3 |
| `recall` | 18.4 |
| `f1` | 5.2 |

These are raw API values, without normalization or percentage conversion. The response does not explicitly identify the unit/scale, evaluation split, confidence threshold, or whether these are bbox or mask metrics. If these are percentage-scale metrics, they indicate weak performance; do not present them as validated mask accuracy or relabel them as test-set results. Treat autonomous label acceptance as unsupported by this inspection.

`models_list.metrics` was null, but `trainings_get` did expose the summary above. `models_get` failed with an unsupported-request/permission error for both the full model reference and the workspace-local slug; the former showed a duplicated workspace in the server route. `model_evals_list` also failed with an unsupported-request/permission error. Thus per-class, per-split, and separately identified bbox/mask evaluations remain unavailable. These failures do not contradict the model existence/training completion verified by the version and model-list endpoints. No evaluation job was created.

### Workflow behavior that matters before integration

The supplied outer Workflow is `tomsidesegbbox-vtomsidesegbbox-1-yolo26n-seg-t1-logic`. It passes its `image` input and the verified model ID into base Workflow `tom_side_seg_bbox`, with `workflow_version_id=null` (no explicit inner-version pin in this saved definition).

The base Workflow contains:

1. `roboflow_core/roboflow_instance_segmentation_model@v3`.
2. `roboflow_core/roboflow_dataset_upload@v2`, targeting `tom_side_seg_bbox` with the input image and model predictions, using an `active_learning` batch prefix and a named upload quota.

Therefore this Workflow is configured with a dataset-writing step. A future run may upload the submitted image and predictions subject to that step's quota/settings; it is not a prediction-only path. We did not run it or change it. Before a future inference-only integration, explicitly select a prediction-only route or make a reviewed Workflow change within the user's authorized scope. Do not silently execute this upload step as a connectivity test.

Base defaults are confidence 0.4, IoU threshold 0.3, class-agnostic NMS false, and maximum detections 1000. The outer Workflow binds only image/model ID and exposes only `predictions`; it does not expose the base `model_id` or `inference_id` outputs. Preserve model identity in local provenance from the verified configuration if later adapting this interface, and record whether an inference ID is actually returned.

Outputs use `coordinates_system=own`. There is no explicit crop/resize block in the saved Workflow, but training preprocessing and output-coordinate declarations alone do not verify runtime coordinates. Any future adapter must validate original image dimensions, EXIF orientation and coordinate transforms using an authorized response fixture; retain numeric mask polygons instead of a preview-only representation.

### Integration implications for Claude

- Reuse the existing editor, COCO/draft import and compound-leaf membership implementation. Map the five source class strings explicitly; preserve the original class and model/version provenance. The current exact-name importer cannot assume underscore names match its hyphenated/canonical names.
- A segmentation project type does not establish that all leaf classes have true traced outlines: inspect original annotations before treating leaf masks as surfaces, especially where the user annotated leaflets/compound leaves with rectangles. Bounding rectangles or box-shaped segmentation targets must not become observed leaf boundaries or PPFD occluders.
- Each photo's model detections are 2D drafts. The saved Workflow contains no cross-view identity matching, compound-leaf parent assignment, anatomical landmark detection, triangulation, or PPFD calculation.
- Keep independent sub-stem instances, physical leaflet IDs, visible attachment review, unresolved cases, and growth-JSON count review from the existing handoff. Never create or merge leaflets to force agreement with counts.
- Original-pixel bbox/mask coordinates and evidence provenance must survive import. Do not treat a model detection ID, bbox corner or bbox center as a reviewed physical correspondence.
- Current ChArUco calibration quality and the unchanged 1 px gate remain separate. Nothing in this inspection validates metric 3D geometry or PPFD readiness.

### Evidence and execution record

Redacted artifacts are under `build/roboflow_side_model_review_20260921/`:

- `workflow_key2.json`, `inner_workflow_key2.json`: actual outer/base Workflow definitions.
- `side_project.json`, `side_version1.json`: project classes, counts and version/preprocessing.
- `side_models_v1.json`, `side_training_v1.json`: model identity, finished training and raw metrics.
- `side_model.json`, `side_model_resolved.json`, `side_evaluations.json`: failed detailed lookup responses, retained to explain the limits.
- `metadata_tool_schemas.json`, `training_tool_schemas.json`: server-returned schemas used for the read-only calls.
- `read_metadata.py` and `calls_01.json` through `calls_05.json`: read-only inspection bridge and request manifests; credentials are read at runtime and never embedded.

Only metadata reads and local inspection artifacts/handoff updates were performed. No inference, training, evaluation run, photo upload, model/Workflow mutation, source integration, or existing-label/calibration change occurred. No model-quality test is claimed from this metadata inspection.
