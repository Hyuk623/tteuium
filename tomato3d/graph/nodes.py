"""Node (phytomer) detection and ordering.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def detect_nodes(session_dir: Path) -> None:
    """Detect and order phytomer nodes along the stem.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.graph.nodes.detect_nodes is a later stage and is not implemented"
    )
