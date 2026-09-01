"""Mascot state machine managing companion states, triggers, and auto-reversion."""

from enum import Enum
from typing import Optional, Callable
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from wiz.core.idle_detector import get_system_idle_seconds


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
    """
    Manages the current state of Wiz, automated idle transitions (10s -> IDLE, 1m -> SLEEP),
    activity recovery (User input -> WORKING), and transient notification/celebration states.
    """

    # Signal emitted when state changes: (new_state: MascotState, old_state: MascotState)
    state_changed = pyqtSignal(object, object)

    def __init__(
        self,
        initial_state: MascotState = MascotState.IDLE,
        idle_threshold_sec: float = 10.0,
        sleep_threshold_sec: float = 60.0,
        enable_idle_monitoring: bool = True,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._current_state: MascotState = initial_state
        self._previous_state: MascotState = initial_state

        self.idle_threshold_sec: float = idle_threshold_sec
        self.sleep_threshold_sec: float = sleep_threshold_sec
        self._custom_idle_getter: Optional[Callable[[], float]] = None

        # Auto-revert timer for transient states like COMPLETE and NOTIFY
        self._revert_timer = QTimer(self)
        self._revert_timer.setSingleShot(True)
        self._revert_timer.timeout.connect(self._on_revert_timeout)

        # Background idle checking timer (runs every 500ms for responsive state updates)
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(500)
        self._idle_timer.timeout.connect(self._check_idle_state)
        if enable_idle_monitoring:
            self._idle_timer.start()

    @property
    def current_state(self) -> MascotState:
        """Get the current mascot state."""
        return self._current_state

    def set_idle_getter(self, getter: Optional[Callable[[], float]]) -> None:
        """Inject custom idle duration getter (useful for unit tests and simulations)."""
        self._custom_idle_getter = getter

    def get_idle_seconds(self) -> float:
        """Fetch elapsed idle seconds from custom getter or system API."""
        if self._custom_idle_getter is not None:
            return self._custom_idle_getter()
        return get_system_idle_seconds()

    def set_state(self, new_state: MascotState, duration_ms: Optional[int] = None) -> None:
        """
        Transition to a new state.
        
        Args:
            new_state: The target MascotState.
            duration_ms: Optional duration in milliseconds after which to revert to baseline state.
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

    def trigger_notify(self, duration_ms: int = 3500) -> None:
        """Set mascot to NOTIFY state (attention sparkles) for the given duration."""
        self.set_state(MascotState.NOTIFY, duration_ms=duration_ms)

    def trigger_complete(self, duration_ms: int = 3500) -> None:
        """Set mascot to COMPLETE state (celebration flash) for the given duration."""
        self.set_state(MascotState.COMPLETE, duration_ms=duration_ms)

    def trigger_sleep(self) -> None:
        """Set mascot to SLEEP state (dimmed, closed eyes)."""
        self.set_state(MascotState.SLEEP)

    def revert_to_baseline(self) -> None:
        """Revert state based on current user activity and idle duration."""
        idle_sec = self.get_idle_seconds()
        if idle_sec >= self.sleep_threshold_sec:
            target = MascotState.SLEEP
        elif idle_sec >= self.idle_threshold_sec:
            target = MascotState.IDLE
        else:
            target = MascotState.WORKING

        self.set_state(target)

    def _on_revert_timeout(self) -> None:
        """Revert back to baseline state upon transient timer expiration."""
        self.revert_to_baseline()

    def _check_idle_state(self) -> None:
        """
        Evaluate system idle time and transition between WORKING, IDLE, and SLEEP states:
        - Active user input (< 10s idle) -> WORKING
        - Idle for 10s (>= 10s and < 60s) -> IDLE
        - Idle for 1m (>= 60s) -> SLEEP
        """
        # If currently in a transient state (COMPLETE or NOTIFY), let the animation finish
        if self._revert_timer.isActive() or self._current_state in (MascotState.COMPLETE, MascotState.NOTIFY):
            return

        idle_sec = self.get_idle_seconds()

        if idle_sec >= self.sleep_threshold_sec:
            if self._current_state != MascotState.SLEEP:
                self.set_state(MascotState.SLEEP)
        elif idle_sec >= self.idle_threshold_sec:
            if self._current_state != MascotState.IDLE:
                self.set_state(MascotState.IDLE)
        else:
            # User is actively working
            if self._current_state != MascotState.WORKING:
                self.set_state(MascotState.WORKING)
