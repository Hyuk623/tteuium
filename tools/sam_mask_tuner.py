"""Build an offline sensitivity editor from saved SAM crop logits.

python -m tools.sam_mask_tuner --run build/.../run04_petiole_logits
  --case-id left_petiole --trial-id guided --out build/.../petiole_tuner
Run sam_leaf_trial with --save-logits first. Existing masks are never overwritten.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, output_dir, write_json
from tools.sam_leaf_trial import restore_mask


def collect_payload(run_dir: Path, case_id: str, trial_id: str) -> dict:
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+',value) for value in (case_id,trial_id)):
        raise StudyError('Invalid case/trial ID')
    run=read_json(run_dir/'run.json');manifest=read_json(run_dir/'prompts.json')
    if not run.get('saved_crop_logits'): raise StudyError('Rerun inference with --save-logits')
    case=next((c for c in manifest['cases'] if c['case_id']==case_id),None)
    source=next((c for c in run['cases'] if c['case_id']==case_id),None)
    if case is None or source is None: raise StudyError('Case not found')
    trial=next((t for t in case['trials'] if t['trial_id']==trial_id),None)
    if trial is None: raise StudyError('Trial not found')
    image_path=Path(source['image_path'])
    if file_hash(image_path)!=case['image_sha256'] or source['image_sha256']!=case['image_sha256']:
        raise StudyError('Source image changed')
    crop=tuple(case['crop_xyxy_px']);x0,y0,x1,y1=crop
    case_dir=run_dir/case_id
    with Image.open(image_path) as original:
        image_size=original.size;source_crop=np.array(original.convert('RGB').crop(crop))
    with Image.open(case_dir/'source_crop.png') as saved:
        if not np.array_equal(np.array(saved.convert('RGB')),source_crop): raise StudyError('Saved crop differs from source')
    with (run_dir/'metrics.csv').open(newline='',encoding='utf-8') as stream:
        records=[r for r in csv.DictReader(stream) if r['case_id']==case_id and r['trial_id']==trial_id]
    records.sort(key=lambda r:int(r['candidate_index']))
    if [int(r['candidate_index']) for r in records]!=[0,1,2] or sum(r['top_model_score']=='True' for r in records)!=1:
        raise StudyError('Expected three unique candidates and one model selection')
    candidates=[]
    for record in records:
        index=int(record['candidate_index']);stem=f'{trial_id}_candidate{index}'
        logits_file=case_dir/f'{stem}_logits.npy'
        logits=np.load(logits_file,allow_pickle=False)
        if logits.shape!=(y1-y0,x1-x0) or not np.isfinite(logits).all(): raise StudyError('Invalid score raster')
        baseline=restore_mask(logits>0,crop,image_size)
        with Image.open(case_dir/f'{stem}_mask.png') as saved:
            if not np.array_equal(np.array(saved),baseline): raise StudyError('Default mask differs from saved inference')
        candidates.append(dict(index=index,score=float(record['predicted_iou']),baseline_area_px=int(np.count_nonzero(baseline)),
            logits_sha256=file_hash(logits_file),logits_base64=base64.b64encode(logits.astype('<f4').tobytes()).decode('ascii')))
    return dict(schema_version='sam-mask-tuner-1',case_id=case_id,target_class=case.get('target_class','leaflet'),trial_id=trial_id,
        crop_xyxy_px=crop,image_size_px=image_size,image_sha256=case['image_sha256'],source_run_sha256=file_hash(run_dir/'run.json'),
        points=trial.get('points',[]),box_xyxy_px=trial.get('box_xyxy_px'),candidates=candidates,
        top_candidate=next(i for i,r in enumerate(records) if r['top_model_score']=='True'),
        image_data_url='data:image/png;base64,'+base64.b64encode((case_dir/'source_crop.png').read_bytes()).decode('ascii'))


def build(args: argparse.Namespace) -> dict:
    payload=collect_payload(args.run,args.case_id,args.trial_id)
    initial=getattr(args,'initial_sensitivity',50)
    if type(initial) is not int or not 0<=initial<=100: raise StudyError('Initial sensitivity must be an integer in [0,100]')
    payload['initial_sensitivity']=initial
    template=Path(__file__).with_suffix('.html').read_text(encoding='utf-8')
    core=Path(__file__).with_suffix('.js').read_text(encoding='utf-8')
    page=template.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')).replace('__CORE__',core)
    folder=output_dir(args.out);(folder/'index.html').write_text(page,encoding='utf-8')
    metadata={key:value for key,value in payload.items() if key not in ('image_data_url','candidates')}
    metadata['candidates']=[{k:v for k,v in c.items() if k!='logits_base64'} for c in payload['candidates']]
    metadata.update(initial_sensitivity=initial,sam_reference_sensitivity=50,default_minimum_component_area_px=0,default_seed_filter=False,
                    threshold_mapping='(50 - sensitivity) * 0.08; select logits > threshold',component_connectivity=8,
                    threshold_range_logit=[-4,4],html_sha256=file_hash(folder/'index.html'))
    write_json(folder/'metadata.json',metadata)
    return dict(out=str(folder),html_bytes=(folder/'index.html').stat().st_size)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--case-id',required=True)
    parser.add_argument('--trial-id',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--initial-sensitivity',type=int,default=50,help='Starting UI preference; SAM reference stays at 50')
    print(build(parser.parse_args()))


if __name__=='__main__': main()
