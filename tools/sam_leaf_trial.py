"""Run reproducible SAM 2 organ prompt trials, preserving original pixel coordinates.

Example: python -m tools.sam_leaf_trial --manifest build/.../prompts.json
  --repository build/.../vendor/sam2 --runtime build/.../runtime
  --checkpoint build/.../checkpoints/sam2.1_hiera_tiny.pt --out build/.../run01
All masks are predictions requiring review, not 3D landmarks or ground truth.
"""
from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json, write_rows, output_dir


def crop_prompt(case: dict, trial: dict, image_size: tuple[int, int]) -> tuple:
    crop = case['crop_xyxy_px']
    if len(crop) != 4 or any(type(v) is not int for v in crop):
        raise StudyError('Crop must be four integer pixel-edge coordinates')
    x0,y0,x1,y1=crop
    if not (0 <= x0 < x1 <= image_size[0] and 0 <= y0 < y1 <= image_size[1]):
        raise StudyError('Crop outside the source image')
    points,labels=[],[]
    for p in trial.get('points',[]):
        x,y,label=p['x_px'],p['y_px'],p['label']
        if not (np.isfinite([x,y]).all() and x0<=x<x1 and y0<=y<y1 and label in (0,1)):
            raise StudyError('Point outside crop or invalid include/exclude label')
        points.append([x-x0,y-y0]);labels.append(label)
    box=trial.get('box_xyxy_px')
    if box is not None:
        if len(box)!=4 or not np.isfinite(box).all() or not (x0<=box[0]<box[2]<=x1 and y0<=box[1]<box[3]<=y1):
            raise StudyError('Box outside crop or empty')
        box=np.asarray(box,dtype=np.float32)-[x0,y0,x0,y0]
    if not points and box is None: raise StudyError('At least one point or box is required')
    return tuple(crop),np.asarray(points,dtype=np.float32) if points else None,np.asarray(labels,dtype=np.int32) if points else None,box


def restore_mask(mask: np.ndarray, crop: tuple, image_size: tuple[int,int]) -> np.ndarray:
    x0,y0,x1,y1=crop
    if mask.shape!=(y1-y0,x1-x0): raise StudyError('SAM mask dimensions disagree with crop')
    full=np.zeros((image_size[1],image_size[0]),dtype=np.uint8)
    full[y0:y1,x0:x1]=np.asarray(mask,dtype=np.uint8)*255
    return full


