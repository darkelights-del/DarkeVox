"""Settings dialog: hotkeys, speech model and microphone, polish, injection.

Tabbed so the whole dialog fits a 1080p laptop with room to spare. Layout
follows darkevox-ui-style: each section is a cream-50 card (16 radius),
overline labels above controls, captions for help text. The Polish tab
shows only the active backend's fields. Edits happen on a deep copy; the
caller receives it via the saved signal only after validation passes.
API keys go straight to the keyring, never into the TOML.
"""

from __future__ import annotations

import copy
import logging

from PySide6.QtCore import QPropertyAnimation, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from darkevox.audio.hotkeys import parse_combo
from darkevox.config import BACKENDS, INJECT_METHODS, STT_MODELS, TONES, Config, set_api_key
from darkevox.ui import motion
from darkevox.ui.buttons import AnimatedButton

log = logging.getLogger(__name__)

_DEFAULT_MIC = "System default"


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "caption")
    label.setWordWrap(True)
    return label


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("role", "card")
    box = QVBoxLayout(frame)
    box.setContentsMargins(16, 16, 16, 16)
    box.setSpacing(8)
    return frame, box


def _field(box: QVBoxLayout, label_text: str, widget: QWidget) -> QWidget:
    """Label-above-control, wrapped so a whole row can hide with its label."""
    row = QWidget()
    col = QVBoxLayout(row)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(4)
    label = QLabel(label_text.upper())
    label.setProperty("role", "overline")
    col.addWidget(label)
    col.addWidget(widget)
    box.addWidget(row)
    return row


def _mark_invalid(edit: QLineEdit, invalid: bool) -> None:
    edit.setProperty("invalid", invalid)
    style = edit.style()
    style.unpolish(edit)
    style.polish(edit)


def _page() -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(12, 16, 12, 12)
    box.setSpacing(12)
    return page, box


def list_input_devices() -> list[str]:
    """Names of input-capable devices; empty when audio enumeration fails."""
    try:
        import sounddevice

        return [
            device["name"]
            for device in sounddevice.query_devices()
            if device.get("max_input_channels", 0) > 0
        ]
    except Exception as exc:
        log.warning("microphone enumeration failed: %s", exc)
        return []


