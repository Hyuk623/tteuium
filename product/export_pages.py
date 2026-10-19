"""Build a mock-only Pages site. Never reads a running app database."""
import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from product.backend.db import initialize, connect
from product.backend.schemas import SensorEvent, ObservationBatch
from product.backend.services.ingestion import ingest, import_research
from product.backend.services.rules import RuleConfig
from product.backend.services.dashboard import dashboard_state
from product.device_contract.seed_demo import sensor_values

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/'product/frontend/dashboard'


def build(output: Path) -> None:
    output=output.resolve()
    build_root=(ROOT/'build').resolve()
    if not output.is_relative_to(build_root) or output==build_root:
        raise ValueError('Pages output must be a subdirectory of build/')
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pages-fixture-',dir=build_root) as temporary:
        db=Path(temporary)/'synthetic.sqlite3'
        initialize(db)
        now=datetime.now(timezone.utc)
        today=now.replace(hour=0,minute=0,second=0,microsecond=0)
        with connect(db) as conn:
            conn.execute('INSERT INTO plants VALUES(?,?)',('mvp-demo','나의 작은 토마토'))
            conn.execute('INSERT INTO devices VALUES(?,?,?)',('mvp-mock','가상 실내 센서','mvp-demo'))
        for day in range(30):
            at=today-timedelta(days=29-day)
            for hour in range(24):
                timestamp=at+timedelta(hours=hour)
                if timestamp>now:continue
                ingest(db,SensorEvent(schema_version='1.0',event_id=f'pages-{day}-{hour}',device_id='mvp-mock',observed_at=timestamp,source='mock',sensors=sensor_values(timestamp)),RuleConfig())
            height=150+day*1.7
            observation=ObservationBatch(import_id=f'pages-growth-{day}',plant_id='mvp-demo',observed_at=at,source_ref='pages-synthetic-only-v1',source_sha256=hashlib.sha256(b'pages-synthetic-only-v1').hexdigest(),geometry_variant_id='demo',evidence='mock',measurements=[{'metric':key,'value':value,'unit':unit,'status':'model'} for key,value,unit in [('plant_height',height,'mm'),('leaf_area',11000+day*360,'mm2'),('canopy_area',8000+day*240,'mm2')]])
            import_research(db,observation)
        ingest(db,SensorEvent(schema_version='1.0',event_id='pages-latest',device_id='mvp-mock',observed_at=now,source='mock',sensors=sensor_values(now)),RuleConfig())
        with connect(db) as conn:
            for days_ago,filename in [(13,'demo-before.svg'),(0,'demo-now.svg')]:
                cursor=conn.execute('INSERT INTO images(plant_id,captured_at,reference) VALUES(?,?,?)',('mvp-demo',(today-timedelta(days=days_ago)).isoformat(),'./'+filename))
                conn.execute('INSERT INTO image_sources VALUES(?,?)',(cursor.lastrowid,'mock'))
        for days in (7,14,30):
            state=dashboard_state(db,'mvp-demo',days,300)
            (output/f'state-{days}.json').write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
    for source in FRONTEND.iterdir():
        if source.is_file() and source.suffix in ('.html','.js','.css','.svg'):
            shutil.copyfile(source,output/source.name)
    html=(output/'index.html').read_text(encoding='utf-8').replace('/static/','./')
    html=html.replace('<script src="./app.js">','<script src="./pages-adapter.js"></script><script src="./app.js">')
    html=html.replace('<p id="notice"', '<p class="notice" id="pages-mode">공개 체험 데모 · 모의 데이터 로딩 중</p><p id="notice"')
    html=html.replace('<a href="/docs">API 문서</a>','<a href="https://github.com/Hyuk623/tteuium">소스 코드</a>')
    (output/'index.html').write_text(html,encoding='utf-8')
    shutil.copyfile(ROOT/'product/pages-adapter.js',output/'pages-adapter.js')
    (output/'.nojekyll').write_text('',encoding='utf-8')
    print('Mock-only Pages site: '+str(output))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/pages')
    build(parser.parse_args().output)
