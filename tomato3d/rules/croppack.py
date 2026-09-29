"""Crop pack JSON loader and validator.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def load_crop_pack(path: Path) -> None:
    """Load and validate a crop pack.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.rules.croppack.load_crop_pack is a later stage and is not implemented"
    )
