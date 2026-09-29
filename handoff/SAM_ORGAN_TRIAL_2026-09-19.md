# SAM leaflet, stem and petiole trial — 2026-09-19

## Scope and actual outcome

User authorized a SAM trial, offered Colab, and extended the request to separating internodes and leaves. This supersedes the earlier proposal's statement that no SAM inference had been performed. All work stays in this project; the core pipeline, config, docs and existing annotator were not edited.

Ran pretrained Meta SAM 2.1 Tiny on three actual upright 3024 x 3024 working PNGs from Photos-1: IMG_7911, IMG_7922 and IMG_7924. The source files in Downloads were not altered. There were seven distinct prompted targets: five leaflets, one visible main-stem segment and one petiole candidate. Initial, correction and organ trials comprise 24 prompt sets and 72 candidate masks. These are selected examples, not a held-out accuracy study.

Observed from complete-crop overlays:

- Boxes helped separate touching leaves and include both bright/dark portions of a folded leaflet. Point-only prompts sometimes merged adjacent organs or selected only part of a blade.
- The crowded central leaflet remains ambiguous. No complete hidden outline was accepted.
- A second positive point helped the folded leaflet. Extra clicks did not guarantee cleanup: the isolated leaflet retained disconnected neighboring fragments.
- The visible central main stem can be selected separately from a leaflet. A single stem/petiole click can merge both organs; box/guided prompts constrained the intended region more clearly.
- Petiole masks retained nearby fragments. Independently prompted guided stem and petiole masks overlap by 438 original-resolution pixels, stem and leaflet by 1 pixel; no exclusivity cleanup was applied. These are prediction conflicts, not ground-truth errors quantified against an expert mask.

No human ground-truth masks or human timing trial exist. Model `predicted_iou` is confidence, **not measured accuracy**. Candidate masks remain unreviewed by the user; qualitative observations are in `visual_review.csv`.

## Internodes: implemented boundary and remaining work

`node_candidates.csv` stores two manually proposed junction points on IMG_7924, with original image coordinates and explicit assistant/unreviewed provenance. `internode_candidates.csv` records their possible adjacency as `I1_candidate`, with `length_mm=unavailable` and `status=unconfirmed_adjacency`. The dotted connector in `node_candidates_review.jpg` is only a relationship suggestion, not a measured centerline or segmented internode.

SAM does not automatically determine anatomical node identity, confirm consecutive nodes, detect hidden nodes, or produce internode length. The current visible-stem mask is not an internode mask. A human must distinguish main stem, compound-leaf petiole/rachis and side shoot, confirm nodes across views, and then split the stem between confirmed adjacent nodes. Do not convert an image-space distance using the board-plane scale for elevated plant organs. Valid camera calibration and 3D correspondences remain required for metric lengths.

## Implementation and reproduction

- `tools/sam_leaf_trial.py`: standalone manifest-driven CPU/CUDA/auto runner, original-pixel prompts, source hashes, three masks per prompt, full-resolution binary PNGs, contour CSVs preserving holes/disconnected rings, complete-crop review sheets, metrics and model/source provenance.
- `tools/sam_trial_bundle.py`: builds the portable ZIP and Colab replay notebook. Source images are deduplicated and referenced by unchanged SHA-256. Notebook verifies ZIP, payload, checkpoint and pinned source revision before running.
- `tools/tests/test_sam_leaf_trial.py` and `tools/tests/test_sam_trial_bundle.py`: five targeted tests passed for coordinate restoration, invalid inputs, disconnected regions/holes, image preservation/rebasing, and notebook cell syntax/setup order.

Example from project root:

```powershell
python -m tools.sam_leaf_trial --manifest build/sam_trial_20260919/organ_prompts.json --repository build/sam_trial_20260919/vendor/sam2 --runtime build/sam_trial_20260919/runtime --checkpoint build/sam_trial_20260919/checkpoints/sam2.1_hiera_tiny.pt --out build/sam_trial_20260919/new_organ_run --threads 4 --device auto
python -m pytest -q tools/tests/test_sam_leaf_trial.py tools/tests/test_sam_trial_bundle.py
```

Use a new output directory for every run. `encoder_seconds` is repeated on the three candidate rows of a prompt; aggregate only the top-model-score row per prompt to avoid triple counting. Zero indicates reused embeddings, not a zero-cost image encoder. Timings exclude imports, model loading, human prompts/review and saving files.

## Colab deliverables and validation

Under `build/sam_trial_20260919/colab/`:

- `SAM_Tomato_Colab.ipynb`: open in Colab, select a GPU runtime, run cells in order, and upload the paired `sam_tomato_trial_inputs.zip` (~25 MB). This is a replay notebook with fixed prompts, not an interactive drawing app.
- `SAM_Tomato_local_executed.ipynb` and `.html`: saved CPU execution, six code cells completed top-to-bottom; HTML output and organ comparison image inspected in the browser.
- The portable replay generated all 72 masks identically to the original CPU trials (file hashes), including the organ trial. `../validation.json` records this check and timing ranges.

**Colab's upload/install/download and actual GPU branches were not executed.** Local notebook verification reused the prepared repository/runtime/checkpoint via documented environment variables. No photos were uploaded to a cloud service during this task.

Runtime: native Windows, PyTorch 2.13.0+cpu, four CPU threads; SAM source commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`; checkpoint SHA-256 `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`. CUDA extensions and hole/sprinkle postprocessing were disabled. Private dependencies and weights are confined to `build/sam_trial_20260919/`.

## Review links and integration request

Generated local artifacts are under `build/sam_trial_20260919/`:

- `organs_quicklook.jpg`: focused leaf / visible stem / petiole comparison; full-crop images remain available in `run03_organs/index.html` and `comparison_full.jpg`.
- `run01/`, `run02_corrections/`, `run03_organs/`: all prompts, candidates, masks, contour CSVs and run metadata.
- `node_candidates_review.jpg`, `node_candidates.csv`, `internode_candidates.csv`, `organ_overlap.csv`, `visual_review.csv`, `validation.json`.

Claude/design review requested: define main-stem, compound-leaf petiole/rachis, side-shoot and node annotation semantics; confirmation and cross-view identity rules; and whether accepted masks should be mutually exclusive. Keep raw overlapping predictions for audit. Codex can then connect reviewed masks to the existing annotator's explicit accepted-contour path and add node/organ controls. That frontend integration, automatic cross-view identity, node training, complete plant labeling and metric reconstruction are **not implemented by this trial**. SAM contour vertex order must never become physical landmark correspondence.

Primary implementation references: [Meta SAM 2](https://github.com/facebookresearch/sam2), [installation](https://github.com/facebookresearch/sam2/blob/main/INSTALL.md), [image predictor](https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py).
