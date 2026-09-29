"""Offline research report and exportable figures. No network or synthetic claims."""
from __future__ import annotations

import html
from pathlib import Path

import numpy as np

from .common import number, rows, write_rows


def make_report(folder: Path, summary: dict, records: list[dict], run_paths: list[Path]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    warning = ("SYNTHETIC SOFTWARE DEMONSTRATION — not plant measurements"
               if summary["data_kind"] == "synthetic" else
               "No evaluation measurements" if summary["data_kind"] == "no_data" else
               "Observed data — inspect coverage, assumptions and uncertainty")
    variants = summary["variants"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    x = [v["view_count"] for v in variants]
    axes[0].scatter(x, [np.nan if v["nrmse_pct"] is None else v["nrmse_pct"] for v in variants])
    axes[0].axhline(summary["protocol"]["nrmse_limit_pct"], color="crimson", linestyle="--", label="Absolute-error limit")
    axes[0].set(xlabel="Photographs", ylabel="NRMSE (%)", title="Accuracy against physical reference")
    axes[0].legend()
    axes[1].scatter(x, [v["success_fraction"]*100 for v in variants])
    axes[1].axhline(summary["protocol"]["minimum_session_success_fraction"]*100, color="crimson", linestyle="--")
    axes[1].set(xlabel="Photographs", ylabel="Complete sessions (%)", ylim=(-2, 102), title="All planned sessions counted")
    fig.suptitle(warning, fontsize=9)
    for suffix in ("png", "svg"):
        fig.savefig(folder / f"view_count_accuracy.{suffix}", dpi=160)
    plt.close(fig)
    times = []
    for path in run_paths:
        if (path.parent / "timings.csv").exists():
            times.extend(rows(path.parent / "timings.csv"))
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    counts = sorted({int(r["view_count"]) for r in times})
    ax.plot(counts, [np.mean([float(r["reconstruction_seconds"])+float(r["light_seconds"]) for r in times if int(r["view_count"]) == count]) for count in counts], "o-")
    ax.set(xlabel="Photographs", ylabel="Compute seconds", title="Reconstruction + light calculation; manual time excluded")
    fig.savefig(folder / "compute_time.png", dpi=160)
    plt.close(fig)
    workload = []
    for count, scope in sorted({(int(r["view_count"]), r.get("work_scope", "unavailable")) for r in times}):
        group = [r for r in times if int(r["view_count"]) == count and r.get("work_scope", "unavailable") == scope]
        complete = []
        for row in group:
            human = [number(row.get(k), k, missing=True) for k in ("capture_seconds", "annotation_seconds", "correction_seconds")]
            if all(t is not None for t in human):
                complete.append(sum(human) + float(row["reconstruction_seconds"]) + float(row["light_seconds"]))
        workload.append(dict(view_count=count, work_scope=scope, n_variant_sessions=len(group),
                             n_complete_worklogs=len(complete), mean_total_seconds=float(np.mean(complete)) if complete else None))
    write_rows(folder / "workload.csv", workload,
               ("view_count", "work_scope", "n_variant_sessions", "n_complete_worklogs", "mean_total_seconds"))
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    for scope in sorted({r["work_scope"] for r in workload}):
        usable = [r for r in workload if r["work_scope"] == scope and r["mean_total_seconds"] is not None]
        if usable:
            ax.plot([r["view_count"] for r in usable], [r["mean_total_seconds"]/60 for r in usable], "o-", label=scope)
    if ax.lines:
        ax.legend()
    else:
        ax.text(.5,.5,"No complete manual worklogs supplied",ha="center",va="center",transform=ax.transAxes)
    ax.set(xlabel="Photographs", ylabel="Minutes", title="Capture + annotation + correction + compute (logged cases)")
    for suffix in ("png", "svg"):
        fig.savefig(folder / f"total_work_time.{suffix}", dpi=160)
    plt.close(fig)
    pairs = [(number(r["measured_ppfd_umol_m2_s"], "measured", missing=True),
              number(r["predicted_ppfd_umol_m2_s"], "predicted", missing=True))
             for r in records if r["variant_id"] == "v41_s00" and r["measurement_status"] == "valid" and r["run_status"] == "ok"]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    fig, ax = plt.subplots(figsize=(5, 4), layout="constrained")
    if pairs:
        array = np.asarray(pairs)
        ax.scatter(array[:, 0], array[:, 1], s=12)
        limit = max(float(array.max()), 1)
        ax.plot([0, limit], [0, limit], "k--")
    ax.set(xlabel="Measured PPFD", ylabel="Predicted PPFD", title="41 photographs: individual sensor readings")
    fig.savefig(folder / "measured_vs_predicted.png", dpi=160)
    plt.close(fig)
    mesh_image = ""
    if run_paths and (run_paths[0].parent / "leaf_light_map.csv").exists():
        triangles = [r for r in rows(run_paths[0].parent / "leaf_light_map.csv") if r["variant_id"] == "v41_s00"]
        if triangles:
            vertices = np.asarray([[[float(r[f"v{i}_{a}_mm"]) for a in "xyz"] for i in range(3)] for r in triangles])
            light = np.asarray([number(r["ppfd_umol_m2_s"], "map PPFD", missing=True) for r in triangles], dtype=float)
            fig = plt.figure(figsize=(6, 5), layout="constrained")
            ax = fig.add_subplot(projection="3d")
            collection = Poly3DCollection(vertices, cmap="viridis", edgecolor="gray", linewidth=0.2)
            collection.set_array(np.ma.masked_invalid(light))
            ax.add_collection3d(collection)
            xyz = vertices.reshape(-1, 3)
            ax.auto_scale_xyz(xyz[:, 0], xyz[:, 1], xyz[:, 2])
            ax.set(xlabel="Grow X (mm)", ylabel="Grow Y (mm)", zlabel="Grow Z (mm)", title="First session: reconstructed leaf surfaces")
            fig.colorbar(collection, ax=ax, label="Incident PPFD (umol/m2/s)", shrink=0.6)
            fig.savefig(folder / "leaf_light_3d.png", dpi=160)
            plt.close(fig)
            mesh_image = '<img src="leaf_light_3d.png" alt="3D leaf light map">'
    cells = []
    for v in variants:
        fmt = lambda n: "unavailable" if n is None else f"{n:.2f}"
        cells.append(f'<tr><td>{html.escape(v["variant_id"])}</td><td>{v["view_count"]}</td><td>{fmt(v["nrmse_pct"])}</td><td>{fmt(v["upper_one_sided_pp"])}</td><td>{v["successful_sessions"]}/{v["planned_sessions"]}</td><td>{"pass" if v["passes"] else html.escape(", ".join(v["failure_reasons"]))}</td></tr>')
    minimum = summary["minimum_tested_view_count"]
    baseline = variants[0]
    contribution = ("unavailable" if baseline["rmse_improvement_over_no_plants"] is None
                    else f"{baseline['rmse_improvement_over_no_plants']:.2f} umol/m2/s")
    verdict = "Not established" if minimum is None else f"{minimum} photographs among tested configurations"
    content = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tomato leaf light study</title><style>body{{font:16px system-ui;max-width:1100px;margin:30px auto;padding:0 16px;color:#172b24;background:#f7faf8}}h1,h2{{color:#194b39}}.notice{{padding:16px;background:#fff1cc;border:1px solid #a57c23}}img{{max-width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border:1px solid #b8cac2;padding:8px;text-align:left}}.scroll{{overflow:auto}}code{{overflow-wrap:anywhere}}</style>
<h1>Tomato 3D leaf light study</h1><p class="notice">{html.escape(warning)}</p>
<p><a href="inspector.html">Inspect photographs, subset geometry and sensor comparisons</a></p>
<p><b>Minimum tested view count:</b> {verdict}</p><p>Valid measurements: {summary['valid_measurement_count']} / {summary['planned_measurement_count']} planned.</p>
<p>RQ1 compares predictions with sensor measurements. RQ2 compares their errors using the same measurements. A 41-view reconstruction is not ground truth.</p>
<img src="view_count_accuracy.png" alt="Accuracy and session coverage by number of photographs">
<div class="scroll"><table><thead><tr><th>Variant</th><th>Images</th><th>NRMSE %</th><th>Upper error increase, pp</th><th>Complete sessions</th><th>Decision</th></tr></thead><tbody>{''.join(cells)}</tbody></table></div>
<p>41-view RMSE improvement over the empty light-field model on common sites: {contribution}. Positive means lower error with leaf geometry; negative means the empty-field model performed better. This is descriptive, not a significance test.</p>
<img src="measured_vs_predicted.png" alt="Predicted versus measured PPFD"><img src="compute_time.png" alt="Compute time"><img src="total_work_time.png" alt="Logged total work time">{mesh_image}
<h2>Interpretation</h2><p>{html.escape(summary['inference'])} {html.escape(summary['minimum_rule'])} {html.escape(summary['missingness'])}</p>
<p>Manual annotation/correction time is unavailable unless logged; compute time is not total workload. Direct-light geometry and optical assumptions remain limitations. This is not a photosynthesis or yield measurement.</p>
<p>Machine-readable results: <a href="evaluation.json">evaluation.json</a>, <a href="view_count_metrics.csv">metrics CSV</a>, <a href="session_coverage.csv">coverage CSV</a>, <a href="repeatability.csv">repeatability CSV</a>, <a href="workload.csv">workload CSV</a>.</p>
<p>Frozen protocol: <code>{summary['protocol_sha256']}</code></p></html>'''
    (folder / "report.html").write_text(content, encoding="utf-8")
    from .explorer import make_explorer
    make_explorer(folder, summary, records, run_paths)
