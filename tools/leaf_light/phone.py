"""Prepare ordinary RGB phone images without modifying originals or inventing depth.

Use the identical conversion for calibration and study images. PNG pixels are upright
and EXIF orientation is removed. The profile catches observable changes; missing EXIF
cannot prove that focus, zoom, lens switching, or computational processing stayed fixed.
"""
from __future__ import annotations

from pathlib import Path

from .common import StudyError, file_hash, output_dir, read_json, write_json, write_rows

SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".dng"}
METADATA_TAGS = {"make": 271, "model": 272, "lens_model": 42036,
                 "focal_length_mm": 37386, "digital_zoom_ratio": 41988}
NUMERIC_TAGS = {"focal_length_mm", "digital_zoom_ratio"}


def read_phone_image(path: Path) -> tuple[object, dict]:
    from PIL import Image, ImageOps
    # Some photo exports name HEIF containers .DNG. Inspect the bytes, never
    # treat a true RAW/DNG TIFF as an already-developed RGB photograph.
    with path.open("rb") as stream:
        iso_container = stream.read(12)[4:8] == b"ftyp"
    misnamed_dng = path.suffix.lower() == ".dng"
    if misnamed_dng and not iso_container:
        raise StudyError("RAW/DNG is not an RGB input; export original-size HEIF or JPEG")
    if path.suffix.lower() in {".heic", ".heif"} or iso_container:
        try:
            from pillow_heif import register_heif_opener
        except ImportError as exc:
            raise StudyError("HEIC requires optional pillow-heif, or an original-size JPEG export") from exc
        register_heif_opener()
    with Image.open(path) as original:
        if misnamed_dng and original.format != "HEIF":
            raise StudyError("Only HEIF content mislabeled .DNG is supported; export RAW as RGB")
        exif = original.getexif()
        nested = exif.get_ifd(34665) if 34665 in exif else {}
        metadata = {}
        for name, tag in METADATA_TAGS.items():
            value = nested.get(tag, exif.get(tag))
            metadata[name] = (float(value) if name in NUMERIC_TAGS else str(value).strip()) if value is not None else None
        metadata["source_orientation"] = int(exif.get(274, 1))
        if metadata["source_orientation"] not in range(1, 9):
            raise StudyError(f"Invalid EXIF orientation: {path.name}")
        # HEIF decoders may already apply container orientation; respect their exposed EXIF.
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.info.clear()
        metadata["image_width_px"], metadata["image_height_px"] = image.size
        return image, metadata


def normalize(source: Path, camera_id: str, out: Path, reference_profile: Path | None = None) -> dict:
    paths = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES)
    if not paths:
        raise StudyError("No JPEG, PNG, HEIC, HEIF, or HEIF mislabeled .DNG photographs found")
    if not camera_id.strip():
        raise StudyError("Supply an ID for this physical phone + lens + capture mode")
    names = [p.stem.casefold() for p in paths]
    if len(set(names)) != len(names):
        raise StudyError("Duplicate file stems would overwrite working images")
    metadata_rows = []
    for path in paths:
        image, meta = read_phone_image(path)
        image.close()
        metadata_rows.append(meta)
    constant = {}
    for key in metadata_rows[0]:
        values = {r[key] for r in metadata_rows if r[key] is not None}
        if len(values) > 1:
            raise StudyError(f"Phone images mix {key}; keep one lens, zoom, resolution and device orientation")
        constant[key] = next(iter(values)) if values else None
    incomplete = [k for k in METADATA_TAGS if any(r[k] is None for r in metadata_rows)]
    reference = read_json(reference_profile) if reference_profile else None
    if reference:
        if reference["camera_id"] != camera_id:
            raise StudyError("Phone camera ID differs from calibration profile")
        for key, value in constant.items():
            expected = reference["capture_settings"].get(key)
            if value is not None and expected is not None and value != expected:
                raise StudyError(f"Phone {key} differs from calibration profile")
    folder = output_dir(out)
    image_dir = folder / "images"
    image_dir.mkdir()
    mapping = []
    for path, expected in zip(paths, metadata_rows):
        source_hash = file_hash(path)
        image, actual = read_phone_image(path)
        if actual != expected:
            raise StudyError("Source image metadata changed during preparation")
        target = image_dir / f"{path.stem}.png"
        image.save(target, format="PNG")
        image.close()
        if source_hash != file_hash(path):
            raise StudyError("Source image changed during conversion")
        mapping.append(dict(source_file=str(path.resolve()), working_file=f"images/{target.name}",
                            source_sha256=source_hash, working_sha256=file_hash(target), **actual))
    write_rows(folder / "phone_images.csv", mapping, list(mapping[0]))
    result = {"schema_version": "phone-rgb-1", "camera_id": camera_id,
              "capture_settings": constant, "metadata_incomplete": incomplete,
              "reference_profile_sha256": file_hash(reference_profile) if reference_profile else None,
              "image_mapping_sha256": file_hash(folder / "phone_images.csv"),
              "processing": "EXIF upright RGB PNG; no resizing, cropping, depth estimation or colour calibration",
              "notice": "File order is not a capture schedule. Record view identities explicitly in the session plan. EXIF checks do not prove fixed focus or unchanged image processing. HEIF content named .DNG is decoded as RGB; true RAW/DNG is not developed here."}
    write_json(folder / "phone_profile.json", result)
    return result


def validate_profile(profile_path: Path, intrinsics: object, selected_paths: list[Path]) -> dict:
    """Bind prepared phone pixels to their profile and calibrated image dimensions."""
    from .common import rows
    profile = read_json(profile_path)
    if profile["schema_version"] != "phone-rgb-1":
        raise StudyError("Unsupported phone profile")
    settings = profile["capture_settings"]
    if profile["camera_id"] != intrinsics.camera_id or (
        settings["image_height_px"], settings["image_width_px"]
    ) != intrinsics.image_shape:
        raise StudyError("Phone profile disagrees with calibrated camera or resolution")
    mapping_path = profile_path.parent / "phone_images.csv"
    if file_hash(mapping_path) != profile["image_mapping_sha256"]:
        raise StudyError("Phone mapping changed")
    mapping = {(profile_path.parent / r["working_file"]).resolve(): r for r in rows(mapping_path)}
    for path in selected_paths:
        row = mapping.get(path.resolve())
        if row is None or file_hash(path) != row["working_sha256"]:
            raise StudyError("Selected image is absent from or changed since phone normalization")
    return profile
