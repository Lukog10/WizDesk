"""Unit tests for QuickEntryDialog and SettingsDialog."""

import sys
from datetime import date
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from wiz.core.state_machine import StateMachine, MascotState
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import QuickEntryDialog, SegmentedFilterBar, RoundedCheckbox, CreateSectionDialog
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
    """Test creating tasks and filtering via redesigned QuickEntryDialog."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # Verify initial seeded tasks or add a new task
    dialog.add_input.setText("Ship MVP update")
    dialog.project_combo.setCurrentText("Work")
    dialog._on_quick_add_task()

    # Verify task in DB
    tasks = repo.get_task_hierarchy(status_filter="Task")
    task_titles = [t.title for t in tasks]
    assert "Ship MVP update" in task_titles

    # Switch filter tab
    dialog.filter_bar.set_active_filter("Completed")
    assert dialog.filter_bar.current_filter == "Completed"

    # Toggle a task to done
    target_task = [t for t in tasks if t.title == "Ship MVP update"][0]
    dialog._on_task_status_toggled(target_task.id, "done")

    # Now verify in completed list
    completed_tasks = repo.get_task_hierarchy(status_filter="Completed")
    completed_titles = [t.title for t in completed_tasks]
    assert "Ship MVP update" in completed_titles

    dialog.close()


def test_quick_entry_dialog_subtasks_and_section_change(qapp, repo):
    """Test creating subtasks under a task and changing task section/project."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # Create a task in 'Personal Projects'
    task_id = repo.create_task("Build custom prototype", project_tag="Personal Projects")
    dialog.refresh_tasks()

    # Add a subtask
    dialog._on_subtask_added(task_id, "Create Figma vector assets")
    tasks = repo.get_task_hierarchy(status_filter="Task")
    target = [t for t in tasks if t.id == task_id][0]
    assert len(target.subtasks) == 1
    assert target.subtasks[0].title == "Create Figma vector assets"

    # Toggle subtask to done -> parent task stays in 'Task'
    st_id = target.subtasks[0].id
    dialog._on_subtask_toggled(st_id, "done")
    tasks_after_st = repo.get_task_hierarchy(status_filter="Task")
    target_after = [t for t in tasks_after_st if t.id == task_id][0]
    assert target_after.status == "not_started"
    assert target_after.subtasks[0].status == "done"

    # Move section from 'Personal Projects' to 'Work'
    dialog._on_task_project_changed(task_id, "Work")
    tasks_work = repo.get_task_hierarchy(status_filter="Task")
    target_work = [t for t in tasks_work if t.id == task_id][0]
    assert target_work.project_tag == "Work"

    # Toggle parent task to done -> goes to 'Completed'
    dialog._on_task_status_toggled(task_id, "done")
    completed_tasks = repo.get_task_hierarchy(status_filter="Completed")
    assert any(t.id == task_id for t in completed_tasks)

    # Delete subtask
    dialog._on_subtask_deleted(st_id)
    tasks_reloaded = repo.get_task_hierarchy(status_filter="Completed")
    target_reloaded = [t for t in tasks_reloaded if t.id == task_id][0]
    assert len(target_reloaded.subtasks) == 0

    dialog.close()


def test_quick_entry_dialog_notes_flow(qapp, repo):
    """Test switching to Quick Notes mode and logging/toggling work notes."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # Switch to notes mode
    dialog._set_view_mode("notes")
    assert dialog.current_view_mode == "notes"

    # Log a quick work note
    dialog.note_input.setText("Investigated background window polling performance")
    dialog.note_project_combo.setCurrentText("Work")
    dialog._on_quick_add_note()

    notes = repo.get_notes_for_date(date.today())
    assert any("Investigated background window polling" in n.content for n in notes)

    target_note = [n for n in notes if "Investigated background window polling" in n.content][0]
    dialog._on_note_toggled(target_note.id, True)

    reloaded_notes = repo.get_notes_for_date(date.today())
    updated_note = [n for n in reloaded_notes if n.id == target_note.id][0]
    assert updated_note.is_completed is True

    # Move note section from 'Work' to 'Personal Projects'
    dialog._on_note_project_changed(target_note.id, "Personal Projects")
    notes_moved = repo.get_notes_for_date(date.today())
    moved_note = [n for n in notes_moved if n.id == target_note.id][0]
    assert moved_note.project_tag == "Personal Projects"

    dialog.close()


def test_rounded_checkbox(qapp):
    """Test RoundedCheckbox state toggling."""
    box = RoundedCheckbox(checked=False)
    assert not box.isChecked

    box.setChecked(True)
    assert box.isChecked


def test_create_section_dialog(qapp):
    """Test custom CreateSectionDialog functionality."""
    dlg = CreateSectionDialog()
    dlg.input_field.setText("  Architecture & Design  ")
    assert dlg.section_name == "Architecture & Design"
    dlg._on_submit()
    assert dlg.result() == CreateSectionDialog.DialogCode.Accepted
    dlg.close()


def test_settings_dialog(qapp, repo, tmp_path):
    """Test SettingsDialog loading and saving."""
    dialog = SettingsDialog(repository=repo)
    dialog.vault_path_input.setText(str(tmp_path / "Vault"))
    dialog._on_save()

    assert dialog.result() == SettingsDialog.DialogCode.Accepted
    dialog.close()
