from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve(value: Any) -> Any:
    if value is None:
        return None
    getter = getattr(value, "get_object", None)
    if getter is None:
        return value
    try:
        return getter()
    except Exception:
        return value


def _object_key(value: Any) -> tuple[str, int]:
    idnum = getattr(value, "idnum", None)
    if idnum is not None:
        return ("indirect", int(idnum))
    return ("direct", id(value))


@dataclass(frozen=True, slots=True)
class TextItem:
    x0: float
    x1: float
    top: float
    bottom: float
    size: float
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ImageItem:
    x0: float
    x1: float
    top: float
    bottom: float
    pixel_width: int | None
    pixel_height: int | None
    dpi_x: float | None
    dpi_y: float | None
    colorspace: str | None


@dataclass(frozen=True, slots=True)
class PageFacts:
    number: int
    width: float
    height: float
    rotation: int
    media_box: tuple[float, float, float, float]
    crop_box: tuple[float, float, float, float]
    trim_box: tuple[float, float, float, float] | None
    bleed_box: tuple[float, float, float, float] | None
    text: tuple[TextItem, ...]
    images: tuple[ImageItem, ...]
    line_widths: tuple[float, ...]
    annotation_count: int
    has_transparency: bool
    is_blank: bool


@dataclass(slots=True)
class FontFacts:
    base_font: str
    subtype: str
    embedded: bool
    subset: bool
    pages: set[int] = field(default_factory=set)

    def as_dict(self) -> dict[str, Any]:
        return {
            "base_font": self.base_font,
            "subtype": self.subtype,
            "embedded": self.embedded,
            "subset": self.subset,
            "pages": sorted(self.pages),
        }


@dataclass(frozen=True, slots=True)
class DocumentFacts:
    encrypted: bool
    parse_error: str | None
    pdf_header: str | None
    page_count: int
    pages: tuple[PageFacts, ...]
    fonts: tuple[FontFacts, ...]
    metadata_keys: tuple[str, ...]
    has_attachments: bool
    has_javascript: bool
    bookmark_count: int
    form_field_count: int

    def report_summary(self) -> dict[str, Any]:
        image_count = sum(len(page.images) for page in self.pages)
        low_dpi_count = sum(
            image.dpi_x is not None
            and image.dpi_y is not None
            and min(image.dpi_x, image.dpi_y) < 300
            for page in self.pages
            for image in page.images
        )
        return {
            "pdf_header": self.pdf_header,
            "encrypted": self.encrypted,
            "font_count": len(self.fonts),
            "embedded_font_count": sum(font.embedded for font in self.fonts),
            "image_count": image_count,
            "low_dpi_image_count": low_dpi_count,
            "annotation_count": sum(page.annotation_count for page in self.pages),
            "transparent_page_count": sum(page.has_transparency for page in self.pages),
            "blank_page_count": sum(page.is_blank for page in self.pages),
            "bookmark_count": self.bookmark_count,
            "form_field_count": self.form_field_count,
            "has_attachments": self.has_attachments,
            "has_javascript": self.has_javascript,
            "metadata_keys": list(self.metadata_keys),
        }


def _box_tuple(box: Any) -> tuple[float, float, float, float]:
    return (
        _number(getattr(box, "left", 0)),
        _number(getattr(box, "bottom", 0)),
        _number(getattr(box, "right", 0)),
        _number(getattr(box, "top", 0)),
    )


def _font_descriptor(font: Any) -> Any:
    descriptor = _resolve(font.get("/FontDescriptor"))
    if descriptor is not None:
        return descriptor
    descendants = _resolve(font.get("/DescendantFonts"))
    if descendants:
        descendant = _resolve(descendants[0])
        if descendant is not None:
            return _resolve(descendant.get("/FontDescriptor"))
    return None


