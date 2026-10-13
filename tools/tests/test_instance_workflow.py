from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools import instance_workflow as w
from tools import leaflet_mask_batch as masks
from tools.leaf_light import common
from tools.tests.test_leaflet_mask_batch import batch, action  # noqa: F401


def test_brush_preserves_small_regions_and_undo_without_inference(batch):
    b, _, _ = batch; b.run(); identity = b.manifest['ids'][0]
    original = b.mask(b.item(identity))[0].copy(); calls = b.segmenter.calls
    action(b, 'brush', strokes=[dict(mode='paint', radius_px=2, points_px=[[100, 30], [105, 30]]),
                              dict(mode='erase', radius_px=2, points_px=[[25, 25]])])
    current = b.mask(b.item(identity))[0]
    assert current[30, 102] and not current[25, 25] and current[90, 90] and not current[36,36]
    assert b.item(identity)['review'] == 'edited' and b.segmenter.calls == calls
    reloaded = masks.Batch(b.root)
    assert np.array_equal(reloaded.mask(reloaded.item(identity))[0], current)
    action(b, 'accept'); exported = b.export()
    assert np.asarray(Image.open(Path(exported['path'])/f'{identity}.png'))[30,102] == 255
    action(b, 'undo'); action(b, 'undo')
    assert np.array_equal(original, b.mask(b.item(identity))[0])
    assert b.segmenter.calls == calls


def test_brush_original_coordinates_clipping_and_lossless_raster():
    base = np.zeros((30,40), bool);base[0,0] = True
    changed = masks.brush_mask(base,[100,200,140,230],[dict(mode='paint',radius_px=2,points_px=[[110,210]])])
    assert changed[10,10] and changed[0,0] and not changed[20,20]
    assert np.array_equal(masks.unpack_mask(masks.pack_mask(changed), changed.shape), changed)
    with pytest.raises(common.StudyError, match='inside'):
        masks.brush_mask(base,[100,200,140,230],[dict(mode='erase',radius_px=2,points_px=[[99,210]])])


def test_snapshot_cached_sweep_preserves_settings_and_stale_on_edits(batch, tmp_path):
    b, _, _ = batch; b.run(); action(b,'select',sensitivity=71)
    settings = common.read_json(w.DEFAULTS)
    cap = common.read_json(b.session/'capture.json')
    cap.update(plant_id='dwt_01', session_id='S')
    cap['frames'][0].update(view_code='11', pose_status='failed')
    backup = dict(plant_id='dwt_01', session_id='S', variants={'__all__':{'leaflets':{}}})
    out=tmp_path/'snapshot';out.mkdir()
    before = {p: common.file_hash(p) for p in (b.root/'items').glob('*.json')}
    obs, raster, sig, hashes = w.snapshot(b,backup,cap,out,'sensitivity_sweep','pilot',settings)
    assert len(obs)==2 and all(o['leaf_key'] is None for o in obs)
    calls = b.segmenter.calls
    result = w.sensitivity_sweep(out,obs,{},settings,True)
    assert 71 in result['sensitivity_values'] and result['evaluated_photos']==0
    assert result['metric_status'].startswith('unavailable') and b.segmenter.calls==calls
    assert before=={p:common.file_hash(p) for p in before}
    common.write_json(out/'manifest.json',dict(input_signature=sig,source_hashes=hashes))
    assert w.stale_reasons(out,b,backup)==[]
    action(b,'defer')
    assert 'items' in w.stale_reasons(out,b,backup)
    new = deepcopy(backup);new['variants']['__all__']['leaflets']={'other':{}}
    assert 'backup' in w.stale_reasons(out,b,new)


def test_reference_coverage_eval_and_dwt02_freeze_gate(batch,tmp_path):
    b,_,_=batch;b.run()
    settings = common.read_json(w.DEFAULTS)
    cap=common.read_json(b.session/'capture.json');cap.update(plant_id='dwt_01',session_id='S')
    cap['frames'][0].update(view_code='11',pose_status='failed')
    backup=dict(variants={'__all__':{'leaflets':{}}})
    out=tmp_path/'snap';out.mkdir()
    obs,_,_,_=w.snapshot(b,backup,cap,out,'sensitivity_sweep','pilot',settings)
    # Independently constructed visible reference, not a prediction used as target.
    reference=dict(schema_version='instance-visible-reference-1',plant_id='dwt_01',session_id='S',version='1',reviewer='synthetic test',
        independent_manual_review=True,photos=[dict(image_file='photo.png',image_sha256=cap['frames'][0]['sha256'],coverage='complete_visible',
        instances=[dict(reference_id='a',visibility='full',origin='independent_manual',rings=[dict(points_px=[[20,20],[69,20],[69,69],[20,69]])])])])
    checked=w.validate_reference(reference,cap)
    result=w.sensitivity_sweep(out,obs,checked,settings,True)
    assert result['evaluated_photos']==1 and all(r['fp']>=1 for r in result['comparison'])
    assert w.sensitivity_sweep(out,obs,checked,settings,False)['evaluated_photos']==0
    checked['photo.png']['coverage']='incomplete'
    assert w.sensitivity_sweep(out,obs,checked,settings,True)['evaluated_photos']==0


