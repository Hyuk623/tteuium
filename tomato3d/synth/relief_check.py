"""Addendum D step B5b validation: rotation-induced appearance change of a flat textured test leaflet.

Mirrors D0 (``rot_grid``): a flat leaflet (albedo texture + height map + bump) lies on white paper under a fixed
key light and a fixed top-down orthographic camera, and is rotated 0/90/180/270 deg about the vertical. Per leaflet:
mean grey brightness and local contrast (std of grey minus Gaussian(sigma) inside the eroded leaf mask), both
divided by the median paper grey, then (max-min)/mean over the 4 rotations - the same statistics as D0.
Runs in the tomato_synth environment (bpy). Small renders; not a heavy job.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.synth.images import imread

IMG_PX = 256
LEAF_LEN_MM = 40.0
ORTHO_MM = 64.0


def _leaf_mask_tex(height_png: Path) -> np.ndarray:
    h = imread(height_png, cv2.IMREAD_GRAYSCALE)
    m = (np.abs(h.astype(int) - 128) > 1).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m.astype(bool)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    filled = (lab == big).astype(np.uint8)
    cs, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(filled, cs, -1, 1, -1)
    return filled.astype(bool)


def _leaf_mesh(aspect: float, rot_deg: float, roll_deg: float, n: int = 24, height_img: np.ndarray | None = None,
               relief_amp_rel: float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Test leaflet as a grid surface (optionally rolled like generator leaflets), rotated about +z."""
    from tomato3d.synth.leaflet_surface import surface_points

    xs = np.linspace(0, 1, n)
    ys = np.linspace(-aspect / 2, aspect / 2, max(3, int(n * aspect)))
    gx, gy = np.meshgrid(xs, ys)
    uv = np.c_[gx.ravel(), gy.ravel()]
    a = math.radians(rot_deg)
    head = np.array([math.cos(a), math.sin(a), 0.0])
    left = np.array([-math.sin(a), math.cos(a), 0.0])
    base = np.array([0.0, 0.0, 6.0]) - head * LEAF_LEN_MM / 2
    leaf = dict(length_mm=LEAF_LEN_MM, width_scale=1.0, roll_deg=roll_deg, twist_deg=0.0, bend_deg=0.0,
                heading=head, left=left, up=np.array([0.0, 0.0, 1.0]), base_mm=base)
    verts = surface_points(uv, leaf)
    ny, nx = gx.shape
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            k = j * nx + i
            faces += [(k, k + 1, k + nx + 1), (k, k + nx + 1, k + nx)]
    tex_uv = np.c_[uv[:, 0], 0.5 + uv[:, 1] / aspect]
    faces = np.array(faces)
    if relief_amp_rel > 0 and height_img is not None:          # B5c: mesh-level relief, same rule as scene.py
        from tomato3d.synth.leaflet_surface import displace, sample_height

        verts = displace(verts, faces, relief_amp_rel * LEAF_LEN_MM * sample_height(height_img, tex_uv))
    return verts, faces, tex_uv


def _render(tex: Path, height: Path, aspect: float, rot_deg: float, *, light_size_m: float, bump_strength: float,
            bump_distance_m: float, samples: int, out_png: Path, roughness: float = 0.5,
            roll_deg: float = 0.0, device: str = "CPU", relief_amp_rel: float = 0.0,
            specular: float | None = None, mesh_n: int = 24) -> np.ndarray:
    import bpy
    from mathutils import Matrix

    from tomato3d.synth import render_blender as rb

    rb.reset()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    if device == "GPU":
        rb.enable_gpu()
    sc.cycles.device = device
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = sc.render.resolution_y = IMG_PX
    sc.render.image_settings.file_format = "PNG"
    paper = rb._material("paper", (0.8, 0.8, 0.8, 1.0), 0.9)
    leaf = rb._material("leaf", (1.0, 1.0, 1.0, 1.0), roughness, 0.15, image=tex, interpolation="Linear",
                        height=height, bump_strength=bump_strength, bump_distance_m=bump_distance_m, specular=specular)
    s = 0.2
    rb._mesh_object("paper", np.array([[-s, -s, 0], [s, -s, 0], [s, s, 0], [-s, s, 0]]) * 1000,
                    np.array([(0, 1, 2), (0, 2, 3)]), paper)
    himg = imread(height, cv2.IMREAD_GRAYSCALE) if relief_amp_rel > 0 else None
    verts, faces, tex_uv = _leaf_mesh(aspect, rot_deg, roll_deg, n=mesh_n, height_img=himg, relief_amp_rel=relief_amp_rel)
    rb._mesh_object("leaf", verts, faces, leaf, uv=tex_uv)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.3
    sc.world = world
    light = bpy.data.lights.new("key", type="AREA")
    light.energy = 4.0
    light.size = light_size_m
    key = bpy.data.objects.new("key", light)
    el, az, dist = math.radians(50), math.radians(30), 0.6
    pos = np.array([dist * math.cos(el) * math.cos(az), dist * math.cos(el) * math.sin(az), dist * math.sin(el)])
    key.location = pos.tolist()
    key.rotation_mode = "QUATERNION"
    key.rotation_quaternion = rb._look_quaternion(-pos)
    sc.collection.objects.link(key)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ORTHO_MM / 1000
    cam = bpy.data.objects.new("cam", cam_data)
    cam.matrix_world = Matrix(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0.3), (0, 0, 0, 1)))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.filepath = str(Path(out_png).resolve())
    bpy.ops.render.render(write_still=True)
    return imread(out_png, cv2.IMREAD_COLOR)


