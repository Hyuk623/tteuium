"""Rebuild the compact P1 test fixture from existing generator outputs (run from the project root).

    python -X utf8 tests/fixtures/p1/build_fixture.py

Copies, never regenerates: two O-mature top-view scenes and one R.1 side-view scene. Only the
contours a scene uses are kept; ``contour_index`` values are remapped to the reduced library and
the remap is recorded in ``SOURCES.json`` with the sha256 of every source file.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
O_CELL = ROOT / "build/synthetic_dwarf_tomato_20261008_07/O-mature"
SIDE = ROOT / "build/sideprop_20261009_01"
TOP_VIEW = "00_dwt_t1_20261002_27"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reduce_cell(cell: Path, scenes: list[str], out_cell: Path, sources: dict) -> None:
    lib = json.loads((cell / "leaflet_contours.json").read_text(encoding="utf-8"))
    used: list[int] = []
    graphs = {}
    for scene in scenes:
        graph = json.loads((cell / "scenes" / scene / "plant_graph.json").read_text(encoding="utf-8"))
        graphs[scene] = graph
        for interior in graph["interiors"].values():
            for leaf in interior["leaflets"]:
                if leaf["contour_index"] not in used:
                    used.append(leaf["contour_index"])
    remap = {old: new for new, old in enumerate(sorted(used))}
    out_cell.mkdir(parents=True, exist_ok=True)
    (out_cell / "leaflet_contours.json").write_text(json.dumps(
        {"origin": "reduced copy for tests", "contours": [lib["contours"][i] for i in sorted(used)]}),
        encoding="utf-8")
    # full generator config: the P1 completion adapter samples from its declared ranges
    shutil.copyfile(cell / "generator_config.json", out_cell / "generator_config.json")
    sources[out_cell.name] = {
        "source_cell": cell.relative_to(ROOT).as_posix(),
        "leaflet_contours_sha256": sha(cell / "leaflet_contours.json"),
        "generator_config_sha256": sha(cell / "generator_config.json"),
        "contour_index_remap": {str(k): v for k, v in remap.items()},
        "scenes": {},
    }
    for scene, graph in graphs.items():
        for interior in graph["interiors"].values():
            for leaf in interior["leaflets"]:
                leaf["contour_index"] = remap[leaf["contour_index"]]
        sdir = out_cell / "scenes" / scene
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "plant_graph.json").write_text(json.dumps(graph), encoding="utf-8")
        index = json.loads((cell / "scenes" / scene / "leaflet_index.json").read_text(encoding="utf-8"))
        for entry in index.values():
            entry["contour_index"] = remap[entry["contour_index"]]
            entry.pop("texture", None)
        (sdir / "leaflet_index.json").write_text(json.dumps(index), encoding="utf-8")
        sources[out_cell.name]["scenes"][scene] = {
            "plant_graph_sha256": sha(cell / "scenes" / scene / "plant_graph.json")}


def main() -> None:
    sources: dict = {}
    reduce_cell(O_CELL, ["scene_0000", "scene_0001"], OUT / "O-mature", sources)
    vdir = OUT / "O-mature/scenes/scene_0000/views" / TOP_VIEW
    vdir.mkdir(parents=True, exist_ok=True)
    src_view = O_CELL / "scenes/scene_0000/views" / TOP_VIEW
    shutil.copyfile(src_view / "visible_mask.png", vdir / "visible_mask.png")
    sources["O-mature"]["top_view"] = {"view": TOP_VIEW, "visible_mask_sha256": sha(src_view / "visible_mask.png")}
    reduce_cell(SIDE, ["scene_0000"], OUT / "sideprop", sources)
    job = json.loads((SIDE / "scenes/scene_0000/render_job/job.json").read_text(encoding="utf-8"))
    sdir = OUT / "sideprop/scenes/scene_0000"
    (sdir / "render_job").mkdir(parents=True, exist_ok=True)
    (sdir / "render_job/job.json").write_text(json.dumps(
        {"views": [{k: v[k] for k in ("name", "K_render", "size", "R", "t")} for v in job["views"]]}),
        encoding="utf-8")
    for view in sorted((SIDE / "scenes/scene_0000/views").iterdir()):
        (sdir / "views" / view.name).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(view / "labels.json", sdir / "views" / view.name / "labels.json")
    sources["sideprop"]["render_job_sha256"] = sha(SIDE / "scenes/scene_0000/render_job/job.json")
    (OUT / "SOURCES.json").write_text(json.dumps(sources, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
