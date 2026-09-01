"""
System-wide idle detection for Windows using GetLastInputInfo.
Provides real-time seconds since last keyboard or mouse input across the system.
"""

import sys
import ctypes

if sys.platform == "win32":
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("dwTime", ctypes.c_uint),
        ]


def get_system_idle_seconds() -> float:
    """
    Return how many seconds elapsed since the last user keyboard or mouse input.
    On non-Windows systems or errors, returns 0.0.
    """
    if sys.platform != "win32":
        return 0.0

    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            if hasattr(ctypes.windll.kernel32, "GetTickCount64"):
                millis = ctypes.windll.kernel32.GetTickCount64() - lii.dwTime
            else:
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception as e:
        print(f"[IdleDetector] Error fetching idle time: {e}")

    return 0.0
