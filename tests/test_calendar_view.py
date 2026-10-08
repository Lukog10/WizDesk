"""Tests for the dedicated CalendarView and MonthCalendarGridWidget."""

from datetime import date, timedelta
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from wiz.core.state_machine import StateMachine
from wiz.storage.models import StorageRepository
from wiz.ui.calendar_view import CalendarView, MonthCalendarGridWidget, ScheduleTaskModalDialog
from wiz.ui.popup_dialog import QuickEntryDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def repo(tmp_path):
    from wiz.storage.db import Database
    db_file = tmp_path / "test_calendar_wiz.db"
    return StorageRepository(Database(db_file))


def test_month_calendar_grid_widget(qapp):
    """Test MonthCalendarGridWidget initialization, date selection, and month switching."""
    today = date.today()
    grid = MonthCalendarGridWidget(today, is_dark=True)
    assert grid.selected_date == today
    assert grid.current_year == today.year
    assert grid.current_month == today.month

    # Test month switching
    grid.set_month(2026, 10, {"2026-10-15": "active"})
    assert grid.current_year == 2026
    assert grid.current_month == 10
    assert grid.date_status_map == {"2026-10-15": "active"}

    # Test selecting date
    new_dt = date(2026, 10, 20)
    grid.set_selected_date(new_dt)
    assert grid.selected_date == new_dt
    assert grid.current_month == 10

    # Test theme toggle
    grid.set_dark_mode(False)
    assert not grid.is_dark
    grid.set_dark_mode(True)
    assert grid.is_dark


def test_calendar_view_initialization_and_layout(qapp, repo):
    """Test CalendarView components, master-detail layout, and theme toggling."""
    cal_view = CalendarView(repo, is_dark=True)
    assert cal_view.selected_date == date.today()
    assert cal_view.active_preset is None
    assert cal_view.left_column.width() == 275
    assert hasattr(cal_view, "calendar_card")
    assert hasattr(cal_view, "quick_views_card")
    assert hasattr(cal_view, "agenda_card")
    assert hasattr(cal_view, "categories_card")
    assert cal_view.scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert cal_view.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    # Test headline does not have double dash
    assert "—" not in cal_view.agenda_title.text()
    assert "--" not in cal_view.agenda_title.text()
    assert "Today, " in cal_view.agenda_title.text()

    # Test theme switching
    cal_view.set_dark_mode(False)
    assert not cal_view.is_dark
    cal_view.set_dark_mode(True)
    assert cal_view.is_dark


