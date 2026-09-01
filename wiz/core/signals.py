"""Central PyQt signal hub for decoupled application communication."""

from PyQt6.QtCore import QObject, pyqtSignal


class AppSignals(QObject):
    """Central event bus emitting signals across application modules."""

    # UI / Mascot visibility & action signals
    toggle_mascot_visibility = pyqtSignal()
    request_quick_entry = pyqtSignal()
    request_settings = pyqtSignal()
    request_sync = pyqtSignal()
    quit_application = pyqtSignal()
    theme_changed = pyqtSignal(str)  # 'light' or 'dark'

    # Tracking & Activity signals
    # session_polled: (app_name: str, window_title: str, project_tag: str)
    session_polled = pyqtSignal(str, str, str)

    # Note / Task logging events
    note_created = pyqtSignal(int)      # note_id
    task_created = pyqtSignal(int)      # task_id
    task_updated = pyqtSignal(int)      # task_id
    task_completed = pyqtSignal(int)    # task_id

    # Obsidian sync status
    # sync_finished: (success: bool, message: str)
    sync_finished = pyqtSignal(bool, str)


# Global singleton instance
app_signals = AppSignals()
