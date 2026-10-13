"""Synthetic arithmetic checks; fixture coefficients are not crop recommendations."""
import copy
import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools import monthly_growth as model


def scenario() -> dict:
    p = model.blank_input()
    p['initial_stem_height_mm'] = 100
    p['initial_compounds'] = [dict(compound_id='fixture_leaf', attachment_height_mm=50,
        azimuth_deg=0, elevation_deg=-30, axis_length_mm=10, blade_width_mm=6,
        area_cm2=2, unfolded_fraction=.2)]
    p['growth'] = dict(stem_mm_per_dev_day=2, stem_max_mm=140, axis_mm_per_dev_day=3,
        axis_max_mm=50, width_mm_per_dev_day=2, width_max_mm=30, area_cm2_per_dev_day=.5,
        area_max_cm2=12, unfolding_per_dev_day=.1, elevation_deg_per_dev_day=5,
        elevation_target_deg=20)
    p['emergence'] = dict(enabled=True, next_dev_day=.5, interval_dev_days=2,
        first_azimuth_deg=40, divergence_deg=100, birth=dict(elevation_deg=-10,
        axis_length_mm=0, blade_width_mm=0, area_cm2=0, unfolded_fraction=0))
    for d in p['days']:
        d['development_multiplier'] = 1
    return p


def test_initial_state_preservation_and_month():
    p = scenario(); original = copy.deepcopy(p)
    r = model.simulate(p)
    assert p == original
    assert len(r['frames']) == 31
    assert r['frames'][-1]['day'] == 30
    leaf = r['frames'][0]['compounds'][0]
    for key, val in p['initial_compounds'][0].items():
        assert leaf[key] == val
    assert leaf['tip_xyz_mm'][2] == pytest.approx(45)
    assert leaf['birth_calendar_day'] is None  # Existing leaf age is unknown.
    assert r['frames'][0]['date'] is None
    assert r['validated_growth'] is False and r['suitable_for_ppfd'] is False


def test_partial_day_event_has_only_remaining_time_to_grow():
    r = model.simulate(scenario())
    leaf = r['frames'][1]['compounds'][1]
    assert leaf['birth_calendar_day'] == .5
    assert leaf['attachment_height_mm'] == 101
    assert leaf['axis_length_mm'] == 1.5
    assert leaf['unfolded_fraction'] == .05
    assert r['frames'][2]['compounds'][1]['attachment_height_mm'] == 101
    assert r['frames'][30]['compound_count'] == 16


def test_stopped_clock_and_fractional_multiplier():
    p = scenario()
    for d in p['days']: d['development_multiplier'] = 0
    r = model.simulate(p)
    assert r['frames'][30]['stem_height_mm'] == 100
    assert r['frames'][30]['compounds'] == r['frames'][0]['compounds']
    p['days'][1]['development_multiplier'] = 2
    r = model.simulate(p)
    assert r['frames'][2]['compounds'][1]['birth_calendar_day'] == 1.25
    assert r['frames'][2]['compounds'][1]['axis_length_mm'] == 4.5


def test_bounds_and_target_angle_both_directions():
    p = scenario(); p['emergence']['enabled'] = False
    r = model.simulate(p)
    end = r['frames'][30]
    assert end['stem_height_mm'] == 140
    leaf = end['compounds'][0]
    assert [leaf[k] for k in ['axis_length_mm', 'blade_width_mm', 'area_cm2', 'unfolded_fraction', 'elevation_deg']] == [50,30,12,1,20]
    p['growth']['elevation_target_deg'] = -60
    assert model.simulate(p)['frames'][30]['compounds'][0]['elevation_deg'] == -60


def test_event_on_day_boundary_has_no_extra_growth():
    p = scenario(); p['emergence']['next_dev_day'] = 1
    r = model.simulate(p)
    leaf = r['frames'][1]['compounds'][1]
    assert leaf['birth_calendar_day'] == 1
    assert leaf['axis_length_mm'] == 0
    p['days'][1]['development_multiplier'] = 0
    assert model.simulate(p)['frames'][2]['compound_count'] == 2


def test_optional_metadata_environment_and_calendar():
    p = scenario()
    p['metadata']['start_date'] = '2026-10-03'
    r = model.simulate(p)
    assert r['frames'][30]['date'] == '2026-11-02'
    assert r['frames'][1]['environment']['ppfd_umol_m2_s'] is None
    changed = copy.deepcopy(p)
    changed['metadata']['cultivar'] = 'not fitted'
    changed['days'][0]['temperature_c'] = 35
    changed['days'][0]['ppfd_umol_m2_s'] = 999
    alt = model.simulate(changed)
    assert alt['frames'][-1]['compounds'] == r['frames'][-1]['compounds']


