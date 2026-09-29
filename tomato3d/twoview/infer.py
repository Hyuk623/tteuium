"""Two-view inference to the phenotypes CSV schema.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def infer(session_dir: Path) -> None:
    """Run two-view inference for one capture.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.twoview.infer.infer is a later stage and is not implemented"
    )
