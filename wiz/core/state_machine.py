"""Mascot state machine managing companion states, triggers, signals, and auto-reversion."""

from enum import Enum
from typing import Optional, Callable
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from wiz.core.config import config
from wiz.core.idle_detector import get_system_idle_seconds
from wiz.core.signals import app_signals
from wiz.core.sound import sound_manager


class MascotState(str, Enum):
    """Enumeration of all visual & behavioral mascot states."""
    IDLE = "idle"          # Monitor / Active gaze tracking
    WORKING = "working"    # Active work logging (thin spinner)
    NOTIFY = "notify"      # Task operation acknowledgment (sparkles)
    COMPLETE = "complete"  # Celebration arpeggio
    SLEEP = "sleep"        # Resting nap

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
    Manages companion mascot state, reactive event listeners via app_signals,
    cursor monitoring baseline (IDLE), activity logging (WORKING),
    task notifications (NOTIFY), celebrations (COMPLETE), and inactivity sleep (SLEEP).
    """

    # Signal emitted when state changes: (new_state: MascotState, old_state: MascotState)
    state_changed = pyqtSignal(object, object)

    def __init__(
        self,
        initial_state: MascotState = MascotState.IDLE,
        idle_threshold_sec: float = 10.0,
        sleep_threshold_sec: Optional[float] = None,
        enable_idle_monitoring: bool = True,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._current_state: MascotState = initial_state
        self._previous_state: MascotState = initial_state

        self.idle_threshold_sec: float = idle_threshold_sec
        self.sleep_threshold_sec: float = (
            sleep_threshold_sec if sleep_threshold_sec is not None else 60.0
        )
        self._custom_idle_getter: Optional[Callable[[], float]] = None

        # Auto-revert timer for transient states like COMPLETE, NOTIFY, WORKING
        self._revert_timer = QTimer(self)
        self._revert_timer.setSingleShot(True)
        self._revert_timer.timeout.connect(self._on_revert_timeout)

        # Background idle checking timer (runs every 500ms)
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(500)
        self._idle_timer.timeout.connect(self._check_idle_state)
        if enable_idle_monitoring:
            self._idle_timer.start()

        # Connect application event bus to companion triggers
        self._connect_app_signals()

    def _connect_app_signals(self) -> None:
        """Subscribe state machine to decoupled app_signals."""
        app_signals.activity_logged.connect(self._on_activity_logged)
        app_signals.task_created.connect(self._on_task_action)
        app_signals.task_updated.connect(self._on_task_action)
        app_signals.task_deleted.connect(self._on_task_action)
        app_signals.task_completed.connect(self._on_task_completed)
        app_signals.task_cancelled.connect(self._on_task_cancelled)

    def _on_activity_logged(self, app_name: str, duration_sec: int) -> None:
        """Trigger WORKING state when window tracker records an activity session."""
        self.trigger_working(duration_ms=2500)
        sound_manager.play_work_log()

    def _on_task_action(self, task_id: int) -> None:
        """Trigger NOTIFY state when a task is created, updated, or deleted."""
        self.trigger_notify(duration_ms=2000)
        sound_manager.play_task_notify()

    def _on_task_completed(self, task_id: int) -> None:
        """Trigger COMPLETE state celebration when a task is completed."""
        self.trigger_complete(duration_ms=3500)
        sound_manager.play_task_complete()

    def _on_task_cancelled(self, task_id: int) -> None:
        """Play soft cancellation sound when a task is cancelled."""
        sound_manager.play_task_cancel()

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
        """Set mascot to IDLE (Monitor) state."""
        self.set_state(MascotState.IDLE)

    def trigger_working(self, duration_ms: int = 2500) -> None:
        """Set mascot to WORKING state (work logging animation) for duration."""
        self.set_state(MascotState.WORKING, duration_ms=duration_ms)

    def trigger_notify(self, duration_ms: int = 2000) -> None:
        """Set mascot to NOTIFY state (attention sparkles) for duration."""
        self.set_state(MascotState.NOTIFY, duration_ms=duration_ms)

    def trigger_complete(self, duration_ms: int = 3500) -> None:
        """Set mascot to COMPLETE state (celebration flash) for duration."""
        self.set_state(MascotState.COMPLETE, duration_ms=duration_ms)

    def trigger_sleep(self) -> None:
        """Set mascot to SLEEP state (dimmed, closed eyes)."""
        self.set_state(MascotState.SLEEP)

    def revert_to_baseline(self) -> None:
        """Revert state based on current system idle duration."""
        idle_sec = self.get_idle_seconds()
        sleep_limit = self.sleep_threshold_sec
        if idle_sec >= sleep_limit:
            target = MascotState.SLEEP
        else:
            target = MascotState.IDLE

        self.set_state(target)

    def _on_revert_timeout(self) -> None:
        """Revert back to baseline state upon transient timer expiration."""
        self.revert_to_baseline()

    def on_inactivity_detected(self) -> None:
        """Handle signal when system becomes inactive (transition to SLEEP)."""
        if self._current_state != MascotState.SLEEP:
            self.set_state(MascotState.SLEEP)
            sound_manager.play_sleep()

    def on_activity_resumed(self) -> None:
        """Handle signal when system activity resumes (transition from SLEEP to IDLE)."""
        if self._current_state == MascotState.SLEEP:
            self.set_state(MascotState.IDLE)
            sound_manager.play_wake()

    def _check_idle_state(self) -> None:
        """
        Evaluate system idle time and handle SLEEP and wake transitions:
        - If idle >= sleep_inactivity_sec -> transition to SLEEP and play sleep sound.
        - If waking from SLEEP (idle < sleep_inactivity_sec) -> transition to IDLE and play wake sound.
        - Otherwise remain in IDLE (Monitor) or let transient states finish.
        """
        # If currently in a transient state (COMPLETE, NOTIFY, WORKING), let animation finish
        if self._revert_timer.isActive() or self._current_state in (
            MascotState.COMPLETE,
            MascotState.NOTIFY,
            MascotState.WORKING,
        ):
            return

        idle_sec = self.get_idle_seconds()
        sleep_limit = self.sleep_threshold_sec

        if idle_sec >= sleep_limit:
            if self._current_state != MascotState.SLEEP:
                self.set_state(MascotState.SLEEP)
                sound_manager.play_sleep()
        else:
            # User is active on the computer
            if self._current_state == MascotState.SLEEP:
                self.set_state(MascotState.IDLE)
                sound_manager.play_wake()
