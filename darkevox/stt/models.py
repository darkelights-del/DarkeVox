"""STT model management: presence check, first-run download, CUDA detection.

Core module: no Qt. The download reports progress by directory size because
faster-whisper's downloader exposes no byte callback; approximate totals per
model make the bar honest enough ("412 / 484 MB").
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

SUPPORTED_MODELS = ("base.en", "small.en", "large-v3-turbo")

# Rough repo sizes used only to scale the progress bar.
APPROX_SIZE_MB = {
    "base.en": 145,
    "small.en": 484,
    "large-v3-turbo": 1_620,
}


def detect_cuda() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:  # ctranslate2 missing or broken CUDA runtime: treat as CPU
        return False


def resolve_device(device: str, compute_type: str) -> tuple[str, str]:
    """Map 'auto' settings to what this machine actually has.

    CTranslate2 accelerates on NVIDIA CUDA only (no Intel iGPU path), so CPU
    int8 is the honest default.
    """
    if device == "auto":
        device = "cuda" if detect_cuda() else "cpu"
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def model_path(model: str, models_dir: Path) -> Path:
    return models_dir / model


def is_downloaded(model: str, models_dir: Path) -> bool:
    # CTranslate2 conversions always ship model.bin + config.json; a pure file
    # check keeps faster_whisper's heavy import off the app-startup path.
    target = model_path(model, models_dir)
    return (target / "model.bin").is_file() and (target / "config.json").is_file()


def download(model: str, models_dir: Path) -> Path:
    """Blocking download; run on a worker thread. Returns the model directory."""
    from faster_whisper import download_model

    target = model_path(model, models_dir)
    target.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s to %s", model, target)
    download_model(model, output_dir=str(target))
    return target


def downloaded_mb(model: str, models_dir: Path) -> float:
    """Bytes on disk so far, in MB; drives the first-run progress bar."""
    target = models_dir / model
    if not target.exists():
        return 0.0
    return sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / 1_048_576
