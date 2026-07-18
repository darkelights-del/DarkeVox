"""Click vs hold vs drag interpretation for the panel mic."""

from __future__ import annotations

from darkevox.ui.interaction import PressHoldInterpreter


class Recorder:
    def __init__(self) -> None:
        self.events: list[str] = []

    def interpreter(self) -> PressHoldInterpreter:
        return PressHoldInterpreter(
            on_click=lambda: self.events.append("click"),
            on_hold_start=lambda: self.events.append("hold_start"),
            on_hold_end=lambda: self.events.append("hold_end"),
        )


def test_quick_release_is_a_click() -> None:
    rec = Recorder()
    it = rec.interpreter()
    it.press()
    it.release()
    assert rec.events == ["click"]


def test_long_press_is_push_to_talk() -> None:
    rec = Recorder()
    it = rec.interpreter()
    it.press()
    it.hold_elapsed()
    assert rec.events == ["hold_start"]
    assert it.holding
    it.release()
    assert rec.events == ["hold_start", "hold_end"]


def test_drag_cancels_a_pending_click() -> None:
    rec = Recorder()
    it = rec.interpreter()
    it.press()
    it.cancel()
    it.release()
    assert rec.events == []


def test_drag_during_hold_still_ends_the_hold() -> None:
    rec = Recorder()
    it = rec.interpreter()
    it.press()
    it.hold_elapsed()
    it.cancel()
    assert rec.events == ["hold_start", "hold_end"]
    it.release()
    assert rec.events == ["hold_start", "hold_end"]


def test_timer_firing_after_release_does_nothing() -> None:
    rec = Recorder()
    it = rec.interpreter()
    it.press()
    it.release()
    it.hold_elapsed()
    assert rec.events == ["click"]
