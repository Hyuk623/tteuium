"""Remote half of the heavy-compute offload (Kaggle or Colab; the same file runs locally in tests).

    python tools/offload_remote.py --job <folder with job.json> --models <folder(s) holding the weights> --out <work>

Per plant in the job: model drafts (tools.organ_prelabel, detector ensemble + flips + stem/petiole instance masks),
then SAM leaflet masks through the very same tools.leaflet_mask_batch code the PC uses. The batch is keyed with the
PC's model signature carried in the job, so the returned cache entries are cache hits on the PC; the device that
actually computed them is recorded next to them (result.json -> computed_on). Nothing here reads a board pose,
writes a decision, or uses an untuned model: every weight is checked against the SHA-256 listed in the job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))  # job/code on the remote machine, the project root locally

from tools.leaf_light import common  # noqa: E402

RESULT_SCHEMA = 'offload-result-1'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def find_weights(entries: list[dict], roots: list[Path]) -> dict:
    """{name: path} for every listed weight, found by file name under the roots and accepted only by SHA-256."""
    found = {}
    for e in entries:
        hits = [p for r in roots for p in Path(r).rglob(e['name']) if p.is_file()]
        ok = [p for p in hits if sha(p) == e['sha256']]
        if not ok:
            raise common.StudyError(f"weight {e['name']} with sha256 {e['sha256'][:12]} not found under {roots}")
        found[e['name']] = ok[0]
    return found


def device() -> str:
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except ImportError:
        return 'cpu'


def run(job_dir: Path, model_roots: list[Path], out: Path, only_s1: bool = False) -> dict:
    from tools import organ_prelabel, leaflet_mask_batch as lmb, leaflet_segmenter as seg, plant_auto
    job_dir, out = Path(job_dir), Path(out)
    job = common.read_json(job_dir / 'job.json')
    manifest = common.read_json(job_dir / 'manifest.json')
    for rel, digest in manifest['files'].items():
        if sha(job_dir / rel) != digest:
            raise common.StudyError(f'job file changed in transit: {rel}')
    weights = find_weights(job['detectors'] + [job['sam']['checkpoint']], model_roots)
    dev = device()
    sam_cfg = dict(job['sam']['config'], checkpoint=str(weights[job['sam']['checkpoint']['name']]),
                   repository=str(next(p.parent.parent for r in model_roots for p in Path(r).rglob('sam2_image_predictor.py'))),
                   runtime=None, device=dev)
    out.mkdir(parents=True, exist_ok=True)
    res_path = out / 'result.json'
    result = common.read_json(res_path) if res_path.exists() else dict(
        schema=RESULT_SCHEMA, job_id=job['job_id'], job_manifest_sha256=sha(job_dir / 'manifest.json'), plants={})
    result['computed_on'] = dict(device=dev, python=sys.version.split()[0], platform=platform.platform(),
                                 gpu=_gpu_name() if dev == 'cuda' else None)
    for plant in job['plants']:
        if result['plants'].get(plant, {}).get('status') == 'done':
            continue  # resume after a lost session
        t0 = time.time()
        pdir = out / plant
        shutil.rmtree(pdir, ignore_errors=True)
        session = job_dir / 'inputs' / plant  # capture.json (frames subset) + images/
        capture = common.read_json(session / 'capture.json')
        images = [session / f['image_path'] for f in capture['frames']]
        pre = organ_prelabel.run([weights[d['name']] for d in job['detectors']], images, pdir / 'prelabel')
        t1 = time.time()
        entry = dict(status='drafts_only', prelabel=dict(per_class=pre['per_class'], boxes=pre['boxes']),
                     seconds=dict(drafts=round(t1 - t0, 1)))
        if not only_s1:
            # the batch must live under common.BUILD (its output rule); it is a scratch copy on the remote side
            scratch = common.BUILD / 'offload_scratch' / plant
            shutil.rmtree(scratch, ignore_errors=True)
            labels = scratch / 'labels'
            plant_auto.labels_from_prelabels(pre, capture, session, labels, None, seed=False)
            lmb.prepare(plant, labels, session, scratch / 'masks')
            batch = lmb.Batch(scratch / 'masks', seg.Sam2Segmenter(sam_cfg, common.ROOT))
            signature = job['sam']['pc_signature']
            batch.model_signature = lambda: signature  # PC keys; computed_on says where they were made
            batch.start(False, False)
            while batch.worker.is_alive():
                batch.worker.join(10)
            status = batch.status()
            items = {}
            (pdir / 'cache').mkdir(parents=True)
            for identity in batch.manifest['ids']:
                it = batch.item(identity)
                items[identity] = dict(prompts=it['prompts'], generation=it['generation'], cache_key=it['cache_key'],
                                       error=it['error'])
                if it['cache_key']:
                    dst = pdir / 'cache' / it['cache_key']
                    if not dst.exists():
                        shutil.copytree(scratch / 'masks' / 'cache' / it['cache_key'], dst)
            common.write_json(pdir / 'items.json', items)
            entry.update(status='done', masks=dict(ready=sum(i['generation'] == 'ready' for i in items.values()),
                                                   failed=sum(i['generation'] == 'failed' for i in items.values()),
                                                   batch_status=status.get('counts', status)),
                         seconds=dict(entry['seconds'], sam=round(time.time() - t1, 1)))
        else:
            entry['status'] = 'done'
        result['plants'][plant] = entry
        result['files'] = {str(p.relative_to(out)).replace('\\', '/'): sha(p) for p in out.rglob('*')
                           if p.is_file() and p.name != 'result.json'}
        common.write_json(res_path, result)  # after every plant, so a re-run resumes
    return result


def _gpu_name():
    try:
        import torch
        return torch.cuda.get_device_name(0)
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--job', required=True, type=Path)
    ap.add_argument('--models', required=True, type=Path, nargs='+')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--only-s1', action='store_true', help='drafts only, no SAM (for a quick check)')
    a = ap.parse_args()
    r = run(a.job, a.models, a.out, a.only_s1)
    print(json.dumps({k: v for k, v in r.items() if k != 'files'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