def test_explicit_environment_curves_multiply_with_daily_clock():
    p = scenario()
    p['response'] = {'mode': 'curves', 'curves': {
        'temperature_c': [{'value': 10, 'multiplier': 0}, {'value': 30, 'multiplier': 1}],
        'ppfd_umol_m2_s': [{'value': 0, 'multiplier': 0}, {'value': 100, 'multiplier': 1}]}}
    for d in p['days']:
        d.update(temperature_c=20, ppfd_umol_m2_s=50, development_multiplier=2)
    r = model.simulate(p)
    assert r['frames'][1]['development_days'] == .5
    assert r['frames'][1]['environment']['response_factors'] == {'temperature_c': .5, 'ppfd_umol_m2_s': .5}
    assert r['frames'][1]['compounds'][1]['birth_calendar_day'] == 1
    assert r['frames'][30]['development_days'] == 15
    p['days'][0]['temperature_c'] = 10
    assert model.simulate(p)['frames'][1]['development_days'] == 0


@pytest.mark.parametrize('value', [None, 9, 31])
def test_response_requires_environment_inside_supplied_domain(value):
    p = scenario()
    p['response'] = {'mode': 'curves', 'curves': {'temperature_c': [
        {'value': 10, 'multiplier': 0}, {'value': 30, 'multiplier': 1}]}}
    for d in p['days']: d['temperature_c'] = 20
    p['days'][0]['temperature_c'] = value
    with pytest.raises(ValueError): model.simulate(p)


def test_response_does_not_sort_duplicate_knots_or_invent_curve():
    p = scenario(); p['response']['mode'] = 'curves'
    with pytest.raises(ValueError): model.simulate(p)
    p['response']['curves'] = {'temperature_c': [
        {'value': 20, 'multiplier': 0}, {'value': 20, 'multiplier': 1}]}
    with pytest.raises(ValueError): model.simulate(p)


@pytest.mark.parametrize('bad', [None, float('nan'), float('inf'), -1, True, '2'])
def test_reject_invalid_expansion(bad):
    p = scenario(); p['growth']['axis_mm_per_dev_day'] = bad
    with pytest.raises(ValueError): model.simulate(p)


def test_blank_template_does_not_run_or_invent_defaults():
    p = model.blank_input()
    assert all(d['development_multiplier'] is None for d in p['days'])
    assert all(v is None for v in p['growth'].values())
    with pytest.raises(ValueError): model.simulate(p)


@pytest.mark.parametrize('change', [
    lambda p: p['metadata'].update(sowing_date='2026-10-04', start_date='2026-10-03'),
    lambda p: p['days'][0].update(day=2),
    lambda p: p['days'].pop(),
    lambda p: p['emergence'].update(interval_dev_days=0),
    lambda p: p['emergence'].update(interval_dev_days=.001),
    lambda p: p['initial_compounds'].append(copy.deepcopy(p['initial_compounds'][0])),
    lambda p: p['initial_compounds'][0].update(attachment_height_mm=101),
    lambda p: p['growth'].update(area_max_cm2=1),
    lambda p: p['emergence']['birth'].update(unfolded_fraction=2),
    lambda p: p['days'][0].update(photoperiod_h=25),
])
def test_reject_ambiguous_or_impossible_inputs(change):
    p = scenario(); change(p)
    with pytest.raises(ValueError): model.simulate(p)


def test_export_traceable_and_non_overwriting(tmp_path, monkeypatch):
    monkeypatch.setattr(model, 'BUILD_ROOT', tmp_path)
    p = scenario(); r = model.simulate(p); out = tmp_path / 'run'
    model.export_result(p, r, out)
    saved = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    for name, digest in saved['files'].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    with (out / 'daily.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 31 and rows[-1]['compound_count'] == '16'
    assert '__MONTHLY_BOOT__' not in (out / 'viewer.html').read_text(encoding='utf-8')
    with pytest.raises(FileExistsError): model.export_result(p, r, out)
    with pytest.raises(ValueError): model.export_result(p, r, tmp_path.parent / 'outside')


def test_json_script_text_cannot_break_saved_page():
    p = scenario(); p['metadata']['cultivar'] = '</script><script>alert(1)</script>'
    html = model.page(p, model.simulate(p))
    assert p['metadata']['cultivar'] not in html
    assert '\\u003c/script>' in html
