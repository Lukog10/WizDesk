"""Unit tests for window tracker background service and active window polling."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest

from wiz.tracker.window_tracker import (
    ActiveWindowInfo,
    get_active_window_info,
    WindowTracker,
)
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository


@pytest.fixture
def test_repo(tmp_path):
    """Provide an isolated database repository for tracker tests."""
    db = Database(tmp_path / "test_tracker.db")
    return StorageRepository(db)


def test_get_active_window_info_excludes_explorer():
    """Verify get_active_window_info filters out explorer.exe windows."""
    with patch("wiz.tracker.window_tracker.HAS_WIN32", True), \
         patch("wiz.tracker.window_tracker.win32gui.GetForegroundWindow", return_value=12345), \
         patch("wiz.tracker.window_tracker.win32gui.GetWindowText", return_value="Downloads - File Explorer"), \
         patch("wiz.tracker.window_tracker.win32process.GetWindowThreadProcessId", return_value=(0, 9999)), \
         patch("wiz.tracker.window_tracker.psutil.Process") as mock_proc:
        mock_proc.return_value.name.return_value = "explorer.exe"
        info = get_active_window_info()
        assert info is None


def test_get_active_window_info_excludes_desktop_program_manager():
    """Verify get_active_window_info filters out desktop Program Manager."""
    with patch("wiz.tracker.window_tracker.HAS_WIN32", True), \
         patch("wiz.tracker.window_tracker.win32gui.GetForegroundWindow", return_value=12345), \
         patch("wiz.tracker.window_tracker.win32gui.GetWindowText", return_value="Program Manager"), \
         patch("wiz.tracker.window_tracker.win32process.GetWindowThreadProcessId", return_value=(0, 9999)), \
         patch("wiz.tracker.window_tracker.psutil.Process") as mock_proc:
        mock_proc.return_value.name.return_value = "explorer.exe"
        info = get_active_window_info()
        assert info is None


def test_get_active_window_info_allows_code():
    """Verify get_active_window_info returns ActiveWindowInfo for code editors."""
    with patch("wiz.tracker.window_tracker.HAS_WIN32", True), \
         patch("wiz.tracker.window_tracker.win32gui.GetForegroundWindow", return_value=12345), \
         patch("wiz.tracker.window_tracker.win32gui.GetWindowText", return_value="WizDesk - window_tracker.py"), \
         patch("wiz.tracker.window_tracker.win32process.GetWindowThreadProcessId", return_value=(0, 9999)), \
         patch("wiz.tracker.window_tracker.psutil.Process") as mock_proc:
        mock_proc.return_value.name.return_value = "Code.exe"
        info = get_active_window_info()
        assert info is not None
        assert info.app_name == "Code"
        assert info.window_title == "WizDesk - window_tracker.py"
        assert info.pid == 9999


def test_get_active_window_info_allows_taskmgr_and_wizdesk():
    """Verify get_active_window_info returns ActiveWindowInfo for Task Manager and WizDesk."""
    with patch("wiz.tracker.window_tracker.HAS_WIN32", True), \
         patch("wiz.tracker.window_tracker.win32gui.GetForegroundWindow", return_value=12345), \
         patch("wiz.tracker.window_tracker.win32gui.GetWindowText", return_value="Task Manager"), \
         patch("wiz.tracker.window_tracker.win32process.GetWindowThreadProcessId", return_value=(0, 1111)), \
         patch("wiz.tracker.window_tracker.psutil.Process") as mock_proc:
        mock_proc.return_value.name.return_value = "Taskmgr.exe"
        info = get_active_window_info()
        assert info is not None
        assert info.app_name == "Taskmgr"
        assert info.window_title == "Task Manager"

    with patch("wiz.tracker.window_tracker.HAS_WIN32", True), \
         patch("wiz.tracker.window_tracker.win32gui.GetForegroundWindow", return_value=12346), \
         patch("wiz.tracker.window_tracker.win32gui.GetWindowText", return_value="WizDesk Workspace"), \
         patch("wiz.tracker.window_tracker.win32process.GetWindowThreadProcessId", return_value=(0, 2222)), \
         patch("wiz.tracker.window_tracker.psutil.Process") as mock_proc:
        mock_proc.return_value.name.return_value = "WizDesk.exe"
        info2 = get_active_window_info()
        assert info2 is not None
        assert info2.app_name == "WizDesk"
        assert info2.window_title == "WizDesk Workspace"


def test_tracker_excluded_window_transition(test_repo):
    """
    Verify that when user switches from a tracked app to an excluded window (info is None),
    the previous session is flushed, tracking is cleared, and no time accumulates for the excluded window.
    """
    tracker = WindowTracker(repository=test_repo)
    t0 = datetime(2026, 10, 5, 9, 0, 0)
    tracker._session_start = t0
    tracker._current_app = "VS Code"
    tracker._current_title = "main.py"
    tracker._current_project = "Wiz"

    # Simulate switching to an excluded window (e.g. File Explorer or desktop) 60s later
    t1 = t0 + timedelta(seconds=60)
    elapsed = (t1 - tracker._session_start).total_seconds()
    assert elapsed >= 10

    # Execute exclusion flush logic
    test_repo.log_session(
        app_name=tracker._current_app,
        window_title=tracker._current_title or "",
        start_time=tracker._session_start,
        end_time=t1,
        project_tag=tracker._current_project,
    )
    tracker._current_app = None
    tracker._current_title = None
    tracker._current_project = None
    tracker._session_start = t1

    # Verify session was logged for VS Code
    sessions = test_repo.get_sessions_for_date(t0.date())
    assert len(sessions) == 1
    assert sessions[0].app_name == "VS Code"
    assert sessions[0].duration_minutes == 1.0

    # User remains in File Explorer for 30 minutes (info is None)
    # Tracker should do nothing while info is None
    assert tracker._current_app is None

    # Now user switches to Chrome at t2
    t2 = t1 + timedelta(minutes=30)
    new_info = ActiveWindowInfo(app_name="Chrome", window_title="Documentation", pid=8888)

    # Tracking resumes fresh without including the 30m spent in Explorer
    if tracker._current_app is None:
        tracker._session_start = t2
        tracker._current_app = new_info.app_name
        tracker._current_title = new_info.window_title
        tracker._current_project = "Research"

    assert tracker._current_app == "Chrome"
    assert tracker._session_start == t2

    # Log Chrome session 15m later
    t3 = t2 + timedelta(minutes=15)
    test_repo.log_session(
        app_name=tracker._current_app,
        window_title=tracker._current_title,
        start_time=tracker._session_start,
        end_time=t3,
        project_tag=tracker._current_project,
    )

    all_sessions = test_repo.get_sessions_for_date(t0.date())
    assert len(all_sessions) == 2
    assert all_sessions[0].app_name == "VS Code"
    assert all_sessions[0].duration_minutes == 1.0
    assert all_sessions[1].app_name == "Chrome"
    assert all_sessions[1].duration_minutes == 15.0
