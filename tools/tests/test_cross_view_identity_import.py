import json
import shutil

import pytest

from tools import cross_view_identity_import as xv
from tools.leaf_light.common import StudyError


def decision(object_id, kind, verdict, panels, plant='p1'):
    return dict(schema_version='threshold-decision-log-1', object_id=object_id, plant_id=plant, decision=verdict,
                decision_detail=dict(kind=kind, masks=[dict(view=v, mask_ids=ids) for v, ids in panels]))


class FakeBatch:
    def __init__(self, items):
        self.items = items

    def item(self, mask_id):
        return self.items[mask_id]


ITEMS = {'m1': dict(image_file='p1_1.png', source_annotation_id=1), 'm2': dict(image_file='p1_2.png', source_annotation_id=2),
         'm3': dict(image_file='p1_3.png', source_annotation_id=3), 'm4': dict(image_file='p1_1.png', source_annotation_id=4),
         'm5': dict(image_file='p1_2.png', source_annotation_id=5)}


def test_same_links_chain_and_duplicate_keeps_directly_linked_mask():
    docs = [decision('a', 'match', 'same', [('1', ['m1']), ('2', ['m2'])]),
            decision('b', 'match', 'same', [('2', ['m2']), ('3', ['m3'])]),
            decision('c', 'dup', 'duplicate', [('1', ['m1', 'm4']), ('2', ['m2'])])]
    plans, skipped = xv.plan_groups(xv.group_decisions(docs, 'p1'), FakeBatch(ITEMS))
    assert len(plans) == 1
    assert [o['mask_id'] for o in plans[0]['observations']] == ['m1', 'm2', 'm3']
    assert skipped == [dict(group_id='xv_001', masks=['m4'], reason='duplicate_mask_not_adopted')]
    assert set(plans[0]['provenance']['decision_ids']) == {'a', 'b', 'c'}


def test_different_decision_inside_a_group_blocks_the_whole_group():
    docs = [decision('a', 'match', 'same', [('1', ['m1']), ('2', ['m2'])]),
            decision('b', 'match', 'same', [('2', ['m2']), ('3', ['m3'])]),
            decision('c', 'pair', 'different', [('1', ['m1']), ('3', ['m3'])])]
    decided = xv.group_decisions(docs, 'p1')
    plans, skipped = xv.plan_groups(decided, FakeBatch(ITEMS))
    assert plans == [] and decided['conflicts'][0]['decision'] == 'c'
    assert skipped[0]['reason'] == 'conflicts_with_a_different_decision'


def test_unsure_different_and_single_photo_create_nothing():
    docs = [decision('a', 'match', 'unsure', [('1', ['m1']), ('2', ['m2'])]),
            decision('b', 'match', 'different', [('1', ['m4']), ('2', ['m5'])]),
            decision('c', 'dup', 'duplicate', [('1', ['m1', 'm4']), ('2', ['m2'])])]
    plans, skipped = xv.plan_groups(xv.group_decisions(docs, 'p1'), FakeBatch(ITEMS))
    # the duplicate pair is one leaf seen in one photo only, and neither mask has a direct link
    assert plans == [] and {s['reason'] for s in skipped} == {'several_masks_in_one_photo_without_one_direct_link', 'fewer_than_two_photos'}


def test_merged_mask_is_never_adopted():
    docs = [decision('a', 'match', 'same', [('1', ['m1']), ('2', ['m2'])]),
            decision('b', 'match', 'same', [('2', ['m2']), ('3', ['m3'])]),
            decision('m', 'merge', 'merged', [('3', ['m3']), ('2', ['m2'])])]
    plans, skipped = xv.plan_groups(xv.group_decisions(docs, 'p1'), FakeBatch(ITEMS))
    assert [o['mask_id'] for o in plans[0]['observations']] == ['m1', 'm2']
    assert any(s['reason'] == 'mask_judged_to_merge_leaves' for s in skipped)


