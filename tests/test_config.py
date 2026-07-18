"""Config round-trip, merge, and path behavior."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from darkevox import config


def test_defaults_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    original = config.Config()
    config.save(original, path)
    loaded = config.load(path)
    assert loaded == original


def test_modified_values_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    cfg = config.Config()
    cfg.llm.backend = "openrouter"
    cfg.llm.openrouter_model = "some/model:free"
    cfg.polish.default_tone = "message"
    cfg.dictionary.terms = ["Jake", "Q1 segment", "DarkeVox"]
    config.save(cfg, path)
    loaded = config.load(path)
    assert loaded == cfg


def test_partial_file_fills_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[llm]\nbackend = "openrouter"\n', encoding="utf-8")
    cfg = config.load(path)
    assert cfg.llm.backend == "openrouter"
    assert cfg.llm.polish_model == "qwen2.5:3b"
    assert cfg.stt.model == "small.en"


def test_unknown_keys_ignored(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[llm]\nbanana = 1\n[mystery]\nx = 2\n', encoding="utf-8")
    cfg = config.load(path)
    assert cfg == config.Config()


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = config.load(tmp_path / "nope.toml")
    assert cfg == config.Config()


def test_corrupt_file_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("not [valid toml ===", encoding="utf-8")
    cfg = config.load(path)
    assert cfg == config.Config()


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "nested" / "config.toml"
    config.save(config.Config(), path)
    assert path.is_file()


def test_ollama_is_the_default_backend() -> None:
    cfg = config.Config()
    assert cfg.llm.backend == "ollama"
    assert cfg.llm.polish_model == "qwen2.5:3b"
    assert cfg.llm.summarize_model == "qwen2.5:7b"
    assert cfg.llm.openrouter_model == ""
    assert cfg.stt.cloud_enabled is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX path convention")
def test_dirs_respect_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert config.config_dir() == tmp_path / "cfg" / "DarkeVox"
    assert config.data_dir() == tmp_path / "data" / "DarkeVox"
    assert config.models_dir() == tmp_path / "data" / "DarkeVox" / "models"
