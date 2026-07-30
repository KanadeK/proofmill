from __future__ import annotations

import argparse
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import reportlab
from PIL import Image
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from proofmill.profiles import BookSpec, expected_cover_points

FONT_NAME = "ProofMillVera"


def _register_font() -> str:
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return FONT_NAME
    font_path = Path(reportlab.__file__).resolve().parent / "fonts" / "Vera.ttf"
    if not font_path.is_file():
        raise FileNotFoundError(f"ReportLab test font not found: {font_path}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))
    return FONT_NAME


def make_good_interior(path: Path, pages: int = 24) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    font = _register_font()
    document = canvas.Canvas(
        str(path),
        pagesize=(6 * 72, 9 * 72),
        pageCompression=1,
        invariant=1,
    )
    document.setTitle("ProofMill clean interior fixture")
    document.setAuthor("ProofMill")
    for page_number in range(1, pages + 1):
        document.setFillColor(HexColor("#1E2923"))
        document.setFont(font, 9)
        document.drawString(72, 604, "THE QUIET WORKSHOP")
        document.setFillColor(HexColor("#65736A"))
        document.drawRightString(360, 604, str(page_number))
        document.setFillColor(HexColor("#1E2923"))
        document.setFont(font, 11)
        document.drawString(72, 540, f"Chapter note {page_number}")
        document.setFont(font, 9)
        lines = [
            "This synthetic page stays inside mirrored print margins.",
            "It is committed only as deterministic preflight example data.",
            "No private manuscript text is required to exercise the scanner.",
        ]
        for offset, line in enumerate(lines):
            document.drawString(72, 510 - offset * 18, line)
        document.setLineWidth(1)
        document.setStrokeColor(HexColor("#AAB7AF"))
        document.line(72, 84, 360, 84)
        document.showPage()
    document.save()


def make_good_cover(path: Path, pages: int = 120) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    font = _register_font()
    spec = BookSpec(
        trim_width_in=Decimal("6"),
        trim_height_in=Decimal("9"),
        ink="black",
        paper="white",
        page_count=pages,
    )
    width, height = expected_cover_points(spec, pages)
    document = canvas.Canvas(
        str(path),
        pagesize=(width, height),
        pageCompression=1,
        invariant=1,
    )
    document.setTitle("ProofMill clean cover fixture")
    document.setFillColor(HexColor("#163F32"))
    document.rect(0, 0, width, height, stroke=0, fill=1)
    spine_width = width - (12.25 * 72)
    front_x0 = 0.125 * 72 + 6 * 72 + spine_width
    document.setFillColor(HexColor("#F4EBDD"))
    document.setFont(font, 30)
    document.drawString(front_x0 + 54, height - 150, "THE QUIET")
    document.drawString(front_x0 + 54, height - 190, "WORKSHOP")
    document.setFont(font, 11)
    document.drawString(front_x0 + 54, height - 228, "A deterministic sample cover")
    document.setFont(font, 10)
    document.drawString(54, 110, "Back cover copy remains inside the safe area.")
    document.save()


def _low_resolution_image() -> ImageReader:
    image = Image.new("RGB", (24, 24), "#B73737")
    stream = BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return ImageReader(stream)


def make_bad_interior(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(
        str(path),
        pagesize=(8.5 * 72, 11 * 72),
        pageCompression=1,
        invariant=1,
    )
    document.setTitle("ProofMill intentionally broken interior fixture")
    document.setFont("Helvetica", 6)
    document.drawString(3, 3, "Unsafe edge text")
    document.setFont("Helvetica", 12)
    document.drawString(42, 730, "Intentionally broken print interior")
    document.drawImage(_low_resolution_image(), 72, 400, width=144, height=144)
    document.setLineWidth(0.25)
    document.line(42, 380, 300, 380)
    set_alpha = getattr(document, "setFillAlpha", None)
    if set_alpha is not None:
        set_alpha(0.45)
        document.setFillColor(Color(0.2, 0.4, 0.8))
        document.rect(280, 400, 120, 120, stroke=0, fill=1)
        set_alpha(1)
    document.linkURL("https://example.com", (42, 710, 220, 740), relative=0)
    document.showPage()
    for _ in range(3):
        document.showPage()
    document.save()


def make_bad_cover(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(
        str(path),
        pagesize=(8.5 * 72, 11 * 72),
        pageCompression=1,
        invariant=1,
    )
    document.setTitle("ProofMill intentionally broken cover fixture")
    document.setFont("Helvetica", 18)
    document.drawString(2, 770, "Text outside safe edge")
    document.setFont("Helvetica", 8)
    document.saveState()
    document.translate(444, 360)
    document.rotate(90)
    document.drawCentredString(0, 0, "SPINE TEXT")
    document.restoreState()
    document.linkURL("https://example.com", (2, 760, 220, 790), relative=0)
    document.save()


def generate_all(output: Path) -> None:
    make_good_interior(output / "good-interior.pdf")
    make_good_cover(output / "good-cover.pdf")
    make_bad_interior(output / "bad-interior.pdf")
    make_bad_cover(output / "bad-cover.pdf")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("examples/generated"))
    args = parser.parse_args()
    generate_all(args.output)
    print(f"Generated fixtures in {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
