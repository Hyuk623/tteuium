"""RGB rendering with Blender (``bpy``, headless, Cycles CPU) in the undistorted render space.

The camera is the square-pixel pinhole of :class:`camera.RenderGeometry` with the real
solved pose; the result is warped into the distorted output by the same map as the masks.
Domain randomisation (leaf colour, translucency, roughness, key light, ambient, backdrop,
white balance, noise) comes from ``generator_config.json`` ranges via the scene parameters.

Blender units are metres; geometry arrives in board-frame millimetres.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.synth.images import imread, imwrite

MM = 1e-3
#: Leaflet textures are normalised to this mean sRGB (tomato3d.synth.textures.MEAN_SRGB); the material gain maps
#: it to the scene's ``leaf_srgb_mean`` in linear space.
TEXTURE_MEAN_SRGB = 0.5


def _bpy():
    import bpy  # lazy: tomato_synth env only

    return bpy


def _srgb_to_linear(c: float) -> float:
    c = min(max(c, 0.0), 1.0)
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def chroma_to_linear_rgb(r: float, g: float, srgb_mean: float) -> tuple[float, float, float, float]:
    """Photo chromaticity (sRGB r, g, b = 1 - r - g) at mean sRGB channel ``srgb_mean``, as linear RGBA."""
    b = max(0.0, 1.0 - r - g)
    k = 3.0 * srgb_mean
    return (_srgb_to_linear(r * k), _srgb_to_linear(g * k), _srgb_to_linear(b * k), 1.0)


def reset() -> None:
    bpy = _bpy()
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _material(name: str, color, roughness: float, translucency: float = 0.0, image: Path | None = None,
              interpolation: str = "Closest", height: Path | None = None, bump_strength: float = 0.0,
              bump_distance_m: float = 0.0005, specular: float | None = None):
    bpy = _bpy()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    if specular is not None:
        bsdf.inputs["Specular IOR Level"].default_value = float(specular)
    shader = bsdf
    if image is not None:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(Path(image).resolve()))
        tex.interpolation = interpolation
        mul = nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        links.new(tex.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = color
        links.new(mul.outputs[2], bsdf.inputs["Base Color"])
    bump = None
    if height is not None and bump_strength > 0:
        htex = nodes.new("ShaderNodeTexImage")
        htex.image = bpy.data.images.load(str(Path(height).resolve()))
        htex.image.colorspace_settings.name = "Non-Color"
        htex.interpolation = "Linear"
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = float(bump_strength)
        bump.inputs["Distance"].default_value = float(bump_distance_m)
        links.new(htex.outputs["Color"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if translucency > 0:
        tr = nodes.new("ShaderNodeBsdfTranslucent")
        tr.inputs["Color"].default_value = color
        if image is not None:
            links.new(mul.outputs[2], tr.inputs["Color"])
        if bump is not None:
            links.new(bump.outputs["Normal"], tr.inputs["Normal"])
        mix = nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = translucency
        links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        links.new(tr.outputs["BSDF"], mix.inputs[2])
        shader = mix
    links.new(shader.outputs[0], out.inputs["Surface"])
    return mat


def _mesh_object(name: str, verts_mm: np.ndarray, faces: np.ndarray, mat, uv: np.ndarray | None = None):
    bpy = _bpy()
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata((np.asarray(verts_mm) * MM).tolist(), [], np.asarray(faces).tolist())
    if uv is not None:
        layer = mesh.uv_layers.new(name="uv")
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                layer.data[li].uv = uv[mesh.loops[li].vertex_index].tolist()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def enable_gpu() -> str:
    """Enable every OptiX (else CUDA) device for Cycles; return the backend or raise."""
    bpy = _bpy()
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend
            return f"{backend}: " + ", ".join(d.name for d in gpus)
    raise RuntimeError("no OptiX/CUDA device available to Cycles")


#: Defaults reproduce every run before Addendum D B5b (soft 0.3 m key light, no relief).
LOOK_DEFAULTS = dict(key_light_size_m=0.3, bump_strength=0.0, bump_distance_m=0.0005, leaf_specular=None,
                     leaf_roughness=None)


def build_scene(parts: list[dict[str, Any]], sp: dict[str, Any], board_texture: Path, *, samples: int,
                backdrop_distance_mm: float, pot_center_mm: np.ndarray, device: str = "CPU",
                look: dict[str, float] | None = None) -> None:
    """Create every object, material and light for one plant scene (``device`` CPU or GPU)."""
    bpy = _bpy()
    lk = dict(LOOK_DEFAULTS, **(look or {}))
    reset()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    if device == "GPU":
        enable_gpu()
    scene.cycles.device = device
    scene.cycles.samples = int(samples)
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    leaf_rgb = chroma_to_linear_rgb(sp["leaf_chroma_r"], sp["leaf_chroma_g"], sp["leaf_srgb_mean"])
    stem_rgb = chroma_to_linear_rgb(sp["leaf_chroma_r"], sp["leaf_chroma_g"], sp["leaf_srgb_mean"] * 1.3)
    gray = sp["backdrop_gray"]
    mats = {
        "leaf": _material("leaf", leaf_rgb, sp["leaf_roughness"], sp["leaf_translucency"]),
        "stem": _material("stem", stem_rgb, 0.6, 0.1),
        "pot": _material("pot", (0.02, 0.02, 0.022, 1.0), 0.35),
        "soil": _material("soil", (0.06, 0.04, 0.025, 1.0), 0.95),
        "board": _material("board", (0.8, 0.8, 0.8, 1.0), 0.8, image=board_texture),
        "backdrop": _material("backdrop", (gray, gray, gray, 1.0), 0.9),
        "floor": _material("floor", (0.04, 0.04, 0.04, 1.0), 0.9),
    }
    tex_gain = _srgb_to_linear(sp["leaf_srgb_mean"]) / _srgb_to_linear(TEXTURE_MEAN_SRGB)
    for part in parts:
        mat_info = part.get("material", {})
        kind = mat_info.get("kind", "stem")
        if kind == "leaf_tex":
            key = f"leaf_tex::{mat_info['texture']}"
            if key not in mats:
                tex_path = Path(mat_info["texture"])
                h_path = tex_path.with_name(tex_path.stem + "_h.png")
                rough = lk["leaf_roughness"] if lk["leaf_roughness"] is not None else sp["leaf_roughness"]
                mats[key] = _material(key, (tex_gain, tex_gain, tex_gain, 1.0), rough,
                                      sp["leaf_translucency"], image=tex_path, interpolation="Linear",
                                      height=h_path if h_path.exists() else None,
                                      bump_strength=lk["bump_strength"], bump_distance_m=lk["bump_distance_m"],
                                      specular=lk["leaf_specular"])
            kind = key
        _mesh_object(part["name"], part["vertices"], part["faces"], mats[kind], part.get("uv"))
    d = backdrop_distance_mm
    cx, cy = float(pot_center_mm[0]), float(pot_center_mm[1])
    floor = np.array([[cx - d, cy - d, -1.0], [cx + d, cy - d, -1.0], [cx + d, cy + d, -1.0], [cx - d, cy + d, -1.0]])
    _mesh_object("floor", floor, np.array([(0, 1, 2), (0, 2, 3)]), mats["floor"])
    walls = []
    for k in range(4):
        a0, a1 = k * math.pi / 2, (k + 1) * math.pi / 2
        p0 = [cx + d * math.cos(a0) * 1.42, cy + d * math.sin(a0) * 1.42]
        p1 = [cx + d * math.cos(a1) * 1.42, cy + d * math.sin(a1) * 1.42]
        walls.append(np.array([[*p0, -1.0], [*p1, -1.0], [*p1, 2 * d], [*p0, 2 * d]]))
    for i, w in enumerate(walls):
        _mesh_object(f"backdrop_{i}", w, np.array([(0, 1, 2), (0, 2, 3)]), mats["backdrop"])
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = sp["world_light_strength"]
    scene.world = world
    light = bpy.data.lights.new("key", type="AREA")
    light.energy = sp["key_light_power_w"]
    light.size = float(lk["key_light_size_m"])
    key = bpy.data.objects.new("key", light)
    el, az = math.radians(sp["key_light_elevation_deg"]), math.radians(sp["key_light_azimuth_deg"])
    dist = 0.6
    pos = np.array([cx * MM + dist * math.cos(el) * math.cos(az), cy * MM + dist * math.cos(el) * math.sin(az),
                    dist * math.sin(el)])
    key.location = pos.tolist()
    direction = np.array([cx * MM, cy * MM, 0.05]) - pos
    key.rotation_mode = "QUATERNION"
    key.rotation_quaternion = _look_quaternion(direction)
    scene.collection.objects.link(key)
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam


def _look_quaternion(direction: np.ndarray):
    from mathutils import Vector  # bpy companion

    return Vector(direction.tolist()).to_track_quat("-Z", "Y")


def render_view(K_render: np.ndarray, size_px: tuple[int, int], R: np.ndarray, t: np.ndarray,
                out_png: Path) -> np.ndarray:
    """Render the render-space pinhole view; return an ``uint8`` RGB array (H, W, 3)."""
    bpy = _bpy()
    from mathutils import Matrix

    scene = bpy.context.scene
    W, H = size_px
    scene.render.resolution_x, scene.render.resolution_y = W, H
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1.0
    cam = scene.camera.data
    cam.type = "PERSP"
    cam.sensor_fit = "HORIZONTAL" if W >= H else "VERTICAL"
    cam.sensor_width = cam.sensor_height = 36.0
    big = float(max(W, H))
    f = float(K_render[0, 0])
    cam.lens = f * 36.0 / big
    cx_edge, cy_edge = K_render[0, 2] + 0.5, K_render[1, 2] + 0.5
    cam.shift_x = (W / 2.0 - cx_edge) / big
    cam.shift_y = (cy_edge - H / 2.0) / big
    cam.clip_start, cam.clip_end = 0.005, 5.0
    c2w = np.eye(4)
    c2w[:3, :3] = R.T @ np.diag([1.0, -1.0, -1.0])
    c2w[:3, 3] = (-R.T @ t) * MM
    scene.camera.matrix_world = Matrix(c2w.tolist())
    scene.render.filepath = str(Path(out_png).resolve())
    bpy.ops.render.render(write_still=True)
    import cv2

    img = imread((Path(out_png).resolve()), cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def post_process(rgb: np.ndarray, sp: dict[str, Any], rng: np.random.Generator) -> np.ndarray:
    """White-balance jitter and sensor noise on the distorted output."""
    img = rgb.astype(np.float32) / 255.0
    gains = np.array([sp["wb_gain_r"], 1.0, sp["wb_gain_b"]], np.float32)
    img = img * gains[None, None]
    if sp["image_noise_sigma"] > 0:
        img = img + rng.normal(0.0, sp["image_noise_sigma"], img.shape).astype(np.float32)
    return (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
