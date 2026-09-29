"""Review page for contradictory cross-view decisions (2026-09-29).

    python -X utf8 -m tools.conflict_review --run build/pipeline_<ts> [--config tools/plant_pipeline_plants.json]

S4 (tools.cross_view_identity_import) links masks through every "same"/"duplicate" decision; when two masks that a
person called "different" end up in one group, the whole group is left out (a conflict). The normal review page never
shows an answered pair again, so a person could not fix it. This page lists, per conflict, the "different" decision
and the chain of decisions that joins the two masks, with photo crops, and lets a person change any of them. Saving
downloads a cross_view_decisions_<plant>_<ts>.json holding only the changed decisions with a new decided_at: S4 keeps
the latest answer per question, and the watcher reruns the pipeline. Nothing is decided here automatically.
"""
from __future__ import annotations

import argparse
import base64
import glob
import io
import json
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from tools.cross_view_identity_import import LINK_KINDS, group_decisions, load_decisions
from tools.leaf_light.common import read_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
KO = {'same': '같음', 'different': '다름', 'duplicate': '중복(한 잎)', 'unsure': '모름', 'single_leaf': '소엽 하나뿐',
      'fine': '문제없음', 'merged': '합쳐짐', 'target_merged': '대상이 합쳐짐'}


def decision_sources(plant: str, cfg: dict, g: dict) -> list[Path]:
    """The same decision files S4 reads (plant_pipeline.Plant.s4)."""
    src = [ROOT / p for p in cfg.get('decisions', [])]
    src += [Path(p) for p in glob.glob(str(Path(g['downloads']) / f'cross_view_decisions_{plant}_*.json'))]
    return [p for p in src if p.exists()]


def chain(docs: list[dict], a: str, b: str) -> list[dict]:
    """Shortest sequence of linking decisions ('same' links, 'duplicate' groups) that joins mask a to mask b."""
    edges: dict[str, list] = {}
    for d in docs:
        kind, verdict = d['decision_detail']['kind'], d['decision']
        panels = [m['mask_ids'] for m in d['decision_detail']['masks']]
        ids = [i for p in panels for i in p]
        if kind in LINK_KINDS and verdict == 'same':
            pairs = [(ids[0], i) for i in ids[1:]]
        elif kind == 'dup' and verdict == 'duplicate':
            pairs = [(panels[0][0], i) for i in panels[0][1:]]
        else:
            continue
        for x, y in pairs:
            edges.setdefault(x, []).append((y, d)); edges.setdefault(y, []).append((x, d))
    prev, q = {a: None}, deque([a])
    while q:
        x = q.popleft()
        if x == b:
            break
        for y, d in edges.get(x, []):
            if y not in prev:
                prev[y] = (x, d); q.append(y)
    if b not in prev:
        return []
    out, x = [], b
    while prev[x]:
        x, d = prev[x]
        out.append(d)
    return out[::-1]


def crop(batch: Path, mask_id: str, cache: dict) -> str:
    """JPEG data URI: the mask's photo around its box, the box drawn, the mask outline when it can be rendered."""
    if mask_id in cache:
        return cache[mask_id]
    item = read_json(batch / 'items' / f'{mask_id}.json')
    session = Path(read_json(batch / 'manifest.json')['session'])
    im = Image.open(session / item['image_path']).convert('RGB')
    x, y, w, h = item['source_bbox_xywh_px']
    m = max(w, h) * 0.6
    box = (int(max(0, x - m)), int(max(0, y - m)), int(min(im.size[0], x + w + m)), int(min(im.size[1], y + h + m)))
    dr = ImageDraw.Draw(im)
    try:
        import cv2
        from tools.leaflet_mask_batch import Batch
        mask, meta = Batch(batch).mask(item)  # crop-resolution mask; meta['crop_px'] places it in the photo
        x0, y0 = meta['crop_px'][:2]
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            pts = [(int(px) + x0, int(py) + y0) for px, py in cnt.reshape(-1, 2)]
            if len(pts) > 2:
                dr.line(pts + [pts[0]], fill=(255, 60, 60), width=max(3, int(min(im.size) / 600)))
    except Exception:
        pass  # the box alone still identifies the observation
    dr.rectangle([x, y, x + w, y + h], outline=(255, 214, 0), width=max(4, int(min(im.size) / 400)))
    im = im.crop(box)
    im.thumbnail((360, 360))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=82)
    cache[mask_id] = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    return cache[mask_id]


