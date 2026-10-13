"""P1 state package: build (fixture engineering run / real-data audit), validate, P2 dry-read, replay.

Layout of ``build/p1_state_<YYYYMMDD>_<nn>/`` (CSV tables, JSON metadata)::

    p1_request.json                 inputs (paths + sha256), code/schema hashes - what replay re-runs
    p1_manifest.json                schema version, run_status per segment, P2 field map, file hashes
    captures.csv  frame_transforms.csv
    observations/observations.csv   all observation rows (provenance per row)
    observations/<inst>__<cap>/masks.json   packed masks (lossless intervals)
    observations/truth_join.csv     FIXTURE ONLY - obs -> truth vertex; never read by the tracker
    identity_manifest.csv  events.csv  match_candidates.csv
    axes.csv  trusses.csv           MTG A4 axes (+ A5 segment columns) and A5 registry trusses
    mtg_vertices.csv  mtg_edges.csv  structure_state.csv  change_log.csv  unresolved.csv
    comparisons.csv                 diurnal-guarded visible-area changes
    areas.csv                       four area kinds, full_outline basis
    candidates.csv  completion_report.csv   generated sub-MTGs (never in the main snapshot)
    side_geometry.csv (+ side_validation_*.csv for fixtures)
    optical_surfaces/*.csv  optical_surface_manifest.csv
    canopy_placement.json  canopy_merge_check.json
    truth/                          FIXTURE ONLY - truth MTG / areas / serial table
    compare_observation.csv         observation-derived vs truth (fixture) - written by collect
    audit_gaps.csv                  REAL AUDIT - every missing input by name
    viewer/index.html               display only

Publishing is coherent: everything is written to a staging folder next to the target and moved
into place in one rename; a failure leaves no partial folder with a manifest.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.io.tables import read_table, write_table
from tomato3d.state import axes as ax
from tomato3d.state import camera as cam
from tomato3d.state import canopy as cn
from tomato3d.state import fixture_truth as ft
from tomato3d.state import ingest
from tomato3d.state import optical as op
from tomato3d.state import potscale as ps
from tomato3d.state import schema as s
from tomato3d.state import sidegeom as sg
from tomato3d.state import trusses as tr
from tomato3d.state import update as up
from tomato3d.state.fixture_sequence import Step, compound_observations, identity_score, run_sequence
from tomato3d.state.topraster import OrthoCamera
from tomato3d.track import link

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CODE_FILES = (
    "tomato3d/state/schema.py", "tomato3d/state/geometry.py", "tomato3d/state/topraster.py",
    "tomato3d/state/fixture_truth.py", "tomato3d/state/fixture_sequence.py", "tomato3d/state/ingest.py",
    "tomato3d/state/update.py", "tomato3d/state/sidegeom.py", "tomato3d/state/optical.py",
    "tomato3d/state/canopy.py", "tomato3d/state/package.py", "tomato3d/track/link.py", "tomato3d/state/axes.py",
    "tomato3d/state/trusses.py", "tomato3d/state/potscale.py", "tomato3d/state/camera.py",
    "tomato3d/synth/compound_leaf.py",
    "tomato3d/state/p1_config.json", "tomato3d/track/tracking_config_template.json",
    "tomato3d/track/tracking_config_fixture.json",
)
FIXTURE_TIME_ZERO = datetime(2026, 10, 11, 8, 0, tzinfo=timezone(timedelta(hours=9)))


class PackageError(RuntimeError):
    """A package cannot be published as a success; the message names the failed rule."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes(root: Path = PROJECT_ROOT) -> dict[str, str]:
    return {rel: sha256_file(root / rel) for rel in CODE_FILES}


def code_version(root: Path = PROJECT_ROOT) -> str:
    digest = hashlib.sha256(json.dumps(code_hashes(root), sort_keys=True).encode()).hexdigest()
    return f"p1code-{digest[:16]}"


def _git_describe(root: Path) -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "not_a_git_repository"
    except (OSError, subprocess.SubprocessError):
        return "not_a_git_repository"


def _safe(name: str) -> str:
    return name.replace("/", "_").replace("#", "~").replace("|", "__")


def _rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


# --------------------------------------------------------------------------------------
# Writer
# --------------------------------------------------------------------------------------


class Writer:
    """Collects tables/documents in a staging folder; :meth:`publish` moves it into place at once."""

    def __init__(self, target: Path):
        self.target = Path(target)
        if self.target.exists() and (self.target / "p1_manifest.json").exists():
            raise PackageError(f"{self.target} already holds a published package; use a new run folder")
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.stage = Path(tempfile.mkdtemp(prefix=f".{self.target.name}.staging-", dir=self.target.parent))

    def table(self, rel: str, rows: Sequence[Mapping[str, str]], columns: Sequence[str]) -> None:
        s.check_table_header(columns, rel)
        write_table(self.stage / rel, [dict(r) for r in rows], columns)

    def json(self, rel: str, doc: Any) -> None:
        path = self.stage / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=1, sort_keys=False, default=str) + "\n", encoding="utf-8")

    def text(self, rel: str, text: str) -> None:
        path = self.stage / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def path(self, rel: str) -> Path:
        p = self.stage / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def file_hashes(self) -> dict[str, str]:
        return {p.relative_to(self.stage).as_posix(): sha256_file(p) for p in sorted(self.stage.rglob("*"))
                if p.is_file() and p.name != "p1_manifest.json"}

    def publish(self) -> Path:
        if self.target.exists():
            if any(self.target.iterdir()) and not (self.target / "p1_request.json").exists():
                raise PackageError(f"{self.target} exists and is not a prepared P1 folder")
            request = self.target / "p1_request.json"
            if request.exists() and not (self.stage / "p1_request.json").exists():
                shutil.copyfile(request, self.stage / "p1_request.json")
            shutil.rmtree(self.target)
        self.stage.rename(self.target)
        return self.target

    def abort(self) -> None:
        shutil.rmtree(self.stage, ignore_errors=True)


# --------------------------------------------------------------------------------------
# Fixture engineering run (P1.10)
# --------------------------------------------------------------------------------------

O_MATURE = Path("build/synthetic_dwarf_tomato_20261008_07/O-mature/scenes")
SIDEPROP = Path("build/sideprop_20261009_01/scenes")


def default_fixture_request() -> dict[str, Any]:
    """Declared multi-plant fixture: 3 source plants, a duplicate instance, an other-variety plant,
    3 time points (am, pm, am) with rotation, removal, a new compound and an occlusion."""
    return dict(
        mode="fixture",
        source_plants=[
            dict(source_plant_id="fx_om0", scene_dir=(O_MATURE / "scene_0000").as_posix()),
            dict(source_plant_id="fx_om1", scene_dir=(O_MATURE / "scene_0001").as_posix()),
            dict(source_plant_id="fx_sp0", scene_dir=(SIDEPROP / "scene_0000").as_posix(), side_views=True),
        ],
        donor_scene=(O_MATURE / "scene_0002").as_posix(),
        completion_pool_scenes=[(O_MATURE / f"scene_{k:04d}").as_posix() for k in range(3, 15)],
        sequences={
            "fx_om0": [dict(capture_id="c0", time_h=0, phase="am", yaw_deg=0),
                       dict(capture_id="c1", time_h=12, phase="pm", yaw_deg=35),
                       dict(capture_id="c2", time_h=24, phase="am", yaw_deg=-20, remove=[1],
                            add=[[2, 150.0]], occlude=[3])],
            "fx_om1": [dict(capture_id="c0", time_h=0, phase="am", yaw_deg=10),
                       dict(capture_id="c1", time_h=12, phase="pm", yaw_deg=60, rotation_known=False),
                       dict(capture_id="c2", time_h=24, phase="am", yaw_deg=0, merge=[[2, 4]])],
            "fx_sp0": [dict(capture_id="c0", time_h=0, phase="am", yaw_deg=0),
                       dict(capture_id="c1", time_h=12, phase="pm", yaw_deg=-45),
                       dict(capture_id="c2", time_h=24, phase="am", yaw_deg=15)],
        },
        instances=[
            dict(plant_instance_id="fx_om0", slot_id="T2-row1-L", yaw_deg=0.0, variety="micro_tom"),
            dict(plant_instance_id="fx_om0#2", slot_id="T2-row1-R", yaw_deg=90.0, variety="micro_tom"),
            dict(plant_instance_id="fx_om1", slot_id="T1-row2-L", yaw_deg=30.0, variety="micro_tom"),
            dict(plant_instance_id="fx_sp0", slot_id="T3-row2-R", yaw_deg=0.0, variety="micro_tom"),
            dict(plant_instance_id="fx_other", slot_id="T2-row4-L", yaw_deg=0.0, variety="other"),
        ],
        decisions=None,
    )


def default_sideshoot_request() -> dict[str, Any]:
    """MTG A4 fixture: one O-mature plant with a substem S1 (3 leaves, present before the first capture) and a
    side shoot S2 that appears with two leaves at c1 (axis_shoot) and is a substem at c2 (both leaves expanded).
    Daily captures (one per date) so registry dates map to captures one-to-one. Leaf sizes, stem lengths and
    elevations are fixture declarations; side leaves are generated by build_compound (numpy backend)."""
    s1 = dict(axis="S1", parent_serial=2, leaf_lengths_mm=[30.0, 26.0, 18.0], seed=11, stem_length_mm=14.0,
              stem_elevation_deg=50.0)
    s2_young = dict(axis="S2", parent_serial=5, leaf_lengths_mm=[14.0, 13.0], seed=12, stem_length_mm=4.0,
                    stem_elevation_deg=50.0)
    s2_grown = dict(s2_young, leaf_lengths_mm=[24.0, 21.0], stem_length_mm=7.0)
    return dict(
        mode="fixture",
        source_plants=[dict(source_plant_id="fx_ss0", scene_dir=(O_MATURE / "scene_0004").as_posix())],
        donor_scene=(O_MATURE / "scene_0002").as_posix(),
        completion_pool_scenes=[(O_MATURE / f"scene_{k:04d}").as_posix() for k in range(5, 9)],
        sequences={"fx_ss0": [
            dict(capture_id="c0", time_h=0, phase="am", yaw_deg=0, side_shoots=[s1]),
            dict(capture_id="c1", time_h=24, phase="am", yaw_deg=30, side_shoots=[s1, s2_young]),
            dict(capture_id="c2", time_h=48, phase="am", yaw_deg=-15, side_shoots=[s1, s2_grown])]},
        side_shoot_registry={"fx_ss0": [
            dict(axis="S1", parent_serial=2, first_observed="2026-10-09",
                 states=[["substem", "2026-10-10"]], note="fixture: substem before the first capture"),
            dict(axis="S2", parent_serial=5, first_observed="2026-10-12",
                 states=[["axis_shoot", "2026-10-12"], ["substem", "2026-10-13"]],
                 note="fixture: two leaves appear at c1, fully expanded at c2")]},
        instances=[dict(plant_instance_id="fx_ss0", slot_id="T2-row2-L", yaw_deg=0.0, variety="micro_tom")],
        decisions=None,
    )


def default_truss_request() -> dict[str, Any]:
    """MTG A5 fixture: the side-shoot plant (S1 substem, S2 axis_shoot -> substem) with two registry trusses.

    * M: a truss directly above main leaf serial 4 (rank 4), recorded before the first capture; the main stem
      continues above it (leaves 5 and 6 are segment 2; S2 sits in the axil of leaf 5, i.e. in segment 2);
    * S1: a truss directly above its leaf serial 9 (S1 rank 3), first recorded at c2 (S1 apical segment 1 -> 2).

    Trusses carry no geometry (none exists in the generator); ``above_rank`` is read from the fixture truth
    ranks at the first capture, like ``parent_rank``. ``fixture_leaf_records``: the snapshot receives each
    tracked compound's truth rank + unfolded flag through the fixture truth join (status synthetic_truth) in
    place of the human leaf record a real plant needs - without it no rank, so no segment_index, exists."""
    req = default_sideshoot_request()
    req["truss_registry"] = {"fx_ss0": [
        dict(axis="M", above_serial=4, first_observed="2026-10-09",
             note="fixture: first main-stem truss above main leaf 4, before the first capture"),
        dict(axis="S1", above_serial=9, first_observed="2026-10-13",
             note="fixture: substem S1 truss above its third leaf, first seen at c2")]}
    req["fixture_leaf_records"] = True
    return req


