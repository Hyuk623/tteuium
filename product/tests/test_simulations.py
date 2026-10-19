from datetime import datetime, timezone
import base64
import pytest
from fastapi.testclient import TestClient
from product.backend.api import create_app
from product.backend.db import connect
from product.backend.simulations import register_result


def test_simulation_assets_are_scoped_persistent_and_sandboxed(tmp_path):
    db=tmp_path/'product.sqlite3'
    with TestClient(create_app(db)) as c:
        c.post('/api/plants',json={'id':'p','name':'Plant'})
        c.post('/api/plants',json={'id':'q','name':'Other'})
        meta=dict(plant_id='p',title='Test model',run_id='run1',scenario_id='scenario1',generated_at=datetime.now(timezone.utc),input_kind='synthetic_fixture')
        png=tmp_path/'frame.png'
        png.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aHioAAAAASUVORK5CYII='))
        identifier=register_result(db,png,**meta)
        assert register_result(db,png,**meta)==identifier
        rows=c.get('/api/simulations?plant_id=p').json()
        assert len(rows)==1 and rows[0]['provenance']=='model'
        assert c.get('/api/simulations?plant_id=q').json()==[]
        assert c.get('/api/simulations?plant_id=missing').status_code==404
        asset=c.get(rows[0]['asset_url'])
        assert asset.content==png.read_bytes()
        assert asset.headers['content-type']=='image/png'
        viewer=tmp_path/'viewer.html';viewer.write_text('<html><script>document.body.textContent="fixture"</script></html>')
        second=register_result(db,viewer,**meta)
        response=c.get('/api/simulations/'+second+'/asset')
        assert 'sandbox allow-scripts' in response.headers['content-security-policy']
        assert "connect-src 'none'" in response.headers['content-security-policy']
        with connect(db) as connection:
            connection.execute('UPDATE simulation_results SET asset_name=? WHERE id=?',('../viewer.html',second))
        assert c.get('/api/simulations/'+second+'/asset').status_code==404
        viewer.write_text('<script>const data=__DATA__;</script>')
        with pytest.raises(ValueError):register_result(db,viewer,**meta)
    with TestClient(create_app(db)) as c:
        assert len(c.get('/api/simulations?plant_id=p').json())==2
