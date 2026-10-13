"""Render jobs: export on the local PC, render RGB elsewhere (Kaggle GPU), finalise locally.

A job is ``<scene_dir>/render_job/`` with ``job.json`` (scene parameters, per-view render-space
camera, output names) and ``parts.npz`` (mesh arrays). Only the undistorted render-space canvas
is rendered remotely; the distortion warp and post-processing run locally with the same map as
the masks, so RGB and masks stay pixel-aligned.

Remote entry point (needs only bpy, numpy, opencv and this package)::

    python -m tomato3d.synth.render_remote --jobs <dir with scene_*/render_job> --out <dir> --device GPU
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

JOB_SCHEMA = "synth-render-job-1"


def export_job(scene: dict[str, Any], views: list[dict[str, Any]], *, samples: int, backdrop_distance_mm: float,
               pot_center_mm: np.ndarray, board_texture: Path, look: dict[str, float] | None = None) -> Path:
    """Write ``render_job/`` for one scene. ``views``: dicts with name, K_render, size, R, t."""
    jdir = Path(scene["scene_dir"]) / "render_job"
    jdir.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {}
    parts_meta = []
    tex_dir = jdir / "textures"
    for i, p in enumerate(scene["parts"]):
        material = dict(p.get("material", {}))
        if material.get("kind") == "leaf_tex":           # ship the texture with the job, relative path
            src = Path(material["texture"])
            tex_dir.mkdir(exist_ok=True)
            dst = tex_dir / src.name
            if not dst.exists():
                dst.write_bytes(src.read_bytes())
            h_src = src.with_name(src.stem + "_h.png")
            if h_src.exists() and not (tex_dir / h_src.name).exists():
                (tex_dir / h_src.name).write_bytes(h_src.read_bytes())
            material["texture"] = f"textures/{src.name}"
        arrays[f"v{i}"] = np.asarray(p["vertices"], np.float32)
        arrays[f"f{i}"] = np.asarray(p["faces"], np.int32)
        if p.get("uv") is not None:
            arrays[f"uv{i}"] = np.asarray(p["uv"], np.float32)
        parts_meta.append(dict(name=p["name"], organ=p["organ"], material=material,
                               has_uv=p.get("uv") is not None))
    np.savez_compressed(jdir / "parts.npz", **arrays)
    tex = jdir / "board_texture.png"
    tex.write_bytes(Path(board_texture).read_bytes())
    job = dict(schema=JOB_SCHEMA, scene_id=scene["scene_id"], seed=scene["seed"], samples=int(samples),
               backdrop_distance_mm=float(backdrop_distance_mm), pot_center_mm=np.asarray(pot_center_mm).tolist(),
               scene_params=scene["scene_params"], parts=parts_meta, look=look or {},
               views=[dict(name=v["name"], K_render=np.asarray(v["K_render"]).tolist(), size=list(v["size"]),
                           R=np.asarray(v["R"]).tolist(), t=np.asarray(v["t"]).tolist()) for v in views])
    (jdir / "job.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    return jdir


def load_parts(jdir: Path, job: dict[str, Any]) -> list[dict[str, Any]]:
    data = np.load(Path(jdir) / "parts.npz")
    parts = []
    for i, meta in enumerate(job["parts"]):
        material = dict(meta["material"])
        if material.get("kind") == "leaf_tex":
            material["texture"] = str((Path(jdir) / material["texture"]).resolve())
        parts.append(dict(name=meta["name"], organ=meta["organ"], material=material,
                          vertices=data[f"v{i}"].astype(np.float64), faces=data[f"f{i}"],
                          uv=data[f"uv{i}"] if meta["has_uv"] else None))
    return parts


def render_jobs(jobs_root: Path, out_root: Path, device: str) -> list[dict[str, Any]]:
    """Render every job under ``jobs_root``; canvases go to ``out_root/<scene>/<view>.png``.

    Resumable: views whose canvas already exists are skipped.
    """
    from tomato3d.synth import render_blender as rb

    log = []
    for job_path in sorted(Path(jobs_root).rglob("render_job/job.json")):
        jdir = job_path.parent
        job = json.loads(job_path.read_text(encoding="utf-8"))
        sdir = Path(out_root) / job["scene_id"]
        todo = [v for v in job["views"] if not (sdir / f"{v['name']}.png").exists()]
        if not todo:
            continue
        sdir.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        rb.build_scene(load_parts(jdir, job), job["scene_params"], (jdir / "board_texture.png").resolve(),
                       samples=job["samples"], backdrop_distance_mm=job["backdrop_distance_mm"],
                       pot_center_mm=np.asarray(job["pot_center_mm"]), device=device, look=job.get("look"))
        for v in todo:
            rb.render_view(np.asarray(v["K_render"]), tuple(v["size"]), np.asarray(v["R"]), np.asarray(v["t"]),
                           sdir / f"{v['name']}.png")
        entry = dict(scene_id=job["scene_id"], views=len(todo), seconds=round(time.time() - t0, 1), device=device)
        log.append(entry)
        print(json.dumps(entry), flush=True)
    return log


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", choices=("CPU", "GPU"), default="GPU")
    args = ap.parse_args(argv)
    if args.device == "GPU":
        from tomato3d.synth import render_blender as rb

        print("cycles device:", rb.enable_gpu(), flush=True)
    log = render_jobs(Path(args.jobs), Path(args.out), args.device)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "render_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
