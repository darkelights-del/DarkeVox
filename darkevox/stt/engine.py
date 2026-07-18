"""faster-whisper wrapper. Warm-loaded once at startup; never per-utterance.

vad_filter stays on always: Whisper hallucinates text on silence and the
built-in Silero VAD is the standard mitigation. Core module: no Qt.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from darkevox.stt.models import resolve_device

log = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    language: str
    audio_s: float
    elapsed_ms: float


def build_initial_prompt(dictionary_terms: list[str]) -> str | None:
    """Seed Whisper with the personal dictionary so names spell right.

    Whisper treats initial_prompt as preceding conversation, which biases
    decoding toward these spellings without forcing them.
    """
    terms = [t.strip() for t in dictionary_terms if t.strip()]
    if not terms:
        return None
    return "Glossary: " + ", ".join(terms) + "."


class SttEngine:
    """One warm model instance, used from the single worker thread."""

    def __init__(
        self,
        model: str,
        models_dir: Path,
        device: str = "auto",
        compute_type: str = "auto",
        language: str = "en",
        beam_size: int = 5,
    ) -> None:
        self._model_name = model
        self._models_dir = models_dir
        self._device, self._compute_type = resolve_device(device, compute_type)
        self._language = language
        self._beam_size = max(1, beam_size)
        self._model: Any = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        from darkevox.stt.models import is_downloaded, model_path

        start = time.perf_counter()
        if is_downloaded(self._model_name, self._models_dir):
            source = str(model_path(self._model_name, self._models_dir))
        else:
            # First-run dialog normally prevents this; fall back to letting
            # faster-whisper fetch into our models dir rather than crashing.
            source = self._model_name
        self._model = WhisperModel(
            source,
            device=self._device,
            compute_type=self._compute_type,
            download_root=str(self._models_dir),
        )
        log.info(
            "stt model %s loaded on %s/%s in %.0f ms",
            self._model_name,
            self._device,
            self._compute_type,
            (time.perf_counter() - start) * 1000,
        )

    def transcribe(
        self, audio: np.ndarray, initial_prompt: str | None = None
    ) -> TranscriptionResult:
        if self._model is None:
            raise RuntimeError("SttEngine.load() must run before transcribe()")
        audio = audio.reshape(-1).astype(np.float32, copy=False)
        start = time.perf_counter()
        # Beam search buys real accuracy on imperfect mics; cross-segment
        # conditioning stays off (repetition loops in dictation).
        segments, info = self._model.transcribe(
            audio,
            language=self._language or None,
            vad_filter=True,
            initial_prompt=initial_prompt,
            beam_size=self._beam_size,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", self._language),
            audio_s=audio.size / 16_000,
            elapsed_ms=elapsed_ms,
        )
