"""Cross-capture compound-leaf tracking (P1.4) - the phynotype2 section 5/7 contract, in tomato3d.

``phynotype2/`` is absent at its recorded path, so the tracker lives here (P1 prompt section 1).
If ``phynotype2/`` is restored it should import from this module rather than re-implement it.

Contract kept:

* the association unit is the compound leaf; the terminal leaflet has no track of its own and
  is carried by its compound through an **explicit** membership (``parent_obs_id``);
* every capture is matched against **all** live tracks (reappearance is possible);
* cues are reported per pair (``match_candidates.csv``); none is dropped silently - a cue that
  cannot be computed (no pot centre, no solved rotation) is ``unavailable`` and leaves the cost;
* a link is ``proposed`` unless a human decision confirms it; the declared weights were never
  fitted from human decisions, so no automatic confirmation exists;
* six states: continued, unobserved, reappeared, first_observed, removal_confirmed, ambiguous;
  absence in one image is never removal (``removal_confirmed`` only from a decision/record);
* split / merge are flagged as ``fragment_suspect`` / ``merge_suspect`` events and never
  resolved automatically; a contested observation never mints a new id;
* no azimuth prior (MTG 8.5 open);
* axes (MTG A4): a track keeps one axis for life. Linking across two KNOWN, different axes is forbidden
  (cost = infinity, match row ``cost = forbidden_cross_axis``), so a main-stem track is never re-assigned
  to a side shoot; an unknown axis may be set once from an accepted link (``axis_assigned`` event); a new
  side-shoot leaf opens a new id on its own axis.

IDs are ``<plant_id>/C<4-digit serial>`` issued in creation order and never renumbered.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import schema as s

TEMPLATE_CONFIG = Path(__file__).with_name("tracking_config_template.json")
FIXTURE_CONFIG = Path(__file__).with_name("tracking_config_fixture.json")
SHAPE_DESCRIPTOR = "log_area_ratio_v1"
CUES = ("d_azimuth", "d_radial", "shape_compound", "mask_iou_prev")
#: cue -> normalising divisor, so that 1.0 on each cue means "a large change". Declared, not fitted.
AZIMUTH_SCALE_DEG = 90.0


class TrackingError(ValueError):
    """Inputs violate the tracking contract (unknown decision, wrong capture order...)."""


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _value(cfg: Mapping[str, Any], *keys: str) -> Any:
    node: Any = cfg
    for key in keys:
        node = node[key]
    return node["value"]


# --------------------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CaptureFrame:
    """Per-capture image -> plant registration (phynotype2 3.1). ``None`` = unavailable."""

    capture_id: str
    capture_time_h: float | None
    photoperiod_phase: str
    center_px: tuple[float, float] | None
    rotation_deg: float | None

    @property
    def rotation_solved(self) -> bool:
        return self.rotation_deg is not None and self.center_px is not None


@dataclass
class CompoundObs:
    obs_id: str
    mask: np.ndarray
    terminal_obs_id: str | None = None
    #: MTG A4 axis code (M, S1, ...) from a human label / synthetic GT, else ``unavailable``
    axis_hint: str = UNAVAILABLE


@dataclass(frozen=True)
class Decision:
    """A human decision (W5 kinds subset). ``decision_ref`` names the file/record it came from."""

    kind: str
    capture_id: str
    track_id: str
    obs_id: str | None
    decision_ref: str


DECISION_KINDS = ("same", "different", "occluded", "removal_confirmed")


def load_decisions(path: Path | None) -> list[Decision]:
    if path is None or not Path(path).exists():
        return []
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for item in raw["decisions"]:
        if item["kind"] not in DECISION_KINDS:
            raise TrackingError(f"unknown decision kind {item['kind']!r}")
        if not item.get("decision_ref"):
            raise TrackingError("a decision needs decision_ref (who/which record)")
        out.append(Decision(item["kind"], item["capture_id"], item["track_id"], item.get("obs_id"),
                            item["decision_ref"]))
    return out


# --------------------------------------------------------------------------------------
# Features and cues
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ObsFeatures:
    area_px: int
    distal_azimuth_deg: float | None
    distal_radius_px: float | None


def features(mask: np.ndarray, frame: CaptureFrame) -> ObsFeatures:
    ys, xs = np.nonzero(mask)
    area = int(len(xs))
    if frame.center_px is None or area == 0:
        return ObsFeatures(area, None, None)
    cx, cy = frame.center_px
    dx, dy = xs - cx, cy - ys  # image rows grow downward; plant +Y up
    r = np.hypot(dx, dy)
    k = int(np.argmax(r))
    if frame.rotation_deg is None:
        return ObsFeatures(area, None, float(r[k]))
    az_img = math.degrees(math.atan2(float(dy[k]), float(dx[k])))
    return ObsFeatures(area, (az_img - frame.rotation_deg) % 360.0, float(r[k]))


def _derotate(mask: np.ndarray, frame: CaptureFrame) -> np.ndarray | None:
    """Mask resampled into the plant-aligned image (rotation removed about the pot centre)."""
    if not frame.rotation_solved:
        return None
    cx, cy = frame.center_px  # type: ignore[misc]
    # image rotates with the pot by +rotation (counter-clockwise seen from above = clockwise in
    # image rows-down coordinates); undo it
    m = cv2.getRotationMatrix2D((cx, cy), -float(frame.rotation_deg), 1.0)  # type: ignore[arg-type]
    out = cv2.warpAffine(mask.astype(np.uint8), m, (mask.shape[1], mask.shape[0]), flags=cv2.INTER_NEAREST)
    return out.astype(bool)


def _containment(part: np.ndarray | None, whole: np.ndarray | None) -> float | None:
    """Fraction of ``part`` lying inside ``whole`` (both plant-aligned); ``None`` if unavailable."""
    if part is None or whole is None:
        return None
    n = int(part.sum())
    return None if n == 0 else int((part & whole).sum()) / n


def _wrap(a: float) -> float:
    w = (a + 180.0) % 360.0 - 180.0
    return 180.0 if w == -180.0 else w


@dataclass
class _Track:
    track_id: str
    last_capture_index: int
    last_features: ObsFeatures
    last_aligned_mask: np.ndarray | None
    observed_history: list[int] = field(default_factory=list)
    removed: bool = False
    #: last capture with an observation linked to this track at all (accepted OR ambiguous); an
    #: ambiguous capture is not an absence, so it does not make the next link a reappearance
    last_present_index: int = -1
    #: MTG A4: a compound belongs to one axis for life; ``unavailable`` until an observation states it
    axis: str = UNAVAILABLE


def pair_cues(track: _Track, feat: ObsFeatures, aligned: np.ndarray | None) -> dict[str, float | None]:
    prev = track.last_features
    d_az = None
    if prev.distal_azimuth_deg is not None and feat.distal_azimuth_deg is not None:
        d_az = abs(_wrap(feat.distal_azimuth_deg - prev.distal_azimuth_deg))
    d_rad = None
    if prev.distal_radius_px and feat.distal_radius_px:
        d_rad = abs(math.log(feat.distal_radius_px / prev.distal_radius_px))
    shape = abs(math.log(max(feat.area_px, 1) / max(prev.area_px, 1)))
    iou = None
    if aligned is not None and track.last_aligned_mask is not None:
        inter = int((aligned & track.last_aligned_mask).sum())
        union = int((aligned | track.last_aligned_mask).sum())
        iou = inter / union if union else None
    return {"d_azimuth": d_az, "d_radial": d_rad, "shape_compound": shape, "mask_iou_prev": iou}


def pair_cost(cues: Mapping[str, float | None], weights: Mapping[str, float] | None) -> float:
    """Weighted MEAN over the cues that exist (a missing cue neither adds nor removes cost).
    Null weights -> equal weights, used for ranking only (every link stays proposed)."""
    terms = {
        "d_azimuth": None if cues["d_azimuth"] is None else cues["d_azimuth"] / AZIMUTH_SCALE_DEG,
        "d_radial": cues["d_radial"],
        "shape_compound": cues["shape_compound"],
        "mask_iou_prev": None if cues["mask_iou_prev"] is None else 1.0 - cues["mask_iou_prev"],
    }
    w = weights or {k: 1.0 for k in CUES}
    used = [(w[k], v) for k, v in terms.items() if v is not None and w.get(k)]
    if not used:
        return math.inf
    return sum(wk * v for wk, v in used) / sum(wk for wk, _ in used)


# --------------------------------------------------------------------------------------
# Tracker
# --------------------------------------------------------------------------------------


@dataclass
class TrackResult:
    identity_rows: list[dict[str, str]]
    events: list[dict[str, str]]
    match_rows: list[dict[str, str]]
    obs_to_track: dict[tuple[str, str], str]
    config_status: dict[str, str]


def _fmt(v: float | None, digits: int = 4) -> str:
    return s.fmt(v, digits) if v is not None and math.isfinite(v) else UNAVAILABLE


def track_plant(
    plant_id: str,
    plant_instance_id: str,
    frames: Sequence[CaptureFrame],
    observations: Mapping[str, Sequence[CompoundObs]],
    config: Mapping[str, Any],
    decisions: Sequence[Decision] = (),
    evidence: str = "synthetic_fixture",
) -> TrackResult:
    """Track the compound observations of one plant through its captures, in time order."""
    from scipy.optimize import linear_sum_assignment

    weights = _value(config, "association", "weights")
    no_match = _value(config, "association", "no_match_cost")
    margin_thr = _value(config, "association", "ambiguity_margin")
    contain_min = _value(config, "association", "split_merge_containment_min")
    config_status = {
        "weights": "declared" if weights else "null_equal_weight_ranking_only",
        "no_match_cost": "declared" if no_match is not None else "null_every_fate_to_review",
        "ambiguity_margin": "declared" if margin_thr is not None else "null_every_link_to_review",
        "split_merge_containment_min": "declared" if contain_min is not None else "null_cost_rule_only",
        "auto_confirm": "none (no rule fitted from human decisions)",
    }
    times = [f.capture_time_h for f in frames]
    if any(t is not None for t in times):
        known = [t for t in times if t is not None]
        if known != sorted(known):
            raise TrackingError("captures are not in time order")
    dec_by = {(d.capture_id, d.track_id): d for d in decisions}
    tracks: dict[str, _Track] = {}
    next_serial = 1
    identity: list[dict[str, str]] = []
    events: list[dict[str, str]] = []
    matches: list[dict[str, str]] = []
    obs_to_track: dict[tuple[str, str], str] = {}
    n_events = 0

    def new_event(capture_id: str, kind: str, track_ids: list[str], obs_ids: list[str], ref: str) -> str:
        nonlocal n_events
        n_events += 1
        eid = f"{plant_instance_id}/E{n_events:04d}"
        events.append(dict(event_id=eid, plant_instance_id=plant_instance_id, capture_id=capture_id,
                           event_type=kind, track_ids=";".join(track_ids), obs_ids=";".join(obs_ids),
                           decision_ref=ref))
        return eid

    def id_row(capture: CaptureFrame, organ_id: str, organ_class: str, parent: str, obs_id: str, state: str,
               reason: str, link: str, cost: float | None, margin: float | None, gap: int | None,
               emergence: tuple[str, str], ev: list[str], axis: str | None = None) -> dict[str, str]:
        if axis is None:
            owner = organ_id[:-2] if organ_id.endswith("/T") else organ_id
            axis = tracks[owner].axis if owner in tracks else UNAVAILABLE
        return dict(plant_instance_id=plant_instance_id, source_plant_id=plant_id, capture_id=capture.capture_id,
                    organ_id=organ_id, organ_class=organ_class, axis=axis,
                    # MTG A5: derived from the truss registry + ranks after the structure update
                    # (tomato3d.state.trusses.fill_identity_segments); the tracker never sets it
                    segment_index=UNAVAILABLE, parent_id=parent, obs_id=obs_id,
                    track_state=state, unobserved_reason=reason, correspondence_status=link,
                    match_cost=_fmt(cost), match_margin=_fmt(margin),
                    gap_captures=UNAVAILABLE if gap is None else str(gap),
                    emergence_interval_start=emergence[0], emergence_interval_end=emergence[1],
                    events=";".join(ev) if ev else UNAVAILABLE, evidence=evidence)

    for ci, frame in enumerate(frames):
        obs = list(observations.get(frame.capture_id, []))
        feats = [features(o.mask, frame) for o in obs]
        aligned = [_derotate(o.mask, frame) for o in obs]
        live = [t for t in tracks.values() if not t.removed]
        cost = np.full((len(live), len(obs)), math.inf)
        for ti, t in enumerate(live):
            for oi, o in enumerate(obs):
                cues = pair_cues(t, feats[oi], aligned[oi])
                cross_axis = UNAVAILABLE not in (t.axis, o.axis_hint) and t.axis != o.axis_hint
                c = math.inf if cross_axis else pair_cost(cues, weights)
                cost[ti, oi] = c
                matches.append(dict(
                    plant_instance_id=plant_instance_id, capture_id=frame.capture_id, track_id=t.track_id,
                    obs_id=o.obs_id, d_azimuth_deg=_fmt(cues["d_azimuth"]),
                    d_radial_px=_fmt(cues["d_radial"]), shape_compound=_fmt(cues["shape_compound"]),
                    mask_iou_prev=_fmt(cues["mask_iou_prev"]),
                    dt_h=_fmt(None if frame.capture_time_h is None or frames[t.last_capture_index].capture_time_h is None
                              else frame.capture_time_h - frames[t.last_capture_index].capture_time_h),
                    same_phase=UNAVAILABLE if UNAVAILABLE in (frame.photoperiod_phase,
                                                              frames[t.last_capture_index].photoperiod_phase)
                    else str(frame.photoperiod_phase == frames[t.last_capture_index].photoperiod_phase).lower(),
                    gap_captures=str(ci - t.last_capture_index - 1),
                    cost="forbidden_cross_axis" if cross_axis else _fmt(c)))
        # augmented assignment: a "no match" column per track and row per observation
        big = 1e6
        nm = no_match if no_match is not None else big / 10
        n_t, n_o = len(live), len(obs)
        aug = np.full((n_t + n_o, n_o + n_t), big)
        finite = np.where(np.isfinite(cost), cost, big)
        aug[:n_t, :n_o] = finite
        aug[:n_t, n_o:] = np.where(np.eye(n_t, dtype=bool), nm, big)
        aug[n_t:, :n_o] = np.where(np.eye(n_o, dtype=bool), nm, big)
        aug[n_t:, n_o:] = 0.0
        rows_i, cols_i = linear_sum_assignment(aug) if aug.size else (np.array([], int), np.array([], int))
        assigned: dict[int, int] = {}  # track index -> obs index
        for r, c in zip(rows_i, cols_i):
            if r < n_t and c < n_o and aug[r, c] < big:
                assigned[r] = c
        obs_owner = {o: t for t, o in assigned.items()}

        def second_best_margin(ti: int, oi: int) -> float | None:
            c0 = cost[ti, oi]
            alts = [cost[tj, oi] for tj in range(n_t) if tj != ti] + [cost[ti, oj] for oj in range(n_o) if oj != oi]
            alts = [a for a in alts if math.isfinite(a)]
            return (min(alts) - c0) if alts else None

        contested_obs: set[int] = set()
        handled_tracks: set[int] = set()
        # merge suspects: an unmatched track whose best affordable observation went to another track
        if no_match is not None:
            for ti in range(n_t):
                if ti in assigned or not np.isfinite(cost[ti]).any():
                    continue
                oi = int(np.argmin(cost[ti]))
                inside = _containment(live[ti].last_aligned_mask, aligned[oi])
                by_overlap = contain_min is not None and inside is not None and inside >= contain_min
                if oi in obs_owner and (cost[ti, oi] < no_match or by_overlap):
                    other = live[obs_owner[oi]].track_id
                    eid = new_event(frame.capture_id, "merge_suspect", [live[ti].track_id, other],
                                    [obs[oi].obs_id], "tracker_proposal")
                    identity.append(id_row(frame, live[ti].track_id, "compound_leaf", plant_id, obs[oi].obs_id,
                                           "ambiguous", UNAVAILABLE, "proposed", float(cost[ti, oi]), None,
                                           None, (UNAVAILABLE, UNAVAILABLE), [eid]))
                    handled_tracks.add(ti)
                    contested_obs.add(oi)
            # fragment suspects: an unmatched observation whose best affordable track is taken
            for oi in range(n_o):
                if oi in obs_owner or n_t == 0 or not np.isfinite(cost[:, oi]).any():
                    continue
                ti = int(np.argmin(cost[:, oi]))
                inside = _containment(aligned[oi], live[ti].last_aligned_mask)
                by_overlap = contain_min is not None and inside is not None and inside >= contain_min
                if ti in assigned and (cost[ti, oi] < no_match or by_overlap):
                    eid = new_event(frame.capture_id, "fragment_suspect", [live[ti].track_id],
                                    [obs[assigned[ti]].obs_id, obs[oi].obs_id], "tracker_proposal")
                    contested_obs.add(oi)
                    contested_obs.add(assigned[ti])
                    handled_tracks.add(ti)
                    identity.append(id_row(frame, live[ti].track_id, "compound_leaf", plant_id,
                                           f"{obs[assigned[ti]].obs_id};{obs[oi].obs_id}", "ambiguous",
                                           UNAVAILABLE, "proposed", float(cost[ti, oi]), None, None,
                                           (UNAVAILABLE, UNAVAILABLE), [eid]))
        # assigned pairs
        for ti, oi in sorted(assigned.items()):
            if ti in handled_tracks:
                continue
            t = live[ti]
            o = obs[oi]
            margin = second_best_margin(ti, oi)
            gap = ci - max(t.last_capture_index, t.last_present_index) - 1
            decision = dec_by.get((frame.capture_id, t.track_id))
            link = "proposed"
            ev: list[str] = []
            if decision is not None and decision.kind == "same" and decision.obs_id == o.obs_id:
                link = "confirmed"
            elif decision is not None and decision.kind == "different" and decision.obs_id == o.obs_id:
                link = "rejected"
            ambiguous = (margin_thr is None or no_match is None or (margin is not None and margin < margin_thr)
                         or oi in contested_obs)
            if link == "rejected":
                state = "ambiguous"
            elif ambiguous and link != "confirmed":
                state = "ambiguous"
            else:
                state = "continued" if gap == 0 else "reappeared"
            if state != "ambiguous" and link != "rejected" and t.axis == UNAVAILABLE and o.axis_hint != UNAVAILABLE:
                t.axis = o.axis_hint
                ev.append(new_event(frame.capture_id, "axis_assigned", [t.track_id], [o.obs_id],
                                    f"observation_axis_hint:{o.axis_hint}"))
            identity.append(id_row(frame, t.track_id, "compound_leaf", plant_id, o.obs_id, state, UNAVAILABLE,
                                   link, float(cost[ti, oi]), margin, gap if state == "reappeared" else 0,
                                   (UNAVAILABLE, UNAVAILABLE), ev))
            t.last_present_index = ci
            if link != "rejected" and state != "ambiguous":
                obs_to_track[(frame.capture_id, o.obs_id)] = t.track_id
                if o.terminal_obs_id:
                    obs_to_track[(frame.capture_id, o.terminal_obs_id)] = f"{t.track_id}/T"
                    identity.append(id_row(frame, f"{t.track_id}/T", "terminal_leaflet", t.track_id,
                                           o.terminal_obs_id, state, UNAVAILABLE, link, None, None, None,
                                           (UNAVAILABLE, UNAVAILABLE), []))
                # an ambiguous link never updates the track: it keeps its last accepted observation
                if state != "ambiguous":
                    t.last_capture_index = ci
                    t.last_features = feats[oi]
                    t.last_aligned_mask = aligned[oi]
                    t.observed_history.append(ci)
        # unmatched tracks
        for ti, t in enumerate(live):
            if ti in assigned or ti in handled_tracks:
                continue
            decision = dec_by.get((frame.capture_id, t.track_id))
            if decision is not None and decision.kind == "removal_confirmed":
                eid = new_event(frame.capture_id, "removal_confirmed", [t.track_id], [], decision.decision_ref)
                identity.append(id_row(frame, t.track_id, "compound_leaf", plant_id, UNAVAILABLE,
                                       "removal_confirmed", UNAVAILABLE, "confirmed", None, None, None,
                                       (UNAVAILABLE, UNAVAILABLE), [eid]))
                t.removed = True
                continue
            reason = "occluded" if decision is not None and decision.kind == "occluded" else "unknown"
            identity.append(id_row(frame, t.track_id, "compound_leaf", plant_id, UNAVAILABLE, "unobserved",
                                   reason, "proposed", None, None, ci - t.last_capture_index,
                                   (UNAVAILABLE, UNAVAILABLE), []))
        # unmatched observations -> new tracks (unless contested or the no-match threshold is null)
        for oi, o in enumerate(obs):
            if oi in obs_owner or oi in contested_obs:
                continue
            if no_match is None and live:
                identity.append(id_row(frame, UNAVAILABLE_TRACK, "compound_leaf", plant_id, o.obs_id, "ambiguous",
                                       UNAVAILABLE, "proposed", None, None, None, (UNAVAILABLE, UNAVAILABLE),
                                       [], o.axis_hint))
                continue
            tid = s.compound_id(plant_id, next_serial)
            next_serial += 1
            emergence = (UNAVAILABLE if ci == 0 else frames[ci - 1].capture_id, frame.capture_id)
            tracks[tid] = _Track(tid, ci, feats[oi], aligned[oi], [ci], last_present_index=ci, axis=o.axis_hint)
            identity.append(id_row(frame, tid, "compound_leaf", plant_id, o.obs_id, "first_observed",
                                   UNAVAILABLE, "proposed", None, None, None, emergence, []))
            obs_to_track[(frame.capture_id, o.obs_id)] = tid
            if o.terminal_obs_id:
                obs_to_track[(frame.capture_id, o.terminal_obs_id)] = f"{tid}/T"
                identity.append(id_row(frame, f"{tid}/T", "terminal_leaflet", tid, o.terminal_obs_id,
                                       "first_observed", UNAVAILABLE, "proposed", None, None, None, emergence, []))
    return TrackResult(identity, events, matches, obs_to_track, config_status)


UNAVAILABLE_TRACK = s.UNASSIGNED_ORGAN


def link_organs(plant_id: str) -> None:
    """Stage-1 stub entry point, kept for the fixed import graph. Use :func:`track_plant`."""
    raise NotImplementedError(
        "tomato3d.track.link.link_organs(plant_id) has no input contract; call track_plant(...) "
        "with captures, observations and a tracking config (P1.4)"
    )
