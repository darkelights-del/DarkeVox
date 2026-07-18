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
