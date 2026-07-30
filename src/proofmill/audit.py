from __future__ import annotations

import hashlib
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

from proofmill.guidance import guidance_for
from proofmill.models import AuditReport, Issue, Severity
from proofmill.pdfinspect import DocumentFacts, PageFacts, inspect_pdf
from proofmill.profiles import (
    BLEED_INCH,
    POINTS_PER_INCH,
    BookSpec,
    expected_cover_points,
    expected_interior_points,
    inside_margin_in,
    outside_margin_in,
    spine_width_in,
    supported_page_range,
)

MAX_FILE_BYTES = 650 * 1024 * 1024
DIMENSION_TOLERANCE_POINTS = 1.0
POSITION_TOLERANCE_POINTS = 0.5


def _digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def _issue(
    code: str,
    severity: Severity,
    message: str,
    *,
    page: int | None = None,
    evidence: dict[str, Any] | None = None,
) -> Issue:
    guidance = guidance_for(code)
    return Issue(
        code=code,
        severity=severity,
        title=guidance.title,
        message=message,
        repair=guidance.repair,
        page=page,
        evidence=evidence or {},
        source_url=guidance.source_url,
    )


def _sort_issues(issues: Iterable[Issue]) -> tuple[Issue, ...]:
    return tuple(
        sorted(
            issues,
            key=lambda item: (
                -item.severity.rank,
                item.page if item.page is not None else 0,
                item.code,
                str(item.evidence),
            ),
        )
    )