def contour_rows(mask: np.ndarray, tolerance_px: float) -> list[dict]:
    contours,hierarchy=cv2.findContours(mask,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    output=[]
    for ring,contour in enumerate(contours):
        polygon=cv2.approxPolyDP(contour,tolerance_px,True).reshape(-1,2)
        for vertex,(x,y) in enumerate(polygon):
            output.append(dict(ring_index=ring,parent_ring_index=int(hierarchy[0,ring,3]),
                vertex_index=vertex,x_px=int(x),y_px=int(y)))
    return output


def overlay(rgb: np.ndarray, mask: np.ndarray, points: np.ndarray | None, labels: np.ndarray | None,
            box: np.ndarray | None) -> Image.Image:
    canvas=rgb.copy();selected=mask.astype(bool)
    canvas[selected]=(canvas[selected]*0.5+np.array([30,230,180])*0.5).astype(np.uint8)
    outlines,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(canvas,outlines,-1,(255,220,55),2)
    im=Image.fromarray(canvas);draw=ImageDraw.Draw(im)
    if box is not None: draw.rectangle(tuple(map(float,box)),outline='#58baff',width=3)
    if points is not None:
        for (x,y),label in zip(points,labels):
            color='#55ff55' if label else '#ff4455'
            draw.ellipse((x-6,y-6,x+6,y+6),fill=color,outline='black',width=2)
    im.thumbnail((900,900))
    return im


def comparison_image(run_dir: Path, tile_width_px: int = 400) -> Image.Image:
    """Show the complete input crop and each top-scored prediction, without ROI hiding."""
    manifest=read_json(run_dir/'prompts.json')
    with (run_dir/'metrics.csv').open(encoding='utf-8',newline='') as stream:
        selected={(r['case_id'],r['trial_id']):r for r in csv.DictReader(stream) if r['top_model_score']=='True'}
    columns=1+max(len(case['trials']) for case in manifest['cases'])
    row_height_px=tile_width_px+65
    canvas=Image.new('RGB',(columns*tile_width_px,len(manifest['cases'])*row_height_px),'#f2f5f3')
    draw=ImageDraw.Draw(canvas)
    for row,case in enumerate(manifest['cases']):
        cid=case['case_id']
        items=[('SOURCE: '+cid,run_dir/cid/'source_crop.png')]
        for trial in case['trials']:
            tid=trial['trial_id'];record=selected[(cid,tid)]
            items.append((f'{tid} | model score {float(record["predicted_iou"]):.3f}',run_dir/cid/f'{tid}_candidate{record["candidate_index"]}.jpg'))
        for col,(label,path) in enumerate(items):
            with Image.open(path) as source:
                picture=source.convert('RGB');picture.thumbnail((tile_width_px-12,tile_width_px))
            x=col*tile_width_px;y=row*row_height_px
            draw.text((x+8,y+8),label,fill='#152d25',font_size=15)
            canvas.paste(picture,(x+(tile_width_px-picture.width)//2,y+48))
    return canvas


def run(args: argparse.Namespace) -> dict:
    manifest=read_json(args.manifest)
    if manifest.get('schema_version')!='sam-leaf-trial-1': raise StudyError('Unknown trial manifest')
    prepared=[];case_ids=set()
    for case in manifest['cases']:
        cid=case['case_id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',cid) or cid in case_ids: raise StudyError('Invalid/duplicate case ID')
        case_ids.add(cid);path=(args.manifest.parent/case['image_file']).resolve()
        with Image.open(path) as image:
            if image.getexif().get(274,1)!=1: raise StudyError('Normalize image orientation before inference')
            rgb=np.array(image.convert('RGB'));size=image.size
        if case.get('image_sha256')!=file_hash(path): raise StudyError('Source image hash mismatch')
        trial_ids=set()
        for trial in case['trials']:
            tid=trial['trial_id']
            if not re.fullmatch(r'[A-Za-z0-9_-]+',tid) or tid in trial_ids: raise StudyError('Invalid/duplicate trial ID')
            trial_ids.add(tid);crop_prompt(case,trial,size)
        prepared.append((case,path,rgb,size))
    tolerance=float(manifest['contour_tolerance_px'])
    if not np.isfinite(tolerance) or tolerance<0: raise StudyError('Invalid contour tolerance')
    sys.path.insert(0,str(args.runtime.resolve()));sys.path.insert(0,str(args.repository.resolve()))
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    torch.set_num_threads(args.threads)
    device=('cuda' if torch.cuda.is_available() else 'cpu') if args.device=='auto' else args.device
    if device=='cuda' and not torch.cuda.is_available(): raise StudyError('CUDA was requested but is unavailable')
    def synchronize() -> None:
        if device=='cuda': torch.cuda.synchronize()
    started=perf_counter()
    model=build_sam2(args.model_config,str(args.checkpoint.resolve()),device=device,apply_postprocessing=False)
    predictor=SAM2ImagePredictor(model,max_hole_area=0,max_sprinkle_area=0)
    model_load_seconds=perf_counter()-started
    folder=output_dir(args.out);write_json(folder/'prompts.json',manifest)
    metrics=[];details=[];tiles=[];last_key=None
    with torch.inference_mode():
        for case,path,rgb,size in prepared:
            cid=case['case_id'];case_dir=folder/cid;case_dir.mkdir()
            crop=tuple(case['crop_xyxy_px']);x0,y0,x1,y1=crop
            crop_rgb=rgb[y0:y1,x0:x1];key=(str(path),crop)
            encode_seconds=0.0
            if key!=last_key:
                synchronize();started=perf_counter();predictor.set_image(crop_rgb);synchronize()
                encode_seconds=perf_counter()-started;last_key=key
            Image.fromarray(crop_rgb).save(case_dir/'source_crop.png')
            for trial in case['trials']:
                _,points,labels,box=crop_prompt(case,trial,size)
                synchronize();started=perf_counter()
                save_logits=getattr(args,'save_logits',False)
                predictions,scores,_=predictor.predict(point_coords=points,point_labels=labels,box=box,multimask_output=True,return_logits=save_logits)
                masks=predictions>predictor.mask_threshold if save_logits else predictions
                synchronize()
                inference_seconds=perf_counter()-started
                top=int(np.argmax(scores));tid=trial['trial_id']
                for candidate,(mask,score) in enumerate(zip(masks,scores)):
                    stem=f'{tid}_candidate{candidate}';full=restore_mask(mask,crop,size)
                    if save_logits:
                        np.save(case_dir/f'{stem}_logits.npy',predictions[candidate].astype(np.float32),allow_pickle=False)
                    Image.fromarray(full).save(case_dir/f'{stem}_mask.png')
                    rings=contour_rows(full,tolerance)
                    write_rows(case_dir/f'{stem}_contours.csv',rings,
                        ('ring_index','parent_ring_index','vertex_index','x_px','y_px'))
                    picture=overlay(crop_rgb,mask,points,labels,box);picture.save(case_dir/f'{stem}.jpg',quality=93)
                    record=dict(case_id=cid,target_class=case.get('target_class','leaflet'),trial_id=tid,candidate_index=candidate,top_model_score=candidate==top,
                        predicted_iou=float(score),mask_area_px=int(np.count_nonzero(mask)),
                        point_prompts=0 if labels is None else len(labels),box_prompts=int(box is not None),
                        encoder_seconds=encode_seconds,inference_seconds=inference_seconds,
                        measured_iou=None,human_review='unreviewed')
                    metrics.append(record)
                    if candidate==top:
                        tiles.append((cid,tid,picture.copy(),record))
                print(f'{cid}/{tid}: encoder {encode_seconds:.2f}s, prompts {inference_seconds:.2f}s, top {top}, scores {scores.tolist()}',flush=True)
                encode_seconds=0.0
            if file_hash(path)!=case['image_sha256']: raise StudyError('Source changed during inference')
            details.append(dict(case_id=cid,target_class=case.get('target_class','leaflet'),image_path=str(path),image_sha256=case['image_sha256'],crop_xyxy_px=crop))
    write_rows(folder/'metrics.csv',metrics,list(metrics[0]))
    result=dict(status='prediction_trial_completed',model='SAM 2.1',model_config=args.model_config,
        checkpoint_sha256=file_hash(args.checkpoint),repository_commit=subprocess.check_output(['git','-C',str(args.repository),'rev-parse','HEAD'],text=True).strip(),
        torch_version=torch.__version__,device=device,threads=args.threads,model_load_seconds=model_load_seconds,
        runner_source_sha256=file_hash(Path(__file__)),
        saved_crop_logits=getattr(args,'save_logits',False),mask_threshold_logit=0.0,
        cases=details,manifest_sha256=file_hash(args.manifest),postprocessing_hole_fill=False,postprocessing_sprinkle_removal=False,
        notice='Predictions, not human ground truth. Predicted IoU is model confidence, not measured accuracy. No cross-view identity tracking, 3D or PPFD was performed.')
    write_json(folder/'run.json',result)
    cards=[]
    for cid,tid,picture,record in tiles:
        cards.append(f'<article><h2>{html.escape(cid)} / {html.escape(tid)}</h2><img src="{cid}/{tid}_candidate{record["candidate_index"]}.jpg"><p>모델 점수 {record["predicted_iou"]:.3f} · 후보 {record["candidate_index"]} · 추론 {record["inference_seconds"]:.2f}초</p></article>')
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><title>SAM 소엽 분할 시험</title><style>body{font:16px system-ui;background:#11211c;color:#e6f5eb;margin:24px}main{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}article{background:#20352c;padding:12px;border-radius:12px}img{width:100%}h2{font-size:16px}p{line-height:1.5}</style><h1>SAM 2.1 소엽 분할 시험</h1><p>초록 영역: 분할 예측 · 노란 선: 윤곽 · 초록 점: 포함 · 빨간 점: 제외 · 파란 박스: 대상 범위.<br>각 입력의 모델 점수가 가장 높은 후보입니다. 점수는 실측 정확도가 아니며, 모두 검토가 필요합니다.</p><main>'+''.join(cards)+'</main></html>'
    (folder/'index.html').write_text(page,encoding='utf-8')
    comparison_image(folder).save(folder/'comparison_full.jpg',quality=94)
    return result


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','repository','runtime','checkpoint','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--device',choices=['cpu','cuda','auto'],default='cpu')
    parser.add_argument('--save-logits',action='store_true',help='Save crop-sized float32 score rasters for sensitivity review')
    parser.add_argument('--model-config',default='configs/sam2.1/sam2.1_hiera_t.yaml')
    args=parser.parse_args()
    if args.threads<1: parser.error('--threads must be positive')
    run(args)


if __name__=='__main__': main()
