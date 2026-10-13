# MTG convention for individual dwarf-tomato plants (2026-10-10)

Status: **specification. Decisions 8.1 and 8.2 made by the user on 2026-10-10 (section 8).** Author: Claude. No code yet.
Korean summary for the human: project doc `claude/MTG_기준_2026-10-10.md`.
Sources: Godin-style multiscale tree graph (scales, `/` decomposition, `<` succession, `+` branching);
Butturini et al. 2026, in silico Plants 8:diaf024, section 2.2.2 and Fig. 4 (rank/order convention);
generator tags in `tomato3d/synth/compound_leaf.py`; compound-structure record of 2026-10-10
(project doc `claude/복엽구조_형태_2026-10-10.md`).

## 1. Purpose and scope

One MTG per plant per capture, describing an **individual** plant (not an averaged plant). It is the shared
structure format between observation (phynotype2, reconstruction), the generator, light calculation and growth
forecasting. Flowers, trusses and roots are reserved classes, not specified here.

Not adopted from diaf024: their MTG is a **probabilistic average** over six plants with an occurrence-probability
column. Ours is per individual; instead of occurrence probability every value carries a `source_status`.

## 2. Scales and vertex classes

| scale | class | meaning |
|---|---|---|
| 1 | `Plant` | one plant |
| 2 | `Axis` | main stem (order 0) or side shoot (order 1) |
| 3 | `Metamer` | node + internode below it + what the node bears (one compound leaf, or cotyledon pair) |
| 3 | `CompoundLeaf` | the compound leaf borne by a metamer (complex of its organs) |
| 4 | `Internode` | stem segment |
| 4 | `Cotyledon` | each cotyledon |
| 4 | `Petiole` | attachment point P0 to the first leaflet-pair node |
| 4 | `RachisSegment` | rachis between two consecutive leaflet-bearing nodes |
| 4 | `Leaflet` | primary leaflet: terminal, paired lateral, or intercalary |
| 5 | `SecondaryLeaflet` | small leaflet branching from a leaflet base (decided 8.2: own vertex) |
| 4 | `Apex` | shoot apex / bud |

## 3. Edges

Every vertex row has `complex_id` (the vertex one scale up that contains it, `/`) and, within its scale,
`parent_id` with `edge_type`:
- `<` succession along the same axis: internode -> next internode; petiole -> first rachis segment ->
  next rachis segment; **last rachis segment -> terminal leaflet** (the terminal leaflet continues the rachis axis).
- `+` branching: node -> petiole (leaf insertion); node -> side-shoot first internode; rachis node -> lateral or
  intercalary leaflet; leaflet -> secondary leaflet.
So the terminal leaflet is the only leaflet attached by `<`; lateral leaflets are attached by `+`. This makes
"terminal" a structural fact of the graph, not only a tag.

## 4. Identifiers (identity is never a position)

- `vertex_id` is a stable string that never encodes rank, height or order of appearance in a photo.
- Plant: `<plant_id>` (e.g. `dwt_101`).
- Axis: `<plant_id>/A0` main stem; `<plant_id>/A1-<serial>` side shoots.
- CompoundLeaf: `<plant_id>/C<4-digit serial>` - identical to phynotype2 `track_id`. Serials are issued in
  creation order and never reused or renumbered.
- Leaflet: `<compound_id>/<tag>`. Tags as in the generator: `T` terminal; `P<i><L|R>` lateral pair i counted
  **from the base** (P1 = basal pair), L/R = left/right looking from base to tip; `I<j>` intercalary with a
  `side` attribute (L|R). Observed structures that differ from the generator's placement rule (e.g. an
  intercalary pair) are recorded as observed; the generator rule is not imposed on observations.
- SecondaryLeaflet: `<leaflet_id>/S<k>`.
- Internode / Petiole / RachisSegment: `<owner_id>/<class code><index from base>` (e.g. `.../C0003/R2`).
- Human names (`L01`, organ_label) are **display attributes only** (`display_name`), never identity.

## 5. Positional attributes

