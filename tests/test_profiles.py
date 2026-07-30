from __future__ import annotations

from decimal import Decimal

import pytest

from proofmill.profiles import (
    BookSpec,
    expected_cover_points,
    expected_interior_points,
    inside_margin_in,
    parse_trim,
    spine_width_in,
    supported_page_range,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("6x9", (Decimal("6"), Decimal("9"))),
        ("A5", (Decimal("5.83"), Decimal("8.27"))),
        ("7.25×10", (Decimal("7.25"), Decimal("10"))),
        ("6in x 9in", (Decimal("6"), Decimal("9"))),
    ],
)
def test_parse_trim(value: str, expected: tuple[Decimal, Decimal]) -> None:
    assert parse_trim(value) == expected


@pytest.mark.parametrize("value", ["6", "axb", "0x9", "25x9", "-1x9"])
def test_parse_trim_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_trim(value)


def test_expected_interior_dimensions_include_asymmetric_bleed() -> None:
    spec = BookSpec(Decimal("6"), Decimal("9"), bleed=True)
    assert expected_interior_points(spec) == pytest.approx((441, 666))


def test_cover_math_and_spine_profiles() -> None:
    white = BookSpec(Decimal("6"), Decimal("9"), page_count=120)
    cream = BookSpec(Decimal("6"), Decimal("9"), paper="cream", page_count=120)
    color = BookSpec(Decimal("6"), Decimal("9"), ink="premium-color", page_count=120)
    assert spine_width_in(white, 120) == Decimal("0.270240")
    assert spine_width_in(cream, 120) == Decimal("0.3000")
    assert spine_width_in(color, 120) == Decimal("0.281640")
    assert expected_cover_points(white, 120) == pytest.approx((901.45728, 666))


@pytest.mark.parametrize(
    ("pages", "margin"),
    [(24, "0.375"), (151, "0.5"), (301, "0.625"), (501, "0.75"), (701, "0.875")],
)
def test_inside_margin_tiers(pages: int, margin: str) -> None:
    assert inside_margin_in(pages) == Decimal(margin)


def test_supported_page_ranges() -> None:
    base = BookSpec(Decimal("6"), Decimal("9"))
    assert supported_page_range(base) == (24, 828)
    assert supported_page_range(BookSpec(Decimal("6"), Decimal("9"), ink="standard-color")) == (
        72,
        600,
    )
    assert supported_page_range(BookSpec(Decimal("6"), Decimal("9"), paper="cream")) == (24, 776)
