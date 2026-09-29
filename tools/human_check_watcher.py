"""Rerun the plant pipeline whenever a person saves a decision file (2026-09-24).

    python -X utf8 -m tools.human_check_watcher [--interval 20]

Watches the Downloads folder named in tools/plant_pipeline_plants.json for decision files saved from the
review pages -- human_checks_*.json (the human-check page) and cross_view_decisions_*.json (S4 review pages).
When a new or changed file has been quiet for a short while, it runs `python -m tools.plant_pipeline --all`
once and records the run. It never edits decision files, never runs two pipelines at once, and does nothing
else: decisions that need code changes are listed in the run's HUMAN_TASKS.md for Claude to act on.

State and log live in build/human_checks/ (watcher_state.json, watcher.log, last_run.json).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
HOME = ROOT / 'build' / 'human_checks'
PATTERNS = ('human_checks_*.json', 'cross_view_decisions_*.json', 'reject_reasons_*.json')
#: A file must be unchanged for this many seconds before it is acted on (the browser may still be writing).
QUIET_S = 10


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    with open(HOME / 'watcher.log', 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')


def snapshot(folder: Path) -> dict:
    out = {}
    for pat in PATTERNS:
        for f in folder.glob(pat):
            try:
                st = f.stat()
            except OSError:
                continue
            out[f.name] = [st.st_mtime, st.st_size]
    return out


def read_state() -> dict:
    try:
        return json.loads((HOME / 'watcher_state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def write_state(seen: dict) -> None:
    (HOME / 'watcher_state.json').write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding='utf-8')


def run_pipeline(trigger: list[str]) -> None:
    log(f'decision files changed: {", ".join(trigger)} -> running plant_pipeline --all')
    started = time.time()
    r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'tools.plant_pipeline', '--all'], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    tail = (r.stdout or '').strip().splitlines()[-1:] or ['']
    try:
        out = json.loads(tail[0]).get('out')
    except ValueError:
        out = None
    result = dict(finished_at=datetime.now().isoformat(timespec='seconds'), seconds=round(time.time() - started),
                  returncode=r.returncode, out=out, trigger=trigger, stderr_tail=(r.stderr or '')[-1500:])
    (HOME / 'last_run.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f'pipeline finished rc={r.returncode} out={out}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--interval', type=float, default=20)
    ap.add_argument('--once', action='store_true', help='check once and exit (for testing)')
    a = ap.parse_args()
    HOME.mkdir(parents=True, exist_ok=True)
    (HOME / 'watcher.pid').write_text(str(os.getpid()), encoding='utf-8')
    folder = Path(json.loads(CONFIG.read_text(encoding='utf-8'))['downloads'])
    seen = read_state()
    if not seen:  # first start: files already there were handled by earlier runs
        seen = snapshot(folder)
        write_state(seen)
    log(f'watching {folder} for {", ".join(PATTERNS)}')
    while True:
        now = snapshot(folder)
        changed = [n for n, v in now.items() if seen.get(n) != v and time.time() - v[0] >= QUIET_S]
        if changed:
            run_pipeline(sorted(changed))
            for n in changed:
                seen[n] = now[n]
            write_state(seen)
        if a.once:
            break
        time.sleep(a.interval)


if __name__ == '__main__':
    main()
