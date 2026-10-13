"""Build the separate Korean F2/F7 report from saved analysis tables.

python -m tools.f2_f7_report --out build/compound_structure_f2_f7_20261006_01
"""
from __future__ import annotations
import argparse
import csv
import html
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tools.f2_f7_analysis import read_json,save_json,sha,table
from tools.f2_compound_measurements import read_csv


def run(out: Path) -> dict:
    out=out.resolve()
    policy=read_json(out/'policy.json')
    root=Path(policy['project_root'])
    f7=read_json(out/'F7_summary.json')
    f2=read_json(out/'F2_summary.json')
    rows=read_csv(out/'artifact_classification.csv')
    artifacts=['library_components','flattened_contours','sam_contours','texture_bank_v2']
    names=['라이브러리 구성요소','펼친 잎 윤곽 풀','SAM 윤곽 풀','B5a 텍스처 뱅크']
    fig,axes=plt.subplots(1,3,figsize=(15,4),constrained_layout=True)
    for axis,metric in zip(axes,['norm_perimeter','solidity','aspect']):
        for name in artifacts:
            v=np.sort([float(r[metric]) for r in rows if r['artifact']==name])
            axis.step(v,np.arange(1,len(v)+1)/len(v),where='post',label=f'{name} (n={len(v)})')
        axis.set(xlabel=metric,ylabel='Empirical cumulative fraction',ylim=(0,1.02))
        axis.grid(alpha=.2)
    axes[0].set_xscale('log')
    axes[0].axvspan(f7['classifier']['threshold']-f7['classifier']['guard'],f7['classifier']['threshold']+f7['classifier']['guard'],alpha=.12,color='black')
    axes[0].legend(fontsize=7,loc='lower right')
    fig.suptitle('F7: shape distributions at 64 contour points; candidate labels only')
    fig.savefig(out/'shape_distributions.png',dpi=160)
    plt.close(fig)
    # Separate supplemental rows, never append to the human capture CSV.
    supp=[]
    for n,kind,level,uses,flags in [
        (47,'mixed','leaflet','shape_contour;area;class_reference','damaged_tip'),
        (48,'mixed','compound','compound_structure;shape_contour;class_reference','hand_occlusion;overlap;necrosis'),
        (49,'interjected','leaflet','shape_contour;area;class_reference','on_ruler_overlap'),
        (50,'main','leaflet','shape_contour;area;texture;class_reference','partly_damaged'),
        (51,'interjected','leaflet','shape_contour;area;texture;class_reference','')]:
        p=root/f'data/raw/leaf_library/leaf_lib_20261006/leaf_{n}.png'
        supp.append(dict(session_id='leaf_lib_20261006',photo_file=p.name,source_filename='chat_upload_original_filename_unavailable',
          sha256=sha(p),captured_at='2026-10-06',level=level,pressed='no',ruler_in_frame='yes',
          leaflet_class=kind,uses=uses,quality_flags=flags,record_status='separate_supplement_not_applied_to_capture_csv'))
    table(out/'leaf_library_capture_supplement.csv',supp)
    photo_rows=[]
    for photo in sorted({r.get('photo','') for r in rows if r['artifact']=='library_components'}):
        cc=Counter(r['leaflet_class'] for r in rows if r['artifact']=='library_components' and r['photo']==photo)
        photo_rows.append(dict(photo=photo,**{c:cc[c] for c in ('main','interjected','unknown')},basis='component_shape_candidates_not_verified_anatomical_counts'))
    table(out/'library_photo_class_counts.csv',photo_rows)
    table(out/'c6_steps.csv',[
        dict(step='F2',status='diagnostic',result='8 photos reviewed; 8 provisional projected ratios; full rachis fractions unavailable; not a generator prior',C6_AP50='NaN'),
        dict(step='F7',status='diagnostic',result='236/61/1163/115 records classified; texture candidates main=83 interjected=2 unknown=30; anatomy unvalidated',C6_AP50='NaN')])
    tr=''.join(f'<tr><td>{name}</td><td>{f7[k]["n"]}</td>'+''.join(f'<td>{f7[k]["classes"].get(c,0)}</td>' for c in ['main','interjected','unknown'])+'</tr>' for name,k in zip(names,artifacts))
    checks=[]
    for name,n in zip(artifacts,[236,61,1163,115]):
        group=[r for r in rows if r['artifact']==name]
        checks.append(dict(check=f'{name}_complete_unique',passed=len(group)==n and len({r['item_id'] for r in group})==n))
    for name in ['input_provenance.json','F2_input_provenance.json']:
        p=read_json(out/name)
        checks.append(dict(check=f'{name}_source_hashes_unchanged',passed=all(sha(Path(k))==v for k,v in p['sha256_before'].items())))
    table(out/'delivery_checks.csv',checks)
    if not all(c['passed'] for c in checks): raise RuntimeError('delivery/source integrity checks failed')
    report='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>F.2·F.7 별도 분석</title>
