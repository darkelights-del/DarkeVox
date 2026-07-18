"""QPainter-drawn icons. No binary image assets live in this repo."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from darkevox.ui.theme import TOKENS


def tray_icon(recording: bool = False) -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48):
        icon.addPixmap(_render_mic(size, recording))
    return icon


def _render_mic(size: int, recording: bool) -> QPixmap:
    """The DarkeVox mark: an original voice-wave, not an emoji mic.

    Five rounded bars on a deep-blue squircle; the recording state deepens
    the ground and lifts the wave. Drawn from the palette, never from
    glyph fonts.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    background = QColor(TOKENS["blue_500" if recording else "blue_400"])
    radius = size * 0.30
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    _draw_mic_glyph(painter, size)
    painter.end()
    return pixmap


# Bar heights of the voice-wave, as fractions of the mark's height.
_WAVE = (0.26, 0.46, 0.62, 0.38, 0.22)


def _draw_mic_glyph(painter: QPainter, size: int) -> None:
    unit = size / 16.0
    foreground = QColor(TOKENS["cream_50"])
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(foreground)
    bar_w = 1.6 * unit
    gap = 0.9 * unit
    total = len(_WAVE) * bar_w + (len(_WAVE) - 1) * gap
    x = (size - total) / 2
    mid = size / 2
    for fraction in _WAVE:
        bar_h = fraction * size
        painter.drawRoundedRect(
            QRectF(x, mid - bar_h / 2, bar_w, bar_h), bar_w / 2, bar_w / 2
        )
        x += bar_w + gap
