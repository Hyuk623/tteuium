"""Scene meshes in the board frame: leaflets, stem/rachis/petiolule tubes, apex, pot, soil, board.

A *part* is a dict with ``name``, ``organ`` (key of :data:`raster.ORGAN_CLASSES` or
``backdrop``), ``instance`` (leaflet index >= 1, else 0), ``vertices`` (N,3 board mm),
``faces`` (M,3), optional ``uv`` and ``material`` (render hints), and ``raster`` (False for
parts only Blender draws).

Placement: the plant-local frame (soil surface on the stem axis, +Z up) is rotated by
``plant_rotation_deg`` about +Z and translated to the pot centre on the soil surface. The pot
stands at the board centre (``board_center_mm`` + ``pot_center_offset_mm``, sheet frame,
mapped with :func:`tomato3d.calib.board.sheet_to_board_mm`).
"""

from __future__ import annotations

import math
from typing import Any

from pathlib import Path

import numpy as np

from tomato3d.synth.config import constant
from tomato3d.synth.leaflet_surface import surface_points, triangulate_contour


def pot_center_board_mm(spec) -> np.ndarray:
    """Board-frame XY of the pot centre at board height 0."""
    from tomato3d.calib.board import sheet_to_board_mm

    cx, cy = spec.board_center_mm
    ox, oy = spec.pot_center_offset_mm
    return sheet_to_board_mm(np.array([[cx + ox, cy + oy, 0.0]]), spec)[0]


def plant_to_board(points_local: np.ndarray, rotation_deg: float, base_board_mm: np.ndarray) -> np.ndarray:
    a = math.radians(rotation_deg)
    R = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    return np.asarray(points_local, float) @ R.T + np.asarray(base_board_mm, float)[None]


