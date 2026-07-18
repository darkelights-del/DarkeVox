"""First-run model download dialog. Honest progress, no marketing copy."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class DownloadDialog(QDialog):
    cancelled = Signal()

    def __init__(self, model: str, approx_mb: int) -> None:
        super().__init__()
        self.setWindowTitle("DarkeVox setup")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"Downloading the {model} speech model")
        title.setProperty("role", "section")
        layout.addWidget(title)

        caption = QLabel(f"One time, about {approx_mb} MB. Dictation starts when this finishes.")
        caption.setProperty("role", "caption")
        caption.setWordWrap(True)
        layout.addWidget(caption)

        self._bar = QProgressBar()
        self._bar.setRange(0, approx_mb)
        self._bar.setValue(0)
        self._bar.setFormat("%v / %m MB")
        layout.addWidget(self._bar)

        self._status = QLabel("")
        self._status.setProperty("role", "error")
        self._status.setWordWrap(True)
        self._status.hide()
        layout.addWidget(self._status)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self._on_cancel)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def set_progress(self, mb: float) -> None:
        self._bar.setValue(min(int(mb), self._bar.maximum()))

    def show_error(self, message: str) -> None:
        self._status.setText(message)
        self._status.show()

    def _on_cancel(self) -> None:
        self.cancelled.emit()
        self.reject()
