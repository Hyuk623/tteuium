"""The supplied phone export is HEIF with a DNG suffix, not RAW data."""
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tools.leaf_light.phone import normalize, read_phone_image
from tools.leaf_light.common import StudyError, file_hash


def test_heif_named_dng_keeps_decoded_pixels_and_original(tmp_path: Path) -> None:
    pillow_heif = pytest.importorskip('pillow_heif')
    pillow_heif.register_heif_opener()
    source = tmp_path / 'source'
    source.mkdir()
    path = source / 'phone.DNG'
    image = Image.new('RGB', (64, 48), (31, 132, 71))
    image.save(path, format='HEIF', quality=95)
    before = file_hash(path)
    decoded, _ = read_phone_image(path)
    normalize(source, 'phone', tmp_path / 'normalized')
    with Image.open(tmp_path / 'normalized/images/phone.png') as working:
        np.testing.assert_array_equal(np.asarray(decoded), np.asarray(working))
    assert file_hash(path) == before
    decoded.close()


def test_tiff_dng_is_not_silently_read_as_rgb(tmp_path: Path) -> None:
    path = tmp_path / 'raw.DNG'
    Image.new('RGB', (20, 20)).save(path, format='TIFF')
    with pytest.raises(StudyError, match='RAW/DNG'):
        read_phone_image(path)
    with pytest.raises(StudyError, match='RAW/DNG'):
        normalize(tmp_path, 'phone', tmp_path / 'output')
    assert not (tmp_path / 'output').exists()
