"""Pure press/hold/drag interpretation for the panel's mic button.

No Qt imports: the panel feeds mouse events and a timer callback in; this
decides whether the gesture was a click (toggle a session), a hold
(push-to-talk while pressed), or a drag (neither).
"""

from __future__ import annotations

from collections.abc import Callable

HOLD_MS = 280  # press longer than this is push-to-talk, shorter is a click
DRAG_CANCEL_PX = 6  # moving further than this turns the gesture into a drag


class PressHoldInterpreter:
    def __init__(
        self,
        on_click: Callable[[], None],
        on_hold_start: Callable[[], None],
        on_hold_end: Callable[[], None],
    ) -> None:
        self._on_click = on_click
        self._on_hold_start = on_hold_start
        self._on_hold_end = on_hold_end
        self._armed = False
        self._holding = False

    @property
    def holding(self) -> bool:
        return self._holding

    def press(self) -> None:
        self._armed = True
        self._holding = False

    def hold_elapsed(self) -> None:
        """The caller's HOLD_MS timer fired while the button stayed down."""
        if self._armed:
            self._armed = False
            self._holding = True
            self._on_hold_start()

    def release(self) -> None:
        if self._holding:
            self._holding = False
            self._on_hold_end()
        elif self._armed:
            self._armed = False
            self._on_click()

    def cancel(self) -> None:
        """The gesture became a drag; a hold in progress still ends cleanly."""
        self._armed = False
        if self._holding:
            self._holding = False
            self._on_hold_end()
