"""
Unit and integration tests for Task Stopwatch and Status Synchronization.
Verifies:
1. Status change to in_progress automatically starts stopwatch and preserves existing duration.
2. Status change to done automatically finishes stopwatch and adds elapsed time.
3. Re-opening completed work to in_progress continues from tracked duration.
4. Status change to not_started or cancelled pauses stopwatch and flushes delta.
5. Manual Play sets status in_progress; Manual Pause keeps status in_progress.
6. App shutdown flush (flush_all_running_stopwatches) leaves tasks in_progress and clears timer_started_at.
7. Startup recovery (recover_dangling_stopwatches) caps elapsed delta to latest window session.
8. Periodic heartbeat commits delta safely.
9. UI synchronization in TaskRowWidget and TaskStopwatchWidget.
"""

from datetime import datetime, timedelta
import pytest
from PyQt6.QtWidgets import QApplication

from wiz.storage.db import Database
from wiz.storage.models import StorageRepository, TaskRecord
from wiz.ui.popup_dialog import TaskRowWidget, TaskStopwatchWidget


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance for UI widget testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def repo(tmp_path):
    """Provide an isolated database and repository for each test."""
    db = Database(db_path=tmp_path / "test_stopwatch_sync.db")
    repo_obj = StorageRepository(db=db)
    yield repo_obj
    db.close()


def test_status_to_in_progress_starts_stopwatch(repo: StorageRepository):
    """Setting status to in_progress starts the stopwatch and preserves existing duration."""
    task_id = repo.create_task("Draft proposal", project_tag="General")
    task = repo.get_task_by_id(task_id)
    assert task.status == "not_started"
    assert task.timer_started_at is None
    assert task.duration_seconds == 0

    # 1. Update status to in_progress
    repo.update_task_status(task_id, "in_progress")
    task = repo.get_task_by_id(task_id)
    assert task.status == "in_progress"
    assert task.timer_started_at is not None
    assert task.duration_seconds == 0
    assert task.completed_at is None


def test_status_to_done_commits_duration_and_stops_stopwatch(repo: StorageRepository):
    """Setting status to done stops the stopwatch, adds delta to duration, and stamps completed_at."""
    task_id = repo.create_task("Code parser", project_tag="General")
    repo.update_task_status(task_id, "in_progress")

    # Simulate 15 seconds elapsed
    simulated_start = datetime.now() - timedelta(seconds=15)
    repo.update_task_duration(task_id, duration_seconds=10, timer_started_at=simulated_start)

    # 2. Update status to done
    repo.update_task_status(task_id, "done")
    task = repo.get_task_by_id(task_id)
    assert task.status == "done"
    assert task.timer_started_at is None
    assert task.duration_seconds >= 25
    assert task.completed_at is not None
    assert task.last_completed_date is not None


def test_reopen_completed_task_continues_from_tracked_time(repo: StorageRepository):
    """Changing a completed task back to in_progress preserves duration and restarts stopwatch."""
    task_id = repo.create_task("Prepare presentation", project_tag="General")
    # Mark done with 300 seconds (5 mins) logged
    now = datetime.now()
    repo.update_task_status(task_id, "done")
    repo.update_task_duration(task_id, duration_seconds=300, timer_started_at=None)

    task = repo.get_task_by_id(task_id)
    assert task.status == "done"
    assert task.duration_seconds == 300

    # Re-open by setting status to in_progress
    repo.update_task_status(task_id, "in_progress")
    task = repo.get_task_by_id(task_id)
    assert task.status == "in_progress"
    # Tracked time must be preserved exactly
    assert task.duration_seconds == 300
    # Stopwatch must be ticking
    assert task.timer_started_at is not None
    # Completed date must be cleared
    assert task.completed_at is None
    assert task.last_completed_date is None


def test_status_to_not_started_pauses_stopwatch_and_flushes_delta(repo: StorageRepository):
    """Changing status to not_started or cancelled flushes running delta and clears timer_started_at."""
    task_id = repo.create_task("Research libs", project_tag="General")
    repo.update_task_status(task_id, "in_progress")

    # Simulate 20 seconds elapsed
    simulated_start = datetime.now() - timedelta(seconds=20)
    repo.update_task_duration(task_id, duration_seconds=50, timer_started_at=simulated_start)

    # Change to not_started
    repo.update_task_status(task_id, "not_started")
    task = repo.get_task_by_id(task_id)
    assert task.status == "not_started"
    assert task.timer_started_at is None
    assert task.duration_seconds >= 70
    assert task.completed_at is None


