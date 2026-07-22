"""System tray icon and menu: status, tone, toggle dictation, settings, quit.

The tray is the app's front door: a left-click opens the panel, the menu
opens with a glanceable status row (dot + label), and the update action
tells the truth about whether an update exists. Menus stay stock QMenu:
mutating a QMenu's window flags recreates its native popup window and
silently breaks right-click after first use (field-reported). QSS styles
them; Windows 11 rounds popup corners natively.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from darkevox import __version__
from darkevox.config import TONES
from darkevox.ui.icons import dot_pixmap, tray_icon
from darkevox.ui.status import DOTS, READY, ready


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
        self.setToolTip(f"DarkeVox {__version__}")
        # setContextMenu does not take ownership; keep the menu referenced.
        self._menu = QMenu()
        self._status = QAction(ready(), self._menu)
        self._status.setEnabled(False)
        self._menu.addAction(self._status)
        self._menu.addSeparator()

        self._panel_action = QAction("Open panel", self._menu)
        self._panel_action.triggered.connect(self.panel_requested.emit)
        self._menu.addAction(self._panel_action)

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
        self._update_action = QAction("Check for updates", self._menu)
        self._update_action.triggered.connect(self.update_requested.emit)
        self._menu.addAction(self._update_action)
        settings_action = QAction("Settings", self._menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self._menu.addAction(settings_action)
        quit_action = QAction("Quit DarkeVox", self._menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)
        self.setContextMenu(self._menu)

        # Left-click opens the panel; the menu stays on right-click.
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.panel_requested.emit()

    def set_status(self, text: str, state: str = READY) -> None:
        self._status.setText(text)
        self._status.setIcon(dot_pixmap(DOTS.get(state, DOTS[READY])))
        self.setToolTip(f"DarkeVox {__version__} — {text}")

    def set_panel_visible(self, visible: bool) -> None:
        self._panel_action.setText("Open panel" if not visible else "Hide panel")

    def set_update_available(self, available: bool) -> None:
        self._update_action.setText(
            "Update available — install" if available else "Check for updates"
        )

    def set_tone(self, tone: str) -> None:
        action = self._tone_actions.get(tone)
        if action is not None:
            action.setChecked(True)

    def set_recording(self, recording: bool) -> None:
        self.setIcon(tray_icon(recording=recording))

    def notify(self, title: str, body: str) -> None:
        self.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 4000)
