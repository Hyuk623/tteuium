"""Declared synthetic capture sequences for tracking tests and the engineering run (fixture only).

A sequence is a list of steps applied to one :class:`~tomato3d.state.fixture_truth.FixturePlant`.
Every step is a controlled change that is written into the run manifest:

* ``yaw_deg``            the pot is turned (the image rotates with it);
* ``rotation_known``     whether the capture's rotation is registered (``rotation_status``);
* ``remove``             compound serials removed before this capture (a real removal);
* ``add``                ``(donor_plant, donor_serial, yaw_deg)`` new compounds before this capture;
* ``occlude``            compound serials whose pixels an external occluder hides in this capture;
* ``merge`` / ``split``  simulated segmentation failures in this capture;
* ``time_h`` / ``phase`` declared fixture clock (``phase`` in am|pm).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import fixture_truth as ft
from tomato3d.state.topraster import OrthoCamera, TopRender
from tomato3d.track.link import CaptureFrame, CompoundObs


@dataclass
class Step:
    capture_id: str
    time_h: float
    phase: str
    yaw_deg: float = 0.0
    rotation_known: bool = True
    remove: list[int] = field(default_factory=list)
    add: list[tuple[ft.FixturePlant, int, float]] = field(default_factory=list)
    occlude: list[int] = field(default_factory=list)
    merge: list[list[int]] = field(default_factory=list)
    split: list[int] = field(default_factory=list)
    #: MTG A4 side shoots present at this capture: dicts with axis, parent_serial, leaf_lengths_mm, seed,
    #: stem_length_mm, stem_elevation_deg (fixture-declared; a regrown axis keeps its compound serials)
    side_shoots: list[dict[str, Any]] = field(default_factory=list)

    def describe(self) -> dict[str, Any]:
        return dict(capture_id=self.capture_id, time_h=self.time_h, phase=self.phase, yaw_deg=self.yaw_deg,
                    rotation_known=self.rotation_known, remove=self.remove,
                    add=[dict(donor=d.source_plant_id, donor_serial=k, yaw_deg=y) for d, k, y in self.add],
                    occlude=self.occlude, merge=self.merge, split=self.split, side_shoots=self.side_shoots)


@dataclass
class CaptureState:
    step: Step
    plant: ft.FixturePlant
    render: TopRender
    obs: ft.ObservationSet
    frame: CaptureFrame


def run_sequence(plant: ft.FixturePlant, steps: list[Step], camera: OrthoCamera, min_visible_px: int,
                 plant_instance_id: str, gen_cfg: dict[str, Any] | None = None,
                 contours: list[np.ndarray] | None = None) -> list[CaptureState]:
    states: list[CaptureState] = []
    current = plant
    for step in steps:
        for serial in step.remove:
            current = ft.remove_compound(current, serial)
        for donor, serial, yaw in step.add:
            current = ft.add_compound_from(current, donor, serial, yaw)
        for side in step.side_shoots:
            if gen_cfg is None or contours is None:
                raise ValueError("side shoots need the generator config and contour pool")
            current = ft.set_side_shoot(current, side["axis"], int(side["parent_serial"]),
                                        [float(x) for x in side["leaf_lengths_mm"]], gen_cfg, contours,
                                        int(side["seed"]), float(side["stem_length_mm"]),
                                        float(side["stem_elevation_deg"]))
        render = ft.render_capture(current, step.yaw_deg, camera)
        if step.occlude:
            hide = {f"{ft.s.compound_id(current.source_plant_id, k)}/" for k in step.occlude}
            for idx, lid in enumerate(render.ids, start=1):
                if any(lid.startswith(h) for h in hide):
                    render.visible[render.visible == idx] = 0
        cid = lambda k: ft.s.compound_id(current.source_plant_id, k)  # noqa: E731
        obs = ft.observe_top(render, plant_instance_id, step.capture_id, min_visible_px,
                             source_id=f"synthetic_gt:ortho_top:{step.capture_id}",
                             merge_groups=[[cid(k) for k in grp] for grp in step.merge],
                             split_compounds=[cid(k) for k in step.split],
                             axis_of=ft.axis_of_compounds(current))
        frame = CaptureFrame(capture_id=step.capture_id, capture_time_h=step.time_h, photoperiod_phase=step.phase,
                             center_px=(camera.center_px, camera.center_px),
                             rotation_deg=step.yaw_deg if step.rotation_known else None)
        states.append(CaptureState(step, current, render, obs, frame))
    return states


def compound_observations(state: CaptureState) -> list[CompoundObs]:
    """Tracker input: compound observations with their explicit terminal membership."""
    rows = state.obs.rows
    terminal_of = {r["parent_obs_id"]: r["obs_id"] for r in rows
                   if r["obs_class"] == "terminal_leaflet" and r["membership_status"] == "confirmed"}
    return [CompoundObs(r["obs_id"], state.obs.masks[r["obs_id"]], terminal_of.get(r["obs_id"]),
                        r.get("axis_hint", UNAVAILABLE))
            for r in rows if r["obs_class"] == "compound_leaf"]


def truth_compound_of_obs(state: CaptureState) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in state.obs.truth_join:
        out.setdefault(row["obs_id"], []).append(row["truth_vertex_id"])
    return out


def identity_score(states: list[CaptureState], obs_to_track: dict[tuple[str, str], str]) -> dict[str, Any]:
    """Fixture evaluation against the truth join: switches, fragmentations, forced wrong links.

    A track is attributed to the truth compound it was first opened on. ``wrong_links`` counts
    observations the tracker linked to a track attributed to a DIFFERENT truth compound.
    """
    track_truth: dict[str, str] = {}
    truth_tracks: dict[str, set[str]] = {}
    wrong = 0
    linked = 0
    for st in states:
        tmap = truth_compound_of_obs(st)
        for row in st.obs.rows:
            if row["obs_class"] != "compound_leaf":
                continue
            tid = obs_to_track.get((st.step.capture_id, row["obs_id"]))
            truths = tmap.get(row["obs_id"], [])
            if tid is None or len(truths) != 1:
                continue
            truth = truths[0].split("~")[0]
            linked += 1
            if tid not in track_truth:
                track_truth[tid] = truth
            elif track_truth[tid] != truth:
                wrong += 1
            truth_tracks.setdefault(truth, set()).add(tid)
    fragmented = sum(1 for t in truth_tracks.values() if len(t) > 1)
    return dict(linked_observations=linked, wrong_links=wrong, fragmented_truth_compounds=fragmented,
                truth_compounds=len(truth_tracks), track_to_truth=track_truth)


def visible_fraction(state: CaptureState, serial: int) -> float:
    lids = [lid for lid in state.render.ids if lid.startswith(ft.s.compound_id(state.plant.source_plant_id, serial) + "/")]
    vis = sum(int(state.render.visible_mask(l).sum()) for l in lids)
    amo = sum(int(state.render.amodal[l].sum()) for l in lids)
    return vis / amo if amo else float("nan")


def stack_masks(masks: list[np.ndarray]) -> np.ndarray:
    return np.any(np.stack(masks), axis=0)
