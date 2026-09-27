"""Window backdrop blur utilities for Windows 11 Desktop Window Manager (DWM).

Provides safe, hardware-accelerated Acrylic and Mica backdrop blur on Windows 11,
with graceful fallback on Linux, macOS, and legacy Windows versions.
"""

import sys
from typing import Optional

# DWM constants for Windows 11 (build 22621+)
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MICA = 2
DWMSBT_ACRYLIC = 3
DWMSBT_MICA_ALT = 4


def is_windows_11() -> bool:
    """Return True if running on Windows 11 (build 22000 or newer)."""
    if sys.platform != "win32":
        return False
    try:
        ver = sys.getwindowsversion()
        return ver.major >= 10 and ver.build >= 22000
    except Exception:
        return False


def set_window_backdrop(
    hwnd: int,
    backdrop_type: int = DWMSBT_ACRYLIC,
    is_dark: bool = True,
) -> bool:
    """Apply DWM system backdrop (Acrylic or Mica) and dark mode attribute to a window.

    On non-Windows platforms (e.g. Linux), safely returns False without error.
    """
    if not is_windows_11() or not hwnd:
        return False

    try:
        import ctypes
        from ctypes import c_int, sizeof, byref

        dwmapi = ctypes.windll.dwmapi

        # 1. Coordinate Dark / Light mode with DWM compositor
        dark_val = c_int(1 if is_dark else 0)
        dwmapi.DwmSetWindowAttribute(
            c_int(hwnd),
            c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
            byref(dark_val),
            c_int(sizeof(dark_val)),
        )

        # 2. Apply system backdrop (Acrylic = 3, Mica = 2)
        backdrop_val = c_int(backdrop_type)
        hr = dwmapi.DwmSetWindowAttribute(
            c_int(hwnd),
            c_int(DWMWA_SYSTEMBACKDROP_TYPE),
            byref(backdrop_val),
            c_int(sizeof(backdrop_val)),
        )
        return hr == 0
    except Exception:
        return False


def set_window_acrylic(hwnd: int, is_dark: bool = True) -> bool:
    """Convenience helper to apply Acrylic frosted glass blur."""
    return set_window_backdrop(hwnd, backdrop_type=DWMSBT_ACRYLIC, is_dark=is_dark)


def set_window_mica(hwnd: int, is_dark: bool = True) -> bool:
    """Convenience helper to apply Mica desktop wallpaper tint."""
    return set_window_backdrop(hwnd, backdrop_type=DWMSBT_MICA, is_dark=is_dark)
