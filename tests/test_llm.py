"""LLM transports: Ollama request/response handling and backend selection."""

from __future__ import annotations

import httpx
import pytest

from darkevox.config import LlmConfig
from darkevox.polish import llm as llm_mod
from darkevox.polish.llm import LlmError, OllamaClient, OpenRouterClient, client_from_config

MESSAGES = [{"role": "user", "content": "hi"}]


def _patch_post(monkeypatch: pytest.MonkeyPatch, handler) -> list[dict]:
    calls: list[dict] = []

    def fake_post(url: str, json: dict, timeout: float) -> httpx.Response:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return handler(url, json, timeout)

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


def test_ollama_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(url, json, timeout):
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": " Polished. "}},
            request=httpx.Request("POST", url),
        )

    calls = _patch_post(monkeypatch, handler)
    client = OllamaClient("http://localhost:11434", "qwen2.5:3b")
    assert client.chat(MESSAGES, timeout_s=10.0) == "Polished."
    assert calls[0]["url"] == "http://localhost:11434/api/chat"
    assert calls[0]["json"]["model"] == "qwen2.5:3b"
    assert calls[0]["json"]["stream"] is False
    assert calls[0]["timeout"] == 10.0


def test_ollama_down_retries_once_then_plain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(url, json, timeout):
        raise httpx.ConnectError("refused")

    calls = _patch_post(monkeypatch, handler)
    client = OllamaClient("http://localhost:11434", "qwen2.5:3b")
    with pytest.raises(LlmError, match="Ollama isn't running"):
        client.chat(MESSAGES, timeout_s=5.0)
    assert len(calls) == 2  # one retry on connection failure


def test_ollama_timeout_no_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(url, json, timeout):
        raise httpx.ReadTimeout("slow")

    calls = _patch_post(monkeypatch, handler)
    client = OllamaClient("http://localhost:11434", "qwen2.5:3b")
    with pytest.raises(LlmError, match="timed out"):
        client.chat(MESSAGES, timeout_s=5.0)
    assert len(calls) == 1  # timeouts fall back instead of doubling the wait


def test_ollama_missing_model_names_the_pull_command(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(url, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(404, json={"error": "model not found"}, request=request)

    _patch_post(monkeypatch, handler)
    client = OllamaClient("http://localhost:11434", "qwen2.5:3b")
    with pytest.raises(LlmError, match="ollama pull"):
        client.chat(MESSAGES, timeout_s=5.0)


class _FakeCompletions:
    def __init__(self, content: str | None = None, exc: Exception | None = None) -> None:
        self._content = content
        self._exc = exc
        self.kwargs: dict | None = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self._exc is not None:
            raise self._exc
        message = type("Message", (), {"content": self._content})
        choice = type("Choice", (), {"message": message})
        return type("Response", (), {"choices": [choice]})


def _openrouter_with(fake: _FakeCompletions) -> OpenRouterClient:
    client = OpenRouterClient("https://openrouter.ai/api/v1", "some/model:free", "sk-test")
    chat = type("Chat", (), {"completions": fake})()
    client._client = type("Sdk", (), {"chat": chat})()
    return client


def test_openrouter_success_trims_and_passes_params() -> None:
    fake = _FakeCompletions("  Polished.  ")
    client = _openrouter_with(fake)
    assert client.chat(MESSAGES, timeout_s=7.0) == "Polished."
    assert fake.kwargs is not None
    assert fake.kwargs["model"] == "some/model:free"
    assert fake.kwargs["timeout"] == 7.0


def test_openrouter_empty_reply_is_llm_error() -> None:
    with pytest.raises(LlmError, match="empty reply"):
        _openrouter_with(_FakeCompletions(content=None)).chat(MESSAGES, timeout_s=5.0)


def test_openrouter_sdk_exception_normalized_to_llm_error() -> None:
    with pytest.raises(LlmError, match="OpenRouter call failed"):
        _openrouter_with(_FakeCompletions(exc=RuntimeError("boom"))).chat(MESSAGES, timeout_s=5.0)


def test_backend_selection_ollama() -> None:
    client = client_from_config(LlmConfig())
    assert isinstance(client, OllamaClient)


def test_backend_openrouter_requires_model_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = LlmConfig(backend="openrouter")
    with pytest.raises(LlmError, match="No OpenRouter model set"):
        client_from_config(cfg)
    cfg.openrouter_model = "some/model:free"
    monkeypatch.setattr(llm_mod, "get_api_key", lambda name: None)
    with pytest.raises(LlmError, match="No OpenRouter API key"):
        client_from_config(cfg)
    monkeypatch.setattr(llm_mod, "get_api_key", lambda name: "sk-test")
    assert client_from_config(cfg) is not None


def test_unknown_backend_rejected() -> None:
    with pytest.raises(LlmError, match="Unknown LLM backend"):
        client_from_config(LlmConfig(backend="claude-api"))
