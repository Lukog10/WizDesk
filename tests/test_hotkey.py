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
        assert "<ctrl>+<shift>+t" in registered_dict
        assert "<ctrl>+<shift>+n" in registered_dict
        assert mock_instance.start.called

        # Test reload on signal
        mock_instance.reset_mock()
        app_signals.hotkeys_changed.emit()
        assert mock_instance.stop.called
        assert mock_instance.start.called

        # Test stop
        listener.stop()
        assert listener._listener is None
