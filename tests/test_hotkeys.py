"""Combo parsing and the hold/toggle state machine."""

from __future__ import annotations

import pytest

from darkevox.audio.hotkeys import ComboTracker, parse_combo


def test_parse_combo_basic() -> None:
    assert parse_combo("ctrl+alt+space") == frozenset({"ctrl", "alt", "space"})
    assert parse_combo("Ctrl + Alt + D") == frozenset({"ctrl", "alt", "d"})


def test_parse_combo_aliases() -> None:
    assert parse_combo("control+option+space") == frozenset({"ctrl", "alt", "space"})
    assert parse_combo("cmd+f5") == frozenset({"win", "f5"})


def test_parse_combo_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown key"):
        parse_combo("ctrl+banana")
    with pytest.raises(ValueError):
        parse_combo("")


class Recorder:
    def __init__(self) -> None:
        self.events: list[str] = []

    def tracker(self) -> ComboTracker:
        return ComboTracker(
            hold=parse_combo("ctrl+alt+space"),
            toggle=parse_combo("ctrl+alt+d"),
            on_hold_start=lambda: self.events.append("hold_start"),
            on_hold_end=lambda: self.events.append("hold_end"),
            on_toggle=lambda: self.events.append("toggle"),
        )


def test_hold_fires_on_full_combo_and_release() -> None:
    rec = Recorder()
    t = rec.tracker()
    t.press("ctrl")
    t.press("alt")
    assert rec.events == []
    t.press("space")
    assert rec.events == ["hold_start"]
    t.release("space")
    assert rec.events == ["hold_start", "hold_end"]


def test_hold_ends_when_modifier_lifts_first() -> None:
    rec = Recorder()
    t = rec.tracker()
    for key in ("ctrl", "alt", "space"):
        t.press(key)
    t.release("ctrl")
    assert rec.events == ["hold_start", "hold_end"]
    t.release("space")
    t.release("alt")
    assert rec.events == ["hold_start", "hold_end"]  # no double end


def test_toggle_fires_once_per_press() -> None:
    rec = Recorder()
    t = rec.tracker()
    for key in ("ctrl", "alt", "d"):
        t.press(key)
    t.press("d")  # key-repeat while held must not re-fire
    assert rec.events == ["toggle"]
    t.release("d")
    t.press("d")
    assert rec.events == ["toggle", "toggle"]


def test_rapid_mashing_never_wedges() -> None:
    rec = Recorder()
    t = rec.tracker()
    for _ in range(20):
        t.press("ctrl")
        t.press("alt")
        t.press("space")
        t.release("space")
    starts = rec.events.count("hold_start")
    ends = rec.events.count("hold_end")
    assert starts == ends == 20
    # after everything releases, state is clean and a fresh hold still works
    t.release("ctrl")
    t.release("alt")
    t.press("ctrl")
    t.press("alt")
    t.press("space")
    assert rec.events[-1] == "hold_start"


def test_callback_exception_does_not_break_tracking() -> None:
    events: list[str] = []

    def explode() -> None:
        raise RuntimeError("boom")

    t = ComboTracker(
        hold=parse_combo("ctrl+space"),
        toggle=parse_combo("ctrl+d"),
        on_hold_start=explode,
        on_hold_end=lambda: events.append("end"),
        on_toggle=lambda: None,
    )
    t.press("ctrl")
    t.press("space")  # start callback explodes; tracker must survive
    t.release("space")
    assert events == ["end"]
