"""Calibration contract tests: statistical failure modes and immutable integration."""
from copy import deepcopy
import json
import math
from pathlib import Path
import shutil
import uuid

import numpy as np
import pytest

from tools import growth_calibration as g
from tools.leaf_light.common import BUILD, StudyError, digest, file_hash, read_json, rows, write_json


@pytest.fixture
def folder():
    path = BUILD / ('test_growth_calibration_' + uuid.uuid4().hex)
    path.mkdir(parents=True)
    yield path
    # Only remove this test-owned, verified child of build/.
    assert path.resolve().is_relative_to(BUILD.resolve()) and path.name.startswith('test_growth_calibration_')
    shutil.rmtree(path)


@pytest.fixture
def fixture(folder):
    return g.synthetic_fixture(folder / 'inputs', replicates=3)


def edit_rows(obs, transform):
    manifest = read_json(obs); path = obs.parent / manifest['observations']['path']
    rr = rows(path); rr = transform(rr)
    g._csv(path, rr, tuple(rr[0]) if rr else g.COLUMNS)
    manifest['observations']['sha256'] = file_hash(path); write_json(obs, manifest)


def reasons(audit):
    return {x['reason_code'] for x in audit['missing_evidence']}


def test_blank_templates_do_not_invent_biology(folder):
    d = g.templates(folder / 'blank')
    p = read_json(d / 'fit_plan.json')
    a = g.audit_calibration_data(d / 'observations.json', d / 'treatments.json', p)
    assert a['status'] == 'unavailable' and a['record_count'] == 0
    assert p['parameters'] == {} and p['targets'] == []
    out = g.export_calibration(dict(status=a['status'], data_audit=a, fit_plan=p), folder / 'blank_audit')
    assert read_json(out / 'manifest.json')['seed'] is None


def test_joint_recovery_validation_immutability(fixture, folder):
    obs, p, tr, ev, ep = fixture
    before = file_hash(obs.parent / 'observations.csv')
    result = g.fit_growth_parameters(obs, ev, p, tr)
    s = result['parameter_set']
    assert result['status'] == 'synthetic_fitted'
    assert s['values']['D'] == pytest.approx(24, abs=.3)
    assert s['values']['k'] == pytest.approx(.12, abs=.004)
    assert s['values']['light_beta'] == pytest.approx(.25, abs=.015)
    assert all(set(x['values']) == {'D', 'k', 'light_beta'} for x in s['particles'])
    assert np.asarray(s['covariance']).shape == (3, 3)
    validation = g.validate_parameter_set(s, obs, ep)
    assert validation['status'] == 'synthetic_evaluated'
    assert s['validation_status'] == 'unevaluated'  # caller object is immutable
    assert not validation['parameter_set']['accepted_for_domain']
    assert {r['horizon_days'] for r in validation['validation']} >= {7, 14, 21, 30}
    assert any(r['metric'] == 'persistence_absolute_error' for r in validation['validation'])
    assert any(r['metric'] == 'observation_predictive_coverage' for r in validation['validation'])
    assert file_hash(obs.parent / 'observations.csv') == before
    out = g.export_calibration(result, folder / 'result')
    assert all((out / n).exists() for n in ('evidence_registry.json', 'fit_plan.json', 'parameter_set.json',
                 'data_audit.json', 'fit_diagnostics.csv', 'validation.csv', 'requirements.csv', 'manifest.json'))
    manifest = read_json(out / 'manifest.json')
    assert all(file_hash(out / n) == h for n, h in manifest['artifact_hashes'].items())
    with pytest.raises(StudyError, match='already exists'): g.export_calibration(result, out)


def test_reproducible_bootstrap(fixture):
    obs, p, tr, ev, ep = fixture
    a = g.fit_growth_parameters(obs, ev, p, tr)['parameter_set']
    b = g.fit_growth_parameters(obs, ev, p, tr)['parameter_set']
    assert a == b


def test_endpoint_only_rejected(fixture):
    obs, p, tr, ev, ep = fixture
    edit_rows(obs, lambda rr: [r for r in rr if r['elapsed_days'] == '30'])
    assert 'endpoint_only_cannot_identify_dynamics' in reasons(g.audit_calibration_data(obs, tr, p))


