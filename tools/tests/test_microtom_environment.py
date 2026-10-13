"""Climate CSV, DLI, pointer resolution and 16-cell light validation (hand-computed fixtures)."""
from __future__ import annotations
import math
import uuid
from pathlib import Path

import pytest

from tools import microtom_environment as me
from tools.vtc_development import demo, prepare
from tools.vtc_development_io import TABLES, load_package
from tools.vtc_growth_io import ROOT, ContractError, read_json, rows, write_csv


def test_climate_csv_matches_v3_header_and_thermal_time(tmp_path):
    side = me.make_climate_csv(tmp_path, '2026-10-11T06:00:00+09:00', 5, t_base_c=5.7)
    table = rows(tmp_path / 'environment.csv', TABLES['environment.csv'])
    assert len(table) == 5 and table[0]['source_kind'] == 'user_stated' and table[3]['interval'] == '3'
    assert table[1]['start_time'] == '2026-10-12T06:00:00+09:00'
    assert math.isclose(side['thermal_time_dd_per_day'], 18.63, abs_tol=0.005)
    assert math.isclose(me.thermal_time_per_day(26, 22, 14, 5.7), 18.6333, abs_tol=1e-4)
    assert side['kind'] == 'set_points_not_logs' and side['rh_pct'] == 60 and side['lights_on_clock_time'] is None
    assert math.isclose(side['dli_factor_mol_per_umol_s'], 0.0504)


def test_climate_csv_accepted_by_v3_package():
    inputs = demo(ROOT / 'build' / ('microtom_env_test_' + uuid.uuid4().hex), intervals=4, rays=1000)
    req = read_json(inputs / 'request.json')
    me.make_climate_csv(inputs, req['start_time'], 4)
    assert load_package(inputs)['tables']['environment.csv'][0]['source_kind'] == 'user_stated'
    with pytest.raises(ContractError):
        me.make_climate_csv(inputs, '2026-10-11T06:00:00', 4)  # naive timestamp refused


def test_dli_is_derived_from_photoperiod(tmp_path):
    assert math.isclose(me.dli_from_ppfd(300, 14), 15.12)
    assert math.isclose(me.dli_from_ppfd(100, 16), 5.76)  # not a fixed 0.0504 for every photoperiod
    write_csv(tmp_path / 'light_input.csv', [dict(reference_ppfd_umol_m2_s=300, source_kind='user_assumed', measured_at='')])
    li = me.load_light_input(tmp_path / 'light_input.csv', 14)
    assert li['conditional'] is True and li['absolute_status'] == 'conditional_on_assumed_reference' and math.isclose(li['dli_mol_m2_d'], 15.12)
    write_csv(tmp_path / 'light_input.csv', [dict(reference_ppfd_umol_m2_s=250, source_kind='measured', measured_at='2026-10-20T10:00:00+09:00')])
    assert me.load_light_input(tmp_path / 'light_input.csv')['conditional'] is False
    write_csv(tmp_path / 'light_input.csv', [dict(reference_ppfd_umol_m2_s=250, source_kind='measured', measured_at='')])
    with pytest.raises(ContractError):
        me.load_light_input(tmp_path / 'light_input.csv')  # measured needs a timestamp


def _slot_csv(path: Path, ratios: list[float]) -> None:
    write_csv(path, [dict(slot_id=f'S{i}', tray='t', ratio_now=r, ratio_now_lo=r, ratio_now_hi=r) for i, r in enumerate(ratios)])


def test_pointer_resolution_and_loud_abort(tmp_path):
    _slot_csv(tmp_path / 'records' / 'a.csv' if (tmp_path / 'records').mkdir() is None else tmp_path / 'records' / 'a.csv', [0.9, 1.1])
    pointer = tmp_path / 'inputs' / 'light_ratio_latest.txt'; pointer.parent.mkdir()
    pointer.write_text('../records/a.csv\n', encoding='utf-8')
    res = me.resolve_ratio_pointer(pointer)
    assert res['schema'] == 'slot' and res['n_rows'] == 2 and res['role'] == 'comparison_only' and len(res['target_sha256']) == 64
    targets = me.slot_relative_targets(res, tray_base_factor=1.047)
    assert math.isclose(targets[0]['relative_target'], 0.9 / 1.047) and targets[0]['base'] == 'three_trays'
    write_csv(tmp_path / 'records' / 'bad.csv', [dict(slot='x', value=1)])
    pointer.write_text('../records/bad.csv\n', encoding='utf-8')
    with pytest.raises(ContractError, match='header'):
        me.resolve_ratio_pointer(pointer)
    pointer.write_text(str((tmp_path / 'records' / 'a.csv').resolve()) + '\n', encoding='utf-8')
    with pytest.raises(ContractError, match='relative'):
        me.resolve_ratio_pointer(pointer)
    pointer.write_text('../records/a.csv\n../records/a.csv\n', encoding='utf-8')
    with pytest.raises(ContractError, match='one line'):
        me.resolve_ratio_pointer(pointer)


