"""P1.5 - observations + tracks -> one MTG snapshot per capture (Stage-2 spec sections 5-7).

Rules implemented (each has a test):

* identity comes only from the tracker (``identity_manifest``); this module never mints an id;
* every value carries its own ``__status``; a snapshot is computed from **its own capture only** -
  nothing is filled from a previous capture, a model prior or a generator range (no promotion);
* top view alone: insertion angle, elevation, 3-D position, true surface, rachis bends, theta
  and rank stay ``unavailable`` (Stage-2 section 5);
* ``rank`` / ``rachis_bend_type`` come only from a human record (status ``user_stated``) or, for
  rank, from the A1.1 anchoring rule applied to supplied heights (:func:`anchor_ranks`);
* side-view geometry enters a compound row only through an explicit cross-view join supplied
  by the caller, with that join's provenance; a real cross-view join does not exist yet;
* generated candidates never enter the main snapshot (:func:`candidate_rows` builds the sub-MTG);
* diurnal guard: :func:`comparisons` writes a change only between captures of the same phase with
  both times since lights-on present;
* every ``unavailable`` cell gets a row in ``unresolved.csv`` with its blocking reason;
* MTG A5: ``Truss`` vertices come only from the truss registry (no detector, no generated geometry) and
  ``segment_index`` is derived from that registry plus the ranks (:mod:`tomato3d.state.trusses`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import geometry as g
from tomato3d.state import schema as s
from tomato3d.state import trusses as tr

#: P1 extension of ``blade_azimuth_basis`` (A2 12.4 lists terminal_tip | last_pair_node): the
#: top-view proxy, from the compound mask point nearest the pot centre to the farthest one.
TOP_BLADE_BASIS = "top_mask_proximal_to_distal"


@dataclass(frozen=True)
class CaptureInfo:
    capture_id: str
    frame: str  # plant_local_mm (rim-plane projection, needs scale + centre) or image_px
    mm_per_px: float | None
    center_px: tuple[float, float] | None
    rotation_deg: float | None
    photoperiod_phase: str
    time_since_lights_on_min: float | None
    evidence: str
    scale_source: str
    #: T6: 1-sigma of mm_per_px (0 for a declared synthetic camera); propagated to every mm2 value
    mm_per_px_sd: float | None = None


@dataclass
class SnapshotInputs:
    plant_id: str
    plant_instance_id: str
    capture: CaptureInfo
    observations: Sequence[Mapping[str, str]]
    masks: Mapping[str, np.ndarray]
    identity_rows: Sequence[Mapping[str, str]]
    human_records: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    side_values: Mapping[str, Mapping[str, tuple[str, str]]] = field(default_factory=dict)
    side_join_ref: str = UNAVAILABLE
    #: compound vertex id -> side view the side values came from (MTG A3); recorded in structure_state
    side_view_of: Mapping[str, str] = field(default_factory=dict)
    #: MTG A4: ``axes.csv`` rows (all captures; this snapshot uses its own capture's rows)
    axes_rows: Sequence[Mapping[str, str]] = ()
    plant_values: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    #: status written for ``human_records`` values: ``user_stated`` (a person's record) or, in a synthetic
    #: fixture only, ``synthetic_truth`` (leaf records read from the scene truth through the fixture join)
    record_status: str = "user_stated"
    #: MTG A5: trusses recorded on or before this capture; None = no truss registry (segments unavailable)
    trusses_now: Sequence[tr.TrussEntry] | None = None
    #: status of the registry's ``above_rank`` (``user_stated`` real, ``synthetic_truth`` fixture)
    truss_status: str = "user_stated"


# --------------------------------------------------------------------------------------
# Rank anchoring (MTG A1.1)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RankResult:
    ranks: dict[str, int]
    unresolved: dict[str, str]


def anchor_ranks(heights_mm: Mapping[str, float], previous: Mapping[str, int] | None) -> RankResult:
    """A1.1: at the reference capture (``previous is None``) the lowest compound is rank 1 and
    ranks rise by 1 per compound upward. Later captures never renumber: existing ranks are kept
    (also for leaves no longer present), a new compound above every ranked one takes max + 1, a
    lower one discovered later takes 0, -1, ... A new compound between two ranked ones cannot be
    ranked without renumbering, so it stays unavailable with that reason (the rule has no case)."""
    if previous is None:
        order = sorted(heights_mm, key=lambda k: (heights_mm[k], k))
        return RankResult({k: i for i, k in enumerate(order, start=1)}, {})
    ranks = dict(previous)
    unresolved: dict[str, str] = {}
    ranked_present = {k: heights_mm[k] for k in heights_mm if k in previous}
    new = sorted((k for k in heights_mm if k not in previous), key=lambda k: (heights_mm[k], k))
    if not ranked_present:
        for k in new:
            unresolved[k] = "no ranked compound present to anchor against"
        return RankResult(ranks, unresolved)
    top_h, low_h = max(ranked_present.values()), min(ranked_present.values())
    above = [k for k in new if heights_mm[k] > top_h]
    below = sorted((k for k in new if heights_mm[k] < low_h), key=lambda k: -heights_mm[k])
    for k in above:
        ranks[k] = max(ranks.values()) + 1
    floor = min(ranks.values())
    for i, k in enumerate(below, start=1):
        ranks[k] = min(floor, 1) - i
    for k in new:
        if k not in ranks:
            unresolved[k] = "new compound between ranked compounds; A1.1 has no case without renumbering"
    return RankResult(ranks, unresolved)


# --------------------------------------------------------------------------------------
# Snapshot
# --------------------------------------------------------------------------------------


def _row(inp: SnapshotInputs, vertex_id: str, scale: int, cls: str, complex_id: str, parent: str, edge: str,
         observed: bool, axis: str = UNAVAILABLE) -> dict[str, str]:
    row = s.blank_mtg_row()
    row.update(plant_instance_id=inp.plant_instance_id, plant_id=inp.plant_id, capture_id=inp.capture.capture_id,
               snapshot_capture_id=inp.capture.capture_id, vertex_id=vertex_id, scale=str(scale), axis=axis,
               complex_id=complex_id, parent_id=parent, edge_type=edge, display_name=UNAVAILABLE,
               observed="true" if observed else "false", frame=inp.capture.frame, evidence=inp.capture.evidence,
               **{"class": cls})
    return row


def _mask_axis(mask: np.ndarray, info: CaptureInfo) -> tuple[float | None, float | None]:
    """(blade azimuth deg in the plant frame, projected axis length mm) from a top mask, or None."""
    if info.center_px is None or info.rotation_deg is None:
        return None, None
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None, None
    cx, cy = info.center_px
    r = np.hypot(xs - cx, cy - ys)
    near, far = int(np.argmin(r)), int(np.argmax(r))
    vec = np.array([xs[far] - xs[near], ys[near] - ys[far], 0.0], float)  # image rows down -> +Y up
    az = g.azimuth_deg(vec)
    az = None if az is None else (az - info.rotation_deg) % 360.0
    length = None if info.mm_per_px is None else float(np.hypot(vec[0], vec[1])) * info.mm_per_px
    return az, length


def build_snapshot(inp: SnapshotInputs) -> list[dict[str, str]]:
    """Main MTG snapshot of one plant at one capture (top-view observations + supplied records)."""
    cap = inp.capture
    pid = inp.plant_id
    axis = f"{pid}/A0"
    obs_by_id = {o["obs_id"]: o for o in inp.observations}
    rows: list[dict[str, str]] = []
    plant = _row(inp, pid, 1, "Plant", UNAVAILABLE, UNAVAILABLE, UNAVAILABLE, True)
    for attr, (value, status) in inp.plant_values.items():
        s.set_value(plant, attr, value, status)
    rows.append(plant)
    main = _row(inp, axis, 2, "Axis", pid, UNAVAILABLE, UNAVAILABLE, False, "M")
    s.set_value(main, "order", "0", "derived")
    rows.append(main)
    for a in sorted((r for r in inp.axes_rows if r["capture_id"] == cap.capture_id and r["axis"] != "M"),
                    key=lambda r: int(r["axis"][1:])):
        side = _row(inp, a["axis_vertex_id"], 2, "Axis", pid, axis, "+", False, a["axis"])
        s.set_value(side, "order", "1", "derived")
        if a["parent_rank"] != UNAVAILABLE:
            s.set_value(side, "parent_rank", a["parent_rank"], a["parent_rank__status"])
        rows.append(side)
    compounds = [r for r in inp.identity_rows
                 if r["capture_id"] == cap.capture_id and r["organ_class"] == "compound_leaf"
                 and r["organ_id"] != s.UNASSIGNED_ORGAN]
    terminals = {r["parent_id"]: r for r in inp.identity_rows
                 if r["capture_id"] == cap.capture_id and r["organ_class"] == "terminal_leaflet"}
    for ident in sorted(compounds, key=lambda r: r["organ_id"]):
        cid = ident["organ_id"]
        observed_now = ident["track_state"] in ("continued", "reappeared", "first_observed")
        leaf_axis = ident.get("axis", UNAVAILABLE)
        complex_id = UNAVAILABLE if leaf_axis == UNAVAILABLE else (axis if leaf_axis == "M" else f"{pid}/{leaf_axis}")
        row = _row(inp, cid, 3, "CompoundLeaf", complex_id, UNAVAILABLE, "+", observed_now, leaf_axis)
        if leaf_axis != UNAVAILABLE:
            s.set_value(row, "order", "0" if leaf_axis == "M" else "1", "derived")
        record = inp.human_records.get(cid, {})
        if record.get("leaf_unfolded") in ("true", "false"):
            s.set_value(row, "leaf_unfolded", record["leaf_unfolded"], inp.record_status)
        if record.get("rank") not in (None, "", UNAVAILABLE):
            s.set_value(row, "rank", record["rank"], inp.record_status)
        if record.get("rachis_bend_type") not in (None, "", UNAVAILABLE):
            s.set_value(row, "rachis_bend_type", record["rachis_bend_type"], "user_stated")
        if observed_now and ident["obs_id"] in obs_by_id and cap.frame == "plant_local_mm":
            az, _ = _mask_axis(inp.masks[ident["obs_id"]], cap)
            if az is not None:
                s.set_value(row, "blade_azimuth_deg", s.fmt(az, 3), "reconstructed")
                s.set_value(row, "blade_azimuth_basis", TOP_BLADE_BASIS, "reconstructed")
        for attr, (value, status) in inp.side_values.get(cid, {}).items():
            s.set_value(row, attr, value, status)
        rows.append(row)
        term = terminals.get(cid)
        if term is not None and term["obs_id"] in obs_by_id:
            trow = _row(inp, term["organ_id"], 4, "Leaflet", cid, UNAVAILABLE, "<", True, leaf_axis)
            trow["side"] = "C"
            if cap.frame == "plant_local_mm":
                az, _ = _mask_axis(inp.masks[term["obs_id"]], cap)
                if az is not None:
                    s.set_value(trow, "azimuth_deg", s.fmt(az, 3), "reconstructed")
            rows.append(trow)
    # MTG A5: registry trusses as scale-3 vertices on their axis, then segment_index on every axis row
    if inp.trusses_now:
        axis_vertex = {r["axis"]: r["vertex_id"] for r in rows if r["class"] == "Axis"}
        rows += tr.truss_vertex_rows(plant, inp.trusses_now, axis_vertex, inp.truss_status)
    tr.apply_segments(rows, inp.trusses_now)
    return rows


# --------------------------------------------------------------------------------------
# Areas (four kinds, never merged) and structure state
# --------------------------------------------------------------------------------------


def area_rows(inp: SnapshotInputs, obs_to_track: Mapping[tuple[str, str], str]) -> list[dict[str, str]]:
    """Visible projected area per observed compound/leaflet. Completed / lamina / green-only stay
    unavailable here (no completion accepted, top view gives no surface, no colour model)."""
    cap = inp.capture
    out = []
    for o in inp.observations:
        if o["obs_class"] not in ("compound_leaf", "terminal_leaflet", "leaflet"):
            continue
        if o["review_state"] not in ("accepted", "edited"):
            continue
        tid = obs_to_track.get((cap.capture_id, o["obs_id"]))
        if o["obs_class"] == "leaflet":
            parent_track = obs_to_track.get((cap.capture_id, o["parent_obs_id"]))
            compound, leaflet = (parent_track or UNAVAILABLE), UNAVAILABLE
        elif o["obs_class"] == "terminal_leaflet":
            compound, leaflet = (tid.rsplit("/", 1)[0] if tid else UNAVAILABLE), (tid or UNAVAILABLE)
        else:
            compound, leaflet = (tid or UNAVAILABLE), UNAVAILABLE
        row = {c: UNAVAILABLE for c in s.AREAS_COLUMNS}
        row.update(plant_instance_id=inp.plant_instance_id, capture_id=cap.capture_id, compound_id=compound,
                   leaflet_id=leaflet, part="compound" if o["obs_class"] == "compound_leaf" else "leaflet",
                   obs_id=o["obs_id"], evidence=cap.evidence, area_basis=s.AREA_BASIS_MAIN,
                   scale_source=cap.scale_source if cap.mm_per_px is not None else UNAVAILABLE,
                   visible_projected_area_px2=o["area_px2"], visible_projected_area_px2__status="observed")
        if cap.mm_per_px is not None and cap.mm_per_px_sd is not None:  # never an mm value without its sd
            area = float(o["area_px2"]) * cap.mm_per_px ** 2
            row.update(visible_projected_area_mm2=s.fmt(area, 3), visible_projected_area_mm2__status="observed",
                       visible_projected_area_mm2_sd=s.fmt(2.0 * area * cap.mm_per_px_sd / cap.mm_per_px, 3))
        out.append(row)
    return out


def structure_state_rows(inp: SnapshotInputs, snapshot: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    cap = inp.capture
    ident = {r["organ_id"]: r for r in inp.identity_rows if r["capture_id"] == cap.capture_id}
    out = []
    for v in snapshot:
        tr = ident.get(v["vertex_id"])
        out.append(dict(
            plant_instance_id=inp.plant_instance_id, plant_id=inp.plant_id, capture_id=cap.capture_id,
            vertex_id=v["vertex_id"], part=v["class"],
            upstream_track_state=tr["track_state"] if tr else UNAVAILABLE,
            link_status=tr["correspondence_status"] if tr else UNAVAILABLE,
            time_since_lights_on_min=s.fmt(cap.time_since_lights_on_min) if cap.time_since_lights_on_min is not None
            else UNAVAILABLE,
            photoperiod_phase=cap.photoperiod_phase, frame=v["frame"],
            scale_status="solved" if cap.mm_per_px is not None else UNAVAILABLE,
            evidence_ref=(f"identity_manifest.csv#{cap.capture_id}|{v['vertex_id']}|obs={tr['obs_id']}" if tr
                          else f"observations/{cap.capture_id}")
            + (f";side_geometry.csv#view={inp.side_view_of[v['vertex_id']]};{inp.side_join_ref}"
               if v["vertex_id"] in inp.side_view_of else ""),
        ))
    return out


# --------------------------------------------------------------------------------------
# Unresolved accounting, change log, comparisons
# --------------------------------------------------------------------------------------

_TOP_ONLY_REASONS: dict[str, str] = {
    "base_xyz_mm": "top view alone: depth along the camera ray is unbounded (Stage-2 5 row 9)",
    "tip_xyz_mm": "top view alone: depth along the camera ray is unbounded (Stage-2 5 row 9)",
    "elevation_deg": "top view alone: elevation not identifiable (A1.4 needs dz)",
    "compound_insertion_angle_deg": "A2 12.2: side view or 3-D only; no joined side geometry",
    "leaflet_insertion_angle_deg": "needs the rachis tangent in 3-D; not observable from a top view",
    "rank": "rank needs the stem position (MTG 5); no human record or anchored heights supplied",
    "rachis_bend_type": "human label only (MTG 8.4 on hold); no record for this compound",
    "petiole_base_azimuth_deg": "A2 12.4: insertion point not visible / not reconstructed",
    "area_mm2": "true leaf surface needs per-leaflet 3-D (Stage-2 5 row 4)",
    "length_mm": "top view gives a projected axis only; true length not identifiable",
    "width_mm": "top view gives a projected outline only",
    "normal_xyz": "surface orientation not identifiable from one top view",
    "variety": "not recorded for this plant",
    "slot_id": "plant_id <-> slot table is empty (data/records/plant_registry, 0 of 24 filled)",
    "light_ratio": "needs slot_id",
    "height_top_leaf_mm": "needs a side view with scale",
    "stem_length_mm": "needs side view or 3-D stem",
    "order": "axis membership not stated (no axis hint from a human label or synthetic GT)",
    "parent_rank": "side_shoot_registry has no parent_rank for this axis (top view cannot place the axil)",
    "leaf_unfolded": "unfolding is a human record (A4 rank rule); none supplied for this leaf",
    "segment_index": "A5: derived from the truss registry + leaf ranks; registry absent, rank unavailable, or a "
                     "truss on this axis has no recorded position",
}
#: Every value of a Truss vertex except its registry fields: no detector, no generated geometry (A5).
TRUSS_REASON = "truss: human registry record only (A5); no truss detector and no synthetic truss geometry exist"


def unresolved_rows(snapshot: Sequence[Mapping[str, str]], default_reason: str) -> list[dict[str, str]]:
    out = []
    for v in snapshot:
        for attr in s.MTG_VALUE_ATTRIBUTES:
            if v[attr] != UNAVAILABLE:
                continue
            if attr.startswith("rachis_bend_alpha_") or attr in ("n_bend_nodes", "rachis_curvature_deg",
                                                                  "rachis_bend_theta_deg", "chord_to_path_ratio"):
                reason = "A2 12.3 / A1.5: needs node geometry from a side view or 3-D"
            elif attr in ("azimuth_deg", "blade_azimuth_deg", "blade_azimuth_basis"):
                reason = ("not observed in this capture" if v["observed"] == "false"
                          else "needs a solved pot centre and rotation (A2 12.1)")
            else:
                reason = _TOP_ONLY_REASONS.get(attr, default_reason)
            if v["class"] == s.TRUSS_CLASS and attr not in ("parent_rank", "segment_index", "order"):
                reason = TRUSS_REASON
            out.append(dict(plant_instance_id=v["plant_instance_id"], capture_id=v["capture_id"],
                            vertex_id=v["vertex_id"], attr=attr, reason=reason))
    return out


def change_log(previous: Sequence[Mapping[str, str]], current: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    prev = {v["vertex_id"]: v for v in previous}
    out = []
    for v in current:
        p = prev.get(v["vertex_id"])
        for attr in s.MTG_VALUE_ATTRIBUTES:
            new = (v[attr], v[f"{attr}__status"])
            old = (p[attr], p[f"{attr}__status"]) if p else (UNAVAILABLE, UNAVAILABLE)
            if new == old:
                continue
            rule = ("new_vertex" if p is None else
                    "own_capture_observation" if new[1] != UNAVAILABLE else "not_observed_this_capture_no_carry")
            out.append(dict(plant_instance_id=v["plant_instance_id"],
                            from_capture_id=p["capture_id"] if p else UNAVAILABLE, to_capture_id=v["capture_id"],
                            vertex_id=v["vertex_id"], attr=attr, old_value=old[0], old_status=old[1],
                            new_value=new[0], new_status=new[1], rule_applied=rule))
    return out


def comparisons(plant_instance_id: str, a: CaptureInfo, b: CaptureInfo, areas_a: Sequence[Mapping[str, str]],
                areas_b: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Visible-area change per compound between two captures, behind the diurnal guard."""
    same = (a.photoperiod_phase == b.photoperiod_phase and a.photoperiod_phase != UNAVAILABLE
            and a.time_since_lights_on_min is not None and b.time_since_lights_on_min is not None)
    va = {r["compound_id"]: r["visible_projected_area_px2"] for r in areas_a if r["part"] == "compound"}
    vb = {r["compound_id"]: r["visible_projected_area_px2"] for r in areas_b if r["part"] == "compound"}
    out = []
    for cid in sorted(set(va) & set(vb) - {UNAVAILABLE}):
        ok = same
        out.append(dict(plant_instance_id=plant_instance_id, from_capture_id=a.capture_id, to_capture_id=b.capture_id,
                        vertex_id=cid, quantity="visible_projected_area_px2",
                        comparison_status="compared_same_phase" if ok else "unavailable_diurnal_confound",
                        from_value=va[cid] if ok else UNAVAILABLE, to_value=vb[cid] if ok else UNAVAILABLE,
                        delta=str(int(vb[cid]) - int(va[cid])) if ok else UNAVAILABLE))
    return out