def test_other_plant_decision_is_refused():
    with pytest.raises(StudyError):
        xv.group_decisions([decision('a', 'match', 'same', [('1', ['m1']), ('2', ['m2'])], plant='p2')], 'p1')


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js required')
def test_editor_code_adopts_and_confirms_without_touching_visibility(tmp_path, monkeypatch):
    det = lambda aid, sid, x: dict(class_name='leaflet', annotation_id=aid, object_id=aid, image_width_px=100, image_height_px=100,
                                   bbox=dict(x_min_px=x, y_min_px=10, x_max_px=x + 20, y_max_px=30), source=dict(source_annotation_id=sid))
    backup = dict(plant_id='p1', session_id='s1',
                  capture=dict(intrinsics=dict(image_width_px=100, image_height_px=100),
                               frames=[dict(image_file='p1_1.png'), dict(image_file='p1_2.png')]),
                  variants={'__all__': dict(leaflets={}, boxes={}, membership=dict(
                      detections={'p1_1.png': [det('d1', 1, 10), det('d4', 4, 50)], 'p1_2.png': [det('d2', 2, 12)]}))})
    (tmp_path / 'b.json').write_text(json.dumps(backup), encoding='utf-8')
    dec = tmp_path / 'dec'; dec.mkdir()
    (dec / 'a.json').write_text(json.dumps(decision('a', 'match', 'same', [('1', ['m1']), ('2', ['m2'])])), encoding='utf-8')
    monkeypatch.setattr(xv, 'Batch', lambda root: FakeBatch(ITEMS))
    report = xv.import_identities(tmp_path / 'b.json', [dec], tmp_path, tmp_path / 'out')
    assert len(report['applied']) == 1 and not report['skipped']
    new = json.loads((tmp_path / 'out' / 'identities.backup.json').read_text(encoding='utf-8'))
    leaf = next(iter(new['variants']['__all__']['leaflets'].values()))
    assert set(leaf['bboxes']) == {'p1_1.png', 'p1_2.png'}
    assert {str(b['source_detection']['source_annotation_id']) for b in leaf['bboxes'].values()} == {'1', '2'}
    assert all(s['identity_review'] == 'confirmed' and s['visibility'] == 'unknown' for s in leaf['view_status'].values())
    assert leaf['cross_view_review']['decision_ids'] == ['a']
    # the unlinked detection stays a detection
    d4 = new['variants']['__all__']['membership']['detections']['p1_1.png'][1]
    assert 'adopted_into' not in d4
    with pytest.raises(StudyError):
        xv.import_identities(tmp_path / 'b.json', [dec], tmp_path, tmp_path / 'out')


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js required')
def test_saved_review_file_with_visibility_answers(tmp_path, monkeypatch):
    det = lambda aid, sid, x: dict(class_name='leaflet', annotation_id=aid, object_id=aid, image_width_px=100, image_height_px=100,
                                   bbox=dict(x_min_px=x, y_min_px=10, x_max_px=x + 20, y_max_px=30), source=dict(source_annotation_id=sid))
    backup = dict(plant_id='p1', session_id='s1',
                  capture=dict(intrinsics=dict(image_width_px=100, image_height_px=100),
                               frames=[dict(image_file='p1_1.png'), dict(image_file='p1_2.png')]),
                  variants={'__all__': dict(leaflets={}, boxes={}, membership=dict(
                      detections={'p1_1.png': [det('d1', 1, 10)], 'p1_2.png': [det('d2', 2, 12)]}))})
    (tmp_path / 'b.json').write_text(json.dumps(backup), encoding='utf-8')
    same = decision('a', 'match', 'same', [('1', ['m1']), ('2', ['m2'])])
    vis_old = dict(decision('v', 'vis', 'visibility_set', [('1', ['m1']), ('2', ['m2'])]), visibility={'m1': 'partial', 'm2': 'full'}, decided_at='2026-09-22T01:00:00Z')
    vis_new = dict(vis_old, visibility={'m1': 'full', 'm2': 'unknown'}, decided_at='2026-09-22T02:00:00Z')
    (tmp_path / 'f1.json').write_text(json.dumps(dict(schema='cross-view-decisions-file-1', decisions=[same, vis_old])), encoding='utf-8')
    (tmp_path / 'f2.json').write_text(json.dumps(dict(schema='cross-view-decisions-file-1', decisions=[vis_new])), encoding='utf-8')
    monkeypatch.setattr(xv, 'Batch', lambda root: FakeBatch(ITEMS))
    report = xv.import_identities(tmp_path / 'b.json', [tmp_path / 'f1.json', tmp_path / 'f2.json'], tmp_path, tmp_path / 'out')
    leaf = next(iter(json.loads((tmp_path / 'out' / 'identities.backup.json').read_text(encoding='utf-8'))['variants']['__all__']['leaflets'].values()))
    # the later answer replaces the earlier one; 'unknown' is not an answer and leaves the default
    assert leaf['view_status']['p1_1.png']['visibility'] == 'full'
    assert leaf['view_status']['p1_2.png']['visibility'] == 'unknown'
    assert len(report['visibility_applied']) == 1
