"""QPainter-drawn icons. No binary image assets live in this repo."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from darkevox.ui.theme import TOKENS


def tray_icon(recording: bool = False) -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48):
        icon.addPixmap(_render_mic(size, recording))
    return icon


def _render_mic(size: int, recording: bool) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    background = QColor(TOKENS["blue_500" if recording else "blue_300"])
    radius = size * 0.28
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    _draw_mic_glyph(painter, size)
    painter.end()
    return pixmap


def _draw_mic_glyph(painter: QPainter, size: int) -> None:
    # Glyph drawn on a 16-unit design grid, scaled to the target size.
    unit = size / 16.0
    foreground = QColor(TOKENS["cream_50"])
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(foreground)
    capsule = QRectF(6.4 * unit, 3.0 * unit, 3.2 * unit, 6.2 * unit)
    painter.drawRoundedRect(capsule, 1.6 * unit, 1.6 * unit)
    pen = QPen(foreground, max(1.0, 1.2 * unit))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cradle = QRectF(4.6 * unit, 4.4 * unit, 6.8 * unit, 6.8 * unit)
    painter.drawArc(cradle, 200 * 16, 140 * 16)
    painter.drawLine(QPointF(8.0 * unit, 11.2 * unit), QPointF(8.0 * unit, 13.0 * unit))