def test_pseudoreplication_rejected(fixture):
    obs, p, tr, ev, ep = fixture
    edit_rows(obs, lambda rr: [dict(r, unit_id='train-unit-' + str(int(r['ppfd_umol_m2_s'] == '300.0'))) if r['split'] == 'train' else r for r in rr])
    assert 'insufficient_independent_treatment_units' in reasons(g.audit_calibration_data(obs, tr, p))


def test_collinear_ppfd_dli_rejected(fixture):
    obs, p, tr, ev, ep = fixture
    f = deepcopy(p['targets'][0]['features'][0]); f.update(column='dli', coefficient='dli_beta', unit='mol/m2/day', scale=5., center=10., domain=[1., 30.])
    p['targets'][0]['features'].append(f); p['parameters']['dli_beta'] = deepcopy(p['parameters']['light_beta'])
    edit_rows(obs, lambda rr: [dict(r, dli=float(r['ppfd_umol_m2_s']) * .0576) for r in rr])
    m = read_json(obs); m['feature_units']['dli'] = 'mol/m2/day'; write_json(obs, m)
    assert 'collinear_response_terms' in reasons(g.audit_calibration_data(obs, tr, p))


def test_constant_environment_cannot_identify_response(fixture):
    obs, p, tr, ev, ep = fixture
    edit_rows(obs, lambda rr: [dict(r, ppfd_umol_m2_s=200.) for r in rr])
    assert 'constant_input_cannot_identify_response' in reasons(g.audit_calibration_data(obs, tr, p))


@pytest.mark.parametrize('change,match', [
    (lambda p: p['parameters']['k'].update(unit='1/degree_day'), 'unit mismatch'),
    (lambda p: p['split']['validation_plants'].append(p['split']['train_plants'][0]), 'leakage'),
    (lambda p: p['split']['validation_units'].append(p['split']['train_units'][0]), 'leakage'),
    (lambda p: p['parameters']['D'].update(bounds=[0, 60]), 'positive bounds'),
    (lambda p: p['targets'][0]['observation_error'].update(within_series_rho=1), 'correlation'),
])
def test_invalid_plans_fail(fixture, change, match):
    obs, p, tr, ev, ep = fixture
    change(p)
    with pytest.raises(StudyError, match=match): g.audit_calibration_data(obs, tr, p)


def test_missing_sd_not_zero_error(fixture):
    obs, p, tr, ev, ep = fixture
    edit_rows(obs, lambda rr: [dict(r, measurement_sd='') for r in rr])
    assert 'measurement_error_missing' in reasons(g.audit_calibration_data(obs, tr, p))


def test_changed_support_not_growth(fixture):
    obs, p, tr, ev, ep = fixture
    edit_rows(obs, lambda rr: [dict(r, coverage_basis='partial') for r in rr])
    assert 'incomparable_coverage' in reasons(g.audit_calibration_data(obs, tr, p))


def test_real_data_requires_scientific_review(fixture):
    obs, p, tr, ev, ep = fixture
    m = read_json(obs); m['data_kind'] = 'observed'; write_json(obs, m)
    assert 'scientific_review_missing' in reasons(g.audit_calibration_data(obs, tr, p))


def test_no_scenario_training_exposure(fixture):
    obs, p, tr, ev, ep = fixture
    edit_rows(obs, lambda rr: [dict(r, exposure_kind='assumed') for r in rr])
    assert 'training_exposure_not_observed' in reasons(g.audit_calibration_data(obs, tr, p))


def test_optimizer_failure_not_parameters(fixture):
    obs, p, tr, ev, ep = fixture
    p['optimizer']['maxiter'] = 1
    result = g.fit_growth_parameters(obs, ev, p, tr)
    assert result['status'] == 'fit_failed' and result['parameter_set'] is None


def test_evidence_endpoint_rate_and_units(fixture):
    obs, p, tr, ev, ep = fixture
    ev['records'][1]['evidence_role'] = 'endpoint'
    with pytest.raises(StudyError, match='Endpoint'): g.fit_growth_parameters(obs, ev, p, tr)
    ev['records'][1]['evidence_role'] = 'fitted_parameter'; ev['records'][1]['unit'] = 'deg'
    with pytest.raises(StudyError, match='unit mismatch'): g.fit_growth_parameters(obs, ev, p, tr)