def plant_conflicts(run: Path, plant: str, pcfg: dict, g: dict) -> dict | None:
    rep_path = run / plant / 'identities' / 'identity_import_report.json'
    if not rep_path.exists():
        return None
    rep = read_json(rep_path)
    if not rep['conflicts']:
        return None
    docs = [d for d in load_decisions(decision_sources(plant, pcfg, g)) if d.get('plant_id') == plant]
    by_id = {d['object_id']: d for d in docs}
    batch = ROOT / pcfg['batch'] if not Path(pcfg['batch']).is_absolute() else Path(pcfg['batch'])
    cache, items = {}, []
    for c in rep['conflicts']:
        diff = by_id[c['decision']]
        a, b = c['masks'][0], c['masks'][-1]
        rows = []
        # the shortest chain alone was not enough (09-29: cutting it exposed another path), so every linking decision
        # that touches either end of the "different" pair is shown too: all of them must agree for a split to hold
        touching = [d for d in docs if d['decision'] in ('same', 'duplicate', 'unsure', 'different') and d is not diff
                    and d['decision_detail']['kind'] in (*LINK_KINDS, 'dup')
                    and {a, b} & {i for m in d['decision_detail']['masks'] for i in m['mask_ids']}]
        seen, ordered = set(), []
        for d in [diff] + chain(docs, a, b) + sorted(touching, key=lambda d: d['object_id']):
            if d['object_id'] not in seen:
                seen.add(d['object_id']); ordered.append(d)
        for d in ordered:
            panels = d['decision_detail']['masks']
            rows.append(dict(object_id=d['object_id'], decision=d['decision'], decision_ko=KO.get(d['decision'], d['decision']),
                             decided_at=d.get('decided_at'), kind=d['decision_detail']['kind'],
                             role='different' if d is diff else 'chain' if d in chain(docs, a, b) else 'touching',
                             panels=[dict(view=p['view'], masks=p['mask_ids'], img=crop(batch, p['mask_ids'][0], cache)) for p in panels]))
        items.append(dict(conflict=c['decision'], masks=c['masks'], rows=rows))
    return dict(plant=plant, session=rep.get('session_id') or docs[0].get('session_id'), conflicts=items,
                docs={r['object_id']: {k: v for k, v in by_id[r['object_id']].items() if not k.startswith('_')}
                      for it in items for r in it['rows']})


