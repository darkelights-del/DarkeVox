"""Dev-mode updater: repo detection and git outcome handling with a fake runner."""

from __future__ import annotations

from pathlib import Path

from darkevox.update import apply_update, check, repo_root


class _Proc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _runner(responses: dict[str, _Proc]):
    """Dispatch on the git subcommand ('fetch', 'rev-list', 'pull')."""

    def run(cmd: list[str], **kwargs: object) -> _Proc:
        sub = cmd[3]  # ["git", "-C", root, <subcommand>, ...]
        return responses[sub]

    return run


def test_repo_root_finds_the_checkout(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "darkevox" / "polish"
    nested.mkdir(parents=True)
    assert repo_root(nested / "llm.py") == tmp_path


def test_repo_root_none_outside_a_checkout(tmp_path: Path) -> None:
    nested = tmp_path / "just" / "files"
    nested.mkdir(parents=True)
    assert repo_root(nested / "x.py") is None


def test_check_up_to_date(tmp_path: Path) -> None:
    status = check(tmp_path, _runner({"fetch": _Proc(0), "rev-list": _Proc(0, "0\n")}))
    assert not status.available
    assert status.message == "DarkeVox is up to date."


def test_check_reports_commits_behind(tmp_path: Path) -> None:
    status = check(tmp_path, _runner({"fetch": _Proc(0), "rev-list": _Proc(0, "3\n")}))
    assert status.available
    assert status.message == "Update available: 3 new commits."


def test_check_offline(tmp_path: Path) -> None:
    status = check(tmp_path, _runner({"fetch": _Proc(1, stderr="could not resolve host")}))
    assert not status.available
    assert "offline" in status.message


def test_check_without_upstream(tmp_path: Path) -> None:
    responses = {"fetch": _Proc(0), "rev-list": _Proc(128, stderr="no upstream")}
    status = check(tmp_path, _runner(responses))
    assert not status.available
    assert "No upstream" in status.message


def test_apply_success(tmp_path: Path) -> None:
    status = apply_update(tmp_path, _runner({"pull": _Proc(0, "Fast-forward")}))
    assert status.applied
    assert "Restart DarkeVox" in status.message


def test_apply_failure_names_the_manual_fix(tmp_path: Path) -> None:
    status = apply_update(tmp_path, _runner({"pull": _Proc(1, stderr="local changes")}))
    assert not status.applied
    assert "git pull" in status.message