- `order`: 0 main stem, 1 side shoot (diaf024).
- `rank` (decision 8.1, user 2026-10-10): **the lowest compound leaf present on the plant being grown is rank 1**;
  ranks increase by 1 per leaf-bearing node upward along the main stem; every compound has its own rank (no shared
  rank). Cotyledons are not ranked (`rank = unavailable`, class `Cotyledon`).
  - Anchoring (Claude's reading, to be confirmed by the user): ranks are fixed at the plant's **rank reference
    capture** (`rank_reference_capture_id` in the plant row) and never renumbered afterwards. A leaf lost later
    keeps its rank; the next leaf does not become rank 1. New leaves above take max rank + 1. A lower leaf
    discovered later (previously hidden) gets rank 0, -1, ... rather than shifting existing ranks.
  - This matches the repository's `rank_from_bottom` counting at the reference capture; it does not match
    diaf024 (cotyledon internode = 0, first two leaves shared rank 1), so diaf024 rank values are not directly
    comparable - a conversion needs the cotyledon node and leaves below the reference, which are usually unknown.
  - Side shoots: rank counted on that axis from 1 (first leaf of the shoot).
  - `unavailable` when the stem position is not established (always the case from top view alone).
- `pair_index` (1 = basal), `side` (L|R|C for terminal), `node_index` along the rachis (1 = first pair node).

## 6. Value attributes and source status

Every numeric or categorical attribute has a sibling `<name>__status` in:
`measured` (instrument on the organ), `photo_estimate` (read from a photo scale, with `<name>__error_mm` if
stated), `reconstructed` (pipeline from images), `generated_candidate` (generator output; also needs
`candidate_id`), `assumed` (placeholder), `unavailable` (value empty; nothing imputed).

Geometry (state the frame in a file-level `frame` field; mm, degrees in files):
`base_xyz_mm`, `tip_xyz_mm`, `length_mm`, `width_mm`, `area_mm2`, `azimuth_deg`, `elevation_deg` (signed;
never `abs`), `normal_xyz`.

CompoundLeaf-level:
- `total_length_mm` (petiole base to terminal tip).
- `rachis_bend_type` in `flat|bent|intermediate|unknown`; `rachis_bend_theta_deg` = angle between the base
  direction (P0 -> first pair node) and the distal direction (rachis mid -> last pair node);
  `chord_to_path_ratio` = |P0 -> last pair node| / path length through the nodes. Thresholds for the types are
  **not set** (pending measurement of the seven example photos); until then `rachis_bend_type` comes only from a
  human label. From top view alone it is `unknown`.
- `n_primary_pairs`, `n_intercalary`, `has_secondary_leaflets` (derived from child vertices, never typed in).
Leaflet-level: `condition` in `green|browned|curled_damaged|unknown`; `area_basis` in `green_only|full_outline`
(pending human decision on browned margins).

## 7. Time, observation and generated geometry

- One MTG snapshot per (plant, capture): files `mtg_vertices.csv` per snapshot, with `plant_id, capture_id`.
  Identity across snapshots is by `vertex_id`; appearance/disappearance comes from phynotype2 `track_states.csv`
  and `events.csv`, never inferred from a missing vertex.
- Generated geometry never enters the main snapshot as observed. Each generator candidate is a separate
  sub-MTG (`candidate_id`) rooted at the same CompoundLeaf `vertex_id`, all its values `generated_candidate`.
- A vertex absent from a capture is either listed with `observed = false` (structure known, not seen) or not
  listed (structure unknown); it is never deleted from earlier snapshots.

## 8. Pending decisions (human)

8.1 DECIDED (user, 2026-10-10): "현재 육성중인 식물의 맨 아래잎을 랭크1로" - the lowest leaf of the plant being
grown is rank 1 (section 5). Open sub-question for the user: the anchoring rule in section 5 (fixed at a reference
capture, no renumbering) is Claude's reading.
8.2 DECIDED (user, 2026-10-10): secondary leaflets are their own vertices at scale 5 (`SecondaryLeaflet`).

## 9. File layout (CSV, project rule)

`mtg_vertices.csv`: `plant_id, capture_id, vertex_id, scale, class, complex_id, parent_id, edge_type,
display_name, order, rank, pair_index, side, node_index, observed, candidate_id,
frame, <attributes>, <attribute>__status ...`. Attribute columns are declared in a JSON sidecar
`mtg_schema.json` (name, unit, allowed values). Conversion to OpenAlea `.mtg` text or GroIMP input is a separate
exporter and must preserve `vertex_id`.

## 10. Worked example - the dissected compound of 2026-10-10

```
CompoundLeaf  dwt_?/C????        total_length_mm 50.71 (measured, caliper)
                                 rachis_bend_type unknown (type before detachment not recorded)
 / Petiole        P0 -> node 1   petiole+rachis length ~33 mm (photo_estimate, +-2 mm, whole axis)
 < RachisSegment  R1 (node 1) + P1L ~20 mm, + P1R ~18 mm        (photo_estimate)
 < RachisSegment  R2 (node 2) + P2L ~24 mm (+ S1 secondary), + P2R ~26 mm (largest)
 < RachisSegment  R3 (node 3) + P3L ~23 mm, + P3R ~17 mm (condition browned/curled_damaged)
                              + I1 (side L) ~10 mm, + I2 (side R) ~10 mm   (observed intercalary pair)
 < Leaflet T ~23 mm (+ S1 secondary at base)
rank: unavailable (stem position not recorded)
```
Only `total_length_mm` is `measured`; all other lengths are `photo_estimate`.

---

## 11. Amendment A1 (2026-10-10) — incorporated by reference (appended 2026-10-11, Claude Code)

A1.1–A1.5 of `handoff/CLAUDE_CODE_CLI_PROMPT_MTG_AMEND_2026-10-10.md` are adopted **as written there**;
A1.1 is a user decision. Nothing above this line is rewritten (`handoff/` is append-only, CONVENTIONS §5);
the in-place `[superseded by A1.x]` marks that prompt asked for are replaced by this list:

| Earlier text | Now |
|---|---|
| §5, "Anchoring (Claude's reading, to be confirmed by the user)" | **confirmed** — A1.1, decision 8.1b |
| §8.1, "Open sub-question for the user: the anchoring rule" | **resolved** — 8.1b |
| §6 status vocabulary | gains `user_stated`, `app_ratio` (A1.2) and `derived` (A1.5, §12 below) |
| §6 `elevation_deg` "signed; never abs" | sign fixed by A1.4: angle above the horizontal plane of the file's `frame`, **+ = upward**, range −90..+90, `atan2(dz, hypot(dx, dy))` |
| §6 bend points P0..P3 free-floating | vertex references per A1.5: P0 = base of the Petiole vertex, P1 = node of lateral pair 1, P3 = node of the last lateral pair, P2 = rachis-path midpoint between P1 and P3 (derived, not stored); `theta_deg`, `chord_over_path` status `derived` |
| Plant vertex attributes | gains `variety`, `slot_id`, `light_ratio`, `light_ratio_source` (A1.2); other-variety plants carry a plant-level MTG only (A1.3) |

A1.4 generator check, done 2026-10-11: the generator stores `leaf_elevation_deg` as "initial rachis
elevation above horizontal" (+ = up, `generator_config_template.json:49-54`) and `rachis_droop_deg` /
`leaflet_bend_deg` as **downward-positive** bends (`:184-191`, `leaflet_surface.py:12`). No sign conflict with
A1.4; conversion: elevation of a drooped segment = initial elevation − cumulative droop. No `mtg_schema.json`
or `mtg_vertices.csv` exists yet, so there is nothing to add there; when one is created it must carry §9 + §12.

## 12. Amendment A2 (2026-10-11) — geometry attributes from the literature review (Claude Code)

Source: `handoff/CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md` P1 item 1 (+ its Sarlikioti addendum). Binding
rule unchanged: none of the cited papers is Micro-Tom; every literature number entering a file carries
`source_kind = literature_other_cultivar` (or `literature_wild_species`). This amendment defines quantities;
it sets **no thresholds and no default values**.

### 12.1 Azimuth reference — prerequisite, previously undefined
`azimuth_deg` (§6) had no stated zero or sense. Definition: the angle of a direction projected onto the
horizontal plane of the file's `frame`, measured from the frame's **+X toward +Y**, i.e. counter-clockwise
when viewed from +Z (from above), range [0, 360). For `frame = plant_local_mm` the rotation comes from
phynotype2 `frame_transforms.csv`; if `rotation_status` is not solved, **every azimuth in that capture is
`unavailable`**. phynotype2's "azimuth around the pot centre" is this definition with the pot centre as origin.

### 12.2 CompoundLeaf `insertion_angle_deg`
Angle between the main-stem axis **above the node** and the petiole direction (P0 → P1 of A1.5), 0–180°
(Chen 2014 "leaf angle"): 0 = petiole lying along the stem upward, 90 = perpendicular, 180 = hanging along
the stem. Source: a side view with solved relative pose, or 3-D. **Top view alone ⇒ `unavailable`.**

**Scope note (homonym, deliberate):** a `Leaflet.insertion_angle_deg` already exists in the generator and
in `tomato3d/synth/leafarea.py:339` / Addendum C — the angle between the rachis tangent and the leaflet
midrib, in the leaf plane. Same column name at two scales, different reference axes. In `mtg_vertices.csv`
every row carries `class`, so the two never share a cell; **any flat export must prefix by class**
(`compound_insertion_angle_deg`, `leaflet_insertion_angle_deg`). Do not rename either.

### 12.3 CompoundLeaf `rachis_bend_alpha_<i>_deg`, `n_bend_nodes`, `rachis_curvature_deg`
Axis segments, in `<` order (§3): Petiole (P0 → node 1), then RachisSegment R1, R2, … The bend at lateral-pair
node *i* is α_i = angle between the direction of the segment ending at node *i* and the direction of the
segment starting there, in the plane spanned by the two directions (Chen 2014 Fig. 1B). **Sign: positive =
the distal segment bends downward** (its `elevation_deg` lower than the proximal segment's), negative = it
rises. This matches the generator's downward-positive `rachis_droop_deg` and A1.4's upward-positive
elevation. One column per node (CSV): `rachis_bend_alpha_1_deg` … `rachis_bend_alpha_<m>_deg`, with
`n_bend_nodes = m` = number of lateral-pair nodes; the terminal leaflet is not a node and gets no α. For a
3-pair compound: α1 (Petiole → R1), α2 (R1 → R2), α3 (R2 → R3, the segment carrying the terminal leaflet).
`rachis_curvature_deg` = signed Σ α_i, status `derived`.

**Relation to θ (A1.5, 복엽 §3).** θ is the angle between P0 → P1 (petiole) and P2 → P3 (rachis midpoint →
last pair node). When the bends are coplanar and P2 lies on the segment ending at P3, θ = |α1 + … + α_{m−1}|:
θ **excludes the last bend α_m**, whose distal segment carries the terminal leaflet — which is exactly why θ
ignores terminal droop by construction. Σα includes it. They are therefore different quantities and both are
kept, both `derived`; each is `unavailable` whenever any node geometry it needs is `unavailable`. Flat/bent
thresholds remain unset (pending the 7 example photos, §8.4).

### 12.4 CompoundLeaf `petiole_base_azimuth_deg` and `blade_azimuth_deg` — two fields
- `petiole_base_azimuth_deg`: azimuth (12.1) of P0 → P1 — the insertion direction around the stem.
- `blade_azimuth_deg`: azimuth of the lamina direction, P1 → terminal-leaflet tip; if the tip is `unavailable`,
  P1 → last pair node, and `blade_azimuth_basis = last_pair_node` is recorded.
Each has its own `__status`. They are **never merged**. Justification: Sarlikioti et al. 2011 (mcr221)
measured row-crop phyllotaxis ≈160° against a nominal 137.5° because mature leaves rearrange, so the apparent
blade direction is not the insertion direction; Reinhardt et al. 2005 supports post-initiation change of the
apparent divergence. The separation is a design rule, not a result of either paper, and neither is Micro-Tom.
From a top view with solved rotation, `blade_azimuth_deg` is observable (`reconstructed` or
`photo_estimate`); `petiole_base_azimuth_deg` only if the insertion point itself is visible, else `unavailable`.

### 12.5 Plant `phyllotaxis_mean_divergence_deg`, `phyllotaxis_handedness`, `phyllotaxis_fit_sd_deg`, `phyllotaxis_fit_n`
Status `derived`. Produced only by the phyllotaxis estimator (`tools/phyllotaxis_fit.py`, **planned** —
literature prompt P1 item 2, not yet written) from ≥ 5 consecutive main-stem compounds with known **true
leaf order** and `petiole_base_azimuth_deg` present, by cumulative-angle regression y = a + b·leaf_index
(Kanahama 1993 method); otherwise all four `unavailable`. MTG `rank` 1 is the lowest leaf at the reference
capture, **not necessarily true leaf 1**; the first→second true-leaf interval is excluded only when the true
index is known. `phyllotaxis_handedness ∈ left|right|unknown`, **project definition**: `left` = successive
leaves advance counter-clockwise viewed from above (+Z, i.e. increasing azimuth under 12.1), `right` =
clockwise. This is operational; do not assume it matches any paper's left/right usage without checking that
paper's convention. The Kanahama range 119.3–154.7° (wild species) is the only published spread and may be
used as a prior **width**, never as a Micro-Tom value.

### 12.6 Side-view height — name carries the definition
If a height enters the Plant row it is one of `height_top_leaf_mm` (soil surface → highest leaflet point;
what images give) or `stem_length_mm` (P0 of the lowest ranked metamer → apex; what a model gives). Never one
column for both (diaf022 had exactly this mismatch between image and model).

### 12.7 File layout (extends §9)
`mtg_vertices.csv` gains, each with `<name>__status`: CompoundLeaf — `insertion_angle_deg`,
`rachis_bend_alpha_<i>_deg` (i = 1..n_bend_nodes), `n_bend_nodes`, `rachis_curvature_deg`,
`petiole_base_azimuth_deg`, `blade_azimuth_deg`, `blade_azimuth_basis`; Plant — the four 12.5 fields,
`height_top_leaf_mm`, `stem_length_mm`. Units: degrees in files, mm. When `mtg_schema.json` is created it
must list these with the allowed values above.

### 12.8 Unchanged, stated so nothing is read into A2
§6 status rules; `rachis_bend_type` stays a human label until §8.4 is decided; leaflet blade curl stays
undefined (§8.3); no generator value is changed; no numeric default is introduced anywhere.

### Pending decisions added to §8
- **8.3** Leaflet blade curl / rugosity: definition, reference axis and sign — human (복엽 §6 item 3).
- **8.4** θ flat/bent boundaries — after the 7 example photos are measured with the A1.5 points.
- **8.5** Whether the Kanahama prior width may seed the phynotype2 association tie-breaker (P1 item 3) —
  human; until then the tracker uses no azimuth prior.

### Worked example (§10) addendum
Dissected compound of 2026-10-10: `insertion_angle_deg unavailable` (detached), every `rachis_bend_alpha_<i>_deg`
and `rachis_curvature_deg` `unavailable` (detached; type before detachment not recorded), both azimuths
`unavailable` (no frame), `variety micro_tom`, `slot_id unavailable`, `light_ratio unavailable`.

## 13. Human decisions of 2026-10-11 (appended by Claude/claude.ai; nothing above edited)
User statement (2026-10-11): "1,2 는 보류, 3은 원래 윤곽".
- **area_basis = `full_outline` (decided).** Leaflet area is measured on the original leaflet outline,
  including browned / necrotic margins; it is NOT restricted to green tissue. Applies to every leaflet
  area field (projected px², mm² once scaled, caliper/scan records) and to the 기관측정 소엽 sheet.
  A green-only area may be stored only as an extra field `area_green_only_*` with its own status, never
  in the main area column. Status of the rule: `user_stated`.
- **8.3 leaflet blade curl / rugosity → `on_hold`** (no definition, axis or sign; stays undefined, no default).
- **8.4 θ flat/bent boundaries → `on_hold`** (`rachis_bend_type` stays a human label; no numeric threshold).
- 8.5 unchanged (still open).

## 14. Amendment A3 — side-view measurement source (Claude Code, 2026-10-12)

Appended on the instruction of `handoff/CLAUDE_CODE_CLI_PROMPT_P1_FIXES_2026-10-11.md` (A2). Nothing above this
line is edited. A3 adds **no threshold and no default value**; it fixes which side image a CompoundLeaf's
side-view angles are read from.

### 14.1 Rule
The side-view CompoundLeaf quantities — `insertion_angle_deg` (12.2; flat exports
`compound_insertion_angle_deg`), `rachis_bend_alpha_<i>_deg`, `n_bend_nodes`, `rachis_curvature_deg` (12.3),
`rachis_bend_theta_deg` and `chord_to_path_ratio` (A1.5) — enter a CompoundLeaf vertex **only from a side view
in which that compound's camera-relative direction class is `cl_left` or `cl_right`** (terminal leaflet pointing
sideways = the compound seen roughly side-on). Among such views the first by `view_id` is used. If a compound
has no such view in a capture, those attributes stay `unavailable` for that capture (reason recorded); a
`cl_toward`, `cl_away` or `unclear` view is never used for them. The direction class is the human label on real
photos (5 classes incl. `unclear`, `handoff/DETECTOR_POLICY_2026-10-09.md`) or the generator label on fixtures.
Rule version tag: `MTG_A3_v1:first_view_by_view_id_with_direction_class_cl_left_or_cl_right`.

### 14.2 Recording field
`side_geometry.csv` (one row per compound × view) carries `direction_class`, `selected_for_mtg`
(`true` on the one row whose values enter the MTG, else `false`) and `view_selection_rule` (the version tag).
The MTG snapshot's `structure_state.csv` `evidence_ref` of that CompoundLeaf names the selected `view_id` and the
rule. Implementation: `tomato3d/state/sidegeom.py::select_views` (the only implementation).

### 14.3 Evidence — synthetic only
R.1 side set, 50 finalized scenes (`build/sideprop_20261009_01`, batch a), generator truth points projected
through each scene's render camera, 2-D angle vs 3-D truth (`build/p1_side_validation_20261011/`):

| Selection | per-compound `compound_insertion_angle_deg` \|error\| median / p90 |
|---|---|
| A3 rule (first `cl_left`/`cl_right` view) | **7.0° / 15.6°** |
| first view regardless of class | 14.6° / 49.5° |
| by class, all compound-views | `cl_left` 5.4°, `cl_right` 6.1°, `cl_toward` 25.0°, `cl_away` 40.7° (medians) |

These are **projection errors against synthetic truth** (foreshortening of a 3-D angle seen in one image); they
are not real-photo accuracy, which is unmeasured (no human P0..Pm points exist). They justify the selection
rule only; they are not a tolerance and set no flat/bent boundary (8.4 stays on hold).

### 14.4 Unchanged
12.2 "top view alone ⇒ unavailable" stands; a side value needs a side image. Cross-view association of a
side-view compound with a top-view track is not defined here (fixtures join through their truth; real data
has no join yet).

### 14.5 Correction and full-set revalidation (Claude Code, 2026-10-12, same session)
The 7.0° / 15.6° row in 14.3 (and in `handoff/P1_EXECUTION_2026-10-11.md` §6.2) was computed with a silent
fallback to the first view for the 40 of 348 compounds that have **no** `cl_left`/`cl_right` view. A3 as written
in 14.1 has no fallback (those compounds stay `unavailable`). Without the fallback, and on the full R.1 set now
that render batches b and c are finalized (`build/p1_side_validation_20261012_01/side_view_rule_summary.csv`):

| Scenes | compounds with a side-on view | A3 median / p90 | first view median / p90 | compounds with no side-on view |
|---|---|---|---|---|
| 0–49 (batch a) | 308 | 6.1° / 13.8° | 14.5° / 48.6° | 40 |
| 0–149 (a+b+c) | 870 | **5.9° / 13.7°** | 14.5° / 52.9° | 168 (16 %) |

Per-class medians on all 150 scenes: `cl_left` 5.4°, `cl_right` 5.6°, `cl_toward` 25.7°, `cl_away` 40.7°;
quadrant converter exact 3118/3118. Still synthetic projection error, not real-photo accuracy. The rule in 14.1
is unchanged; 16 % of compounds get no side value from a 4-view capture under it.

## 15. Amendment A4 — axes and side shoots (Claude Code, 2026-10-12)

Appended on the instruction of `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SIDESHOOT_2026-10-12.md` (S1); nothing above is
edited. Source of the decisions: the user's side-shoot decisions of 2026-10-12 (claude.ai project doc
`정의집_토마토_2026-10-11` §1-1, not on disk; restated in the prompt), all `user_stated`. No threshold, angle or
default size is introduced. Consumer alignment: `handoff/P4_SIDESHOOT_SCIENCE_AND_IO_CONTRACT_2026-10-12.md` §3
(`fsp-axes-1`).

