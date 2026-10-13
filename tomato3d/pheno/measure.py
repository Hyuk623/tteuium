"""Phenotype computation to CSV.

Stage 1 fixes this import graph. Nothing here is implemented yet; every entry point
raises NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path  # noqa: F401  (part of the future signatures)


def measure_phenotypes(session_dir: Path) -> None:
    """Compute phenotypes for one session.

    Raises:
        NotImplementedError: always. This stage is not implemented yet.
    """
    raise NotImplementedError(
        "tomato3d.pheno.measure.measure_phenotypes is a later stage and is not implemented"
    )
