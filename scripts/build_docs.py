from __future__ import annotations

import argparse
import html
import shutil
from decimal import Decimal
from pathlib import Path

import pdfplumber
from generate_examples import generate_all

from proofmill import __version__
from proofmill.audit import audit_cover, audit_interior
from proofmill.models import AuditBundle
from proofmill.profiles import PROFILE_SNAPSHOT, BookSpec
from proofmill.reports import write_html, write_json

ROOT = Path(__file__).resolve().parents[1]


def _reset_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ROOT or ROOT not in resolved.parents:
        raise ValueError(f"refusing to replace unsafe docs output: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _render_pdf_preview(source: Path, destination: Path) -> tuple[int, int]:
    with pdfplumber.open(source) as document:
        preview = document.pages[0].to_image(resolution=112, antialias=True)
        width, height = preview.original.size
        preview.save(str(destination), format="PNG", quantize=False)
    return width, height


def _landing_page(bundle: AuditBundle, preview_size: tuple[int, int]) -> str:
    featured_issues = [
        issue
        for report in bundle.reports
        for issue in report.issues
        if issue.severity.value == "error"
    ][:3]
    finding_items = "".join(
        f"""<li>
          <div><code>{html.escape(issue.code)}</code><strong>{html.escape(issue.title)}</strong></div>
          <span>{html.escape(issue.message)}</span>
        </li>"""
        for issue in featured_issues
    )
    preview_width, preview_height = preview_size
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Open-source, local-first print PDF preflight for KDP.">
  <title>ProofMill - know before the upload</title>
  <script>
    const requestedTheme = new URLSearchParams(window.location.search).get("theme");
    if (requestedTheme === "light" || requestedTheme === "dark") {{
      document.documentElement.dataset.theme = requestedTheme;
    }}
  </script>
  <style>
    :root {{ color-scheme:light dark; --ink:#17211c; --muted:#5c6961; --paper:#f4f2ec;
      --panel:#fbfaf6; --panel-strong:#e5eee7; --green:#176b4d; --green-ink:#f4f8f5;
      --red:#9a3333; --line:#c9d0c9; --shadow:#94a79a;
      font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
    :root[data-theme="light"] {{ color-scheme:light; }}
    :root[data-theme="dark"] {{ color-scheme:dark; --ink:#eef3ef; --muted:#b7c2bb; --paper:#121814;
      --panel:#19221d; --panel-strong:#23362b; --green:#63bd91; --green-ink:#102018;
      --red:#f08a83; --line:#3b4a40; --shadow:#0a0f0c; }}
    @media (prefers-color-scheme:dark) {{
      :root:not([data-theme="light"]) {{ --ink:#eef3ef; --muted:#b7c2bb; --paper:#121814;
        --panel:#19221d;
        --panel-strong:#23362b; --green:#63bd91; --green-ink:#102018; --red:#f08a83;
        --line:#3b4a40; --shadow:#0a0f0c; }}
    }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); }}
    a {{ color:inherit; }}
    .skip {{ position:absolute; left:18px; top:-80px; padding:10px 14px; color:var(--green-ink);
      background:var(--green); z-index:2; }}
    .skip:focus {{ top:12px; }}
    .shell {{ width:min(1160px,calc(100% - 40px)); margin:auto; }}
    nav {{ display:flex; justify-content:space-between; align-items:center; padding:24px 0;
      border-bottom:1px solid var(--line); }}
    .brand {{ display:flex; align-items:center; gap:11px; font-weight:900; letter-spacing:.08em;
      text-decoration:none; }}
    .mark {{ width:38px; height:38px; display:grid; place-items:center; color:var(--green-ink);
      background:var(--green); border-radius:8px; transform:rotate(-3deg); }}
    nav .links {{ display:flex; gap:22px; font-size:.86rem; font-weight:700; }}
    nav a:hover {{ color:var(--green); }}
    header {{ min-height:calc(100dvh - 88px); display:grid; grid-template-columns:1.08fr .92fr;
      gap:70px; align-items:center; padding:64px 0 78px; }}
    .kicker {{ color:var(--green); text-transform:uppercase; letter-spacing:.15em;
      font-size:.75rem; font-weight:900; }}
    h1 {{ margin:20px 0; max-width:690px; font:700 clamp(3.6rem,7vw,6.6rem)/.9 Georgia,serif;
      letter-spacing:-.06em; }}
    .lede {{ max-width:620px; color:var(--muted); font-size:1.15rem; line-height:1.65; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:30px; }}
    .button {{ display:inline-block; padding:13px 18px; border:1px solid var(--ink);
      border-radius:6px; text-decoration:none; font-weight:850; white-space:nowrap; }}
    .button:hover {{ color:var(--green-ink); background:var(--green); border-color:var(--green); }}
    .button:active {{ transform:translateY(1px); }}
    .button.primary {{ color:var(--green-ink); background:var(--green); border-color:var(--green); }}
    :focus-visible {{ outline:3px solid var(--green); outline-offset:4px; }}
    .cover-proof {{ margin:0; }}
    .cover-proof img {{ display:block; width:100%; height:auto; border:1px solid var(--line);
      border-radius:8px; background:var(--panel); box-shadow:18px 18px 0 var(--shadow); }}
    .cover-proof figcaption {{ margin-top:28px; color:var(--muted); font-size:.82rem; line-height:1.5; }}
    section {{ padding:88px 0; border-top:1px solid var(--line); }}
    .section-copy {{ max-width:720px; margin-bottom:42px; }}
    h2 {{ margin:0; font:700 clamp(2.5rem,5vw,4.8rem)/.96 Georgia,serif;
      letter-spacing:-.045em; }}
    .section-copy p {{ margin:18px 0 0; color:var(--muted); font-size:1.06rem; line-height:1.7; }}
    .result-grid {{ display:grid; grid-template-columns:.72fr 1.28fr; gap:18px; align-items:start; }}
    .score {{ padding:28px; border-radius:8px; color:var(--green-ink); background:var(--green); }}
    .score span,.score strong {{ display:block; }}
    .score strong {{ margin-top:16px; font:700 4.6rem/1 Georgia,serif; }}
    .score p {{ margin:18px 0 0; line-height:1.55; }}
    .actual-findings {{ margin:0; padding:0; list-style:none; border:1px solid var(--line);
      border-radius:8px; background:var(--panel); }}
    .actual-findings li {{ display:grid; grid-template-columns:.72fr 1fr; gap:24px;
      padding:22px; border-bottom:1px solid var(--line); }}
    .actual-findings li:last-child {{ border-bottom:0; }}
    .actual-findings div,.actual-findings strong {{ display:block; min-width:0; }}
    .actual-findings code {{ color:var(--red); font:800 .73rem/1.4 ui-monospace,monospace;
      overflow-wrap:anywhere; }}
    .actual-findings strong {{ margin-top:7px; }}
    .actual-findings span {{ color:var(--muted); line-height:1.5; }}
    .report-link {{ display:inline-block; margin-top:18px; color:var(--green); font-weight:800; }}
    .capabilities {{ display:grid; grid-template-columns:repeat(12,1fr); gap:14px; }}
    .capability {{ min-height:210px; padding:26px; border:1px solid var(--line);
      border-radius:8px; background:var(--panel); }}
    .capability:nth-child(1),.capability:nth-child(4) {{ grid-column:span 7; }}
    .capability:nth-child(2),.capability:nth-child(3) {{ grid-column:span 5; }}
    .capability:nth-child(5) {{ grid-column:span 4; }}
    .capability:nth-child(6) {{ grid-column:span 8; background:var(--panel-strong); }}
    .capability h3 {{ margin:0 0 38px; font-size:1.08rem; }}
    .capability p {{ max-width:48ch; margin:0; color:var(--muted); line-height:1.55; }}
    code {{ font-family:ui-monospace,monospace; }}
    .install-wrap {{ display:grid; grid-template-columns:1fr .65fr; gap:40px; align-items:end; }}
    .install-wrap .section-copy {{ margin-bottom:0; }}
    .install {{ margin:0; padding:22px; color:var(--green-ink); background:var(--green);
      border-radius:8px; overflow:auto; }}
    footer {{ display:flex; justify-content:space-between; gap:24px; padding:38px 0 70px;
      color:var(--muted); border-top:1px solid var(--line); font-size:.84rem; }}
    @media(max-width:820px) {{
      .shell {{ width:min(100% - 32px,680px); }}
      header,.result-grid,.install-wrap {{ grid-template-columns:1fr; }}
      header {{ min-height:0; gap:52px; padding:48px 0 72px; }}
      nav .links {{ display:none; }}
      h1 {{ font-size:clamp(2.8rem,12vw,4rem); }}
      .capabilities {{ grid-template-columns:1fr; }}
      .capability:nth-child(n) {{ grid-column:auto; }}
      .actual-findings li {{ grid-template-columns:1fr; gap:10px; }}
      section {{ padding:72px 0; }}
    }}
  </style>
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <div class="shell">
    <nav>
      <a class="brand" href="#"><span class="mark">PM</span> PROOFMILL</a>
      <div class="links"><a href="#checks">Checks</a><a href="demo-report.html">Live report</a>
        <a href="https://github.com/KanadeK/proofmill">GitHub</a></div>
    </nav>
    <main id="main">
    <header>
      <div>
        <div class="kicker">Open source print PDF preflight</div>
        <h1>Know before the upload.</h1>
        <p class="lede">Inspect geometry, fonts, images, hidden features, and cover math locally
          before upload.</p>
        <div class="actions"><a class="button primary" href="demo-report.html">Explore a real report</a>
          <a class="button" href="https://github.com/KanadeK/proofmill">View source</a></div>
      </div>
      <figure class="cover-proof">
        <img src="good-cover.png" alt="Rendered synthetic passing paperback cover fixture"
          width="{preview_width}" height="{preview_height}">
        <figcaption>A real rendered page from the repository's deterministic passing cover PDF.</figcaption>
      </figure>
    </header>
    <section id="checks">
      <div class="section-copy"><h2>Evidence, not a confidence score.</h2>
        <p>This result is generated from the committed failing PDFs. Every finding includes a
          stable code, measurement, repair path, and source while manuscript text stays private.</p>
      </div>
      <div class="result-grid">
        <article class="score">
          <span>Actual fixture result</span>
          <strong>{bundle.counts["error"]}</strong>
          <p>errors and {bundle.counts["warning"]} warnings across the synthetic interior and
            cover package.</p>
        </article>
        <div>
          <ul class="actual-findings">{finding_items}</ul>
          <a class="report-link" href="demo-report.html">Open every finding and its evidence</a>
        </div>
      </div>
    </section>
    <section>
      <div class="section-copy"><h2>The checks are concrete.</h2>
        <p>ProofMill reads PDF objects and measured geometry. Unsupported claims stay out of the
          result instead of being dressed up as a score.</p>
      </div>
      <div class="capabilities">
        <article class="capability"><h3>Interior geometry</h3>
          <p>Single pages, trim, asymmetric bleed, mirrored gutters, rotations, and spreads.</p></article>
        <article class="capability"><h3>Print content</h3>
          <p>Used font embedding, effective image DPI, safe text, transparency, and thin strokes.</p></article>
        <article class="capability"><h3>Cover math</h3>
          <p>Paper-specific spine width, one-page wrap, outside safety, and spine text clearance.</p></article>
        <article class="capability"><h3>Hidden features</h3>
          <p>Annotations, forms, JavaScript, attachments, bookmarks, encryption, and file size.</p></article>
        <article class="capability"><h3>CI receipts</h3>
          <p>Deterministic JSON and offline HTML with exact input SHA-256 values and exit codes.</p></article>
        <article class="capability"><h3>Reproducible proof data</h3>
          <p>Regenerate the committed passing and failing PDFs to exercise detection paths without
            sharing a manuscript.</p></article>
      </div>
    </section>
    <section>
      <div class="install-wrap">
        <div class="section-copy"><h2>One command to begin.</h2>
          <p>Download the wheel from the latest GitHub Release. Python 3.11 or newer is supported
            on Windows, macOS, and Linux.</p></div>
        <pre class="install"><code>python -m pip install proofmill-0.1.0-py3-none-any.whl
proofmill init
proofmill audit --config proofmill.json</code></pre>
      </div>
    </section>
    </main>
    <footer><span>MIT licensed. Rule snapshot {PROFILE_SNAPSHOT}.</span>
      <span>Independent project. Always review the platform preview and a physical proof.</span></footer>
  </div>
</body>
</html>
"""


def build(output: Path) -> None:
    _reset_output(output)
    examples = ROOT / "examples" / "generated"
    required = [
        examples / name
        for name in ("bad-interior.pdf", "bad-cover.pdf", "good-interior.pdf", "good-cover.pdf")
    ]
    if not all(path.is_file() for path in required):
        generate_all(examples)
    spec = BookSpec(
        Decimal("6"),
        Decimal("9"),
        ink="black",
        paper="white",
        page_count=40,
    )
    bundle = AuditBundle(
        (
            audit_interior(examples / "bad-interior.pdf", spec),
            audit_cover(examples / "bad-cover.pdf", spec),
        ),
        tool_version=__version__,
    )
    preview_size = _render_pdf_preview(examples / "good-cover.pdf", output / "good-cover.png")
    (output / "index.html").write_text(
        _landing_page(bundle, preview_size),
        encoding="utf-8",
        newline="\n",
    )
    write_html(bundle, output / "demo-report.html")
    write_json(bundle, output / "demo-report.json")
    (output / ".nojekyll").write_text("", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist-site")
    args = parser.parse_args()
    build(args.output)
    print(f"Built static docs in {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
