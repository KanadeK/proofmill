from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from proofmill.models import AuditBundle


def bundle_json(bundle: AuditBundle) -> str:
    return json.dumps(bundle.as_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(bundle: AuditBundle, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(bundle_json(bundle), encoding="utf-8", newline="\n")


def _json_pre(value: dict[str, Any]) -> str:
    return html.escape(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def bundle_html(bundle: AuditBundle) -> str:
    report_sections: list[str] = []
    for report in bundle.reports:
        issue_cards: list[str] = []
        for issue in report.issues:
            location = f"<span>Page {issue.page}</span>" if issue.page else ""
            source = (
                f'<a href="{html.escape(issue.source_url)}" rel="noreferrer">Official source</a>'
                if issue.source_url
                else ""
            )
            evidence = (
                f"<details><summary>Evidence</summary><pre>{_json_pre(issue.evidence)}</pre></details>"
                if issue.evidence
                else ""
            )
            issue_cards.append(
                f"""
                <article class="issue {issue.severity.value}">
                  <div class="issue-head">
                    <span class="severity">{issue.severity.value}</span>
                    <code>{html.escape(issue.code)}</code>
                    {location}
                  </div>
                  <h3>{html.escape(issue.title)}</h3>
                  <p>{html.escape(issue.message)}</p>
                  <div class="repair"><strong>Repair</strong>{html.escape(issue.repair)}</div>
                  <div class="issue-links">{source}</div>
                  {evidence}
                </article>
                """
            )
        if not issue_cards:
            issue_cards.append(
                '<article class="empty">No findings at the selected failure threshold.</article>'
            )
        facts = "".join(
            f"<div><dt>{html.escape(str(key).replace('_', ' '))}</dt>"
            f"<dd>{html.escape(_format_fact(value))}</dd></div>"
            for key, value in report.facts.items()
        )
        report_sections.append(
            f"""
            <section class="document">
              <div class="document-title">
                <div>
                  <p class="eyebrow">{html.escape(report.kind)} PDF</p>
                  <h2>{html.escape(report.filename)}</h2>
                  <p class="hash">SHA-256 {html.escape(report.sha256)}</p>
                </div>
                <span class="status {report.status}">{report.status}</span>
              </div>
              <div class="metrics">
                <div><strong>{report.page_count}</strong><span>pages</span></div>
                <div><strong>{report.counts["error"]}</strong><span>errors</span></div>
                <div><strong>{report.counts["warning"]}</strong><span>warnings</span></div>
                <div><strong>{report.counts["info"]}</strong><span>notes</span></div>
              </div>
              <details class="facts">
                <summary>Document facts</summary>
                <dl>{facts}</dl>
              </details>
              <div class="issues">{"".join(issue_cards)}</div>
            </section>
            """
        )

    return (
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ProofMill preflight report</title>
  <style>
    :root { color-scheme: light dark; --ink:#17201c; --muted:#68736c; --paper:#f5f0e7;
      --panel:#fffdf8; --line:#d8d1c4; --green:#176b4d; --amber:#9a5b00; --red:#a33131;
      --blue:#315f8c; --metric:#faf7f0; --issue:#fffdf8; --pre:#f2efe8; --wash:#dfeadf;
      --mark-ink:#f4f8f5;
      font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }
    @media (prefers-color-scheme:dark) {
      :root { --ink:#edf2ee; --muted:#b3beb7; --paper:#111713; --panel:#19211c;
        --line:#3c4941; --green:#65bd92; --amber:#e4aa54; --red:#ef8982; --blue:#87acd0;
        --metric:#202b24; --issue:#202923; --pre:#101612; --wash:#26352c;
        --mark-ink:#102018; }
    }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:
      radial-gradient(circle at 15% 0%, var(--wash) 0, transparent 28rem), var(--paper); }
    :focus-visible { outline:3px solid var(--green); outline-offset:4px; }
    main { width:min(1120px, calc(100% - 32px)); margin:0 auto; padding:64px 0 96px; }
    .hero { display:grid; grid-template-columns:1fr auto; gap:32px; align-items:end;
      padding-bottom:32px; border-bottom:1px solid var(--line); }
    .brand { display:flex; align-items:center; gap:12px; font-weight:800; letter-spacing:.08em; }
    .mark { width:38px; height:38px; display:grid; place-items:center; color:var(--mark-ink);
      background:var(--green); border-radius:10px; transform:rotate(-3deg); }
    h1 { max-width:760px; margin:34px 0 12px; font-family:Georgia,serif;
      font-size:clamp(2.8rem,7vw,5.8rem); line-height:.92; letter-spacing:-.055em; }
    .lede { max-width:720px; margin:0; color:var(--muted); font-size:1.1rem; line-height:1.65; }
    .overall { min-width:180px; padding:22px; border:1px solid var(--line); background:var(--panel);
      box-shadow:8px 8px 0 #c7d5c6; }
    .overall span { display:block; color:var(--muted); font-size:.75rem; text-transform:uppercase;
      letter-spacing:.12em; }
    .overall strong { display:block; margin-top:5px; font-size:2.2rem; text-transform:uppercase; }
    .document { margin-top:48px; padding:28px; border:1px solid var(--line);
      background:var(--panel);
      box-shadow:0 18px 50px rgba(56,49,39,.08); }
    .document-title { display:flex; justify-content:space-between; gap:24px; align-items:start; }
    .eyebrow { margin:0 0 8px; color:var(--green); text-transform:uppercase; letter-spacing:.14em;
      font-size:.72rem; font-weight:800; }
    h2 { margin:0; font-size:1.9rem; overflow-wrap:anywhere; }
    .hash { max-width:680px; margin:10px 0 0; color:var(--muted);
      font:12px/1.5 ui-monospace,monospace;
      overflow-wrap:anywhere; }
    .status { padding:8px 12px; border:1px solid currentColor; text-transform:uppercase;
      letter-spacing:.1em; font-size:.72rem; font-weight:900; }
    .status.pass { color:var(--green); }.status.warn { color:var(--amber); }
    .status.fail { color:var(--red); }
    .metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:1px; margin:26px 0;
      background:var(--line); border:1px solid var(--line); }
    .metrics div { padding:18px; background:var(--metric); }
    .metrics strong,.metrics span { display:block; }
    .metrics strong { font:700 1.7rem/1 Georgia,serif; }
    .metrics span { margin-top:6px; color:var(--muted); font-size:.78rem; }
    .facts { margin-bottom:28px; border-top:1px solid var(--line);
      border-bottom:1px solid var(--line); }
    summary { cursor:pointer; padding:14px 0; font-weight:750; }
    .facts dl { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:0 0 18px; }
    .facts dl div { min-width:0; }
    dt { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }
    dd { margin:5px 0 0; overflow-wrap:anywhere; }
    .issues { display:grid; gap:14px; }
    .issue { padding:20px 20px 20px 24px; border:1px solid var(--line); border-left-width:5px;
      background:var(--issue); }
    .issue.error { border-left-color:var(--red); }.issue.warning { border-left-color:var(--amber); }
    .issue.info { border-left-color:var(--blue); }
    .issue-head { display:flex; gap:9px; align-items:center; color:var(--muted); font-size:.75rem; }
    .severity { padding:3px 7px; color:white; background:var(--blue); text-transform:uppercase;
      letter-spacing:.08em; font-size:.65rem; font-weight:850; }
    .error .severity { background:var(--red); }.warning .severity { background:var(--amber); }
    .issue h3 { margin:14px 0 6px; font-size:1.08rem; }
    .issue p { margin:0; line-height:1.55; }
    .repair { display:grid; grid-template-columns:64px 1fr; gap:8px; margin-top:13px;
      color:var(--muted);
      line-height:1.5; }
    .issue-links { margin-top:10px; }.issue a { color:var(--green); font-weight:700; }
    pre { padding:14px; overflow:auto; background:var(--pre); color:var(--ink); font-size:.74rem; }
    .empty { padding:24px; border:1px dashed var(--line); color:var(--green); }
    footer { margin-top:36px; color:var(--muted); font-size:.8rem; line-height:1.6; }
    @media (max-width:700px) {
      .hero { grid-template-columns:1fr; }.overall { min-width:0; }
      .metrics { grid-template-columns:repeat(2,1fr); }.facts dl { grid-template-columns:1fr; }
      .document { padding:20px; }.document-title { display:grid; }
      .document-title .status { justify-self:start; }.repair { grid-template-columns:1fr; }
    }
    @media print {
      body { background:white; }.hero { break-after:page; }
      .document { box-shadow:none; break-inside:avoid; }
    }
  </style>
</head>
<body>
<main>
  <header class="hero">
    <div>
      <div class="brand"><span class="mark">PM</span> PROOFMILL</div>
      <h1>Know before the upload.</h1>
      <p class="lede">A deterministic, local-first print PDF preflight. No manuscript text is
      included in this report; boundary evidence uses one-way fingerprints.</p>
    </div>
    <div class="overall"><span>Overall result</span><strong>"""
        + html.escape(bundle.status)
        + """</strong></div>
  </header>
  """
        + "".join(report_sections)
        + """
  <footer>
    Profile: """
        + html.escape(bundle.profile)
        + " | Schema "
        + html.escape(bundle.schema_version)
        + " | ProofMill "
        + html.escape(bundle.tool_version)
        + """. ProofMill is an independent preflight assistant, not an Amazon service or a
    guarantee of platform acceptance. Always review the platform preview and a physical proof.
  </footer>
</main>
</body>
</html>
"""
    )


def _format_fact(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)


def write_html(bundle: AuditBundle, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(bundle_html(bundle), encoding="utf-8", newline="\n")


def console_report(bundle: AuditBundle) -> str:
    lines = [
        f"ProofMill {bundle.tool_version} | {bundle.profile} | {bundle.status.upper()}",
        (
            f"{bundle.counts['error']} error(s), {bundle.counts['warning']} warning(s), "
            f"{bundle.counts['info']} note(s)"
        ),
    ]
    for report in bundle.reports:
        lines.append("")
        lines.append(
            f"{report.kind.upper()}  {report.filename}  "
            f"{report.page_count} page(s)  {report.status.upper()}"
        )
        lines.append(f"SHA-256  {report.sha256}")
        for issue in report.issues:
            location = f" page {issue.page}" if issue.page else ""
            lines.append(
                f"[{issue.severity.value.upper():7}] {issue.code}{location}: {issue.message}"
            )
            lines.append(f"          repair: {issue.repair}")
    return "\n".join(lines) + "\n"
