"""The status pill: frameless, always on top, never takes focus or clicks.

Spec lives in darkevox-ui-style (Components > HUD). States: listening
(pulsing blue), transcribing (steady blue), polishing (honey), done
(word-count flash with a one-shot dot swell), error (clay, stays 4 s).
A sage "grounded" badge appends when polish used retrieved context.

Timing: this pill rides every hotkey dictation, so it enters near-instantly
(90 ms) and leaves with a short fade (150 ms) — immediacy is the polish.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget

from darkevox.ui import motion
from darkevox.ui.theme import (
    DUR_ENTER,
    DUR_EXIT,
    DUR_SWELL,
    FONT_BODY_PX,
    FONT_CAPTION_PX,
    PULSE_MS,
    SHADOW_BLUR,
    SHADOW_DY,
    SHADOW_MARGIN,
    SHADOW_RGBA,
    TOKENS,
)

_STATE_DOTS = {
    "listening": "blue_300",
    "transcribing": "blue_400",
    "polishing": "honey_300",
    "done": "sage_300",
    "error": "clay_400",
}

_HEIGHT = 36
_PAD = 16
_DOT = 8
_GAP = 8
_BADGE_H = 20
_MAX_LABEL_PX = 320


class Hud(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(SHADOW_BLUR)
        shadow.setOffset(0, SHADOW_DY)
        shadow.setColor(QColor(*SHADOW_RGBA))
        self.setGraphicsEffect(shadow)

        self._state = "listening"
        self._label = ""
        self._grounded = False
        self._dot_opacity = 1.0
        self._dot_swell = 1.0
        self._font = QFont()
        self._font.setPixelSize(FONT_BODY_PX)
        self._badge_font = QFont()
        self._badge_font.setPixelSize(FONT_CAPTION_PX)

        self._pulse = QVariantAnimation(self)
        self._pulse.setDuration(PULSE_MS)
        self._pulse.setStartValue(0.55)
        self._pulse.setKeyValueAt(0.5, 1.0)
        self._pulse.setEndValue(0.55)
        self._pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse.setLoopCount(-1)
        self._pulse.valueChanged.connect(self._on_pulse)

        # Near-instant in (the user pressed a key; confirmation must not
        # dawdle), short fade out. Asymmetric on purpose.
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setEasingCurve(motion.EASE_OUT_SOFT)
        self._fade.finished.connect(self._after_fade)

        # Label changes while visible re-center with a short glide instead
        # of a one-frame jump.
        self._geo = QPropertyAnimation(self, b"geometry", self)
        self._geo.setDuration(motion.duration(120))
        self._geo.setEasingCurve(motion.EASE_OUT)

        self._swell = QVariantAnimation(self)
        self._swell.setDuration(motion.duration(DUR_SWELL))
        self._swell.setStartValue(1.35)
        self._swell.setEndValue(1.0)
        self._swell.setEasingCurve(motion.EASE_OUT)
        self._swell.valueChanged.connect(self._on_swell)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    def show_state(
        self,
        state: str,
        label: str,
        grounded: bool = False,
        auto_hide_ms: int | None = None,
    ) -> None:
        entered_done = state == "done" and self._state != "done"
        self._state = state
        self._label = label
        self._grounded = grounded
        if state == "listening":
            if self._pulse.state() != QVariantAnimation.State.Running and motion.enabled():
                self._pulse.start()
        else:
            self._pulse.stop()
            self._dot_opacity = 1.0
        if entered_done and motion.enabled():
            # The session's payoff: one swell, no loop, no bounce.
            self._swell.stop()
            self._dot_swell = 1.35
            self._swell.start()
        self._place()
        self._hide_timer.stop()
        if auto_hide_ms is not None:
            self._hide_timer.start(auto_hide_ms)
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self._start_fade(1.0, DUR_ENTER)
        else:
            self._fade.stop()
            self.setWindowOpacity(1.0)
        self.update()

    def _start_fade(self, end: float, ms: int) -> None:
        self._fade.stop()
        self._fade.setDuration(motion.duration(ms))
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(end)
        self._fade.start()

    def _fade_out(self) -> None:
        if self.isVisible():
            self._start_fade(0.0, DUR_EXIT)

    def _after_fade(self) -> None:
        if float(self._fade.endValue()) == 0.0:
            self.hide()
            self.setWindowOpacity(1.0)

    def done(self, words: int) -> None:
        label = f"{words} word" if words == 1 else f"{words} words"
        self.show_state("done", label, auto_hide_ms=1600)

    def error(self, message: str) -> None:
        self.show_state("error", message, auto_hide_ms=4000)

    def dismiss(self) -> None:
        self._pulse.stop()
        self._hide_timer.stop()
        self._fade.stop()
        self.hide()
        self.setWindowOpacity(1.0)

    def hideEvent(self, event: object) -> None:  # Qt override
        # Guarantee: no looping animation ever ticks on a hidden window.
        self._pulse.stop()
        super().hideEvent(event)

    def _on_pulse(self, value: float) -> None:
        self._dot_opacity = float(value)
        self.update()

    def _on_swell(self, value: object) -> None:
        self._dot_swell = float(value)  # type: ignore[arg-type]
        self.update()

    def _elided_label(self) -> str:
        return QFontMetrics(self._font).elidedText(
            self._label, Qt.TextElideMode.ElideRight, _MAX_LABEL_PX
        )

    def _content_width(self) -> int:
        label_px = min(
            QFontMetrics(self._font).horizontalAdvance(self._label), _MAX_LABEL_PX
        )
        width = _PAD + _DOT + _GAP + label_px
        if self._grounded:
            width += _GAP + self._badge_width()
        return width + _PAD

    def _badge_width(self) -> int:
        return QFontMetrics(self._badge_font).horizontalAdvance("grounded") + 12

    def _place(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = self._content_width() + 2 * SHADOW_MARGIN
        height = _HEIGHT + 2 * SHADOW_MARGIN
        x = available.center().x() - width // 2
        y = available.bottom() - height - 8 + SHADOW_MARGIN
        from PySide6.QtCore import QRect

        target = QRect(x, y, width, height)
        if self.isVisible() and motion.enabled() and self.geometry() != target:
            self._geo.stop()
            self._geo.setStartValue(self.geometry())
            self._geo.setEndValue(target)
            self._geo.start()
        else:
            self.setGeometry(target)

    def paintEvent(self, event: object) -> None:  # Qt override, camelCase required
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pill = self.rect().adjusted(
            SHADOW_MARGIN, SHADOW_MARGIN, -SHADOW_MARGIN, -SHADOW_MARGIN
        )
        painter.setPen(QPen(QColor(TOKENS["cream_200"]), 1))
        painter.setBrush(QColor(TOKENS["cream_50"]))
        painter.drawRoundedRect(pill, _HEIGHT / 2, _HEIGHT / 2)

        dot_color = QColor(TOKENS[_STATE_DOTS.get(self._state, "blue_300")])
        dot_color.setAlphaF(self._dot_opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot_color)
        dot = _DOT * self._dot_swell
        dot_x = pill.left() + _PAD + (_DOT - dot) / 2
        dot_y = pill.center().y() - dot / 2 + 1
        painter.drawEllipse(int(dot_x), int(dot_y), int(dot), int(dot))

        painter.setFont(self._font)
        painter.setPen(QColor(TOKENS["ink_900"]))
        text_x = pill.left() + _PAD + _DOT + _GAP
        painter.drawText(
            text_x,
            pill.top(),
            pill.width(),
            pill.height(),
            Qt.AlignmentFlag.AlignVCenter,
            self._elided_label(),
        )

        if self._grounded:
            badge_w = self._badge_width()
            badge_x = pill.right() - _PAD - badge_w
            badge_y = pill.center().y() - _BADGE_H // 2 + 1
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(TOKENS["sage_300"]))
            painter.drawRoundedRect(
                badge_x, badge_y, badge_w, _BADGE_H, _BADGE_H / 2, _BADGE_H / 2
            )
            painter.setFont(self._badge_font)
            painter.setPen(QColor(TOKENS["ink_900"]))
            painter.drawText(
                badge_x,
                badge_y,
                badge_w,
                _BADGE_H,
                Qt.AlignmentFlag.AlignCenter,
                "grounded",
            )
        painter.end()
