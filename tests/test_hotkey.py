"""Unit tests for global hotkey string normalization, display formatting, and listener lifecycle."""

import pytest
from unittest.mock import MagicMock, patch
from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.utils.hotkey import (
    normalize_hotkey_str,
    format_display_shortcut,
    GlobalHotkeyListener,
)


def test_normalize_hotkey_str():
    """Test user string normalization into pynput syntax."""
    assert normalize_hotkey_str("Ctrl+Shift+W") == "<ctrl>+<shift>+w"
    assert normalize_hotkey_str("ctrl+shift+w") == "<ctrl>+<shift>+w"
    assert normalize_hotkey_str("Ctrl-Shift-W") == "<ctrl>+<shift>+w"
    assert normalize_hotkey_str("Control+Alt+T") == "<ctrl>+<alt>+t"
    assert normalize_hotkey_str("Win+Shift+N") == "<cmd>+<shift>+n"
    assert normalize_hotkey_str("Super+Option+X") == "<cmd>+<alt>+x"
    assert normalize_hotkey_str("<ctrl>+<shift>+w") == "<ctrl>+<shift>+w"
    assert normalize_hotkey_str("") == ""
    assert normalize_hotkey_str("   ") == ""


def test_format_display_shortcut():
    """Test pynput string formatting into user-friendly UI presentation."""
    assert format_display_shortcut("<ctrl>+<shift>+w") == "Ctrl+Shift+W"
    assert format_display_shortcut("<ctrl>+<alt>+t") == "Ctrl+Alt+T"
    assert format_display_shortcut("<cmd>+<shift>+n") == "Win+Shift+N"
    assert format_display_shortcut("") == ""


def test_global_hotkey_listener_lifecycle(qapp):
    """Test GlobalHotkeyListener initialization, registration, reload, and stop."""
    with patch("wiz.utils.hotkey.keyboard.GlobalHotKeys") as mock_hotkeys_cls:
        mock_instance = MagicMock()
        mock_hotkeys_cls.return_value = mock_instance

        listener = GlobalHotkeyListener()
        listener.start()

        assert mock_hotkeys_cls.called
        registered_dict = mock_hotkeys_cls.call_args[0][0]
        assert "<ctrl>+<shift>+w" in registered_dict
        assert "<ctrl>+<shift>+m" in registered_dict
        assert "<ctrl>+m" not in registered_dict
        assert "<ctrl>+<shift>+t" in registered_dict
        assert "<ctrl>+<shift>+n" in registered_dict
        assert mock_instance.start.called

        # Verify executing <ctrl>+<shift>+m callback emits toggle_mascot_visibility
        emitted = []
        app_signals.toggle_mascot_visibility.connect(lambda: emitted.append(True))
        registered_dict["<ctrl>+<shift>+m"]()
        assert len(emitted) == 1

        # Test reload on signal
        mock_instance.reset_mock()
        app_signals.hotkeys_changed.emit()
        assert mock_instance.stop.called
        assert mock_instance.start.called

        # Test stop
        listener.stop()
        assert listener._listener is None


def test_wiz_application_hotkey_toggles(qapp):
    """Test show/close toggle behavior for workspace, quick task bar, and quick note bar."""
    from wiz.__main__ import WizApplication

    with patch("wiz.__main__.MascotWindow"), \
         patch("wiz.__main__.TrayIcon"), \
         patch("wiz.__main__.WindowTracker"), \
         patch("wiz.__main__.GlobalHotkeyListener"), \
         patch("wiz.__main__.ObsidianSync"), \
         patch("wiz.__main__.sound_manager"):
        app = WizApplication()

        # 1. Workspace toggle: when closed -> opens; when open -> closes
        mock_entry = MagicMock()
        mock_entry.isVisible.return_value = False
        mock_entry.isMinimized.return_value = False
        app._quick_entry_dialog = mock_entry

        app.show_quick_entry()
        assert mock_entry.show.called
        assert not mock_entry.close.called

        mock_entry.reset_mock()
        mock_entry.isVisible.return_value = True
        mock_entry.isMinimized.return_value = False

        app.show_quick_entry()
        assert mock_entry.close.called

        # 2. Workspace force open (e.g. from settings or secondary instance)
        mock_entry.reset_mock()
        mock_entry.isVisible.return_value = True
        mock_entry.isMinimized.return_value = False

        app.show_quick_entry(toggle=False)
        assert mock_entry.show.called
        assert not mock_entry.close.called

        # 3. Quick task bar toggle: when closed -> opens; when open in task mode -> closes
        mock_bar = MagicMock()
        mock_bar.isVisible.return_value = False
        mock_bar.mode = "task"
        app._quick_bar_dialog = mock_bar

        app.show_quick_task_bar()
        assert mock_bar.show_mode.called
        assert not mock_bar.close.called

        mock_bar.reset_mock()
        mock_bar.isVisible.return_value = True
        mock_bar.mode = "task"

        app.show_quick_task_bar()
        assert mock_bar.close.called

        # 4. Quick note bar toggle: when closed -> opens; when open in note mode -> closes
        mock_bar.reset_mock()
        mock_bar.isVisible.return_value = False
        mock_bar.mode = "note"

        app.show_quick_note_bar()
        assert mock_bar.show_mode.called
        assert not mock_bar.close.called

        mock_bar.reset_mock()
        mock_bar.isVisible.return_value = True
        mock_bar.mode = "note"

        app.show_quick_note_bar()
        assert mock_bar.close.called

        # 5. Mode switching: open in task mode, user triggers note bar -> switches mode without closing
        mock_bar.reset_mock()
        mock_bar.isVisible.return_value = True
        mock_bar.mode = "task"

        app.show_quick_note_bar()
        assert not mock_bar.close.called
        mock_bar.show_mode.assert_called_with("note", mascot_rect=app.mascot_window.geometry())

