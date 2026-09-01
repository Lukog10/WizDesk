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
    assert cfg.get("tracking_interval_seconds") == 1800
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
