"""Own numpy z-buffer rasteriser: visible instance mask, amodal masks, depth and organ classes.

Rasterises in the undistorted render space (pixel centres, perspective-correct depth) and
warps every layer with the same nearest-neighbour inverse distortion map as the RGB image.

* ``visible``: ``uint16`` leaflet instance index (1..N) of the front-most surface; 0 when the
  front-most surface is not a leaflet (stem, pot, board ... or nothing).
* ``amodal[i]``: every pixel leaflet *i* covers, ignoring all occluders.
* ``depth_mm``: camera-frame ``Z`` of the front-most surface in mm (0 = no surface).
* ``organ``: :data:`ORGAN_CLASSES` of the front-most surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from tomato3d.synth.camera import RenderGeometry, project_render

ORGAN_CLASSES: dict[str, int] = {
    "background": 0, "leaflet": 1, "stem": 2, "rachis": 3, "petiolule": 4, "apex": 5,
    "pot": 6, "soil": 7, "board": 8,
}
INVALID_LABEL = 255
NEAR_PLANE_MM = 1.0


@dataclass
class RasterLayers:
    visible: np.ndarray            # uint16
    amodal: dict[int, np.ndarray]  # instance index -> bool
    depth_mm: np.ndarray           # float32
    organ: np.ndarray              # uint8
    valid: np.ndarray              # bool


def _raster_part(px: np.ndarray, z: np.ndarray, faces: np.ndarray, width: int, height: int,
                 zbuf: np.ndarray, idbuf: np.ndarray, organbuf: np.ndarray, instance: int, organ: int,
                 amodal: np.ndarray | None) -> None:
    for tri in faces:
        if np.any(z[tri] < NEAR_PLANE_MM):
            continue
        p = px[tri]
        x0, y0 = np.floor(p.min(axis=0)).astype(int)
        x1, y1 = np.ceil(p.max(axis=0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, width - 1), min(y1, height - 1)
        if x0 > x1 or y0 > y1:
            continue
        (ax, ay), (bx, by), (cx, cy) = p
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1, dtype=np.float64), np.arange(y0, y1 + 1, dtype=np.float64))
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        w2 = 1.0 - w0 - w1
        eps = -1e-9
        inside = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
        if not inside.any():
            continue
        inv_z = w0 / z[tri[0]] + w1 / z[tri[1]] + w2 / z[tri[2]]
        depth = 1.0 / inv_z
        if amodal is not None:
            amodal[y0:y1 + 1, x0:x1 + 1] |= inside
        win = zbuf[y0:y1 + 1, x0:x1 + 1]
        front = inside & (depth < win)
        if front.any():
            win[front] = depth[front]
            idbuf[y0:y1 + 1, x0:x1 + 1][front] = instance
            organbuf[y0:y1 + 1, x0:x1 + 1][front] = organ


def rasterize(parts: list[dict[str, Any]], R: np.ndarray, t: np.ndarray, geom: RenderGeometry
              ) -> RasterLayers:
    """Rasterise mesh ``parts`` (board-frame mm) for one view and warp to the output image."""
    W, H = geom.render_size_px
    zbuf = np.full((H, W), np.inf)
    idbuf = np.zeros((H, W), np.uint16)
    organbuf = np.zeros((H, W), np.uint8)
    amodal_render: dict[int, np.ndarray] = {}
    for part in parts:
        if not part.get("raster", True):
            continue
        px, z = project_render(part["vertices"], R, t, geom.K_render)
        instance = int(part.get("instance", 0))
        amodal = None
        if instance > 0:
            amodal = amodal_render.setdefault(instance, np.zeros((H, W), bool))
        _raster_part(px, z, np.asarray(part["faces"]), W, H, zbuf, idbuf, organbuf, instance,
                     ORGAN_CLASSES[part["organ"]], amodal)
    depth = np.where(np.isfinite(zbuf), zbuf, 0.0).astype(np.float32)
    visible = geom.warp(idbuf, nearest=True, fill=0)
    organ = geom.warp(organbuf, nearest=True, fill=INVALID_LABEL)
    depth_out = geom.warp(depth, nearest=True, fill=0.0)
    amodal_out = {k: geom.warp(v.astype(np.uint8), nearest=True, fill=0).astype(bool)
                  for k, v in amodal_render.items()}
    return RasterLayers(visible=visible, amodal=amodal_out, depth_mm=depth_out, organ=organ,
                        valid=geom.valid.copy())
