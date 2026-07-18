"""Polish pipeline: success, fallback, verbatim bypass, grounding, sanitizer."""

from __future__ import annotations

from darkevox.config import LlmConfig, PolishConfig
from darkevox.context.provider import GroundingChunk
from darkevox.polish.llm import LlmError
from darkevox.polish.pipeline import PolishPipeline, sanitize


class FakeClient:
    def __init__(self, reply: str = "Clean text.", error: LlmError | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls: list[list[dict[str, str]]] = []
        self.timeouts: list[float] = []

    def chat(self, messages: list[dict[str, str]], timeout_s: float) -> str:
        self.calls.append(messages)
        self.timeouts.append(timeout_s)
        if self.error is not None:
            raise self.error
        return self.reply


class FakeProvider:
    def __init__(self, chunks: list[GroundingChunk] | None = None, explode: bool = False):
        self.chunks = chunks or []
        self.explode = explode
        self.queries: list[str] = []

    def retrieve(self, query: str, k: int = 3, floor: float = 0.35) -> list[GroundingChunk]:
        if self.explode:
            raise RuntimeError("index corrupted")
        self.queries.append(query)
        return self.chunks


def _pipeline(client: FakeClient, provider: FakeProvider | None = None, grounding: bool = False):
    polish_cfg = PolishConfig(grounding_enabled=grounding)
    return PolishPipeline(client, LlmConfig(), polish_cfg, ["Jake"], provider)


def test_polish_success() -> None:
    client = FakeClient("Tell Jake the meeting moved to Friday.")
    result = _pipeline(client).polish("uh tell jake um the meeting moved to friday", "message")
    assert result.text == "Tell Jake the meeting moved to Friday."
    assert not result.fell_back and not result.used_grounding
    assert result.elapsed_ms >= 0
    assert client.timeouts == [10.0]  # config default reaches the transport


def test_llm_failure_falls_back_to_raw() -> None:
    client = FakeClient(error=LlmError("Ollama isn't running."))
    result = _pipeline(client).polish("keep these words", "email")
    assert result.fell_back
    assert result.text == "keep these words"
    assert "Ollama isn't running." in result.note
    assert "Raw transcript injected." in result.note


def test_empty_reply_falls_back_to_raw() -> None:
    client = FakeClient(reply="   ")
    result = _pipeline(client).polish("keep these words", "email")
    assert result.fell_back
    assert result.text == "keep these words"


def test_verbatim_bypasses_network_entirely() -> None:
    client = FakeClient()
    result = _pipeline(client).polish("exactly as spoken", "verbatim")
    assert result.text == "exactly as spoken"
    assert client.calls == []


def test_empty_transcript_bypasses_network() -> None:
    client = FakeClient()
    result = _pipeline(client).polish("   ", "email")
    assert client.calls == []
    assert not result.fell_back


def test_grounding_chunks_reach_the_prompt() -> None:
    chunks = [GroundingChunk("the Q3 budget is $4,200", "budget.pdf", 0.9)]
    provider = FakeProvider(chunks)
    client = FakeClient("Email Sam that the Q3 budget is $4,200.")
    result = _pipeline(client, provider, grounding=True).polish(
        "email sam that the q3 budget is forty two hundred", "email"
    )
    assert result.used_grounding
    system = client.calls[0][0]["content"]
    assert "$4,200" in system and "<reference>" in system
    assert provider.queries == ["email sam that the q3 budget is forty two hundred"]


def test_grounding_disabled_never_touches_provider() -> None:
    provider = FakeProvider([GroundingChunk("x", "y", 1.0)])
    client = FakeClient()
    result = _pipeline(client, provider, grounding=False).polish("hello", "email")
    assert provider.queries == []
    assert not result.used_grounding


def test_provider_failure_polishes_ungrounded() -> None:
    provider = FakeProvider(explode=True)
    client = FakeClient("Hello.")
    result = _pipeline(client, provider, grounding=True).polish("hello", "email")
    assert result.text == "Hello."
    assert not result.used_grounding and not result.fell_back


def test_sanitize_strips_fences_and_quotes() -> None:
    assert sanitize("```\nHello there.\n```") == "Hello there."
    assert sanitize("```text\nHello there.\n```") == "Hello there."
    assert sanitize('"Hello there."') == "Hello there."
    assert sanitize("Hello there.") == "Hello there."
    assert sanitize('She said "hi" and left.') == 'She said "hi" and left.'
    assert sanitize("  padded  ") == "padded"


def test_sanitize_never_eats_content() -> None:
    # A one-word first line is a note title, not a language tag.
    assert sanitize("```\nGroceries\n- milk\n- eggs\n```") == "Groceries\n- milk\n- eggs"
    # Wrapper quotes strip when inner quotes stay balanced without them...
    assert sanitize('"She said "hi" and left."') == 'She said "hi" and left.'
    assert sanitize("“Hello there.”") == "Hello there."
    # ...but an unbalanced inner quote means the wrapper might be content.
    assert sanitize("'don't'") == "'don't'"
