"""Frozen predicted PPFD remains separate from measured routes and source evidence."""
import pytest

from tools import reference_dli as producer
from tools import reference_dli_consumer as consumer
from tools import reference_dli_frozen as frozen
from tools.leaf_light import common
from tools.reference_dli_demo import create_inputs


def inputs(folder):
    demo=create_inputs(folder)
    for name in ('scene.json','fit.json'):common.write_json(folder/name,{'source_kind':'synthetic_test_only'})
    common.write_rows(folder/'predictions.csv',[dict(point_id='ref',x_mm=0.,y_mm=0.,z_mm=200.,
        ppfd_umol_m2_s=200.,seed_standard_error_umol_m2_s=1.)],frozen.COLUMNS)
    p=demo['position']
    data=dict(schema_version=frozen.SCHEMA,quantity='incident',unit='umol/m2/s',source_kind='fitted',
        sensor_normal=[0,0,1],frame_id=p['frame_id'],coordinate_frame=p['coordinate_frame'],height_basis=p['height_basis'],
        predictions_csv='predictions.csv',predictions_sha256=common.file_hash(folder/'predictions.csv'),
        fit_ref='fit.json',scene_ref='scene.json',source_hashes={str((folder/n).resolve()):common.file_hash(folder/n)
        for n in ('scene.json','fit.json')},fixture_ids=['LED-01','LED-02','LED-03'],
        output_basis='all_fixtures_full_photon_output',fixed_optics_beam_spectrum=True,
        time_support=dict(start_at='2026-10-04T00:00:00+09:00',end_at='2026-10-05T00:00:00+09:00',source_ref=demo['source_ref']),
        conditional_reasons=['synthetic_only'],uncertainty=dict(systematic_status='unavailable'))
    common.write_json(folder/'frozen_prediction.json',data)
    return data


@pytest.fixture
def ready(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    inputs(tmp_path/'inputs')
    return tmp_path


def produce(path):
    f=path/'inputs'
    return producer.prepare_record(f/'reference_position.json',f/'schedule.json',route='simulated',
                                   frozen_prediction=f/'frozen_prediction.json')


def test_end_to_end_consumer_checks_conditional_dli(ready):
    record,audit=produce(ready)
    assert record['status']=='unavailable' and record['value'] is None
    assert record['days']['2026-10-04']['dli_mol_m2_day']==pytest.approx(11.52,rel=1e-12,abs=1e-12)
    assert record['days']['2026-10-04']['n_readings']==0
    producer.save_result(record,audit,ready/'result')
    checked=consumer.validate_result(ready/'result'/'reference_dli.json')
    assert checked['valid'] and 'independent_frozen' in checked['arithmetic']


@pytest.mark.parametrize('field,value,match',[
    ('frame_id','different','frame_mismatch'),('position_mm',[1,0,200],'exact_position'),
])
def test_frame_and_position_do_not_silently_translate(ready,field,value,match):
    p=ready/'inputs'/'reference_position.json'; data=common.read_json(p);data[field]=value;common.write_json(p,data)
    with pytest.raises(common.StudyError,match=match):produce(ready)


def test_tampered_source_is_rejected(ready):
    common.write_json(ready/'inputs'/'fit.json',{'changed':True})
    with pytest.raises(common.StudyError,match='hash_mismatch'):produce(ready)


def test_independent_consumer_rejects_changed_dose_even_with_rehashed_artifacts(ready):
    record,audit=produce(ready);record['days']['2026-10-04']['dli_mol_m2_day']+=1
    producer.save_result(record,audit,ready/'bad')
    with pytest.raises(common.StudyError,match='frozen_dose'):consumer.validate_result(ready/'bad'/'reference_dli.json')


def test_staggered_lamps_require_per_fixture_prediction(ready):
    p=ready/'inputs'/'schedule.json';s=common.read_json(p);s['fixtures']['LED-01'][0]['start_hhmm']='07:00';common.write_json(p,s)
    record,_=produce(ready)
    assert 'frozen_total_prediction_requires_common_fixture_fraction' in record['reasons']
    assert record['days']['2026-10-04']['dli_mol_m2_day'] is None


def test_support_and_missing_association_do_not_promote_prediction(ready):
    p=ready/'inputs'/'reference_position.json';s=common.read_json(p);s['plant_association']=None;common.write_json(p,s)
    record,audit=produce(ready)
    assert record['value'] is None
    producer.save_result(record,audit,ready/'result')
    assert consumer.validate_result(ready/'result'/'reference_dli.json')['valid']


def test_no_mix_of_measurement_and_prediction_route(ready):
    f=ready/'inputs'
    with pytest.raises(common.StudyError,match='separate_simulated_route'):
        producer.prepare_record(f/'reference_position.json',f/'schedule.json',route='logged',
                                frozen_prediction=f/'frozen_prediction.json')


@pytest.mark.parametrize('field', ['value_rule','applicability_source_ref','fixed_horizon_tolerance'])
def test_missing_reduction_policy_keeps_verified_daily_audit_only(ready,field):
    p=ready/'inputs'/'reference_position.json';d=common.read_json(p);d[field]=None;common.write_json(p,d)
    record,audit=produce(ready)
    assert record['status']=='unavailable' and record['value'] is None
    assert record['days']['2026-10-04']['dli_mol_m2_day']==pytest.approx(11.52)
    producer.save_result(record,audit,ready/'result')
    assert consumer.validate_result(ready/'result'/'reference_dli.json')['valid']


def test_missing_time_support_never_extrapolates(ready):
    p=ready/'inputs'/'frozen_prediction.json';d=common.read_json(p);d['time_support']['end_at']=None;common.write_json(p,d)
    record,audit=produce(ready)
    assert 'frozen_prediction_time_support_missing' in record['reasons']
    producer.save_result(record,audit,ready/'result')
    assert consumer.validate_result(ready/'result'/'reference_dli.json')['valid']


def test_negative_unknown_and_true_zero_prediction(ready):
    f=ready/'inputs';path=f/'predictions.csv'; table=common.rows(path)
    table[0]['ppfd_umol_m2_s']=0.;common.write_rows(path,table,frozen.COLUMNS)
    data=common.read_json(f/'frozen_prediction.json');data['predictions_sha256']=common.file_hash(path)
    common.write_json(f/'frozen_prediction.json',data)
    record,_=produce(ready);assert record['days']['2026-10-04']['dli_mol_m2_day']==0.
    table[0]['ppfd_umol_m2_s']=-1;common.write_rows(path,table,frozen.COLUMNS)
    data['predictions_sha256']=common.file_hash(path);common.write_json(f/'frozen_prediction.json',data)
    with pytest.raises(common.StudyError,match='negative'):produce(ready)
