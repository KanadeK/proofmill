from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from proofmill import __version__

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NAME = "KanadeK"
EXPECTED_EMAIL = "121669563+KanadeK@users.noreply.github.com"


def _capture(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True, encoding="utf-8").strip()


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _asset_hashes(dist: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(dist.iterdir())
        if path.is_file() and path.name != "SHA256SUMS"
    }


def check(*, run_verify: bool) -> dict[str, object]:
    if run_verify:
        _run(["uv", "run", sys.executable, "scripts/verify.py"])
    status = _capture(["git", "status", "--porcelain=v1"])
    if status:
        raise RuntimeError(f"worktree is not clean:\n{status}")
    if _capture(["git", "config", "user.name"]) != EXPECTED_NAME:
        raise RuntimeError("unexpected local git user.name")
    if _capture(["git", "config", "user.email"]) != EXPECTED_EMAIL:
        raise RuntimeError("unexpected local git user.email")
    history = _capture(
        [
            "git",
            "log",
            "--format=%H%x09%an%x09%ae%x09%cn%x09%ce%x09%B%x00",
        ]
    )
    if not history:
        raise RuntimeError("release check requires at least one commit")
    commits = []
    for record in history.split("\x00"):
        if not record.strip():
            continue
        parts = record.strip().split("\t", 5)
        if len(parts) != 6:
            raise RuntimeError("could not parse git history")
        sha, author, author_email, committer, committer_email, body = parts
        if (author, author_email, committer, committer_email) != (
            EXPECTED_NAME,
            EXPECTED_EMAIL,
            EXPECTED_NAME,
            EXPECTED_EMAIL,
        ):
            raise RuntimeError(f"unexpected author or committer in {sha}")
        if re.search(r"(?im)^Co-authored-by:", body):
            raise RuntimeError(f"Co-authored-by trailer found in {sha}")
        commits.append(sha)

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f'version = "{__version__}"' not in pyproject:
        raise RuntimeError("pyproject version does not match package version")
    if f"## [{__version__}]" not in changelog:
        raise RuntimeError("changelog does not contain the package version")

    dist = ROOT / "dist"
    required = {
        f"proofmill-{__version__}-py3-none-any.whl",
        f"proofmill-{__version__}.tar.gz",
        f"proofmill-examples-{__version__}.zip",
    }
    hashes = _asset_hashes(dist)
    missing = required - set(hashes)
    if missing:
        raise RuntimeError(f"missing release assets: {sorted(missing)}")
    checksum_lines = (dist / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    recorded = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in checksum_lines}
    if recorded != hashes:
        raise RuntimeError("SHA256SUMS does not match release assets")
    result: dict[str, object] = {
        "ok": True,
        "version": __version__,
        "head": _capture(["git", "rev-parse", "HEAD"]),
        "branch": _capture(["git", "branch", "--show-current"]),
        "commit_count": len(commits),
        "author": f"{EXPECTED_NAME} <{EXPECTED_EMAIL}>",
        "assets": hashes,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args()
    check(run_verify=not args.skip_verify)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
