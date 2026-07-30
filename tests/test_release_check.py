from __future__ import annotations

from subprocess import CompletedProcess

from scripts import release_check


def test_missing_runner_git_identity_is_allowed(monkeypatch) -> None:
    def missing_config(*args, **kwargs) -> CompletedProcess[str]:
        return CompletedProcess(args=args[0], returncode=1, stdout="", stderr="")

    monkeypatch.setattr(release_check.subprocess, "run", missing_config)

    assert release_check._optional_git_config("user.name") is None


def test_present_runner_git_identity_is_read(monkeypatch) -> None:
    def configured(*args, **kwargs) -> CompletedProcess[str]:
        return CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="KanadeK\n",
            stderr="",
        )

    monkeypatch.setattr(release_check.subprocess, "run", configured)

    assert release_check._optional_git_config("user.name") == "KanadeK"
