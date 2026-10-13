# N / O / P — session state for the next session (2026-10-09, Claude Code)

Prompt being executed: `handoff/CLAUDE_CODE_CLI_PROMPT_NOP_2026-10-08.md`. Run folder
`build/synthetic_dwarf_tomato_20261008_07/` (`_07`); cell P will live in `_08/` (only `P_contract.json` exists there).
Nothing below changes any rule: detector frozen (609f…), B1 GT rule, gate bounds, SAM v5, pool 195, `_06` read-only.
No score-dependent threshold has been touched. **No row has been written to `c6_steps.csv` yet** (N's row is the
precondition for running P).

## 1. Done, in order

| step | where | state |
|---|---|---|
| Code: specular repair in bank build | `tomato3d/synth/textures.py` (`specular_mask`, `repair_specular`, `make_texture(specular_rule=)`, `build_bank(pool_mask_ids=, specular_rule=)`) | done, tests `tests/test_synth_texture_specular.py` (3) pass |
| Code: determinate compound cap | `tomato3d/synth/structure.py` (`CAP_RANGE = "compounds_per_plant_cap"`, drawn last; P3 `node_budget` point mass replaces `stop_probability`; `observed_node_count=1` on the stem axis) | done, tests `tests/test_synth_structure_cap.py` (2) pass; 13 synth tests green |
| Parent `_07` | inputs copied from `_06`; `stage1_contract.json` re-declared (same flags as `_06`, 100/5 scenes, seeds 20262005 / 20264000, 2+10 views, 512 px, 64 spp) | done |
| Contracts before render | `make_contracts_NOP.py` → `N_contract.json`, `O_contract.json`, `../_08/P_contract.json`; `contract_amendments.json` steps N, O, P-declared, N-bank | done 2026-10-08 10:50 / 11:02 |
| N bank | `build_bank_N.py` → `banks/current_195_delight/` (263 textures), `N_bank_report.json`, `N_bank_amendment.json` | done; sha256 `0559d22a1809…`; accepted |
| Cells | `make_cells_NO.py N-delight` / `O-mature`: config derived from `_06/G2-a`, diff asserted = declared only, cell contract pins contours + bank | N config `1f551e856df7…`, O config `a3bd428c0705…` |
| Generate | 15 scenes each, 180 manifest rows each, 0 rejections (`cli generate`, A4 pins verified) | done (after one memory-kill + restart) |
| Kaggle | dataset `dolgfish/tomato-synth-render-jobs` (upload needs `--dir-mode zip`); kernel `dolgfish/tomato-synth-render` **v8** (v7 died Kaggle-side: ERRORED_MOUNTING_DATASET; v8 ran ~5.5 h wall, status log `kaggle/klog/status.log`) | COMPLETE 18:45; `kaggle/kout/renders.zip` (92 MB, 360 canvases) |
| Extract + finalize | `post_render.sh` → `kaggle/kout/renders/{N-delight,O-mature}`; `N-delight/`, `O-mature/` finalized 180 + 180, missing 0 | done |
| Evaluate N B1 | `N-delight/eval_N-delight_B1rule.json` (20:03) | done — interim numbers in §3 |
| Evaluate N contract-GT, N realism, O B1, O contract-GT, O realism, analysis | `post_render.sh` continues as an **orphan** (bash PID 44324 survived the memory kill; was at "evaluate N-delight contract" at 20:03), log `post_render.log` | running / pending — check first (§2) |

Human decisions recorded for O (LOG 2026-10-08): `plant_age_days` 28–30 and `compounds_per_plant_cap` 6–8, both
`user_assumed` with provenance PENDING (no sowing dates, no compound counts in `data/records/`); J.3 literature
kind not used. Engine limit: P3 horizon is 30 development days (tools/, read-only) → noted for the tools owner.
D.2 "|p50 − 0.187| ≤ 0.047" was found to be a rendered relief statistic, not a bank statistic; the bank acceptance
applied instead is the same quantity (contrast_rel, `leaflib.appearance`) on the 195 pool crops before/after
repair, band after/before p50 ∈ [0.75, 1.25] → measured 0.974, accepted (`N_contract.json` `contrast_acceptance`).
`handoff/CLAUDE_CODE_CLI_PROMPT_L_RANK_SIZE_PROFILE_2026-10-08.md` carries the note that L.2 is retired and O
supersedes it.

## 2. First thing next session — check what the orphan pipeline finished

```bash
cd "/c/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis"
grep -v '^\s*$' build/synthetic_dwarf_tomato_20261008_07/post_render.log | tail -8
ls build/synthetic_dwarf_tomato_20261008_07/{N-delight,O-mature} | grep -E 'eval_|realism'
ls build/synthetic_dwarf_tomato_20261008_07/NO_analysis.json build/synthetic_dwarf_tomato_20261008_07/detections 2>&1
tasklist | grep -i python   # an evaluate still alive? then wait, do not start a second one
```