### 15.1 Decisions
1. **Registration.** A side shoot first appears with **two leaves together**. It is registered as an `axis_shoot`:
   an order-1 axis; `first_observed` = that capture; emergence interval = (previous capture, this capture].
   Absence of a side shoot in an image never removes it; an unobserved side shoot is never generated
   (`topology_scope = provided_axes`, `completeness = unavailable`, unchanged).
2. **State change.** An `axis_shoot` becomes a `substem` when its first two leaves are fully expanded (an
   observation classification recorded by a person, not an age threshold). From then on its apex bundle is shown
   as `shoot′` (S1), `shoot″` (S2), …; the main-stem apex bundle stays `shoot`.
3. **Ranks on every axis.** The same rule on every axis: a leaf gets the next rank when it has unfolded and is
   separately visible; ranks are never renumbered (A1.1 applies per axis). Tie of the first two leaves of a side
   axis in one capture: **proposal** — the basal leaf of the side axis is rank 1 (`tie_rule = proposed`).
4. **Prime = which side shoot, not axis order.** S1 → `′`, S2 → `″`. Numbering basis is **open**; implemented
   proposal: registration order, immutable; same capture → lower node first (`numbering_basis = proposed`).
5. **Sympodial continuation** (the axis taking over above a truss) is main stem `M`, never a substem. A truss has
   no leaves, so the two-leaf rule already excludes it from registration.
