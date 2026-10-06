"""
Unit and integration tests for WizDesk v1.2.0 Task Stopwatch.
Tests active elapsed time tracking, start, pause, resume, completion, and shutdown persistence.
"""

from datetime import datetime, timedelta
import pytest
from PyQt6.QtCore import Qt
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository, TaskRecord
from wiz.ui.popup_dialog import format_duration_seconds, TaskStopwatchWidget, TaskRowWidget


@pytest.fixture
def repo(tmp_path):
    """Provide a clean isolated database repository for stopwatch testing."""
    db = Database(db_path=tmp_path / "test_stopwatch.db")
    repo_obj = StorageRepository(db=db)
    yield repo_obj
    db.close()


def test_format_duration_seconds():
    """Verify format_duration_seconds formats standard and compact timestamps correctly."""
    assert format_duration_seconds(0, compact=False) == "00:00"
    assert format_duration_seconds(0, compact=True) == "0m"

    assert format_duration_seconds(45, compact=False) == "00:45"
    assert format_duration_seconds(45, compact=True) == "1m"

    assert format_duration_seconds(1440, compact=False) == "24:00"
    assert format_duration_seconds(1440, compact=True) == "24m"

    assert format_duration_seconds(3600, compact=False) == "1:00:00"
    assert format_duration_seconds(3600, compact=True) == "1h"

    assert format_duration_seconds(4500, compact=False) == "1:15:00"
    assert format_duration_seconds(4500, compact=True) == "1h 15m"


def test_task_stopwatch_repository_lifecycle(repo: StorageRepository):
    """Test start, pause, resume, and completion of task stopwatches in StorageRepository."""
    task_id = repo.create_task("Write parser module", project_tag="Work")
    tasks = repo.get_task_hierarchy(include_completed=True)
    t = [task for task in tasks if task.id == task_id][0]
    assert t.duration_seconds == 0
    assert not t.is_timer_running
    assert t.total_elapsed_seconds == 0

    # 1. Start stopwatch
    started = repo.start_task_stopwatch(task_id)
    assert started is True

    tasks = repo.get_task_hierarchy(include_completed=True)
    t = [task for task in tasks if task.id == task_id][0]
    assert t.is_timer_running is True
    assert t.status == "in_progress"
    assert t.timer_started_at is not None

    # Simulate 12 seconds elapsed
    simulated_start = datetime.now() - timedelta(seconds=12)
    repo.update_task_duration(task_id, duration_seconds=0, timer_started_at=simulated_start)

    tasks = repo.get_task_hierarchy(include_completed=True)
    t = [task for task in tasks if task.id == task_id][0]
    assert t.total_elapsed_seconds >= 12

    # 2. Pause stopwatch
    paused = repo.pause_task_stopwatch(task_id)
    assert paused is True

    tasks = repo.get_task_hierarchy(include_completed=True)
    t = [task for task in tasks if task.id == task_id][0]
    assert not t.is_timer_running
    assert t.duration_seconds >= 12

    # 3. Resume stopwatch
    repo.start_task_stopwatch(task_id)
    simulated_resume = datetime.now() - timedelta(seconds=8)
    repo.update_task_duration(task_id, duration_seconds=t.duration_seconds, timer_started_at=simulated_resume)

    # 4. Complete task stopwatch
    completed = repo.complete_task_stopwatch(task_id)
    assert completed is True

    tasks = repo.get_task_hierarchy(include_completed=True)
    t = [task for task in tasks if task.id == task_id][0]
    assert t.status == "done"
    assert not t.is_timer_running
    assert t.duration_seconds >= 20


def test_task_stopwatch_flush_all(repo: StorageRepository):
    """Verify that flush_all_running_stopwatches safely commits all ticking tasks to database."""
    t1 = repo.create_task("Ticking Task 1", project_tag="Work")
    t2 = repo.create_task("Ticking Task 2", project_tag="Work")

    repo.start_task_stopwatch(t1)
    repo.start_task_stopwatch(t2)

    # Set artificial start times
    dt1 = datetime.now() - timedelta(seconds=40)
    dt2 = datetime.now() - timedelta(seconds=75)
    repo.update_task_duration(t1, duration_seconds=10, timer_started_at=dt1)
    repo.update_task_duration(t2, duration_seconds=20, timer_started_at=dt2)

    flushed_count = repo.flush_all_running_stopwatches()
    assert flushed_count == 2

    tasks = repo.get_task_hierarchy(include_completed=True)
    t1_rec = [t for t in tasks if t.id == t1][0]
    t2_rec = [t for t in tasks if t.id == t2][0]

    assert not t1_rec.is_timer_running
    assert not t2_rec.is_timer_running
    assert t1_rec.duration_seconds >= 50
    assert t2_rec.duration_seconds >= 95


def test_task_stopwatch_widget_ui(qapp, repo: StorageRepository):
    """Test TaskStopwatchWidget UI toggling, live ticking, and theme changes."""
    task_id = repo.create_task("UI Timer Test", project_tag="Work")
    tasks = repo.get_task_hierarchy(include_completed=True)
    task = [t for t in tasks if t.id == task_id][0]

    widget = TaskStopwatchWidget(task=task, repo=repo, is_dark=False)
    assert widget.btn.isVisible()
    assert not widget.ticker.isActive()

    # Toggle to start timer
    widget._toggle_stopwatch()
    assert widget.task.is_timer_running is True
    assert widget.ticker.isActive() is True
    assert widget.time_label.isVisible() is True

    # Toggle to pause timer
    widget._toggle_stopwatch()
    assert widget.task.is_timer_running is False
    assert widget.ticker.isActive() is False

    # Mark completed
    widget.task.status = "done"
    widget.task.duration_seconds = 120
    widget.refresh()
    assert not widget.btn.isVisible()
    assert widget.time_label.isVisible()
    assert "2m" in widget.time_label.text()

    # Theme toggle
    widget.set_theme(is_dark=True)
    assert widget.is_dark is True

    widget.deleteLater()


def test_task_row_stopwatch_integration(qapp, repo: StorageRepository):
    """Verify that starting stopwatch on TaskRowWidget updates row status and completion flushes timer."""
    task_id = repo.create_task("Integration Row Test", project_tag="Work")
    tasks = repo.get_task_hierarchy(include_completed=True)
    task = [t for t in tasks if t.id == task_id][0]

    row = TaskRowWidget(task, all_projects=["Work"], is_dark=False, repo=repo)
    assert hasattr(row, "stopwatch_widget")

    # Start stopwatch via widget button
    row.stopwatch_widget._toggle_stopwatch()
    assert row.task.status == "in_progress"
    assert row.status_combo.currentText() == "In progress"

    # Mark task done via checkbox
    row.checkbox.setChecked(True)
    assert row.task.status == "done"
    assert not row.task.is_timer_running
    assert not row.stopwatch_widget.btn.isVisible()

    row.deleteLater()
