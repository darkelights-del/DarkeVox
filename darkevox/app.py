"""Entry point: single-instance lock, logging, first-run model download,
controller and polish wiring, tray, Qt event loop.

Qt imports stay inside functions so the module is importable (for the lock
and tests) without PySide6 present.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
from dataclasses import fields

from darkevox import APP_NAME
from darkevox import config as config_mod
from darkevox.logging_setup import setup_logging

log = logging.getLogger(__name__)

_ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    """One DarkeVox per session: named mutex on Windows, abstract socket elsewhere.

    The abstract-socket path covers Linux dev boxes; the app itself only
    targets Windows, where the kernel mutex is the standard mechanism.
    """

    def __init__(self, name: str = "darkevox") -> None:
        self._name = name
        self._mutex_handle: int | None = None
        self._sock: socket.socket | None = None

    def acquire(self) -> bool:
        if sys.platform == "win32":
            return self._acquire_windows()
        return self._acquire_posix()

    def _acquire_windows(self) -> bool:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        self._mutex_handle = kernel32.CreateMutexW(None, False, f"Local\\{self._name}")
        return kernel32.GetLastError() != _ERROR_ALREADY_EXISTS

    def _acquire_posix(self) -> bool:
        self._sock = socket.socket(socket.AF_UNIX)
        try:
            self._sock.bind(f"\0{self._name}-lock")
        except OSError:
            return False
        return True


def _keystrokes() -> object:
    from darkevox.inject.injector import NullKeystrokes, PynputKeystrokes

    try:
        return PynputKeystrokes()
    except Exception as exc:  # no display server on a dev box
        log.warning("pynput unavailable (%s); keystrokes disabled", exc)
        return NullKeystrokes()


def _ensure_model(cfg: config_mod.Config) -> bool:
    """Download the STT model on first run, with an honest progress dialog.

    Returns False when the user cancelled or the download failed; the app
    still runs, dictation just reports the model as missing.
    """
    from darkevox.stt import models

    model = cfg.stt.model
    models_root = config_mod.models_dir()
    if models.is_downloaded(model, models_root):
        return True

    from PySide6.QtCore import QTimer

    from darkevox.ui.firstrun import DownloadDialog

    outcome: dict[str, str | bool] = {"done": False, "error": ""}

    def run() -> None:
        try:
            models.download(model, models_root)
            outcome["done"] = True
        except Exception as exc:
            log.exception("model download failed")
            outcome["error"] = str(exc)

    thread = threading.Thread(target=run, daemon=True, name="darkevox-download")
    dialog = DownloadDialog(model, models.APPROX_SIZE_MB.get(model, 500))
    timer = QTimer(dialog)

    def poll() -> None:
        dialog.set_progress(models.downloaded_mb(model, models_root))
        if outcome["done"]:
            timer.stop()
            dialog.accept()
        elif outcome["error"]:
            timer.stop()
            dialog.show_error("Download failed. Check your connection and relaunch DarkeVox.")

    timer.setInterval(300)
    timer.timeout.connect(poll)
    thread.start()
    timer.start()
    accepted = dialog.exec() == dialog.DialogCode.Accepted
    if not accepted:
        log.warning("model download cancelled or failed; dictation disabled this run")
    return accepted and models.is_downloaded(model, models_root)


def _build_polisher(cfg: config_mod.Config, state) -> object | None:
    """Assemble the polish pipeline, or None when the backend is misconfigured."""
    from darkevox.context.provider import NullContextProvider
    from darkevox.controller import PolishOutcome
    from darkevox.polish.llm import LlmError, client_from_config
    from darkevox.polish.pipeline import PolishPipeline

    try:
        client = client_from_config(cfg.llm)
    except LlmError as exc:
        log.warning("polish disabled: %s", exc)
        return None
    pipeline = PolishPipeline(
        client, cfg.llm, cfg.polish, cfg.dictionary.terms, NullContextProvider()
    )

    def polisher(text: str) -> PolishOutcome:
        result = pipeline.polish(text, state.tone)
        return PolishOutcome(
            text=result.text,
            used_grounding=result.used_grounding,
            fell_back=result.fell_back,
            note=result.note,
        )

    return polisher


def _apply_config(target: config_mod.Config, source: config_mod.Config) -> None:
    """Copy section values in place so every holder of the config sees them."""
    for section in (f.name for f in fields(target)):
        src, dst = getattr(source, section), getattr(target, section)
        for name in (f.name for f in fields(dst)):
            setattr(dst, name, getattr(src, name))


def main() -> int:
    cfg = config_mod.load()
    log_file = setup_logging(config_mod.logs_dir(), console=sys.stderr is not None)
    instance = SingleInstance()
    if not instance.acquire():
        log.info("DarkeVox is already running; exiting")
        return 0

    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    from darkevox import update as update_mod
    from darkevox.audio.hotkeys import HotkeyManager
    from darkevox.controller import DictationController
    from darkevox.inject.clipboard import system_clipboard
    from darkevox.inject.injector import Injector
    from darkevox.state import AppState
    from darkevox.stt.engine import SttEngine
    from darkevox.ui.hud import Hud
    from darkevox.ui.settings import SettingsDialog
    from darkevox.ui.theme import qss
    from darkevox.ui.tray import Tray

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(qss())
    log.info("started; config=%s log=%s", config_mod.config_path(), log_file)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        log.warning("system tray unavailable; app has no visible surface")

    tray = Tray()
    tray.quit_requested.connect(app.quit)
    tray.set_status("idle")
    tray.show()

    model_ready = _ensure_model(cfg)
    if not model_ready:
        tray.notify("DarkeVox", "Speech model missing. Relaunch to download it.")

    state = AppState(tone=cfg.polish.default_tone, grounding=cfg.polish.grounding_enabled)
    engine = SttEngine(
        cfg.stt.model,
        config_mod.models_dir(),
        device=cfg.stt.device,
        compute_type=cfg.stt.compute_type,
        language=cfg.stt.language,
    )
    injector = Injector(
        system_clipboard(),
        _keystrokes(),
        method=cfg.inject.method,
        restore_delay_ms=cfg.inject.restore_delay_ms,
    )
    controller = DictationController(cfg, state, engine, injector)
    controller.set_polisher(_build_polisher(cfg, state))
    hud = Hud()

    def on_state(state_name: str, label: str) -> None:
        auto_hide = 1600 if state_name == "done" else None
        hud.show_state(state_name, label, auto_hide_ms=auto_hide)
        tray.set_status(label)

    controller.state_changed.connect(on_state)
    controller.injected.connect(hud.done)
    controller.notice.connect(hud.error)
    controller.error.connect(hud.error)
    controller.error.connect(lambda message: tray.notify("DarkeVox", message))
    controller.recording_changed.connect(tray.set_recording)

    tray.set_tone(state.tone)
    tray.tone_selected.connect(lambda tone: (setattr(state, "tone", tone), tray.set_tone(tone)))
    tray.toggle_dictation.connect(controller.toggle)

    if model_ready:
        controller.warm_load()

    hotkey_slot: list[HotkeyManager] = []

    def start_hotkeys() -> None:
        manager = HotkeyManager(
            cfg.hotkeys.hold,
            cfg.hotkeys.toggle,
            on_hold_start=controller.hold_start,
            on_hold_end=controller.hold_end,
            on_toggle=controller.toggle,
        )
        try:
            manager.start()
            hotkey_slot.append(manager)
        except Exception:
            log.exception("global hotkey listener failed to start")
            tray.notify("DarkeVox", "Global hotkeys could not start. See the log.")

    def on_settings_saved(new_cfg: config_mod.Config) -> None:
        _apply_config(cfg, new_cfg)
        config_mod.save(cfg)
        state.tone = cfg.polish.default_tone
        tray.set_tone(state.tone)
        controller.set_polisher(_build_polisher(cfg, state))
        while hotkey_slot:
            hotkey_slot.pop().stop()
        start_hotkeys()
        log.info("settings applied")

    def open_settings() -> None:
        dialog = SettingsDialog(cfg)
        dialog.saved.connect(on_settings_saved)
        dialog.exec()

    tray.settings_requested.connect(open_settings)

    class _Notifier(QObject):
        message = Signal(str)

    notifier = _Notifier()
    notifier.message.connect(lambda text: tray.notify("DarkeVox", text))

    def run_update(apply: bool) -> None:
        # Worker thread; tray access crosses back via the notifier signal.
        def work() -> None:
            root = update_mod.repo_root()
            if root is None:
                notifier.message.emit("Updates need a git install of DarkeVox.")
                return
            status = update_mod.check(root)
            if not status.available:
                if apply or not status.message.endswith("up to date."):
                    notifier.message.emit(status.message)
                return
            if apply:
                notifier.message.emit(update_mod.apply_update(root).message)
            else:
                notifier.message.emit(f"{status.message} Tray: Update now.")

        threading.Thread(target=work, daemon=True, name="darkevox-update").start()

    tray.update_requested.connect(lambda: run_update(apply=True))
    if cfg.update.auto_check:
        run_update(apply=False)

    start_hotkeys()

    exit_code = app.exec()
    while hotkey_slot:
        hotkey_slot.pop().stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
