# Claude Code CLI prompt — I.4b: adopt the re-measured ruler width in `tomato3d/`

Paste the block below. Everything above it is context for whoever is pasting.

## Why this is a handoff and not a diff

`tomato3d/` is your column (CONVENTIONS.md §1). The I.4b re-run was done in `build/`, by recomputing the
width scale from the I.4 per-photo cache, and it did **not** touch the module. Three places still hardcode
3.0 cm. Only you can change them.

## What is already settled — do not re-derive it

- The ruler's short-edge width (outer metal edge to outer plastic edge) is **31.1 mm**, `source_kind:
  user_measured`, stated 2026-10-08. It supersedes 3.0 cm (`user_stated`, 2026-10-07).
- Under the acceptance rule **declared on 2026-10-07 and not changed**, the width scale is now **adopted on the
  library set**: median signed disagreement vs the tick scale +0.22 % (was +3.89 %), median absolute 0.89 %,
  p10–p90 −1.32 to +0.91 %, on the 13 library photos where both scales are usable.
- Per-photo scale uncertainty **±1.12 %**, i.e. **±2.23 % on an area**, from the p10–p90 half-width of the implied
  width in cm (3.117 median, 3.063–3.169). **The ±1.2 % / ±2.4 % figures quoted on 2026-10-07 were the 3.0 cm
  values and are superseded.**
- Numbers and the method: `build/local_queue_20261008_01/I4b_summary.json`, `I4b_ruler_scale.csv`,
  `I4b_photo_scale.csv`, `run_I4b.py`; report section `C6_REPORT.md` → "Addendum I.4b".

## What is NOT settled — do not overstate it in a commit message or report

1. The agreement above is **not independent evidence**. 31.1 mm was arrived at after I.4's tick cross-check implied
   3.117 cm. The independent evidence is the user's physical re-measurement, which matched to 0.07 mm.
2. Adoption covers only **25 of 236 library components (11 %)**: 13 of 51 library photos have both edges on paper
   and in frame, 12 of those carry a segmented component. **C2 and C4 in cm² remain blocked on photographs.**
3. On the 117 dwt_1xx plant photos the ruler stands vertically beside the pot; **0 of 117** have both scales
   readable. Nothing about plant photos follows from this.

---

## Paste from here

Standing corrections, so these are not rediscovered:

- The generator **does** have an interjected-leaflet class: `compound_leaf.py` has `intercalary_count` (0–1),
  `intercalary_rel_size` (0.12–0.25 of terminal) and `intercalary_gaps` placing them between main pairs. Any claim
  that it is absent is wrong.
- "5–7 leaflets per compound" counts **main** leaflets only (F.12). The realised ~5.0 main leaflets is roughly
  right; only the interjected class is short.
- Normalised perimeter (perimeter²/area) is **genotype-dependent and not influenced by irradiance** (Barbosa et al.
  2019, Plant Cell Environ 42:1600). Do not add light-condition handling to any shape parameter.

Task — four changes, no more:

1. `tomato3d/synth/ruler.py`: set `RULER_WIDTH_CM = 3.11`. Update the module docstring: the width is 31.1 mm,
   `user_measured` 2026-10-08, superseding 3.0 cm `user_stated` 2026-10-07. Keep the description of what the width
   spans (outer metal edge to outer plastic edge) — that part was correct.

2. Same file, `_tick_period`: `expect = width_px / 30.0` silently assumes 3.0 cm. Replace the literal with
   `RULER_WIDTH_CM * 10`. **State in the docstring that this cannot change any existing result**: the true period
   sits at 1.93× the lower and 0.60× the upper bound of the `[0.5, 1.6] × expect` search window, so the selected
   autocorrelation peak is unchanged. Verify that claim by re-running the 13 usable library photos and confirming
   `px_per_cm_tick` matches `build/local_queue_20261007_01/I4_rows_cache.jsonl` to 2 decimals. **If it does not
   match, stop and report** — that would mean I.4b's recompute-from-cache was invalid and the Addendum I.4b
   numbers have to be withdrawn, not patched.

3. `tomato3d/synth/leaflib.py`, `build_library`: the contour records currently hardcode `scale_available=False` and
   `scale_status="ruler_present_scale_pending" if ruler_in_frame == "yes" else "no_ruler"`. Wire in an optional
   per-photo scale table (`build/local_queue_20261008_01/I4b_photo_scale.csv`: `photo`, `px_per_cm`,
   `ruler_width_cm`, `source_kind`, `scale_rel_uncertainty_pct`, `area_rel_uncertainty_pct`, `scale_status`).
   Where a photo is present with a scale, set `scale_available=True`, `px_per_cm`, `scale_source_kind`,
   `scale_rel_uncertainty_pct` and `scale_status="ruler_width_scale_adopted"`. Where it is absent or blank, leave
   today's behaviour exactly as it is. **Default the table argument to `None` and change nothing when it is
   `None`** — no existing caller may shift behaviour.

4. Tests in `tests/test_synth_ruler.py`: update any 3.0-derived expectation, and add one test that a known
   `width_px` yields `width_px / 3.11` and that the scale-table path leaves records untouched when no table is
   given.

Do not:

- do not change the acceptance rule (`max_rms_px` 3.0, `parallel_tol_deg` 1.0, adopt `median_abs ≤ 2 %`,
  `|median_signed| ≤ 1 %`) — it was declared before the 3.0 cm run and is what the adoption rests on;
- do not re-run the full 168-photo I.4 sweep to "confirm" the adoption — this container's cv2 is 5.0.0 and the
  cache was made elsewhere, so a different number would be version drift, not a finding. Re-measure only the 13
  photos needed for check 2;
- do not fill a scale for any dwt_1xx plant photo;
- do not touch `config/`, `data/records/` or the C6 gate values;
- do not widen the uncertainty to the old ±2.4 % "to be safe", and do not narrow it below ±1.12 %;
- do not describe the width-vs-tick agreement as validation of the 31.1 mm figure.

Record when done: a row in `build/synthetic_dwarf_tomato_20261005_03/c6_steps.csv` (step `I4c`, marked
`diagnostic`), a short section in `C6_REPORT.md` after "Addendum I.4b", and one line in `handoff/LOG.md`.
