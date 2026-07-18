"""RingBuffer ordering, wraparound, and drop-oldest behavior."""

from __future__ import annotations

import numpy as np

from darkevox.audio.capture import RingBuffer


def _samples(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float32)


def test_append_drain_preserves_order() -> None:
    ring = RingBuffer(capacity_s=1.0, sample_rate=8)
    ring.append(_samples(1, 2, 3))
    ring.append(_samples(4, 5))
    assert ring.drain().tolist() == [1, 2, 3, 4, 5]


def test_drain_resets() -> None:
    ring = RingBuffer(capacity_s=1.0, sample_rate=8)
    ring.append(_samples(1, 2))
    ring.drain()
    assert len(ring) == 0
    assert ring.drain().size == 0


def test_wraparound_keeps_newest() -> None:
    ring = RingBuffer(capacity_s=1.0, sample_rate=4)  # capacity 4 samples
    ring.append(_samples(1, 2, 3))
    ring.append(_samples(4, 5, 6))  # overflows: 1 and 2 drop
    out = ring.drain().tolist()
    assert out == [3, 4, 5, 6]


def test_block_larger_than_capacity_keeps_tail() -> None:
    ring = RingBuffer(capacity_s=1.0, sample_rate=4)
    ring.append(_samples(1, 2, 3, 4, 5, 6, 7))
    assert ring.drain().tolist() == [4, 5, 6, 7]


def test_two_dimensional_input_flattens() -> None:
    ring = RingBuffer(capacity_s=1.0, sample_rate=8)
    ring.append(np.array([[1.0], [2.0]], dtype=np.float32))
    assert ring.drain().tolist() == [1, 2]
