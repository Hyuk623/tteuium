"""Run standalone browser annotation model/controller regressions through Node."""
from pathlib import Path
import shutil
import subprocess
import pytest


@pytest.mark.parametrize("script", ["leaf_annotator.test.cjs", "leaf_annotator_diagnostic.test.cjs",
                                    "leaf_annotator_leaflet.test.cjs", "leaf_annotator_ai.test.cjs",
                                    "leaf_annotator_auto.test.cjs", "leaf_annotator_pairs.test.cjs",
                                    "leaf_annotator_membership.test.cjs"])
def test_annotator_regressions(script: str) -> None:
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for annotator JavaScript regression tests')
    result = subprocess.run([node, '--test', str(Path(__file__).with_name(script))],
                            capture_output=True, encoding='utf-8', errors='replace', timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
