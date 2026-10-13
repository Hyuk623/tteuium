"""Independent raw-reading checks must survive rehashed producer-output forgery."""
import pytest

from tools import reference_dli as producer
from tools.reference_dli_consumer import validate_result
from tools.reference_dli_demo import create_inputs, write_readings
from tools.leaf_light.common import StudyError, file_hash, read_json, write_json


def package(tmp_path, monkeypatch, route='spot_schedule'):
    import tools.leaf_light.common as common
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    source = tmp_path/'inputs'; create_inputs(source, route)
    record, audit = producer.prepare_record(source/'reference_position.json', source/'schedule.json', route=route,
        readings_path=source/'reference_readings.csv', survey_path=source/'spot_survey.csv')
    producer.save_result(record, audit, tmp_path/'result')
    return tmp_path/'result/reference_dli.json'


@pytest.mark.parametrize('route', ['spot_schedule', 'logged'])
def test_independent_reading_arithmetic_accepts_real_producer(tmp_path, monkeypatch, route):
    path = package(tmp_path, monkeypatch, route)
    # The independent validator must never rerun the producer or its day adapter.
    def forbidden(*args, **kwargs): raise AssertionError('producer replay is not independent validation')
    monkeypatch.setattr(producer, 'prepare_record', forbidden)
    import tools.reference_dli_intervals as intervals
    monkeypatch.setattr(intervals, 'daily_logged', forbidden)
    monkeypatch.setattr(intervals, 'daily_spot', forbidden)
    monkeypatch.setattr(intervals, 'photon_integral', forbidden)
    result = validate_result(path)
    assert result['valid'] and result['value'] == pytest.approx(11.52, abs=1e-12, rel=1e-12)


@pytest.mark.parametrize('mutation', ['value', 'basis', 'unit', 'scope', 'source_kind', 'days_used', 'association', 'domain'])
def test_forged_reference_record_rejected(tmp_path, monkeypatch, mutation):
    path = package(tmp_path, monkeypatch)
    record = read_json(path)
    if mutation == 'value': record['value'] = 12.
    if mutation == 'basis': record['basis_id'] = 'invented'
    if mutation == 'unit': record['unit'] = 'mol/m2/d'
    if mutation == 'scope': record['model_scope'] = 'tissue'
    if mutation == 'source_kind': record['source_kind'] = 'measured_logged'
    if mutation == 'days_used': record['days_used'][0]['value'] = 13.
    if mutation == 'association': record['plant_association']['accepted_plant_instance_ids'].append('invented')
    if mutation == 'domain': record['applicability_domain']['max'] = 999.
    write_json(path, record)
    with pytest.raises(StudyError): validate_result(path)


def test_numeric_forgery_even_when_daily_json_csv_audit_and_hashes_agree(tmp_path, monkeypatch):
    import csv
    path = package(tmp_path, monkeypatch)
    record = read_json(path); record['value'] = record['candidate_value'] = 12.
    record['days_used'][0]['value'] = 12.
    day = record['days']['2026-10-04']; day['dli_mol_m2_day'] = 12.
    audit = read_json(path.parent/'integration_evidence.json'); audit['integration']['days']['2026-10-04'] = day
    write_json(path.parent/'integration_evidence.json', audit)
    csv_path = path.parent/'reference_dli.csv'
    with csv_path.open(newline='') as stream:
        reader = csv.DictReader(stream); columns = reader.fieldnames; rows = list(reader)
    rows[0]['dli_mol_m2_day'] = 12.
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
    record['artifact_hashes'] = {name:file_hash(path.parent/name) for name in record['artifact_hashes']}
    write_json(path, record)
    with pytest.raises(StudyError, match='raw_dli_mol_m2_day_mismatch'): validate_result(path)


def test_consumer_rechecks_tissue_basis_at_consumption(tmp_path, monkeypatch):
    path = package(tmp_path, monkeypatch)
    with pytest.raises(StudyError, match='basis_collides_with_tissue_basis'):
        validate_result(path, tissue_bases={'synthetic_reference'})