def _common_issues(facts: DocumentFacts, size_bytes: int) -> list[Issue]:
    issues: list[Issue] = []
    if size_bytes > MAX_FILE_BYTES:
        issues.append(
            _issue(
                "FILE_TOO_LARGE",
                Severity.ERROR,
                f"The PDF is {size_bytes / 1024 / 1024:.1f} MB; the profile limit is 650 MB.",
                evidence={"size_bytes": size_bytes, "limit_bytes": MAX_FILE_BYTES},
            )
        )
    if facts.encrypted:
        issues.append(
            _issue(
                "PDF_ENCRYPTED",
                Severity.ERROR,
                "The PDF is encrypted and cannot be reliably inspected or submitted.",
            )
        )
    if facts.parse_error:
        issues.append(
            _issue(
                "PDF_PARSE_ERROR",
                Severity.ERROR,
                "ProofMill could not parse the PDF.",
                evidence={"parser_error": facts.parse_error},
            )
        )
        return issues

    for font in facts.fonts:
        if not font.embedded:
            issues.append(
                _issue(
                    "FONT_NOT_EMBEDDED",
                    Severity.ERROR,
                    f"Font {font.base_font} is referenced but not embedded.",
                    evidence={
                        "font": font.base_font,
                        "subtype": font.subtype,
                        "pages": sorted(font.pages)[:20],
                    },
                )
            )
        elif font.subset:
            issues.append(
                _issue(
                    "FONT_SUBSET",
                    Severity.INFO,
                    f"Font {font.base_font} is embedded as a subset.",
                    evidence={"font": font.base_font, "pages": sorted(font.pages)[:20]},
                )
            )

    annotation_pages = [
        {"page": page.number, "count": page.annotation_count}
        for page in facts.pages
        if page.annotation_count
    ]
    if annotation_pages:
        issues.append(
            _issue(
                "ANNOTATIONS_PRESENT",
                Severity.ERROR,
                f"Found annotations on {len(annotation_pages)} page(s).",
                evidence={"pages": annotation_pages[:20]},
            )
        )
    if facts.form_field_count:
        issues.append(
            _issue(
                "FORM_FIELDS_PRESENT",
                Severity.ERROR,
                f"Found {facts.form_field_count} interactive form field(s).",
                evidence={"field_count": facts.form_field_count},
            )
        )
    if facts.has_javascript:
        issues.append(
            _issue(
                "JAVASCRIPT_PRESENT",
                Severity.ERROR,
                "The PDF contains a JavaScript name tree or open action.",
            )
        )
    if facts.has_attachments:
        issues.append(
            _issue(
                "ATTACHMENTS_PRESENT",
                Severity.ERROR,
                "The PDF contains one or more embedded files.",
            )
        )
    if facts.bookmark_count:
        issues.append(
            _issue(
                "BOOKMARKS_PRESENT",
                Severity.WARNING,
                f"Found {facts.bookmark_count} bookmark item(s).",
                evidence={"bookmark_count": facts.bookmark_count},
            )
        )

    transparent_pages = [page.number for page in facts.pages if page.has_transparency]
    if transparent_pages:
        issues.append(
            _issue(
                "TRANSPARENCY_PRESENT",
                Severity.WARNING,
                f"Transparency or a soft mask appears on {len(transparent_pages)} page(s).",
                evidence={"pages": transparent_pages[:30]},
            )
        )

    low_dpi: list[dict[str, Any]] = []
    excessive_dpi: list[dict[str, Any]] = []
    for page in facts.pages:
        for image in page.images:
            if image.dpi_x is None or image.dpi_y is None:
                continue
            effective = min(image.dpi_x, image.dpi_y)
            sample = {
                "page": page.number,
                "effective_dpi": round(effective, 1),
                "bbox": [
                    round(image.x0, 2),
                    round(image.top, 2),
                    round(image.x1, 2),
                    round(image.bottom, 2),
                ],
                "pixels": [image.pixel_width, image.pixel_height],
            }
            if effective < 299.5:
                low_dpi.append(sample)
            elif max(image.dpi_x, image.dpi_y) > 600.5:
                excessive_dpi.append(sample)
    if low_dpi:
        issues.append(
            _issue(
                "IMAGE_LOW_DPI",
                Severity.ERROR,
                f"Found {len(low_dpi)} placed image(s) below 300 effective DPI.",
                evidence={"count": len(low_dpi), "samples": low_dpi[:12]},
            )
        )
    if excessive_dpi:
        issues.append(
            _issue(
                "IMAGE_EXCESSIVE_DPI",
                Severity.INFO,
                f"Found {len(excessive_dpi)} placed image(s) above 600 effective DPI.",
                evidence={"count": len(excessive_dpi), "samples": excessive_dpi[:12]},
            )
        )

    thin_lines: list[dict[str, Any]] = []
    for page in facts.pages:
        for width in page.line_widths:
            if 0.01 < width < 0.75:
                thin_lines.append({"page": page.number, "width_points": round(width, 3)})
    if thin_lines:
        issues.append(
            _issue(
                "THIN_LINE",
                Severity.WARNING,
                f"Found {len(thin_lines)} vector stroke(s) thinner than 0.75 point.",
                evidence={"count": len(thin_lines), "samples": thin_lines[:20]},
            )
        )
    return issues


def _safe_text_rect(
    page: PageFacts,
    spec: BookSpec,
    page_count: int,
) -> tuple[float, float, float, float]:
    bleed_points = float(BLEED_INCH * POINTS_PER_INCH) if spec.bleed else 0.0
    trim_width_points = float(spec.trim_width_in * POINTS_PER_INCH)
    trim_height_points = float(spec.trim_height_in * POINTS_PER_INCH)
    right_page = page.number % 2 == 1
    if spec.direction == "rtl":
        right_page = not right_page

    trim_x0 = 0.0 if not spec.bleed or right_page else bleed_points
    trim_x1 = trim_x0 + trim_width_points
    trim_top = bleed_points
    trim_bottom = trim_top + trim_height_points

    gutter = float(inside_margin_in(page_count) * POINTS_PER_INCH)
    outside = float(outside_margin_in(spec.bleed) * POINTS_PER_INCH)
    if right_page:
        safe_x0 = trim_x0 + gutter
        safe_x1 = trim_x1 - outside
    else:
        safe_x0 = trim_x0 + outside
        safe_x1 = trim_x1 - gutter
    return safe_x0, safe_x1, trim_top + outside, trim_bottom - outside


