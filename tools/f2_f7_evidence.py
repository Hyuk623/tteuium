"""Source-image review and contour-resolution sensitivity; read-only bank inputs.

python -m tools.f2_f7_evidence --prior build/compound_structure_f2_f7_20261006_01 --out build/compound_structure_f2_f7_20261006_02
"""
from __future__ import annotations
import argparse
import csv
import html
import json
from collections import Counter
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from tools.f2_f7_analysis import read_json,save_json,sha,metrics,largest,fit_threshold,classify,table,rgb
from tools.f2_compound_measurements import read_csv


def stable_label(prior: str, labels: list[str]) -> tuple[str,str]:
    if prior=='unknown': return 'unknown','prior_uncertainty_preserved'
    if labels and all(v==prior for v in labels): return prior,'resolution_stable_shape_candidate'
    return 'unknown','representation_or_resolution_disagreement'


def bounded_crop(mask: np.ndarray, pad: int) -> tuple[int,int,int,int]:
    y,x=np.nonzero(mask)
    if not len(x): raise ValueError('empty source mask')
    return max(0,int(x.min())-pad),max(0,int(y.min())-pad),min(mask.shape[1],int(x.max())+pad+1),min(mask.shape[0],int(y.max())+pad+1)


def run(prior: Path,out: Path) -> dict:
    prior,out=prior.resolve(),out.resolve()
    policy=read_json(prior/'policy.json')
    root=Path(policy['project_root']).resolve()
    if not out.is_relative_to(root/'build') or out==prior: raise ValueError('new build output required')
    out.mkdir(parents=True,exist_ok=True)
    (out/'cards').mkdir(exist_ok=True)
    protected={}
    def source(path):
        p=Path(path)
        p=p if p.is_absolute() else root/p
        p=p.resolve()
        if str(p) not in protected: protected[str(p)]=sha(p)
        return p
    # Preserve all first-run inputs and outputs, not just bank manifests.
    old=read_json(source(prior/'input_provenance.json'))
    for p,h in old['sha256_before'].items():
        if sha(source(p))!=h: raise ValueError(f'prior input changed: {p}')
    for p in prior.iterdir():
        if p.is_file(): source(p)
    old_rows={r['item_id']:r for r in read_csv(prior/'artifact_classification.csv') if r['artifact']=='texture_bank_v2'}
    bank=read_json(source(policy['bank']))['textures']
    lib=read_json(source(Path(policy['library_root'])/'library_components.json'))['records']
    lib={r['component_id']:r for r in lib}
    sam_doc=read_json(source(policy['sam']))
    sam={r['mask_id']:r for r in sam_doc['contours']}
    exports={p:source(Path(v['export'])/'accepted.json').parent for p,v in sam_doc['sources'].items()}
    accepted={p:{r['id']:r for r in read_json(exp/'accepted.json')['observations']} for p,exp in exports.items()}
    ref_contours=[]
    for r in policy['references']:
        if not r['fit_eligible']: continue
        a=rgb(source(r['photo'])); x0,y0,x1,y1=r['roi_xyxy']; a=a[y0:y1,x0:x1]
        hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV)
        m=(hsv[:,:,1]>=policy['reference_min_saturation'])|(hsv[:,:,2]<policy['reference_dark_value'])
        ref_contours.append((r,largest(m)))
    resolutions=(64,128,256)
    fits={}
    for n in resolutions:
        rs=[dict(label=r['label'],photo=r['photo'],**metrics(c,n)) for r,c in ref_contours]
        f=fit_threshold(rs)
        shifts=[]
        for photo in {r['photo'] for r in rs}:
            try: shifts.append(abs(fit_threshold([r for r in rs if r['photo']!=photo])['threshold']-f['threshold']))
            except ValueError: pass
        f['guard']=max(.1*f['threshold'],max(shifts or [0]))
        f['biological_validation']='unavailable_same_seven_blades_three_photos'
        fits[n]=f
    save_json(out/'resolution_fit_policy.json',fits)
    rows=[]; detail=[]; cards=[]
    for entry in bank:
        previous=old_rows[entry['file']]
        if entry['source']=='library_crop':
            r=lib[entry['component_id']]
            image_path=source(Path(policy['library_root'])/r['crop'])
            a=rgb(image_path); mask=~np.all(a>=250,axis=2)
            contour=largest(mask)
            context=a.copy(); overlay=a.copy()
            cv2.polylines(overlay,[contour.astype(np.int32)],True,(255,0,180),2)
            source_id=entry['component_id']; mask_path=image_path
            image_identity='source_segmented_crop;full_photo_not_registered_to_crop'
        else:
            source_id=entry['mask_id']; r=sam[source_id]; obs=accepted[r['plant_id']][source_id]
            mask_path=source(exports[r['plant_id']]/obs['mask_file'])
            if sha(mask_path)!=r['mask_sha256']: raise ValueError('mask identity mismatch')
            mask=np.asarray(Image.open(mask_path).convert('L'))>0
            contour=largest(mask)
            session_manifest=source(exports[r['plant_id']].parent.parent/'manifest.json')
            session=read_json(session_manifest)['session'].replace('\\','/')
            # Historical absolute prefixes contain mojibake. Resolve the recorded build-relative suffix only.
            relative=session[session.index('build/'):]
            image_path=source(Path(relative)/'images'/r['image_file'])
            if sha(image_path)!=obs['image_sha256']: raise ValueError('photo identity mismatch')
            a=rgb(image_path)
            if a.shape[:2]!=mask.shape: raise ValueError('photo/mask size mismatch')
            x0,y0,x1,y1=bounded_crop(mask,max(30,int(max(np.ptp(contour[:,0]),np.ptp(contour[:,1]))*.5)))
            context=a[y0:y1,x0:x1].copy(); overlay=context.copy()
            cv2.polylines(overlay,[(contour-[x0,y0]).astype(np.int32)],True,(255,0,180),2)
            image_identity='original_photo_sha256_matches_accepted_export'
        quality='' if previous['class_status'] in ('shape_candidate_not_botanical_ground_truth','near_fitted_threshold') else previous['class_status']
        labels=[]; vals=[]
        for n in resolutions:
            sh=metrics(contour,n); f=fits[n]
            label,status=classify(sh['norm_perimeter'],f['threshold'],f['guard'],quality)
            labels.append(label); vals.append(sh['norm_perimeter'])
            detail.append(dict(texture=entry['file'],source_id=source_id,contour_points=n,
                               **{k:v for k,v in sh.items() if k!='contour_points'},threshold=f['threshold'],
                               guard=f['guard'],leaflet_class=label,class_status=status))
        stable,status=stable_label(previous['leaflet_class'],labels)
        priority=previous['leaflet_class']!='main' or stable=='unknown'
        row=dict(texture=entry['file'],source_id=source_id,source_kind=entry['source'],
                 prior_class=previous['leaflet_class'],native64_class=labels[0],native128_class=labels[1],native256_class=labels[2],
                 stable_class=stable,stability_status=status,priority_review=priority,
                 native64_perimeter=vals[0],native128_perimeter=vals[1],native256_perimeter=vals[2],
                 prior64_perimeter=float(previous['norm_perimeter']),
                 source_image=str(image_path),source_mask=str(mask_path),image_identity=image_identity,
                 human_class='',human_reviewer='',human_notes='',botanical_validation='unavailable')
        rows.append(row)
        tex_path=source(Path(policy['bank']).parent/entry['file'])
        if sha(tex_path)!=entry['sha256']: raise ValueError('texture hash mismatch')
        card=Image.new('RGB',(960,390),'white'); d=ImageDraw.Draw(card)
        d.text((8,6),f"{entry['file']} | {source_id} | prior={previous['leaflet_class']} stable={stable}",fill='black')
        d.text((8,25),f"Native contours 64/128/256: {' / '.join(labels)}",fill='black')
        for i,(im,title) in enumerate([(Image.fromarray(context),'Source context'),(Image.fromarray(overlay),'Source contour overlay'),(Image.open(tex_path).convert('RGB'),'Existing B5a texture')]):
            d.text((i*320+8,49),title,fill='black')
            card.paste(ImageOps.contain(im,(310,310)),(i*320+5,73))
        card_path=f"cards/{Path(entry['file']).stem}.jpg"
        card.save(out/card_path,quality=90)
        cards.append(dict(**row,card_path=card_path))
    table(out/'texture_evidence.csv',rows)
    table(out/'native_contour_metrics.csv',detail)
    table(out/'human_review_blank.csv',[{k:r[k] for k in ('texture','source_id','prior_class','stable_class','human_class','human_reviewer','human_notes')} for r in rows])
    summary=dict(n_textures=len(rows),prior_counts=dict(Counter(r['prior_class'] for r in rows)),
                 native_counts={n:dict(Counter(d['leaflet_class'] for d in detail if d['contour_points']==n)) for n in resolutions},
                 stable_counts=dict(Counter(r['stable_class'] for r in rows)),
                 n_priority_review=sum(r['priority_review'] for r in rows),
                 n_changed_known_to_unknown=sum(r['prior_class']!='unknown' and r['stable_class']=='unknown' for r in rows),
                 n_human_reviewed=0,n_confirmed_anatomical_interjected=None,
                 library_photo_context_limit='55 library entries are source segmented crops; rig 60 entries are original photos verified against accepted export',
                 F2='No new anatomical evidence: full rachis attachment fractions and total counts remain unavailable',
                 F3='not_run;F1 remains unconfirmed',all_source_hashes_unchanged=all(sha(Path(p))==h for p,h in protected.items()))
    if not summary['all_source_hashes_unchanged']: raise ValueError('source changed')
    save_json(out/'summary.json',summary)
    save_json(out/'input_provenance.json',protected)
    blocks=[]
    for r in cards:
        ident=html.escape(r['texture'])
        blocks.append(f'''<article data-id="{ident}" data-priority="{str(r['priority_review']).lower()}" data-class="{r['stable_class']}">
<h3>{ident} · {html.escape(r['source_id'])}</h3><p>기존 후보 {r['prior_class']} → 해상도 일치 후보 <b>{r['stable_class']}</b> · {r['stability_status']}</p>
<img loading="lazy" src="{r['card_path']}" alt="원자료와 윤곽 및 기존 텍스처 비교">
<p><label>사람의 확인 <select aria-label="{ident} 클래스"><option value="">미검토</option><option value="main">소엽 확인</option><option value="interjected">소소엽 확인</option><option value="unknown">판정 불가</option><option value="non_leaf">잎 아님</option></select></label> <input aria-label="{ident} 검토자" placeholder="검토자"> <input aria-label="{ident} 근거" placeholder="판단 근거·가림·접힘"></p></article>''')
    template=r'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>F.7 원자료 검토</title>
