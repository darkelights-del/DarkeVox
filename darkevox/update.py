"""Dev-mode self-update: fast-forward git pull when running from a clone.

Until the phase 7 installer exists, an "update" is new commits on the
upstream branch. Everything here shells out to git with timeouts and runs
on a background thread in app.py; the dictation hot path never waits on
the network. No Qt imports.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


@dataclass
class UpdateStatus:
    available: bool
    applied: bool = False
    message: str = ""  # user-visible, shown as a tray notification


def repo_root(start: Path | None = None) -> Path | None:
    """The enclosing git checkout, or None when DarkeVox wasn't run from one."""
    path = (start or Path(__file__).resolve()).parent
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _git(root: Path, *args: str, runner: Runner = subprocess.run) -> tuple[int, str]:
    try:
        proc = runner(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("git %s failed: %s", args, exc)
        return 1, str(exc)
    return proc.returncode, f"{proc.stdout}{proc.stderr}".strip()


def check(root: Path, runner: Runner = subprocess.run) -> UpdateStatus:
    code, out = _git(root, "fetch", "--quiet", runner=runner)
    if code != 0:
        log.warning("update fetch failed: %s", out)
        return UpdateStatus(False, message="Update check failed. Are you offline?")
    code, out = _git(root, "rev-list", "--count", "HEAD..@{u}", runner=runner)
    if code != 0:
        log.warning("update rev-list failed: %s", out)
        return UpdateStatus(False, message="Update check failed. No upstream branch.")
    try:
        behind = int(out.split()[0]) if out else 0
    except ValueError:
        behind = 0
    if behind == 0:
        return UpdateStatus(False, message="DarkeVox is up to date.")
    plural = "s" if behind != 1 else ""
    return UpdateStatus(True, message=f"Update available: {behind} new commit{plural}.")


def apply_update(root: Path, runner: Runner = subprocess.run) -> UpdateStatus:
    code, out = _git(root, "pull", "--ff-only", runner=runner)
    if code != 0:
        log.warning("update pull failed: %s", out)
        return UpdateStatus(
            True, applied=False, message="Update failed. Run git pull in the DarkeVox folder."
        )
    return UpdateStatus(True, applied=True, message="Updated. Restart DarkeVox to finish.")
