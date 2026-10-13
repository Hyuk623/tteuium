"""One command for the semi-automatic tomato 3D pipeline (S0..S7) on one or more plants.

    python -X utf8 -m tools.plant_pipeline --all
    python -X utf8 -m tools.plant_pipeline --plant dwt_01 --plant dwt_03
    python -X utf8 -m tools.plant_pipeline --all --xl --groimp-core ../groimp/core.jar

Every run writes a fresh build/pipeline_<timestamp>/ with one folder per plant, a status.json per plant, and two
Korean summaries: STATUS.md (what each stage produced) and HUMAN_TASKS.md (only the work a person must do, with
the file or page to open). A stage never invents a missing input; it reports `waiting_for_human` or `unavailable`
with the reason, and later stages continue with whatever exists.

Stages
  S0 session      prepared photos and measured ChArUco poses (tools.import_organized_capture), reused if present
  S1 labels       Roboflow labels in original pixels (tools.roboflow_session_import), reused if present
  S2 masks        leaflet masks and human acceptance (tools.leaflet_mask_batch); SAM runs only where authorised
  S3 structure    hull, compound regions, stem, petioles (tools.plant_structure)
  S4 identities   saved human decisions -> editor identities (tools.cross_view_identity_import), then new
                  candidates + visibility questions as a local review page (tools.cross_view_candidates)
  S5 direction    model-2 tip-direction labels (waits until an export is configured)
  S6 evidence     Document 06 diagnostic fusion (tools.instance_workflow)
  S7 hierarchy    organ hierarchy + 3D viewer (tools.plant_hierarchy)
  S8 traits       whole-plant leaf-area proxy, canopy area, hull size, stem diameter (tools.plant_traits); the run
                  summary adds the calibration (measurements/leaf_area.csv) and PPFD/DLI (measurements/light.csv)

Goal 'whole_plant' (default, user decision 2026-10-01): HUMAN_TASKS.md lists first only what the traits need
(measurements); S2-S5 review tasks are listed as optional, needed only for leaf-level results.
Nothing is metric-validated or PPFD-ready until the calibration exists: poses fail the 1 px gate.
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

from tools.leaf_light.common import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
DONE, WAIT, UNAVAILABLE, FAILED = 'done', 'waiting_for_human', 'unavailable', 'failed'
STATUS_KO = {DONE: '완료', WAIT: '사람 작업 대기', UNAVAILABLE: '불가', FAILED: '오류'}


def rel(p):
    return ROOT / p if p else None


NAMES_PAGE = """<!doctype html><html lang=ko><meta charset=utf-8><title>복엽 이름 확인</title>
<style>:root{--bg:#fff;--ink:#1d1d1f;--mut:#6b6b70;--line:#e3e3e6;--acc:#2f6a2a}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--ink:#ececef;--mut:#9a9aa1;--line:#2c2c30;--acc:#8fce86}}
body{background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,'Malgun Gothic',sans-serif;margin:24px auto;max-width:1200px;padding:0 16px}
h1{font-size:20px;margin:0}h2{font-size:17px;margin:28px 0 6px}p{color:var(--mut);margin:4px 0 12px}
.imgs{display:flex;gap:8px;overflow-x:auto}.imgs img{height:340px;border:1px solid var(--line);border-radius:6px}
table{border-collapse:collapse;margin-top:8px}td,th{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left}
th{color:var(--mut);font-weight:600}.sw{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:middle}
select{font:inherit;padding:2px 4px}button{font:inherit;padding:8px 16px;border-radius:8px;border:1px solid var(--acc);background:var(--acc);color:var(--bg);cursor:pointer}
.bar{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center}
.small{font-size:12px;color:var(--mut)}</style>
<div class=bar><h1>복엽 이름 확인</h1><button id=save>결정 파일 저장</button><span id=msg class=small></span></div>
<p>규칙: 아래에서 위로 L01, L02 …, 전개 중인 잎이 맨 위(마지막 번호). 사진 위 이름과 색을 보고, 맞으면 "제안 유지", 틀리면 올바른 이름을 고르세요.
고르지 않은 영역은 결정 없음으로 남습니다. 저장 파일은 다운로드 폴더에 두면 감시기가 파이프라인을 다시 돌립니다.</p>
<div id=root></div>
<script>
const DATA = __DATA__;
const root = document.getElementById('root');
for (const p of DATA.plants) {
  const sec = document.createElement('section');
  sec.innerHTML = `<h2>${p.plant}</h2><p>생육 기록: ${p.growth || '없음'} · ${p.naming}</p><div class=imgs>${p.images.map(i => `<a href="${i}" target=_blank><img src="${i}"></a>`).join('')}</div>`;
  const t = document.createElement('table');
  t.innerHTML = '<tr><th>색</th><th>영역</th><th>제안</th><th>중앙 높이 (mm)</th><th>복셀</th><th>사진</th><th>결정</th></tr>';
  for (const r of p.regions) {
    const opts = ['', 'confirm', ...p.names, 'none'].map(v => `<option value="${v}">${v === '' ? '(결정 없음)' : v === 'confirm' ? '제안 유지' : v === 'none' ? '이름 없음(잎 아님·조각)' : v}</option>`).join('');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><span class=sw style="background:rgb(${r.rgb})"></span></td><td>${r.region}${r.fragment ? ' (조각)' : ''}</td><td><b>${r.proposed || '—'}</b>${r.human ? ' <span class=small>(사람 확인됨)</span>' : ''}</td><td>${r.z}</td><td>${r.voxels}</td><td>${r.photos}</td><td><select data-plant="${p.plant}" data-region="${r.region}" data-z="${r.z}">${opts}</select></td>`;
    t.appendChild(tr);
  }
  sec.appendChild(t); root.appendChild(sec);
}
document.getElementById('save').onclick = () => {
  const names = JSON.parse(JSON.stringify(DATA.previous.names || {}));
  let n = 0;
  for (const s of document.querySelectorAll('select')) {
    if (!s.value) continue;
    (names[s.dataset.plant] ||= {})[s.dataset.region] = {name: s.value === 'none' ? '' : s.value, median_z_mm: +s.dataset.z};
    n++;
  }
  const out = {...DATA.previous, schema: 'human-checks-1', run: DATA.run, saved_at: new Date().toISOString(), names};
  const ts = new Date().toISOString().replace(/[-:]/g, '').replace('T', '_').slice(0, 15);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {type: 'application/json'}));
  a.download = `human_checks_${ts}.json`; a.click();
  document.getElementById('msg').textContent = `${n}개 영역 결정을 저장했습니다 (이전 결정 유지).`;
};
</script>"""


def names_page(out: Path, plants: list, checks: dict) -> Path:
    """One page to confirm or correct the compound-leaf names of every plant (2026-09-29). It saves a
    human_checks_*.json that keeps the earlier decisions and names, so a new save never drops them."""
    from tools.plant_structure import PALETTE
    data = dict(run=out.name, previous={k: v for k, v in checks.items() if k not in ('source',)}, plants=[])
    for p in plants:
        sj = out / p.name / 'structure' / 'structure.json'
        if not sj.exists():
            continue
        st = read_json(sj)
        growth = read_json(Path(st['inputs']['growth'])) if st['inputs'].get('growth') else None
        ids = sorted(e['compound_leaf_id'] for e in (growth or {}).get('compound_leaves', []) if e.get('compound_leaf_id'))
        n = max(len(ids), len(st['compound_regions'])) + 1
        names = sorted(set(ids) | {f'L{i:02d}' for i in range(1, n + 1)}) + ['growing_leaf']
        data['plants'].append(dict(
            plant=p.name, naming=st['compound_region_meta'].get('naming', ''),
            growth=', '.join(f"{e['compound_leaf_id']}({e.get('leaflet_count')}{', 전개 중' if e.get('is_unfolding') else ''})"
                             for e in (growth or {}).get('compound_leaves', [])),
            images=[f'{p.name}/structure/overlays/{f.name}' for f in sorted((sj.parent / 'overlays').glob('*.jpg'))],
            names=names,
            regions=[dict(region=c['region'], proposed=c.get('proposed_name'), z=c['median_z_mm'], voxels=c['voxels'],
                          photos=c['photos'], fragment=c.get('fragment'), human=c.get('name_source') == 'human',
                          rgb=','.join(map(str, PALETTE[c['region'] % len(PALETTE)])))
                     for c in sorted(st['compound_regions'], key=lambda c: c['median_z_mm'])]))
    page = out / 'NAMES_REVIEW.html'
    page.write_text(NAMES_PAGE.replace('__DATA__', json.dumps(data, ensure_ascii=False)), encoding='utf-8')
    return page


def latest_human_checks(g: dict) -> dict:
    """Newest decision file saved from the human-check page (human_checks_*.json in Downloads), or {}."""
    files = sorted(Path(g['downloads']).glob('human_checks_*.json'), key=lambda f: f.stat().st_mtime)
    for f in reversed(files):
        try:
            d = read_json(f)
        except Exception:
            continue
        if d.get('schema') == 'human-checks-1':
            return dict(d, source=str(f))
    return {}


def run_module(args: list[str], timeout=3600) -> dict:
    r = subprocess.run([sys.executable, '-X', 'utf8', '-m'] + args, cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else f'exit {r.returncode}')
    lines = [l for l in r.stdout.strip().splitlines() if l.strip().startswith('{')]
    return json.loads(lines[-1]) if lines else {}


class Plant:
    def __init__(self, name: str, cfg: dict, glob_cfg: dict, out: Path):
        self.name, self.cfg, self.g, self.out = name, cfg, glob_cfg, out / name
        self.out.mkdir(parents=True)
        self.stages, self.tasks = {}, []
        self.capture = rel(cfg['capture'])
        # pose_session (2026-10-01): a copy of the edit session with extra board poses from ArUco marker corners
        # (tools.marker_pose_rescue); S0 still reports the original capture, every posed stage uses this session
        self.session = rel(cfg['pose_session']) if cfg.get('pose_session') else self.capture / 'edit_session'
        self.original_session = self.capture / 'edit_session'  # S6 (Codex instance workflow) checks its prepared hashes against this one
        self.labels = rel(cfg['labels'])
        self.seed = self.labels / 'seed_with_imports.backup.json'
        self.growth = rel(cfg.get('growth'))
        self.batch = rel(cfg.get('batch'))
        self.backup = self.seed

    def stage(self, key, status, summary, **extra):
        self.stages[key] = dict(status=status, summary=summary, **extra)

    def task(self, priority, text, where=None):
        self.tasks.append(dict(priority=priority, text=text, where=str(where) if where else None))

    # S0
    def s0(self):
        if not (self.capture / 'capture.json').exists():
            args = ['tools.import_organized_capture', '--source', str(rel(self.cfg['photo_source'])), '--mapping', str(rel(self.g['mapping'])),
                    '--plant', self.name, '--intrinsics', str(rel(self.g['intrinsics'])), '--out', str(self.capture)]
            for code, reason in (self.cfg.get('exclude_views') or {}).items():
                args += ['--exclude-view', f'{code}={reason}']
            run_module(args)
        cap = read_json(self.capture / 'capture.json')
        solved = [f['view_code'] for f in cap['frames'] if f['pose_status'] == 'solved']
        passed = sum(bool(f.get('passes_pose_gate')) for f in cap['frames'])
        report = read_json(self.capture / 'import_report.json') if (self.capture / 'import_report.json').exists() else {}
        rescued = []
        if self.cfg.get('pose_session') and (self.session / 'capture.json').exists():
            rescued = [f['view_code'] for f in read_json(self.session / 'capture.json')['frames'] if f.get('pose_status') == 'solved_marker_corners']
        self.stage('S0', DONE, f"사진 {len(cap['frames'])}장, 카메라 위치 계산 {len(solved)}장({', '.join(solved)})"
                   + (f" + 마커 귀퉁이 포즈 {len(rescued)}장({', '.join(rescued)})" if rescued else '') + f", 1 px 기준 통과 {passed}장",
                   solved_views=solved, marker_corner_views=rescued, excluded=report.get('excluded_views', []))
        if not (self.session / 'capture.json').exists():
            raise RuntimeError('edit_session missing: run tools.prepare_leaf_edit_session')

    # S1
    def s1(self):
        if not self.seed.exists():
            args = ['tools.roboflow_session_import', '--plant', self.name, '--package', 'build/roboflow_dataset_review_20260922/by_plant',
                    '--session', str(self.session), '--out', str(self.labels)]
            if self.growth and self.growth.exists():
                args += ['--growth', str(self.growth)]
            run_module(args)
        rep = read_json(self.labels / 'mapping_report.json')
        self.label_source = 'auto' if rep.get('schema_version') == 'plant-auto-labels-1' else 'human'
        if self.label_source == 'auto':
            self.stage('S1', DONE, f"모델 초안 라벨 {rep['mapped_annotations']}개(자동, 사람 미확인), 사진 {rep['mapped_photos']}장",
                       label_source='auto')
        else:
            self.stage('S1', DONE, f"라벨 {rep['mapped_annotations']}/{rep['source_annotations']}개 원본 좌표로 변환, 사진 {rep['mapped_photos']}장",
                       label_source='human')
        g = read_json(self.growth) if self.growth and self.growth.exists() else None
        if not g or not g.get('compound_leaves'):
            self.task(1, f'{self.name} 생육 기록 JSON 작성 (복엽 수, 복엽별 소엽 수, 생장점 수). 소엽 개수 비교와 복엽 이름(L01=가장 아래, 위로 갈수록 번호 증가)에 쓰입니다.', self.growth)
            self.growth = None

    # S2
    def s2(self):
        if not self.batch or not (self.batch / 'manifest.json').exists():
            self.stage('S2', WAIT, '소엽 마스크 배치가 없습니다. SAM 마스크 생성은 사용자 허락이 필요합니다(지난 허락은 dwt_01/02 한정).')
            self.task(1, f'{self.name} SAM 소엽 마스크 생성 허락 (로컬 CPU, 박스마다 후보 마스크). 허락 후 준비·생성은 자동입니다.')
            return
        from tools.leaflet_mask_batch import Batch
        # reasons for earlier rejections, saved from the reject-reason page (2026-09-27); applied through Batch.review
        saved = sorted(Path(self.g['downloads']).glob('reject_reasons_*.json'))
        if saved:
            from tools.reject_reasons import apply as apply_reasons
            self.reject_reason_result = apply_reasons(self.name, self.batch, saved)
        b = Batch(self.batch)
        c, why = Counter(), Counter()
        n_auto = 0
        for i in b.manifest['ids']:
            it = b.item(i)
            n_auto += it['generation'] == 'ready' and it['review'] == 'accepted' and it.get('review_source') == 'auto'
            c[('accepted' if it['review'] in ('accepted', 'accepted_by_user') else it['review'])
              if it['generation'] == 'ready' else 'not_generated'] += 1
            if it['review'] == 'rejected':
                why[it.get('reject_reason') or 'no_reason'] += 1
            if it['review'] == 'accepted' and it.get('visibility') == 'partial':
                why['accepted_partial'] += 1
        self.mask_counts = dict(c)
        n_acc = c.get('accepted', 0)
        todo = sum(v for k, v in c.items() if k not in ('accepted', 'rejected'))
        status = DONE if n_acc and not todo else WAIT if todo or not n_acc else DONE
        KO = dict(duplicate_box='복수 박스', box_misses_leaf='잎 못 담음', false_positive='오탐', no_reason='이유 없음')
        why_txt = ', '.join(f'{KO[k]} {v}' for k, v in why.items() if k in KO)
        self.stage('S2', status, f"마스크 {sum(c.values())}개: 수락 {n_acc}" + (f"(자동 {n_auto}, 사람 미확인)" if n_auto else '') +
                   (f"(가려짐 {why['accepted_partial']})" if why.get('accepted_partial') else '') +
                   f", 미검토 {c.get('unreviewed', 0)}, 수정 중 {c.get('edited', 0)}, 거절 {c.get('rejected', 0)}" + (f"({why_txt})" if why_txt else '') +
                   f", 미생성 {c.get('not_generated', 0)}", counts=dict(c), reject_reasons=dict(why), auto_accepted=n_auto)
        if n_auto:
            self.task(5, f"(선택) {self.name} 자동 수락 마스크 {n_auto}개 검토. 고치면 사람 결과가 자동 결과를 덮어씁니다. 편집기 포트 {self.cfg.get('editor_port')}")
        if why.get('no_reason'):
            self.task(3, f"{self.name} 거절 {why['no_reason']}개에 이유 붙이기 (가려짐/복수 박스/잎 못 담음/오탐). build/reject_reasons_20260927/review.html")
        if todo:
            self.task(2, f"{self.name} 소엽 마스크 검토 {todo}개 (수락/거절). 편집기 http://127.0.0.1:{self.cfg.get('editor_port')}/ 의 '복엽·소엽 윤곽 비교'")

    # S3
    def s3(self):
        out = self.out / 'structure'
        args = ['tools.plant_structure', '--session', str(self.session), '--backup', str(self.seed), '--out', str(out)]
        if self.cfg.get('view_grouping') is not None:
            self.out.mkdir(parents=True, exist_ok=True)
            grouping_path = self.out / 'view_grouping.json'
            write_json(grouping_path, self.cfg['view_grouping'])
            args += ['--view-grouping', str(grouping_path)]
        if self.growth:
            args += ['--growth', str(self.growth)]
        names = (latest_human_checks(self.g).get('names') or {}).get(self.name)
        if names:
            self.out.mkdir(parents=True, exist_ok=True)
            write_json(self.out / 'name_decisions.json', names)
            args += ['--names', str(self.out / 'name_decisions.json')]
        r = run_module(args)
        st = read_json(out / 'structure.json')
        self.structure = out
        if st.get('human_names_status') == 'unavailable_assignment_changed_or_unbound':
            self.task(4, f'{self.name} 현재 영역 분할과 연결되지 않은 이전 잎 이름은 적용하지 않았습니다. 새 후보 영역을 다시 확인하세요.',
                      out / 'structure.json')
        names = ', '.join(f"{c['proposed_name'] or '영역' + str(c['region'])}" for c in sorted(st['compound_regions'], key=lambda c: -c['median_z_mm']))
        pet = [p for p in st['petioles'] if p.get('status') == 'fitted']
        self.stage('S3', DONE, f"겉껍질 {st['hull']['occupancy_cm3']} cm³ (사진 {len(st['views_used'])}장), 복엽 영역 {len(st['compound_regions'])}개({names}), "
                   f"줄기 {('맞춤(아래 줄기, 외곽 추적)' if st['stem'].get('method') == 'hull_trunk' else '맞춤') if st['stem'].get('status') == 'fitted' else '불가: ' + st['stem'].get('reason', '')}, 잎자루 {len(pet)}개",
                   views=st['views_used'], stem=st['stem'].get('status'))
        try:  # 3D stem axis projected into every posed photo (tools.stem_completion, 2026-09-29): a check, never a label
            from tools.stem_completion import complete
            sc = complete(self.session, self.seed, out / 'structure.json', self.out / 'stem_completion')
            self.stages['S3']['summary'] += (f", 줄기 투영: 포즈 사진 {len(sc['posed_photos'])}장, 제안 {sc['proposals']}개(가려진 부분 포함, 사람 확인 전)")
            self.stages['S3']['stem_completion'] = dict(proposals=sc['proposals'], independent=sc['independent_agreement'])
        except Exception as e:  # never blocks S3
            self.stages['S3']['stem_completion_error'] = f'{type(e).__name__}: {e}'
        try:  # stem/petiole diameter from the 2D polygons + 3D axis depth (tools.stem_thickness, 2026-09-29)
            from tools.stem_thickness import measure_structure
            th = measure_structure(self.session, self.seed, out / 'structure.json')
            write_json(self.out / 'stem_thickness.json', th)
            ms = th['main_stem']
            self.stages['S3']['summary'] += (f", 줄기 굵기 {ms['diameter_mm']} mm (폭이 일정한 사진 {ms['steady_photos']}/{ms['photos']}장)"
                                             if ms.get('status') == 'measured' else f", 줄기 굵기 불가({ms.get('reason', ms.get('status'))})")
            self.stages['S3']['stem_thickness'] = {k: ms.get(k) for k in ('status', 'diameter_mm', 'steady_photos', 'photos', 'steady_spread_pct')}
        except Exception as e:  # never blocks S3
            self.stages['S3']['stem_thickness_error'] = f'{type(e).__name__}: {e}'
        named = [c for c in st['compound_regions'] if not c.get('fragment')]
        if named and any(c['proposed_name'] for c in named) and not all(c.get('name_source') == 'human' for c in named):
            self.task(4, f'{self.name} 복엽 이름 제안(아래에서 위로 L01, L02 …, 전개 중 잎=맨 위) 확인. 사진에 이름이 적혀 있습니다; '
                         "고르고 '결정 파일 저장'", self.out.parent / 'NAMES_REVIEW.html')

    # S4
    def s4(self):
        sources = [rel(p) for p in self.cfg.get('decisions', [])]
        downloads = sorted(glob.glob(str(Path(self.g['downloads']) / f'cross_view_decisions_{self.name}_*.json')))
        sources += [Path(p) for p in downloads]
        sources = [p for p in sources if p and p.exists()]
        n_links = 0
        if sources:
            r = run_module(['tools.cross_view_identity_import', '--backup', str(self.seed), '--decisions', *map(str, sources),
                            '--batch', str(self.batch), '--out', str(self.out / 'identities')])
            self.backup = self.out / 'identities' / 'identities.backup.json'
            rep = read_json(self.out / 'identities' / 'identity_import_report.json')
            n_links = len(rep['applied'])
            vis = len(rep['visibility_applied'])
            conflicts = len(rep['conflicts'])
        if not getattr(self, 'mask_counts', {}).get('accepted') or not getattr(self, 'structure', None):
            self.stage('S4', WAIT if n_links == 0 else DONE, f'확인된 소엽 {n_links}장. 새 후보는 수락된 마스크와 S3가 있어야 만듭니다.')
            return
        args = ['tools.cross_view_candidates', '--session', str(self.session), '--backup', str(self.backup), '--batch', str(self.batch),
                '--structure', str(self.structure), '--out', str(self.out / 'candidates')]
        # feature-posed photos join S4 only after the user allowed them (human-check page, pose_candidates)
        feat = rel(self.cfg.get('feature_poses'))
        use_feat = (latest_human_checks(self.g).get('decisions') or {}).get('pose_candidates') == 'use_as_diagnostic'
        if use_feat and feat and feat.exists():
            args += ['--extra-poses', str(feat)]
            self.feature_poses_used = feat
        r = run_module(args + ['--decisions', *map(str, sources)])
        page = self.out / 'candidates' / 'review.html'
        pending = r.get('items', 0) + r.get('visibility_items', 0)
        self.stage('S4', WAIT if pending else DONE,
                   f"결정 파일 {len(sources)}개 → 확인된 소엽 {n_links}장" + (f', 보임 정도 반영 {vis}건, 충돌 {conflicts}건' if sources else '') +
                   f"; 새 질문: 같은 소엽 후보 {r.get('items', 0)}개, 보임 정도 {r.get('visibility_items', 0)}개" +
                   (f"; 특징점 포즈 사진 {len(r['feature_pose_views'])}장 포함(진단용)" if r.get('feature_pose_views') else ''),
                   review_page=str(page))
        if pending:
            self.task(2, f"{self.name} 소엽 대응 검토 {pending}개 (같은 소엽 후보 {r.get('items', 0)}, 보임 정도 {r.get('visibility_items', 0)}). "
                         f"페이지를 열고 고른 뒤 '결정 파일 저장' → 다운로드 폴더에 그대로 두면 다음 실행이 읽습니다.", page)

    # S5
    def s5(self):
        if not self.cfg.get('direction_labels'):
            self.stage('S5', WAIT, '모델 2(잎끝 방향) 라벨이 아직 없습니다.')
            self.task(3, f'{self.name} 모델 2 라벨: 모델 1 소엽 박스를 복사해 잎끝 방향 클래스(side_left/side_right/front/back)로 바꾼 export. '
                         '정면/후면 기준 한 줄을 먼저 정해 주세요.')
            return
        self.stage('S5', UNAVAILABLE, 'export는 설정됐지만 가져오기 도구는 첫 export를 보고 맞춥니다(형식 확인 필요).')

    # S6
    def s6(self):
        if self.backup == self.seed or not self.batch or not (self.batch / 'manifest.json').exists():
            self.stage('S6', WAIT, '확인된 소엽 ID가 없어 3D 근거 계산을 건너뜁니다.')
            return
        out = self.out / 'evidence'
        r = run_module(['tools.instance_workflow', '--operation', 'instance_fusion', '--session', str(self.original_session), '--backup', str(self.backup),
                        '--context', str(self.original_session / 'annotations.source.json'), '--batch', str(self.batch), '--out', str(out),
                        '--mode', 'diagnostic', '--scope', 'all'])
        ex = Counter(e['reason'] for e in read_json(out / 'evidence.json').get('exclusions', []))
        status = DONE if r.get('supported_voxels') else WAIT if ex.get('visibility_unknown') else UNAVAILABLE
        self.stage('S6', status, f"Document 06 진단 계산: {r.get('status')}, 지지 칸 {r.get('supported_voxels')}, 확인된 관측 {r.get('human_identity_confirmed')}, "
                   f"보임 정도 미정 {ex.get('visibility_unknown', 0)}", exclusions=dict(ex))

    # S7
    def s7(self):
        if not getattr(self, 'structure', None):
            self.stage('S7', UNAVAILABLE, 'S3 구조가 없습니다.')
            return
        args = ['tools.plant_hierarchy', '--session', str(self.session), '--backup', str(self.backup), '--structure', str(self.structure),
                '--out', str(self.out / 'hierarchy')]
        if self.batch and (self.batch / 'manifest.json').exists():
            args += ['--batch', str(self.batch)]
        if self.growth:
            args += ['--growth', str(self.growth)]
        cand = self.out / 'candidates' / 'candidates.json'
        if cand.exists():
            args += ['--proposals', str(cand)]
            if getattr(self, 'feature_poses_used', None):
                args += ['--extra-poses', str(self.feature_poses_used)]
        c = run_module(args)
        h = read_json(self.out / 'hierarchy' / 'hierarchy.json')
        cover = ', '.join(f"{x['proposed_name'] or '영역' + str(x['region'])} {x['coverage'] or len(x['leaflets'])}" for x in h['compound_leaves'])
        self.stage('S7', DONE, f"확인된 소엽 {c.get('confirmed_leaflets')}장 중 3D 영역 {c.get('with_region')}장; 복엽별 {cover}" +
                   (f"; 자동 제안 소엽 {c['proposed_leaflets']}장(사람 확인 전)" if c.get('proposed_leaflets') else ''),
                   viewer=str(self.out / 'hierarchy' / 'viewer.html'))

    # S8
    def s8(self):
        if not getattr(self, 'structure', None):
            self.stage('S8', UNAVAILABLE, 'S3 구조가 없어 형질을 계산하지 못합니다.')
            return
        from tools.plant_traits import plant_traits
        t = plant_traits(self.name, self.session, self.structure, self.batch, self.out / 'stem_thickness.json',
                         area_policy=self.cfg.get('area_policy'), view_grouping=self.cfg.get('view_grouping'),
                         capture_style=self.cfg.get('capture_style'))
        write_json(self.out / 'traits.json', t)
        top = f"{t['top_leaf_area_cm2']} cm²" if t['top_leaf_area_cm2'] is not None else '계산 근거 부족'
        self.stage('S8', DONE, f"대리 잎 면적 {t['leaf_area_proxy_cm2']} cm²({t['leaf_area_proxy_view']}, {t['leaf_area_proxy_photos']}장, "
                   f"수락 마스크 비율 {t['accepted_share_pct']}%), 위 사진 잎 {top}, 외곽 바닥 {t['hull_footprint_cm2']} cm², "
                   f"높이 {t['hull_height_mm']} mm, 줄기 {t['stem_diameter_mm']} mm; "
                   f"집계 상태 {t.get('aggregation_status', 'legacy_completeness_not_established')}",
                   traits=str(self.out / 'traits.json'))

    def run(self):
        for key in ('s0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8'):
            t = time.time()
            try:
                getattr(self, key)()
            except Exception as e:  # a failed stage is reported; later stages still run on what exists
                self.stage(key.upper(), FAILED, f'{type(e).__name__}: {e}', trace=traceback.format_exc()[-1500:])
            self.stages.setdefault(key.upper(), dict(status=UNAVAILABLE, summary='실행되지 않음'))['seconds'] = round(time.time() - t, 1)
        write_json(self.out / 'status.json', dict(plant=self.name, stages=self.stages, human_tasks=self.tasks,
                                                   validated_metric=False, suitable_for_ppfd=False))
        return self


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--plant', action='append', default=[])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--xl', action='store_true', help='Append static XL export and a separate handoff receipt')
    ap.add_argument('--groimp-core', type=Path, help='With --xl, verify using this installed GroIMP core.jar')
    ap.add_argument('--config', type=Path, default=CONFIG, help='Plant list (default tools/plant_pipeline_plants.json; '
                    'photo-only auto runs write their own)')
    a = ap.parse_args(argv)
    if a.groimp_core and not a.xl:
        ap.error('--groimp-core requires --xl')
    cfg = read_json(a.config)
    names = list(cfg['plants']) if a.all or not a.plant else a.plant
    out = (a.out or ROOT / "build" / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}").resolve()  # relative --out broke the summary links (10-01)
    out.mkdir(parents=True, exist_ok=False)
    checks = latest_human_checks(cfg)
    if checks:
        write_json(out / 'human_checks.json', checks)  # the decisions this run saw
    plants = [Plant(n, cfg['plants'][n], cfg, out).run() for n in names]
    lines = ['# 파이프라인 상태', '', f'실행: {out.name}. 모든 값은 진단용입니다(카메라 위치가 1 px 기준 미통과, 측정·광량 계산 입력 아님).', '']
    lines += ['| 단계 | ' + ' | '.join(p.name for p in plants) + ' |', '|---|' + '---|' * len(plants)]
    for s in ('S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'):
        lines.append(f'| {s} | ' + ' | '.join(STATUS_KO[p.stages.get(s, {}).get("status", UNAVAILABLE)] for p in plants) + ' |')
    for p in plants:
        lines += ['', f'## {p.name}', '']
        lines += [f"- **{s}** ({STATUS_KO[v['status']]}): {v['summary']}" for s, v in p.stages.items()]
        if p.stages.get('S7', {}).get('viewer'):
            lines.append(f"- 3D 보기: `{Path(p.stages['S7']['viewer']).relative_to(ROOT)}`")
    (out / 'STATUS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    try:  # contradictory S4 decisions leave a whole leaflet group out; a person resolves them on one page (2026-09-29)
        from tools.conflict_review import build as build_conflicts
        conflict_page = build_conflicts(out, a.config)
    except Exception as e:
        conflict_page = None
        (out / 'conflict_review_error.txt').write_text(f'{type(e).__name__}: {e}', encoding='utf-8')
    for p in plants:
        rep = out / p.name / 'identities' / 'identity_import_report.json'
        n = len(read_json(rep)['conflicts']) if rep.exists() else 0
        if n and conflict_page:
            p.task(1, f'{p.name} 짝짓기 충돌 {n}건 해결 (모순된 결정 때문에 해당 소엽 묶음 전체가 빠져 있음). '
                      "틀린 결정을 바꾸고 '결정 파일 저장'", conflict_page)
    try:  # S8 over all plants: traits.csv, calibration and light (tools.plant_traits)
        from tools.plant_traits import from_run, summarize
        traits = summarize(from_run(out), out, rel(cfg.get('measurements', 'measurements'))) if any(out.glob('*/traits.json')) else None
    except Exception as e:
        traits = None
        (out / 'traits_error.txt').write_text(f'{type(e).__name__}: {e}', encoding='utf-8')
    tasks = sorted(((t['priority'], p.name, t) for p in plants for t in p.tasks), key=lambda x: (x[0], x[1]))
    tl = ['# 사람이 해야 할 작업', '', '끝나면 `python -X utf8 -m tools.plant_pipeline --all` 을 다시 실행하면 결과가 반영됩니다.', '']
    if cfg.get('goal', 'whole_plant') == 'whole_plant':
        tl += ['## 필수 (개체 잎 면적·PPFD·DLI 에 필요한 것)', '']
        tl += [f'{n}. {t}' for n, t in enumerate((traits or {}).get('human_tasks') or ['없음'], 1)]
        tl += ['', '## 선택 (잎 하나하나 단위 결과가 필요할 때만)', '']
    for n, (pri, plant, t) in enumerate(tasks, 1):
        tl.append(f"{n}. [{plant}] {t['text']}" + (f"\n   - 위치: `{t['where']}`" if t['where'] else ''))
    pending = {k: v for k, v in (checks.get('decisions') or {}).items() if v}
    if pending:
        tl += ['', '## 받은 결정 (코드 변경이 필요한 것은 Claude 가 반영)', '']
        tl += [f'- {k}: {json.dumps(v, ensure_ascii=False)}' for k, v in pending.items()]
    (out / 'HUMAN_TASKS.md').write_text('\n'.join(tl) + '\n', encoding='utf-8')
    names_page(out, plants, checks)
    try:  # the 3D status site for every plant of this run (tools.plant_site); a failure here never fails the run
        from tools.plant_site import build as build_site
        build_site(out, config=a.config)
    except Exception as e:
        (out / 'site_error.txt').write_text(f'{type(e).__name__}: {e}', encoding='utf-8')
    delivery = None
    if a.xl:
        from tools.plant_xl_handoff import prepare
        delivery = prepare(out, out / 'xl_handoff', names, a.groimp_core)
    print(json.dumps(dict(out=str(out), status={p.name: {s: v['status'] for s, v in p.stages.items()} for p in plants},
                          xl_handoff=delivery['status'] if delivery else 'not_requested'), ensure_ascii=False))
    return int(delivery is not None and delivery['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