# --------------------------------------------------------------------------------------
# Candidate sub-MTG
# --------------------------------------------------------------------------------------


def candidate_rows(plant_instance_id: str, plant_id: str, capture_id: str, compound_vertex_id: str,
                   candidate_id: str, frame: str, evidence: str, leaflets: Sequence[Mapping[str, object]],
                   axis: str = UNAVAILABLE) -> list[dict[str, str]]:
    """Sub-MTG of one generated candidate, rooted at the tracked compound's vertex id.
    Every value is ``generated_candidate``; nothing here is an observation."""
    status = "generated_candidate"
    root = s.blank_mtg_row()
    root.update(plant_instance_id=plant_instance_id, plant_id=plant_id, capture_id=capture_id,
                snapshot_capture_id=capture_id, vertex_id=compound_vertex_id, scale="3", axis=axis,
                complex_id=UNAVAILABLE if axis == UNAVAILABLE else (f"{plant_id}/A0" if axis == "M" else f"{plant_id}/{axis}"),
                parent_id=UNAVAILABLE, edge_type="+", display_name=UNAVAILABLE, observed="false",
                candidate_id=candidate_id, frame=frame, evidence=evidence, **{"class": "CompoundLeaf"})
    rows = [root]
    for leaf in leaflets:
        row = s.blank_mtg_row()
        row.update(axis=axis)
        row.update(plant_instance_id=plant_instance_id, plant_id=plant_id, capture_id=capture_id,
                   snapshot_capture_id=capture_id, vertex_id=f"{compound_vertex_id}/{leaf['tag']}", scale="4",
                   complex_id=compound_vertex_id, parent_id=UNAVAILABLE, edge_type="<" if leaf["tag"] == "T" else "+",
                   display_name=UNAVAILABLE, observed="false", candidate_id=candidate_id, frame=frame,
                   evidence=evidence, **{"class": "Leaflet"})
        s.set_value(row, "area_mm2", s.fmt(float(leaf["area_mm2"]), 3), status)  # type: ignore[arg-type]
        s.set_value(row, "base_xyz_mm", s.fmt_triple(leaf["base_mm"]), status)  # type: ignore[arg-type]
        rows.append(row)
    return rows