def test_freeze_is_versioned_and_cannot_overwrite(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    root=tmp_path/'runs';root.mkdir();dev=root/'dev';dev.mkdir()
    common.write_json(dev/'manifest.json',dict(plant_id='dwt_01',settings=common.read_json(w.DEFAULTS)))
    common.write_json(dev/'result.json',dict(operation='sensitivity_sweep',evaluated_photos=0))
    frozen=w.freeze_parameters(dev,root/'frozen.json')
    assert frozen['validation']=='exploratory_unvalidated' and frozen['settings_sha256']==common.digest(frozen['settings'])
    with pytest.raises(common.StudyError,match='already exists'):
        w.freeze_parameters(dev,root/'frozen.json')


def growth_import(batch):
    b, labels, session = batch
    capture = dict(plant_id='dwt_01', session_id='dwt_01_20260920')
    base = session/'seed.backup.json'
    common.write_json(base, capture)
    growth_path = labels/'human_growth.json'
    growth = dict(plant_id='dwt_01', capture_date='2026-09-20', compound_leaves=[])
    common.write_json(growth_path, growth)
    b.manifest['input_hashes'].update({str(base): common.file_hash(base), str(growth_path): common.file_hash(growth_path)})
    common.write_json(labels/'seed_with_imports.backup.json', dict(**capture, seed_derivation=dict(
        tool='tools.roboflow_session_import', base_seed=str(base), base_seed_sha256=common.file_hash(base),
        coco=b.manifest['source_coco'], coco_sha256=b.manifest['source_coco_sha256'], growth_reference=str(growth_path))))
    masks.atomic_json(b.root/'manifest.json', b.manifest)
    return b, capture, growth_path, growth


def test_growth_metadata_refresh_is_derived_and_staleness_tracks_new_source(batch, tmp_path):
    b, capture, path, growth = growth_import(batch)
    before = {p: common.file_hash(p) for p in [b.root/'manifest.json', *b.root.glob('items/*.json')]}
    old = common.file_hash(path)
    growth['compound_leaves'] = [dict(compound_leaf_id='L04', leaflet_count=5)]
    common.write_json(path, growth)
    hashes, audit = w.checked_import_sources(b, capture)
    assert hashes[str(path)] == common.file_hash(path) != old
    assert audit['refreshed_references'][0]['old_sha256'] == old
    assert audit['growth_reference']['record'] == growth
    assert audit['growth_reference']['used_for_geometry'] is False
    assert b.manifest['input_hashes'][str(path)] == old
    assert before == {p: common.file_hash(p) for p in before}
    run = tmp_path/'derived'; run.mkdir()
    backup = dict(variants={})
    common.write_json(run/'manifest.json', dict(input_signature=w.input_signature(b, backup, b.manifest['ids']), source_hashes=hashes))
    assert w.stale_reasons(run,b,backup) == []
    common.write_json(path, {**growth, 'notes': 'later edit'})
    assert 'source_changed:human_growth.json' in w.stale_reasons(run,b,backup)
    with pytest.raises(common.StudyError, match='during snapshot'):
        w.verify_snapshot_sources(hashes)


@pytest.mark.parametrize('kind', ['image', 'labels', 'calibration', 'missing', 'unknown_json'])
def test_non_growth_import_changes_still_block(batch, kind):
    b, capture, path, growth = growth_import(batch)
    protected = path.parent/('other.png' if kind == 'image' else 'other.json')
    protected.write_text('original')
    b.manifest['input_hashes'][str(protected)] = common.file_hash(protected)
    common.write_json(path, {**growth, 'notes': 'allowed update'})
    if kind == 'missing':
        protected.unlink()
    else:
        protected.write_text('changed')
    with pytest.raises(common.StudyError, match='import validation failed'):
        w.checked_import_sources(b, capture)


@pytest.mark.parametrize('changes', [dict(plant_id='dwt_02'), dict(capture_date='2026-09-21'), dict(compound_leaves=None)])
def test_growth_identity_and_shape_are_validated(batch, changes):
    b, capture, path, growth = growth_import(batch)
    common.write_json(path, {**growth, **changes})
    with pytest.raises(common.StudyError, match='plant/date or record structure'):
        w.checked_import_sources(b, capture)


def test_growth_exemption_requires_verified_import_linkage(batch):
    b, capture, path, growth = growth_import(batch)
    seed = path.parent/'seed_with_imports.backup.json'
    data = common.read_json(seed)
    data['seed_derivation']['coco_sha256'] = 'wrong'
    common.write_json(seed, data)
    with pytest.raises(common.StudyError, match='linkage mismatch'):
        w.checked_import_sources(b, capture)
    seed.unlink()
    common.write_json(path, {**growth, 'notes': 'no declared role'})
    with pytest.raises(common.StudyError, match='protected import input changed'):
        w.checked_import_sources(b, capture)


@pytest.mark.parametrize('plant', ['dwt_03', 'dwt_04'])
def test_extra_plants_use_recorded_pilot_without_expanding_evaluation(batch, tmp_path, plant):
    b, _, _ = batch
    cap = common.read_json(b.session/'capture.json')
    cap.update(plant_id=plant, session_id='S')
    cap['frames'][0].update(view_code='11', pose_status='failed')
    out = tmp_path/'extra_pilot'; out.mkdir()
    w.check_operation_scope('instance_fusion', plant)
    with pytest.raises(common.StudyError, match='evaluation protocol'):
        w.check_operation_scope('sensitivity_sweep', plant)
    obs, _, _, _ = w.snapshot(b, dict(variants={'__all__': {'leaflets': {}}}), cap, out,
                             'instance_fusion', 'pilot', common.read_json(w.DEFAULTS))
    assert len(obs) == 2


@pytest.mark.parametrize('plant', w.FUSION_PLANTS)
def test_run_accepts_four_plants_without_inference(batch, tmp_path, monkeypatch, plant):
    b, capture, _, _ = growth_import(batch)
    # Synthetic ungenerated observations exercise the full wrapper and missing-evidence output.
    if plant != 'dwt_01':
        (Path(b.manifest['source_coco']).parent/'seed_with_imports.backup.json').unlink()
    else:
        growth = Path(b.manifest['source_coco']).parent/'human_growth.json'
        common.write_json(growth, dict(plant_id=plant, capture_date='2026-09-20', compound_leaves=[], notes='new human edit'))
    b.manifest['plant_id'] = plant
    masks.atomic_json(b.root/'manifest.json', b.manifest)
    cap = common.read_json(b.session/'capture.json')
    cap.update(plant_id=plant, session_id=f'{plant}_20260920', intrinsics_path=str(b.session/'intrinsics.json'),
               board_spec_path=str(b.session/'board.json'))
    cap['frames'][0].update(view_code='11', pose_status='failed')
    for name in ('session_report.json', 'context.json', 'intrinsics.json', 'board.json'):
        common.write_json(b.session/name, {})
    backup = dict(variants={'__all__': {'leaflets': {}}})
    monkeypatch.setattr(w, 'checked_inputs', lambda *args: (cap, {}, backup, {}))
    monkeypatch.setattr(w, 'fuse', lambda *args: dict(status='insufficient_evidence', voxels=[], exclusions=[]))
    out = tmp_path/'run'
    result = w.run('instance_fusion', b.session, b.session/'unused', b.session/'context.json', b.root, out, scope='all')
    assert result['inference_calls'] == 0 and not result['suitable_for_ppfd']
    assert common.read_json(out/'manifest.json')['plant_id'] == plant
    assert (out/'import_freshness.json').is_file()
    if plant == 'dwt_01':
        audit = common.read_json(out/'import_freshness.json')
        assert len(audit['refreshed_references']) == 1
        assert audit['growth_reference']['record']['notes'] == 'new human edit'


def test_missing_growth_reference_still_blocks(batch):
    b, capture, path, _ = growth_import(batch)
    path.unlink()
    with pytest.raises(common.StudyError, match='missing input'):
        w.checked_import_sources(b, capture)
