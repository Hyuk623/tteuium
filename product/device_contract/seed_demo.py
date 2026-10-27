"""Seed 14 days through the public HTTP contract. No hardware or inference required."""
import argparse
import hashlib
import math
import time
from urllib.error import URLError
from datetime import datetime, timedelta, timezone
from product.device_contract.mock_sensor import post, register


KST = timezone(timedelta(hours=9))


def sensor_values(at: datetime) -> dict:
    """Hypothetical indoor fixture, not a recommended growing environment."""
    local = at.astimezone(KST)
    hour = local.hour + local.minute / 60 + local.second / 3600
    day = local.toordinal()
    daytime = math.cos((hour - 15) / 24 * math.tau)
    weather = math.sin(day * .73)
    noise = math.sin(at.timestamp() / 233) * .18
    return {'temperature_c': round(23 + 2.5*daytime + .6*weather + noise, 1),
            'humidity_pct': round(59 - 7*daytime + 2*weather - noise, 1)}


def live_sample(base: str) -> None:
    now = datetime.now(timezone.utc)
    post(base, '/api/readings', {'schema_version':'1.0','event_id':'demo-live-'+now.strftime('%Y%m%d%H%M%S%f'),'device_id':'mvp-mock','observed_at':now.isoformat(),'source':'mock','sensors':sensor_values(now)})


def seed(base: str) -> None:
    plant = 'mvp-demo'
    register(base, '/api/plants', {'id': plant, 'name': '나의 작은 토마토'})
    register(base, '/api/devices', {'id': 'mvp-mock', 'name': '거실 · 모의 센서', 'plant_id': plant})
    # Stable daily timestamps make retries safe; today's fresh sample is separate.
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for day in range(14):
        at = today - timedelta(days=13-day)
        # Values depend on date, not relative seed offset, so tomorrow's retry is safe.
        for hour in range(24):
            observed = at + timedelta(hours=hour)
            if observed > datetime.now(timezone.utc):
                continue
            post(base, '/api/readings', {'schema_version': '1.0', 'event_id': 'demo-th-'+observed.strftime('%Y%m%d%H'), 'device_id': 'mvp-mock', 'observed_at': observed.isoformat(), 'source': 'mock', 'sensors': sensor_values(observed)})
        token = at.strftime('%Y%m%d')
        age_days = (at - datetime(2026, 10, 1, tzinfo=timezone.utc)).days
        growth = (1 + math.tanh((age_days-25)/40)) / 2
        height = round(120 + 220*growth, 1)
        leaf_area = round(8000 + 26000*growth, 1)
        canopy_area = round(6000 + 18000*growth, 1)
        post(base, '/api/observations', {'import_id': 'demo-growth-'+token, 'plant_id': plant, 'observed_at': at.isoformat(), 'source_ref': 'mock-history-v2', 'source_sha256': hashlib.sha256(b'mock-history-v2').hexdigest(), 'scenario_id': 'observation', 'geometry_variant_id': 'demo', 'evidence': 'mock', 'measurements': [{'metric': metric, 'value': value, 'unit': unit, 'status': 'model'} for metric,value,unit in [('plant_height',height,'mm'),('leaf_area',leaf_area,'mm2'),('canopy_area',canopy_area,'mm2')]]})
    # Images are illustrations, explicitly tagged; no claim of camera capture.
    from urllib.request import urlopen
    import json
    with urlopen(base+'/api/images?plant_id='+plant) as response:
        existing = json.load(response)
    for days_ago, filename in [(13,'demo-before.svg'),(0,'demo-now.svg')]:
        captured = (today-timedelta(days=days_ago)).isoformat()
        reference = '/static/'+filename
        if not any(r['captured_at']==captured and r['reference']==reference for r in existing):
            post(base,'/api/images',{'plant_id':plant,'captured_at':captured,'reference':reference,'source':'mock'})
    live_sample(base)
    print('14-day mock history ready: '+base)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--live', action='store_true', help='Continue sending temperature/humidity samples')
    parser.add_argument('--interval', type=int, default=300, help='Live interval in seconds (default 300)')
    args = parser.parse_args()
    if args.interval < 1:
        parser.error('--interval must be positive')
    base = args.url.rstrip('/')
    while True:
        try:
            seed(base)
            break
        except (URLError, TimeoutError, ConnectionError) as error:
            if not args.live:
                raise
            print(f'Mock initialization failed; retrying in {args.interval}s: {error}', flush=True)
            time.sleep(args.interval)
    if args.live:
        try:
            while True:
                time.sleep(args.interval)
                try:
                    live_sample(base)
                    print('Mock sample sent: '+datetime.now(timezone.utc).isoformat(), flush=True)
                except (URLError, TimeoutError, ConnectionError) as error:
                    print(f'Mock sample failed; retrying in {args.interval}s: {error}', flush=True)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
