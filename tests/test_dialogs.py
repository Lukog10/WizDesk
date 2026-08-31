"""Unit tests for QuickEntryDialog and SettingsDialog."""

import sys
from datetime import date
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from wiz.core.state_machine import StateMachine, MascotState
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import QuickEntryDialog
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


def test_quick_entry_dialog_notes(qapp, repo):
    """Test creating and displaying notes via QuickEntryDialog."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # Simulate typing note
    dialog.note_input.setText("Testing dialog note creation")
    dialog._on_save_note()

    # Verify note in DB and UI
    notes = repo.get_notes_for_date(date.today())
    assert len(notes) == 1
    assert notes[0].content == "Testing dialog note creation"

    assert dialog.notes_list.count() == 1
    dialog.close()


def test_quick_entry_dialog_tasks(qapp, repo):
    """Test creating and displaying tasks via QuickEntryDialog."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    dialog.task_input.setText("Implement UI Polish")
    dialog._on_save_task()

    tasks = repo.get_task_hierarchy()
    assert len(tasks) == 1
    assert tasks[0].title == "Implement UI Polish"
    assert dialog.task_tree.topLevelItemCount() == 1

    dialog.close()


def test_settings_dialog(qapp, repo, tmp_path):
    """Test SettingsDialog loading and saving."""
    dialog = SettingsDialog(repository=repo)
    dialog.vault_path_input.setText(str(tmp_path / "Vault"))
    dialog._on_save()

    assert dialog.result() == SettingsDialog.DialogCode.Accepted
    dialog.close()
