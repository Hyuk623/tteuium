# P2 lamp calibration implementation brief — 2026-10-13

Authorized by the user: review then start code work against CODEX_CLI_PROMPT_P2_LAMP_CALIBRATION_2026-10-13.md.

Implement a separate native reflection-aware fitter reusing ppfd_validation lamp_adapter, sensing_mesh, rig surfaces and native runner. Preserve the direct fitter and absolute blockers. Freeze explicit scene variants, bounds, calibration/validation split, source hashes and ray/job budgets before execution; optimize only rim calibration rows. Export conditional held-out metrics, native control runs and sensor first-hit/total diagnostics with actual backend support checked. Unknown geometry/beam must block real execution instead of receiving fabricated defaults.

Add a versioned frozen spatial prediction consumer to reference_dli with coordinate, time, schedule, uncertainty, provenance and hash checks. Preserve existing measured routes, domain and plant-association gates. Model predictions are never measured. Add focused contract tests and real native synthetic transport checks where available, and a fresh build readiness package for the 46 actual observations.

Known unresolved physical inputs: lamp emitting geometry/position/beam; full enclosure dimensions; sensor footprint/calibration; scene correspondence for plants. Canopy extent is user-stated 42 x 28 cm with derived coordinates and approximate placement; corner/orientation variants remain conditional. Do not interpret variant agreement as physical validation. The analytic 60% diffuse estimate is a comparator only. Keep recorded 300 mm/14 h separate from older provisional 400 mm and the user's 16 h/full-output operating instruction until reconciled.

No config/data-record/docs edits, no P3/P4 growth changes, no training/upload. Source ownership claims in LOG; active flow-map writer owns integration of supplied rows. All generated artifacts under fresh build paths. Results and unimplemented portions must be explicit.

Execution addendum: user confirmed 300 mm / 14 h / 100% and 50 mm gaps. Implementation and test evidence is recorded in P2_LAMP_CALIBRATION_EXECUTION_2026-10-13.md; real calibration remains blocked by explicit physical inputs. No old package hashes were repaired.
