"""System tray icon and menu."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from darkevox.ui.icons import tray_icon


class Tray(QSystemTrayIcon):
    quit_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setIcon(tray_icon())
        self.setToolTip("DarkeVox")
        # setContextMenu does not take ownership; keep the menu referenced.
        self._menu = QMenu()
        self._status = QAction("idle", self._menu)
        self._status.setEnabled(False)
        self._menu.addAction(self._status)
        self._menu.addSeparator()
        quit_action = QAction("Quit DarkeVox", self._menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)
        self.setContextMenu(self._menu)

    def set_status(self, text: str) -> None:
        self._status.setText(text)
        self.setToolTip(f"DarkeVox: {text}")

    def set_recording(self, recording: bool) -> None:
        self.setIcon(tray_icon(recording=recording))

    def notify(self, title: str, body: str) -> None:
        self.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 4000)
