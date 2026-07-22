"""The floating dictation panel: live transcript, editable polish, mouse PTT.

One big frameless always-on-top card — no minimized state. It fades in
(90 ms) and closes to the tray (150 ms fade), exactly like the HUD, and
reopens from a tray click. The mic is the meter: its wave bars ride the
live input level and a pulse ring breathes while recording. Voice BUILDS
on the draft (darkevox.ui.draft) — a new take appends, never replaces,
and an accidental tap can't wipe words. Status copy comes from
darkevox.ui.status, the one vocabulary every surface shares.

Spec: darkevox-ui-style (Components > Panel). All heavy work stays on the
controller's worker thread; this file only paints and forwards.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QShortcut,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from darkevox.inject.focus import ForegroundTracker
from darkevox.ui import motion, status
from darkevox.ui.buttons import AnimatedButton
from darkevox.ui.draft import Draft
from darkevox.ui.icons import _draw_mic_glyph
from darkevox.ui.interaction import DRAG_CANCEL_PX, HOLD_MS, PressHoldInterpreter
from darkevox.ui.theme import (
    DUR_ENTER,
    DUR_EXIT,
    DUR_PRESS,
    DUR_RELEASE,
    DUR_SETTLE,
    DUR_TEXT_SETTLE,
    DUR_TINT,
    PULSE_MS,
    RADIUS_CONTROL,
    SHADOW_BLUR,
    SHADOW_DY,
    SHADOW_MARGIN,
    SHADOW_RGBA,
    TOKENS,
)

_CARD_WIDTH = 380
_MIC = 56
_TONES = ("email", "message", "notes", "verbatim")


def _overline(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setProperty("role", "overline")
    return label


class _MicButton(QWidget):
    """The card's round mic: click toggles, hold is push-to-talk.

    Sliding off the button (>6 px) cancels the gesture. Press scale,
    hover tint, recording pulse ring, and the live level that scales the
    wave bars all live here; loops stop whenever the widget hides.
    """

    def __init__(self, controller: Any) -> None:
        super().__init__()
        self._controller = controller
        self.recording = False
        self.setFixedSize(_MIC, _MIC)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
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
        self._cancelled = False

        self._scale = 1.0
        self._level = 0.0
        self._pulse_v = 0.0
        self._bg = QColor(TOKENS["blue_400"])
        self._scale_anim = motion.make_anim(self, DUR_PRESS, self._on_scale)
        self._level_anim = motion.make_anim(self, DUR_TINT, self._on_level)
        self._bg_anim = motion.make_anim(self, DUR_TINT, self._on_bg)
        self._pulse = QVariantAnimation(self)
        self._pulse.setDuration(PULSE_MS)
        self._pulse.setStartValue(0.0)
        self._pulse.setKeyValueAt(0.5, 1.0)
        self._pulse.setEndValue(0.0)
        self._pulse.setEasingCurve(motion.QEasingCurve.Type.InOutSine)
        self._pulse.setLoopCount(-1)
        self._pulse.valueChanged.connect(self._on_pulse)

    # ---- live state ----

    def set_recording(self, recording: bool) -> None:
        self.recording = recording
        self._sync_pulse()
        if not recording:
            self._level = 0.0
            self._level_anim.stop()
        self._retint()
        self.update()

    def set_level(self, level: float) -> None:
        if self.recording and self.isVisible():
            motion.retarget(self._level_anim, self._level, max(0.0, min(1.0, level)))

    def _sync_pulse(self) -> None:
        should_run = self.recording and self.isVisible() and motion.enabled()
        running = self._pulse.state() == QVariantAnimation.State.Running
        if should_run and not running:
            self._pulse.start()
        elif not should_run and running:
            self._pulse.stop()
            self._pulse_v = 0.0

    def _target_bg(self) -> QColor:
        if self.recording:
            return QColor(TOKENS["blue_500"])
        if self.underMouse():
            return QColor(TOKENS["blue_300"])
        return QColor(TOKENS["blue_400"])

    def _retint(self) -> None:
        motion.retarget(self._bg_anim, QColor(self._bg), self._target_bg(), DUR_TINT)

    def _on_scale(self, value: object) -> None:
        self._scale = float(value)  # type: ignore[arg-type]
        self.update()

    def _on_level(self, value: object) -> None:
        self._level = float(value)  # type: ignore[arg-type]
        self.update()

    def _on_pulse(self, value: object) -> None:
        self._pulse_v = float(value)  # type: ignore[arg-type]
        self.update()

    def _on_bg(self, value: object) -> None:
        if isinstance(value, QColor):
            self._bg = value
            self.update()

    def showEvent(self, event: object) -> None:  # Qt override
        super().showEvent(event)
        self._sync_pulse()

    def hideEvent(self, event: object) -> None:  # Qt override
        self._pulse.stop()
        self._pulse_v = 0.0
        super().hideEvent(event)

    # ---- mouse ----

    def enterEvent(self, event: object) -> None:  # Qt override
        self._retint()
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:  # Qt override
        self._retint()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # Qt override
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press_pos = event.globalPosition().toPoint()
        self._cancelled = False
        self._interpreter.press()
        self._hold_timer.start()
        motion.retarget(self._scale_anim, self._scale, 0.96, DUR_PRESS)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # Qt override
        if self._press_pos is None or self._cancelled:
            return
        pos = event.globalPosition().toPoint()
        if (pos - self._press_pos).manhattanLength() > DRAG_CANCEL_PX:
            # Slipped off the button: cancel rather than misfire a session.
            self._cancelled = True
            self._hold_timer.stop()
            self._interpreter.cancel()
            motion.retarget(self._scale_anim, self._scale, 1.0, DUR_RELEASE)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # Qt override
        self._hold_timer.stop()
        if not self._cancelled:
            self._interpreter.release()
        self._press_pos = None
        self._cancelled = False
        motion.retarget(self._scale_anim, self._scale, 1.0, DUR_RELEASE)

    # ---- painting ----

    def paintEvent(self, event: QPaintEvent) -> None:  # Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._scale != 1.0:
            center = self.rect().center()
            painter.translate(center)
            painter.scale(self._scale, self._scale)
            painter.translate(-center)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg)
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        level = self._level if self.recording else None
        _draw_mic_glyph(painter, self.width(), level=level)
        if self.recording and self._pulse_v > 0.01:
            color = QColor(TOKENS["blue_300"])
            color.setAlphaF(0.25 + 0.55 * self._pulse_v)
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        painter.end()


class _DragHeader(QWidget):
    """Card title row; dragging it moves the panel, release settles on-screen."""

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
            # Locked 1:1 to the pointer; easing during drag feels detached.
            self.window().move(event.globalPosition().toPoint() - self._offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # Qt override
        moved = self._offset is not None
        self._offset = None
        if moved:
            window = self.window()
            if isinstance(window, Panel):
                window.settle_on_screen()


class _SegmentFrame(QFrame):
    """The tone picker's track: a filled rounded strip behind the chips."""

    def paintEvent(self, event: QPaintEvent) -> None:  # Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(TOKENS["cream_200"]))
        painter.drawRoundedRect(self.rect(), RADIUS_CONTROL, RADIUS_CONTROL)
        painter.end()


