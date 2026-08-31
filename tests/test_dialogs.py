"""Unit tests for Project Tracking Dialog, Task Cards, and SettingsDialog."""

import sys
from datetime import date
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from wiz.core.state_machine import StateMachine, MascotState
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import (
    QuickEntryDialog,
    SegmentedFilterBar,
    CircularCheckButton,
    FlagButton,
    TaskCardWidget,
)
from wiz.ui.settings_dialog import SettingsDialog


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance is initialized."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def repo(tmp_path):
    """Temporary storage repository."""
    db_file = tmp_path / "test_dialogs.db"
    return StorageRepository(Database(db_file))


def test_quick_entry_dialog_task_flow(qapp, repo):
    """Test creating tasks, expanding subtasks, adding logs, and status filtering."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # 1. Add a task under 'Work'
    dialog.add_input.setText("Ship MVP update")
    dialog.project_combo.setCurrentText("Work")
    dialog._on_quick_add_task()

    # Verify task in DB
    tasks = repo.get_task_hierarchy(status_filter="All")
    task_titles = [t.title for t in tasks]
    assert "Ship MVP update" in task_titles

    target_task = [t for t in tasks if t.title == "Ship MVP update"][0]

    # 2. Add subtask and log to this task
    dialog._on_subtask_added(target_task.id, "Write unit tests")
    dialog._on_log_added(target_task.id, "testing now")

    reloaded = repo.get_task_hierarchy(status_filter="All")
    reloaded_target = [t for t in reloaded if t.id == target_task.id][0]
    assert len(reloaded_target.subtasks) == 1
    assert reloaded_target.subtasks[0].title == "Write unit tests"
    assert len(reloaded_target.task_logs) == 1
    assert reloaded_target.task_logs[0].content == "testing now"

    # 3. Switch filter tab to 'To Do'
    dialog.filter_bar.set_active_filter("To Do")
    assert dialog.filter_bar.current_filter == "To Do"

    # 4. Toggle task status to 'done'
    dialog._on_task_status_toggled(target_task.id, "done")

    # 5. Verify in 'Done' filter
    dialog.filter_bar.set_active_filter("Done")
    done_tasks = repo.get_task_hierarchy(status_filter="Done")
    done_titles = [t.title for t in done_tasks]
    assert "Ship MVP update" in done_titles

    dialog.close()


def test_circular_check_button(qapp):
    """Test CircularCheckButton state toggles."""
    btn = CircularCheckButton(status="not_started")
    assert btn.status == "not_started"

    btn.set_status("done")
    assert btn.status == "done"

    btn.set_status("in_progress")
    assert btn.status == "in_progress"


def test_flag_button(qapp):
    """Test FlagButton priority flag state."""
    flag = FlagButton(flagged=False)
    assert not flag.isFlagged

    flag.setFlagged(True)
    assert flag.isFlagged


def test_settings_dialog(qapp, repo, tmp_path):
    """Test SettingsDialog loading and saving."""
    dialog = SettingsDialog(repository=repo)
    dialog.vault_path_input.setText(str(tmp_path / "Vault"))
    dialog._on_save()

    assert dialog.result() == SettingsDialog.DialogCode.Accepted
    dialog.close()
