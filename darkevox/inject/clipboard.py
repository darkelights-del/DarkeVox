"""Clipboard backends behind one protocol.

WindowsClipboard uses pywin32 (guarded imports, retry on the lock other
apps briefly hold). InMemoryClipboard backs the tests and dev boxes.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Protocol

log = logging.getLogger(__name__)


class ClipboardBackend(Protocol):
    def get_text(self) -> str | None: ...

    def set_text(self, text: str) -> None: ...

    def has_non_text(self) -> bool: ...


class InMemoryClipboard:
    def __init__(self) -> None:
        self._text: str | None = None
        self.non_text = False

    def get_text(self) -> str | None:
        return self._text

    def set_text(self, text: str) -> None:
        self._text = text
        self.non_text = False

    def has_non_text(self) -> bool:
        return self.non_text


class WindowsClipboard:
    """pywin32-backed clipboard. Only constructed on Windows."""

    _RETRIES = 5
    _RETRY_DELAY_S = 0.05

    def _open(self) -> None:
        import win32clipboard

        for attempt in range(self._RETRIES):
            try:
                win32clipboard.OpenClipboard()
                return
            except Exception:
                if attempt == self._RETRIES - 1:
                    raise
                time.sleep(self._RETRY_DELAY_S)

    def get_text(self) -> str | None:
        import win32clipboard
        import win32con

        self._open()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                return str(win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT))
            return None
        finally:
            win32clipboard.CloseClipboard()

    def set_text(self, text: str) -> None:
        import win32clipboard
        import win32con

        self._open()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()

    def has_non_text(self) -> bool:
        import win32clipboard
        import win32con

        self._open()
        try:
            fmt = 0
            while True:
                fmt = win32clipboard.EnumClipboardFormats(fmt)
                if fmt == 0:
                    return False
                if fmt not in (
                    win32con.CF_TEXT,
                    win32con.CF_UNICODETEXT,
                    win32con.CF_OEMTEXT,
                    win32con.CF_LOCALE,
                ):
                    return True
        finally:
            win32clipboard.CloseClipboard()


def system_clipboard() -> ClipboardBackend:
    if sys.platform == "win32":
        return WindowsClipboard()
    log.warning("no system clipboard backend off-Windows; using in-memory stub")
    return InMemoryClipboard()
