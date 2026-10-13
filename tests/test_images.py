"""Unicode-safe image IO."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from tomato3d.io.images import ImageIOError, read_image, write_image

NON_ASCII_DIRNAME = "한글 폴더"


@pytest.fixture
def non_ascii_dir(tmp_path: Path) -> Path:
    directory = tmp_path / NON_ASCII_DIRNAME
    directory.mkdir()
    return directory


def test_opencv_path_io_fails_where_this_module_succeeds(non_ascii_dir: Path) -> None:
    """Pins the platform defect this module exists for, so its reason stays visible.

    If a future OpenCV fixes path handling, this test fails and the module can be
    reconsidered - not silently kept or silently dropped.
    """
    import sys

    if sys.platform != "win32":
        pytest.skip("the imread/imwrite path defect is Windows-specific")
    image = np.full((8, 8, 3), 200, np.uint8)
    target = non_ascii_dir / "opencv.png"
    assert cv2.imwrite(str(target), image) is False
    write_image(target, image)
    assert cv2.imread(str(target)) is None
    assert read_image(target) is not None


@pytest.mark.parametrize("suffix", [".png", ".jpg"])
def test_roundtrip_under_a_non_ascii_path(non_ascii_dir: Path, suffix: str) -> None:
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, size=(40, 60, 3), dtype=np.uint8)
    path = non_ascii_dir / f"이미지{suffix}"
    write_image(path, image)

    decoded = read_image(path)
    assert decoded is not None
    assert decoded.shape == image.shape
    if suffix == ".png":
        assert np.array_equal(decoded, image)


def test_single_channel_mask_roundtrip(non_ascii_dir: Path) -> None:
    mask = np.zeros((30, 40), np.uint8)
    mask[5:20, 10:30] = 255
    path = non_ascii_dir / "mask.png"
    write_image(path, mask)
    assert np.array_equal(read_image(path, cv2.IMREAD_UNCHANGED), mask)


def test_read_missing_or_undecodable_returns_none(non_ascii_dir: Path) -> None:
    assert read_image(non_ascii_dir / "missing.jpg") is None
    empty = non_ascii_dir / "empty.jpg"
    empty.write_bytes(b"")
    assert read_image(empty) is None
    garbage = non_ascii_dir / "garbage.jpg"
    garbage.write_bytes(b"this is not an image")
    assert read_image(garbage) is None


def test_write_to_an_unwritable_path_raises(non_ascii_dir: Path) -> None:
    blocker = non_ascii_dir / "not_a_directory"
    blocker.write_text("a file where a folder is expected", encoding="utf-8")
    with pytest.raises(ImageIOError, match="cannot write"):
        write_image(blocker / "mask.png", np.zeros((4, 4), np.uint8))


def test_write_with_an_unencodable_suffix_raises(non_ascii_dir: Path) -> None:
    with pytest.raises(ImageIOError, match="cannot encode"):
        write_image(non_ascii_dir / "mask.notanimage", np.zeros((4, 4), np.uint8))
