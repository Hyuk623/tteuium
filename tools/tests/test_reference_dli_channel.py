"""Producer checks using explicitly synthetic measurement and domain evidence."""
import csv
from copy import deepcopy

import pytest

from tools import reference_dli as channel
from tools.leaf_light.common import DLI_UNIT, StudyError, read_json, write_json, file_hash
from tools.reference_dli_demo import create_inputs, row, write_readings

ABS = REL = 1e-12


def produce(folder, route='spot_schedule', **kwargs):
    return channel.prepare_record(folder/'reference_position.json', folder/'schedule.json', route=route,
        readings_path=folder/'reference_readings.csv', survey_path=folder/'spot_survey.csv', **kwargs)


def change_position(folder, **changes):
    p = read_json(folder/'reference_position.json'); p.update(changes)
    write_json(folder/'reference_position.json', p)
    return p


@pytest.mark.parametrize('route', ['spot_schedule', 'logged'])
def test_synthetic_measured_routes_produce_11_52_with_provenance(tmp_path, route):
    folder = tmp_path/'inputs'; create_inputs(folder, route)
    record, audit = produce(folder, route)
    assert record['status'] == 'available', record['reasons']
    assert record['value'] == pytest.approx(11.52, rel=REL, abs=ABS)
    assert record['unit'] == DLI_UNIT and record['quantity'] == 'incident'
    assert record['source_kind'] == 'measured_'+route
    assert record['days']['2026-10-04']['ambient_light'] == 'asserted_not_measured'
    assert record['source_hashes'] and record['code_hashes']
    assert set(audit['selection']['included_reading_ids']).isdisjoint(audit['selection']['survey_reading_ids'])


@pytest.mark.parametrize('value', [False, 'unknown'])
def test_cosine_warning_retains_false_versus_unknown_every_row(tmp_path, value):
    folder = tmp_path/'inputs'; create_inputs(folder)
    change_position(folder, cosine_corrected=value)
    record, _ = produce(folder)
    assert record['status'] == 'available'
    assert record['reference']['cosine_corrected'] == value
    assert all(d['cosine_corrected'] == value and 'cosine_response_uncorrected' in d['flags']
               for d in record['days'].values())


@pytest.mark.parametrize('field,value,reason', [
    ('levelled', False, 'sensor_level_not_established'),
    ('cosine_corrected', None, 'cosine_response_metadata_missing'),
    ('applicability_source_ref', None, 'applicability_evidence_missing'),
    ('fixed_horizon_tolerance', None, 'fixed_horizon_tolerance_missing'),
    ('value_rule', None, 'value_rule_missing'),
    ('dst_policy', None, 'dst_policy_missing'),
    ('output_constant', None, 'spot_schedule_assumption_undeclared')])
def test_missing_scientific_evidence_is_unavailable(tmp_path, field, value, reason):
    folder = tmp_path/'inputs'; create_inputs(folder)
    change_position(folder, **{field:value})
    record, _ = produce(folder)
    assert record['status'] == 'unavailable' and record['value'] is None
    assert reason in record['reasons']


def test_domain_bounds_must_match_hashed_coefficient_domain(tmp_path):
    folder = tmp_path/'inputs'; create_inputs(folder)
    change_position(folder, applicability_interval_mol_m2_day=[0., 31.])
    with pytest.raises(StudyError, match='applicability_bounds_do_not_match_source_domain'): produce(folder)


def test_complete_out_of_domain_keeps_numeric_daily_audit_not_usable_value(tmp_path):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    write_readings(folder/'reference_readings.csv', [dict(r, ppfd_umol_m2_s=1000.) for r in inputs['readings']])
    record, _ = produce(folder)
    assert record['status'] == 'out_of_applicability' and record['value'] is None
    day = record['days']['2026-10-04']
    assert day['coverage_status'] == 'complete' and day['applicability_status'] == 'out_of_applicability'
    assert day['dli_mol_m2_day'] == pytest.approx(57.6, rel=REL, abs=ABS)
    assert record['candidate_value'] == pytest.approx(57.6, rel=REL, abs=ABS)


@pytest.mark.parametrize('unit', ['lux', 'W/m2'])
def test_nonphoton_readings_rejected_even_with_missing_geometry(tmp_path, unit):
    folder = tmp_path/'inputs'; create_inputs(folder)
    change_position(folder, reading_unit=unit, position_mm=[None, None, None])
    with pytest.raises(StudyError, match='non_photon_unit'): produce(folder)


def test_legacy_units_named_refusal_and_tissue_basis_collision(tmp_path):
    folder = tmp_path/'inputs'; create_inputs(folder)
    change_position(folder, unit='mol/m2/d')
    with pytest.raises(StudyError, match='legacy_dli_unit_spelling'): produce(folder)
    change_position(folder, unit=DLI_UNIT)
    manifest = tmp_path/'tissue.json'; write_json(manifest, {'nested':{'area_basis_id':'synthetic_reference'}})
    with pytest.raises(StudyError, match='basis_collides_with_tissue_basis'): produce(folder, tissue_manifest=manifest)


