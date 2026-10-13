"""Empty study CSVs and a read-only validator. No PPFD/DLI is inferred.

python -m tools.observation_records --templates --out build/<new>
python -m tools.observation_records --input build/<records> --out build/<audit>
"""
import argparse
import csv
from datetime import date, datetime, time
from pathlib import Path
import math

from tools.first_flowering import templates as flowering_templates, events, PLANTS, VISITS, RECORDS, LIGHT
from tools.groimp_density import SENSORS, MEASUREMENTS, sensor_triangles
from tools.leaf_light.common import StudyError
from tools.leaf_preprocess_lab import assert_build, sha, write_json

CAPTURES=('plant_id','captured_at','session_id','image_file')
SCHEDULE=('plot_id','lamp_id','effective_start','effective_end','height_mm','height_reference',
          'tilt_deg','azimuth_deg','output_setting_pct','measured_power_w','on_time','off_time','timezone')
AREA=('plant_id','date','status','evidence_file')
SCHEMAS={'plants.csv':PLANTS,'flower_visits.csv':VISITS,'growth.csv':RECORDS,'light_timeseries.csv':LIGHT,
         'captures.csv':CAPTURES,'lighting.csv':SCHEDULE,'sensors.csv':SENSORS,'ppfd_readings.csv':MEASUREMENTS,
         'area_evidence.csv':AREA}


def templates(out):
    out=assert_build(out);flowering_templates(out)
    for name,cols in SCHEMAS.items():
        if (out/name).exists():continue
        with (out/name).open('w',encoding='utf-8-sig',newline='') as f:csv.writer(f).writerow(cols)
    (out/'작성안내.txt').write_text('''관찰 기록 작성 안내

빈 값은 미측정입니다. 0으로 채우지 마세요. CSV는 UTF-8로 저장합니다.
개체와 촬영일을 구분하고, 한 개체의 여러 사진을 다른 개체로 세지 않습니다.
plants.csv: plant_id=개체, plot_id=재배구, density_id=밀도 조건.
start_date/end_date는 계획한 관찰 기간(YYYY-MM-DD). 아직 관찰하지 않은 날의 행을 만들지 마세요.
split은 observe_only로 시작할 수 있습니다. 한 재배구의 split/density는 동일해야 합니다.

captures.csv: captured_at은 2026-10-01T15:00:00+09:00처럼 시간대 포함.
session_id는 촬영 세션, image_file은 이 폴더 기준 상대 경로 또는 기존 사진 절대 경로.
과거 사진은 실제 촬영일로 기록하고 새 관찰일 사진처럼 기록하지 않습니다.

growth.csv: height_mm=초장(mm), leaf_count=복엽 수(소엽 수 아님).
temperature_c=섭씨, relative_humidity_pct=상대습도(%).
reviewed_leaf_area_mm2는 독립 측정으로 확인된 잎 면적만 입력합니다.
진단용 3D/투영 면적은 이 칸에 넣지 않습니다. 값을 입력하면 area_evidence.csv에
같은 개체·날짜, status=independent_measurement, 측정 근거 파일을 연결합니다.

flower_visits.csv: 매일 같은 시간대에 관찰합니다.
not_open=미개화, bud_only=봉오리만, first_open=첫 개화 확인/이후 이미 개화한 상태, missed=관찰 누락.
human_confirmed=true/false. 꽃잎이 벌어져 내부가 보이는 첫 꽃의 증거 사진을 evidence_photo에 입력합니다.
개화 후 꽃이 떨어져도 미개화로 되돌리지 않습니다. 시작일부터 개화했다면 그대로 first_open을 기록합니다.
놓친 날은 missed, 종료일까지 미개화하면 종료일을 개화일로 쓰지 않습니다.

lighting.csv: 재배구·조명마다 설정 적용 기간을 기록합니다(시간대 포함 ISO 시각).
height_mm는 조명 중심 높이, height_reference는 board_origin(보드 원점) 또는 canopy_top(수관 상단).
tilt_deg는 수직 아래 방향으로부터 기울기(0~180), azimuth_deg는 보드 +X에서 +Y 방향(0~360 미만).
output_setting_pct는 기기의 출력 설정(%), measured_power_w는 전력계로 측정한 소비전력(W).
출력 %를 PPFD나 실제 전력으로 바꾸어 적지 않습니다.
on_time/off_time은 HH:MM(:SS), timezone=Asia/Seoul. 소등이 점등보다 이르면 자정 넘김입니다.
같은 점등·소등 시각은 의미가 모호하므로 사용하지 않습니다.

PPFD 센서가 없으므로 sensors.csv/ppfd_readings.csv는 빈 양식으로 둡니다.
light_timeseries.csv에도 실측/검토된 광 자료가 없으면 값을 만들지 않습니다.
실측 PPFD가 없으면 실측 DLI도 미산출입니다. CO2 입력은 없습니다.
센서 확보 후 위치(mm), 단위 법선 방향, 감지면 크기, 모델/교정/장면 해시를 기록합니다.
PPFD 단위는 micromol m^-2 s^-1. 반복 측정마다 다른 reading_id를 사용합니다.

검사 명령: python -m tools.observation_records --input <이 폴더> --out build/<새 검사 폴더>
검사는 원본 CSV를 수정하지 않습니다. 오류·경고와 개화 관측 상태만 별도 저장합니다.
''',encoding='utf-8')
    write_json(out/'record_policy.json',dict(sensor_available=False,measured_dli=None,
        leaf_count_semantics='compound_leaves',timezone='Asia/Seoul',surface_area_not_measurement=True))
    return dict(out=str(out),status='empty_templates_created')


