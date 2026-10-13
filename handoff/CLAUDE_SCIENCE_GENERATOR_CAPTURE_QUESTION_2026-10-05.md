# Quick question: minimal photos for the synthetic dwarf tomato generator

Context: following your 2026-10-05 review (`CLAUDE_TOPVIEW_3D_DIFFUSION_REVIEW_2026-10-05.md`), I am building a synthetic dwarf tomato generator: plant structure from my P3 growth engine, compound-leaf interior with L-Py/PlantGL, leaflet outlines from real photos, rendered in my 18-view ChArUco rig geometry. The generator's realism gate and the amodal-completion test still use my normal 18-view sessions.

**Proposal:** for generator-building data only, instead of uploading full 18-view sessions, I upload per plant:
- 1 top-view photo of the whole plant, and
- 1 close-up top-view photo of **each compound leaf** (e.g. a plant with 3 compound leaves → 3 compound-leaf photos + 1 plant top view = 4 photos),
on the ChArUco board / with a scale reference.

Questions (short answers please):
1. Is this enough to build the leaflet contour library and the compound-leaf priors (leaflet pair count, spacing, size taper, terminal/intercalary leaflets)? What is missing?
2. What can these photos **not** give that the generator needs (e.g. insertion angle, rachis droop, leaflet bend/roll, internode length, height)? Is one extra side photo per plant (or the existing side ring) enough for those?
3. Capture rules that matter: camera height/angle for the compound-leaf shot, whether the leaf must be flattened or photographed in its natural pose, scale reference, background, lighting, ID labelling so each compound-leaf photo maps to its position on the plant.
4. How many plants / compound leaves are enough for Stage 1 (100 scenes) and Stage 2 (1,000–5,000 scenes)?
5. Any risk that this data biases the generator (e.g. only well-exposed upper leaves, flattened shapes) and how to avoid it.

Label answers **verified source fact / design proposal / open assumption**. Keep it brief.
