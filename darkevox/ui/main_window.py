"""The main window. Phase 3 ships the Compose tab: paste rough text, pick a
tone, read the polished result next to the original, copy it. The Context
tab (library, summaries, Q&A) joins in phases 4-5.

This is also the debugging surface for prompt quality: both versions stay
visible and editable, so a bad polish is diagnosable at a glance.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

_TONES = ("email", "message", "notes")


def _overline(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setProperty("role", "overline")
    return label


class MainWindow(QWidget):
    def __init__(self, controller: Any, default_tone: str) -> None:
        super().__init__()
        self.setWindowTitle("DarkeVox")
        self.setMinimumSize(560, 520)
        self._controller = controller
        self._tone = default_tone if default_tone in _TONES else "email"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_compose(), "Compose")
        layout.addWidget(self._tabs)

    def _build_compose(self) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(10)

        box.addWidget(_overline("Rough"))
        self._input = QPlainTextEdit()
        self._input.setPlaceholderText("paste or type rough text, then pick a tone")
        box.addWidget(self._input, stretch=3)

        tone_row = QHBoxLayout()
        self._tone_buttons: dict[str, QPushButton] = {}
        for tone in _TONES:
            button = QPushButton(tone)
            button.setCheckable(True)
            button.clicked.connect(lambda _c=False, t=tone: self._select_tone(t))
            tone_row.addWidget(button)
            self._tone_buttons[tone] = button
        self._tone_buttons[self._tone].setChecked(True)
        tone_row.addStretch(1)
        polish = QPushButton("Polish")
        polish.setProperty("variant", "primary")
        polish.clicked.connect(self._polish)
        tone_row.addWidget(polish)
        box.addLayout(tone_row)

        box.addWidget(_overline("Polished"))
        self._output = QPlainTextEdit()
        self._output.setPlaceholderText("the cleaned version lands here, editable")
        box.addWidget(self._output, stretch=3)

        bottom = QHBoxLayout()
        self._status = QLabel("offline-friendly: polish runs on your Ollama")
        self._status.setProperty("role", "caption")
        bottom.addWidget(self._status, stretch=1)
        copy = QPushButton("Copy")
        copy.clicked.connect(self._copy)
        bottom.addWidget(copy)
        box.addLayout(bottom)
        return page

    def _select_tone(self, tone: str) -> None:
        self._tone = tone
        for name, button in self._tone_buttons.items():
            button.setChecked(name == tone)

    def _polish(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            self._status.setText("nothing to polish yet")
            return
        self._status.setText("polishing")
        self._controller.request_polish(text, self._tone, requester="compose")

    def on_polish_ready(self, text: str, tone: str, fell_back: bool) -> None:
        self._output.setPlainText(text)
        self._status.setText(
            "polish unavailable; showing your text" if fell_back else f"polished: {tone}"
        )

    def _copy(self) -> None:
        text = self._output.toPlainText().strip() or self._input.toPlainText().strip()
        if text:
            QGuiApplication.clipboard().setText(text)
            self._status.setText("copied")

    def open_compose(self) -> None:
        self._tabs.setCurrentIndex(0)
        self.show()
        self.raise_()
        self.activateWindow()