Then `bash build/synthetic_dwarf_tomato_20261008_07/post_render_resume.sh` — it skips every step whose output
exists, runs the rest one at a time, refuses to start while an evaluate for `_07` is still running. Expected
outputs: `eval_<cell>_B1rule.json`, `eval_<cell>_contractgt.json`, `realism_B1rule.json` per cell;
`NO_analysis.json`, `NO_plant_crops.png`, `detections/<cell>/` (analysis caches the detector runs, reuse them).
Each evaluate takes ~60–70 min on this CPU (N B1: 18:56 → 20:03); the analysis runs the detector again for the
paired bootstrap unless the cache exists. Memory: the machine kills background work when idle-low; run one heavy
step per command and keep the foreground timeout at 600000.

## 3. Interim N numbers (pooled over 180 views, same evaluate as `_06/post_render.log` lines 10/15)

| cell | AP50 B1 (pooled) | recall | GT n | FP@0.25 | SAM median |
|---|---|---|---|---|---|
| G2-0 (`_06`) | 0.287 | 0.372 | 3949 | 250 | 0.665 |
| G2-a (`_06`, control) | 0.2752 | 0.3697 | 3949 | 291 | 0.662 |
| **N-delight** | **0.2807** | 0.3707 | 3949 | **298** | 0.6616 |

GT n 3949 = G2-a to the leaflet, as the geometry-identity rule requires (the full C1–C5 digit check is in the
analysis). **The declared FP pass band (`FP(N) ≤ 270`, fully back `≤ 255`) is not met on this interim read: FP went
291 → 298.** Do not re-threshold; the N verdict is written from `NO_analysis.json` (verdict_N: geometry identity,
bank report, FP band, paired C6 delta N − G2-a with the scene bootstrap, reading). With FP not falling, the
"blotches were an artifact, not the limiter" fallback does not apply as written; the honest reading will be that
the repair removed the specular pixels (bank before_mean 0.0424 → 8e-05) without moving FP, so the blotches were
not what the detector was firing on — say that plainly, and keep N as the appearance baseline only on realism
grounds if realism_B1rule shows no regression. C6 claim only if the paired CI excludes 0.

O geometry pre-check (no render needed, already in the analysis script): declared ratio p50 1.859 (G2-a 1.731;
by cap 6: 1.351 n=6, 7: 1.704 n=2, 8: 2.165 n=7) → the declared `reading_if_unchanged` (≥ 1.6) fires: age/cap
are not what sets the taper. Findings to report, not to fix: cap 8 is unreachable inside the 30-day horizon;
rank 1 is the P3 origin leaf with a 12–25 mm head start vs 2 mm birth length (post-hoc rank-2 ratio O 1.403 vs
G2-a 1.399); youngest compound age p50 8.56 d vs 2.48 d; compound age p50 20.5 vs 15.0 d. lt150 GT share and C1–C3
excursions come from the evaluate/realism files. O never claims C6.

## 4. Records still to write (after `NO_analysis.json`)

1. `build/synthetic_dwarf_tomato_20261005_03/c6_steps.csv`: rows `N` and `O` in the G2-row format
   (`step,"text",,,…,kaggle_run_id` with config sha256, `leaflet_contours_sha256 5426e31f559e…`,
   `texture_bank_sha256` N `0559d22a1809…` / O `07cedd4af5b6…`, run id `dolgfish/tomato-synth-render v8`).
2. `build/synthetic_dwarf_tomato_20261005_03/C6_REPORT.md`: one section per cell, separate verdicts (N: bank
   report numbers, D.2 note, geometry identity, FP band, paired deltas; O: pre-commitment, ratio by cap, rank-2
   post-hoc note, lt150 share, C1–C3 excursions as findings, engine horizon limit, no C6 claim).
3. `handoff/LOG.md`: one line per cell.
4. Memory `tomato-synthetic-stage1.md`: N/O outcome bullet.
5. Only then cell P in `_08/`: parent inputs copy, `stage1_contract.json`, `cli amend` P-cell with control =
   N-delight if N met its FP band **else G2-a** (interim: G2-a), config derived with `leaflet_roll_deg` 0–15 as
   declared in `P_contract.json`, generate 15 scenes with `--rgb` export, one Kaggle batch, evaluate, analysis with
   the aspect falsification (p50 must reach ≥ 0.520, half of 0.485 → 0.555), P row/section/LOG.

## 5. Open items for the human

- O: cap 6–8 and age 28–30 are user_stated; the destructive session (`data/records/destructive_capture_20261008/`)
  re-anchors both when `2_plant.csv` / `6_compound.csv` get rows.
- Tools owner: P3 `horizon_days = 30` blocks any snapshot older than 30 d (cell O could not go beyond).
- Kaggle: dataset mounts failed once Kaggle-side (v7); v8 took ~5.5 h instead of 41 min — if it recurs, re-push
  is the only lever (dataset status was `ready` both times).
- Detector policy (LOG 2026-10-09): N/O/P stay under the frozen detector 609f…; the tomato_top_nonboard series
  becomes the C6 judge only via a declared instrument change.
