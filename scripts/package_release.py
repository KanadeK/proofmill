from __future__ import annotations

import argparse
import base64
import csv
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
from collections.abc import Callable
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import cast

from proofmill import __version__
from proofmill.audit import audit_cover, audit_interior
from proofmill.models import AuditBundle
from proofmill.profiles import BookSpec
from proofmill.reports import write_html, write_json

ROOT = Path(__file__).resolve().parents[1]
generate_all = cast(
    Callable[[Path], None],
    import_module("scripts.generate_examples" if __package__ else "generate_examples").generate_all,
)
FIXED_ZIP_TIME = (2026, 7, 30, 0, 0, 0)
SOURCE_DATE_EPOCH = "1785369600"
TEXT_SUFFIXES = {
    ".cfg",
    ".json",
    ".md",
    ".py",
    ".txt",
}
TEXT_NAMES = {
    "LICENSE",
    "METADATA",
    "PKG-INFO",
    "RECORD",
    "WHEEL",
}


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


def _is_text_member(name: str) -> bool:
    path = Path(name)
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES


def _normalize_payload(name: str, data: bytes) -> bytes:
    if _is_text_member(name):
        return data.replace(b"\r\n", b"\n")
    return data


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    return info


def _write_zip(destination: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(_zip_info(name), data, compress_type=zipfile.ZIP_STORED)


def _zip_tree(source: Path, destination: Path) -> None:
    entries = {
        path.relative_to(source).as_posix(): _normalize_payload(
            path.relative_to(source).as_posix(), path.read_bytes()
        )
        for path in sorted(source.rglob("*"))
        if path.is_file()
    }
    _write_zip(destination, entries)


def _write_checksums(output: Path) -> None:
    lines = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.name}")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def _wheel_record(entries: dict[str, bytes], record_name: str) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, data in sorted(entries.items()):
        digest = (
            base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
        )
        writer.writerow((name, f"sha256={digest}", len(data)))
    writer.writerow((record_name, "", ""))
    return stream.getvalue().encode("utf-8")


def _normalize_wheel(output: Path) -> None:
    archives = sorted(output.glob("proofmill-*.whl"))
    if len(archives) != 1:
        raise RuntimeError(f"expected exactly one wheel, found {len(archives)}")
    source = archives[0]
    entries: dict[str, bytes] = {}
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            if not member.is_dir():
                entries[member.filename] = _normalize_payload(member.filename, archive.read(member))
    record_names = [name for name in entries if name.endswith(".dist-info/RECORD")]
    if len(record_names) != 1:
        raise RuntimeError(f"expected exactly one wheel RECORD, found {len(record_names)}")
    record_name = record_names[0]
    del entries[record_name]
    entries[record_name] = _wheel_record(entries, record_name)
    temporary = source.with_suffix(source.suffix + ".tmp")
    _write_zip(temporary, entries)
    temporary.replace(source)


def _normalize_sdist(output: Path) -> None:
    archives = sorted(output.glob("proofmill-*.tar.gz"))
    if len(archives) != 1:
        raise RuntimeError(f"expected exactly one source archive, found {len(archives)}")
    source = archives[0]
    members: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(source, "r:gz") as archive:
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            extracted = archive.extractfile(member) if member.isfile() else None
            data = extracted.read() if extracted is not None else None
            normalized = _normalize_payload(member.name, data) if data is not None else None
            if normalized is not None:
                member.size = len(normalized)
            members.append(
                (
                    member,
                    normalized,
                )
            )

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
                    if member.isdir():
                        member.mode = 0o755
                    elif member.isfile():
                        member.mode = 0o644
                    else:
                        raise RuntimeError(f"unsupported source archive member: {member.name}")
                    archive.addfile(member, io.BytesIO(data) if data is not None else None)
    temporary.replace(source)


def validate_archives(output: Path) -> None:
    epoch = int(SOURCE_DATE_EPOCH)
    zip_paths = [
        *sorted(output.glob("proofmill-*.whl")),
        *sorted(output.glob("proofmill-examples-*.zip")),
    ]
    if len(zip_paths) != 2:
        raise RuntimeError(f"expected wheel and examples ZIP, found {len(zip_paths)}")
    for path in zip_paths:
        with zipfile.ZipFile(path) as archive:
            zip_members = archive.infolist()
            if [member.filename for member in zip_members] != sorted(
                member.filename for member in zip_members
            ):
                raise RuntimeError(f"archive members are not sorted: {path.name}")
            for zip_member in zip_members:
                mode = (zip_member.external_attr >> 16) & 0o777
                if (
                    zip_member.date_time != FIXED_ZIP_TIME
                    or zip_member.create_system != 3
                    or zip_member.compress_type != zipfile.ZIP_STORED
                    or mode != 0o644
                ):
                    raise RuntimeError(
                        f"non-canonical ZIP metadata: {path.name}:{zip_member.filename}"
                    )
                data = archive.read(zip_member)
                if _is_text_member(zip_member.filename) and b"\r\n" in data:
                    raise RuntimeError(
                        f"non-canonical line endings: {path.name}:{zip_member.filename}"
                    )

    sdists = sorted(output.glob("proofmill-*.tar.gz"))
    if len(sdists) != 1:
        raise RuntimeError(f"expected exactly one source archive, found {len(sdists)}")
    source = sdists[0]
    header = source.read_bytes()[:10]
    if len(header) != 10 or int.from_bytes(header[4:8], "little") != epoch:
        raise RuntimeError(f"non-canonical gzip timestamp: {source.name}")
    with tarfile.open(source, "r:gz") as archive:
        tar_members = archive.getmembers()
        if [member.name for member in tar_members] != sorted(member.name for member in tar_members):
            raise RuntimeError(f"archive members are not sorted: {source.name}")
        for tar_member in tar_members:
            expected_mode = 0o755 if tar_member.isdir() else 0o644
            if (
                tar_member.mtime != epoch
                or tar_member.uid != 0
                or tar_member.gid != 0
                or tar_member.uname
                or tar_member.gname
                or tar_member.pax_headers
                or tar_member.mode != expected_mode
            ):
                raise RuntimeError(f"non-canonical tar metadata: {source.name}:{tar_member.name}")
            if tar_member.isfile() and _is_text_member(tar_member.name):
                extracted = archive.extractfile(tar_member)
                if extracted is None or b"\r\n" in extracted.read():
                    raise RuntimeError(
                        f"non-canonical line endings: {source.name}:{tar_member.name}"
                    )


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
    env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
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
    _normalize_wheel(output)
    _normalize_sdist(output)
    validate_archives(output)
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
