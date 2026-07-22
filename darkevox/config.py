"""Config load/save for DarkeVox.

TOML lives at ``config_dir()/config.toml``. API keys live in the OS keyring
(Windows Credential Manager on the target platform), never in the TOML.
Unknown keys in the file are ignored so old configs survive upgrades.
"""

from __future__ import annotations

import logging
import os
import sys
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import tomli_w

from darkevox import APP_NAME

log = logging.getLogger(__name__)

KEYRING_SERVICE = APP_NAME

STT_MODELS = ("base.en", "small.en", "large-v3-turbo")
TONES = ("email", "message", "notes", "verbatim")
BACKENDS = ("ollama", "openrouter")
INJECT_METHODS = ("paste", "type")


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / APP_NAME


def data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.toml"


def models_dir() -> Path:
    return data_dir() / "models"


def logs_dir() -> Path:
    return data_dir() / "logs"


@dataclass
class HotkeysConfig:
    hold: str = "ctrl+alt+space"
    toggle: str = "ctrl+alt+d"
    # Logs every raw key event; turn on only to diagnose a combo that won't fire.
    log_keys: bool = False


@dataclass
class SttConfig:
    model: str = "small.en"
    device: str = "auto"  # auto | cpu | cuda
    compute_type: str = "auto"  # auto -> int8 on cpu, float16 on cuda
    language: str = "en"
    # 5 = accuracy (default); 1 = greedy, faster but noticeably sloppier on
    # imperfect mics. Raise the model to medium.en before blaming the mic.
    beam_size: int = 5
    # Microphone: "" = system default; a device index or name substring
    # otherwise (see the log line listing devices at startup).
    input_device: str = ""
    # Audio leaves this machine ONLY when cloud_enabled is true.
    cloud_enabled: bool = False
    cloud_provider: str = "groq"
    cloud_model: str = "whisper-large-v3-turbo"


@dataclass
class LlmConfig:
    backend: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    polish_model: str = "qwen2.5:3b"
    # Reserved for the phase 4-5 context engine; background work, quality over speed.
    summarize_model: str = "qwen2.5:7b"
    openrouter_url: str = "https://openrouter.ai/api/v1"
    # The free-model list rotates; the user picks from the live list (see README).
    openrouter_model: str = ""
    timeout_s: float = 10.0
    retries: int = 1
    # Keeps the polish model resident in Ollama between dictations; without it
    # the model unloads after ~5 idle minutes and the next call cold-loads
    # past the timeout.
    keep_alive: str = "30m"


@dataclass
class PolishConfig:
    default_tone: str = "email"
    grounding_enabled: bool = False
    grounding_k: int = 3
    grounding_floor: float = 0.35


@dataclass
class InjectConfig:
    method: str = "paste"
    restore_delay_ms: int = 300


@dataclass
class UiConfig:
    # Panel geometry persists across launches; -1 means "not placed yet".
    panel_x: int = -1
    panel_y: int = -1
    # Closed to tray when you quit -> stays closed next launch.
    panel_hidden: bool = False
    # Turns every animation into an instant set; also honored automatically
    # when Windows' "Show animations" accessibility setting is off.
    reduce_motion: bool = False


@dataclass
class UpdateConfig:
    # Checks the git upstream once per launch, off the hot path. The phase 7
    # installer will swap this for release-based updates.
    auto_check: bool = True


@dataclass
class DictionaryConfig:
    terms: list[str] = field(default_factory=list)


@dataclass
class Config:
    hotkeys: HotkeysConfig = field(default_factory=HotkeysConfig)
    stt: SttConfig = field(default_factory=SttConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    polish: PolishConfig = field(default_factory=PolishConfig)
    inject: InjectConfig = field(default_factory=InjectConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    dictionary: DictionaryConfig = field(default_factory=DictionaryConfig)


def _merge_section(section: Any, raw: dict[str, Any]) -> None:
    known = {f.name for f in fields(section)}
    for key, value in raw.items():
        if key in known:
            setattr(section, key, value)
        else:
            log.debug("ignoring unknown config key: %s", key)


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    cfg = Config()
    if not path.is_file():
        return cfg
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.error("config unreadable, using defaults: %s", exc)
        return cfg
    for name in (f.name for f in fields(cfg)):
        section_raw = raw.get(name)
        if isinstance(section_raw, dict):
            _merge_section(getattr(cfg, name), section_raw)
    return cfg


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(asdict(cfg)), encoding="utf-8")


def get_api_key(name: str) -> str | None:
    """Read a secret from the OS keyring; None when unset or keyring is unavailable."""
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, name)
    except Exception as exc:  # keyring backends fail in odd ways; never crash over a key
        log.warning("keyring read failed for %s: %s", name, exc)
        return None


def set_api_key(name: str, value: str) -> bool:
    """Store a secret in the OS keyring. Returns False when the backend is unavailable."""
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, name, value)
        return True
    except Exception as exc:
        log.warning("keyring write failed for %s: %s", name, exc)
        return False
