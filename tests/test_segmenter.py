"""Pause detection: cut after speech + silence, never on short speech."""

from __future__ import annotations

import numpy as np

from darkevox.audio.segmenter import PauseSegmenter, SegmenterConfig

RATE = 1000  # small fake sample rate keeps test arrays tiny


def _speech(seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    return (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * RATE), dtype=np.float32)


def _segmenter() -> PauseSegmenter:
    cfg = SegmenterConfig(silence_rms=0.01, min_speech_s=5.0, min_silence_s=1.0)
    return PauseSegmenter(cfg, sample_rate=RATE)


def test_cuts_after_speech_then_pause() -> None:
    seg = _segmenter()
    assert seg.feed(_speech(6.0)) is None
    result = seg.feed(_silence(1.2))
    assert result is not None
    assert result.size == int(7.2 * RATE)
    assert seg.flush() is None  # everything was consumed by the cut


def test_no_cut_on_short_speech() -> None:
    seg = _segmenter()
    assert seg.feed(_speech(2.0)) is None
    assert seg.feed(_silence(2.0)) is None  # pause, but speech under minimum


def test_no_cut_without_pause() -> None:
    seg = _segmenter()
    for _ in range(4):
        assert seg.feed(_speech(3.0)) is None


def test_flush_returns_remainder() -> None:
    seg = _segmenter()
    seg.feed(_speech(2.0))
    remainder = seg.flush()
    assert remainder is not None
    assert remainder.size == int(2.0 * RATE)
    assert seg.flush() is None


def test_silence_run_resets_on_new_speech() -> None:
    seg = _segmenter()
    seg.feed(_speech(6.0))
    seg.feed(_silence(0.5))
    seg.feed(_speech(0.5))  # pause broken before reaching one second
    assert seg.feed(_silence(0.7)) is None  # silence run restarted
    result = seg.feed(_silence(0.4))
    assert result is not None  # now the pause completes
