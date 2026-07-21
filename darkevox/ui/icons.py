"""QPainter-drawn icons. No binary image assets live in this repo.

The few glyphs QSS needs as images (combo arrow, checkmark, spin chevrons)
are rendered here at startup into the app's config directory and referenced
by path; they are generated artifacts, never checked in.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from darkevox.ui.theme import TOKENS


def tray_icon(recording: bool = False) -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48):
        icon.addPixmap(_render_mic(size, recording))
    return icon


def _render_mic(size: int, recording: bool) -> QPixmap:
    """The DarkeVox mark: an original voice-wave, not an emoji mic.

    Five rounded bars on a deep-blue squircle. Recording deepens the ground
    and adds a clay dot badge so the state reads at 16 px on a taskbar.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_mark(painter, size, recording=recording)
    if recording:
        badge = size * 0.28
        painter.setPen(QPen(QColor(TOKENS["cream_50"]), max(1.0, size / 24)))
        painter.setBrush(QColor(TOKENS["clay_400"]))
        painter.drawEllipse(QRectF(size - badge - 1, 1, badge, badge))
    painter.end()
    return pixmap


# Bar heights of the voice-wave, as fractions of the mark's height.
_WAVE = (0.26, 0.46, 0.62, 0.38, 0.22)


def draw_mark(
    painter: QPainter,
    size: int,
    recording: bool = False,
    level: float | None = None,
) -> None:
    """Draw the squircle ground plus the wave glyph.

    `level` (0..1) scales the bars live while recording, so the mark itself
    is the mic meter; None paints the resting logo.
    """
    background = QColor(TOKENS["blue_500" if recording else "blue_400"])
    radius = size * 0.30
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    _draw_mic_glyph(painter, size, level=level)


def _draw_mic_glyph(painter: QPainter, size: int, level: float | None = None) -> None:
    unit = size / 16.0
    foreground = QColor(TOKENS["cream_50"])
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(foreground)
    bar_w = 1.6 * unit
    gap = 0.9 * unit
    total = len(_WAVE) * bar_w + (len(_WAVE) - 1) * gap
    x = (size - total) / 2
    mid = size / 2
    scale = 1.0 if level is None else 0.35 + 0.65 * max(0.0, min(1.0, level))
    for fraction in _WAVE:
        bar_h = max(bar_w, fraction * size * scale)
        painter.drawRoundedRect(
            QRectF(x, mid - bar_h / 2, bar_w, bar_h), bar_w / 2, bar_w / 2
        )
        x += bar_w + gap


def dot_pixmap(color_token: str, size: int = 10) -> QPixmap:
    """A small status dot, used by the tray menu status row."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(TOKENS[color_token]))
    painter.drawEllipse(QRectF(0.5, 0.5, size - 1, size - 1))
    painter.end()
    return pixmap


def _chevron(size: int, ink: str, down: bool) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(ink), size / 6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    w, m = size, size * 0.28
    if down:
        path = [QPointF(m, w * 0.38), QPointF(w / 2, w * 0.66), QPointF(w - m, w * 0.38)]
    else:
        path = [QPointF(m, w * 0.62), QPointF(w / 2, w * 0.34), QPointF(w - m, w * 0.62)]
    painter.drawPolyline(path)
    painter.end()
    return pixmap


def _checkmark(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(TOKENS["cream_50"]), size / 6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    path = QPainterPath(QPointF(size * 0.22, size * 0.52))
    path.lineTo(size * 0.42, size * 0.72)
    path.lineTo(size * 0.78, size * 0.30)
    painter.drawPath(path)
    painter.end()
    return pixmap


def ensure_style_assets(directory: Path) -> dict[str, str]:
    """Render the QSS-referenced glyphs into `directory`, returning name->path.

    Regenerated every launch (cheap, and stays in sync with token changes).
    Failures degrade to an empty dict: the QSS simply omits those images.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        assets = {
            "combo_arrow": _chevron(20, TOKENS["ink_600"], down=True),
            "spin_up": _chevron(16, TOKENS["ink_600"], down=False),
            "spin_down": _chevron(16, TOKENS["ink_600"], down=True),
            "check": _checkmark(16),
        }
        paths: dict[str, str] = {}
        for name, pixmap in assets.items():
            target = directory / f"{name}.png"
            if pixmap.save(str(target), "PNG"):
                paths[name] = str(target)
        return paths
    except OSError:
        return {}
