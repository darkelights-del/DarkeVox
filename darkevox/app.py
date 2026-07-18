"""Entry point: single-instance lock, logging, tray, Qt event loop.

Qt imports stay inside main() so the module is importable (for the lock and
tests) without PySide6 present.
"""

from __future__ import annotations

import logging
import socket
import sys

from darkevox import APP_NAME
from darkevox import config as config_mod
from darkevox.logging_setup import setup_logging

log = logging.getLogger(__name__)

_ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    """One DarkeVox per session: named mutex on Windows, abstract socket elsewhere.

    The abstract-socket path covers Linux dev boxes; the app itself only
    targets Windows, where the kernel mutex is the standard mechanism.
    """

    def __init__(self, name: str = "darkevox") -> None:
        self._name = name
        self._mutex_handle: int | None = None
        self._sock: socket.socket | None = None

    def acquire(self) -> bool:
        if sys.platform == "win32":
            return self._acquire_windows()
        return self._acquire_posix()

    def _acquire_windows(self) -> bool:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        self._mutex_handle = kernel32.CreateMutexW(None, False, f"Local\\{self._name}")
        return kernel32.GetLastError() != _ERROR_ALREADY_EXISTS

    def _acquire_posix(self) -> bool:
        self._sock = socket.socket(socket.AF_UNIX)
        try:
            self._sock.bind(f"\0{self._name}-lock")
        except OSError:
            return False
        return True


def main() -> int:
    cfg = config_mod.load()
    log_file = setup_logging(config_mod.logs_dir(), console=sys.stderr is not None)
    instance = SingleInstance()
    if not instance.acquire():
        log.info("DarkeVox is already running; exiting")
        return 0

    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    from darkevox.ui.theme import qss
    from darkevox.ui.tray import Tray

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(qss())
    log.info("started; config=%s log=%s", config_mod.config_path(), log_file)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        log.warning("system tray unavailable; app has no visible surface")

    tray = Tray()
    tray.quit_requested.connect(app.quit)
    tray.set_status("idle")
    tray.show()

    _ = cfg  # phases 1-2 wire hotkeys, STT, and polish from here
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
