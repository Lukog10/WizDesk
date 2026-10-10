"""
Unit tests for the ToggleSwitch component and settings view toggle integration.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QPaintEvent
from PyQt6.QtCore import QRect

from wiz.ui.toggle_switch import ToggleSwitch




def test_toggle_switch_initial_states(qapp):
    """Test default creation in off and on states."""
    sw_off = ToggleSwitch(checked=False, is_dark=True)
    assert sw_off.isChecked() is False
    assert bool(sw_off.isChecked) is False
    assert sw_off.get_thumb_position() == 0.0
    assert sw_off.width() == 38
    assert sw_off.height() == 22

    sw_on = ToggleSwitch(checked=True, is_dark=False)
    assert sw_on.isChecked() is True
    assert bool(sw_on.isChecked) is True
    assert sw_on.get_thumb_position() == 1.0


def test_toggle_switch_signals_and_programmatic_change(qapp):
    """Test setChecked triggers signal and updates state properly."""
    sw = ToggleSwitch(checked=False, is_dark=True)
    emitted = []
    sw.toggled.connect(emitted.append)

    sw.setChecked(True)
    assert sw.isChecked() is True
    assert emitted == [True]

    # No redundant emission if setting same value
    sw.setChecked(True)
    assert emitted == [True]

    sw.setChecked(False)
    assert sw.isChecked() is False
    assert emitted == [True, False]


def test_toggle_switch_mouse_interaction(qapp):
    """Test clicking toggles state."""
    sw = ToggleSwitch(checked=False, is_dark=True)
    emitted = []
    sw.toggled.connect(emitted.append)

    event_left = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    sw.mousePressEvent(event_left)
    assert sw.isChecked() is True
    assert emitted == [True]

    sw.mousePressEvent(event_left)
    assert sw.isChecked() is False
    assert emitted == [True, False]


def test_toggle_switch_keyboard_interaction(qapp):
    """Test Spacebar and Enter keys toggle switch state."""
    sw = ToggleSwitch(checked=False, is_dark=True)
    emitted = []
    sw.toggled.connect(emitted.append)

    event_space = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Space,
        Qt.KeyboardModifier.NoModifier,
    )
    sw.keyPressEvent(event_space)
    assert sw.isChecked() is True
    assert emitted == [True]

    event_return = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
    )
    sw.keyPressEvent(event_return)
    assert sw.isChecked() is False
    assert emitted == [True, False]


def test_toggle_switch_theming_and_painting(qapp):
    """Verify theme switching and paint event execution without errors."""
    sw = ToggleSwitch(checked=True, is_dark=False)
    assert sw.is_dark is False

    sw.set_theme(True)
    assert sw.is_dark is True

    sw.set_dark_mode(False)
    assert sw.is_dark is False

    # Trigger paintEvent directly for both light and dark modes
    paint_evt = QPaintEvent(QRect(0, 0, 38, 22))
    sw.paintEvent(paint_evt)

    sw.set_theme(True)
    sw.paintEvent(paint_evt)