def _frames_along(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Parallel-transport normal/binormal along a polyline."""
    tangents = np.gradient(points, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
    ref = np.array([1.0, 0.0, 0.0]) if abs(tangents[0][0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    n = np.cross(tangents[0], ref)
    n /= np.linalg.norm(n)
    normals, binormals = [], []
    for t in tangents:
        n = n - np.dot(n, t) * t
        n /= np.linalg.norm(n)
        normals.append(n)
        binormals.append(np.cross(t, n))
    return np.array(normals), np.array(binormals)


def tube(points: np.ndarray, radii: np.ndarray, sides: int) -> tuple[np.ndarray, np.ndarray]:
    """Open tube mesh around a polyline (drops zero-length segments)."""
    pts = np.asarray(points, float)
    keep = np.r_[True, np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-6]
    pts, radii = pts[keep], np.asarray(radii, float)[keep]
    if len(pts) < 2:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int32)
    normals, binormals = _frames_along(pts)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    ring = np.cos(ang)[None, :, None] * normals[:, None] + np.sin(ang)[None, :, None] * binormals[:, None]
    verts = (pts[:, None] + radii[:, None, None] * ring).reshape(-1, 3)
    faces = []
    for i in range(len(pts) - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            c, d = a + sides, b + sides
            faces += [(a, b, d), (a, d, c)]
    return verts, np.array(faces, np.int32)


def uv_sphere(center: np.ndarray, radius: float, n: int = 8) -> tuple[np.ndarray, np.ndarray]:
    th = np.linspace(0, math.pi, n + 1)
    ph = np.linspace(0, 2 * math.pi, 2 * n, endpoint=False)
    verts = np.array([[math.sin(a) * math.cos(b), math.sin(a) * math.sin(b), math.cos(a)] for a in th for b in ph])
    verts = np.asarray(center)[None] + radius * verts
    m = 2 * n
    faces = []
    for i in range(n):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            faces += [(a, b, b + m), (a, b + m, a + m)]
    return verts, np.array(faces, np.int32)


def cylinder(center_xy: np.ndarray, radius: float, z0: float, z1: float, sides: int,
             cap_top: bool) -> tuple[np.ndarray, np.ndarray]:
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    ring = np.stack([np.cos(ang), np.sin(ang)], axis=1) * radius + np.asarray(center_xy)[None, :2]
    bottom = np.c_[ring, np.full(sides, z0)]
    top = np.c_[ring, np.full(sides, z1)]
    verts = np.vstack([bottom, top])
    faces = []
    for j in range(sides):
        a, b = j, (j + 1) % sides
        faces += [(a, b, b + sides), (a, b + sides, a + sides)]
    if cap_top:
        verts = np.vstack([verts, [[center_xy[0], center_xy[1], z1]]])
        c = len(verts) - 1
        faces += [(sides + j, sides + (j + 1) % sides, c) for j in range(sides)]
    return verts, np.array(faces, np.int32)


def disk(center_xy: np.ndarray, radius: float, z: float, sides: int) -> tuple[np.ndarray, np.ndarray]:
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    ring = np.c_[np.cos(ang) * radius + center_xy[0], np.sin(ang) * radius + center_xy[1], np.full(sides, z)]
    verts = np.vstack([ring, [[center_xy[0], center_xy[1], z]]])
    return verts, np.array([(j, (j + 1) % sides, sides) for j in range(sides)], np.int32)


def load_texture_bank(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Optional leaflet albedo textures (Addendum D B5a): constant ``leaf_texture_bank`` = bank.json path."""
    import json
    from pathlib import Path

    from tomato3d.synth.config import input_path

    entry = cfg.get("constants", {}).get("leaf_texture_bank")
    if not entry:
        return []
    bank_path = input_path(entry["value"])
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    return [dict(t, path=str((bank_path.parent / t["file"]).resolve()),
                 height_path=str((bank_path.parent / t["height_file"]).resolve()) if t.get("height_file") else None,
                 mask_path=str((bank_path.parent / t["mask_file"]).resolve()) if t.get("mask_file") else None)
            for t in bank["textures"]]


class TexturePlacer:
    """Texture choice + UV placement per leaflet, with the flat-fill fraction (Addendum G.2 A1).

    ``leaf_texture_pairing`` (constant): absent or ``leaflet_id_hash`` = B5a behaviour (texture by sha256 of the
    leaflet id, s = x, t = 0.5 + y / aspect); ``same_mask_warp`` = the texture built from the contour's own mask
    when the bank has one (else the hash choice), placed by :func:`textures.warp_uv` so the outline lands on
    textured texels.
    """

    def __init__(self, bank: list[dict[str, Any]], cfg: dict[str, Any], contour_ids: list[str | None] | None):
        self.bank = bank
        self.mode = cfg.get("constants", {}).get("leaf_texture_pairing", {}).get("value", "leaflet_id_hash")
        if self.mode not in ("leaflet_id_hash", "same_mask_warp"):
            raise ValueError(f"unknown leaf_texture_pairing {self.mode!r}")
        self.contour_ids = contour_ids
        self.by_mask = {t["mask_id"]: t for t in bank if t.get("mask_id")}
        self._sil: dict[str, Any] = {}
        self._cache: dict[tuple, dict[str, Any]] = {}

    def _silhouette(self, tex):
        from tomato3d.synth.textures import silhouette_profile, texture_silhouette

        if tex["path"] not in self._sil:
            sil = texture_silhouette(tex)
            self._sil[tex["path"]] = (sil, silhouette_profile(sil))
        return self._sil[tex["path"]]

    def place(self, leaflet_id: str, ci: int, contour: np.ndarray, uv: np.ndarray) -> tuple[dict, np.ndarray, dict]:
        from tomato3d.synth.textures import contour_profile, flat_fill_fraction, hash_uv, warp_uv

        mask_id = self.contour_ids[ci] if self.contour_ids is not None else None
        if self.mode == "same_mask_warp" and mask_id in self.by_mask:
            tex, pairing = self.by_mask[mask_id], "same_mask"
        else:
            tex, pairing = pick_texture(self.bank, leaflet_id), ("hash" if self.mode == "leaflet_id_hash" else
                                                                 "fallback_hash_warp")
        key = (ci, tex["path"], pairing)
        if key not in self._cache:
            sil, tprof = self._silhouette(tex)
            if pairing == "hash":
                fn = lambda q, a=tex["aspect"]: hash_uv(q, a)
                info = dict(flip_x=False, flip_y=False)
            else:
                cprof = contour_profile(contour)
                best = None
                for fx in (False, True):                 # same mask: orientation that overlays the two silhouettes
                    for fy in (False, True):
                        g = (lambda q, fx=fx, fy=fy: hash_uv(np.c_[1 - q[:, 0] if fx else q[:, 0],
                                                                    -q[:, 1] if fy else q[:, 1]], tex["aspect"]))
                        score = flat_fill_fraction(contour, g, sil) if pairing == "same_mask" else 0.0
                        if best is None or score < best[0]:
                            best = (score, fx, fy)
                        if pairing != "same_mask":
                            break
                    if pairing != "same_mask":
                        break
                _, fx, fy = best
                fn = lambda q, c=cprof, tp=tprof, fx=fx, fy=fy: warp_uv(q, c, tp, flip_x=fx, flip_y=fy)
                info = dict(flip_x=fx, flip_y=fy)
            info["flat_fill_fraction"] = flat_fill_fraction(contour, fn, sil)
            self._cache[key] = dict(fn=fn, info=info)
        c = self._cache[key]
        return tex, c["fn"](uv), dict(c["info"], pairing=pairing, texture=Path(tex["path"]).name)


def pick_texture(bank: list[dict[str, Any]], leaflet_id: str) -> dict[str, Any]:
    """Deterministic texture choice per leaflet id."""
    import hashlib

    h = int(hashlib.sha256(leaflet_id.encode("utf-8")).hexdigest()[:8], 16)
    return bank[h % len(bank)]


def leaflet_texture_uv(uv: np.ndarray, tex_aspect: float) -> np.ndarray:
    """Leaflet frame (x 0..1 base->tip, y lateral, unit length) -> texture (s along midrib, t across)."""
    uv = np.asarray(uv, float)
    return np.c_[uv[:, 0], 0.5 + uv[:, 1] / max(tex_aspect, 1e-6)]


def board_plane(spec) -> dict[str, Any]:
    """The printed sheet at board z = 0 with UVs for the ChArUco texture (sheet frame)."""
    from tomato3d.calib.board import sheet_to_board_mm

    w, h = spec.board_width_mm, spec.board_height_mm
    sheet = np.array([[0, 0, 0], [w, 0, 0], [w, h, 0], [0, h, 0]], float)
    verts = sheet_to_board_mm(sheet, spec)
    uv = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], float)  # texture row 0 = sheet y 0
    return dict(name="board", organ="board", instance=0, vertices=verts,
                faces=np.array([(0, 1, 2), (0, 2, 3)], np.int32), uv=uv, material=dict(kind="board"))


