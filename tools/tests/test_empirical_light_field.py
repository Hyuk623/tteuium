from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools import empirical_light_field as field_api
from tools.empirical_canopy import directions, intercept
from tools.leaf_light import common
from tools.leaf_light.common import StudyError, digest, file_hash, read_json, write_json, write_rows
from tools.reference_dli_consumer import validate_result
from tools.reference_dli_empirical import run


@pytest.fixture
def setup_field(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    evidence = tmp_path/'evidence.json'; write_json(evidence, {'fixture': True})
    config = dict(board={'width_cm': 60, 'depth_cm': 40}, tray={'count': 3},
        lamp={'position_on_board': [300, 200], 'height_above_board_cm': 30, 'bar_length_cm': 50, 'bar_spacing_cm': 5},
        environment={'enclosure': 'synthetic'}, canopy_grid={'width_cm': 42, 'depth_cm': 28},
        empirical_contract=dict(coordinate_frame='grow', height_basis='shelf_floor', source_kind='fixture_truth',
            tray_bounds_xy_mm=[70, 490, 70, 350], coordinate_variant='as_recorded', plants_above_150_mm=False,
            conditional_reasons=['fixture_not_physical'], source_refs=[{'path': str(evidence), 'sha256': file_hash(evidence)}],
            direction_source_kind='user_assumed', direction_bars=[{'start_mm': [290, 200, 300], 'stop_mm': [310, 200, 300]}]))
    configuration = tmp_path/'configuration.json'; write_json(configuration, config)
    data = [dict(plane_id=str(z), plane_height_cm=z/10, grid_row=i, grid_col=j,
                 x_cm=x/10, y_cm=y/10, ppfd_umol_m2_s=2*x+3*y+4*z)
        for z in (70, 150) for i, x in enumerate((100, 450)) for j, y in enumerate((90, 330))]
    grid = tmp_path/'grid.csv'; write_rows(grid, data, list(data[0]))
    field = field_api.freeze(grid, configuration, tmp_path/'field')
    return tmp_path, config, configuration, field


def scene(field):
    return dict(schema_version='empirical-canopy-1', coordinate_frame='grow', source_kind='fixture_truth',
        source_ref='synthetic test geometry', configuration_sha256=field['configuration_sha256'],
        direction_source_kind='user_assumed', diffuse_fractions=[.5, .6, .7],
        leaf_transmittance=.5, leaf_transmittance_source_ref='synthetic test',
        quadrature=dict(bar_samples=5, dome_mu_samples=8, dome_phi_samples=16,
                        max_pairs_per_chunk=7, max_total_pairs=1000000), triangles=[],
        receivers=[dict(receiver_id='r', leaf_id='leaf', position_mm=[300, 200, 100], normal=[0, 0, 1],
                        supported_one_sided_area_m2=.01, own_triangle=-1)])


def test_nodes_and_affine_interpolation(setup_field):
    _, _, path, field = setup_field
    loaded = field_api.load_field(path.parent/'field/field.json', path)
    for sample in field['samples']:
        value = field_api.evaluate(loaded, [sample[k] for k in ('x_mm', 'y_mm', 'z_mm')])
        assert value['ppfd_umol_m2_s'] == sample['ppfd_umol_m2_s']
        assert value['source_kind'] == 'derived'
    assert field_api.evaluate(field, [300, 200, 110])['ppfd_umol_m2_s'] == pytest.approx(1640, abs=1e-12, rel=1e-12)


@pytest.mark.parametrize('xyz', [[300, 200, 150.0001], [300, 200, 69.999], [99, 200, 100],
                                  [451, 200, 100], [300, 89, 100], [300, 331, 100], [500, 200, 100]])
def test_refuse_extrapolation(setup_field, xyz):
    with pytest.raises(StudyError): field_api.evaluate(setup_field[3], xyz)


@pytest.mark.parametrize('section,key,value', [('board', 'width_cm', 61), ('tray', 'count', 4),
    ('lamp', 'position_on_board', [300, 201]), ('lamp', 'height_above_board_cm', 31),
    ('lamp', 'bar_length_cm', 49), ('lamp', 'bar_spacing_cm', 6),
    ('environment', 'enclosure', 'changed'), ('canopy_grid', 'width_cm', 43)])
def test_config_change_refused(setup_field, section, key, value):
    root, config, _, _ = setup_field
    changed = deepcopy(config); changed[section][key] = value
    path = root/'changed.json'; write_json(path, changed)
    with pytest.raises(StudyError, match='configuration_changed'):
        field_api.load_field(root/'field/field.json', path)


def test_no_silent_missing_or_duplicate_samples(setup_field):
    data = setup_field[3]['samples']
    for broken in (data[:-1], data+[data[0]]):
        with pytest.raises(StudyError): field_api.grids(broken)


def test_direction_normalization_and_scenario_spread(setup_field):
    field = setup_field[3]; s = scene(field)
    bars = field['configuration']['empirical_contract']['direction_bars']
    u, w, v, d = directions(np.array([300, 200, 100]), bars, s['quadrature'])
    assert np.sum(w*u[:, 2]) == pytest.approx(1, abs=1e-12, rel=1e-12)
    assert np.sum(d*v[:, 2]) == pytest.approx(1, abs=1e-12, rel=1e-12)
    result = intercept(field, s)
    for row in result['receivers']:
        assert row['upper_ppfd_umol_m2_s'] == pytest.approx(1600, abs=1e-10, rel=1e-12)
        assert row['lower_ppfd_umol_m2_s'] == 0
    s['receivers'][0]['normal'] = [1, 0, 0]
    result = intercept(field, s)
    assert len(result['leaves']) == 3 and result['spreads'][0]['spread_ppfd_umol_m2_s'] > 0


def test_physical_leaf_crossings_unknown_tau_and_zero(setup_field):
    field = setup_field[3]; s = scene(field)
    vertices = [[-10000, -10000, 140], [10000, -10000, 140], [10000, 10000, 140]]
    s['triangles'] = [dict(role='leaf', surface_id='shade', vertices_mm=vertices),
        dict(role='leaf', surface_id='shade', vertices_mm=[vertices[0], vertices[2], [-10000, 10000, 140]])]
    out = intercept(field, s)
    assert all(r['upper_ppfd_umol_m2_s'] == pytest.approx(800, abs=1e-10, rel=1e-12) for r in out['receivers'])
    # Same physical surface triangles must count once, even at a shared edge.
    s['leaf_transmittance'] = None
    assert all(r['status'] == 'unavailable' for r in intercept(field, s)['receivers'])
    zero = deepcopy(field)
    for r in zero['samples']: r['ppfd_umol_m2_s'] = 0
    assert all(r['intercepted_flux_umol_s'] == 0 for r in intercept(zero, s)['receivers'])


def test_own_triangle_and_area_weighting(setup_field):
    field = setup_field[3]; s = scene(field)
    s['triangles'] = [dict(role='leaf', surface_id='leaf', vertices_mm=[[-10000,-10000,140],[10000,-10000,140],[0,10000,140]])]
    s['receivers'][0]['own_triangle'] = 0
    s['leaf_transmittance'] = None
    s['receivers'].append(dict(s['receivers'][0], receiver_id='r2', position_mm=[200,200,100], supported_one_sided_area_m2=.03))
    out = intercept(field, s)
    for row in out['leaves']:
        assert row['intercepted_flux_umol_s'] == pytest.approx(58, abs=1e-10, rel=1e-12)
        assert row['mean_ppfd_umol_m2_s'] == pytest.approx(1450, abs=1e-10, rel=1e-12)


def test_walls_resource_limits_and_missing_pose_refused(setup_field):
    field = setup_field[3]; s = scene(field)
    s['triangles'] = [dict(role='wall')]
    with pytest.raises(StudyError, match='no_walls'): intercept(field, s)
    s['triangles'] = []; s['quadrature']['max_total_pairs'] = 1
    with pytest.raises(StudyError, match='resource_budget'): intercept(field, s)
    field['configuration']['empirical_contract']['direction_bars'] = None
    with pytest.raises(StudyError, match='direction_geometry'): intercept(field, s)


def make_dli(setup_field):
    root, _, configuration, _ = setup_field
    p = root/'positions.csv'
    write_rows(p, [dict(position_id='inside', x_mm=300, y_mm=200, z_mm=110),
                   dict(position_id='above', x_mm=300, y_mm=200, z_mm=151)],
               ('position_id', 'x_mm', 'y_mm', 'z_mm'))
    operation = root/'operation.json'
    write_json(operation, dict(daily_on_hours=14, output_fraction=1, measurement_output_fraction=1,
        constant_during_on=True, source_kind='user_stated', source_ref='user 30cm 14h 100%'))
    run(root/'field/field.json', configuration, p, operation, root/'dose')
    return root/'dose/reference_dli.json'


def test_independent_reference_consumer(setup_field, monkeypatch):
    path = make_dli(setup_field)
    monkeypatch.setattr(field_api, 'evaluate', lambda *_: pytest.fail('consumer must not use producer'))
    result = validate_result(path, current_configuration=setup_field[2])
    assert result['valid'] and result['positions'] == 2 and result['value'] is None
    record = read_json(path)
    assert record['positions'][0]['dli_mol_m2_day'] == pytest.approx(1640*14*.0036)
    assert record['positions'][1]['dli_mol_m2_day'] is None
    with pytest.raises(StudyError, match='requires_current_configuration'): validate_result(path)


@pytest.mark.parametrize('key,value', [('source_kind','simulated'), ('method','measured'), ('value',10),
                                      ('model_scope','whole_plant'), ('time_basis','complete_local_day')])
def test_consumer_rejects_provenance_promotion(setup_field, key, value):
    path = make_dli(setup_field); record = read_json(path); record[key] = value; write_json(path, record)
    with pytest.raises(StudyError): validate_result(path, current_configuration=setup_field[2])


def test_independent_arithmetic_tamper_even_with_new_artifact_hash(setup_field):
    path = make_dli(setup_field); record = read_json(path)
    record['positions'][0]['dli_mol_m2_day'] += 1
    write_rows(path.parent/'reference_dli.csv', record['positions'], list(record['positions'][0]))
    record['artifact_hashes']['reference_dli.csv'] = file_hash(path.parent/'reference_dli.csv')
    write_json(path, record)
    with pytest.raises(StudyError, match='arithmetic_mismatch'): validate_result(path, current_configuration=setup_field[2])


def test_diffuse_quadrature_convergence(setup_field):
    field = setup_field[3]; s = scene(field); s['receivers'][0]['normal'] = [1,0,0]
    s['diffuse_fractions'] = [1.]
    s['quadrature'].update(dome_mu_samples=64, dome_phi_samples=128)
    ppfd = intercept(field, s)['receivers'][0]
    # Uniform upper hemisphere radiance: each vertical face receives Q/2.
    assert ppfd['upper_ppfd_umol_m2_s'] == pytest.approx(800, rel=.001, abs=.01)
    assert ppfd['lower_ppfd_umol_m2_s'] == pytest.approx(800, rel=.001, abs=.01)
