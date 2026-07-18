"""Energy-based pause detection so long toggle dictations stream through STT
in segments instead of one blob. Whisper's own VAD still runs per segment;
this only decides where to cut.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from darkevox.audio.capture import SAMPLE_RATE


@dataclass
class SegmenterConfig:
    silence_rms: float = 0.010  # ~-40 dBFS; below this a block counts as silence
    min_speech_s: float = 5.0  # never cut segments shorter than this
    min_silence_s: float = 1.0  # a pause this long marks a cut point


class PauseSegmenter:
    """Feed audio blocks; get a finished segment back when a pause follows speech."""

    def __init__(self, config: SegmenterConfig | None = None, sample_rate: int = SAMPLE_RATE):
        self._cfg = config or SegmenterConfig()
        self._rate = sample_rate
        self._blocks: list[np.ndarray] = []
        self._buffered = 0
        self._silence_run = 0

    @property
    def buffered_s(self) -> float:
        return self._buffered / self._rate

    def feed(self, block: np.ndarray) -> np.ndarray | None:
        """Returns a segment ready for STT, or None while one is still building."""
        block = block.reshape(-1)
        if block.size == 0:
            return None
        self._blocks.append(block)
        self._buffered += block.size
        rms = float(np.sqrt(np.mean(np.square(block))))
        if rms < self._cfg.silence_rms:
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
        """Return whatever is buffered (end of dictation), or None if empty."""
        if not self._blocks:
            return None
        segment = np.concatenate(self._blocks)
        self._blocks = []
        self._buffered = 0
        self._silence_run = 0
        return segment
