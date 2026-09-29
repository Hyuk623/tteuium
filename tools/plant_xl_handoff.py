"""Finish an existing S0-S7 run with traceable static XL export and optional GroIMP checks.

python -m tools.plant_xl_handoff --run build/pipeline_TIMESTAMP --out build/xl_TIMESTAMP
Add --core ../groimp/core.jar to verify compilation, reset, save and reopen locally.
No reconstruction, inference, label modification or upstream status rewrite is performed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from tools.groimp_structure_export import export_plant, load_snapshot, text_json
from tools.groimp_static_verify import verify
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json


def prepare(run: Path, out: Path, plants: list[str] | None = None,
            core: Path | None = None, java: str = 'java') -> dict:
    """Export all requested plants, retain upstream gates, and report partial failure."""
    run = run.resolve()
    names = plants if plants is not None else sorted(p.parent.name for p in run.glob('*/status.json'))
    if not names or len(names) != len(set(names)):
        raise StudyError('No plant statuses found or duplicate plants requested')
    out = output_dir(out)
    report = dict(schema='pipeline-xl-handoff-1', run=str(run), plants={},
                  validated_metric=False, suitable_for_ppfd=False,
                  scope='static diagnostic transport; not completed reconstruction')
    for name in names:
        entry = dict(status='failed', groimp_verified=False)
        report['plants'][name] = entry
        try:
            snapshot = load_snapshot(run, name)
            entry['upstream_stages'] = snapshot['status']['stages']
            entry['upstream_open'] = {k: v for k, v in entry['upstream_stages'].items()
                                      if v.get('status') != 'done'}
            entry['human_tasks'] = snapshot['status'].get('human_tasks', [])
            entry['source_hashes'] = snapshot['source_hashes']
            project = out / name / 'export'
            manifest = export_plant(run, name, project)
            graph = read_json(project / 'structure_snapshot.json')
            entry.update(project=str(project), module_counts=manifest['module_counts'],
                         geometry_counts=manifest['geometry_counts'],
                         source_stage=manifest['source_stage'], status='generated_not_runtime_verified')
            entry['stem_evidence'] = [n['metadata'] for n in graph['nodes'] if n['module'] == 'MainStem']
            entry['sub_stem_evidence'] = [dict(key=n['key'], **n['metadata']) for n in graph['nodes']
                                        if n['module'] == 'SubStem']
            entry['limited_sub_stems'] = [n['key'] for n in graph['nodes'] if n['module'] == 'SubStem'
                                         and (len(set(n['metadata'].get('views', []))) < 2
                                              or n['metadata'].get('length_two_view_mm') is None)]
            entry['limitations'] = [
                'Source S7 positions/regions are diagnostic, not S6 supported evidence or leaf surfaces.',
                'Pose gates, unresolved visibility/identity/membership and upstream failures remain in force.',
                'Hull volume is not leaf tissue volume; display markers/axes are not PPFD geometry.',
                'Single-view sub-stem extents are not two-view verified lengths.',
                'Historical structure hash was unavailable in the source; current hashes are recorded.',
            ]
            if core is not None:
                result = verify(project, core.resolve(), out / name / 'verification', java)
                entry['verification'] = result
                if result['status'] != 'passed':
                    raise StudyError('GroIMP verification failed; inspect verification.json and logs')
                entry.update(status='runtime_verified', groimp_verified=True)
            # Never promote an export if its source changed while the verifier ran.
            changed = [p for p, digest in entry['source_hashes'].items() if file_hash(Path(p)) != digest]
            if changed:
                raise StudyError(f'Input changed during handoff: {changed}')
            entry['artifact_hashes'] = {str(p.relative_to(out)): file_hash(p)
                                        for p in (out / name).rglob('*') if p.is_file()}
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            entry.update(status='failed', groimp_verified=False, error=f'{type(exc).__name__}: {exc}')
        write_json(out / 'handoff.json', report)
    report['status'] = 'failed' if any(v['status'] == 'failed' for v in report['plants'].values()) else (
        'runtime_verified' if core is not None else 'generated_not_runtime_verified')
    write_json(out / 'handoff.json', report)
    lines = ['# Static XL delivery to Claude', '', f'Source run: `{run}`', '',
             f'Delivery status: **{report["status"]}**. This is transport status, not research completion.', '',
             '| Plant | XL result | Upstream open stages | Limited sub-stem axes |', '|---|---|---|---|']
    for name, entry in report['plants'].items():
        lines.append(f'| {name} | {entry["status"]} | {", ".join(entry.get("upstream_open", {})) or "none recorded"} | '
                     f'{len(entry.get("limited_sub_stems", []))} |')
    lines += ['', '## Continue from this delivery', '',
              '- Open `<plant>/export/Model.rgg`; use the organ mapping and metadata in that directory.',
              '- Inspect `handoff.json` for exact source hashes, upstream failures, human tasks and per-plant evidence.',
              '- If verified, inspect `<plant>/verification/verification.json` and its logs. GUI visual inspection remains unverified.',
              '- Recompute after human edits into a NEW pipeline run and a NEW XL handoff directory; do not overwrite snapshots.',
              '- Do not convert masks/hulls/markers into claimed leaf surfaces. Do not infer absent organs from growth counts.',
              '- Preserve hull_trunk provenance, unknown diameter and single-view sub-stem limitations.',
              '- Training, PPFD, growth rules, heavy-step Colab offload and remote Artifact publication are outside this operation.',
              '', '## Errors', '']
    lines += [f'- {name}: {entry["error"]}' for name, entry in report['plants'].items() if 'error' in entry]
    (out / 'CLAUDE_README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--plant', action='append')
    parser.add_argument('--core', type=Path)
    parser.add_argument('--java', default='java')
    args = parser.parse_args(argv)
    report = prepare(args.run, args.out, args.plant, args.core, args.java)
    print(text_json(dict(status=report['status'], out=str(args.out.resolve()),
                         plants={k: v['status'] for k, v in report['plants'].items()})))
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
