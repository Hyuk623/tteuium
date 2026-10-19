"""Read model: bounded date windows and provenance-isolated observation series."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException
from product.backend.db import connect

GROWTH = {'plant_height', 'leaf_area', 'canopy_area'}


def dashboard_state(path: Path, plant_id: str, days: int, stale_seconds: int) -> dict:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).isoformat()
    with connect(path) as db:
        plant = db.execute('SELECT * FROM plants WHERE id=?', (plant_id,)).fetchone()
        if not plant:
            raise HTTPException(404, 'unknown plant')
        devices = [dict(r) for r in db.execute('SELECT * FROM devices WHERE plant_id=?', (plant_id,))]
        readings = []
        for device in devices:
            rows = db.execute('SELECT payload FROM sensor_readings WHERE device_id=? AND observed_at>=? AND observed_at<=? ORDER BY observed_at LIMIT 10001', (device['id'], since, now.isoformat())).fetchall()
            if len(rows) > 10000:
                raise HTTPException(422, 'Too many readings; select a shorter period')
            readings.extend(json.loads(r['payload']) for r in rows)
        readings.sort(key=lambda r: r['observed_at'])
        measurements = []
        for row in db.execute('SELECT m.*,r.payload FROM plant_measurements m JOIN research_imports r USING(import_id) WHERE plant_id=? AND observed_at>=? AND observed_at<=? ORDER BY observed_at,m.id', (plant_id, since, now.isoformat())):
            item = dict(row)
            origin = json.loads(item.pop('payload'))
            item['provenance'] = {k: v for k, v in origin.items() if k != 'measurements'}
            item['source_kind'] = 'mock' if origin['evidence'] in ('mock', 'synthetic_fixture') else ('human' if origin['evidence'] == 'human' else 'model')
            item['series'] = '|'.join([item['metric'], item['source_kind'], origin['scenario_id'], origin['geometry_variant_id'], item['status']])
            measurements.append(item)
        images = [dict(r) for r in db.execute('SELECT * FROM images WHERE plant_id=? AND captured_at>=? AND captured_at<=? ORDER BY captured_at', (plant_id, since, now.isoformat()))]
        for image in images:
            meta = db.execute('SELECT source FROM image_sources WHERE image_id=?', (image['id'],)).fetchone()
            image['source'] = meta['source'] if meta else 'unknown'
        actions = [dict(r) | {'provenance': 'human'} for r in db.execute('SELECT * FROM actions WHERE plant_id=? ORDER BY created_at DESC LIMIT 100', (plant_id,))]
    checks = []
    for device in devices:
        own = [r for r in readings if r['device_id'] == device['id']]
        latest = own[-1] if own else None
        device['latest'] = latest
        device['status'] = 'unavailable' if not latest else ('stale' if (now - datetime.fromisoformat(latest['observed_at'])).total_seconds() > stale_seconds else 'available')
        if device['status'] != 'available':
            checks.append({'observation': '최근 환경 데이터를 확인해 주세요.', 'evidence': {'device_id': device['id'], 'last_observed_at': latest['observed_at'] if latest else None}, 'check': '장치 연결과 마지막 측정 시각을 확인해 주세요.', 'action': '확인한 내용을 기록에 남겨 주세요.', 'provenance': 'derived'})
        elif any(v is None for v in latest['sensors'].values()):
            checks.append({'observation': '일부 센서값이 없습니다.', 'evidence': {'event_id': latest['event_id'], 'missing': [k for k,v in latest['sensors'].items() if v is None]}, 'check': '센서 연결 상태를 확인해 주세요.', 'action': '확인 후 다시 측정해 주세요.', 'provenance': 'derived'})
    series = {}
    for item in measurements:
        if item['metric'] in GROWTH:
            series.setdefault(item['series'], []).append(item)
    # Only a non-increase is described. No unvalidated biological threshold is assumed.
    for key, items in series.items():
        valid = [m for m in items if m['value'] is not None and datetime.fromisoformat(m['observed_at']) >= now-timedelta(days=6)]
        if len(valid) < 2:
            continue
        first, last = valid[0], valid[-1]
        span = (datetime.fromisoformat(last['observed_at']) - datetime.fromisoformat(first['observed_at'])).total_seconds()/86400
        if span >= 5 and last['value'] <= first['value'] and (now-datetime.fromisoformat(last['observed_at'])).total_seconds() <= 86400:
            checks.append({'observation': '최근 5일 이상 이 지표의 증가가 관찰되지 않았습니다.', 'evidence': {'series': key, 'from': first['observed_at'], 'to': last['observed_at'], 'first': first['value'], 'last': last['value'], 'unit': last['unit'], 'source': last['source_kind']}, 'check': '측정 방법을 먼저 확인하고 조명·온도·급수 기록을 살펴보세요.', 'action': '확인 내용을 기록하고 같은 방법으로 다시 관찰해 주세요.', 'provenance': 'derived'})
    return {'plant': dict(plant), 'period_days': days, 'generated_at': now.isoformat(), 'state': {
        'Growth': {'support': 'supported', 'status': 'available' if any(m['metric'] in GROWTH and m['value'] is not None for m in measurements) else 'unavailable', 'measurements': measurements},
        'Environment': {'support': 'supported', 'status': 'available' if readings else 'unavailable', 'devices': devices, 'readings': readings},
        'Light': {'support': 'supported', 'status': 'available' if any(m['metric'] not in GROWTH and m['value'] is not None for m in measurements) else 'unavailable', 'summary': '빛의 충분함은 아직 판단하지 않습니다. 측정된 밝기와 모델 결과를 구분해 살펴보세요.', 'measurements': [m for m in measurements if m['metric'] not in GROWTH], 'extensions': {'ppfd': 'unavailable', 'dli': 'unavailable', 'leaf_light_distribution': 'unavailable'}},
        'Fruit': {'support': 'planned', 'status': 'unavailable'},
        'Condition': {'support': 'planned', 'status': 'unavailable', 'diagnosis': 'unavailable'},
        'Action': {'support': 'manual', 'status': 'available' if actions else 'unavailable', 'entries': actions}}, 'images': images, 'checks': checks,
        'summary': '현재 데이터에서는 뚜렷한 이상을 판단할 수 없습니다. 이는 정상 판정이 아니며, 질병·영양결핍 진단을 제공하지 않습니다.'}
