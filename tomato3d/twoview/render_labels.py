"""Project multi-view 3D into the two-view label space.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def render_labels(session_dir: Path) -> None:
    """Distil multi-view geometry into two-view labels.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.twoview.render_labels.render_labels is a later stage and is not implemented"
    )
