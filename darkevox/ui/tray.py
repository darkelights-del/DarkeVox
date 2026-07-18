"""System tray icon and menu: status, tone, toggle dictation, settings, quit."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from darkevox.config import TONES
from darkevox.ui.icons import tray_icon


class Tray(QSystemTrayIcon):
    quit_requested = Signal()
    tone_selected = Signal(str)
    toggle_dictation = Signal()
    panel_requested = Signal()
    settings_requested = Signal()
    update_requested = Signal()

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

        panel_action = QAction("Open panel", self._menu)
        panel_action.triggered.connect(self.panel_requested.emit)
        self._menu.addAction(panel_action)

        toggle_action = QAction("Toggle dictation", self._menu)
        toggle_action.triggered.connect(self.toggle_dictation.emit)
        self._menu.addAction(toggle_action)

        tone_menu = self._menu.addMenu("Tone")
        self._tone_group = QActionGroup(tone_menu)
        self._tone_actions: dict[str, QAction] = {}
        for tone in TONES:
            action = QAction(tone, tone_menu)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, t=tone: self.tone_selected.emit(t))
            self._tone_group.addAction(action)
            tone_menu.addAction(action)
            self._tone_actions[tone] = action

        self._menu.addSeparator()
        update_action = QAction("Update now", self._menu)
        update_action.triggered.connect(self.update_requested.emit)
        self._menu.addAction(update_action)
        settings_action = QAction("Settings", self._menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self._menu.addAction(settings_action)
        quit_action = QAction("Quit DarkeVox", self._menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)
        self.setContextMenu(self._menu)

    def set_status(self, text: str) -> None:
        self._status.setText(text)
        self.setToolTip(f"DarkeVox: {text}")

    def set_tone(self, tone: str) -> None:
        action = self._tone_actions.get(tone)
        if action is not None:
            action.setChecked(True)

    def set_recording(self, recording: bool) -> None:
        self.setIcon(tray_icon(recording=recording))

    def notify(self, title: str, body: str) -> None:
        self.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 4000)
