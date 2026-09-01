"""Mascot state machine managing companion states, triggers, and auto-reversion."""

from enum import Enum
from typing import Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class MascotState(str, Enum):
    """Enumeration of all visual & behavioral mascot states."""
    IDLE = "idle"
    WORKING = "working"
    NOTIFY = "notify"
    COMPLETE = "complete"
    SLEEP = "sleep"

    @property
    def asset_filename(self) -> str:
        """Return the corresponding SVG filename in the assets folder."""
        mapping = {
            MascotState.IDLE: "wiz-idle.svg",
            MascotState.WORKING: "wiz-working.svg",
            MascotState.NOTIFY: "wiz-notify.svg",
            MascotState.COMPLETE: "wiz-complete.svg",
            MascotState.SLEEP: "wiz-sleep.svg",
        }
        return mapping[self]


class StateMachine(QObject):
    """Manages the current state of Wiz and handles timed state transitions."""

    # Signal emitted when state changes: (new_state: MascotState, old_state: MascotState)
    state_changed = pyqtSignal(object, object)

    def __init__(self, initial_state: MascotState = MascotState.IDLE, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._current_state: MascotState = initial_state
        self._previous_state: MascotState = initial_state

        # Auto-revert timer for transient states like COMPLETE and NOTIFY
        self._revert_timer = QTimer(self)
        self._revert_timer.setSingleShot(True)
        self._revert_timer.timeout.connect(self._on_revert_timeout)

    @property
    def current_state(self) -> MascotState:
        """Get the current mascot state."""
        return self._current_state

    def set_state(self, new_state: MascotState, duration_ms: Optional[int] = None) -> None:
        """
        Transition to a new state.
        
        Args:
            new_state: The target MascotState.
            duration_ms: Optional duration in milliseconds after which to revert to previous state.
        """
        if self._current_state == new_state:
            # If already in the target state but duration is provided, refresh the timer
            if duration_ms and duration_ms > 0:
                self._revert_timer.start(duration_ms)
            return

        old_state = self._current_state
        self._previous_state = old_state
        self._current_state = new_state

        # Cancel any pending revert timer unless a new duration is specified
        self._revert_timer.stop()
        if duration_ms and duration_ms > 0:
            self._revert_timer.start(duration_ms)

        self.state_changed.emit(new_state, old_state)

    def transition_to(self, new_state: MascotState, duration_ms: Optional[int] = None) -> None:
        """Alias for set_state to transition to a new state."""
        self.set_state(new_state, duration_ms=duration_ms)

    def trigger_idle(self) -> None:
        """Set mascot to IDLE resting state."""
        self.set_state(MascotState.IDLE)

    def trigger_working(self) -> None:
        """Set mascot to WORKING state (loading-spinner eyes / tracking active)."""
        self.set_state(MascotState.WORKING)

    def trigger_notify(self, duration_ms: int = 6000) -> None:
        """Set mascot to NOTIFY state (attention sparkles) for the given duration."""
        self.set_state(MascotState.NOTIFY, duration_ms=duration_ms)

    def trigger_complete(self, duration_ms: int = 3500) -> None:
        """Set mascot to COMPLETE state (celebration flash) for the given duration."""
        self.set_state(MascotState.COMPLETE, duration_ms=duration_ms)

    def trigger_sleep(self) -> None:
        """Set mascot to SLEEP state (dimmed, closed eyes)."""
        self.set_state(MascotState.SLEEP)

    def _on_revert_timeout(self) -> None:
        """Revert back to IDLE or previous baseline state upon timer expiration."""
        target = self._previous_state if self._previous_state != self._current_state else MascotState.IDLE
        if target in (MascotState.COMPLETE, MascotState.NOTIFY):
            target = MascotState.IDLE
        self.set_state(target)
