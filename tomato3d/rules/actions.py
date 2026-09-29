"""Leaf removal and fruit culling suggestions.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def suggest_actions(session_dir: Path) -> None:
    """Suggest cultural actions for one session.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.rules.actions.suggest_actions is a later stage and is not implemented"
    )