6. **Orders.** `order` 0 = main stem, 1 = side shoot. Order-2 side shoots are an **open item** and are rejected by
   the validators until defined.

### 15.2 Stored fields (never a prime character in any file)
- `axis` ∈ `M`, `S1`, `S2`, … on every `mtg_vertices.csv` and `identity_manifest.csv` row (`unavailable` when
  no human label / synthetic truth states it); `order` 0/1; `rank` integer per axis;
  `parent_rank` = rank of the **main-stem** leaf at whose axil the side shoot sits (MTG attribute on the side Axis
  vertex, and in `axes.csv`; `unavailable` without a human record or a side view — from top views the human
  registry is the only source); `axis_state` ∈ `axis_shoot` | `substem` (`main` for M in `axes.csv`);
  `leaf_unfolded` (CompoundLeaf, true|false; a rank requires `true`).
- Display labels only: `1`, `1′`, `1″` (`tomato3d/state/schema.py::display_label`); validators reject U+2032,
  U+2033, U+2034, U+2057, U+02B9, U+02BA in any stored cell.

### 15.3 Identifiers
- Axis vertex: `<plant_id>/A0` for the main stem (§4, unchanged) and **`<plant_id>/S<k>`** for side shoots
  (replaces the unused `A1-<serial>` grammar of §4 for side shoots).
