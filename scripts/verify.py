from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from generate_examples import generate_all

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_NAMES = (
    "bad-cover.pdf",
    "bad-interior.pdf",
    "good-cover.pdf",
    "good-interior.pdf",
)


def _run(command: list[str], *, expected: int = 0) -> None:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != expected:
        raise RuntimeError(
            f"command exited {result.returncode}, expected {expected}: {' '.join(command)}"
        )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_examples() -> None:
    with tempfile.TemporaryDirectory(prefix="proofmill-fixtures-") as temporary:
        generated = Path(temporary)
        generate_all(generated)
        for name in EXAMPLE_NAMES:
            committed = ROOT / "examples" / "generated" / name
            if not committed.is_file():
                raise FileNotFoundError(f"committed example is missing: {committed}")
            if _hash(generated / name) != _hash(committed):
                raise RuntimeError(f"committed example is stale or nondeterministic: {name}")
    print("Committed PDF fixtures are deterministic.")


def main() -> int:
    python = sys.executable
    _run(["uv", "run", "ruff", "format", "--check", "."])
    _run(["uv", "run", "ruff", "check", "."])
    _run(["uv", "run", "mypy"])
    _run(
        [
            "uv",
            "run",
            "pytest",
            "--basetemp=tmp/verify-pytest",
            "-o",
            "cache_dir=tmp/verify-pytest-cache",
            "--cov=proofmill",
            "--cov-report=term-missing",
            "--cov-report=xml",
        ]
    )
    _verify_examples()
    _run(
        [
            "uv",
            "run",
            "proofmill",
            "audit",
            "--config",
            "examples/proofmill.json",
            "--output-dir",
            "artifacts/good",
            "--quiet",
        ]
    )
    _run(
        [
            "uv",
            "run",
            "proofmill",
            "audit",
            "--config",
            "examples/proofmill-bad.json",
            "--output-dir",
            "artifacts/bad",
            "--quiet",
        ],
        expected=1,
    )
    _run(["uv", "run", python, "scripts/build_docs.py"])
    _run(["uv", "run", python, "scripts/secret_scan.py"])
    _run(
        [
            "uv",
            "run",
            python,
            "scripts/determinism_check.py",
            "--copy-to",
            "dist",
        ]
    )
    _run(["uv", "run", python, "scripts/package_smoke.py", "--dist", "dist"])
    _run(["git", "diff", "--check"])
    if os.environ.get("CI"):
        _run(["git", "status", "--short"])
    print("ProofMill verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