def test_registry_preserves_unknown_uncertainty(fixture):
    ev = fixture[3]
    records, issues = g.validate_evidence_registry(ev)
    assert not issues and records[0]['uncertainty'] is None
    ev['records'][0]['uncertainty'] = dict(kind='unknown', value=0)
    with pytest.raises(StudyError, match='distinguish'): g.validate_evidence_registry(ev)


def test_source_hash_guard(fixture):
    obs, p, tr, ev, ep = fixture
    with (obs.parent / 'observations.csv').open('a') as f: f.write('\n')
    with pytest.raises(StudyError, match='hash mismatch'): g.audit_calibration_data(obs, tr, p)


def test_validation_no_future_training_or_promotion(fixture):
    obs, p, tr, ev, ep = fixture
    s = g.fit_growth_parameters(obs, ev, p, tr)['parameter_set']
    s['training_observed_until'] = '2026-03-01T00:00:00+00:00'
    with pytest.raises(StudyError, match='predates'): g.validate_parameter_set(s, obs, ep)
    s['accepted_for_domain'] = True
    with pytest.raises(StudyError, match='promotion'): g.validate_parameter_set(s, obs, ep)


def test_circular_likelihood_wrap():
    t = dict(family='azimuth_rotation', parameters={'D': 'D', 'k': 'k'}, features=[], observation_error={'kappa': 50.})
    r = dict(target_id='angle', initial_value=math.pi - .01, elapsed_days=10., value=-math.pi + .01)
    a = g._loss({'D': .02 / (1 - math.exp(-1)), 'k': .1}, [r], {'angle': t})
    r['value'] += 2 * math.pi
    b = g._loss({'D': .02 / (1 - math.exp(-1)), 'k': .1}, [r], {'angle': t})
    assert a == pytest.approx(b)


def test_event_censoring_probability_and_stopping():
    t = dict(family='lognormal_wait', reference_day=1., parameters={'mu': 'mu', 'sigma': 'sigma', 'stop': 'stop'}, features=[])
    values = {'mu': math.log(5.), 'sigma': .3, 'stop': .2}
    interval = dict(lower_day=0., upper_day=5., censoring='interval')
    right = dict(lower_day=5., upper_day=None, censoring='right')
    assert math.exp(g._event_log_probability(t, values, interval)) == pytest.approx(.4)
    assert math.exp(g._event_log_probability(t, values, right)) == pytest.approx(.6)
    assert math.exp(g._event_log_probability(t, values, dict(right, lower_day=1e6))) == pytest.approx(.2)
    assert g._event_log_probability(t, dict(values, stop=1.), interval) == -math.inf


def test_export_empty_cells_not_unavailable(folder):
    r = dict(status='unavailable', requirements=[g._issue('data', 'missing')])
    out = g.export_calibration(r, folder / 'empty')
    assert rows(out / 'requirements.csv')[0]['source'] == ''
    assert read_json(out / 'parameter_set.json') is None


def test_engine_binding_preserves_origin_and_dependency(fixture, folder):
    from tools import probabilistic_compound_growth as engine
    obs, p, tr, ev, ep = fixture
    origin, model = engine.synthetic_fixture(folder / 'engine_inputs')
    # Test explicit existing-family binding only. Other process assumptions stay supplied.
    base = model['parameter_particles'][0]
    family = next(iter(base['existing_blocks'].values()))
    p['engine_bindings'] = [dict(kind='physical_location' if any(x['name'] == coord for x in base['coordinates']) else 'constant', target_id='length', role=role, family=family,
                                 coordinate=coord, unit=unit) for role, coord, unit in
                                 [('D', 'D_length_mm', 'mm'), ('k', 'k_length', '1/development_day')]]
    s = g.fit_growth_parameters(obs, ev, p, tr)['parameter_set']
    model['environment_scenario']['values'] = {'ppfd_umol_m2_s': 200.}
    before = deepcopy(model)
    config = g.apply_parameter_set(s, model, model['environment_scenario']['values'])
    assert model == before
    assert len(config['parameter_particles']) == len(s['particles']) * len(model['parameter_particles'])
    bank = engine.sample_forecast(origin, config)
    assert bank['trajectories']
    states = engine.decode_trajectory(bank['trajectories'][0], [0, 7, 30])
    assert all(not state['optical_eligible'] for state in states)
    zero = next(r for r in states if r['elapsed_days'] == 0 and r['source_compound_leaf_id'])
    assert zero['rachis_arc_length_mm'] == origin['blocks'][0]['rachis_arc_length_mm']
    with pytest.raises(StudyError, match='clock'):
        g.apply_parameter_set(s, dict(model, clock={'kind': 'piecewise_constant'}), model['environment_scenario']['values'])


