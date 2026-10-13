"""Addendum D B5a/B5b: texture alignment and UV, height maps, textures shipped inside render jobs."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from tomato3d.synth.scene import leaflet_texture_uv, pick_texture
from tomato3d.synth.textures import TEX_SIZE, align_crop, height_map, make_texture


def _leaf(angle_deg=30.0):
    img = np.full((300, 400, 3), 255, np.uint8)
    mask = np.zeros((300, 400), np.uint8)
    # ovate leaflet: wider near the base (left before rotation)
    pts = np.array([[60, 150], [120, 95], [220, 105], [340, 145], [220, 195], [120, 205]], np.int32)
    cv2.fillPoly(mask, [pts], 1)
    img[mask.astype(bool)] = (60, 140, 90)
    for x in range(90, 330, 30):
        cv2.line(img, (x, 110), (x + 20, 190), (40, 100, 60), 2)
    M = cv2.getRotationMatrix2D((200, 150), angle_deg, 1.0)
    return (cv2.warpAffine(img, M, (400, 300), borderValue=(255, 255, 255)),
            cv2.warpAffine(mask, M, (400, 300), flags=cv2.INTER_NEAREST).astype(bool))


def test_align_crop_puts_base_left_and_axis_horizontal():
    img, mask = _leaf(30.0)
    al = align_crop(img, mask)
    assert al is not None
    _, m = al
    assert m.shape[1] > m.shape[0]                        # principal axis horizontal
    widths = m.sum(axis=0)
    assert widths[: len(widths) // 2].sum() >= widths[len(widths) // 2:].sum()   # wider half on the left


def test_texture_has_no_paper_and_fixed_size():
    img, mask = _leaf(-20.0)
    t = make_texture(img, mask)
    assert t["texture"].shape[:2] == (TEX_SIZE[1], TEX_SIZE[0])
    assert np.all(t["texture"] < 250)                     # outside filled with leaf colour, never the sheet
    h = t["height"]
    assert h.shape[:2] == (TEX_SIZE[1], TEX_SIZE[0]) and h.dtype == np.uint8
    assert h.std() > 2                                    # relief present


def test_height_map_flat_outside_leaf():
    img, mask = _leaf(0.0)
    h = height_map(img, mask)
    out = cv2.resize((~mask).astype(np.uint8), TEX_SIZE, interpolation=cv2.INTER_NEAREST)
    out = cv2.erode(out, np.ones((7, 7), np.uint8)).astype(bool)          # skip the resampled outline band
    assert np.all(np.abs(h[out].astype(int) - 127) <= 1)


def test_uv_and_texture_choice_are_deterministic():
    uv = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 0.2], [0.5, -0.2]])
    tuv = leaflet_texture_uv(uv, 0.4)
    assert np.allclose(tuv[:, 0], uv[:, 0]) and np.allclose(tuv[2:, 1], [1.0, 0.0])
    bank = [dict(path=f"t{i}.png", aspect=0.5) for i in range(7)]
    assert pick_texture(bank, "scene_0001/L03/P1L") is pick_texture(bank, "scene_0001/L03/P1L")


def test_render_job_ships_textures_and_heights(tmp_path):
    from tomato3d.synth.render_remote import export_job, load_parts

    src = tmp_path / "bank"
    src.mkdir()
    cv2.imwrite(str(src / "tex_000.png"), np.full((8, 8, 3), 100, np.uint8))
    cv2.imwrite(str(src / "tex_000_h.png"), np.full((8, 8), 128, np.uint8))
    board = tmp_path / "board.png"
    cv2.imwrite(str(board), np.zeros((4, 4), np.uint8))
    parts = [dict(name="leaf", organ="leaflet", vertices=np.zeros((3, 3)), faces=np.array([[0, 1, 2]]),
                  uv=np.zeros((3, 2)), material=dict(kind="leaf_tex", texture=str(src / "tex_000.png")))]
    scene = dict(scene_id="scene_0000", seed=1, scene_params={}, parts=parts, scene_dir=tmp_path / "scene")
    jdir = export_job(scene, [], samples=8, backdrop_distance_mm=100.0, pot_center_mm=np.zeros(3), board_texture=board,
                      look=dict(bump_strength=1.0))
    job = json.loads((jdir / "job.json").read_text())
    assert job["parts"][0]["material"]["texture"] == "textures/tex_000.png" and job["look"]["bump_strength"] == 1.0
    assert (jdir / "textures" / "tex_000.png").exists() and (jdir / "textures" / "tex_000_h.png").exists()
    loaded = load_parts(jdir, job)
    assert Path(loaded[0]["material"]["texture"]).is_absolute()
