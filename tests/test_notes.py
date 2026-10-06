"""
Unit and integration tests for WizDesk v1.2.0 Permanent Long Notes Engine and Workspace.
Tests CRUD operations, tagging, pinned sorting, Obsidian vault sync, and UI workspace widgets.
"""

from datetime import datetime, date
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from wiz.core.config import config
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository, NoteRecord
from wiz.sync.obsidian import ObsidianSync, sync_permanent_note
from wiz.ui.popup_dialog import NoteCardWidget, NoteEditorWidget, PermanentNotesWorkspaceWidget


@pytest.fixture
def repo(tmp_path):
    """Provide a clean isolated database repository for notes testing."""
    db = Database(db_path=tmp_path / "test_notes.db")
    repo_obj = StorageRepository(db=db)
    yield repo_obj
    db.close()


def test_permanent_notes_crud_lifecycle(repo: StorageRepository):
    """Verify create, get, update, pin toggle, and delete lifecycle for permanent notes."""
    # 1. Create permanent note with tags
    coding_tag = repo.get_tag_by_name("coding")
    assert coding_tag is not None
    tag_id = coding_tag.id

    note_id = repo.create_permanent_note(
        title="System Architecture",
        content="# Architecture\nDetailed system specifications.",
        project_tag="Work",
        tag_ids=[tag_id],
        is_pinned=False,
    )
    assert note_id > 0

    # 2. Retrieve notes list and check attributes
    notes = repo.get_permanent_notes()
    assert len(notes) == 1
    note = notes[0]
    assert note.id == note_id
    assert note.title == "System Architecture"
    assert "Detailed system specifications" in note.content
    assert note.project_tag == "Work"
    assert note.is_pinned is False
    assert len(note.tags) == 1
    assert note.tags[0].name == "Coding"

    # 3. Update note content, title, project tag, and pin status
    updated = repo.update_permanent_note(
        note_id=note_id,
        title="Refactored System Architecture",
        content="# Architecture v2\nUpdated with event bus.",
        project_tag="CorePlatform",
        tag_ids=[tag_id],
        is_pinned=True,
    )
    assert updated is True

    notes_updated = repo.get_permanent_notes()
    assert len(notes_updated) == 1
    updated_note = notes_updated[0]
    assert updated_note.title == "Refactored System Architecture"
    assert "Updated with event bus." in updated_note.content
    assert updated_note.project_tag == "CorePlatform"
    assert updated_note.is_pinned is True

    # 4. Create a second unpinned note and check sorting (pinned first)
    second_id = repo.create_permanent_note(
        title="Meeting Summary",
        content="Discussion notes from sync.",
        project_tag="General",
        is_pinned=False,
    )
    all_notes = repo.get_permanent_notes()
    assert len(all_notes) == 2
    # Pinned note must come first
    assert all_notes[0].id == note_id
    assert all_notes[0].is_pinned is True
    assert all_notes[1].id == second_id
    assert all_notes[1].is_pinned is False

    # 5. Delete note
    deleted = repo.delete_permanent_note(note_id)
    assert deleted is True
    remaining = repo.get_permanent_notes()
    assert len(remaining) == 1
    assert remaining[0].id == second_id


def test_permanent_notes_project_and_tag_filtering(repo: StorageRepository):
    """Verify filtering permanent notes by project tag and tag ID."""
    debug_tag = repo.get_tag_by_name("debug")
    research_tag = repo.get_tag_by_name("research")
    assert debug_tag is not None and research_tag is not None

    n1 = repo.create_permanent_note(
        title="Bug Investigation",
        content="Investigating memory spike in polling loop.",
        project_tag="AppCore",
        tag_ids=[debug_tag.id],
    )
    n2 = repo.create_permanent_note(
        title="Competitor Audit",
        content="Analyzing alternative productivity solutions.",
        project_tag="Marketing",
        tag_ids=[research_tag.id],
    )
    n3 = repo.create_permanent_note(
        title="Release Checklist",
        content="Steps before v1.2.0 deployment.",
        project_tag="AppCore",
        tag_ids=[debug_tag.id, research_tag.id],
    )

    # Filter by project tag
    core_notes = repo.get_permanent_notes(project_tag="AppCore")
    core_ids = [n.id for n in core_notes]
    assert n1 in core_ids
    assert n3 in core_ids
    assert n2 not in core_ids

    # Filter by tag ID
    debug_notes = repo.get_permanent_notes(tag_id=debug_tag.id)
    debug_ids = [n.id for n in debug_notes]
    assert n1 in debug_ids
    assert n3 in debug_ids
    assert n2 not in debug_ids


