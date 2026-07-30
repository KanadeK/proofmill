from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from proofmill.models import Severity
from proofmill.profiles import BookSpec, parse_trim


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    source: Path
    interior: Path | None
    cover: Path | None
    spec: BookSpec
    fail_on: Severity


DEFAULT_CONFIG: dict[str, Any] = {
    "$schema": "https://raw.githubusercontent.com/KanadeK/proofmill/main/src/proofmill/proofmill.schema.json",
    "profile": "kdp-paperback",
    "trim": "6x9",
    "bleed": False,
    "ink": "black",
    "paper": "white",
    "direction": "ltr",
    "interior": "book/interior.pdf",
    "cover": "book/cover.pdf",
    "page_count": None,
    "fail_on": "error",
}


def write_default_config(path: Path, *, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if force else "x"
    with path.open(mode, encoding="utf-8", newline="\n") as stream:
        json.dump(DEFAULT_CONFIG, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def _choice(value: Any, name: str, choices: set[str]) -> str:
    if not isinstance(value, str) or value not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {allowed}")
    return value


def _optional_path(value: Any, name: str, base: Path) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty path or null")
    candidate = Path(value)
    return candidate if candidate.is_absolute() else (base / candidate)


def load_config(path: Path) -> ProjectConfig:
    source = path.resolve()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in {source.name} at line {exc.lineno}, column {exc.colno}"
        ) from exc
    if not isinstance(raw, dict):
        raise ValueError("configuration root must be a JSON object")
    profile = raw.get("profile", "kdp-paperback")
    if profile != "kdp-paperback":
        raise ValueError("the 0.1 release supports only the kdp-paperback profile")
    trim_width, trim_height = parse_trim(str(raw.get("trim", "6x9")))
    ink = _choice(raw.get("ink", "black"), "ink", {"black", "standard-color", "premium-color"})
    paper = _choice(raw.get("paper", "white"), "paper", {"white", "cream", "groundwood"})
    direction = _choice(raw.get("direction", "ltr"), "direction", {"ltr", "rtl"})
    bleed = raw.get("bleed", False)
    if not isinstance(bleed, bool):
        raise ValueError("bleed must be true or false")
    page_count = raw.get("page_count")
    if page_count is not None and (not isinstance(page_count, int) or page_count <= 0):
        raise ValueError("page_count must be a positive integer or null")
    fail_on = Severity(_choice(raw.get("fail_on", "error"), "fail_on", {"error", "warning"}))
    base = source.parent
    interior = _optional_path(raw.get("interior"), "interior", base)
    cover = _optional_path(raw.get("cover"), "cover", base)
    if interior is None and cover is None:
        raise ValueError("configure at least one of interior or cover")
    if cover is not None and interior is None and page_count is None:
        raise ValueError("page_count is required when checking a cover without an interior")
    return ProjectConfig(
        source=source,
        interior=interior,
        cover=cover,
        spec=BookSpec(
            trim_width_in=trim_width,
            trim_height_in=trim_height,
            bleed=bleed,
            ink=ink,
            paper=paper,
            direction=direction,
            page_count=page_count,
            profile=profile,
        ),
        fail_on=fail_on,
    )
