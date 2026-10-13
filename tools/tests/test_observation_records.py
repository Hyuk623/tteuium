import csv
from pathlib import Path
import pytest
from tools import observation_records as records
from tools.leaf_preprocess_lab import sha


def write(folder,name,rows):
    with (folder/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=records.SCHEMAS[name]);w.writeheader();w.writerows(rows)


@pytest.fixture
def folder(tmp_path,monkeypatch):
    monkeypatch.setattr(records,'assert_build',lambda p:Path(p))
    out=tmp_path/'records';records.templates(out)
    write(out,'plants.csv',[dict(plant_id='p1',plot_id='plot1',density_id='d1',start_date='2026-10-01',end_date='2026-11-12',split='observe_only')])
    return out


def test_empty_measurements_not_zero_or_dli(folder):
    before={p.name:sha(p) for p in folder.glob('*.csv')}
    r=records.validate(folder)
    assert r['status']=='valid' and r['measured_dli'] is None
    assert r['counts']['ppfd_readings.csv']==0 and r['leaf_count_semantics']=='compound_leaves'
    assert before=={p.name:sha(p) for p in folder.glob('*.csv')}


@pytest.mark.parametrize('values',[
    dict(plant_id='unknown',date='2026-10-01'),dict(plant_id='p1',date='2026-09-01'),
    dict(plant_id='p1',date='bad'),dict(plant_id='p1',date='2026-10-01',leaf_count='1.5'),
    dict(plant_id='p1',date='2026-10-01',height_mm='NaN'),dict(plant_id='p1',date='2026-10-01',relative_humidity_pct='101'),
    dict(plant_id='p1',date='2026-10-01',reviewed_leaf_area_mm2='100')])
def test_growth_ids_dates_units_and_area_evidence(folder,values):
    write(folder,'growth.csv',[values]);assert records.validate(folder)['status']=='invalid'


def test_duplicate_records_and_missing_photo(folder):
    row=dict(plant_id='p1',captured_at='2026-10-01T12:00:00+09:00',session_id='s',image_file='absent.png')
    write(folder,'captures.csv',[row,row]);r=records.validate(folder)
    reasons={i['reason'] for i in r['issues']}
    assert 'missing_capture_photo' in reasons and 'duplicate_record' in reasons


def test_flowering_interval_missed_right_censoring_and_already_open(folder):
    (folder/'flower.jpg').write_bytes(b'test evidence placeholder')
    def visit(d,state):return dict(plant_id='p1',date=d,state=state,human_confirmed='true',evidence_photo='flower.jpg' if state=='first_open' else '')
    write(folder,'flower_visits.csv',[visit('2026-10-01','bud_only'),visit('2026-10-02','missed'),visit('2026-10-03','first_open')])
    r=records.validate(folder);assert r['events'][0]['event_status']=='interval_censored' and r['events'][0]['upper_day']==2
    write(folder,'flower_visits.csv',[visit('2026-10-01','not_open')]);r=records.validate(folder)
    assert r['events'][0]['event_status']=='right_censored' and r['events'][0]['first_open_date'] is None
    write(folder,'flower_visits.csv',[visit('2026-10-01','first_open')]);assert records.validate(folder)['events'][0]['event_status']=='already_flowered_at_entry'
    write(folder,'flower_visits.csv',[visit('2026-10-01','first_open'),visit('2026-10-02','not_open')]);assert records.validate(folder)['status']=='invalid'


def test_lighting_separates_settings_and_power_and_reports_overlap(folder):
    r=dict(plot_id='plot1',lamp_id='LED1',effective_start='2026-10-01T00:00:00+09:00',effective_end='2026-10-02T00:00:00+09:00',height_mm='300',height_reference='board_origin',tilt_deg='0',azimuth_deg='0',output_setting_pct='50',measured_power_w='',on_time='18:00',off_time='06:00',timezone='Asia/Seoul')
    write(folder,'lighting.csv',[r]);assert records.validate(folder)['status']=='valid'
    write(folder,'lighting.csv',[r,{**r,'effective_start':'2026-10-01T12:00:00+09:00'}])
    assert any(i['reason']=='overlapping_lamp_settings' for i in records.validate(folder)['issues'])