def _image_mask(tex_mask: np.ndarray, aspect: float, rot_deg: float) -> np.ndarray:
    """Leaf mask in the rendered image (orthographic, centred, rotated like the mesh)."""
    px_per_mm = IMG_PX / ORTHO_MM
    Lp, Wp = LEAF_LEN_MM * px_per_mm, LEAF_LEN_MM * aspect * px_per_mm
    tm = cv2.resize(tex_mask.astype(np.uint8), (max(1, int(round(Lp))), max(1, int(round(Wp)))),
                    interpolation=cv2.INTER_NEAREST)
    tm = tm[::-1]                                   # texture v=0 is the bottom row in Blender; image y points down
    canvas = np.zeros((IMG_PX, IMG_PX), np.uint8)
    y0, x0 = (IMG_PX - tm.shape[0]) // 2, (IMG_PX - tm.shape[1]) // 2
    canvas[y0:y0 + tm.shape[0], x0:x0 + tm.shape[1]] = tm
    M = cv2.getRotationMatrix2D((IMG_PX / 2 - 0.5, IMG_PX / 2 - 0.5), rot_deg, 1.0)   # CCW in image = CCW about +z seen from above
    return cv2.warpAffine(canvas, M, (IMG_PX, IMG_PX), flags=cv2.INTER_NEAREST).astype(bool)


def _rendered_leaf(bgr: np.ndarray) -> np.ndarray:
    """Pixels covered by the (green) leaf in the render - the rolled leaf is narrower than its flat mask."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 1] > 40) & (hsv[:, :, 0] >= 20) & (hsv[:, :, 0] <= 95)


def _metrics(bgr: np.ndarray, mask: np.ndarray, rect: np.ndarray, sigma: float) -> dict[str, float]:
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
    inner = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    hp = g - cv2.GaussianBlur(g, (0, 0), sigma)
    paper = float(np.median(g[~cv2.dilate(rect.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)]))
    return dict(brightness_rel=float(g[inner].mean()) / paper, contrast_rel=float(hp[inner].std()) / paper)


def run(bank_json: Path, out_dir: Path, *, light_sizes, bump_strengths, bump_distance_m: float, samples: int,
        component_prefix: str, sigma_px: float, bump_distances=None, roughnesses=(0.5,), rolls=(0.0,),
        max_textures: int | None = None, device: str = "CPU", relief_amps=(0.0,), speculars=(None,),
        mesh_n: int = 24) -> dict[str, Any]:
    bank_json = Path(bank_json)
    bank = json.loads(bank_json.read_text(encoding="utf-8"))
    texs = [t for t in bank["textures"] if str(t.get("component_id", "")).startswith(component_prefix)]
    texs = sorted(texs, key=lambda t: t["component_id"])[:max_textures] if max_textures else texs
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    import itertools

    for size, bs, bd, rough, roll, amp, spec in itertools.product(light_sizes, bump_strengths,
                                                                  bump_distances or [bump_distance_m], roughnesses,
                                                                  rolls, relief_amps, speculars):
        if True:
            ch_b, ch_c = [], []
            for t in texs:
                tex = bank_json.parent / t["file"]
                hgt = bank_json.parent / t["height_file"]
                tmask = _leaf_mask_tex(hgt)
                vals = []
                for rot in (0, 90, 180, 270):
                    img = _render(tex, hgt, t["aspect"], rot, light_size_m=size, bump_strength=bs,
                                  bump_distance_m=bd, samples=samples, out_png=out_dir / "tmp.png",
                                  roughness=rough, roll_deg=roll, device=device, relief_amp_rel=amp,
                                  specular=spec, mesh_n=mesh_n)
                    m = _image_mask(tmask, t["aspect"], rot) & _rendered_leaf(img)
                    rect = _rendered_leaf(img) | _image_mask(np.ones_like(tmask), t["aspect"], rot)
                    vals.append(_metrics(img, m, rect, sigma_px))
                b = np.array([v["brightness_rel"] for v in vals])
                c = np.array([v["contrast_rel"] for v in vals])
                ch_b.append(float(np.ptp(b) / b.mean()))
                ch_c.append(float(np.ptp(c) / c.mean()))
            results.append(dict(key_light_size_m=size, bump_strength=bs, bump_distance_m=bd, roughness=rough,
                                roll_deg=roll, relief_amp_rel=amp, specular=spec, mesh_n=mesh_n, n=len(texs),
                                brightness_change_p50=float(np.median(ch_b)), contrast_change_p50=float(np.median(ch_c)),
                                brightness_change_p10_p90=np.percentile(ch_b, [10, 90]).tolist(),
                                contrast_change_p10_p90=np.percentile(ch_c, [10, 90]).tolist()))
            print(json.dumps(results[-1]), flush=True)
    return dict(results=results, bump_distance_m=bump_distance_m, samples=samples, image_px=IMG_PX,
                textures=[t["file"] for t in texs])
