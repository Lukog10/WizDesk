r"""Windows Startup registration manager for WizDesk.

Manages automatic launch on Windows login via the HKCU Run registry key:
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
"""

import sys
from pathlib import Path
from typing import Optional

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "WizDesk"


def get_launch_command() -> str:
    """Resolve the executable command line to launch WizDesk on startup."""
    # 1. If running as a frozen PyInstaller application
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
        return f'"{exe_path}"'

    # 2. Check if compiled distribution executable exists
    project_root = Path(__file__).resolve().parents[2]
    dist_exe = project_root / "dist" / "WizDesk" / "WizDesk.exe"
    if dist_exe.exists():
        return f'"{dist_exe.resolve()}"'

    # 3. Development / source mode fallback
    python_exe = Path(sys.executable).resolve()
    pythonw_candidate = python_exe.parent / "pythonw.exe"
    if pythonw_candidate.exists():
        python_exe = pythonw_candidate

    return (
        f'"{python_exe}" -c '
        f'"import sys, runpy; sys.path.insert(0, r\'{project_root}\'); runpy.run_module(\'wiz\', run_name=\'__main__\')"'
    )


def is_autostart_enabled() -> bool:
    """Check if WizDesk is registered to launch on startup in Windows Registry."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except (FileNotFoundError, OSError):
        return False


def set_autostart(enabled: bool) -> bool:
    """Register or unregister WizDesk in Windows HKCU Run registry."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH)

        with key:
            if enabled:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except (FileNotFoundError, OSError):
                    pass
        return True
    except Exception:
        return False
