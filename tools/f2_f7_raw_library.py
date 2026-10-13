"""Decode original leaf library, verify old component crops and expose photo context.

Run with the existing tomato_synth Python (pillow_heif installed). No source writes.
python -m tools.f2_f7_raw_library --prior build/compound_structure_f2_f7_20261006_01 --out build/compound_structure_f2_f7_20261006_02
"""
from __future__ import annotations
import argparse
import html
from pathlib import Path
import numpy as np
import cv2
from PIL import Image,ImageOps,ImageDraw
from tools.f2_f7_analysis import read_json,save_json,sha,table
from tools.f2_compound_measurements import read_csv
from tomato3d.synth.leaflib import read_bgr,segment_leaflets,PRM


def run(prior:Path,out:Path):
    prior,out=prior.resolve(),out.resolve()
    policy=read_json(prior/'policy.json'); root=Path(policy['project_root']).resolve()
    if not out.is_relative_to(root/'build') or out==prior: raise ValueError('separate build output required')
    folder=root/'data/raw/leaf_library/leaf_lib_20261006'
    captures={r['photo_file']:r for r in read_csv(folder/'leaf_library_capture.csv')}
    supplemental={r['photo_file']:r for r in read_csv(prior/'leaf_library_capture_supplement.csv')}
    records=read_json(root/policy['library_root']/'library_components.json')['records']
    bank=read_json(root/policy['bank'])['textures']
    bank_by_component={e['component_id']:e for e in bank if e['source']=='library_crop'}
    by_id={r['component_id']:r for r in records}
    hashes={str(folder/'leaf_library_capture.csv'):sha(folder/'leaf_library_capture.csv')}
    for p in [root/policy['library_root']/'library_components.json',root/policy['bank'],root/'tomato3d/synth/leaflib.py',root/'tomato3d/synth/capture.py']:
        hashes[str(p)]=sha(p)
    (out/'raw_photos').mkdir(exist_ok=True)
    (out/'raw_context').mkdir(exist_ok=True)
    checks=[]; photo_rows=[]; panels=[]
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in ('.heic','.png'):continue
        digest=sha(path); hashes[str(path)]=digest
        row=captures.get(path.name,supplemental.get(path.name))
        if row is None or digest!=row['sha256']:raise ValueError(f'capture hash missing/mismatch {path.name}')
        if path.suffix.lower()=='.heic':
            bgr=read_bgr(path,PRM['max_side_px']); image=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
            masks=segment_leaflets(bgr) if row['level'] in ('leaflet','compound') else []
            for n,mask in enumerate(masks):
                cid=f'{path.stem}_c{n:02d}'
                y,x=np.nonzero(mask); x0,y0,x1,y1=int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)
                crop=bgr[y0:y1,x0:x1].copy(); crop[~mask[y0:y1,x0:x1]]=255
                old=by_id.get(cid)
                verified=False
                if old:
                    old_path=root/policy['library_root']/old['crop'];hashes[str(old_path)]=sha(old_path)
                    before=np.asarray(Image.open(old_path).convert('RGB'))
                    after=cv2.cvtColor(crop,cv2.COLOR_BGR2RGB)
                    verified=before.shape==after.shape and np.array_equal(before,after)
                checks.append(dict(photo=path.name,component_id=cid,crop_pixel_identical=verified,
                    x0_px=x0,y0_px=y0,x1_px=x1,y1_px=y1,coordinate_frame='EXIF_oriented_max_side3024',
                    in_texture_bank=cid in bank_by_component))
                if verified and cid in bank_by_component:
                    entry=bank_by_component[cid]
                    context=image.copy(); d=ImageDraw.Draw(context);d.rectangle((x0,y0,x1,y1),outline='#ff00b7',width=8)
                    context=ImageOps.contain(context,(1200,1200))
                    context.save(out/'raw_context'/f"{Path(entry['file']).stem}.jpg",quality=94)
        else:
            image=ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        preview=ImageOps.contain(image,(1600,1600))
        preview.save(out/'raw_photos'/f'{path.stem}.jpg',quality=94)
        photo_rows.append(dict(photo=path.name,sha256=digest,decoded_analysis_width_px=image.width,decoded_analysis_height_px=image.height,
             content=row.get('content','user_photo_description_in_addendum_F'),level=row['level'],uses=row['uses'],
             quality_flags=row['quality_flags'],leaflet_class_user_given=row.get('leaflet_class',''),
             source_record='original_capture_csv' if path.name in captures else 'separate_supplement',
             source_path=str(path)))
        panels.append(f'<section><h2>{html.escape(path.name)}</h2><p>{html.escape(row.get("content",""))} · {html.escape(row["quality_flags"])}</p><img loading="lazy" src="raw_photos/{path.stem}.jpg" alt="{path.name} 원본에서 디코딩한 사진"></section>')
        print(path.name,flush=True)
    table(out/'raw_photo_inventory.csv',photo_rows)
    table(out/'component_raw_registration.csv',checks)
    bank_checks=[r for r in checks if r['in_texture_bank']]
    summary=dict(n_photos=len(photo_rows),heic=sum(r['photo'].endswith('.heic') for r in photo_rows),png=sum(r['photo'].endswith('.png') for r in photo_rows),
        excluded_from_leaf_segmentation=[r['photo'] for r in photo_rows if r['level'] not in ('leaflet','compound')],
        n_components=len(checks),n_pixel_identical=sum(r['crop_pixel_identical'] for r in checks),
        n_library_bank_components=len(bank_checks),n_library_bank_pixel_identical=sum(r['crop_pixel_identical'] for r in bank_checks),
        compound_capture_content=[dict(photo=r['photo'],content=r['content'],flags=r['quality_flags']) for r in photo_rows if 'compound_structure' in r['uses']],
        all_sources_unchanged=all(sha(Path(p))==h for p,h in hashes.items()))
    save_json(out/'raw_library_summary.json',summary)
    save_json(out/'raw_library_provenance.json',hashes)
    (out/'RAW_PHOTOS_KO.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>잎 라이브러리 원사진</title><style>body{font-family:Malgun Gothic,sans-serif;max-width:1100px;margin:auto;background:#f4f6f2;padding:24px}img{max-width:100%}section{background:white;padding:18px;margin:25px 0}</style><h1>원사진 51장</h1><p>지정한 data/raw/leaf_library/leaf_lib_20261006 폴더의 HEIC 46장과 PNG 5장에서 생성한 열람용 사본입니다. 원본은 변경하지 않았습니다. 내용 표시는 원본 촬영표를 그대로 따릅니다.</p>'+''.join(panels)+'</html>',encoding='utf-8')
    # Attach registered full-photo context links; no change to old proposal labels.
    page=out/'REVIEW_KO.html'
    text=page.read_text(encoding='utf-8')
    for row in bank_checks:
        if not row['crop_pixel_identical']:continue
        entry=bank_by_component[row['component_id']]
        marker=f'<h3>{entry["file"]} · {row["component_id"]}</h3>'
        link=f'<p><a href="raw_context/{Path(entry["file"]).stem}.jpg" target="_blank">원본 HEIC 전체 사진에서 위치 보기</a> · <a href="raw_photos/{Path(row["photo"]).stem}.jpg" target="_blank">표시 없는 사진</a></p>'
        if marker+link not in text:text=text.replace(marker,marker+link)
    text=text.replace('라이브러리 55개는 기존 분할 crop을 보여주므로 주변 복엽 맥락은 없습니다.',f'라이브러리 {len(bank_checks)}개는 원본 HEIC를 다시 디코딩·분할하여 기존 crop과 픽셀 일치를 확인했습니다. 각 항목의 전체 사진 링크에서 주변 맥락을 확인할 수 있습니다.')
    notice='<p><a href="RAW_PHOTOS_KO.html">지정 폴더의 원사진 51장 전체 보기</a> · <a href="raw_photo_inventory.csv">사진별 내용·해시 목록</a></p><p>촬영표상 leaf_03·04는 노화한 복엽 조각이고 leaf_17은 잎이 없는 줄기 조각입니다. 03·04를 완전한 복엽의 개수·위치 측정에 쓰거나 17을 소엽으로 분류하지 않습니다.</p>'
    if notice not in text:
        text=text.replace('<nav>',notice+'<nav>')
    page.write_text(text,encoding='utf-8')
    evidence=read_json(out/'summary.json')
    evidence['library_photo_context_limit']='55 library source crops pixel-registered to original HEIC; full-photo context linked. Botanical class remains unvalidated.'
    evidence['raw_library_summary']=summary
    save_json(out/'summary.json',evidence)
    save_json(out/'delivery_manifest.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='delivery_manifest.json'})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    print(run(**vars(p.parse_args())))
