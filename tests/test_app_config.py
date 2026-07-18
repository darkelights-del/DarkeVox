"""_apply_config must mutate the live Config in place, section by section."""

from __future__ import annotations

from darkevox.app import _apply_config
from darkevox.config import Config


def test_apply_config_copies_every_section() -> None:
    target = Config()
    source = Config()
    source.llm.backend = "openrouter"
    source.llm.timeout_s = 22.5
    source.hotkeys.hold = "ctrl+shift+h"
    source.polish.default_tone = "notes"
    source.dictionary.terms = ["Jake", "Q1 segment"]
    _apply_config(target, source)
    assert target == source


def test_apply_config_keeps_section_identity() -> None:
    """Holders keep references to sections; rebinding them would orphan every holder."""
    target = Config()
    held_llm = target.llm
    held_dictionary = target.dictionary
    source = Config()
    source.llm.polish_model = "llama3.2:3b"
    source.dictionary.terms = ["DarkeVox"]
    _apply_config(target, source)
    assert held_llm is target.llm
    assert held_llm.polish_model == "llama3.2:3b"
    assert held_dictionary is target.dictionary
    assert held_dictionary.terms == ["DarkeVox"]
