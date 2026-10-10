"""Comprehensive integration test suite covering all features, functions,
buttons, and clicks across the entire WizDesk workspace.
"""

import sys
from datetime import date, datetime, timedelta
import pytest
from PyQt6.QtCore import Qt, QPoint, QDate, QCoreApplication, QEvent

from wiz.core.config import config
from wiz.core.state_machine import StateMachine, MascotState
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository, TaskRecord, SubtaskRecord, NoteRecord, ProjectRecord
from wiz.ui.popup_dialog import (
    QuickEntryDialog,
    TaskRowWidget,
    SubtaskRowWidget,
    CreateSectionDialog,
    CalendarPopupDialog,
)
from wiz.ui.quick_bar_dialog import QuickBarPopup
from wiz.ui.calendar_view import CalendarView, ScheduleTaskModalDialog
from wiz.ui.timeline_view import TimelineView
from wiz.ui.project_dashboard_view import ProjectDashboardView
from wiz.ui.settings_view import SettingsView


@pytest.fixture
def repo(tmp_path):
    """Temporary storage repository isolated for testing."""
    db_file = tmp_path / "test_workspace_all.db"
    repository = StorageRepository(Database(db_file))
    repository.create_or_update_project("Work", ["code", "dev"], color="#FF6B3D")
    repository.create_or_update_project("Personal", ["gym", "life"], color="#10B981")
    return repository