def test_real_slot_file_resolves_if_present():
    target = ROOT / 'data/records/env_light_20261010/plant_slot_light_ratio_20261010.csv'
    if not target.exists():
        pytest.skip('human record not present')
    folder = ROOT / 'build' / ('microtom_ptr_test_' + uuid.uuid4().hex); folder.mkdir()
    import os
    (folder / 'light_ratio_latest.txt').write_text(Path(os.path.relpath(target, folder)).as_posix() + '\n', encoding='utf-8')
    res = me.resolve_ratio_pointer(folder / 'light_ratio_latest.txt')
    assert res['schema'] == 'slot' and Path(res['target']) == target.resolve()


def test_pointer_retarget_changes_only_frozen_ratio_and_hash():
    inputs = demo(ROOT / 'build' / ('microtom_ptr_a_' + uuid.uuid4().hex), intervals=2, rays=1000)
    a = prepare(inputs, ROOT / 'build' / ('microtom_ptr_run_a_' + uuid.uuid4().hex))
    write_csv(inputs / 'ratios_b.csv', [dict(grid_row=r, grid_col=c, ratio_to_mean=1.1 if (r + c) % 2 else 0.9) for r in range(1, 5) for c in range(1, 5)])
    (inputs / 'light_ratio_latest.txt').write_text('ratios_b.csv\n', encoding='utf-8')
    b = prepare(inputs, ROOT / 'build' / ('microtom_ptr_run_b_' + uuid.uuid4().hex))
    diff_frozen = {k for k in a['frozen_hashes'] if a['frozen_hashes'][k] != b['frozen_hashes'][k]}
    assert diff_frozen == {'resolved_ratio_target'}  # frozen pointer text is identical; only the ratio file and its hash moved
    diff_source = {k for k in a['source_hashes'] if a['source_hashes'].get(k) != b['source_hashes'].get(k)}
    assert diff_source == {'light_ratio_latest.txt', 'resolved_ratio_target'}
    assert a['parameter_hash'] == b['parameter_hash'] and a['binding']['engine_hash'] == b['binding']['engine_hash']


def _cells(values: list[float], key: str) -> list[dict]:
    out = []
    for i, v in enumerate(values):
        r, c = i // 4 + 1, i % 4 + 1
        out.append(dict(grid_row=r, grid_col=c, absorbed_umol_s=v * 0.0004, area_m2=0.0004) if key == 'sim' else dict(grid_row=r, grid_col=c, ratio_to_mean=v))
    return out


def test_light_validation_hand_computed(tmp_path):
    measured = [0.9] * 8 + [1.1] * 8  # mean 1.0 exactly
    write_csv(tmp_path / 'measured.csv', _cells(measured, 'meas'))
    write_csv(tmp_path / 'sim_const.csv', _cells([5.0] * 16, 'sim'))  # constant field -> ratio 1 everywhere
    s = me.light_validation(tmp_path / 'sim_const.csv', tmp_path / 'measured.csv', tmp_path / 'light_validation.csv')
    assert math.isclose(s['ratio_rmse'], 0.1) and s['pearson_r'] == 'unavailable' and s['absolute_calibration'] is False
    assert (tmp_path / 'light_validation.summary.json').exists() and len(rows(tmp_path / 'light_validation.csv')) == 16
    write_csv(tmp_path / 'sim_prop.csv', _cells([m * 123.4 for m in measured], 'sim'))  # proportional -> perfect shape match
    s = me.light_validation(tmp_path / 'sim_prop.csv', tmp_path / 'measured.csv')
    assert math.isclose(s['ratio_rmse'], 0, abs_tol=1e-12) and math.isclose(s['pearson_r'], 1.0)
    write_csv(tmp_path / 'sim_anti.csv', _cells([1.1] * 8 + [0.9] * 8, 'sim'))  # anti-correlated
    s = me.light_validation(tmp_path / 'sim_anti.csv', tmp_path / 'measured.csv')
    assert math.isclose(s['ratio_rmse'], 0.2) and math.isclose(s['pearson_r'], -1.0)
    s = me.light_validation(tmp_path / 'sim_const.csv', tmp_path / 'measured.csv', tray_base_factor=1.047)
    assert math.isclose(s['ratio_rmse'], math.sqrt(sum((1 - m / 1.047) ** 2 for m in measured) / 16))
    write_csv(tmp_path / 'short.csv', _cells(measured, 'meas')[:15])
    with pytest.raises(ContractError, match='16'):
        me.light_validation(tmp_path / 'sim_const.csv', tmp_path / 'short.csv')


def test_light_validation_against_v3_sensors_if_present(tmp_path):
    sensors = ROOT / 'build/vtc_dev_v3_delivery_sufficient/results/sensors.csv'
    grid = ROOT / 'data/records/env_light_20261010/light_ratio_map_20261010.csv'
    if not (sensors.exists() and grid.exists()):
        pytest.skip('V3 sensors or human grid record absent')
    s = me.light_validation(sensors, grid, tmp_path / 'lv.csv')
    assert s['n_cells'] == 16 and 0 <= s['ratio_rmse'] and -1 <= s['pearson_r'] <= 1 and s['lamp_placement_status'] == 'declared_guess'
