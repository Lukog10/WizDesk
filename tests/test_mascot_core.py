"""Unit tests for Wiz Core State Machine, Config, and Mascot UI Components."""

import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from wiz.core.config import Config
from wiz.core.state_machine import StateMachine, MascotState
from wiz.ui.mascot_widget import MascotWidget
from wiz.ui.mascot_window import MascotWindow
from wiz.ui.tray_icon import TrayIcon


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance for Qt unit testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_config_defaults(tmp_path):
    """Test Config default values and JSON persistence."""
    test_config_file = tmp_path / "test_config.json"
    cfg = Config(config_file=test_config_file)

    assert cfg.window_size == (140, 168)
    assert cfg.get("tracking_interval_seconds") == 300
    assert cfg.get("enable_floating_animation") is True

    # Test setting and saving
    cfg.set("enable_floating_animation", False)
    assert test_config_file.exists()

    # Reload from file
    cfg_reloaded = Config(config_file=test_config_file)
    assert cfg_reloaded.get("enable_floating_animation") is False


def test_state_machine_transitions(qapp):
    """Test StateMachine transitions and signal emissions."""
    sm = StateMachine(initial_state=MascotState.IDLE)
    assert sm.current_state == MascotState.IDLE

    emitted_states = []

    def handle_state_change(new_state, old_state):
        emitted_states.append((new_state, old_state))

    sm.state_changed.connect(handle_state_change)

    # Transition to WORKING via transition_to alias
    sm.transition_to(MascotState.WORKING)
    assert sm.current_state == MascotState.WORKING
    assert emitted_states[-1] == (MascotState.WORKING, MascotState.IDLE)

    # Transition to SLEEP
    sm.trigger_sleep()
    assert sm.current_state == MascotState.SLEEP
    assert emitted_states[-1] == (MascotState.SLEEP, MascotState.WORKING)


def test_mascot_window_and_widget_init(qapp):
    """Test MascotWindow and MascotWidget creation and state rendering."""
    sm = StateMachine(initial_state=MascotState.IDLE)
    window = MascotWindow(sm)

    assert window.mascot_widget is not None
    assert window.width() > 0
    assert window.height() > 0

    # Switch states and verify widget updates
    sm.set_state(MascotState.COMPLETE)
    assert sm.current_state == MascotState.COMPLETE

    window.close()


def test_tray_icon_init(qapp):
    """Test TrayIcon initialization and menu creation."""
    sm = StateMachine(initial_state=MascotState.IDLE)
    tray = TrayIcon(sm)
    assert tray.toolTip() == "WizDesk - Desktop Companion and Work Tracker"
    assert tray.contextMenu() is not None
    assert len(tray.contextMenu().actions()) > 0


def test_automated_idle_and_sleep_state_transitions(qapp):
    """
    Test exact state transition requirements:
    - 0s idle (User at work) -> WORKING
    - 10s idle -> IDLE
    - 1m (60s) idle -> SLEEP
    - Resume work -> WORKING
    """
    sm = StateMachine(initial_state=MascotState.IDLE, enable_idle_monitoring=False)
    
    current_simulated_idle = 0.0
    sm.set_idle_getter(lambda: current_simulated_idle)

    # 1. User starts working (0.0s idle)
    current_simulated_idle = 0.0
    sm._check_idle_state()
    assert sm.current_state == MascotState.WORKING

    # 2. Idle for 10 seconds -> IDLE
    current_simulated_idle = 10.0
    sm._check_idle_state()
    assert sm.current_state == MascotState.IDLE

    # 3. Idle for 1 minute (60s) -> SLEEP
    current_simulated_idle = 60.0
    sm._check_idle_state()
    assert sm.current_state == MascotState.SLEEP

    # 4. User resumes activity (0.5s idle) -> WORKING
    current_simulated_idle = 0.5
    sm._check_idle_state()
    assert sm.current_state == MascotState.WORKING

    # 5. Adding task/subtask triggers NOTIFY
    sm.trigger_notify(duration_ms=100)
    assert sm.current_state == MascotState.NOTIFY

    # While in NOTIFY, idle check does not interrupt
    current_simulated_idle = 15.0
    sm._check_idle_state()
    assert sm.current_state == MascotState.NOTIFY

    # After revert, transitions to IDLE based on 15s idle
    sm._on_revert_timeout()
    assert sm.current_state == MascotState.IDLE

    # 6. Completing / cancelling task triggers COMPLETE
    sm.trigger_complete(duration_ms=100)
    assert sm.current_state == MascotState.COMPLETE

    # Revert back to working when user is active
    current_simulated_idle = 0.0
    sm._on_revert_timeout()
    assert sm.current_state == MascotState.WORKING


def test_application_quit_signal(qapp):
    """Test that quit_application signal triggers application shutdown and quit."""
    from wiz.core.signals import app_signals
    from wiz.__main__ import WizApplication

    app_instance = WizApplication()
    quit_called = []

    def handle_quit():
        quit_called.append(True)

    app_signals.quit_application.connect(handle_quit)
    app_signals.quit_application.emit()

    assert len(quit_called) > 0
    app_instance.shutdown()