<style>body{font-family:"Malgun Gothic",sans-serif;max-width:1050px;margin:32px auto;padding:0 20px;background:#f5f7f3;color:#16332d;line-height:1.65}article{background:white;padding:18px;margin:20px 0;border:1px solid #d5dfd8;border-radius:8px}img{max-width:100%}nav{position:sticky;top:0;background:#e5ede5;padding:12px;z-index:2}input,select,button{font:inherit;padding:6px;margin:3px;max-width:100%}.warning{padding:16px;background:#fff1d7}h3{margin:0}table{border-collapse:collapse}td,th{padding:6px 16px;border-bottom:1px solid #ccd7cf}</style>
<h1>F.7 원자료 검토 — 텍스처 115개</h1>
<p>분류 점수만 보던 1차 분석에 원자료와 윤곽 해상도 점검을 추가했습니다. 64·128·256점마다 같은 기준 사진으로 다시 맞춘 분류가 기존 후보와 모두 같을 때만 ‘해상도 일치 후보’로 남겼습니다. 기존 unknown은 자동 승격하지 않았습니다.</p>
<div class="warning"><b>후보 분류는 해부학적 정답이 아닙니다.</b> 작은 기준 집합(7개 잎, 3장)의 한계가 그대로 남습니다. 사람 확인 칸은 모두 비워 두었습니다. 원본 마스크·생성기·텍스처는 변경하지 않으며, 아래 내보내기는 별도 검토 CSV를 다운로드합니다.</div>
<p>__COUNTS__</p><p>Rig 원사진 60개 연결은 accepted export의 사진 해시로 확인했습니다. 라이브러리 55개는 기존 분할 crop을 보여주므로 주변 복엽 맥락은 없습니다. F.2의 전체 잎축 위치·개수는 새 증거가 없어 여전히 미확정입니다. F.3은 실행하지 않았습니다.</p>
<p><a href="texture_evidence.csv">115개 근거 CSV</a> · <a href="native_contour_metrics.csv">해상도별 지표 CSV</a> · <a href="human_review_blank.csv">빈 사람 검토표</a></p>
<nav><button data-filter="priority">우선 검토</button><button data-filter="all">전체</button><button data-filter="interjected">소소엽 후보</button><button data-filter="unknown">불확실</button><input id="search" aria-label="ID 검색" placeholder="파일·원자료 ID 검색"><button id="export">사람 검토 CSV 내보내기</button><span id="count"></span></nav>
__CARDS__
<script>
const cards=[...document.querySelectorAll('article')]; let filter='priority';
const storageKey='f2-f7-review-20261006-02';let saved={};try{saved=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch(e){}
for(const card of cards){const fields=[...card.querySelectorAll('select,input')];const old=saved[card.dataset.id]||['','',''];fields.forEach((f,i)=>{f.value=old[i]||'';f.addEventListener('change',()=>{saved[card.dataset.id]=fields.map(x=>x.value);try{localStorage.setItem(storageKey,JSON.stringify(saved))}catch(e){} refresh()})})}
function refresh(){const q=document.querySelector('#search').value.toLowerCase();let n=0;for(const c of cards){const ok=(filter==='all'||filter==='priority'&&c.dataset.priority==='true'||c.dataset.class===filter)&&c.textContent.toLowerCase().includes(q);c.hidden=!ok;if(ok)n++}document.querySelector('#count').textContent=` 표시 ${n}/115 · 입력 ${cards.filter(c=>c.querySelector('select').value).length}`}
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;refresh()}));document.querySelector('#search').addEventListener('input',refresh);
document.querySelector('#export').addEventListener('click',()=>{const quote=v=>'"'+String(v).replaceAll('"','""')+'"';const rows=[['texture','human_class','human_reviewer','human_notes','review_basis']];for(const c of cards){rows.push([c.dataset.id,...[...c.querySelectorAll('select,input')].map(x=>x.value),'user_entered_not_automatically_validated'])}const blob=new Blob(['\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='f7_human_review.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)});refresh();
</script></html>'''
    counts=f"기존 후보: 소엽 {summary['prior_counts'].get('main',0)}, 소소엽 {summary['prior_counts'].get('interjected',0)}, 불확실 {summary['prior_counts'].get('unknown',0)}. 해상도 일치 후보: 소엽 {summary['stable_counts'].get('main',0)}, 소소엽 {summary['stable_counts'].get('interjected',0)}, 불확실 {summary['stable_counts'].get('unknown',0)}. 우선 검토 {summary['n_priority_review']}개."
    (out/'REVIEW_KO.html').write_text(template.replace('__COUNTS__',counts).replace('__CARDS__','\n'.join(blocks)),encoding='utf-8')
    save_json(out/'delivery_manifest.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='delivery_manifest.json'})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args())),indent=2))
