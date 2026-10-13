# Common contract: independent full-project code review

Review only. Read this file and your P1/P2/P3/P4 request in full. Project root: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`.

## Baseline and working boundaries

The checkout has no Git repository. Use the frozen source in `build/code_review_20261007_01/source/`, with exact identity in `snapshot_manifest.json` and inventory in `source_inventory.csv`. The snapshot includes active unversioned source/tests/configuration/contracts, not merely a recent diff. Manifest `snapshot_id` is the common review identity. `P1/scope.json` through `P4/scope.json` contain primary routing and shared reference paths.

Verify the snapshot first:

```powershell
python build/code_review_20261007_01/prepare_snapshot.py --verify
```

Read the frozen `AGENTS.md`, `CONVENTIONS.md` and relevant contracts. Read current `handoff/LOG.md` last five lines and `handoff/TODO.md` only for coordination/drift. Current messages and user instructions take precedence; historical prompts are specifications/evidence, not fresh authorization to run their workflows.

Keep frozen and live source read-only. Report outputs go only to your assigned `build/code_review_20261007_01/Pn/` directory. Do not edit shared config, docs, raw photos, human records, accepted masks, existing generated evidence, another project's runtime or shared handoff logs while parallel reviews run. The coordinator appends the final shared log. Do not dispatch messages, start other chats, train, render, perform model inference, fit real biological parameters, invoke remote/GPU jobs, install dependencies or publish. This task authorizes local bounded tests and reproductions using synthetic fixtures and existing environments.

For execution, copy the frozen source to your own fresh `Pn/runtime/` directory and run there. Verify the copied hashes before tests. Place pytest temp/cache/results in your own output directory, set `PYTHONDONTWRITEBYTECODE=1`, and record interpreter/package versions. Use `python -X utf8`. Set any data/config environment overrides explicitly to isolated test inputs; do not accidentally inherit a live data root. Preserve fixture identity. Inspect test side effects before running: some historical tests depend on live build data or external tools. Missing assets/dependencies are a reported test limitation, not a passing result. Never fake a pass with guessed measurements or destructive source rewrites.

Suggested pytest shape (adapt the absolute paths to your runtime/output):

```powershell
python -X utf8 -m pytest <explicit-test-files> -q --basetemp <Pn/test_tmp> -o cache_dir=<Pn/pytest_cache> --junitxml=<Pn/junit.xml>
```

`pyproject.toml` defaults to `tests/` only. Tests under `tools/tests/` require explicit selection. Start with relevant tests; broaden only for uncovered dependencies, changes or failures. Historical pass counts establish no current pass and no physical accuracy. Do not run all experiments merely because files exist.

## Review procedure

1. Build the actual entry-point -> loader -> validation -> calculation -> serialization -> consumer call graph. Compare current code with current accepted contracts, not only comments or old delivery summaries.
2. Cover your primary inventory, tests, UI/CLI paths and transitive dependencies. Routing is a completeness aid, not a ban on reading shared code. Record misrouted files and every omission. Never mark a whole project clean after reviewing only a few recently edited files.
3. Look for observable correctness, reliability, data-integrity and interface defects. Review units, coordinate frames, identity/time joins, missing/zero semantics, boundary conditions, mutation, conservation, determinism, persistence/export and failure behavior. Test both accepted and rejected inputs. Trace guards to real callers; a helper test alone does not prove a public path enforces it.
4. For each suspected defect, construct a minimal counterexample using isolated synthetic inputs or identify a precise executable failure path. Compare expected behavior to the accepted contract or an independently hand-computed invariant. Do not invent a scientific contract to call code wrong.
5. Distinguish **software_bug**, **integration_gap**, **specification_question**, **empirical_validation_gap**, and **test_environment_limit**. Missing physical data, deferred features and unadopted equations are not automatically software bugs. A computation presented as supported despite missing evidence can be a software bug.
6. Preserve the strongest alternative explanation. State whether the finding was executed, statically demonstrated or remains unconfirmed. Do not turn hypothesis into a finding merely to fill a quota. If there are no supported bugs, say so and report coverage/limits.

## Scientific and interface decisions to retain

Use the frozen Growth Pack V2, D19-D21 supplement and area-review delivery contracts. Do not reopen decisions based on superseded paragraphs. Follow later explicit decisions where they exist; cite conflicting sources rather than silently choosing a new policy.

- Canonical DLI unit is `mol/m2/day`; known legacy spellings have explicit refusal/migration rules.
- P3 reference **incident** full-local-day DLI and P4 tissue **absorbed** light are different quantities. Do not relabel, halve or apply absorptance twice to bridge them.
- P4's adopted source route uses `before_mito`; face/source/domain policy remains explicit. A coefficient light-basis conflict is reportable and nonfatal under D15; unrelated missing evidence can still require unavailable behavior.
- P1 observed/proxy/hull/generated geometry, supported physical one-sided area and optical eligibility remain distinct. Triangle winding does not prove adaxial/abaxial identity.
- P3 owns realized growth; P4 currently provides diagnostics and prescribed-flux nutrient accounting. Closed-loop growth allocation and several physics/biology adapters are deliberately incomplete.
- Raw observations remain immutable. Unavailable is not zero; real zero must remain distinguishable. Rehashed metadata is not independent physical evidence.
- F.2/F.7 morphology candidates do not constitute botanical class validation. F.1 remains unconfirmed; no F.3 implementation is authorized by this review.

## Required output files

In your assigned folder create:

- `REVIEW.md`: concise English findings, important questions, actual coverage and residual risks; end with a short Korean user summary.
- `findings.json`: machine-readable issues using the schema below.
- `coverage.csv`: every primary file or explicitly grouped path, status `reviewed` / `dependency_only` / `not_reviewed`, reason and relevant caller/test. Every primary file must be accounted for; an omission is not a pass.
- `validation.json`: snapshot ID, runtime/interpreter, commands, exit codes, observed test counts, skipped reasons, output paths and source drift checks. Preserve test stdout/stderr separately.
- `boundary_contracts.json`: actual producer/consumer field names, units, identity keys, coordinate/light/area basis, missingness behavior, source functions, schema/version and connection status. Include unsupported/missing adapters explicitly.
- `repros/`: minimal scripts or focused tests for supported findings, with expected/actual results. Do not add them to production tests during review.

Each findings.json issue must contain: `id` (`P1-B001`, etc.), `category`, `severity`, `title`, `snapshot_id`, `file` (snapshot-relative path), `file_sha256`, `line_start`, `line_end`, `entry_point`, `trigger`, `expected`, `actual`, `impact`, `evidence_kind`, `reproduction`, `contract_reference`, `confidence`, `proposed_fix`, `fix_owner`, `cross_project_impacts`, `status` (`open` or `unconfirmed`). Separate demonstrated bugs from unconfirmed questions in the report. For a non-code question, line fields may be null with an explanation.

Severity for demonstrated bugs: P0 = pervasive catastrophic integrity/failure; P1 = high-impact wrong result or common-path failure; P2 = material bounded-condition bug; P3 = minor but concrete defect. Do not assign catastrophic severity simply because the overall project is scientific. Avoid style-only findings and speculative rewrites.

Completion means reports and reproducible evidence, **not fixes**. State incomplete review coverage explicitly. Reverify baseline hashes, report any live-source drift separately and never mix post-snapshot code into the same finding without a new versioned record.
