"""Read-only inputs for Addendum C step C0 (project-relative paths, verified 2026-10-05).

The v5 SAM training used exactly these four accepted exports (268 + 248 + 278 + 369 = 1,163 masks).
dwt_03/dwt_04 live under ``leaflet_mask_batch_20260925_tuned`` (the ``_20260922`` export folders of those
plants are empty). Poses: ``pose_rescue_20261001`` holds the most solved poses for every plant.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

ACCEPTED_SOURCES: dict[str, Path] = {
    "dwt_01": Path("build/leaflet_mask_batch_20260922/dwt_01/exports/accepted_20260929_092627_faeb15"),
    "dwt_02": Path("build/leaflet_mask_batch_20260922/dwt_02/exports/accepted_20260929_092727_139059"),
    "dwt_03": Path("build/leaflet_mask_batch_20260925_tuned/dwt_03/exports/accepted_20260929_092816_35b47e"),
    "dwt_04": Path("build/leaflet_mask_batch_20260925_tuned/dwt_04/exports/accepted_20260929_092913_25d191"),
}
POSE_FILES: dict[str, Path | None] = {
    p: Path(f"build/pose_rescue_20261001/{p}/edit_session/capture.json") for p in ACCEPTED_SOURCES
}


def decision_files() -> list[Path]:
    return sorted(Path("~/Downloads").expanduser().glob("cross_view_decisions_dwt_*.json"))


def look_at_board_mm() -> np.ndarray:
    from tomato3d.config import get_settings
    from tomato3d.io.schemas import BoardSpec, load_json_model
    from tomato3d.synth.scene import pot_center_board_mm

    spec = load_json_model(get_settings().board_spec_path, BoardSpec)
    p = pot_center_board_mm(spec)
    return np.array([p[0], p[1], 0.0])
