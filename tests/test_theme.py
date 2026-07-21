"""The theme must stay in lockstep with .claude/skills/darkevox-ui-style."""

from __future__ import annotations

from darkevox.ui import theme


def test_tokens_match_the_skill() -> None:
    assert theme.TOKENS["cream_50"] == "#FFFDF8"
    assert theme.TOKENS["cream_100"] == "#FAF5EC"
    assert theme.TOKENS["blue_400"] == "#6FA1D4"
    assert theme.TOKENS["ink_900"] == "#2A3340"
    assert theme.TOKENS["clay_400"] == "#D9857E"


# sage/honey color the HUD's state dots, painted in code rather than styled via QSS.
_PAINTED_ONLY = {"sage_300", "honey_300"}


def test_qss_builds_and_substitutes_fully() -> None:
    sheet = theme.qss()
    assert "$" not in sheet, "unsubstituted template variable left in QSS"
    for name, value in theme.TOKENS.items():
        if name in _PAINTED_ONLY:
            continue
        assert value in sheet, f"token {name} unused in QSS"


def test_qss_covers_core_widgets() -> None:
    sheet = theme.qss()
    for selector in ("QMenu", "QPushButton", "QLineEdit", "QProgressBar", "QToolTip"):
        assert selector in sheet


def test_window_background_is_opt_in_never_global() -> None:
    """The old global QWidget fill painted opaque squares behind every
    rounded frameless surface — the 'square everything' bug."""
    sheet = theme.qss()
    assert 'QWidget[role="window"]' in sheet
    for line in sheet.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("QWidget {"), "global QWidget fill is back"


def test_contrast_ramp_tokens_exist_and_are_used() -> None:
    sheet = theme.qss()
    assert theme.TOKENS["blue_600"] == "#44739F"  # primary rest, 4.9:1 on cream
    assert theme.TOKENS["blue_700"] == "#3A648C"  # primary pressed
    assert theme.TOKENS["clay_600"] == "#AD5049"  # error text, 4.8:1
    for token in ("blue_600", "blue_650", "blue_700", "clay_600"):
        assert theme.TOKENS[token] in sheet


def test_interactive_states_are_complete() -> None:
    sheet = theme.qss()
    assert "QPushButton:focus" in sheet
    assert 'QPushButton[variant="primary"]:disabled' in sheet
    assert 'QPushButton[variant="quiet"]:pressed' in sheet
    assert "QLineEdit:disabled" in sheet
    assert "QScrollBar::handle:vertical" in sheet


def test_qss_asset_urls_render_when_paths_given() -> None:
    sheet = theme.qss({"combo_arrow": "/tmp/a.png", "check": "/tmp/c.png"})
    assert 'QComboBox::down-arrow { image: url("/tmp/a.png")' in sheet
    assert "$" not in sheet
