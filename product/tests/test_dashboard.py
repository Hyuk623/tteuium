from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from product.backend.api import create_app


def observation(at, value, identifier, evidence='human'):
    return {'import_id':identifier,'plant_id':'p','observed_at':at.isoformat(),'source_ref':'test','source_sha256':'0'*64,'geometry_variant_id':'demo' if evidence=='mock' else 'manual','evidence':evidence,'measurements':[{'metric':'plant_height','value':value,'unit':'mm','status':'model' if evidence=='mock' else 'human'}]}


def test_state_period_provenance_checks_and_persistence(tmp_path):
    path=tmp_path/'state.db'
    now=datetime.now(timezone.utc)
    with TestClient(create_app(path)) as c:
        c.post('/api/plants',json={'id':'p','name':'Plant'})
        c.post('/api/plants',json={'id':'other','name':'Other'})
        for delta,value,key,source in [(13,80,'old','human'),(5.5,100,'start','human'),(0,100,'end','human'),(0,300,'mock','mock')]:
            assert c.post('/api/observations',json=observation(now-timedelta(days=delta),value,key,source)).status_code==201
        state=c.get('/api/plants/p/state?days=7').json()
        assert set(state['state'])=={'Growth','Environment','Light','Fruit','Condition','Action'}
        assert len(state['state']['Growth']['measurements'])==3
        assert len({m['series'] for m in state['state']['Growth']['measurements']})==2
        assert len(state['checks'])==1
        assert state['checks'][0]['evidence']['source']=='human'
        assert state['state']['Condition']['diagnosis']=='unavailable'
        assert c.get('/api/plants/other/state').json()['state']['Growth']['measurements']==[]
        assert c.get('/api/plants/missing/state').status_code==404
        assert c.get('/api/plants/p/state?days=0').status_code==422
        assert len(c.get('/api/plants/p/state?days=14').json()['state']['Growth']['measurements'])==4
        for kind in ['water','nutrients','lighting','pruning','pollination','relocation']:
            assert c.post('/api/actions',json={'plant_id':'p','kind':kind,'note':'record'}).status_code==201
        assert c.post('/api/images',json={'plant_id':'p','captured_at':now.isoformat(),'reference':'/static/demo-now.svg','source':'mock'}).status_code==201
    with TestClient(create_app(path)) as c:
        state=c.get('/api/plants/p/state').json()
        assert len(state['state']['Action']['entries'])==6
        assert state['images'][0]['source']=='mock'


def test_observation_validation_and_no_cross_source_comparison(tmp_path):
    now=datetime.now(timezone.utc)
    with TestClient(create_app(tmp_path/'state.db')) as c:
        c.post('/api/plants',json={'id':'p','name':'Plant'})
        first=observation(now-timedelta(days=5.5),100,'one')
        assert c.post('/api/observations',json=first).status_code==201
        assert c.post('/api/observations',json=first).json()['duplicate']
        assert c.post('/api/observations',json=observation(now,50,'two','mock')).status_code==201
        assert c.get('/api/plants/p/state').json()['checks']==[]
        bad=observation(now,100,'bad');bad['measurements'][0]['status']='measured'
        assert c.post('/api/observations',json=bad).status_code==422
        bad=observation(now+timedelta(days=1),100,'future')
        assert c.post('/api/observations',json=bad).status_code==422
        first['measurements'][0]['value']=2
        assert c.post('/api/observations',json=first).status_code==409

def test_uninstalled_sensors_do_not_generate_missing_checks(tmp_path):
    with TestClient(create_app(tmp_path/'sensors.db')) as c:
        c.post('/api/plants',json={'id':'p','name':'Plant'})
        c.post('/api/devices',json={'id':'d','name':'Indoor','plant_id':'p'})
        now=datetime.now(timezone.utc).isoformat()
        event={'schema_version':'1.0','event_id':'th-only','device_id':'d','observed_at':now,'source':'mock','sensors':{'temperature_c':23.1,'humidity_pct':58}}
        assert c.post('/api/readings',json=event).status_code==201
        assert c.get('/api/plants/p/state').json()['checks']==[]
        event['event_id']='humidity-missing';event['sensors']['humidity_pct']=None
        assert c.post('/api/readings',json=event).status_code==201
        assert c.get('/api/plants/p/state').json()['checks'][0]['evidence']['missing']==['humidity_pct']

def test_action_date_and_legacy_migration(tmp_path):
    import sqlite3
    path = tmp_path/'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE actions (id INTEGER PRIMARY KEY, plant_id TEXT, created_at TEXT, kind TEXT, note TEXT)')
        db.execute("INSERT INTO actions VALUES (1,'p','2026-10-18T10:00:00Z','note','legacy')")
    with TestClient(create_app(path)) as c:
        c.post('/api/plants',json={'id':'p','name':'Plant'})
        result=c.post('/api/actions',json={'plant_id':'p','note':'past day','action_date':'2026-09-12'})
        assert result.status_code==201
        assert c.post('/api/actions',json={'plant_id':'p','note':'invalid','action_date':'2026-02-30'}).status_code==422
    with TestClient(create_app(path)) as c:
        entries=c.get('/api/actions?plant_id=p').json()
        assert entries[0]['action_date']=='2026-09-12'
        assert entries[0]['created_at'][:10]!='2026-09-12'
        assert entries[1]['action_date'] is None
        assert entries[1]['note']=='legacy'
