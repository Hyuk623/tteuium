"""First-open-flower records and interval-censored prediction; no CO2 input.

python -m tools.first_flowering --help
Dates are ISO calendar dates. A visit is not an exact biological event time.
Models use a fixed, predeclared landmark day and plot-disjoint evaluation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr

from tools.leaf_light.common import (StudyError, file_hash, number, output_dir,
                                    read_json, rows, write_json, write_rows)

PLANTS = ('plant_id', 'plot_id', 'density_id', 'start_date', 'end_date', 'split')
VISITS = ('plant_id', 'date', 'state', 'human_confirmed', 'evidence_photo')
RECORDS = ('plant_id', 'date', 'height_mm', 'leaf_count', 'reviewed_leaf_area_mm2',
           'temperature_c', 'relative_humidity_pct')
LIGHT = ('plant_id', 'date', 'geometry_date', 'lower_ppfd_umol_m2_s',
         'upper_ppfd_umol_m2_s', 'leaf_ppfd_cv', 'source_run', 'review_state')
EVENTS = PLANTS + ('event_status', 'last_nonflowering_date', 'first_open_date',
                  'lower_day', 'upper_day', 'evidence_photo', 'n_unconfirmed_visits')
BASE_FEATURES = ('height_mm', 'leaf_count', 'reviewed_leaf_area_mm2')
LIGHT_FEATURES = ('lower_ppfd_umol_m2_s', 'upper_ppfd_umol_m2_s', 'leaf_ppfd_cv')


def day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise StudyError(f'Invalid ISO date: {value!r}') from exc


def events(plants: list[dict], visits: list[dict], evidence_base: Path) -> list[dict]:
    """Resolve endpoints without converting censoring dates into event dates."""
    ids = [p['plant_id'] for p in plants]
    if len(ids) != len(set(ids)):
        raise StudyError('Duplicate plant_id; multiple photos are not multiple plants')
    by_plant = defaultdict(list)
    plots: dict[str, tuple[str, str]] = {}
    for p in plants:
        if not p['plant_id'] or not p['plot_id'] or not p['density_id']:
            raise StudyError('Plant, plot and density IDs are required')
        if p['split'] not in ('development', 'evaluation', 'observe_only'):
            raise StudyError('Unknown split')
        pair = (p['density_id'], p['split'])
        if p['plot_id'] in plots and plots[p['plot_id']] != pair:
            raise StudyError('One plot cannot span densities or development/evaluation splits')
        plots[p['plot_id']] = pair
        if day(p['end_date']) < day(p['start_date']):
            raise StudyError('Study end precedes start')
    seen = set()
    for v in visits:
        if v['plant_id'] not in ids:
            raise StudyError(f"Unknown plant in visits: {v['plant_id']}")
        key = (v['plant_id'], v['date'])
        if key in seen:
            raise StudyError(f'Duplicate daily visit: {key}')
        seen.add(key)
        if v['state'] not in ('not_open', 'bud_only', 'first_open', 'missed'):
            raise StudyError('Visit state must be not_open, bud_only, first_open or missed')
        if v['human_confirmed'] not in ('true', 'false'):
            raise StudyError('human_confirmed must be true or false')
        day(v['date'])
        by_plant[v['plant_id']].append(v)
    result = []
    for p in plants:
        start, end = day(p['start_date']), day(p['end_date'])
        good, ignored = [], 0
        for v in sorted(by_plant[p['plant_id']], key=lambda r: r['date']):
            d = day(v['date'])
            if d < start or d > end:
                raise StudyError(f"Visit outside declared observation period: {p['plant_id']} {d}")
            if v['human_confirmed'] != 'true' or v['state'] == 'missed':
                ignored += 1
                continue
            if v['state'] == 'first_open':
                photo = v['evidence_photo']
                if not photo or not (evidence_base / photo).is_file():
                    raise StudyError('Confirmed first open flower requires an existing evidence photo')
            good.append(v)
        positive = next((v for v in good if v['state'] == 'first_open'), None)
        if positive and any(v['date'] > positive['date'] and v['state'] != 'first_open' for v in good):
            raise StudyError('Ever-flowered status cannot revert to nonflowering')
        negatives = [v for v in good if v['state'] in ('not_open', 'bud_only')
                     and (not positive or v['date'] < positive['date'])]
        last = negatives[-1] if negatives else None
        lo = (day(last['date']) - start).days if last else None
        hi = (day(positive['date']) - start).days if positive else None
        if positive and hi == 0:
            status = 'already_flowered_at_entry'
        elif positive and last:
            status = 'interval_censored'
        elif positive:
            status = 'baseline_unknown'
        elif last:
            status = 'right_censored'
        else:
            status = 'no_confirmed_observation'
        result.append(dict(p, event_status=status,
            last_nonflowering_date=last['date'] if last else None,
            first_open_date=positive['date'] if positive else None,
            lower_day=lo, upper_day=hi,
            evidence_photo=positive['evidence_photo'] if positive else None,
            n_unconfirmed_visits=ignored))
    return result


def plot_summary(event_rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in event_rows:
        groups[(row['plot_id'], row['density_id'])].append(row)
    result = []
    for (plot, density), group in sorted(groups.items()):
        at_risk = [r for r in group if r['event_status'] in ('interval_censored', 'right_censored')]
        opened = [r for r in at_risk if r['event_status'] == 'interval_censored']
        result.append(dict(plot_id=plot, density_id=density, n_plants=len(group),
            n_known_at_risk=len(at_risk), n_confirmed_open=len(opened),
            observed_open_fraction=len(opened)/len(at_risk) if at_risk else None,
            n_right_censored=sum(r['event_status'] == 'right_censored' for r in group),
            n_already_open=sum(r['event_status'] == 'already_flowered_at_entry' for r in group),
            n_baseline_unknown=sum(r['event_status'] == 'baseline_unknown' for r in group),
            first_open_lower_day_min=min((r['lower_day'] for r in opened), default=None),
            first_open_upper_day_max=max((r['upper_day'] for r in opened), default=None),
            latest_confirmed_followup_day=max((r['lower_day'] for r in at_risk), default=None)))
    return result


def log_probability(lower: np.ndarray, upper: np.ndarray, mu: np.ndarray,
                    sigma: float) -> np.ndarray:
    """Lognormal interval/right-censored log probabilities, in elapsed days."""
    zl = (np.log(np.maximum(lower, np.finfo(float).tiny)) - mu)/sigma
    zu = (np.log(np.maximum(upper, np.finfo(float).tiny)) - mu)/sigma
    out = log_ndtr(-zl)
    finite = np.isfinite(upper)
    # Stable difference of survival functions for upper-tail intervals, CDFs otherwise.
    a = np.where(zl[finite] > 0, log_ndtr(-zl[finite]), log_ndtr(zu[finite]))
    b = np.where(zl[finite] > 0, log_ndtr(-zu[finite]), log_ndtr(zl[finite]))
    delta = np.minimum(b - a, -np.finfo(float).eps)
    out[finite] = a + np.log(-np.expm1(delta))
    return out


def feature_table(event_rows: list[dict], growth: list[dict], light: list[dict],
                  landmark_day: int) -> tuple[list[dict], list[dict]]:
    """One causal row per plant. Strictly no later observation/snapshot lookup."""
    if landmark_day < 0:
        raise StudyError('landmark_day must be nonnegative')
    ids = {r['plant_id'] for r in event_rows}
    for collection in (growth, light):
        seen = set()
        for r in collection:
            key = (r['plant_id'], r['date'])
            if key in seen or r['plant_id'] not in ids:
                raise StudyError('Duplicate dated record or unknown plant')
            day(r['date']); seen.add(key)
    for r in growth:
        for name in RECORDS[2:]:
            value=number(r.get(name),name,missing=True)
            if value is None:
                continue
            if name in BASE_FEATURES and value<0:
                raise StudyError(f'Negative {name}')
            if name=='leaf_count' and value!=int(value):
                raise StudyError('Observed leaf count must be an integer')
            if name=='relative_humidity_pct' and not 0<=value<=100:
                raise StudyError('Relative humidity must be within 0–100 percent')
    accepted, exclusions = [], []
    for e in event_rows:
        pid, start = e['plant_id'], day(e['start_date'])
        reason = None
        if e['event_status'] not in ('interval_censored', 'right_censored'):
            reason = e['event_status']
        elif e['lower_day'] < landmark_day:
            reason = 'not_confirmed_event_free_through_landmark'
        elif e['event_status'] == 'right_censored' and e['lower_day'] == landmark_day:
            reason = 'no_followup_after_landmark'
        def latest(collection: list[dict]) -> dict | None:
            eligible = [r for r in collection if r['plant_id'] == pid
                        and 0 <= (day(r['date']) - start).days <= landmark_day]
            return max(eligible, key=lambda r: r['date']) if eligible else None
        g, l = latest(growth), latest(light)
        if not g:
            reason = reason or 'no_pre_landmark_growth'
        values = {}
        if g:
            for name in BASE_FEATURES:
                values[name] = number(g.get(name), name, missing=True)
                if values[name] is not None and values[name] < 0:
                    raise StudyError(f'Negative {name}')
            if any(v is None for v in values.values()):
                reason = reason or 'incomplete_baseline_features'
        light_reason = 'no_pre_landmark_light'
        if l:
            if day(l['geometry_date']) > day(l['date']):
                raise StudyError('Geometry snapshot is later than the light observation')
            if l['geometry_date'] != l['date']:
                light_reason = 'light_date_is_not_geometry_snapshot_date'
            elif not l['source_run'] or l['review_state'] != 'reviewed':
                light_reason = 'light_not_reviewed_or_missing_provenance'
            else:
                for name in LIGHT_FEATURES:
                    values[name] = number(l.get(name), name, missing=True)
                    if values[name] is not None and values[name] < 0:
                        raise StudyError(f'Negative {name}')
                light_reason = None if all(values[n] is not None for n in LIGHT_FEATURES) else 'incomplete_light_features'
        if reason:
            exclusions.append(dict(plant_id=pid, reason=reason))
        else:
            accepted.append(dict(e, **values, growth_date=g['date'],
                light_date=l['date'] if l else None, light_exclusion=light_reason,
                landmark_day=landmark_day))
    return accepted, exclusions


def fit_aft(train: list[dict], names: tuple[str, ...], settings: dict) -> dict:
    """Conditional likelihood T > landmark, with training-only normalization."""
    x = np.asarray([[r[n] for n in names] for r in train], dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale == 0] = 1
    X = np.column_stack([np.ones(len(x)), (x-mean)/scale])
    lower = np.array([r['lower_day'] for r in train], float)
    upper = np.array([r['upper_day'] if r['upper_day'] is not None else np.inf for r in train])
    lm = np.array([r['landmark_day'] for r in train], float)
    weights = np.array([1/sum(q['plot_id'] == r['plot_id'] for q in train) for r in train])
    weights *= len(train)/weights.sum()
    ridge = number(settings['ridge'], 'ridge')
    if ridge < 0:
        raise StudyError('ridge must be nonnegative')
    def objective(theta: np.ndarray) -> float:
        mu, sigma = X@theta[:-1], np.exp(theta[-1])
        likelihood = log_probability(lower, upper, mu, sigma) - log_probability(lm, np.full(len(lm), np.inf), mu, sigma)
        return float(-np.sum(weights*likelihood) + ridge*np.sum(theta[1:-1]**2))
    centre = np.median(upper[np.isfinite(upper)])
    initial = np.r_[np.log(max(centre, 1)), np.zeros(len(names)), 0.0]
    fitted = minimize(objective, initial, method='L-BFGS-B',
                      bounds=[(None, None)]*(len(names)+1)+[(-4, 4)],
                      options={'maxiter':int(settings['max_iterations'])})
    if not fitted.success or not np.isfinite(fitted.fun):
        raise StudyError(f'AFT fit failed: {fitted.message}')
    return dict(features=list(names), mean=mean.tolist(), scale=scale.tolist(),
                coefficients=fitted.x[:-1].tolist(), sigma=float(np.exp(fitted.x[-1])),
                objective=float(fitted.fun), n_plants=len(train),
                n_plots=len({r['plot_id'] for r in train}), fit_status='converged')


def predict_aft(model: dict, records: list[dict]) -> list[dict]:
    if not records:
        return []
    x = np.asarray([[r[n] for n in model['features']] for r in records])
    X = np.column_stack([np.ones(len(x)), (x-np.array(model['mean']))/np.array(model['scale'])])
    mu, sigma = X@np.array(model['coefficients']), model['sigma']
    result = []
    for i, r in enumerate(records):
        lm = r['landmark_day']
        z = (np.log(max(lm, np.finfo(float).tiny))-mu[i])/sigma
        log_survival = log_ndtr(-z)
        # Conditional median from log survival, avoiding 1-CDF cancellation.
        from scipy.special import ndtri_exp
        median = float(np.exp(mu[i] - sigma*ndtri_exp(log_survival + np.log(.5))))
        quantiles = [float(np.exp(mu[i] - sigma*ndtri_exp(log_survival + np.log1p(-q)))) for q in (.025,.975)]
        lo, hi = r['lower_day'], r['upper_day']
        nll = -float(log_probability(np.array([lo]), np.array([hi if hi is not None else np.inf]),
                                    np.array([mu[i]]), sigma)[0] - log_survival)
        interval_distance = max(lo-median, 0, median-hi) if hi is not None else None
        result.append(dict(plant_id=r['plant_id'], plot_id=r['plot_id'], split=r['split'],
            predicted_total_day_median=median, predicted_remaining_day_median=median-lm,
            predicted_total_day_p025=quantiles[0],predicted_total_day_p975=quantiles[1],
            interval_distance_days=interval_distance, conditional_nll=nll))
    return result


def compare_models(records: list[dict], settings: dict) -> dict:
    """Paired comparison uses the same complete-case plants for both models."""
    paired = [r for r in records if r['light_exclusion'] is None]
    development = [r for r in paired if r['split'] == 'development']
    evaluation = [r for r in paired if r['split'] == 'evaluation']
    result = dict(status='unavailable', reason=None, models={},
        n_baseline_eligible=len(records), n_paired_eligible=len(paired),
        n_development=len(development), n_evaluation=len(evaluation))
    if ({r['plot_id'] for r in development} & {r['plot_id'] for r in evaluation}
        or {r['plant_id'] for r in development} & {r['plant_id'] for r in evaluation}):
        raise StudyError('Development/evaluation leakage')
    gates = [('min_development_plots', len({r['plot_id'] for r in development})),
             ('min_development_events', sum(r['upper_day'] is not None for r in development)),
             ('min_evaluation_plots', len({r['plot_id'] for r in evaluation}))]
    for key, count in gates:
        threshold = settings.get(key)
        if threshold is None or not isinstance(threshold, int) or threshold < 1 or count < threshold:
            result['reason'] = f'{key} not configured or unmet (observed {count})'
            return result
    for label, names in [('baseline', BASE_FEATURES), ('with_light', BASE_FEATURES+LIGHT_FEATURES)]:
        try:
            model = fit_aft(development, names, settings)
            predictions = predict_aft(model, evaluation)
        except StudyError as exc:
            result['reason'] = str(exc)
            return result
        by_plot = defaultdict(list)
        for r in predictions:
            by_plot[r['plot_id']].append(r['conditional_nll'])
        model['evaluation_plot_mean_nll'] = float(np.mean([np.mean(v) for v in by_plot.values()]))
        errors=defaultdict(list)
        for r in predictions:
            if r['interval_distance_days'] is not None:
                errors[r['plot_id']].append(r['interval_distance_days'])
        model['evaluation_plot_mean_interval_distance_days'] = float(np.mean([np.mean(v) for v in errors.values()])) if errors else None
        model['predictions'] = predictions
        result['models'][label] = model
    result.update(status='evaluated_exploratory', reason=None,
        delta_plot_mean_nll=result['models']['with_light']['evaluation_plot_mean_nll']-
                            result['models']['baseline']['evaluation_plot_mean_nll'],
        interpretation='Negative delta favours light features on these held-out plots; no significance or generalization claim.')
    return result


def analyse(input_dir: Path, out: Path, settings_path: Path) -> dict:
    settings = read_json(settings_path)
    plants = rows(input_dir/'plants.csv', PLANTS)
    visits = rows(input_dir/'flower_visits.csv', VISITS)
    event_rows = events(plants, visits, input_dir)
    summaries = plot_summary(event_rows)
    features, excluded = feature_table(event_rows, rows(input_dir/'growth.csv', RECORDS),
                                      rows(input_dir/'light_timeseries.csv', LIGHT), int(settings['landmark_day']))
    comparison = compare_models(features, settings)
    folder = output_dir(out)
    write_rows(folder/'flower_events.csv', event_rows, EVENTS)
    plot_cols = ('plot_id','density_id','n_plants','n_known_at_risk','n_confirmed_open',
        'observed_open_fraction','n_right_censored','n_already_open','n_baseline_unknown',
        'first_open_lower_day_min','first_open_upper_day_max','latest_confirmed_followup_day')
    write_rows(folder/'plot_flowering.csv', summaries, plot_cols)
    density = []
    for did in sorted({r['density_id'] for r in summaries}):
        group = [r for r in summaries if r['density_id'] == did]
        fractions = [r['observed_open_fraction'] for r in group if r['observed_open_fraction'] is not None]
        density.append(dict(density_id=did, n_independent_plots=len(group),
            n_plots_with_known_baseline=len(fractions),
            mean_plot_observed_open_fraction=float(np.mean(fractions)) if fractions else None,
            flowering_day_estimate=None, optimum=None))
    write_rows(folder/'density_flowering.csv', density, ('density_id','n_independent_plots',
        'n_plots_with_known_baseline','mean_plot_observed_open_fraction','flowering_day_estimate','optimum'))
    write_rows(folder/'feature_exclusions.csv', excluded, ('plant_id','reason'))
    write_rows(folder/'causal_features.csv', features, EVENTS+BASE_FEATURES+LIGHT_FEATURES+
               ('growth_date','light_date','light_exclusion','landmark_day'))
    predictions=[]
    for name,model in comparison['models'].items():
        predictions.extend(dict(model=name,**r) for r in model['predictions'])
    write_rows(folder/'flower_predictions.csv',predictions,('model','plant_id','plot_id','split',
        'predicted_total_day_median','predicted_remaining_day_median','predicted_total_day_p025',
        'predicted_total_day_p975','interval_distance_days','conditional_nll'))
    write_json(folder/'prediction_comparison.json', comparison)
    sources = [input_dir/n for n in ('plants.csv','flower_visits.csv','growth.csv','light_timeseries.csv')]+[settings_path]
    evidence = {str((input_dir/r['evidence_photo']).resolve()) for r in event_rows if r['evidence_photo']}
    sources += [Path(p) for p in sorted(evidence)]
    report = dict(schema_version='first-flowering-1', n_plants=len(plants),
        prediction_status=comparison['status'], source_hashes={str(p.resolve()):file_hash(p) for p in sources},
        endpoint='Human-confirmed first flower with open petals and visible interior',
        co2_recorded=False, photosynthesis='unavailable',
        limits=['Descriptive open fractions are not censor-adjusted probabilities; follow-up may differ.',
                'Intervals are not midpoint-imputed flowering dates. Right censoring ends at last verified negative visit.',
                'Plots, not plants within a plot, are density replicates. No causal density effect or yield optimum is claimed.',
                'AFT predictions are optional exploratory lognormal models; configured sample gates are not power calculations.'])
    write_json(folder/'analysis.json', report)
    return report


def templates(out: Path) -> dict:
    folder = output_dir(out)
    for name, columns in [('plants.csv',PLANTS),('flower_visits.csv',VISITS),('growth.csv',RECORDS),('light_timeseries.csv',LIGHT)]:
        write_rows(folder/name, [], columns)
    settings = dict(landmark_day=0, ridge=1.0, max_iterations=2000,
                    planned_observation_weeks=6,
                    min_development_plots=None, min_development_events=None, min_evaluation_plots=None)
    write_json(folder/'analysis_settings.json', settings)
    (folder/'README.txt').write_text('Fill records with actual observations; blanks are unavailable, not zero.\n'
        'split: development / evaluation / observe_only. One plot has one split and density.\n'
        'state: not_open / bud_only / first_open / missed; human_confirmed: true / false.\n'
        'first_open needs an evidence photo path relative to this directory.\n'
        'No CO2 column. Record temperature/humidity when available. Do not fabricate records.\n'
        'Configure model sample gates before independent evaluation. No scientific sufficiency threshold is assumed.\n', encoding='utf-8')
    return {'out':str(folder), 'status':'empty_templates_created'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates', action='store_true')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.templates:
        print(templates(args.out))
    elif args.input and args.settings:
        print(analyse(args.input, args.out, args.settings))
    else:
        parser.error('Use --templates or both --input and --settings')


if __name__ == '__main__':
    main()
