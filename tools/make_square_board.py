"""Create and verify 190 mm, 5x5 or 7x7 ChArUco A4 print artifacts.

Run with a Python environment containing OpenCV. Pass the PDF runtime interpreter
and Poppler executable explicitly. Shared pipeline configuration is not modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


def layout_pdf(build_dir: Path, squares: int) -> None:
    """Lay out the verified board image at exact physical dimensions."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    stem = f"charuco_board_{squares}x{squares}_190mm"
    spec = json.loads((build_dir / f"{stem}_spec.json").read_text())
    pdf_path = build_dir / f"{stem}_A4.pdf"
    marker_count = squares * squares // 2
    corner_count = (squares - 1) ** 2
    board_left_mm, board_top_mm = 10.0, 20.0
    board_bottom_mm = 297.0 - board_top_mm - spec["board_height_mm"]
    square_mm = spec["square_size_mm"]
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    pdf.setTitle(f"ChArUco {squares}x{squares} - 190 x 190 mm - A4 actual size")
    pdf.setAuthor("Tomato 3D phenotyping")
    pdf.drawImage(str(build_dir / f"{stem}.png"),
                  board_left_mm * mm, board_bottom_mm * mm,
                  width=190.0 * mm, height=190.0 * mm)
    pdf.setFont("Helvetica", 7)
    for index in range(squares):
        pdf.drawCentredString((board_left_mm + (index + 0.5) * square_mm) * mm,
                             (297.0 - board_top_mm + 3.0) * mm, str(index + 1))
        pdf.drawRightString(8.0 * mm,
                            (297.0 - board_top_mm - (index + 0.5) * square_mm) * mm - 2,
                            chr(65 + index))
    ruler_y_mm = 57.0
    pdf.setLineWidth(0.4)
    pdf.line(10 * mm, ruler_y_mm * mm, 110 * mm, ruler_y_mm * mm)
    for tick in range(101):
        tick_height_mm = 3.0 if tick % 10 == 0 else (2.0 if tick % 5 == 0 else 1.0)
        pdf.line((10 + tick) * mm, ruler_y_mm * mm,
                 (10 + tick) * mm, (ruler_y_mm + tick_height_mm) * mm)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(113 * mm, 56.4 * mm, "100 mm - measure after printing")
    pdf.setFont("Helvetica", 8)
    lines = [
        f"ChArUco  DICT_4X4_50   squares {squares} x {squares}   board 190 x 190 mm",
        f"Square {square_mm:.6f} mm   marker {spec['marker_size_mm']:.6f} mm   corners {corner_count}   markers {marker_count}",
        "PRINT AT 100% / ACTUAL SIZE - disable 'fit to page'. A4 portrait.",
        "Matte paper. Mount flat. Verify the 100 mm ruler before calibration.",
        f"Detector settings: use the accompanying {squares}x{squares} board specification JSON.",
    ]
    for index, line in enumerate(lines):
        pdf.drawString(10 * mm, (48 - 4.5 * index) * mm, line)
    pdf.showPage()
    pdf.save()


