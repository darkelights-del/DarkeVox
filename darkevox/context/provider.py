"""The bridge seam between dictation and the future knowledge base.

Phases 4-6 implement a real provider over SQLite + fastembed behind this
exact interface; until then NullContextProvider keeps the polish pipeline
honest about having no context. Core module: plain Python, no Qt, nothing
here may be awkward to expose over HTTP later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GroundingChunk:
    text: str
    source: str
    score: float


class ContextProvider(Protocol):
    def retrieve(self, query: str, k: int = 3, floor: float = 0.35) -> list[GroundingChunk]:
        """Chunks relevant to the query, best first, none below the score floor."""
        ...


class NullContextProvider:
    """No knowledge base yet: retrieves nothing, grounds nothing."""

    def retrieve(self, query: str, k: int = 3, floor: float = 0.35) -> list[GroundingChunk]:
        return []
