"""Package the existing preprocessing comparison for a GPU-only Colab run.

python -m tools.preprocess_colab --out build/preprocess_colab_20260929
"""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
import stat

import nbformat as nbf
from tools.leaf_preprocess_lab import assert_build, read_json, write_json, sha
from tools.preprocess_compare import ROOT, ACCEPTED, INDEX, SESSION, FULL, TILES, SAM


def make_notebook(bundle_hash):
    cells=[]
    md=lambda s:cells.append(nbf.v4.new_markdown_cell(s))
    code=lambda s:cells.append(nbf.v4.new_code_cell(s))
    md('# 토마토 전처리 비교 · Colab GPU\n\n기존 모델은 재학습하지 않습니다. dwt_01의 4장 시험 → 검토 사진 전체의 평활화 비교 → 선택 후보의 밝기 비교 순서입니다.\n\n아직 실행 결과가 없는 노트북입니다. 원본 기준 조건도 GPU에서 다시 실행합니다. **런타임 → 런타임 유형 변경 → T4 GPU**를 선택하고 실행하세요. 입력 ZIP은 본 노트북과 함께 제공됩니다.')
    md('## 1. GPU 확인 및 입력 ZIP 올리기\nGPU가 없으면 중단합니다. 노트북 파일이 아닌 `preprocess_inputs.zip`을 선택하세요.')
    code("import torch\nfrom pathlib import Path\nfrom google.colab import files\nassert torch.cuda.is_available(), 'Colab GPU 런타임으로 변경하세요. CPU에서 반복 추론하지 않습니다.'\nprint(torch.cuda.get_device_name(0))\narchive_path = Path('/content/preprocess_inputs.zip')\n# The Files panel is an alternative when the output-frame picker is unavailable.\nif archive_path.is_file():\n    uploaded = {str(archive_path): None}\nelse:\n    uploaded = files.upload()")
    md('## 2. 입력 해시 검증과 안전한 압축 해제\n원본 사진, 검토 마스크, 고정 모델과 필요한 도구만 포함합니다. 보정·라벨 원본을 덮어쓰지 않습니다.')
    code(f'''from pathlib import Path, PurePosixPath
import hashlib, json, zipfile, os
expected_zip_sha256 = {bundle_hash!r}
matches = [Path(p) for p in uploaded if p.endswith('.zip')]
assert len(matches) == 1, '입력 ZIP 하나만 선택하세요.'
archive = matches[0]
def digest_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
assert digest_file(archive) == expected_zip_sha256, 'ZIP 해시 불일치'
workspace = Path('/content/tomato_preprocess')
workspace.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('bundle_manifest.json'))
    assert len(z.infolist()) == len(manifest['files'])+1
    assert sum(i.file_size for i in z.infolist()) < 4*1024**3
    for name,expected in manifest['files'].items():
        p=PurePosixPath(name)
        assert not p.is_absolute() and '..' not in p.parts and '\\\\' not in name and ':' not in name
        data=z.read(name)
        assert hashlib.sha256(data).hexdigest()==expected, name
        target=workspace/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists(): assert digest_file(target)==expected, '기존 입력 파일이 변경되었습니다: '+name
        else: target.write_bytes(data)
os.chdir(workspace)
del uploaded
print('검증한 입력 파일:',len(manifest['files']))''')
    md('## 3. 실행 환경 준비\nPyTorch는 Colab GPU 환경을 사용합니다. 나머지 패키지는 지정된 버전을 설치하며 실제 버전을 결과에 기록합니다. 로컬과 GPU의 미세한 수치 차이를 섞지 않습니다.')
    code("import subprocess, sys\nsubprocess.run([sys.executable,'-m','pip','install','-q','ultralytics==8.4.131','scipy==1.18.0','opencv-python==4.13.0.92','hydra-core==1.3.2','iopath==0.1.10','pytest','pandas','matplotlib'],check=True)\nassert tuple(map(int,torch.__version__.split('+')[0].split('.')[:2])) >= (2,5)\nsubprocess.run([sys.executable,'-m','pytest','tools/tests/test_preprocess_study.py','tools/tests/test_leaf_preprocess_lab.py','-q'],check=True)")
    md('## 4. 4장 파일럿\n11·18·24·25번 사진의 모든 검토 소엽으로 7가지 평활화를 시험합니다. 중단 후 같은 셀을 다시 실행하면 해시가 일치하는 캐시만 재사용합니다. 작은 수치 지도 비교는 기존 비교실에서 선택했던 소엽을 별도로 사용합니다.')
    code("common=[sys.executable,'-u','-m','tools.preprocess_compare','--device','cuda','--sam-config','build/colab_sam_config.json']\nsubprocess.run(common+['--out','build/colab_preprocess_pilot','--views','11','18','24','25'],check=True)")
    md('## 5. dwt_01 검토 사진 전체로 확대\n268개 검토 소엽 관측을 포함하는 14장 사진을 사용합니다. 같은 식물의 여러 사진이므로 독립 식물 14개로 해석하지 않습니다. 동일 조건의 검토 기준에 대해서만 비교합니다.')
    code("subprocess.run(common+['--out','build/colab_preprocess_expanded'],check=True)\nimport pandas as pd\nsummary=pd.read_csv('build/colab_preprocess_expanded/summary.csv')\ndisplay(summary)")
    md('## 6. 탐색 후보 선택과 밝기·대비 비교\n기관 탐지와 마스크 결과의 최고 평활화를 각각 후보로 둡니다. 원본보다 개선되지 않은 경우 해당 후보는 추가하지 않습니다. 이 선택은 dwt_01 탐색용이며 새 개체의 검증을 대신하지 않습니다.')
    code("baseline=summary.set_index('condition').loc['none__none']\ncandidates=['none']\nfor metric in ['map50_production','mean_mask_iou']:\n    best=summary.loc[summary[metric].idxmax()]\n    if best[metric]>baseline[metric]: candidates.append(best['condition'].split('__')[0])\ncandidates=list(dict.fromkeys(candidates))\nPath('build/tone_candidate_selection.json').write_text(json.dumps({'candidates':candidates,'rule':'strict improvement over original; max production AP50 and max mean mask IoU separately','exploratory':True},indent=2))\nsubprocess.run(common+['--out','build/colab_preprocess_tone','--smoothing',*candidates,'--tones','none','gamma085','gamma115','clahe15'],check=True)")
    md('## 7. 밝기·RGB 비율 수치 지도\n검토된 기존 파일럿 소엽 4개의 수치 배열과 공통 유효 영역을 저장합니다. 이 단계도 GPU에서 실행하며 비율 지도는 탐지기 입력을 대체하지 않습니다.')
    code("subprocess.run(common+['--out','build/colab_preprocess_scalars','--views','11','18','24','25','--mask-limit','1','--scalar'],check=True)")
    md('## 8. 결과 확인\nAP50은 기존 운영 출력 기준(confidence ≥ 0.25)을 유지한 값입니다. 낮은 confidence까지 포함하는 학습 보고서의 AP와 직접 비교하지 않습니다. 독립 주맥 기준·수정 시간·3D 정확도는 아직 미평가입니다.')
    code("import matplotlib.pyplot as plt\nfor name in ['expanded','tone']:\n    table=pd.read_csv(f'build/colab_preprocess_{name}/summary.csv')\n    display(table[['condition','photos','reviewed_masks','map50_production','mean_mask_iou','mean_mask_dice','merge_candidates']])\n    ax=table.set_index('condition')[['map50_production','mean_mask_iou']].plot.bar(figsize=(12,4),ylim=(0,1),rot=55)\n    ax.set_ylabel('Score (0–1)'); ax.set_title('dwt_01 exploratory comparison · '+name)\n    plt.tight_layout(); plt.show()")
    md('## 9. 결과 ZIP 내려받기\n완료된 실행만 결과에 포함합니다. CSV·설정·예측 마스크·비교 이미지·수치 배열을 내려받습니다. 큰 SAM 후보 logits 캐시는 Colab 작업 폴더에 남으며 기본 ZIP에서 제외됩니다. 후보 재선택/재계산을 이어가려면 런타임 종료 전에 캐시도 따로 보관하세요.')
    code("import zipfile\nresult_zip=Path('/content/preprocess_colab_results.zip')\nwith zipfile.ZipFile(result_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:\n    for run in ['pilot','expanded','tone','scalars']:\n        folder=Path('build/colab_preprocess_'+run)\n        assert (folder/'complete.json').is_file(), str(folder)+' 미완료'\n        for p in folder.rglob('*'):\n            if p.is_file() and 'sam_cache' not in p.parts: z.write(p,p.as_posix())\n    z.write('build/tone_candidate_selection.json')\n    z.writestr('RESULTS_README.txt','GPU results; SAM logits caches excluded. Preserve manifests; original labels are unchanged. Human midrib/3D accuracy is unavailable.')\nfiles.download(str(result_zip))")
    notebook=nbf.v4.new_notebook(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),
             accelerator='GPU',colab=dict(name='Tomato_Preprocessing_GPU.ipynb',provenance=[])))
    # Colab may not surface inherited subprocess stdout in the cell output.
    # Stream it explicitly so long inference runs expose progress and failures.
    streaming = '''def run_comparison(command):
    import time
    started = time.monotonic()
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, bufsize=1) as process:
        for line in process.stdout:
            print(line, end='', flush=True)
        code = process.wait()
    print('Elapsed seconds:', round(time.monotonic()-started, 2), flush=True)
    if code:
        raise subprocess.CalledProcessError(code, command)

'''
    notebook.cells[8].source = streaming + notebook.cells[8].source
    for index in (8, 10, 12, 14):
        notebook.cells[index].source = notebook.cells[index].source.replace(
            'subprocess.run(common+', 'run_comparison(common+').replace('],check=True)', '])')
    nbf.validate(notebook)
    return notebook


