from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

from scripts.package_release import (
    FIXED_ZIP_TIME,
    SOURCE_DATE_EPOCH,
    _normalize_sdist,
    _normalize_wheel,
    _zip_tree,
)


def _write_source_archive(path: Path, *, newline: bytes, mode: int, mtime: int) -> None:
    with tarfile.open(path, "w:gz") as archive:
        directory = tarfile.TarInfo("proofmill-0.1.0/")
        directory.type = tarfile.DIRTYPE
        directory.mode = mode
        directory.mtime = mtime
        archive.addfile(directory)
        payload = newline.join((b"Metadata-Version: 2.4", b"Name: proofmill", b""))
        member = tarfile.TarInfo("proofmill-0.1.0/PKG-INFO")
        member.size = len(payload)
        member.mode = mode
        member.mtime = mtime
        archive.addfile(member, io.BytesIO(payload))


def _write_wheel(path: Path, *, newline: bytes, mode: int, create_system: int) -> None:
    entries = {
        "proofmill/__init__.py": b'__version__ = "0.1.0"' + newline,
        "proofmill-0.1.0.dist-info/METADATA": newline.join(
            (b"Metadata-Version: 2.4", b"Name: proofmill", b"")
        ),
        "proofmill-0.1.0.dist-info/RECORD": b"stale" + newline,
        "proofmill-0.1.0.dist-info/WHEEL": b"Wheel-Version: 1.0" + newline,
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in reversed(tuple(entries.items())):
            info = zipfile.ZipInfo(name, (2025, 1, 2, 3, 4, 6))
            info.create_system = create_system
            info.external_attr = mode << 16
            archive.writestr(info, data)


def test_zip_tree_has_platform_neutral_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.txt").write_bytes(b"one\r\ntwo\r\n")
    destination = tmp_path / "examples.zip"

    _zip_tree(source, destination)

    with zipfile.ZipFile(destination) as archive:
        member = archive.infolist()[0]
        assert member.create_system == 3
        assert member.date_time == FIXED_ZIP_TIME
        assert member.compress_type == zipfile.ZIP_STORED
        assert (member.external_attr >> 16) & 0o777 == 0o644
        assert archive.read(member) == b"one\ntwo\n"


def test_wheel_normalization_removes_host_differences(tmp_path: Path) -> None:
    windows = tmp_path / "windows"
    linux = tmp_path / "linux"
    windows.mkdir()
    linux.mkdir()
    windows_wheel = windows / "proofmill-0.1.0-py3-none-any.whl"
    linux_wheel = linux / "proofmill-0.1.0-py3-none-any.whl"
    _write_wheel(windows_wheel, newline=b"\r\n", mode=0o666, create_system=0)
    _write_wheel(linux_wheel, newline=b"\n", mode=0o644, create_system=3)

    _normalize_wheel(windows)
    _normalize_wheel(linux)

    assert windows_wheel.read_bytes() == linux_wheel.read_bytes()
    with zipfile.ZipFile(windows_wheel) as archive:
        record = archive.read("proofmill-0.1.0.dist-info/RECORD")
        assert b"sha256=" in record
        assert record.endswith(b"RECORD,,\n")


def test_sdist_normalization_removes_host_differences(tmp_path: Path) -> None:
    windows = tmp_path / "windows"
    linux = tmp_path / "linux"
    windows.mkdir()
    linux.mkdir()
    windows_sdist = windows / "proofmill-0.1.0.tar.gz"
    linux_sdist = linux / "proofmill-0.1.0.tar.gz"
    _write_source_archive(windows_sdist, newline=b"\r\n", mode=0o777, mtime=1)
    _write_source_archive(linux_sdist, newline=b"\n", mode=0o644, mtime=2)

    _normalize_sdist(windows)
    _normalize_sdist(linux)

    assert windows_sdist.read_bytes() == linux_sdist.read_bytes()
    with tarfile.open(windows_sdist, "r:gz") as archive:
        members = archive.getmembers()
        assert all(member.mtime == int(SOURCE_DATE_EPOCH) for member in members)
        assert members[0].mode == 0o755
        assert members[1].mode == 0o644
        extracted = archive.extractfile(members[1])
        assert extracted is not None
        assert extracted.read() == b"Metadata-Version: 2.4\nName: proofmill\n"
