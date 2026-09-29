"""Export or inspect reconstructed triangle CSV with the optional Open3D viewer."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .common import StudyError, output_dir, rows


def vertices(path: Path, variant_id: str) -> np.ndarray:
    records = [r for r in rows(path) if r.get("geometry_variant_id", r.get("variant_id")) == variant_id]
    if not records:
        raise StudyError("No triangles for that variant")
    result = np.asarray([[[float(r[f"v{k}_{axis}_mm"]) for axis in "xyz"] for k in range(3)] for r in records])
    if not np.isfinite(result).all():
        raise StudyError("Non-finite mesh")
    return result


def export(path: Path, variant_id: str, out: Path) -> None:
    tri = vertices(path, variant_id)
    folder = output_dir(out)
    with (folder / "leaves_mm.ply").open("w", encoding="ascii") as stream:
        stream.write("ply\nformat ascii 1.0\ncomment units millimetres; coordinate frame inherited from CSV\n")
        stream.write(f"element vertex {tri.size//3}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(tri)}\nproperty list uchar int vertex_indices\nend_header\n")
        for xyz in tri.reshape(-1, 3):
            stream.write(" ".join(map(str, xyz)) + "\n")
        for i in range(len(tri)):
            stream.write(f"3 {3*i} {3*i+1} {3*i+2}\n")


def view(path: Path, variant_id: str) -> None:
    try:
        import open3d as o3d
    except ImportError as exc:
        raise StudyError("Optional Open3D is not installed. Use export-mesh for an external viewer, or install Open3D in a supported Python environment.") from exc
    tri = vertices(path, variant_id)
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(tri.reshape(-1, 3))
    mesh.triangles = o3d.utility.Vector3iVector(np.arange(tri.size//3).reshape(-1, 3))
    mesh.compute_vertex_normals()
    mesh.paint_uniform_color([0.2, 0.65, 0.3])
    o3d.visualization.draw_geometries([mesh], mesh_show_back_face=True)
