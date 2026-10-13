"""Run fixed-model, source-preserving preprocessing comparisons (no training).

python -m tools.preprocess_compare --out build/preprocess_study_20260929 --views 11 18 24 25
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from tools import organ_prelabel as detector
from tools.leaf_preprocess_lab import sha, read_json, write_json, assert_build
from tools.preprocess_study import SMOOTHING, TONES, recipe, process_rgb, scalar_maps, scalar_result, display_scalar, cache_key

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = ROOT/'build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260929_092627_faeb15/accepted.json'
SESSION = ROOT/'build/new_captures_20260920/dwt_01/edit_session'
INDEX = ROOT/'build/organ_detector_v4_20260929/upload/dataset/index.json'
FULL = ROOT/'build/organ_detector_v4_20260929/kout_full/full_lopo_dwt_01.pt'
TILES = ROOT/'build/organ_detector_v4_20260929/kout_tiles/tiles_lopo_dwt_01.pt'
SAM = ROOT/'build/leaflets4_20260927/sam2_config_tuned_heldout_dwt_01.json'


def csv_write(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)


def box_metrics(predictions, truth, class_id, threshold=.25):
    """Per-class score-ordered one-to-one matching, 101-point AP at IoU .5.

    AP here is explicitly truncated at the production output score threshold.
    It is not interchangeable with a low-confidence model-validation AP.
    """
    candidates = [(score, photo, box) for photo, rows in predictions.items() for c,box,score in rows if c==class_id]
    refs = {photo:[r['xyxy'] for r in rows if r['cls']==class_id] for photo, rows in truth.items()}
    count = sum(map(len, refs.values())); used = {p:set() for p in refs}
    tp, fp = [], []
    for score, photo, box in sorted(candidates, key=lambda r:-r[0]):
        if score < threshold:
            continue
        matches = [(detector.iou(box,b), j) for j,b in enumerate(refs[photo]) if j not in used[photo]]
        best,j = max(matches, default=(0,-1))
        ok = best >= .5
        if ok:
            used[photo].add(j)
        tp.append(int(ok)); fp.append(int(not ok))
    t, f = np.cumsum(tp), np.cumsum(fp)
    recall = t/count if count else np.zeros(len(t))
    precision = t/np.maximum(t+f,1)
    ap = float(np.mean([max(precision[recall>=q], default=0.) for q in np.linspace(0,1,101)])) if count else None
    return dict(class_name=detector.CLASSES[class_id], reference_count=count, predictions=len(tp),
                true_positive=sum(tp), false_positive=sum(fp), false_negative=count-sum(tp),
                precision=float(sum(tp)/len(tp)) if tp else None,
                recall=float(sum(tp)/count) if count else None, ap50_production=ap,
                score_floor=threshold, ap_definition='101point IoU0.5; production-threshold truncated')


def detect(full, tiles, rgb, window):
    views = ('orig','h','v')
    fused = [r for r in detector.wbf([detector.predict(full,rgb,v) for v in views],3) if r[2]>=detector.CONF_OUT]
    tiled = detector.tile_predictions([tiles],rgb,window,views,False)
    result = [r for r in fused if detector.CLASSES[r[0]] not in detector.TILE_ONLY_CLASSES+detector.TILE_FUSE_CLASSES]
    for name in detector.TILE_ONLY_CLASSES+detector.TILE_FUSE_CLASSES:
        c = detector.CLASSES.index(name); boxes=tiled.get(c,[])
        if name in detector.TILE_FUSE_CLASSES:
            boxes=detector.merge_same_class(boxes+[(b,s,None) for cc,b,s in fused if cc==c])
        result += [(c,b,s) for b,s,_ in boxes if s>=detector.CONF_OUT]
    return result


def sam_one(seg, rgb, obs, folder, condition, model_hash):
    from tools.leaflet_segmenter import prompt_crop, checked_prompts
    h,w = rgb.shape[:2]
    box,pos,neg = checked_prompts(obs['prompts'],w,h)
    x0,y0,x1,y1 = prompt_crop(box,pos,neg,w,h)
    sub = np.ascontiguousarray(rgb[y0:y1,x0:x1])
    prompt = dict(box=box,positive=pos,negative=neg,crop=[x0,y0,x1,y1])
    key = cache_key(sub,condition,dict(model=model_hash,prompt=prompt,source_id=obs['id'],
                                     candidate_rule='highest_model_score',sensitivity=obs['sensitivity']))
    folder.mkdir(parents=True,exist_ok=True)
    meta_path=folder/f'{key}.json'; array_path=folder/f'{key}.npz'
    if meta_path.exists():
        meta=read_json(meta_path)
        if sha(array_path)!=meta['array_sha256']:
            raise ValueError('Cached logits corrupted')
        with np.load(array_path) as a:
            logits=a['logits']; scores=a['scores']
    else:
        localbox=None if box is None else [box[0]-x0,box[1]-y0,box[2]-x0,box[3]-y0]
        start=time.perf_counter()
        cands=seg.predict_logits(sub,localbox,[[x-x0,y-y0] for x,y in pos],[[x-x0,y-y0] for x,y in neg])
        if not cands:
            raise RuntimeError('SAM returned no candidates')
        logits=np.stack([c.logits for c in cands]); scores=np.array([c.score for c in cands])
        np.savez_compressed(array_path,logits=logits,scores=scores)
        meta=dict(cache_key=key,prompt=prompt,condition=condition,model_sha256=model_hash,
                  seconds=time.perf_counter()-start,array_sha256=sha(array_path))
        write_json(meta_path,meta)
    selected=int(scores.argmax())
    threshold=np.float32((50-obs['sensitivity'])*.08)
    return logits[selected]>threshold, (x0,y0,x1,y1), dict(seconds=meta['seconds'],candidate=selected,
            model_score=float(scores[selected]),sensitivity=obs['sensitivity'],cache_key=key)


def run(args):
    import torch
    from ultralytics import YOLO
    from tools.leaflet_segmenter import load_segmenter
    torch.set_num_threads(4)
    device=getattr(args,'device','cpu')
    sam_config=getattr(args,'sam_config',SAM)
    if device=='cuda' and not torch.cuda.is_available():
        raise RuntimeError('GPU required. Select a Colab GPU runtime; CPU fallback is disabled.')
    out=assert_build(args.out); out.mkdir(parents=True,exist_ok=True)
    accepted=read_json(ACCEPTED)
    observations=[o for o in accepted['observations'] if o.get('review')=='accepted_by_user']
    photos=[p for p in read_json(INDEX)['photos'] if p['plant']=='dwt_01' and
            (not args.views or int(p['photo'].split('_')[-1]) in args.views)]
    if not photos:
        raise ValueError('No matching human-labeled photos')
    conditions=[recipe(m,t) for m in args.smoothing for t in args.tones]
    pilot_manifest=ROOT/'build/rgb_preprocess_lab_20260929/dataset.json'
    pilot_ids={s['image_file']:s['observation_id'] for s in read_json(pilot_manifest)['samples'] if s['plant_id']=='dwt_01'}
    checkpoint=Path(read_json(sam_config)['checkpoint'])
    checkpoint=checkpoint if checkpoint.is_absolute() else ROOT/checkpoint
    inputs=[ACCEPTED,INDEX,FULL,TILES,sam_config,checkpoint,SESSION/'capture.json',pilot_manifest]
    inputs += [SESSION/'images'/f"{p['photo']}.png" for p in photos]
    obs_by_photo={p['photo']:[o for o in observations if Path(o['image_file']).stem==p['photo']] for p in photos}
    inputs += [ACCEPTED.parent/o['mask_file'] for obs in obs_by_photo.values() for o in obs]
    hashes={str(p):sha(p) for p in inputs}
    manifest=dict(schema='preprocess-comparison-1',plant='dwt_01',views=[p['photo'] for p in photos],
       conditions=conditions,source_hashes=hashes,held_out='dwt_01',training_run=False,
       device=device,detector_weights_sha256=[hashes[str(FULL)],hashes[str(TILES)]],
       sam_candidate_rule='highest model score; not GT optimized',mask_limit_per_photo=args.mask_limit,
       mask_sampling='existing lab observation first, remaining IDs sorted; limit=0 means all',
       detector=dict(conf_out=.25,conf_member=.01,iou_fuse=.55,imgsz=1280,views=['orig','h','v'],
                     full_image=True,fixed_original_plant_window=True,existing_scale_plan=True),
       ground_truth='human Roboflow organs; v4 human-accepted leaflet outlines; no automatic labels',
       limitations=['dwt_01 exploratory selection, not independent final validation',
                    'mask reference is human-reviewed model-assisted annotation, not independent manual tracing',
                    'visibility may be unspecified; GT coverage not proven exhaustive',
                    'midrib accuracy, click repeatability, correction time and 3D accuracy unavailable'],
       versions=dict(python=platform.python_version(),torch=torch.__version__,opencv=cv2.__version__,numpy=np.__version__),
       tool_hashes={p.name:sha(p) for p in [Path(__file__),Path(__file__).with_name('preprocess_study.py'),
                                            Path(detector.__file__),Path(__file__).with_name('leaflet_segmenter.py')]})
    if (out/'manifest.json').exists() and read_json(out/'manifest.json') != manifest:
        raise ValueError('Run snapshot differs; use a new output directory')
    write_json(out/'manifest.json',manifest)
    full,tiles=YOLO(str(FULL)).to(device),YOLO(str(TILES)).to(device)
    seg=load_segmenter('sam2',sam_config)
    seg.config['device']=device  # runtime override; configuration file stays untouched
    det_rows,mask_rows,scalar_rows=[],[],[]
    for condition in conditions:
        name=condition['smoothing']+'__'+condition['tone']; preds={}; truth={}
        for photo in photos:
            stem=photo['photo']; folder=out/name/stem; folder.mkdir(parents=True,exist_ok=True)
            src=SESSION/'images'/f'{stem}.png'
            with Image.open(src) as im:
                original=np.array(im.convert('RGB'))
            start=time.perf_counter(); rgb=process_rgb(original,condition['smoothing'],condition['tone'])
            preprocessing_seconds=time.perf_counter()-start
            window=list(detector.plant_window(original))
            key=cache_key(rgb,condition,dict(full=hashes[str(FULL)],tiles=hashes[str(TILES)],window=window,
                                           settings=manifest['detector'],code=manifest['tool_hashes']))
            prediction_path=folder/'predictions.json'
            if prediction_path.exists():
                pd=read_json(prediction_path)
                if pd['cache_key']!=key:
                    raise ValueError('Prediction cache mismatch')
            else:
                start=time.perf_counter(); boxes=detect(full,tiles,rgb,window)
                pd=dict(cache_key=key,predictions=boxes,seconds=time.perf_counter()-start,
                        preprocessing_seconds=preprocessing_seconds,window=window)
                write_json(prediction_path,pd)
                Image.fromarray(rgb).save(folder/'processed.png')
                overlay=Image.fromarray(rgb); draw=ImageDraw.Draw(overlay)
                for c,b,s in boxes:
                    draw.rectangle(b,outline=detector.COLOURS[c],width=4)
                    draw.text((b[0],b[1]),f'{detector.CLASSES[c]} {s:.2f}',fill=detector.COLOURS[c])
                overlay.thumbnail((1200,1200)); overlay.save(folder/'detections.jpg',quality=90)
            preds[stem]=pd['predictions']; truth[stem]=photo['gt']
            for c in range(5):
                det_rows.append(dict(condition=name,photo=stem,seconds=pd['seconds'],
                      preprocessing_seconds=pd['preprocessing_seconds'],**box_metrics({stem:preds[stem]},{stem:truth[stem]},c)))
            obs=obs_by_photo[stem]
            if args.mask_limit:
                # Deterministic pilot only, no best-mask selection. Report denominator.
                obs=sorted(obs,key=lambda o:(o['id']!=pilot_ids.get(o['image_file']),str(o['id'])))[:args.mask_limit]
            references=[]
            for ob in obs_by_photo[stem]:
                with Image.open(ACCEPTED.parent/ob['mask_file']) as im:
                    references.append((ob['id'],np.asarray(im)>0))
            ref_lookup=dict(references)
            maps=None
            for ob in obs:
                reference=ref_lookup[ob['id']]
                if sha(src)!=ob['image_sha256']:
                    raise ValueError('Accepted-mask photo hash mismatch')
                pred,crop,meta=sam_one(seg,rgb,ob,folder/'sam_cache',condition,read_json(sam_config)['checkpoint_sha256'])
                x0,y0,x1,y1=crop; ref=reference[y0:y1,x0:x1]
                intersection=int((pred&ref).sum()); area=int(pred.sum()); ref_area=int(reference.sum())
                union=area+ref_area-intersection
                overlaps=[rid for rid,rm in references if (pred&rm[y0:y1,x0:x1]).sum()>=.2*rm.sum()]
                mask_rows.append(dict(condition=name,photo=stem,observation_id=ob['id'],
                       visibility=ob.get('visibility') or 'unspecified',status='success',
                       iou=intersection/union if union else None,dice=2*intersection/(area+ref_area) if area+ref_area else None,
                       missing=int(area==0),merge_candidate=int(len(overlaps)>=2),**meta))
                Image.fromarray(pred.astype(np.uint8)*255).save(folder/f"{ob['id']}_predicted.png")
                write_json(folder/f"{ob['id']}_prediction.json",dict(crop_xyxy_px=list(crop),
                       original_shape=list(reference.shape),**meta))
                if args.scalar and condition['tone']=='none':
                    # Context crop contains at least 128 pixels around the prompt. Filter before masking.
                    if maps is None:
                        maps=scalar_maps(original)
                    diag=folder/ob['id']; diag.mkdir(exist_ok=True)
                    for channel,values in maps.items():
                        a,v,common,stats=scalar_result(values[y0:y1,x0:x1],ref,condition['smoothing'])
                        np.save(diag/f'{channel}.npy',a,allow_pickle=False)
                        Image.fromarray(display_scalar(a,common)).save(diag/f'{channel}.png')
                        Image.fromarray(common.astype(np.uint8)*255).save(diag/f'{channel}_common.png')
                        scalar_rows.append(dict(condition=name,photo=stem,observation_id=ob['id'],channel=channel,**stats))
            del references,ref_lookup
            csv_write(out/'detection_by_photo.csv',det_rows); csv_write(out/'masks.csv',mask_rows)
            csv_write(out/'scalar_maps.csv',scalar_rows)
            print(json.dumps(dict(condition=name,photo=stem,masks=len(obs),detector_seconds=round(pd['seconds'],2))),flush=True)
        # Dataset-level AP must pool ranked detections, not average per-photo AP.
        for c in range(5):
            det_rows.append(dict(condition=name,photo='ALL',**box_metrics(preds,truth,c)))
    csv_write(out/'detection_by_photo.csv',det_rows)
    summary=[]
    for condition in conditions:
        name=condition['smoothing']+'__'+condition['tone']
        dr=[r for r in det_rows if r['condition']==name and r['photo']=='ALL']
        mr=[r for r in mask_rows if r['condition']==name]
        summary.append(dict(condition=name,photos=len(photos),reviewed_masks=len(mr),
            map50_production=float(np.mean([r['ap50_production'] for r in dr if r['ap50_production'] is not None])),
            mean_mask_iou=float(np.mean([r['iou'] for r in mr])) if mr else None,
            mean_mask_dice=float(np.mean([r['dice'] for r in mr])) if mr else None,
            empty_masks=sum(r['missing'] for r in mr),merge_candidates=sum(r['merge_candidate'] for r in mr),
            detector_seconds=sum(r.get('seconds',0) for r in det_rows if r['condition']==name and r['photo']!='ALL')/5,
            sam_seconds=sum(r['seconds'] for r in mr),human_review_seconds=None,midrib_accuracy=None))
    csv_write(out/'summary.csv',summary)
    audit={path:sha(Path(path))==digest for path,digest in hashes.items()}
    write_json(out/'source_audit.json',audit)
    if not all(audit.values()):
        raise ValueError('Source changed during run')
    write_json(out/'complete.json',dict(status='complete',summary=summary,sources_unchanged=True,
         evaluated_photos=len(photos),available_reviewed_masks=sum(map(len,obs_by_photo.values())),
         evaluated_masks_per_condition=len(mask_rows)//len(conditions),validated_metric=False,suitable_for_ppfd=False))
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True); p.add_argument('--views',type=int,nargs='*')
    p.add_argument('--smoothing',choices=list(SMOOTHING),nargs='+',default=list(SMOOTHING))
    p.add_argument('--tones',choices=TONES,nargs='+',default=['none'])
    p.add_argument('--mask-limit',type=int,default=0,help='0=all reviewed masks; positive=deterministic timing pilot')
    p.add_argument('--scalar',action='store_true',help='Save source scalar maps, common support and arrays')
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--sam-config',type=Path,default=SAM)
    a=p.parse_args()
    if a.mask_limit<0:
        p.error('mask-limit must be nonnegative')
    try:
        print(json.dumps(run(a),allow_nan=False))
    except Exception as exc:
        out=assert_build(a.out)
        if out.exists():
            write_json(out/'failure.json',dict(status='incomplete',error_type=type(exc).__name__,error=str(exc)))
        raise


if __name__=='__main__':
    main()