def _steps(seq: Sequence[Mapping[str, Any]], donor: ft.FixturePlant) -> list[Step]:
    return [Step(capture_id=d["capture_id"], time_h=float(d["time_h"]), phase=d["phase"],
                 yaw_deg=float(d.get("yaw_deg", 0.0)), rotation_known=bool(d.get("rotation_known", True)),
                 remove=list(d.get("remove", [])), add=[(donor, int(k), float(y)) for k, y in d.get("add", [])],
                 occlude=list(d.get("occlude", [])), merge=[list(m) for m in d.get("merge", [])],
                 split=list(d.get("split", [])), side_shoots=list(d.get("side_shoots", []))) for d in seq]


def _input_snapshot(request: Mapping[str, Any]) -> dict[str, str]:
    """sha256 of every input file a fixture/real run reads (replay compares these)."""
    paths: list[Path] = []
    if request["mode"] == "fixture":
        scene_dirs = [Path(p["scene_dir"]) for p in request["source_plants"]] + [Path(request["donor_scene"])] + [
            Path(p) for p in request["completion_pool_scenes"]]
        for sd in scene_dirs:
            paths += [sd / "plant_graph.json", sd / "leaflet_index.json"]
            cell = sd.parent.parent
            paths += [cell / "leaflet_contours.json", cell / "generator_config.json"]
            if (sd / "render_job" / "job.json").exists():
                paths.append(sd / "render_job" / "job.json")
            for lab in sorted((sd / "views").glob("*/labels.json")):
                paths.append(lab)
    else:
        raw = Path(request["raw_dir"])
        for c in sorted(raw.glob(f"{request.get('plant_glob', 'dwt_1*')}/*/generator_capture.csv")):
            paths.append(c)
        if request.get("detector_weights"):
            paths.append(Path(request["detector_weights"]))
        for im in request.get("detector_images", []):
            paths.append(Path(im))
        # human records the real build reads when present (A4 side shoots, A5 trusses, T6 pots); a record that
        # appears or changes later makes replay refuse with the record named
        for rec in (ax.REGISTRY_PATH, tr.REGISTRY_PATH, ps.POT_SPEC_PATH):
            if (PROJECT_ROOT / rec).exists():
                paths.append(rec)
        paths += [f.relative_to(PROJECT_ROOT) for f in ps.rim_point_files(PROJECT_ROOT / ps.RIM_POINTS_PATH.parent)]
    paths.append(cn.SLOT_TABLE)
    out = {}
    for p in sorted(set(paths)):
        full = p if p.is_absolute() else PROJECT_ROOT / p
        out[_rel(full)] = sha256_file(full)
    return out