def special_fixture(fixture, family):
    obs, p, tr, ev, ep = fixture
    t = p['targets'][0]; t['features'] = []; t['family'] = family
    p['parameters'].pop('light_beta')
    if family == 'azimuth_rotation':
        t.update(unit='rad', angle_reference='parent_local_azimuth')
        t['observation_error'] = dict(kind='von_mises', kappa=200., source_ref='synthetic_fixture')
        p['parameters']['D'].update(initial=.4, bounds=[.05, 2.], unit='rad', source_ref='fixture_rad')
        ev['records'].append(dict(ev['records'][0], id='fixture_rad', unit='rad', angle_reference='parent_local_azimuth'))
        def transform(rr):
            for r in rr:
                r.update(unit='rad', initial_value=3.0)
                v = 3 + .6 * (1 - math.exp(-.12 * float(r['elapsed_days'])))
                r['value'] = math.atan2(math.sin(v), math.cos(v))
            return rr
        edit_rows(obs, transform)
        m = read_json(obs); m['target_metadata'] = {'length': {'angle_reference': 'parent_local_azimuth'}}; write_json(obs, m)
    else:
        t.update(unit='calendar_day', reference_day=1., event_endpoint='residual_wait', parameters={'mu': 'mu', 'sigma': 'sigma', 'stop': 'stop'})
        p['parameters'] = {
            'mu': dict(status='fit', initial=1.3, bounds=[.1, 3.], unit='log(calendar_day/reference_day)', transform='identity', source_ref='fixture_mu', bounds_source='fixture'),
            'sigma': dict(status='fixed', value=.3, unit='dimensionless', transform='log', source_ref='fixture_dimensionless'),
            'stop': dict(status='fixed', value=0., unit='probability', transform='identity', source_ref='fixture_probability')}
        ev['records'].extend([dict(ev['records'][0], id='fixture_mu', unit='log(calendar_day/reference_day)'), dict(ev['records'][0], id='fixture_probability', unit='probability')])
        def transform(rr):
            for i, r in enumerate(rr):
                q = (i % 5 + .5) / 5
                event_day = float(g.lognorm.ppf(q, .3, scale=5.))
                r.update(unit='calendar_day', organ_id='event-' + str(i), lower_day=event_day - .1, upper_day=event_day + .1,
                         censoring='interval', visibility_status='confirmed', value='', initial_value='')
                if float(r['elapsed_days']) < event_day + .1:
                    r.update(lower_day=float(r['elapsed_days']), upper_day='', censoring='right')
            return rr
        edit_rows(obs, transform)
    ep['plan_hash'] = digest(p)
    return obs, p, tr, ev, ep


@pytest.mark.parametrize('family', ['azimuth_rotation', 'lognormal_wait'])
def test_declared_angular_and_event_fits(fixture, family):
    obs, p, tr, ev, ep = special_fixture(fixture, family)
    result = g.fit_growth_parameters(obs, ev, p, tr)
    assert result['parameter_set'] is not None, result
    if family == 'azimuth_rotation':
        assert result['parameter_set']['values']['D'] == pytest.approx(.6, abs=.02)
        assert result['parameter_set']['values']['k'] == pytest.approx(.12, abs=.01)
    else:
        assert result['parameter_set']['values']['mu'] == pytest.approx(math.log(5), abs=.2)
    v = g.validate_parameter_set(result['parameter_set'], obs, ep)
    assert any(r['value'] is not None for r in v['validation'])


