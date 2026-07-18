"""Design tokens and the app stylesheet.

Code mirror of .claude/skills/darkevox-ui-style; change the skill first, then
this file. Pure strings (no Qt imports) so tests run on any platform.
"""

from __future__ import annotations

from string import Template

TOKENS: dict[str, str] = {
    "cream_50": "#FFFDF8",
    "cream_100": "#FAF5EC",
    "cream_200": "#F0E7D8",
    "blue_100": "#DEEBF8",
    "blue_200": "#BCD6EF",
    "blue_300": "#97BEE5",
    "blue_400": "#6FA1D4",
    "blue_500": "#4C7FB5",
    "ink_900": "#2A3340",
    "ink_600": "#5B6675",
    "ink_400": "#939CAA",
    "sage_300": "#A9C7A0",
    "honey_300": "#EDCF9A",
    "clay_400": "#D9857E",
}

FONT_STACK = '"Segoe UI Variable", "Segoe UI", sans-serif'

# QSS has no box-shadow; floating surfaces (HUD, menus) apply the one app shadow
# via QGraphicsDropShadowEffect with these values. Large and soft reads modern;
# tight and dark reads 2010.
SHADOW_BLUR = 24
SHADOW_DY = 6
SHADOW_RGBA = (42, 51, 64, 22)

_QSS = Template(
    """
* {
    font-family: $font;
    font-size: 13px;
    color: $ink_900;
}
QWidget { background: $cream_100; }
QMenu {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item { background: transparent; padding: 6px 24px 6px 12px; border-radius: 6px; }
QMenu::item:selected { background: $blue_100; }
QMenu::item:disabled { color: $ink_600; font-size: 11px; }
QMenu::separator { height: 1px; background: $cream_200; margin: 4px 8px; }
QPushButton {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: 10px;
    padding: 9px 18px;
}
QPushButton:hover { background: $cream_200; }
QPushButton:pressed { background: $blue_100; }
QPushButton:disabled { color: $ink_400; }
QPushButton:checked { background: $blue_100; border: 1px solid $blue_400; }
QPushButton[variant="primary"] {
    background: $blue_500;
    border: none;
    color: $cream_50;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover { background: $blue_400; color: $cream_50; }
QPushButton[variant="primary"]:pressed { background: $blue_500; color: $cream_50; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background: $cream_200;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 9px;
    selection-background-color: $blue_200;
    placeholder-text-color: $ink_400;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid $blue_400;
    background: $cream_50;
}
QLineEdit[invalid="true"] { border: 1px solid $clay_400; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: 8px;
    selection-background-color: $blue_100;
    selection-color: $ink_900;
}
QFrame[role="card"] {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: 16px;
}
QFrame[role="card"] QWidget { background: transparent; }
QFrame[role="card"] QLineEdit, QFrame[role="card"] QComboBox,
QFrame[role="card"] QSpinBox, QFrame[role="card"] QDoubleSpinBox,
QFrame[role="card"] QPlainTextEdit {
    background: $cream_200;
}
QFrame[role="card"] QLineEdit:focus, QFrame[role="card"] QComboBox:focus,
QFrame[role="card"] QSpinBox:focus, QFrame[role="card"] QDoubleSpinBox:focus,
QFrame[role="card"] QPlainTextEdit:focus {
    background: $cream_50;
}
QFrame[role="card"] QPushButton { background: $cream_50; }
QFrame[role="card"] QPushButton:hover { background: $cream_200; }
QFrame[role="card"] QPushButton:pressed { background: $blue_100; }
QFrame[role="card"] QPushButton:checked { background: $blue_100; }
QFrame[role="card"] QPushButton[variant="primary"] {
    background: $blue_500;
    border: none;
    color: $cream_50;
}
QFrame[role="card"] QPushButton[variant="primary"]:hover { background: $blue_400; }
QPushButton[variant="quiet"] {
    background: transparent;
    border: none;
    padding: 3px 10px;
    font-size: 11px;
    color: $ink_600;
}
QPushButton[variant="quiet"]:hover { background: $cream_200; color: $ink_900; }
QLabel { background: transparent; }
QLabel[role="caption"] { font-size: 11px; color: $ink_600; }
QLabel[role="overline"] {
    font-size: 10px;
    font-weight: 600;
    color: $ink_400;
    letter-spacing: 1px;
}
QLabel[role="error"] { font-size: 11px; color: $clay_400; }
QLabel[role="title"] { font-size: 20px; }
QLabel[role="section"] { font-size: 15px; }
QProgressBar {
    background: $blue_100;
    border: none;
    border-radius: 6px;
    min-height: 12px;
    text-align: center;
    font-size: 11px;
    color: $ink_600;
}
QProgressBar::chunk { background: $blue_300; border-radius: 6px; }
QCheckBox { background: transparent; spacing: 8px; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $cream_200;
    border-radius: 4px;
    background: $cream_50;
}
QCheckBox::indicator:checked { background: $blue_400; border: 1px solid $blue_400; }
QToolTip {
    background: $cream_50;
    color: $ink_900;
    border: 1px solid $cream_200;
    padding: 4px 8px;
}
"""
)


def qss() -> str:
    return _QSS.substitute(TOKENS, font=FONT_STACK)
