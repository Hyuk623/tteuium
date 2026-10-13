"""Batch evidence must preserve observations and never invent main-vein labels."""
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from tools import leaf_preprocess_lab as lab
from tools.leaf_vein_batch import generate
from tools.tests.test_leaf_preprocess_lab import pilot


def test_all_includes_multiple_labels_per_photo_and_batch_states(pilot):
    app, _, _, doc = pilot
    obs = doc['samples'][0]
    accepted = Path(obs['accepted_export'])
    export = lab.read_json(accepted)
    export['observations'].append(dict(export['observations'][0], id='obs2', source_annotation_id=10))
    lab.write_json(accepted, export)
    session = Path(obs['source_image']).parent
    out = app.root.parent/'expanded'
    expanded = lab.prepare([accepted], [session], out, all_observations=True)
    assert len(expanded['samples']) == 2
    summary = generate(out)
    assert summary['observations'] == 2
    assert sum(summary['counts'].values()) == 2
    assert not summary['main_vein_identified'] and summary['source_verification_passed']
    result = lab.read_json(out/'veins/sample_000.json')
    assert result['review'] == 'unreviewed' and result['anchors_original_px'] == []
    assert result['observation']['crop_xyxy_px'] == expanded['samples'][0]['crop_xyxy_px']
    arrays = np.load(out/'veins/sample_000.npz')
    assert not arrays['evidence'][~arrays['valid']].any()
    with pytest.raises(FileExistsError):
        generate(out)


def test_source_changes_block_batch(pilot):
    app, _, _, doc = pilot
    Path(doc['samples'][0]['source_mask']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='Frozen sources changed'):
        generate(app.root)


def test_flat_image_is_unavailable_not_success(pilot):
    app, _, _, doc = pilot
    item = doc['samples'][0]
    p = app.root/'samples'/item['id']/'original.png'
    with Image.open(p) as im:
        shape = np.asarray(im).shape
    Image.fromarray(np.full(shape, 100, np.uint8)).save(p)
    item['original_crop_sha256'] = lab.sha(p)
    lab.write_json(app.dataset_path, doc)
    result = generate(app.root)
    assert result['counts']['unavailable'] == 1
    assert lab.read_json(app.root/'veins/sample_000.json')['reason'] == 'no_ridge_response'