def validate(folder):
    folder=Path(folder).resolve();issues=[];tables={};hashes={}
    def issue(file,row,reason,severity='error'):issues.append(dict(file=file,row=row,severity=severity,reason=reason))
    for name,cols in SCHEMAS.items():
        path=folder/name
        if not path.exists():issue(name,0,'missing_file');tables[name]=[];continue
        hashes[name]=sha(path)
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if not set(cols)<=set(reader.fieldnames or []):issue(name,1,'missing_columns')
            tables[name]=[{k:(v.strip() if isinstance(v,str) else v) for k,v in r.items()} for r in reader]
    plants={r.get('plant_id'):r for r in tables['plants.csv']};plots={r.get('plot_id') for r in tables['plants.csv']}
    def numeric(r,key,lo=None,hi=None,integer=False,required=False):
        v=r.get(key,'')
        if v=='':
            if required:raise ValueError('missing_'+key)
            return None
        n=float(v)
        if not math.isfinite(n) or (lo is not None and n<lo) or (hi is not None and n>hi) or (integer and not n.is_integer()):raise ValueError('invalid_'+key)
        return n
    def dated(s):return date.fromisoformat(s)
    def timestamp(s):
        t=datetime.fromisoformat(s)
        if t.utcoffset() is None:raise ValueError('timestamp_timezone_required')
        return t
    def file_exists(s):return bool(s) and (folder/s).is_file()
    keys={'plants.csv':('plant_id',),'flower_visits.csv':('plant_id','date'),'growth.csv':('plant_id','date'),
          'captures.csv':('plant_id','session_id','image_file'),'area_evidence.csv':('plant_id','date'),
          'lighting.csv':('plot_id','lamp_id','effective_start'),'sensors.csv':('sensor_id',),
          'ppfd_readings.csv':('reading_id',),'light_timeseries.csv':('plant_id','date')}
    schedules={}
    for name,records in tables.items():
        seen=set()
        for i,r in enumerate(records,2):
            try:
                key=tuple(r.get(k,'') for k in keys[name])
                if any(not v for v in key):raise ValueError('missing_identifier_or_date')
                if key in seen:raise ValueError('duplicate_record')
                seen.add(key)
                if name!='plants.csv' and 'plant_id' in r and r['plant_id'] not in plants:raise ValueError('unknown_plant')
                if 'date' in r:dated(r['date'])
                if name=='growth.csv':
                    for field in ['height_mm','reviewed_leaf_area_mm2']:numeric(r,field,lo=0)
                    numeric(r,'leaf_count',lo=0,integer=True);numeric(r,'temperature_c');numeric(r,'relative_humidity_pct',0,100)
                    plant=plants[r['plant_id']]
                    if not dated(plant['start_date'])<=dated(r['date'])<=dated(plant['end_date']):raise ValueError('growth_outside_observation_period')
                    if r.get('reviewed_leaf_area_mm2',''):
                        evidence=[a for a in tables['area_evidence.csv'] if a.get('plant_id')==r['plant_id'] and a.get('date')==r['date'] and a.get('status')=='independent_measurement' and file_exists(a.get('evidence_file',''))]
                        if not evidence:raise ValueError('independent_leaf_area_evidence_required')
                if name=='area_evidence.csv':
                    if r['status']!='independent_measurement' or not file_exists(r['evidence_file']):raise ValueError('invalid_area_evidence')
                if name=='captures.csv':
                    timestamp(r['captured_at'])
                    if not file_exists(r['image_file']):raise ValueError('missing_capture_photo')
                if name=='lighting.csv':
                    if r['plot_id'] not in plots:raise ValueError('unknown_plot')
                    start,end=timestamp(r['effective_start']),timestamp(r['effective_end'])
                    if end<=start:raise ValueError('invalid_effective_interval')
                    group=(r['plot_id'],r['lamp_id'])
                    if any(start<b and a<end for a,b in schedules.get(group,[])):raise ValueError('overlapping_lamp_settings')
                    schedules.setdefault(group,[]).append((start,end))
                    numeric(r,'height_mm',lo=0,required=True);numeric(r,'tilt_deg',0,180,required=True)
                    az=numeric(r,'azimuth_deg',0,360,required=True)
                    if az==360:raise ValueError('azimuth_must_be_less_than_360')
                    numeric(r,'output_setting_pct',0,100,required=True);numeric(r,'measured_power_w',lo=0)
                    if r['height_reference'] not in ('board_origin','canopy_top'):raise ValueError('height_reference_required')
                    if r['timezone']!='Asia/Seoul':raise ValueError('unsupported_schedule_timezone')
                    if time.fromisoformat(r['on_time'])==time.fromisoformat(r['off_time']):raise ValueError('ambiguous_equal_on_off_time')
                if name=='sensors.csv':sensor_triangles(r)
                if name=='ppfd_readings.csv':
                    if r['sensor_id'] not in {s.get('sensor_id') for s in tables['sensors.csv']}:raise ValueError('unknown_sensor')
                    numeric(r,'ppfd_umol_m2_s',lo=0,required=True)
                    if r['split_role'] not in ('calibration','evaluation'):raise ValueError('invalid_measurement_split')
                    for f in ('case_id','scene_sha256','sensor_spec_sha256','sensor_model','calibration_reference'):
                        if not r.get(f):raise ValueError('missing_'+f)
                    if r['all_fixtures_full_output'] not in ('true','false'):raise ValueError('invalid_fixture_output_state')
                if name=='light_timeseries.csv':
                    for f in ('lower_ppfd_umol_m2_s','upper_ppfd_umol_m2_s','leaf_ppfd_cv'):numeric(r,f,lo=0)
                    if any(r.get(f) for f in ('lower_ppfd_umol_m2_s','upper_ppfd_umol_m2_s')) and (not r.get('source_run') or not r.get('geometry_date') or not r.get('review_state')):raise ValueError('light_provenance_required')
                    if r.get('geometry_date'):dated(r['geometry_date'])
            except (ValueError,TypeError,KeyError,StudyError) as e:issue(name,i,str(e))
    event_rows=[]
    if not any(i['file'] in ('plants.csv','flower_visits.csv') for i in issues):
        try:event_rows=events(tables['plants.csv'],tables['flower_visits.csv'],folder)
        except (ValueError,KeyError,StudyError) as e:issue('flower_visits.csv',0,str(e))
    if not tables['plants.csv']:issue('plants.csv',0,'no_actual_observations','warning')
    if not tables['ppfd_readings.csv']:issue('ppfd_readings.csv',0,'PPFD_unmeasured_DLI_unavailable','warning')
    for name,h in hashes.items():
        if sha(folder/name)!=h:raise ValueError('Input changed during validation')
    return dict(status='invalid' if any(i['severity']=='error' for i in issues) else 'valid',issues=issues,
        source_hashes=hashes,counts={n:len(r) for n,r in tables.items()},events=event_rows,
        measured_dli=None,leaf_count_semantics='compound_leaves')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--templates',action='store_true');p.add_argument('--input',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.templates:r=templates(a.out)
    else:
        if not a.input:p.error('--input is required')
        r=validate(a.input);out=assert_build(a.out);out.mkdir(parents=True,exist_ok=False);write_json(out/'validation.json',r)
        with (out/'issues.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['file','row','severity','reason']);w.writeheader();w.writerows(r['issues'])
    print(r['status'])


if __name__=='__main__':main()