def build_fixture(target: Path, request: Mapping[str, Any]) -> Path:
    cfg = ft.load_p1_config()
    cam = OrthoCamera(int(ft.cfg_value(cfg, "fixture", "ortho_image_size_px")),
                      float(ft.cfg_value(cfg, "fixture", "ortho_mm_per_px")))
    min_px = int(ft.cfg_value(cfg, "fixture", "min_visible_px"))
    lights = ft.cfg_value(cfg, "fixture", "fixture_time_since_lights_on_min")
    tcfg = link.load_config(link.FIXTURE_CONFIG)
    w = Writer(target)
    try:
        segments: list[s.SegmentStatus] = []
        donor = ft.load_plant(PROJECT_ROOT / request["donor_scene"], "fx_donor")
        pool_compounds: list[tuple[str, ft.FixtureCompound]] = []
        for sd in request["completion_pool_scenes"]:
            pp = ft.load_plant(PROJECT_ROOT / sd, "pool")
            pool_compounds += [(f"{sd}#{c.gen_compound_id}", c) for c in pp.compounds]
        captures, frames_rows, obs_rows, truth_join = [], [], [], []
        identity, events, matches = [], [], []
        mtg, edges, state_rows, changes, unresolved, comps = [], [], [], [], [], []
        area_rows, cand_rows, completion_report = [], [], []
        truth_mtg, truth_edges, truth_areas, serials = [], [], [], []
        side_rows, side_errors = [], []
        axes_all: list[dict[str, str]] = []
        trusses_all: list[dict[str, str]] = []
        truss_declared = bool(request.get("truss_registry"))
        classification: list[dict[str, str]] = []
        latest: dict[str, tuple[ft.FixturePlant, Any]] = {}
        candidates_by_src: dict[str, list[op.Candidate]] = {}
        id_scores: dict[str, Any] = {}
        fixture_entries = []
        for spec in request["source_plants"]:
            pid = spec["source_plant_id"]
            plant = ft.load_plant(PROJECT_ROOT / spec["scene_dir"], pid)
            fixture_entries.append(ft.fixture_manifest_entry(plant, cam))
            serials += ft.compound_serial_table(plant)
            gen_cfg_p, contours_p = _generator_inputs(PROJECT_ROOT / spec["scene_dir"])
            states = run_sequence(plant, _steps(request["sequences"][pid], donor), cam, min_px, pid,
                                  gen_cfg_p, contours_p)
            obs_by_cap = {st.step.capture_id: compound_observations(st) for st in states}
            result = link.track_plant(pid, pid, [st.frame for st in states], obs_by_cap, tcfg,
                                      link.load_decisions(request.get("decisions")))
            identity += result.identity_rows
            events += result.events
            matches += result.match_rows
            id_scores[pid] = {k: v for k, v in identity_score(states, result.obs_to_track).items()
                              if k != "track_to_truth"}
            truth_ranks = _truth_ranks_per_axis(states)
            plant_axes = _fixture_axes(w, request, pid, states, truth_ranks, result)
            clock = [ax.CaptureClock(st.step.capture_id, FIXTURE_TIME_ZERO + timedelta(hours=st.step.time_h))
                     for st in states]
            truss_entries = _fixture_trusses(w, request, pid, states, truth_ranks)
            tr.annotate_axes(plant_axes, truss_entries, pid, pid, clock)
            axis_vertex_of = {r["axis"]: r["axis_vertex_id"] for r in plant_axes}
            if truss_entries is not None:
                trusses_all += tr.truss_table_rows(pid, pid, clock, truss_entries, axis_vertex_of,
                                                   "synthetic_fixture", "synthetic_truth")
            leaf_records = _fixture_leaf_records(states, truth_ranks, result) if request.get(
                "fixture_leaf_records") else {}
            axes_all += plant_axes
            for st in states:
                classification += ax.classify(st.obs.rows, ax.state_of_axes(plant_axes, st.step.capture_id))
            prev_snapshot: list[dict[str, str]] = []
            prev_info: up.CaptureInfo | None = None
            prev_areas: list[dict[str, str]] = []
            infos: list[tuple[up.CaptureInfo, list[dict[str, str]]]] = []
            for st in states:
                step = st.step
                when = FIXTURE_TIME_ZERO + timedelta(hours=step.time_h)
                rot_known = step.rotation_known
                info = up.CaptureInfo(capture_id=step.capture_id, frame="plant_local_mm" if rot_known else "image_px",
                                      mm_per_px=cam.mm_per_px, center_px=(cam.center_px, cam.center_px),
                                      rotation_deg=step.yaw_deg if rot_known else None,
                                      photoperiod_phase=step.phase, time_since_lights_on_min=float(lights[step.phase]),
                                      evidence="synthetic_fixture", scale_source="synthetic_ortho_camera_declared",
                                      mm_per_px_sd=0.0)
                captures.append(dict(
                    capture_id=step.capture_id, plant_instance_id=pid, source_plant_id=pid, evidence="synthetic_fixture",
                    view="top", capture_time=when.isoformat(), capture_time__status="assumed",
                    capture_tz="UTC+09:00", capture_tz_source="assumed",
                    time_since_lights_on_min=str(lights[step.phase]), time_since_lights_on_min__status="assumed",
                    photoperiod_phase=step.phase, frame=info.frame, scale_source=info.scale_source,
                    scale_status="solved", mm_per_px=s.fmt(cam.mm_per_px), mm_per_px_sd="0",
                    scale_convention="synthetic_ortho_camera_declared", scale_sources="1",
                    scale_cross_check="none_single_source", scale_plane="synthetic_camera",
                    scale_reference="synthetic_ortho_camera_declared", scale_reference_plane="synthetic_camera",
                    scale_reference_plane_offset_mm=UNAVAILABLE,
                    rotation_status="solved" if rot_known
                    else UNAVAILABLE, image_path=f"synthetic:ortho_top/{pid}/{step.capture_id}",
                    image_sha256=hashlib.sha256(st.render.visible.tobytes()).hexdigest(), session_id=f"{pid}_fixture",
                    note=json.dumps(step.describe())))
                frames_rows.append(dict(plant_instance_id=pid, capture_id=step.capture_id,
                                        center_x_px=s.fmt(cam.center_px), center_y_px=s.fmt(cam.center_px),
                                        mm_per_px=s.fmt(cam.mm_per_px), mm_per_px_sd="0",
                                        scale_convention="synthetic_ortho_camera_declared",
                                        scale_reference_plane="synthetic_camera",
                                        scale_reference_plane_offset_mm=UNAVAILABLE,
                                        rim_homography_px_to_mm=UNAVAILABLE,
                                        rotation_deg=s.fmt(step.yaw_deg) if rot_known else UNAVAILABLE,
                                        scale_status="solved", rotation_status="solved" if rot_known else UNAVAILABLE,
                                        method="synthetic_ortho_camera_declared"))
                obs_rows += st.obs.rows
                truth_join += st.obs.truth_join
                w.json(f"observations/{_safe(pid)}__{_safe(step.capture_id)}/masks.json", ingest.pack_masks(st.obs.masks))
                # truth
                trows = ft.truth_mtg(st.plant, pid, step.capture_id, truth_ranks[step.capture_id])
                now = None if truss_entries is None else tr.known_at(truss_entries, pid, clock, step.capture_id)
                if now:
                    trows += tr.truss_vertex_rows(next(r for r in trows if r["class"] == "Plant"), now,
                                                  axis_vertex_of, "synthetic_truth")
                tr.apply_segments(trows, now)
                s.check_mtg_rows(trows, "truth/truth_mtg_vertices.csv")
                truth_mtg += trows
                truth_edges += ft.mtg_edges(trows)
                truth_areas += ft.truth_area_rows(st.plant, pid, step.capture_id, st.render, cam)
                # observation path -> snapshot
                inp = up.SnapshotInputs(plant_id=pid, plant_instance_id=pid, capture=info, observations=st.obs.rows,
                                        masks=st.obs.masks, identity_rows=result.identity_rows, axes_rows=plant_axes,
                                        human_records=leaf_records.get(step.capture_id, {}),
                                        record_status="synthetic_truth", trusses_now=now,
                                        truss_status="synthetic_truth")
                if spec.get("side_views") and step.capture_id == states[-1].step.capture_id:
                    finalized = [v.name for v in sorted((PROJECT_ROOT / spec["scene_dir"] / "views").iterdir())
                                 if (v / "rgb.png").exists()]
                    rows_s, errs = sg.validate_scene(PROJECT_ROOT / spec["scene_dir"], pid, finalized)
                    rows_s = sg.select_views(rows_s)
                    side_rows += rows_s
                    side_errors += errs
                    inp.side_values, inp.side_view_of, join_ref = _side_join(rows_s, st, result.obs_to_track)
                    inp.side_join_ref = join_ref
                snap = up.build_snapshot(inp)
                s.check_mtg_rows(snap)
                mtg += snap
                edges += ft.mtg_edges(snap)
                state_rows += up.structure_state_rows(inp, snap)
                changes += up.change_log(prev_snapshot, snap)
                unresolved += up.unresolved_rows(snap, "not produced by this capture")
                areas_now = up.area_rows(inp, result.obs_to_track)
                area_rows += areas_now
                if prev_info is not None:
                    comps += up.comparisons(pid, prev_info, info, prev_areas, areas_now)
                infos.append((info, areas_now))
                prev_snapshot, prev_info, prev_areas = snap, info, areas_now
            # c0 vs c2 (same phase) too, so the guard shows both outcomes
            if len(infos) >= 3:
                comps += up.comparisons(pid, infos[0][0], infos[2][0], infos[0][1], infos[2][1])
            last = states[-1]
            latest[pid] = (last.plant, last)
            # conditional completion for observed compounds of the latest capture that touch others:
            # two adapters, each reported on its own row (pool donors; generator conditioned on the observation)
            plant_visible = last.render.visible > 0
            gen_cfg, gen_contours = _generator_inputs(PROJECT_ROOT / spec["scene_dir"])
            terminal_of = {r["parent_obs_id"]: r["obs_id"] for r in last.obs.rows
                           if r["obs_class"] == "terminal_leaflet" and r["membership_status"] == "confirmed"}
            tol = float(ft.cfg_value(cfg, "completion", "coverage_tolerance"))
            max_kept = int(ft.cfg_value(cfg, "completion", "max_kept"))
            cap_yaw = last.step.yaw_deg if last.step.rotation_known else 0.0
            for orow in last.obs.rows:
                if orow["obs_class"] != "compound_leaf" or orow["touches_other_mask"] != "true":
                    continue
                tid = result.obs_to_track.get((last.step.capture_id, orow["obs_id"]))
                if tid is None:
                    continue
                mask = last.obs.masks[orow["obs_id"]]
                kept_pool, rep_pool = op.complete_compound(mask, plant_visible, cap_yaw, cam, pool_compounds, tol,
                                                           max_kept, tid)
                kept_gen, rep_gen = op.generate_candidates(
                    mask, plant_visible, cap_yaw, cam, gen_cfg, gen_contours,
                    int(ft.cfg_value(cfg, "completion", "generator_n_samples")),
                    float(ft.cfg_value(cfg, "completion", "extent_slack_rel")), tol, max_kept, tid,
                    last.obs.masks.get(terminal_of.get(orow["obs_id"], "")),
                    int(ft.cfg_value(cfg, "completion", "refine_top")),
                    [float(x) for x in ft.cfg_value(cfg, "completion", "refine_yaw_deg")],
                    [float(x) for x in ft.cfg_value(cfg, "completion", "refine_scale")])
                for kept_i, rep in ((kept_pool, rep_pool), (kept_gen, rep_gen)):
                    completion_report.append(dict(
                        plant_instance_id=pid, capture_id=last.step.capture_id, track_id=tid, obs_id=orow["obs_id"],
                        reasons="touches_other_mask", adapter=rep["adapter"],
                        n_tried=str(rep.get("n_pool", rep.get("n_samples"))), n_generated=str(rep["n_generated"]),
                        n_contract_rejected=str(rep.get("n_contract_rejected", 0)),
                        best_coverage=s.fmt(rep.get("best_coverage", max((c.coverage for c in kept_i), default=None)), 4),
                        coverage_tolerance=s.fmt(tol, 4), n_kept=str(rep["n_kept"]),
                        kept_background_violation_min=s.fmt(min((c.background_violation for c in kept_i), default=None), 4),
                        kept_background_violation_max=s.fmt(max((c.background_violation for c in kept_i), default=None), 4),
                        candidate_status=rep["candidate_status"],
                        terminal_pins=json.dumps(rep.get("pins", {}), sort_keys=True),
                        prior_status=rep["prior_status"]))
                kept = kept_pool + kept_gen
                for cand in kept:
                    leaves = [dict(tag=vid.rsplit("/", 1)[1],
                                   area_mm2=float(ft.g.triangle_areas(*m).sum()),
                                   base_mm=list(m[0].mean(axis=0))) for vid, m in sorted(cand.meshes.items())]
                    track_axis = next((r["axis"] for r in result.identity_rows if r["organ_id"] == tid), UNAVAILABLE)
                    cand_rows += up.candidate_rows(pid, pid, last.step.capture_id, tid, cand.candidate_id,
                                                   "plant_local_mm", "synthetic_fixture", leaves, track_axis)
                    candidates_by_src.setdefault(pid, []).append(cand)
        tr.fill_identity_segments(identity, mtg)
        s.check_captures(captures)
        s.check_observations(obs_rows, "synthetic_fixture")
        s.check_identity_rows(identity)
        s.check_candidate_rows(cand_rows, "candidates.csv")
        scale_by_cap = {r["capture_id"]: r["scale_status"] for r in captures}
        plane_by_cap = {r["capture_id"]: s.reference_plane_of(r) for r in captures}
        s.check_areas(area_rows, scale_by_cap, plane_by_cap)
        s.check_areas(truth_areas, scale_by_cap, plane_by_cap)
        segments.append(s.SegmentStatus("P1.3_ingest", "fixture_only",
                                        "synthetic_gt observations from ortho renders of generator scenes"))
        segments.append(s.SegmentStatus("P1.4_tracking", "fixture_only",
                                        "fixture-declared association config; every link proposed (no human decisions)"))
        segments.append(s.SegmentStatus("P1.5_structure_update", "fixture_only", "top-view observation path"))
        segments.append(s.SegmentStatus(
            "P1.4_trusses", "fixture_only",
            "fixture truss registry (synthetic_truth above_rank) -> trusses.csv, Truss vertices, segment_index"
            if truss_declared else "no truss registry declared for this fixture: segment_index unavailable"))
        segments.append(s.SegmentStatus("P1.6_side_geometry", "fixture_only",
                                        "projected generator truth points on R.1 scene_0000 (batch a, rendered)"))
        # instances, optical surfaces, canopy
        slots = cn.load_slots(PROJECT_ROOT / cn.SLOT_TABLE)
        reqs = [cn.InstanceRequest(i["plant_instance_id"], i["slot_id"], i["yaw_deg"], i["variety"],
                                   "fixture_declared", "fixture_declared") for i in request["instances"]]
        placements = cn.place(reqs, slots, cfg)
        pmap = {p.plant_instance_id: p for p in placements}
        optical_rows: list[dict[str, str]] = []
        optical_dir = w.path("optical_surfaces/.keep").parent
        for p in placements:
            src = p.source_plant_id
            if src not in latest:
                # other-variety occluder: a plant-level MTG row from the placement record (A1.3); it has no
                # photo, so it gets no captures.csv row (capture_id 'no_capture' marks the record-only snapshot)
                row = s.blank_mtg_row()
                row.update(plant_instance_id=p.plant_instance_id, plant_id=src, capture_id="no_capture",
                           snapshot_capture_id="no_capture", vertex_id=src, scale="1", parent_id=UNAVAILABLE,
                           complex_id=UNAVAILABLE, edge_type=UNAVAILABLE, display_name=UNAVAILABLE, observed="false",
                           frame="image_px", evidence="synthetic_fixture", **{"class": "Plant"})
                s.set_value(row, "variety", "other", "assumed")
                s.set_value(row, "slot_id", p.slot_id or UNAVAILABLE, "assumed" if p.slot_id else UNAVAILABLE)
                s.set_value(row, "light_ratio", p.light_ratio, "app_ratio" if p.light_ratio != UNAVAILABLE else UNAVAILABLE)
                mtg.append(row)
                unresolved += up.unresolved_rows([row], "other-variety plant: plant-level MTG only (A1.3)")
                continue
            plant, last = latest[src]
            cap_id = last.step.capture_id
            if p.plant_instance_id != src:  # duplicate instance: replicate the source's P1 rows under its own id
                for table in (identity, mtg, edges, state_rows, area_rows, unresolved, axes_all, trusses_all):
                    table += [dict(r, plant_instance_id=p.plant_instance_id) for r in table
                              if r["plant_instance_id"] == src]
                captures += [dict(r, plant_instance_id=p.plant_instance_id) for r in captures
                             if r["plant_instance_id"] == src]
            optical_rows += op.export_truth(optical_dir, Path("optical_surfaces"), plant, p.plant_instance_id, cap_id)
            for cand in candidates_by_src.get(src, []):
                optical_rows += op.export_candidates(optical_dir, Path("optical_surfaces"), p.plant_instance_id,
                                                     cap_id, [cand])
        (optical_dir / ".keep").unlink(missing_ok=True)
        s.check_optical_rows(optical_rows)
        for row in mtg:
            p = pmap.get(row["plant_instance_id"])
            if row["class"] == "Plant" and p is not None and row["slot_id"] == UNAVAILABLE and p.slot_id:
                s.set_value(row, "slot_id", p.slot_id, "assumed")
                s.set_value(row, "light_ratio", p.light_ratio, "app_ratio")
                s.set_value(row, "variety", p.variety, "assumed")
        unresolved = _reconcile_unresolved(mtg, unresolved)
        s.check_mtg_rows(mtg)
        s.check_captures(captures)
        doc = cn.placement_document(placements, reqs, cfg, sha256_file(PROJECT_ROOT / cn.SLOT_TABLE),
                                    "synthetic_fixture")
        merge_check = _merge_check(w.stage, optical_rows, pmap)
        segments.append(s.SegmentStatus("P1.7_optical_surfaces", "fixture_only",
                                        "truth meshes (supported, fixture) + pool-donor conditional candidates"))
        segments.append(s.SegmentStatus("P1.8_canopy_placement", "fixture_only",
                                        "fixture-declared slots and yaws; tray geometry assumed_unmeasured"))
        # write
        w.table("captures.csv", captures, s.CAPTURES_COLUMNS)
        s.check_frame_transforms(frames_rows)
        w.table("frame_transforms.csv", frames_rows, s.FRAME_TRANSFORMS_COLUMNS)
        w.table("observations/observations.csv", obs_rows, s.OBSERVATIONS_COLUMNS)
        w.table("observations/truth_join.csv", truth_join, s.TRUTH_JOIN_COLUMNS)
        w.table("identity_manifest.csv", identity, s.IDENTITY_COLUMNS)
        w.table("events.csv", events, s.EVENTS_COLUMNS)
        w.table("match_candidates.csv", matches, s.MATCH_CANDIDATES_COLUMNS)
        s.check_axes(axes_all)
        s.check_trusses(trusses_all)
        s.check_axes_coverage(axes_all, mtg, identity, _truss_axis_rows(trusses_all))
        w.table("axes.csv", axes_all, s.AXES_COLUMNS)
        w.table("trusses.csv", trusses_all, s.TRUSSES_COLUMNS)
        w.table("axis_classification.csv", classification, ax.CLASSIFICATION_COLUMNS)
        w.table("mtg_vertices.csv", mtg, s.MTG_VERTICES_COLUMNS)
        w.table("mtg_edges.csv", edges, s.MTG_EDGES_COLUMNS)
        w.table("structure_state.csv", state_rows, s.STRUCTURE_STATE_COLUMNS)
        w.table("change_log.csv", changes, s.CHANGE_LOG_COLUMNS)
        w.table("unresolved.csv", unresolved, s.UNRESOLVED_COLUMNS)
        w.table("comparisons.csv", comps, s.COMPARISONS_COLUMNS)
        w.table("areas.csv", area_rows, s.AREAS_COLUMNS)
        w.table("candidates.csv", cand_rows, s.MTG_VERTICES_COLUMNS)
        w.table("completion_report.csv", completion_report, COMPLETION_COLUMNS)
        w.table("side_geometry.csv", side_rows, s.SIDE_GEOMETRY_COLUMNS)
        w.table("side_validation_errors.csv", side_errors, sg.SIDE_ERROR_COLUMNS)
        w.table("side_validation_summary.csv", sg.summarize_errors(side_errors, [0, 30, 60, 90.01]),
                sg.SIDE_SUMMARY_COLUMNS)
        w.table("optical_surface_manifest.csv", optical_rows, s.OPTICAL_MANIFEST_COLUMNS)
        w.table("truth/truth_mtg_vertices.csv", truth_mtg, s.MTG_VERTICES_COLUMNS)
        w.table("truth/truth_mtg_edges.csv", truth_edges, s.MTG_EDGES_COLUMNS)
        w.table("truth/truth_areas.csv", truth_areas, s.AREAS_COLUMNS)
        w.table("truth/compound_serials.csv", serials, SERIAL_COLUMNS)
        w.json("canopy_placement.json", doc)
        w.json("canopy_merge_check.json", merge_check)
        if not merge_check["round_trip_ok"]:
            raise PackageError("canopy merge/split round trip failed")
        _write_viewer(w, optical_rows, pmap)
        w.table("compare_observation.csv", compare_observation(w.stage), COMPARE_COLUMNS)
        segments.insert(0, s.SegmentStatus("P1.2_fixture_truth", "fixture_only",
                                           "truth MTG/areas/surfaces from generator meshes"))
        manifest = _manifest(w, request, segments, evidence="synthetic_fixture",
                             extra=dict(fixtures=fixture_entries, tracking_identity_scores=id_scores,
                                        tracking_config=_rel(link.FIXTURE_CONFIG),
                                        completeness=dict(
                                            observation_reconstruction_real="not demonstrated by this package "
                                                                            "(fixture boundary)",
                                            interfaces="implemented; validated by collect",
                                            fixture_engineering_path="executed")))
        w.json("p1_manifest.json", manifest)
        return w.publish()
    except Exception:
        w.abort()
        raise


