"""Failure paths must reject incomplete diagnostics before any new output is written."""
from pathlib import Path
import pytest
from tools import p2_lamp_controls as controls
from tools.leaf_light.common import StudyError,write_json


@pytest.mark.parametrize('grid,samples,rtol', [((0,1),1,.02),((1,1),0,.02),((1,1),1,-1),((1,1),1,float('nan'))])
def test_invalid_numerical_controls_fail_before_loading(tmp_path,grid,samples,rtol):
    with pytest.raises(StudyError):
        controls.check(tmp_path/'nonexistent.json',tmp_path/'out',emitter_grid=grid,sensor_samples=samples,
                       relative_tolerance=rtol,absolute_tolerance=.1,standard_error_multiplier=6)
    assert not (tmp_path/'out').exists()


def test_artifact_tampering_refused_before_direct_comparison(tmp_path):
    (tmp_path/'artifact.json').write_text('{}')
    write_json(tmp_path/'fit.json',dict(artifact_hashes={'artifact.json':'wrong'}))
    with pytest.raises(StudyError,match='native artifact changed'):
        controls.check(tmp_path/'fit.json',tmp_path/'out',emitter_grid=(1,1),sensor_samples=1,
                       relative_tolerance=.02,absolute_tolerance=.1,standard_error_multiplier=6)
