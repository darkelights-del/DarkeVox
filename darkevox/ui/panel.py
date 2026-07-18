"""The floating dictation panel: live transcript, editable polish, mouse PTT.

A frameless always-on-top card that collapses into a mic pill. The mic (in
both states) is mouse-activated: click toggles a session, press-and-hold is
push-to-talk, dragging moves the window and cancels the gesture. Sessions
started here stream the raw transcript live into an editable field; tone
buttons re-polish the (possibly hand-edited) raw text into the second
editable field; Insert returns focus to the previous app and pastes.

Spec: darkevox-ui-style (Components > Panel). All heavy work stays on the
controller's worker thread; this file only paints and forwards.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from darkevox.inject.focus import ForegroundTracker
from darkevox.ui.icons import _render_mic
from darkevox.ui.interaction import DRAG_CANCEL_PX, HOLD_MS, PressHoldInterpreter
from darkevox.ui.theme import SHADOW_BLUR, SHADOW_DY, SHADOW_RGBA, TOKENS

_MARGIN = 14  # room for the drop shadow
_CARD_WIDTH = 380
_PILL = 56
_TONES = ("email", "message", "notes")


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "caption")
    return label


class _MicControl(QWidget):
    """Shared mouse logic for the mic: click, hold, drag."""

    def __init__(self, controller: Any, draggable: bool) -> None:
        super().__init__()
        self._controller = controller
        self._draggable = draggable
        self.recording = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._interpreter = PressHoldInterpreter(
            on_click=controller.panel_click,
            on_hold_start=controller.panel_press,
            on_hold_end=controller.panel_release,
        )
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.setInterval(HOLD_MS)
        self._hold_timer.timeout.connect(self._interpreter.hold_elapsed)
        self._press_pos: QPoint | None = None
        self._drag_offset: QPoint | None = None
        self._dragging = False

    def set_recording(self, recording: bool) -> None:
        self.recording = recording
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # Qt override
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press_pos = event.globalPosition().toPoint()
        self._drag_offset = self._press_pos - self.window().frameGeometry().topLeft()
        self._dragging = False
        self._interpreter.press()
        self._hold_timer.start()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # Qt override
        if self._press_pos is None:
            return
        pos = event.globalPosition().toPoint()
        if not self._dragging and (pos - self._press_pos).manhattanLength() > DRAG_CANCEL_PX:
            self._dragging = True
            self._hold_timer.stop()
            self._interpreter.cancel()
        if self._dragging and self._draggable and self._drag_offset is not None:
            self.window().move(pos - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # Qt override
        self._hold_timer.stop()
        if not self._dragging:
            self._interpreter.release()
        self._press_pos = None
        self._dragging = False


class _Pill(_MicControl):
    """Collapsed state: the whole widget is the mic. Double-click expands."""

    def __init__(self, controller: Any, on_expand: Any) -> None:
        super().__init__(controller, draggable=True)
        self._on_expand = on_expand
        self.setFixedSize(_PILL, _PILL)
        self.setToolTip("Click: start/stop. Hold: push to talk. Double-click: open.")

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # Qt override
        self._interpreter.cancel()
        self._on_expand()

    def paintEvent(self, event: QPaintEvent) -> None:  # Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), _render_mic(_PILL, self.recording))
        painter.end()


class _MicButton(_MicControl):
    """Expanded state: a round mic button inside the card."""

    def __init__(self, controller: Any) -> None:
        super().__init__(controller, draggable=False)
        self.setFixedSize(52, 52)

    def paintEvent(self, event: QPaintEvent) -> None:  # Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill = TOKENS["blue_500" if self.recording else "blue_400"]
        if self.underMouse() and not self.recording:
            fill = TOKENS["blue_300"]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(fill))
        painter.drawEllipse(self.rect())
        from darkevox.ui.icons import _draw_mic_glyph

        _draw_mic_glyph(painter, self.width())
        painter.end()


class _DragHeader(QWidget):
    """Card title row; dragging it moves the panel."""

    def __init__(self) -> None:
        super().__init__()
        self._offset: QPoint | None = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # Qt override
        if self._offset is not None:
            self.window().move(event.globalPosition().toPoint() - self._offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # Qt override
        self._offset = None


class Panel(QWidget):
    def __init__(self, controller: Any, tracker: ForegroundTracker, default_tone: str) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._controller = controller
        self._tracker = tracker
        self._tone = default_tone if default_tone in _TONES else "email"
        self._live = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)
        self._pill = _Pill(controller, on_expand=self.show_expanded)
        self._card = self._build_card()
        self._stack.addWidget(self._wrap_pill())
        self._stack.addWidget(self._card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(SHADOW_BLUR)
        shadow.setOffset(0, SHADOW_DY)
        shadow.setColor(QColor(*SHADOW_RGBA))
        self._stack.setGraphicsEffect(shadow)

        # Track the window the user actually works in, so Insert can hand
        # focus back before pasting.
        self._poll = QTimer(self)
        self._poll.setInterval(500)
        self._poll.timeout.connect(self._poll_foreground)

    # ---- construction ----

    def _wrap_pill(self) -> QWidget:
        holder = QWidget()
        box = QVBoxLayout(holder)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self._pill, alignment=Qt.AlignmentFlag.AlignCenter)
        return holder

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        card.setFixedWidth(_CARD_WIDTH)
        box = QVBoxLayout(card)
        box.setContentsMargins(16, 12, 16, 16)
        box.setSpacing(8)

        header = _DragHeader()
        header_box = QHBoxLayout(header)
        header_box.setContentsMargins(0, 0, 0, 0)
        title = QLabel("DarkeVox")
        title.setProperty("role", "section")
        header_box.addWidget(title)
        header_box.addStretch(1)
        collapse = QPushButton("hide")
        collapse.setProperty("variant", "quiet")
        collapse.clicked.connect(self.show_pill)
        header_box.addWidget(collapse)
        box.addWidget(header)

        mic_row = QHBoxLayout()
        self._mic = _MicButton(self._controller)
        mic_row.addWidget(self._mic)
        self._status = QLabel("click the mic, or hold it to talk")
        self._status.setProperty("role", "caption")
        self._status.setWordWrap(True)
        mic_row.addWidget(self._status, stretch=1)
        box.addLayout(mic_row)

        box.addWidget(_caption("Heard"))
        self._raw = QPlainTextEdit()
        self._raw.setPlaceholderText("your words land here as you speak")
        self._raw.setMinimumHeight(76)
        box.addWidget(self._raw)

        box.addWidget(_caption("Polished"))
        self._polished = QPlainTextEdit()
        self._polished.setPlaceholderText("pick a tone below to polish")
        self._polished.setMinimumHeight(76)
        box.addWidget(self._polished)

        tone_row = QHBoxLayout()
        self._tone_buttons: dict[str, QPushButton] = {}
        for tone in _TONES:
            button = QPushButton(tone)
            button.setCheckable(True)
            button.clicked.connect(lambda _c=False, t=tone: self._polish_as(t))
            tone_row.addWidget(button)
            self._tone_buttons[tone] = button
        self._tone_buttons[self._tone].setChecked(True)
        box.addLayout(tone_row)

        action_row = QHBoxLayout()
        copy = QPushButton("Copy")
        copy.clicked.connect(self._copy)
        action_row.addWidget(copy)
        clear = QPushButton("Clear")
        clear.clicked.connect(self._clear)
        action_row.addWidget(clear)
        action_row.addStretch(1)
        insert = QPushButton("Insert")
        insert.setProperty("variant", "primary")
        insert.clicked.connect(self._insert)
        action_row.addWidget(insert)
        box.addLayout(action_row)
        return card

    # ---- state switching ----

    def show_expanded(self) -> None:
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16_777_215, 16_777_215)
        self._stack.setCurrentIndex(1)
        self.adjustSize()
        self.show()
        self._poll.start()

    def show_pill(self) -> None:
        self._stack.setCurrentIndex(0)
        self.setFixedSize(_PILL + 2 * _MARGIN, _PILL + 2 * _MARGIN)
        self.show()
        self._poll.start()

    def collapsed(self) -> bool:
        return self._stack.currentIndex() == 0

    def hideEvent(self, event: object) -> None:  # Qt override
        self._poll.stop()
        super().hideEvent(event)

    def _poll_foreground(self) -> None:
        self._tracker.poll({int(self.winId())})

    # ---- controller-facing slots (wired in app.py) ----

    def set_recording(self, recording: bool) -> None:
        self._live = recording
        self._pill.set_recording(recording)
        self._mic.set_recording(recording)
        if recording:
            self._status.setText("listening")
        elif not self._raw.toPlainText():
            self._status.setText("click the mic, or hold it to talk")

    def set_partial(self, text: str) -> None:
        if self._live:
            self._raw.setPlainText(text)
            self._raw.moveCursor(QTextCursor.MoveOperation.End)

    def on_session_finished(self, text: str) -> None:
        self._raw.setPlainText(text)
        if not text:
            self._status.setText("no speech heard")
            return
        self._polish_as(self._tone)

    def on_polish_ready(self, text: str, tone: str, fell_back: bool) -> None:
        self._polished.setPlainText(text)
        status = "polish unavailable; showing raw" if fell_back else f"polished: {tone}"
        self._status.setText(status)

    # ---- actions ----

    def _polish_as(self, tone: str) -> None:
        self._tone = tone
        for name, button in self._tone_buttons.items():
            button.setChecked(name == tone)
        raw = self._raw.toPlainText().strip()
        if not raw:
            self._status.setText("nothing to polish yet")
            return
        self._status.setText("polishing")
        self._controller.request_polish(raw, tone)

    def _best_text(self) -> str:
        return self._polished.toPlainText().strip() or self._raw.toPlainText().strip()

    def _copy(self) -> None:
        text = self._best_text()
        if text:
            QGuiApplication.clipboard().setText(text)
            self._status.setText("copied")

    def _insert(self) -> None:
        text = self._best_text()
        if text:
            self._controller.request_inject(text)
            self._status.setText("inserting")

    def _clear(self) -> None:
        self._raw.clear()
        self._polished.clear()
        self._status.setText("click the mic, or hold it to talk")
