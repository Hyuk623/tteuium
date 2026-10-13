# Research and development plan: top-view → plausible 3D for dwarf tomato with a diffusion model

I want to build a model that takes a **top-view image** (later possibly top-view + depth) of a dwarf tomato plant and produces a **plausible 3D plant**, including parts that are occluded or curved and therefore not directly visible. I plan to train it on my own multi-view dwarf tomato data. Please find the relevant literature, open-source code and datasets, and propose a concrete training and development method. This is a research/design discussion: do not write production code.

## 1 What I already have (facts)

- **Capture rig:** plant on a ChArUco board; per session 18 photos (top + side ring), camera poses from the board (some views fail the pose gate), calibrated scale in board mm.
- **Plants:** 24 dwarf tomato plants will get a full 18-view session; ≥6 plants will be repeated every 3–4 days for ~30 days; plus a twice-daily fixed top-view canopy camera (planned). Cultivar is a dwarf determinate type; plants ~60–90 mm tall, side leaf-area proxy ~10–17 cm² at the current stage.
- **Existing pipeline per plant:** organ detector (leaflet AP50 ≈ 0.74–0.77, plant-held-out), SAM-based leaflet masks (IoU ≈ 0.82–0.86), visual hull / outer envelope, compound-leaf regions, stem and petiole polylines, supported triangle surfaces only where multi-view evidence exists. Human-reviewed masks exist for 4 plants (~1,160 masks).
- **Zero-shot diffusion trial already run:** pretrained ViewFusion (Zero123 105000.ckpt) conditioned on the top image vs top+side, evaluated against a held-out real view under a validated camera mapping. Result: leaf-level IoU ≈ 0.26 (control level); filled-envelope IoU ≈ 0.46–0.49 at the held-out pose, **below the plain visual hull (0.57)**. Top-only vs top+side difference not significant. So an off-the-shelf object NVS model does not help yet; domain adaptation is needed.
- **Compute:** no local GPU; Kaggle T4 / Colab (≈15 GiB VRAM, session limits). Public pretrained weights are allowed.
- **Growth/light models downstream:** a light simulator (ray tracing over leaf triangles) and a growth model (CompoundLeaf trajectories). Rule: **generated geometry is never treated as observed tissue**; it must be labelled `origin=generative`, carry uncertainty, and is not used for light (PPFD) or for fitting growth coefficients unless a later validated gate allows it.

Project root (open named files directly; the OneDrive tree listing times out): `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis`. Relevant: `handoff/CLAUDE_MULTIVIEW_TRIAL_RESULT_2026-10-03.md`, `build/multiview_completion_20261004_04/`, `build/mapping_validation_20261004_02/`, `tools/MULTIVIEW_COMPLETION.md`, `tools/completion_viewfusion.py`, `build/ONE_PIPELINE_2026-10-01.md`, `build/al_4plants_20261002/AL4_RESULTS.md`. If you cannot read them, say so.

## 2 What I want you to survey (cite exact papers, repos, licenses)

For each item give: citation (year, venue, arXiv/DOI), repo URL and license, pretrained weights availability, input/output representation, VRAM/time needs, and whether it was shown on plants or thin/occluded structures. Mark anything you could not open.

1. **Single-image / few-view 3D generation:** Zero123, Zero123++, SyncDreamer, Wonder3D, SV3D, One-2-3-45(++), InstantMesh, LGM, TripoSR, CRM, and newer large reconstruction models; multi-view diffusion + reconstruction pipelines.
2. **Amodal completion / occlusion reasoning:** amodal segmentation and amodal image completion with diffusion; occluded-leaf completion in plant phenotyping.
3. **Plant-specific 3D:** leaf/plant point-cloud and mesh reconstruction from images (NeRF / 3D Gaussian splatting for plants, plant organ segmentation in 3D), single-view plant reconstruction, leaf surface fitting (parametric leaf models, B-spline/NURBS leaves).
4. **Structure-aware / procedural approaches:** inverse procedural modelling, L-system or graph-based plant models fitted to images, skeleton-first (stem/petiole graph) then leaf placement, diffusion over plant graphs or skeletons.
5. **Datasets usable for pretraining:** public 3D plant datasets (e.g. Pheno4D, ROSE-X, Plant3D, any tomato-specific sets), multi-view plant image sets, synthetic plant generators (GroIMP/XL, L-Py, Blender plant add-ons). Note size, species, licence and whether tomato is included.
6. **Depth-assisted top view:** RGB-D / monocular depth (e.g. Depth Anything, Marigold) as conditioning for completion.

## 3 Design questions

1. **Representation:** which output is appropriate for my use — multi-view images then reconstruction, point cloud, Gaussian splats, mesh, or a structured plant graph (stem polyline + compound-leaf nodes + leaflet surfaces)? Which representation keeps "observed vs generated" separable per region?
2. **Conditioning:** top RGB only; top RGB + leaflet masks; + monocular/RGB-D depth; + previous full 18-view 3D of the same plant (temporal prior). Which gives the best gain per unit of data?
3. **Training data from my rig:** how to turn each 18-view session into training pairs (input = top view; target = held-out side views, visual hull, supported surfaces, masks, skeleton). How to handle missing or failed poses, and partial/uncertain targets (supported vs unobserved regions) in the loss.
4. **Data scale:** with ~24 plants × 1 session + ~6 plants × 8–10 sessions (~80–100 sessions, ~1,500–1,800 images), what is realistic: zero-shot, LoRA/adapter fine-tuning of a pretrained NVS model, full fine-tune, or training a small structure model from scratch? How much synthetic data (procedural dwarf tomato from L-system/GroIMP, rendered in my rig geometry) is needed, and how to close the synthetic-to-real gap?
5. **Plant-level splits and leakage:** splits by plant, not by image; temporal sessions of one plant never in both train and test; augmentation that does not leak held-out views.
6. **Uncertainty:** how to produce multiple samples and per-region confidence; how to tag generated regions so downstream tools can exclude them.
7. **Evaluation:** metrics against held-out real views (silhouette IoU at validated camera mapping, leaf-level IoU, Chamfer distance to supported surfaces, leaf area/height/envelope volume error, leaf count), required baselines (visual hull, copy-nearest-view, zero-shot ViewFusion result above), statistical test across plants, and what improvement would justify use.
8. **Compute plan:** what fits on Kaggle/Colab T4 (batch size, resolution, mixed precision, LoRA rank, training hours); what would need a larger GPU.
9. **Risks:** hallucinated leaves, mode collapse to an average plant, thin-structure failure (petioles), board/background leakage, overfitting to 24 plants, growth-stage shift as plants get bigger than the training range.

## 4 Output I want

1. A literature/open-source table (sections 2.1–2.6) with relevance to my case and licence.
2. 2–3 candidate architectures for my data size, compared on expected accuracy, data need, compute, and how cleanly they separate observed vs generated geometry; one recommended.
3. A step-by-step development roadmap (data preparation → baseline → fine-tune/synthetic pretraining → evaluation gate → integration), with concrete deliverables, dataset formats (CSV/JSON manifests) and decision gates.
4. Minimum data collection additions that would most improve the model (e.g. depth camera, extra side views, repeated sessions).
5. At most 3 decisions I must make first.

Label every statement **verified source fact**, **design proposal**, or **open assumption**. Do not present results from papers you could not open as verified. Keep "looks plausible" separate from "geometrically correct".