def _outside_rect(
    bbox: tuple[float, float, float, float],
    rect: tuple[float, float, float, float],
) -> bool:
    x0, x1, top, bottom = bbox
    safe_x0, safe_x1, safe_top, safe_bottom = rect
    return (
        x0 < safe_x0 - POSITION_TOLERANCE_POINTS
        or x1 > safe_x1 + POSITION_TOLERANCE_POINTS
        or top < safe_top - POSITION_TOLERANCE_POINTS
        or bottom > safe_bottom + POSITION_TOLERANCE_POINTS
    )


def _blank_runs(pages: tuple[PageFacts, ...], minimum: int = 3) -> list[list[int]]:
    runs: list[list[int]] = []
    current: list[int] = []
    for page in pages:
        if page.is_blank:
            current.append(page.number)
        else:
            if len(current) >= minimum:
                runs.append(current)
            current = []
    if len(current) >= minimum:
        runs.append(current)
    return runs


def audit_interior(path: Path, spec: BookSpec) -> AuditReport:
    path = path.resolve()
    size_bytes = path.stat().st_size
    facts = inspect_pdf(path)
    issues = _common_issues(facts, size_bytes)

    if facts.parse_error is None and not facts.encrypted:
        page_count = facts.page_count
        minimum, maximum = supported_page_range(spec)
        if not minimum <= page_count <= maximum:
            issues.append(
                _issue(
                    "PAGE_COUNT_OUT_OF_RANGE",
                    Severity.ERROR,
                    (
                        f"The selected options support {minimum}-{maximum} pages; "
                        f"this PDF has {page_count}."
                    ),
                    evidence={"actual": page_count, "minimum": minimum, "maximum": maximum},
                )
            )
        if page_count % 2:
            issues.append(
                _issue(
                    "ODD_PAGE_COUNT",
                    Severity.INFO,
                    f"KDP will round {page_count} pages up to {page_count + 1} for printing.",
                    evidence={"actual": page_count, "effective": page_count + 1},
                )
            )

        expected_width, expected_height = expected_interior_points(spec)
        mismatches: list[dict[str, Any]] = []
        rotations: list[dict[str, Any]] = []
        spreads: list[int] = []
        sizes: set[tuple[float, float]] = set()
        for page in facts.pages:
            sizes.add((round(page.width, 2), round(page.height, 2)))
            if (
                abs(page.width - expected_width) > DIMENSION_TOLERANCE_POINTS
                or abs(page.height - expected_height) > DIMENSION_TOLERANCE_POINTS
            ):
                mismatches.append(
                    {
                        "page": page.number,
                        "actual_points": [round(page.width, 2), round(page.height, 2)],
                    }
                )
            if page.rotation % 360:
                rotations.append({"page": page.number, "rotation": page.rotation})
            if (
                page.width > expected_width * 1.7
                and abs(page.height - expected_height) <= DIMENSION_TOLERANCE_POINTS * 3
            ):
                spreads.append(page.number)
        if mismatches:
            issues.append(
                _issue(
                    "PAGE_SIZE_MISMATCH",
                    Severity.ERROR,
                    (
                        f"{len(mismatches)} page(s) differ from the expected "
                        f"{expected_width:.2f} x {expected_height:.2f} points."
                    ),
                    evidence={
                        "expected_points": [round(expected_width, 2), round(expected_height, 2)],
                        "pages": mismatches[:20],
                    },
                )
            )
        if len(sizes) > 1:
            issues.append(
                _issue(
                    "PAGE_SIZE_INCONSISTENT",
                    Severity.ERROR,
                    f"The interior contains {len(sizes)} different page sizes.",
                    evidence={"sizes_points": [list(size) for size in sorted(sizes)[:20]]},
                )
            )
        if rotations:
            issues.append(
                _issue(
                    "PAGE_ROTATED",
                    Severity.WARNING,
                    f"Found encoded page rotation on {len(rotations)} page(s).",
                    evidence={"pages": rotations[:20]},
                )
            )
        if spreads:
            issues.append(
                _issue(
                    "SPREAD_DETECTED",
                    Severity.ERROR,
                    f"{len(spreads)} page(s) look like reader spreads rather than single pages.",
                    evidence={"pages": spreads[:20]},
                )
            )

        unsafe_by_page: list[dict[str, Any]] = []
        for page in facts.pages:
            safe_rect = _safe_text_rect(page, spec, page_count)
            unsafe = [
                item
                for item in page.text
                if _outside_rect((item.x0, item.x1, item.top, item.bottom), safe_rect)
            ]
            if unsafe:
                unsafe_by_page.append(
                    {
                        "page": page.number,
                        "count": len(unsafe),
                        "safe_rect_points": [round(value, 2) for value in safe_rect],
                        "samples": [
                            {
                                "bbox": [
                                    round(item.x0, 2),
                                    round(item.top, 2),
                                    round(item.x1, 2),
                                    round(item.bottom, 2),
                                ],
                                "text_fingerprint": item.fingerprint,
                            }
                            for item in unsafe[:5]
                        ],
                    }
                )
        if unsafe_by_page:
            count = sum(item["count"] for item in unsafe_by_page)
            issues.append(
                _issue(
                    "TEXT_OUTSIDE_SAFE_AREA",
                    Severity.ERROR,
                    f"Found {count} text item(s) crossing a required margin.",
                    evidence={"pages": unsafe_by_page[:30]},
                )
            )

        blank_runs = _blank_runs(facts.pages)
        if blank_runs:
            issues.append(
                _issue(
                    "EXCESSIVE_BLANK_PAGES",
                    Severity.WARNING,
                    f"Found {len(blank_runs)} run(s) of at least three blank pages.",
                    evidence={"runs": blank_runs},
                )
            )

    return AuditReport(
        kind="interior",
        filename=path.name,
        sha256=_digest(path),
        size_bytes=size_bytes,
        page_count=facts.page_count,
        spec=spec.as_dict(),
        facts=facts.report_summary(),
        issues=_sort_issues(issues),
    )


