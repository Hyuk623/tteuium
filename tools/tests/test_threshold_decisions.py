"""Decision records for threshold calibration: every source maps onto threshold-decision-log-1 rows."""
import csv
import json

import numpy as np
import pytest

from tools import threshold_decisions as tool
from tools.leaf_light import common


def decision(i, rule='leaflet_inside_compound', value=0.5, decided='keep', plant='dwt_02'):
    return dict(schema_version=tool.SCHEMA, source='test', rule_id=rule, rule_version=1, score_name='inside_fraction',
                score_value=value, scores=dict(inside_fraction=value), decision=decided, plant_id=plant,
                session_id='s', image_file='p.png', object_id=f'det_{i}', decided_at='2026-09-22T00:00:00Z')


def test_review_page_and_editor_records_become_rows(tmp_path):
    review = tmp_path / 'review'; review.mkdir()
    for i, (v, d) in enumerate([(0.0, 'missing_compound'), (0.73, 'keep')]):
        common.write_json(review / f'det_{i}.json', decision(i, value=v, decided=d))
    backup = tmp_path / 'backup.json'
    log = [dict(decision(9, rule='membership_candidate', value=3.2, decided='accepted'), decision_id='dec_9',
                scores=dict(heuristic_score=3.2, attachment_distance_px=0.5), decision_detail=dict(parent_id='L01'))]
    common.write_json(backup, dict(variants={'__all__': dict(membership=dict(decision_log=log))}))
    summary = tool.collect(tmp_path / 'out', [review], [backup])
    rows = list(csv.DictReader(open(tmp_path / 'out' / 'decisions.csv', encoding='utf-8')))
    assert [r['decision'] for r in rows] == ['missing_compound', 'keep', 'accepted']
    assert json.loads(rows[2]['scores_json'])['attachment_distance_px'] == 0.5
    assert rows[0]['record_ref'].startswith('det_0.json#sha256=')
    rules = {r['rule_id']: r for r in summary['rules']}
    assert rules['leaflet_inside_compound']['ready_to_fit'] is False
    assert any('one plant only' in why for why in rules['leaflet_inside_compound']['not_ready_because'])


def test_readiness_needs_enough_decisions_of_every_kind_from_two_plants():
    rows = [tool._row(dict(decision(i, decided='keep' if i % 2 else 'missing_compound', plant='dwt_01' if i < 60 else 'dwt_02')), 'x')
            for i in range(120)]
    assert tool.summarise(rows)['rules'][0]['ready_to_fit'] is True
    assert tool.summarise(rows[:40])['rules'][0]['ready_to_fit'] is False


def test_foreign_or_incomplete_records_are_refused(tmp_path):
    review = tmp_path / 'review'; review.mkdir()
    common.write_json(review / 'a.json', dict(decision='keep'))
    with pytest.raises(common.StudyError, match='Not a threshold-decision-log-1'):
        tool.collect(tmp_path / 'out', [review])
    common.write_json(review / 'a.json', decision(1)); common.write_json(review / 'b.json', decision(1))
    with pytest.raises(common.StudyError, match='Duplicate decision ids'):
        tool.collect(tmp_path / 'out2', [review])


def test_mask_reviews_record_the_default_mask_the_reviewer_saw(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    root = tmp_path / 'batch'; (root / 'items').mkdir(parents=True)
    logits = np.full((1, 20, 20), -5.0, np.float32); logits[0, 5:15, 5:15] = 3.0; logits[0, 5:15, 15:18] = 1.0
    key = 'k1'; (root / 'cache' / key).mkdir(parents=True)
    np.savez_compressed(root / 'cache' / key / 'logits.npz', logits=logits)
    common.write_json(root / 'cache' / key / 'result.json', dict(crop_px=[0, 0, 20, 20], scores=[0.9], default_candidate=0,
                                                               sensitivity=20, risk=dict(priority=1)))
    common.write_json(root / 'manifest.json', dict(schema_version='leaflet-mask-batch-1', ids=['a', 'b', 'c'],
                                                   session=str(tmp_path / 'sess' / 'edit_session'), photo_count=1, plant_id='P'))
    base = dict(plant_id='P', image_file='p.png', generation='ready', cache_key=key, selected_candidate=0, manual_rings=None,
                source_bbox_xywh_px=[5, 5, 13, 10], history=[dict(action='accept', at='t')], review_seconds=3, edit_seconds=0)
    common.write_json(root / 'items' / 'a.json', dict(base, id='a', review='accepted', changed=False, sensitivity=20, revision=2))
    common.write_json(root / 'items' / 'b.json', dict(base, id='b', review='accepted', changed=True, sensitivity=50, revision=4))
    common.write_json(root / 'items' / 'c.json', dict(base, id='c', review='unreviewed', changed=False, sensitivity=20, revision=1))
    rows = {r['object_id']: r for r in tool.from_mask_batch(root)}
    assert set(rows) == {'a', 'b'}, 'an open review is not a decision'
    a, b = (json.loads(rows[k]['scores_json']) for k in 'ab')
    assert rows['a']['decision'] == 'accepted_unchanged' and a['iou_default_vs_final'] == 1.0
    assert rows['b']['decision'] == 'accepted_edited' and b['final_sensitivity'] == 50
    # Default (sensitivity 20, logit > 2.4) keeps the 100 px core; widened to 50 (logit > 0) it is 130 px.
    assert a['default_fill_ratio'] == pytest.approx(100 / 130)
    assert b['iou_default_vs_final'] == pytest.approx(100 / 130) and b['default_pieces'] == 1
    assert rows['a']['score_name'] == 'default_fill_ratio' and rows['a']['rule_id'] == 'mask_default_threshold'
