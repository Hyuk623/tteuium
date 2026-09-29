# Colab integration for the static XL export

## Authorized scope
The user requested starting Colab integration after the static GroIMP export was completed. Connect the existing static exporter through a portable input ZIP, a Colab notebook and verified local result import. Start with pipeline_20260927_202748, all four plants. No training, reconstruction, radiation calculation or automatic CPU failover is introduced. Colab is an interactive batch execution environment, not a background worker or public application server.

## Implementation contract
- Package only the required Python sources and recorded hierarchy/structure/status/annotation snapshots, with original paths and SHA-256 values. Do not package photos, model weights, credentials, unrelated project files or the GroIMP installation.
- Preserve original snapshot bytes. Create separate runtime hierarchy copies with an explicit path map so Windows references work in Linux. Never replace source hashes to conceal changed data.
- Reuse the existing exporter. Pin the required Python dependencies, record the actual runtime and preserve diagnostic flags and source statuses.
- Provide a Korean guided notebook: upload the bundle, validate its expected digest, prepare the runtime, run exports, download results. No Drive-wide authorization is required for this first file-transfer workflow.
- Verify returned bundle identity, file integrity, expected plant set, graph content and exact generated RGG against the originating local bundle before accepting into a fresh build directory. Imported exports still need GroIMP runtime verification; do not carry forward local verification claims automatically.
- Test safe archive extraction, changed/missing inputs, cross-platform relocation, all four plants, repeat/resume behavior and result tampering. Validate notebook structure and execute its computation cells locally; distinguish this from actual hosted Colab execution.

## References
- https://research.google.com/colaboratory/faq.html
- https://colab.research.google.com/notebooks/io.ipynb

## Outcome
## Implemented and verified on 2026-09-28

- Added `tools/colab_xl_bridge.py` with `pack`, `run`, and `import` commands. The existing static exporter is reused without changing the reconstruction pipeline.
- Added `tools/tests/test_colab_xl_bridge.py`: archive safety, snapshot integrity, portable relocation, resume, notebook validation, and returned-content tampering checks. Together with the existing export/bridge tests, 14 tests passed before the notebook sidebar fallback update; the final repeat is recorded below.
- Prepared four-plant inputs from `build/pipeline_20260927_202748` in `build/colab_xl_release_20260928/`. The 531,761-byte input ZIP contains 32 files, no photos, weights, credentials, or GroIMP installation.
- Input ZIP SHA-256: `cdfc06144d54e525d790c8530c95dd7c31d5a8150410845a29c8b219549abe5a`.
- A complete isolated local pack/run/import check passed for all four plants. Evidence: `build/colab_xl_local_roundtrip_20260928/returned/`. This is local Windows validation, not a downloaded cloud result.
- The hosted Colab notebook was created and saved at https://colab.research.google.com/drive/18OG7-8n6UsqLvqOrm0Zcwg0wy-VG9cK4 . Existing account access was used; sharing permissions were not changed.
- The actual hosted run passed all four static exports: `dwt_01: static export checked` through `dwt_04: static export checked`. Setup took about 24 seconds; export cell about 1 second, as displayed by Colab (not a performance benchmark).
- Hosted environment reported Python 3.13.15, Linux, 2 CPUs, numpy 2.2.4, pandas 3.0.3, pydantic 2.13.4, and `hosted_colab=true`.
- Remote result: `/content/tomato_xl/build/colab_job/tomato_colab_result_1790564967809190541.zip`; also copied to `/content/tomato_colab_result.zip` for the Files sidebar.

## Transfer limitation and continuation

The embedded `files.upload()` chooser did not reach the automation file chooser. Upload through the Colab Files sidebar succeeded. The hosted first cell now reads `/content/tomato_colab_inputs.zip` when available, falling back to `files.upload()` otherwise. This fallback is also in the current notebook generator and the companion `Tomato_XL_Colab_sidebar.ipynb`. The original release ZIP remains unchanged and hash-verified; its embedded source is the immutable version used for the hosted run.