PAGE = """<!doctype html><html lang=ko><meta charset=utf-8><title>짝짓기 충돌 검토</title>
<style>:root{--bg:#fff;--ink:#1d1d1f;--mut:#6b6b70;--line:#e3e3e6;--acc:#2f6a2a;--warn:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--ink:#ececef;--mut:#9a9aa1;--line:#2c2c30;--acc:#8fce86;--warn:#f2b8b5}}
body{background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,'Malgun Gothic',sans-serif;margin:0 auto;max-width:1200px;padding:0 16px 40px}
.bar{position:sticky;top:0;background:var(--bg);padding:12px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;z-index:2}
h1{font-size:20px;margin:0}h2{font-size:17px;margin:28px 0 4px}h3{font-size:15px;margin:18px 0 6px}p{color:var(--mut);margin:6px 0}
.row{display:flex;gap:14px;align-items:center;border:1px solid var(--line);border-radius:10px;padding:10px;margin:8px 0;flex-wrap:wrap}
.row.diff{border-color:var(--warn)}.pan{text-align:center}.pan img{display:block;max-height:220px;border-radius:6px}
.lab{font-size:12px;color:var(--mut)}.ch label{margin-right:10px;white-space:nowrap}button{font:inherit;padding:8px 16px;border-radius:8px;
border:1px solid var(--acc);background:var(--acc);color:var(--bg);cursor:pointer}.tag{font-weight:600}</style>
<div class=bar><h1>짝짓기 충돌 검토</h1><span id=msg class=lab></span></div>
<p>아래 결정들은 서로 모순입니다. 빨간 테두리는 "다름" 결정, "이어 준 경로"는 두 마스크를 한 소엽으로 이은 결정, "다른 연결"은 같은 마스크에 붙은 나머지 결정입니다.
<b>두 마스크가 정말 다른 소엽이면, 둘을 잇는 모든 "같음"을 바꿔야 합니다</b>(하나만 끊으면 다른 경로로 다시 이어짐). 정말 같은 소엽이면 "다름"만 "같음"으로 바꾸면 됩니다.
사진(노란 박스 = 해당 마스크, 빨간 선 = 마스크 윤곽)을 보고 고친 뒤 식물별 저장을 누르세요. 바꾼 결정만 새 시각으로 저장되고 다음 실행에서 우선합니다.</p>
<div id=root></div>
<script>
const DATA = __DATA__;
const root = document.getElementById('root');
for (const P of DATA.plants) {
  const sec = document.createElement('section');
  sec.innerHTML = `<h2>${P.plant} · 충돌 ${P.conflicts.length}건 <button data-plant="${P.plant}">${P.plant} 결정 파일 저장</button></h2>`;
  P.conflicts.forEach((c, i) => {
    const box = document.createElement('div');
    box.innerHTML = `<h3>충돌 ${i + 1}: ${c.masks.join(' ↔ ')}</h3>`;
    for (const r of c.rows) {
      const row = document.createElement('div');
      row.className = 'row' + (r.decision === 'different' ? ' diff' : '');
      const pans = r.panels.map(p => `<div class=pan><img src="${p.img}"><div class=lab>사진 ${p.view} · ${p.masks.join(', ')}</div></div>`).join('<div>↔</div>');
      const opts = ['same', 'different', 'unsure'].map(v => `<label><input type=radio name="${P.plant}|${r.object_id}" value="${v}" ${v === r.decision ? 'checked' : ''}> ${{same: '같음', different: '다름', unsure: '모름'}[v]}</label>`).join('');
      const role = {different: '다름 결정', chain: '이어 준 경로', touching: '다른 연결'}[r.role] || '';
      row.innerHTML = `${pans}<div><div class=lab>${role}</div><div>현재: <span class=tag>${r.decision_ko}</span></div><div class=ch>${r.kind === 'dup' ? '<span class=lab>(중복 결정: 같음=한 잎, 다름=다른 잎)</span><br>' : ''}${opts}</div></div>`;
      box.appendChild(row);
    }
    sec.appendChild(box);
  });
  root.appendChild(sec);
}
for (const b of document.querySelectorAll('button[data-plant]')) b.onclick = () => {
  const P = DATA.plants.find(p => p.plant === b.dataset.plant), now = new Date().toISOString(), out = [];
  for (const [id, doc] of Object.entries(P.docs)) {
    const sel = document.querySelector(`input[name="${P.plant}|${id}"]:checked`);
    if (!sel) continue;
    let v = sel.value;
    if (doc.decision_detail.kind === 'dup') v = v === 'same' ? 'duplicate' : v;
    if (v === doc.decision) continue;
    const d = JSON.parse(JSON.stringify(doc));
    d.history = [...(d.history || []), {decision: doc.decision, decided_at: doc.decided_at, changed_on: 'conflict review page'}];
    d.decision = v; d.decided_at = now; out.push(d);
  }
  if (!out.length) { document.getElementById('msg').textContent = `${P.plant}: 바뀐 결정이 없습니다.`; return; }
  const file = {schema: 'cross-view-decisions-file-1', plant: P.plant, session: P.session, saved_at: now, source: 'conflict review page', decisions: out};
  const ts = now.replace(/[-:]/g, '').slice(0, 13);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(file, null, 1)], {type: 'application/json'}));
  a.download = `cross_view_decisions_${P.plant}_${ts}.json`; a.click();
  document.getElementById('msg').textContent = `${P.plant}: 결정 ${out.length}개를 바꿔 저장했습니다.`;
};
</script>"""


def build(run: Path, config: Path = CONFIG) -> Path | None:
    run, g = Path(run), read_json(config)
    plants = [x for x in (plant_conflicts(run, name, pcfg, g) for name, pcfg in g['plants'].items() if (run / name).exists()) if x]
    if not plants:
        return None
    page = run / 'CONFLICTS_REVIEW.html'
    page.write_text(PAGE.replace('__DATA__', json.dumps(dict(run=run.name, plants=plants), ensure_ascii=False)), encoding='utf-8')
    return page


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--config', type=Path, default=CONFIG)
    a = ap.parse_args()
    print(json.dumps(dict(page=str(build(a.run, a.config))), ensure_ascii=False))


if __name__ == '__main__':
    main()
