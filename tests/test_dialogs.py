"""Unit tests for QuickEntryDialog and SettingsDialog."""

import sys
from datetime import date, timedelta
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from wiz.core.config import config
from wiz.core.state_machine import StateMachine, MascotState
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import QuickEntryDialog, RoundedCheckbox, CreateSectionDialog, TaskRowWidget, CalendarPopupDialog
from wiz.ui.quick_bar_dialog import QuickBarPopup
from wiz.ui.settings_dialog import SettingsDialog
from wiz.ui.mascot_window import MascotWindow


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

    # Toggle a task to in_progress and verify mascot state and task list
    target_task = [t for t in tasks if t.title == "Ship MVP update"][0]
    dialog._on_task_status_toggled(target_task.id, "in_progress")
    assert sm.current_state == MascotState.WORKING

    in_prog_tasks = repo.get_task_hierarchy(status_filter="In progress")
    assert "Ship MVP update" in [t.title for t in in_prog_tasks]

    # Toggle a task to done
    dialog._on_task_status_toggled(target_task.id, "done")
    assert sm.current_state == MascotState.COMPLETE

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


def test_app_icon_and_favicon_loading(qapp):
    """Test get_app_icon and get_app_pixmap using idle SVG."""
    from wiz.ui.icons import get_app_icon, get_app_pixmap

    icon = get_app_icon("wiz-idle.svg")
    assert not icon.isNull()

    pm = get_app_pixmap(32, asset_name="wiz-idle.svg")
    assert not pm.isNull()
    assert pm.width() == 32
    assert pm.height() == 32

    # Test alias idle.svg
    icon_alias = get_app_icon("idle.svg")
    assert not icon_alias.isNull()


def test_task_row_inline_status_toggles(qapp, repo):
    """Test changing status via the status dropdown (In progress, Completed, Cancelled, Status) on TaskRowWidget."""
    task_id = repo.create_task("Test inline status task", project_tag="Work")
    tasks = repo.get_task_hierarchy(status_filter="Task")
    task = [t for t in tasks if t.id == task_id][0]

    row = TaskRowWidget(task, ["Work", "Personal"])
    emitted_statuses = []
    row.status_toggled.connect(lambda tid, st: emitted_statuses.append(st))

    # Initial state
    assert not row.checkbox.isChecked
    assert row.status_combo.currentText() in ("Open", "Status")

    # Select 'In progress' from dropdown
    row.status_combo.setCurrentText("In progress")
    assert emitted_statuses[-1] == "in_progress"
    assert row.task.status == "in_progress"

    # Select 'Completed' from dropdown
    row.status_combo.setCurrentText("Completed")
    assert emitted_statuses[-1] == "done"
    assert row.task.status == "done"
    assert row.checkbox.isChecked

    # Select 'Cancelled' from dropdown
    row.status_combo.setCurrentText("Cancelled")
    assert emitted_statuses[-1] == "cancelled"
    assert row.task.status == "cancelled"
    assert not row.checkbox.isChecked

    # Select 'Open' (default) to reset
    row.status_combo.setCurrentText("Open")
    assert emitted_statuses[-1] == "not_started"
    assert row.task.status == "not_started"

    row.deleteLater()


def test_calendar_date_navigation_and_day_isolation(qapp, repo, tmp_path):
    """Test date navigation, day isolation for tasks/notes, and scrollbar removal."""
    from datetime import timedelta
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # 1. Verify scrollbars are off
    assert dialog.scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert dialog.notes_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    # 2. Add task today
    today = date.today()
    yesterday = today - timedelta(days=1)

    t_today = repo.create_task("Today specific task", project_tag="Work")
    t_yesterday = repo.create_task("Yesterday specific task", project_tag="Work")

    # Update created_at timestamp for yesterday's task
    with repo.db.cursor() as cur:
        cur.execute("UPDATE tasks SET created_at = ? WHERE id = ?", (f"{yesterday.isoformat()}T10:00:00", t_yesterday))

    # Viewing today: only today's task is shown
    dialog.set_selected_date(today)
    today_tasks = repo.get_task_hierarchy(target_date=today, status_filter="Task")
    today_ids = [t.id for t in today_tasks]
    assert t_today in today_ids
    assert t_yesterday not in today_ids
    assert dialog.today_pill_btn.isHidden()

    # Navigate to yesterday via prev_day button
    dialog._on_prev_day()
    assert dialog.selected_date == yesterday
    assert not dialog.today_pill_btn.isHidden()

    yesterday_tasks = repo.get_task_hierarchy(target_date=yesterday, status_filter="Task")
    yesterday_ids = [t.id for t in yesterday_tasks]
    assert t_yesterday in yesterday_ids
    assert t_today not in yesterday_ids

    # Click 'Today' button to return to today
    dialog._on_today_clicked()
    assert dialog.selected_date == today
    assert dialog.today_pill_btn.isHidden()

    dialog.close()


