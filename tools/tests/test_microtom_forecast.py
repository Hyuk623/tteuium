"""Forecast-layer software criteria (spec §12): reproducibility, id namespace, immutability, provenance, labels, scope.

The deterministic tests consume existing verified V3 results (acceptance scenarios) so they need no Java;
the native test runs V3 through the forecast layer and is skipped when GroIMP or Java is absent.
"""
from __future__ import annotations
import json
import shutil
import uuid
from pathlib import Path

import pytest

from tools import microtom_forecast as mf
from tools import microtom_forecast_io as fio
from tools.vtc_growth_io import ROOT, ContractError, read_json, rows, sha

ACCEPTANCE = ROOT / 'build' / 'vtc_dev_v3_acceptance_01'
RESULT_RUNS = [ACCEPTANCE / 'sufficient', ACCEPTANCE / 'three_pairs']


def _have_results() -> bool:
    return all((r / 'results' / 'manifest.json').exists() and (r / 'inputs' / 'request.json').exists() for r in RESULT_RUNS)


def _root() -> Path:
    return ROOT / 'build' / ('microtom_fc_test_' + uuid.uuid4().hex)


def _scenario(**kw) -> dict:
    s = mf.default_scenario('seed_route', horizons_days=[1, 3, 7], members=2, seed=11, rays=300000, diagnostic=True)
    s.update(kw)
    return s


@pytest.fixture
def issued() -> Path:
    if not _have_results():
        pytest.skip('verified V3 acceptance results absent')
    return mf.issue(_scenario(), out_root=_root(), date='20261011', existing_results=RESULT_RUNS)


def _frozen_files(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}


def test_reproducibility_same_inputs_same_files(issued):
    again = mf.issue(_scenario(), out_root=_root(), date='20261011', existing_results=RESULT_RUNS)
    assert again.name == issued.name  # separate roots -> same run id -> comparable bytes
    assert _frozen_files(again) == _frozen_files(issued)
    a, b = read_json(issued / 'manifest.json'), read_json(again / 'manifest.json')
    assert a['artifact_hashes'] == b['artifact_hashes'] and a['input_snapshot_sha256'] == b['input_snapshot_sha256']
    assert {k for k in a if a[k] != b[k]} <= {'issued_at'}