COMPLETION_COLUMNS = ("plant_instance_id", "capture_id", "track_id", "obs_id", "reasons", "adapter", "n_tried",
                      "n_generated", "n_contract_rejected", "best_coverage", "coverage_tolerance", "n_kept",
                      "kept_background_violation_min", "kept_background_violation_max", "candidate_status",
                      "terminal_pins", "prior_status")


def _generator_inputs(scene_dir: Path) -> tuple[dict[str, Any], list[np.ndarray]]:
    """The scene's own cell generator config + contour library (the candidate generator's priors)."""
    from tomato3d.synth.contours import load_library

    cell = Path(scene_dir).resolve().parent.parent
    gen_cfg = json.loads((cell / "generator_config.json").read_text(encoding="utf-8"))
    contours, _ = load_library(cell / "leaflet_contours.json")
    return gen_cfg, contours
SERIAL_COLUMNS = ("source_plant_id", "vertex_id", "generator_compound_id", "age_days", "source_ref")


def _truth_ranks_per_axis(states) -> dict[str, dict[str, int]]:
    """A1.1 anchoring applied on EVERY axis separately (A4): the first capture an axis is seen is its rank
    reference; the basal of two leaves seen together is rank 1 (tie rule, proposal)."""
    previous: dict[str, dict[str, int]] = {}
    out: dict[str, dict[str, int]] = {}
    for st in states:
        ranks: dict[str, int] = {}
        for axis in sorted({c.axis for c in st.plant.compounds}):
            heights = {st.plant.compound_vertex_id(c): float(c.attachment_mm[2])
                       for c in st.plant.compounds if c.axis == axis}
            result = up.anchor_ranks(heights, previous.get(axis))
            previous[axis] = result.ranks
            ranks.update({k: v for k, v in result.ranks.items() if k in heights})
        out[st.step.capture_id] = ranks
    return out


def _fixture_axes(w: Writer, request: Mapping[str, Any], pid: str, states, truth_ranks, result) -> list[dict[str, str]]:
    """Fixture registry -> the SAME reader as real data -> axes.csv rows (MTG A4).

    The fixture registry is written into the package as ``side_shoot_registry.csv`` (synthetic, status
    synthetic_truth); parent ranks come from the truth ranks at the first capture. ``parent_node_id`` and the
    registration leaves are tracker ids, joined through the fixture truth join (synthetic only)."""
    spec = (request.get("side_shoot_registry") or {}).get(pid, [])
    clock = [ax.CaptureClock(st.step.capture_id, FIXTURE_TIME_ZERO + timedelta(hours=st.step.time_h)) for st in states]
    first = states[0]
    truth_to_track = {}
    for row in first.obs.truth_join:
        tid = result.obs_to_track.get((first.step.capture_id, row["obs_id"]))
        if tid and row["truth_vertex_id"].count("/") == 1:
            truth_to_track[row["truth_vertex_id"]] = tid
    rank_c0 = truth_ranks[first.step.capture_id]
    main_rank_to_node = {}
    for c in first.plant.compounds:
        vid = first.plant.compound_vertex_id(c)
        if c.axis == "M" and vid in rank_c0 and vid in truth_to_track:
            main_rank_to_node[rank_c0[vid]] = truth_to_track[vid]
    entries: list[ax.RegistryEntry] = []
    if spec:
        path = w.path(f"side_shoot_registry/{_safe(pid)}.csv")
        import csv as _csv

        with path.open("w", encoding="utf-8", newline="") as fh:
            wr = _csv.writer(fh, lineterminator="\n")
            wr.writerow(ax.REGISTRY_COLUMNS)
            for e in spec:
                parent_vid = s.compound_id(pid, int(e["parent_serial"]))
                rank = rank_c0.get(parent_vid)
                for state, day in e["states"]:
                    wr.writerow([pid, e["axis"], "" if rank is None else rank, e["first_observed"], state, day,
                                 e["note"] + "; parent_rank from fixture truth"])
        entries = ax.read_registry(path)
    leaves: dict[str, list[str]] = {}
    for e in entries:
        first_day = e.first_observed
        cap = next((c.capture_id for c in clock if c.when is not None and c.when.date() == first_day), None)
        ids = sorted(r["organ_id"] for r in result.identity_rows
                     if cap and r["capture_id"] == cap and r["axis"] == e.axis and r["organ_class"] == "compound_leaf"
                     and r["track_state"] == "first_observed")
        if len(ids) == 2:
            leaves[e.axis] = ids
    return ax.axes_rows(pid, pid, clock, entries, main_rank_to_node, "synthetic_fixture", "synthetic_truth", leaves)


