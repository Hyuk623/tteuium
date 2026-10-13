"""Phase-2 light scene (v2): graph kept, display geometry not optical, inputs verified, failure states explicit."""
import json
import math

import numpy as np
import pytest

from tools import groimp_light_scene as gs
from tools.leaf_light.common import StudyError, file_hash

EXPORT = """// Static diagnostic snapshot.
import de.grogra.graph.impl.Node;
import de.grogra.xl.util.FloatList;

module Plant(String organKey) extends Node;
module PositionMarker(String organKey, String metadata) extends Sphere(0.001);
module AxisSegment(String organKey, String metadata) extends Line;
module LeafSurface(String organKey, String metadata) extends MeshNode;

protected void init()
[
    Axiom ==>
    Plant("p/1")
    [ Translate(0.1f,0f,0.1f) PositionMarker("p/1", "{\\"display_only\\": true}").(setShader(YELLOW)) ]
    [ AxisSegment("p/1/axis", "{}").(setAxis(-0.01f,0.02f,0.03f)) ]
    ;
]

public void report()
{
    println("COUNT Plant=" + count((* Plant *)));
}
"""


def grid():
    return gs.sensors(np.array([0.1, -0.05]))


def lamps():
    return [(np.array([0.1, -0.05, 0.4]), 1000.0)]


def test_light_declarations_follow_the_imports_and_the_plant_stays():
    rgg = gs.scene_rgg(EXPORT, lamps(), grid(), 1000)
    lines = rgg.split('\n')
    last_import = max(k for k, l in enumerate(lines) if l.startswith('import '))
    first_module = min(k for k, l in enumerate(lines) if l.startswith('module '))
    assert last_import < first_module
    assert 'Plant("p/1")' in rgg and 'public void report()' in rgg
    assert rgg.count('Sensor(') == len(grid()) + 1 and rgg.count('RL(-90) Sensor(') == len(grid())


def test_sensor_anchor_centres_the_plate():
    rgg = gs.scene_rgg(None, lamps(), [(0, 0.2, 0.3)], 10)
    assert f'Translate(0.20000f, {0.3 - gs.SENSOR_M / 2:.5f}f, 0) RL(-90) Sensor(0)' in rgg


def test_optical_copy_keeps_ids_and_drops_display_geometry():
    text, elig = gs.optical_copy(EXPORT)
    assert 'extends Sphere' not in text and 'extends Line' not in text
    assert 'setShader(' not in text and 'setAxis(' not in text
    assert 'PositionMarker("p/1"' in text and 'AxisSegment("p/1/axis"' in text and 'Plant("p/1")' in text
    assert elig['PositionMarker'] == dict(instances=1, optical=False) and elig['AxisSegment']['instances'] == 1
    assert elig['LeafSurface'] == dict(instances=0, optical=True)


def test_optical_copy_refuses_an_unknown_export_layout():
    with pytest.raises(StudyError):
        gs.optical_copy(EXPORT.replace('extends Sphere(0.001)', 'extends Sphere(0.002)'))


def test_an_export_without_one_axiom_is_refused():
    with pytest.raises(StudyError):
        gs.scene_rgg(EXPORT.replace('Axiom ==>', 'X ==>'), lamps(), grid(), 10)


def _handoff(tmp_path, change=None):
    exp = tmp_path / 'h' / 'p1' / 'export'
    exp.mkdir(parents=True)
    (exp / 'Model.rgg').write_text(EXPORT, encoding='utf-8')
    (exp / 'coordinates.csv').write_text('organ_key,x_m,y_m,z_m\np/1,0.1,0,0.1\n', encoding='utf-8')
    (exp / 'organs.csv').write_text('key,module\np/1,Plant\n', encoding='utf-8')
    (exp / 'export.json').write_text('{"session_id": "s"}', encoding='utf-8')
    hashes = {f'p1\\export\\{n}': file_hash(exp / n) for n in gs.EXPORT_FILES}
    (tmp_path / 'h' / 'handoff.json').write_text(json.dumps({'plants': {'p1': {'artifact_hashes': hashes}}}), encoding='utf-8')
    if change:
        (exp / change).write_text((exp / change).read_text(encoding='utf-8') + '\n', encoding='utf-8')
    return tmp_path / 'h'


def test_export_files_are_checked_against_the_handoff(tmp_path):
    export, hashes = gs.verify_export(_handoff(tmp_path), 'p1')
    assert set(hashes) == set(gs.EXPORT_FILES)


@pytest.mark.parametrize('changed', ['coordinates.csv', 'organs.csv', 'Model.rgg'])
def test_a_changed_export_file_is_refused(tmp_path, changed):
    with pytest.raises(StudyError, match='changed'):
        gs.verify_export(_handoff(tmp_path, changed), 'p1')


def test_a_missing_export_file_is_refused(tmp_path):
    h = _handoff(tmp_path)
    (h / 'p1' / 'export' / 'organs.csv').unlink()
    with pytest.raises(StudyError, match='missing'):
        gs.verify_export(h, 'p1')


def test_python_sensor_under_a_point_lamp_matches_inverse_square():
    val = gs.python_sensors([(np.array([0.0, 0.0, 0.5]), 1000.0)], [(0, 0.0, 0.0)])[0]
    expected = 1000.0 / (4 * math.pi * 0.25) * gs.SENSOR_M ** 2
    assert abs(val / expected - 1) < 0.01


