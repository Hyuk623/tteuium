"""PC half of the heavy-compute offload: pack a job, send it to Kaggle, import the result (2026-09-28).

    python -X utf8 -m tools.offload_job pack   --plant P --session <edit_session> [--plant ... --session ...] --out <job>
    python -X utf8 -m tools.offload_job kaggle --job <job> [--cpu]          # upload + push + wait + download
    python -X utf8 -m tools.offload_job import --job <job> --result <downloaded> --plant P --session <edit_session> \\
                                              --labels <new labels dir> --batch <new batch dir>

Only S1 model drafts and S2 SAM masks leave the PC (design: handoff/CLAUDE_HEAVY_COMPUTE_OFFLOAD_DESIGN_2026-09-28.md).
The job carries prepared frames, the code that runs remotely, the weights' SHA-256 (weights travel once as the Kaggle
dataset tomato-offload-models) and the PC's SAM model signature, so the returned SAM results are cache entries of the
PC's own batch. Import accepts a result only when the job hash, plant set and every file hash match, and writes new
folders only. Kaggle upload/collection is Claude's column; Colab runs the same job through Codex's runner.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
JOB_SCHEMA = 'offload-job-1'
CODE = ['tools/__init__.py', 'tools/leaf_light/__init__.py', 'tools/leaf_light/common.py', 'tools/organ_prelabel.py',
        'tools/leaflet_segmenter.py', 'tools/leaflet_mask_batch.py', 'tools/plant_auto.py', 'tools/offload_remote.py']
KAGGLE_USER = 'dolgfish'
MODELS_DATASET = f'{KAGGLE_USER}/tomato-offload-models'
FRAME_KEYS = ('image_file', 'image_path', 'sha256', 'view_code', 'observed_view_group', 'pose_status', 'passes_pose_gate')


def pc_signature(sam_config: Path) -> dict:
    """The model signature the PC's mask batch will compute for this SAM config (cache keys depend on it)."""
    from tools import leaflet_mask_batch as lmb, leaflet_segmenter as seg
    probe = lmb.Batch.__new__(lmb.Batch)
    probe.segmenter = seg.load_segmenter('sam2', Path(sam_config))
    return lmb.Batch.model_signature(probe)


def pack(plants: dict[str, Path], out: Path, detectors: list[Path], sam_config: Path,
         tile_detectors: list[Path] | None = None, crop: bool = True, smoothing: str = 'none') -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    sam = read_json(sam_config)
    ckpt = Path(sam['checkpoint'])
    if file_hash(ckpt) != sam['checkpoint_sha256']:
        raise StudyError('SAM checkpoint differs from its config')
    for rel in CODE:
        (out / 'code' / rel).parent.mkdir(parents=True, exist_ok=True)
        if (ROOT / rel).exists():
            shutil.copy2(ROOT / rel, out / 'code' / rel)
        else:  # tools/ is a namespace package on the PC; an empty marker keeps imports identical remotely
            (out / 'code' / rel).write_text('', encoding='utf-8')
    for plant, session in plants.items():
        cap = read_json(Path(session) / 'capture.json')
        dst = out / 'inputs' / plant
        (dst / 'images').mkdir(parents=True)
        frames = []
        for f in cap['frames']:
            src = Path(session) / f['image_path']
            if file_hash(src) != f['sha256']:
                raise StudyError(f'prepared frame changed: {src}')
            shutil.copy2(src, dst / f['image_path'])
            frames.append({k: f.get(k) for k in FRAME_KEYS})
        write_json(dst / 'capture.json', dict(plant_id=cap['plant_id'], session_id=cap.get('session_id'), frames=frames,
                                              intrinsics=cap['intrinsics']))
    job = dict(schema=JOB_SCHEMA, job_id=f"{'-'.join(plants)}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
               plants=list(plants), created_at=datetime.now().isoformat(timespec='seconds'),
               detectors=[dict(name=p.name, sha256=file_hash(p), source=str(p)) for p in detectors],
               tile_detectors=[dict(name=p.name, sha256=file_hash(p), source=str(p)) for p in (tile_detectors or [])],
               crop=crop, smoothing=smoothing,
               sam=dict(checkpoint=dict(name=ckpt.name, sha256=sam['checkpoint_sha256'], source=str(ckpt)),
                        config={k: v for k, v in sam.items() if k not in ('checkpoint', 'repository', 'runtime')},
                        pc_config=str(sam_config), pc_signature=pc_signature(sam_config)),
               note='prepared frames only; no poses, labels of people, decisions or credentials')
    write_json(out / 'job.json', job)
    files = {str(p.relative_to(out)).replace('\\', '/'): file_hash(p) for p in sorted(out.rglob('*'))
             if p.is_file() and p.name != 'manifest.json'}
    write_json(out / 'manifest.json', dict(schema=JOB_SCHEMA, files=files))
    return job


