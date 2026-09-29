"""Run browser-independent threshold, filtering and export regressions."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_mask_tuner_regressions() -> None:
    node=shutil.which('node')
    if not node: pytest.skip('Node.js required for mask tuner regressions')
    result=subprocess.run([node,'--test',str(Path(__file__).with_name('sam_mask_tuner.test.cjs'))],
                          capture_output=True,encoding='utf-8',errors='replace',timeout=45)
    assert result.returncode==0,result.stdout+result.stderr
