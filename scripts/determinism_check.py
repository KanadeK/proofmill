from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path

from package_release import ROOT, package


def _hashes(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.iterdir())
        if item.is_file()
    }


def check(copy_to: Path | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="proofmill-determinism-") as temporary:
        base = Path(temporary)
        first = base / "first"
        second = base / "second"
        package(first)
        package(second)
        first_hashes = _hashes(first)
        second_hashes = _hashes(second)
        if first_hashes != second_hashes:
            names = sorted(set(first_hashes) | set(second_hashes))
            differences = [
                name for name in names if first_hashes.get(name) != second_hashes.get(name)
            ]
            raise RuntimeError(f"nondeterministic release assets: {differences}")
        if copy_to is not None:
            resolved = copy_to.resolve()
            if resolved == ROOT:
                raise ValueError("refusing to replace the repository root")
            if resolved.exists():
                shutil.rmtree(resolved)
            shutil.copytree(first, resolved)
    print("Determinism check passed for all release assets.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--copy-to", type=Path)
    args = parser.parse_args()
    check(args.copy_to)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
