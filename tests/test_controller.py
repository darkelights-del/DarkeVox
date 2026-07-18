"""End-to-end controller flow with fakes: hold -> capture -> STT -> inject.

Runs Qt offscreen; exercises the real signal wiring and worker thread.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from darkevox.config import Config
from darkevox.controller import DictationController, PolishOutcome
from darkevox.inject.clipboard import InMemoryClipboard
from darkevox.inject.injector import Injector
from darkevox.state import AppState
from darkevox.stt.engine import TranscriptionResult


class FakeEngine:
    def __init__(self, text: str = "hello world", texts: list[str] | None = None) -> None:
        self.text = text
        self.texts = list(texts or [])
        self.loaded = False
        self.prompts: list[str | None] = []

    def load(self) -> None:
        self.loaded = True

    def transcribe(self, audio: np.ndarray, initial_prompt: str | None = None):
        self.prompts.append(initial_prompt)
        text = self.texts.pop(0) if self.texts else self.text
        return TranscriptionResult(text, "en", audio.size / 16000, 5.0)


class FakeCapture:
    def __init__(self, audio: np.ndarray, drains: list[np.ndarray] | None = None) -> None:
        self._audio = audio
        self._drains = list(drains or [])

    def start(self) -> None:
        pass

    def drain(self) -> np.ndarray:
        if self._drains:
            return self._drains.pop(0)
        return np.empty(0, dtype=np.float32)

    def stop(self) -> np.ndarray:
        return self._audio


class FakeKeys:
    def __init__(self) -> None:
        self.pastes = 0

    def paste(self) -> None:
        self.pastes += 1

    def type_text(self, text: str) -> None:
        pass


def _pump_until(app: QApplication, predicate, timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _controller(qapp: QApplication, engine: FakeEngine, clipboard: InMemoryClipboard):
    cfg = Config()
    cfg.dictionary.terms = ["Jake"]
    state = AppState()
    injector = Injector(clipboard, FakeKeys(), restore_delay_ms=0, sleep=lambda _s: None)
    audio = np.ones(16000, dtype=np.float32)
    controller = DictationController(
        cfg, state, engine, injector, capture_factory=lambda: FakeCapture(audio)
    )
    return controller, state


def test_hold_flow_transcribes_and_injects(qapp: QApplication) -> None:
    engine = FakeEngine("hello world")
    clipboard = InMemoryClipboard()
    controller, _state = _controller(qapp, engine, clipboard)
    injected_words: list[int] = []
    controller.injected.connect(injected_words.append)

    controller.hold_start()
    assert _pump_until(qapp, lambda: _state_recording(controller))
    controller.hold_end()
    assert _pump_until(qapp, lambda: bool(injected_words))
    assert injected_words == [2]
    assert clipboard.get_text() == "hello world"  # nothing prior, transcript stays
    assert engine.prompts == ["Glossary: Jake."]


def _state_recording(controller: DictationController) -> bool:
    return controller._state.recording  # test peeks; fine for a fixture-owned object


def test_polisher_hook_runs_between_stt_and_inject(qapp: QApplication) -> None:
    engine = FakeEngine("raw words here")
    clipboard = InMemoryClipboard()
    controller, state = _controller(qapp, engine, clipboard)
    state.tone = "email"
    controller.set_polisher(lambda text, tone: PolishOutcome(text.upper(), used_grounding=True))
    done: list[int] = []
    controller.injected.connect(done.append)
    grounded: list[bool] = []
    controller.grounded_changed.connect(grounded.append)

    controller.hold_start()
    _pump_until(qapp, lambda: _state_recording(controller))
    controller.hold_end()
    assert _pump_until(qapp, lambda: bool(done))
    assert clipboard.get_text() == "RAW WORDS HERE"
    assert grounded == [True]


def test_polisher_fallback_emits_its_note(qapp: QApplication) -> None:
    engine = FakeEngine("the raw words")
    clipboard = InMemoryClipboard()
    controller, state = _controller(qapp, engine, clipboard)
    state.tone = "email"
    controller.set_polisher(
        lambda text, tone: PolishOutcome(text, fell_back=True, note="Ollama isn't running.")
    )
    notices: list[str] = []
    controller.notice.connect(notices.append)
    done: list[int] = []
    controller.injected.connect(done.append)

    controller.hold_start()
    _pump_until(qapp, lambda: _state_recording(controller))
    controller.hold_end()
    assert _pump_until(qapp, lambda: bool(done))
    assert notices == ["Ollama isn't running."]
    assert clipboard.get_text() == "the raw words"


def test_toggle_flow_streams_segments_and_joins(qapp: QApplication) -> None:
    engine = FakeEngine(texts=["part one", "part two"])
    clipboard = InMemoryClipboard()
    cfg = Config()
    state = AppState(tone="verbatim")
    injector = Injector(clipboard, FakeKeys(), restore_delay_ms=0, sleep=lambda _s: None)
    # Drain feed: 9 s of speech, then 1.2 s of silence -> the segmenter cuts
    # segment one mid-recording; the 1 s tail at stop becomes segment two.
    speech = np.full(9 * 16000, 0.2, dtype=np.float32)
    silence = np.zeros(int(1.2 * 16000), dtype=np.float32)
    tail = np.full(16000, 0.2, dtype=np.float32)
    capture = FakeCapture(tail, drains=[speech, silence])
    controller = DictationController(
        cfg, state, engine, injector, capture_factory=lambda: capture
    )
    done: list[int] = []
    controller.injected.connect(done.append)

    controller.toggle()
    assert _pump_until(qapp, lambda: _state_recording(controller))
    assert _pump_until(qapp, lambda: len(engine.prompts) >= 1)  # eager segment STT
    controller.toggle()
    assert _pump_until(qapp, lambda: bool(done))
    assert clipboard.get_text() == "part one part two"
    assert len(engine.prompts) == 2  # two segments, never one blob


def test_panel_session_streams_and_delivers_raw(qapp: QApplication) -> None:
    engine = FakeEngine("hello there")
    clipboard = InMemoryClipboard()
    controller, _state = _controller(qapp, engine, clipboard)
    partials: list[tuple[str, str]] = []
    controller.partial_transcript.connect(lambda text, sink: partials.append((text, sink)))
    finished: list[str] = []
    controller.session_finished.connect(finished.append)

    controller.panel_click()
    assert _pump_until(qapp, lambda: _state_recording(controller))
    assert controller.session_sink == "panel"
    controller.panel_click()
    assert _pump_until(qapp, lambda: bool(finished))
    assert finished == ["hello there"]
    assert partials == [("hello there", "panel")]  # streamed live, sink attached
    assert clipboard.get_text() is None  # panel sessions never auto-inject


def test_panel_polish_and_inject_on_demand(qapp: QApplication) -> None:
    engine = FakeEngine()
    clipboard = InMemoryClipboard()
    controller, _state = _controller(qapp, engine, clipboard)
    controller._sleep = lambda _s: None
    controller.set_polisher(lambda text, tone: PolishOutcome(f"[{tone}] {text}"))
    ready: list[tuple[str, str, bool]] = []
    controller.panel_polish_ready.connect(lambda t, tone, fb: ready.append((t, tone, fb)))

    controller.request_polish("hi there", "notes")
    assert _pump_until(qapp, lambda: bool(ready))
    assert ready == [("[notes] hi there", "notes", False)]

    restores: list[bool] = []

    def restorer() -> bool:
        restores.append(True)
        return True

    controller.set_focus_restorer(restorer)
    done: list[int] = []
    controller.injected.connect(done.append)
    controller.request_inject("final text")
    assert _pump_until(qapp, lambda: bool(done))
    assert done == [2]
    assert clipboard.get_text() == "final text"
    assert restores == [True]  # focus went back to the user's app before pasting


def test_panel_polish_verbatim_and_missing_polisher_pass_through(qapp: QApplication) -> None:
    engine = FakeEngine()
    clipboard = InMemoryClipboard()
    controller, _state = _controller(qapp, engine, clipboard)
    ready: list[tuple[str, str, bool]] = []
    controller.panel_polish_ready.connect(lambda t, tone, fb: ready.append((t, tone, fb)))

    controller.request_polish("as spoken", "verbatim")  # no polisher installed either
    assert _pump_until(qapp, lambda: bool(ready))
    assert ready == [("as spoken", "verbatim", False)]


def test_injection_waits_for_modifier_release(qapp: QApplication) -> None:
    engine = FakeEngine("waited words")
    clipboard = InMemoryClipboard()
    controller, state = _controller(qapp, engine, clipboard)
    state.tone = "verbatim"
    controller._sleep = lambda _s: None  # keep the wait loop instant in tests
    guard_calls: list[bool] = []

    def guard() -> bool:
        guard_calls.append(True)
        return len(guard_calls) < 3  # fingers still on Ctrl+Alt for two polls

    controller.set_modifier_guard(guard)
    done: list[int] = []
    controller.injected.connect(done.append)

    controller.hold_start()
    _pump_until(qapp, lambda: _state_recording(controller))
    controller.hold_end()
    assert _pump_until(qapp, lambda: bool(done))
    assert len(guard_calls) >= 3  # injection held off until the guard cleared
    assert clipboard.get_text() == "waited words"


def test_verbatim_tone_skips_polisher(qapp: QApplication) -> None:
    engine = FakeEngine("keep me raw")
    clipboard = InMemoryClipboard()
    controller, state = _controller(qapp, engine, clipboard)
    state.tone = "verbatim"
    calls: list[str] = []

    def polisher(text: str, tone: str) -> PolishOutcome:
        calls.append(text)
        return PolishOutcome("SHOULD NOT APPEAR")

    controller.set_polisher(polisher)
    done: list[int] = []
    controller.injected.connect(done.append)

    controller.hold_start()
    _pump_until(qapp, lambda: _state_recording(controller))
    controller.hold_end()
    assert _pump_until(qapp, lambda: bool(done))
    assert calls == []
    assert clipboard.get_text() == "keep me raw"
