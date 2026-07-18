"""Settings dialog: hotkeys, speech model, polish backend, tone, injection.

Edits a deep copy; the caller receives it via the saved signal only after
validation passes. API keys go straight to the keyring, never into the TOML.
"""

from __future__ import annotations

import copy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from darkevox.audio.hotkeys import parse_combo
from darkevox.config import BACKENDS, INJECT_METHODS, STT_MODELS, TONES, Config, set_api_key


def _section(title: str) -> QLabel:
    label = QLabel(title)
    label.setProperty("role", "section")
    return label


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "caption")
    label.setWordWrap(True)
    return label


class SettingsDialog(QDialog):
    saved = Signal(object)  # Config

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setWindowTitle("DarkeVox settings")
        self.setMinimumWidth(420)
        self._cfg = copy.deepcopy(cfg)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self._build_hotkeys(layout)
        self._build_speech(layout)
        self._build_polish(layout)
        self._build_injection(layout)
        self._build_buttons(layout)

    def _build_hotkeys(self, layout: QVBoxLayout) -> None:
        layout.addWidget(_section("Hotkeys"))
        form = QFormLayout()
        self._hold = QLineEdit(self._cfg.hotkeys.hold)
        self._toggle = QLineEdit(self._cfg.hotkeys.toggle)
        form.addRow("Hold to talk", self._hold)
        form.addRow("Toggle dictation", self._toggle)
        layout.addLayout(form)
        self._hotkey_error = _caption("")
        self._hotkey_error.setProperty("role", "error")
        self._hotkey_error.hide()
        layout.addWidget(self._hotkey_error)

    def _build_speech(self, layout: QVBoxLayout) -> None:
        layout.addWidget(_section("Speech"))
        form = QFormLayout()
        self._stt_model = QComboBox()
        self._stt_model.addItems(STT_MODELS)
        self._stt_model.setCurrentText(self._cfg.stt.model)
        form.addRow("Model", self._stt_model)
        layout.addLayout(form)
        layout.addWidget(
            _caption(
                "small.en is the accuracy sweet spot on CPU. large-v3-turbo is worth it "
                "only with an NVIDIA GPU. Model changes apply after a restart."
            )
        )

    def _build_polish(self, layout: QVBoxLayout) -> None:
        layout.addWidget(_section("Polish"))
        form = QFormLayout()
        self._backend = QComboBox()
        self._backend.addItems(BACKENDS)
        self._backend.setCurrentText(self._cfg.llm.backend)
        form.addRow("Backend", self._backend)
        self._ollama_url = QLineEdit(self._cfg.llm.ollama_url)
        form.addRow("Ollama URL", self._ollama_url)
        self._polish_model = QLineEdit(self._cfg.llm.polish_model)
        form.addRow("Ollama model", self._polish_model)
        self._openrouter_model = QLineEdit(self._cfg.llm.openrouter_model)
        self._openrouter_model.setPlaceholderText("pick from openrouter.ai/models (free filter)")
        form.addRow("OpenRouter model", self._openrouter_model)
        self._openrouter_key = QLineEdit()
        self._openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._openrouter_key.setPlaceholderText("unchanged if left empty")
        form.addRow("OpenRouter key", self._openrouter_key)
        self._tone = QComboBox()
        self._tone.addItems(TONES)
        self._tone.setCurrentText(self._cfg.polish.default_tone)
        form.addRow("Default tone", self._tone)
        self._timeout = QDoubleSpinBox()
        self._timeout.setRange(3.0, 30.0)
        self._timeout.setSuffix(" s")
        self._timeout.setValue(self._cfg.llm.timeout_s)
        form.addRow("Polish timeout", self._timeout)
        layout.addLayout(form)
        layout.addWidget(
            _caption(
                "Ollama runs on this machine and costs nothing. OpenRouter's free model "
                "list rotates; check it before relying on a name. Keys are stored in "
                "Windows Credential Manager, not in the config file."
            )
        )

    def _build_injection(self, layout: QVBoxLayout) -> None:
        layout.addWidget(_section("Injection"))
        form = QFormLayout()
        self._method = QComboBox()
        self._method.addItems(INJECT_METHODS)
        self._method.setCurrentText(self._cfg.inject.method)
        form.addRow("Method", self._method)
        layout.addLayout(form)
        layout.addWidget(
            _caption("paste suits almost everything; type is for apps that block Ctrl+V.")
        )

    def _build_buttons(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        save = QPushButton("Save")
        save.setProperty("variant", "primary")
        save.clicked.connect(self._save)
        row.addWidget(save)
        layout.addLayout(row)

    def _save(self) -> None:
        try:
            parse_combo(self._hold.text())
            parse_combo(self._toggle.text())
        except ValueError:
            self._hotkey_error.setText("Use a combo like ctrl+alt+space.")
            self._hotkey_error.show()
            return
        cfg = self._cfg
        cfg.hotkeys.hold = self._hold.text().strip()
        cfg.hotkeys.toggle = self._toggle.text().strip()
        cfg.stt.model = self._stt_model.currentText()
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