def test_task_and_subtask_ui_renaming(qapp, repo):
    """Test inline renaming for TaskRowWidget and SubtaskRowWidget."""
    t_id = repo.create_task("Draft UI spec", project_tag="Work")
    st_id = repo.create_subtask(t_id, "Draw mockups")

    tasks = repo.get_task_hierarchy(status_filter="Task")
    task = [t for t in tasks if t.id == t_id][0]

    row = TaskRowWidget(task, ["Work", "Personal"])
    renamed_tasks = []
    renamed_subtasks = []
    row.task_renamed.connect(lambda tid, title: renamed_tasks.append((tid, title)))
    row.subtask_renamed.connect(lambda sid, title: renamed_subtasks.append((sid, title)))

    # Test Task renaming flow
    assert not row.label.isHidden()
    assert row.edit_input.isHidden()

    row.start_renaming()
    assert row.label.isHidden()
    assert not row.edit_input.isHidden()
    assert row.edit_input.text() == "Draft UI spec"

    # Finish renaming
    row.edit_input.setText("Finalize UI spec")
    row._finish_renaming()

    assert not row.label.isHidden()
    assert row.edit_input.isHidden()
    assert row.label.text() == "Finalize UI spec"
    assert renamed_tasks[-1] == (t_id, "Finalize UI spec")

    # Test Subtask renaming flow
    st_row = row.subtasks_layout.itemAt(0).widget()
    assert not st_row.label.isHidden()
    assert st_row.edit_input.isHidden()

    st_row.start_renaming()
    assert st_row.label.isHidden()
    assert not st_row.edit_input.isHidden()

    st_row.edit_input.setText("Draw vector icons")
    st_row._finish_renaming()

    assert not st_row.label.isHidden()
    assert st_row.edit_input.isHidden()
    assert st_row.label.text() == "Draw vector icons"
    assert renamed_subtasks[-1] == (st_id, "Draw vector icons")

    row.deleteLater()


def test_task_and_subtask_time_display(qapp, repo):
    """Test that TaskRowWidget and SubtaskRowWidget display created and completed time labels."""
    from wiz.ui.popup_dialog import TaskRowWidget
    from wiz.storage.models import TaskRecord, SubtaskRecord
    from datetime import datetime, timedelta

    created_dt = datetime.now() - timedelta(minutes=45)
    completed_dt = datetime.now()

    task = TaskRecord(
        id=99,
        title="Timed Task",
        project_tag="Work",
        status="not_started",
        created_at=created_dt,
        subtasks=[
            SubtaskRecord(
                id=101,
                task_id=99,
                title="Timed Subtask",
                status="not_started",
                created_at=created_dt,
            )
        ]
    )

    row = TaskRowWidget(task, all_projects=["Work"])
    
    # Check uncompleted task time label: (1:36 PM)
    expected_created = created_dt.strftime("%I:%M %p").lstrip("0")
    assert f"({expected_created})" in row.time_label.text()

    # Check uncompleted subtask time label: (1:36 PM)
    st_row = row.subtasks_layout.itemAt(0).widget()
    assert f"({expected_created})" in st_row.time_label.text()

    # Mark subtask done: (1:36 PM - 1:57 PM)
    st_row.checkbox.setChecked(True)
    assert " - " in st_row.time_label.text()
    assert expected_created in st_row.time_label.text()

    # Mark task done: (1:36 PM - 1:57 PM)
    row.status_combo.setCurrentText("Completed")
    assert " - " in row.time_label.text()
    assert expected_created in row.time_label.text()

    row.deleteLater()


def test_dark_mode_theme_toggle_and_dialog_styling(qapp, repo):
    """Test dynamic theme switching between Light and Dark mode on QuickEntryDialog and SettingsDialog."""
    sm = StateMachine()
    qed = QuickEntryDialog(sm, repository=repo)
    settings = SettingsDialog(repository=repo)

    # 1. Verify default or initial theme application
    qed.apply_theme("light")
    assert not qed.is_dark
    assert qed.theme_btn.text() == "☾"

    settings.apply_theme("light")
    assert not settings.is_dark
    assert not settings.dark_mode_check.isChecked()

    # 2. Switch to Dark Mode via theme_btn / apply_theme
    qed.toggle_theme()
    assert config.theme == "dark"
    assert qed.is_dark
    assert qed.theme_btn.text() == "☀"

    # Verify settings dialog responded to theme change
    assert settings.is_dark
    assert settings.dark_mode_check.isChecked()

    # 3. Switch back to Light Mode via SettingsCheckbox
    settings.dark_mode_check.setChecked(False)
    assert config.theme == "light"
    assert not qed.is_dark
    assert qed.theme_btn.text() == "☾"
    assert not settings.is_dark

    # 4. Test CalendarPopupDialog with dark mode
    cal_dark = CalendarPopupDialog(date.today(), is_dark=True)
    assert cal_dark.is_dark
    cal_light = CalendarPopupDialog(date.today(), is_dark=False)
    assert not cal_light.is_dark

    # 5. Test CreateSectionDialog with dark mode
    sec_dark = CreateSectionDialog(is_dark=True)
    assert sec_dark.is_dark
    sec_light = CreateSectionDialog(is_dark=False)
    assert not sec_light.is_dark

    qed.close()
    settings.close()
    cal_dark.close()
    cal_light.close()
    sec_dark.close()
    sec_light.close()


