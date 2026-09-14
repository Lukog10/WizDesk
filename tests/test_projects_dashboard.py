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
from wiz.ui.chart_widgets import (
    KpiStatCard,
    ProjectComparisonChartWidget,
    AppUsageAnalyticsWidget,
    ProjectComparisonCanvas,
    AppUsageRingCanvas,
)
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QMouseEvent


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


def test_get_dashboard_analytics_aggregation(repo: StorageRepository):
    """Test get_dashboard_analytics across timeframes, buckets, and ranking."""
    now = datetime.now()

    # 1. Setup two projects
    repo.create_or_update_project("WizCore", ["core"], color="#6366F1", description="Core backend")
    repo.create_or_update_project("WizUI", ["ui"], color="#10B981", description="Desktop interface")

    # 2. Add tasks
    t1 = repo.create_task("Implement charts", project_tag="WizUI")
    repo.update_task_status(t1, "done")
    t2 = repo.create_task("Fix query optimization", project_tag="WizCore")

    # 3. Add sessions
    s1 = now - timedelta(hours=2)
    s2 = now - timedelta(hours=1)
    repo.log_session("VS Code", "models.py", s1, s2, project_tag="WizCore")

    s3 = now - timedelta(minutes=45)
    repo.log_session("Chrome", "Dashboard Reference", s3, now, project_tag="WizUI")

    # Test "today"
    data_today = repo.get_dashboard_analytics("today")
    assert data_today["timeframe"] == "today"
    assert len(data_today["chart_bucket_labels"]) == 6
    assert data_today["total_tracked_hours"] >= 1.5
    assert data_today["completed_tasks_count"] == 1
    assert data_today["open_tasks_count"] == 1
    assert len(data_today["apps_breakdown"]) == 2
    assert data_today["top_app"] is not None
    assert len(data_today["chart_project_series"]) >= 2

    # Test "this_week"
    data_week = repo.get_dashboard_analytics("this_week")
    assert data_week["timeframe"] == "this_week"
    assert len(data_week["chart_bucket_labels"]) == 7
    assert data_week["chart_bucket_labels"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert data_week["total_tracked_hours"] >= 1.5

    # Test "this_month"
    data_month = repo.get_dashboard_analytics("this_month")
    assert data_month["timeframe"] == "this_month"
    assert len(data_month["chart_bucket_labels"]) == 4

    # Test "all_time"
    data_all = repo.get_dashboard_analytics("all_time")
    assert data_all["timeframe"] == "all_time"
    assert len(data_all["chart_bucket_labels"]) >= 2
    assert "WizCore" in data_all["chart_bucket_labels"]


def test_kpi_stat_card_ui(qapp):
    """Test KpiStatCard rendering, data updates, and theme toggling."""
    # Hero Card
    hero_card = KpiStatCard("Total Tracked Time", "18.5h", "+12.4%", is_hero=True, is_dark=True)
    assert hero_card.is_hero is True
    assert hero_card.lbl_value.text() == "18.5h"
    assert hero_card.lbl_change.text() == "+12.4%"

    hero_card.update_data("22.0h", "+18.0%")
    assert hero_card.lbl_value.text() == "22.0h"
    assert hero_card.lbl_change.text() == "+18.0%"

    hero_card.set_theme(is_dark=False)
    assert hero_card.is_dark is False
    hero_card.set_theme(is_dark=True)
    assert hero_card.is_dark is True

    # Standard Stat Card
    stat_card = KpiStatCard("Active Projects", "4", "", is_hero=False, is_dark=True)
    assert stat_card.is_hero is False
    assert stat_card.lbl_value.text() == "4"
    assert stat_card.lbl_change.isHidden()

    stat_card.update_data("5", "Active")
    assert stat_card.lbl_value.text() == "5"
    assert stat_card.lbl_change.text() == "Active"
    assert not stat_card.lbl_change.isHidden()


def test_project_comparison_chart_widget_ui(qapp):
    """Test ProjectComparisonChartWidget mode switching (Bar/Area), series rendering, and hover."""
    widget = ProjectComparisonChartWidget(is_dark=True)
    assert widget.canvas.chart_mode == "bar"

    series = [
        {"name": "WizCore", "color": "#6366F1", "hours": [1.0, 2.0, 1.5, 0.5, 2.5, 1.0, 0.0], "total_hours": 8.5},
        {"name": "WizUI", "color": "#10B981", "hours": [0.5, 1.0, 0.5, 1.5, 0.5, 2.0, 0.0], "total_hours": 6.0},
    ]
    bucket_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    widget.set_data(series, bucket_labels)
    assert widget.canvas.series == series
    assert widget.canvas.bucket_labels == bucket_labels
    assert widget.legend_layout.count() >= 2

    # Switch to Area mode
    widget.btn_area.click()
    assert widget.canvas.chart_mode == "area"

    # Switch back to Bar mode
    widget.btn_bar.click()
    assert widget.canvas.chart_mode == "bar"

    # Simulate mouse hover on canvas
    hover_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(60.0, 50.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.canvas.mouseMoveEvent(hover_event)
    assert widget.canvas.hover_bucket_idx is not None

    widget.canvas.leaveEvent(None)
    assert widget.canvas.hover_bucket_idx is None

    # Theme toggle
    widget.set_theme(is_dark=False)
    assert widget.is_dark is False
    widget.set_theme(is_dark=True)
    assert widget.is_dark is True


def test_app_usage_analytics_widget_ui(qapp):
    """Test AppUsageAnalyticsWidget mode switching (Ring/Bar) and data rendering."""
    widget = AppUsageAnalyticsWidget(is_dark=True)
    assert widget.active_mode == "ring"
    assert widget.stack.currentWidget() == widget.ring_page

    apps = [
        {"app_name": "Cursor", "hours": 6.5, "percentage": 65.0, "color": "#3B82F6"},
        {"app_name": "Chrome", "hours": 2.5, "percentage": 25.0, "color": "#10B981"},
        {"app_name": "Terminal", "hours": 1.0, "percentage": 10.0, "color": "#F59E0B"},
    ]
    widget.set_data(apps, 10.0)
    assert widget.ring_canvas.total_hours == 10.0
    assert len(widget.ring_canvas.apps_data) == 3
    assert widget.ring_list_layout.count() == 3

    # Switch to Bar mode (user requested option)
    widget.btn_bar.click()
    assert widget.active_mode == "bar"
    assert widget.stack.currentWidget() == widget.bar_page
    assert widget.bar_page_layout.count() >= 3

    # Switch back to Ring mode
    widget.btn_ring.click()
    assert widget.active_mode == "ring"
    assert widget.stack.currentWidget() == widget.ring_page

    # Theme toggle
    widget.set_theme(is_dark=False)
    assert widget.is_dark is False
    widget.set_theme(is_dark=True)
    assert widget.is_dark is True


def test_projects_overview_dashboard_full_integration(qapp, repo: StorageRepository):
    """Test full integration of visual dashboard: KPI cards, charts, and drilldown cards."""
    now = datetime.now()

    repo.create_or_update_project("DealDeck", ["deal"], color="#6366F1", description="Sales CRM")
    t1 = repo.create_task("Pipeline View", project_tag="DealDeck")
    repo.update_task_status(t1, "done")
    repo.log_session("Cursor", "dealdeck.ts", now - timedelta(hours=2), now, project_tag="DealDeck")

    overview = ProjectsOverviewPage(repo, is_dark=True)

    # Check KPI cards populated
    assert overview.kpi_hero.value_text != "0h"
    assert overview.kpi_projects.value_text == "1"
    assert overview.kpi_top_app.value_text == "Cursor"
    assert "1 / 1" in overview.kpi_tasks.value_text

    # Check charts populated
    assert len(overview.chart_widget.canvas.series) >= 1
    assert len(overview.apps_widget.apps_data) >= 1

    # Test timeframe switching
    overview.btn_tf_today.click()
    assert overview.active_timeframe == "today"
    assert len(overview.chart_widget.canvas.bucket_labels) == 6

    overview.btn_tf_week.click()
    assert overview.active_timeframe == "this_week"
    assert len(overview.chart_widget.canvas.bucket_labels) == 7

    overview.btn_tf_month.click()
    assert overview.active_timeframe == "this_month"
    assert len(overview.chart_widget.canvas.bucket_labels) == 4

    overview.btn_tf_all.click()
    assert overview.active_timeframe == "all_time"

    # Theme toggle
    overview.set_theme(is_dark=False)
    assert overview.is_dark is False
    overview.set_theme(is_dark=True)
    assert overview.is_dark is True


def test_project_comparison_canvas_hover_and_crosshair(qapp):
    """Test interactive mouse tracking, crosshair positioning, and tooltip generation."""
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QEvent, QPointF
    from wiz.ui.chart_widgets import ProjectComparisonCanvas

    canvas = ProjectComparisonCanvas(is_dark=True)
    canvas.resize(400, 200)

    series = [
        {"name": "WizDesk Core", "color": "#6366F1", "hours": [2.5, 4.0, 1.5, 3.0, 2.0, 0.0, 0.0]},
        {"name": "Client Portal", "color": "#10B981", "hours": [1.0, 2.5, 0.0, 1.5, 4.0, 0.0, 0.0]},
    ]
    bucket_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    canvas.set_data(series, bucket_labels)

    # Initial state has no hover
    assert canvas.hover_bucket_idx is None

    # Simulate mouse move over Tuesday (index 1)
    # Total plot_w = 400 - 34 - 14 = 352. b_w = 352 / 7 = 50.28.
    # Bucket 1 center = 34 + 1.5 * 50.28 = ~109.4
    move_ev = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(110.0, 80.0),
        QPointF(110.0, 80.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move_ev)
    assert canvas.hover_bucket_idx == 1
    assert canvas.hover_pos == QPoint(110, 80)

    # Repaint with hover active to verify crosshair and glassmorphic card rendering
    canvas.repaint()

    # Switch to Area mode and repaint
    canvas.set_chart_mode("area")
    assert canvas.chart_mode == "area"
    canvas.repaint()

    # Simulate mouse leaving canvas
    leave_ev = QEvent(QEvent.Type.Leave)
    canvas.leaveEvent(leave_ev)
    assert canvas.hover_bucket_idx is None
    assert canvas.hover_pos is None


def test_kpi_card_sparkline_and_progress(qapp):
    """Test micro-sparkline canvas rendering and mini task progress bars."""
    from wiz.ui.chart_widgets import KpiStatCard

    # Hero card with sparkline
    hero = KpiStatCard("Total Tracked Time", "18.8h", "+368%", is_hero=True, is_dark=True)
    hero.resize(200, 90)
    assert hero.sparkline is not None

    sparkline_vals = [2.5, 4.0, 3.2, 1.8, 2.5, 0.0, 0.0]
    hero.set_sparkline_data(sparkline_vals)
    assert hero.sparkline.values == sparkline_vals
    hero.repaint()

    # Standard card with subtitle and task progress
    task_card = KpiStatCard("Tasks Completed", "0 / 0", is_hero=False, is_dark=True)
    task_card.resize(200, 90)
    assert task_card.sparkline is None

    task_card.update_data("3 / 4", "75%", subtitle="75% completed", progress_pct=75)
    assert task_card.value_text == "3 / 4"
    assert task_card.change_text == "75%"
    assert task_card.subtitle_text == "75% completed"
    assert not task_card.progress_bar.isHidden()
    assert task_card.progress_bar.value() == 75
    task_card.repaint()


def test_kpi_card_hover_and_cursor(qapp):
    """Test pointing hand cursor and hover state triggers on KPI cards."""
    from wiz.ui.chart_widgets import KpiStatCard
    from PyQt6.QtCore import QEvent

    hero = KpiStatCard("Total Tracked Time", "18.8h", "+368%", is_hero=True, is_dark=True)
    assert hero.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert hero.sparkline is not None
    assert hero.sparkline.is_hovered is False

    # Simulate mouse enter
    enter_ev = QEvent(QEvent.Type.Enter)
    hero.enterEvent(enter_ev)
    assert hero.sparkline.is_hovered is True

    # Simulate mouse leave
    leave_ev = QEvent(QEvent.Type.Leave)
    hero.leaveEvent(leave_ev)
    assert hero.sparkline.is_hovered is False

    # Standard card has pointing hand cursor too
    card = KpiStatCard("Active Projects", "3", is_hero=False, is_dark=True)
    assert card.cursor().shape() == Qt.CursorShape.PointingHandCursor


def test_project_comparison_canvas_spotlight(qapp):
    """Test crosshair cursor and series spotlighting on comparison chart canvas."""
    from wiz.ui.chart_widgets import ProjectComparisonCanvas

    canvas = ProjectComparisonCanvas(is_dark=True)
    canvas.resize(400, 200)
    assert canvas.cursor().shape() == Qt.CursorShape.CrossCursor
    assert canvas.spotlight_series is None

    series = [
        {"name": "Alpha", "color": "#6366F1", "hours": [1.0, 2.0, 3.0]},
        {"name": "Beta", "color": "#10B981", "hours": [0.5, 1.5, 2.5]},
    ]
    canvas.set_data(series, ["Mon", "Tue", "Wed"])

    canvas.set_spotlight_series("Alpha")
    assert canvas.spotlight_series == "Alpha"
    canvas.repaint()

    canvas.set_chart_mode("area")
    canvas.repaint()

    canvas.set_spotlight_series(None)
    assert canvas.spotlight_series is None
    canvas.repaint()


def test_app_usage_ring_canvas_hover(qapp):
    """Test mouse tracking, hovered ring detection, and center text morphing on AppUsageRingCanvas."""
    from wiz.ui.chart_widgets import AppUsageRingCanvas
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QPointF, QEvent

    canvas = AppUsageRingCanvas(is_dark=True)
    assert canvas.hasMouseTracking() is True

    apps_data = [
        {"app_name": "VS Code", "hours": 8.0, "percentage": 50, "color": "#3B82F6"},
        {"app_name": "Chrome", "hours": 4.0, "percentage": 25, "color": "#10B981"},
        {"app_name": "Terminal", "hours": 2.0, "percentage": 12, "color": "#F59E0B"},
    ]
    canvas.set_data(apps_data, 14.0)

    # Initial state
    assert canvas.hovered_ring_idx is None

    # Center is (70, 70). Outer ring radius = 70 - 10 = 60.
    # Point at (70, 10) is dx=0, dy=-60 (top of ring, angle = 90 deg, inside arc).
    move_ev = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(70.0, 10.0),
        QPointF(70.0, 10.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move_ev)
    assert canvas.hovered_ring_idx == 0
    assert canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
    canvas.repaint()

    # Second ring radius = 60 - (7 + 5) = 48.
    # Point at (70, 70 - 48) = (70, 22).
    move_ev2 = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(70.0, 22.0),
        QPointF(70.0, 22.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move_ev2)
    assert canvas.hovered_ring_idx == 1
    canvas.repaint()

    # Programmatic hover setter
    canvas.set_hovered_ring(2)
    assert canvas.hovered_ring_idx == 2
    canvas.repaint()

    # Mouse leave resets hover
    leave_ev = QEvent(QEvent.Type.Leave)
    canvas.leaveEvent(leave_ev)
    assert canvas.hovered_ring_idx is None
    assert canvas.cursor().shape() == Qt.CursorShape.ArrowCursor
    canvas.repaint()


def test_get_dashboard_analytics_distinct_colors_for_duplicate_and_untagged(repo: StorageRepository):
    """Ensure projects with default colors and untagged work receive distinct colors."""
    now = datetime.now()

    # Create two projects that both have the same default color #6366F1
    repo.create_or_update_project("Project1", ["p1"], color="#6366F1")
    repo.create_or_update_project("Project2", ["p2"], color="#6366F1")

    # Log sessions for Project1, Project2, and Untagged
    s1 = now - timedelta(hours=3)
    s2 = now - timedelta(hours=2)
    s3 = now - timedelta(hours=1)
    repo.log_session("VS Code", "p1.py", s1, s2, project_tag="Project1")
    repo.log_session("PyCharm", "p2.py", s2, s3, project_tag="Project2")
    repo.log_session("Chrome", "untagged.html", s3, now, project_tag=None)

    data = repo.get_dashboard_analytics("today")
    series = data["chart_project_series"]
    assert len(series) >= 3

    colors = [s["color"] for s in series]
    # Verify all assigned colors are strictly unique
    assert len(colors) == len(set(colors))

    # Verify Project1, Project2, and Untagged each have unique colors
    p1_s = next(s for s in series if s["name"] == "Project1")
    p2_s = next(s for s in series if s["name"] == "Project2")
    untagged_s = next(s for s in series if s["name"] == "Untagged")

    assert p1_s["color"] != p2_s["color"]
    assert p1_s["color"] != untagged_s["color"]
    assert p2_s["color"] != untagged_s["color"]


def test_project_comparison_canvas_distinct_colors_sanitization(qapp):
    """Ensure ProjectComparisonCanvas and ChartWidget enforce distinct colors across series."""
    canvas = ProjectComparisonCanvas(is_dark=True)
    duplicate_series = [
        {"name": "Alpha", "color": "#6366F1", "hours": [1.0, 2.0]},
        {"name": "Beta", "color": "#6366F1", "hours": [2.0, 1.0]},
        {"name": "Untagged", "color": "#6366F1", "hours": [0.5, 0.5]},
    ]
    canvas.set_data(duplicate_series, ["10:00", "12:00"])

    colors = [s["color"] for s in canvas.series]
    assert len(colors) == len(set(colors))
    assert canvas.series[0]["color"] != canvas.series[1]["color"]
    assert canvas.series[1]["color"] != canvas.series[2]["color"]

    # Test widget legend sync
    widget = ProjectComparisonChartWidget(is_dark=True)
    widget.set_data(duplicate_series, ["10:00", "12:00"])
    assert widget.canvas.series[0]["color"] != widget.canvas.series[1]["color"]