def _truss_axis_rows(trusses: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    return [dict(plant_instance_id=r["plant_instance_id"], axis=r["axis_id"]) for r in trusses]


def _fixture_trusses(w: Writer, request: Mapping[str, Any], pid: str, states, truth_ranks
                     ) -> list[tr.TrussEntry] | None:
    """Fixture truss registry -> ``truss_registry/<pid>.csv`` in the package -> the SAME reader as real data.
    ``above_rank`` = the truth rank (first capture) of the declared leaf. None = no registry declared."""
    spec = (request.get("truss_registry") or {}).get(pid)
    if spec is None:
        return None
    rank_c0 = truth_ranks[states[0].step.capture_id]
    path = w.path(f"truss_registry/{_safe(pid)}.csv")
    import csv as _csv

    with path.open("w", encoding="utf-8", newline="") as fh:
        wr = _csv.writer(fh, lineterminator="\n")
        wr.writerow(tr.REGISTRY_COLUMNS)
        for e in spec:
            rank = rank_c0.get(s.compound_id(pid, int(e["above_serial"])))
            wr.writerow([pid, e["axis"], "" if rank is None else rank, e["first_observed"],
                         e["note"] + "; above_rank from fixture truth"])
    entries = tr.read_registry(path)
    side_path = w.path(f"side_shoot_registry/{_safe(pid)}.csv")
    tr.check_against_axes(entries, ax.read_registry(side_path) if side_path.exists() else [])
    return entries


def _fixture_leaf_records(states, truth_ranks, result) -> dict[str, dict[str, dict[str, str]]]:
    """FIXTURE ONLY: per capture, track id -> {rank, leaf_unfolded} from the scene truth, joined through the
    fixture truth join (synthetic_truth; stands in for the human leaf record of a real plant). A track joined to
    more than one truth compound (a wrong link) gets no record."""
    truth_of: dict[str, set[str]] = {}
    for st in states:
        for row in st.obs.truth_join:
            tid = result.obs_to_track.get((st.step.capture_id, row["obs_id"]))
            if tid and not tid.endswith("/T") and row["truth_vertex_id"].count("/") == 1:
                truth_of.setdefault(tid, set()).add(row["truth_vertex_id"])
    out: dict[str, dict[str, dict[str, str]]] = {}
    for st in states:
        ranks = truth_ranks[st.step.capture_id]
        recs: dict[str, dict[str, str]] = {}
        for tid, truths in truth_of.items():
            if len(truths) == 1 and next(iter(truths)) in ranks:
                recs[tid] = dict(rank=str(ranks[next(iter(truths))]), leaf_unfolded="true")
        out[st.step.capture_id] = recs
    return out


def _side_join(side_rows: Sequence[Mapping[str, str]], state, obs_to_track: Mapping[tuple[str, str], str]
               ) -> tuple[dict[str, dict[str, tuple[str, str]]], dict[str, str], str]:
    """FIXTURE ONLY: join side-view rows (truth compound ids) to tracker ids through the truth join.
    A real cross-view (side <-> top) association does not exist; real side rows stay in side_geometry.csv."""
    truth_to_track: dict[str, str] = {}
    for row in state.obs.truth_join:
        tid = obs_to_track.get((state.step.capture_id, row["obs_id"]))
        if tid and "/T" not in tid and row["truth_vertex_id"].count("/") == 1:
            truth_to_track[row["truth_vertex_id"]] = tid
    selected = [r for r in side_rows if r["selected_for_mtg"] == "true"]  # MTG A3 (sidegeom.select_views)
    best = {r["compound_id"]: r for r in selected}
    if len(best) != len(selected):
        raise PackageError("MTG A3: more than one side view selected for a compound")
    out: dict[str, dict[str, tuple[str, str]]] = {}
    views: dict[str, str] = {}
    for truth_id, r in best.items():
        tid = truth_to_track.get(truth_id)
        if tid is None:
            continue
        vals: dict[str, tuple[str, str]] = {}
        for attr in ("compound_insertion_angle_deg", *s.ALPHA_COLUMNS, "rachis_curvature_deg",
                     "rachis_bend_theta_deg", "chord_to_path_ratio"):
            if r[attr] != UNAVAILABLE:
                vals[attr] = (r[attr], "derived")
        if r["n_bend_nodes"] != UNAVAILABLE:
            vals["n_bend_nodes"] = (r["n_bend_nodes"], "derived")
        out[tid] = vals
        views[tid] = r["view_id"]
    return out, views, ("fixture_truth_join:observations/truth_join.csv (synthetic only); side view chosen by "
                        f"{sg.VIEW_SELECTION_RULE}; compounds without such a view stay unavailable")


def _reconcile_unresolved(mtg: Sequence[Mapping[str, str]], rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop unresolved rows whose cell was filled later (slot/ratio set from placement); dedupe."""
    filled = {(v["plant_instance_id"], v["capture_id"], v["vertex_id"], a) for v in mtg for a in s.MTG_VALUE_ATTRIBUTES
              if v[a] != UNAVAILABLE}
    seen, out = set(), []
    for r in rows:
        key = (r["plant_instance_id"], r["capture_id"], r["vertex_id"], r["attr"])
        if key in filled or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _merge_check(stage: Path, optical_rows: Sequence[Mapping[str, str]], pmap: Mapping[str, cn.Placement]
                 ) -> dict[str, Any]:
    files = sorted({r["surface_file"] for r in optical_rows if r["optical_readiness"] == "supported"})
    rows = [r for f in files for r in read_table(stage / f, s.OPTICAL_TRIANGLES_COLUMNS)]
    merged = cn.merge_triangles(pmap, rows)
    back = cn.split_triangles(pmap, merged)
    orig = {(r["external_leaflet_id"], r["triangle_id"]): r for r in rows}
    max_err = 0.0
    for inst_rows in back.values():
        for r in inst_rows:
            o = orig[(r["external_leaflet_id"], r["triangle_id"])]
            for k in range(3):
                for a in "xyz":
                    max_err = max(max_err, abs(float(r[f"v{k}_{a}_mm"]) - float(o[f"v{k}_{a}_mm"])))
    per_instance = {}
    for inst, p in pmap.items():
        ids = {r["external_leaflet_id"] for r in rows if s.split_external_id(r["external_leaflet_id"])[0] == inst}
        per_instance[inst] = dict(in_optical_scene=p.in_optical_scene, leaflets=len(ids),
                                  triangles=sum(1 for r in merged if s.split_external_id(r["external_leaflet_id"])[0] == inst))
    dup_sets = {}
    for inst in pmap:
        src = s.source_of_instance(inst)
        dup_sets.setdefault(src, []).append(inst)
    distinct = all(
        len({s.split_external_id(r["external_leaflet_id"])[0] for r in merged
             if s.source_of_instance(s.split_external_id(r["external_leaflet_id"])[0]) == src}) == len(
            [i for i in insts if pmap[i].in_optical_scene])
        for src, insts in dup_sets.items())
    return dict(frame_in="plant_local_mm", frame_canopy="canopy_mm", n_triangles_in=len(rows),
                n_triangles_merged=len(merged), max_round_trip_error_mm=round(max_err, 6),
                round_trip_tolerance_mm=1e-3, round_trip_ok=bool(max_err <= 1e-3 and len(rows) == len(merged)),
                duplicate_instances_distinct=distinct, per_instance=per_instance,
                note="merged canopy triangles are not stored; P2 applies canopy_placement.json itself")


def _write_viewer(w: Writer, optical_rows: Sequence[Mapping[str, str]], pmap: Mapping[str, cn.Placement]) -> None:
    """Display-only canopy top view: leaflet outlines (projected triangle hulls) per instance."""
    import cv2

    shapes = []
    for f in sorted({r["surface_file"] for r in optical_rows if r["optical_readiness"] != "unavailable"}):
        rows = read_table(w.stage / f, s.OPTICAL_TRIANGLES_COLUMNS)
        by: dict[str, list[list[float]]] = {}
        for r in rows:
            by.setdefault(r["external_leaflet_id"], []).extend(
                [[float(r[f"v{k}_x_mm"]), float(r[f"v{k}_y_mm"]), float(r[f"v{k}_z_mm"])] for k in range(3)])
        cond = "cand_" in f
        for ext, pts in by.items():
            inst, _ = s.split_external_id(ext)
            p = pmap[inst]
            if not p.placed:
                continue
            q = p.to_canopy(np.asarray(pts))
            hull = cv2.convexHull(q[:, :2].astype(np.float32)).reshape(-1, 2)
            shapes.append(dict(id=ext, inst=inst, cond=cond, z=float(q[:, 2].mean()),
                               pts=[[round(float(x), 1), round(float(y), 1)] for x, y in hull]))
    shapes.sort(key=lambda d: d["z"])
    html = VIEWER_HTML.replace("__DATA__", json.dumps(shapes))
    w.text("viewer/index.html", html)


VIEWER_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>P1 canopy view</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui,sans-serif;margin:16px;background:#fafaf7;color:#222}
canvas{border:1px solid #ccc;background:#fff;max-width:100%}.n{font-size:13px;color:#555}</style></head>
<body><h3>P1 state - canopy top view (display only)</h3>
<p class="n">Leaflet outlines = convex hulls of located surface triangles, placed with canopy_placement.json.
Green = supported (synthetic fixture truth), orange = conditional completion (generated candidate).
Display only: nothing here is a measurement.</p><canvas id="c" width="900" height="600"></canvas>
<pre id="i" class="n"></pre><script>
const S=__DATA__;const c=document.getElementById('c'),x=c.getContext('2d');
let a=[1e9,1e9,-1e9,-1e9];for(const s of S)for(const p of s.pts){a[0]=Math.min(a[0],p[0]);a[1]=Math.min(a[1],p[1]);a[2]=Math.max(a[2],p[0]);a[3]=Math.max(a[3],p[1]);}
const sc=Math.min((c.width-40)/(a[2]-a[0]),(c.height-40)/(a[3]-a[1]));
const T=p=>[20+(p[0]-a[0])*sc,20+(p[1]-a[1])*sc];
for(const s of S){x.beginPath();s.pts.forEach((p,k)=>{const q=T(p);k?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]);});x.closePath();
x.fillStyle=s.cond?'rgba(230,140,40,0.25)':'rgba(60,150,70,0.45)';x.strokeStyle=s.cond?'#c76b00':'#2d6e35';x.fill();x.stroke();}
const n={};for(const s of S)n[s.inst]=(n[s.inst]||0)+1;document.getElementById('i').textContent='leaflet outlines per instance: '+JSON.stringify(n);
</script></body></html>
"""


def _manifest(w: Writer, request: Mapping[str, Any], segments: Sequence[s.SegmentStatus], evidence: str,
              extra: Mapping[str, Any]) -> dict[str, Any]:
    return dict(
        schema_version=s.P1_SCHEMA_VERSION,
        schema_revision=s.P1_SCHEMA_REVISION,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        evidence=evidence,
        counts_as_photo_reconstruction=evidence == "real_photo",
        code_version=code_version(), code_hashes=code_hashes(), git=_git_describe(PROJECT_ROOT),
        request=dict(request),
        input_snapshot=_input_snapshot(request),
        run_status=[seg.as_dict() for seg in segments],
        overall_status=_overall(segments),
        p2_field_map=P2_FIELD_MAP,
        files=w.file_hashes(),
        **extra,
    )


def _overall(segments: Sequence[s.SegmentStatus]) -> str:
    states = {seg.status for seg in segments}
    if "failed" in states:
        return "failed"
    if states == {"executed"}:
        return "executed"
    if "unavailable" in states:
        return "partial" if states - {"unavailable"} else "unavailable"
    return "fixture_only"


P2_FIELD_MAP: list[dict[str, str]] = [
    dict(producer="canopy_placement.json instances[].plant_instance_id / source_plant_id",
         consumer="tools/vtc_growth_io.py HEADERS['plants.csv'] plant_instance_id, source_plant_id",
         rule="copied; duplicates are distinct instances"),
    dict(producer="canopy_placement.json instances[].p2_plants_csv.{tx_mm,ty_mm,tz_mm,yaw_deg,transform_source}",
         consumer="plants.csv tx_mm, ty_mm, tz_mm, yaw_deg, transform_source",
         rule="same names and units (mm, deg); only instances with placement_status=placed and in_optical_scene"),
    dict(producer="optical_surface_manifest.csv external_leaflet_id (= <plant_instance_id>|<vertex_id>)",
         consumer="leaflets.csv plant_instance_id, compound_id, leaflet_id; P2 per-leaflet light output key",
         rule="split at '|': instance | MTG vertex id; compound_id = vertex id without the last '/<tag>'"),
    dict(producer="optical_surfaces/*.csv triangles (plant_local_mm, adaxial_ccw, one_sided_lamina_full_outline)",
         consumer="P2 located leaflet geometry (GroIMP/VTC scene; tomato3d.light LEAF_SURFACES-like triangles)",
         rule="apply canopy transform once; incident/absorbed per external_leaflet_id on the one-sided area"),
    dict(producer="optical_surface_manifest.csv optical_readiness",
         consumer="P2 input gate", rule="supported -> usable; conditional_completion -> scenario only, flagged; "
                                        "unavailable -> leaflet absent from the optical scene"),
    dict(producer="mtg_vertices.csv / mtg_edges.csv / structure_state.csv",
         consumer="tools/vtc_development_observation.py validate_initial (FILES mtg_vertices.csv, mtg_edges.csv, "
                  "structure_state.csv)",
         rule="frame must be plant_local_mm with metric 3-D base/tip (observed|model_estimated); top-view snapshots "
              "do not satisfy it (3-D unavailable) - reported by the dry-read, not converted"),
    dict(producer="canopy_placement.json instances[].light_ratio (status app_ratio)",
         consumer="P2 light-ratio pointer (ratio-only use)",
         rule="never an absolute PPFD; P2 multiplies nothing already ray-traced"),
    dict(producer="axes.csv (fsp-axes-1 exchange: axis_id, axis_vertex_id, order, parent_axis_id, parent_node_id, "
                  "parent_rank, stage, source_kind, source_ref, segment_index, segment_index__status, truss_count)",
         consumer="tools/fsp_axes.py producer axes adapter (P4); P3 forecast input state",
         rule="segment_index = apical segment of the axis at that capture = truss_count + 1 (MTG A5); "
              "unavailable without a truss registry - never defaulted to 1"),
    dict(producer="trusses.csv (truss_vertex_id, axis_id, axis_vertex_id, parent_rank = above_rank on the bearing "
                  "axis, segment_index = segment the truss closes, first_observed_*, emergence_interval_*)",
         consumer="P4 per-axis truss history / P3 truss nodes",
         rule="registry-recorded only (no detector, no geometry); a truss on S<k> exists only for a registered axis"),
    dict(producer="mtg_vertices.csv segment_index (+ __status) on Axis / CompoundLeaf / Truss / organ rows; "
                  "identity_manifest.csv segment_index",
         consumer="P4 committed state / P3 forecast MTG rows",
         rule="1 + trusses below the node on its axis; status derived; unavailable when rank or registry is missing"),
    dict(producer="(none)", consumer="plants.csv age_days, reserve_gC, mass_source; leaflets.csv dry_mass_g, age_days",
         rule="not produced by P1 (no photograph supplies mass, age or reserve) -> unavailable"),
]


# --------------------------------------------------------------------------------------
# Real-data audit (P1.9)
# --------------------------------------------------------------------------------------


def default_real_request() -> dict[str, Any]:
    tops = sorted((PROJECT_ROOT / "build/roboflow_upload_20261009/top_level_views").glob("dwt_1??_top.jpg"))
    return dict(mode="real", raw_dir="data/raw", plant_glob="dwt_1*",
                real_side_photos="build/roboflow_upload_20261009/side_views",
                detector_weights="build/organ_detector_v4_20260929/kout_full/full_final_all.pt",
                detector_images=[_rel(p) for p in tops], detector_imgsz=512, detector_conf=0.25,
                human_labels=None, side_points=None)


GAPS = [
    ("P1.3_ingest", "time_since_lights_on_min", "lights_on_clock_time is null in env_light_20261010.json"),
    ("P1.3_ingest", "rotation", "no pot orientation mark recorded (azimuth_basis capture_order_assumed)"),
    ("P1.3_ingest", "top_detection", "tomato_top_nonboard does not exist; Roboflow dwt_top_seg_bbox has 0 images"),
    ("P1.3_ingest", "human_top_labels", "no human boxes/masks for dwt_1xx top views"),
    ("P1.4_tracking", "tracks", "needs accepted top masks over >= 2 captures of one plant; dwt_1xx have 1 capture each"),
    ("P1.5_structure_update", "snapshot_values", "no tracked compounds; Plant/Axis rows only"),
    ("P1.6_side_geometry", "side_points", "no human P0..Pm points on the 52 real side photos (side_points.csv absent)"),
    ("P1.6_side_geometry", "direction_labels", "52 real side photos unlabelled (real_eval LABELING_GUIDE pending)"),
    ("P1.7_optical_surfaces", "located_surfaces", op.Q2_UNAVAILABLE),
    ("P1.8_canopy_placement", "slot_id", "plant_id <-> slot table empty (plant registry: 0 of 24 plant_id filled)"),
    ("P1.8_canopy_placement", "yaw", "no pot orientation recorded"),
]


def _gap(c: Mapping[str, str], why: str) -> dict[str, str]:
    return dict(plant_instance_id=c["plant_instance_id"], capture_id=c["capture_id"], segment="P1.3_ingest",
                item="scale", run_status="unavailable", missing_input=why)


def _json(v: Any) -> str:
    return json.dumps(np.round(np.asarray(v, float), 9).tolist())


def _pose_row(c: Mapping[str, str], pose: Any, focal: Mapping[str, float] | None, ref: str) -> dict[str, str]:
    row = {k: UNAVAILABLE for k in s.CAMERA_POSES_COLUMNS}
    row.update(plant_instance_id=c["plant_instance_id"], capture_id=c["capture_id"], view=c["view"],
               image_sha256=c["image_sha256"], pose_status=pose.status if pose.status != "unavailable" else UNAVAILABLE,
               reason=pose.reason or (UNAVAILABLE if pose.status == "validated" else "unspecified"),
               source_ref=ref, evidence="real_photo",
               occluded_sides=";".join(map(str, pose.occluded_sides)) if pose.occluded_sides else UNAVAILABLE)
    if focal:
        row.update(f_px_width_basis=s.fmt(focal["width"], 3), f_px_diagonal_basis=s.fmt(focal["diagonal"], 3))
    if pose.status == "unavailable":
        return row
    e = pose.per_basis[pose.f_basis]
    row.update(f_px=s.fmt(pose.f_px, 3), f_basis=pose.f_basis,
               principal_point_px=_json(pose.pp), principal_point_source=cam.PRINCIPAL_POINT_SOURCE,
               focal_from_rim_px=s.fmt(pose.focal_from_rim_px, 1), focal_from_rim_sd_px=s.fmt(pose.focal_from_rim_sd_px, 1),
               self_check_ratio_residual=s.fmt(e["ratio_residual"], 6), self_check_ratio_sd=s.fmt(e["ratio_sd"], 6),
               self_check_orth_residual=s.fmt(e["orth_residual"], 6), self_check_orth_sd=s.fmt(e["orth_sd"], 6),
               rotation_rim_to_camera=_json(pose.R), translation_mm=_json(pose.t),
               camera_centre_rim_mm=_json(-pose.R.T @ pose.t), camera_distance_mm=s.fmt(pose.distance_mm, 3),
               camera_distance_sd_mm=s.fmt(pose.distance_sd_mm, 3), tilt_deg=s.fmt(pose.tilt_deg, 3))
    return row


def _real_pot_scale(captures: list[dict[str, str]], gaps: list[dict[str, str]]
                    ) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, str]]]:
    """P1 T6 + side rim pose: per-pot rim scale and camera pose on each real top / side capture from the human pot
    records (read-only).

    TOP: rim-plane scale (T6) + camera pose. SIDE (about 25 deg): camera pose from the visible rim; a VERTICAL scale on
    the pot axis is published only when the pose is validated (two-axis self-check). LEVEL: the rim is seen edge-on -
    no square, no pose (unavailable). Fills the capture's scale cells in place; returns frame_transforms rows, a
    per-capture report, and camera_poses rows; appends one ``scale`` gap per capture that stays unscaled."""
    cfg = ft.load_p1_config()
    spec_path = PROJECT_ROOT / ps.POT_SPEC_PATH
    specs = ps.read_pot_spec(spec_path) if spec_path.exists() else None
    files = ps.rim_point_files(PROJECT_ROOT / ps.RIM_POINTS_PATH.parent)
    points = ps.read_rim_points_all(files)
    pval = lambda name: ft.cfg_value(cfg, "pot_scale", name)  # noqa: E731
    frames, reports, poses = [], [], []
    for c in captures:
        pid = c["source_plant_id"]
        if c["view"] == "level":
            gaps.append(_gap(c, "level view: the rim is seen edge-on, no rim square for a scale or a pose; upright-ruler "
                                "scale pending (I.4)"))
            continue
        key = (pid, c["image_sha256"])
        ref = f"{'+'.join(p.name for p in files) or 'rim_points (absent)'}#{pid}|{c['image_sha256'][:12]}"
        spec = ps.spec_for(specs, pid) if specs is not None else None
        try:
            focal = cam.focal_candidates(cam.read_exif(PROJECT_ROOT / c["image_path"]))
            pp = cam.principal_point(c, PROJECT_ROOT)
            focal_reason = ""
        except (cam.CameraError, OSError) as exc:
            focal, pp, focal_reason = None, None, f"photo EXIF / size unreadable: {exc}"
        if specs is None:
            why = (f"{ps.POT_SPEC_PATH.as_posix()} absent - the user's caliper value (square cell, 60 mm outer top edge "
                   "across the flats, 2026-10-12) must be entered there (template build/pot_records_template/)")
        elif key not in points:
            why = (f"no rim edge points for this {c['view']} photo in data/records/pots/rim_points*.csv "
                   f"(tool: python -m tomato3d.cli.rim_points_tool --views {c['view']})")
        else:
            why = ""
        pose = (cam.analyse(points[key], spec, focal=focal, pp=pp, view=c["view"],
                            draws=int(pval("monte_carlo_draws")), seed=int(pval("monte_carlo_seed")),
                            k_sigma=float(pval("pose_self_check_k_sigma")),
                            accept_rel=float(pval("cross_check_accept_rel")), stop_rel=float(pval("cross_check_stop_rel")))
                if not why and focal else cam.PoseResult("unavailable", why or focal_reason))
        poses.append(_pose_row(c, pose, focal, ref))
        if c["view"] == "top":
            if why:
                result = ps.PotScale("unavailable", why)
            else:
                result = ps.derive(points[key], spec, draws=int(pval("monte_carlo_draws")),
                                   seed=int(pval("monte_carlo_seed")), accept_rel=float(pval("cross_check_accept_rel")),
                                   stop_rel=float(pval("cross_check_stop_rel")),
                                   record_ref=f"{ps.RIM_POINTS_PATH.name}#{pid}|{c['image_sha256'][:12]}")
            fields = ps.capture_fields(result)
            c.update({k: v for k, v in fields.items() if k in c})
            frames.append(dict(
                plant_instance_id=c["plant_instance_id"], capture_id=c["capture_id"],
                center_x_px=s.fmt(result.center_px[0], 3) if result.center_px else UNAVAILABLE,
                center_y_px=s.fmt(result.center_px[1], 3) if result.center_px else UNAVAILABLE,
                mm_per_px=fields["mm_per_px"], mm_per_px_sd=fields["mm_per_px_sd"],
                scale_convention=fields["scale_convention"], scale_reference_plane=fields["scale_reference_plane"],
                scale_reference_plane_offset_mm=fields["scale_reference_plane_offset_mm"],
                rim_homography_px_to_mm=fields["rim_homography_px_to_mm"],
                rotation_deg=UNAVAILABLE, scale_status=fields["scale_status"], rotation_status=UNAVAILABLE,
                method="pot_rim_square_homography" if result.status == "solved" else UNAVAILABLE))
            reports.append(dict(
                capture_id=c["capture_id"], plant_id=pid, view="top", status=result.status, reason=result.reason,
                convention=result.convention, mm_per_px=result.mm_per_px, mm_per_px_sd=result.mm_per_px_sd,
                anisotropy=result.anisotropy, side_sigma_px=result.side_sigma_px,
                side_residual_px=result.side_residual_px, scale_sources=result.scale_sources,
                cross_check=result.cross_check, ruler_disagreement=result.ruler_disagreement,
                camera_distance_mm=pose.distance_mm, pose_status=pose.status,
                reference=result.reference, reference_plane=result.reference_plane,
                reference_plane_offset_mm=result.reference_plane_offset_mm,
                plane_bias=ps.PLANE_BIAS.get(result.reference_plane, UNAVAILABLE),
                plane_note=ps.plane_note(result.reference_plane),
                rotation="unavailable: the square rim fixes the axes only up to 90 deg; no orientation mark"))
            if result.status != "solved":
                gaps.append(_gap(c, result.reason))
            continue
        # side view: vertical scale on the pot axis only with a validated pose
        solved = pose.status == "validated" and pose.vertical_mm_per_px is not None
        c.update(scale_status="solved" if solved else UNAVAILABLE,
                 scale_source=f"pot_rim:{spec.ref if spec else ''};{ref};pose" if solved else UNAVAILABLE,
                 mm_per_px=s.fmt(pose.vertical_mm_per_px, 8) if solved else UNAVAILABLE,
                 mm_per_px_sd=s.fmt(pose.vertical_mm_per_px_sd, 8) if solved else UNAVAILABLE,
                 scale_convention="pot_rim_pose_vertical_axis" if solved else UNAVAILABLE,
                 scale_sources="1" if solved else "0",
                 scale_cross_check="none_single_source" if solved else UNAVAILABLE,
                 scale_plane="pot_axis_vertical" if solved else UNAVAILABLE,
                 scale_reference=pose.reference if solved else UNAVAILABLE,
                 scale_reference_plane="pot_rim" if solved else UNAVAILABLE,
                 scale_reference_plane_offset_mm="0" if solved else UNAVAILABLE)
        reports.append(dict(
            capture_id=c["capture_id"], plant_id=pid, view="side", status="solved" if solved else "unavailable",
            reason="" if solved else (pose.reason or why), pose_status=pose.status, f_basis=pose.f_basis,
            vertical_mm_per_px=pose.vertical_mm_per_px, vertical_mm_per_px_sd=pose.vertical_mm_per_px_sd,
            camera_distance_mm=pose.distance_mm, tilt_deg=pose.tilt_deg, ruler_cross_check=pose.cross_check,
            reference=pose.reference, reference_plane=pose.reference_plane, occluded_sides=list(pose.occluded_sides),
            plane_note="vertical scale at the rim centre on the pot axis; parts off the axis or at other heights are at "
                       "other distances (no correction applied)"))
        if not solved:
            gaps.append(_gap(c, why or (f"side view: camera pose {pose.status} ({pose.reason}); a vertical scale needs "
                                        "a validated pose")))
    return frames, reports, poses


