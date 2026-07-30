from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path

from generate_examples import generate_all

from proofmill import __version__
from proofmill.audit import audit_cover, audit_interior
from proofmill.models import AuditBundle
from proofmill.profiles import BookSpec
from proofmill.reports import write_html, write_json

ROOT = Path(__file__).resolve().parents[1]
FIXED_ZIP_TIME = (2026, 7, 30, 0, 0, 0)
SOURCE_DATE_EPOCH = "1785369600"


def _safe_reset(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ROOT:
        raise ValueError("refusing to replace the repository root")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def _zip_tree(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def _write_checksums(output: Path) -> None:
    lines = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.name}")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def _normalize_sdist(output: Path) -> None:
    archives = sorted(output.glob("proofmill-*.tar.gz"))
    if len(archives) != 1:
        raise RuntimeError(f"expected exactly one source archive, found {len(archives)}")
    source = archives[0]
    members: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(source, "r:gz") as archive:
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            extracted = archive.extractfile(member) if member.isfile() else None
            members.append((member, extracted.read() if extracted is not None else None))

    temporary = source.with_suffix(source.suffix + ".tmp")
    epoch = int(SOURCE_DATE_EPOCH)
    with temporary.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for member, data in members:
                    member.mtime = epoch
                    member.uid = 0
                    member.gid = 0
                    member.uname = ""
                    member.gname = ""
                    member.pax_headers = {}
                    archive.addfile(member, io.BytesIO(data) if data is not None else None)
    temporary.replace(source)


def package(output: Path) -> None:
    output = output.resolve()
    _safe_reset(output)
    examples = ROOT / "examples" / "generated"
    generate_all(examples)
    with tempfile.TemporaryDirectory(prefix="proofmill-release-") as temporary:
        stage = Path(temporary) / f"proofmill-examples-{__version__}"
        stage.mkdir(parents=True)
        generated_stage = stage / "generated"
        generated_stage.mkdir()
        for source in sorted(examples.glob("*.pdf")):
            shutil.copyfile(source, generated_stage / source.name)
        shutil.copyfile(ROOT / "examples" / "proofmill.json", stage / "proofmill.json")
        shutil.copyfile(ROOT / "examples" / "proofmill-bad.json", stage / "proofmill-bad.json")

        good_spec = BookSpec(Decimal("6"), Decimal("9"), page_count=120)
        bad_spec = BookSpec(Decimal("6"), Decimal("9"), page_count=40)
        good_bundle = AuditBundle(
            (
                audit_interior(generated_stage / "good-interior.pdf", good_spec),
                audit_cover(generated_stage / "good-cover.pdf", good_spec),
            ),
            tool_version=__version__,
        )
        bad_bundle = AuditBundle(
            (
                audit_interior(generated_stage / "bad-interior.pdf", bad_spec),
                audit_cover(generated_stage / "bad-cover.pdf", bad_spec),
            ),
            tool_version=__version__,
        )
        write_json(good_bundle, stage / "good-report.json")
        write_html(good_bundle, stage / "good-report.html")
        write_json(bad_bundle, stage / "bad-report.json")
        write_html(bad_bundle, stage / "bad-report.html")
        manifest = {
            "name": "proofmill examples",
            "version": __version__,
            "good_status": good_bundle.status,
            "bad_status": bad_bundle.status,
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        _zip_tree(stage, output / f"proofmill-examples-{__version__}.zip")

    env = dict(os.environ)
    env.setdefault("SOURCE_DATE_EPOCH", SOURCE_DATE_EPOCH)
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(output),
        ],
        env=env,
    )
    _normalize_sdist(output)
    _write_checksums(output)
    print(f"Packaged release assets in {output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    package(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
