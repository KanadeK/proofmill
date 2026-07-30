# ProofMill

> Know whether a print PDF is structurally ready before the upload.

[简体中文](README.zh-CN.md) · [Live report](https://kanadek.github.io/proofmill/) ·
[Repair guide](docs/REPAIR_GUIDE.md) · [Rule sources](docs/RULES.md)

[![CI](https://github.com/KanadeK/proofmill/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/proofmill/actions/workflows/ci.yml)
[![Security](https://github.com/KanadeK/proofmill/actions/workflows/security.yml/badge.svg)](https://github.com/KanadeK/proofmill/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-176b4d.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-315f8c.svg)](pyproject.toml)

ProofMill is a local-first CLI for self-publishers, book designers, and small presses. It
opens the actual interior and cover PDFs, applies a versioned KDP paperback rule profile,
and produces deterministic console, JSON, and offline HTML reports with page-level evidence
and repair instructions.

It is not a form with a green button. The scanner parses page geometry, PDF resources,
placed-image dimensions, text coordinates, annotations, transparency state, and font
descriptors. The committed examples include both a passing book package and deliberately
broken PDFs that exercise independent failure paths.

## The two-minute path

Install the release wheel:

```bash
python -m pip install proofmill-0.1.0-py3-none-any.whl
```

Or run from a checkout:

```bash
uv sync
uv run proofmill audit --config examples/proofmill.json
```

Check one interior:

```bash
proofmill check book/interior.pdf \
  --kind interior \
  --trim 6x9 \
  --no-bleed \
  --json artifacts/report.json \
  --html artifacts/report.html
```

Check one cover after the interior page count is final:

```bash
proofmill check book/cover.pdf \
  --kind cover \
  --trim 6x9 \
  --pages 120 \
  --ink black \
  --paper white
```

Exit code `0` means no finding met the selected failure threshold, `1` means the audit
found a release-blocking issue, and `2` means the command or input could not be used.

## What it checks

| Surface | Real checks in v0.1.0 |
| --- | --- |
| File | PDF readability, encryption, 650 MB limit, embedded files, JavaScript |
| Interior | page count, exact trim/bleed dimensions, mixed sizes, rotations, likely spreads |
| Typography | referenced fonts actually used by text, embedding, subset status, 7 pt context |
| Margins | mirrored gutter/outside safe rectangles and word bounding boxes, without reporting manuscript text |
| Images | intrinsic pixels versus placed size for effective DPI, below-300 failures, above-600 notes |
| Print objects | annotations, AcroForm fields, transparency/soft masks, sub-0.75 pt vector strokes |
| Pagination | odd page-count rounding and runs of three or more blank pages |
| Cover | one-page wrap, paper/ink-specific spine math, bleed dimensions, outer text safety |
| Spine | no spine text at 79 pages or fewer, 0.0625 inch fold clearance above that |
| Evidence | SHA-256, structured findings, official source per rule, deterministic JSON/HTML |

Run `proofmill rules` to inspect every rule code and its official source snapshot. Run
`proofmill explain IMAGE_LOW_DPI` for one repair path.

## Project configuration

Create a starter file:

```bash
proofmill init
```

The paired audit prevents a common production mistake: sizing the cover from a stale
interior page count.

```json
{
  "$schema": "https://raw.githubusercontent.com/KanadeK/proofmill/main/src/proofmill/proofmill.schema.json",
  "profile": "kdp-paperback",
  "trim": "6x9",
  "bleed": false,
  "ink": "black",
  "paper": "white",
  "direction": "ltr",
  "interior": "book/interior.pdf",
  "cover": "book/cover.pdf",
  "page_count": null,
  "fail_on": "error"
}
```

If `page_count` is `null`, ProofMill uses the inspected interior count and applies the
platform's even-page rounding to cover math. Relative paths resolve from the configuration
file, not from the shell's current directory.

## Run it in GitHub Actions

Commit `proofmill.json` and the PDFs it references, then add:

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@v4
  - name: Preflight print PDFs
    uses: KanadeK/proofmill@v0.1.0
    with:
      config: proofmill.json
      output-dir: artifacts/proofmill
  - name: Keep the evidence
    if: always()
    uses: actions/upload-artifact@v4
    with:
      name: proofmill-report
      path: artifacts/proofmill/
```

The action fails the job with the same exit-code contract as the CLI. Its HTML and JSON
reports remain downloadable when the audit fails.

## Reports do not quote the manuscript

ProofMill performs all work on the local machine and makes no network requests. The JSON
and HTML report contain the file name, hash, geometry, counts, and compact evidence. When
text crosses a margin, the report stores a one-way 12-character fingerprint and bounding
box instead of the word itself. This makes a report useful in CI without turning it into a
second copy of an unpublished manuscript.

## Reproduce the proof

The repository includes generated PDFs because a scanner without inspectable examples is
hard to trust.

```bash
uv sync --extra dev
uv run python scripts/generate_examples.py

# Passing package
uv run proofmill audit \
  --config examples/proofmill.json \
  --output-dir artifacts/good

# Deliberately fails and explains each repair
uv run proofmill audit \
  --config examples/proofmill-bad.json \
  --output-dir artifacts/bad
```

The bad package currently demonstrates wrong page geometry, too few pages, text outside
the safe area, an unembedded font, low effective DPI, a thin line, transparency, a link
annotation, blank-page runs, a wrong cover wrap, and prohibited spine text.

## Acceptance command

For maintainers and release reviewers, one command rebuilds the evidence:

```bash
uv run python scripts/verify.py
```

It runs formatting, lint, strict type checking, tests with branch coverage, fixture
regeneration, passing/failing CLI acceptance, deterministic report comparison, wheel and
source build, clean-environment install smoke, secret scanning, docs generation, and
release-asset packaging.

Useful narrower commands:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=proofmill --cov-report=term-missing
uv run python scripts/package_release.py
```

## When a check fails

Start with the rule code in the console output:

```bash
proofmill explain PAGE_SIZE_MISMATCH
```

Then follow [the repair decision tree](docs/REPAIR_GUIDE.md). The short version is:

1. Fix the source layout rather than patching the exported PDF.
2. Export a fresh, unlocked, single-page PDF with fonts embedded.
3. Rerun ProofMill on the exact file you will upload.
4. If the same rule remains, inspect the JSON evidence page and bounding box.
5. If ProofMill is wrong, keep the PDF private and file an issue with the redacted report,
   tool version, authoring application, and minimal synthetic reproduction.

## Honest boundaries

ProofMill is an independent open-source preflight assistant. It is not affiliated with
Amazon and cannot guarantee acceptance, manufacturing quality, or legal font rights.
Platform rules change; the built-in profile states its snapshot date.

Version 0.1.0 deliberately does not:

- upload or auto-modify a manuscript;
- OCR text baked into images;
- certify PDF/X, ICC color management, ink coverage, overprint, or font licensing;
- reproduce proprietary platform review heuristics;
- replace the platform previewer or a physical proof.

Those limits are visible in reports and in the [architecture notes](docs/ARCHITECTURE.md),
not hidden behind a confidence score.

## Why this project

KDP's current guidance identifies bleed, dimensions, fonts, images, transparency, layers,
annotations, and pagination as common failure surfaces. Community threads continue to show
authors losing repeated upload cycles to opaque margin and font errors. Existing search
results are dominated by hosted or paid checkers. ProofMill makes the rules, evidence,
test fixtures, and release artifacts reviewable on GitHub.

The dated research trail and links are in [docs/RESEARCH.md](docs/RESEARCH.md).

## Contributing

New print profiles and checks need a primary source, a synthetic positive fixture, a
negative fixture, deterministic output, and a repair instruction. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). Amazon, Kindle Direct Publishing, KDP, IngramSpark, and other product names
belong to their respective owners.