def test_forecast_ids_never_collide_with_observed_or_source_ids(issued):
    mtg = fio.read_table(issued / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    fids = {r['forecast_id'] for r in mtg}
    source = {r['source_organ_id'] for r in mtg} | {r['rooted_at_vertex_id'] for r in mtg}
    assert fids and all(f.startswith('F:' + issued.name + ':') for f in fids)
    assert not (fids & source)
    for member in rows(issued / 'members.csv'):
        states = rows(Path(ROOT / member['results_dir'] if not Path(member['results_dir']).is_absolute() else member['results_dir']) / 'states.csv')
        assert not (fids & {s['organ_id'] for s in states})
    assert rows(issued / 'forecast_map.csv') == []  # header only at issue
    assert all(r['status'] == 'generated_candidate' for r in mtg)


def test_previous_forecasts_preserved_and_write_once(issued):
    before = _frozen_files(issued); manifest_before = (issued / 'manifest.json').read_bytes()
    second = mf.issue(_scenario(), out_root=issued.parent, date='20261011', existing_results=RESULT_RUNS)
    assert second.name == 'forecast_20261011_02' and second != issued
    assert _frozen_files(issued) == before and (issued / 'manifest.json').read_bytes() == manifest_before
    fio.verify_forecast(issued); fio.verify_forecast(second)
    with pytest.raises(ContractError, match='already issued'):
        fio.finalize(issued, read_json(issued / 'manifest.json'))
    (issued / 'forecast_intervals.csv').write_text('tampered', encoding='utf-8')
    with pytest.raises(ContractError, match='changed'):
        fio.verify_forecast(issued)


def test_status_labels_and_scope(issued):
    m = read_json(issued / 'manifest.json')
    assert m['run_status'] == 'assumption_conditioned' and m['evaluation_status'] == 'evaluated_unaccepted'
    assert m['conditional_simulation'] is True and m['topology_scope'] == 'provided_axes' and m['completeness'] == 'unavailable'
    assert m['direction_mechanisms'] == dict(fixed_generation='active_user_assumed', extrapolated_observed_change='unavailable', tropism='not_modelled')
    assert m['ensemble']['spread_kind'] == 'declared_scenario_set' and m['ensemble']['calibrated_probability'] is False
    assert m['engine'] == 'v3_direct' and m['engine_scope'] == 'single_plant_no_canopy' and m['sowing_source'] == 'assumed_issue_minus_days_at_start'
    assert m['growth_accuracy_status'].startswith('not_testable')
    for p in issued.rglob('*'):
        if p.is_file() and p.suffix in ('.csv', '.json'):
            assert 'accepted_for_domain' not in p.read_text(encoding='utf-8'), p
    unresolved = {r['quantity']: r for r in fio.read_table(issued / 'unresolved.csv', fio.UNRESOLVED_COLUMNS)}
    assert unresolved['tropism']['status'] == 'not_modelled' and unresolved['side_shoot_emergence']['status'] == 'unavailable'
    assert unresolved['CURVE_RATIO']['status'] == 'inactive_in_engine' and unresolved['INTERNODE_CAP']['status'] == 'unavailable'
    assert 'baselines' in unresolved and unresolved['baselines']['reason'].startswith('blocked_by_preconditions')


def test_zero_unsourced_defaults(issued):
    assumptions = fio.read_table(issued / 'forecast_assumptions.csv', fio.ASSUMPTION_COLUMNS)
    assert assumptions and all(a['source_kind'] and a['source_ref'] for a in assumptions)
    assert all(a['source_kind'] != 'measured' for a in assumptions)
    engine_keys = {a['engine_key'] for a in assumptions} | {a['symbol'] for a in assumptions}
    for member in rows(issued / 'members.csv'):
        req = read_json(Path(member['inputs_dir']) / 'request.json') if Path(member['inputs_dir']).is_absolute() else read_json(issued / member['inputs_dir'] / 'request.json')
        missing = set(req['parameters']) - engine_keys
        assert not missing, missing  # every engine parameter traces to a registry or v3_default_retained row
    symbols = {a['symbol'] for a in assumptions}
    assert {'CLIMATE_DAY_C', 'CLIMATE_NIGHT_C', 'CLIMATE_PHOTOPERIOD_H', 'CO2_PPM', 'REFERENCE_PPFD', 'DLI_DERIVED', 'RATIO_POINTER_TARGET', 'LAMP:L1:power_umol_s'} <= symbols
    by = {a['symbol']: a for a in assumptions}
    assert by['INTERNODE_CAP']['value'] == '"unavailable"' and by['INTERNODE_CAP_M']['origin'] == 'v3_default_retained'
    assert by['CURVE_RATIO']['engine_status'] == 'inactive_in_engine' and by['CAND_AZIMUTH_SUCCESSION']['source_kind'] == 'literature_wild_species'
    for r in fio.read_table(issued / 'forecast_intervals.csv', fio.INTERVAL_COLUMNS):
        assert r['source_kind'] == 'user_assumed' and r['calibrated'] == 'False' and r['interval_kind'] == 'declared_scenario_envelope'


def test_no_compound_envelope_and_full_outline(issued):
    mtg = fio.read_table(issued / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    assert not any(r['surface_role'] == 'compound_envelope' for r in mtg)
    leaflets = [r for r in mtg if r['class'] == 'Leaflet']
    assert leaflets and all(r['area_basis'] == 'full_outline' and r['surface_role'] == 'individual_leaflet_polygon' for r in leaflets)
    assert all(r['direction_mechanism'] == 'fixed_generation' for r in mtg)
    assert all(r['frame'] == 'plant_local_mm' for r in mtg)


def test_aggregation_envelopes_and_events(issued):
    iv = fio.read_table(issued / 'forecast_intervals.csv', fio.INTERVAL_COLUMNS)
    for r in iv:
        assert float(r['interval_low']) <= float(r['point']) <= float(r['interval_high'])
        assert 0 < float(r['presence_probability']) <= 1 and r['n_members'] == '2'
    assert any(r['presence_probability'] == '0.5' for r in iv)  # three_pairs member has organs the other lacks
    assert all(r['probability_basis'] in fio.PROBABILITY_BASIS for r in fio.read_table(issued / 'forecast_events.csv', fio.EVENT_COLUMNS))
    plant = {(r['quantity'], r['horizon_day']): r for r in iv if r['forecast_id'].endswith(':p1/Plant')}
    assert plant[('compounds', '1')]['days_after_sowing'] == '31' and plant[('compounds', '7')]['days_after_sowing'] == '37'
    ev = fio.read_table(issued / 'forecast_events.csv', fio.EVENT_COLUMNS)
    kinds = {r['event_type'] for r in ev}
    assert {'new_compound', 'new_truss', 'apex_stop', 'new_internode'} <= kinds and any(k.startswith('organ_initiation:') for k in kinds)
    for r in ev:
        assert 0 <= float(r['probability']) <= 1 and r['probability_kind'] == 'member_fraction_declared_scenario_set'
        if r['probability'] == '0.0':
            assert r['timing_day_median'] == 'unavailable'


def test_horizon_longer_than_results_is_refused():
    if not _have_results():
        pytest.skip('verified V3 acceptance results absent')
    with pytest.raises(ContractError, match='too short'):
        mf.issue(_scenario(horizons_days=[1, 60]), out_root=_root(), date='20261011', existing_results=RESULT_RUNS)


def test_failed_issue_leaves_marker_not_forecast():
    if not _have_results():
        pytest.skip('verified V3 acceptance results absent')
    root = _root()
    with pytest.raises(ContractError):
        mf.issue(_scenario(ensemble=dict(size=3, seed=1)), out_root=root, date='20261011', existing_results=RESULT_RUNS)
    folder = root / 'forecast_20261011_01'
    assert (folder / 'FAILED.json').exists() and not (folder / 'manifest.json').exists()
    with pytest.raises(FileNotFoundError):
        fio.verify_forecast(folder)


def test_new_forecast_dir_numbering(tmp_path):
    root = ROOT / 'build' / ('microtom_dir_test_' + uuid.uuid4().hex)
    a = fio.new_forecast_dir(root, '20261011'); b = fio.new_forecast_dir(root, '20261011'); c = fio.new_forecast_dir(root, '20261012')
    assert (a.name, b.name, c.name) == ('forecast_20261011_01', 'forecast_20261011_02', 'forecast_20261012_01')
    with pytest.raises(ContractError):
        fio.new_forecast_dir(ROOT / 'tools' / 'not_a_build_dir')  # outside build/: refused before any mkdir
    assert not (ROOT / 'tools' / 'not_a_build_dir').exists()


def _native_available() -> bool:
    from tools.groimp_light_sanity import CORE
    return CORE.is_file() and shutil.which('java') is not None


def test_native_fixture_route_issue_and_phase():
    source = ROOT / 'build' / 'vtc_dev_v3_delivery_sufficient'
    if not (_native_available() and (source / 'results' / 'manifest.json').exists()):
        pytest.skip('GroIMP/Java or the verified V3 source run is absent')
    s = mf.default_scenario('stage2_fixture', horizons_days=[1], members=2, seed=5, rays=300000,
                            source_run='build/vtc_dev_v3_delivery_sufficient', fixture_day=30, diagnostic=True)
    s['lights_on_clock_time'] = '06:00'
    folder = mf.issue(s, out_root=_root(), date='20261011')
    m = fio.verify_forecast(folder)
    assert m['input_snapshot_kind'] == 'stage2_observation_fixture' and m['engine_runtime']['member_source'] == 'native_v3_run'
    assert m['engine'] == 'v3_direct' and m['issue_class'] == 'diagnostic' and m['engine_runtime']['quantitative_light_sampling'] is False
    assert m['photoperiod_phase']['time_since_lights_on_min_at_boundaries'] == 0
    assert 'NR_LEAFLET_PAIRS_BY_RANK' in m['ensemble']['excluded_parameters']  # B3: inventory check binds PAIRS on a fixture
    for member in rows(folder / 'members.csv'):
        req = read_json(folder / member['inputs_dir'] / 'request.json')
        assert req['initialization_route'] == 'stage2_observation_fixture' and req['forecast_layer']['inactive_in_engine'] == ['CURVE_RATIO', 'BENT_FRACTION', 'AREA_CORRECTION']
        assert req['parameters']['PAIRS']['value'] == [1, 1, 2]  # fixture inventory keeps the source PAIRS
        results = read_json(folder / member['results_dir'] / 'manifest.json')
        assert results['software_status'] == 'verified_native_trajectory' and results['run_status'] == 'assumption_conditioned'
    mtg = fio.read_table(folder / 'forecast_mtg.csv', fio.MTG_COLUMNS)
    assert {r['root_relation'] for r in mtg} >= {'continuation'}
    cont = [r for r in mtg if r['root_relation'] == 'continuation']
    assert all(r['rooted_at_vertex_id'] == r['source_organ_id'] for r in cont)
    new = [r for r in mtg if r['root_relation'] == 'new_organ']
    assert all(r['rooted_at_vertex_id'] != r['source_organ_id'] for r in new)
