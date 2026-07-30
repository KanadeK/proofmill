from __future__ import annotations

import json

from proofmill.models import AuditBundle, AuditReport, Issue, Severity
from proofmill.reports import bundle_html, bundle_json, console_report


def _report(*issues: Issue) -> AuditReport:
    return AuditReport(
        kind="interior",
        filename="sample.pdf",
        sha256="a" * 64,
        size_bytes=123,
        page_count=24,
        spec={"trim": "6x9"},
        facts={"encrypted": False},
        issues=issues,
    )


def test_report_status_and_thresholds() -> None:
    info = Issue("I", Severity.INFO, "Info", "message", "repair")
    warning = Issue("W", Severity.WARNING, "Warn", "message", "repair")
    error = Issue("E", Severity.ERROR, "Error", "message", "repair")
    assert _report().status == "pass"
    assert _report(info).status == "pass"
    assert _report(warning).status == "warn"
    assert _report(error).status == "fail"
    assert _report(warning).fails_at(Severity.WARNING)
    assert not _report(warning).fails_at(Severity.ERROR)


def test_bundle_serialization_is_stable_and_html_escapes() -> None:
    issue = Issue(
        "TEST",
        Severity.ERROR,
        "<unsafe>",
        "message & detail",
        "repair",
        page=2,
        evidence={"value": "<script>"},
        source_url="https://example.com/?a=1&b=2",
    )
    bundle = AuditBundle((_report(issue),))
    first = bundle_json(bundle)
    assert first == bundle_json(bundle)
    payload = json.loads(first)
    assert payload["status"] == "fail"
    rendered = bundle_html(bundle)
    assert "&lt;unsafe&gt;" in rendered
    assert "<script>" not in rendered
    assert "text_fingerprint" not in rendered
    assert "ProofMill preflight report" in rendered
    console = console_report(bundle)
    assert "[ERROR  ] TEST page 2" in console


def test_issue_omits_empty_optional_fields() -> None:
    payload = Issue("X", Severity.INFO, "x", "m", "r").as_dict()
    assert "page" not in payload
    assert "evidence" not in payload
    assert "source_url" not in payload
