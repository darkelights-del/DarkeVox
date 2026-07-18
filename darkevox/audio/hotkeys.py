"""Global hotkeys: hold-to-talk and toggle mode.

ComboTracker is a pure state machine over key-name strings so tests can
drive it without pynput. HotkeyManager owns the pynput listener and maps
real keys onto those names. Plain callbacks only; app.py bridges to Qt.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

_ALIASES = {
    "control": "ctrl",
    "ctl": "ctrl",
    "windows": "win",
    "super": "win",
    "cmd": "win",
    "option": "alt",
    "return": "enter",
}

_KNOWN_SPECIAL = {
    "ctrl", "alt", "shift", "win", "space", "enter", "tab", "esc",
    "backspace", "delete", "home", "end", "insert", "caps_lock",
    *{f"f{i}" for i in range(1, 25)},
}


def parse_combo(combo: str) -> frozenset[str]:
    """'ctrl+alt+space' -> frozenset({'ctrl','alt','space'}). Raises ValueError."""
    parts = [part.strip().lower() for part in combo.split("+")]
    keys: set[str] = set()
    for part in parts:
        part = _ALIASES.get(part, part)
        single_char = len(part) == 1 and (part.isalnum() or part in "`-=[]\\;',./")
        if not single_char and part not in _KNOWN_SPECIAL:
            raise ValueError(f"unknown key '{part}' in combo '{combo}'")
        keys.add(part)
    if not keys:
        raise ValueError(f"empty combo '{combo}'")
    return frozenset(keys)


class ComboTracker:
    """Tracks pressed keys; fires hold start/end and toggle edges.

    Hold: starts when every key of the hold combo is down, ends when any of
    them lifts. Toggle: fires once per full press (must fully release at
    least one combo key before it can fire again). Rapid mashing may drop a
    press; it can never wedge the state, which is the phase 1 guarantee.
    """

    def __init__(
        self,
        hold: frozenset[str],
        toggle: frozenset[str],
        on_hold_start: Callable[[], None],
        on_hold_end: Callable[[], None],
        on_toggle: Callable[[], None],
    ) -> None:
        self._hold = hold
        self._toggle = toggle
        self._on_hold_start = on_hold_start
        self._on_hold_end = on_hold_end
        self._on_toggle = on_toggle
        self._pressed: set[str] = set()
        self._hold_active = False
        self._toggle_armed = True

    def press(self, key: str) -> None:
        self._pressed.add(key)
        if not self._hold_active and self._hold <= self._pressed:
            self._hold_active = True
            self._fire(self._on_hold_start)
        if self._toggle_armed and self._toggle <= self._pressed:
            self._toggle_armed = False
            self._fire(self._on_toggle)

    def release(self, key: str) -> None:
        self._pressed.discard(key)
        if self._hold_active and not self._hold <= self._pressed:
            self._hold_active = False
            self._fire(self._on_hold_end)
        if not self._toggle <= self._pressed:
            self._toggle_armed = True

    @staticmethod
    def _fire(callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception:  # a callback crash must not kill the listener thread
            log.exception("hotkey callback failed")


def _key_name(key: Any, listener: Any) -> str | None:
    """Map a pynput key event to the canonical names parse_combo produces."""
    key = listener.canonical(key)
    char = getattr(key, "char", None)
    if char:
        return char.lower()
    name = getattr(key, "name", None)
    if not name:
        return None
    base = name.split("_")[0]
    if base in ("ctrl", "alt", "shift", "cmd"):
        return "win" if base == "cmd" else base
    return name


class HotkeyManager:
    """Owns the pynput global listener and feeds ComboTracker."""

    def __init__(
        self,
        hold_combo: str,
        toggle_combo: str,
        on_hold_start: Callable[[], None],
        on_hold_end: Callable[[], None],
        on_toggle: Callable[[], None],
    ) -> None:
        self._tracker = ComboTracker(
            parse_combo(hold_combo),
            parse_combo(toggle_combo),
            on_hold_start,
            on_hold_end,
            on_toggle,
        )
        self._listener: Any = None

    def start(self) -> None:
        from pynput import keyboard

        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _press(self, key: Any) -> None:
        name = _key_name(key, self._listener)
        if name:
            self._tracker.press(name)

    def _release(self, key: Any) -> None:
        name = _key_name(key, self._listener)
        if name:
            self._tracker.release(name)
