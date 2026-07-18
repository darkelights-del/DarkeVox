"""The status pill: frameless, always on top, never takes focus or clicks.

Spec lives in darkevox-ui-style (Components > HUD). States: listening
(pulsing blue), transcribing (steady blue), polishing (honey), done
(word-count flash), error (clay, stays 4 s). A sage "grounded" badge
appends when polish used retrieved context.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget

from darkevox.ui.theme import SHADOW_BLUR, SHADOW_DY, SHADOW_RGBA, TOKENS

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
_MARGIN = 12  # room for the drop shadow around the pill


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
        self._font = QFont()
        self._font.setPixelSize(13)
        self._badge_font = QFont()
        self._badge_font.setPixelSize(11)

        self._pulse = QVariantAnimation(self)
        self._pulse.setDuration(1200)
        self._pulse.setStartValue(0.55)
        self._pulse.setKeyValueAt(0.5, 1.0)
        self._pulse.setEndValue(0.55)
        self._pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse.setLoopCount(-1)
        self._pulse.valueChanged.connect(self._on_pulse)

        # The spec's 250 ms fade for the pill appearing and leaving.
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(250)
        self._fade.finished.connect(self._after_fade)

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
        self._state = state
        self._label = label
        self._grounded = grounded
        if state == "listening":
            if self._pulse.state() != QVariantAnimation.State.Running:
                self._pulse.start()
        else:
            self._pulse.stop()
            self._dot_opacity = 1.0
        self._place()
        self._hide_timer.stop()
        if auto_hide_ms is not None:
            self._hide_timer.start(auto_hide_ms)
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self._start_fade(1.0)
        else:
            self._fade.stop()
            self.setWindowOpacity(1.0)
        self.update()

    def _start_fade(self, end: float) -> None:
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(end)
        self._fade.start()

    def _fade_out(self) -> None:
        if self.isVisible():
            self._start_fade(0.0)

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

    def _on_pulse(self, value: float) -> None:
        self._dot_opacity = float(value)
        self.update()

    def _content_width(self) -> int:
        width = _PAD + _DOT + _GAP + QFontMetrics(self._font).horizontalAdvance(self._label)
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
        width = self._content_width() + 2 * _MARGIN
        height = _HEIGHT + 2 * _MARGIN
        x = available.center().x() - width // 2
        y = available.bottom() - height - 8 + _MARGIN
        self.setGeometry(x, y, width, height)

    def paintEvent(self, event: object) -> None:  # Qt override, camelCase required
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pill = self.rect().adjusted(_MARGIN, _MARGIN, -_MARGIN, -_MARGIN)
        painter.setPen(QPen(QColor(TOKENS["cream_200"]), 1))
        painter.setBrush(QColor(TOKENS["cream_50"]))
        painter.drawRoundedRect(pill, _HEIGHT / 2, _HEIGHT / 2)

        dot_color = QColor(TOKENS[_STATE_DOTS.get(self._state, "blue_300")])
        dot_color.setAlphaF(self._dot_opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot_color)
        dot_x = pill.left() + _PAD
        dot_y = pill.center().y() - _DOT // 2 + 1
        painter.drawEllipse(dot_x, dot_y, _DOT, _DOT)

        painter.setFont(self._font)
        painter.setPen(QColor(TOKENS["ink_900"]))
        text_x = dot_x + _DOT + _GAP
        painter.drawText(
            text_x,
            pill.top(),
            pill.width(),
            pill.height(),
            Qt.AlignmentFlag.AlignVCenter,
            self._label,
        )

        if self._grounded:
            badge_w = self._badge_width()
            badge_x = pill.right() - _PAD - badge_w
            badge_h = 18
            badge_y = pill.center().y() - badge_h // 2 + 1
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(TOKENS["sage_300"]))
            painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, badge_h / 2, badge_h / 2)
            painter.setFont(self._badge_font)
            painter.setPen(QColor(TOKENS["ink_900"]))
            painter.drawText(
                badge_x,
                badge_y,
                badge_w,
                badge_h,
                Qt.AlignmentFlag.AlignCenter,
                "grounded",
            )
        painter.end()