def build_real(target: Path, request: Mapping[str, Any]) -> Path:
    w = Writer(target)
    try:
        photos = ingest.discover_raw(PROJECT_ROOT / request["raw_dir"], request.get("plant_glob", "dwt_1*"))
        if not photos:
            raise PackageError(f"no generator_capture.csv under {request['raw_dir']}")
        capture_tz = request.get("capture_tz")
        captures, problems = ingest.real_capture_rows(photos, PROJECT_ROOT, capture_tz)
        if problems:
            raise PackageError("raw photo hash/presence/time problems: " + "; ".join(problems))
        s.check_captures(captures)
        plants = sorted({c["plant_instance_id"] for c in captures})
        segments = [s.SegmentStatus("P1.3_ingest_captures", "executed", "")]
        gaps: list[dict[str, str]] = []
        frames_rows, scale_reports, pose_rows = _real_pot_scale(captures, gaps)
        s.check_captures(captures)
        n_top = sum(c["view"] == "top" for c in captures)
        n_solved = sum(c["scale_status"] == "solved" for c in captures if c["view"] == "top")
        segments.append(s.SegmentStatus(
            "P1.3_pot_rim_scale", "executed" if n_solved == n_top and n_top else "unavailable",
            "" if n_solved == n_top and n_top else
            f"{n_solved} of {n_top} top captures solved; reasons per capture in audit_gaps.csv (item scale)"))
        n_side = sum(c["view"] == "side" for c in captures)
        n_side_solved = sum(c["scale_status"] == "solved" for c in captures if c["view"] == "side")
        n_validated = sum(r["pose_status"] == "validated" for r in pose_rows)
        segments.append(s.SegmentStatus(
            "P1.3_side_rim_pose", "executed" if n_side_solved == n_side and n_side else "unavailable",
            "" if n_side_solved == n_side and n_side else
            f"{n_side_solved} of {n_side} side captures have a vertical scale; {n_validated} of {len(pose_rows)} poses "
            "validated (camera_poses.csv); reasons in audit_gaps.csv"))
        if capture_tz:
            segments.append(s.SegmentStatus("P1.3_capture_timezone", "executed",
                                            f"capture_tz {capture_tz} (user_stated: {request.get('capture_tz_ref', '')})"))
        else:
            segments.append(s.SegmentStatus("P1.3_capture_timezone", "unavailable",
                                            "no --capture-tz stated; device-clock times kept naive"))
            for pid in plants:
                gaps.append(dict(plant_instance_id=pid, capture_id="all", segment="P1.3_ingest", item="capture_tz",
                                 run_status="unavailable",
                                 missing_input="capture timezone not stated by the user (prepare --capture-tz)"))
        obs_rows: list[dict[str, str]] = []
        det_doc: list[dict[str, Any]] = []
        # optional flagged detector proposals on the decoded top JPGs
        weights = request.get("detector_weights")
        images = [PROJECT_ROOT / p for p in request.get("detector_images", [])]
        if weights and images:
            det_doc = ingest.run_detector(images, PROJECT_ROOT / weights, int(request["detector_imgsz"]),
                                          float(request["detector_conf"]))
            cap_of_key, plant_of_key = {}, {}
            for img in images:
                plant = img.name.split("_top")[0]
                cap = next(c["capture_id"] for c in captures if c["plant_instance_id"] == plant and c["view"] == "top")
                cap_of_key[img.name], plant_of_key[img.name] = cap, plant
            obs_rows = ingest.proposal_rows(det_doc, cap_of_key, plant_of_key)
            s.check_observations(obs_rows, "real_photo")
            w.json("observations/detector_proposals.json", dict(
                detector_status=ingest.DETECTOR_STATUS_C6,
                note="decoded JPG copies of the raw HEIC top photos (build/roboflow_upload_20261009/top_level_views); "
                     "proposals only - never tracked, never an area, never an observation",
                images=[dict(key=d["key"], jpg_sha256=d["rgb_sha256"]) for d in det_doc],
                detections=det_doc))
            segments.append(s.SegmentStatus("P1.3_detector_proposals", "executed",
                                            "flagged proposals only (unvalidated_on_boardfree_top)"))
        trackable = ingest.trackable(obs_rows)
        segments.append(s.SegmentStatus("P1.3_observations", "unavailable",
                                        "no accepted top-view masks: no top detector, no human labels"))
        for seg, item, why in GAPS:
            for pid in plants:
                gaps.append(dict(plant_instance_id=pid, capture_id="all", segment=seg, item=item,
                                 run_status="unavailable", missing_input=why))
        for seg in ("P1.4_tracking", "P1.5_structure_update", "P1.6_side_geometry", "P1.7_optical_surfaces",
                    "P1.8_canopy_placement"):
            why = "; ".join(g[2] for g in GAPS if g[0] == seg)
            segments.append(s.SegmentStatus(seg, "unavailable", why))
        assert not trackable
        # MTG A4: registry-driven side-shoot registration only (top views cannot find side shoots)
        registry = PROJECT_ROOT / ax.REGISTRY_PATH
        entries = ax.read_registry(registry) if registry.exists() else []
        if not registry.exists():
            for pid in plants:
                gaps.append(dict(plant_instance_id=pid, capture_id="all", segment="P1.4_axes", item="side_shoot_registry",
                                 run_status="unavailable",
                                 missing_input=f"{ax.REGISTRY_PATH.as_posix()} absent (template: build/side_shoot_registry_template/)"))
        axes_all: list[dict[str, str]] = []
        for pid in plants:
            caps = sorted((c for c in captures if c["plant_instance_id"] == pid),
                          key=lambda c: (c["capture_time"], c["capture_id"]))
            clock = [ax.CaptureClock(c["capture_id"], datetime.fromisoformat(c["capture_time"])
                                     if c["capture_time"] != UNAVAILABLE else None) for c in caps]
            axes_all += ax.axes_rows(pid, pid, clock, entries, {}, "real_photo", "user_stated")
        # MTG A5: registry-driven trusses and segment_index (no truss detector exists)
        truss_path = PROJECT_ROOT / tr.REGISTRY_PATH
        truss_entries = tr.read_registry(truss_path) if truss_path.exists() else None
        if truss_entries is not None:
            tr.check_against_axes(truss_entries, entries, plants)
        else:
            for pid in plants:
                gaps.append(dict(plant_instance_id=pid, capture_id="all", segment="P1.4_trusses", item="truss_registry",
                                 run_status="unavailable",
                                 missing_input=f"{tr.REGISTRY_PATH.as_posix()} absent (template: "
                                               "build/truss_registry_template/); segment_index unavailable"))
        trusses_all: list[dict[str, str]] = []
        clocks: dict[str, list[ax.CaptureClock]] = {}
        for pid in plants:
            caps = sorted((c for c in captures if c["plant_instance_id"] == pid),
                          key=lambda c: (c["capture_time"], c["capture_id"]))
            clocks[pid] = [ax.CaptureClock(c["capture_id"], datetime.fromisoformat(c["capture_time"])
                                           if c["capture_time"] != UNAVAILABLE else None) for c in caps]
            tr.annotate_axes(axes_all, truss_entries, pid, pid, clocks[pid])
            if truss_entries is not None:
                axis_vertex_of = {r["axis"]: r["axis_vertex_id"] for r in axes_all if r["plant_instance_id"] == pid}
                trusses_all += tr.truss_table_rows(pid, pid, clocks[pid], truss_entries, axis_vertex_of,
                                                   "real_photo", "user_stated")
        s.check_axes(axes_all)
        s.check_trusses(trusses_all)
        segments.append(s.SegmentStatus("P1.4_axes", "executed" if registry.exists() else "unavailable",
                                        "" if registry.exists() else "side_shoot_registry.csv absent; M only"))
        segments.append(s.SegmentStatus("P1.4_trusses", "executed" if truss_entries is not None else "unavailable",
                                        "" if truss_entries is not None else
                                        "truss_registry.csv absent; segment_index unavailable"))
        # minimal snapshot: Plant + Axis per plant, everything unavailable with reasons
        mtg, unresolved, state_rows = [], [], []
        top_caps = {c["plant_instance_id"]: c for c in captures if c["view"] == "top"}
        for pid in plants:
            cap = top_caps[pid]
            info = up.CaptureInfo(cap["capture_id"], "image_px", None, None, None, UNAVAILABLE, None, "real_photo",
                                  UNAVAILABLE)
            inp = up.SnapshotInputs(pid, pid, info, [], {}, [], axes_rows=axes_all,
                                    trusses_now=None if truss_entries is None else
                                    tr.known_at(truss_entries, pid, clocks[pid], cap["capture_id"]))
            snap = up.build_snapshot(inp)
            mtg += snap
            unresolved += up.unresolved_rows(snap, "no observation of this plant could be tracked")
            state_rows += up.structure_state_rows(inp, snap)
        s.check_mtg_rows(mtg)
        optical_rows = [op.manifest_row(pid, top_caps[pid]["capture_id"], f"{pid}/C????", "unavailable",
                                        op.Q2_UNAVAILABLE, "none", "real_photo") for pid in plants]
        for r in optical_rows:
            r["vertex_id"] = UNAVAILABLE
            r["compound_id"] = UNAVAILABLE
            r["external_leaflet_id"] = f"{r['plant_instance_id']}|unavailable"
        cfg = ft.load_p1_config()
        slots = cn.load_slots(PROJECT_ROOT / cn.SLOT_TABLE)
        reqs = [cn.InstanceRequest(pid, None, None, UNAVAILABLE, UNAVAILABLE, UNAVAILABLE) for pid in plants]
        placements = cn.place(reqs, slots, cfg)
        w.table("captures.csv", captures, s.CAPTURES_COLUMNS)
        s.check_frame_transforms(frames_rows)
        w.table("frame_transforms.csv", frames_rows, s.FRAME_TRANSFORMS_COLUMNS)
        w.json("pot_rim_scale.json", scale_reports)
        s.check_camera_poses(pose_rows, captures)
        w.table("camera_poses.csv", pose_rows, s.CAMERA_POSES_COLUMNS)
        w.table("observations/observations.csv", obs_rows, s.OBSERVATIONS_COLUMNS)
        w.table("identity_manifest.csv", [], s.IDENTITY_COLUMNS)
        w.table("axes.csv", axes_all, s.AXES_COLUMNS)
        w.table("trusses.csv", trusses_all, s.TRUSSES_COLUMNS)
        w.table("mtg_vertices.csv", mtg, s.MTG_VERTICES_COLUMNS)
        w.table("mtg_edges.csv", [], s.MTG_EDGES_COLUMNS)
        w.table("structure_state.csv", state_rows, s.STRUCTURE_STATE_COLUMNS)
        w.table("unresolved.csv", unresolved, s.UNRESOLVED_COLUMNS)
        w.table("areas.csv", [], s.AREAS_COLUMNS)
        w.table("side_geometry.csv", [], s.SIDE_GEOMETRY_COLUMNS)
        w.table("optical_surface_manifest.csv", optical_rows, s.OPTICAL_MANIFEST_COLUMNS)
        w.table("audit_gaps.csv", gaps, s.AUDIT_GAPS_COLUMNS)
        w.json("canopy_placement.json", cn.placement_document(placements, reqs, cfg,
                                                              sha256_file(PROJECT_ROOT / cn.SLOT_TABLE), "real_photo"))
        side_dir = PROJECT_ROOT / request["real_side_photos"]
        side_files = sorted(side_dir.glob("*.jpg"))
        manifest = _manifest(w, request, segments, evidence="real_photo", extra=dict(
            real_side_photos=dict(folder=request["real_side_photos"], n=len(side_files),
                                  status="referenced; no points, no labels -> side geometry unavailable"),
            completeness=dict(observation_reconstruction_real="unavailable - see audit_gaps.csv",
                              interfaces="captures/MTG/unresolved/optical/canopy files written with reasons",
                              fixture_engineering_path="not part of this package")))
        w.json("p1_manifest.json", manifest)
        return w.publish()
    except Exception:
        w.abort()
        raise


