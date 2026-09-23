"""Tests for the dedicated CalendarView and MonthCalendarGridWidget."""

from datetime import date, timedelta
import pytest
from PyQt6.QtWidgets import QApplication

from wiz.core.state_machine import StateMachine
from wiz.storage.models import StorageRepository
from wiz.ui.calendar_view import CalendarView, MonthCalendarGridWidget
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
    assert cal_view.grid_widget is not None
    assert cal_view.add_input is not None
    assert cal_view.section_combo is not None
    assert cal_view.add_btn is not None

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
