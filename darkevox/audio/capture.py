"""Microphone capture into a ring buffer. 16 kHz mono float32, no Qt.

The PortAudio callback thread appends; the app drains. On overflow the
oldest audio drops (better than blocking the audio thread), with one
warning per recording.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16_000


class CaptureError(RuntimeError):
    """Microphone unavailable or the audio backend failed."""


def parse_device(value: str) -> int | str | None:
    """Config [stt] input_device: '' = default, digits = index, else name match."""
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return value


class RingBuffer:
    """Fixed-capacity FIFO of float32 samples, drop-oldest on overflow."""

    def __init__(self, capacity_s: float, sample_rate: int = SAMPLE_RATE) -> None:
        self._capacity = int(capacity_s * sample_rate)
        self._buffer = np.zeros(self._capacity, dtype=np.float32)
        self._write = 0
        self._count = 0
        self._lock = threading.Lock()
        self._overflowed = False

    def __len__(self) -> int:
        with self._lock:
            return self._count

    def append(self, samples: np.ndarray) -> None:
        samples = samples.reshape(-1).astype(np.float32, copy=False)
        if samples.size >= self._capacity:
            samples = samples[-self._capacity :]
        with self._lock:
            end = self._write + samples.size
            if end <= self._capacity:
                self._buffer[self._write : end] = samples
            else:
                first = self._capacity - self._write
                self._buffer[self._write :] = samples[:first]
                self._buffer[: end % self._capacity] = samples[first:]
            self._write = end % self._capacity
            if self._count + samples.size > self._capacity:
                if not self._overflowed:
                    self._overflowed = True
                    log.warning("ring buffer overflow; oldest audio dropped")
                self._count = self._capacity
            else:
                self._count += samples.size

    def drain(self) -> np.ndarray:
        """Return everything buffered, oldest first, and reset."""
        with self._lock:
            if self._count == 0:
                return np.empty(0, dtype=np.float32)
            start = (self._write - self._count) % self._capacity
            if start + self._count <= self._capacity:
                out = self._buffer[start : start + self._count].copy()
            else:
                first = self._capacity - start
                out = np.concatenate(
                    (self._buffer[start:], self._buffer[: self._count - first])
                )
            self._count = 0
            self._overflowed = False
            return out


class MicrophoneCapture:
    """Owns the sounddevice input stream. start() raises CaptureError when no mic."""

    def __init__(self, device: int | str | None = None, capacity_s: float = 300.0) -> None:
        self._device = device
        self._ring = RingBuffer(capacity_s)
        self._stream: Any = None

    @property
    def running(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        # sounddevice loads PortAudio at import; keep that cost and any missing-
        # library failure out of module import so tests run anywhere.
        try:
            import sounddevice as sd
        except OSError as exc:
            raise CaptureError(f"audio backend unavailable: {exc}") from exc
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=self._device,
                callback=self._on_audio,
            )
        except (sd.PortAudioError, ValueError) as exc:
            raise CaptureError(f"microphone unavailable: {exc}") from exc
        try:
            stream.start()
        except (sd.PortAudioError, ValueError) as exc:
            stream.close()  # opened but unstartable; don't leak the PortAudio handle
            raise CaptureError(f"microphone unavailable: {exc}") from exc
        actual_rate = getattr(stream, "samplerate", SAMPLE_RATE)
        if actual_rate and abs(actual_rate - SAMPLE_RATE) > 1:
            # PortAudio may open at a hardware rate; whisper assumes 16 kHz.
            log.warning("mic opened at %s Hz (requested %s)", actual_rate, SAMPLE_RATE)
        self._stream = stream

    def _on_audio(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        if status:
            log.debug("audio callback status: %s", status)
        self._ring.append(indata[:, 0])

    def drain(self) -> np.ndarray:
        """Drain buffered audio while the stream keeps running (toggle mode)."""
        return self._ring.drain()

    def stop(self) -> np.ndarray:
        """Stop the stream and return the remaining buffered audio."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        return self._ring.drain()
