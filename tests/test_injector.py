"""Clipboard-swap injection: restore, non-text handling, failure paths.

The invariant under test everywhere: the transcript is never lost.
"""

from __future__ import annotations

from darkevox.inject.clipboard import InMemoryClipboard
from darkevox.inject.injector import Injector


class FakeKeys:
    def __init__(self, fail_paste: bool = False, fail_type: bool = False) -> None:
        self.pastes = 0
        self.typed: list[str] = []
        self.fail_paste = fail_paste
        self.fail_type = fail_type
        self.clipboard_at_paste: str | None = None
        self._clipboard: InMemoryClipboard | None = None

    def watch(self, clipboard: InMemoryClipboard) -> None:
        self._clipboard = clipboard

    def paste(self) -> None:
        if self.fail_paste:
            raise RuntimeError("paste blocked")
        self.pastes += 1
        if self._clipboard is not None:
            self.clipboard_at_paste = self._clipboard.get_text()

    def type_text(self, text: str) -> None:
        if self.fail_type:
            raise RuntimeError("typing blocked")
        self.typed.append(text)


def _injector(clipboard: InMemoryClipboard, keys: FakeKeys, method: str = "paste") -> Injector:
    return Injector(clipboard, keys, method=method, restore_delay_ms=0, sleep=lambda _s: None)


def test_paste_swaps_and_restores() -> None:
    clipboard = InMemoryClipboard()
    clipboard.set_text("previous contents")
    keys = FakeKeys()
    keys.watch(clipboard)
    report = _injector(clipboard, keys).inject("hello world")
    assert report.ok and report.method == "paste" and report.restored
    assert keys.pastes == 1
    assert keys.clipboard_at_paste == "hello world"  # transcript was on the clipboard at Ctrl+V
    assert clipboard.get_text() == "previous contents"


def test_empty_clipboard_not_restored() -> None:
    clipboard = InMemoryClipboard()
    keys = FakeKeys()
    report = _injector(clipboard, keys).inject("hello")
    assert report.ok and not report.restored
    assert clipboard.get_text() == "hello"  # transcript stays; nothing to restore


def test_non_text_clipboard_not_restored() -> None:
    clipboard = InMemoryClipboard()
    clipboard.set_text("placeholder")
    clipboard.non_text = True
    keys = FakeKeys()
    report = _injector(clipboard, keys).inject("hello")
    assert report.ok and not report.restored
    assert clipboard.get_text() == "hello"


def test_paste_failure_leaves_transcript_on_clipboard() -> None:
    clipboard = InMemoryClipboard()
    clipboard.set_text("previous")
    keys = FakeKeys(fail_paste=True)
    report = _injector(clipboard, keys).inject("precious words")
    assert not report.ok
    assert "clipboard" in report.note
    assert clipboard.get_text() == "precious words"


def test_typing_method_never_touches_clipboard() -> None:
    clipboard = InMemoryClipboard()
    clipboard.set_text("untouched")
    keys = FakeKeys()
    report = _injector(clipboard, keys, method="type").inject("typed out")
    assert report.ok and report.method == "type"
    assert keys.typed == ["typed out"]
    assert clipboard.get_text() == "untouched"


def test_typing_failure_leaves_transcript_on_clipboard() -> None:
    clipboard = InMemoryClipboard()
    keys = FakeKeys(fail_type=True)
    report = _injector(clipboard, keys, method="type").inject("precious words")
    assert not report.ok and report.method == "type"
    assert "clipboard" in report.note
    assert clipboard.get_text() == "precious words"


def test_empty_text_is_a_noop() -> None:
    clipboard = InMemoryClipboard()
    keys = FakeKeys()
    report = _injector(clipboard, keys).inject("")
    assert report.ok and keys.pastes == 0
