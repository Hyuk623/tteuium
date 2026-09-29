"""OBJ transport preserves identity and converts units once, with open leaf surfaces."""
import pytest

from tools.groimp_bridge import export
from tools.leaf_light.common import rows
from tools.tests.test_canopy_light import inputs


def test_open_leaf_export_and_grow_transform(tmp_path):
    inputs(tmp_path)
    info=export(tmp_path/'geometry.csv','v25',tmp_path/'board')
    lines=(tmp_path/'board/leaves_m.obj').read_text().splitlines()
    vertex=next(line for line in lines if line.startswith('v '))
    assert [float(v) for v in vertex.split()[1:]]==pytest.approx([-.04,-.04,.1])
    assert sum(line.startswith('f ') for line in lines)==4
    assert len(rows(tmp_path/'board/identity_map.csv'))==4
    assert info['watertight_required'] is False and info['groimp_import_verified'] is False
    export(tmp_path/'geometry.csv','v25',tmp_path/'grow',tmp_path/'scene.json')
    vertex=next(line for line in (tmp_path/'grow/leaves_m.obj').read_text().splitlines() if line.startswith('v '))
    assert [float(v) for v in vertex.split()[1:]]==pytest.approx([.26,.16,.1])


def test_unknown_variant_cannot_emit_empty_success(tmp_path):
    inputs(tmp_path)
    with pytest.raises(ValueError,match='Unknown'): export(tmp_path/'geometry.csv','unknown',tmp_path/'out')
    assert not (tmp_path/'out').exists()