- Compounds keep their track ids `<plant_id>/C<4-digit serial>` (never renumbered, never re-assigned to another
  axis) and gain `axis`; their `complex_id` is their axis vertex. A compound belongs to one axis for life.
- `axes.csv` (one row per plant instance × capture × axis) carries both the A4 names and the fsp-axes-1 exchange
  names: `axis` = `axis_id`, `axis_state` = `stage` (validator-enforced equality); `parent_node_id` = the main-stem
  CompoundLeaf vertex whose rank is `parent_rank` (the leaf at whose axil the shoot sits), else `unavailable`;
  main axis `parent_rank = 0` (fsp-axes-1 sentinel, not a leaf rank). An order-1 axis needs a registration record
  (`registration_ref` to the registry row) and, when both leaves were observed, `registration_leaf_ids` (exactly two).

### 15.4 Human registry
`data/records/side_shoots/side_shoot_registry.csv` (human-owned, read-only; template
`build/side_shoot_registry_template/`): `plant_id, axis, parent_rank, first_observed, axis_state, state_date, note`
— one row per side shoot and recorded state (`state_date` added so the substem change can be placed at a
capture). Registry dates map to the first capture of that plant on or after the date.

### 15.5 Open items
Numbering basis (15.1-4), tie rule (15.1-3), order-2 side shoots (15.1-6), whether a side shoot carrying a truss
continues sympodially as its own S-axis (fsp-axes-1 states it does; not observed here), and how a top-view tracker
could ever propose an axis without a human label (today it cannot: no axis is inferred from position).