def test_occlusion_not_censoring(fixture):
    obs, p, tr, ev, ep = special_fixture(fixture, 'lognormal_wait')
    edit_rows(obs, lambda rr: [dict(r, visibility_status='occluded') for r in rr])
    assert 'event_visibility_unconfirmed' in reasons(g.audit_calibration_data(obs, tr, p))


def test_angular_reference_mismatch_unavailable(fixture):
    obs, p, tr, ev, ep = special_fixture(fixture, 'azimuth_rotation')
    m = read_json(obs); m['target_metadata']['length']['angle_reference'] = 'upper_angle_to_stem'; write_json(obs, m)
    assert 'angle_reference_mismatch' in reasons(g.audit_calibration_data(obs, tr, p))


def test_partial_target_fit_does_not_invent_missing_target(fixture):
    obs, p, tr, ev, ep = fixture
    missing = deepcopy(p['targets'][0]); missing['id'] = 'area'
    p['targets'].append(missing)
    result = g.fit_growth_parameters(obs, ev, p, tr)
    assert result['parameter_set']['eligible_targets'] == ['length']
    assert result['data_audit']['status'] == 'partially_available'


def test_rank_failure_not_calibration(fixture):
    obs, p, tr, ev, ep = fixture
    # Two indistinguishable coefficients for a role, with different columns but
    # nonlinear model ambiguity not caught solely by the environment design.
    p['parameters']['unused'] = deepcopy(p['parameters']['D'])
    data, context = g._load(obs)
    target = p['targets'][0]
    target['parameters']['unused_role'] = 'unused'
    value, diag = g._fit_once([r for r in data if r['split'] == 'train'], p, ['length'])
    assert value is None and diag['status'] == 'nonidentifiable'


def _width_model(folder):
    from tools import probabilistic_compound_growth as engine
    origin, model = engine.synthetic_fixture(folder / 'engine_inputs')
    base = model['parameter_particles'][0]
    family = next(iter(base['existing_blocks'].values()))
    model['environment_scenario']['values'] = {'ppfd_umol_m2_s': 200.}
    return model, base, family


@pytest.mark.parametrize('coordinate', ['left_target_mm', 'right_target_mm'])
def test_same_unit_increment_to_absolute_width_rejected(fixture, folder, coordinate):
    obs, p, tr, ev, ep = fixture
    model, base, family = _width_model(folder)
    kind = 'physical_location' if any(x['name'] == coordinate for x in base['coordinates']) else 'constant'
    p['engine_bindings'] = [dict(kind=kind, target_id='length', role='D', family=family, coordinate=coordinate, unit='mm')]
    s = g.fit_growth_parameters(obs, ev, p, tr)['parameter_set']
    before = deepcopy(model)
    with pytest.raises(StudyError, match='meaning mismatch'):
        g.apply_parameter_set(s, model, model['environment_scenario']['values'])
    assert model == before


def test_rate_to_increment_rejected_even_if_units_checked_later(fixture, folder):
    obs, p, tr, ev, ep = fixture
    model, base, family = _width_model(folder)
    p['engine_bindings'] = [dict(kind='constant', target_id='length', role='k', family=family, coordinate='D_area_cm2', unit='cm2')]
    s = g.fit_growth_parameters(obs, ev, p, tr)['parameter_set']
    with pytest.raises(StudyError, match='meaning mismatch'):
        g.apply_parameter_set(s, model, model['environment_scenario']['values'])


def test_undeclared_coordinate_meaning_refused():
    with pytest.raises(StudyError, match='undeclared'):
        g._check_binding_meaning({'family': 'anchored_expansion'}, 'D', 'length_x_max_mm')


def test_valid_meanings_pass():
    for coordinate in ('D_length_mm', 'D_segment_mm', 'D_area_cm2'):
        g._check_binding_meaning({'family': 'anchored_expansion'}, 'D', coordinate)
    for coordinate in ('k_length', 'k_width', 'k_area', 'k_segment'):
        g._check_binding_meaning({'family': 'anchored_expansion'}, 'k', coordinate)
    g._check_binding_meaning({'family': 'azimuth_rotation'}, 'D', 'rotation_z_rad')
