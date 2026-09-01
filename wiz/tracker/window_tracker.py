"""Background active window tracker using pywin32 and psutil."""

import sys
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.storage.models import StorageRepository

# Windows API imports
if sys.platform == "win32":
    try:
        import win32gui
        import win32process
        import psutil
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False


@dataclass
class ActiveWindowInfo:
    """Snapshot of foreground application and window title."""
    app_name: str
    window_title: str
    pid: int


def get_active_window_info() -> Optional[ActiveWindowInfo]:
    """Retrieve the currently active foreground window details on Windows."""
    if not HAS_WIN32:
        return None

    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        window_title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid <= 0:
            return None

        try:
            proc = psutil.Process(pid)
            app_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            app_name = "Unknown"

        # Ignore empty/shell tray windows
        if not window_title and app_name in ("ShellExperienceHost.exe", "SearchHost.exe"):
            return None

        return ActiveWindowInfo(
            app_name=app_name,
            window_title=window_title,
            pid=pid,
        )
    except Exception as e:
        print(f"[WindowTracker] Error fetching active window: {e}")
        return None


class WindowTracker(QThread):
    """
    Background worker thread that periodically polls the active foreground window,
    matches project keywords, logs sessions to SQLite, and emits signals.
    """

    session_recorded = pyqtSignal(str, str, str)  # app_name, window_title, project_tag

    def __init__(self, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.repo = repository or StorageRepository()
        self._is_running: bool = True
        self._last_poll_time: datetime = datetime.now()

        # Session tracking state
        self._current_app: Optional[str] = None
        self._current_title: Optional[str] = None
        self._current_project: Optional[str] = None
        self._session_start: datetime = datetime.now()

    def stop(self) -> None:
        """Signal the background thread to terminate."""
        self._is_running = False
        self.wait(2000)

    def run(self) -> None:
        """Main background tracking loop."""
        print("[WindowTracker] Background activity tracker started.")

        # Polling frequency for active change detection
        # Note: PRD defines 30m intervals for session chunking, we check window state every 5s
        # and flush completed session chunks to DB.
        check_interval_sec = 5

        while self._is_running:
            try:
                now = datetime.now()
                info = get_active_window_info()

                if info:
                    project_tag = self.repo.match_project_tag(f"{info.window_title} {info.app_name}")

                    # Check if active window/app changed or if 5m session limit reached
                    elapsed = (now - self._session_start).total_seconds()
                    max_session_sec = config.get("tracking_interval_seconds", 300)

                    app_changed = (self._current_app != info.app_name)
                    title_changed = (self._current_title != info.window_title)

                    if self._current_app is not None and (app_changed or elapsed >= max_session_sec):
                        # Flush previous session to database if valid duration (> 10s)
                        if elapsed >= 10:
                            self.repo.log_session(
                                app_name=self._current_app,
                                window_title=self._current_title or "",
                                start_time=self._session_start,
                                end_time=now,
                                project_tag=self._current_project,
                            )
                            self.session_recorded.emit(
                                self._current_app,
                                self._current_title or "",
                                self._current_project or "",
                            )
                            app_signals.session_polled.emit(
                                self._current_app,
                                self._current_title or "",
                                self._current_project or "",
                            )

                        # Reset session start
                        self._session_start = now

                    # Update current tracking state
                    self._current_app = info.app_name
                    self._current_title = info.window_title
                    self._current_project = project_tag

            except Exception as e:
                print(f"[WindowTracker] Exception in tracking loop: {e}")

            # Sleep in short slices for responsive stop
            for _ in range(check_interval_sec * 2):
                if not self._is_running:
                    break
                time.sleep(0.5)

        # Flush final session before exit
        if self._current_app and (datetime.now() - self._session_start).total_seconds() >= 10:
            try:
                self.repo.log_session(
                    app_name=self._current_app,
                    window_title=self._current_title or "",
                    start_time=self._session_start,
                    end_time=datetime.now(),
                    project_tag=self._current_project,
                )
            except Exception as e:
                print(f"[WindowTracker] Error logging final session on stop: {e}")

        print("[WindowTracker] Background activity tracker stopped.")
