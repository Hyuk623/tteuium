"""The optional completion boundary preserves source data and held-out isolation."""
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from tools import multiview_completion as mc
from tools.leaf_light import common


@pytest.fixture
def request_file(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    assets, views = [], []
    for name, role, group in [('top','condition','top'), ('side','condition','side'), ('heldout','evaluation','side')]:
        image = tmp_path/(name+'.png')
        Image.new('RGB',(8,8),(40,120,20)).save(image)
        assets.append(dict(asset_id=name, path=image.name, sha256=common.file_hash(image),
                           parent_asset_ids=[], source_image_ids=[name], provenance_status='declared', origin='observed'))
        views.append(dict(image_id=name, role=role, image_asset_id=name, original_size_px=[8,8], view_group=group))
    data = dict(schema=mc.SCHEMA, request_id='test', plant_id='p', session_id='s',
                deployment_mode='multiview', assets=assets, observations=views,
                movement_group_id='g', movement_evidence='synthetic fixture',
                composition='alternative_hypothesis_only', sample_selection='retain_all_declared_seeds',
                backend=dict(name='fixture',revision='fixture_rev',checkpoint='fixture_ckpt',
                             model_policy='user_authorized_public_trial',policy_source='synthetic test only'),
                budgets=dict(max_candidates=1,seeds=[123],steps=5,max_wall_time_s=60))
    path = tmp_path/'request.json'
    common.write_json(path,data)
    return path


def edit(request_file, function):
    data = common.read_json(request_file)
    function(data)
    common.write_json(request_file,data)


def test_prepare_does_not_expose_heldout_pixels(request_file, tmp_path):
    edit(request_file,lambda d:d.update(relative_area_baseline={'path':'all_views.csv'}, evaluator_private_metadata='secret_target'))
    original = {p:common.file_hash(p) for p in tmp_path.iterdir() if p.is_file()}
    result = mc.prepare_request(request_file,tmp_path/'prepared')
    assert result['status']=='prepared' and not result['backend_executed']
    package, manifest = mc.verify_prepared(tmp_path/'prepared')
    assert {a['asset_id'] for a in package['assets']}=={'top','side'}
    assert {v['image_id'] for v in package['observations']}=={'top','side'}
    assert not (tmp_path/'prepared/inputs/heldout.png').exists()
    assert 'relative_area_baseline' not in package and 'evaluator_private_metadata' not in package
    assert all(common.file_hash(p)==h for p,h in original.items())


def test_top_only_rejects_side_condition(request_file):
    edit(request_file,lambda d:d.update(deployment_mode='top_only'))
    assert 'top_only_contains_non_top_condition' in mc.audit_request(request_file)['blockers']


def test_dependency_closure_rejects_hidden_side_geometry(request_file):
    def mutate(d):
        d['deployment_mode']='top_only'
        d['observations'][1]['role']='evaluation'
        d['assets'][0]['parent_asset_ids']=['side']
    edit(request_file,mutate)
    assert 'forbidden_conditioning_dependency:side' in mc.audit_request(request_file)['blockers']


def test_dependency_cycles_and_missing_parents(request_file):
    edit(request_file,lambda d:d['assets'][0].update(parent_asset_ids=['top']))
    with pytest.raises(common.StudyError,match='Cyclic'):
        mc.audit_request(request_file)
    edit(request_file,lambda d:d['assets'][0].update(parent_asset_ids=['missing']))
    with pytest.raises(common.StudyError,match='Unknown dependency'):
        mc.audit_request(request_file)


def test_input_hash_and_size_validation(request_file):
    edit(request_file,lambda d:d['assets'][0].update(sha256='incorrect'))
    with pytest.raises(common.StudyError,match='hash mismatch'):
        mc.audit_request(request_file)


@pytest.mark.parametrize('mutation,reason',[
    (lambda d:d['backend'].update(model_policy='unknown'),'model_policy_evidence_missing'),
    (lambda d:d['budgets'].update(max_candidates=0),'budget_missing:max_candidates'),
    (lambda d:d['budgets'].update(seeds=[1,1]),'explicit_unique_seeds_required'),
    (lambda d:d['assets'][0].update(provenance_status='unknown'),'unknown_dependency_provenance:top'),
    (lambda d:d['assets'][0].update(origin='generative'),'generated_input_requires_separate_stage:top'),
    (lambda d:d.update(composition='union'),'composition_contract_not_implemented')])
def test_gates(request_file,mutation,reason):
    edit(request_file,mutation)
    assert reason in mc.audit_request(request_file)['blockers']


def bundle_fixture(request_file, tmp_path):
    prepared=tmp_path/'prepared'
    mc.prepare_request(request_file,prepared)
    package,manifest=mc.verify_prepared(prepared)
    candidate=tmp_path/'candidate';candidate.mkdir()
    image=candidate/'view.png';Image.new('RGB',(8,8)).save(image)
    bundle=dict(schema='completion-candidates-1',request_sha256=manifest['request_sha256'],
                conditioning_asset_ids=sorted(a['asset_id'] for a in package['assets']),
                backend=package['backend'],backend_executed=True,
                candidates=[dict(candidate_id='seed123',seed=123,origin='generative',
                                 validated_metric=False,suitable_for_ppfd=False,representation='novel_view_rgb',
                                 views=[dict(target_id='virtual',path='view.png',sha256=common.file_hash(image),size_px=[8,8])])])
    common.write_json(candidate/'bundle.json',bundle)
    return prepared,candidate/'bundle.json'


def test_import_and_review_keep_hypothesis_separate(request_file,tmp_path):
    prepared,bundle=bundle_fixture(request_file,tmp_path)
    result=mc.import_candidate_bundle(prepared,bundle,tmp_path/'imported')
    assert result['metric_geometry_status']=='unavailable_from_novel_view_rgb'
    view=mc.export_review_bundle(tmp_path/'imported',tmp_path/'review')
    assert Path(view['viewer']).is_file()
    assert '생성된 시점' in Path(view['viewer']).read_text(encoding='utf-8')
    assert not any(tmp_path.rglob('candidate_surfaces.csv'))
    evaluation=mc.evaluate_candidates(prepared,tmp_path/'imported',tmp_path/'evaluation')
    assert evaluation['status']=='evaluation_unavailable'
    assert all(r['value'] is None for r in evaluation['rows'])


@pytest.mark.parametrize('field,value,message',[
    ('request_sha256','wrong','request hash'),('conditioning_asset_ids',['heldout'],'closure mismatch'),
    ('backend_executed',False,'not an executed')])
def test_candidate_provenance_refused(request_file,tmp_path,field,value,message):
    prepared,bundle=bundle_fixture(request_file,tmp_path)
    d=common.read_json(bundle);d[field]=value;common.write_json(bundle,d)
    with pytest.raises(common.StudyError,match=message):
        mc.import_candidate_bundle(prepared,bundle,tmp_path/'imported')


def test_candidate_cannot_be_optical_or_drop_seeds(request_file,tmp_path):
    prepared,bundle=bundle_fixture(request_file,tmp_path)
    d=common.read_json(bundle);d['candidates'][0]['suitable_for_ppfd']=True;common.write_json(bundle,d)
    with pytest.raises(common.StudyError,match='optical'):
        mc.import_candidate_bundle(prepared,bundle,tmp_path/'imported')
    d['candidates'][0]['suitable_for_ppfd']=False;d['candidates'][0]['seed']=999;common.write_json(bundle,d)
    with pytest.raises(common.StudyError,match='declared seeds'):
        mc.import_candidate_bundle(prepared,bundle,tmp_path/'imported')


def test_tampered_prepared_asset_refused(request_file,tmp_path):
    mc.prepare_request(request_file,tmp_path/'prepared')
    (tmp_path/'prepared/inputs/top.png').write_bytes(b'changed')
    with pytest.raises(common.StudyError,match='changed'):
        mc.verify_prepared(tmp_path/'prepared')


def test_known_visibility_metric_preserves_unknown_and_empty():
    observed=np.array([[1,1],[0,0]],bool);predicted=np.array([[1,0],[1,0]],bool)
    known=np.array([[1,1],[0,0]],bool)
    result=mc.silhouette_metric(predicted,observed,known)
    assert result['value']==.5 and result['denominator']==2 and result['excluded_pixels']==2
    assert mc.silhouette_metric(predicted,observed,np.zeros((2,2),bool))['value'] is None


CONTRACT_TARGETS=[dict(target_id='T_eval',source='declared_virtual_pose',model_pose_polar_azimuth_radius=[60,80,1.25],passes_pose_gate=False),
                  dict(target_id='T_ring_000',source='declared_virtual_pose',model_pose_polar_azimuth_radius=[60,0,1.5],passes_pose_gate=False)]
CONTRACT=dict(heldout_image_ids=['heldout'],targets=CONTRACT_TARGETS,seeds=[123],
              sampler=dict(steps=5,max_wall_time_s_per_arm=60,guidance_scale=3.,ddim_eta=0.,autocast=True,
                           checkpoint='fixture_ckpt',checkpoint_sha256='fixture_hash'),
              arms=dict(multiview=dict(condition_image_ids=['top','side'],condition_weights='equal'),
                        top_only=dict(condition_image_ids=['top'],forbidden_image_ids=['side'],condition_weights='equal')))


def arm_archives(request_file,tmp_path,targets_by_arm=None,top_only_side_role='evaluation',mutate_arm=None):
    from tools import completion_package as cp
    from tools.completion_viewfusion import REVISION
    vendor=tmp_path/'vendor';vendor.mkdir(exist_ok=True)
    (vendor/'LICENSE').write_text('Synthetic source fixture, not a model',encoding='utf-8')
    common.write_json(vendor/'source_manifest.json',dict(revision=REVISION,files={'LICENSE':common.file_hash(vendor/'LICENSE')}))
    archives={}
    for arm in ('multiview','top_only'):
        targets=(targets_by_arm or {}).get(arm,CONTRACT_TARGETS)
        weights=[1.0,1.0] if arm=='multiview' or top_only_side_role=='condition' else [1.0]
        def mutate(d):
            d['deployment_mode']=arm
            d['observations'][1]['role']='condition' if arm=='multiview' else top_only_side_role
            d['backend'].update(name='viewfusion_zero123',revision=REVISION,checkpoint_sha256='fixture_hash',
                                parameters={k:CONTRACT['sampler'][k] for k in ('guidance_scale','ddim_eta','autocast')})
            d['budgets']['max_target_views']=len(targets)
            d['targets']=[dict(t,condition_weights=weights) for t in targets]
            if mutate_arm: mutate_arm(d,arm)
        edit(request_file,mutate)
        prepared=tmp_path/f'{arm}_prepared';mc.prepare_request(request_file,prepared)
        archives[arm]=Path(cp.pack(prepared,vendor,tmp_path/f'{arm}_package')['archive'])
    return archives


def test_arm_archives_share_contract_targets_and_isolation(request_file,tmp_path):
    from tools import completion_package as cp
    report=cp.verify_arm_isolation(CONTRACT,arm_archives(request_file,tmp_path))
    assert report['arms']['top_only']['condition_image_ids']==['top']
    assert report['arms']['multiview']['target_ids']==report['arms']['top_only']['target_ids']==['T_eval','T_ring_000']


def test_arm_isolation_rejects_unmatched_targets(request_file,tmp_path):
    from tools import completion_package as cp
    moved=[dict(CONTRACT_TARGETS[0],model_pose_polar_azimuth_radius=[60,95,1.25]),CONTRACT_TARGETS[1]]
    archives=arm_archives(request_file,tmp_path,targets_by_arm=dict(top_only=moved))
    with pytest.raises(common.StudyError,match='Target list differs'):
        cp.verify_arm_isolation(CONTRACT,archives)


def test_arm_isolation_rejects_side_data_in_top_only(request_file,tmp_path):
    from tools import completion_package as cp
    # The audit blocks a side condition in top_only, so pack() refuses before upload.
    blocked=tmp_path/'blocked';blocked.mkdir()
    with pytest.raises(common.StudyError,match='not enabled'):
        arm_archives(request_file,blocked,top_only_side_role='condition')
    archives=arm_archives(request_file,tmp_path)
    import zipfile
    with zipfile.ZipFile(archives['top_only'],'a') as z:
        z.writestr('inputs/side.png',b'side pixels')
    with pytest.raises(common.StudyError,match='Forbidden content in top_only'):
        cp.verify_arm_isolation(CONTRACT,archives)


def test_archive_contains_no_evaluation_assets(request_file,tmp_path):
    import zipfile
    from tools import completion_package as cp
    from tools.completion_viewfusion import REVISION
    def change_backend(d):
        d['backend'].update(name='viewfusion_zero123',revision=REVISION)
        d['budgets']['max_target_views']=1
        d['targets']=[dict(target_id='virtual',source='declared_virtual_pose')]
    edit(request_file,change_backend)
    prepared=tmp_path/'prepared';mc.prepare_request(request_file,prepared)
    vendor=tmp_path/'vendor';vendor.mkdir()
    (vendor/'LICENSE').write_text('Synthetic source fixture, not a model',encoding='utf-8')
    common.write_json(vendor/'source_manifest.json',dict(revision=REVISION,files={'LICENSE':common.file_hash(vendor/'LICENSE')}))
    report=cp.pack(prepared,vendor,tmp_path/'package')
    assert not report['uploaded'] and not report['backend_executed']
    with zipfile.ZipFile(report['archive']) as archive:
        names=archive.namelist()
        assert 'inputs/top.png' in names and 'inputs/side.png' in names
        assert 'inputs/heldout.png' not in names
        assert 'request.snapshot.json' not in names and 'audit.json' not in names


@pytest.mark.parametrize('mutation,reason',[
    ('image_bytes','Archive member hash mismatch'),
    ('extra_file','Archive inventory differs'),
    ('duplicate','Duplicate archive member'),
    ('path_escape','Unsafe archive member'),
])
def test_archive_integrity_rejects_tampering(request_file,tmp_path,mutation,reason):
    import zipfile
    from tools import completion_package as cp
    archives=arm_archives(request_file,tmp_path)
    original=archives['top_only']
    replacement=tmp_path/'tampered.zip'
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(replacement,'w') as dest:
        for name in source.namelist():
            value=source.read(name)
            if mutation=='image_bytes' and name=='inputs/top.png':
                value=b'changed image bytes'
            dest.writestr(name,value)
        if mutation=='extra_file': dest.writestr('unlisted.png',b'extra')
        if mutation=='path_escape': dest.writestr('../outside.png',b'extra')
        if mutation=='duplicate':
            with pytest.warns(UserWarning,match='Duplicate name'):
                dest.writestr('inputs/top.png',b'shadow input')
    with pytest.raises(common.StudyError,match=reason):
        cp.verify_archive(replacement)
    if mutation=='image_bytes':
        archives['top_only']=replacement
        with pytest.raises(common.StudyError,match=reason):
            cp.verify_arm_isolation(CONTRACT,archives)


@pytest.mark.parametrize('field,value',[
    ('model_pose_polar_azimuth_radius',[60,95,1.25]),
    ('passes_pose_gate',True),
    ('passes_pose_gate',None),
])
def test_import_rejects_changed_or_missing_target_provenance(request_file,tmp_path,field,value):
    target=dict(target_id='virtual',model_pose_polar_azimuth_radius=[60,80,1.25],passes_pose_gate=False)
    edit(request_file,lambda d:d.update(targets=[target]))
    prepared,bundle=bundle_fixture(request_file,tmp_path)
    data=common.read_json(bundle)
    view=data['candidates'][0]['views'][0]
    view.update(target)
    if value is None:
        del view[field]
    else:
        view[field]=value
    common.write_json(bundle,data)
    with pytest.raises(common.StudyError,match='target provenance mismatch'):
        mc.import_candidate_bundle(prepared,bundle,tmp_path/'rejected')
    view.update(target)
    common.write_json(bundle,data)
    accepted=mc.import_candidate_bundle(prepared,bundle,tmp_path/'accepted')
    assert accepted['candidates'][0]['views'][0]['passes_pose_gate'] is False


@pytest.mark.parametrize('field,value,reason',[
    ('seeds',[999],'budget'),('steps',9,'budget'),('max_wall_time_s',61,'budget'),
    ('guidance_scale',2.,'parameters'),('ddim_eta',.1,'parameters'),('autocast',False,'parameters'),
    ('checkpoint','other','Checkpoint'),('checkpoint_sha256','other_hash','Checkpoint'),
    ('condition_weights',[1.,2.],'equal rule'),
])
def test_arm_contract_rejects_sampler_seed_checkpoint_weight_changes(request_file,tmp_path,field,value,reason):
    from tools import completion_package as cp
    def mutation(d,arm):
        if arm!='multiview': return
        if field in ('seeds','steps','max_wall_time_s'):d['budgets'][field]=value
        elif field in ('checkpoint','checkpoint_sha256'):d['backend'][field]=value
        elif field=='condition_weights':d['targets'][0][field]=value
        else:d['backend']['parameters'][field]=value
    with pytest.raises(common.StudyError,match=reason):
        cp.verify_arm_isolation(CONTRACT,arm_archives(request_file,tmp_path,mutate_arm=mutation))


def test_forbidden_image_prefix_is_not_an_identity_collision(request_file,tmp_path):
    from copy import deepcopy
    from tools import completion_package as cp
    def rename(d):
        d['assets'][0].update(asset_id='photo_130',source_image_ids=['photo_130'])
        d['observations'][0].update(image_id='photo_130',image_asset_id='photo_130')
    edit(request_file,rename)
    contract=deepcopy(CONTRACT)
    contract['heldout_image_ids'].append('photo_13')
    for arm in contract['arms']:contract['arms'][arm]['condition_image_ids'][0]='photo_130'
    assert cp.verify_arm_isolation(contract,arm_archives(request_file,tmp_path))['status']=='isolated_with_identical_targets'


def test_saved_partial_cannot_be_imported_even_with_full_inventory(request_file,tmp_path):
    from tools.completion_viewfusion import save_candidate_progress
    prepared,bundle=bundle_fixture(request_file,tmp_path)
    data=common.read_json(bundle)
    save_candidate_progress(bundle.parent,data)
    partial=bundle.parent/'candidate_bundle.partial.json'
    assert common.read_json(partial)['complete'] is False
    assert not (bundle.parent/'candidate_bundle.partial.tmp.json').exists()
    with pytest.raises(common.StudyError,match='Partial'):
        mc.import_candidate_bundle(prepared,partial,tmp_path/'partial_import')
    common.write_json(bundle,common.read_json(partial))
    with pytest.raises(common.StudyError,match='Partial'):
        mc.import_candidate_bundle(prepared,bundle,tmp_path/'renamed_partial')
    data['complete']=True
    common.write_json(bundle,data)
    assert mc.import_candidate_bundle(prepared,bundle,tmp_path/'final_import')['complete'] is True
