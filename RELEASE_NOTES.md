# ProofMill 0.1.0

The first public release turns print-PDF rejection checks into a local, reproducible gate.

## Highlights

- Audits KDP paperback interiors and one-page cover wraps.
- Checks real PDF geometry, font embedding, safe text, effective image DPI, annotations,
  forms, scripts, attachments, transparency, thin strokes, blank runs, and spine math.
- Produces deterministic JSON and self-contained HTML without quoting manuscript text.
- Includes a passing book package and a deliberately broken package with expected findings.
- Runs as a Python CLI or a reusable GitHub composite action.
- Ships with English and Simplified Chinese documentation and an evidence-linked repair guide.

## Assets

- `proofmill-0.1.0-py3-none-any.whl` - universal Python wheel
- `proofmill-0.1.0.tar.gz` - source distribution
- `proofmill-examples-0.1.0.zip` - passing/failing PDFs, configs, and reports
- `SHA256SUMS` - hashes for every release asset

ProofMill is independent of Amazon and does not guarantee platform acceptance. Review the
platform preview and a physical proof before publication.

