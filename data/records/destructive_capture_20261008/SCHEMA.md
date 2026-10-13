# Capture record schema — intact capture and destructive measurement (2026-10-08)

Seven append-only CSVs in `templates/`, headers only. One table per granularity so no value is typed twice.
Human-owned: the recording tool writes these, nothing in the pipeline edits them.

## Enumerations

| column | allowed values |
|---|---|
| `tripod`, `exposure_locked`, `board_present`, `flowering`, `has_terminal`, `damaged` | `y` / `n` |
| `planned_role` | `intact_only` / `defoliation` / `dismantle` / `reserve` |
| `photo_kind` | `top` / `side` / `level` / `E` / `defoliation_step` / `compound_spread` / `blade` |
| `side` | `L` / `R` / `terminal` |
| `class_by_position` | `main` / `interjected` / `terminal` |
| `method` (height) | `ruler_visual` / `ruler_caliper` / `other` |
| `arrangement` | `alone` / `pair` / `quad` |
| `ruler_width_source_kind` | `user_measured` (it is 31.1 mm, measured 2026-10-08) |
| `quality_flags` | `;`-separated: `blurred`, `ruler_cut`, `board_occluded`, `exposure_jump`, `hand_in_frame`, `plant_cut` |
| `variety_cultivar` | `unknown` only. See rule 7. |
| `growth_habit` | `determinate` / `indeterminate` / `unknown` |
| `terminal_inflorescence` | `y` / `n` / `unknown` |
| `leaf_color` | `dark_green` / `normal` / `unknown` |
| `leaf_rugosity` | `smooth` / `slight` / `rugose` / `unknown` |
| `bse_fuchsin_result` | `dry_patches` / `uniform` / `not_tested` |

## Keys

- `photo_id` is the join key for every photo. Make it `<session_id>_<nnnn>`, incrementing per shutter press.
- `plant_id` is given by the user. **Do not invent one**, and do not reuse `dwt_01…04` or `dwt_101…113` —
  these plants cannot be mapped to either set, and the sets are independent samples of the same population.
- `compound_id` is per plant, e.g. `C01` from the bottom. `station_index` counts attachment stations along the
  rachis from the base, so a main pair and the interjected pair after it have different station indices.

## Rules the tool must enforce

1. **Blank is not zero.** An unmeasured field stays empty; `0` means a measured zero. Never substitute a default.
2. **Units are in the column name** (`_cm`, `_mm`, `_g`, `_deg`). Do not add a column without one.
3. **Append on every row**, immediately. Never hold a session in memory — the destructive steps cannot be redone.
4. **Carry the previous value** for `plant_id`, `compound_id`, `session_id` until changed.
5. **Do not type `photo_file` in the field.** Record `entry_time` and match to the camera's files by EXIF
   timestamp afterwards; `photo_file` is filled by that matching step.
6. **`class_by_position` is set by the leaflet's position on the rachis, never by its shape.** Shape is what the
   generator is trying to learn from these blades; labelling by shape would be circular.

7. **Never put a cultivar name in `variety_cultivar`.** The plants are sold under the market name
   "앉은뱅이 토마토" and no cultivar, vendor catalogue entry or seed-lot identifier could be found, so the value
   is the literal string `unknown` and the tool must reject anything else. The phenotype columns
   (`growth_habit` … `bse_fuchsin_result`) are where a genotype inference is recorded, and they are recorded as
   **observations, never as a cultivar call** — a plant that looks exactly like Micro-Tom is still `unknown`.
   Writing a guessed cultivar would let an inference be read later as a measurement.
9. **Group photos (`arrangement` = `pair` / `quad`): `plant_id` stays empty, `group_id` names the plants**
   joined by `+` (e.g. `dwt_05+dwt_07`), `pitch_cm` is the centre-to-centre pot distance (pots touching =
   the pot outer diameter, recorded in `1_session.csv` notes). `alone` photos leave `group_id` and `pitch_cm`
   empty and keep `plant_id`.
10. **Each plant's own orientation is FIXED across arrangements.** Mark every pot once, align the mark to the
   board, and never rotate a pot between its `alone`, `pair` and `quad` photos — a rotation makes the visible-area
   difference unreadable (occlusion vs pose would be confounded). Shoot `alone` first, then `pair`, then `quad`.

8. **`seed_vendor` + `seed_lot_or_purchase_ref` + `seed_label_photo` are the only reproducibility anchor** that
   exists for this material. If all three are blank, the plants cannot be re-sourced and every downstream
   genotype-dependent parameter stays `user_assumed`. Fill them before the destructive session, not after.

## Why the phenotype columns exist

The cultivar is unrecoverable, so the genotype facts the FSP needs are obtained by observation instead. Each
column answers one modelling question, and the literature that makes the observation diagnostic is named so the
inference is auditable:

| column(s) | what it decides in the model | source |
|---|---|---|
| `growth_habit`, `terminal_inflorescence`, `leaves_between_inflor` | whether stem-length prediction needs a termination point, and how many leaves a sympodial unit carries. A determinate plant breaks any "more resource → more stem" form. | Martí et al. 2006, J Exp Bot 57:2037 — Micro-Tom carries `sp` (self-pruning), confirmed by crossing and sequence |
| `leaf_color`, `leaf_rugosity` | whether internode length has a hormonal ceiling that light and resource supply cannot lift. Dark-green + rugose co-segregates with the `d` (DWARF, BR-biosynthesis) defect; GA3 alone barely elongates such plants, GA3 + brassinolide elongates >6x. Also: a rugose blade is not flat, which bears on the flat-leaf assumption in Addendum D.1 and on mesh relief (B5c). | Martí et al. 2006, same |
| `bse_fuchsin_result` | whether gs, Kleaf and A respond to shading at all. Heterobaric (BSE present) leaves showed Kleaf -41 % under shade; homobaric (`obv`) leaves sat at the same low value in both conditions. Test: 1 % fuchsin acid infiltrated at 0.027 MPa for 2 min — dry patches = heterobaric, uniform = homobaric. Optional; only needed before a light-treatment comparison. | Barbosa et al. 2019, Plant Cell Environ 42:1600 |

One finding from the same literature changes what is **not** worth recording per light condition: normalised
perimeter (perimeter^2/area) was strongly genotype-dependent and **not** influenced by irradiance, and elliptical
Fourier shape differences between light treatments were small. Blade outline shape is therefore a genotype
constant for this material. What light moved was SLA and the gas-exchange parameters. Do not add light-condition
columns to the shape tables.

## What is deliberately not recorded

Leaflet length, width and area are **not typed**. They come from the photographs with the ruler in frame
(31.1 mm outer-to-outer, `user_measured`), which is faster and more accurate than hand measurement, and carries a
known ±1.12 % per-photo scale uncertainty (**±2.23 % on an area**), measured in I.4b on 2026-10-08 and superseding the ±1.2 / ±2.4 % quoted at the old 3.0 cm width.

## Order of use

`1_session` once → `2_plant` per plant → `3_photo` per shutter press throughout → `4_height_reading` from the
`level` photos → then, only after the intact captures have been checked, `5_defoliation_step` (plant 1),
`6_compound` and `7_blade` (plants 2-3 and plant 1's removed compounds).