def pack(out):
    out=assert_build(out);out.mkdir(parents=True,exist_ok=False)
    selected=set()
    def add(path):
        path=Path(path).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Outside project input')
        selected.add(path)
    for name in ['preprocess_colab.py','preprocess_compare.py','preprocess_study.py','leaf_preprocess_lab.py',
                 'leaf_preprocess_lab.html','leaf_preprocess_lab.js','organ_prelabel.py','leaflet_segmenter.py',
                 'leaf_light/__init__.py','leaf_light/common.py','tests/test_preprocess_study.py','tests/test_leaf_preprocess_lab.py']:
        add(ROOT/'tools'/name)
    for p in [ACCEPTED,INDEX,FULL,TILES,SESSION/'capture.json',ROOT/'build/rgb_preprocess_lab_20260929/dataset.json']:
        add(p)
    observations=[o for o in read_json(ACCEPTED)['observations'] if o.get('review')=='accepted_by_user']
    for o in observations:
        add(ACCEPTED.parent/o['mask_file']);add(SESSION/'images'/o['image_file'])
    cfg=read_json(SAM);checkpoint=Path(cfg['checkpoint']);add(checkpoint)
    repo=Path(cfg['repository'])
    for p in (repo/'sam2').rglob('*'):
        if p.is_file() and p.suffix in ('.py','.yaml','.yml'):
            add(p)
    for name in ('LICENSE','README.md','setup.py','pyproject.toml'):
        if (repo/name).exists():add(repo/name)
    portable=dict(cfg,repository=repo.relative_to(ROOT).as_posix(),checkpoint=checkpoint.relative_to(ROOT).as_posix(),device='cuda')
    portable.pop('runtime',None)
    extra={'build/colab_sam_config.json':json.dumps(portable,indent=2).encode(), 'tools/__init__.py':b''}
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in selected}
    hashes.update({k:hashlib.sha256(v).hexdigest() for k,v in extra.items()})
    manifest=dict(schema='preprocess-colab-input-1',files=hashes,source_config_sha256=sha(SAM),
                  note='Only portable derived SAM config paths/device changed; weight/image/label bytes unchanged',
                  source_photos=len({o['image_file'] for o in observations}),reviewed_masks=len(observations))
    archive=out/'preprocess_inputs.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in sorted(selected):z.write(p,p.relative_to(ROOT).as_posix())
        for name,data in extra.items():z.writestr(name,data)
        z.writestr('bundle_manifest.json',json.dumps(manifest,indent=2))
    write_json(out/'bundle_manifest.json',manifest)
    nbf.write(make_notebook(sha(archive)),out/'Tomato_Preprocessing_GPU.ipynb')
    (out/'사용안내.md').write_text('# Colab 전처리 비교\n\n1. `Tomato_Preprocessing_GPU.ipynb`를 Colab에서 엽니다.\n2. 런타임 유형을 GPU로 바꿉니다.\n3. 위에서 순서대로 실행하고 첫 업로드에서 `preprocess_inputs.zip`을 선택합니다.\n4. 끝나면 `preprocess_colab_results.zip`을 내려받습니다.\n\n기존 모델 재학습·원본 수정 없음. 대량 추론은 로컬에서 실행하지 않습니다. GPU 실행 전에는 비교 완료나 개선을 주장하지 않습니다.\n',encoding='utf-8')
    return dict(out=str(out),archive_sha256=sha(archive),bytes=archive.stat().st_size,files=len(hashes),
                photos=manifest['source_photos'],masks=len(observations),notebook_executed=False)