def test_obsidian_permanent_note_sync(tmp_path, repo: StorageRepository):
    """Verify syncing permanent notes to Obsidian vault WizNotes directory with frontmatter."""
    vault_dir = tmp_path / "ObsidianVault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    orig_path = config.get("obsidian_vault_path")
    try:
        config.set("obsidian_vault_path", str(vault_dir))

        coding_tag = repo.get_tag_by_name("coding")
        assert coding_tag is not None

        note_id = repo.create_permanent_note(
            title="API Contract Spec",
            content="## Endpoints\n- GET /api/v1/tasks\n- POST /api/v1/notes",
            project_tag="Platform",
            tag_ids=[coding_tag.id],
        )
        notes = repo.get_permanent_notes()
        note = [n for n in notes if n.id == note_id][0]

        sync_engine = ObsidianSync(repo)
        success, msg = sync_engine.sync_note(note)
        assert success is True

        expected_file = vault_dir / "WizNotes" / "API Contract Spec.md"
        assert expected_file.exists()
        content = expected_file.read_text(encoding="utf-8")
        assert "title: \"API Contract Spec\"" in content
        assert "project: \"Platform\"" in content
        assert "Coding" in content
        assert "# API Contract Spec" in content
        assert "GET /api/v1/tasks" in content
    finally:
        config.set("obsidian_vault_path", orig_path)


def test_note_card_widget(qapp, repo: StorageRepository):
    """Verify NoteCardWidget displays title, snippet preview, pin state, and emits signals."""
    note = NoteRecord(
        id=42,
        title="Database Migration Guide",
        content="Steps to run SQLite schema migration without data loss for v1.2.0 release.",
        project_tag="DevOps",
        created_at=datetime(2026, 10, 6, 10, 0, 0),
        updated_at=datetime(2026, 10, 6, 10, 30, 0),
        is_pinned=True,
    )
    card = NoteCardWidget(note=note, is_selected=False, is_dark=True)
    assert card.note_id == 42
    assert card.title_lbl.text() == "Database Migration Guide"
    assert "Steps to run SQLite" in card.snip_lbl.text()

    # Verify select signal
    selected_ids = []
    card.selected.connect(selected_ids.append)
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    assert selected_ids == [42]

    # Verify delete signal
    deleted_ids = []
    card.delete_requested.connect(deleted_ids.append)
    card.del_btn.click()
    assert deleted_ids == [42]


def test_note_editor_widget_editing_and_stats(qapp, repo: StorageRepository, tmp_path):
    """Verify NoteEditorWidget loads a note, updates text, updates stats, and saves to database."""
    vault_dir = tmp_path / "ObsidianTestVault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    orig_path = config.get("obsidian_vault_path")
    try:
        config.set("obsidian_vault_path", str(vault_dir))

        note_id = repo.create_permanent_note(
            title="Draft Note",
            content="Initial content line.",
            project_tag="Work",
        )
        note = repo.get_permanent_notes()[0]

        editor = NoteEditorWidget(repo=repo, is_dark=False)
        editor.load_note(note)

        assert editor.title_input.text() == "Draft Note"
        assert editor.text_edit.toPlainText() == "Initial content line."
        assert "3 words" in editor.stats_lbl.text()

        # Modify title and content
        editor.title_input.setText("Updated Draft Note")
        editor.text_edit.setPlainText("One two three four five six words.")
        editor._update_stats()
        assert "7 words" in editor.stats_lbl.text()

        # Save note manually
        editor._save_active_note()

        reloaded = repo.get_permanent_notes()[0]
        assert reloaded.title == "Updated Draft Note"
        assert reloaded.content == "One two three four five six words."

        # Verify obsidian sync file written
        synced_file = vault_dir / "WizNotes" / "Updated Draft Note.md"
        assert synced_file.exists()
    finally:
        config.set("obsidian_vault_path", orig_path)


def test_permanent_notes_workspace_widget(qapp, repo: StorageRepository):
    """Verify PermanentNotesWorkspaceWidget creation bar, cards list rendering, and search filter."""
    workspace = PermanentNotesWorkspaceWidget(repo=repo, is_dark=True)
    workspace.show()

    # 1. Create a new note from top input bar
    workspace.note_title_input.setText("Frontend Guidelines")
    workspace._on_create_clicked()

    notes = repo.get_permanent_notes()
    assert len(notes) == 1
    assert notes[0].title == "Frontend Guidelines"
    assert workspace.active_note_id == notes[0].id

    # 2. Add second note
    workspace.note_title_input.setText("Backend Guidelines")
    workspace._on_create_clicked()

    all_notes = repo.get_permanent_notes()
    assert len(all_notes) == 2

    # 3. Test search filter
    workspace.search_input.setText("Backend")
    # Cards layout should filter to Backend note
    rendered_cards = [
        workspace.cards_layout.itemAt(i).widget()
        for i in range(workspace.cards_layout.count())
        if isinstance(workspace.cards_layout.itemAt(i).widget(), NoteCardWidget)
    ]
    assert len(rendered_cards) == 1
    assert rendered_cards[0].title_lbl.text() == "Backend Guidelines"

    # Reset search
    workspace.search_input.setText("")
    all_rendered = [
        workspace.cards_layout.itemAt(i).widget()
        for i in range(workspace.cards_layout.count())
        if isinstance(workspace.cards_layout.itemAt(i).widget(), NoteCardWidget)
    ]
    assert len(all_rendered) == 2
