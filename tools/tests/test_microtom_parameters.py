"""Registry provenance and V3 request round-trip (software criteria only; no biological claim)."""
from __future__ import annotations
import csv
import uuid
from pathlib import Path

import pytest

from tools import microtom_parameters as mp
from tools.vtc_development import demo
from tools.vtc_development_io import PARAMS, load_package
from tools.vtc_growth_io import ROOT, ContractError, read_json, write_json


@pytest.fixture
def registry() -> list[dict]:
    return mp.load_registry()


def test_every_row_has_unit_source_kind_and_reference(registry):
    for r in registry:
        assert r['unit'] and r['source_kind'] in mp.SOURCE_KINDS and r['source_ref'] and r['uncertainty'], r['key']


def test_no_row_claims_measured(registry):
    assert all(r['source_kind'] != 'measured' for r in registry)


def test_required_rows_present(registry):
    keys = {r['key'] for r in registry}
    for k in ('FINAL_VEG_PHYT_NUM', 'SP_STOP_RULE', 'TRUSS_INTERVAL', 'NR_LEAFLET_PAIRS_BY_RANK', 'MIDDLE_PAIR_RAMP', 'CURVE_RATIO',
              'BENT_FRACTION', 'AREA_CORRECTION', 'INTERNODE_CAP', 'PHYLLOCHRON', 'T_BASE', 'DAYS_AT_START',
              'CAND_INTERNODE_LOGISTIC', 'CAND_INSERTION_ANGLE_CHEN7', 'CAND_AZIMUTH_SUCCESSION'):
        assert k in keys, k
    by = {r['key']: r for r in registry}
    assert by['INTERNODE_CAP']['value'] == 'unavailable' and '72' not in str(by['INTERNODE_CAP']['value'])
    assert by['BENT_FRACTION']['value'] == 'unavailable' and by['BENT_FRACTION']['source_kind'] == 'unavailable'
    assert by['CURVE_RATIO']['value'] == [1, 2, 2] and by['CURVE_RATIO']['source_kind'] == 'literature_other_cultivar'
    assert by['PHYLLOCHRON']['value'] == 37.9 and by['PHYLLOCHRON']['source_kind'] == 'literature_other_cultivar'
    assert by['T_BASE']['value'] == 5.7 and by['T_BASE']['source_kind'] == 'user_assumed'
    assert by['DAYS_AT_START']['value'] == 30 and by['DAYS_AT_START']['engine_status'] == 'layer_only'
    assert [1, 1, 2] in by['NR_LEAFLET_PAIRS_BY_RANK']['candidates'] and [1, 1, 3] in by['NR_LEAFLET_PAIRS_BY_RANK']['candidates']
    assert all(by[k]['engine_status'] == 'candidate' and by[k]['value'] == 'unavailable' for k in ('CAND_INTERNODE_LOGISTIC', 'CAND_INSERTION_ANGLE_CHEN7', 'CAND_AZIMUTH_SUCCESSION'))


def test_active_rows_map_to_engine_vocabulary(registry):
    for r in registry:
        if r['engine_status'] == 'active':
            assert r['engine_key'] in PARAMS and r['source_kind'] in mp.ENGINE_SOURCE_KINDS, r['key']
    assert 'literature_wild_species' not in {r['source_kind'] for r in registry if r['engine_status'] == 'active'}


def test_overrides_round_trip_into_valid_v3_request(registry):
    inputs = demo(ROOT / 'build' / ('microtom_param_test_' + uuid.uuid4().hex), intervals=2, rays=1000)
    req = read_json(inputs / 'request.json')
    overrides = mp.build_request_overrides(registry)
    assert set(overrides['parameters']) <= PARAMS
    assert [i['key'] for i in overrides['inactive_in_engine']] == ['CURVE_RATIO', 'BENT_FRACTION', 'AREA_CORRECTION']
    assert [i['engine_key'] for i in overrides['engine_default_retained']] == ['INTERNODE_CAP_M']
    new = mp.apply_overrides(req, overrides)
    assert new['parameters']['INTERNODE_CAP_M'] == req['parameters']['INTERNODE_CAP_M']  # retained, not invented
    assert new['parameters']['FIRST_LEAVES']['value'] == 9 and new['parameters']['BASE_C']['value'] == 5.7
    assert new['parameters']['PHYLLOCHRON_DD']['source_kind'] == 'literature_other_cultivar'
    write_json(inputs / 'request.json', new)
    pkg = load_package(inputs)  # V3's own contract validation
    assert pkg['request']['parameters']['PAIRS']['value'] == [1, 1, 2]


def test_member_sampling_is_seeded_and_inside_candidates(registry):
    a, b = mp.sample_member(registry, 11, 3), mp.sample_member(registry, 11, 3)
    assert a == b and set(a) == {'FINAL_VEG_PHYT_NUM', 'NR_LEAFLET_PAIRS_BY_RANK', 'MIDDLE_PAIR_RAMP'}
    by = {r['key']: r for r in registry}
    for k, v in a.items():
        assert v in by[k]['candidates']
    assert 'NR_LEAFLET_PAIRS_BY_RANK' not in mp.sample_member(registry, 11, 3, exclude=('NR_LEAFLET_PAIRS_BY_RANK',))
    draws = {tuple(sorted((k, str(v)) for k, v in mp.sample_member(registry, 11, i).items())) for i in range(40)}
    assert len(draws) > 1  # the scenario set is actually explored


def test_member_value_outside_candidates_rejected(registry):
    with pytest.raises(ContractError):
        mp.build_request_overrides(registry, {'FINAL_VEG_PHYT_NUM': 12})
    with pytest.raises(ContractError):
        mp.build_request_overrides(registry, {'PHYLLOCHRON': 30})  # not a candidate_set row


def _copy_registry_with(tmp_path: Path, **changes) -> Path:
    with mp.REGISTRY_PATH.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    for r in rows:
        if r['key'] in changes:
            r.update(changes[r['key']])
    out = tmp_path / 'registry.csv'
    with out.open('w', encoding='utf-8', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=list(mp.COLUMNS)); w.writeheader(); w.writerows(rows)
    return out


def test_registry_rejects_measured_or_unsourced(tmp_path):
    with pytest.raises(ContractError, match='measured'):
        mp.load_registry(_copy_registry_with(tmp_path, PHYLLOCHRON={'source_kind': 'measured'}))
    with pytest.raises(ContractError, match='source_ref'):
        mp.load_registry(_copy_registry_with(tmp_path, T_BASE={'source_ref': ''}))
    with pytest.raises(ContractError, match='not a V3 parameter'):
        mp.load_registry(_copy_registry_with(tmp_path, T_BASE={'engine_key': 'TBASE_TYPO'}))
    with pytest.raises(ContractError, match='unavailable'):
        mp.load_registry(_copy_registry_with(tmp_path, INTERNODE_CAP={'value': '72'}))
