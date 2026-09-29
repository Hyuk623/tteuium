"""Stem centreline extraction.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def extract_skeleton(session_dir: Path) -> None:
    """Extract the stem centreline.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.graph.skeleton.extract_skeleton is a later stage and is not implemented"
    )
