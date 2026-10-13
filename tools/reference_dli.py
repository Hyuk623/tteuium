"""Reference incident DLI: measured routes, frozen predictions, and simulation readiness."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from tools.leaf_light.common import DLI_UNIT, StudyError, file_hash, output_dir, read_json, write_json
from tools.reference_dli_contract import (DAILY_COLUMNS, READING_COLUMNS, Missing, association,
    dates_and_geometry, evidence, number, read_readings, select_readings, survey_tolerance)
from tools.reference_dli_intervals import dated_schedule, daily_logged, daily_spot, spot_scale, mean_support_timeline
from tools.reference_dli_policy import ambient_evidence, choose_value, domain, sensor_flags

SOURCE_KINDS = {'logged': 'measured_logged', 'spot_schedule': 'measured_spot_schedule', 'simulated': 'simulated'}


def _tissue_ids(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith('area_basis_id') and isinstance(item, str): result.add(item)
            if key.endswith('area_basis_ids') and isinstance(item, list):
                result.update(x for x in item if isinstance(x, str))
            result.update(_tissue_ids(item))
    elif isinstance(value, list):
        for item in value: result.update(_tissue_ids(item))
    return result


def _track(path: Path, hashes: dict) -> Path:
    path = path.resolve()
    hashes[str(path)] = file_hash(path)
    return path


def code_hashes() -> dict:
    root = Path(__file__).resolve().parent
    return {str(path): file_hash(path) for path in [
        root/'reference_dli.py', root/'reference_dli_frozen.py', root/'reference_dli_contract.py', root/'reference_dli_intervals.py',
        root/'reference_dli_policy.py', root/'reference_dli_consumer.py', root/'light_time.py', root/'leaf_light/common.py', root/'light_growth_bridge.py',
        root/'compound_growth.py', root.parent/'tomato3d/light/scene.py'] if path.is_file()}


def _empty_day(local_date: str | None, reason: str) -> dict:
    return dict(local_date=local_date, start_at=None, end_at=None, duration_s=None,
        on_duration_s=None, coverage_status='schedule_missing' if 'schedule' in reason or 'clock' in reason else 'incomplete',
        dli_mol_m2_day=None, mean_ppfd_umol_m2_s=None, n_readings=0,
        included_reading_ids=[], integration_segments=[], gaps=[], reason=reason)


def _optional_policy_evidence(position: dict, base: Path, hashes: dict) -> None:
    for field, label in [('transition_source_ref', 'transition_support'),
                         ('interval_mean_split_source_ref', 'interval_mean_split'),
                         ('dimming_source_ref', 'dimming_response')]:
        if position.get(field) is not None:
            evidence(position[field], base, hashes, label)


def simulation_reason(scene: dict | None) -> str:
    fixtures = (scene or {}).get('fixtures')
    if not fixtures: return 'lamp_ppf_missing'
    for fixture in fixtures:
        ppf = fixture.get('photon_flux_umol_s')
        if isinstance(ppf, dict): ppf = ppf.get('value')
        if ppf is None: return 'lamp_ppf_missing'
        number(ppf, 'photon_flux_umol_s', 0)
    return 'simulation_execution_deferred'


def prepare_record(position_path: Path, schedule_path: Path, *, route: str,
                   readings_path: Path | None = None, survey_path: Path | None = None,
                   scene_path: Path | None = None, tissue_manifest: Path | None = None,
                   frozen_prediction: Path | None = None) -> tuple[dict, dict]:
    """Compute without writing; Missing yields auditable unavailability, malformed inputs fail.

    Evidence paths are resolved relative to reference_position.json. Input/code
    hashes describe this run and must not be rewritten when implementation changes.
    """
    if route not in SOURCE_KINDS: raise StudyError('invalid_reference_route')
    if frozen_prediction is not None:
        if route != 'simulated' or any(x is not None for x in (readings_path, survey_path, scene_path)):
            raise StudyError('frozen_prediction_requires_separate_simulated_route')
        from tools.reference_dli_frozen import prepare
        return prepare(position_path, schedule_path, frozen_prediction, tissue_manifest)
    hashes: dict = {}
    position_path = _track(position_path, hashes)
    schedule_path = _track(schedule_path, hashes)
    p, schedule = read_json(position_path), read_json(schedule_path)
    base = position_path.parent
    tissue = _tissue_ids(read_json(_track(tissue_manifest, hashes))) if tissue_manifest else set()
    # Validate scientific data before attempting availability gates: negative or
    # non-photon measurements must never be hidden by another missing field.
    readings = read_readings(_track(readings_path, hashes), p) if readings_path else []
    survey = read_readings(_track(survey_path, hashes), p, survey=True) if survey_path else []
    scene = read_json(_track(scene_path, hashes)) if scene_path else None
    selected_dates = p.get('dates') or []
    days = {d: _empty_day(d, 'inputs_not_ready') for d in selected_dates}
    selection = dict(included_reading_ids=[], excluded_readings=[], survey_reading_ids=[r['reading_id'] for r in survey])
    audit: dict = dict(schema_version='reference-dli-audit-1', selection=selection, schedule=None,
                      position_tolerance=None, plant_association=None, ambient={}, integration={})
    applicability = None
    reasons: list[str] = []
    reduction = dict(status='unavailable', value=None, candidate_value=None, value_rule=p.get('value_rule'),
                     fixed_over_horizon=None, days_used=[], days_not_used=[], reasons=[])
    try:
        dates, _ = dates_and_geometry(p, base, hashes, tissue)
        selected_dates = dates
        _optional_policy_evidence(p, base, hashes)
        if route == 'simulated':
            raise Missing(simulation_reason(scene))
        try:
            timeline = dated_schedule(p, schedule, dates)
        except Missing as exc:
            if route != 'logged': raise
            timeline = mean_support_timeline(p, dates, str(exc))
        audit['schedule'] = timeline
        mode = p.get('gradient_exposure_basis')
        if mode == 'scheduled_on_duration':
            if any(day['on_duration_s'] is None for day in timeline['days'].values()):
                raise Missing('gradient_scheduled_duration_unavailable')
            effective_s = max(day['on_duration_s'] for day in timeline['days'].values())
            if route == 'spot_schedule': effective_s *= spot_scale(p, timeline)['factor']
        elif mode == 'full_elapsed_day' and route == 'logged':
            effective_s = max(day['duration_s'] for day in timeline['days'].values())
        else:
            raise Missing('gradient_temporal_exposure_basis_missing')
        tolerance = survey_tolerance(p, survey, effective_s, base, hashes)
        audit['position_tolerance'] = tolerance
        accepted, excluded = select_readings(p, readings, tolerance)
        selection.update(included_reading_ids=[r['reading_id'] for r in accepted], excluded_readings=excluded)
        # Retain computed daily audit values even when association/domain evidence
        # later prevents a usable whole-plant input.
        audit['ambient'] = ambient_evidence(p, accepted, dates, base, hashes)
        integration = (daily_logged(p, readings, set(selection['included_reading_ids']), timeline)
                       if route == 'logged' else daily_spot(p, accepted, timeline))
        audit['integration'] = integration
        days = integration['days']
        for d in dates:
            if audit['ambient'][d]['contradictory_reading_ids']:
                reasons.append('ambient_none_contradicted_by_lights_off_reading')
        try:
            audit['plant_association'] = association(p, tolerance, base, hashes)
        except Missing as exc:
            reasons.append(str(exc))
        try:
            applicability = domain(p, base, hashes)
        except Missing as exc:
            reasons.append(str(exc))
        reduction = choose_value(p, days, applicability, base, hashes)
        reasons.extend(reduction['reasons'])
    except Missing as exc:
        reasons.append(str(exc))
        if not audit['integration']:
            days = {d: _empty_day(d, str(exc)) for d in selected_dates}
    if not days:
        days = {'unselected': _empty_day(None, reasons[0] if reasons else 'date_selection_missing')}
    # Simulation readiness must always name the transport limitation, even when
    # missing real geometry/schedule prevents earlier common readiness checks.
    if route == 'simulated':
        reasons.append(simulation_reason(scene))
    flags = sensor_flags(p)
    for d, day in days.items():
        ambient = audit['ambient'].get(d, dict(ambient_light='asserted_not_measured',
            ambient_light_declared=p.get('ambient_light'), evidence_status='asserted_not_measured', reading_ids=[]))
        audit['ambient'][d] = ambient
        value = day['dli_mol_m2_day']
        app_status = ('unavailable' if value is None or applicability is None else
                      'in_applicability' if applicability['min'] <= value <= applicability['max'] else 'out_of_applicability')
        day.update(basis_id=p.get('basis_id'), source_kind=SOURCE_KINDS[route],
            ambient_light=ambient['ambient_light'], ambient_light_declared=ambient['ambient_light_declared'],
            applicability_low=applicability['min'] if applicability else None,
            applicability_high=applicability['max'] if applicability else None, applicability_status=app_status,
            cosine_corrected=p.get('cosine_corrected', 'unknown'), levelled=p.get('levelled'), flags=list(flags))
    if reasons:
        reduction.update(value=None, status='out_of_applicability' if set(reasons) == {'out_of_applicability'} else 'unavailable')
        if reduction['status'] == 'unavailable' and reduction.get('fixed_over_horizon') is True:
            reduction['fixed_over_horizon'] = None
    record = dict(schema_version='reference-dli-result-1', quantity='incident', model_scope='whole_plant',
        unit=DLI_UNIT, basis_id=p.get('basis_id'), source_kind=SOURCE_KINDS[route], time_basis='complete_local_day',
        spatial_basis='declared_reference_position_horizontal_plane', **reduction)
    record.update(reasons=sorted(set(reasons)), reference={key: p.get(key) for key in (
        'frame_id', 'coordinate_frame', 'position_mm', 'sensor_normal', 'plane', 'height_basis', 'source_ref',
        'cosine_corrected', 'cosine_source_ref', 'levelled', 'level_source_ref')}, timezone=p.get('timezone'),
        dst_policy=p.get('dst_policy'), ambient_light=audit['ambient'], days=days,
        applicability_interval=[applicability['min'], applicability['max']] if applicability else [None, None],
        applicability_domain=applicability, applicability_source_ref=p.get('applicability_source_ref'),
        plant_association=audit['plant_association'], operating_metadata=p.get('operating_metadata'),
        source_hashes=hashes, code_hashes=code_hashes(),
        inputs=dict(position=str(position_path), schedule=str(schedule_path),
            readings=str(readings_path.resolve()) if readings_path else None,
            survey=str(survey_path.resolve()) if survey_path else None,
            scene=str(scene_path.resolve()) if scene_path else None,
            tissue_manifest=str(tissue_manifest.resolve()) if tissue_manifest else None),
        disclosures=['incident_reference_sensor_not_tissue_average', 'not_a_growth_or_physiology_prediction',
                     'synthetic_software_validation_does_not_establish_physical_accuracy'])
    return record, audit


def save_result(record: dict, audit: dict, out: Path) -> dict:
    folder = output_dir(out)
    write_json(folder/'integration_evidence.json', audit)
    with (folder/'reference_dli.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=DAILY_COLUMNS)
        writer.writeheader()
        for day in record['days'].values():
            row = {key: day.get(key) for key in DAILY_COLUMNS}
            row['flags'] = '|'.join(row['flags'])
            writer.writerow(row)  # None is deliberately an empty daily numeric field.
    record = dict(record, artifact_hashes={name: file_hash(folder/name) for name in
                                         ('integration_evidence.json', 'reference_dli.csv')})
    write_json(folder/'reference_dli.json', record)
    return dict(status=record['status'], reasons=record['reasons'], out=str(folder),
                result_sha256=file_hash(folder/'reference_dli.json'))


def templates(out: Path) -> dict:
    folder = output_dir(out)
    p = dict(schema_version='reference-dli-1', unit=DLI_UNIT, reading_unit='umol/m2/s', basis_id=None,
        frame_id=None, coordinate_frame=None, position_mm=[None, None, None], sensor_normal=[0, 0, 1],
        plane='horizontal', height_basis=None, timezone='Asia/Seoul', dates=[], dst_policy=None,
        source_ref=None, cosine_corrected='unknown', cosine_source_ref=None, levelled=None, level_source_ref=None,
        ambient_light=None, daytime_ambient_reading_ids=[], daytime_source_ref=None,
        output_constant=None, output_fraction=1., measurement_output_fraction=None,
        applicability_interval_mol_m2_day=[None, None], applicability_source_ref=None,
        value_rule=None, representative_date=None, fixed_horizon_tolerance=None,
        position_tolerance=None, gradient_exposure_basis=None, plant_association=None,
        logger_sample_semantics=None, max_gap_seconds=None, transition_policy=None, transition_source_ref=None,
        max_schedule_minutes=100000, operating_metadata=dict(fixture_count=3, daily_on_hours=16,
            output_fraction=1., provenance='user_confirmed', actual_clock_windows_confirmed=False))
    write_json(folder/'reference_position.json', p)
    write_json(folder/'schedule.json', dict(timezone='Asia/Seoul', dates=[], provenance=None,
        fixed_optics_beam_spectrum=None, fixtures={f'LED-{i:02}': [dict(start_hhmm=None, end_hhmm=None,
            output_fraction=1.)] for i in range(1, 4)}))
    for name in ('reference_readings.csv', 'spot_survey.csv'):
        with (folder/name).open('w', encoding='utf-8', newline='') as stream:
            csv.writer(stream).writerow(READING_COLUMNS)
    return dict(status='incomplete_blank_real_templates', out=str(folder))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    t = sub.add_parser('templates'); t.add_argument('--out', type=Path, required=True)
    empirical = sub.add_parser('empirical')
    for name in ('field', 'configuration', 'positions', 'operation', 'out'):
        empirical.add_argument('--'+name, type=Path, required=True)
    for command in ('compute', 'simulate'):
        cmd = sub.add_parser(command)
        for name in ('position', 'schedule', 'out'):
            cmd.add_argument('--'+name, type=Path, required=True)
        cmd.add_argument('--tissue-manifest', type=Path)
        if command == 'compute':
            cmd.add_argument('--route', choices=('logged', 'spot_schedule'), required=True)
            cmd.add_argument('--readings', type=Path, required=True)
            cmd.add_argument('--survey', type=Path)
        else:
            group = cmd.add_mutually_exclusive_group(required=True)
            group.add_argument('--scene', type=Path)
            group.add_argument('--frozen-prediction', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'templates': result = templates(args.out)
        elif args.command == 'empirical':
            from tools.reference_dli_empirical import run as run_empirical
            record = run_empirical(args.field, args.configuration, args.positions, args.operation, args.out)
            result = dict(status=record['status'], positions=len(record['positions']), out=str(args.out))
        else:
            record, audit = prepare_record(args.position, args.schedule,
                route=args.route if args.command == 'compute' else 'simulated',
                readings_path=getattr(args, 'readings', None), survey_path=getattr(args, 'survey', None),
                scene_path=getattr(args, 'scene', None), tissue_manifest=args.tissue_manifest,
                frozen_prediction=getattr(args, 'frozen_prediction', None))
            result = save_result(record, audit, args.out)
        print(result)
        return 0
    except (StudyError, OSError, ValueError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
