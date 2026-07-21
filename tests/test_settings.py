"""Settings dialog logic: hotkey conflict validation and mic mapping."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from darkevox.config import Config
from darkevox.ui.settings import SettingsDialog


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _dialog(qapp: QApplication) -> SettingsDialog:
    return SettingsDialog(Config())


def test_valid_distinct_combos_pass(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._hold.setText("ctrl+alt+space")
    dialog._toggle.setText("ctrl+alt+d")
    assert dialog._combo_error() == ""


def test_bad_syntax_is_rejected(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._hold.setText("not a combo !!!")
    dialog._toggle.setText("ctrl+alt+d")
    assert "combo like" in dialog._combo_error()


def test_equal_combos_conflict(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._hold.setText("ctrl+alt+space")
    dialog._toggle.setText("ctrl+alt+space")
    assert "differ" in dialog._combo_error()


def test_subset_combos_conflict(qapp: QApplication) -> None:
    """A subset fires on the same press: ctrl+space triggers inside
    ctrl+alt+space's chord."""
    dialog = _dialog(qapp)
    dialog._hold.setText("ctrl+space")
    dialog._toggle.setText("ctrl+alt+space")
    assert "differ" in dialog._combo_error()


def test_backend_fields_follow_the_backend(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._sync_backend_fields("ollama")
    assert dialog._openrouter_model_row.isHidden()
    assert not dialog._ollama_url_row.isHidden()
    dialog._sync_backend_fields("openrouter")
    assert dialog._ollama_url_row.isHidden()
    assert not dialog._openrouter_model_row.isHidden()
