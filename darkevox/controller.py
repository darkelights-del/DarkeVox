"""Dictation controller: hotkeys -> capture -> STT [-> polish] -> inject.

Threading (see darkevox-guidelines): pynput callbacks arrive on the listener
thread and only emit signals; the Qt main thread runs the slots that touch
capture and timers; the single worker thread owns the STT model and the
inject step. UI objects never appear here beyond signal emission.

The polish hook is the phase 2 seam: ``set_polisher`` installs a callable
``(transcript) -> PolishOutcome``; with none installed, raw transcripts
inject directly.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from darkevox.audio.capture import SAMPLE_RATE, CaptureError, MicrophoneCapture
from darkevox.audio.segmenter import PauseSegmenter
from darkevox.config import Config
from darkevox.inject.injector import Injector
from darkevox.logging_setup import format_timings, stage
from darkevox.state import AppState
from darkevox.stt.engine import SttEngine, build_initial_prompt

log = logging.getLogger(__name__)

_MIN_UTTERANCE_S = 0.25  # shorter than this is a key tap, not speech


@dataclass
class PolishOutcome:
    text: str
    used_grounding: bool = False
    fell_back: bool = False
    note: str = ""  # user-visible when fell_back


Polisher = Callable[[str], PolishOutcome]


class DictationController(QObject):
    state_changed = Signal(str, str)  # (state, label) for HUD and tray
    grounded_changed = Signal(bool)  # last polish used retrieved context
    recording_changed = Signal(bool)
    injected = Signal(int)  # word count for the done flash
    notice = Signal(str)  # non-fatal, user-visible ("Polish timed out...")
    error = Signal(str)

    _hold_start_requested = Signal()
    _hold_end_requested = Signal()
    _toggle_requested = Signal()

    def __init__(
        self,
        cfg: Config,
        state: AppState,
        engine: SttEngine,
        injector: Injector,
        capture_factory: Callable[[], MicrophoneCapture] = MicrophoneCapture,
    ) -> None:
        super().__init__()
        self._cfg = cfg
        self._state = state
        self._engine = engine
        self._injector = injector
        self._capture_factory = capture_factory
        self._capture: MicrophoneCapture | None = None
        self._segmenter: PauseSegmenter | None = None
        self._segments: list[str] = []  # touched only by the worker thread
        self._polisher: Polisher | None = None
        self._jobs: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._worker = threading.Thread(target=self._work, daemon=True, name="darkevox-worker")
        self._worker.start()
        self._drain_timer = QTimer(self)
        self._drain_timer.setInterval(250)
        self._drain_timer.timeout.connect(self._drain_toggle_audio)
        # Hotkey callbacks land on the pynput thread; these signals hop the
        # actual work onto the main thread where timers and capture live.
        self._hold_start_requested.connect(self._on_hold_start)
        self._hold_end_requested.connect(self._on_hold_end)
        self._toggle_requested.connect(self._on_toggle)

    def set_polisher(self, polisher: Polisher | None) -> None:
        self._polisher = polisher

    def warm_load(self) -> None:
        self._jobs.put(("load", None))

    # ---- entry points safe to call from any thread ----

    def hold_start(self) -> None:
        self._hold_start_requested.emit()

    def hold_end(self) -> None:
        self._hold_end_requested.emit()

    def toggle(self) -> None:
        self._toggle_requested.emit()

    # ---- main-thread slots ----

    def _on_hold_start(self) -> None:
        if self._state.recording:
            return
        self._start_capture()
        if self._capture is not None:
            self.state_changed.emit("listening", "listening")

    def _on_hold_end(self) -> None:
        if self._segmenter is not None or self._capture is None:
            return  # toggle session active, or capture never started
        audio = self._capture.stop()
        self._capture = None
        self._set_recording(False)
        if audio.size < _MIN_UTTERANCE_S * SAMPLE_RATE:
            self.state_changed.emit("done", "no speech")
            return
        self.state_changed.emit("transcribing", "transcribing")
        self._jobs.put(("utterance", audio))

    def _on_toggle(self) -> None:
        if self._segmenter is None:
            if self._state.recording:
                return  # a hold is in progress; toggle waits its turn
            self._start_capture()
            if self._capture is None:
                return
            self._segmenter = PauseSegmenter()
            self._drain_timer.start()
            self.state_changed.emit("listening", "listening (toggle)")
        else:
            self._drain_timer.stop()
            assert self._capture is not None
            tail = self._capture.stop()
            self._capture = None
            segmenter = self._segmenter
            self._segmenter = None
            self._set_recording(False)
            segment = segmenter.feed(tail) if tail.size else None
            if segment is not None:
                self._jobs.put(("segment", segment))
            remainder = segmenter.flush()
            if remainder is not None:
                self._jobs.put(("segment", remainder))
            self.state_changed.emit("transcribing", "transcribing")
            self._jobs.put(("finalize", None))

    def _drain_toggle_audio(self) -> None:
        if self._capture is None or self._segmenter is None:
            return
        block = self._capture.drain()
        if block.size == 0:
            return
        segment = self._segmenter.feed(block)
        if segment is not None:
            self._jobs.put(("segment", segment))

    def _start_capture(self) -> None:
        try:
            capture = self._capture_factory()
            capture.start()
        except CaptureError as exc:
            log.error("capture failed: %s", exc)
            self.error.emit("No microphone found.")
            return
        self._capture = capture
        self._set_recording(True)

    def _set_recording(self, recording: bool) -> None:
        self._state.recording = recording
        self.recording_changed.emit(recording)

    # ---- worker thread ----

    def _initial_prompt(self) -> str | None:
        return build_initial_prompt(self._cfg.dictionary.terms)

    def _work(self) -> None:
        while True:
            kind, payload = self._jobs.get()
            try:
                self._handle_job(kind, payload)
            except Exception:
                log.exception("worker job %s failed", kind)
                self.error.emit("Dictation failed. Details are in the log.")
            finally:
                self._jobs.task_done()

    def _handle_job(self, kind: str, payload: Any) -> None:
        if kind == "load":
            try:
                self._engine.load()
            except Exception:
                log.exception("stt model load failed")
                self.error.emit("Speech model failed to load. Check the log.")
        elif kind == "utterance":
            timings: dict[str, float] = {}
            with stage(timings, "stt"):
                result = self._engine.transcribe(payload, self._initial_prompt())
            self._finish(result.text, timings)
        elif kind == "segment":
            result = self._engine.transcribe(payload, self._initial_prompt())
            self._segments.append(result.text)
        elif kind == "finalize":
            text = " ".join(part for part in self._segments if part).strip()
            self._segments.clear()
            self._finish(text, {})

    def _finish(self, text: str, timings: dict[str, float]) -> None:
        # A newer recording owns the HUD; this dictation still injects, but its
        # progress/done signals stay quiet instead of clobbering "listening".
        quiet = self._state.recording
        if not text:
            if not quiet:
                self.state_changed.emit("done", "no speech")
            return
        grounded = False
        if self._polisher is not None and self._state.tone != "verbatim":
            if not quiet:
                self.state_changed.emit("polishing", "polishing")
            with stage(timings, "polish"):
                outcome = self._polisher(text)
            text = outcome.text
            grounded = outcome.used_grounding
            if outcome.fell_back:
                self.notice.emit(outcome.note or "Polish unavailable. Raw transcript injected.")
        self.grounded_changed.emit(grounded)
        with stage(timings, "inject"):
            report = self._injector.inject(text)
        log.info("dictation %s", format_timings(timings))
        if not report.ok:
            self.error.emit(report.note or "Injection failed.")
        elif self._state.recording:
            log.info("dictation finished during a new recording; HUD flash skipped")
        else:
            self.injected.emit(len(text.split()))