def generate_and_verify(build_dir: Path, pdf_python: Path, pdftoppm: Path, squares: int) -> None:
    """Generate marker-safe labels and verify the rasterized final PDF."""
    import cv2
    import numpy as np

    build_dir.mkdir(parents=True, exist_ok=True)
    qa_dir = build_dir / "qa_square_board"
    qa_dir.mkdir(exist_ok=True)
    stem = f"charuco_board_{squares}x{squares}_190mm"
    marker_count = squares * squares // 2
    corner_count = (squares - 1) ** 2
    spec = {
        "schema_version": "1.0", "pattern": "charuco", "aruco_dict": "DICT_4X4_50",
        "squares_x": squares, "squares_y": squares,
        "square_size_mm": 190.0 / squares, "marker_size_mm": (190.0 / squares) * 22.0 / 30.0,
        "board_width_mm": 190.0, "board_height_mm": 190.0,
        "legacy_pattern": False, "marker_ids": list(range(marker_count)),
        "scope": "Printed pattern only; rig placement and pipeline configuration require matching values.",
    }
    spec_path = build_dir / f"{stem}_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    board = cv2.aruco.CharucoBoard((squares, squares), spec["square_size_mm"], spec["marker_size_mm"], dictionary)
    board.setLegacyPattern(False)
    plain = board.generateImage((4200, 4200), marginSize=0, borderBits=1)
    labelled = plain.copy()
    cell_px = 4200 // squares
    sample_offset_px = round(cell_px * 0.06)
    for row in range(squares):
        for col in range(squares):
            # A white corner margin identifies a marker-bearing square.
            if plain[row * cell_px + sample_offset_px, col * cell_px + sample_offset_px] != 0:
                continue
            label = f"{chr(65 + row)}{col + 1}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale, thickness = 3.5 * cell_px / 600, round(9 * cell_px / 600)
            (width_px, height_px), _ = cv2.getTextSize(label, font, scale, thickness)
            origin_px = (col * cell_px + (cell_px - width_px) // 2,
                         row * cell_px + (cell_px + height_px) // 2)
            cv2.putText(labelled, label, origin_px, font, scale, 255, thickness, cv2.LINE_AA)
    detector = cv2.aruco.CharucoDetector(board)

    def detect(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
        corners, ids, _, marker_ids = detector.detectBoard(image)
        assert corners is not None and ids is not None and marker_ids is not None
        order = np.argsort(ids.ravel())
        return corners.reshape(-1, 2)[order], ids.ravel()[order], len(marker_ids)

    def padded(image: np.ndarray) -> np.ndarray:
        return cv2.copyMakeBorder(image, 100, 100, 100, 100, cv2.BORDER_CONSTANT, value=255)

    base_corners, base_ids, base_markers = detect(padded(plain))
    coded_corners, coded_ids, coded_markers = detect(padded(labelled))
    assert len(base_ids) == len(coded_ids) == corner_count
    assert base_markers == coded_markers == marker_count
    assert np.array_equal(base_ids, coded_ids)
    displacement_px = float(np.max(np.linalg.norm(base_corners - coded_corners, axis=1)))
    assert displacement_px == 0.0, displacement_px
    cv2.imencode(".png", labelled)[1].tofile(str(build_dir / f"{stem}.png"))
    subprocess.run([str(pdf_python), str(Path(__file__).resolve()), "--layout", "--squares", str(squares), "--build-dir", str(build_dir)], check=True)
    pdf_path = build_dir / f"{stem}_A4.pdf"
    prefix = qa_dir / f"{squares}x{squares}_300dpi"
    subprocess.run([str(pdftoppm), "-r", "300", "-singlefile", "-png", str(pdf_path), str(prefix)], check=True)
    raster = cv2.imdecode(np.fromfile(str(prefix.with_suffix(".png")), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    _, raster_ids, raster_markers = detect(raster)
    assert len(raster_ids) == corner_count and raster_markers == marker_count
    pixels_per_mm = 300 / 25.4
    # Restrict to the board and use its black corner squares to measure outer extent.
    x0, y0 = int(9 * pixels_per_mm), int(19 * pixels_per_mm)
    crop = raster[y0:int(211 * pixels_per_mm), x0:int(201 * pixels_per_mm)]
    ys, xs = np.where(crop < 64)
    width_mm = float((xs.max() - xs.min() + 1) / pixels_per_mm)
    height_mm = float((ys.max() - ys.min() + 1) / pixels_per_mm)
    assert abs(width_mm - 190) < 0.2 and abs(height_mm - 190) < 0.2
    report = {
        "squares_x": squares, "squares_y": squares,
        "markers_detected": coded_markers, "markers_expected": marker_count,
        "corners_detected": len(coded_ids), "corners_expected": corner_count,
        "cell_code_max_corner_displacement_px": displacement_px,
        "pdf_raster_dpi": 300, "pdf_raster_board_width_mm": width_mm,
        "pdf_raster_board_height_mm": height_mm,
        "pdf_raster_square_width_mm": width_mm / squares,
        "pdf_raster_square_height_mm": height_mm / squares,
        "pdf_raster_markers_detected": raster_markers,
        "pdf_raster_corners_detected": len(raster_ids),
        "physical_print_verified": False, "opencv_version": cv2.__version__,
    }
    (build_dir / f"{stem}_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Preview only; all verification uses the full 300 dpi raster.
    preview = cv2.resize(raster, (849, 1200), interpolation=cv2.INTER_AREA)
    cv2.imencode(".png", preview)[1].tofile(str(qa_dir / f"{squares}x{squares}_preview.png"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=Path("build"))
    parser.add_argument("--squares", type=int, choices=(5, 7), default=7)
    parser.add_argument("--pdf-python", type=Path)
    parser.add_argument("--pdftoppm", type=Path)
    parser.add_argument("--layout", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.layout:
        layout_pdf(args.build_dir.resolve(), args.squares)
    else:
        if args.pdf_python is None or args.pdftoppm is None:
            parser.error("--pdf-python and --pdftoppm are required")
        generate_and_verify(args.build_dir.resolve(), args.pdf_python, args.pdftoppm, args.squares)
