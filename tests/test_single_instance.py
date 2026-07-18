"""The single-instance lock refuses a second acquire (POSIX path)."""

from __future__ import annotations

import sys

import pytest

from darkevox.app import SingleInstance


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX abstract-socket path")
def test_second_acquire_fails() -> None:
    first = SingleInstance("darkevox-test-lock")
    second = SingleInstance("darkevox-test-lock")
    assert first.acquire() is True
    assert second.acquire() is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX abstract-socket path")
def test_distinct_names_do_not_collide() -> None:
    a = SingleInstance("darkevox-test-lock-a")
    b = SingleInstance("darkevox-test-lock-b")
    assert a.acquire() is True
    assert b.acquire() is True