# --------------------------------------------------------------------------------------
# Validate / stale check / P2 dry-read / compare / replay
# --------------------------------------------------------------------------------------


def validate(package: Path) -> list[str]:
    """Every validator over a published package. Returns problems (empty = valid)."""
    problems: list[str] = []
    pkg = Path(package)
    try:
        man = json.loads((pkg / "p1_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"manifest unreadable: {exc}"]
    if man.get("schema_version") != s.P1_SCHEMA_VERSION:
        problems.append(f"schema_version {man.get('schema_version')} != {s.P1_SCHEMA_VERSION}")
    for rel, digest in man["files"].items():
        p = pkg / rel
        if not p.exists():
            problems.append(f"missing file {rel}")
        elif sha256_file(p) != digest:
            problems.append(f"file changed since publish: {rel}")
    if man.get("code_hashes") != code_hashes():
        changed = [k for k, v in code_hashes().items() if man.get("code_hashes", {}).get(k) != v]
        problems.append(f"stale: code/schema changed since this package was built ({', '.join(changed)})")
    evidence = man["evidence"]
    checks = [
        ("captures.csv", None, s.check_captures),
        ("mtg_vertices.csv", None, s.check_mtg_rows),
        ("identity_manifest.csv", None, s.check_identity_rows),
        ("optical_surface_manifest.csv", s.OPTICAL_MANIFEST_COLUMNS, s.check_optical_rows),
    ]
    tables: dict[str, list[dict[str, str]]] = {}
    for name, cols, fn in checks:
        try:
            tables[name] = read_table(pkg / name, cols)
            fn(tables[name])
        except Exception as exc:  # noqa: BLE001 - every failure is reported, none hidden
            problems.append(f"{name}: {exc}")
    truss_rows: list[dict[str, str]] = []
    if (pkg / "trusses.csv").exists():
        try:
            truss_rows = read_table(pkg / "trusses.csv", s.TRUSSES_COLUMNS)
            s.check_trusses(truss_rows)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"trusses.csv: {exc}")
    if (pkg / "axes.csv").exists():
        try:
            axes_rows = read_table(pkg / "axes.csv")  # revision-3 headers still accepted by check_axes
            s.check_axes(axes_rows)
            s.check_axes_coverage(axes_rows, tables.get("mtg_vertices.csv", []), tables.get("identity_manifest.csv", []),
                                  _truss_axis_rows(truss_rows))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"axes.csv: {exc}")
    try:
        obs = read_table(pkg / "observations/observations.csv")
        s.check_observations(obs, evidence)
    except Exception as exc:  # noqa: BLE001
        problems.append(f"observations.csv: {exc}")
    try:
        caps = tables.get("captures.csv", [])
        scale = {r["capture_id"]: r["scale_status"] for r in caps}
        planes = {r["capture_id"]: s.reference_plane_of(r) for r in caps}
        s.check_areas(read_table(pkg / "areas.csv"), scale, planes)  # revision <= 4 headers still accepted
    except Exception as exc:  # noqa: BLE001
        problems.append(f"areas.csv: {exc}")
    if (pkg / "frame_transforms.csv").exists():
        try:
            s.check_frame_transforms(read_table(pkg / "frame_transforms.csv"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"frame_transforms.csv: {exc}")
    if (pkg / "candidates.csv").exists():
        try:
            s.check_candidate_rows(read_table(pkg / "candidates.csv", s.MTG_VERTICES_COLUMNS), "candidates.csv")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"candidates.csv: {exc}")
    for name in ("mtg_vertices.csv", "identity_manifest.csv", "captures.csv", "optical_surface_manifest.csv"):
        for r in tables.get(name, []):
            if evidence == "real_photo" and r.get("evidence") == "synthetic_fixture":
                problems.append(f"{name}: synthetic row inside a real package")
                break
            if evidence == "synthetic_fixture" and r.get("evidence") == "real_photo":
                problems.append(f"{name}: fixture package labels a row real_photo")
                break
    if evidence == "real_photo" and man.get("counts_as_photo_reconstruction") is not True:
        problems.append("real package must declare counts_as_photo_reconstruction")
    if evidence == "synthetic_fixture" and man.get("counts_as_photo_reconstruction") is not False:
        problems.append("fixture package may never count as photo reconstruction")
    # every unavailable snapshot cell has an unresolved row
    try:
        unres = {(r["plant_instance_id"], r["capture_id"], r["vertex_id"], r["attr"])
                 for r in read_table(pkg / "unresolved.csv", s.UNRESOLVED_COLUMNS)}
        for v in tables.get("mtg_vertices.csv", []):
            for a in s.MTG_VALUE_ATTRIBUTES:
                if v[a] == UNAVAILABLE and (v["plant_instance_id"], v["capture_id"], v["vertex_id"], a) not in unres:
                    problems.append(f"unresolved.csv lacks {v['vertex_id']} {a} @ {v['capture_id']}")
                    raise StopIteration
    except StopIteration:
        pass
    except Exception as exc:  # noqa: BLE001
        problems.append(f"unresolved.csv: {exc}")
    for seg in man["run_status"]:
        if seg["run_status"] not in s.RUN_STATUSES:
            problems.append(f"run_status {seg}")
    return problems


