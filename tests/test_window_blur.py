"""Tests for cross-platform window blur and backdrop utility."""

import sys
from unittest.mock import patch, MagicMock

import pytest

from wiz.utils.window_blur import (
    is_windows_11,
    set_window_backdrop,
    set_window_acrylic,
    set_window_mica,
    DWMSBT_ACRYLIC,
    DWMSBT_MICA,
)


def test_is_windows_11_detection():
    """Verify Windows 11 platform detection logic."""
    if sys.platform == "win32":
        # On modern Windows runner, returns a bool without crashing
        assert isinstance(is_windows_11(), bool)
    else:
        assert is_windows_11() is False


def test_is_windows_11_mock_linux():
    """Verify detection returns False on Linux or macOS."""
    with patch("sys.platform", "linux"):
        assert is_windows_11() is False

    with patch("sys.platform", "darwin"):
        assert is_windows_11() is False


def test_set_window_backdrop_invalid_hwnd():
    """Verify calling backdrop with invalid hwnd safely returns False."""
    assert set_window_backdrop(0) is False
    assert set_window_backdrop(None) is False


def test_set_window_backdrop_mock_linux():
    """Verify backdrop helper safely returns False on Linux without errors."""
    with patch("wiz.utils.window_blur.is_windows_11", return_value=False):
        assert set_window_backdrop(12345) is False
        assert set_window_acrylic(12345) is False
        assert set_window_mica(12345) is False


def test_set_window_backdrop_mock_windows_success():
    """Verify backdrop calls DWM APIs successfully when on Windows 11."""
    with patch("wiz.utils.window_blur.is_windows_11", return_value=True):
        mock_dwmapi = MagicMock()
        mock_dwmapi.DwmSetWindowAttribute.return_value = 0
        mock_ctypes = MagicMock()
        mock_ctypes.windll.dwmapi = mock_dwmapi

        with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            result = set_window_backdrop(99999, backdrop_type=DWMSBT_ACRYLIC, is_dark=True)
            assert result is True
            assert mock_dwmapi.DwmSetWindowAttribute.call_count == 2


def test_set_window_backdrop_exception_resilience():
    """Verify OS errors during DWM calls are caught and return False."""
    with patch("wiz.utils.window_blur.is_windows_11", return_value=True):
        mock_dwmapi = MagicMock()
        mock_dwmapi.DwmSetWindowAttribute.side_effect = OSError("DWM compositor unavailable")
        mock_ctypes = MagicMock()
        mock_ctypes.windll.dwmapi = mock_dwmapi

        with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            result = set_window_backdrop(99999)
            assert result is False