class SettingsDialog(QDialog):
    saved = Signal(object)  # Config

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setProperty("role", "window")
        self.setWindowTitle("DarkeVox settings")
        self.setMinimumWidth(460)
        self._cfg = copy.deepcopy(cfg)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_general(), "General")
        tabs.addTab(self._build_polish(), "Polish")
        tabs.addTab(self._build_injection(), "Injection")
        layout.addWidget(tabs)
        self._build_buttons(layout)

    # ---- pages ----

    def _build_general(self) -> QWidget:
        page, box = _page()
        card, cbox = _card()
        self._hold = QLineEdit(self._cfg.hotkeys.hold)
        self._toggle = QLineEdit(self._cfg.hotkeys.toggle)
        _field(cbox, "Hold to talk", self._hold)
        _field(cbox, "Toggle dictation", self._toggle)
        self._hotkey_error = _caption("")
        self._hotkey_error.setProperty("role", "error")
        self._hotkey_error.hide()
        cbox.addWidget(self._hotkey_error)
        box.addWidget(card)

        card, cbox = _card()
        self._stt_model = QComboBox()
        self._stt_model.addItems(STT_MODELS)
        self._stt_model.setCurrentText(self._cfg.stt.model)
        _field(cbox, "Speech model", self._stt_model)
        self._mic = QComboBox()
        self._mic.addItem(_DEFAULT_MIC)
        for name in list_input_devices():
            self._mic.addItem(name)
        current = self._cfg.stt.input_device.strip()
        if current:
            index = self._mic.findText(current)
            if index < 0:
                self._mic.addItem(current)
                index = self._mic.count() - 1
            self._mic.setCurrentIndex(index)
        _field(cbox, "Microphone", self._mic)
        cbox.addWidget(
            _caption(
                "small.en is the accuracy sweet spot on CPU. large-v3-turbo is worth it "
                "only with an NVIDIA GPU. Model changes apply after a restart."
            )
        )
        box.addWidget(card)
        box.addStretch(1)
        return page

    def _build_polish(self) -> QWidget:
        page, box = _page()
        card, cbox = _card()
        self._backend = QComboBox()
        self._backend.addItems(BACKENDS)
        self._backend.setCurrentText(self._cfg.llm.backend)
        _field(cbox, "Backend", self._backend)
        self._ollama_url = QLineEdit(self._cfg.llm.ollama_url)
        self._ollama_url_row = _field(cbox, "Ollama URL", self._ollama_url)
        self._polish_model = QLineEdit(self._cfg.llm.polish_model)
        self._polish_model_row = _field(cbox, "Ollama model", self._polish_model)
        self._openrouter_model = QLineEdit(self._cfg.llm.openrouter_model)
        self._openrouter_model.setPlaceholderText("pick from openrouter.ai/models (free filter)")
        self._openrouter_model_row = _field(cbox, "OpenRouter model", self._openrouter_model)
        self._openrouter_key = QLineEdit()
        self._openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._openrouter_key.setPlaceholderText("unchanged if left empty")
        self._openrouter_key_row = _field(cbox, "OpenRouter key", self._openrouter_key)
        self._tone = QComboBox()
        self._tone.addItems(TONES)
        self._tone.setCurrentText(self._cfg.polish.default_tone)
        _field(cbox, "Default tone", self._tone)
        self._timeout = QDoubleSpinBox()
        self._timeout.setRange(3.0, 30.0)
        self._timeout.setSuffix(" s")
        self._timeout.setValue(self._cfg.llm.timeout_s)
        _field(cbox, "Polish timeout", self._timeout)
        cbox.addWidget(
            _caption(
                "Ollama runs on this machine and costs nothing. OpenRouter's free model "
                "list rotates; check it before relying on a name. Keys are stored in "
                "Windows Credential Manager, not in the config file."
            )
        )
        box.addWidget(card)
        box.addStretch(1)
        self._backend.currentTextChanged.connect(self._sync_backend_fields)
        self._sync_backend_fields(self._backend.currentText())
        return page

    def _sync_backend_fields(self, backend: str) -> None:
        """Only the active backend's fields are visible: seven inputs of
        cognitive load collapse to the three the user actually needs."""
        ollama = backend == "ollama"
        self._ollama_url_row.setVisible(ollama)
        self._polish_model_row.setVisible(ollama)
        self._openrouter_model_row.setVisible(not ollama)
        self._openrouter_key_row.setVisible(not ollama)

    def _build_injection(self) -> QWidget:
        page, box = _page()
        card, cbox = _card()
        self._method = QComboBox()
        self._method.addItems(INJECT_METHODS)
        self._method.setCurrentText(self._cfg.inject.method)
        _field(cbox, "Method", self._method)
        cbox.addWidget(
            _caption("paste suits almost everything; type is for apps that block Ctrl+V.")
        )
        box.addWidget(card)
        box.addStretch(1)
        return page

    def _build_buttons(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = AnimatedButton("Cancel", "secondary")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        save = AnimatedButton("Save", "primary")
        save.clicked.connect(self._save)
        row.addWidget(save)
        layout.addLayout(row)

    # ---- validation and save ----

    def _combo_error(self) -> str:
        """Syntax first, then intra-app conflicts: equal or subset combos
        would both fire on one press."""
        combos = {}
        for name, edit in (("hold", self._hold), ("toggle", self._toggle)):
            try:
                combos[name] = parse_combo(edit.text())
                _mark_invalid(edit, False)
            except ValueError:
                _mark_invalid(edit, True)
                return "Use a combo like ctrl+alt+space."
        hold, toggle = combos["hold"], combos["toggle"]
        if hold <= toggle or toggle <= hold:
            _mark_invalid(self._hold, True)
            _mark_invalid(self._toggle, True)
            return "Hold and toggle must differ, and neither may contain the other."
        return ""

    def _show_error(self, message: str) -> None:
        self._hotkey_error.setText(message)
        if not self._hotkey_error.isVisible() and motion.enabled():
            effect = QGraphicsOpacityEffect(self._hotkey_error)
            effect.setOpacity(0.0)
            self._hotkey_error.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", effect)
            anim.setDuration(motion.duration(150))
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: self._hotkey_error.setGraphicsEffect(None))
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._hotkey_error.show()

    def _save(self) -> None:
        error = self._combo_error()
        if error:
            self._show_error(error)
            return
        self._hotkey_error.hide()
        cfg = self._cfg
        cfg.hotkeys.hold = self._hold.text().strip()
        cfg.hotkeys.toggle = self._toggle.text().strip()
        cfg.stt.model = self._stt_model.currentText()
        mic = self._mic.currentText()
        cfg.stt.input_device = "" if mic == _DEFAULT_MIC else mic
        cfg.llm.backend = self._backend.currentText()
        cfg.llm.ollama_url = self._ollama_url.text().strip()
        cfg.llm.polish_model = self._polish_model.text().strip()
        cfg.llm.openrouter_model = self._openrouter_model.text().strip()
        cfg.llm.timeout_s = float(self._timeout.value())
        cfg.polish.default_tone = self._tone.currentText()
        cfg.inject.method = self._method.currentText()
        key = self._openrouter_key.text().strip()
        if key:
            set_api_key("openrouter", key)
        self.saved.emit(cfg)
        self.accept()
