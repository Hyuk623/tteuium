"""Exercise the documented CLIs through a real loopback HTTP server."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen


def test_mock_and_adapter_over_http(tmp_path):
    root = Path(__file__).resolve().parents[2]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with (tmp_path/'server.log').open('w') as log:
        process = subprocess.Popen([sys.executable,'-m','product.backend.api','--db',str(tmp_path/'live.sqlite3'),'--rules','product/rules.demo.json','--port',str(port)],cwd=root,stdout=log,stderr=log,creationflags=flags)
        try:
            for _ in range(100):
                try:
                    with urlopen(base+'/api/health',timeout=1) as response:
                        assert response.status==200
                    break
                except OSError:
                    assert process.poll() is None, 'server exited; inspect server.log'
                    time.sleep(.1)
            else:
                raise AssertionError('server readiness timeout')
            subprocess.run([sys.executable,'-m','product.device_contract.mock_sensor','--url',base,'--count','4','--interval','0'],cwd=root,check=True,capture_output=True,timeout=20,creationflags=flags)
            subprocess.run([sys.executable,'-m','product.backend.adapters.tomato3d','--url',base,'--csv','product/tests/fixtures/plant_light.csv','--plant-id','demo-plant','--scenario-id','as_built','--geometry-variant-id','fixture','--observed-at','2026-10-14T09:00:00+09:00','--evidence','synthetic_fixture','--import-id','http-fixture'],cwd=root,check=True,capture_output=True,timeout=20,creationflags=flags)
            with urlopen(base+'/api/readings?device_id=demo-device') as response:
                assert len(json.load(response))==4
            with urlopen(base+'/api/measurements?plant_id=demo-plant') as response:
                assert len(json.load(response))==8
            with urlopen(base+'/api/recommendations?plant_id=demo-plant') as response:
                assert any(r['rule_id']=='water_low' for r in json.load(response))
            for _ in range(2):
                subprocess.run([sys.executable,'-m','product.device_contract.seed_demo','--url',base],cwd=root,check=True,capture_output=True,timeout=30,creationflags=flags)
            with urlopen(base+'/api/plants/mvp-demo/state?days=14') as response:
                state=json.load(response)
                growth=state['state']['Growth']['measurements']
                assert len(growth)==42
                heights=[m['value'] for m in growth if m['metric']=='plant_height']
                assert heights==sorted(heights)
                assert len(state['images'])==2
                assert all(m['source_kind']=='mock' for m in growth)
            with urlopen(base) as response:
                assert b'/static/app.js' in response.read()
        finally:
            process.terminate()
            process.wait(timeout=10)
