from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofmill.cli import main
from proofmill.config import DEFAULT_CONFIG, load_config, write_default_config


def test_init_and_load_config(tmp_path: Path) -> None:
    config_path = tmp_path / "proofmill.json"
    write_default_config(config_path)
    loaded = load_config(config_path)
    assert loaded.spec.trim_label == "6x9"
    assert loaded.interior == tmp_path / "book" / "interior.pdf"
    with pytest.raises(FileExistsError):
        write_default_config(config_path)
    write_default_config(config_path, force=True)


@pytest.mark.parametrize(
    "patch",
    [
        {"profile": "other"},
        {"trim": "bad"},
        {"ink": "infrared"},
        {"paper": "cardboard"},
        {"direction": "down"},
        {"bleed": "yes"},
        {"page_count": 0},
        {"fail_on": "never"},
        {"interior": None, "cover": None},
        {"interior": None, "cover": "cover.pdf", "page_count": None},
    ],
)
def test_config_rejects_invalid_values(tmp_path: Path, patch: dict[str, object]) -> None:
    payload = dict(DEFAULT_CONFIG)
    payload.update(patch)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_config_rejects_non_object_and_invalid_json(tmp_path: Path) -> None:
    non_object = tmp_path / "list.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="root"):
        load_config(non_object)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="line"):
        load_config(invalid)


def test_cli_check_good_and_bad(
    example_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good_json = tmp_path / "good.json"
    good_html = tmp_path / "good.html"
    good_exit = main(
        [
            "check",
            str(example_dir / "good-interior.pdf"),
            "--trim",
            "6x9",
            "--json",
            str(good_json),
            "--html",
            str(good_html),
        ]
    )
    assert good_exit == 0
    assert json.loads(good_json.read_text(encoding="utf-8"))["status"] == "pass"
    assert "<!doctype html>" in good_html.read_text(encoding="utf-8")
    assert "PASS" in capsys.readouterr().out

    bad_exit = main(["check", str(example_dir / "bad-interior.pdf"), "--trim", "6x9", "--quiet"])
    assert bad_exit == 1


def test_cli_cover_requires_pages(example_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "check",
            str(example_dir / "good-cover.pdf"),
            "--kind",
            "cover",
            "--trim",
            "6x9",
        ]
    )
    assert exit_code == 2
    assert "--pages" in capsys.readouterr().err


def test_cli_paired_audit_init_and_json_rules(
    example_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = {
        "profile": "kdp-paperback",
        "trim": "6x9",
        "bleed": False,
        "ink": "black",
        "paper": "white",
        "direction": "ltr",
        "interior": str(example_dir / "good-interior.pdf"),
        "cover": str(example_dir / "good-cover.pdf"),
        "page_count": 120,
        "fail_on": "error",
    }
    config_path = tmp_path / "paired.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "reports"
    assert (
        main(
            [
                "audit",
                "--config",
                str(config_path),
                "--output-dir",
                str(output),
                "--quiet",
            ]
        )
        == 0
    )
    assert json.loads((output / "report.json").read_text(encoding="utf-8"))["status"] == "pass"
    assert (output / "report.html").is_file()

    init_path = tmp_path / "starter.json"
    assert main(["init", str(init_path)]) == 0
    assert init_path.is_file()
    assert main(["init", str(init_path)]) == 2
    assert "exists" in capsys.readouterr().err.lower()
    assert main(["init", str(init_path), "--force"]) == 0

    capsys.readouterr()
    assert main(["rules", "--json"]) == 0
    rules = json.loads(capsys.readouterr().out)
    assert rules["profile"] == "kdp-paperback"
    assert len(rules["rules"]) >= 20


def test_cli_cover_success_and_bad_audit(
    example_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "check",
                str(example_dir / "good-cover.pdf"),
                "--kind",
                "cover",
                "--trim",
                "6x9",
                "--pages",
                "120",
                "--quiet",
            ]
        )
        == 0
    )
    bad_config = {
        "profile": "kdp-paperback",
        "trim": "6x9",
        "bleed": False,
        "ink": "black",
        "paper": "white",
        "interior": str(example_dir / "bad-interior.pdf"),
        "cover": None,
        "fail_on": "error",
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad_config), encoding="utf-8")
    assert main(["audit", "--config", str(path), "--output-dir", str(tmp_path / "bad")]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_cli_rules_explain_and_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rules"]) == 0
    assert "PAGE_SIZE_MISMATCH" in capsys.readouterr().out
    assert main(["explain", "image_low_dpi"]) == 0
    assert "300 effective DPI" in capsys.readouterr().out
    assert main(["explain", "not-a-rule"]) == 2
    assert "unknown ProofMill rule" in capsys.readouterr().err
    assert main(["check", "missing.pdf", "--trim", "6x9"]) == 2
    assert "not found" in capsys.readouterr().err
