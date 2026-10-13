"""Per-view organ instance segmentation.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def segment_organs(session_dir: Path) -> None:
    """Segment organ instances in every view.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.organ.segment2d.segment_organs is a later stage and is not implemented"
    )