def import_result(job_dir: Path, result_dir: Path, plant: str, session: Path, labels: Path, batch_dir: Path,
                  growth: Path | None = None, mask_model: Path | None = None) -> dict:
    """Verify a returned result, then build the PC's labels and batch from it; SAM results become cache hits."""
    from tools import leaflet_mask_batch as lmb, leaflet_segmenter as seg, plant_auto
    job_dir, result_dir = Path(job_dir), Path(result_dir)
    job = read_json(job_dir / 'job.json')
    res = read_json(result_dir / 'result.json')
    if res.get('schema') != 'offload-result-1' or res['job_id'] != job['job_id']:
        raise StudyError('Result belongs to another job')
    if res['job_manifest_sha256'] != file_hash(job_dir / 'manifest.json'):
        raise StudyError('Result was computed from a different job bundle')
    if plant not in res['plants'] or res['plants'][plant].get('status') != 'done':
        raise StudyError(f'{plant} is not finished in the result')
    bad = [rel for rel, digest in res['files'].items() if rel.startswith(plant + '/') and
           (not (result_dir / rel).is_file() or file_hash(result_dir / rel) != digest)]
    if bad:
        raise StudyError(f'Result files changed or missing: {bad[:5]}')
    capture = read_json(Path(session) / 'capture.json')
    pre = dict(out=str(result_dir / plant / 'prelabel'), per_class=res['plants'][plant]['prelabel']['per_class'])
    plant_auto.labels_from_prelabels(pre, capture, Path(session), Path(labels), growth)
    lmb.prepare(plant, Path(labels), Path(session), Path(batch_dir))
    sam_cfg = Path(job['sam']['pc_config'])
    batch = lmb.Batch(Path(batch_dir), seg.load_segmenter('sam2', sam_cfg))
    if batch.model_signature() != job['sam']['pc_signature']:
        raise StudyError('The PC SAM config changed since the job was packed')
    remote = read_json(result_dir / plant / 'items.json')
    local = {i: batch.item(i)['prompts'] for i in batch.manifest['ids']}
    if set(remote) != set(local) or any(remote[i]['prompts'] != local[i] for i in local):
        raise StudyError('Remote and PC batches disagree on items or prompts')
    copied = 0
    for i, r in remote.items():
        if r['cache_key']:
            dst = Path(batch_dir) / 'cache' / r['cache_key']
            if not dst.exists():
                shutil.copytree(result_dir / plant / 'cache' / r['cache_key'], dst)
                copied += 1
    batch.start(False, False)  # every ready remote item is a cache hit; only remote failures are computed here
    while batch.worker.is_alive():
        batch.worker.join(10)
    if mask_model:  # learned human review: only confident masks are accepted, the rest wait for a person
        from tools.decision_learning import apply_mask_model
        accepted = apply_mask_model(Path(batch_dir), Path(mask_model), plant)
    else:
        accepted = batch.auto_accept()
    record = dict(job_id=job['job_id'], plant=plant, computed_on=res.get('computed_on'), cache_entries_copied=copied,
                  remote_seconds=res['plants'][plant].get('seconds'), auto_accept=accepted,
                  result_dir=str(result_dir), imported_at=datetime.now().isoformat(timespec='seconds'))
    write_json(Path(batch_dir) / 'offload_import.json', record)
    return record


# ---------------- Kaggle transport (Claude's column)

NETWORK_ERRORS = ('NameResolutionError', 'Max retries exceeded', 'ConnectionError', 'Read timed out')


def _kaggle(*args, check=True, tries=6) -> str:
    for attempt in range(tries):  # this PC loses DNS for api.kaggle.com now and then; wait it out
        try:  # a download can hang with no error (09-28: 8 h on one output page), so every call has a time limit
            r = subprocess.run(['kaggle', *args], capture_output=True, text=True, encoding='utf-8', errors='replace',
                               env={**os.environ, 'PYTHONUTF8': '1'}, timeout=900)
            text, code = (r.stdout + r.stderr).strip(), r.returncode
        except subprocess.TimeoutExpired:
            text, code = 'Read timed out (no answer within 900 s)', 1
        if not any(e in text for e in NETWORK_ERRORS):
            break
        time.sleep(30 * (attempt + 1))
    if check and code != 0:
        raise StudyError(f'kaggle {" ".join(args[:2])} failed: {text[-500:]}')
    return text


def _dataset_exists(ref: str) -> bool:
    return any(w in _kaggle('datasets', 'status', ref, check=False).lower() for w in ('ready', 'pending', 'processing'))


