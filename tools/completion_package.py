"""Pack only permitted model inputs and isolated code; never upload automatically."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json
from tools.multiview_completion import resolve, verify_prepared
from tools.completion_viewfusion import REVISION, verify_package

ROOT = Path(__file__).resolve().parents[1]
CODE = ('tools/leaf_light/common.py', 'tools/multiview_completion.py',
        'tools/completion_viewfusion.py', 'tools/completion_package.py')


def pack(prepared: Path, vendor: Path, out: Path) -> dict:
    request, manifest = verify_prepared(prepared)
    verify_package(prepared/'backend_request.json')
    metadata = read_json(vendor/'source_manifest.json')
    if metadata['revision'] != REVISION:
        raise StudyError('Uninspected vendor revision')
    folder = output_dir(out)
    package = folder/'payload';package.mkdir()
    shutil.copyfile(prepared/'backend_request.json',package/'backend_request.json')
    for asset in request['assets']:
        source = resolve(prepared,asset['path'])
        target = resolve(package,asset['path'])
        if not target.is_relative_to(package.resolve()):
            raise StudyError('Input package path escapes destination')
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        if file_hash(target) != asset['sha256']:
            raise StudyError('Input changed while packing')
    for name in CODE:
        target = package/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    for name in ('tools/__init__.py','tools/leaf_light/__init__.py'):
        (package/name).write_text('',encoding='utf-8')
    for name, expected in metadata['files'].items():
        source = resolve(vendor,name)
        target = resolve(package/'vendor/ViewFusion',name)
        if not source.is_relative_to(vendor.resolve()) or not target.is_relative_to((package/'vendor/ViewFusion').resolve()):
            raise StudyError('Invalid vendor path')
        if file_hash(source) != expected:
            raise StudyError('Vendor source changed')
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    shutil.copyfile(vendor/'source_manifest.json',package/'vendor/ViewFusion/source_manifest.json')
    # A supplied GPU runtime executes explicitly. No package import installs dependencies.
    runner = '''from pathlib import Path
from tools.completion_viewfusion import main
if __name__ == "__main__":
    main()
'''
    (package/'run_trial.py').write_text(runner,encoding='utf-8')
    readme = '''# Isolated ViewFusion trial package

This package contains only declared conditioning inputs. Evaluation photographs,
the all-view capture and historical outputs are excluded. No model has run merely
because this archive exists. Do not upload without the user's destination authorization.

Use a dedicated Python 3.11 CUDA environment. Install the official ViewFusion/Zero123
runtime dependencies in that environment, never into the existing local program.
The dependency setup still requires an actual GPU smoke test; this package does
not claim verified installation. Supply the explicitly selected official Zero123
105000.ckpt checkpoint separately. The loader requires tensor-only checkpoint loading.

From the extracted payload root:

    python run_trial.py --request backend_request.json --vendor vendor/ViewFusion --checkpoint /path/to/105000.ckpt --out build/trial_01

Budgets and seeds are frozen in backend_request.json. Outputs stay in the new build
directory. A failed run writes status.json; a completed run writes candidate_bundle.json
and generated views. Preserve the entire output directory when returning results.
Images are novel-view hypotheses, not physical leaf surfaces or optical inputs.
The selected real camera poses failed their original quality gates; no metric
projection is validated. Never relabel that state to obtain a passing score.
'''
    (package/'README.md').write_text(readme,encoding='utf-8')
    files={str(p.relative_to(package)).replace('\\','/'):file_hash(p)
           for p in sorted(package.rglob('*')) if p.is_file()}
    result=dict(schema='completion-execution-package-1',request_sha256=manifest['request_sha256'],
                files=files,included_condition_images=[v['image_id'] for v in request['observations']],
                backend_executed=False,uploaded=False,runtime_installation_verified=False)
    write_json(package/'package_manifest.json',result)
    archive=folder/'execution_package.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(package.rglob('*')):
            if path.is_file():z.write(path,str(path.relative_to(package)).replace('\\','/'))
    result.update(archive=str(archive),archive_sha256=file_hash(archive),archive_bytes=archive.stat().st_size)
    write_json(folder/'package_audit.json',result)
    return result


TARGET_KEYS = ('target_id','source','model_pose_polar_azimuth_radius','passes_pose_gate')
PRIVATE_NAMES = ('request.snapshot.json','audit.json','.csv')


def verify_archive(archive: Path) -> dict:
    """Verify the exact transfer inventory without extracting or changing inputs."""
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise StudyError('Duplicate archive member')
        for name in names:
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                    or str(path) != name or z.getinfo(name).is_dir()):
                raise StudyError('Unsafe archive member')
        manifest = json.loads(z.read('package_manifest.json'))
        if manifest.get('schema') != 'completion-execution-package-1':
            raise StudyError('Unsupported archive manifest')
        declared = manifest['files']
        if set(names) != set(declared) | {'package_manifest.json'}:
            raise StudyError('Archive inventory differs from manifest')
        for name, expected in declared.items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise StudyError(f'Archive member hash mismatch: {name}')
        request = json.loads(z.read('backend_request.json'))
        if manifest['request_sha256'] != request['source_request_sha256']:
            raise StudyError('Archive request provenance mismatch')
        conditions = [v['image_id'] for v in request['observations']]
        if (any(v['role'] != 'condition' for v in request['observations'])
                or len(conditions) != len(set(conditions))
                or conditions != manifest['included_condition_images']):
            raise StudyError('Archive condition inventory mismatch')
        assets = request['assets']
        paths = [a['path'] for a in assets]
        ids = [a['asset_id'] for a in assets]
        if len(paths) != len(set(paths)) or len(ids) != len(set(ids)):
            raise StudyError('Duplicate archive input identity')
        if set(paths) != {n for n in names if n.startswith('inputs/')}:
            raise StudyError('Archive inputs differ from declared assets')
        for asset in assets:
            if declared.get(asset['path']) != asset['sha256']:
                raise StudyError('Archive input hash declaration mismatch')
            if not set(asset['source_image_ids']).issubset(conditions):
                raise StudyError('Forbidden archive input provenance')
            if not set(asset['parent_asset_ids']).issubset(ids):
                raise StudyError('Missing archive dependency')
    return dict(schema='completion-archive-verification-1', status='verified',
                archive_sha256=file_hash(archive), verified_members=len(declared),
                condition_image_ids=conditions, backend_execution_verified=False)


def verify_arm_isolation(contract: dict, archives: dict[str, Path]) -> dict:
    """Check transfer archives against a common evaluation contract before upload.

    Every arm must carry exactly the contract target list, no archive may hold a
    held-out image or evaluator file, and each arm excludes its forbidden images
    and anything whose provenance derives from them.
    """
    expected = [{k:t[k] for k in TARGET_KEYS} for t in contract['targets']]
    if set(archives) != set(contract['arms']):
        raise StudyError('Archive set does not match contract arms')
    report = {}
    for arm, archive in archives.items():
        forbidden = set(contract['heldout_image_ids']) | set(contract['arms'][arm].get('forbidden_image_ids', []))
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            request_text = z.read('backend_request.json').decode('utf-8')
        request = json.loads(request_text)
        targets = [{k:t.get(k) for k in TARGET_KEYS} for t in request.get('targets', [])]
        if targets != expected:
            raise StudyError(f'Target list differs from contract: {arm}')
        declared_ids = {v['image_id'] for v in request['observations']}
        for asset in request['assets']:
            declared_ids.update([asset['asset_id'], *asset['source_image_ids']])
        path_ids = {part for name in names for part in PurePosixPath(name).parts}
        path_ids.update(PurePosixPath(part).stem for part in tuple(path_ids))
        leaked = sorted(forbidden & (declared_ids | path_ids))
        derived = sorted(a['asset_id'] for a in request['assets'] if set(a['source_image_ids']) & forbidden)
        private = sorted(n for n in names if n.endswith(PRIVATE_NAMES))
        if leaked or derived or private:
            raise StudyError(f'Forbidden content in {arm}: {leaked + derived + private}')
        conditions = sorted(v['image_id'] for v in request['observations'])
        if conditions != sorted(contract['arms'][arm]['condition_image_ids']):
            raise StudyError(f'Condition images differ from contract: {arm}')
        sampler = contract['sampler']
        budget = request['budgets']
        expected_budget = dict(seeds=contract['seeds'], steps=sampler['steps'],
                               max_wall_time_s=sampler['max_wall_time_s_per_arm'])
        if any(budget.get(k) != v for k,v in expected_budget.items()):
            raise StudyError(f'Seed or sampler budget differs from contract: {arm}')
        expected_parameters = {k:sampler[k] for k in ('guidance_scale','ddim_eta','autocast')}
        if request['backend'].get('parameters') != expected_parameters:
            raise StudyError(f'Sampler parameters differ from contract: {arm}')
        if any(request['backend'].get(k) != sampler[k] for k in ('checkpoint','checkpoint_sha256')):
            raise StudyError(f'Checkpoint differs from contract: {arm}')
        if contract['arms'][arm].get('condition_weights') != 'equal':
            raise StudyError('Only the declared equal-condition-weight contract is supported')
        for target in request['targets']:
            weights = target.get('condition_weights', [])
            if (len(weights) != len(conditions) or not weights
                    or any(type(w) not in (int,float) or not math.isfinite(w) or w<=0 for w in weights)
                    or any(w != weights[0] for w in weights)):
                raise StudyError(f'Condition weights differ from equal rule: {arm}')
        integrity = verify_archive(archive)
        report[arm] = dict(archive_sha256=file_hash(archive), condition_image_ids=conditions,
                           forbidden_image_ids=sorted(forbidden), target_ids=[t['target_id'] for t in targets],
                           members=len(names), verified_members=integrity['verified_members'])
    return dict(schema='completion-arm-isolation-1', status='isolated_with_identical_targets', arms=report)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--vendor',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=pack(args.prepared,args.vendor,args.out)
    print({k:result[k] for k in ('archive','archive_bytes','backend_executed','uploaded')})


if __name__=='__main__':
    main()
