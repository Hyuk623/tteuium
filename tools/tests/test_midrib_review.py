"""Human anchors, source immutability and missing-evidence behavior."""
import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from tools import midrib_review as mr, leaf_preprocess_lab as lab
from tools.tests.test_midrib_flow import _leaf


def fixture_input():
    rgb,mask,line=_leaf(True)
    anchors=[[60, int(line[line[:,0]==60,1][0])], [260,int(line[line[:,0]==260,1][0])]]
    return rgb,mask,anchors,line


def test_original_coordinate_path_and_input_preservation():
    rgb,mask,anchors,line=fixture_input(); before=rgb.copy(); mask_before=mask.copy()
    offset=np.array([101,207]); original=(np.array(anchors)+offset).tolist()
    r=mr.propose(rgb,mask,rgb,original,[101,207,421,367],{})
    assert r['status']=='proposed'
    path=np.array(r['path_original_px'])-offset
    np.testing.assert_array_equal(path[[0,-1]],anchors)
    truth=dict(line.tolist())
    assert np.median([abs(y-truth[x]) for x,y in path if x in truth])<=3
    assert np.all(r['valid'][path[:,1],path[:,0]])
    np.testing.assert_array_equal(rgb,before);np.testing.assert_array_equal(mask,mask_before)


def test_mask_gap_is_not_bridged():
    rgb,mask,anchors,_=fixture_input();mask[:,155:165]=False
    r=mr.propose(rgb,mask,rgb,anchors,[0,0,320,160],{})
    assert r['status']=='unavailable' and not r['path_original_px']


def test_no_anchor_snapping_and_no_uniform_image_path():
    rgb,mask,anchors,_=fixture_input()
    r=mr.propose(rgb,mask,rgb,[[0,0],anchors[1]],[0,0,320,160],{})
    assert r['status']=='unavailable'
    uniform=np.full_like(rgb,100)
    r=mr.propose(uniform,mask,uniform,anchors,[0,0,320,160],{})
    assert r['status']=='unavailable'


@pytest.mark.parametrize('points', [[[float('nan'),20]], [[True,20]], [[-1,20]], [[5.2,20]]])
def test_invalid_anchor_coordinates(points):
    rgb,mask,_,_=fixture_input()
    with pytest.raises(ValueError):mr.propose(rgb,mask,rgb,points,[0,0,320,160],{})


@pytest.mark.parametrize('cfg',[{'sigma_px':0},{'sigma_px':float('inf')},{'polarity':'both'},{'channel':'unknown'}])
def test_invalid_options(cfg):
    with pytest.raises(ValueError):mr.parse_options(cfg)


def test_lab_save_is_derived_and_preserves_source(tmp_path,monkeypatch):
    monkeypatch.setattr(lab,'assert_build',lambda p:Path(p).resolve())
    rgb,mask,anchors,_=fixture_input()
    src=tmp_path/'session';src.mkdir();export=tmp_path/'export';export.mkdir()
    photo=src/'photo.png';mask_path=export/'mask.png'
    Image.fromarray(rgb).save(photo);Image.fromarray(mask.astype(np.uint8)*255).save(mask_path)
    lab.write_json(src/'capture.json',{'frames':[{'image_file':'photo.png','image_path':'photo.png','sha256':lab.sha(photo)}]})
    accepted=export/'accepted.json'
    lab.write_json(accepted,{'schema_version':'accepted-leaflet-masks-1','observations':[dict(
        id='fixture',plant_id='fixture',source_annotation_id=1,image_file='photo.png',image_sha256=lab.sha(photo),
        image_size_px=[320,160],mask_file='mask.png',mask_area_px=int(mask.sum()),review='accepted_by_user',
        image_provenance={'view_group':'side'})]})
    run=tmp_path/'run';doc=lab.prepare([accepted],[src],run);app=lab.Lab(run)
    hashes={p:lab.sha(Path(p)) for p in doc['sources']}
    r=app.save_midrib('sample_000',lab.DEFAULTS,anchors,{},'candidate','synthetic test only')
    record=r['record']
    assert record['proposal']['path_original_px'][0]==anchors[0]
    assert not record['physical_point_identity_confirmed'] and not record['inference_run']
    assert (run/r['relative_path']/'path.csv').exists()
    assert all(lab.sha(Path(p))==h for p,h in hashes.items())
    r2=app.save_midrib('sample_000',lab.DEFAULTS,anchors,{},'confirmed_2d','fixture')
    assert r2['relative_path']!=r['relative_path']
    assert not r2['record']['suitable_for_ppfd']
    mask_path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):
        app.save_midrib('sample_000',lab.DEFAULTS,anchors,{},'candidate','')
