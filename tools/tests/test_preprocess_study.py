import numpy as np
import pytest
from scipy.signal import savgol_filter
from tools import preprocess_study as ps
from tools.preprocess_compare import box_metrics
from tools import leaf_preprocess_lab as lab


def test_original_pixels_channel_order_and_input_preserved():
    rgb=np.random.default_rng(4).integers(0,256,(31,45,3),dtype=np.uint8)
    before=rgb.copy()
    assert np.array_equal(ps.process_rgb(rgb),rgb)
    for m in ps.SMOOTHING:
        out=ps.process_rgb(rgb,m)
        assert out.shape==rgb.shape and out.dtype==np.uint8
    assert np.array_equal(rgb,before)
    rgb=np.full((20,20,3),[170,70,30],np.uint8)
    assert ps.process_rgb(rgb,'sg5')[10,10,0]>ps.process_rgb(rgb,'sg5')[10,10,2]


def test_separable_sg_and_polynomial_preservation():
    y,x=np.indices((31,33)); v=(x*x+2*y*y+x*y).astype(np.float32)
    expected=savgol_filter(savgol_filter(v,7,2,axis=1,mode='mirror'),7,2,axis=0,mode='mirror')
    assert np.allclose(ps.smooth(v,'sg7'),expected)
    assert np.allclose(ps.smooth(v,'sg7')[4:-4,4:-4],v[4:-4,4:-4],atol=.001)


def test_sg_overshoot_retained_not_clipped():
    a=np.zeros((31,31),np.float32);a[:,15:]=1
    out,_,_,stats=ps.scalar_result(a,np.ones_like(a,bool),'sg7')
    assert np.nanmin(out)<0 and np.nanmax(out)>1 and stats['out_of_range_count']>0
    assert ps.display_scalar(out).dtype==np.uint8


def test_ratio_before_filter_and_stored_not_linear_rgb():
    rgb=np.zeros((25,25,3),np.uint8);rgb[:,:12]=[200,100,50];rgb[:,12:]=[10,40,20]
    raw=ps.scalar_maps(rgb)['green']
    assert raw[5,5]==pytest.approx(100/350)
    out,_,_,_=ps.scalar_result(raw,np.ones((25,25),bool),'mean3')
    ratio_after=ps.scalar_maps(ps.process_rgb(rgb,'mean3'))['green']
    assert not np.allclose(out[8:16,11:14],ratio_after[8:16,11:14])


def test_boundary_holes_nan_common_support_and_no_background_fill():
    a=np.full((45,45),.4,np.float32);a[:,0:8]=.9;a[20,20]=np.nan
    mask=np.zeros((45,45),bool);mask[8:38,8:38]=True;mask[12,12]=False
    before=mask.copy(); common=[]
    for m in ps.SMOOTHING:
        out,valid,c,stats=ps.scalar_result(a,mask,m)
        common.append(c)
        assert not c[20,20] and not c[12,12] and not c[9,9]
        assert np.isnan(out[~valid]).all()
        assert np.allclose(out[c],.4,atol=1e-6)
    assert all(np.array_equal(common[0],c) for c in common)
    assert np.array_equal(mask,before)


def test_cache_separates_recipe_image_model_and_prompts():
    a=np.zeros((8,8,3),np.uint8);r=ps.recipe();p={'model':'A','prompts':[]}
    key=ps.cache_key(a,r,p)
    assert key!=ps.cache_key(a,ps.recipe('sg5'),p)
    assert key!=ps.cache_key(a+1,r,p)
    assert key!=ps.cache_key(a,r,{'model':'B','prompts':[]})
    assert key!=ps.cache_key(a,r,{'model':'A','prompts':[[1,2]]})


def test_one_to_one_matching_duplicate_false_positive_and_missing():
    truth={'a':[{'cls':1,'xyxy':[0,0,10,10]},{'cls':1,'xyxy':[20,20,30,30]}]}
    preds={'a':[(1,[0,0,10,10],.9),(1,[0,0,10,10],.8)]}
    r=box_metrics(preds,truth,1)
    assert (r['true_positive'],r['false_positive'],r['false_negative'])==(1,1,1)
    assert r['recall']==.5 and r['precision']==.5
    assert box_metrics(preds,truth,4)['ap50_production'] is None


def test_study_controls_do_not_stack_or_modify_legacy():
    with pytest.raises(ValueError):
        lab.settings({'protocol':'study','ev':.5})
    with pytest.raises(ValueError):
        ps.recipe('sg5','gamma_clahe')
    assert lab.settings({})['protocol']=='legacy'


def test_zero_ratio_excluded_and_empty_mask_unavailable():
    rgb=np.zeros((50,50,3),np.uint8)
    raw=ps.scalar_maps(rgb)['red']
    a,v,c,s=ps.scalar_result(raw,np.ones((50,50),bool),'sg5')
    assert not v.any() and not c.any() and s['minimum'] is None
    _,_,_,s=ps.scalar_result(np.ones((50,50),np.float32),np.zeros((50,50),bool),'sg5')
    assert s['common_percent']==0 and s['out_of_range_percent'] is None


def test_colab_notebook_is_valid_python_and_gpu_guarded():
    import nbformat
    from tools.preprocess_colab import make_notebook
    n=make_notebook('a'*64); nbformat.validate(n)
    cells=[c.source for c in n.cells if c.cell_type=='code']
    for source in cells: compile(source,'cell','exec')
    assert 'assert torch.cuda.is_available()' in cells[0]
    assert "'--device','cuda'" in ''.join(cells)


def test_result_import_rejects_traversal_before_writing(tmp_path,monkeypatch):
    import zipfile
    from tools import preprocess_colab as pc
    monkeypatch.setattr(pc,'assert_build',lambda p:p)
    archive=tmp_path/'bad.zip';out=tmp_path/'out'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('../original.png',b'bad')
    with pytest.raises(ValueError):pc.import_results(archive,out)
    assert not out.exists()
