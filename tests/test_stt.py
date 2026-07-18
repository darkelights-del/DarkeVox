"""STT helpers that need no model: prompt seeding, paths, device resolution."""

from __future__ import annotations

from pathlib import Path

from darkevox.stt.engine import build_initial_prompt
from darkevox.stt.models import downloaded_mb, is_downloaded, model_path, resolve_device


def test_initial_prompt_from_dictionary() -> None:
    prompt = build_initial_prompt(["Jake", " Q1 segment ", "DarkeVox", ""])
    assert prompt == "Glossary: Jake, Q1 segment, DarkeVox."


def test_initial_prompt_empty() -> None:
    assert build_initial_prompt([]) is None
    assert build_initial_prompt(["  ", ""]) is None


def test_resolve_device_cpu_defaults(monkeypatch) -> None:
    monkeypatch.setattr("darkevox.stt.models.detect_cuda", lambda: False)
    assert resolve_device("auto", "auto") == ("cpu", "int8")


def test_resolve_device_cuda(monkeypatch) -> None:
    monkeypatch.setattr("darkevox.stt.models.detect_cuda", lambda: True)
    assert resolve_device("auto", "auto") == ("cuda", "float16")
    assert resolve_device("cpu", "auto") == ("cpu", "int8")
    assert resolve_device("cuda", "int8_float16") == ("cuda", "int8_float16")


def test_is_downloaded_checks_files(tmp_path: Path) -> None:
    assert not is_downloaded("small.en", tmp_path)
    target = model_path("small.en", tmp_path)
    target.mkdir(parents=True)
    (target / "model.bin").write_bytes(b"x")
    assert not is_downloaded("small.en", tmp_path)  # config.json still missing
    (target / "config.json").write_text("{}")
    assert is_downloaded("small.en", tmp_path)


def test_downloaded_mb(tmp_path: Path) -> None:
    assert downloaded_mb("base.en", tmp_path) == 0.0
    target = model_path("base.en", tmp_path)
    target.mkdir(parents=True)
    (target / "model.bin").write_bytes(b"\0" * 1_048_576)
    assert abs(downloaded_mb("base.en", tmp_path) - 1.0) < 0.01
