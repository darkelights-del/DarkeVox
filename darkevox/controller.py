"""Dictation controller: hotkeys/panel -> capture -> STT [-> polish] -> inject.

Threading (see darkevox-guidelines): pynput callbacks arrive on the listener
thread and only emit signals; the Qt main thread runs the slots that touch
capture and timers; the single worker thread owns the STT model, polish, and
the inject step. UI objects never appear here beyond signal emission.

Every session streams: the pause segmenter cuts at natural breaths, each
segment transcribes eagerly on the worker, and partial_transcript carries
the accumulated text live. A session has a sink: "inject" (hotkeys: polish
and inject automatically) or "panel" (the floating panel receives the raw
transcript and drives polish/inject itself via request_polish/request_inject).
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from darkevox.audio.capture import SAMPLE_RATE, CaptureError, MicrophoneCapture
from darkevox.audio.segmenter import PauseSegmenter
from darkevox.config import Config
from darkevox.inject.injector import Injector
from darkevox.logging_setup import format_timings, stage
from darkevox.state import AppState
from darkevox.stt.engine import SttEngine, build_initial_prompt
from darkevox.ui import status

log = logging.getLogger(__name__)

_MIN_UTTERANCE_S = 0.25  # shorter than this is a key tap, not speech


@dataclass
class PolishOutcome:
    text: str
    used_grounding: bool = False
    fell_back: bool = False
    note: str = ""  # user-visible when fell_back


Polisher = Callable[[str, str], PolishOutcome]  # (text, tone) -> outcome


class DictationController(QObject):
    state_changed = Signal(str, str)  # (state, label) for HUD and tray
    partial_transcript = Signal(str, str)  # (accumulated raw text, sink it belongs to)
    session_finished = Signal(str)  # panel sessions: full raw transcript at stop
    polish_ready = Signal(str, str, bool)  # (text, tone, fell_back) for the panel
    grounded_changed = Signal(bool)  # last polish used retrieved context
    recording_changed = Signal(bool)
    audio_level = Signal(float)  # live input level 0..1 while recording
    injected = Signal(int)  # word count for the done flash
    notice = Signal(str)  # non-fatal, user-visible ("Polish timed out...")
    error = Signal(str)

    _hold_start_requested = Signal(str)  # sink
    _hold_end_requested = Signal()
    _toggle_requested = Signal(str)  # sink

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
        self._modifier_guard: Callable[[], bool] | None = None
        self._focus_restorer: Callable[[], bool] | None = None
        self._stt_ready = True
        self._sleep: Callable[[float], None] = time.sleep
        self._capture: MicrophoneCapture | None = None
        self._segmenter: PauseSegmenter | None = None
        self._session_kind: str | None = None  # hold | toggle
        self._session_sink: str = "inject"
        self._session_samples = 0  # main thread; total audio captured this session
        self._listen_started = 0.0  # main thread; anchors the live duration label
        self._listen_shown_s = 0
        self._segments: list[str] = []  # touched only by the worker thread
        self._session_stt_ms = 0.0  # worker thread; STT time accumulated this session
        self._polisher: Polisher | None = None
        self._jobs: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._worker = threading.Thread(target=self._work, daemon=True, name="darkevox-worker")
        self._worker.start()
        self._drain_timer = QTimer(self)
        self._drain_timer.setInterval(250)
        self._drain_timer.timeout.connect(self._drain_live_audio)
        # Hotkey callbacks land on the pynput thread; these signals hop the
        # actual work onto the main thread where timers and capture live.
        self._hold_start_requested.connect(self._on_hold_start)
        self._hold_end_requested.connect(self._on_hold_end)
        self._toggle_requested.connect(self._on_toggle)

    @property
    def session_sink(self) -> str:
        return self._session_sink

    def set_polisher(self, polisher: Polisher | None) -> None:
        self._polisher = polisher

    def set_injector(self, injector: Injector) -> None:
        """Settings apply live: a method change swaps the injector in place."""
        self._injector = injector

    def set_stt_ready(self, ready: bool) -> None:
        self._stt_ready = ready

    def set_modifier_guard(self, guard: Callable[[], bool] | None) -> None:
        """guard() returns True while hotkey modifiers are physically held.

        Injection waits for release: a synthesized Ctrl+V while the user's
        fingers are still on Ctrl+Alt reaches the app as Ctrl+Alt+V, which
        pastes nothing.
        """
        self._modifier_guard = guard

    def set_focus_restorer(self, restorer: Callable[[], bool] | None) -> None:
        """Panel Insert stole focus by being clicked; restorer() re-activates
        the window the user was actually working in before we paste."""
        self._focus_restorer = restorer

    def warm_load(self) -> None:
        self._jobs.put(("load", None))

    # ---- entry points safe to call from any thread ----

    def hold_start(self) -> None:
        self._hold_start_requested.emit("inject")

    def hold_end(self) -> None:
        self._hold_end_requested.emit()

    def toggle(self) -> None:
        self._toggle_requested.emit("inject")

    def panel_press(self) -> None:
        """Mouse push-to-talk from the panel's mic button."""
        self._hold_start_requested.emit("panel")

    def panel_release(self) -> None:
        self._hold_end_requested.emit()

    def panel_click(self) -> None:
        """Mouse click on the mic: toggle a panel session."""
        self._toggle_requested.emit("panel")

    def request_polish(self, text: str, tone: str) -> None:
        """On-demand polish for the panel (the app's one polish surface)."""
        self._jobs.put(("panel_polish", (text.strip(), tone)))

    def request_inject(self, text: str) -> None:
        self._jobs.put(("panel_inject", text))

    # ---- main-thread slots ----

    def _on_hold_start(self, sink: str) -> None:
        if self._session_kind is not None:
            return
        self._start_session("hold", sink)

    def _on_hold_end(self) -> None:
        if self._session_kind != "hold":
            return
        self._end_session()

    def _on_toggle(self, sink: str) -> None:
        if self._session_kind is None:
            self._start_session("toggle", sink)
        elif self._session_kind == "toggle":
            self._end_session()
        # a hold in progress ignores toggle presses

    def _start_session(self, kind: str, sink: str) -> None:
        if not self._stt_ready:
            # Speaking into a missing model would transcribe nothing and lose
            # the words; refuse up front with the directive message.
            self.error.emit("Speech model missing. Relaunch DarkeVox to download it.")
            return
        try:
            capture = self._capture_factory()
            capture.start()
        except CaptureError as exc:
            log.error("capture failed: %s", exc)
            self.error.emit("No microphone found.")
            return
        self._capture = capture
        self._segmenter = PauseSegmenter()
        self._session_kind = kind
        self._session_sink = sink
        self._session_samples = 0
        self._listen_started = time.monotonic()
        self._listen_shown_s = 0
        self._drain_timer.start()
        self._set_recording(True)
        if sink == "inject":
            self.state_changed.emit(status.LISTENING, status.listening(0))

    def _end_session(self) -> None:
        self._drain_timer.stop()
        capture = self._capture
        segmenter = self._segmenter
        sink = self._session_sink
        self._capture = None
        self._segmenter = None
        self._session_kind = None
        self._set_recording(False)
        if capture is None or segmenter is None:
            return
        tail = capture.stop()
        self._session_samples += tail.size
        if self._session_samples < _MIN_UTTERANCE_S * SAMPLE_RATE:
            # A key tap, not speech: transcribing it wastes an STT call and a
            # short blip can hallucinate a phantom word into the document.
            segmenter.flush()
            if sink == "panel":
                self.session_finished.emit("")
            else:
                self.state_changed.emit(status.NO_SPEECH, status.no_speech())
            return
        segment = segmenter.feed(tail) if tail.size else None
        if segment is not None:
            self._jobs.put(("segment", (segment, sink)))
        remainder = segmenter.flush()
        if remainder is not None:
            self._jobs.put(("segment", (remainder, sink)))
        if sink == "inject":
            self.state_changed.emit(status.TRANSCRIBING, status.transcribing())
        self._jobs.put(("finalize", sink))

    def _drain_live_audio(self) -> None:
        if self._capture is None or self._segmenter is None:
            return
        if self._session_sink == "inject":
            # The HUD's listening heartbeat: same string the panel shows,
            # re-emitted once per whole second.
            elapsed = int(time.monotonic() - self._listen_started)
            if elapsed != self._listen_shown_s:
                self._listen_shown_s = elapsed
                self.state_changed.emit(status.LISTENING, status.listening(elapsed))
        block = self._capture.drain()
        if block.size == 0:
            return
        self._session_samples += block.size
        rms = float(np.sqrt(np.mean(np.square(block))))
        self.audio_level.emit(min(1.0, rms / 0.08))
        segment = self._segmenter.feed(block)
        if segment is not None:
            # The sink rides inside the job: reading self._session_sink later
            # (worker or queued slot) races a newer session changing it.
            self._jobs.put(("segment", (segment, self._session_sink)))

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
        elif kind == "segment":
            audio, sink = payload
            result = self._engine.transcribe(audio, self._initial_prompt())
            log.info("segment stt=%.0fms audio=%.1fs", result.elapsed_ms, result.audio_s)
            self._session_stt_ms += result.elapsed_ms
            if result.text:
                self._segments.append(result.text)
                self.partial_transcript.emit(" ".join(self._segments), sink)
        elif kind == "finalize":
            text = " ".join(part for part in self._segments if part).strip()
            stt_ms = self._session_stt_ms
            self._segments.clear()
            self._session_stt_ms = 0.0
            if payload == "panel":
                log.info("panel session stt=%.0fms", stt_ms)
                self.session_finished.emit(text)
            else:
                self._finish(text, {"stt": stt_ms})
        elif kind == "panel_polish":
            self._panel_polish(*payload)
        elif kind == "panel_inject":
            self._panel_inject(payload)

    def _panel_polish(self, text: str, tone: str) -> None:
        if not text or tone == "verbatim" or self._polisher is None:
            self.polish_ready.emit(text, tone, False)
            return
        outcome = self._polisher(text, tone)
        if outcome.fell_back:
            self.notice.emit(outcome.note or "Polish unavailable.")
        self.grounded_changed.emit(outcome.used_grounding)
        self.polish_ready.emit(outcome.text, tone, outcome.fell_back)

    def _panel_inject(self, text: str) -> None:
        if not text:
            return
        self._wait_for_modifier_release()
        if self._focus_restorer is not None:
            try:
                if self._focus_restorer():
                    self._sleep(0.15)  # give Windows a beat to move focus
            except Exception:
                log.exception("focus restore failed")
        report = self._injector.inject(text)
        if report.ok:
            self.injected.emit(len(text.split()))
        else:
            self.error.emit(report.note or "Injection failed.")

    def _wait_for_modifier_release(self, timeout_s: float = 2.0) -> None:
        guard = self._modifier_guard
        if guard is None:
            return
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                if not guard():
                    return
            except Exception:
                return
            self._sleep(0.03)

    def _finish(self, text: str, timings: dict[str, float]) -> None:
        # A newer recording owns the HUD; this dictation still injects, but its
        # progress/done signals stay quiet instead of clobbering "listening".
        quiet = self._state.recording
        if not text:
            if not quiet:
                self.state_changed.emit(status.NO_SPEECH, status.no_speech())
            return
        grounded = False
        if self._polisher is not None and self._state.tone != "verbatim":
            if not quiet:
                self.state_changed.emit(status.POLISHING, status.polishing(self._state.tone))
            with stage(timings, "polish"):
                outcome = self._polisher(text, self._state.tone)
            text = outcome.text
            grounded = outcome.used_grounding
            if outcome.fell_back:
                note = outcome.note or "Polish unavailable."
                self.notice.emit(f"{note} Raw transcript injected.")
        self.grounded_changed.emit(grounded)
        with stage(timings, "inject"):
            self._wait_for_modifier_release()
            report = self._injector.inject(text)
        log.info("dictation %s", format_timings(timings))
        if not report.ok:
            self.error.emit(report.note or "Injection failed.")
        elif self._state.recording:
            log.info("dictation finished during a new recording; HUD flash skipped")
        else:
            count = len(text.split())
            # injected first (the HUD swell keys on entering the state),
            # then state_changed so the tray reaches a terminal state too.
            self.injected.emit(count)
            self.state_changed.emit(status.INSERTED, status.inserted(count))
