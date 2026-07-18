"""Best-effort return of focus to the app the user was working in.

Clicking the panel makes it the foreground window, so a paste would land in
DarkeVox itself. The tracker polls the real foreground window while the
panel is open (ignoring our own windows) and re-activates it before Insert
pastes. Windows-only underneath; a silent no-op elsewhere.
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)


class ForegroundTracker:
    def __init__(self) -> None:
        self._target: int | None = None

    @property
    def target(self) -> int | None:
        return self._target

    def poll(self, own_window_ids: set[int]) -> None:
        """Remember the current foreground window unless it is one of ours."""
        if sys.platform != "win32":
            return
        import win32gui

        try:
            hwnd = win32gui.GetForegroundWindow()
        except Exception:
            return
        if hwnd and hwnd not in own_window_ids:
            self._target = hwnd

    def restore(self) -> bool:
        """Re-activate the remembered window; True when focus actually moved."""
        if sys.platform != "win32" or not self._target:
            return False
        import win32gui

        try:
            win32gui.SetForegroundWindow(self._target)
            return True
        except Exception as exc:  # foreground lock, window gone: paste proceeds blind
            log.warning("could not restore foreground window: %s", exc)
            return False
