"""First-run model download dialog. Honest progress, no marketing copy.

The first thing a user ever sees, so it carries the brand: the wave mark
beside the title. The bar glides between polled values (linear — easing
would read as rubber-banding on a data display), the readout sits below
as a caption, and a failure offers Retry instead of a dead end.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QVariantAnimation, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from darkevox.ui import motion
from darkevox.ui.buttons import AnimatedButton
from darkevox.ui.icons import _render_mic


class DownloadDialog(QDialog):
    cancelled = Signal()
    retry_requested = Signal()

    def __init__(self, model: str, approx_mb: int) -> None:
        super().__init__()
        self.setProperty("role", "window")
        self.setWindowTitle("DarkeVox setup")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._approx_mb = approx_mb

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(12)
        mark = QLabel()
        pixmap = QPixmap(_render_mic(48, False))
        mark.setPixmap(pixmap)
        mark.setFixedSize(48, 48)
        head.addWidget(mark)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel(f"Downloading the {model} speech model")
        title.setProperty("role", "section")
        title_col.addWidget(title)
        caption = QLabel(f"One time, about {approx_mb} MB. Dictation starts when this finishes.")
        caption.setProperty("role", "caption")
        caption.setWordWrap(True)
        title_col.addWidget(caption)
        head.addLayout(title_col, stretch=1)
        layout.addLayout(head)

        self._bar = QProgressBar()
        self._bar.setRange(0, approx_mb)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar)
        self._readout = QLabel(f"0 / {approx_mb} MB")
        self._readout.setProperty("role", "caption")
        self._readout.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._readout)

        self._status = QLabel("")
        self._status.setProperty("role", "error")
        self._status.setWordWrap(True)
        self._status.hide()
        layout.addWidget(self._status)

        buttons = QHBoxLayout()
        note = QLabel("You can change the model later in Settings.")
        note.setProperty("role", "caption")
        buttons.addWidget(note)
        buttons.addStretch(1)
        self._retry = AnimatedButton("Retry", "primary")
        self._retry.clicked.connect(self._on_retry)
        self._retry.hide()
        buttons.addWidget(self._retry)
        cancel = AnimatedButton("Cancel", "secondary")
        cancel.clicked.connect(self._on_cancel)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        self._bar_anim = QVariantAnimation(self)
        self._bar_anim.setDuration(motion.duration(280))
        self._bar_anim.valueChanged.connect(
            lambda value: self._bar.setValue(int(value))  # type: ignore[arg-type]
        )

    def set_progress(self, mb: float) -> None:
        target = min(int(mb), self._bar.maximum())
        self._readout.setText(f"{target} / {self._approx_mb} MB")
        if motion.enabled() and self.isVisible():
            self._bar_anim.stop()
            self._bar_anim.setStartValue(self._bar.value())
            self._bar_anim.setEndValue(target)
            self._bar_anim.start()
        else:
            self._bar.setValue(target)

    def show_error(self, message: str) -> None:
        self._status.setText(message)
        self._status.show()
        self._retry.show()

    def _on_retry(self) -> None:
        self._status.hide()
        self._retry.hide()
        self.retry_requested.emit()

    def _on_cancel(self) -> None:
        self._bar_anim.stop()
        self.cancelled.emit()
        self.reject()

    def closeEvent(self, event: object) -> None:  # Qt override
        self._bar_anim.stop()
        super().closeEvent(event)
