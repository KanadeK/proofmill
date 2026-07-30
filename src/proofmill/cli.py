from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from proofmill import __version__
from proofmill.audit import audit_cover, audit_interior
from proofmill.config import load_config, write_default_config
from proofmill.guidance import GUIDANCE, guidance_for
from proofmill.models import AuditBundle, Severity
from proofmill.profiles import (
    KDP_FIX_URL,
    KDP_FONT_URL,
    KDP_IMAGE_URL,
    KDP_SUBMISSION_URL,
    KDP_TRIM_URL,
    PROFILE_SNAPSHOT,
    BookSpec,
    parse_trim,
)
from proofmill.reports import console_report, write_html, write_json


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proofmill",
        description="Local-first print PDF preflight for self-publishers.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check one interior or cover PDF.")
    check.add_argument("pdf", type=Path)
    check.add_argument("--kind", choices=("interior", "cover"), default="interior")
    check.add_argument("--trim", required=True, help="Trim size in inches, for example 6x9.")
    check.add_argument("--bleed", action=argparse.BooleanOptionalAction, default=False)
    check.add_argument(
        "--ink",
        choices=("black", "standard-color", "premium-color"),
        default="black",
    )
    check.add_argument("--paper", choices=("white", "cream", "groundwood"), default="white")
    check.add_argument("--direction", choices=("ltr", "rtl"), default="ltr")
    check.add_argument("--pages", type=int, help="Final interior page count for a cover.")
    check.add_argument("--json", dest="json_path", type=Path)
    check.add_argument("--html", dest="html_path", type=Path)
    check.add_argument("--fail-on", choices=("error", "warning"), default="error")
    check.add_argument("--quiet", action="store_true")

    audit = subparsers.add_parser("audit", help="Check an interior and cover from JSON config.")
    audit.add_argument("--config", type=Path, default=Path("proofmill.json"))
    audit.add_argument("--output-dir", type=Path, default=Path("artifacts/proofmill"))
    audit.add_argument("--quiet", action="store_true")

    init = subparsers.add_parser("init", help="Write a documented starter configuration.")
    init.add_argument("path", nargs="?", type=Path, default=Path("proofmill.json"))
    init.add_argument("--force", action="store_true")

    rules = subparsers.add_parser("rules", help="List the auditable rule snapshot and sources.")
    rules.add_argument("--json", action="store_true")

    explain = subparsers.add_parser("explain", help="Explain one rule code and its repair.")
    explain.add_argument("code")
    return parser


def _spec_from_args(args: argparse.Namespace) -> BookSpec:
    width, height = parse_trim(args.trim)
    if args.kind == "cover" and (args.pages is None or args.pages <= 0):
        raise ValueError("--pages must be a positive integer for cover checks")
    return BookSpec(
        trim_width_in=width,
        trim_height_in=height,
        bleed=args.bleed,
        ink=args.ink,
        paper=args.paper,
        direction=args.direction,
        page_count=args.pages,
    )


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} PDF not found: {path}")


def _check_command(args: argparse.Namespace) -> int:
    _ensure_file(args.pdf, args.kind)
    spec = _spec_from_args(args)
    report = (
        audit_interior(args.pdf, spec) if args.kind == "interior" else audit_cover(args.pdf, spec)
    )
    bundle = AuditBundle((report,), tool_version=__version__)
    if args.json_path:
        write_json(bundle, args.json_path)
    if args.html_path:
        write_html(bundle, args.html_path)
    if not args.quiet:
        print(console_report(bundle), end="")
    return 1 if bundle.fails_at(Severity(args.fail_on)) else 0


def _audit_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    reports = []
    if config.interior is not None:
        _ensure_file(config.interior, "interior")
        reports.append(audit_interior(config.interior, config.spec))
    if config.cover is not None:
        _ensure_file(config.cover, "cover")
        page_count = config.spec.page_count
        if page_count is None and reports:
            page_count = reports[0].page_count
        if page_count is None:
            raise ValueError("page_count could not be derived for the cover")
        reports.append(audit_cover(config.cover, replace(config.spec, page_count=page_count)))
    bundle = AuditBundle(tuple(reports), profile=config.spec.profile, tool_version=__version__)
    output_dir = args.output_dir
    write_json(bundle, output_dir / "report.json")
    write_html(bundle, output_dir / "report.html")
    if not args.quiet:
        print(console_report(bundle), end="")
        print(f"Reports: {(output_dir / 'report.json').resolve()}")
        print(f"         {(output_dir / 'report.html').resolve()}")
    return 1 if bundle.fails_at(config.fail_on) else 0


def _rules_payload() -> dict[str, Any]:
    return {
        "profile": "kdp-paperback",
        "snapshot": PROFILE_SNAPSHOT,
        "sources": [
            KDP_SUBMISSION_URL,
            KDP_TRIM_URL,
            KDP_FONT_URL,
            KDP_IMAGE_URL,
            KDP_FIX_URL,
        ],
        "rules": [
            {
                "code": code,
                "title": guidance.title,
                "repair": guidance.repair,
                "source_url": guidance.source_url,
            }
            for code, guidance in sorted(GUIDANCE.items())
        ],
    }


def _rules_command(args: argparse.Namespace) -> int:
    payload = _rules_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ProofMill kdp-paperback rules (snapshot {PROFILE_SNAPSHOT})")
        for item in payload["rules"]:
            assert isinstance(item, dict)
            print(f"{item['code']:<30} {item['title']}")
        print("\nOfficial sources:")
        for source in payload["sources"]:
            print(f"- {source}")
    return 0


def _explain_command(args: argparse.Namespace) -> int:
    code = args.code.strip().upper()
    guidance = guidance_for(code)
    print(f"{code}: {guidance.title}")
    print(f"Repair: {guidance.repair}")
    print(f"Source: {guidance.source_url}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return _check_command(args)
        if args.command == "audit":
            return _audit_command(args)
        if args.command == "init":
            write_default_config(args.path, force=args.force)
            print(f"Wrote {args.path.resolve()}")
            return 0
        if args.command == "rules":
            return _rules_command(args)
        if args.command == "explain":
            return _explain_command(args)
    except (FileExistsError, FileNotFoundError, KeyError, OSError, ValueError) as exc:
        print(f"proofmill: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unknown command: {args.command}")
    return 2
