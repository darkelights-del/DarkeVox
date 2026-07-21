"""The floating dictation panel: live transcript, editable polish, mouse PTT.

A frameless always-on-top card that collapses into a mic pill; the two
states morph into each other (240 ms out / 180 ms back, OutQuart) instead
of teleporting. The mic is the meter: its wave bars ride the live input
level, and a pulse ring breathes while recording. Voice BUILDS on the
draft (darkevox.ui.draft) — a new take appends, never replaces, and an
accidental tap can't wipe words.

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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from darkevox.inject.focus import ForegroundTracker
from darkevox.ui import motion
from darkevox.ui.buttons import AnimatedButton
from darkevox.ui.draft import Draft
from darkevox.ui.icons import draw_mark
from darkevox.ui.interaction import DRAG_CANCEL_PX, HOLD_MS, PressHoldInterpreter
from darkevox.ui.theme import (
    DUR_PANEL_CLOSE,
    DUR_PANEL_OPEN,
    DUR_PRESS,
    DUR_RELEASE,
    DUR_SETTLE,
    PULSE_MS,
    RADIUS_CONTROL,
    SHADOW_BLUR,
    SHADOW_DY,
    SHADOW_MARGIN,
    SHADOW_RGBA,
    TOKENS,
)

_CARD_WIDTH = 380
_PILL = 56
_TONES = ("email", "message", "notes", "verbatim")

# Status dot colors share the HUD's vocabulary so every surface speaks it.
_STATE_DOTS = {
    "listening": "blue_300",
    "transcribing": "blue_400",
    "polishing": "honey_300",
    "inserted": "sage_300",
    "fallback": "honey_300",
    "error": "clay_400",
}


def _overline(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setProperty("role", "overline")
    return label


class _MicControl(QWidget):
    """Shared mouse logic and living paint state for the mic.

    Click, hold, drag; press scale, hover tint, recording pulse, and the
    live level that scales the wave bars. Loops stop whenever the widget
    hides so nothing ticks invisibly.
    """

    def __init__(self, controller: Any, draggable: bool, on_click: Any = None) -> None:
        super().__init__()
        self._controller = controller
        self._draggable = draggable
        self.recording = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._interpreter = PressHoldInterpreter(
            on_click=on_click or controller.panel_click,
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

        self._scale = 1.0
        self._level = 0.0
        self._pulse_v = 0.0
        self._scale_anim = motion.make_anim(self, DUR_PRESS, self._on_scale)
        self._level_anim = motion.make_anim(self, 150, self._on_level)
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

    def _on_scale(self, value: object) -> None:
        self._scale = float(value)  # type: ignore[arg-type]
        self.update()

    def _on_level(self, value: object) -> None:
        self._level = float(value)  # type: ignore[arg-type]
        self.update()

    def _on_pulse(self, value: object) -> None:
        self._pulse_v = float(value)  # type: ignore[arg-type]
        self.update()

    def showEvent(self, event: object) -> None:  # Qt override
        super().showEvent(event)
        self._sync_pulse()

    def hideEvent(self, event: object) -> None:  # Qt override
        self._pulse.stop()
        self._pulse_v = 0.0
        super().hideEvent(event)

    # ---- paint helpers ----

    def _paint_setup(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._scale != 1.0:
            center = self.rect().center()
            painter.translate(center)
            painter.scale(self._scale, self._scale)
            painter.translate(-center)

    def _pulse_pen(self) -> QPen | None:
        if not self.recording or self._pulse_v <= 0.01:
            return None
        color = QColor(TOKENS["blue_300"])
        color.setAlphaF(0.25 + 0.55 * self._pulse_v)
        return QPen(color, 2)

    # ---- mouse ----

    def enterEvent(self, event: object) -> None:  # Qt override
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:  # Qt override
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # Qt override
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press_pos = event.globalPosition().toPoint()
        self._drag_offset = self._press_pos - self.window().frameGeometry().topLeft()
        self._dragging = False
        self._interpreter.press()
        self._hold_timer.start()
        motion.retarget(self._scale_anim, self._scale, 0.96, DUR_PRESS)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # Qt override
        if self._press_pos is None:
            return
        pos = event.globalPosition().toPoint()
        if not self._dragging and (pos - self._press_pos).manhattanLength() > DRAG_CANCEL_PX:
            self._dragging = True
            self._hold_timer.stop()
            self._interpreter.cancel()
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            motion.retarget(self._scale_anim, self._scale, 1.0, DUR_RELEASE)
        if self._dragging and self._draggable and self._drag_offset is not None:
            # Locked 1:1 to the pointer; easing during drag feels detached.
            self.window().move(pos - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # Qt override
        self._hold_timer.stop()
        was_drag = self._dragging
        if not self._dragging:
            self._interpreter.release()
        self._press_pos = None
        self._dragging = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        motion.retarget(self._scale_anim, self._scale, 1.0, DUR_RELEASE)
        if was_drag and self._draggable:
            window = self.window()
            if isinstance(window, Panel):
                window.settle_on_screen()


class _Pill(_MicControl):
    """Collapsed state: the whole widget is the mic. Double-click expands.

    A single click commits only after the double-click window closes, so
    expanding the panel never toggles a session by accident. A state dot
    at the top edge mirrors the HUD's colors; the tooltip carries the
    live status text.
    """

    def __init__(self, controller: Any, on_expand: Any) -> None:
        self._click_timer = QTimer()
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(QGuiApplication.styleHints().mouseDoubleClickInterval())
        super().__init__(controller, draggable=True, on_click=self._click_timer.start)
        self._click_timer.setParent(self)
        self._click_timer.timeout.connect(controller.panel_click)
        self._on_expand = on_expand
        self._dot: str | None = None
        self.setFixedSize(_PILL, _PILL)
        self.setToolTip("Click: start/stop. Hold: push to talk. Double-click: open.")

    def set_dot(self, token: str | None) -> None:
        self._dot = token
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # Qt override
        self._click_timer.stop()
        self._interpreter.cancel()
        self._on_expand()

    def paintEvent(self, event: QPaintEvent) -> None:  # Qt override
        painter = QPainter(self)
        self._paint_setup(painter)
        level = self._level if self.recording else None
        draw_mark(painter, _PILL, recording=self.recording, level=level)
        pulse = self._pulse_pen()
        if pulse is not None:
            painter.setPen(pulse)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            radius = _PILL * 0.30
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)
        if self._dot is not None:
            painter.setPen(QPen(QColor(TOKENS["cream_50"]), 1.5))
            painter.setBrush(QColor(TOKENS[self._dot]))
            painter.drawEllipse(self.width() - 13, 1, 11, 11)
        painter.end()


class _MicButton(_MicControl):
    """Expanded state: a round mic button inside the card."""

    def __init__(self, controller: Any) -> None:
        super().__init__(controller, draggable=False)
        self.setFixedSize(_PILL, _PILL)
        self._bg = QColor(TOKENS["blue_400"])
        self._bg_anim = motion.make_anim(self, 150, self._on_bg)

    def _target_bg(self) -> QColor:
        if self.recording:
            return QColor(TOKENS["blue_500"])
        if self.underMouse():
            return QColor(TOKENS["blue_300"])
        return QColor(TOKENS["blue_400"])

    def _retint(self) -> None:
        motion.retarget(self._bg_anim, QColor(self._bg), self._target_bg(), 150)

    def _on_bg(self, value: object) -> None:
        if isinstance(value, QColor):
            self._bg = value
            self.update()

    def set_recording(self, recording: bool) -> None:
        super().set_recording(recording)
        self._retint()

    def enterEvent(self, event: object) -> None:  # Qt override
        self._retint()
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:  # Qt override
        self._retint()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # Qt override
        painter = QPainter(self)
        self._paint_setup(painter)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg)
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        from darkevox.ui.icons import _draw_mic_glyph

        level = self._level if self.recording else None
        _draw_mic_glyph(painter, self.width(), level=level)
        pulse = self._pulse_pen()
        if pulse is not None:
            painter.setPen(pulse)
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
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)
        self._pill = _Pill(controller, on_expand=self.show_expanded)
        self._card = self._build_card()
        self._stack.addWidget(self._wrap_pill())
        self._stack.addWidget(self._card)

        # With every container genuinely transparent, this one shadow
        # silhouettes the actual card/pill shape, not a square.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(SHADOW_BLUR)
        shadow.setOffset(0, SHADOW_DY)
        shadow.setColor(QColor(*SHADOW_RGBA))
        self._stack.setGraphicsEffect(shadow)

        self._geo_anim = QPropertyAnimation(self, b"geometry", self)
        self._geo_anim.setEasingCurve(motion.EASE_OUT)
        self._geo_anim.finished.connect(self._on_morph_done)
        self._morph_target: str | None = None

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

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._on_escape)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._insert)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self._copy)

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
        box.setContentsMargins(20, 16, 20, 20)
        box.setSpacing(8)

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
        collapse.clicked.connect(self.show_pill)
        header_box.addWidget(collapse)
        box.addWidget(header)

        mic_row = QHBoxLayout()
        mic_row.setSpacing(12)
        self._mic = _MicButton(self._controller)
        mic_row.addWidget(self._mic)
        status_col = QVBoxLayout()
        status_col.setSpacing(2)
        status_col.addStretch(1)
        self._status = QLabel("")
        self._status.setProperty("role", "body")
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
        seg_box.setContentsMargins(3, 3, 3, 3)
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

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self._copy_btn = AnimatedButton("Copy", "secondary")
        self._copy_btn.clicked.connect(self._copy)
        action_row.addWidget(self._copy_btn)
        clear = AnimatedButton("Clear", "quiet")
        clear.clicked.connect(self._clear)
        action_row.addWidget(clear)
        action_row.addStretch(1)
        insert = AnimatedButton("Insert", "primary")
        insert.clicked.connect(self._insert)
        action_row.addWidget(insert)
        box.addLayout(action_row)
        return card

    # ---- geometry and morphing ----

    def _rect_for(self, expanded: bool) -> QRect:
        if expanded:
            hint = self._card.sizeHint()
            size = (hint.width() + 2 * SHADOW_MARGIN, hint.height() + 2 * SHADOW_MARGIN)
        else:
            size = (_PILL + 2 * SHADOW_MARGIN, _PILL + 2 * SHADOW_MARGIN)
        current = self.frameGeometry()
        screen = QApplication.primaryScreen()
        area = screen.availableGeometry() if screen is not None else QRect(0, 0, 1920, 1080)
        # Pin the corner nearest the screen edges so the card emerges from
        # where the pill sits instead of jumping across it.
        x = current.x()
        y = current.y()
        if current.center().x() > area.center().x():
            x = current.right() - size[0]
        if current.center().y() > area.center().y():
            y = current.bottom() - size[1]
        rect = QRect(x, y, size[0], size[1])
        margin = SHADOW_MARGIN
        rect.moveLeft(
            max(area.left() - margin, min(rect.left(), area.right() - rect.width() + margin))
        )
        rect.moveTop(
            max(area.top() - margin, min(rect.top(), area.bottom() - rect.height() + margin))
        )
        return rect

    def _free_size(self) -> None:
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16_777_215, 16_777_215)

    def show_expanded(self) -> None:
        was_visible = self.isVisible()
        collapsed = self.collapsed()
        self._free_size()
        self._stack.setCurrentIndex(1)
        target = self._rect_for(expanded=True)
        if was_visible and collapsed and motion.enabled():
            self._morph_target = "card"
            self._fade_card(0.0, 1.0)
            self._geo_anim.stop()
            self._geo_anim.setDuration(motion.duration(DUR_PANEL_OPEN))
            self._geo_anim.setStartValue(self.geometry())
            self._geo_anim.setEndValue(target)
            self._geo_anim.start()
        else:
            self.setGeometry(target)
        self.show()
        self._poll.start()
        self.visibility_changed.emit(True)

    def show_pill(self) -> None:
        was_visible = self.isVisible()
        expanded = not self.collapsed()
        target = self._rect_for(expanded=False)
        if was_visible and expanded and motion.enabled():
            self._morph_target = "pill"
            self._fade_card(1.0, 0.0)
            self._free_size()
            self._geo_anim.stop()
            self._geo_anim.setDuration(motion.duration(DUR_PANEL_CLOSE))
            self._geo_anim.setStartValue(self.geometry())
            self._geo_anim.setEndValue(target)
            self._geo_anim.start()
        else:
            self._stack.setCurrentIndex(0)
            self.setFixedSize(target.size())
            self.setGeometry(target)
        self.show()
        self._poll.start()
        self.visibility_changed.emit(True)

    def _on_morph_done(self) -> None:
        if self._morph_target == "pill":
            self._stack.setCurrentIndex(0)
            self.setFixedSize(self._rect_for(expanded=False).size())
            self._clear_card_fade()
        elif self._morph_target == "card":
            self._clear_card_fade()
        self._morph_target = None

    def _fade_card(self, start: float, end: float) -> None:
        effect = QGraphicsOpacityEffect(self._card)
        effect.setOpacity(start)
        self._card.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", effect)
        anim.setDuration(motion.duration(150 if end > start else 80))
        anim.setEasingCurve(motion.EASE_OUT_SOFT)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _clear_card_fade(self) -> None:
        self._card.setGraphicsEffect(None)

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
        self._morph_target = None
        self._geo_anim.stop()
        self._geo_anim.setDuration(motion.duration(DUR_SETTLE))
        self._geo_anim.setStartValue(self.geometry())
        self._geo_anim.setEndValue(target)
        self._geo_anim.start()

    def collapsed(self) -> bool:
        return self._stack.currentIndex() == 0 or self._morph_target == "pill"

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.close_to_tray()
        elif self.collapsed():
            self.show_pill()
        else:
            self.show_expanded()

    def close_to_tray(self) -> None:
        self.hide()
        self.visibility_changed.emit(False)

    def hideEvent(self, event: object) -> None:  # Qt override
        self._poll.stop()
        super().hideEvent(event)

    def contextMenuEvent(self, event: object) -> None:  # Qt override
        menu = QMenu(self)
        menu.addAction("Settings", self.settings_requested.emit)
        menu.addAction("Hide DarkeVox (tray keeps running)", self.close_to_tray)
        menu.exec(event.globalPos())

    def _on_escape(self) -> None:
        if not self.collapsed():
            self.show_pill()

    def _poll_foreground(self) -> None:
        self._tracker.poll({int(self.winId())})

    # ---- status machine ----

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
        error = state == "error"
        self._status.setProperty("role", "error" if error else "body")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._pill.set_dot(_STATE_DOTS.get(state))
        tooltip = title if not sub else f"{title} — {sub}"
        self._pill.setToolTip(tooltip)
        if revert_ms is not None:
            self._revert_timer.start(revert_ms)

    def _show_ready(self) -> None:
        words = len(self._raw.toPlainText().split())
        if words:
            self._set_status("ready", f"Ready — {words} words in the draft")
        elif self._hotkey_hint:
            self._set_status("ready", "Ready", f"hold {self._hotkey_hint} or click the mic")
        else:
            self._set_status("ready", "Ready", "click the mic, or hold it to talk")

    def _tick_listening(self) -> None:
        self._listen_seconds += 1
        minutes, seconds = divmod(self._listen_seconds, 60)
        self._set_status("listening", f"Listening — {minutes}:{seconds:02d}")

    # ---- controller-facing slots (wired in app.py) ----

    def set_recording(self, recording: bool) -> None:
        self._live = recording
        self._pill.set_recording(recording)
        self._mic.set_recording(recording)
        self._raw.setReadOnly(recording)
        if recording:
            self._draft.begin_session(self._raw.toPlainText())
            self._listen_seconds = 0
            self._listen_timer.start()
            self._set_status("listening", "Listening — 0:00")
        else:
            self._listen_timer.stop()
            self._set_status("transcribing", "Transcribing…")

    def set_level(self, level: float) -> None:
        self._pill.set_level(level)
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
                self._set_status("ready", "No speech heard", "try again, closer to the mic")
            return
        self._settle(self._raw)
        self._polish_as(self._tone)

    def on_polish_ready(self, text: str, tone: str, fell_back: bool) -> None:
        self._polished.setGraphicsEffect(None)
        self._polished.setPlainText(text)
        self._settle(self._polished)
        if fell_back:
            note = self._pending_note or "check the polish backend, then click a tone to retry"
            self._set_status("fallback", "Polish unavailable — showing raw", note)
        else:
            words = len(text.split())
            label = "as spoken" if tone == "verbatim" else tone
            self._set_status("ready", f"Polished — {label}", f"{words} words · Insert or Copy")
        self._pending_note = ""

    def on_notice(self, note: str) -> None:
        self._pending_note = note

    def on_error(self, message: str) -> None:
        self._set_status("error", message)

    def on_inserted(self, words: int) -> None:
        self._set_status("inserted", f"Inserted — {words} words", revert_ms=2000)

    def _settle(self, field: QPlainTextEdit) -> None:
        """New text lands with a short opacity settle instead of a teleport."""
        if not self.isVisible() or not motion.enabled():
            return
        effect = QGraphicsOpacityEffect(field)
        effect.setOpacity(0.55)
        field.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", effect)
        anim.setDuration(motion.duration(180))
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
            self._set_status("ready", "Nothing to polish yet", revert_ms=2000)
            return
        if tone == "verbatim":
            self._polished.setPlainText(raw)
            self._settle(self._polished)
            self._set_status("ready", "As spoken", f"{len(raw.split())} words · Insert or Copy")
            return
        self._set_status("polishing", f"Polishing — {tone}…")
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
            self._set_status("ready", "Nothing to copy yet", revert_ms=2000)
            return
        QGuiApplication.clipboard().setText(text)
        words = len(text.split())
        self._set_status("ready", f"Copied — {words} words", revert_ms=2000)
        self._copy_btn.setText("Copied")
        QTimer.singleShot(1200, lambda: self._copy_btn.setText("Copy"))

    def _insert(self) -> None:
        text = self._best_text()
        if not text:
            self._set_status("ready", "Nothing to insert yet", revert_ms=2000)
            return
        self._controller.request_inject(text)
        self._set_status("polishing", "Inserting…")

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