def scene_parts(graph: dict[str, Any], interiors: dict[str, dict[str, Any]], contours: list[np.ndarray],
                cfg: dict[str, Any], scene_params: dict[str, float], spec,
                contour_ids: list[str | None] | None = None) -> tuple[list[dict], dict]:
    """Build every part for one plant; return (parts, leaflet index table)."""
    sides = int(constant(cfg, "tube_sides"))
    grid_n = int(constant(cfg, "leaflet_mesh_grid_n"))
    pot_xy = pot_center_board_mm(spec)
    soil_z = scene_params["pot_height_mm"] - scene_params["soil_depth_below_rim_mm"]
    base = np.array([pot_xy[0], pot_xy[1], soil_z])
    rot = scene_params["plant_rotation_deg"]

    def place(p):
        return plant_to_board(np.atleast_2d(p), rot, base)

    parts: list[dict[str, Any]] = []
    stem = np.array(graph["stem"]["points_mm"])
    r_stem = scene_params["stem_radius_mm"]
    radii = np.linspace(r_stem, 0.6 * r_stem, len(stem))
    v, f = tube(place(stem), radii, sides)
    parts.append(dict(name="stem", organ="stem", instance=0, vertices=v, faces=f, material=dict(kind="stem")))
    v, f = uv_sphere(place(stem[-1])[0], constant(cfg, "apex_bud_radius_mm"))
    parts.append(dict(name="apex", organ="apex", instance=0, vertices=v, faces=f, material=dict(kind="leaf")))

    tri_cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    index: dict[str, Any] = {}
    bank = load_texture_bank(cfg)
    placer = TexturePlacer(bank, cfg, contour_ids) if bank else None
    height_cache: dict[str, np.ndarray] = {}
    instance = 0
    r_rachis = scene_params["rachis_radius_mm"]
    for comp in graph["compounds"]:
        interior = interiors[comp["compound_id"]]
        rachis = np.array(interior["rachis_points_mm"])
        if len(rachis) >= 2:
            v, f = tube(place(rachis), np.linspace(r_rachis, 0.5 * r_rachis, len(rachis)), max(4, sides // 2))
            parts.append(dict(name=f"rachis_{comp['compound_id']}", organ="rachis", instance=0, vertices=v,
                              faces=f, material=dict(kind="stem")))
        for leaf in interior["leaflets"]:
            instance += 1
            ci = leaf["contour_index"]
            if ci not in tri_cache:
                tri_cache[ci] = triangulate_contour(contours[ci], grid_n)
            uv, faces = tri_cache[ci]
            verts = place(surface_points(uv, leaf))
            part = dict(name=leaf["leaflet_id"], organ="leaflet", instance=instance, vertices=verts,
                        faces=faces, material=dict(kind="leaf", compound_id=comp["compound_id"]))
            tex_info = None
            if bank:
                tex, part["uv"], tex_info = placer.place(leaf["leaflet_id"], ci, contours[ci], uv)
                amp_rel = float(cfg.get("constants", {}).get("leaf_relief_amplitude_rel", {}).get("value", 0.0))
                if amp_rel > 0 and tex.get("height_path"):
                    from tomato3d.synth.images import imread
                    from tomato3d.synth.leaflet_surface import displace, sample_height

                    hmap = height_cache.setdefault(tex["height_path"], imread(Path(tex["height_path"]), 0))
                    offsets = amp_rel * float(leaf["length_mm"]) * sample_height(hmap, part["uv"])
                    part["vertices"] = displace(verts, faces, offsets)
                part["material"] = dict(kind="leaf_tex", texture=tex["path"], compound_id=comp["compound_id"])
            parts.append(part)
            index[str(instance)] = dict(leaflet_id=leaf["leaflet_id"], compound_id=comp["compound_id"],
                                        tag=leaf["tag"], kind=leaf["kind"], rank_from_bottom=comp["rank_from_bottom"],
                                        contour_index=ci, length_mm=leaf["length_mm"],
                                        contour_id=contour_ids[ci] if contour_ids is not None else None,
                                        texture=tex_info)
            pet = float(leaf.get("petiolule_mm", 0.0))
            if pet > 0.2:
                start = np.array(leaf["base_mm"]) - pet * np.array(leaf["heading"])
                v, f = tube(place(np.array([start, leaf["base_mm"]])), np.array([0.6, 0.4]) * r_rachis, 4)
                parts.append(dict(name=f"petiolule_{leaf['leaflet_id']}", organ="petiolule", instance=0,
                                  vertices=v, faces=f, material=dict(kind="stem")))
    pot_r, pot_h = scene_params["pot_radius_mm"], scene_params["pot_height_mm"]
    v, f = cylinder(pot_xy, pot_r, 0.0, pot_h, int(constant(cfg, "pot_sides")), cap_top=False)
    parts.append(dict(name="pot", organ="pot", instance=0, vertices=v, faces=f, material=dict(kind="pot")))
    v, f = disk(pot_xy, pot_r * 0.97, soil_z, int(constant(cfg, "pot_sides")))
    parts.append(dict(name="soil", organ="soil", instance=0, vertices=v, faces=f, material=dict(kind="soil")))
    parts.append(board_plane(spec))
    return parts, index