def _collect_resource_facts(
    resources_ref: Any,
    page_number: int,
    fonts: dict[tuple[str, str, bool], FontFacts],
    seen: set[tuple[str, int]],
) -> bool:
    if resources_ref is None:
        return False
    key = _object_key(resources_ref)
    if key in seen:
        return False
    seen.add(key)
    resources = _resolve(resources_ref)
    if not hasattr(resources, "get"):
        return False

    transparent = False
    font_map = _resolve(resources.get("/Font"))
    if hasattr(font_map, "items"):
        for font_ref in font_map.values():
            font = _resolve(font_ref)
            if not hasattr(font, "get"):
                continue
            raw_name = str(font.get("/BaseFont", "Unknown")).lstrip("/")
            subtype = str(font.get("/Subtype", "Unknown")).lstrip("/")
            descriptor = _font_descriptor(font)
            embedded = subtype == "Type3"
            if descriptor is not None and hasattr(descriptor, "get"):
                embedded = embedded or any(
                    descriptor.get(name) is not None
                    for name in ("/FontFile", "/FontFile2", "/FontFile3")
                )
            subset = "+" in raw_name[:9]
            font_key = (raw_name, subtype, embedded)
            font_facts = fonts.setdefault(
                font_key,
                FontFacts(raw_name, subtype, embedded, subset),
            )
            font_facts.pages.add(page_number)

    ext_states = _resolve(resources.get("/ExtGState"))
    if hasattr(ext_states, "values"):
        for state_ref in ext_states.values():
            state = _resolve(state_ref)
            if not hasattr(state, "get"):
                continue
            stroke_alpha = _number(state.get("/CA"), 1.0)
            fill_alpha = _number(state.get("/ca"), 1.0)
            soft_mask = state.get("/SMask")
            if stroke_alpha < 0.999 or fill_alpha < 0.999:
                transparent = True
            if soft_mask is not None and str(soft_mask) != "/None":
                transparent = True

    xobjects = _resolve(resources.get("/XObject"))
    if hasattr(xobjects, "values"):
        for object_ref in xobjects.values():
            pdf_object = _resolve(object_ref)
            if not hasattr(pdf_object, "get"):
                continue
            subtype = str(pdf_object.get("/Subtype", ""))
            if pdf_object.get("/SMask") is not None or pdf_object.get("/Mask") is not None:
                transparent = True
            if subtype == "/Form":
                transparent = (
                    _collect_resource_facts(
                        pdf_object.get("/Resources"),
                        page_number,
                        fonts,
                        seen,
                    )
                    or transparent
                )
    return transparent


def _count_bookmarks(outline: Any) -> int:
    if isinstance(outline, list):
        return sum(_count_bookmarks(item) for item in outline)
    return 1


def _root_features(reader: PdfReader) -> tuple[bool, bool]:
    root = _resolve(reader.trailer.get("/Root"))
    if not hasattr(root, "get"):
        return False, False
    names = _resolve(root.get("/Names"))
    has_attachments = bool(hasattr(names, "get") and names.get("/EmbeddedFiles") is not None)
    has_javascript = bool(hasattr(names, "get") and names.get("/JavaScript") is not None)
    open_action = _resolve(root.get("/OpenAction"))
    if hasattr(open_action, "get") and str(open_action.get("/S", "")) == "/JavaScript":
        has_javascript = True
    return has_attachments, has_javascript


def _image_item(raw: Any) -> ImageItem:
    x0 = _number(raw.get("x0"))
    x1 = _number(raw.get("x1"))
    top = _number(raw.get("top"))
    bottom = _number(raw.get("bottom"))
    srcsize = raw.get("srcsize")
    pixel_width: int | None = None
    pixel_height: int | None = None
    if isinstance(srcsize, (tuple, list)) and len(srcsize) >= 2:
        pixel_width = int(srcsize[0])
        pixel_height = int(srcsize[1])
    display_width = abs(x1 - x0)
    display_height = abs(bottom - top)
    dpi_x = (
        pixel_width * 72.0 / display_width
        if pixel_width is not None and display_width > 0.01
        else None
    )
    dpi_y = (
        pixel_height * 72.0 / display_height
        if pixel_height is not None and display_height > 0.01
        else None
    )
    colorspace = raw.get("colorspace")
    return ImageItem(
        x0=x0,
        x1=x1,
        top=top,
        bottom=bottom,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        colorspace=str(colorspace) if colorspace is not None else None,
    )


