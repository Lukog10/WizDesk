"""Global hotkey listener using pynput."""

from typing import Optional, Dict, Callable
from PyQt6.QtCore import QObject

from wiz.core.config import config
from wiz.core.signals import app_signals

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


def normalize_hotkey_str(hk: str) -> str:
    """Normalize user-friendly shortcut string to pynput format (e.g. 'Ctrl+Shift+W' -> '<ctrl>+<shift>+w')."""
    if not hk:
        return ""
    hk_clean = hk.strip().lower()
    if "<" in hk_clean and ">" in hk_clean:
        return hk_clean
    parts = [p.strip() for p in hk_clean.replace("-", "+").split("+") if p.strip()]
    normalized_parts = []
    for part in parts:
        if part in ("ctrl", "control"):
            normalized_parts.append("<ctrl>")
        elif part in ("alt", "option"):
            normalized_parts.append("<alt>")
        elif part == "shift":
            normalized_parts.append("<shift>")
        elif part in ("cmd", "win", "windows", "super"):
            normalized_parts.append("<cmd>")
        else:
            normalized_parts.append(part)
    return "+".join(normalized_parts)


def format_display_shortcut(hk: str) -> str:
    """Format pynput shortcut string to clean display string (e.g. '<ctrl>+<shift>+w' -> 'Ctrl+Shift+W')."""
    if not hk:
        return ""
    tokens = hk.strip().replace("<", "").replace(">", "").split("+")
    display_tokens = []
    for t in tokens:
        t_lower = t.lower()
        if t_lower == "ctrl":
            display_tokens.append("Ctrl")
        elif t_lower == "alt":
            display_tokens.append("Alt")
        elif t_lower == "shift":
            display_tokens.append("Shift")
        elif t_lower == "cmd":
            display_tokens.append("Win")
        else:
            display_tokens.append(t.upper())
    return "+".join(display_tokens)


class GlobalHotkeyListener(QObject):
    """Listens for global shortcut triggers across the OS."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        app_signals.hotkeys_changed.connect(self.reload)

    def start(self) -> None:
        """Start listening for configured global hotkeys."""
        if not HAS_PYNPUT:
            print("[Hotkey] Warning: pynput not available, global hotkeys disabled.")
            return

        self.stop()

        hk_ws = normalize_hotkey_str(config.get("hotkey_workspace", config.get("global_hotkey", "<ctrl>+<shift>+w")))
        hk_mascot = normalize_hotkey_str(config.get("hotkey_toggle_mascot", "<ctrl>+<shift>+m"))
        hk_task = normalize_hotkey_str(config.get("hotkey_quick_task", "<ctrl>+<shift>+t"))
        hk_note = normalize_hotkey_str(config.get("hotkey_quick_note", "<ctrl>+<shift>+n"))

        hotkeys_map: Dict[str, Callable] = {}
        if hk_ws:
            hotkeys_map[hk_ws] = lambda: app_signals.request_quick_entry.emit()
        if hk_mascot:
            hotkeys_map[hk_mascot] = lambda: app_signals.toggle_mascot_visibility.emit()
        if hk_task:
            hotkeys_map[hk_task] = lambda: app_signals.request_quick_task_bar.emit()
        if hk_note:
            hotkeys_map[hk_note] = lambda: app_signals.request_quick_note_bar.emit()

        if not hotkeys_map:
            return

        try:
            self._listener = keyboard.GlobalHotKeys(hotkeys_map)
            self._listener.start()
            print(f"[Hotkey] Registered {len(hotkeys_map)} global hotkeys: {list(hotkeys_map.keys())}")
        except Exception as e:
            print(f"[Hotkey] Error starting global hotkey listener: {e}")

    def reload(self) -> None:
        """Restart listener with updated hotkey settings."""
        self.stop()
        self.start()

    def stop(self) -> None:
        """Stop global hotkey listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