def test_quick_bar_popup_and_multi_click_gestures(qapp, repo):
    """Test QuickBarPopup for Task and Note creation, theme toggling, and multi-click gestures."""
    from wiz.core.signals import app_signals
    from PyQt6.QtCore import QRect

    sm = StateMachine()
    popup = QuickBarPopup(sm, repository=repo)

    # 1. Test Task Mode
    mascot_rect = QRect(200, 400, 80, 80)
    popup.show_mode("task", mascot_rect=mascot_rect)
    assert popup.mode == "task"
    assert "Task" in popup.mode_badge.text()
    assert popup.submit_btn.text() == "Add"

    # Add task via quick bar
    popup.input_field.setText("Quick Bar Created Task")
    popup._on_submit()

    tasks = repo.get_task_hierarchy(target_date=date.today())
    assert any(t.title == "Quick Bar Created Task" for t in tasks)

    # 2. Test Note Mode
    popup.show_mode("note", mascot_rect=mascot_rect)
    assert popup.mode == "note"
    assert "Note" in popup.mode_badge.text()
    assert popup.submit_btn.text() == "Log Note"

    popup.input_field.setText("Quick Bar Logged Work Note")
    popup._on_submit()

    notes = repo.get_notes_for_date(date.today())
    assert any(n.content == "Quick Bar Logged Work Note" for n in notes)

    # 3. Test Theme Switching
    popup.apply_theme("dark")
    assert popup.is_dark
    popup.apply_theme("light")
    assert not popup.is_dark

    # 4. Test Multi-Click Gestures on MascotWindow
    mascot = MascotWindow(sm)
    received_signals = []

    app_signals.request_quick_entry.connect(lambda: received_signals.append("quick_entry"))

    # Simulate Double-click (2 clicks -> opens workspace window)
    mascot._click_count = 2
    mascot._on_click_timeout()
    assert received_signals[-1] == "quick_entry"

    popup.close()
    mascot.close()


def test_quick_entry_dialog_scheduling_and_repeat_flow(qapp, repo):
    """Test task scheduling, repeat modes, upcoming/unfinished filters, and quick-add reset."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    today = date.today()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    # 1. Verify quick-add schedule & repeat default states
    assert dialog._pending_task_schedule is None
    assert dialog._pending_task_repeat == "none"
    assert dialog.add_schedule_btn.scheduled_date is None
    assert dialog.add_repeat_btn.repeat_mode == "none"

    # 2. Add scheduled future task
    dialog.add_input.setText("Plan Q4 Roadmap")
    dialog._pending_task_schedule = tomorrow.strftime("%Y-%m-%d")
    dialog.add_schedule_btn.set_scheduled_date(tomorrow.strftime("%Y-%m-%d"))
    dialog._pending_task_repeat = "daily"
    dialog.add_repeat_btn.set_repeat_mode("daily")
    dialog._on_quick_add_task()

    # Verify reset after creation
    assert dialog._pending_task_schedule is None
    assert dialog._pending_task_repeat == "none"
    assert dialog.add_schedule_btn.scheduled_date is None
    assert dialog.add_repeat_btn.repeat_mode == "none"

    # Verify task in DB
    all_tasks = repo.get_task_hierarchy(status_filter="all")
    created = [t for t in all_tasks if t.title == "Plan Q4 Roadmap"][0]
    assert created.scheduled_date == tomorrow.strftime("%Y-%m-%d")
    assert created.repeat_mode == "daily"
    assert created.is_recurring is True

    # 3. Test Calendar View Upcoming Preset
    dialog._set_view_mode("calendar")
    assert dialog.current_view_mode == "calendar"
    dialog.calendar_view.btn_upcoming_preset.click()
    assert dialog.calendar_view.active_preset == "upcoming"
    assert "Upcoming Scheduled Tasks" in dialog.calendar_view.agenda_title.text()

    # Switch back to Today via today preset
    dialog.calendar_view.btn_today_preset.click()
    assert dialog.calendar_view.active_preset is None
    assert dialog.calendar_view.selected_date == today

    # 4. Test Overdue Preset
    repo.create_task("Submit Tax Forms", project_tag="Work", scheduled_date=yesterday.strftime("%Y-%m-%d"))
    dialog.calendar_view.btn_overdue_preset.click()
    assert dialog.calendar_view.active_preset == "overdue"
    assert "Overdue Tasks" in dialog.calendar_view.agenda_title.text()

    # Switch back to Tasks view
    dialog._set_view_mode("tasks")
    assert dialog.current_view_mode == "tasks"
    assert dialog.filter_bar.current_filter == "Task"

    # 5. Test updating schedule and repeat on an existing task via dialog handlers
    dialog._on_task_schedule_changed(created.id, today.strftime("%Y-%m-%d"))
    dialog._on_task_repeat_changed(created.id, "weekdays")

    updated = [t for t in repo.get_task_hierarchy(status_filter="all") if t.id == created.id][0]
    assert updated.scheduled_date == today.strftime("%Y-%m-%d")
    assert updated.repeat_mode == "weekdays"

    dialog.close()