def test_calendar_view_quick_presets_and_agenda(qapp, repo):
    """Test Upcoming, Overdue, and Today presets in CalendarView."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    repo.create_task("Future Planning", project_tag="Work", scheduled_date=tomorrow.strftime("%Y-%m-%d"))
    repo.create_task("Overdue Item", project_tag="Personal Projects", scheduled_date=yesterday.strftime("%Y-%m-%d"))

    cal_view = CalendarView(repo, is_dark=True)

    # 1. Upcoming preset
    cal_view.btn_upcoming_preset.click()
    assert cal_view.active_preset == "upcoming"
    assert "Upcoming Scheduled Tasks" in cal_view.agenda_title.text()
    assert cal_view.add_bar_container.isHidden()

    # 2. Overdue preset
    cal_view.btn_overdue_preset.click()
    assert cal_view.active_preset == "overdue"
    assert "Overdue Tasks" in cal_view.agenda_title.text()
    assert cal_view.add_bar_container.isHidden()

    # 3. Today preset
    cal_view.btn_today_preset.click()
    assert cal_view.active_preset is None
    assert cal_view.selected_date == today
    assert not cal_view.add_bar_container.isHidden()


def test_calendar_view_inline_task_scheduling(qapp, repo):
    """Test inline task creation directly from CalendarView schedules task for active date."""
    target_dt = date.today() + timedelta(days=3)
    cal_view = CalendarView(repo, is_dark=True)
    cal_view._on_grid_date_selected(target_dt)
    assert cal_view.selected_date == target_dt

    # Schedule a task
    cal_view.add_input.setText("Ship Calendar Feature")
    cal_view.section_combo.setCurrentText("Work")
    cal_view.add_btn.click()

    # Verify task was created in DB with target_dt
    tasks = repo.get_task_hierarchy(target_date=target_dt, status_filter="task")
    assert any(t.title == "Ship Calendar Feature" and t.scheduled_date == target_dt.strftime("%Y-%m-%d") for t in tasks)

    # Verify dot is added for that date
    summary = repo.get_scheduled_summary_for_month(target_dt.year, target_dt.month)
    assert target_dt.strftime("%Y-%m-%d") in summary
    assert summary[target_dt.strftime("%Y-%m-%d")] == "active"


def test_calendar_view_category_filtering(qapp, repo):
    """Test category breakdown and filtering by project category in CalendarView."""
    today = date.today()
    repo.create_task("Code API Endpoint", project_tag="Coding", scheduled_date=today.strftime("%Y-%m-%d"))
    repo.create_task("Browse Design Inspo", project_tag="Browsing", scheduled_date=today.strftime("%Y-%m-%d"))
    repo.create_task("WizDesk Architecture", project_tag="WizDesk", scheduled_date=today.strftime("%Y-%m-%d"))

    cal_view = CalendarView(repo, is_dark=True)
    assert "All" in cal_view.category_buttons
    assert "Coding" in cal_view.category_buttons
    assert "Browsing" in cal_view.category_buttons
    assert "WizDesk" in cal_view.category_buttons

    # Category counts
    assert cal_view.category_buttons["Coding"].count >= 1
    assert cal_view.category_buttons["Browsing"].count >= 1
    assert cal_view.category_buttons["WizDesk"].count >= 1

    # Filter to Coding
    cal_view.category_buttons["Coding"].click()
    assert cal_view.selected_category_filter == "Coding"
    assert "1 task" in cal_view.task_count_badge.text()

    # Click Coding again to toggle back to All
    cal_view.category_buttons["Coding"].click()
    assert cal_view.selected_category_filter is None
    assert "3 tasks" in cal_view.task_count_badge.text()


def test_calendar_view_mouse_clicks_do_not_move_window(qapp, repo):
    """Verify that clicking calendar dates one by one cannot trigger window dragging."""
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QPointF, QPoint

    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)
    dialog._set_view_mode("calendar")
    dialog.show()
    qapp.processEvents()

    init_pos = dialog.pos()
    grid = dialog.calendar_view.grid_widget

    # Click every rendered date in the grid one by one
    for target_date, cell_rect in list(grid._cell_rects.items()):
        center_pt = cell_rect.center()
        global_pt = grid.mapToGlobal(center_pt.toPoint())

        # Press
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(center_pt),
            QPointF(global_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        grid.mousePressEvent(press_ev)

        # Move slightly (jitter / micro-drag)
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(center_pt + QPointF(5, 5)),
            QPointF(global_pt + QPoint(5, 5)),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        grid.mouseMoveEvent(move_ev)

        # Release
        release_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(center_pt),
            QPointF(global_pt),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        grid.mouseReleaseEvent(release_ev)

        # Ensure window position never altered
        assert dialog.pos() == init_pos
        assert dialog._drag_start_pos is None
        assert dialog._is_dragging is False

    dialog.close()


def test_calendar_view_delete_task(qapp, repo):
    """Test deleting a created task in CalendarView via delete button and action request."""
    from wiz.core.signals import app_signals

    today = date.today()
    task_id = repo.create_task(
        "Calendar Task to Delete",
        project_tag="Work",
        scheduled_date=today.strftime("%Y-%m-%d"),
    )
    assert task_id is not None

    deleted_signal_ids = []
    app_signals.task_deleted.connect(deleted_signal_ids.append)

    cal_view = CalendarView(repo, is_dark=True)
    qapp.processEvents()

    # Find the task row in agenda
    assert cal_view.task_list_layout.count() == 1
    row = cal_view.task_list_layout.itemAt(0).widget()
    assert row is not None
    assert hasattr(row, "delete_btn")

    # Click the delete button
    row.delete_btn.click()
    qapp.processEvents()

    # Verify task was deleted from database
    active_tasks = repo.get_task_hierarchy(target_date=today)
    assert task_id not in [t.id for t in active_tasks]

    # Verify task was removed from agenda layout
    assert cal_view.task_list_layout.count() == 0
    assert "0 tasks" in cal_view.task_count_badge.text()
    assert task_id in deleted_signal_ids

    cal_view.close()


def test_calendar_view_status_changed_no_flicker(qapp, repo):
    """Test changing task status in CalendarView updates database and row without destroying widgets or flickering."""
    today = date.today()
    task_id = repo.create_task(
        "Calendar Status Task",
        project_tag="Work",
        scheduled_date=today.strftime("%Y-%m-%d"),
    )
    assert task_id is not None

    cal_view = CalendarView(repo, is_dark=True)
    qapp.processEvents()

    assert cal_view.task_list_layout.count() == 1
    row = cal_view.task_list_layout.itemAt(0).widget()
    assert row is not None

    # Initial state
    assert not row.checkbox.isChecked()

    # Change status via row handler
    cal_view._on_row_status_changed(task_id, "done")
    qapp.processEvents()

    # Verify task updated in repo
    tasks = repo.get_task_hierarchy(target_date=today)
    matching = next((t for t in tasks if t.id == task_id), None)
    assert matching is not None
    assert matching.status == "done"

    # In day view, the row is preserved (not recreated)
    assert cal_view.task_list_layout.count() == 1
    cal_view.close()


def test_calendar_view_sub_stack_navigation_and_back(qapp, repo):
    """Test switching between Month Grid (Page 0) and Date Detail (Page 1), back button and Esc key."""
    today = date.today()
    target_dt = today + timedelta(days=2)
    cal_view = CalendarView(repo, is_dark=True)
    qapp.processEvents()

    # Initial state: on Page 0 (Month Grid View)
    assert cal_view.sub_stack.currentIndex() == 0

    # User clicks a date in the month grid
    cal_view._on_grid_date_selected(target_dt)
    qapp.processEvents()

    # Navigated to Page 1 (Date Detail Followup Page)
    assert cal_view.sub_stack.currentIndex() == 1
    assert target_dt.strftime("%B %d") in cal_view.agenda_title.text()

    # Click Back to Calendar button
    cal_view.btn_back_to_cal.click()
    qapp.processEvents()
    assert cal_view.sub_stack.currentIndex() == 0

    # Test Escape key returns to Page 0
    cal_view._on_grid_date_selected(target_dt)
    assert cal_view.sub_stack.currentIndex() == 1
    esc_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    cal_view.keyPressEvent(esc_event)
    qapp.processEvents()
    assert cal_view.sub_stack.currentIndex() == 0

    cal_view.close()


def test_calendar_pending_red_dots_and_upcoming_green_dots(qapp, repo):
    """Verify that uncompleted past tasks are marked as pending (red dot) and future tasks as upcoming (green dot)."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    # 1. Past unfinished task -> pending (red dot indicator)
    repo.create_task("Overdue Bug Fix", project_tag="Work", scheduled_date=yesterday.strftime("%Y-%m-%d"))

    # 2. Future unfinished task -> upcoming (green dot indicator)
    repo.create_task("Upcoming Design Review", project_tag="Work", scheduled_date=tomorrow.strftime("%Y-%m-%d"))

    task_data = repo.get_calendar_month_task_data(today.year, today.month)

    y_str = yesterday.strftime("%Y-%m-%d")
    t_str = tomorrow.strftime("%Y-%m-%d")

    assert y_str in task_data
    assert task_data[y_str]["has_pending"] is True
    assert task_data[y_str]["status"] == "pending"

    assert t_str in task_data
    assert task_data[t_str]["has_upcoming"] is True
    assert task_data[t_str]["status"] == "upcoming"

    # Test in CalendarView grid
    cal_view = CalendarView(repo, is_dark=True)
    qapp.processEvents()
    cal_data = cal_view.grid_widget.date_status_map
    assert y_str in cal_data
    assert cal_data[y_str]["has_pending"] is True
    assert t_str in cal_data
    assert cal_data[t_str]["has_upcoming"] is True

    cal_view.close()


