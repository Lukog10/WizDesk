"""Main application entry point for WizDesk desktop companion."""

import sys
import ctypes
from typing import Optional
from datetime import date

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from wiz.core.config import config
from wiz.core.state_machine import StateMachine, MascotState
from wiz.core.signals import app_signals
from wiz.core.sound import sound_manager
from wiz.storage.models import StorageRepository
from wiz.ui.mascot_window import MascotWindow
from wiz.ui.tray_icon import TrayIcon
from wiz.ui.popup_dialog import QuickEntryDialog
from wiz.ui.quick_bar_dialog import QuickBarPopup
from wiz.ui.settings_dialog import SettingsDialog
from wiz.ui.icons import get_app_icon
from wiz.ui.fonts import init_fonts, get_font, FONT_SANS
from wiz.tracker.window_tracker import WindowTracker
from wiz.sync.obsidian import ObsidianSync
from wiz.utils.hotkey import GlobalHotkeyListener

SINGLE_INSTANCE_SERVER_NAME = "lukog_wizdesk_single_instance_pipe"


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
        self._quick_bar_dialog: Optional[QuickBarPopup] = None
        self._settings_dialog: Optional[SettingsDialog] = None
        self._local_server: Optional[QLocalServer] = None

        # Background Services
        self.tracker = WindowTracker(self.repo)
        self.hotkey_listener = GlobalHotkeyListener()

        # Connect signals
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Bind global signals to UI handlers and actions."""
        # Sound manager initial state
        sound_manager.set_enabled(config.sound_effects_enabled)
        sound_manager.update_volume(config.sound_volume)

        # Mascot state sound effects & inactivity sleep transition
        self.state_machine.state_changed.connect(self._on_mascot_state_changed)
        app_signals.inactivity_detected.connect(self.state_machine.on_inactivity_detected)
        app_signals.activity_resumed.connect(self.state_machine.on_activity_resumed)

        app_signals.request_quick_entry.connect(self.show_quick_entry)
        app_signals.request_quick_task_bar.connect(self.show_quick_task_bar)
        app_signals.request_quick_note_bar.connect(self.show_quick_note_bar)
        app_signals.request_settings.connect(self.show_settings)
        app_signals.request_sync.connect(self.trigger_sync)
        app_signals.sync_finished.connect(self._on_sync_finished)
        app_signals.session_polled.connect(self._on_session_polled)
        app_signals.task_created.connect(self._on_task_created)
        app_signals.task_completed.connect(lambda _: sound_manager.play_task_complete())
        app_signals.task_deleted.connect(lambda _: sound_manager.play_task_delete())
        app_signals.note_created.connect(lambda _: self.sync_engine.sync_date(date.today(), emit_signal=False))
        app_signals.quit_application.connect(self.quit)

    def _on_task_created(self, task_id: int) -> None:
        """Play task add chime and trigger background daily sync."""
        sound_manager.play_task_add()
        self.sync_engine.sync_date(date.today(), emit_signal=False)

    def _on_mascot_state_changed(self, new_state: MascotState) -> None:
        """Play organic audio cues on mascot state transitions."""
        if new_state == MascotState.WORKING:
            sound_manager.play_state_working()
        elif new_state == MascotState.SLEEP:
            sound_manager.play_state_sleep()
        elif new_state == MascotState.IDLE:
            sound_manager.play_state_wake()
        elif new_state == MascotState.COMPLETE:
            sound_manager.play_task_complete()
        elif new_state == MascotState.NOTIFY:
            sound_manager.play_chime()

    def start(self) -> None:
        """Launch UI and background worker threads."""
        self.mascot_window.show()
        self.tray_icon.show()
        self.tracker.start()
        self.hotkey_listener.start()

        # If Obsidian vault path is empty on first run, offer a gentle notification
        if not config.obsidian_vault_path or not config.obsidian_vault_path.exists():
            print("[WizDesk] Tip: Configure your Obsidian Vault path in Settings to enable daily log sync.")
        else:
            self.sync_engine.sync_date(date.today(), emit_signal=False)

        # Check and perform automated database backup if scheduled
        if config.get("auto_backup_enabled", True):
            try:
                from wiz.storage.backup import backup_manager
                last_bak = config.get("last_backup_date", "")
                today_str = date.today().isoformat()
                interval = int(config.get("auto_backup_interval_days", 1))
                should_backup = False
                if not last_bak:
                    should_backup = True
                else:
                    last_date = date.fromisoformat(last_bak)
                    if (date.today() - last_date).days >= interval:
                        should_backup = True
                if should_backup:
                    backup_manager.create_backup(self.repo.db, tag="auto")
                    config.set("last_backup_date", today_str)
            except Exception as e:
                print(f"[WizDesk] Auto-backup notice: {e}")

    def show_quick_entry(self) -> None:
        """Open or focus the full Quick-Entry workspace dialog."""
        sound_manager.play_window_open()
        if self._quick_entry_dialog is None:
            self._quick_entry_dialog = QuickEntryDialog(self.state_machine, self.repo)
        if self._quick_entry_dialog.isMinimized():
            self._quick_entry_dialog.showNormal()
        self._quick_entry_dialog.show()
        self._quick_entry_dialog.raise_()
        self._quick_entry_dialog.activateWindow()

    def show_quick_task_bar(self) -> None:
        """Open the compact Quick Task bar positioned near the mascot (Double-click gesture)."""
        sound_manager.play_window_open()
        if self._quick_bar_dialog is None:
            self._quick_bar_dialog = QuickBarPopup(self.state_machine, self.repo)
        self._quick_bar_dialog.show_mode("task", mascot_rect=self.mascot_window.geometry())

    def show_quick_note_bar(self) -> None:
        """Open the compact Quick Note bar positioned near the mascot (Triple-click gesture)."""
        sound_manager.play_window_open()
        if self._quick_bar_dialog is None:
            self._quick_bar_dialog = QuickBarPopup(self.state_machine, self.repo)
        self._quick_bar_dialog.show_mode("note", mascot_rect=self.mascot_window.geometry())

    def show_settings(self) -> None:
        """Open or focus the embedded settings view inside the workspace."""
        self.show_quick_entry()
        if self._quick_entry_dialog:
            self._quick_entry_dialog._set_view_mode("settings")

    def trigger_sync(self) -> None:
        """Run manual or scheduled Obsidian sync."""
        success, msg = self.sync_engine.sync_date(date.today(), emit_signal=True)
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
        self.sync_engine.sync_date(date.today(), emit_signal=False)

    def shutdown(self) -> None:
        """Gracefully stop background threads and flush pending data."""
        print("[WizDesk] Shutting down background services...")
        self.tracker.stop()
        self.hotkey_listener.stop()
        self.sync_engine.sync_date(date.today(), emit_signal=False)

    def quit(self) -> None:
        """Gracefully shut down background services, hide tray, and exit application."""
        self.shutdown()
        if self._local_server:
            self._local_server.close()
            QLocalServer.removeServer(SINGLE_INSTANCE_SERVER_NAME)
        if self.tray_icon:
            self.tray_icon.hide()
        if self.mascot_window:
            self.mascot_window.close()
        if self._quick_entry_dialog:
            self._quick_entry_dialog.close()
        if self._quick_bar_dialog:
            self._quick_bar_dialog.close()
        if self._settings_dialog:
            self._settings_dialog.close()
        app = QApplication.instance()
        if app:
            app.quit()


def main() -> None:
    """Initialize and run the WizDesk companion application."""
    set_windows_app_id()

    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Enforce Single-Instance application lock
    test_socket = QLocalSocket()
    test_socket.connectToServer(SINGLE_INSTANCE_SERVER_NAME)
    if test_socket.waitForConnected(400):
        # Existing instance is alive: request it to focus the workspace and exit
        test_socket.write(b"show_workspace\n")
        test_socket.flush()
        test_socket.waitForBytesWritten(600)
        test_socket.close()
        print("[WizDesk] Another instance is already running. Focused active window.")
        sys.exit(0)

    # Initialize local server on primary instance
    QLocalServer.removeServer(SINGLE_INSTANCE_SERVER_NAME)
    local_server = QLocalServer()
    local_server.listen(SINGLE_INSTANCE_SERVER_NAME)

    init_fonts()
    app.setFont(get_font(10))
    # Global stylesheet: ensures font-family cascades to every widget,
    # even if individual stylesheets set only font-size (which resets family in Qt).
    app.setStyleSheet(f"* {{ font-family: {FONT_SANS}; }}")
    app.setApplicationName("WizDesk")
    app.setApplicationDisplayName("WizDesk")
    app.setWindowIcon(get_app_icon("wiz-idle.svg"))
    app.setQuitOnLastWindowClosed(False)

    wiz_app = WizApplication()
    wiz_app._local_server = local_server

    def _handle_instance_message():
        sock = local_server.nextPendingConnection()
        if sock:
            sock.readyRead.connect(lambda: _on_socket_read(sock))

    def _on_socket_read(sock: QLocalSocket):
        data = bytes(sock.readAll()).decode("utf-8", errors="ignore")
        if "show_workspace" in data:
            wiz_app.show_quick_entry()
        sock.close()

    local_server.newConnection.connect(_handle_instance_message)
    wiz_app.start()

    # Handle graceful exit on OS signals
    import signal
    signal.signal(signal.SIGINT, lambda *_: wiz_app.quit())

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        wiz_app.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()
