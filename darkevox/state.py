"""The single mutable application state (see darkevox-guidelines: no other globals)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppState:
    tone: str = "email"
    dictation_mode: str = "hold"  # hold | toggle
    recording: bool = False
    busy: bool = False
    grounding: bool = False
