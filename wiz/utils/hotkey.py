"""Global hotkey listener using pynput."""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

from wiz.core.config import config
from wiz.core.signals import app_signals

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


class GlobalHotkeyListener(QObject):
    """Listens for global shortcut triggers across the OS."""

    triggered = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def start(self) -> None:
        """Start listening for configured global hotkeys."""
        if not HAS_PYNPUT:
            print("[Hotkey] Warning: pynput not available, global hotkeys disabled.")
            return

        hotkey_str = config.get("global_hotkey", "<ctrl>+<shift>+w")
        try:
            hotkeys_map = {
                hotkey_str: self._on_hotkey_pressed
            }
            self._listener = keyboard.GlobalHotKeys(hotkeys_map)
            self._listener.start()
            print(f"[Hotkey] Listening for global shortcut: {hotkey_str}")
        except Exception as e:
            print(f"[Hotkey] Error starting global hotkey listener: {e}")

    def _on_hotkey_pressed(self) -> None:
        """Called when hotkey combo is pressed."""
        self.triggered.emit()
        app_signals.request_quick_entry.emit()

    def stop(self) -> None:
        """Stop global hotkey listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
