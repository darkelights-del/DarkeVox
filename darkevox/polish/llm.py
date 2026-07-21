"""LLM transport: Ollama native /api/chat by default, OpenRouter opt-in.

Both hide behind LlmClient.chat(); the pipeline neither knows nor cares
which network it is on. Every call carries a hard timeout. LlmError
messages are written for the HUD: plain words, already actionable.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from darkevox.config import LlmConfig, get_api_key

log = logging.getLogger(__name__)


class LlmError(RuntimeError):
    """Transport or configuration failure; the message is user-visible."""


class LlmClient(Protocol):
    def chat(self, messages: list[dict[str, str]], timeout_s: float) -> str: ...


class OllamaClient:
    def __init__(self, base_url: str, model: str, keep_alive: str = "30m") -> None:
        self._url = base_url.rstrip("/") + "/api/chat"
        self._model = model
        self._keep_alive = keep_alive

    def warm(self) -> None:
        """Load the model into Ollama's memory ahead of the first dictation.

        An empty messages array is Ollama's documented load-only request. The
        cold load takes longer than the polish timeout on CPU, which is why
        first calls time out without this. Failures only log; polish itself
        still falls back to raw.
        """
        import httpx

        try:
            httpx.post(
                self._url,
                json={"model": self._model, "messages": [], "keep_alive": self._keep_alive},
                timeout=300.0,
            ).raise_for_status()
            log.info("ollama model %s warm", self._model)
        except Exception as exc:
            log.warning("ollama warm-load failed: %s", exc)

    def chat(self, messages: list[dict[str, str]], timeout_s: float) -> str:
        import httpx

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": self._keep_alive,
            # 0.0: cleanup is deterministic work; sampling heat is where small
            # models start "improving" what the speaker actually said.
            "options": {"temperature": 0.0},
        }
        last_connect_error: Exception | None = None
        for _attempt in range(2):  # one retry, connection errors only
            try:
                response = httpx.post(self._url, json=payload, timeout=timeout_s)
                response.raise_for_status()
                return str(response.json()["message"]["content"]).strip()
            except httpx.ConnectError as exc:
                last_connect_error = exc
            except httpx.TimeoutException as exc:
                raise LlmError("Polish timed out; the model may still be loading.") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise LlmError(
                        f"Ollama doesn't have {self._model}. Run: ollama pull {self._model}"
                    ) from exc
                raise LlmError(f"Ollama error {exc.response.status_code}.") from exc
            except httpx.HTTPError as exc:
                # The rest of the transport zoo (ReadError, RemoteProtocolError, ...);
                # anything escaping as a non-LlmError would bypass the raw-text fallback.
                raise LlmError("Ollama connection failed.") from exc
            except (KeyError, ValueError) as exc:
                raise LlmError("Ollama sent an unexpected reply.") from exc
        raise LlmError("Ollama isn't running. Start Ollama.") from last_connect_error


class OpenRouterClient:
    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        self._base_url = base_url
        self._model = model
        self._api_key = api_key
        self._client: Any = None

    def chat(self, messages: list[dict[str, str]], timeout_s: float) -> str:
        try:
            if self._client is None:
                from openai import OpenAI

                self._client = OpenAI(base_url=self._base_url, api_key=self._api_key)
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.0,
                timeout=timeout_s,
            )
            content = response.choices[0].message.content
            if not content:
                raise LlmError("OpenRouter sent an empty reply.")
            return str(content).strip()
        except LlmError:
            raise
        except Exception as exc:  # SDK raises a small zoo; the HUD needs one plain line
            log.warning("openrouter call failed: %s", exc)
            raise LlmError("OpenRouter call failed. Check the model name and key.") from exc


def client_from_config(cfg: LlmConfig) -> LlmClient:
    """Build the configured backend, validating what the backend needs."""
    if cfg.backend == "ollama":
        return OllamaClient(cfg.ollama_url, cfg.polish_model, keep_alive=cfg.keep_alive)
    if cfg.backend == "openrouter":
        if not cfg.openrouter_model:
            raise LlmError(
                "No OpenRouter model set. Pick one from openrouter.ai/models (filter: free)."
            )
        api_key = get_api_key("openrouter")
        if not api_key:
            raise LlmError("No OpenRouter API key saved. Add it in Settings.")
        return OpenRouterClient(cfg.openrouter_url, cfg.openrouter_model, api_key)
    raise LlmError(f"Unknown LLM backend '{cfg.backend}'.")
