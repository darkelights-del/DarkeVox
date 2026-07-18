"""Rotating file log plus per-stage timing helpers.

Latency discipline (see darkevox-guidelines): every dictation logs
capture/stt/polish/inject timings so regressions are visible in the log,
not discovered by feel.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(log_dir: Path, level: int = logging.INFO, console: bool = False) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "darkevox.log"
    root = logging.getLogger()
    root.setLevel(level)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(file_handler)
    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(stream)
    return log_file


@contextmanager
def stage(timings: dict[str, float], name: str) -> Iterator[None]:
    """Record the wall-clock milliseconds of one pipeline stage into ``timings``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        timings[name] = (time.perf_counter() - start) * 1000.0


def format_timings(timings: dict[str, float]) -> str:
    """'stt=843ms polish=51ms total=894ms' — the line the latency budget is judged by."""
    parts = [f"{name}={value:.0f}ms" for name, value in timings.items()]
    parts.append(f"total={sum(timings.values()):.0f}ms")
    return " ".join(parts)
