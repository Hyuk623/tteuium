"""Organ class enum and ontology.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def organ_classes() -> tuple[str, ...]:
    """Return the ordered organ class vocabulary.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.organ.classes.organ_classes is a later stage and is not implemented"
    )