class Panel(QWidget):
    settings_requested = Signal()
    visibility_changed = Signal(bool)

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
        self._draft = Draft()
        self._hotkey_hint = ""
        self._pending_note = ""
        self._listen_seconds = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN)
        self._card = self._build_card()
        outer.addWidget(self._card)

        # With every container genuinely transparent, the one shadow
        # silhouettes the card shape, never a square.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(SHADOW_BLUR)
        shadow.setOffset(0, SHADOW_DY)
        shadow.setColor(QColor(*SHADOW_RGBA))
        self._card.setGraphicsEffect(shadow)

        # Open/close ride windowOpacity, the HUD's proven pattern.
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setEasingCurve(motion.EASE_OUT_SOFT)
        self._fade.finished.connect(self._after_fade)
        self._geo_anim = QPropertyAnimation(self, b"geometry", self)
        self._geo_anim.setEasingCurve(motion.EASE_OUT)

        self._revert_timer = QTimer(self)
        self._revert_timer.setSingleShot(True)
        self._revert_timer.timeout.connect(self._show_ready)
        self._listen_timer = QTimer(self)
        self._listen_timer.setInterval(1000)
        self._listen_timer.timeout.connect(self._tick_listening)

        # Track the window the user actually works in, so Insert can hand
        # focus back before pasting.
        self._poll = QTimer(self)
        self._poll.setInterval(500)
        self._poll.timeout.connect(self._poll_foreground)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.close_to_tray)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._insert)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self._copy)

    # ---- construction ----

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        card.setFixedWidth(_CARD_WIDTH)
        box = QVBoxLayout(card)
        box.setContentsMargins(20, 20, 20, 20)
        box.setSpacing(4)

        header = _DragHeader()
        header_box = QHBoxLayout(header)
        header_box.setContentsMargins(0, 0, 0, 0)
        header_box.setSpacing(4)
        title = QLabel("DarkeVox")
        title.setProperty("role", "section")
        header_box.addWidget(title)
        header_box.addStretch(1)
        settings_btn = AnimatedButton("settings", "quiet")
        settings_btn.clicked.connect(self.settings_requested.emit)
        header_box.addWidget(settings_btn)
        collapse = AnimatedButton("hide", "quiet")
        collapse.clicked.connect(self.close_to_tray)
        header_box.addWidget(collapse)
        box.addWidget(header)

        box.addSpacing(8)
        mic_row = QHBoxLayout()
        mic_row.setSpacing(12)
        self._mic = _MicButton(self._controller)
        mic_row.addWidget(self._mic)
        status_col = QVBoxLayout()
        status_col.setSpacing(2)
        status_col.addStretch(1)
        self._status = QLabel("")
        status_col.addWidget(self._status)
        self._status_sub = QLabel("")
        self._status_sub.setProperty("role", "caption")
        status_col.addWidget(self._status_sub)
        status_col.addStretch(1)
        mic_row.addLayout(status_col, stretch=1)
        box.addLayout(mic_row)

        box.addSpacing(8)
        heard_row = QHBoxLayout()
        heard_row.addWidget(_overline("Heard"))
        heard_row.addStretch(1)
        self._undo_btn = AnimatedButton("undo take", "quiet")
        self._undo_btn.clicked.connect(self._undo_take)
        self._undo_btn.hide()
        heard_row.addWidget(self._undo_btn)
        box.addLayout(heard_row)
        self._raw = QPlainTextEdit()
        self._raw.setPlaceholderText("your words build up here as you speak")
        self._raw.setFixedHeight(72)
        box.addWidget(self._raw)

        box.addSpacing(8)
        box.addWidget(_overline("Polished"))
        self._polished = QPlainTextEdit()
        self._polished.setProperty("variant", "hero")
        self._polished.setPlaceholderText(
            "pick a tone to polish — Insert prefers this field when filled"
        )
        self._polished.setFixedHeight(120)
        box.addWidget(self._polished)

        box.addSpacing(8)
        segment = _SegmentFrame()
        seg_box = QHBoxLayout(segment)
        seg_box.setContentsMargins(4, 4, 4, 4)
        seg_box.setSpacing(2)
        self._tone_buttons: dict[str, AnimatedButton] = {}
        for tone in _TONES:
            button = AnimatedButton(tone, "chip")
            button.setCheckable(True)
            button.setToolTip("click again to re-polish after edits")
            button.clicked.connect(lambda _c=False, t=tone: self._polish_as(t))
            seg_box.addWidget(button, stretch=1)
            self._tone_buttons[tone] = button
        self._tone_buttons[self._tone].setChecked(True)
        box.addWidget(segment)

        box.addSpacing(8)
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self._copy_btn = AnimatedButton(status.COPY, "secondary")
        self._copy_btn.clicked.connect(self._copy)
        action_row.addWidget(self._copy_btn)
        clear = AnimatedButton("Clear", "quiet")
        clear.setMinimumHeight(36)  # rides in the action row; align with its peers
        clear.clicked.connect(self._clear)
        action_row.addWidget(clear)
        action_row.addStretch(1)
        insert = AnimatedButton("Insert", "primary")
        insert.clicked.connect(self._insert)
        action_row.addWidget(insert)
        box.addLayout(action_row)
        return card

    # ---- visibility ----

    def show_panel(self) -> None:
        self.adjustSize()
        self._clamp_instantly()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self._start_fade(1.0, DUR_ENTER)
        else:
            self._fade.stop()
            self.setWindowOpacity(1.0)
        self._poll.start()
        self.visibility_changed.emit(True)

    def close_to_tray(self) -> None:
        if not self.isVisible():
            return
        self._start_fade(0.0, DUR_EXIT)
        self.visibility_changed.emit(False)

    def toggle_visibility(self) -> None:
        if self.isVisible() and float(self._fade.endValue() or 1.0) != 0.0:
            self.close_to_tray()
        else:
            self.show_panel()

    def _start_fade(self, end: float, ms: int) -> None:
        self._fade.stop()
        self._fade.setDuration(motion.duration(ms))
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(end)
        self._fade.start()

    def _after_fade(self) -> None:
        if float(self._fade.endValue()) == 0.0:
            self.hide()
            self.setWindowOpacity(1.0)

    def _clamp_instantly(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        rect = self.frameGeometry()
        margin = SHADOW_MARGIN
        x = max(area.left() - margin, min(rect.x(), area.right() - rect.width() + margin))
        y = max(area.top() - margin, min(rect.y(), area.bottom() - rect.height() + margin))
        self.move(x, y)

    def settle_on_screen(self) -> None:
        """After a drag release, glide back if the panel hangs off-screen."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        rect = self.frameGeometry()
        margin = SHADOW_MARGIN
        x = max(area.left() - margin, min(rect.x(), area.right() - rect.width() + margin))
        y = max(area.top() - margin, min(rect.y(), area.bottom() - rect.height() + margin))
        if (x, y) == (rect.x(), rect.y()):
            return
        target = QRect(x, y, rect.width(), rect.height())
        if not motion.enabled():
            self.setGeometry(target)
            return
        self._geo_anim.stop()
        self._geo_anim.setDuration(motion.duration(DUR_SETTLE))
        self._geo_anim.setStartValue(self.geometry())
        self._geo_anim.setEndValue(target)
        self._geo_anim.start()

    def hideEvent(self, event: object) -> None:  # Qt override
        self._poll.stop()
        super().hideEvent(event)

    def contextMenuEvent(self, event: object) -> None:  # Qt override
        menu = QMenu(self)
        menu.addAction("Settings", self.settings_requested.emit)
        menu.addAction("Hide DarkeVox (tray keeps running)", self.close_to_tray)
        menu.exec(event.globalPos())

    def _poll_foreground(self) -> None:
        self._tracker.poll({int(self.winId())})

    # ---- status ----

    def set_hotkey_hint(self, combo: str) -> None:
        self._hotkey_hint = combo
        if not self._live:
            self._show_ready()

    def _set_status(
        self,
        state: str,
        title: str,
        sub: str = "",
        revert_ms: int | None = None,
    ) -> None:
        self._revert_timer.stop()
        self._status.setText(title)
        self._status_sub.setText(sub)
        self._status_sub.setVisible(bool(sub))
        error = state == status.ERROR
        self._status.setProperty("role", "error" if error else "")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        if revert_ms is not None:
            self._revert_timer.start(revert_ms)

    def _show_ready(self) -> None:
        draft_words = len(self._raw.toPlainText().split())
        if draft_words:
            self._set_status(status.READY, status.ready(draft_words))
        else:
            self._set_status(status.READY, status.ready(), status.ready_hint(self._hotkey_hint))

    def _tick_listening(self) -> None:
        self._listen_seconds += 1
        self._set_status(status.LISTENING, status.listening(self._listen_seconds))

    # ---- controller-facing slots (wired in app.py) ----

    def set_recording(self, recording: bool) -> None:
        self._live = recording
        self._mic.set_recording(recording)
        self._raw.setReadOnly(recording)
        if recording:
            self._draft.begin_session(self._raw.toPlainText())
            self._listen_seconds = 0
            self._listen_timer.start()
            self._set_status(status.LISTENING, status.listening(0))
        else:
            self._listen_timer.stop()
            self._set_status(status.TRANSCRIBING, status.transcribing())

    def set_level(self, level: float) -> None:
        self._mic.set_level(level)

    def set_partial(self, text: str) -> None:
        if self._live:
            self._raw.setPlainText(self._draft.render(text))
            self._raw.moveCursor(QTextCursor.MoveOperation.End)

    def on_session_finished(self, text: str) -> None:
        committed = self._draft.commit(text)
        self._raw.setReadOnly(False)
        self._raw.setPlainText(committed)
        self._raw.moveCursor(QTextCursor.MoveOperation.End)
        self._undo_btn.setVisible(self._draft.can_undo)
        if not text.strip():
            if committed:
                self._show_ready()
            else:
                self._set_status(status.NO_SPEECH, status.no_speech(), status.no_speech_hint())
            return
        self._settle(self._raw)
        self._polish_as(self._tone)

    def on_polish_ready(self, text: str, tone: str, fell_back: bool) -> None:
        self._polished.setGraphicsEffect(None)
        self._polished.setPlainText(text)
        self._settle(self._polished)
        if fell_back:
            note = self._pending_note or status.fallback_hint()
            self._set_status(status.FALLBACK, status.fallback(), note)
        else:
            count = len(text.split())
            self._set_status(
                status.READY, status.polished(tone), status.polished_hint(count)
            )
        self._pending_note = ""

    def on_notice(self, note: str) -> None:
        self._pending_note = note

    def on_error(self, message: str) -> None:
        self._set_status(status.ERROR, message)

    def on_inserted(self, words: int) -> None:
        self._set_status(status.INSERTED, status.inserted(words), revert_ms=2000)

    def _settle(self, field: QPlainTextEdit) -> None:
        """New text lands with a short opacity settle instead of a teleport."""
        if not self.isVisible() or not motion.enabled():
            return
        effect = QGraphicsOpacityEffect(field)
        effect.setOpacity(0.55)
        field.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", effect)
        anim.setDuration(motion.duration(DUR_TEXT_SETTLE))
        anim.setEasingCurve(motion.EASE_OUT_SOFT)
        anim.setStartValue(0.55)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda f=field: f.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ---- actions ----

    def _polish_as(self, tone: str) -> None:
        self._tone = tone
        for name, button in self._tone_buttons.items():
            button.setChecked(name == tone)
        self._draft.sync(self._raw.toPlainText())
        raw = self._raw.toPlainText().strip()
        if not raw:
            self._set_status(status.READY, status.nothing_yet("polish"), revert_ms=2000)
            return
        if tone == "verbatim":
            self._polished.setPlainText(raw)
            self._settle(self._polished)
            count = len(raw.split())
            self._set_status(
                status.READY, status.polished("verbatim"), status.polished_hint(count)
            )
            return
        self._set_status(status.POLISHING, status.polishing(tone))
        if self.isVisible() and motion.enabled():
            effect = QGraphicsOpacityEffect(self._polished)
            effect.setOpacity(0.55)
            self._polished.setGraphicsEffect(effect)
        self._controller.request_polish(raw, tone)

    def _best_text(self) -> str:
        return self._polished.toPlainText().strip() or self._raw.toPlainText().strip()

    def _copy(self) -> None:
        text = self._best_text()
        if not text:
            self._set_status(status.READY, status.nothing_yet("copy"), revert_ms=2000)
            return
        QGuiApplication.clipboard().setText(text)
        self._set_status(status.READY, status.copied(len(text.split())), revert_ms=2000)
        self._copy_btn.setText(status.COPIED)
        QTimer.singleShot(1200, lambda: self._copy_btn.setText(status.COPY))

    def _insert(self) -> None:
        text = self._best_text()
        if not text:
            self._set_status(status.READY, status.nothing_yet("insert"), revert_ms=2000)
            return
        self._controller.request_inject(text)
        self._set_status(status.INSERTING, status.inserting())

    def _undo_take(self) -> None:
        restored = self._draft.undo()
        if restored is None:
            return
        self._raw.setPlainText(restored)
        self._raw.moveCursor(QTextCursor.MoveOperation.End)
        self._undo_btn.setVisible(self._draft.can_undo)
        self._show_ready()

    def _clear(self) -> None:
        self._draft.clear()
        self._raw.clear()
        self._polished.clear()
        self._undo_btn.hide()
        self._show_ready()
