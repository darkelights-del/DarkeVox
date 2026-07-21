"""Design tokens and the app stylesheet.

Code mirror of .claude/skills/darkevox-ui-style; change the skill first, then
this file. Pure strings and numbers (no Qt imports) so tests run anywhere.

The window fill is opt-in: framed windows set the "window" role property.
Frameless translucent surfaces (panel, HUD) must never inherit an opaque
background, or their rounded corners render inside a square.
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
    "blue_600": "#44739F",
    "blue_650": "#3F6B98",
    "blue_700": "#3A648C",
    "ink_900": "#2A3340",
    "ink_600": "#5B6675",
    "ink_400": "#939CAA",
    "sage_300": "#A9C7A0",
    "honey_300": "#EDCF9A",
    "clay_400": "#D9857E",
    "clay_600": "#AD5049",
}

FONT_STACK = '"Segoe UI Variable", "Segoe UI", sans-serif'

# One type scale for the whole app; painted text (HUD, buttons) reads these
# instead of restating numbers.
FONT_BODY_PX = 13
FONT_CAPTION_PX = 11
FONT_OVERLINE_PX = 10
FONT_SECTION_PX = 15

# One radius scale: small chrome, controls, cards. Nothing else.
RADIUS_SM = 6
RADIUS_CONTROL = 10
RADIUS_CARD = 16

# QSS has no box-shadow; floating surfaces apply the one app shadow via
# QGraphicsDropShadowEffect with these values. Large and soft reads modern;
# tight and dark reads 2010. SHADOW_MARGIN is the transparent border a
# frameless window needs so the blur is never clipped.
SHADOW_BLUR = 24
SHADOW_DY = 6
SHADOW_RGBA = (42, 51, 64, 42)
SHADOW_MARGIN = 30

# Motion tokens (milliseconds). Exponential ease-outs only; no bounce.
# High-frequency surfaces enter near-instantly and exit with a short fade.
DUR_PRESS = 110
DUR_RELEASE = 160
DUR_HOVER = 170
DUR_HOVER_OUT = 150
DUR_ENTER = 90
DUR_EXIT = 150
DUR_PANEL_OPEN = 240
DUR_PANEL_CLOSE = 180
DUR_SETTLE = 200
DUR_TEXT_DIP = 110
DUR_SWELL = 280
PULSE_MS = 1200

_QSS = Template(
    """
