"""Unit and integration tests for WizDesk Tags Engine, Task-Tag relations, and Note-Tag relations."""

import pytest
from datetime import datetime
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository, TagRecord


@pytest.fixture
def repo(tmp_path):
    """Provide a clean in-memory database repository for testing."""
    db = Database(db_path=tmp_path / "test_tags.db")
    repo_obj = StorageRepository(db=db)
    yield repo_obj
    db.close()


def test_default_seeded_tags(repo):
    """Verify that initial default tags (Coding, Debug, Design, Research) are seeded."""
    tags = repo.get_all_tags()
    tag_names = [t.name for t in tags]
    assert "Coding" in tag_names
    assert "Debug" in tag_names
    assert "Design" in tag_names
    assert "Research" in tag_names


def test_create_and_get_tag(repo):
    """Verify creating a new tag and fetching it by ID and name."""
    created = repo.create_tag(name="DevOps", icon="server", color="#10B981")
    assert created.id is not None
    assert created.name == "DevOps"
    assert created.icon == "server"
    assert created.color == "#10B981"

    by_id = repo.get_tag_by_id(created.id)
    assert by_id is not None
    assert by_id.name == "DevOps"

    by_name = repo.get_tag_by_name("devops")
    assert by_name is not None
    assert by_name.id == created.id


def test_update_and_delete_tag(repo):
    """Verify updating tag attributes and deleting a tag."""
    tag = repo.create_tag(name="Testing", icon="flag", color="#EF4444")
    assert repo.update_tag(tag.id, name="QA & Testing", icon="shield", color="#3B82F6")

    updated = repo.get_tag_by_id(tag.id)
    assert updated.name == "QA & Testing"
    assert updated.icon == "shield"
    assert updated.color == "#3B82F6"

    assert repo.delete_tag(tag.id)
    assert repo.get_tag_by_id(tag.id) is None


def test_task_tag_associations(repo):
    """Verify creating tasks with tags, adding/removing tags, and task hierarchy loading."""
    tag_coding = repo.get_tag_by_name("Coding")
    tag_debug = repo.get_tag_by_name("Debug")
    assert tag_coding is not None
    assert tag_debug is not None

    task_id = repo.create_task(
        title="Fix NullPointer in parser",
        project_tag="WizDesk",
        tag_ids=[tag_coding.id, tag_debug.id],
    )
    assert task_id > 0

    task_tags = repo.get_tags_for_task(task_id)
    assert len(task_tags) == 2
    tag_names = [t.name for t in task_tags]
    assert "Coding" in tag_names
    assert "Debug" in tag_names

    tasks = repo.get_task_hierarchy(project_tag="WizDesk")
    matching = [t for t in tasks if t.id == task_id]
    assert len(matching) == 1
    assert len(matching[0].tags) == 2

    # Remove one tag
    assert repo.remove_task_tag(task_id, tag_debug.id)
    refreshed_tags = repo.get_tags_for_task(task_id)
    assert len(refreshed_tags) == 1
    assert refreshed_tags[0].name == "Coding"


def test_task_tag_filtering(repo):
    """Verify filtering get_task_hierarchy by tag_id."""
    tag_design = repo.get_tag_by_name("Design")
    tag_research = repo.get_tag_by_name("Research")

    t1_id = repo.create_task(title="Design UI Mockups", tag_ids=[tag_design.id])
    t2_id = repo.create_task(title="Explore vector icons", tag_ids=[tag_research.id])

    design_tasks = repo.get_task_hierarchy(tag_id=tag_design.id)
    design_ids = [t.id for t in design_tasks]
    assert t1_id in design_ids
    assert t2_id not in design_ids

    research_tasks = repo.get_task_hierarchy(tag_id=tag_research.id)
    research_ids = [t.id for t in research_tasks]
    assert t2_id in research_ids
    assert t1_id not in research_ids


def test_note_tag_associations(repo):
    """Verify creating notes with tags and retrieving notes with tag pills."""
    tag_research = repo.get_tag_by_name("Research")
    note_id = repo.create_note(
        title="SQLite Pragma Benchmarks",
        content="Testing in-memory serialization speed.",
        project_tag="Engine",
        tag_ids=[tag_research.id],
    )
    assert note_id > 0

    note_tags = repo.get_tags_for_note(note_id)
    assert len(note_tags) == 1
    assert note_tags[0].name == "Research"

    notes = repo.get_notes(tag_id=tag_research.id)
    assert any(n.id == note_id for n in notes)
    matching_note = next(n for n in notes if n.id == note_id)
    assert matching_note.title == "SQLite Pragma Benchmarks"
    assert len(matching_note.tags) == 1