def test_daytime_ambient_measurement_and_contradiction(tmp_path):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    readings = inputs['readings']+[row('ambient', '2026-10-04T05:30:00+09:00', 0., state='off')]
    write_readings(folder/'reference_readings.csv', readings)
    change_position(folder, daytime_ambient_reading_ids=['ambient'], daytime_source_ref=inputs['source_ref'])
    record, _ = produce(folder)
    assert record['status'] == 'available'
    assert record['days']['2026-10-04']['ambient_light'] == 'none'
    readings[-1]['ppfd_umol_m2_s'] = 5.
    write_readings(folder/'reference_readings.csv', readings)
    record, _ = produce(folder)
    assert record['value'] is None and record['status'] == 'unavailable'
    assert 'ambient_none_contradicted_by_lights_off_reading' in record['reasons']
    assert record['days']['2026-10-04']['ambient_light'] == 'present'


def test_position_tolerance_derived_not_survey_averaging(tmp_path):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    # A very large off-position value is excluded; it cannot enter the mean.
    readings = inputs['readings']+[row('far', '2026-10-04T12:01:30+09:00', 9999., (50., 0., 200.))]
    write_readings(folder/'reference_readings.csv', readings)
    record, audit = produce(folder)
    assert record['value'] == pytest.approx(11.52, rel=REL, abs=ABS)
    tol = audit['position_tolerance']
    assert tol['gradient_dli_per_mm'] == pytest.approx(.1*16*3600e-6, rel=REL, abs=ABS)
    assert tol['allowed_distance_mm'] == pytest.approx(.1/(.1*16*3600e-6), rel=REL, abs=ABS)
    assert audit['selection']['excluded_readings'][0]['reading_id'] == 'far'


@pytest.mark.parametrize('case', ['flat', 'collinear', 'outside'])
def test_unsupported_gradient_never_invents_radius(tmp_path, case):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    data = inputs['survey']
    if case == 'flat': data = [dict(r, ppfd_umol_m2_s=200.) for r in data]
    if case == 'collinear': data = data[:2]
    if case == 'outside': change_position(folder, position_mm=[30., 0., 200.])
    write_readings(folder/'spot_survey.csv', data)
    record, audit = produce(folder)
    assert record['status'] == 'unavailable' and audit['position_tolerance'] is None


@pytest.mark.parametrize('xyz,limit,expected', [([5., 0., 200.], .1, 'available'),
    ([5., 0., 200.], .001, 'unavailable'), ([50., 0., 200.], 100., 'unavailable')])
def test_shared_plant_reference_requires_all_locations_uniform(tmp_path, xyz, limit, expected):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    change_position(folder, plant_association=dict(plant_instance_ids=['A', 'B'], association_evidence=inputs['source_ref'],
        uniformity_basis=dict(source_ref=inputs['source_ref'], max_dli_difference_mol_m2_day=limit,
                              positions_mm={'A':[0., 0., 200.], 'B':xyz})))
    record, audit = produce(folder)
    assert record['status'] == expected
    if expected == 'available': assert record['plant_association']['accepted_plant_instance_ids'] == ['A', 'B']
    else: assert audit['plant_association'] is None


def test_days_used_spread_not_silently_reduced(tmp_path):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    change_position(folder, dates=['2026-10-04', '2026-10-05'], value_rule='mean_of_complete_days')
    s = inputs['schedule']; s['dates'].append('2026-10-05'); write_json(folder/'schedule.json', s)
    readings = inputs['readings']+[row('next', '2026-10-05T12:00:00+09:00', 180.)]
    write_readings(folder/'reference_readings.csv', readings)
    record, _ = produce(folder)
    assert 'dli_not_constant_over_horizon' in record['reasons']
    assert record['value'] is None and record['fixed_over_horizon'] is False
    assert len(record['days_used']) == 2


@pytest.mark.parametrize('ppf,reason', [(None, 'lamp_ppf_missing'),
    ({'value':None,'status':'unavailable'}, 'lamp_ppf_missing'),
    ({'value':100.,'status':'assumed'}, 'simulation_execution_deferred')])
def test_simulation_is_readiness_only_for_both_missing_and_known_ppf(tmp_path, ppf, reason, monkeypatch):
    import tools.ppfd_validation as optical
    def forbidden(*args, **kwargs): raise AssertionError('simulation or fit unexpectedly executed')
    monkeypatch.setattr(optical, 'python_point_ppfd', forbidden)
    monkeypatch.setattr(optical, 'fit_empty_rig', forbidden)
    folder = tmp_path/'inputs'; create_inputs(folder)
    scene = tmp_path/'scene.json'; write_json(scene, {'fixtures':[{'photon_flux_umol_s':ppf}]})
    record, _ = channel.prepare_record(folder/'reference_position.json', folder/'schedule.json', route='simulated', scene_path=scene)
    assert record['status'] == 'unavailable' and record['value'] is None
    assert reason in record['reasons']
    assert record['days']['2026-10-04']['ambient_light'] == 'asserted_not_measured'


