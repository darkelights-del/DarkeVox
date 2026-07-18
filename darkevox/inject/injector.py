"""Text injection at the cursor: clipboard swap + Ctrl+V, typing as the
explicitly configured alternative.

The contract that outranks everything (darkevox-guidelines): never lose the
transcript. Any failure leaves the text on the clipboard and says so in the
report. The typing fallback is never auto-attempted after a paste failure,
because we cannot verify the focused field (it could be a password box).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from darkevox.inject.clipboard import ClipboardBackend

log = logging.getLogger(__name__)


class Keystrokes(Protocol):
    def paste(self) -> None: ...

    def type_text(self, text: str) -> None: ...


class PynputKeystrokes:
    def __init__(self) -> None:
        from pynput.keyboard import Controller

        self._controller = Controller()

    def paste(self) -> None:
        from pynput.keyboard import Key

        with self._controller.pressed(Key.ctrl):
            self._controller.press("v")
            self._controller.release("v")

    def type_text(self, text: str) -> None:
        self._controller.type(text)


class NullKeystrokes:
    """Dev-box stand-in when pynput has no display server; logs instead of typing."""

    def paste(self) -> None:
        log.info("null keystrokes: paste skipped")

    def type_text(self, text: str) -> None:
        log.info("null keystrokes: would type %d chars", len(text))


@dataclass
class InjectReport:
    ok: bool
    method: str
    restored: bool
    note: str = ""


class Injector:
    def __init__(
        self,
        clipboard: ClipboardBackend,
        keys: Keystrokes,
        method: str = "paste",
        restore_delay_ms: int = 300,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clipboard = clipboard
        self._keys = keys
        self._method = method
        self._restore_delay_s = restore_delay_ms / 1000.0
        self._sleep = sleep

    def inject(self, text: str) -> InjectReport:
        if not text:
            return InjectReport(ok=True, method=self._method, restored=False, note="empty text")
        if self._method == "type":
            return self._inject_by_typing(text)
        return self._inject_by_paste(text)

    def _inject_by_typing(self, text: str) -> InjectReport:
        try:
            self._keys.type_text(text)
            return InjectReport(ok=True, method="type", restored=False)
        except Exception:
            log.exception("typing injection failed")
            rescued = self._leave_on_clipboard(text)
            return InjectReport(ok=False, method="type", restored=False, note=_rescue_note(rescued))

    def _inject_by_paste(self, text: str) -> InjectReport:
        saved: str | None = None
        non_text = False
        try:
            non_text = self._clipboard.has_non_text()
            if non_text:
                # v1 restores text only; images/files would need format plumbing.
                log.warning("clipboard holds non-text content; it will not be restored")
            else:
                saved = self._clipboard.get_text()
            self._clipboard.set_text(text)
            self._keys.paste()
            self._sleep(self._restore_delay_s)
            restored = False
            if saved is not None and not non_text:
                self._clipboard.set_text(saved)
                restored = True
            return InjectReport(ok=True, method="paste", restored=restored)
        except Exception:
            log.exception("paste injection failed")
            rescued = self._leave_on_clipboard(text)
            return InjectReport(
                ok=False, method="paste", restored=False, note=_rescue_note(rescued)
            )

    def _leave_on_clipboard(self, text: str) -> bool:
        try:
            self._clipboard.set_text(text)
            return True
        except Exception:
            log.exception("could not place transcript on clipboard")
            # Last resort for the never-lose-words rule: the log keeps the text.
            log.error("transcript preserved here: %s", text)
            return False


def _rescue_note(rescued: bool) -> str:
    if rescued:
        return "Injection failed. Transcript is on the clipboard."
    return "Injection failed. Transcript saved to the log."
