"""Explicit synthetic fixtures for reference-DLI software validation, never real observations."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from tools.leaf_light.common import DLI_UNIT, file_hash, output_dir, write_json
from tools.reference_dli_contract import READING_COLUMNS


def write_readings(path: Path, readings: list[dict]) -> None:
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=READING_COLUMNS)
        writer.writeheader(); writer.writerows(readings)


def row(rid: str, at: str, q: float | None, xyz=(0., 0., 200.), state='on', **extra) -> dict:
    return dict(reading_id=rid, measured_at=at, ppfd_umol_m2_s=q,
        position_x_mm=xyz[0], position_y_mm=xyz[1], position_z_mm=xyz[2],
        sensor_model='SYNTHETIC-METER', sensor_serial='SYNTHETIC-ONLY', lights_state=state,
        notes='Synthetic software fixture; no physical measurement', **extra)


def create_inputs(folder: Path, route: str = 'spot_schedule') -> dict:
    """Fixture values/policies are deliberately explicit and are not CLI defaults."""
    folder.mkdir(parents=True, exist_ok=False)
    policy = dict(source_kind='synthetic_test_only', description='Predeclared test evidence, not cultivar or sensor validation',
                  unit=DLI_UNIT, coefficient_domain=dict(min=0., max=30., unit=DLI_UNIT))
    write_json(folder/'synthetic_evidence.json', policy)
    ref = dict(path='synthetic_evidence.json', sha256=file_hash(folder/'synthetic_evidence.json'))
    p = dict(schema_version='reference-dli-1', unit=DLI_UNIT, reading_unit='umol/m2/s', basis_id='synthetic_reference',
        frame_id='synthetic_grow', coordinate_frame='grow_mm_z_up', position_mm=[0., 0., 200.],
        sensor_normal=[0, 0, 1], plane='horizontal', height_basis='synthetic_fixed_height_from_floor',
        source_ref=ref, cosine_corrected=True, cosine_source_ref=ref, levelled=True, level_source_ref=ref,
        timezone='Asia/Seoul', dates=['2026-10-04'], dst_policy='utc_elapsed',
        ambient_light='none', output_constant=True, output_fraction=1., measurement_output_fraction=1.,
        daytime_ambient_reading_ids=[], daytime_source_ref=None,
        applicability_interval_mol_m2_day=[0., 30.], applicability_source_ref=dict(ref, json_pointer='/coefficient_domain'),
        value_rule='single_representative_day', representative_date='2026-10-04',
        fixed_horizon_tolerance=dict(spread_metric='max_minus_min', value=.5, unit=DLI_UNIT, source_ref=ref),
        position_tolerance=dict(method='affine_horizontal_survey', allowable_dli_error_mol_m2_day=.1,
            survey_plane_tolerance_mm=0., max_fit_residual_umol_m2_s=1e-10, source_ref=ref, temporal_transfer_source_ref=ref),
        gradient_exposure_basis='scheduled_on_duration',
        plant_association=dict(plant_instance_ids=['synthetic_plant'], association_evidence=ref,
            uniformity_basis=dict(source_ref=ref)),
        logger_sample_semantics='instantaneous', max_gap_seconds=3600,
        transition_policy='hold_observed_endpoint_on_each_side', transition_source_ref=ref,
        max_schedule_minutes=10000, operating_metadata=dict(fixture_count=3, daily_on_hours=16,
            output_fraction=1., provenance='synthetic_clocks_user_confirmed_duration_not_real_measurement'))
    schedule = dict(timezone='Asia/Seoul', dates=['2026-10-04'], provenance={'source_kind':'synthetic'},
        fixed_optics_beam_spectrum=True, fixtures={fid: [dict(start_hhmm='06:00', end_hhmm='22:00', output_fraction=1.)]
        for fid in ('LED-01', 'LED-02', 'LED-03')})
    readings = ([row(str(hour), f'2026-10-04T{hour:02}:00:00+09:00', 200. if 6 <= hour < 22 else 0.,
                     state='on' if 6 <= hour < 22 else 'off') for hour in range(24)]
                + [row('24', '2026-10-05T00:00:00+09:00', 0., state='off')]) if route == 'logged' else [
        row('a', '2026-10-04T12:00:00+09:00', 190.), row('b', '2026-10-04T12:00:30+09:00', 200.),
        row('c', '2026-10-04T12:01:00+09:00', 210.)]
    survey = [row('survey-'+str(i), '2026-10-04T12:00:00+09:00', 200.+.1*x, (x, y, 200.))
              for i, (x, y) in enumerate([(-10., -10.), (10., -10.), (10., 10.), (-10., 10.)])]
    write_json(folder/'reference_position.json', p); write_json(folder/'schedule.json', schedule)
    write_readings(folder/'reference_readings.csv', readings); write_readings(folder/'spot_survey.csv', survey)
    return dict(position=p, schedule=schedule, readings=readings, survey=survey, source_ref=ref)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--route', choices=['logged', 'spot_schedule'], required=True)
    args = parser.parse_args(argv)
    parent = output_dir(args.out)
    create_inputs(parent/'inputs', args.route)
    print(dict(status='synthetic_inputs_only', out=str(parent/'inputs')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
