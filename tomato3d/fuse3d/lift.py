"""2D instance mask to 3D point subset.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def lift_instances(session_dir: Path) -> None:
    """Lift per-view organ masks onto the reconstructed geometry.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.fuse3d.lift.lift_instances is a later stage and is not implemented"
    )
