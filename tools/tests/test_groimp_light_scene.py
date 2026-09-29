"""Phase-2 light scene: the plant graph is kept intact and the light declarations land where RGG accepts them."""
import numpy as np
import pytest

from tools import groimp_light_scene as gs
from tools.leaf_light.common import StudyError

EXPORT = """// Static diagnostic snapshot.
import de.grogra.graph.impl.Node;
import de.grogra.xl.util.FloatList;

module Plant(String organKey) extends Node;
boolean showCandidates = false;

protected void init()
[
    Axiom ==>
    Plant("p/1")
    ;
]

public void report()
{
    println("COUNT Plant=" + count((* Plant *)));
}
"""


def grid():
    return gs.sensors(np.array([0.1, -0.05]))


def test_light_declarations_follow_the_imports_and_the_plant_stays():
    rgg = gs.scene_rgg(EXPORT, np.array([0.1, -0.05, 0.4]), grid(), 1000)
    lines = rgg.split('\n')
    last_import = max(k for k, l in enumerate(lines) if l.startswith('import '))
    first_module = min(k for k, l in enumerate(lines) if l.startswith('module '))
    assert last_import < first_module, 'RGG needs imports before any declaration'
    assert 'Plant("p/1")' in rgg and 'public void report()' in rgg, 'the export graph and its methods are kept'
    assert rgg.count('Sensor(') == len(grid()) + 1 and 'Lamp()' in rgg and 'public void measure()' in rgg
    assert 'COUNT Plant=' in rgg.split('public void measure()')[1]


def test_empty_scene_has_lamp_and_sensors_only():
    rgg = gs.scene_rgg(None, np.array([0.1, -0.05, 0.4]), grid(), 1000)
    assert 'Plant(' not in rgg and 'Axiom ==> [ Translate' in rgg and rgg.count('Sensor(') == len(grid()) + 1


def test_an_export_without_one_axiom_is_refused():
    with pytest.raises(StudyError):
        gs.scene_rgg(EXPORT.replace('Axiom ==>', 'X ==>'), np.array([0, 0, 1.0]), grid(), 10)


def test_sensor_grid_is_centred_under_the_plant():
    g = np.array([(x, y) for _, x, y in grid()])
    assert len(g) == gs.GRID ** 2 and np.allclose(g.mean(0), [0.1, -0.05])