## 16. Amendment A5 — trusses, segments and confirmed axis policies (Claude Code, 2026-10-12)

Appended on the instruction of `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md` (T1); nothing above is
edited. Source: the user's decisions of 2026-10-12 as recorded in `docs/정의집_토마토_2026-10-11.md` §0, §1-1 (now
on disk; this convention stays the binding contract). All decisions below are `user_stated`. No threshold, cadence,
angle or size is introduced. Implementation: `tomato3d/state/trusses.py`, `schema.py` revision 4.

### 16.1 A4 proposals now confirmed (no longer proposals)
1. **Side-shoot numbering** = registration (`axis_shoot`) order: `S1`, `S2`, …; on a tie within one capture the
   lower attachment node is numbered first; a number once given is never changed. Stored as
   `numbering_basis = user_stated:registration_order_immutable;same_capture_lower_node_first` (packages of
   revision ≤ 3 carry the earlier `proposed:` value).
2. **Rank 1 on a simultaneous expansion** of the first two leaves of a side axis in one capture = the basal leaf
   of that side axis. Stored as `tie_rule = user_stated:basal_leaf_of_side_axis_is_rank_1`.
3. **Order-2 side shoots — notation reserved, code still forbids.** The spelling is the dotted axis path
   `S1.1`, `S1.2` (`order = 2`, `parent_axis = S1`, `parent_rank` = the rank on S1; display label `S1.1:1`).
   Primes are NOT reused: prime count already means "which side shoot". Every validator that rejects order 2 (or
   an `S1.1` code in any table or registry) now names this reserved spelling in its error.

