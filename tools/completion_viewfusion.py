"""Bounded ViewFusion/Zero123 inference in a separate GPU environment.

This module never installs packages or downloads checkpoints. It consumes the
prepared condition-only package, a pinned vendor tree and an explicit checkpoint.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import random
import signal
import sys
import time

import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json
from tools.multiview_completion import TARGET_PROVENANCE_KEYS, identifier, resolve

REVISION = '61286dc572ae3b4e8924ab51c45ca0bbd53c58ea'
MODEL_IMAGE_PX = 256


def apply_ema_on_cpu(model) -> bool:
    """Select EMA inference weights without a GPU backup or retained EMA buffers."""
    if not getattr(model, 'use_ema', False):
        return False
    import torch
    ema = model.model_ema
    parameters = dict(model.model.named_parameters())
    if any(p.device.type != 'cpu' for p in parameters.values()) or any(b.device.type != 'cpu' for b in ema.buffers()):
        raise StudyError('EMA must be applied before CUDA transfer')
    flags = {name:p.requires_grad for name,p in parameters.items()}
    try:
        # LitEma tracks names at construction and asserts if those parameters
        # were subsequently frozen. Restore flags after its native copy.
        for name,p in parameters.items():
            p.requires_grad_(name in ema.m_name2s_name)
        with torch.no_grad():
            ema.copy_to(model.model)
    finally:
        for name,p in parameters.items():
            p.requires_grad_(flags[name])
    del model.model_ema
    model.use_ema = False
    return True


def encode_conditions(model, images, autocast: bool):
    """Cache deterministic CLIP embeddings and VAE modes once per trial."""
    import torch
    with torch.inference_mode(), torch.autocast(images.device.type, enabled=autocast):
        embedding = model.get_learned_conditioning(images).detach()
        latent = model.encode_first_stage(images).mode().detach()
    return embedding, latent


def save_candidate_progress(folder: Path, report: dict) -> None:
    """Atomically preserve incomplete samples without creating a final bundle."""
    partial = dict(report, complete=False)
    temporary = folder/'candidate_bundle.partial.tmp.json'
    write_json(temporary, partial)
    temporary.replace(folder/'candidate_bundle.partial.json')


def camera_condition(target: list[float], reference: list[float]) -> list[float]:
    """Zero123 uses polar angle, azimuth and normalized radius differences.

    Angles in requests are degrees, matching repository file conventions.
    Radius has explicitly declared model units, never inferred millimetres.
    """
    if len(target) != 3 or len(reference) != 3 or not np.isfinite([target,reference]).all():
        raise StudyError('Finite polar/azimuth/radius triples required')
    if any(not 0 <= p[0] <= 180 or p[2] <= 0 for p in (target,reference)):
        raise StudyError('Invalid polar angle or model radius')
    dpolar = math.radians(target[0]-reference[0])
    dazimuth = math.radians(target[1]-reference[1]) % (2*math.pi)
    return [dpolar, math.sin(dazimuth), math.cos(dazimuth), target[2]-reference[2]]


def load_conditions(request: dict, base: Path) -> tuple[np.ndarray, list[list[float]], list[dict]]:
    assets = {a['asset_id']:a for a in request['assets']}
    arrays, poses, transforms = [], [], []
    for view in request['observations']:
        if view['role'] != 'condition':
            raise StudyError('Evaluator image found in backend package')
        image_path = resolve(base, assets[view['image_asset_id']]['path'])
        with Image.open(image_path) as source:
            picture = source.convert('RGB')
        crop = view.get('model_crop_xyxy_px')
        if (not isinstance(crop,list) or len(crop)!=4 or any(type(v) is not int for v in crop)
                or not 0 <= crop[0] < crop[2] <= picture.width
                or not 0 <= crop[1] < crop[3] <= picture.height):
            raise StudyError('Explicit original-pixel model crop required')
        if crop[2]-crop[0] != crop[3]-crop[1]:
            raise StudyError('Square model crop required; no implicit aspect distortion')
        if view.get('mask_asset_id'):
            with Image.open(resolve(base,assets[view['mask_asset_id']]['path'])) as source:
                foreground = source.convert('L')
            if foreground.size != picture.size:
                raise StudyError('Condition mask size mismatch')
            picture = Image.composite(picture,Image.new('RGB',picture.size,'white'),foreground)
        picture = picture.crop(crop).resize((MODEL_IMAGE_PX,MODEL_IMAGE_PX),Image.Resampling.LANCZOS)
        pose = view.get('model_pose_polar_azimuth_radius')
        camera_condition(pose,pose)
        if not view.get('model_pose_source'):
            raise StudyError('Model pose assumption/provenance required')
        poses.append(pose)
        arrays.append(np.asarray(picture,dtype=np.float32).transpose(2,0,1)/127.5-1.)
        transforms.append(dict(image_id=view['image_id'],crop_xyxy_px=crop,
                               model_size_px=[MODEL_IMAGE_PX,MODEL_IMAGE_PX],
                               resize_scale=MODEL_IMAGE_PX/(crop[2]-crop[0]),
                               background='saved_mask_white_composite' if view.get('mask_asset_id') else 'original',
                               metric_projection_validated=False))
    if not arrays:
        raise StudyError('No condition images')
    return np.stack(arrays),poses,transforms


def verify_package(path: Path) -> dict:
    request = read_json(path)
    if request.get('backend_execution_enabled') is not True or request.get('preparation_blockers'):
        raise StudyError('Request is not enabled for backend execution')
    if request.get('backend',{}).get('name') != 'viewfusion_zero123':
        raise StudyError('Wrong backend')
    if request['backend'].get('revision') != REVISION:
        raise StudyError('Uninspected backend revision')
    if request['backend'].get('model_policy') not in ('user_authorized_public_trial','user_tuned'):
        raise StudyError('Model policy not eligible')
    allowed = {v['image_id'] for v in request['observations']}
    for asset in request['assets']:
        if not set(asset['source_image_ids']).issubset(allowed):
            raise StudyError('Forbidden backend dependency')
        if file_hash(resolve(path.parent,asset['path'])) != asset['sha256']:
            raise StudyError('Backend input hash mismatch')
    seeds = request['budgets']['seeds']
    if (not seeds or len(set(seeds))!=len(seeds) or
            len(seeds)>request['budgets']['max_candidates']):
        raise StudyError('Invalid candidate budget')
    targets = request.get('targets',[])
    if not targets or len(targets)>request['budgets']['max_target_views']:
        raise StudyError('Target view budget exceeded or targets absent')
    ids = [identifier(t['target_id']) for t in targets]
    if len(set(ids))!=len(ids) or any(t.get('source')!='declared_virtual_pose' for t in targets):
        raise StudyError('Unique deployment-known virtual targets required')
    return request


def run(request_path: Path, vendor: Path, checkpoint: Path, out: Path) -> dict:
    """Run the pinned authors' interpolation sampler; no training or 3D promotion."""
    request = verify_package(request_path)
    metadata = read_json(vendor/'source_manifest.json')
    if metadata['revision'] != REVISION:
        raise StudyError('Vendor revision mismatch')
    for name, sha in metadata['files'].items():
        if file_hash(vendor/name) != sha:
            raise StudyError('Vendor source modified without a recorded patch')
    expected = request['backend'].get('checkpoint_sha256')
    checkpoint_hash = file_hash(checkpoint)
    if expected and expected != checkpoint_hash:
        raise StudyError('Checkpoint hash mismatch')
    arrays, poses, transforms = load_conditions(request,request_path.parent)
    folder = output_dir(out)
    write_json(folder/'status.json',dict(status='initializing',backend_executed=False,
                                       request_sha256=request['source_request_sha256']))
    start = time.monotonic()
    try:
        import torch
        if not torch.cuda.is_available():
            raise StudyError('CUDA GPU unavailable; CPU fallback is not enabled')
        properties = torch.cuda.get_device_properties(0)
        if properties.total_memory/1024**3 < request['budgets']['minimum_device_vram_gb']:
            raise StudyError('GPU memory below the declared trial requirement')
        if hasattr(signal,'SIGALRM'):
            def timeout(signum: int, frame: object) -> None:
                raise TimeoutError('Model trial exceeded wall-time budget')
            signal.signal(signal.SIGALRM,timeout)
            signal.alarm(request['budgets']['max_wall_time_s'])
        sys.path.insert(0,str((vendor/'zero123').resolve()))
        from omegaconf import OmegaConf
        from ldm.util import instantiate_from_config
        from ldm.models.diffusion.my_ddim import DDIMSampler
        config = OmegaConf.load(vendor/'zero123/configs/sd-swap_att-c_concat-256.yaml')
        model = instantiate_from_config(config.model)
        # Official checkpoint supplied explicitly; tensor-only loading is required.
        # The official training checkpoint is ~15.5 GB. Map tensor storages
        # instead of copying optimizer tensors into RAM during deserialization.
        state = torch.load(checkpoint,map_location='cpu',weights_only=True,mmap=True)
        incompatible = model.load_state_dict(state['state_dict'],strict=False)
        del state
        if incompatible.unexpected_keys:
            raise StudyError(f'Unexpected checkpoint keys: {incompatible.unexpected_keys[:8]}')
        critical = [k for k in incompatible.missing_keys if k.startswith(('model.diffusion_model.','cc_projection.','first_stage_model.'))]
        # ema_scope() swaps EMA buffers into the UNet; unloaded EMA would sample from random init.
        if getattr(model,'use_ema',False):
            critical += [k for k in incompatible.missing_keys if k.startswith('model_ema.')]
        if critical:
            raise StudyError(f'Missing model weights: {critical[:8]}')
        ema_applied_on_cpu = apply_ema_on_cpu(model)
        model = model.to('cuda').eval()
        sampler = DDIMSampler(model)
        settings = request['backend']['parameters']
        cond_images = torch.from_numpy(arrays).to('cuda')
        base_conditioning, latent = encode_conditions(model, cond_images, settings['autocast'])
        candidates = []
        report = dict(schema='completion-candidates-1',request_sha256=request['source_request_sha256'],
                      conditioning_asset_ids=sorted(a['asset_id'] for a in request['assets']),
                      backend=request['backend'],backend_executed=True,candidates=candidates,complete=False,
                      checkpoint_sha256=checkpoint_hash,vendor_source_manifest=metadata,preprocessing=transforms,
                      runtime=dict(gpu=properties.name,ema_applied_on_cpu=ema_applied_on_cpu,
                                   device_total_vram_gb=properties.total_memory/1024**3,cuda=torch.version.cuda,
                                   versions={p:importlib.metadata.version(p) for p in ('torch','numpy','Pillow','omegaconf')}),
                      metric_geometry_status='unavailable_from_novel_view_rgb',
                      limitation='Model-conditioned image hypotheses; no observed geometry is replaced.')
        with torch.inference_mode():
            for seed in request['budgets']['seeds']:
                random.seed(seed);np.random.seed(seed % (2**32));torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
                candidate_id = f'seed_{seed}'
                destination = folder/candidate_id;destination.mkdir()
                views = []
                candidates.append(dict(candidate_id=candidate_id,seed=seed,origin='generative',representation='novel_view_rgb',
                                       validated_metric=False,suitable_for_ppfd=False,views=views))
                for target in request['targets']:
                    target_pose = target['model_pose_polar_azimuth_radius']
                    offsets = [camera_condition(target_pose,p) for p in poses]
                    # All real conditions are retained. Explicit weights avoid image-number heuristics.
                    weight = np.asarray(target['condition_weights'],dtype=np.float32)
                    if weight.shape != (len(poses),) or not np.isfinite(weight).all() or (weight<=0).any():
                        raise StudyError('Positive weight required for every real condition')
                    weight /= weight.sum()
                    with torch.autocast('cuda',enabled=settings['autocast']):
                        offset = torch.tensor(offsets,device='cuda',dtype=base_conditioning.dtype).unsqueeze(1)
                        conditioning = model.cc_projection(torch.cat([base_conditioning,offset],dim=-1))
                        cond = dict(c_crossattn=[conditioning],c_concat=[latent])
                        uncond = dict(c_crossattn=[torch.zeros_like(conditioning)],c_concat=[torch.zeros_like(latent)])
                        sampled,_ = sampler.sample(S=request['budgets']['steps'],conditioning=cond,
                            batch_size=len(poses),shape=[4,MODEL_IMAGE_PX//8,MODEL_IMAGE_PX//8],verbose=False,
                            unconditional_guidance_scale=settings['guidance_scale'],unconditional_conditioning=uncond,
                            eta=settings['ddim_eta'],t_start=request['budgets']['steps'],
                            interpolation_weight=torch.tensor(weight,device='cuda').reshape(-1,1,1,1))
                        decoded = model.decode_first_stage(sampled.mean(dim=0,keepdim=True))
                        rgb = ((decoded.clamp(-1,1)[0].permute(1,2,0).float().cpu().numpy()+1)*127.5).round().astype(np.uint8)
                    filename = identifier(target['target_id'])+'.png'
                    Image.fromarray(rgb).save(destination/filename)
                    views.append(dict(target_id=target['target_id'],path=f'{candidate_id}/{filename}',
                                      sha256=file_hash(destination/filename),size_px=[MODEL_IMAGE_PX,MODEL_IMAGE_PX],
                                      **{k:target[k] for k in TARGET_PROVENANCE_KEYS if k in target},
                                      condition_weights=weight.tolist()))
                    report['runtime'].update(elapsed_s=time.monotonic()-start,
                        peak_allocated_vram_gb=torch.cuda.max_memory_allocated()/1024**3,
                        peak_reserved_vram_gb=torch.cuda.max_memory_reserved()/1024**3)
                    save_candidate_progress(folder, report)
                    write_json(folder/'status.json',dict(status='running',seed=seed,target_id=target['target_id'],
                                                        elapsed_s=time.monotonic()-start,backend_executed=True))
        verify_package(request_path)
        report['complete'] = True
        write_json(folder/'candidate_bundle.json',report)
        write_json(folder/'status.json',dict(status='completed',backend_executed=True,elapsed_s=time.monotonic()-start))
        return report
    except Exception as exc:
        write_json(folder/'status.json',dict(status='failed',error=f'{type(exc).__name__}: {exc}',elapsed_s=time.monotonic()-start))
        raise
    finally:
        if hasattr(signal,'SIGALRM'):
            signal.alarm(0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--vendor',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    result = run(args.request,args.vendor,args.checkpoint,args.out)
    print(json.dumps(dict(candidates=len(result['candidates']),backend_executed=result['backend_executed'])))


if __name__ == '__main__':
    main()
