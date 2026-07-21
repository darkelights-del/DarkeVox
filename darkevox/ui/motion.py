"""Motion helpers: one place for easing, retargeting, and the reduce gate.

Rules (darkevox-ui-style, Motion): exponential ease-outs only, routine UI
under 300 ms, animations retarget instead of restarting, loops stop when
their surface hides, and keyboard-initiated dictation stays instant.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QVariantAnimation

EASE_OUT = QEasingCurve.Type.OutQuart
EASE_OUT_SOFT = QEasingCurve.Type.OutQuad
EASE_IN_SOFT = QEasingCurve.Type.InQuad

_reduce = False


def configure(reduce_motion: bool) -> None:
    """Set once at startup from config plus the OS animation preference."""
    global _reduce
    _reduce = bool(reduce_motion) or _os_reduces_motion()


def enabled() -> bool:
    return not _reduce


def duration(ms: int) -> int:
    """0 when motion is reduced, so animations become instant sets."""
    return 0 if _reduce else ms


def _os_reduces_motion() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        SPI_GETCLIENTAREAANIMATION = 0x1042
        value = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(  # type: ignore[attr-defined]
            SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(value), 0
        )
        return value.value == 0
    except Exception:
        return False


def make_anim(
    parent: object,
    ms: int,
    on_value: Callable[[object], None],
    easing: QEasingCurve.Type = EASE_OUT_SOFT,
) -> QVariantAnimation:
    """One persistent animation per property; retarget with `retarget()`."""
    anim = QVariantAnimation(parent)
    anim.setDuration(duration(ms))
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(on_value)
    return anim


def retarget(anim: QVariantAnimation, start: object, end: object, ms: int | None = None) -> None:
    """Stop, aim at the new end from the current live value, and go.

    Interruption discipline: never restart from zero, never stack a second
    animation on the same property.
    """
    anim.stop()
    if ms is not None:
        anim.setDuration(duration(ms))
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.start()
