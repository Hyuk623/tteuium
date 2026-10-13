"""All plants in one command: photos of every plant in, one traits table out (2026-10-01).

    python -X utf8 -m tools.plant_batch --photos-root <folder> [--out build/plants_<date>] [--offload kaggle-gpu]
    python -X utf8 -m tools.plant_batch --out build/plants_<date> --summary-only     # after adding measurements

<folder> holds one sub-folder per plant, named by the plant id (e.g. dwt_05/ with its 18 photographs; an optional
growth.json next to them is used as the growth record). Each plant goes through tools.plant_auto: S0 photos and board
poses, marker-corner pose rescue, S1 organ detector v4 (whole photo + 2x2 tiles), S2 SAM v5 leaflet masks with the
learned review model, S3 hull / compounds / stem / stem thickness, S4-S7 diagnostics, S8 traits. Nothing waits for a
person. A plant that already finished is skipped; an interrupted one resumes; a failing one is recorded and the next
plant runs. At the end every plant's traits.json is summarised into <out>/traits/ (traits.csv, TRAITS.md) with the
calibration and light files from measurements/ (tools.plant_traits).

The only human work this asks for is in <out>/traits/TRAITS.md: non-destructive leaf-area measurements of 4-6 plants
and the PPFD / photoperiod readings. Mask review, names and cross-view pairs stay optional (leaf-level results only).
"""
from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime
from pathlib import Path

from tools.leaf_light.common import StudyError, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXT = {'.heic', '.heif', '.jpg', '.jpeg', '.png'}


def plant_folders(root: Path) -> dict:
    return {d.name: d for d in sorted(Path(root).iterdir())
            if d.is_dir() and sum(p.suffix.lower() in IMAGE_EXT for p in d.iterdir()) >= 1}


def traits_files(out: Path) -> list[Path]:
    """The traits.json of each plant's latest auto run (growth variant preferred when both exist)."""
    files = []
    for d in sorted((Path(out) / 'plants').glob('*')):
        found = sorted(d.glob('pipeline_growth/*/traits.json')) or sorted(d.glob('pipeline_no_growth/*/traits.json'))
        files += found[:1]
    return files


def summary(out: Path, measurements: Path | None = None) -> dict:
    from tools.plant_traits import summarize
    files = traits_files(out)
    if not files:
        raise StudyError(f'No traits.json under {out}/plants')
    return summarize([read_json(p) for p in files], Path(out) / 'traits', measurements)


def run(photos_root: Path, out: Path, offload: str = 'local', plants: list[str] | None = None) -> dict:
    from tools import plant_auto
    out = Path(out).resolve()
    (out / 'plants').mkdir(parents=True, exist_ok=True)
    folders = plant_folders(photos_root)
    if plants:
        folders = {k: v for k, v in folders.items() if k in plants}
    if not folders:
        raise StudyError(f'No plant folders with photographs under {photos_root}')
    log_path = out / 'batch_run.json'
    log = read_json(log_path) if log_path.exists() else dict(schema='plant-batch-1', photos_root=str(photos_root), plants={})
    for name, folder in folders.items():
        run_dir = out / 'plants' / name
        entry = log['plants'].setdefault(name, {})
        auto = run_dir / 'auto_run.json'
        if auto.exists() and read_json(auto).get('finished'):
            entry['status'] = 'done'
            continue
        entry.update(status='running', started=datetime.now().isoformat(timespec='seconds'), photos=str(folder))
        write_json(log_path, log)
        try:
            growth = folder / 'growth.json'
            if auto.exists():
                plant_auto.run(None, None, run_dir, resume=True)
            else:
                plant_auto.run(folder, name, run_dir, growth if growth.exists() else None, offload=offload)
            entry.update(status='done', finished=datetime.now().isoformat(timespec='seconds'))
        except Exception as e:  # one plant never stops the others
            entry.update(status='failed', error=f'{type(e).__name__}: {e}', trace=traceback.format_exc()[-1500:])
        write_json(log_path, log)
    try:
        log['summary'] = {k: v for k, v in summary(out).items() if k not in ('rows',)}
    except Exception as e:
        log['summary'] = dict(error=f'{type(e).__name__}: {e}')
    write_json(log_path, log)
    return log


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--photos-root', type=Path, help='one sub-folder of photographs per plant, named by plant id')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--plant', nargs='*', help='only these plant folders')
    ap.add_argument('--offload', choices=['local', 'kaggle-gpu', 'kaggle-cpu'], default='local')
    ap.add_argument('--summary-only', action='store_true', help='only rebuild <out>/traits (e.g. after adding measurements)')
    ap.add_argument('--measurements', type=Path)
    a = ap.parse_args()
    if a.summary_only:
        if not a.out:
            ap.error('--summary-only needs --out')
        d = summary(a.out, a.measurements)
        print(json.dumps({k: d[k] for k in ('plants', 'calibration', 'validated_metric', 'human_tasks')}, ensure_ascii=False))
        return
    if not a.photos_root:
        ap.error('--photos-root is required')
    out = a.out or ROOT / 'build' / f"plants_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log = run(a.photos_root, out, a.offload, a.plant)
    print(json.dumps(dict(out=str(out), plants={k: v['status'] for k, v in log['plants'].items()}, summary=log.get('summary')), ensure_ascii=False))


if __name__ == '__main__':
    main()
