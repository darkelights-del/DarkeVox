"""AnimatedButton: the app's button, self-painted so states can tween.

QSS cannot animate, so hover/press tints there are single-frame swaps; this
class owns its painting and glides between state colors (170 ms in, 150 ms
out, 60 ms to pressed) with a 0.97 press scale. Variants: "secondary"
(default), "primary", "quiet", and "chip" (segmented tone picker).
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QPushButton

from darkevox.ui import motion
from darkevox.ui.theme import (
    DUR_HOVER,
    DUR_HOVER_OUT,
    DUR_PRESS,
    DUR_RELEASE,
    FONT_CAPTION_PX,
    RADIUS_CONTROL,
    RADIUS_SM,
    TOKENS,
)

_T = TOKENS
# variant -> (rest, hover, pressed, checked, text, checked_text, border)
_STYLES: dict[str, tuple[str, str, str, str, str, str, str | None]] = {
    "secondary": (
        _T["cream_50"], _T["cream_200"], _T["blue_100"], _T["blue_100"],
        _T["ink_900"], _T["ink_900"], _T["cream_200"],
    ),
    "primary": (
        _T["blue_600"], _T["blue_650"], _T["blue_700"], _T["blue_600"],
        _T["cream_50"], _T["cream_50"], None,
    ),
    "quiet": (
        "#00000000", _T["cream_200"], _T["blue_100"], _T["blue_100"],
        _T["ink_600"], _T["ink_900"], None,
    ),
    "chip": (
        "#00000000", "#66FFFDF8", _T["blue_100"], _T["cream_50"],
        _T["ink_600"], _T["ink_900"], None,
    ),
}


class AnimatedButton(QPushButton):
    def __init__(self, text: str, variant: str = "secondary") -> None:
        super().__init__(text)
        self._variant = variant if variant in _STYLES else "secondary"
        self.setProperty("variant", variant)  # keeps QSS selectors harmless
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._bg = QColor(_STYLES[self._variant][0])
        self._scale = 1.0
        self._bg_anim = motion.make_anim(self, DUR_HOVER, self._on_bg)
        self._scale_anim = motion.make_anim(self, DUR_PRESS, self._on_scale)
        if variant == "primary":
            font = QFont(self.font())
            font.setWeight(QFont.Weight.DemiBold)
            self.setFont(font)
        if variant in ("quiet", "chip"):
            font = QFont(self.font())
            font.setPixelSize(FONT_CAPTION_PX)
            self.setFont(font)
        self.toggled.connect(lambda _c: self._retint(DUR_HOVER_OUT))

    # ---- state -> colors ----

    def _colors(self) -> tuple[str, str, str, str, str, str, str | None]:
        return _STYLES[self._variant]

    def _target_bg(self) -> QColor:
        rest, hover, pressed, checked, *_ = self._colors()
        if not self.isEnabled():
            return QColor(_T["blue_200"] if self._variant == "primary" else rest)
        if self.isDown():
            return QColor(pressed)
        if self.isChecked():
            return QColor(checked)
        if self.underMouse():
            return QColor(hover)
        return QColor(rest)

    def _text_color(self) -> QColor:
        *_, text, checked_text, _border = self._colors()
        if not self.isEnabled():
            return QColor(_T["cream_50"] if self._variant == "primary" else _T["ink_400"])
        if self.isChecked() or (self.underMouse() and self._variant in ("quiet", "chip")):
            return QColor(checked_text)
        return QColor(text)

    def _retint(self, ms: int) -> None:
        motion.retarget(self._bg_anim, QColor(self._bg), self._target_bg(), ms)

    def _on_bg(self, value: object) -> None:
        if isinstance(value, QColor):
            self._bg = value
            self.update()

    def _on_scale(self, value: object) -> None:
        self._scale = float(value)  # type: ignore[arg-type]
        self.update()

    # ---- events ----

    def enterEvent(self, event: object) -> None:  # Qt override
        self._retint(DUR_HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:  # Qt override
        self._retint(DUR_HOVER_OUT)
        super().leaveEvent(event)

    def mousePressEvent(self, event: object) -> None:  # Qt override
        super().mousePressEvent(event)
        self._retint(60)
        motion.retarget(self._scale_anim, self._scale, 0.97, DUR_PRESS)

    def mouseReleaseEvent(self, event: object) -> None:  # Qt override
        super().mouseReleaseEvent(event)
        self._retint(DUR_HOVER_OUT)
        motion.retarget(self._scale_anim, self._scale, 1.0, DUR_RELEASE)

    def changeEvent(self, event: object) -> None:  # Qt override (enabled flips)
        super().changeEvent(event)
        self._bg = self._target_bg()
        self.update()

    # ---- painting ----

    def paintEvent(self, event: object) -> None:  # Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self._scale != 1.0:
            center = rect.center()
            painter.translate(center)
            painter.scale(self._scale, self._scale)
            painter.translate(-center)
        *_, border = self._colors()
        radius = RADIUS_CONTROL if self._variant != "chip" else RADIUS_SM
        if self.hasFocus():
            focus = _T["ink_900"] if self._variant == "primary" else _T["blue_500"]
            painter.setPen(QPen(QColor(focus), 1))
        elif self._variant == "chip" and self.isChecked():
            painter.setPen(QPen(QColor(_T["cream_200"]), 1))
        elif border is not None:
            painter.setPen(QPen(QColor(border), 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg)
        painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(self._text_color())
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()

    def sizeHint(self):  # Qt override
        metrics = self.fontMetrics()
        pad_x, pad_y = (12, 5) if self._variant in ("quiet", "chip") else (16, 9)
        width = metrics.horizontalAdvance(self.text()) + 2 * pad_x + 2
        height = metrics.height() + 2 * pad_y
        hint = super().sizeHint()
        hint.setWidth(max(width, 0))
        hint.setHeight(max(height, 30 if self._variant in ("quiet", "chip") else 36))
        return hint
