"""The panel's running draft: voice builds on the text box, never replaces it.

Pure logic (no Qt) so the joining rules are testable. A session snapshots
the current text as its base; partials render as base + join + utterance,
and the commit becomes the next base. An empty session leaves the draft
untouched, so an accidental mic tap can never wipe the user's words.
"""

from __future__ import annotations

_TERMINATORS = ".!?…:;\n"
_KEEP_CAPS = {"I", "I'm", "I'll", "I've", "I'd", "OK"}


def join_utterance(base: str, utterance: str, keep_words: tuple[str, ...] = ()) -> str:
    """Append an utterance to the draft with natural spacing and case.

    A new paragraph (base ends in a newline) or a finished sentence keeps
    Whisper's capitalization; joining mid-sentence lowercases the first word
    unless it looks like a proper noun ("I", acronyms, dictionary terms).
    """
    utterance = utterance.strip()
    if not utterance:
        return base
    trimmed = base.rstrip(" ")
    if not trimmed.strip():
        return utterance
    joiner = "" if trimmed.endswith("\n") else " "
    if not trimmed.rstrip("\n").endswith(tuple(_TERMINATORS)) or trimmed.endswith(","):
        first, _, rest = utterance.partition(" ")
        if not (
            first in _KEEP_CAPS
            or first in keep_words
            or (len(first) > 1 and first.isupper())
        ):
            utterance = first[:1].lower() + first[1:] + (" " + rest if rest else "")
    return trimmed + joiner + utterance


class Draft:
    """Session-aware draft state with undo of the last take."""

    def __init__(self, keep_words: tuple[str, ...] = ()) -> None:
        self._keep_words = keep_words
        self._base = ""
        self._undo: list[str] = []

    @property
    def base(self) -> str:
        return self._base

    def sync(self, text: str) -> None:
        """Adopt manual edits made between sessions."""
        self._base = text

    def begin_session(self, current_text: str) -> None:
        self._base = current_text

    def render(self, partial: str) -> str:
        """The live view while recording: base plus the in-flight utterance."""
        return join_utterance(self._base, partial, self._keep_words)

    def commit(self, final: str) -> str:
        """Fold the finished utterance in. Empty utterances change nothing."""
        if not final.strip():
            return self._base
        self._undo.append(self._base)
        del self._undo[:-8]
        self._base = join_utterance(self._base, final, self._keep_words)
        return self._base

    def undo(self) -> str | None:
        """Roll back the last committed take; None when nothing to undo."""
        if not self._undo:
            return None
        self._base = self._undo.pop()
        return self._base

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    def clear(self) -> None:
        self._base = ""
        self._undo.clear()