def ensure_models_dataset(job: dict, stage: Path) -> None:
    """Weights travel once: the dataset holds each file by name; a new version is pushed only when a listed
    SHA-256 is missing from it (the remote side checks every hash again)."""
    want = job['detectors'] + job.get('tile_detectors', []) + [job['sam']['checkpoint']]
    record = ROOT / 'build' / 'offload' / 'models_uploaded.json'  # {name: {sha256, source}} of the latest version
    uploaded = read_json(record) if record.exists() else {}
    if _dataset_exists(MODELS_DATASET) and all(uploaded.get(w['name'], {}).get('sha256') == w['sha256'] for w in want):
        return
    # a new version replaces the old one, so it keeps every earlier weight whose file still exists (re-runnable jobs)
    files = {n: e for n, e in uploaded.items() if Path(e['source']).exists() and file_hash(Path(e['source'])) == e['sha256']}
    files.update({w['name']: dict(sha256=w['sha256'], source=w['source']) for w in want})
    stage.mkdir(parents=True)
    for name, e in files.items():
        shutil.copy2(e['source'], stage / name)
    shutil.copytree(ROOT / 'build' / 'leaflets4_20260927' / 'upload' / 'sam2pkg', stage / 'sam2pkg')
    write_json(stage / 'hashes.json', {n: e['sha256'] for n, e in files.items()})
    write_json(stage / 'dataset-metadata.json', dict(title='tomato offload models', id=MODELS_DATASET,
                                                    licenses=[dict(name='other')]))
    if _dataset_exists(MODELS_DATASET):
        _kaggle('datasets', 'version', '-p', str(stage), '-m', 'weights ' + job['job_id'], '-r', 'zip', '-q')
    else:
        _kaggle('datasets', 'create', '-p', str(stage), '-r', 'zip', '-q')
    write_json(record, files)


def wait_ready(dataset: str, minutes: int = 30) -> None:
    for _ in range(minutes * 4):
        if 'ready' in _kaggle('datasets', 'status', dataset, check=False):
            return
        time.sleep(15)
    raise StudyError(f'{dataset} not ready after {minutes} min')


KERNEL = '''# Heavy-compute offload runner (tools.offload_job, 2026-09-28). Finds the job and the weights, runs the same code
# the PC uses, writes everything under /kaggle/working. Re-pushing resumes finished plants from result.json.
import glob, json, os, shutil, subprocess, sys
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics", "hydra-core", "iopath"], check=True)
jobs = [p for p in glob.glob("/kaggle/input/**/job.json", recursive=True) if json.load(open(p)).get("schema") == "offload-job-1"]
assert len(jobs) == 1, f"expected one offload job, found {jobs}"
src = os.path.dirname(jobs[0]); job = "/kaggle/working/job"
if not os.path.exists(job): shutil.copytree(src, job)
models = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/hashes.json", recursive=True)]
assert models, "tomato-offload-models not attached"
try:
    import torch; print("device", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu", flush=True)
except Exception as e: print("torch", e)
r = subprocess.run([sys.executable, "-X", "utf8", f"{job}/code/tools/offload_remote.py", "--job", job, "--models", *models,
                    "--out", "/kaggle/working/result"])
shutil.rmtree(f"{job}/code/build", ignore_errors=True); shutil.rmtree(f"{job}/inputs", ignore_errors=True)
sys.exit(r.returncode)
'''


RUNNER = f'{KAGGLE_USER}/tomato-offload-runner'


def download_output(kernel: str, out: Path) -> int:
    """Every page of a kernel's output (the CLI returns at most 200 files per call; SAM caches hold hundreds)."""
    tokens, token = [None], None
    while True:
        text = _kaggle('kernels', 'files', kernel, '--page-size', '200', *(['--page-token', token] if token else []), check=False)
        m = re.search(r'Next Page Token = (\S+)', text)
        if not m:
            break
        token = m.group(1)
        tokens.append(token)
    for t in tokens:
        _kaggle('kernels', 'output', kernel, '-p', str(out), '--page-size', '200', '-q', *(['--page-token', t] if t else []),
                check=False)
    return len(tokens)


def kaggle_fetch(job_dir: Path) -> Path:
    """Collect (again) the runner's output for this job, e.g. after an interrupted download."""
    job_dir = Path(job_dir)
    out = job_dir.parent / f'{job_dir.name}_result'
    res = out / 'result' / 'result.json'
    complete = lambda: res.exists() and all((out / 'result' / f).is_file() for f in read_json(res)['files'])
    for _ in range(0 if complete() else 4):  # nothing to fetch when every listed file is already here  # a page can fail quietly when DNS drops; fetch again until every listed file is here
        download_output(RUNNER, out)
        missing = [f for f in read_json(res)['files'] if not (out / 'result' / f).is_file()] if res.exists() else None
        if missing:  # paging can skip files; ask for the rest by name (cache folder names are unique hashes)
            keys = sorted({f.split('/')[2] if '/cache/' in f else re.escape(Path(f).name) for f in missing})
            for i in range(0, len(keys), 40):
                _kaggle('kernels', 'output', RUNNER, '-p', str(out), '--page-size', '200', '-q',
                        '--file-pattern', '(' + '|'.join(keys[i:i + 40]) + ')', check=False)
            missing = [f for f in read_json(res)['files'] if not (out / 'result' / f).is_file()]
        if missing == []:
            break
        time.sleep(30)
    if not res.exists() or read_json(res).get('job_id') != read_json(job_dir / 'job.json')['job_id']:
        raise StudyError(f'The runner output in {out} is not a finished result of this job')
    return out / 'result'


