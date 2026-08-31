"""Unit tests for Wiz SQLite storage layer and repository models."""

from datetime import datetime, date, timedelta
import pytest

from wiz.storage.db import Database
from wiz.storage.models import StorageRepository, TaskRecord, SubtaskRecord


@pytest.fixture
def repo(tmp_path):
    """Provide a fresh SQLite repository backed by a temporary file."""
    db_file = tmp_path / "test_wiz.db"
    db = Database(db_file)
    return StorageRepository(db)


def test_session_logging_and_retrieval(repo):
    """Test inserting and retrieving auto-tracked sessions."""
    now = datetime(2026, 8, 31, 10, 0, 0)
    end = now + timedelta(minutes=30)

    session_id = repo.log_session(
        app_name="Code.exe",
        window_title="Wiz - Visual Studio Code",
        start_time=now,
        end_time=end,
        project_tag="Wiz",
    )
    assert session_id > 0

    sessions = repo.get_sessions_for_date(date(2026, 8, 31))
    assert len(sessions) == 1
    s = sessions[0]
    assert s.app_name == "Code.exe"
    assert s.window_title == "Wiz - Visual Studio Code"
    assert s.project_tag == "Wiz"
    assert s.duration_minutes == 30.0


def test_note_creation_and_completion(repo):
    """Test creating, toggling, and listing quick notes."""
    note_id = repo.create_note("Fixed booking bug in TurfLine", project_tag="TurfLine")
    assert note_id > 0

    notes = repo.get_notes_for_date(date.today())
    assert len(notes) == 1
    assert notes[0].content == "Fixed booking bug in TurfLine"
    assert notes[0].is_completed is False

    # Toggle complete
    repo.toggle_note_completed(note_id, True)
    notes_updated = repo.get_notes_for_date(date.today())
    assert notes_updated[0].is_completed is True


def test_task_subtask_hierarchy_and_logs(repo):
    """Test task hierarchy, subtask status auto-completion, and log entries."""
    task_id = repo.create_task("Build TurfLine booking flow", project_tag="TurfLine")
    assert task_id > 0

    st1_id = repo.create_subtask(task_id, "Design booking UI")
    st2_id = repo.create_subtask(task_id, "Wire up backend API")

    # Add timestamped log to st2
    log_id = repo.add_task_log(task_id, "hit CORS issue, debugging", subtask_id=st2_id)
    assert log_id > 0

    # Fetch hierarchy
    tasks = repo.get_task_hierarchy()
    assert len(tasks) == 1
    t = tasks[0]
    assert t.title == "Build TurfLine booking flow"
    assert len(t.subtasks) == 2
    assert t.subtasks[1].title == "Wire up backend API"
    assert len(t.subtasks[1].logs) == 1
    assert t.subtasks[1].logs[0].content == "hit CORS issue, debugging"

    # Mark both subtasks done -> verify parent auto-completes to 'done'
    repo.update_subtask_status(st1_id, "done")
    repo.update_subtask_status(st2_id, "done")

    tasks_after = repo.get_task_hierarchy()
    assert tasks_after[0].status == "done"


def test_project_keyword_matching(repo):
    """Test project keyword configuration and string matching."""
    repo.create_or_update_project("TurfLine", ["turfline", "booking"])
    repo.create_or_update_project("Wiz", ["wiz", "companion"])

    match1 = repo.match_project_tag("Visual Studio Code - TurfLine backend")
    assert match1 == "TurfLine"

    match2 = repo.match_project_tag("Chrome - Wiz PRD documentation")
    assert match2 == "Wiz"

    match_none = repo.match_project_tag("Spotify - Music Player")
    assert match_none is None