* {
    font-family: $font;
    font-size: ${body}px;
    color: $ink_900;
}
QWidget[role="window"] { background: $cream_100; }
QMenu {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: ${r_control}px;
    padding: 6px;
}
QMenu::item { background: transparent; padding: 8px 24px 8px 12px; border-radius: ${r_sm}px; }
QMenu::item:selected { background: $blue_100; }
QMenu::item:disabled { color: $ink_600; }
QMenu::separator { height: 1px; background: $cream_200; margin: 4px 8px; }
QPushButton {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: ${r_control}px;
    padding: 8px 16px;
}
QPushButton:hover { background: $cream_200; }
QPushButton:pressed { background: $blue_100; }
QPushButton:focus { border: 1px solid $blue_500; }
QPushButton:disabled { color: $ink_400; }
QPushButton:checked { background: $blue_100; border: 1px solid $blue_400; }
QPushButton[variant="primary"] {
    background: $blue_600;
    border: 1px solid transparent;
    color: $cream_50;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover { background: $blue_650; color: $cream_50; }
QPushButton[variant="primary"]:pressed { background: $blue_700; color: $cream_50; }
QPushButton[variant="primary"]:focus { border: 1px solid $ink_900; }
QPushButton[variant="primary"]:disabled { background: $blue_200; color: $cream_50; }
QPushButton[variant="quiet"] {
    background: transparent;
    border: 1px solid transparent;
    padding: 4px 8px;
    font-size: ${caption}px;
    color: $ink_600;
}
QPushButton[variant="quiet"]:hover { background: $cream_200; color: $ink_900; }
QPushButton[variant="quiet"]:pressed { background: $blue_100; color: $ink_900; }
QPushButton[variant="quiet"]:focus { border: 1px solid $blue_500; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background: $cream_200;
    border: 1px solid transparent;
    border-radius: ${r_control}px;
    padding: 9px;
    selection-background-color: $blue_200;
    placeholder-text-color: $ink_600;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid $blue_500;
    background: $cream_50;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QPlainTextEdit:disabled {
    color: $ink_400;
    background: $cream_100;
}
QLineEdit[invalid="true"] { border: 1px solid $clay_400; }
QPlainTextEdit[variant="hero"] { background: $cream_50; border: 1px solid $cream_200; }
QPlainTextEdit[variant="hero"]:focus { border: 1px solid $blue_500; }
QComboBox::drop-down { border: none; width: 26px; }
$combo_arrow_rule
QComboBox QAbstractItemView {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: ${r_control}px;
    selection-background-color: $blue_100;
    selection-color: $ink_900;
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border: none;
    background: transparent;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    border: none;
    background: transparent;
}
$spin_arrow_rules
QFrame[role="card"] {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: ${r_card}px;
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
QFrame[role="card"] QPlainTextEdit[variant="hero"] { background: $cream_50; }
QFrame[role="card"] QPushButton { background: $cream_50; }
QFrame[role="card"] QPushButton:hover { background: $cream_200; }
QFrame[role="card"] QPushButton:pressed { background: $blue_100; }
QFrame[role="card"] QPushButton:checked { background: $blue_100; }
QFrame[role="card"] QPushButton[variant="primary"] {
    background: $blue_600;
    border: 1px solid transparent;
    color: $cream_50;
}
QFrame[role="card"] QPushButton[variant="primary"]:hover { background: $blue_650; }
QFrame[role="card"] QPushButton[variant="primary"]:pressed { background: $blue_700; }
QFrame[role="card"] QPushButton[variant="quiet"] { background: transparent; }
QFrame[role="card"] QPushButton[variant="quiet"]:hover { background: $cream_200; }
QLabel { background: transparent; }
QLabel[role="caption"] { font-size: ${caption}px; color: $ink_600; }
QLabel[role="overline"] {
    font-size: ${overline}px;
    font-weight: 600;
    color: $ink_600;
    letter-spacing: 1px;
}
QLabel[role="error"] { font-size: ${caption}px; color: $clay_600; }
QLabel[role="section"] { font-size: ${section}px; }
QProgressBar {
    background: $blue_100;
    border: none;
    border-radius: ${r_sm}px;
    min-height: 16px;
    text-align: center;
    font-size: ${caption}px;
    color: $ink_900;
}
QProgressBar::chunk { background: $blue_300; border-radius: ${r_sm}px; }
QCheckBox { background: transparent; spacing: 8px; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $cream_200;
    border-radius: 4px;
    background: $cream_50;
}
QCheckBox::indicator:hover { border: 1px solid $blue_400; }
QCheckBox::indicator:checked { background: $blue_500; border: 1px solid $blue_500; }
$check_rule
QTabWidget::pane {
    background: $cream_50;
    border: 1px solid $cream_200;
    border-radius: ${r_control}px;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: $ink_600;
    padding: 8px 20px;
    border: 1px solid transparent;
    border-top-left-radius: ${r_control}px;
    border-top-right-radius: ${r_control}px;
}
QTabBar::tab:selected { background: $cream_50; color: $ink_900; }
QTabBar::tab:hover:!selected { color: $ink_900; }
QTabBar::tab:focus { border: 1px solid $blue_500; }
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(147, 156, 170, 115);
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: rgba(91, 102, 117, 140); }
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: rgba(147, 156, 170, 115);
    border-radius: 4px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: rgba(91, 102, 117, 140); }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip {
    background: $cream_50;
    color: $ink_900;
    border: 1px solid $cream_200;
    border-radius: ${r_sm}px;
    padding: 4px 8px;
}
"""
)


def qss(assets: dict[str, str] | None = None) -> str:
    """Build the stylesheet. `assets` maps glyph names to runtime-generated
    image paths (combo_arrow, check, spin_up, spin_down); QSS cannot draw
    these shapes itself and this repo ships no binary images."""
    assets = assets or {}

    def _url(name: str) -> str:
        return assets[name].replace("\\", "/") if name in assets else ""

    combo_arrow_rule = (
        f'QComboBox::down-arrow {{ image: url("{_url("combo_arrow")}"); '
        "width: 10px; height: 10px; }"
        if "combo_arrow" in assets
        else ""
    )
    spin_arrow_rules = ""
    if "spin_up" in assets and "spin_down" in assets:
        spin_arrow_rules = (
            f'QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{_url("spin_up")}"); '
            "width: 8px; height: 8px; }\n"
            "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow "
            f'{{ image: url("{_url("spin_down")}"); width: 8px; height: 8px; }}'
        )
    check_rule = (
        f'QCheckBox::indicator:checked {{ image: url("{_url("check")}"); '
        f"background: {TOKENS['blue_500']}; border: 1px solid {TOKENS['blue_500']}; }}"
        if "check" in assets
        else ""
    )
    return _QSS.substitute(
        TOKENS,
        font=FONT_STACK,
        body=FONT_BODY_PX,
        caption=FONT_CAPTION_PX,
        overline=FONT_OVERLINE_PX,
        section=FONT_SECTION_PX,
        r_sm=RADIUS_SM,
        r_control=RADIUS_CONTROL,
        r_card=RADIUS_CARD,
        combo_arrow_rule=combo_arrow_rule,
        spin_arrow_rules=spin_arrow_rules,
        check_rule=check_rule,
    )