def p2_dry_read(package: Path) -> dict[str, Any]:
    """Schema-only read of the package as P2 would consume it. Runs no light."""
    pkg = Path(package)
    doc = json.loads((pkg / "canopy_placement.json").read_text(encoding="utf-8"))
    optical = read_table(pkg / "optical_surface_manifest.csv", s.OPTICAL_MANIFEST_COLUMNS)
    plants_rows, issues = [], []
    by_inst = {i["plant_instance_id"]: i for i in doc["instances"]}
    for inst in doc["instances"]:
        if inst["placement_status"] == "placed" and inst["in_optical_scene"]:
            row = dict(plant_instance_id=inst["plant_instance_id"], source_plant_id=inst["source_plant_id"],
                       **inst["p2_plants_csv"])
            for k in ("tx_mm", "ty_mm", "tz_mm", "yaw_deg"):
                if not isinstance(row[k], (int, float)):
                    issues.append(f"{inst['plant_instance_id']}: {k} not numeric")
            plants_rows.append(row)
    usable = cond = unavailable = 0
    tri_files: dict[str, int] = {}
    for r in optical:
        inst, vid = s.split_external_id(r["external_leaflet_id"])
        if inst not in by_inst:
            issues.append(f"{r['external_leaflet_id']}: instance not in canopy_placement.json")
        if r["optical_readiness"] == "unavailable":
            unavailable += 1
            continue
        if r["optical_readiness"] == "supported":
            usable += 1
        else:
            cond += 1
        f = pkg / r["surface_file"]
        if not f.exists() or sha256_file(f) != r["surface_sha256"]:
            issues.append(f"{r['surface_file']}: missing or hash mismatch")
            continue
        if r["surface_file"] not in tri_files:
            tri = read_table(f, s.OPTICAL_TRIANGLES_COLUMNS)
            counts: dict[str, int] = {}
            for t in tri:
                if t["frame"] != "plant_local_mm":
                    issues.append(f"{r['surface_file']}: frame {t['frame']}")
                    break
                counts[t["external_leaflet_id"]] = counts.get(t["external_leaflet_id"], 0) + 1
            tri_files[r["surface_file"]] = 0
            for ext, n in counts.items():
                if ext == r["external_leaflet_id"] and str(n) != r["n_triangles"]:
                    issues.append(f"{ext}: triangle count {n} != manifest {r['n_triangles']}")
    mtg = read_table(pkg / "mtg_vertices.csv", s.MTG_VERTICES_COLUMNS)
    axes_doc: dict[str, Any] = dict(present=(pkg / "axes.csv").exists())
    if axes_doc["present"]:  # MTG A4/A5 exchange (P4 fsp-axes-1 adapter, P3 input state)
        axes_rows = read_table(pkg / "axes.csv")  # revision 3 lacks the A5 columns -> read as unavailable
        trusses = read_table(pkg / "trusses.csv", s.TRUSSES_COLUMNS) if (pkg / "trusses.csv").exists() else []
        for r in axes_rows:
            if r.get("segment_index", UNAVAILABLE) != UNAVAILABLE and                     int(r["segment_index"]) != int(r["truss_count"]) + 1:
                issues.append(f"axes.csv {r['plant_instance_id']} {r['capture_id']} {r['axis']}: segment/truss mismatch")
        axes_doc.update(
            axes_rows=len(axes_rows), side_axes=sorted({r["axis"] for r in axes_rows if r["axis"] != "M"}),
            axes_rows_with_segment_index=sum(r.get("segment_index", UNAVAILABLE) != UNAVAILABLE for r in axes_rows),
            truss_rows=len(trusses), trusses=sorted({(r["axis_id"], r["truss_vertex_id"]) for r in trusses}),
            vertices_with_segment_index=sum(v["segment_index"] != UNAVAILABLE for v in mtg),
            max_segment_index=max((int(v["segment_index"]) for v in mtg if v["segment_index"] != UNAVAILABLE),
                                  default=None))
    v3_ready = [v for v in mtg if v["frame"] == "plant_local_mm" and v["base_xyz_mm__status"] in
                ("observed", "model_estimated") and v["tip_xyz_mm__status"] in ("observed", "model_estimated")]
    return dict(
        consumer="P2 dry-read (schema only; no light run)",
        plants_csv_rows=plants_rows,
        axes_and_trusses=axes_doc,
        leaflets_supported=usable, leaflets_conditional=cond, leaflets_unavailable=unavailable,
        v3_stage2_boundary=dict(
            files_present=all((pkg / f).exists() for f in ("mtg_vertices.csv", "mtg_edges.csv", "structure_state.csv")),
            rows_with_metric_3d_observed_or_model_estimated=len(v3_ready), rows_total=len(mtg),
            missing_supplement=["initial_state.csv", "initial_controls.json", "observation_manifest.json"],
            verdict="not consumable as an initial state: no photo-derived metric 3-D, and the physiology "
                    "supplement (mass, age, reserve, apex state) is not a P1 product"),
        issues=issues, ok=not issues)


def compare_observation(package: Path) -> list[dict[str, str]]:
    """Fixture: observation-derived values vs truth for the same capture and definition."""
    pkg = Path(package)
    if not (pkg / "truth" / "truth_areas.csv").exists():
        return []
    join = read_table(pkg / "observations/truth_join.csv", s.TRUTH_JOIN_COLUMNS)
    ident = read_table(pkg / "identity_manifest.csv", s.IDENTITY_COLUMNS)
    obs = {(r["plant_instance_id"], r["capture_id"], r["obs_id"]): r
           for r in read_table(pkg / "observations/observations.csv", s.OBSERVATIONS_COLUMNS)}
    truth_areas = read_table(pkg / "truth/truth_areas.csv", s.AREAS_COLUMNS)
    vis_truth: dict[tuple[str, str, str], int] = {}
    for r in truth_areas:
        key = (r["plant_instance_id"], r["capture_id"], r["compound_id"])
        vis_truth[key] = vis_truth.get(key, 0) + int(r["visible_projected_area_px2"])
    truth_mtg = {(r["plant_instance_id"], r["capture_id"], r["vertex_id"]): r
                 for r in read_table(pkg / "truth/truth_mtg_vertices.csv", s.MTG_VERTICES_COLUMNS)}
    obs_mtg = {(r["plant_instance_id"], r["capture_id"], r["vertex_id"]): r
               for r in read_table(pkg / "mtg_vertices.csv", s.MTG_VERTICES_COLUMNS)}
    track_of = {(r["plant_instance_id"], r["capture_id"], r["obs_id"]): r for r in ident
                if r["organ_class"] == "compound_leaf"}
    out = []
    for j in join:
        key = (j["plant_instance_id"], j["capture_id"], j["obs_id"])
        o = obs.get(key)
        if o is None or o["obs_class"] != "compound_leaf" or j["truth_vertex_id"].count("/") != 1:
            continue
        idr = track_of.get(key)
        track = idr["organ_id"] if idr else UNAVAILABLE
        tv = vis_truth.get((j["plant_instance_id"], j["capture_id"], j["truth_vertex_id"]))
        tm = truth_mtg.get((j["plant_instance_id"], j["capture_id"], j["truth_vertex_id"]))
        om = obs_mtg.get((j["plant_instance_id"], j["capture_id"], track))
        az_err = UNAVAILABLE
        if tm and om and om["blade_azimuth_deg"] != UNAVAILABLE and tm["blade_azimuth_deg"] != UNAVAILABLE:
            from tomato3d.state.geometry import wrap_deg
            az_err = s.fmt(wrap_deg(float(om["blade_azimuth_deg"]) - float(tm["blade_azimuth_deg"])), 3)
        out.append(dict(plant_instance_id=j["plant_instance_id"], capture_id=j["capture_id"], obs_id=j["obs_id"],
                        truth_vertex_id=j["truth_vertex_id"], track_id=track,
                        track_state=idr["track_state"] if idr else UNAVAILABLE,
                        visible_area_px2_observed=o["area_px2"],
                        visible_area_px2_truth=str(tv) if tv is not None else UNAVAILABLE,
                        blade_azimuth_top_proxy_minus_truth_deg=az_err,
                        definition_note="observed blade azimuth uses the top-mask proximal->distal proxy; truth uses "
                                        "P1->terminal tip (A2 12.4) - different definitions, error reported, not fitted"))
    return out


COMPARE_COLUMNS = ("plant_instance_id", "capture_id", "obs_id", "truth_vertex_id", "track_id", "track_state",
                   "visible_area_px2_observed", "visible_area_px2_truth", "blade_azimuth_top_proxy_minus_truth_deg",
                   "definition_note")


def replay(package: Path) -> dict[str, Any]:
    """Re-run the package's request into a temporary folder and compare every file hash
    (except the manifest, whose timestamp differs). Refuses if an input changed."""
    pkg = Path(package)
    man = json.loads((pkg / "p1_manifest.json").read_text(encoding="utf-8"))
    request = man["request"]
    now = _input_snapshot(request)
    changed_inputs = sorted(k for k in set(now) | set(man["input_snapshot"]) if now.get(k) != man["input_snapshot"].get(k))
    if changed_inputs:
        return dict(ok=False, reason="input snapshot changed", changed_inputs=changed_inputs)
    with tempfile.TemporaryDirectory(dir=pkg.parent) as tmp:
        target = Path(tmp) / "replay"
        (build_fixture if request["mode"] == "fixture" else build_real)(target, request)
        new = json.loads((target / "p1_manifest.json").read_text(encoding="utf-8"))["files"]
    diff = sorted(k for k in set(new) | set(man["files"]) if new.get(k) != man["files"].get(k))
    return dict(ok=not diff, differing_files=diff, n_files=len(man["files"]))
