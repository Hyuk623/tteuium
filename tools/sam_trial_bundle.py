"""Build a portable Colab replay notebook and hashed photo/prompt/code ZIP.

python -m tools.sam_trial_bundle --manifest build/.../prompts.json
  --manifest build/.../organ_prompts.json --run-metadata build/.../run.json
  --out build/.../colab
This prepares files locally; it does not upload photographs or run a cloud GPU.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
from pathlib import Path
import textwrap
import zipfile

from tools.leaf_light.common import ROOT, StudyError, file_hash, output_dir, read_json, write_json


def collect_payload(manifests: list[Path]) -> dict[str, bytes]:
    """Copy exact source pixels; rebase references without changing their hashes."""
    payload={}
    names=set()
    for path in manifests:
        if path.name in names: raise StudyError('Manifest names must be distinct')
        names.add(path.name);manifest=copy.deepcopy(read_json(path))
        for case in manifest['cases']:
            source=(path.parent/case['image_file']).resolve()
            if file_hash(source)!=case['image_sha256']: raise StudyError('Source image hash mismatch')
            relative='images/'+case['image_sha256'][:12]+'_'+source.name
            content=source.read_bytes()
            if relative in payload and payload[relative]!=content: raise StudyError('Image name collision')
            payload[relative]=content;case['image_file']=relative
        import json
        payload[path.name]=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    for relative in ('tools/sam_leaf_trial.py','tools/leaf_light/common.py'):
        payload[relative]=(ROOT/relative).read_bytes()
    for relative in ('tools/__init__.py','tools/leaf_light/__init__.py'):
        payload[relative]=b''
    return payload


def notebook(archive_name: str, archive_sha256: str) -> object:
    import nbformat as nbf
    cells=[]
    def md(source: str) -> None: cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(source).strip()))
    def code(source: str) -> None: cells.append(nbf.v4.new_code_cell(textwrap.dedent(source).strip()))
    md('''
    # Tomato SAM: leaves, stem and petiole — Colab replay

    **사용법:** Colab에 이 노트북을 열고 **런타임 → 런타임 유형 변경 → GPU**를 선택하세요.
    셀을 위에서부터 실행하고, 파일 선택 창에서 함께 제공된 ZIP을 올리세요.
    ZIP에는 실제 사진 3장과 시험용 클릭·박스가 들어 있습니다.

    This is a pretrained **SAM 2.1 Tiny** interactive segmentation trial, not training.
    It replays leaflet, visible-main-stem and petiole prompts. Boxes and include/exclude
    points are supplied by a person/assistant; class names are not automatic classifications.
    Mask confidence is not measured accuracy. Review every mask before using it as a label.

    Local CPU results: boxes helped touching/folded leaflet examples and visible stem selection.
    Petiole boundaries retained noise; crowded leaves remained ambiguous. No held-out manual
    masks exist. Node candidates are a separate manual review artifact, not a SAM output.
    There is no verified internode length, 3D reconstruction, cross-view tracking or PPFD here.
    ''')
    md('''
    ## 1. Load the trial ZIP

    Running the upload cell in Colab copies the supplied photos into your Colab runtime.
    No Google Drive connection is required. The ZIP is verified before its code is imported.
    Local replay can set `SAM_TRIAL_ARCHIVE` to the ZIP and `SAM_TRIAL_WORKDIR` to a new
    directory. Files and hashes are kept in `bundle_manifest.json`.
    ''')
    code(f'''
    from pathlib import Path
    import hashlib, importlib.util, json, os, subprocess, sys, zipfile
    from datetime import datetime, timezone
    try:
        IN_COLAB = importlib.util.find_spec("google.colab") is not None
    except ModuleNotFoundError:
        IN_COLAB = False
    ARCHIVE_NAME = {archive_name!r}
    ARCHIVE_SHA256 = {archive_sha256!r}
    archive = Path(os.environ.get("SAM_TRIAL_ARCHIVE", ARCHIVE_NAME)).resolve()
    if not archive.exists() and IN_COLAB:
        from google.colab import files
        uploaded = files.upload()
        if ARCHIVE_NAME not in uploaded:
            raise ValueError("Upload " + ARCHIVE_NAME)
        archive = Path(ARCHIVE_NAME).resolve()
        del uploaded
    def sha256(path):
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    if sha256(archive) != ARCHIVE_SHA256:
        raise ValueError("ZIP hash mismatch; use the ZIP paired with this notebook")
    workdir = Path(os.environ.get("SAM_TRIAL_WORKDIR", "sam_tomato_workspace")).resolve()
    bundle = workdir / "sam_tomato_trial"
    workdir.mkdir(parents=True, exist_ok=True)
    if not bundle.exists():
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                if not (workdir / member.filename).resolve().is_relative_to(bundle):
                    raise ValueError("Unsafe ZIP path")
            package.extractall(workdir)
    metadata = json.loads((bundle / "bundle_manifest.json").read_text())
    for relative, expected in metadata["files_sha256"].items():
        if sha256(bundle / relative) != expected:
            raise ValueError("Modified/missing bundle file: " + relative)
    print("Verified", len(metadata["files_sha256"]), "files; manifests:", metadata["manifests"])
    ''')
    md('''
    ## 2. Prepare the model

    This downloads Meta's pinned source and a ~156 MB checkpoint, then verifies both.
    Colab normally supplies PyTorch, TorchVision, NumPy, Pillow and OpenCV. Missing base
    packages are reported, not silently replaced. The small Hydra/iopath dependencies are
    installed in a private directory. No custom CUDA extension or hole-filling is used.

    Local verification reused installed CPU dependencies through `SAM_TRIAL_REPOSITORY`,
    `SAM_TRIAL_RUNTIME`, and `SAM_TRIAL_CHECKPOINT`. The Colab download/install and GPU
    branches still need a real Colab run; CPU execution does not validate GPU performance.
    ''')
    code('''
    runtime = Path(os.environ.get("SAM_TRIAL_RUNTIME", bundle / "build/runtime")).resolve()
    repository = Path(os.environ.get("SAM_TRIAL_REPOSITORY", bundle / "build/vendor/sam2")).resolve()
    checkpoint = Path(os.environ.get("SAM_TRIAL_CHECKPOINT", bundle / "build/checkpoints/sam2.1_hiera_tiny.pt")).resolve()
    if not (runtime / "hydra").exists() or not (runtime / "iopath").exists():
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--target", str(runtime),
                               "hydra-core==1.3.2", "iopath==0.1.10"])
    if not repository.exists():
        repository.mkdir(parents=True)
        subprocess.check_call(["git", "init", "--quiet", str(repository)])
        subprocess.check_call(["git", "-C", str(repository), "remote", "add", "origin", metadata["repository_url"]])
        subprocess.check_call(["git", "-C", str(repository), "fetch", "--quiet", "--depth", "1", "origin", metadata["repository_commit"]])
        subprocess.check_call(["git", "-C", str(repository), "checkout", "--quiet", "--detach", "FETCH_HEAD"])
    revision = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    if revision != metadata["repository_commit"]:
        raise ValueError("Unexpected SAM source revision")
    if not checkpoint.exists():
        import urllib.request
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        partial = checkpoint.with_suffix(".part")
        urllib.request.urlretrieve(metadata["checkpoint_url"], partial)
        if sha256(partial) != metadata["checkpoint_sha256"]:
            raise ValueError("Downloaded checkpoint hash mismatch")
        partial.replace(checkpoint)
    if sha256(checkpoint) != metadata["checkpoint_sha256"]:
        raise ValueError("Checkpoint hash mismatch")
    sys.path.insert(0, str(runtime))
    sys.path.insert(0, str(bundle))
    try:
        import torch, torchvision, cv2, numpy, PIL
    except ImportError as exc:
        raise RuntimeError("Select a current Colab GPU runtime with PyTorch/TorchVision/OpenCV/Pillow/NumPy") from exc
    from packaging.version import Version
    if Version(torch.__version__.split('+')[0]) < Version('2.5.1'):
        raise RuntimeError("SAM 2.1 needs PyTorch >= 2.5.1")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print('PyTorch:', torch.__version__, '| Device:', device)
    if device == 'cpu':
        print('CPU fallback: image encoding is slower; this is not a GPU benchmark.')
    ''')
    md('''
    ## 3. Inspect the prompts and run

    Every point uses full-resolution, upright image pixels: label `1` includes, `0` excludes.
    Boxes are `[left, top, right, bottom]`. A box is a prompt, not a hard clipping boundary.
    `refinement_prompts.json` was chosen after inspecting the first trial, so it is adaptive
    correction, not an independent evaluation. All three model candidates are saved.

    Each run gets a new output directory. Later clicks normally reuse the image embedding;
    this replay groups prompts within each manifest. Human labeling time is not measured.
    ''')
    code('''
    for name in metadata['manifests']:
        manifest = json.loads((bundle / name).read_text())
        for case in manifest['cases']:
            print(name, '|', case['case_id'], '|', case.get('target_class', 'leaflet'), '|',
                  ', '.join(trial['trial_id'] for trial in case['trials']))
    ''')
    code('''
    from argparse import Namespace
    from tools.sam_leaf_trial import run
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    run_root = bundle / 'build' / ('replay_' + stamp)
    results = []
    for name in metadata['manifests']:
        out = run_root / Path(name).stem
        result = run(Namespace(manifest=bundle/name, repository=repository, runtime=runtime,
                               checkpoint=checkpoint, out=out, threads=4, device=device,
                               model_config=metadata['model_config']))
        results.append((name, out, result))
    print('Outputs:', run_root)
    ''')
    md('''
    ## 4. Review the masks

    The sheets show the **complete inference crop**, not just a favorable close-up.
    Cyan is the predicted mask; yellow is its contour; green/red points include/exclude;
    blue is the prompt box. The displayed candidate is selected by the model score.
    Inspect the other candidates and full-resolution masks in each output directory.
    ''')
    code('''
    import csv, html
    from IPython.display import Image as DisplayImage, HTML, display
    for name, out, result in results:
        display(HTML('<h3>' + html.escape(name) + '</h3>'))
        display(DisplayImage(filename=str(out/'comparison_full.jpg'), width=1200))
        with (out/'metrics.csv').open(newline='', encoding='utf-8') as stream:
            records = [row for row in csv.DictReader(stream) if row['top_model_score']=='True']
        columns = ['case_id','trial_id','predicted_iou','encoder_seconds','inference_seconds']
        head = ''.join('<th>'+html.escape(key)+'</th>' for key in columns)
        body = ''.join('<tr>'+''.join('<td>'+html.escape(row[key] if key.endswith('_id') else f'{float(row[key]):.3f}')+'</td>' for key in columns)+'</tr>' for row in records)
        display(HTML('<table><tr>'+head+'</tr>'+body+'</table>'))
    ''')
    md('''
    ## 5. Save and next steps

    Download the ZIP below from Colab's file pane (folder icon) after this cell.
    It contains full-resolution masks, contour CSVs, prompt/run metadata and review images.
    `predicted_iou` is **not a measured IoU**; `measured_iou` stays unavailable.

    For internodes: review the main stem and mark actual petiole attachment nodes in multiple
    views. Link consecutive **confirmed** nodes; do not infer hidden nodes from a mask.
    Metric length needs valid calibrated 3D correspondences. Leaf contour vertex indices
    are not anatomical correspondences. Review class identities and save human decisions
    separately before these predictions become training labels.

    Source: [Meta SAM 2](https://github.com/facebookresearch/sam2),
    [image predictor](https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py).
    ''')
    code('''
    import shutil
    result_zip = Path(shutil.make_archive(str(run_root), 'zip', root_dir=run_root))
    print('Download:', result_zip)
    print('Device used:', device, '| no metric 3D / PPFD / automatic node detection performed')
    ''')
    result=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'},'colab':{'name':'SAM_Tomato_Colab.ipynb'},'accelerator':'GPU'})
    nbf.validate(result)
    return result


def build(args: argparse.Namespace) -> dict:
    import json
    import nbformat
    payload=collect_payload(args.manifest)
    run=read_json(args.run_metadata)
    metadata=dict(schema_version='sam-colab-bundle-1',manifests=[p.name for p in args.manifest],
                  repository_url='https://github.com/facebookresearch/sam2.git',repository_commit=run['repository_commit'],
                  checkpoint_url='https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt',
                  checkpoint_sha256=run['checkpoint_sha256'],model_config=run['model_config'],
                  files_sha256={k:hashlib.sha256(v).hexdigest() for k,v in payload.items()})
    payload['bundle_manifest.json']=(json.dumps(metadata,indent=2)+'\n').encode()
    folder=output_dir(args.out);archive=folder/'sam_tomato_trial_inputs.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as package:
        for name,content in payload.items(): package.writestr('sam_tomato_trial/'+name,content)
    nb=notebook(archive.name,file_hash(archive))
    nbformat.write(nb,folder/'SAM_Tomato_Colab.ipynb')
    write_json(folder/'package.json',dict(archive_sha256=file_hash(archive),notebook='SAM_Tomato_Colab.ipynb',
                                        cloud_execution='not_run',files=len(payload)))
    return {'out':str(folder),'archive_bytes':archive.stat().st_size}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,action='append',required=True)
    parser.add_argument('--run-metadata',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    print(build(parser.parse_args()))


if __name__=='__main__': main()
