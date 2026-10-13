"""Pure numerical/preprocessing tests do not masquerade as checkpoint inference."""
import math

import numpy as np
from PIL import Image
import pytest

from tools import completion_viewfusion as vf
from tools.leaf_light import common


def test_camera_condition_matches_zero123_polar_and_wrap():
    result=vf.camera_condition([60,10,1.7],[90,350,1.5])
    assert result==pytest.approx([-math.pi/6,math.sin(math.pi/9),math.cos(math.pi/9),.2])
    assert vf.camera_condition([5,10,1.5],[5,10,1.5])==pytest.approx([0,0,1,0])


@pytest.mark.parametrize('pose',[[181,0,1],[0,0,0],[float('nan'),0,1]])
def test_invalid_camera_condition(pose):
    with pytest.raises(common.StudyError):vf.camera_condition(pose,[90,0,1])


def test_original_image_and_mask_are_immutable(tmp_path):
    image=tmp_path/'photo.png';mask=tmp_path/'mask.png'
    Image.new('RGB',(12,8),(20,100,30)).save(image)
    pixels=np.zeros((8,12),np.uint8);pixels[2:6,4:8]=255
    Image.fromarray(pixels).save(mask)
    before=[common.file_hash(p) for p in (image,mask)]
    request=dict(assets=[dict(asset_id='image',path='photo.png'),dict(asset_id='mask',path='mask.png')],
                 observations=[dict(image_id='v',role='condition',image_asset_id='image',mask_asset_id='mask',
                                    model_crop_xyxy_px=[2,0,10,8],model_pose_polar_azimuth_radius=[90,0,1.5],
                                    model_pose_source='synthetic fixture')])
    arrays,poses,transforms=vf.load_conditions(request,tmp_path)
    assert arrays.shape==(1,3,256,256) and arrays.dtype==np.float32
    assert arrays.min()>=-1 and arrays.max()<=1
    # Lanczos filtering can ring near a sharp foreground/background boundary.
    assert np.all(arrays[0,:,0,0] > .98)
    assert transforms[0]['resize_scale']==32
    assert [common.file_hash(p) for p in (image,mask)]==before
    request['observations'][0]['role']='evaluation'
    with pytest.raises(common.StudyError,match='Evaluator'):
        vf.load_conditions(request,tmp_path)


def test_package_rejects_execution_flag_and_backend_revision(tmp_path):
    path=tmp_path/'request.json'
    common.write_json(path,dict(backend_execution_enabled=False))
    with pytest.raises(common.StudyError,match='not enabled'):
        vf.verify_package(path)
    common.write_json(path,dict(backend_execution_enabled=True,backend=dict(name='viewfusion_zero123',revision='unknown')))
    with pytest.raises(common.StudyError,match='revision'):
        vf.verify_package(path)


@pytest.mark.parametrize('frozen',[False,True])
def test_cpu_ema_applies_shadow_values_releases_buffers_and_preserves_flags(frozen):
    torch=pytest.importorskip('torch')
    class Ema(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.m_name2s_name={'weight':'weight'}
            self.register_buffer('weight',torch.tensor([[7.,8.]]))
        def copy_to(self,model):
            assert model.weight.requires_grad, 'LitEma requires tracked parameters to be trainable during copy'
            model.weight.data.copy_(self.weight)
    model=torch.nn.Module();model.model=torch.nn.Linear(2,1,bias=False)
    model.model_ema=Ema();model.use_ema=True
    model.model.weight.requires_grad_(not frozen)
    assert vf.apply_ema_on_cpu(model)
    torch.testing.assert_close(model.model.weight,torch.tensor([[7.,8.]]))
    assert model.model.weight.requires_grad is not frozen
    assert not model.use_ema and not hasattr(model,'model_ema')
    assert vf.apply_ema_on_cpu(model) is False


def test_ema_copy_failure_preserves_flags_and_does_not_claim_application():
    torch=pytest.importorskip('torch')
    class Ema(torch.nn.Module):
        m_name2s_name={'weight':'weight'}
        def copy_to(self,model):raise RuntimeError('copy failure')
    model=torch.nn.Module();model.model=torch.nn.Linear(2,1,bias=False)
    model.model.weight.requires_grad_(False)
    model.model_ema=Ema();model.use_ema=True
    with pytest.raises(RuntimeError,match='copy failure'):vf.apply_ema_on_cpu(model)
    assert model.model.weight.requires_grad is False
    assert model.use_ema and hasattr(model,'model_ema')


def test_cached_conditioning_keeps_modal_values_and_no_autograd():
    torch=pytest.importorskip('torch')
    class Model:
        calls=[]
        def get_learned_conditioning(self,images):
            self.calls.append('clip');return images+2
        def encode_first_stage(self,images):
            self.calls.append('vae')
            class Distribution:
                def mode(self):return images*3
            return Distribution()
    model=Model();images=torch.tensor([1.,2.],requires_grad=True)
    embedding,latent=vf.encode_conditions(model,images,False)
    assert model.calls==['clip','vae']
    torch.testing.assert_close(embedding,torch.tensor([3.,4.]))
    torch.testing.assert_close(latent,torch.tensor([3.,6.]))
    assert not embedding.requires_grad and not latent.requires_grad
