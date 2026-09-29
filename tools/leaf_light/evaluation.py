"""Paired physical-reference errors, planned-session coverage and plant bootstrap."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from .common import (StudyError, file_hash, load_protocol, number, output_dir,
                     read_json, rows, variants, write_json, write_rows)
from .optics import PREDICTION_COLUMNS


def metrics(measured: np.ndarray, predicted: np.ndarray) -> dict:
    if len(measured) == 0:
        return dict(n_sites=0, mae=None, rmse=None, bias=None, nrmse_pct=None)
    error = predicted - measured
    rmse = float(np.sqrt(np.mean(error ** 2)))
    return dict(n_sites=len(measured), mae=float(np.abs(error).mean()), rmse=rmse,
                bias=float(error.mean()), nrmse_pct=100 * rmse / float(measured.mean()) if measured.mean() > 0 else None)


def paired_bootstrap(triples: dict[str, list[tuple[float, float, float]]], p: dict) -> tuple[float | None, float | None]:
    """Resample complete plant clusters; keep all their dates/sites together."""
    if len(triples) < p["minimum_evaluation_plants"]:
        return None, None
    totals = []
    for plant in sorted(triples):
        data = np.asarray(triples[plant])
        y, ref, candidate = data.T
        totals.append([len(y), y.sum(), ((ref - y)**2).sum(), ((candidate - y)**2).sum()])
    totals = np.asarray(totals)
    if totals[:, 1].sum() <= 0:
        return None, None
    rng = np.random.default_rng(p["bootstrap_seed"])
    n = len(totals)
    weights = rng.multinomial(n, np.full(n, 1 / n), size=p["bootstrap_iterations"])
    boot = weights @ totals
    if np.any(boot[:, 1] <= 0):
        return None, None
    delta = 100 * (np.sqrt(boot[:, 3] / boot[:, 0]) - np.sqrt(boot[:, 2] / boot[:, 0])) / (boot[:, 1] / boot[:, 0])
    pooled = totals.sum(axis=0)
    point = 100 * (np.sqrt(pooled[3] / pooled[0]) - np.sqrt(pooled[2] / pooled[0])) / (pooled[1] / pooled[0])
    return float(point), float(np.quantile(delta, p["confidence"], method="higher"))


def evaluate_data(p: dict, records: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    selections = variants(p)
    variant_ids = {v["variant_id"] for v in selections}
    reference = "v41_s00"
    expected_sessions = {(plant, slot) for plant in p["evaluation_plants"] for slot in p["session_slots"]}
    observations, by_variant, empty_field = {}, defaultdict(dict), {}
    session_sites = defaultdict(lambda: defaultdict(set))
    for row in records:
        plant, slot, variant = row["plant_id"], row["session_slot"], row["variant_id"]
        if plant in p["development_plants"]:
            continue
        if (plant, slot) not in expected_sessions or variant not in variant_ids:
            raise StudyError("Unexpected evaluation plant, slot, or variant")
        key = (plant, slot, row["site_id"], row["replicate_id"])
        if key in by_variant[variant]:
            raise StudyError("Duplicate prediction key")
        measured = number(row["measured_ppfd_umol_m2_s"], "measured PPFD", missing=True)
        predicted = number(row["predicted_ppfd_umol_m2_s"], "predicted PPFD", missing=True)
        if measured is not None and measured < 0 or predicted is not None and predicted < 0:
            raise StudyError("PPFD cannot be negative")
        identity = (measured, row["region_label"], row["measurement_status"])
        if key in observations and observations[key] != identity:
            raise StudyError("Variants do not share identical physical reference measurements")
        observations[key] = identity
        empty_prediction = number(row.get("no_plants_ppfd_umol_m2_s"), "empty-field PPFD", missing=True)
        if key in empty_field and empty_field[key] != empty_prediction:
            raise StudyError("Variants do not share the same calibrated empty light field")
        empty_field[key] = empty_prediction
        if row["run_status"] != "ok":
            predicted = None
        by_variant[variant][key] = predicted
        session_sites[(plant, slot)][row["site_id"]].add(row["replicate_id"])
    expected_count = p["sites_per_session"] * p["replicates_per_site"]
    valid_measurements = {k: v[0] for k, v in observations.items() if v[0] is not None and v[2] == "valid"}
    measurement_coverage = len(valid_measurements) / (len(expected_sessions) * expected_count)
    if len(observations) > len(expected_sessions) * expected_count:
        raise StudyError("More evaluation readings than planned")
    for sites in session_sites.values():
        if len(sites) > p["sites_per_session"] or any(len(r) > p["replicates_per_site"] for r in sites.values()):
            raise StudyError("Too many sites or replicates in a session")
    session_scores = []
    summaries = []
    site_groups = defaultdict(list)
    for key in valid_measurements:
        site_groups[key[:3]].append(key)
    # Absolute scores are site means, not pseudo-independent replicate scores.
    for selection in selections:
        vid = selection["variant_id"]
        available_sites = {}
        success_count = 0
        for plant, slot in sorted(expected_sessions):
            keys = [k for k in valid_measurements if k[:2] == (plant, slot)]
            site_layout = session_sites[(plant, slot)]
            planned_layout = (len(site_layout) == p["sites_per_session"] and
                              all(len(r) == p["replicates_per_site"] for r in site_layout.values()))
            success = (planned_layout and len(keys) >= expected_count * p["minimum_measurement_coverage_fraction"] and
                       all(by_variant[vid].get(k) is not None for k in keys))
            success_count += int(success)
            session_scores.append(dict(plant_id=plant, session_slot=slot, variant_id=vid,
                                       success=success, n_valid_readings=len(keys),
                                       n_predicted=sum(by_variant[vid].get(k) is not None for k in keys)))
        for site, keys in site_groups.items():
            if all(by_variant[vid].get(k) is not None for k in keys):
                available_sites[site] = (float(np.mean([valid_measurements[k] for k in keys])),
                                         float(np.mean([by_variant[vid][k] for k in keys])))
        values = np.asarray(list(available_sites.values())).reshape(-1, 2)
        score = metrics(values[:, 0], values[:, 1])
        empty_pairs = []
        model_pairs = []
        for site, value in available_sites.items():
            keys = site_groups[site]
            if all(empty_field.get(k) is not None for k in keys):
                empty_pairs.append((value[0], float(np.mean([empty_field[k] for k in keys]))))
                model_pairs.append(value)
        empty_array = np.asarray(empty_pairs).reshape(-1, 2)
        model_array = np.asarray(model_pairs).reshape(-1, 2)
        empty_score = metrics(empty_array[:, 0], empty_array[:, 1])
        paired_model_score = metrics(model_array[:, 0], model_array[:, 1])
        improvement = (empty_score["rmse"] - paired_model_score["rmse"]
                       if empty_pairs else None)
        triples = defaultdict(list)
        for site, keys in site_groups.items():
            if all(by_variant[vid].get(k) is not None and by_variant[reference].get(k) is not None for k in keys):
                triples[site[0]].append((float(np.mean([valid_measurements[k] for k in keys])),
                    float(np.mean([by_variant[reference][k] for k in keys])),
                    float(np.mean([by_variant[vid][k] for k in keys]))))
        delta, upper = paired_bootstrap(triples, p) if vid != reference else (0.0, 0.0)
        region_scores = {}
        for region in sorted({v[1] for v in observations.values()}):
            region_values = [v for site, v in available_sites.items() if observations[site_groups[site][0]][1] == region]
            array = np.asarray(region_values).reshape(-1, 2)
            region_scores[region] = metrics(array[:, 0], array[:, 1])
        summaries.append(dict(variant_id=vid, view_count=selection["view_count"], **score,
                              success_fraction=success_count / len(expected_sessions),
                              successful_sessions=success_count, planned_sessions=len(expected_sessions),
                              n_paired_plants=len(triples), delta_nrmse_pp=delta, upper_one_sided_pp=upper,
                              no_plants_paired_n_sites=empty_score["n_sites"],
                              no_plants_paired_rmse=empty_score["rmse"],
                              rmse_improvement_over_no_plants=improvement,
                              regions=region_scores))
    baseline = summaries[0]
    baseline_ok = (baseline["nrmse_pct"] is not None and baseline["nrmse_pct"] <= p["nrmse_limit_pct"] and
                   baseline["success_fraction"] >= p["minimum_session_success_fraction"] and
                   baseline["n_paired_plants"] >= p["minimum_evaluation_plants"])
    measurement_ok = measurement_coverage >= p["minimum_measurement_coverage_fraction"]
    for summary in summaries:
        reasons = []
        if not measurement_ok:
            reasons.append("insufficient_measurement_coverage")
        if not baseline_ok:
            reasons.append("41_view_reference_not_qualified")
        if summary["nrmse_pct"] is None or summary["nrmse_pct"] > p["nrmse_limit_pct"]:
            reasons.append("absolute_error_limit")
        if summary["success_fraction"] < p["minimum_session_success_fraction"]:
            reasons.append("session_coverage_limit")
        if summary["n_paired_plants"] < p["minimum_evaluation_plants"]:
            reasons.append("too_few_independent_plants")
        if summary["upper_one_sided_pp"] is None or summary["upper_one_sided_pp"] > p["noninferiority_margin_pp"]:
            reasons.append("noninferiority_not_established")
        summary["passes"] = not reasons
        summary["failure_reasons"] = reasons
    passing_counts = [count for count in p["view_counts"] if count < 41 and
                      all(s["passes"] for s in summaries if s["view_count"] == count)]
    repeatability = []
    for site, keys in site_groups.items():
        measured = [valid_measurements[k] for k in keys]
        repeatability.append(dict(plant_id=site[0], session_slot=site[1], site_id=site[2],
                                  n_repeats=len(measured), mean_ppfd=float(np.mean(measured)),
                                  sd_ppfd=float(np.std(measured, ddof=1)) if len(measured) > 1 else None))
    summary = dict(measurement_coverage_fraction=measurement_coverage,
                   valid_measurement_count=len(valid_measurements), planned_measurement_count=len(expected_sessions)*expected_count,
                   minimum_tested_view_count=min(passing_counts) if passing_counts else None,
                   variants=summaries, inference="Pointwise one-sided plant-cluster percentile bootstrap; not simultaneous confidence across all choices.",
                   minimum_rule="Every tested starting phase at that view count must pass; no global minimum claim.",
                   missingness="Errors use available site means; paired differences use common sites. All planned sessions remain in coverage denominators.")
    return summary, session_scores, repeatability


def evaluate(protocol_path: Path, run_paths: list[Path], out: Path) -> dict:
    p, protocol_hash = load_protocol(protocol_path)
    combined, sources, kinds, seen, models = [], [], set(), set(), set()
    capture_sessions = set()
    for path in run_paths:
        run = read_json(path)
        if run["protocol_sha256"] != protocol_hash:
            raise StudyError("Run uses a different protocol")
        key = (run["plant_id"], run["session_slot"])
        if key in seen:
            raise StudyError("Multiple runs for the same planned plant/session slot")
        seen.add(key)
        capture_key = (run["plant_id"], run["session_id"])
        if capture_key in capture_sessions:
            raise StudyError("One physical capture cannot fill multiple planned session slots")
        capture_sessions.add(capture_key)
        if run["plant_id"] in p["development_plants"]:
            continue
        prediction_path = path.parent / "predictions.csv"
        if file_hash(prediction_path) != run["predictions_sha256"]:
            raise StudyError("Predictions changed after the run")
        records = rows(prediction_path, PREDICTION_COLUMNS)
        if any((r["plant_id"], r["session_slot"], r["session_id"]) != (*key, run["session_id"]) for r in records):
            raise StudyError("Run metadata and prediction identities disagree")
        combined.extend(records)
        kinds.add(run["data_kind"])
        models.add(run["source_model_sha256"])
        sources.append({"path": str(path.resolve()), "sha256": file_hash(path)})
    if len(kinds) > 1 or len(models) > 1:
        raise StudyError("Cannot combine synthetic/observed data or different frozen source models")
    summary, sessions, repeatability = evaluate_data(p, combined)
    summary.update(protocol_sha256=protocol_hash, data_kind=next(iter(kinds), "no_data"),
                   sources=sources, protocol=p)
    folder = output_dir(out)
    write_json(folder / "evaluation.json", summary)
    flat = [{k: v for k, v in s.items() if k not in ("regions", "failure_reasons")} for s in summary["variants"]]
    write_rows(folder / "view_count_metrics.csv", flat, list(flat[0]))
    write_rows(folder / "session_coverage.csv", sessions, list(sessions[0]))
    write_rows(folder / "repeatability.csv", repeatability,
               ("plant_id", "session_slot", "site_id", "n_repeats", "mean_ppfd", "sd_ppfd"))
    from .report import make_report
    make_report(folder, summary, combined, run_paths)
    return summary