def test_forged_policy_evidence_hash_is_malformed(tmp_path):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    change_position(folder, transition_source_ref=dict(inputs['source_ref'], sha256='0'*64))
    with pytest.raises(StudyError, match='transition_support_evidence_hash_mismatch'): produce(folder)


def test_csv_empty_missing_dli_and_templates_preserve_confirmed_operation(tmp_path, monkeypatch):
    import tools.leaf_light.common as common
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    channel.templates(tmp_path/'blank')
    p = read_json(tmp_path/'blank/reference_position.json')
    assert p['basis_id'] is None and p['position_mm'] == [None]*3
    assert p['operating_metadata']['daily_on_hours'] == 16 and p['output_fraction'] == 1.
    assert all(v[0]['start_hhmm'] is None for v in read_json(tmp_path/'blank/schedule.json')['fixtures'].values())
    record, audit = produce(tmp_path/'blank')
    channel.save_result(record, audit, tmp_path/'result')
    with (tmp_path/'result/reference_dli.csv').open() as stream: rows = list(csv.DictReader(stream))
    assert rows[0]['dli_mol_m2_day'] == '' and rows[0]['local_date'] == ''


def test_logged_interval_means_do_not_require_unobserved_lamp_clock_times(tmp_path):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder, 'logged')
    change_position(folder, logger_sample_semantics='interval_mean', gradient_exposure_basis='full_elapsed_day')
    schedule = inputs['schedule']; schedule['dates'] = []; write_json(folder/'schedule.json', schedule)
    readings = [row('full', '2026-10-05T00:00:00+09:00', 200., state='mixed',
                    support_start_at='2026-10-04T00:00:00+09:00', support_end_at='2026-10-05T00:00:00+09:00')]
    write_readings(folder/'reference_readings.csv', readings)
    record, _ = produce(folder, 'logged')
    assert record['status'] == 'available', record['reasons']
    assert record['value'] == pytest.approx(17.28, rel=REL, abs=ABS)
    assert record['days']['2026-10-04']['on_duration_s'] is None


def test_explicit_dst_refusal_is_not_a_silent_24_hour_day(tmp_path):
    folder = tmp_path/'inputs'; create_inputs(folder)
    change_position(folder, timezone='America/New_York', dates=['2026-03-08'], dst_policy='reject_transitions')
    record, _ = produce(folder)
    assert record['status'] == 'unavailable' and 'dst_transition_refused' in record['reasons']
    assert record['days']['2026-03-08']['dli_mol_m2_day'] is None


@pytest.mark.parametrize('q', [-1., 'nan', 'inf'])
def test_negative_or_nonfinite_measurement_is_malformed(tmp_path, q):
    folder = tmp_path/'inputs'; inputs = create_inputs(folder)
    readings = inputs['readings']; readings[0]['ppfd_umol_m2_s'] = q
    write_readings(folder/'reference_readings.csv', readings)
    with pytest.raises(StudyError, match='invalid_number:ppfd'): produce(folder)


def test_supported_zero_is_available_zero_not_missing(tmp_path):
    folder=tmp_path/'inputs';inputs=create_inputs(folder)
    write_readings(folder/'reference_readings.csv',[dict(r,ppfd_umol_m2_s=0.) for r in inputs['readings']])
    record,_=produce(folder)
    assert record['status']=='available' and record['value']==0.
    assert record['days']['2026-10-04']['coverage_status']=='complete'


def test_multiple_complete_days_mean_retains_both_days_and_passes_independent_consumer(tmp_path,monkeypatch):
    import tools.leaf_light.common as common
    from tools.reference_dli_consumer import validate_result
    monkeypatch.setattr(common,'BUILD',tmp_path)
    folder=tmp_path/'inputs';inputs=create_inputs(folder)
    change_position(folder,dates=['2026-10-04','2026-10-05'],value_rule='mean_of_complete_days')
    schedule=inputs['schedule'];schedule['dates'].append('2026-10-05');write_json(folder/'schedule.json',schedule)
    write_readings(folder/'reference_readings.csv',inputs['readings']+[row('day2','2026-10-05T12:00:00+09:00',202.)])
    record,audit=produce(folder)
    assert record['status']=='available' and len(record['days_used'])==2 and record['days_not_used']==[]
    assert record['value']==pytest.approx((200.+202.)/2*16*3600e-6,rel=REL,abs=ABS)
    channel.save_result(record,audit,tmp_path/'result')
    assert validate_result(tmp_path/'result/reference_dli.json')['valid']
