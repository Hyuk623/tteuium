"""Paired dataset assembly with plant-level splits.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def build_dataset(data_root: Path) -> None:
    """Assemble the paired two-view dataset.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.twoview.dataset.build_dataset is a later stage and is not implemented"
    )
