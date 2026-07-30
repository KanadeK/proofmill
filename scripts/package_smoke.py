from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from proofmill import __version__

ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def smoke(dist: Path) -> None:
    wheels = sorted(dist.resolve().glob("proofmill-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one wheel, found {len(wheels)}")
    with tempfile.TemporaryDirectory(prefix="proofmill-smoke-") as temporary:
        environment = Path(temporary) / "venv"
        _run(["uv", "venv", "--python", "3.11", str(environment)])
        python = (
            environment / "Scripts" / "python.exe"
            if os.name == "nt"
            else environment / "bin" / "python"
        )
        _run(["uv", "pip", "install", "--python", str(python), str(wheels[0])])
        _run([str(python), "-m", "proofmill", "--version"])
        _run(
            [
                str(python),
                "-m",
                "proofmill",
                "check",
                str(ROOT / "examples" / "generated" / "good-interior.pdf"),
                "--trim",
                "6x9",
                "--quiet",
            ]
        )
    print(f"Wheel smoke test passed for ProofMill {__version__}.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    smoke(args.dist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
