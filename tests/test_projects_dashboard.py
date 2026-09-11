"""Tests for the dedicated project tracking dashboard: storage queries, drilldown UI, and dialog integration."""

import pytest
from datetime import datetime, timedelta, date
from pathlib import Path

from wiz.core.state_machine import StateMachine
from wiz.storage.db import Database
from wiz.storage.models import (
    StorageRepository,
    ProjectRecord,
)
from wiz.ui.project_dashboard_view import (
    ProjectDashboardView,
    ProjectsOverviewPage,
    ProjectDetailPage,
    ProjectSummaryCard,
    format_duration,
)
from wiz.ui.popup_dialog import QuickEntryDialog


@pytest.fixture
def repo(tmp_path: Path) -> StorageRepository:
    """Provide an isolated StorageRepository for project dashboard testing."""
    db_file = tmp_path / "test_projects_dashboard.db"
    db = Database(db_path=db_file)
    return StorageRepository(db)


def test_format_duration():
    """Verify human-readable format_duration output."""
    assert format_duration(0) == "0m"
    assert format_duration(-5) == "0m"
    assert format_duration(45) == "45m"
    assert format_duration(60) == "1h"
    assert format_duration(75) == "1h 15m"
    assert format_duration(150) == "2h 30m"


def test_projects_overview_metrics_empty(repo: StorageRepository):
    """Empty database should return empty project list."""
    metrics = repo.get_projects_overview_metrics(timeframe="today")
    assert isinstance(metrics, list)
    assert len(metrics) == 0


def test_projects_overview_metrics_aggregation(repo: StorageRepository):
    """Test project metrics calculation across timeframes."""
    now = datetime.now()

    # 1. Create two projects
    repo.create_or_update_project(
        "Alpha",
        ["alpha", "code"],
        color="#6366F1",
        description="Main product development",
    )
    repo.create_or_update_project(
        "Beta",
        ["beta", "research"],
        color="#10B981",
        description="Secondary initiative",
    )

    # 2. Add tasks to Alpha
    t1 = repo.create_task("Feature 1", project_tag="Alpha")
    t2 = repo.create_task("Feature 2", project_tag="Alpha")
    repo.update_task_status(t1, "done")
    repo.update_task_status(t2, "in progress")

    # 3. Add sessions to Alpha
    s_start1 = now - timedelta(minutes=45)
    s_end1 = now - timedelta(minutes=15)
    repo.log_session("VS Code", "main.py", s_start1, s_end1, project_tag="Alpha")

    s_start2 = now - timedelta(minutes=15)
    s_end2 = now
    repo.log_session("Chrome", "Docs", s_start2, s_end2, project_tag="Alpha")

    # 4. Add task to Beta
    t3 = repo.create_task("Research spec", project_tag="Beta")
    repo.update_task_status(t3, "done")

    # Query overview metrics for 'today'
    overview_today = repo.get_projects_overview_metrics(timeframe="today")
    assert len(overview_today) == 2

    alpha_meta = next(p for p in overview_today if p["name"] == "Alpha")
    assert alpha_meta["color"] == "#6366F1"
    assert alpha_meta["description"] == "Main product development"
    assert alpha_meta["total_tasks"] == 2
    assert alpha_meta["completed_tasks"] == 1
    assert alpha_meta["completion_rate"] == 0.5
    assert alpha_meta["tracked_minutes"] == 45.0
    assert len(alpha_meta["top_apps"]) >= 1

    beta_meta = next(p for p in overview_today if p["name"] == "Beta")
    assert beta_meta["total_tasks"] == 1
    assert beta_meta["completed_tasks"] == 1
    assert beta_meta["completion_rate"] == 1.0
    assert beta_meta["tracked_minutes"] == 0.0

    # Query overview metrics for 'all'
    overview_all = repo.get_projects_overview_metrics(timeframe="all")
    assert len(overview_all) == 2


def test_project_detail_query(repo: StorageRepository):
    """Verify deep-dive project detail query returns tasks, app usage, and keywords."""
    now = datetime.now()
    repo.create_or_update_project(
        "Platform",
        ["infra", "cloud"],
        color="#F59E0B",
        description="Core infrastructure",
    )

    t1 = repo.create_task("Deploy database", project_tag="Platform")
    repo.add_subtask(t1, "Run migrations")
    repo.update_task_status(t1, "done")

    s1 = now - timedelta(minutes=30)
    repo.log_session("Terminal", "pwsh.exe", s1, now, project_tag="Platform")

    detail = repo.get_project_detail("Platform", timeframe="week")
    assert detail["project"] is not None
    assert detail["project"].name == "Platform"
    assert detail["project"].color == "#F59E0B"
    assert detail["project"].description == "Core infrastructure"
    assert detail["total_tasks"] == 1
    assert detail["completed_tasks"] == 1
    assert detail["tracked_minutes"] == 30.0
    assert len(detail["tasks"]) == 1
    assert detail["tasks"][0].title == "Deploy database"
    assert len(detail["apps_breakdown"]) == 1
    assert detail["apps_breakdown"][0]["app_name"] == "Terminal"
    assert detail["project"].keywords == ["infra", "cloud"]