The computation completed, but both `files.download()` and the Files-sidebar Download action failed to produce an observable download through the current in-app browser. Therefore **hosted-result transfer back to Windows and local import of that hosted artifact remain unverified**. Do not claim a complete cloud-to-local round trip. The output ZIP remains in the connected Colab session; download it before the runtime expires. The saved notebook can rerun the same immutable input if the session is lost.

After the downloaded ZIP is available locally, run:

```powershell
python -m tools.colab_xl_bridge import --bundle build/colab_xl_release_20260928/tomato_colab_inputs.zip --result "<downloaded ZIP path>" --out build/colab_xl_hosted_return_20260928
```

The output directory must be new. Then use `tools/groimp_static_verify.py` for the imported model if runtime verification of the returned artifact is needed. Do not inherit verification claims from a different export directory.

## XL status and scope boundary

Static XL/RGG generation, identity/relationship transfer, and local GroIMP CLI compilation/reset/save/reopen were already completed for all four plants and a synthetic mesh case. See `handoff/CODEX_STATIC_XL_IMPLEMENTATION_2026-09-27.md`. GUI visual verification remains separate. This Colab step executes the Python static exporter; it does not execute GroIMP or XL inside Colab.

No L-system growth rules, PPFD simulation, reconstructed leaf surfaces, new model training, or automatic CPU-load-based failover were added. `validated_metric=false` and `suitable_for_ppfd=false` are retained. The connection is an interactive file-batch workflow. Heavy reconstruction/inference offload requires a separate job adapter and is not implemented by this change.

Final verification after the sidebar-input fallback update: `python -X utf8 -m pytest tools/tests/test_colab_xl_bridge.py tools/tests/test_groimp_structure_export.py tools/tests/test_groimp_bridge.py -q` → **14 passed in 16.36 seconds**. The companion notebook was regenerated for the unchanged release ZIP.

## Hosted result recovered and imported — 2026-09-28

This update supersedes the transfer limitation above. The user requested downloading the existing Colab result. Browser downloads remained unresponsive, so recovery used visible notebook output with compressed content-addressed transfer. Local matching bytes were reused only when their SHA-256 exactly matched a remotely computed entry digest; seven differing files were transferred. All 31 ZIP entries match the hosted original byte for byte. The local ZIP is repackaged, not container-byte-identical to the original.

- Recovered ZIP: `build/colab_xl_hosted_return_20260928_transfer/tomato_colab_result.zip`.
- Full recovery evidence and entry hashes: `build/colab_xl_hosted_return_20260928_transfer/recovery_receipt.json`.
- Original hosted ZIP SHA-256: `f195c0ef8b83cd055aaa6a3892c1fadc664d5c90096f30dbfaec4c5c03a1e178`.
- Repackaged ZIP SHA-256: `c19bcba2e9e80de88608e11dd956b39f6cc95272bc5e59076b0e5cfcaa80c74e`.
- Import destination: `build/colab_xl_hosted_return_20260928/`.
- Existing importer returned `import_verified` for dwt_01, dwt_02, dwt_03 and dwt_04; original release input SHA-256 matched.
- `environment.json` preserves the actual hosted Linux environment and `hosted_colab=true`.
- This result belongs to `pipeline_20260927_202748`, not the newer `pipeline_20260928_122948` export. It does not replace newer local outputs.
- No exporter, reconstruction, training, inference or PPFD computation was rerun during recovery. GroIMP runtime verification of this imported directory remains a separate step. Both validity flags remain false.
- GitHub publication remains cancelled; no GitHub action was performed for this recovery.

Reproducible import command (requires a new output directory):

```powershell
python -X utf8 -m tools.colab_xl_bridge import --bundle build/colab_xl_release_20260928/tomato_colab_inputs.zip --result build/colab_xl_hosted_return_20260928_transfer/tomato_colab_result.zip --out build/colab_xl_hosted_return_20260928
```
