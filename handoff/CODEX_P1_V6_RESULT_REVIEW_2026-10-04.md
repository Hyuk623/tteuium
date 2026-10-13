# P1 v6 returned result review

Date: 2026-10-04. Codex review requested by the user for Claude's result handoff, visual sheet, visual note and comparison CSV.

## Review scope

Read the actual returned final bundles, runtime and images; independently validate all seeds, targets, hashes, dimensions and provenance against the frozen preparations using the existing importer. Re-evaluate availability and export fresh review artifacts under `build/p1_v6_result_review_20261004_01/`. Preserve Claude's returns, source masks, configurations and prior failures. No new GPU run, upload, model change or integration is part of this review.

Inspect the 20-view sheet and local conditioning/reference composite. Separate actual runtime success from structural quality and metric/optical acceptance. Check the original eight P1 requirements against the prior baseline evidence and new returned-output evidence before changing goal status.


## Visual findings and interpretation

The sheet contains all four arm/seed rows and five common target columns. Both arms show separated leaf-like patches on white. Multiview generally spreads vertically with more visible texture; top-only usually occupies a lower band with several dark elongated/smeared regions. Layout, size and apparent leaf count differ substantially between seeds and target azimuths. These are qualitative observations, not a measured superiority claim. The images do not establish persistent organ correspondence or coherent hidden plant structure.

The local reference composite is already a set of separated masked leaf regions with most connecting plant structure absent. Consequently, absent stems/petioles in generated outputs cannot be attributed solely to the model. The top condition also includes two small isolated non-leaf-looking objects; repeated small output fragments are consistent with conditioning contamination, but causal attribution needs a controlled revised-mask trial. Do not silently edit the saved mask or rerun under the old request.

Two statements in Claude's visual note need narrower wording:

- Leaf-like output alone does not prove the correct checkpoint or EMA was loaded. That conclusion is supported by the checkpoint hash/probe, pinned executed package, complete runtime and `ema_applied_on_cpu=true` records.
- The claim that particular output fragments "come from" the two input objects is a plausible explanation, not an isolated causal finding. Likewise, the top-only collapse may reflect the view gap and masked conditioning, but this run does not separate those causes.

The note's central conclusion is supported: adding a side condition changes the generated appearance, while neither arm demonstrates reliable hidden-leaf reconstruction. Retain `novel_view_rgb`, `origin=generative`, `validated_metric=false` and `suitable_for_ppfd=false`; do not use these candidates as measured growth, anatomical labels, area, accepted 3D surfaces or optical tissue.


## Independent return verification

Used the existing `import_candidate_bundle`, `evaluate_candidates` and `export_review_bundle` APIs for both arms in fresh output folders. Both final bundles passed request/backend/conditioning provenance, every declared seed and target, image SHA256 and 256 x 256 dimensions, and generative/metric/optical flag checks. Both runs have `complete=true`, return code 0, successful checkpoint size/SHA256 records and CPU EMA application. No replacement output was synthesized for this review.

| Arm | Verified views | Runner elapsed | Peak torch allocated | Process wall time | Peak nvidia-smi used |
| --- | --- | --- | --- | --- | --- |
| Multiview | 10 | about 115 s | 5.085 GiB | 182 s | 5.247 GiB |
| Top-only | 10 | about 121 s | 5.021 GiB | 191 s | 5.190 GiB |

Runner time and process wall time have different scopes. About two minutes per arm describes the runner; the outer process took about three minutes. These observed values are not universal model requirements.

`comparison.csv` correctly has 24 rows for 20 distinct arm/seed/target combinations: 8 unavailable T_eval metric rows (two metrics per candidate), and 16 not-applicable ring rows. All values are blank and all pose gates are false. Neither missing scores nor ring rows should be treated as zero accuracy. Fresh evaluation reports also correctly return `evaluation_unavailable`.

Current checks rehashed all 4,021 baseline source/code records without a mismatch; the 1,318 observations and 54 first references remain covered by the preserved baseline audit. Current runner delivery hashes, full archive isolation, earlier geometry/canopy audit hashes and retained source geometry hashes also passed. Recorded suites remain 55 baseline, 2 synthetic transform and 50 completion tests; these overlap and are not additive. No code changed and no new unit-test run was needed for this actual-output inspection.

Evidence: `build/p1_v6_result_review_20261004_01/verification.json`, fresh `{arm}_import`, `{arm}_evaluation`, `{arm}_review` folders and `completion_audit.json`. Original returns and Claude's notes were not modified.

## Original P1 completion audit

| Requirement | Result |
| --- | --- |
| 1 Observation baseline and area distinctions | Complete: existing audit preserved and source hashes rechecked. |
| 2 Measured geometry and frames | Complete: source evidence preserved; generated poses/scale not promoted. |
| 3 Continue existing completion pipeline | Complete: current delivery hashes and actual existing-API import verified. |
| 4 Generative output typing | Complete: all four candidates and 20 views retain required false eligibility. |
| 5 Common comparison and isolation | Complete: frozen contract/archives and explicit metric unavailability verified. |
| 6 Bounded actual model trial | Complete: real v6 success, all outputs retained and inspected; earlier failures preserved. |
| 7 Future geometry inventory | Complete at requested inventory/reporting scope; 13 groups with real gaps documented. |
| 8 Canopy identity and transform review | Complete at requested review scope; preserved synthetic mapping/split evidence, no adapter. |

The former GPU execution blocker is resolved. The requested P1 observation/completion continuation is complete at its stated software, bounded-trial, review and handoff scope. This does not establish acceptable reconstruction quality, metric area, hidden anatomy, optical geometry or integration readiness. The experiment's weak structural result is retained as a result, not hidden by rerunning or changing acceptance criteria.

Future decisions belong to Claude/design and the human: review a revised conditioning mask/structure policy and camera mapping before a separately specified comparison. If a new trial is selected, preserve these inputs/results and issue a new frozen contract. Do not infer future leaf growth from these images; P3 remains its owner.
