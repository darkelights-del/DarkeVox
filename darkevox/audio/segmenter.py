"""Pause detection for live dictation: cut where the speaker actually pauses.

Two lessons from the field are baked in. Silence is judged RELATIVE to the
loudest audio heard this session (a fixed absolute threshold misfires on
quiet laptop mics: everything reads as silence and cuts land mid-word).
And segments stay LONG: Whisper transcribes whole utterances far better
than context-free fragments, so cuts only happen at real sentence pauses.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from darkevox.audio.capture import SAMPLE_RATE


@dataclass
class SegmenterConfig:
    # Silence = block rms below max(floor, ratio * loudest block this session).
    # The relative term adapts to mic gain; the floor keeps digital silence
    # from counting as speech before anyone talks.
    silence_floor: float = 0.0015  # ~ -56 dBFS
    silence_ratio: float = 0.15
    # Whisper is strongest with whole utterances (its window is 30 s);
    # frequent cuts transcribe fragments and mangle words at the seams.
    min_speech_s: float = 8.0
    min_silence_s: float = 0.9


class PauseSegmenter:
    """Feed audio blocks; get a finished segment back when a pause follows speech."""

    def __init__(self, config: SegmenterConfig | None = None, sample_rate: int = SAMPLE_RATE):
        self._cfg = config or SegmenterConfig()
        self._rate = sample_rate
        self._blocks: list[np.ndarray] = []
        self._buffered = 0
        self._silence_run = 0
        self._peak_rms = 0.0

    @property
    def buffered_s(self) -> float:
        return self._buffered / self._rate

    def _threshold(self) -> float:
        return max(self._cfg.silence_floor, self._cfg.silence_ratio * self._peak_rms)

    def feed(self, block: np.ndarray) -> np.ndarray | None:
        """Returns a segment ready for STT, or None while one is still building."""
        block = block.reshape(-1)
        if block.size == 0:
            return None
        self._blocks.append(block)
        self._buffered += block.size
        rms = float(np.sqrt(np.mean(np.square(block))))
        self._peak_rms = max(self._peak_rms, rms)
        if rms < self._threshold():
            self._silence_run += block.size
        else:
            self._silence_run = 0
        speech_samples = self._buffered - self._silence_run
        if (
            self._silence_run >= self._cfg.min_silence_s * self._rate
            and speech_samples >= self._cfg.min_speech_s * self._rate
        ):
            return self.flush()
        return None

    def flush(self) -> np.ndarray | None:
        """Return whatever is buffered (end of dictation), or None if empty.

        The session's peak-loudness estimate survives the flush on purpose:
        the mic's level doesn't change between segments of one dictation.
        """
        if not self._blocks:
            return None
        segment = np.concatenate(self._blocks)
        self._blocks = []
        self._buffered = 0
        self._silence_run = 0
        return segment
