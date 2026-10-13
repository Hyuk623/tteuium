"""Serve a prepared leaf editor and rebuild saved labels locally on explicit request.

python -m tools.serve_leaf_edit_session --session build/.../edit_session06
  --context build/.../manual_candidates.review09.json --runs build/.../editor_runs
  --initial-backup build/.../third_view_revised.backup.json --port 8821

The editor page is rendered from the CURRENT tools/leaf_point_annotator.html on
every request (with the session's own prepared configuration), so an older copy
in the session folder is never served. Port 8821 is the default because browser
storage is per origin: the prepared sessions were first opened at
http://127.0.0.1:8821, and the same origin keeps that browser's saved labels.
The initial backup is offered only when this browser has no saved work.
Each rebuild snapshots the posted backup into a new run folder under build/.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uuid

from tools import prepare_leaf_edit_session as prepare_tool
from tools.leaf_light import common
from tools.rebuild_leaf_edit_session import checked_inputs, rebuild
from tools import leaflet_segmenter

EDITOR_SOURCE = Path(__file__).with_name('leaf_point_annotator.html')
MAX_BACKUP_BYTES = 16 * 1024 * 1024
DEFAULT_PORT = 8821
CONFIG_PATTERN = re.compile(r'<script id="preparedSessionConfig" type="application/json">(.*?)</script>', re.S)


class EditService:
    def __init__(self, session: Path, context: Path, runs: Path, initial_backup: Path | None = None,
                 segmenter=None, patches: Path | None = None, side_poses: Path | None = None,
                 request: Path | None = None, mask_batch: Path | None = None,
                 compound_mask_batch: Path | None = None):
        self.session, self.context, self.runs = (p.resolve() for p in (session, context, runs))
        self.patches = patches.resolve() if patches is not None else None
        self.side_poses = side_poses.resolve() if side_poses is not None else None
        self.request = request.resolve() if request is not None else None
        self.initial_backup = (initial_backup or self.session/'seed.backup.json').resolve()
        checked_inputs(self.session, self.initial_backup, self.context)
        if not self.runs.is_relative_to(common.BUILD.resolve()) or self.runs == common.BUILD.resolve():
            raise common.StudyError('Runs must stay in a dedicated directory under build')
        if self.runs.is_relative_to(self.session):
            raise common.StudyError('Runs must not be written inside the prepared session')
        found = CONFIG_PATTERN.search((self.session/'index.html').read_text(encoding='utf-8'))
        if not found:
            raise common.StudyError('Prepared session configuration is missing')
        self.config = json.loads(found.group(1))
        seed = common.read_json(self.session/'seed.backup.json')
        if (self.config.get('session_id'), self.config.get('plant_id')) != (seed['session_id'], seed['plant_id']):
            raise common.StudyError('Prepared session configuration differs from its seed')
        self.html()  # Fail at start-up, not on first page load, if the editor cannot be localized.
        self.runs.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.jobs: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.segment_lock = threading.Lock()
        self.segmenter = segmenter or leaflet_segmenter.UnavailableSegmenter(
            'No segmentation model configured; manual labeling is unaffected')
        capture = common.read_json(self.session/'capture.json')
        self.photos = {Path(f['image_file']).name.lower(): (self.session/f['image_path'], f['sha256'], f['image_file'])
                       for f in capture['frames']}
        self.mask_batch = None
        if mask_batch is not None:
            from tools.leaflet_mask_batch import Batch
            self.mask_batch = Batch(mask_batch, self.segmenter, self.segment_lock)
            if self.mask_batch.session.resolve() != self.session:
                raise common.StudyError('Mask batch belongs to another prepared session')
        self.compound_mask_batch = None
        if compound_mask_batch is not None:
            from tools.leaflet_mask_batch import Batch
            self.compound_mask_batch = Batch(compound_mask_batch, self.segmenter, self.segment_lock)
            if (self.compound_mask_batch.session.resolve() != self.session or
                    self.compound_mask_batch.manifest.get('organ_class') != 'compoundleaves'):
                raise common.StudyError('Compound batch belongs to another session/class')

    def segment(self, request: dict) -> tuple[int, dict]:
        """One prompted proposal; nothing is written to labels or disk."""
        info = self.segmenter.info()
        if not info.get('available'):
            return 503, dict(error='AI 제안을 사용할 수 없습니다: ' + str(info.get('reason')), model=info)
        photo = self.photos.get(re.split(r'[\\/]', str(request.get('image_file', '')))[-1].lower())
        if photo is None:
            return 400, dict(error='Unknown session photograph')
        prompts = request.get('prompts')
        if not isinstance(prompts, dict):
            return 400, dict(error='Prompts are required')
        with self.segment_lock:
            try:
                result = leaflet_segmenter.propose(self.segmenter, photo[0], photo[1], prompts)
            except (common.StudyError, ValueError, TypeError) as exc:
                return 400, dict(error=str(exc), model=info)
        result.update(image_file=photo[2], image_sha256=photo[1], target_leaf_key=request.get('target_leaf_key'))
        return 200, result

    def segment_automatic(self, request: dict) -> tuple[int, dict]:
        """Class-agnostic mask drafts for the requested photographs; writes nothing."""
        info = self.segmenter.info()
        if not info.get('available') or not info.get('automatic'):
            return 503, dict(error='자동 제안을 사용할 수 없습니다: ' + str(info.get('reason') or '이 백엔드에는 자동 마스크 기능이 없습니다'), model=info)
        names = request.get('image_files')
        if not isinstance(names, list) or not 1 <= len(names) <= 8:
            return 400, dict(error='사진을 1~8장 선택하세요')
        photos = []
        for name in names:
            photo = self.photos.get(re.split(r'[\/]', str(name))[-1].lower())
            if photo is None:
                return 400, dict(error='Unknown session photograph: ' + str(name))
            photos.append(photo)
        results = []
        with self.segment_lock:
            for path, sha, image_file in photos:
                try:
                    results.append(leaflet_segmenter.propose_automatic(self.segmenter, path, sha, image_file))
                except (common.StudyError, ValueError, TypeError) as exc:
                    results.append(dict(image_file=image_file, image_sha256=sha, error=str(exc), candidates=[]))
        return 200, dict(mode='automatic', photos=results, model=info,
                         note='Unassigned class-agnostic drafts; assign or reject each one.')

    def submit(self, backup: dict) -> tuple[int, dict]:
        with self.lock:
            if any(j['status'] == 'running' for j in self.jobs.values()):
                return 409, dict(error='이미 계산 중입니다. 현재 작업이 끝난 후 다시 요청하세요.')
            job_id = datetime.now().strftime('run_%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:8]
            folder = self.runs/job_id
            folder.mkdir()
            common.write_json(folder/'editor.backup.json', backup)
            job = dict(job_id=job_id, status='running', validated_metric=False,
                       backup_sha256=common.file_hash(folder/'editor.backup.json'),
                       editor_source_sha256=common.file_hash(EDITOR_SOURCE),
                       started_at=datetime.now().astimezone().isoformat(timespec='seconds'))
            common.write_json(folder/'job.json', job)
            self.jobs[job_id] = job
            threading.Thread(target=self._run, args=(job_id, folder), daemon=True).start()
            return 202, deepcopy(job)

    def _run(self, job_id: str, folder: Path) -> None:
        final = dict(self.jobs[job_id])
        try:
            result = rebuild(self.session, folder/'editor.backup.json', self.context, folder/'result', self.patches,
                             self.side_poses, self.request)
            final.update(status='complete', result_url=f'/results/{job_id}/result/index.html',
                         editor_observations=result['editor_observations'], modeled_leaflets=result['modeled_leaflets'],
                         leaflet_bbox_observations=result['leaflet_bbox_observations'],
                         cuboids_available=result['cuboids_available'], input_files_changed=result['input_files_changed'],
                         attached_surface_status=result['attached_surface_status'],
                         attached_surface_count=result['attached_surface_count'],
                         side_pose_status=result['side_pose_status'],
                         side_pose_candidates=result['side_pose_candidates'],
                         side_poses_used_in_hybrid=result['side_poses_used_in_hybrid'],
                         side_pose_stale=result['side_pose_stale'],
                         hybrid_points_added=result['hybrid']['points_added'],
                         hybrid_points_changed=result['hybrid']['points_changed'],
                         hybrid_note=result['hybrid_note'],
                         reference_status=result['reference_status'],
                         reference_finding_counts=result.get('reference_finding_counts'),
                         route_summary=result.get('route_summary'))
        except Exception as exc:  # A failed job must be reported, never left running.
            final.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            if (folder/'result').exists():
                common.write_json(folder/'result'/'REBUILD_FAILED_INCOMPLETE.json', final)
        final['finished_at'] = datetime.now().astimezone().isoformat(timespec='seconds')
        common.write_json(folder/'job.json', final)
        with self.lock:
            self.jobs[job_id] = final

    def status(self, job_id: str) -> dict | None:
        with self.lock:
            return deepcopy(self.jobs.get(job_id))

    def instance_runs(self) -> list[dict]:
        """Discover completed snapshots after a server restart without changing them."""
        records = {}
        for path in self.runs.glob('run_*/job.json'):
            job = common.read_json(path)
            if job.get('operation') in ('sensitivity_sweep', 'instance_fusion'):
                if job.get('status') == 'running' and job['job_id'] not in self.jobs:
                    job = {**job, 'status': 'interrupted', 'error': 'Server stopped before completion'}
                records[job['job_id']] = job
        with self.lock:
            records.update({k: deepcopy(v) for k, v in self.jobs.items() if v.get('operation')})
        return sorted(records.values(), key=lambda x: x['job_id'], reverse=True)

    def submit_instance(self, request: dict) -> tuple[int, dict]:
        from tools.instance_workflow import OPERATIONS
        if self.mask_batch is None or request.get('operation') not in OPERATIONS:
            raise common.StudyError('Document 06 operation / leaflet mask batch required')
        if not isinstance(request.get('backup'), dict) or not isinstance(request['backup'].get('variants'), dict):
            raise common.StudyError('Current editor backup required')
        with self.lock:
            if any(j['status'] == 'running' for j in self.jobs.values()):
                return 409, dict(error='현재 계산을 마친 후 실행하세요.')
            job_id = datetime.now().strftime('run_%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:8]
            folder = self.runs/job_id; folder.mkdir()
            common.write_json(folder/'editor.backup.json', request['backup'])
            common.write_json(folder/'request.json', {k: v for k, v in request.items() if k != 'backup'})
            job = dict(job_id=job_id, status='running', operation=request['operation'], validated_metric=False,
                       suitable_for_ppfd=False, started_at=datetime.now().astimezone().isoformat())
            common.write_json(folder/'job.json', job); self.jobs[job_id] = job
            threading.Thread(target=self._run_instance, args=(job_id, folder), daemon=True).start()
            return 202, deepcopy(job)

    def _run_instance(self, job_id: str, folder: Path) -> None:
        from tools.instance_workflow import run
        final = dict(self.jobs[job_id])
        try:
            request = common.read_json(folder/'request.json')
            result = run(request['operation'], self.session, folder/'editor.backup.json', self.context,
                         self.mask_batch.root, folder/'result', scope=request.get('scope', 'pilot'),
                         mode=request.get('mode', 'strict'), reference=request.get('reference'), frozen=request.get('frozen'))
            final.update(status='complete', evidence_status=result['status'],
                         result_url=f'/results/{job_id}/result/result.json',
                         manifest_url=f'/results/{job_id}/result/manifest.json')
        except Exception as exc:
            final.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        final['finished_at'] = datetime.now().astimezone().isoformat()
        common.write_json(folder/'job.json', final)
        with self.lock: self.jobs[job_id] = final

    def instance_action(self, action: str, request: dict) -> dict:
        from tools.instance_workflow import stale_reasons, freeze_parameters
        jobs = {j['job_id']: j for j in self.instance_runs()}
        identity = request.get('job_id')
        if identity not in jobs or jobs[identity]['status'] != 'complete':
            raise common.StudyError('Completed Document 06 job required')
        folder = self.runs/identity/'result'
        if action == 'staleness':
            reasons = stale_reasons(folder, self.mask_batch, request['backup'])
            return dict(stale=bool(reasons), reasons=reasons)
        if action == 'freeze':
            target = self.runs/('freeze_'+uuid.uuid4().hex[:12])/'frozen_parameters.json'
            frozen = freeze_parameters(folder, target)
            return dict(frozen=frozen, url='/results/'+target.relative_to(self.runs).as_posix())
        raise common.StudyError('Unknown evidence action')

    def html(self) -> bytes:
        source = EDITOR_SOURCE.read_text(encoding='utf-8')
        text = prepare_tool.local_html(source, self.config, self.session)
        controls = '''<section style="padding:12px;background:#e9f3eb;color:#173728"><strong>수정한 라벨로 3D·깊이 다시 계산</strong>
<p>현재 화면의 라벨을 이 컴퓨터의 새 실행 폴더에 백업한 뒤 새 결과를 만듭니다. 기존 작업·백업·결과는 바꾸지 않습니다. 다시 계산에는 딥러닝을 쓰지 않습니다.</p>
<button id="rebuildLocal" type="button">현재 라벨로 다시 계산</button> <span id="rebuildState" role="status"></span>
<a id="rebuildResult" target="_blank" rel="noopener" hidden>새 3D·사진 결과 열기</a></section>'''
        token = json.dumps(self.token if hasattr(self, 'token') else '')
        script = f'<script id="localRebuildToken" type="application/json">{token}</script><script src="/__rebuild_client.js"></script>'
        if getattr(self, 'mask_batch', None) is not None:
            script += '<script src="/__mask_preview_math.js"></script><script src="/__mask_batch.js"></script><script src="/__instance_workflow.js"></script>'
        if text.count('</header>') != 1 or text.count('</html>') != 1:
            raise common.StudyError('Unexpected editor layout; rebuild controls need review')
        return text.replace('</header>', '</header>'+controls, 1).replace('</html>', script+'</html>').encode('utf-8')


def handler_for(service: EditService):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _host_allowed(self) -> bool:
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def _json(self, status: int, value: dict) -> None:
            self._bytes(status, json.dumps(value, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

        def _bytes(self, status: int, body: bytes, mime: str) -> None:
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(body)

        def _file(self, root: Path, relative: str) -> None:
            path = (root/relative).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                self._json(404, dict(error='File not found'))
                return
            self._bytes(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or 'application/octet-stream')

        def do_GET(self):
            if not self._host_allowed():
                self._json(403, dict(error='Loopback host required')); return
            path = unquote(urlsplit(self.path).path)
            try:
                if path in ('/', '/index.html'):
                    self._bytes(200, service.html(), 'text/html; charset=utf-8')
                elif path == '/__rebuild_client.js':
                    self._file(Path(__file__).parent, 'leaf_rebuild_client.js')
                elif path == '/__mask_batch.js':
                    self._file(Path(__file__).parent, 'leaflet_mask_batch.js')
                elif path == '/__mask_preview_math.js':
                    self._file(Path(__file__).parent, 'mask_preview_math.js')
                elif path == '/__instance_workflow.js':
                    self._file(Path(__file__).parent, 'instance_workflow.js')
                elif path == '/api/instances/runs':
                    if self.headers.get('X-Local-Token') != service.token:
                        self._json(403, dict(error='Local session token required')); return
                    self._json(200, dict(jobs=service.instance_runs()))
                elif path == '/bootstrap.js':
                    self._bytes(200, prepare_tool.BOOTSTRAP_JS.encode('utf-8'), 'text/javascript; charset=utf-8')
                elif path == '/seed.backup.json':
                    self._bytes(200, service.initial_backup.read_bytes(), 'application/json')
                elif path.startswith('/api/mask-batch/'):
                    if self.headers.get('X-Local-Token') != service.token:
                        self._json(403, dict(error='Local session token required')); return
                    kind = parse_qs(urlsplit(self.path).query).get('organ_class', ['leaflet'])[0]
                    if kind not in ('leaflet', 'compoundleaves'):
                        self._json(400, dict(error='Unknown organ class')); return
                    batch = service.mask_batch if kind == 'leaflet' else getattr(service, 'compound_mask_batch', None)
                    if batch is None:
                        self._json(404, dict(error='Mask batch not configured')); return
                    action = path.removeprefix('/api/mask-batch/')
                    if action == 'status':
                        status = batch.status()
                        status['available_classes'] = ['leaflet'] + (['compoundleaves'] if getattr(service, 'compound_mask_batch', None) else [])
                        self._json(200, status)
                    elif action == 'queue':
                        self._json(200, dict(items=batch.queue()))
                    elif action.startswith('item/'):
                        self._json(200, batch.detail(action.removeprefix('item/')))
                    elif action.startswith('mask/'):
                        self._bytes(200, batch.png(action.removeprefix('mask/')), 'image/png')
                    elif action.startswith('logits/'):
                        self._bytes(200, batch.preview_logits(action.removeprefix('logits/')), 'application/octet-stream')
                    else:
                        self._json(404, dict(error='Unknown batch resource'))
                elif path == '/api/segmenter':
                    if self.headers.get('X-Local-Token') != service.token:
                        self._json(403, dict(error='Local session token required')); return
                    self._json(200, service.segmenter.info())
                elif path.startswith('/api/jobs/'):
                    if self.headers.get('X-Local-Token') != service.token:
                        self._json(403, dict(error='Local session token required')); return
                    job = service.status(path.removeprefix('/api/jobs/'))
                    self._json(200 if job else 404, job or dict(error='Unknown job'))
                elif path.startswith('/results/'):
                    self._file(service.runs, path.removeprefix('/results/'))
                else:
                    self._file(service.session, path.lstrip('/'))
            except common.StudyError as exc:
                self._json(500, dict(error=str(exc)))

        def do_POST(self):
            # Read only a bounded body before an early rejection. Closing with unread
            # request bytes can reset TCP on Windows and discard the 400/403 reply.
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BACKUP_BYTES:
                    self._json(400, dict(error='Expected JSON body, maximum 16 MiB')); return
                self.connection.settimeout(10)
                raw_body = self.rfile.read(length)
                if len(raw_body) != length:
                    self._json(400, dict(error='Incomplete request body')); return
            except (ValueError, OSError):
                self._json(400, dict(error='Invalid or incomplete request body')); return
            if (not self._host_allowed() or self.headers.get('Origin') != 'http://'+self.headers.get('Host', '')
                    or self.headers.get('X-Local-Token') != service.token):
                self._json(403, dict(error='Same local editor and session token required')); return
            if self.path not in ('/api/rebuild', '/api/segment', '/api/segment_automatic',
                                  '/api/mask-batch/start', '/api/mask-batch/stop',
                                  '/api/mask-batch/review', '/api/mask-batch/export',
                                  '/api/instances/run', '/api/instances/staleness', '/api/instances/freeze'):
                self._json(404, dict(error='Unknown action')); return
            try:
                if self.headers.get_content_type() != 'application/json':
                    raise ValueError('Expected JSON backup, maximum 16 MiB')
                backup = json.loads(raw_body)
                if self.path.startswith('/api/instances/'):
                    if not isinstance(backup, dict): raise ValueError('Expected instance request')
                    action = self.path.rsplit('/', 1)[1]
                    if action == 'run': self._json(*service.submit_instance(backup))
                    else: self._json(200, service.instance_action(action, backup))
                    return
                if self.path.startswith('/api/mask-batch/'):
                    if not isinstance(backup, dict) or service.mask_batch is None:
                        raise ValueError('Mask batch is not configured or request is invalid')
                    kind = backup.get('organ_class', 'leaflet')
                    if kind not in ('leaflet', 'compoundleaves'):
                        raise ValueError('Unknown organ class')
                    batch = service.mask_batch if kind == 'leaflet' else getattr(service, 'compound_mask_batch', None)
                    if batch is None:
                        raise ValueError('This organ class has no prepared batch')
                    action = self.path.rsplit('/', 1)[1]
                    if action == 'start':
                        result = batch.start(bool(backup.get('pilot', False)), bool(backup.get('retry_failed', False)),
                                             identity=backup.get('id'))
                    elif action == 'stop':
                        result = batch.stop()
                    elif action == 'review':
                        result = batch.review(backup.get('id'), backup)
                    else:
                        result = batch.export()
                    self._json(200, result); return
                if self.path in ('/api/segment', '/api/segment_automatic'):
                    if not isinstance(backup, dict):
                        raise ValueError('Expected segmentation request')
                    handler = service.segment if self.path == '/api/segment' else service.segment_automatic
                    self._json(*handler(backup)); return
                if not isinstance(backup, dict) or not isinstance(backup.get('variants'), dict):
                    raise ValueError('Expected editor backup')
            except (ValueError, UnicodeError) as exc:
                self._json(400, dict(error=str(exc))); return
            status, job = service.submit(backup)
            self._json(status, job)
    return Handler


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for key in ('session', 'context', 'runs'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--initial-backup', type=Path, help='Offered only when the browser has no saved work for this session.')
    p.add_argument('--port', type=int, default=DEFAULT_PORT)
    p.add_argument('--patches', type=Path, help='Attach an existing partial-surface run; edited depths mark old surfaces stale. No inference is run.')
    p.add_argument('--side-poses', type=Path, help='Attach diagnostic leaflet-landmark side-camera candidates; the ChArUco baseline is rebuilt unchanged beside them.')
    p.add_argument('--request', type=Path, help='Reconstruction request JSON naming the growth/annotation/capture references to consult (tools.reconstruction_request).')
    p.add_argument('--segmenter', choices=['unavailable', 'sam2', 'mock'], default='unavailable',
                   help='AI proposals backend. mock = deterministic test shapes, not a model.')
    p.add_argument('--segmenter-config', type=Path, help='JSON config for --segmenter sam2 (python -m tools.leaflet_segmenter --write-sam2-config PATH)')
    p.add_argument('--mask-batch', type=Path, help='Attach an existing per-annotation mask batch to this editor.')
    p.add_argument('--compound-mask-batch', type=Path, help='Attach a separate compound-leaf mask batch for class switching.')
    a = p.parse_args()
    service = EditService(a.session, a.context, a.runs, a.initial_backup,
                          leaflet_segmenter.load_segmenter(a.segmenter, a.segmenter_config), patches=a.patches,
                          side_poses=a.side_poses, request=a.request, mask_batch=a.mask_batch,
                          compound_mask_batch=a.compound_mask_batch)
    server = ThreadingHTTPServer(('127.0.0.1', a.port), handler_for(service))
    print(f'Local leaf editor: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