### 16.2 New decisions
4. **Side shoots bear trusses** (user observation). The determinate program is judged per axis, substems included.
5. **A sympodial continuation above a truss is ONE axis.** The axis id stays `M` (or `S1`), leaf ranks run on
   unbroken, the axis is never split. The truss is recorded at its node, and every node carries `segment_index`.
   This closes the A4 open item "whether a side shoot carrying a truss continues as its own S-axis": it does, as
   the same S-axis (§15.5 item resolved; consistent with fsp-axes-1).

### 16.3 `segment_index`
- Integer ≥ 1, **per axis**: segment 1 is from the axis base to its first truss, segment k+1 lies between its
  k-th and (k+1)-th truss. It increments at each truss on that axis and nowhere else.
- Positions along an axis: the leaf of rank r is at (r, 0); a truss recorded with `above_rank = a` sits directly
  above leaf a, at (a, 1). `segment_index(node) = 1 + (trusses on the same axis strictly below the node)`. Hence it
  starts at 1, never decreases along the axis, a truss carries the index of the segment it closes, and the next
  node above a truss is one higher.
- Carried on every row that carries `axis`: `mtg_vertices.csv` value attribute `segment_index` (+ `__status`,
  `derived`) on Axis, CompoundLeaf, Truss and the compound's organ rows (organs repeat their compound's index;
  an Axis row carries its **apical** segment = 1 + its trusses); `identity_manifest.csv` `segment_index`;
  `axes.csv` `segment_index` (+ status) and `truss_count` (apical segment = truss_count + 1).
