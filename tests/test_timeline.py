"""Tests for timeline storage queries, session aggregation, and metrics."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from wiz.storage.db import Database
from wiz.storage.models import (
    StorageRepository,
    SessionRecord,
    aggregate_sessions,
)


@pytest.fixture
def repo(tmp_path: Path) -> StorageRepository:
    """Provide a fresh StorageRepository backed by an isolated temporary database."""
    db_file = tmp_path / "test_timeline.db"
    db = Database(db_path=db_file)
    return StorageRepository(db)


def test_aggregate_sessions_empty():
    """Empty list returns empty list."""
    assert aggregate_sessions([]) == []


def test_aggregate_sessions_contiguous():
    """Contiguous sessions of the same app and project merge into one block."""
    t0 = datetime(2026, 9, 10, 9, 0, 0)
    t1 = t0 + timedelta(minutes=5)
    t2 = t1 + timedelta(minutes=5)
    t3 = t2 + timedelta(minutes=5)

    s1 = SessionRecord(id=1, app_name="Code.exe", window_title="main.py", project_tag="WizDesk", start_time=t0, end_time=t1)
    s2 = SessionRecord(id=2, app_name="Code.exe", window_title="popup.py", project_tag="WizDesk", start_time=t1, end_time=t2)
    s3 = SessionRecord(id=3, app_name="Code.exe", window_title="models.py", project_tag="WizDesk", start_time=t2, end_time=t3)

    merged = aggregate_sessions([s1, s2, s3], max_gap_minutes=5)
    assert len(merged) == 1
    block = merged[0]
    assert block["app_name"] == "Code.exe"
    assert block["project_tag"] == "WizDesk"
    assert block["start_time"] == t0
    assert block["end_time"] == t3
    assert block["duration_minutes"] == 15.0
    assert block["session_count"] == 3


def test_aggregate_sessions_different_apps_and_projects():
    """Sessions with different applications or projects remain distinct."""
    t0 = datetime(2026, 9, 10, 9, 0, 0)
    t1 = t0 + timedelta(minutes=5)
    t2 = t1 + timedelta(minutes=5)

    s1 = SessionRecord(id=1, app_name="Code.exe", window_title="main.py", project_tag="ProjectA", start_time=t0, end_time=t1)
    s2 = SessionRecord(id=2, app_name="Chrome.exe", window_title="Search", project_tag="ProjectA", start_time=t1, end_time=t2)
    s3 = SessionRecord(id=3, app_name="Chrome.exe", window_title="Docs", project_tag="ProjectB", start_time=t2, end_time=t2 + timedelta(minutes=5))

    merged = aggregate_sessions([s1, s2, s3], max_gap_minutes=5)
    assert len(merged) == 3
    assert merged[0]["app_name"] == "Code.exe"
    assert merged[1]["app_name"] == "Chrome.exe"
    assert merged[1]["project_tag"] == "ProjectA"
    assert merged[2]["project_tag"] == "ProjectB"


def test_aggregate_sessions_gap_threshold():
    """A gap exceeding max_gap_minutes prevents merging."""
    t0 = datetime(2026, 9, 10, 9, 0, 0)
    t1 = t0 + timedelta(minutes=5)
    t2 = t1 + timedelta(minutes=10)  # 10 minute gap
    t3 = t2 + timedelta(minutes=5)

    s1 = SessionRecord(id=1, app_name="Code.exe", window_title="main.py", project_tag="WizDesk", start_time=t0, end_time=t1)
    s2 = SessionRecord(id=2, app_name="Code.exe", window_title="main.py", project_tag="WizDesk", start_time=t2, end_time=t3)

    merged = aggregate_sessions([s1, s2], max_gap_minutes=5)
    assert len(merged) == 2


def test_timeline_events_unification_and_metrics(repo: StorageRepository):
    """Verify combined chronological events and summary metrics for a date."""
    target_date = "2026-09-10"

    # 1. Log two sessions
    t1 = datetime(2026, 9, 10, 9, 0, 0)
    t2 = t1 + timedelta(minutes=15)
    repo.log_session("VS Code", "models.py", t1, t2, project_tag="WizDesk")

    t3 = datetime(2026, 9, 10, 11, 0, 0)
    t4 = t3 + timedelta(minutes=20)
    repo.log_session("Chrome", "Documentation", t3, t4, project_tag="Research")

    # 2. Add task and complete a subtask at 10:00
    task_id = repo.create_task("Implement timeline", project_tag="WizDesk")
    subtask_id = repo.add_subtask(task_id, "Build aggregation engine")
    comp_time = datetime(2026, 9, 10, 10, 0, 0)
    repo.update_subtask_status(subtask_id, "done", completed_at=comp_time)

    # 3. Add note at 10:30
    note_time = datetime(2026, 9, 10, 10, 30, 0)
    repo.create_note("Tested session merging logic", project_tag="WizDesk", created_at=note_time)

    # Fetch unified timeline events
    events = repo.get_day_timeline_events(target_date)
    assert len(events) == 4

    # Verify chronological ordering:
    # 09:00 (VS Code session) -> 10:00 (subtask done) -> 10:30 (note) -> 11:00 (Chrome session)
    assert events[0]["event_type"] == "session"
    assert events[0]["title"] == "VS Code"
    assert events[0]["duration_minutes"] == 15.0

    assert events[1]["event_type"] == "task"
    assert events[1]["title"] == "Build aggregation engine"
    assert events[1]["subtitle"] == "Parent: Implement timeline"

    assert events[2]["event_type"] == "note"
    assert events[2]["title"] == "Tested session merging logic"

    assert events[3]["event_type"] == "session"
    assert events[3]["title"] == "Chrome"

    # Verify metrics
    metrics = repo.get_day_metrics(target_date)
    assert metrics["total_tracked_minutes"] == 35.0  # 15m + 20m
    assert metrics["completed_tasks_count"] == 1
    assert metrics["notes_count"] == 1
    assert metrics["unique_apps_count"] == 2


from PyQt6.QtWidgets import QApplication
from wiz.core.state_machine import StateMachine
from wiz.ui.popup_dialog import QuickEntryDialog
from wiz.ui.timeline_view import TimelineView, AppSessionCard, MilestoneCard, EmptyStateCard


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance is initialized."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_timeline_view_ui_filtering_and_theming(qapp, repo: StorageRepository):
    """Test TimelineView widget layout, category filtering, and theme switching."""
    target_date = "2026-09-10"

    # Seed data
    t1 = datetime(2026, 9, 10, 9, 0, 0)
    t2 = t1 + timedelta(minutes=30)
    repo.log_session("VS Code", "models.py", t1, t2, project_tag="WizDesk")

    task_id = repo.create_task("Review timeline", project_tag="WizDesk")
    subtask_id = repo.add_subtask(task_id, "Check UI polish")
    repo.update_subtask_status(subtask_id, "done", completed_at=datetime(2026, 9, 10, 10, 0, 0))

    repo.create_note("Quick note item", project_tag="Other", created_at=datetime(2026, 9, 10, 11, 0, 0))

    # Initialize TimelineView
    view = TimelineView(repo, is_dark=False)
    view.load_date(target_date)

    # All events: 1 session + 1 task + 1 note = 3 cards
    assert view.events_layout.count() == 3

    # Filter to Apps only
    view.btn_apps.click()
    assert view.events_layout.count() == 1
    card = view.events_layout.itemAt(0).widget()
    assert isinstance(card, AppSessionCard)

    # Filter to Tasks & Notes only
    view.btn_tasks.click()
    assert view.events_layout.count() == 2
    for i in range(view.events_layout.count()):
        assert isinstance(view.events_layout.itemAt(i).widget(), MilestoneCard)

    # Reset to All
    view.btn_all.click()
    assert view.events_layout.count() == 3

    # Filter by project 'WizDesk'
    idx = view.project_combo.findText("WizDesk")
    if idx >= 0:
        view.project_combo.setCurrentIndex(idx)
        # Should have 2 items: session (WizDesk) and task (WizDesk)
        assert view.events_layout.count() == 2

    # Date with zero activity renders EmptyStateCard
    view.load_date("2020-01-01")
    assert view.events_layout.count() == 1
    assert isinstance(view.events_layout.itemAt(0).widget(), EmptyStateCard)

    # Theme toggle
    view.set_theme(is_dark=True)
    assert view.is_dark is True
    view.set_theme(is_dark=False)
    assert view.is_dark is False


def test_quick_entry_dialog_activity_mode_switcher(qapp, repo: StorageRepository):
    """Test switching to Activity Timeline view mode inside QuickEntryDialog."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    assert hasattr(dialog, "activity_mode_btn")
    assert hasattr(dialog, "timeline_view")

    # Initially on tasks
    assert dialog.current_view_mode == "tasks"
    assert dialog.stack.currentWidget() == dialog.tasks_page

    # Switch to Activity mode
    dialog.activity_mode_btn.click()
    assert dialog.current_view_mode == "activity"
    assert dialog.stack.currentWidget() == dialog.timeline_view

    # Switch to Quick Notes
    dialog.notes_mode_btn.click()
    assert dialog.current_view_mode == "notes"
    assert dialog.stack.currentWidget() == dialog.notes_page

    # Switch back to Tasks
    dialog.tasks_mode_btn.click()
    assert dialog.current_view_mode == "tasks"
    assert dialog.stack.currentWidget() == dialog.tasks_page

