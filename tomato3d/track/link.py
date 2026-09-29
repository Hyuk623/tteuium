"""Cross-date organ linking.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def link_organs(plant_id: str) -> None:
    """Link organs across sessions of one plant.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.track.link.link_organs is a later stage and is not implemented"
    )