def kaggle_run(job_dir: Path, gpu: bool = True, poll_s: int = 60, max_hours: float = 6) -> Path:
    job_dir = Path(job_dir)
    job = read_json(job_dir / 'job.json')
    slug = 'tomato-offload-job'
    stage = ROOT / 'build' / 'offload' / job['job_id']  # fresh per job: OneDrive can keep deleted folders locked
    ensure_models_dataset(job, stage / 'models')
    wait_ready(MODELS_DATASET)
    ds = stage / 'job'
    shutil.copytree(job_dir, ds)
    write_json(ds / 'dataset-metadata.json', dict(title='tomato offload job', id=f'{KAGGLE_USER}/{slug}', licenses=[dict(name='other')]))
    if _dataset_exists(f'{KAGGLE_USER}/{slug}'):
        _kaggle('datasets', 'version', '-p', str(ds), '-m', job['job_id'], '-r', 'zip', '-q')
    else:
        _kaggle('datasets', 'create', '-p', str(ds), '-r', 'zip', '-q')
    wait_ready(f'{KAGGLE_USER}/{slug}')
    kdir = stage / 'kernel'
    kdir.mkdir(parents=True)
    (kdir / 'run.py').write_text(KERNEL, encoding='utf-8')
    meta = dict(id=f'{KAGGLE_USER}/tomato-offload-runner', title='tomato offload runner', code_file='run.py', language='python',
                kernel_type='script', is_private=True, enable_gpu=gpu, enable_tpu=False, enable_internet=True,
                dataset_sources=[f'{KAGGLE_USER}/{slug}', MODELS_DATASET], kernel_sources=[], competition_sources=[],
                model_sources=[])
    if gpu:
        meta['machine_shape'] = 'NvidiaTeslaT4'  # a P100 fails with the current torch build
    write_json(kdir / 'kernel-metadata.json', meta)
    log = job_dir.parent / f'{job_dir.name}_kaggle.log'
    for _ in range(int(max_hours * 3600 / 180)):
        text = _kaggle('kernels', 'push', '-p', str(kdir), check=False)
        with open(log, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now():%H:%M:%S} push: {text.splitlines()[-1] if text else ''}\n")
        if 'successfully pushed' in text:
            break
        time.sleep(180)  # GPU session limit or network: retry
    else:
        raise StudyError('Could not push the offload runner')
    started = time.time()
    while time.time() - started < max_hours * 3600:
        time.sleep(poll_s)
        s = _kaggle('kernels', 'status', f'{KAGGLE_USER}/tomato-offload-runner', check=False)
        with open(log, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now():%H:%M:%S} {s.splitlines()[-1] if s else ''}\n")
        if 'COMPLETE' in s or 'ERROR' in s or 'CANCEL' in s:
            break
    if 'COMPLETE' not in s:
        raise StudyError(f'Kaggle run ended without a result ({s.splitlines()[-1] if s else "no status"})')
    return kaggle_fetch(job_dir)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('pack')
    p.add_argument('--plant', action='append', required=True)
    p.add_argument('--session', action='append', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--models', nargs='+', type=Path)
    p.add_argument('--sam-config', type=Path)
    k = sub.add_parser('kaggle')
    k.add_argument('--job', required=True, type=Path)
    k.add_argument('--cpu', action='store_true')
    i = sub.add_parser('import')
    for name in ('job', 'result', 'session', 'labels', 'batch'):
        i.add_argument('--' + name, required=True, type=Path)
    i.add_argument('--plant', required=True)
    i.add_argument('--growth', type=Path)
    a = ap.parse_args()
    from tools import plant_auto
    if a.cmd == 'pack':
        if len(a.plant) != len(a.session):
            ap.error('one --session per --plant')
        r = pack(dict(zip(a.plant, a.session)), a.out, a.models or [ROOT / m for m in plant_auto.DEFAULT_MODELS],
                 a.sam_config or ROOT / plant_auto.DEFAULT_SAM)
    elif a.cmd == 'kaggle':
        r = dict(result=str(kaggle_run(a.job, gpu=not a.cpu)))
    else:
        r = import_result(a.job, a.result, a.plant, a.session, a.labels, a.batch, a.growth)
    print(json.dumps(r, ensure_ascii=False, default=str)[:3000])


if __name__ == '__main__':
    main()