def test_sensor_grid_is_centred_under_the_plant():
    g = np.array([(x, y) for _, x, y in grid()])
    assert len(g) == gs.GRID ** 2 and np.allclose(g.mean(0), [0.1, -0.05])


@pytest.mark.parametrize('yaw_deg', [0.0, 30.0, -115.0])
def test_scene_lamps_map_grow_to_board_as_the_inverse_of_board_to_grow(tmp_path, yaw_deg):
    """A LightScene's emitters, mapped into the board frame, land back on themselves through tomato3d's board_to_grow_mm."""
    from pathlib import Path
    from tomato3d.light.frames import board_to_grow_mm
    from tomato3d.light.scene import build_emitters, load_scene
    src = Path(__file__).resolve().parents[2] / 'tests' / 'fixtures' / 'light' / 'light_scene.example.json'
    doc = json.loads(src.read_text(encoding='utf-8'))
    doc['plants'][0]['plant_id'] = 'p1'
    doc['plants'][0]['board_yaw_deg']['value'] = yaw_deg
    path = tmp_path / 'scene.json'
    path.write_text(json.dumps(doc), encoding='utf-8')
    lamp_list, used = gs.lamps_from_scene(path, 'p1')
    scene = load_scene(path)
    origin = np.array(doc['plants'][0]['board_origin_grow_mm']['value'])
    grow = np.concatenate([build_emitters(f)[0].positions_grow_mm for f in scene.fixtures if build_emitters(f)[0] is not None])
    back = board_to_grow_mm(np.array([p for p, _ in lamp_list]) * 1000.0, origin, math.radians(yaw_deg))
    assert np.allclose(back, grow, atol=1e-6)
    assert abs(sum(f for _, f in lamp_list) - sum(f['photon_flux_umol_s']['value'] for f in doc['fixtures'])) < 1e-9
    assert used['lamp_status'].startswith('assumed')  # the example's values are placeholders, never 'measured'


def test_a_scene_without_the_plant_placement_is_refused(tmp_path):
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / 'tests' / 'fixtures' / 'light' / 'light_scene.example.json'
    with pytest.raises(StudyError, match='placement'):
        gs.lamps_from_scene(src, 'no_such_plant')


# ---- Codex review 2026-09-29: F1 (all consumed inputs decide), F2 (directional LED gate), F3 (exact tolerance)

def _scene(tmp_path, edit=None):
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / 'tests' / 'fixtures' / 'light' / 'light_scene.example.json'
    doc = json.loads(src.read_text(encoding='utf-8'))
    doc['plants'][0]['plant_id'] = 'p1'
    if edit:
        edit(doc)
    path = tmp_path / 'scene.json'
    path.write_text(json.dumps(doc), encoding='utf-8')
    return path


def _mark_measured(node):
    if isinstance(node, dict):
        if {'value', 'status', 'source'} <= set(node) and node['value'] is not None:
            node['status'] = 'measured'
        for v in node.values():
            _mark_measured(v)
    elif isinstance(node, list):
        for v in node:
            _mark_measured(v)


def test_centre_and_flux_measured_alone_do_not_make_the_scene_measured(tmp_path):
    def edit(doc):
        for f in doc['fixtures']:
            f['emitting_center_grow_mm']['status'] = 'measured'
            f['photon_flux_umol_s']['status'] = 'measured'
    _, used = gs.lamps_from_scene(_scene(tmp_path, edit), 'p1')
    assert used['lamp_status'] != 'measured'
    text = ' '.join(used['absolute_blockers'])
    assert 'aim_tilt_deg' in text and 'emitting_length_mm' in text and 'placement.board_yaw_deg' in text


def test_a_directional_led_blocks_absolute_output_even_when_everything_is_measured(tmp_path):
    _, used = gs.lamps_from_scene(_scene(tmp_path, _mark_measured), 'p1')
    assert not any('is ' in b for b in used['absolute_blockers']), 'every input is measured here'
    assert used['lamp_status'] != 'measured' and any('directional' in b for b in used['absolute_blockers'])
    assert all('SURROGATE' in f['distribution'] for f in used['fixtures'] if not f.get('skipped'))


def test_an_incomplete_additional_lamp_is_reported_not_silently_dropped(tmp_path):
    import copy

    def edit(doc):
        _mark_measured(doc)
        extra = copy.deepcopy(doc['fixtures'][0])
        extra['fixture_id'] = 'extra_lamp'
        extra['emitting_width_mm'] = dict(value=None, status='unavailable', source='not measured yet')
        doc['fixtures'].append(extra)
    _, used = gs.lamps_from_scene(_scene(tmp_path, edit), 'p1')
    assert any(f.get('skipped') and f['fixture_id'] == 'extra_lamp' for f in used['fixtures'])
    assert any('extra_lamp skipped' in b and 'emitting_width_mm' in b for b in used['absolute_blockers'])


@pytest.mark.parametrize('err,sigma,ok', [(0.035, 0.01, True), (-0.035, 0.01, True), (0.0351, 0.01, False),
                                          (0.04, 0.01, False), (0.005, 0.0, True), (0.0051, 0.0, False)])
def test_python_tolerance_is_exactly_three_sigma_plus_half_a_percent(err, sigma, ok):
    assert gs.within_tolerance(err, sigma) is ok