<style>body{font-family:"Malgun Gothic",sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;line-height:1.7;color:#17292a;background:#f7f8f5}h1{font-size:30px}h2{margin-top:34px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:10px;border-bottom:1px solid #d6deda;text-align:left}img{max-width:100%;background:white}.note{background:#e8eee7;padding:20px;border-left:4px solid #468368}a{color:#11605d}code{background:#edf0eb;padding:2px 5px}</style>
<h1>F.2·F.7 — 복엽 구조와 클래스 혼합 분석</h1><p>2026-10-06 · 기존 파일을 보존한 별도 분석 · 학습·검출 추론·렌더링 없음</p>
<div class="note"><b>형태 기반 후보 분류는 끝났지만, 생성기에 적용할 해부학적 매개변수는 확정되지 않았습니다.</b><br>
F.1의 조각 대 완전한 작은 잎 가설은 여전히 미확인입니다. 이번 사용자의 승인은 F.2·F.7 분석에 한정되며, F.3 구현·착수의 근거로 사용하지 않습니다.</div>
<h2>네 자료 묶음의 분류</h2><p>둘레 복잡도를 주 지표로 사용했습니다. 크기는 클래스 결정에 쓰지 않았습니다. 모든 클래스 값은 <b>형태 후보</b>이며 식물학적으로 확인한 정답이 아닙니다. 복엽 전체 구성요소 29개, 비잎·미분류 15개, 손상 1개 등은 보류했습니다.</p>
<table><tr><th>자료</th><th>전체</th><th>소엽 후보</th><th>소소엽 후보</th><th>불확실</th></tr>__ROWS__</table>
<p>B5a의 텍스처 115개 중 소소엽 형태 후보는 <b>2개</b>: <code>tex_038 ← leaf_43_c07</code>, <code>tex_079 ← dwt_02_a71</code>입니다. 각각 라이브러리 사진과 rig 마스크에서 왔습니다. 실제 두 클래스가 몇 개씩 혼합되었는지는 확인되지 않았습니다. 원본 뱅크를 다시 만들거나 바꾸지 않았습니다.</p>
<img src="texture_interjected_candidates.png" alt="소소엽 형태 텍스처 후보 두 개"><p>오른쪽 원형 SAM 마스크는 형태만으로 해부학적 소소엽 여부를 확정할 수 없습니다. 후보 표시가 확정 혼합 개수는 아닙니다.</p>
<h2>기준 사진·분류 방법과 한계</h2><p>leaf_47·50·51의 적합용 윤곽 7개(소엽 4, 소소엽 3)로 임계값을 맞췄습니다. 심하게 손상된 leaf_47 소소엽·leaf_50 위쪽 잎, 자 눈금이 겹친 leaf_49의 두 영역은 적합에서 제외하고 진단값만 남겼습니다. leaf_48은 겹친 복엽이라 독립 잎 윤곽 학습에 쓰지 않았습니다.</p>
<p>공통 지표는 등간격 64점 윤곽의 <code>둘레² / (4π × 다각형 면적)</code>입니다. 저장된 윤곽 풀의 64점 표현에 맞춘 값이므로 과거 문서의 다른 해상도·분할 방법에서 나온 수치와 직접 비교하면 안 됩니다. 소엽 적합 범위 1.402–2.097, 소소엽 1.120–1.196; 임계값 1.299, 보류 구간 1.169–1.429입니다. 256점 측정도 CSV에 남겼습니다.</p>
<p>적합 자료에서 분리되었다는 결과이지 외부 정확도가 아닙니다. 사진별 제외 점검에서 leaf_47·50의 소엽 4개는 분류됐지만, 소소엽은 모두 leaf_51에 있어 이를 제외하면 학습 클래스 자체가 사라집니다. 독립 소소엽 검증은 불가능합니다. 독립 개체 수와 같은 잎의 재촬영 여부도 미확인입니다.</p>
<p>보류 폭은 10% 최소 폭과 사진별 적합 변동 중 큰 값으로 정한 분석용 보수 기준이며 신뢰구간이 아닙니다. 폭을 0 / 0.5 / 1 / 1.5배로 바꾸면 텍스처 소소엽 후보는 13 / 7 / 2 / 1개입니다. 따라서 <b>혼합 비율의 확정 추정치로 쓰면 안 됩니다.</b> 접힘·가림·주름도 둘레를 바꾸며, 생장점 조직을 별도로 학습하거나 모델링하지 않았습니다. 미분류 객체는 보류했습니다.</p>
<img src="reference_segmentation.png" alt="기준 사진의 분할 윤곽과 품질 플래그"><img src="shape_distributions.png" alt="네 자료의 둘레 복잡도·solidity·aspect 전체 누적분포">
<h2>F.2 복엽 사진 측정</h2><p>지정된 7장(03·04·08·12·19·24·25)과 새 사진 48, 총 8장을 확인했습니다. 03/04, 24/25는 같은 복엽 재촬영 가능성이 있어 독립 표본으로 합산하지 않았습니다. 반복 여부는 사진 유사성에 따른 점검 후보이며 확정 식별이 아닙니다.</p>
<p>확인 가능한 축 구간과 작은 잎 후보를 표시했습니다. 5장, 후보 8개의 영상상 잎몸 길이/인접 소엽 길이비는 <b>0.234–0.601</b>입니다. 이는 양 끝점을 연결한 <b>투영 길이의 잠정 비율</b>이며, 소소엽 여부·인접 소엽 연결·펼친 실제 길이가 미확정입니다. 5px 끝점 오차 민감도도 CSV에 포함했습니다. <code>measured_small_n</code>으로 기록했지만 생성기 매개변수로 사용하지 않습니다.</p>
<p>가림·괴사·말림 때문에 전체 잎축 시작/끝과 각 부착점은 확인하지 못했습니다. 그래서 <b>소엽 쌍 수·소소엽 전체 개수·정단 존재·전체 잎축 대비 부착 위치는 미확정</b>입니다. 보이는 구간을 전체 잎축처럼 정규화하지 않았으며, CSV의 NaN은 0개/0위치라는 뜻이 아닙니다. 후보 수 역시 소소엽 총수가 아닙니다.</p>
<p>F.12의 사용자 기준인 소엽 5–7개와 추가 소소엽을 구분했습니다. leaf_48의 사용자 설명(소엽 7, 소소엽 4–6)은 재측정 결과와 별도 칸에 보존했습니다. 절대 mm 척도를 추정하지 않았습니다.</p>
<img src="labelled_rachises.png" alt="8장에 표시한 보이는 잎축과 후보 길이 측정"><p>청록: 보이는 축 구간. 자홍: 소소엽 후보 길이. 주황: 잠정 인접 소엽 길이. 부착점이 확실하지 않아 위치 비율은 계산하지 않았습니다.</p>
<h2>확정에 필요한 자료</h2><p>복엽별 고유 ID와 재촬영 연결, 기부·정단 부착부가 모두 보이는 펼친 복엽, 양쪽 소엽·소소엽 부착점 표시가 필요합니다. 독립적인 여러 복엽에서 온 손상 없는 소소엽 단독 사진으로 분류 기준을 검증해야 합니다. 비율 측정에는 자가 필수는 아니며, 잎 위에 자 눈금이 겹치면 안 됩니다.</p>
<h2>파일과 검증</h2><p><a href="artifact_classification.csv">전체 항목 분류 CSV</a> · <a href="interjected_leaflets.csv">후보 길이비 CSV</a> · <a href="compound_measurements.csv">사진별 확정/미확정 CSV</a> · <a href="near_threshold.csv">경계 부근 항목</a> · <a href="classification_sensitivity.csv">보류 폭 민감도</a> · <a href="leaf_library_capture_supplement.csv">새 사진 5장 별도 등록표</a></p>
<p>새 사진의 해시와 클래스는 별도 보충 CSV로 저장했고 원본 46행 등록표는 보존했습니다. 전체 분류 건수·ID 중복 검사를 통과했고, 원본 사진·윤곽·뱅크·생성기·C6 보고서의 입력 해시는 재확인했습니다. 기존 C6 점수는 재계산하지 않았습니다. 별도 <code>c6_steps.csv</code> 두 행은 모두 diagnostic입니다.</p>
<p>계산 도구: <code>tools/f2_f7_analysis.py</code>, <code>tools/f2_compound_measurements.py</code>, <code>tools/f2_f7_report.py</code>. 분석 규칙과 수작업 표시 좌표는 이 결과 폴더의 JSON·CSV에 남겼습니다.</p></html>'''.replace('__ROWS__',tr)
    (out/'REPORT_KO.html').write_text(report,encoding='utf-8')
    outputs=[p for p in out.iterdir() if p.is_file() and p.name!='delivery_manifest.json']
    result=dict(checks=checks,all_passed=True,output_sha256={p.name:sha(p) for p in outputs})
    save_json(out/'delivery_manifest.json',result)
    return dict(all_passed=True,n_checks=len(checks),n_outputs=len(outputs))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,type=Path)
    print(run(p.parse_args().out))
