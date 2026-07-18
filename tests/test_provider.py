"""The grounding seam: the null provider grounds nothing, by contract."""

from __future__ import annotations

from darkevox.context.provider import GroundingChunk, NullContextProvider


def test_null_provider_retrieves_nothing() -> None:
    provider = NullContextProvider()
    assert provider.retrieve("anything at all") == []
    assert provider.retrieve("q", k=8, floor=0.0) == []


def test_grounding_chunk_is_frozen() -> None:
    chunk = GroundingChunk("text", "source.md", 0.5)
    try:
        chunk.text = "mutated"  # type: ignore[misc]
        raise AssertionError("GroundingChunk must be immutable")
    except AttributeError:
        pass
