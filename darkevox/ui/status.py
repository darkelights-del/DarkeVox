"""Dictation status vocabulary: state names, dot tokens, and label copy.

The single source every surface renders — controller emissions, the HUD,
the panel status block, and the tray row all import from here, so the app
can never say "listening" three different ways again. Pure strings (no
Qt) so tests run anywhere. Copy follows darkevox-ui-style Microcopy:
sentence case, confident, numbers over adjectives, an em dash between
state and detail.
"""

from __future__ import annotations

# States: the wire values carried by controller.state_changed.
READY = "ready"
LISTENING = "listening"
TRANSCRIBING = "transcribing"
POLISHING = "polishing"
INSERTED = "inserted"
NO_SPEECH = "no_speech"
FALLBACK = "fallback"
ERROR = "error"

# The one dot map. Sage means success only, honey in-progress/warning,
# clay error; no state may borrow another's color.
DOTS: dict[str, str] = {
    READY: "ink_400",
    LISTENING: "blue_300",
    TRANSCRIBING: "blue_400",
    POLISHING: "honey_300",
    INSERTED: "sage_300",
    NO_SPEECH: "ink_400",  # a non-event, not a success: neutral gray
    FALLBACK: "honey_300",
    ERROR: "clay_400",
}

PULSING = frozenset({LISTENING})  # which dot breathes

# HUD auto-hide, milliseconds; states absent here stay until replaced.
AUTO_HIDE: dict[str, int] = {
    INSERTED: 1600,
    NO_SPEECH: 1600,
    FALLBACK: 4000,
    ERROR: 4000,
}


def duration(seconds: int) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def words(n: int) -> str:
    return f"{n} word" if n == 1 else f"{n} words"


def ready(draft_words: int = 0) -> str:
    if draft_words:
        return f"Ready — {words(draft_words)} in the draft"
    return "Ready"


def ready_hint(hotkey: str = "") -> str:
    if hotkey:
        return f"hold {hotkey} or click the mic"
    return "click the mic, or hold it to talk"


def listening(seconds: int) -> str:
    return f"Listening — {duration(seconds)}"


def transcribing() -> str:
    return "Transcribing…"


def polishing(tone: str = "") -> str:
    return f"Polishing — {tone}…" if tone else "Polishing…"


def polished(tone: str) -> str:
    return "As spoken" if tone == "verbatim" else f"Polished — {tone}"


def polished_hint(n: int) -> str:
    return f"{words(n)} · Insert or Copy"


def inserted(n: int) -> str:
    return f"Inserted — {words(n)}"


def inserting() -> str:
    return "Inserting…"


def copied(n: int) -> str:
    return f"Copied — {words(n)}"


def no_speech() -> str:
    return "No speech heard"


def no_speech_hint() -> str:
    return "try again, closer to the mic"


def fallback() -> str:
    return "Polish unavailable — showing raw"


def nothing_yet(verb: str) -> str:
    return f"Nothing to {verb} yet"
