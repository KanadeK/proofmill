from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation

POINTS_PER_INCH = Decimal("72")
BLEED_INCH = Decimal("0.125")

KDP_SUBMISSION_URL = "https://kdp.amazon.com/en_US/help/topic/G201857950"
KDP_TRIM_URL = "https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6"
KDP_FONT_URL = "https://kdp.amazon.com/en_US/help/topic/G202145450"
KDP_IMAGE_URL = "https://kdp.amazon.com/en_US/help/topic/G202169030"
KDP_FIX_URL = "https://kdp.amazon.com/en_US/help/topic/G201834260"

PROFILE_SNAPSHOT = "2026-07-30"

TRIM_PRESETS: dict[str, tuple[Decimal, Decimal]] = {
    "5x8": (Decimal("5"), Decimal("8")),
    "5.25x8": (Decimal("5.25"), Decimal("8")),
    "5.5x8.5": (Decimal("5.5"), Decimal("8.5")),
    "6x9": (Decimal("6"), Decimal("9")),
    "6.14x9.21": (Decimal("6.14"), Decimal("9.21")),
    "6.69x9.61": (Decimal("6.69"), Decimal("9.61")),
    "7x10": (Decimal("7"), Decimal("10")),
    "7.5x9.25": (Decimal("7.5"), Decimal("9.25")),
    "8x10": (Decimal("8"), Decimal("10")),
    "8.25x8.25": (Decimal("8.25"), Decimal("8.25")),
    "8.5x11": (Decimal("8.5"), Decimal("11")),
    "a5": (Decimal("5.83"), Decimal("8.27")),
    "a4": (Decimal("8.27"), Decimal("11.69")),
}


@dataclass(frozen=True, slots=True)
class BookSpec:
    trim_width_in: Decimal
    trim_height_in: Decimal
    bleed: bool = False
    ink: str = "black"
    paper: str = "white"
    direction: str = "ltr"
    page_count: int | None = None
    profile: str = "kdp-paperback"

    @property
    def trim_label(self) -> str:
        return f"{self.trim_width_in.normalize()}x{self.trim_height_in.normalize()}"

    def as_dict(self) -> dict[str, object]:
        values = asdict(self)
        values["trim_width_in"] = float(self.trim_width_in)
        values["trim_height_in"] = float(self.trim_height_in)
        values["trim"] = self.trim_label
        return values


def parse_trim(value: str) -> tuple[Decimal, Decimal]:
    normalized = value.strip().lower().replace("in", "").replace("×", "x")
    if normalized in TRIM_PRESETS:
        return TRIM_PRESETS[normalized]
    parts = normalized.split("x")
    if len(parts) != 2:
        raise ValueError("trim must be a preset such as 6x9 or two dimensions such as 7.25x10")
    try:
        width, height = (Decimal(part.strip()) for part in parts)
    except InvalidOperation as exc:
        raise ValueError(f"invalid trim dimensions: {value}") from exc
    if width <= 0 or height <= 0:
        raise ValueError("trim dimensions must be positive")
    if width > Decimal("20") or height > Decimal("20"):
        raise ValueError("trim dimensions must be expressed in inches and be no larger than 20")
    return width, height


def expected_interior_points(spec: BookSpec) -> tuple[float, float]:
    width = spec.trim_width_in + (BLEED_INCH if spec.bleed else Decimal("0"))
    height = spec.trim_height_in + (BLEED_INCH * 2 if spec.bleed else Decimal("0"))
    return float(width * POINTS_PER_INCH), float(height * POINTS_PER_INCH)


def spine_width_in(spec: BookSpec, page_count: int) -> Decimal:
    if spec.ink == "premium-color":
        factor = Decimal("0.002347")
    elif spec.ink == "standard-color":
        factor = Decimal("0.002252")
    elif spec.paper == "cream":
        factor = Decimal("0.0025")
    elif spec.paper == "groundwood":
        factor = Decimal("0.00235")
    else:
        factor = Decimal("0.002252")
    return factor * page_count


def expected_cover_points(spec: BookSpec, page_count: int) -> tuple[float, float]:
    width = spec.trim_width_in * 2 + spine_width_in(spec, page_count) + BLEED_INCH * 2
    height = spec.trim_height_in + BLEED_INCH * 2
    return float(width * POINTS_PER_INCH), float(height * POINTS_PER_INCH)


def inside_margin_in(page_count: int) -> Decimal:
    if page_count <= 150:
        return Decimal("0.375")
    if page_count <= 300:
        return Decimal("0.5")
    if page_count <= 500:
        return Decimal("0.625")
    if page_count <= 700:
        return Decimal("0.75")
    return Decimal("0.875")


def outside_margin_in(bleed: bool) -> Decimal:
    return Decimal("0.375") if bleed else Decimal("0.25")


def supported_page_range(spec: BookSpec) -> tuple[int, int]:
    if spec.ink == "standard-color":
        return 72, 600
    if spec.ink == "black" and spec.paper == "cream":
        return 24, 776
    return 24, 828
