"""Terminal XL delivery must retain upstream gaps rather than report reconstruction success."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import plant_xl_handoff as xl
from tools import plant_pipeline as pipeline
from tools.leaf_light import common
from tools.tests.test_groimp_structure_export import fixture_snapshot


def test_delivery_keeps_hull_stem_single_view_and_failed_s6(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    run = fixture_snapshot(tmp_path / 'input')
    hierarchy = run / 'DT-001/hierarchy/hierarchy.json'
    h = common.read_json(hierarchy)
    h['stem'].update(method='hull_trunk', diameter_mm=None)
    h['compound_leaves'][0]['petiole'] = dict(status='fitted', views=['v1.png'],
        near_end=[0, 0, 20], far_end=[10, 0, 20], length_two_view_mm=None, extent_any_view_mm=10)
    common.write_json(hierarchy, h)
    before = {p: common.file_hash(p) for p in (tmp_path / 'input').rglob('*') if p.is_file()}
    report = xl.prepare(run, tmp_path / 'out')
    entry = report['plants']['DT-001']
    assert report['status'] == 'generated_not_runtime_verified'
    assert not entry['groimp_verified'] and entry['upstream_open']['S6']['status'] == 'failed'
    assert entry['stem_evidence'][0]['method'] == 'hull_trunk'
    assert entry['stem_evidence'][0]['diameter_mm'] is None
    assert len(entry['limited_sub_stems']) == 1
    assert entry['sub_stem_evidence'][0]['length_two_view_mm'] is None
    assert not entry['geometry_counts'].get('leaf_mesh')
    assert all(common.file_hash(p) == digest for p, digest in before.items())


def test_missing_plant_is_failure_not_silently_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    run = fixture_snapshot(tmp_path / 'input')
    report = xl.prepare(run, tmp_path / 'out', ['DT-001', 'missing'])
    assert report['status'] == 'failed'
    assert report['plants']['DT-001']['status'] == 'generated_not_runtime_verified'
    assert report['plants']['missing']['status'] == 'failed'
    assert (tmp_path / 'out/CLAUDE_README.md').is_file()


def test_failed_compilation_is_not_verified(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    run = fixture_snapshot(tmp_path / 'input')
    monkeypatch.setattr(xl, 'verify', lambda *args: {'status': 'failed', 'error': 'compiler error'})
    report = xl.prepare(run, tmp_path / 'out', core=tmp_path / 'core.jar')
    assert report['status'] == 'failed' and not report['plants']['DT-001']['groimp_verified']


@pytest.mark.parametrize('review,generation', [('unreviewed', 'pending'), ('accepted', 'failed'), ('deferred', 'ready')])
def test_s2_incomplete_masks_cannot_report_done(tmp_path, monkeypatch, review, generation):
    from tools import leaflet_mask_batch
    (tmp_path / 'manifest.json').write_text('{}')
    items = {'a': dict(review='accepted', generation='ready'),
             'b': dict(review=review, generation=generation)}
    monkeypatch.setattr(leaflet_mask_batch, 'Batch', lambda path: SimpleNamespace(
        manifest={'ids': list(items)}, item=lambda key: items[key]))
    plant = pipeline.Plant('DT-001', {'capture': str(tmp_path), 'labels': str(tmp_path),
        'batch': str(tmp_path)}, {'downloads': str(tmp_path)}, tmp_path / 'run')
    plant.s2()
    assert plant.stages['S2']['status'] == pipeline.WAIT
    assert plant.tasks


def test_pipeline_xl_hook_consumes_finished_status_without_reconstruction(tmp_path, monkeypatch):
    run = fixture_snapshot(tmp_path / 'input')
    monkeypatch.setattr(pipeline, 'CONFIG', tmp_path / 'config.json')
    common.write_json(pipeline.CONFIG, {'plants': {'DT-001': {}}, 'downloads': str(tmp_path)})
    class ExistingPlant:
        def __init__(self, name, cfg, g, out):
            self.name, self.stages, self.tasks = name, {'S6': {'status': 'failed', 'summary': 'fixture'}}, []
        def run(self):
            return self
    monkeypatch.setattr(pipeline, 'Plant', ExistingPlant)
    from tools import plant_site
    monkeypatch.setattr(plant_site, 'build', lambda out: None)
    seen = []
    def delivery(source, out, plants, core):
        assert (source / 'STATUS.md').exists()
        seen.append((source, out, plants, core))
        return {'status': 'failed'}
    monkeypatch.setattr(xl, 'prepare', delivery)
    out = tmp_path / 'terminal'
    assert pipeline.main(['--all', '--out', str(out), '--xl']) == 1
    assert seen == [(out, out / 'xl_handoff', ['DT-001'], None)]
