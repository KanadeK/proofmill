# Contributing

ProofMill welcomes reproducible rule fixes and new print profiles.

## Development

```bash
uv sync --extra dev
uv run python scripts/verify.py
```

## Rule contribution contract

Every new blocking rule must include:

1. a dated primary platform or standards source;
2. a stable rule code and human repair instruction;
3. a positive synthetic PDF that does not trigger it;
4. a negative synthetic PDF that does;
5. a test that asserts both outcomes;
6. deterministic JSON/HTML evidence that does not quote manuscript text.

Do not add guessed acceptance thresholds or scrape proprietary previewer output.

## Pull requests

Keep changes focused, explain user impact, and list the exact verification commands. By
participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

