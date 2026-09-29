"""Local rebuild server: current editor, loopback/token checks, path limits, failures, preserved inputs."""
from contextlib import contextmanager
import http.client
import json
import threading
import time

import pytest

from tools import serve_leaf_edit_session as tool
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case  # noqa: F401  (fixture)
from tools.tests.test_rebuild_leaf_edit_session import prepared  # noqa: F401  (fixture)


@contextmanager
def running(service):
    server = tool.ThreadingHTTPServer(('127.0.0.1', 0), tool.handler_for(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=60)
    base = {'Host': f'127.0.0.1:{port}'}
    base.update(headers or {})
    connection.request(method, path, body=body, headers=base)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, data


def post_backup(port, service, backup, **extra):
    headers = {'Origin': f'http://127.0.0.1:{port}', 'X-Local-Token': service.token, 'Content-Type': 'application/json'}
    headers.update(extra)
    status, data = request(port, 'POST', '/api/rebuild', json.dumps(backup).encode(), headers)
    return status, json.loads(data)


def wait(port, service, job_id):
    for _ in range(600):
        status, data = request(port, 'GET', f'/api/jobs/{job_id}', headers={'X-Local-Token': service.token})
        job = json.loads(data)
        if job['status'] != 'running':
            return job
        time.sleep(0.1)
    raise AssertionError('job did not finish')


@pytest.fixture
def service(prepared):
    session, backup_path, context, out, *_ = prepared
    return tool.EditService(session, context, out.parent / 'runs', backup_path), prepared


def test_serves_current_editor_not_the_stale_session_copy(service):
    svc, (session, backup_path, *_ ) = service
    index = session / 'index.html'
    index.write_text(index.read_text(encoding='utf-8').replace('<header>', '<header>STALE_COPY_MARKER', 1), encoding='utf-8')
    with running(svc) as port:
        status, page = request(port, 'GET', '/')
        text = page.decode('utf-8')
        assert status == 200 and 'STALE_COPY_MARKER' not in text
        assert 'id="toolLeafBox"' in text and 'id="rebuildLocal"' in text and svc.token in text
        assert tool.prepare_tool.LOCAL_GUARD in text and tool.prepare_tool.CSP in text
        status, seed = request(port, 'GET', '/seed.backup.json')
        assert status == 200 and seed == backup_path.read_bytes()  # explicit initial backup, not the older seed
        status, script = request(port, 'GET', '/bootstrap.js')
        assert status == 200 and script.decode('utf-8') == tool.prepare_tool.BOOTSTRAP_JS
        assert request(port, 'GET', '/', headers={'Host': 'evil.example:80'})[0] == 403


def test_instance_job_auth_snapshot_failure_and_clustering_not_exposed(service, monkeypatch):
    from types import SimpleNamespace
    from tools import instance_workflow
    svc, (_, _, _, _, _, backup, _) = service
    svc.mask_batch = SimpleNamespace(root=svc.runs/'mask_batch')
    def fake_run(operation, session, backup_path, context, batch_root, out, **kwargs):
        assert common.read_json(backup_path) == backup
        out.mkdir(); common.write_json(out/'result.json',dict(status='unavailable_no_qualified_poses'))
        common.write_json(out/'manifest.json',dict(operation=operation))
        return dict(status='unavailable_no_qualified_poses')
    monkeypatch.setattr(instance_workflow,'run',fake_run)
    with running(svc) as port:
        headers={'Origin':f'http://127.0.0.1:{port}','X-Local-Token':svc.token,'Content-Type':'application/json'}
        body=json.dumps(dict(operation='instance_fusion',backup=backup))
        assert request(port,'POST','/api/instances/run',body,{'Content-Type':'application/json'})[0]==403
        code, data=request(port,'POST','/api/instances/run',body,headers)
        assert code==202
        job=wait(port,svc,json.loads(data)['job_id'])
        assert job['status']=='complete' and job['evidence_status']=='unavailable_no_qualified_poses'
        assert request(port,'GET',job['result_url'])[0]==200
        assert request(port,'GET','/api/instances/runs')[0]==403
        assert request(port,'GET','/api/instances/runs',headers=headers)[0]==200
        body=json.dumps(dict(operation='instance_clustering',backup=backup))
        assert request(port,'POST','/api/instances/run',body,headers)[0]==400
        assert request(port,'POST','/api/instances/staleness',json.dumps(dict(job_id='../escape',backup=backup)),headers)[0]==400


def test_rejects_foreign_origin_missing_token_bad_body_and_path_escape(service):
    svc, (session, backup_path, *_ ) = service
    backup = common.read_json(backup_path)
    with running(svc) as port:
        assert post_backup(port, svc, backup, Origin='http://evil.example')[0] == 403
        assert post_backup(port, svc, backup, **{'X-Local-Token': 'wrong'})[0] == 403
        assert post_backup(port, svc, backup, **{'Content-Type': 'text/plain'})[0] == 400
        assert post_backup(port, svc, ['not', 'a', 'backup'])[0] == 400
        assert request(port, 'GET', '/api/jobs/x')[0] == 403
        for path in ('/results/..%2F..%2Fcapture.json', '/..%2F..%2Fcapture.json', '/results/%2e%2e/editor/seed.backup.json'):
            assert request(port, 'GET', path)[0] == 404, path
    assert not list(svc.runs.iterdir())


def test_rebuild_job_snapshots_backup_preserves_inputs_and_serves_result(service):
    svc, (session, backup_path, context, *_ ) = service
    inputs = [backup_path, context, session / 'seed.backup.json', session / 'capture.json']
    before = [common.file_hash(p) for p in inputs]
    backup = common.read_json(backup_path)
    with running(svc) as port:
        status, job = post_backup(port, svc, backup)
        assert status == 202 and job['status'] == 'running' and job['job_id'].startswith('run_')
        final = wait(port, svc, job['job_id'])
        assert final['status'] == 'complete' and final['input_files_changed'] is False
        assert final['validated_metric'] is False and final['cuboids_available'] == 0
        status, page = request(port, 'GET', final['result_url'])
        assert status == 200 and '소엽' in page.decode('utf-8')
        status, second = post_backup(port, svc, backup)
        assert status == 202 and second['job_id'] != job['job_id']
        wait(port, svc, second['job_id'])
    folder = svc.runs / job['job_id']
    assert common.read_json(folder / 'editor.backup.json') == backup
    assert (folder / 'result/leaflet_extents.csv').is_file()
    assert common.read_json(folder / 'job.json')['backup_sha256'] == common.file_hash(folder / 'editor.backup.json')
    assert [common.file_hash(p) for p in inputs] == before


def test_failed_job_is_reported_and_its_backup_retained(service):
    svc, (session, backup_path, *_ ) = service
    backup = common.read_json(backup_path)
    backup['session_id'] = 'another_session'
    with running(svc) as port:
        status, job = post_backup(port, svc, backup)
        final = wait(port, svc, job['job_id'])
    assert status == 202 and final['status'] == 'failed' and 'identity mismatch' in final['error']
    assert common.read_json(svc.runs / job['job_id'] / 'job.json')['status'] == 'failed'
    assert common.read_json(svc.runs / job['job_id'] / 'editor.backup.json')['session_id'] == 'another_session'


def test_concurrent_submission_is_refused_while_a_job_runs(service, monkeypatch):
    svc, (session, backup_path, *_ ) = service
    release = threading.Event()
    monkeypatch.setattr(tool, 'rebuild', lambda *args: (release.wait(10), (_ for _ in ()).throw(RuntimeError('stopped')))[1])
    backup = common.read_json(backup_path)
    first = svc.submit(backup)
    second = svc.submit(backup)
    release.set()
    assert first[0] == 202 and second[0] == 409
    for _ in range(100):
        if svc.status(first[1]['job_id'])['status'] != 'running':
            break
        time.sleep(0.05)
    assert svc.status(first[1]['job_id'])['status'] == 'failed'


def test_runs_directory_must_be_under_build_and_outside_the_session(prepared):
    session, backup_path, context, out, *_ = prepared
    with pytest.raises(common.StudyError, match='under build'):
        tool.EditService(session, context, out.parent.parent / 'elsewhere', backup_path)
    with pytest.raises(common.StudyError, match='inside the prepared session'):
        tool.EditService(session, context, session / 'runs', backup_path)


def test_http_rebuild_attaches_existing_surfaces_and_hides_them_after_edit(prepared):
    from copy import deepcopy
    from tools.tests.test_leaflet_surface_attachment import patch_run, triangulated, KEY
    from tools import rebuild_leaf_edit_session as rebuild_tool

    session, backup_path, context, out, _, backup, _ = prepared
    common.write_json(backup_path, backup)
    rebuild_tool.rebuild(session, backup_path, context, out / 'baseline')
    patches = patch_run(out / 'patches', common.file_hash(out / 'baseline/editor_point_depths.csv'),
                        triangulated(out / 'baseline'))
    before = common.file_hash(backup_path)
    svc = tool.EditService(session, context, out.parent / 'surface_runs', backup_path, patches=patches)
    with running(svc) as port:
        status, job = post_backup(port, svc, backup)
        assert status == 202
        current = wait(port, svc, job['job_id'])
        assert current['status'] == 'complete'
        assert current['attached_surface_status'] == rebuild_tool.SURFACE_CURRENT
        assert current['attached_surface_count'] == 1
        edited = deepcopy(backup)
        edited['variants']['__all__']['leaflets'][KEY]['pts']['b0']['photo_1.png'][0] += 9
        status, job = post_backup(port, svc, edited)
        assert status == 202
        stale = wait(port, svc, job['job_id'])
        assert stale['status'] == 'complete'
        assert stale['attached_surface_status'] == rebuild_tool.SURFACE_STALE
        url = stale['result_url'].replace('/index.html', '/labels/index.html')
        status, page = request(port, 'GET', url)
        assert status == 200 and '보간 부분 면 0개 삼각형' in page.decode('utf-8')
    assert common.file_hash(backup_path) == before
