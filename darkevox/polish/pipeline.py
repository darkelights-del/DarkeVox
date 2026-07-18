"""Transcript in, polished text out. Tones, optional grounding, raw fallback.

The invariant (darkevox-guidelines): whatever fails here, the caller gets
usable text back. A fallback result carries the raw transcript plus a
user-visible note; it never raises.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from darkevox.config import LlmConfig, PolishConfig
from darkevox.context.provider import ContextProvider, GroundingChunk, NullContextProvider
from darkevox.polish.llm import LlmClient, LlmError
from darkevox.polish.prompts import build_polish_messages

log = logging.getLogger(__name__)


@dataclass
class PolishResult:
    text: str
    tone: str
    used_grounding: bool = False
    fell_back: bool = False
    elapsed_ms: float = 0.0
    note: str = ""  # user-visible when fell_back


_LANG_TAGS = {"text", "txt", "plaintext", "markdown", "md", "python", "json", "bash", "sh"}
_QUOTE_PAIRS = (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"))  # noqa: RUF001


def sanitize(raw: str) -> str:
    """Strip wrapper artifacts models add despite instructions: code fences
    around the whole reply, or one pair of quotes around the whole reply.

    Conservative by design: a first line is dropped only when it is a known
    language tag (a one-word note title is content, not a tag), and wrapper
    quotes are stripped only when the inner quotes stay balanced without them.
    """
    text = raw.strip()
    if text.startswith("```") and text.endswith("```") and len(text) > 6:
        text = text[3:-3].strip()
        first_line, _, rest = text.partition("\n")
        if rest and first_line.lower() in _LANG_TAGS:
            text = rest.strip()
    if len(text) >= 2:
        for opener, closer in _QUOTE_PAIRS:
            if text[0] != opener or text[-1] != closer:
                continue
            inner = text[1:-1]
            if opener == closer:
                balanced = inner.count(opener) % 2 == 0
            else:
                balanced = inner.count(opener) == inner.count(closer)
            if balanced:
                text = inner.strip()
            break
    return text


class PolishPipeline:
    def __init__(
        self,
        client: LlmClient,
        llm_cfg: LlmConfig,
        polish_cfg: PolishConfig,
        dictionary_terms: list[str],
        provider: ContextProvider | None = None,
    ) -> None:
        self._client = client
        self._llm = llm_cfg
        self._polish = polish_cfg
        self._dictionary = dictionary_terms
        self._provider = provider or NullContextProvider()

    def polish(self, transcript: str, tone: str) -> PolishResult:
        start = time.perf_counter()
        if tone == "verbatim" or not transcript.strip():
            return PolishResult(text=transcript, tone=tone)
        grounding = self._retrieve(transcript) if self._polish.grounding_enabled else []
        messages = build_polish_messages(transcript, tone, self._dictionary, grounding)
        try:
            raw = self._client.chat(messages, timeout_s=self._llm.timeout_s)
        except LlmError as exc:
            log.warning("polish fell back to raw transcript: %s", exc)
            return PolishResult(
                text=transcript,
                tone=tone,
                fell_back=True,
                elapsed_ms=(time.perf_counter() - start) * 1000,
                note=f"{exc} Raw transcript injected.",
            )
        except Exception:
            # The invariant outranks everything: polish never loses words,
            # whatever the transport throws.
            log.exception("polish crashed; falling back to raw transcript")
            return PolishResult(
                text=transcript,
                tone=tone,
                fell_back=True,
                elapsed_ms=(time.perf_counter() - start) * 1000,
                note="Polish failed. Raw transcript injected.",
            )
        text = sanitize(raw)
        if not text:
            log.warning("polish produced empty text; using raw transcript")
            return PolishResult(
                text=transcript,
                tone=tone,
                fell_back=True,
                elapsed_ms=(time.perf_counter() - start) * 1000,
                note="Polish came back empty. Raw transcript injected.",
            )
        return PolishResult(
            text=text,
            tone=tone,
            used_grounding=bool(grounding),
            elapsed_ms=(time.perf_counter() - start) * 1000,
        )

    def _retrieve(self, transcript: str) -> list[GroundingChunk]:
        try:
            return self._provider.retrieve(
                transcript, k=self._polish.grounding_k, floor=self._polish.grounding_floor
            )
        except Exception:  # grounding is best-effort; polish proceeds without it
            log.exception("context retrieval failed; polishing ungrounded")
            return []