def _cover_safe_rect(page: PageFacts) -> tuple[float, float, float, float]:
    safe = 0.25 * 72.0
    return safe, page.width - safe, safe, page.height - safe


def audit_cover(path: Path, spec: BookSpec) -> AuditReport:
    if spec.page_count is None:
        raise ValueError("cover preflight requires the final interior page count")
    path = path.resolve()
    size_bytes = path.stat().st_size
    facts = inspect_pdf(path)
    issues = _common_issues(facts, size_bytes)

    effective_pages = spec.page_count + (spec.page_count % 2)
    if spec.page_count % 2:
        issues.append(
            _issue(
                "ODD_PAGE_COUNT",
                Severity.INFO,
                (
                    f"Cover math uses {effective_pages} pages because KDP rounds "
                    f"{spec.page_count} up to an even count."
                ),
                evidence={"actual": spec.page_count, "effective": effective_pages},
            )
        )

    if facts.parse_error is None and not facts.encrypted:
        if facts.page_count != 1:
            issues.append(
                _issue(
                    "COVER_PAGE_COUNT",
                    Severity.ERROR,
                    f"The cover PDF has {facts.page_count} pages; exactly one is required.",
                    evidence={"actual": facts.page_count, "expected": 1},
                )
            )
        if facts.pages:
            page = facts.pages[0]
            expected_width, expected_height = expected_cover_points(spec, effective_pages)
            if (
                abs(page.width - expected_width) > DIMENSION_TOLERANCE_POINTS
                or abs(page.height - expected_height) > DIMENSION_TOLERANCE_POINTS
            ):
                issues.append(
                    _issue(
                        "COVER_SIZE_MISMATCH",
                        Severity.ERROR,
                        (
                            f"The cover is {page.width:.2f} x {page.height:.2f} points; "
                            f"expected {expected_width:.2f} x {expected_height:.2f}."
                        ),
                        evidence={
                            "actual_points": [round(page.width, 2), round(page.height, 2)],
                            "expected_points": [
                                round(expected_width, 2),
                                round(expected_height, 2),
                            ],
                            "spine_width_in": float(spine_width_in(spec, effective_pages)),
                        },
                    )
                )
            if page.rotation % 360:
                issues.append(
                    _issue(
                        "PAGE_ROTATED",
                        Severity.WARNING,
                        f"The cover page has an encoded rotation of {page.rotation} degrees.",
                        page=1,
                        evidence={"rotation": page.rotation},
                    )
                )

            safe_rect = _cover_safe_rect(page)
            unsafe = [
                item
                for item in page.text
                if _outside_rect((item.x0, item.x1, item.top, item.bottom), safe_rect)
            ]
            if unsafe:
                issues.append(
                    _issue(
                        "COVER_TEXT_OUTSIDE_SAFE_AREA",
                        Severity.ERROR,
                        f"Found {len(unsafe)} cover text item(s) crossing the outside safe area.",
                        evidence={
                            "safe_rect_points": [round(value, 2) for value in safe_rect],
                            "samples": [
                                {
                                    "bbox": [
                                        round(item.x0, 2),
                                        round(item.top, 2),
                                        round(item.x1, 2),
                                        round(item.bottom, 2),
                                    ],
                                    "text_fingerprint": item.fingerprint,
                                }
                                for item in unsafe[:10]
                            ],
                        },
                    )
                )

            bleed = float(BLEED_INCH * POINTS_PER_INCH)
            trim_width = float(spec.trim_width_in * POINTS_PER_INCH)
            spine_width = float(spine_width_in(spec, effective_pages) * POINTS_PER_INCH)
            spine_x0 = bleed + trim_width
            spine_x1 = spine_x0 + spine_width
            spine_text = [
                item for item in page.text if spine_x0 <= (item.x0 + item.x1) / 2 <= spine_x1
            ]
            if effective_pages <= 79 and spine_text:
                issues.append(
                    _issue(
                        "SPINE_TEXT_NOT_ALLOWED",
                        Severity.ERROR,
                        (
                            f"Found {len(spine_text)} text item(s) in the spine area "
                            f"at {effective_pages} pages."
                        ),
                        evidence={
                            "page_count": effective_pages,
                            "spine_points": [round(spine_x0, 2), round(spine_x1, 2)],
                        },
                    )
                )
            elif spine_text:
                clearance = float(Decimal("0.0625") * POINTS_PER_INCH)
                unsafe_spine = [
                    item
                    for item in spine_text
                    if item.x0 < spine_x0 + clearance or item.x1 > spine_x1 - clearance
                ]
                if unsafe_spine:
                    issues.append(
                        _issue(
                            "SPINE_TEXT_CLEARANCE",
                            Severity.ERROR,
                            (
                                f"{len(unsafe_spine)} spine text item(s) do not keep "
                                "0.0625 inch clearance from both folds."
                            ),
                            evidence={
                                "spine_points": [round(spine_x0, 2), round(spine_x1, 2)],
                                "required_clearance_points": round(clearance, 2),
                            },
                        )
                    )

    return AuditReport(
        kind="cover",
        filename=path.name,
        sha256=_digest(path),
        size_bytes=size_bytes,
        page_count=facts.page_count,
        spec={**spec.as_dict(), "effective_page_count": effective_pages},
        facts=facts.report_summary(),
        issues=_sort_issues(issues),
    )
