"""The one status vocabulary: every surface renders these exact strings."""

from __future__ import annotations

from darkevox.ui import status


def test_durations_format_mm_ss() -> None:
    assert status.duration(0) == "0:00"
    assert status.duration(7) == "0:07"
    assert status.duration(62) == "1:02"


def test_words_pluralizes() -> None:
    assert status.words(1) == "1 word"
    assert status.words(24) == "24 words"
    assert status.inserted(1) == "Inserted — 1 word"


def test_labels_are_sentence_case_and_confident() -> None:
    assert status.listening(12) == "Listening — 0:12"
    assert status.transcribing() == "Transcribing…"
    assert status.polishing("email") == "Polishing — email…"
    assert status.polished("email") == "Polished — email"
    assert status.polished("verbatim") == "As spoken"
    assert status.no_speech() == "No speech heard"
    assert status.ready(24) == "Ready — 24 words in the draft"
    assert status.ready() == "Ready"


def test_dot_semantics_hold() -> None:
    # Sage means success only; a non-event is neutral, never sage.
    assert status.DOTS[status.INSERTED] == "sage_300"
    assert status.DOTS[status.NO_SPEECH] == "ink_400"
    assert status.DOTS[status.FALLBACK] == "honey_300"
    assert status.DOTS[status.ERROR] == "clay_400"
    assert status.LISTENING in status.PULSING
    assert set(status.AUTO_HIDE) == {
        status.INSERTED,
        status.NO_SPEECH,
        status.FALLBACK,
        status.ERROR,
    }