def import_results(archive, out):
    """Import only derived outputs into a fresh folder; never overwrite project inputs."""
    out=assert_build(out)
    if out.exists():
        raise ValueError('Use a new import directory')
    allowed={'pilot','expanded','tone','scalars'}
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist(); names=[i.filename for i in infos]
        if len(set(n.casefold() for n in names))!=len(names) or sum(i.file_size for i in infos)>20*1024**3:
            raise ValueError('Duplicate paths or excessive archive size')
        for i in infos:
            p=PurePosixPath(i.filename)
            if (p.is_absolute() or '..' in p.parts or '\\' in i.filename or ':' in i.filename
                or stat.S_ISLNK(i.external_attr>>16) or i.is_dir() or p.as_posix()!=i.filename):
                raise ValueError('Unsafe result path')
            if i.filename=='RESULTS_README.txt' or i.filename=='build/tone_candidate_selection.json':
                continue
            if len(p.parts)<3 or p.parts[0]!='build' or p.parts[1] not in {'colab_preprocess_'+n for n in allowed}:
                raise ValueError('Unexpected result path')
        runs=[]
        for name in sorted(allowed):
            prefix='build/colab_preprocess_'+name
            if prefix+'/complete.json' not in names:
                raise ValueError('Missing completion record: '+name)
            complete=json.loads(z.read(prefix+'/complete.json'))
            if complete.get('status')!='complete' or complete.get('sources_unchanged') is not True:
                raise ValueError('Incomplete or modified sources: '+name)
            runs.append(prefix)
        out.mkdir(parents=True)
        for i in infos:
            target=out/i.filename;target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i) as src, target.open('wb') as dst:
                import shutil
                shutil.copyfileobj(src,dst,1024*1024)
    write_json(out/'import_record.json',dict(source_zip=str(Path(archive).resolve()),sha256=sha(Path(archive)),
           runs=runs,original_inputs_overwritten=False,source_compatibility_requires_manifest_hash_check=True))
    return dict(out=str(out),runs=[str(out/r) for r in runs])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--import-results',type=Path)
    a=p.parse_args()
    print(json.dumps(import_results(a.import_results,a.out) if a.import_results else pack(a.out)))


if __name__=='__main__':main()
