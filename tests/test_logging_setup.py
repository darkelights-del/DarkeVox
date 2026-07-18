"""Stage timers and log file creation."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from darkevox.logging_setup import format_timings, setup_logging, stage


def test_stage_records_elapsed_ms() -> None:
    timings: dict[str, float] = {}
    with stage(timings, "stt"):
        time.sleep(0.01)
    assert timings["stt"] >= 10.0


def test_stage_records_on_exception() -> None:
    timings: dict[str, float] = {}
    try:
        with stage(timings, "polish"):
            raise ValueError("boom")
    except ValueError:
        pass
    assert "polish" in timings


def test_format_timings() -> None:
    line = format_timings({"stt": 843.2, "polish": 51.0})
    assert line == "stt=843ms polish=51ms total=894ms"


def test_setup_logging_creates_file(tmp_path: Path) -> None:
    root = logging.getLogger()
    before = list(root.handlers)
    before_level = root.level
    try:
        log_file = setup_logging(tmp_path / "logs")
        logging.getLogger("test").info("hello")
        assert log_file.is_file()
        assert "hello" in log_file.read_text(encoding="utf-8")
    finally:
        for handler in root.handlers[:]:
            if handler not in before:
                root.removeHandler(handler)
                handler.close()
        root.setLevel(before_level)  # setup_logging sets INFO; don't leak it


def test_setup_logging_level_restored_by_previous_test() -> None:
    # Guards the teardown above: the suite must not run at a leaked INFO level.
    assert logging.getLogger().level != logging.INFO
