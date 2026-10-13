"""Per-organ keypoint extraction.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def extract_keypoints(session_dir: Path) -> None:
    """Extract per-organ keypoints.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.graph.keypoints.extract_keypoints is a later stage and is not implemented"
    )