def test_project_crud_lifecycle(repo: StorageRepository):
    """Test full CRUD operations on projects."""
    # Create
    repo.create_or_update_project(
        "TempProject",
        ["temp", "test"],
        color="#8B5CF6",
        description="To be deleted",
    )
    all_projects = repo.get_all_projects()
    assert any(p.name == "TempProject" for p in all_projects)

    # Update
    repo.create_or_update_project(
        "TempProject",
        ["temp", "updated"],
        color="#EC4899",
        description="Updated description",
    )
    all_projects = repo.get_all_projects()
    p = next(p for p in all_projects if p.name == "TempProject")
    assert p.color == "#EC4899"
    assert p.description == "Updated description"
    assert p.keywords == ["temp", "updated"]

    # Delete
    deleted = repo.delete_project_by_name("TempProject")
    assert deleted is True
    all_projects = repo.get_all_projects()
    assert not any(p.name == "TempProject" for p in all_projects)


def test_projects_overview_page_ui(qapp, repo: StorageRepository):
    """Test ProjectsOverviewPage widget rendering and timeframe chip switching."""
    repo.create_or_update_project("Project 1", ["p1"], color="#6366F1")
    repo.create_or_update_project("Project 2", ["p2"], color="#10B981")

    overview = ProjectsOverviewPage(repo, is_dark=True)
    assert overview.active_timeframe == "all_time"
    assert overview.cards_layout.count() == 2

    # Switch timeframe chips
    overview.btn_tf_today.click()
    assert overview.active_timeframe == "today"

    overview.btn_tf_week.click()
    assert overview.active_timeframe == "this_week"

    overview.btn_tf_month.click()
    assert overview.active_timeframe == "this_month"

    overview.btn_tf_all.click()
    assert overview.active_timeframe == "all_time"

    # Theme toggle
    overview.set_theme(is_dark=False)
    assert overview.is_dark is False
    overview.set_theme(is_dark=True)
    assert overview.is_dark is True


def test_project_detail_page_ui(qapp, repo: StorageRepository):
    """Test ProjectDetailPage widget tab navigation, metrics bar, and signals."""
    repo.create_or_update_project(
        "DetailTest",
        ["detail"],
        color="#F43F5E",
        description="Deep dive test project",
    )
    repo.create_task("Sub-feature A", project_tag="DetailTest")

    detail_page = ProjectDetailPage(repo, is_dark=True)
    detail_page.load_project("DetailTest")

    assert detail_page.current_project_name == "DetailTest"
    assert detail_page.title_lbl.text() == "DetailTest"
    assert "Tasks: 0 done (1 open)" in detail_page.lbl_metric_tasks.text()

    # Switch tabs
    detail_page.btn_tab_apps.click()
    assert detail_page.content_stack.currentWidget() == detail_page.apps_page

    detail_page.btn_tab_keywords.click()
    assert detail_page.content_stack.currentWidget() == detail_page.keywords_page

    detail_page.btn_tab_tasks.click()
    assert detail_page.content_stack.currentWidget() == detail_page.tasks_page

    # Verify back button signal
    back_emitted = []
    detail_page.back_clicked.connect(lambda: back_emitted.append(True))
    detail_page.btn_back.click()
    assert len(back_emitted) == 1


def test_project_dashboard_view_drilldown_navigation(qapp, repo: StorageRepository):
    """Test in-page drilldown and back navigation inside ProjectDashboardView."""
    repo.create_or_update_project("WizCore", ["wiz", "core"], color="#0EA5E9")

    dashboard = ProjectDashboardView(repo, is_dark=True)
    assert dashboard.stack.currentWidget() == dashboard.overview_page

    # Drill down to project
    dashboard._show_detail("WizCore")
    assert dashboard.stack.currentWidget() == dashboard.detail_page
    assert dashboard.detail_page.current_project_name == "WizCore"

    # Return to overview
    dashboard._show_overview()
    assert dashboard.stack.currentWidget() == dashboard.overview_page

    # Theme toggle
    dashboard.set_theme(is_dark=False)
    assert dashboard.is_dark is False
    dashboard.set_theme(is_dark=True)
    assert dashboard.is_dark is True


def test_quick_entry_dialog_projects_mode(qapp, repo: StorageRepository):
    """Test 4th Projects mode in QuickEntryDialog and date header scoping."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    assert hasattr(dialog, "projects_mode_btn")
    assert hasattr(dialog, "project_dashboard_view")
    assert hasattr(dialog, "date_header_container")

    # Initial mode is tasks with visible date header
    assert dialog.current_view_mode == "tasks"
    assert not dialog.date_header_container.isHidden()

    # Switch to Projects mode
    dialog.projects_mode_btn.click()
    assert dialog.current_view_mode == "projects"
    assert dialog.stack.currentWidget() == dialog.project_dashboard_view
    assert dialog.date_header_container.isHidden()

    # Switch back to Tasks
    dialog.tasks_mode_btn.click()
    assert dialog.current_view_mode == "tasks"
    assert dialog.stack.currentWidget() == dialog.tasks_page
    assert not dialog.date_header_container.isHidden()

    # Switch to Activity
    dialog.activity_mode_btn.click()
    assert dialog.current_view_mode == "activity"
    assert not dialog.date_header_container.isHidden()

    # Switch to Quick Notes
    dialog.notes_mode_btn.click()
    assert dialog.current_view_mode == "notes"
    assert not dialog.date_header_container.isHidden()