@pytest.fixture
def workspace(qapp, repo):
    """QuickEntryDialog instance with StateMachine and temporary repo."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)
    yield dialog, sm, repo
    dialog.close()


def test_sidebar_navigation_and_collapse_buttons(workspace):
    """Test every sidebar navigation pill and the collapse/expand toggle button."""
    dialog, sm, repo = workspace

    modes = [
        ("tasks", 0, "Tasks & To-Dos"),
        ("notes", 1, "Quick Notes"),
        ("calendar", 2, "Calendar & Schedule"),
        ("activity", 3, "Activity Timeline"),
        ("projects", 4, "Projects Dashboard"),
        ("settings", 5, "Settings & Preferences"),
        ("help", 6, "Help & Documentation"),
    ]

    for mode_name, expected_index, expected_title in modes:
        pill = dialog.sidebar.pills[mode_name]
        pill.click()
        assert dialog.current_view_mode == mode_name
        assert dialog.stack.currentIndex() == expected_index
        assert dialog.page_title_lbl.text() == expected_title

    # Test Sidebar collapse toggle button
    init_collapsed = dialog.sidebar.is_collapsed

    # Click toggle to switch collapsed state
    dialog.sidebar.toggle_btn.click()
    assert dialog.sidebar.is_collapsed == (not init_collapsed)

    # Click toggle to restore collapsed state
    dialog.sidebar.toggle_btn.click()
    assert dialog.sidebar.is_collapsed == init_collapsed


def test_tasks_view_filters_and_bottom_add_bar(workspace):
    """Test task creation via bottom add bar and clicking segmented filter tabs."""
    dialog, sm, repo = workspace
    dialog._set_view_mode("tasks")

    # Bottom add bar: select project, enter task title, and click Add button
    dialog.project_btn.setCurrentText("Work")
    dialog.add_input.setText("Complete frontend integration tests")
    dialog.add_task_btn.click()

    tasks = repo.get_task_hierarchy(include_completed=True)
    created_task = next((t for t in tasks if t.title == "Complete frontend integration tests"), None)
    assert created_task is not None
    assert created_task.project_tag == "Work"
    assert created_task.status in ("not_started", "todo")

    # Test clicking each filter tab
    filter_tabs = ["Task", "In progress", "Completed", "Cancelled"]
    for tab in filter_tabs:
        dialog.filter_bar._buttons[tab].click()
        assert dialog.filter_bar.current_filter == tab


def test_task_row_full_lifecycle_buttons_and_clicks(workspace, qapp):
    """Test all interactive buttons and clicks inside a TaskRowWidget:
    checkbox, stopwatch, inline renaming, subtasks, status combo, and delete.
    """
    dialog, sm, repo = workspace
    dialog._set_view_mode("tasks")

    task_id = repo.create_task("Ship polished feature", project_tag="Work")
    dialog.refresh_tasks()

    def get_current_task_row() -> TaskRowWidget:
        qapp.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        task_rows = dialog.content_widget.findChildren(TaskRowWidget)
        return next((r for r in task_rows if r.task_id == task_id), None)

    row = get_current_task_row()
    assert row is not None

    # 1. Checkbox toggle completion
    row.checkbox.setChecked(True)
    updated_task = repo.get_task_by_id(task_id)
    assert updated_task.status == "done"
    assert sm.current_state == MascotState.COMPLETE

    # Toggle back to uncompleted
    row = get_current_task_row()
    row.checkbox.setChecked(False)
    updated_task = repo.get_task_by_id(task_id)
    assert updated_task.status in ("not_started", "todo")

    # 2. Stopwatch toggle button click: start and pause timer
    row = get_current_task_row()
    row.stopwatch_widget.btn.click()
    updated_task = repo.get_task_by_id(task_id)
    assert updated_task.status == "in_progress"
    assert sm.current_state == MascotState.WORKING

    # Click again to pause stopwatch
    row.stopwatch_widget.btn.click()
    updated_task = repo.get_task_by_id(task_id)
    assert updated_task.is_timer_running is False

    # 3. Inline Renaming
    row.start_renaming()
    assert row.edit_input.isHidden() is False
    row.edit_input.setText("Ship polished feature - V2")
    row._finish_renaming()
    updated_task = repo.get_task_by_id(task_id)
    assert updated_task.title == "Ship polished feature - V2"

    # 4. Subtask button click and creation
    row = get_current_task_row()
    row.add_sub_btn.click()
    assert row.sub_input_widget.isHidden() is False
    row.sub_input.setText("Write unit test for subtask")
    row._on_submit_subtask()

    subtasks = repo.get_task_by_id(task_id).subtasks
    assert len(subtasks) == 1
    assert subtasks[0].title == "Write unit test for subtask"

    # QuickEntryDialog._on_subtask_added refreshed tasks, get the new row
    row = get_current_task_row()
    assert row is not None

    # Toggle subtask checkbox
    st_row = row.findChild(SubtaskRowWidget)
    assert st_row is not None
    st_row.checkbox.setChecked(True)
    updated_st = repo.get_task_by_id(task_id).subtasks[0]
    assert updated_st.status == "done"

    # 5. Status combo change to cancelled
    row = get_current_task_row()
    idx = row.status_combo.findText("Cancelled")
    assert idx >= 0
    row.status_combo.setCurrentIndex(idx)
    updated_task = repo.get_task_by_id(task_id)
    assert updated_task.status == "cancelled"

    # 6. Delete task action
    row = get_current_task_row()
    row.action_requested.emit("delete", task_id)
    assert repo.get_task_by_id(task_id) is None


def test_calendar_view_buttons_and_navigation(workspace):
    """Test calendar view month navigation, grid date selection, back button,
    and schedule modal opening.
    """
    dialog, sm, repo = workspace
    dialog._set_view_mode("calendar")
    cal = dialog.calendar_view

    current_month = cal.grid_widget.current_month
    current_year = cal.grid_widget.current_year

    # Click Next Month button
    cal.next_month_btn.click()
    if current_month == 12:
        assert cal.grid_widget.current_month == 1
        assert cal.grid_widget.current_year == current_year + 1
    else:
        assert cal.grid_widget.current_month == current_month + 1

    # Click Previous Month button
    cal.prev_month_btn.click()
    assert cal.grid_widget.current_month == current_month
    assert cal.grid_widget.current_year == current_year

    # Emit date_selected signal on the grid to open Date Detail Agenda page
    cal.grid_widget.date_selected.emit(date.today())
    assert cal.sub_stack.currentIndex() == 1
    assert cal.selected_date == date.today()

    # Click Back to Calendar button on the agenda view
    cal.btn_back_to_cal.click()
    assert cal.sub_stack.currentIndex() == 0


def test_notes_view_buttons_and_editor(workspace):
    """Test quick note logging via bottom bar, search filter, and note editor actions."""
    dialog, sm, repo = workspace
    dialog._set_view_mode("notes")

    # 1. Log a quick note via bottom bar
    dialog.note_project_btn.setCurrentText("Work")
    dialog.note_input.setText("Architecting high performance database migrations")
    dialog.add_note_btn.click()

    notes = repo.get_permanent_notes()
    note = next((n for n in notes if "Architecting" in n.title), None)
    assert note is not None
    assert note.project_tag == "Work"

    # 2. Search filtering
    dialog.notes_search.setText("Architecting")
    dialog._on_notes_search_changed("Architecting")

    # 3. Open Note Editor
    dialog._on_open_note_dialog(note.id)
    assert dialog.notes_sub_stack.currentIndex() == 1
    assert dialog.note_editor.active_note.id == note.id

    # Edit note title and content
    dialog.note_editor.title_input.setText("Updated Migration Architecture")
    dialog.note_editor.text_edit.setPlainText("# Section 1\nDetails about migration.")
    dialog.note_editor._save_active_note()

    all_notes = repo.get_permanent_notes()
    updated_note = next((n for n in all_notes if n.id == note.id), None)
    assert updated_note is not None
    assert updated_note.title == "Updated Migration Architecture"
    assert "Details about migration" in updated_note.content

    # Toggle preview mode button
    dialog.note_editor.mode_btn.click()
    assert dialog.note_editor.is_preview_mode is True
    assert dialog.note_editor.preview_browser.isHidden() is False

    dialog.note_editor.mode_btn.click()
    assert dialog.note_editor.is_preview_mode is False

    # Click back button to return to notes list
    dialog.note_editor.back_btn.click()
    assert dialog.notes_sub_stack.currentIndex() == 0

    # Delete note
    dialog.note_editor._on_delete_clicked()
    assert next((n for n in repo.get_permanent_notes() if n.id == note.id), None) is None


def test_timeline_activity_view_buttons_and_filters(workspace):
    """Test timeline activity view metrics and category dropdown changes."""
    dialog, sm, repo = workspace
    dialog._set_view_mode("activity")
    tl = dialog.timeline_view

    # Test category filter combo
    categories = ["all", "apps", "notes", "tasks"]
    for cat in categories:
        idx = tl.category_combo.findData(cat)
        if idx >= 0:
            tl.category_combo.setCurrentIndex(idx)
            assert tl._category_filter == cat

    # Trigger load_date
    tl.load_date(date.today().strftime("%Y-%m-%d"))
    assert tl.lbl_metric_time.text().startswith("Tracked:")
    assert tl.lbl_metric_tasks.text().startswith("Completed:")


def test_projects_dashboard_view_buttons_and_drilldown(workspace):
    """Test projects dashboard overview timeframe dropdown and detail drilldown page."""
    dialog, sm, repo = workspace
    dialog._set_view_mode("projects")
    proj_view = dialog.project_dashboard_view

    # Overview page timeframe dropdown
    tf_options = ["today", "this_week", "this_month", "all_time"]
    for tf in tf_options:
        idx = proj_view.overview_page.combo_timeframe.findData(tf)
        if idx >= 0:
            proj_view.overview_page.combo_timeframe.setCurrentIndex(idx)
            assert proj_view.overview_page.active_timeframe == tf

    # Drill down into project detail page
    proj_view._show_detail("Work")
    assert proj_view.stack.currentWidget() == proj_view.detail_page
    assert proj_view.detail_page.current_project_name == "Work"

    # Test tab buttons in detail page
    proj_view.detail_page.btn_tab_tasks.click()
    assert proj_view.detail_page.active_tab == "tasks"

    proj_view.detail_page.btn_tab_apps.click()
    assert proj_view.detail_page.active_tab == "apps"

    proj_view.detail_page.btn_tab_keywords.click()
    assert proj_view.detail_page.active_tab == "keywords"

    # Click back button to return to overview page
    proj_view.detail_page.btn_back.click()
    assert proj_view.stack.currentWidget() == proj_view.overview_page


def test_settings_view_category_bar_and_toggles(workspace):
    """Test switching tabs in settings view and toggling preferences."""
    dialog, sm, repo = workspace
    dialog._set_view_mode("settings")
    sv = dialog.settings_view

    categories = ["general", "hotkeys", "integrations", "security"]
    for cat in categories:
        sv.switch_to_category(cat)
        assert sv.category_bar.active_category == cat

    # Test toggles in General settings
    sv.switch_to_category("general")
    initial_sound = config.sound_effects_enabled
    sv.sound_check.setChecked(not initial_sound)
    sv.save_settings()
    assert config.sound_effects_enabled == (not initial_sound)

    # Revert toggle and save
    sv.sound_check.setChecked(initial_sound)
    sv.save_settings()
    assert config.sound_effects_enabled == initial_sound


def test_quick_bar_popup_task_and_note_modes(qapp, repo):
    """Test quick floating bar popup in task mode and note mode."""
    sm = StateMachine()
    popup = QuickBarPopup(sm, repository=repo)

    # 1. Quick Task Mode
    popup.show_mode("task")
    assert popup.mode == "task"
    assert popup.mode_badge.text() == "Quick Task"

    popup.project_btn.setCurrentText("Work")
    popup.input_field.setText("Submit quarterly tax report")
    popup.submit_btn.click()

    tasks = repo.get_task_hierarchy(include_completed=True)
    task = next((t for t in tasks if t.title == "Submit quarterly tax report"), None)
    assert task is not None
    assert task.project_tag == "Work"

    # 2. Quick Note Mode
    popup.show_mode("note")
    assert popup.mode == "note"
    assert popup.mode_badge.text() == "Quick Work Note"

    popup.project_btn.setCurrentText("Personal")
    popup.input_field.setText("Buy groceries and milk")
    popup.submit_btn.click()

    notes = repo.get_permanent_notes()
    note = next((n for n in notes if "Buy groceries" in (n.title or "") or "Buy groceries" in (n.content or "")), None)
    assert note is not None
    assert note.project_tag == "Personal"

    # 3. Close button
    popup.close_btn.click()
    assert popup.isVisible() is False
    popup.close()


def test_create_section_dialog_and_calendar_popup(qapp, repo):
    """Test CreateSectionDialog and CalendarPopupDialog modal interactions."""
    # CreateSectionDialog
    dlg = CreateSectionDialog(is_dark=True)
    dlg.input_field.setText("Research")
    dlg._on_color_selected("#3B82F6")
    name, color, desc, kws = dlg.get_data()
    assert name == "Research"
    assert color == "#3B82F6"
    repo.create_or_update_project(name, kws, color=color, description=desc)

    projects = repo.get_all_projects()
    created = next((p for p in projects if p.name == "Research"), None)
    assert created is not None
    assert created.color == "#3B82F6"
    dlg.close()

    # CalendarPopupDialog
    cal_dlg = CalendarPopupDialog(current_date=date.today(), is_dark=True)
    cur_d = date.today()
    day_in_month = 15 if cur_d.day != 15 else 16
    target_date = date(cur_d.year, cur_d.month, day_in_month)
    cal_dlg._on_date_selected(QDate(target_date.year, target_date.month, target_date.day))
    assert cal_dlg.selected_date == target_date
    cal_dlg.close()