def test_manual_pause_stopwatch_keeps_status_in_progress(repo: StorageRepository):
    """Manually pausing the stopwatch flushes delta into duration and leaves status as in_progress."""
    task_id = repo.create_task("Refactor backend", project_tag="General")
    repo.start_task_stopwatch(task_id)

    simulated_start = datetime.now() - timedelta(seconds=30)
    repo.update_task_duration(task_id, duration_seconds=0, timer_started_at=simulated_start)

    repo.pause_task_stopwatch(task_id)
    task = repo.get_task_by_id(task_id)
    assert task.status == "in_progress"
    assert task.timer_started_at is None
    assert task.duration_seconds >= 30


def test_shutdown_flush_preserves_in_progress_state(repo: StorageRepository):
    """Graceful quit commits elapsed seconds to DB and leaves tasks in_progress paused."""
    t1 = repo.create_task("Task 1", project_tag="General")
    t2 = repo.create_task("Task 2", project_tag="General")

    repo.start_task_stopwatch(t1)
    repo.start_task_stopwatch(t2)

    simulated_start = datetime.now() - timedelta(seconds=45)
    repo.update_task_duration(t1, duration_seconds=10, timer_started_at=simulated_start)
    repo.update_task_duration(t2, duration_seconds=20, timer_started_at=simulated_start)

    flushed = repo.flush_all_running_stopwatches()
    assert flushed == 2

    task1 = repo.get_task_by_id(t1)
    task2 = repo.get_task_by_id(t2)

    assert task1.status == "in_progress"
    assert task1.timer_started_at is None
    assert task1.duration_seconds >= 55

    assert task2.status == "in_progress"
    assert task2.timer_started_at is None
    assert task2.duration_seconds >= 65


def test_startup_recovery_caps_drift_to_last_session(repo: StorageRepository):
    """Startup recovery sweep caps dangling stopwatches using the last session end_time."""
    # 1. Insert an active window session that ended 2 hours ago
    two_hours_ago = datetime.now() - timedelta(hours=2)
    session_start = two_hours_ago - timedelta(minutes=30)
    repo.log_session(
        app_name="Code.exe",
        window_title="models.py",
        project_tag="General",
        start_time=session_start,
        end_time=two_hours_ago,
    )

    # 2. Insert a task whose timer started 3 hours ago (before crash)
    three_hours_ago = datetime.now() - timedelta(hours=3)
    task_id = repo.create_task("Fix crash bug", project_tag="General")
    repo.update_task_duration(task_id, duration_seconds=100, timer_started_at=three_hours_ago)

    # 3. Run recovery sweep
    recovered = repo.recover_dangling_stopwatches()
    assert recovered == 1

    task = repo.get_task_by_id(task_id)
    assert task.status == "in_progress"
    assert task.timer_started_at is None
    # Delta should be capped to (two_hours_ago - three_hours_ago) = ~3600 seconds (1 hour)
    # plus existing 100 seconds = ~3700 seconds. NOT 3 full hours!
    assert 3500 <= task.duration_seconds <= 3800


def test_periodic_heartbeat_flushes_delta(repo: StorageRepository):
    """Periodic heartbeat commits elapsed delta to duration_seconds and advances timer_started_at."""
    task_id = repo.create_task("Long running task", project_tag="General")
    repo.start_task_stopwatch(task_id)

    simulated_start = datetime.now() - timedelta(seconds=60)
    repo.update_task_duration(task_id, duration_seconds=100, timer_started_at=simulated_start)

    count = repo.periodic_stopwatch_heartbeat()
    assert count == 1

    task = repo.get_task_by_id(task_id)
    assert task.status == "in_progress"
    assert task.timer_started_at is not None
    assert task.duration_seconds >= 160


def test_task_row_ui_status_and_stopwatch_sync(qapp, repo: StorageRepository):
    """Test TaskRowWidget dropdown selection and stopwatch button synchronization."""
    task_id = repo.create_task("UI Sync Task", project_tag="General")
    task = repo.get_task_by_id(task_id)

    row = TaskRowWidget(task, all_projects=["General"], repo=repo)

    # Change dropdown to In progress
    row.status_combo.setCurrentText("In progress")
    assert row.task.status == "in_progress"
    assert row.task.timer_started_at is not None
    assert row.stopwatch_widget.task.is_timer_running is True

    # Check checkbox to complete
    row.checkbox.setChecked(True)
    assert row.task.status == "done"
    assert row.task.timer_started_at is None
    assert row.stopwatch_widget.task.is_timer_running is False

    # Uncheck checkbox to reopen
    row.status_combo.setCurrentText("In progress")
    assert row.task.status == "in_progress"
    assert row.task.timer_started_at is not None
