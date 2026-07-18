"""ForegroundTracker degrades to a silent no-op off Windows."""

from __future__ import annotations

import sys

import pytest

from darkevox.inject.focus import ForegroundTracker


@pytest.mark.skipif(sys.platform == "win32", reason="no-op path is POSIX-only")
def test_tracker_is_a_noop_off_windows() -> None:
    tracker = ForegroundTracker()
    tracker.poll({123})
    assert tracker.target is None
    assert tracker.restore() is False
