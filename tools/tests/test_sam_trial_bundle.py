"""Portable prompt references must retain the original source pixels and hashes."""
import hashlib
import json
from pathlib import Path

import pytest
from tools.leaf_light.common import StudyError
from tools.sam_trial_bundle import collect_payload, notebook


def test_bundle_rebases_two_shared_photo_references_without_changing_pixels(tmp_path: Path):
    image=tmp_path/'image.png';image.write_bytes(b'unchanged image payload')
    sha=hashlib.sha256(image.read_bytes()).hexdigest()
    manifest=tmp_path/'prompts.json'
    source={'cases':[{'image_file':'image.png','image_sha256':sha},{'image_file':'image.png','image_sha256':sha}]}
    manifest.write_text(json.dumps(source))
    result=collect_payload([manifest]);rebased=json.loads(result['prompts.json'])
    assert len([key for key in result if key.startswith('images/')])==1
    for case in rebased['cases']:
        assert hashlib.sha256(result[case['image_file']]).hexdigest()==case['image_sha256']==sha
    assert json.loads(manifest.read_text())==source
    image.write_bytes(b'changed')
    with pytest.raises(StudyError,match='hash mismatch'): collect_payload([manifest])


def test_colab_replay_cells_are_valid_python_and_preserve_setup_order():
    nb=notebook('inputs.zip','a'*64)
    for cell in nb.cells:
        if cell.cell_type=='code': compile(cell.source,'colab_cell','exec')
    sources='\n'.join(cell.source for cell in nb.cells)
    assert sources.index('ZIP hash mismatch')<sources.index('from tools.sam_leaf_trial import run')
