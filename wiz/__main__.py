"""Main application entry point for WizDesk desktop companion."""

import sys
import os
import ctypes
from typing import Optional
from datetime import date

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from wiz.core.config import config
from wiz.core.state_machine import StateMachine, MascotState
from wiz.core.signals import app_signals
from wiz.storage.db import get_db
from wiz.storage.models import StorageRepository
from wiz.ui.mascot_window import MascotWindow
from wiz.ui.tray_icon import TrayIcon
from wiz.ui.popup_dialog import QuickEntryDialog
from wiz.ui.settings_dialog import SettingsDialog
from wiz.tracker.window_tracker import WindowTracker
from wiz.sync.obsidian import ObsidianSync
from wiz.utils.hotkey import GlobalHotkeyListener


def set_windows_app_id() -> None:
    """Set Windows AppUserModelID for proper taskbar / notification grouping."""
    if sys.platform == "win32":
        try:
            my_app_id = "lukog.wizdesk.desktop.companion.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
        except Exception as e:
            print(f"[WizDesk] Warning: Failed to set AppUserModelID: {e}")


class WizApplication:
    """Coordinates core systems, UI windows, background tracker, and sync routines."""

    def __init__(self):
        self.repo = StorageRepository()
        self.state_machine = StateMachine(initial_state=MascotState.IDLE)
        self.sync_engine = ObsidianSync(self.repo)

        # UI instances
        self.mascot_window = MascotWindow(self.state_machine)
        self.tray_icon = TrayIcon(self.state_machine)
        self._quick_entry_dialog: Optional[QuickEntryDialog] = None
        self._settings_dialog: Optional[SettingsDialog] = None

        # Background Services
        self.tracker = WindowTracker(self.repo)
        self.hotkey_listener = GlobalHotkeyListener()

        # Connect signals
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Bind global signals to UI handlers and actions."""
        app_signals.request_quick_entry.connect(self.show_quick_entry)
        app_signals.request_settings.connect(self.show_settings)
        app_signals.request_sync.connect(self.trigger_sync)
        app_signals.sync_finished.connect(self._on_sync_finished)
        app_signals.session_polled.connect(self._on_session_polled)

    def start(self) -> None:
        """Launch UI and background worker threads."""
        self.mascot_window.show()
        self.tray_icon.show()
        self.tracker.start()
        self.hotkey_listener.start()

        # If Obsidian vault path is empty on first run, offer a gentle notification
        if not config.obsidian_vault_path:
            print("[WizDesk] Tip: Configure your Obsidian Vault path in Settings to enable daily log sync.")

    def show_quick_entry(self) -> None:
        """Open or focus the Quick-Entry note and task dialog."""
        if self._quick_entry_dialog is None or not self._quick_entry_dialog.isVisible():
            self._quick_entry_dialog = QuickEntryDialog(self.state_machine, self.repo)
            self._quick_entry_dialog.show()
        self._quick_entry_dialog.raise_()
        self._quick_entry_dialog.activateWindow()

    def show_settings(self) -> None:
        """Open or focus the settings dialog."""
        if self._settings_dialog is None or not self._settings_dialog.isVisible():
            self._settings_dialog = SettingsDialog(self.repo)
            self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def trigger_sync(self) -> None:
        """Run manual or scheduled Obsidian sync."""
        success, msg = self.sync_engine.sync_date(date.today())
        if success:
            self.state_machine.trigger_complete(duration_ms=3000)

    def _on_sync_finished(self, success: bool, message: str) -> None:
        """Handle sync completion notifications."""
        icon = TrayIcon.MessageIcon.Information if success else TrayIcon.MessageIcon.Warning
        self.tray_icon.showMessage("WizDesk Sync", message, icon, 3000)

    def _on_session_polled(self, app_name: str, window_title: str, project_tag: str) -> None:
        """Briefly react when activity tracking records active project work."""
        if project_tag:
            self.state_machine.trigger_working()

    def shutdown(self) -> None:
        """Gracefully stop background threads and flush pending data."""
        print("[WizDesk] Shutting down background services...")
        self.tracker.stop()
        self.hotkey_listener.stop()


def main() -> None:
    """Initialize and run the WizDesk companion application."""
    set_windows_app_id()

    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("WizDesk")
    app.setApplicationDisplayName("WizDesk")
    app.setQuitOnLastWindowClosed(False)

    wiz_app = WizApplication()
    wiz_app.start()

    # Connect app quit
    app_signals.quit_application.connect(lambda: (wiz_app.shutdown(), app.quit()))

    print("[WizDesk] Desktop Companion running.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
