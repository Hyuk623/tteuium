"""Portable, hash-checked Colab batch transport for the existing static XL exporter."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import stat
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

from tools.leaf_light.common import ROOT, StudyError, digest, file_hash, output_dir, read_json, write_json

SCHEMA = 'colab-static-xl-1'
SOURCE_FILES = (
    'tools/colab_xl_bridge.py', 'tools/groimp_structure_export.py', 'tools/groimp_bridge.py',
    'tools/leaf_light/__init__.py', 'tools/leaf_light/common.py',
    'tomato3d/__init__.py', 'tomato3d/io/__init__.py', 'tomato3d/io/schemas.py', 'tomato3d/io/tables.py',
    'tomato3d/light/__init__.py', 'tomato3d/light/geometry.py', 'tomato3d/light/frames.py',
    'tomato3d/light/scene.py', 'tomato3d/light/units.py',
)
DEPENDENCIES = ('numpy', 'pandas', 'pydantic')
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_FILES = 2048
EXPORT_FILES = {'Model.rgg','organs.csv','relationships.csv','coordinates.csv','structure_snapshot.json',
                'export.json','열기안내.md'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_hash(path: Path) -> str:
    """Generated text may use Windows or Linux newlines; original source hashes remain byte-exact."""
    return sha(path.read_bytes().replace(b'\r\n',b'\n'))


def json_bytes(value) -> bytes:
    return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')


def archive_files(path: Path) -> dict[str, bytes]:
    """Validate every path and bound decompression before writing any archive content."""
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>MAX_ARCHIVE_FILES or sum(i.file_size for i in infos)>MAX_ARCHIVE_BYTES:
            raise StudyError('Archive exceeds the static-export size limit')
        names=[]
        for i in infos:
            p=PurePosixPath(i.filename)
            if (i.orig_filename!=i.filename or i.is_dir() or p.is_absolute() or '..' in p.parts or '\\' in i.filename
                    or ':' in i.filename or p.as_posix()!=i.filename
                    or stat.S_ISLNK(i.external_attr>>16)):
                raise StudyError('Unsafe archive path: '+i.filename)
            names.append(i.filename)
        if len({n.casefold() for n in names})!=len(names):
            raise StudyError('Duplicate archive paths')
        return {i.filename:z.read(i) for i in infos}


def verified_archive(path: Path, manifest_name: str) -> tuple[dict,dict[str,bytes]]:
    files=archive_files(path)
    m=json.loads(files[manifest_name])
    expected=m['files']
    if set(files)!=(set(expected)|{manifest_name}):
        raise StudyError('Archive file set differs from its manifest')
    for name,h in expected.items():
        if sha(files[name])!=h:
            raise StudyError('Archive digest mismatch: '+name)
    return m,files


def zip_write(path: Path, files: dict[str,bytes]) -> None:
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):
            z.writestr(name,data)


def pack(run: Path, out: Path, plants: list[str] | None = None) -> dict:
    import tempfile
    from tools.leaf_light.common import BUILD
    from tools.groimp_structure_export import export_plant, load_snapshot, make_graph, render_rgg
    plants=plants or sorted(p.parent.parent.name for p in run.glob('*/hierarchy/hierarchy.json'))
    if not plants or len(set(plants))!=len(plants):
        raise StudyError('Select at least one distinct plant')
    files={name:(ROOT/name).read_bytes() for name in SOURCE_FILES}
    provenance={}
    expected={}
    for plant in plants:
        snapshot=load_snapshot(run,plant)
        graph=make_graph(snapshot)
        h=snapshot['hierarchy']
        paths={'hierarchy':run/plant/'hierarchy/hierarchy.json',
               'backup':Path(h['inputs']['backup']), 'structure':Path(h['inputs']['structure'])/'structure.json',
               'status':run/plant/'status.json'}
        provenance[plant]={}
        for role,p in paths.items():
            name=f'inputs/{plant}/{role}.json'
            data=p.read_bytes()
            original_hash=snapshot['source_hashes'][str(p.resolve())]
            if sha(data)!=original_hash:
                raise StudyError('Input changed while packaging: '+str(p))
            files[name]=data
            provenance[plant][role]=dict(bundle_path=name,original_path=str(p.resolve()),sha256=original_hash)
        expected[plant]=dict(session_id=graph['session_id'],graph_digest=digest(graph),
                             model_sha256=sha(render_rgg(graph).encode('utf-8')))
        BUILD.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='colab_reference_',dir=BUILD) as temp:
            ref=Path(temp)/'export'
            export_plant(run,plant,ref)
            expected[plant]['artifact_sha256']={name:text_hash(ref/name) for name in EXPORT_FILES if name!='export.json'}
    versions={p:importlib.metadata.version(p) for p in DEPENDENCIES}
    files['requirements-colab.txt']=''.join(f'{k}=={v}\n' for k,v in versions.items()).encode()
    m=dict(schema=SCHEMA,kind='input',plants=plants,provenance=provenance,expected=expected,
           dependencies=versions,files={k:sha(v) for k,v in files.items()},
           operation='static_xl_export',validated_metric=False,suitable_for_ppfd=False)
    files['bundle.json']=json_bytes(m)
    out=output_dir(out)
    zip_write(out/'tomato_colab_inputs.zip',files)
    bundle_hash=file_hash(out/'tomato_colab_inputs.zip')
    notebook(out/'Tomato_XL_Colab.ipynb',bundle_hash)
    receipt=dict(bundle_sha256=bundle_hash,plants=plants,files=len(files),bytes=(out/'tomato_colab_inputs.zip').stat().st_size,
                 operation='static_xl_export',hosted_execution_verified=False)
    write_json(out/'receipt.json',receipt)
    return receipt


def check_export(folder: Path, expected: dict) -> None:
    if {p.name for p in folder.iterdir() if p.is_file()}!=EXPORT_FILES:
        raise StudyError('Incomplete or unexpected export files: '+str(folder))
    for name,h in expected['artifact_sha256'].items():
        if text_hash(folder/name)!=h:
            raise StudyError('Returned artifact differs from its input: '+name)
    graph=read_json(folder/'structure_snapshot.json')
    if digest(graph)!=expected['graph_digest'] or text_hash(folder/'Model.rgg')!=expected['model_sha256']:
        raise StudyError('Export does not match its original input snapshot')
    m=read_json(folder/'export.json')
    if (m['model_sha256']!=file_hash(folder/'Model.rgg') or m['snapshot_sha256']!=file_hash(folder/'structure_snapshot.json')
            or m['session_id']!=expected['session_id'] or m['plant_id']!=graph['plant_id']
            or m.get('validated_metric') is not False or m.get('suitable_for_ppfd') is not False
            or m.get('groimp_open_verified') is not False or m.get('save_reopen_verified') is not False):
        raise StudyError('Export manifest is inconsistent or promotes diagnostic status')


def execute(bundle_root: Path) -> Path:
    """Run inside the extracted project. Existing complete plants can be resumed safely."""
    from tools.groimp_structure_export import export_plant
    bundle_root=bundle_root.resolve()
    if bundle_root!=ROOT.resolve():
        raise StudyError('Run the bundled module from the extracted bundle root')
    m=read_json(bundle_root/'bundle.json')
    if m['schema']!=SCHEMA or m['kind']!='input':
        raise StudyError('Wrong input bundle schema')
    for name,h in m['files'].items():
        if file_hash(bundle_root/name)!=h:
            raise StudyError('Bundled input or source changed: '+name)
    versions={p:importlib.metadata.version(p) for p in DEPENDENCIES}
    if versions!=m['dependencies']:
        raise StudyError('Dependency versions differ; install requirements-colab.txt first')
    work=bundle_root/'build/colab_job'
    work.mkdir(parents=True,exist_ok=True)
    relocations={}
    for plant in m['plants']:
        refs=m['provenance'][plant]
        h=read_json(bundle_root/refs['hierarchy']['bundle_path'])
        target=work/'relocated_run'/plant
        (target/'hierarchy').mkdir(parents=True,exist_ok=True)
        (target/'structure').mkdir(exist_ok=True)
        h['inputs']=dict(h['inputs'],backup=str(bundle_root/refs['backup']['bundle_path']),
                          structure=str(target/'structure'))
        # Source hierarchy remains untouched. Only this explicitly derived copy changes paths.
        write_json(target/'hierarchy/hierarchy.json',h)
        (target/'structure/structure.json').write_bytes((bundle_root/refs['structure']['bundle_path']).read_bytes())
        (target/'status.json').write_bytes((bundle_root/refs['status']['bundle_path']).read_bytes())
        relocations[plant]=dict(originals=refs,runtime_backup=h['inputs']['backup'],runtime_structure=h['inputs']['structure'],
                                derived_hierarchy_sha256=file_hash(target/'hierarchy/hierarchy.json'))
        destination=work/'exports'/plant
        if not destination.exists():
            export_plant(work/'relocated_run',plant,destination)
        check_export(destination,m['expected'][plant])
        print(f'{plant}: static export checked',flush=True)
    write_json(work/'relocation.json',relocations)
    write_json(work/'environment.json',dict(python=sys.version,platform=platform.platform(),cpu_count=os.cpu_count(),
        dependencies=versions,hosted_colab='COLAB_RELEASE_TAG' in os.environ,
        validated_metric=False,suitable_for_ppfd=False))
    files={p.relative_to(work/'exports').as_posix():p.read_bytes() for p in (work/'exports').rglob('*') if p.is_file()}
    files.update({name:(work/name).read_bytes() for name in ('relocation.json','environment.json')})
    result=dict(schema=SCHEMA,kind='result',operation='static_xl_export',plants=m['plants'],
                input_manifest_sha256=file_hash(bundle_root/'bundle.json'),
                files={k:sha(v) for k,v in files.items()},validated_metric=False,suitable_for_ppfd=False)
    files['result.json']=json_bytes(result)
    archive=work/f'tomato_colab_result_{time.time_ns()}.zip'
    zip_write(archive,files)
    print(str(archive),flush=True)
    return archive


def import_result(bundle: Path, result: Path, out: Path) -> dict:
    """Validate returned content before creating a new accepted import directory."""
    import tempfile
    original,_=verified_archive(bundle,'bundle.json')
    m,files=verified_archive(result,'result.json')
    if (original['schema']!=SCHEMA or original['kind']!='input' or m['schema']!=SCHEMA
            or m['kind']!='result' or m['plants']!=original['plants']
            or m['input_manifest_sha256']!=sha(archive_files(bundle)['bundle.json'])
            or m.get('validated_metric') is not False or m.get('suitable_for_ppfd') is not False):
        raise StudyError('Returned bundle identity or status mismatch')
    expected_names={f'{p}/{name}' for p in m['plants'] for name in EXPORT_FILES}|{'result.json','relocation.json','environment.json'}
    if set(files)!=expected_names:
        raise StudyError('Unexpected returned plant/files')
    # Temporary inspection stays within build; production output is created only after all checks.
    from tools.leaf_light.common import BUILD
    BUILD.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='colab_verify_',dir=BUILD) as tmp:
        tmp=Path(tmp)
        for name,data in files.items():
            p=tmp/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        for plant in m['plants']:
            check_export(tmp/plant,original['expected'][plant])
        out=output_dir(out)
        for name,data in files.items():
            p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    receipt=dict(status='import_verified',plants=m['plants'],input_zip_sha256=file_hash(bundle),
                 result_zip_sha256=file_hash(result),groimp_runtime_verification='required_separately',
                 validated_metric=False,suitable_for_ppfd=False)
    write_json(out/'import_receipt.json',receipt)
    return receipt


def notebook(path: Path, bundle_hash: str) -> None:
    import nbformat as nb
    cells=[nb.v4.new_markdown_cell('# 토마토 XL 내보내기 · Colab\n\n'
        '기존 기관 구조를 GroIMP용 정적 파일로 변환합니다. **학습·3D 재복원·PPFD 계산은 실행하지 않습니다.**\n\n'
        '런타임은 Python 3의 일반 CPU를 사용하세요. 위에서 아래로 실행하면 입력 ZIP 업로드 → 검증 → 내보내기 → 결과 다운로드 순으로 진행됩니다. '
        '실행을 다시 시작하면 같은 입력 ZIP을 다시 올릴 수 있습니다. [Colab 안내](https://research.google.com/colaboratory/faq.html)'),
        nb.v4.new_markdown_cell('## 1. 입력 ZIP 선택\n함께 받은 `tomato_colab_inputs.zip`을 선택하세요. Google Drive 전체 접근 권한은 필요하지 않습니다.'),
        nb.v4.new_code_cell('from pathlib import Path\nimport hashlib, json, zipfile, stat, sys, subprocess\n'
            'from google.colab import files\n'
            'preuploaded = Path("/content/tomato_colab_inputs.zip")\n'
            'if preuploaded.is_file():\n    bundle_data = preuploaded.read_bytes()\n'
            'else:\n    uploaded = files.upload()\n'
            '    if len(uploaded) != 1:\n        raise ValueError("입력 ZIP 하나만 선택하세요.")\n'
            '    bundle_data = next(iter(uploaded.values()))\n'
            f'EXPECTED_SHA256 = {bundle_hash!r}\n'
            'if hashlib.sha256(bundle_data).hexdigest() != EXPECTED_SHA256:\n    raise ValueError("입력 ZIP이 준비된 파일과 다릅니다.")\n'
            'print("입력 ZIP 확인 완료")'),
        nb.v4.new_markdown_cell('## 2. 파일 검증·실행 환경 준비\n전송된 스냅샷은 보존하고, Colab 경로를 사용하는 복사본을 만듭니다. 최초 실행에는 라이브러리 설치 시간이 필요합니다.'),
        nb.v4.new_code_cell('import io\nfrom pathlib import PurePosixPath\n'
            'workspace = Path("/content/tomato_xl")\n'
            'workspace.mkdir(parents=True, exist_ok=True)\n'
            'with zipfile.ZipFile(io.BytesIO(bundle_data)) as archive:\n'
            '    manifest = json.loads(archive.read("bundle.json"))\n'
            '    expected = manifest["files"]\n'
            '    names = archive.namelist()\n'
            '    if len(names) != len(set(names)) or set(names) != set(expected) | {"bundle.json"}:\n'
            '        raise ValueError("잘못된 ZIP 구성")\n'
            '    for name in names:\n'
            '        relative = PurePosixPath(name)\n'
            '        if relative.is_absolute() or ".." in relative.parts or "\\\\" in name or ":" in name:\n'
            '            raise ValueError("잘못된 ZIP 경로")\n'
            '        data = archive.read(name)\n'
            '        if name in expected and hashlib.sha256(data).hexdigest() != expected[name]:\n'
            '            raise ValueError("파일 검증 실패: " + name)\n'
            '        target = workspace / name\n'
            '        if target.exists() and target.read_bytes() != data:\n'
            '            raise ValueError("다른 실행 파일이 있습니다. 런타임을 새로 시작하세요.")\n'
            '        target.parent.mkdir(parents=True, exist_ok=True)\n'
            '        target.write_bytes(data)\n'
            'subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(workspace / "requirements-colab.txt")], check=True)\n'
            'print("준비된 개체:", ", ".join(manifest["plants"]))'),
        nb.v4.new_markdown_cell('## 3. XL 내보내기 실행\n이미 완료된 개체는 내용 일치 여부를 확인한 뒤 재사용합니다. 진단용 상태가 유지됩니다.'),
        nb.v4.new_code_cell('completed = subprocess.run([sys.executable, "-m", "tools.colab_xl_bridge", "run", "--root", str(workspace)],\n'
            '    cwd=workspace, check=True, text=True, capture_output=True)\n'
            'print(completed.stdout)\n'
            'result_path = Path(completed.stdout.strip().splitlines()[-1])\n'
            'assert result_path.is_file()'),
        nb.v4.new_markdown_cell('## 4. 결과 내려받기\n다운로드한 결과 ZIP을 Codex에 전달하면 원래 입력과 대조해 가져옵니다. GroIMP에서 열기·저장 검증은 로컬에서 별도로 수행합니다.'),
        nb.v4.new_code_cell('files.download(str(result_path))'),
        nb.v4.new_markdown_cell('## 확인 범위\n출력은 `Model.rgg`, 기관·관계·좌표 표, 출처·해시 기록입니다. '
            '이 작업은 치수 정확도를 개선하지 않으며 광 계산 완료를 뜻하지 않습니다. '
            'Colab에 접속한 실제 실행 여부는 결과의 `environment.json`과 실행 기록으로 구분합니다.')]
    book=nb.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'language_info':{'name':'python'},'colab':{'name':path.name}})
    nb.validate(book);nb.write(book,path)


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('pack');p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--plant',action='append')
    p=sub.add_parser('run');p.add_argument('--root',required=True,type=Path)
    p=sub.add_parser('import');p.add_argument('--bundle',required=True,type=Path);p.add_argument('--result',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=ap.parse_args(argv)
    if a.command=='pack':
        print(json.dumps(pack(a.run,a.out,a.plant),ensure_ascii=True))
    elif a.command=='run':
        execute(a.root)
    else:
        print(json.dumps(import_result(a.bundle,a.result,a.out),ensure_ascii=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