- **Derived, never entered and never guessed:** from the human truss registry (16.5) plus the leaf ranks. No
  registry → `unavailable` everywhere (absence of a record is not "no truss"); a leaf without rank →
  `unavailable`; a truss on that axis without a recorded position → the leaves of that axis `unavailable` (the
  apical index, a count, stays known). A snapshot uses only trusses recorded on or before its capture (no
  look-ahead); a truss recorded later may raise the index of an already-ranked leaf in later snapshots — the
  change appears in `change_log.csv`; ranks themselves are never renumbered.
- Used by the two-successive-truss stop rule (counted per axis by the consumer; P1 states no cadence).

### 16.4 Truss vertex (scale table addition)
| scale | class | meaning |
|---|---|---|
| 3 | `Truss` | an inflorescence borne on an axis; sits beside CompoundLeaf on its bearing axis; bears no leaves |

- `vertex_id = <plant_id>/F<4-digit serial>`, the serial issued in registry row order per plant (creation order;
  never a rank or a position, §4). `complex_id` = the bearing axis vertex (`<plant_id>/A0` or `<plant_id>/S<k>`),
  edge `+`. Attributes: `axis`, `order` (derived from the axis), `parent_rank` = the registry's `above_rank` (rank,
  on the bearing axis, of the leaf directly below the truss; status `user_stated` real / `synthetic_truth`
  fixture), `segment_index`. `first_observed`, the emergence interval and the registry reference are in
  `trusses.csv` (one row per plant instance × capture × truss, from the capture of its first record on).
- A truss never carries a leaf `rank` or `leaf_unfolded`, is never an `axis_shoot` (it has no leaves, so the
  two-leaf rule of 15.1-1 already excludes it), and has no geometry: no truss detector exists and the generator
  has no truss geometry (`tomato3d/synth/`, checked 2026-10-12). Every geometric value stays `unavailable`.
- A truss on `S<k>` exists only if that side shoot is in the side-shoot registry and was registered no later than
  the truss.

### 16.5 Human truss registry
`data/records/trusses/truss_registry.csv` (human-owned, read-only for agents; template
`build/truss_registry_template/`): `plant_id, axis, above_rank, first_observed, note`. `axis` = `M` or `S<k>`;
`above_rank` blank when unknown; rows appended in observation order per plant (dates may not go backwards, because
the row order is the truss serial). One truss per (plant, axis, above_rank).

### 16.6 Still open
Whether code may allow `order = 2` (notation fixed in 16.1-3; validators reject it). How a top view could ever
locate a truss or its node without a human record (today it cannot).
