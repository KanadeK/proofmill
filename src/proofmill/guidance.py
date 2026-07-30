from __future__ import annotations

from dataclasses import dataclass

from proofmill.profiles import (
    KDP_FIX_URL,
    KDP_FONT_URL,
    KDP_IMAGE_URL,
    KDP_SUBMISSION_URL,
    KDP_TRIM_URL,
)


@dataclass(frozen=True, slots=True)
class Guidance:
    title: str
    repair: str
    source_url: str


GUIDANCE: dict[str, Guidance] = {
    "PDF_ENCRYPTED": Guidance(
        "Encrypted PDF",
        "Export an unlocked PDF. Remove owner and user passwords before running preflight again.",
        KDP_SUBMISSION_URL,
    ),
    "PDF_PARSE_ERROR": Guidance(
        "Unreadable PDF",
        "Open the source in the authoring tool, export a fresh PDF, and confirm it opens locally.",
        KDP_FIX_URL,
    ),
    "FILE_TOO_LARGE": Guidance(
        "PDF exceeds the upload limit",
        "Downsample only images above the recommended range, then export below 650 MB.",
        KDP_SUBMISSION_URL,
    ),
    "PAGE_COUNT_OUT_OF_RANGE": Guidance(
        "Page count is outside the selected print option",
        "Choose compatible ink, paper, and trim settings or change the manuscript page count.",
        KDP_TRIM_URL,
    ),
    "ODD_PAGE_COUNT": Guidance(
        "Odd page count",
        (
            "Confirm the automatically added trailing blank page is acceptable "
            "before sizing the cover."
        ),
        KDP_FIX_URL,
    ),
    "PAGE_SIZE_MISMATCH": Guidance(
        "Page dimensions do not match the selected trim and bleed",
        "Set the document page size to the exact expected dimensions, export again, and rerun.",
        KDP_TRIM_URL,
    ),
    "PAGE_SIZE_INCONSISTENT": Guidance(
        "Pages use inconsistent dimensions",
        "Make every interior page the same single-page size; remove spreads and mixed inserts.",
        KDP_SUBMISSION_URL,
    ),
    "PAGE_ROTATED": Guidance(
        "Page rotation is encoded in the PDF",
        "Apply rotation in the source layout and export pages with rotation set to zero.",
        KDP_SUBMISSION_URL,
    ),
    "SPREAD_DETECTED": Guidance(
        "Possible two-page spread",
        "Export one PDF page per printed page rather than reader spreads or two-up sheets.",
        KDP_SUBMISSION_URL,
    ),
    "FONT_NOT_EMBEDDED": Guidance(
        "Font is not embedded",
        (
            "Enable font embedding in the authoring tool or replace the font "
            "with one licensed to embed."
        ),
        KDP_FONT_URL,
    ),
    "FONT_SUBSET": Guidance(
        "Font is embedded as a subset",
        (
            "If the print preview changes glyphs, export with full font embedding; "
            "otherwise review the proof."
        ),
        KDP_FONT_URL,
    ),
    "TEXT_OUTSIDE_SAFE_AREA": Guidance(
        "Live text crosses the safe margin",
        (
            "Move the named text inward. Recheck italic overhangs, hidden spaces, "
            "and mirrored gutters."
        ),
        KDP_FIX_URL,
    ),
    "IMAGE_LOW_DPI": Guidance(
        "Image is below 300 effective DPI",
        (
            "Replace it with a higher-resolution source or reduce its placed size "
            "without resampling upward."
        ),
        KDP_IMAGE_URL,
    ),
    "IMAGE_EXCESSIVE_DPI": Guidance(
        "Image is above the recommended 600 DPI",
        (
            "Downsample the source image near 300-600 DPI if file size or upload "
            "processing is a problem."
        ),
        KDP_IMAGE_URL,
    ),
    "THIN_LINE": Guidance(
        "Line is thinner than 0.75 point",
        "Increase the stroke to at least 0.75 point in the source document and export again.",
        KDP_SUBMISSION_URL,
    ),
    "TRANSPARENCY_PRESENT": Guidance(
        "Transparency or soft mask is present",
        (
            "Flatten transparent objects in the source file, then inspect gradients "
            "and shadows in a proof."
        ),
        KDP_FIX_URL,
    ),
    "ANNOTATIONS_PRESENT": Guidance(
        "PDF annotations are present",
        "Remove comments, links, sticky notes, and other annotations from the print export.",
        KDP_SUBMISSION_URL,
    ),
    "FORM_FIELDS_PRESENT": Guidance(
        "Interactive form fields are present",
        "Export a static print PDF without AcroForm fields or widgets.",
        KDP_SUBMISSION_URL,
    ),
    "JAVASCRIPT_PRESENT": Guidance(
        "PDF JavaScript is present",
        "Remove document actions and scripts, then export a static PDF.",
        KDP_SUBMISSION_URL,
    ),
    "ATTACHMENTS_PRESENT": Guidance(
        "Embedded files are present",
        "Remove PDF attachments and package only the single print document.",
        KDP_SUBMISSION_URL,
    ),
    "BOOKMARKS_PRESENT": Guidance(
        "Bookmarks are present",
        (
            "Export a print-only PDF without bookmarks if the upload preview "
            "reports processing errors."
        ),
        KDP_SUBMISSION_URL,
    ),
    "EXCESSIVE_BLANK_PAGES": Guidance(
        "Consecutive blank pages detected",
        (
            "Inspect the reported pages and remove accidental blanks while "
            "preserving intentional pagination."
        ),
        KDP_FIX_URL,
    ),
    "COVER_PAGE_COUNT": Guidance(
        "Cover PDF must contain one page",
        "Export the full back-spine-front wrap as one continuous PDF page.",
        KDP_SUBMISSION_URL,
    ),
    "COVER_SIZE_MISMATCH": Guidance(
        "Cover dimensions do not match the trim, paper, ink, and page count",
        "Regenerate the cover after the interior is final, using the exact reported spine width.",
        KDP_SUBMISSION_URL,
    ),
    "SPINE_TEXT_NOT_ALLOWED": Guidance(
        "Spine text is not supported at this page count",
        "Remove spine text for books with 79 pages or fewer.",
        KDP_SUBMISSION_URL,
    ),
    "SPINE_TEXT_CLEARANCE": Guidance(
        "Spine text is too close to a fold",
        "Keep spine text at least 0.0625 inch from both fold lines.",
        KDP_SUBMISSION_URL,
    ),
    "COVER_TEXT_OUTSIDE_SAFE_AREA": Guidance(
        "Cover text crosses the safe area",
        "Move live cover text at least 0.25 inch from the outside cover edge.",
        KDP_SUBMISSION_URL,
    ),
}


def guidance_for(code: str) -> Guidance:
    try:
        return GUIDANCE[code]
    except KeyError as exc:
        raise KeyError(f"unknown ProofMill rule code: {code}") from exc
