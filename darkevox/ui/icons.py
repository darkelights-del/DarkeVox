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
    unit = size / 16.0
    radius = size * 0.30
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    # A hairline ring in the deeper blue keeps the mark defined on light
    # taskbars, where a flat pastel square dissolves into the background.
    ring = QColor(TOKENS["blue_500"])
    ring.setAlpha(90 if not recording else 0)
    painter.setPen(QPen(ring, max(1.0, 0.5 * unit)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    inset = 0.4 * unit
    painter.drawRoundedRect(
        QRectF(inset, inset, size - 2 * inset, size - 2 * inset),
        radius - inset,
        radius - inset,
    )
    _draw_mic_glyph(painter, size)
    painter.end()
    return pixmap


def _draw_mic_glyph(painter: QPainter, size: int) -> None:
    # Glyph drawn on a 16-unit design grid, scaled to the target size.
    unit = size / 16.0
    foreground = QColor(TOKENS["cream_50"])
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(foreground)
    capsule = QRectF(6.25 * unit, 2.8 * unit, 3.5 * unit, 6.6 * unit)
    painter.drawRoundedRect(capsule, 1.75 * unit, 1.75 * unit)
    pen = QPen(foreground, max(1.0, 1.25 * unit))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cradle = QRectF(4.3 * unit, 4.5 * unit, 7.4 * unit, 7.4 * unit)
    painter.drawArc(cradle, 200 * 16, 140 * 16)
    painter.drawLine(QPointF(8.0 * unit, 11.9 * unit), QPointF(8.0 * unit, 13.4 * unit))
