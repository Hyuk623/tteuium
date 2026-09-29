"""CLI for the approved leaf-light / view-count experiment. Use --help."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tomato3d.config import get_settings
from tomato3d.logging_setup import configure_logging
from tools.leaf_light.common import (BUILD, StudyError, freeze, load_protocol, output_dir,
                                    read_json, template, variants, write_json, write_rows)


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Generate a draft protocol and empty measurement template")
    init.add_argument("--out", type=Path, required=True)
    lock = sub.add_parser("freeze", help="Freeze reviewed design before opening evaluation measurements")
    lock.add_argument("--draft", type=Path, required=True)
    lock.add_argument("--out", type=Path, required=True)
    select = sub.add_parser("selections", help="Print the preregistered image subset schedule")
    select.add_argument("--protocol", type=Path, required=True)
    prepare = sub.add_parser("prepare", help="Read originals and solve each ChArUco camera pose")
    prepare.add_argument("--manifest", type=Path, required=True)
    prepare.add_argument("--intrinsics", type=Path, required=True)
    prepare.add_argument("--protocol", type=Path, required=True)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--phone-profile", type=Path, default=None)
    phone = sub.add_parser("phone-normalize", help="Prepare original smartphone RGB photographs for calibration or capture")
    phone.add_argument("--images", type=Path, required=True)
    phone.add_argument("--camera-id", required=True)
    phone.add_argument("--reference-profile", type=Path, default=None)
    phone.add_argument("--out", type=Path, required=True)
    cvat = sub.add_parser("import-cvat", help="Convert visible CVAT points/contours to research CSV")
    cvat.add_argument("--xml", type=Path, required=True)
    cvat.add_argument("--capture", type=Path, required=True)
    cvat.add_argument("--out", type=Path, required=True)
    cvat.add_argument("--variant", default=None)
    annotation_template = sub.add_parser("annotation-template", help="List selected images and required independent annotation packages")
    annotation_template.add_argument("--capture", type=Path, required=True)
    annotation_template.add_argument("--out", type=Path, required=True)
    recon = sub.add_parser("reconstruct", help="Reconstruct every subset independently from image annotations")
    for name in ("capture", "protocol", "out"):
        recon.add_argument(f"--{name}", type=Path, required=True)
    for name in ("points", "contours", "annotation-sets"):
        recon.add_argument(f"--{name}", type=Path, default=None)
    recon.add_argument("--worklog", type=Path, default=None)
    run = sub.add_parser("run", help="Predict finite-area sensor PPFD and leaf light for all subsets")
    for name in ("reconstruction", "scene", "readings", "protocol", "out"):
        run.add_argument(f"--{name}", type=Path, required=True)
    run.add_argument("--session-slot", required=True)
    evaluate = sub.add_parser("evaluate", help="Score all planned sessions and generate the research report")
    evaluate.add_argument("--protocol", type=Path, required=True)
    evaluate.add_argument("--runs", type=Path, nargs="*", default=[])
    evaluate.add_argument("--out", type=Path, required=True)
    batch = sub.add_parser("batch", help="Run reconstruction, light, and evaluation for explicitly listed jobs")
    batch.add_argument("--jobs", type=Path, required=True)
    batch.add_argument("--protocol", type=Path, required=True)
    batch.add_argument("--out", type=Path, required=True)
    demo = sub.add_parser("demo", help="Run an explicitly SYNTHETIC integration example, not plant validation")
    demo.add_argument("--protocol", type=Path, required=True)
    demo.add_argument("--out", type=Path, required=True)
    for command in ("export-mesh", "view-mesh"):
        mesh = sub.add_parser(command, help="Export PLY / open optional Open3D mesh inspector")
        mesh.add_argument("--geometry", type=Path, required=True)
        mesh.add_argument("--variant", required=True)
        if command == "export-mesh":
            mesh.add_argument("--out", type=Path, required=True)
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    configure_logging(get_settings().log_level)
    try:
        if args.command == "init":
            from tools.leaf_light.optics import READING_COLUMNS
            folder = output_dir(args.out)
            p = template(read_json(get_settings().capture_config_path))
            write_json(folder / "protocol.draft.json", p)
            write_rows(folder / "ppfd_readings.template.csv", [], READING_COLUMNS)
            write_rows(folder / "worklog.template.csv", [dict(variant_id=v["variant_id"],capture_seconds=None,
                annotation_seconds=None,correction_seconds=None,scope="independent_subset",operator="") for v in variants(p)],
                ("variant_id","capture_seconds","annotation_seconds","correction_seconds","scope","operator"))
            write_json(folder / "jobs.template.json", {"jobs": [], "note": "Supply capture, points, contours, scene, readings, session_slot paths; paths relative to this JSON."})
            print(f"Draft and empty templates: {folder}")
        elif args.command == "freeze":
            freeze(args.draft, args.out)
        elif args.command == "selections":
            print(json.dumps(variants(load_protocol(args.protocol)[0]), indent=2))
        elif args.command == "prepare":
            from tools.leaf_light.capture import prepare
            prepare(args.manifest, args.intrinsics, args.protocol, args.out, args.phone_profile)
        elif args.command == "phone-normalize":
            from tools.leaf_light.phone import normalize
            normalize(args.images, args.camera_id, args.out, args.reference_profile)
        elif args.command == "import-cvat":
            from tools.leaf_light.annotations import import_cvat
            import_cvat(args.xml, args.capture, args.out, args.variant)
        elif args.command == "annotation-template":
            capture = read_json(args.capture)
            folder = output_dir(args.out)
            write_json(folder / "annotation_sets.draft.json", {"variants": [dict(
                variant_id=v["variant_id"], source="REVIEW_REQUIRED", operator="",
                reviewed_image_files=v["image_files"], points=f"{v['variant_id']}/points.csv",
                contours=f"{v['variant_id']}/contours.csv") for v in capture["variants"]]})
        elif args.command == "reconstruct":
            from tools.leaf_light.reconstruction import reconstruct
            reconstruct(args.capture, args.points, args.contours, args.protocol, args.out, args.worklog, args.annotation_sets)
        elif args.command == "run":
            from tools.leaf_light.optics import run
            run(args.reconstruction, args.scene, args.readings, args.protocol, args.session_slot, args.out)
        elif args.command == "evaluate":
            from tools.leaf_light.evaluation import evaluate
            evaluate(args.protocol, args.runs, args.out)
        elif args.command in ("export-mesh", "view-mesh"):
            from tools.leaf_light import mesh
            if args.command == "export-mesh":
                mesh.export(args.geometry, args.variant, args.out)
            else:
                mesh.view(args.geometry, args.variant)
        elif args.command == "demo":
            from tools.leaf_light.synthetic import make_inputs
            from tools.leaf_light.reconstruction import reconstruct
            from tools.leaf_light.optics import run
            from tools.leaf_light.evaluation import evaluate
            root = output_dir(args.out)
            inputs = root / "synthetic_inputs"
            make_inputs(args.protocol, inputs)
            reconstruct(inputs / "capture.json", inputs / "points.csv", inputs / "contours.csv", args.protocol, root / "geometry")
            run(root / "geometry/reconstruction.json", inputs / "scene.json", inputs / "readings.csv", args.protocol,
                load_protocol(args.protocol)[0]["session_slots"][0], root / "light")
            evaluate(args.protocol, [root / "light/run.json"], root / "evaluation")
            print(f"SYNTHETIC ONLY: {root / 'evaluation/report.html'}")
        elif args.command == "batch":
            from tools.leaf_light.reconstruction import reconstruct
            from tools.leaf_light.optics import run
            from tools.leaf_light.evaluation import evaluate
            jobs = read_json(args.jobs)["jobs"]
            if not jobs:
                raise StudyError("No jobs supplied; no measurements will be invented")
            root = output_dir(args.out)
            runs = []
            for index, job in enumerate(jobs):
                resolve = lambda key: (args.jobs.parent / job[key]).resolve()
                recon_dir, run_dir = root / f"job_{index:03d}_geometry", root / f"job_{index:03d}_light"
                reconstruct(resolve("capture"), resolve("points") if job.get("points") else None,
                            resolve("contours") if job.get("contours") else None, args.protocol, recon_dir,
                            resolve("worklog") if job.get("worklog") else None,
                            resolve("annotation_sets") if job.get("annotation_sets") else None)
                run(recon_dir / "reconstruction.json", resolve("scene"), resolve("readings"),
                    args.protocol, job["session_slot"], run_dir)
                runs.append(run_dir / "run.json")
            evaluate(args.protocol, runs, root / "evaluation")
        return 0
    except (ValueError, OSError, KeyError, ImportError) as exc:
        print(f"Study error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