def inspect_pdf(path: Path) -> DocumentFacts:
    try:
        reader = PdfReader(str(path), strict=False)
    except Exception as exc:
        return DocumentFacts(
            encrypted=False,
            parse_error=f"{type(exc).__name__}: {exc}",
            pdf_header=None,
            page_count=0,
            pages=(),
            fonts=(),
            metadata_keys=(),
            has_attachments=False,
            has_javascript=False,
            bookmark_count=0,
            form_field_count=0,
        )

    encrypted = bool(reader.is_encrypted)
    if encrypted:
        try:
            unlocked = bool(reader.decrypt(""))
        except Exception:
            unlocked = False
        if not unlocked:
            return DocumentFacts(
                encrypted=True,
                parse_error=None,
                pdf_header=getattr(reader, "pdf_header", None),
                page_count=0,
                pages=(),
                fonts=(),
                metadata_keys=(),
                has_attachments=False,
                has_javascript=False,
                bookmark_count=0,
                form_field_count=0,
            )

    try:
        page_count = len(reader.pages)
        metadata: Any = reader.metadata or {}
        metadata_keys = tuple(sorted(str(key) for key in metadata))
        has_attachments, has_javascript = _root_features(reader)
        try:
            bookmark_count = _count_bookmarks(reader.outline)
        except Exception:
            bookmark_count = 0
        try:
            form_field_count = len(reader.get_fields() or {})
        except Exception:
            form_field_count = 0

        fonts: dict[tuple[str, str, bool], FontFacts] = {}
        page_resource_facts: dict[int, bool] = {}
        for page_number, reader_page_obj in enumerate(reader.pages, start=1):
            page_resource_facts[page_number] = _collect_resource_facts(
                reader_page_obj.get("/Resources"),
                page_number,
                fonts,
                set(),
            )

        pages: list[PageFacts] = []
        used_font_names: set[str] = set()
        with pdfplumber.open(path) as document:
            for page_number, layout_page in enumerate(document.pages, start=1):
                raw_words = layout_page.extract_words(
                    x_tolerance=1,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    extra_attrs=["fontname", "size"],
                )
                used_font_names.update(
                    str(word["fontname"]) for word in raw_words if word.get("fontname") is not None
                )
                text_items = tuple(
                    TextItem(
                        x0=_number(word.get("x0")),
                        x1=_number(word.get("x1")),
                        top=_number(word.get("top")),
                        bottom=_number(word.get("bottom")),
                        size=_number(word.get("size")),
                        fingerprint=_fingerprint(str(word.get("text", ""))),
                    )
                    for word in raw_words
                )
                images = tuple(_image_item(image) for image in layout_page.images)
                vector_objects = [
                    *layout_page.lines,
                    *layout_page.rects,
                    *layout_page.curves,
                ]
                line_widths = tuple(
                    width
                    for item in vector_objects
                    if (width := _number(item.get("linewidth"), -1.0)) >= 0
                )

                reader_page = reader.pages[page_number - 1]
                annots = _resolve(reader_page.get("/Annots"))
                annotation_count = len(annots) if isinstance(annots, list) else 0
                trim_box_ref = reader_page.get("/TrimBox")
                bleed_box_ref = reader_page.get("/BleedBox")
                pages.append(
                    PageFacts(
                        number=page_number,
                        width=float(layout_page.width),
                        height=float(layout_page.height),
                        rotation=int(layout_page.rotation or 0),
                        media_box=_box_tuple(reader_page.mediabox),
                        crop_box=_box_tuple(reader_page.cropbox),
                        trim_box=_box_tuple(_resolve(trim_box_ref)) if trim_box_ref else None,
                        bleed_box=_box_tuple(_resolve(bleed_box_ref)) if bleed_box_ref else None,
                        text=text_items,
                        images=images,
                        line_widths=line_widths,
                        annotation_count=annotation_count,
                        has_transparency=page_resource_facts.get(page_number, False),
                        is_blank=not text_items and not images and not vector_objects,
                    )
                )
    except Exception as exc:
        return DocumentFacts(
            encrypted=encrypted,
            parse_error=f"{type(exc).__name__}: {exc}",
            pdf_header=getattr(reader, "pdf_header", None),
            page_count=0,
            pages=(),
            fonts=(),
            metadata_keys=(),
            has_attachments=False,
            has_javascript=False,
            bookmark_count=0,
            form_field_count=0,
        )

    used_fonts = tuple(
        font
        for font in sorted(fonts.values(), key=lambda item: (item.base_font, item.subtype))
        if font.base_font in used_font_names
    )
    return DocumentFacts(
        encrypted=encrypted,
        parse_error=None,
        pdf_header=getattr(reader, "pdf_header", None),
        page_count=page_count,
        pages=tuple(pages),
        fonts=used_fonts,
        metadata_keys=metadata_keys,
        has_attachments=has_attachments,
        has_javascript=has_javascript,
        bookmark_count=bookmark_count,
        form_field_count=form_field_count,
    )


def _fingerprint(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
