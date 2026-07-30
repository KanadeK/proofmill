from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        return {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}[self]


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    severity: Severity
    title: str
    message: str
    repair: str
    page: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    source_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "repair": self.repair,
        }
        if self.page is not None:
            result["page"] = self.page
        if self.evidence:
            result["evidence"] = self.evidence
        if self.source_url:
            result["source_url"] = self.source_url
        return result


@dataclass(frozen=True, slots=True)
class AuditReport:
    kind: str
    filename: str
    sha256: str
    size_bytes: int
    page_count: int
    spec: dict[str, Any]
    facts: dict[str, Any]
    issues: tuple[Issue, ...]

    @property
    def counts(self) -> dict[str, int]:
        return {
            severity.value: sum(issue.severity is severity for issue in self.issues)
            for severity in Severity
        }

    @property
    def status(self) -> str:
        if self.counts[Severity.ERROR.value]:
            return "fail"
        if self.counts[Severity.WARNING.value]:
            return "warn"
        return "pass"

    def fails_at(self, fail_on: Severity) -> bool:
        return any(issue.severity.rank >= fail_on.rank for issue in self.issues)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "filename": self.filename,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "page_count": self.page_count,
            "status": self.status,
            "counts": self.counts,
            "spec": self.spec,
            "facts": self.facts,
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class AuditBundle:
    reports: tuple[AuditReport, ...]
    profile: str = "kdp-paperback"
    schema_version: str = "1"
    tool_version: str = "0.1.0"

    @property
    def status(self) -> str:
        statuses = {report.status for report in self.reports}
        if "fail" in statuses:
            return "fail"
        if "warn" in statuses:
            return "warn"
        return "pass"

    @property
    def counts(self) -> dict[str, int]:
        return {
            severity.value: sum(report.counts[severity.value] for report in self.reports)
            for severity in Severity
        }

    def fails_at(self, fail_on: Severity) -> bool:
        return any(report.fails_at(fail_on) for report in self.reports)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": {"name": "proofmill", "version": self.tool_version},
            "profile": self.profile,
            "status": self.status,
            "counts": self.counts,
            "reports": [report.as_dict() for report in self.reports],
        }