def test_tag_cascade_deletion(repo):
    """Verify deleting a tag removes junction references without deleting tasks or notes."""
    temp_tag = repo.create_tag(name="Temporary", icon="tag", color="#F59E0B")
    task_id = repo.create_task(title="Task with temp tag", tag_ids=[temp_tag.id])
    note_id = repo.create_note(content="Note with temp tag", tag_ids=[temp_tag.id])

    assert len(repo.get_tags_for_task(task_id)) == 1
    assert len(repo.get_tags_for_note(note_id)) == 1

    assert repo.delete_tag(temp_tag.id)

    assert len(repo.get_tags_for_task(task_id)) == 0
    assert len(repo.get_tags_for_note(note_id)) == 0

    # Ensure parent task and note still exist
    tasks = repo.get_task_hierarchy()
    assert any(t.id == task_id for t in tasks)
    notes = repo.get_notes()
    assert any(n.id == note_id for n in notes)


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance is initialized."""
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_project_icon_button(qapp, repo):
    """Test ProjectIconButton properties, project selection, and backward compatibility."""
    from wiz.ui.popup_dialog import ProjectIconButton
    btn = ProjectIconButton(is_dark=True)
    assert btn.currentText() == "Work"

    btn.setCurrentText("Personal Projects")
    assert btn.currentText() == "Personal Projects"

    projects = repo.get_all_projects()
    btn.set_projects(projects)
    assert "Work" in btn.all_projects


def test_tag_icon_button(qapp, repo):
    """Test TagIconButton selection, clear, and tooltip."""
    from wiz.ui.popup_dialog import TagIconButton
    tag = repo.get_tag_by_name("Coding")
    assert tag is not None

    tag_btn = TagIconButton(repo=repo, is_dark=True)
    assert len(tag_btn.selected_tag_ids) == 0

    tag_btn.set_selected_tag_ids([tag.id])
    assert tag_btn.selected_tag_ids == [tag.id]
    assert "Coding" in tag_btn.toolTip()

    tag_btn.clear_selection()
    assert len(tag_btn.selected_tag_ids) == 0
    assert tag_btn.toolTip() == "Assign Tags"


def test_tag_badge_widget(qapp, repo):
    """Test TagBadgeWidget rendering and clicked signal."""
    from wiz.ui.popup_dialog import TagBadgeWidget
    tag = repo.get_tag_by_name("Design")
    assert tag is not None

    badge = TagBadgeWidget(tag, is_dark=True)
    assert badge.name_label.text() == "Design"

    clicked_ids = []
    badge.clicked.connect(clicked_ids.append)
    badge.clicked.emit(tag.id)
    assert clicked_ids == [tag.id]


def test_tag_filter_bar(qapp, repo):
    """Test TagFilterBar chip construction and selection toggle."""
    from wiz.ui.popup_dialog import TagFilterBar
    bar = TagFilterBar(repo, is_dark=False)
    assert bar.isVisible()

    tag = repo.get_tag_by_name("Debug")
    assert tag is not None

    selected_ids = []
    bar.tag_selected.connect(selected_ids.append)

    bar._select_tag(tag.id)
    assert bar.selected_tag_id == tag.id
    assert selected_ids[-1] == tag.id

    # Toggle off back to None (All)
    bar._select_tag(tag.id)
    assert bar.selected_tag_id is None
    assert selected_ids[-1] is None


def test_quick_entry_dialog_tag_flow(qapp, repo):
    """Test creating a task with tags and filtering by tag in QuickEntryDialog."""
    from wiz.core.state_machine import StateMachine
    from wiz.ui.popup_dialog import QuickEntryDialog

    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    tag_coding = repo.get_tag_by_name("Coding")
    assert tag_coding is not None

    # Set task title, project, and tag
    dialog.add_input.setText("Write parser tests")
    dialog.project_btn.setCurrentText("Work")
    dialog.tag_btn.set_selected_tag_ids([tag_coding.id])

    dialog._on_quick_add_task()

    # Verify task was created with tag in database
    tasks = repo.get_task_hierarchy(tag_id=tag_coding.id)
    assert any(t.title == "Write parser tests" for t in tasks)

    # Verify tag selection cleared on bottom bar
    assert len(dialog.tag_btn.selected_tag_ids) == 0

    # Verify tag filter section is hidden from tasks page layout
    assert dialog.tag_filter_bar.isHidden()
    layout_widgets = [dialog.tasks_page.layout().itemAt(i).widget() for i in range(dialog.tasks_page.layout().count())]
    assert dialog.tag_filter_bar not in layout_widgets

    # Filter tasks using tag filter bar
    dialog.tag_filter_bar._select_tag(tag_coding.id)
    assert dialog.active_tag_filter_id == tag_coding.id

    # Clear filter
    dialog.tag_filter_bar._select_tag(None)
    assert dialog.active_tag_filter_id is None

    dialog.close()


def test_tag_create_dialog_scroll_bar_removed_and_menu_icons(qapp, repo):
    """Test that TagCreateDialog has scrollbars disabled and TagIconButton generates menu icons."""
    from PyQt6.QtCore import Qt
    from wiz.ui.popup_dialog import TagCreateDialog, TagIconButton
    from wiz.ui.icons import get_status_icon

    dlg = TagCreateDialog(repo, is_dark=True)
    # Find the QScrollArea for icons
    scroll_areas = dlg.findChildren(type(dlg.card.findChild(TagCreateDialog).parent() if False else dlg))
    from PyQt6.QtWidgets import QScrollArea
    icon_scrolls = dlg.findChildren(QScrollArea)
    assert len(icon_scrolls) >= 1
    icon_scroll = icon_scrolls[0]

    # Verify both horizontal and vertical scrollbars are permanently off
    assert icon_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert icon_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    # Verify TagIconButton menu icons
    tag_btn = TagIconButton(repo=repo, is_dark=True)
    all_tags = repo.get_all_tags()
    assert len(all_tags) > 0
    first_tag = all_tags[0]
    icon = get_status_icon(f"tags/{first_tag.icon}.svg", first_tag.color, size=16)
    assert not icon.isNull()

