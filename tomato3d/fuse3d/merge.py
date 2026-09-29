"""Cross-view instance merging and persistent organ ids.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def merge_instances(session_dir: Path) -> None:
    """Merge lifted instances into persistent organ ids.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.fuse3d.merge.merge_instances is a later stage and is not implemented"
    )
