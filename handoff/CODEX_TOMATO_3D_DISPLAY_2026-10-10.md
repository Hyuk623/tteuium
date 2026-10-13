# Tomato 3D display

User request: display the tomato in 3D using work completed so far.

Plan: show the existing O-mature scene_0000 synthetic mesh in an interactive local viewer, with a separate existing dwt_t1 observed-photo diagnostic viewer. Use saved vertices unchanged; do not reconstruct, infer, fit, or alter production code/data. Label synthetic geometry and observed hull diagnostics separately. Preserve historical artifacts; write display output to build/tomato_3d_display_20261010_01. Verify browser rendering and controls. No training or external upload.

## Delivery

Created a local interactive WebGL view from the unchanged O-mature scene_0000 OBJ (11,563 nondegenerate triangles displayed; board hidden for display). Added a separate exact copy of the historical dwt_t1 diagnostic viewer. Both views visibly rendered in the Codex browser; preview.png records the observed diagnostic view selected at finalization. Tabs and layer/view controls are present; no automated claim is made about every interaction. Source SHA256 values verified unchanged. Local viewer: http://127.0.0.1:8841/index.html (loopback-only static server); index.html can also be opened locally alongside observed_t1.html. No physical accuracy, new reconstruction, source geometry change, production edit or upload.