def test_schedule_task_modal_dialog(qapp, repo):
    """Test creating and scheduling a task with tags and section via ScheduleTaskModalDialog."""
    tag = repo.create_tag("backend", "#3B82F6")
    today = date.today()
    target_dt = today + timedelta(days=5)

    dlg = ScheduleTaskModalDialog(repo, default_date=target_dt, is_dark=True)
    qapp.processEvents()

    dlg.input_title.setText("Deploy Microservice")
    dlg.section_combo.setCurrentText("Work")

    # Select the tag via tag dropdown
    idx = dlg.tag_combo.findText("backend")
    if idx >= 0:
        dlg.tag_combo.setCurrentIndex(idx)

    created_ids = []
    dlg.task_created.connect(created_ids.append)

    # Submit
    dlg._on_submit()
    qapp.processEvents()

    assert len(created_ids) == 1
    task_id = created_ids[0]

    # Verify task in storage
    tasks = repo.get_task_hierarchy(target_date=target_dt)
    created_task = next((t for t in tasks if t.id == task_id), None)
    assert created_task is not None
    assert created_task.title == "Deploy Microservice"
    assert created_task.project_tag == "Work"
    assert created_task.scheduled_date == target_dt.strftime("%Y-%m-%d")


def test_calendar_category_dropdown_filtering(qapp, repo):
    """Test filtering tasks via category dropdown near schedule button."""
    today = date.today()
    repo.create_task("Code Backend", project_tag="Coding", scheduled_date=today.strftime("%Y-%m-%d"))
    repo.create_task("Browse Ideas", project_tag="Browsing", scheduled_date=today.strftime("%Y-%m-%d"))

    cal_view = CalendarView(repo, is_dark=True)
    qapp.processEvents()

    # Initial state: All categories
    assert cal_view.category_combo.currentText() == "All Categories"
    assert cal_view.selected_category_filter is None

    # Change combo to Coding
    idx = cal_view.category_combo.findText("Coding")
    if idx >= 0:
        cal_view.category_combo.setCurrentIndex(idx)
        qapp.processEvents()
        assert cal_view.selected_category_filter == "Coding"
        assert cal_view.detail_category_combo.currentText() == "Coding"

        # Check detail page shows 1 task
        cal_view._on_grid_date_selected(today)
        qapp.processEvents()
        assert cal_view.task_list_layout.count() == 1

    cal_view.close()
