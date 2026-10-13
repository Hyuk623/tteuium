"""P1 entry point: photos -> current plant state -> canopy placement.

    python -m tomato3d.cli.run_p1 inventory  [--out build/p1_inventory.json]
    python -m tomato3d.cli.run_p1 prepare    --mode fixture|fixture-sideshoot|fixture-truss|real --out build/p1_state_<YYYYMMDD>_<nn> [--request r.json]
                                             [--capture-tz Asia/Seoul --capture-tz-ref "<user statement>"]
    python -m tomato3d.cli.run_p1 run        --package build/p1_state_<YYYYMMDD>_<nn>
    python -m tomato3d.cli.run_p1 collect    --package build/p1_state_<YYYYMMDD>_<nn>
    python -m tomato3d.cli.run_p1 compare-observation --package ... [--out compare.csv]
    python -m tomato3d.cli.run_p1 replay     --package ...
    python -m tomato3d.cli.run_p1 side-validate --out build/p1_side_validation_<YYYYMMDD>

``prepare`` freezes the request and the input snapshot (sha256 of every input) in
``p1_request.json``; ``run`` builds the package from it into a staging folder and publishes it in
one move; ``collect`` validates the package, refuses stale outputs (code or schema hash changed
since the build) and runs the P2 dry-read (schema only, no light); ``replay`` rebuilds from the
frozen request and compares every file hash.

Exit codes: 0 success (every segment executed, or a complete fixture run); 1 the package does not
validate / is stale / replay differs / a segment failed; 2 a usage or input error (bad request,
changed inputs, existing package); 3 the package is valid but PARTIAL - at least one segment is
``unavailable`` (e.g. the real-data audit today). A partial run is never reported as success.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tomato3d.io.tables import write_table
from tomato3d.logging_setup import configure_logging
from tomato3d.state import package as pk

EXIT_OK, EXIT_FAIL, EXIT_INPUT, EXIT_PARTIAL = 0, 1, 2, 3


def _inventory() -> dict:
    """Render runs and real inputs actually present on disk (counts measured, not recalled)."""
    root = pk.PROJECT_ROOT
    runs = {}
    for run in sorted((root / "build").glob("synthetic_dwarf_tomato_*")) + [root / "build/sideprop_20261009_01"]:
        cells = {}
        for scenes in sorted(run.rglob("scenes")):
            if not scenes.is_dir() or "scratch" in scenes.parts:
                continue
            scene_dirs = [d for d in scenes.iterdir() if d.is_dir()]
            views = [v for d in scene_dirs for v in (d / "views").glob("*") if v.is_dir()]
            cells[scenes.parent.relative_to(run).as_posix() or "."] = dict(
                scenes=len(scene_dirs), done=sum((d / "DONE").exists() for d in scene_dirs), views=len(views),
                rgb=sum((v / "rgb.png").exists() for v in views))
        runs[run.relative_to(root).as_posix()] = cells
    raw = sorted((root / "data/raw").glob("dwt_1*/*/generator_capture.csv"))
    return dict(render_runs=runs, real_sessions=[p.parent.relative_to(root).as_posix() for p in raw],
                real_photos=sum(len(list(p.parent.glob("*.heic"))) for p in raw))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_p1", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="op", required=True)
    p = sub.add_parser("inventory", help="count render runs and real inputs on disk")
    p.add_argument("--out", type=Path)
    p = sub.add_parser("prepare", help="freeze a request + input snapshot into a new run folder")
    p.add_argument("--mode", choices=("fixture", "fixture-sideshoot", "fixture-truss", "real"), required=True,
                   help="fixture-sideshoot = MTG A4 synthetic plant with a substem and an axis_shoot; "
                        "fixture-truss = the same plant with registry trusses on M and S1 (MTG A5 segment_index)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--request", type=Path, help="JSON request overriding the built-in default for --mode")
    p.add_argument("--capture-tz", help="real mode: IANA timezone of the camera clock, as stated by the user "
                                        "(e.g. Asia/Seoul). Absent = times stay naive; never assumed")
    p.add_argument("--capture-tz-ref", default="", help="where the user stated the timezone (quoted in the manifest)")
    for name in ("run", "collect", "replay"):
        p = sub.add_parser(name)
        p.add_argument("--package", type=Path, required=True)
    p = sub.add_parser("side-validate", help="P1.6: side geometry vs R.1 truth over finalized scenes")
    p.add_argument("--scenes", type=Path, default=Path("build/sideprop_20261009_01/scenes"))
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("compare-observation", help="observation-derived vs truth (fixture) at matching captures")
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    configure_logging()

    if args.op == "inventory":
        inv = _inventory()
        text = json.dumps(inv, indent=1)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return EXIT_OK

    if args.op == "prepare":
        if args.out.exists() and any(args.out.iterdir()):
            print(f"refused: {args.out} exists and is not empty", file=sys.stderr)
            return EXIT_INPUT
        if args.request is not None:
            request = json.loads(args.request.read_text(encoding="utf-8"))
            if request.get("mode") != args.mode.split("-")[0]:
                print(f"refused: request mode {request.get('mode')!r} != --mode {args.mode}", file=sys.stderr)
                return EXIT_INPUT
        else:
            request = {"fixture": pk.default_fixture_request, "fixture-sideshoot": pk.default_sideshoot_request,
                       "fixture-truss": pk.default_truss_request,
                       "real": pk.default_real_request}[args.mode]()
        if args.capture_tz is not None:
            if args.mode != "real":
                print("refused: --capture-tz applies to real photos only (fixtures carry a declared clock)",
                      file=sys.stderr)
                return EXIT_INPUT
            try:
                pk.s.parse_capture_tz(args.capture_tz)
            except pk.s.P1SchemaError as exc:
                print(f"refused: {exc}", file=sys.stderr)
                return EXIT_INPUT
            if not args.capture_tz_ref:
                print("refused: --capture-tz needs --capture-tz-ref (the user's statement)", file=sys.stderr)
                return EXIT_INPUT
            request = dict(request, capture_tz=args.capture_tz, capture_tz_ref=args.capture_tz_ref)
        args.out.mkdir(parents=True, exist_ok=True)
        doc = dict(request=request, input_snapshot=pk._input_snapshot(request), code_hashes=pk.code_hashes(),
                   code_version=pk.code_version(), schema_version=pk.s.P1_SCHEMA_VERSION)
        (args.out / "p1_request.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"prepared {args.out} ({args.mode}, {len(doc['input_snapshot'])} input files hashed)")
        return EXIT_OK

    if args.op == "side-validate":
        return _side_validate(args.scenes, args.out)

    pkg: Path = args.package
    if args.op == "run":
        req_path = pkg / "p1_request.json"
        if not req_path.exists():
            print(f"refused: {req_path} missing - run `prepare` first", file=sys.stderr)
            return EXIT_INPUT
        doc = json.loads(req_path.read_text(encoding="utf-8"))
        now = pk._input_snapshot(doc["request"])
        changed = sorted(k for k in set(now) | set(doc["input_snapshot"]) if now.get(k) != doc["input_snapshot"].get(k))
        if changed:
            print(f"refused: inputs changed since prepare: {changed[:5]}", file=sys.stderr)
            return EXIT_INPUT
        try:
            builder = pk.build_fixture if doc["request"]["mode"] == "fixture" else pk.build_real
            builder(pkg, doc["request"])
        except pk.PackageError as exc:
            print(f"failed: {exc}", file=sys.stderr)
            return EXIT_FAIL
        print(f"published {pkg}")
        return _collect(pkg)

    if args.op == "collect":
        return _collect(pkg)

    if args.op == "compare-observation":
        rows = pk.compare_observation(pkg)
        if not rows:
            print("compare-observation: unavailable (no truth in this package: real photos have no truth; a later "
                  "observed package is compared through its own P1 observations, never through a prediction)")
            return EXIT_OK
        out = args.out or (pkg.parent / f"{pkg.name}_compare_observation.csv")
        write_table(out, rows, pk.COMPARE_COLUMNS)
        exact = sum(r["visible_area_px2_observed"] == r["visible_area_px2_truth"] for r in rows)
        print(f"compare-observation: {len(rows)} compound observations, visible area equal to truth in {exact}; "
              f"written {out}")
        return EXIT_OK

    if args.op == "replay":
        result = pk.replay(pkg)
        print(json.dumps(result, indent=1))
        if result.get("reason") == "input snapshot changed":
            return EXIT_INPUT
        return EXIT_OK if result["ok"] else EXIT_FAIL
    return EXIT_INPUT


def _side_validate(scenes: Path, out: Path) -> int:
    """Only scenes whose four views are rendered (``rgb.png`` present = finalized) are used."""
    from tomato3d.state import sidegeom as sg

    if out.exists() and any(out.iterdir()):
        print(f"refused: {out} exists and is not empty", file=sys.stderr)
        return EXIT_INPUT
    rows, errors, used = [], [], []
    for sd in sorted(scenes.glob("scene_*")):
        views = [v.name for v in sorted((sd / "views").iterdir()) if (v / "rgb.png").exists()]
        if not views or len(views) != len(list((sd / "views").iterdir())):
            continue
        r, e = sg.validate_scene(sd, f"r1_{sd.name}", views)
        rows += sg.select_views(r)
        errors += e
        used.append(sd.name)
    if not used:
        print(f"unavailable: no finalized scene under {scenes}", file=sys.stderr)
        return EXIT_PARTIAL
    summary = sg.summarize_errors(errors, [0, 15, 30, 45, 60, 75, 90.01])
    write_table(out / "side_geometry.csv", rows, sg.s.SIDE_GEOMETRY_COLUMNS)
    write_table(out / "side_validation_errors.csv", errors, sg.SIDE_ERROR_COLUMNS)
    write_table(out / "side_validation_summary.csv", summary, sg.SIDE_SUMMARY_COLUMNS)
    write_table(out / "side_view_rule_summary.csv", sg.rule_summary(errors), sg.RULE_SUMMARY_COLUMNS)
    (out / "README.json").write_text(json.dumps(dict(
        what="P1.6 side-view geometry vs R.1 truth: generator truth points projected through each scene's render "
             "camera (undistorted K_render canvas); A2 angles measured in 2-D and compared with 3-D truth",
        scenes=len(used), first=used[0], last=used[-1], evidence="synthetic_fixture",
        rule="scenes whose views all have rgb.png (finalized)", view_selection_rule=sg.VIEW_SELECTION_RULE,
        code_version=pk.code_version()), indent=1) + "\n",
        encoding="utf-8")
    print(f"side-validate: {len(used)} scenes, {len(rows)} compound-views, {len(errors)} error rows -> {out}")
    return EXIT_OK


def _collect(pkg: Path) -> int:
    if not (pkg / "p1_manifest.json").exists():
        print(f"failed: {pkg} has no published manifest", file=sys.stderr)
        return EXIT_FAIL
    problems = pk.validate(pkg)
    man = json.loads((pkg / "p1_manifest.json").read_text(encoding="utf-8"))
    dry = pk.p2_dry_read(pkg)
    summary = dict(package=str(pkg), schema_version=man["schema_version"], evidence=man["evidence"],
                   overall_status=man["overall_status"],
                   run_status={r["segment"]: r["run_status"] for r in man["run_status"]},
                   validation_problems=problems, p2_dry_read_ok=dry["ok"], p2_issues=dry["issues"],
                   p2_plants=len(dry["plants_csv_rows"]), leaflets_supported=dry["leaflets_supported"],
                   leaflets_conditional=dry["leaflets_conditional"], leaflets_unavailable=dry["leaflets_unavailable"])
    print(json.dumps(summary, indent=1))
    failed = problems or not dry["ok"] or man["overall_status"] == "failed"
    if failed:
        return EXIT_FAIL
    return EXIT_PARTIAL if man["overall_status"] in ("partial", "unavailable") else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
