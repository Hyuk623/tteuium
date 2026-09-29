"""Organ graph assembly.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def build_connectivity(session_dir: Path) -> None:
    """Assemble the organ connectivity graph.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.graph.connectivity.build_connectivity is a later stage and is not implemented"
    )
