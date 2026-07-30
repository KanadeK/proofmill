from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from proofmill.audit import audit_cover, audit_interior
from proofmill.models import AuditBundle
from proofmill.profiles import BookSpec
from proofmill.reports import bundle_json


def _spec(*, pages: int | None = None) -> BookSpec:
    return BookSpec(Decimal("6"), Decimal("9"), page_count=pages)


def test_good_interior_and_cover_pass(example_dir: Path) -> None:
    interior = audit_interior(example_dir / "good-interior.pdf", _spec())
    cover = audit_cover(example_dir / "good-cover.pdf", _spec(pages=120))
    assert interior.status == "pass"
    assert cover.status == "pass"
    assert interior.page_count == 24
    assert cover.spec["effective_page_count"] == 120
    assert all(issue.code == "FONT_SUBSET" for issue in (*interior.issues, *cover.issues))


def test_bad_interior_finds_independent_failures(example_dir: Path) -> None:
    report = audit_interior(example_dir / "bad-interior.pdf", _spec())
    codes = {issue.code for issue in report.issues}
    assert {
        "ANNOTATIONS_PRESENT",
        "EXCESSIVE_BLANK_PAGES",
        "FONT_NOT_EMBEDDED",
        "IMAGE_LOW_DPI",
        "PAGE_COUNT_OUT_OF_RANGE",
        "PAGE_SIZE_MISMATCH",
        "TEXT_OUTSIDE_SAFE_AREA",
        "THIN_LINE",
        "TRANSPARENCY_PRESENT",
    } <= codes
    serialized = bundle_json(AuditBundle((report,)))
    assert "Unsafe edge text" not in serialized
    assert "text_fingerprint" in serialized


def test_bad_cover_finds_size_edge_and_spine_failures(example_dir: Path) -> None:
    report = audit_cover(example_dir / "bad-cover.pdf", _spec(pages=40))
    codes = {issue.code for issue in report.issues}
    assert {
        "ANNOTATIONS_PRESENT",
        "COVER_SIZE_MISMATCH",
        "COVER_TEXT_OUTSIDE_SAFE_AREA",
        "FONT_NOT_EMBEDDED",
        "SPINE_TEXT_NOT_ALLOWED",
    } <= codes


def test_odd_page_cover_uses_even_effective_count(example_dir: Path) -> None:
    report = audit_cover(example_dir / "good-cover.pdf", _spec(pages=119))
    assert report.spec["effective_page_count"] == 120
    assert "ODD_PAGE_COUNT" in {issue.code for issue in report.issues}
    assert "COVER_SIZE_MISMATCH" not in {issue.code for issue in report.issues}


def test_encrypted_and_corrupt_pdfs_are_reported(example_dir: Path, tmp_path: Path) -> None:
    source = PdfReader(example_dir / "good-interior.pdf")
    writer = PdfWriter()
    writer.append_pages_from_reader(source)
    writer.encrypt("secret")
    encrypted = tmp_path / "encrypted.pdf"
    with encrypted.open("wb") as stream:
        writer.write(stream)
    encrypted_report = audit_interior(encrypted, _spec())
    assert {issue.code for issue in encrypted_report.issues} == {"PDF_ENCRYPTED"}

    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"%PDF-1.7\nnot a real PDF")
    corrupt_report = audit_interior(corrupt, _spec())
    assert "PDF_PARSE_ERROR" in {issue.code for issue in corrupt_report.issues}


def test_json_report_contains_stable_hash(example_dir: Path) -> None:
    report = audit_interior(example_dir / "good-interior.pdf", _spec())
    payload = json.loads(bundle_json(AuditBundle((report,))))
    assert len(payload["reports"][0]["sha256"]) == 64
    assert "generated_at" not in payload


def test_catalog_features_are_reported(example_dir: Path, tmp_path: Path) -> None:
    reader = PdfReader(example_dir / "good-interior.pdf")
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_attachment("note.txt", b"synthetic")
    writer.add_js("app.alert('synthetic')")
    writer.add_outline_item("Synthetic bookmark", 0)
    path = tmp_path / "catalog-features.pdf"
    with path.open("wb") as stream:
        writer.write(stream)
    report = audit_interior(path, _spec())
    codes = {issue.code for issue in report.issues}
    assert {"ATTACHMENTS_PRESENT", "JAVASCRIPT_PRESENT", "BOOKMARKS_PRESENT"} <= codes


def test_mixed_rotated_and_spread_pages_are_reported(example_dir: Path, tmp_path: Path) -> None:
    reader = PdfReader(example_dir / "good-interior.pdf")
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.pages[1].mediabox.upper_right = (500, 648)
    writer.pages[2].mediabox.upper_right = (864, 648)
    writer.pages[3].rotate(90)
    path = tmp_path / "mixed.pdf"
    with path.open("wb") as stream:
        writer.write(stream)
    report = audit_interior(path, _spec())
    codes = {issue.code for issue in report.issues}
    assert {"PAGE_SIZE_INCONSISTENT", "PAGE_ROTATED", "SPREAD_DETECTED"} <= codes


def test_cover_requires_one_pdf_page(example_dir: Path) -> None:
    report = audit_cover(example_dir / "good-interior.pdf", _spec(pages=120))
    assert "COVER_PAGE_COUNT" in {issue.code for issue in report.issues}
