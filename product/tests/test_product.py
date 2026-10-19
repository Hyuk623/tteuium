import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from product.backend.api import create_app
from product.backend.schemas import SensorEvent
from product.backend.services.rules import RuleConfig, evaluate
from product.backend.adapters.tomato3d import adapt


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / 'test.sqlite3', RuleConfig(temperature_high_c=30, water_low_pct=20, demo_only=True))) as c:
        assert c.post('/api/plants', json={'id':'demo-plant','name':'Tomato'}).status_code == 201
        assert c.post('/api/devices', json={'id':'d1','name':'Sensor','plant_id':'demo-plant'}).status_code == 201
        yield c


def event(**updates):
    return {'schema_version':'1.0','event_id':'e1','device_id':'d1','observed_at':datetime.now(timezone.utc).isoformat(),'source':'mock','sensors':{'temperature_c':32,'humidity_pct':50,'water_level_pct':10,'light_lux':1000},**updates}


def test_ingestion_replay_and_conflict(client):
    payload=event()
    assert client.post('/api/readings',json=payload).status_code==201
    assert client.post('/api/readings',json=payload).json()['duplicate']
    payload['sensors']['temperature_c']=25
    assert client.post('/api/readings',json=payload).status_code==409
    assert len(client.get('/api/readings?device_id=d1').json())==1
    recs=client.get('/api/recommendations?plant_id=demo-plant').json()
    assert {r['rule_id'] for r in recs}=={'temperature_high','water_low'}
    assert all('DEMO ONLY' in r['message'] for r in recs)


@pytest.mark.parametrize('changes',[
    {'schema_version':'2.0'}, {'observed_at':'2026-10-14T10:00:00'},
    {'sensors':{'humidity_pct':101}}, {'sensors':{'temperature_c':'32'}},
    {'sensors':{'light_lux':-1}}, {'sensors':{'water_level_pct':True}},
    {'extra':'not allowed'}, {'observed_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},
])
def test_invalid_contract_atomic(client,changes):
    assert client.post('/api/readings',json=event(**changes)).status_code==422
    assert client.get('/api/readings?device_id=d1').json()==[]
    assert client.get('/api/recommendations?plant_id=demo-plant').json()==[]


def test_unknown_device_and_plant(client):
    assert client.post('/api/readings',json=event(device_id='unknown')).status_code==404
    assert client.post('/api/actions',json={'plant_id':'unknown','note':'check'}).status_code==409


def test_out_of_order_and_stale(client):
    assert client.post('/api/readings',json=event()).status_code==201
    old=event(event_id='old',observed_at=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())
    assert client.post('/api/readings',json=old).status_code==201
    assert client.get('/api/devices').json()[0]['latest']['event_id']=='e1'
    assert client.get('/api/recommendations?plant_id=demo-plant').json()[0]['rule_id']=='stale_reading'


def test_rules_disabled_missing_and_boundary():
    now=datetime.now(timezone.utc)
    e=SensorEvent.model_validate(event())
    assert evaluate(e,RuleConfig(),now)==[]
    assert evaluate(e,RuleConfig(temperature_high_c=32,water_low_pct=10),now)==[]
    missing=SensorEvent.model_validate(event(sensors={'temperature_c':None}))
    assert evaluate(missing,RuleConfig(),now)[0][0]=='missing_data'


def test_actions_images_and_dashboard(client):
    assert client.get('/').status_code==200
    assert client.get('/static/app.js').status_code==200
    assert client.post('/api/actions',json={'plant_id':'demo-plant','note':'Manual inspection'}).status_code==201
    assert client.get('/api/actions?plant_id=demo-plant').json()[0]['note']=='Manual inspection'
    assert client.post('/api/images',json={'plant_id':'demo-plant','captured_at':datetime.now(timezone.utc).isoformat(),'reference':'capture/image.jpg'}).status_code==201
    assert len(client.get('/api/images?plant_id=demo-plant').json())==1


def test_persistence(tmp_path):
    path=tmp_path/'persist.sqlite3'
    with TestClient(create_app(path)) as c:
        c.post('/api/plants',json={'id':'p','name':'persistent'})
    with TestClient(create_app(path)) as c:
        assert c.get('/api/plants').json()==[{'id':'p','name':'persistent'}]


def result():
    return adapt(Path(__file__).parent/'fixtures'/'plant_light.csv',plant_id='demo-plant',scenario_id='as_built',geometry_variant_id='fixture',observed_at=datetime(2026,10,14,tzinfo=timezone.utc),evidence='synthetic_fixture',import_id='fixture-1')


def test_research_adapter_and_replay(client):
    data=result().model_dump(mode='json')
    assert client.post('/api/research/import',json=data).status_code==201
    assert client.post('/api/research/import',json=data).json()['duplicate']
    rows=client.get('/api/measurements?plant_id=demo-plant').json()
    metrics={r['metric']:r for r in rows}
    assert metrics['leaf_area']['value']==12000
    assert metrics['leaf_area']['status']=='model_estimated'
    assert metrics['plant_height']['value'] is None
    assert metrics['canopy_area']['status']=='unavailable'
    assert metrics['leaf_ppfd_cv']['value'] is None
    assert metrics['leaf_area']['provenance']['evidence']=='synthetic_fixture'
    data['source_ref']='changed.csv'
    assert client.post('/api/research/import',json=data).status_code==409
    assert len(client.get('/api/measurements?plant_id=demo-plant').json())==8


def test_research_rejects_bad_semantics(client):
    data=result().model_dump(mode='json')
    data['measurements'][0]['unit']='cm2'
    assert client.post('/api/research/import',json=data).status_code==422
    data=result().model_dump(mode='json');data['measurements'][0]['status']='measured'
    assert client.post('/api/research/import',json=data).status_code==422


def test_adapter_rejects_duplicate_and_nan(tmp_path):
    source=Path(__file__).parent/'fixtures'/'plant_light.csv'
    path=tmp_path/'bad.csv'
    for text in (source.read_text()+source.read_text().splitlines()[1]+'\n',source.read_text().replace('12000','NaN')):
        path.write_text(text)
        with pytest.raises(ValueError):
            adapt(path,plant_id='demo-plant',scenario_id='as_built',geometry_variant_id='fixture',observed_at=datetime.now(timezone.utc),evidence='synthetic_fixture',import_id='x')


def test_json_schema_matches_api_model():
    schema=json.loads((Path(__file__).parents[1]/'device_contract'/'sensor-event.schema.json').read_text())
    expected=SensorEvent.model_json_schema();expected['$schema']='https://json-schema.org/draft/2020-12/schema'
    assert schema==expected
    validator=Draft202012Validator(schema,format_checker=FormatChecker())
    validator.validate(event())
    assert list(validator.iter_errors(event(sensors={'humidity_pct':101})))
