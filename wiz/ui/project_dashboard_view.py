"""
Dedicated Project Tracking Dashboard view for WizDesk.
Provides an in-page drilldown architecture:
- Overview Page: Summary cards of all projects with timeframe filters, time tracking, task completion progress, and top apps.
- Detail Page: Deep-dive view for a single project covering tasks, application time breakdown, and keyword auto-tagging rules.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QProgressBar,
    QLineEdit,
    QDialog,
    QMessageBox,
    QStackedWidget,
    QSizePolicy,
)

from wiz.storage.models import StorageRepository, ProjectRecord, TaskRecord
from wiz.ui.chart_widgets import (
    KpiStatCard,
    ProjectComparisonChartWidget,
    AppUsageAnalyticsWidget,
)


PRESET_COLORS = [
    "#6366F1",  # Indigo
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#F43F5E",  # Rose
    "#0EA5E9",  # Sky
    "#8B5CF6",  # Violet
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
]


def format_duration(minutes: float) -> str:
    """Format minutes into human readable duration string."""
    total_mins = int(round(minutes))
    if total_mins <= 0:
        return "0m"
    hours = total_mins // 60
    mins = total_mins % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    if hours > 0:
        return f"{hours}h"
    return f"{mins}m"


class ProjectDialog(QDialog):
    """Clean modal dialog for creating or editing a project."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        is_dark: bool = True,
        project: Optional[ProjectRecord] = None,
    ):
        super().__init__(parent)
        self.is_dark = is_dark
        self.project = project
        self.selected_color = project.color if project else PRESET_COLORS[0]

        title = "Edit Project" if project else "New Project"
        self.setWindowTitle(title)
        self.setFixedSize(400, 380)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_lbl = QLabel(title)
        header_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        layout.addWidget(header_lbl)

        # Name Field
        layout.addWidget(QLabel("Project Name:"))
        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("e.g. TurfLine, Research, WizDesk")
        if project:
            self.name_edit.setText(project.name)
            if project.name == "Untagged":
                self.name_edit.setEnabled(False)
        layout.addWidget(self.name_edit)

        # Color Selector
        layout.addWidget(QLabel("Project Accent Color:"))
        color_layout = QHBoxLayout()
        color_layout.setSpacing(8)
        self.color_buttons: List[QPushButton] = []
        for col in PRESET_COLORS:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            is_active = (col.lower() == self.selected_color.lower())
            border = "2px solid #FFFFFF" if is_active else "1px solid transparent"
            btn.setStyleSheet(f"background-color: {col}; border-radius: 14px; border: {border};")
            btn.clicked.connect(lambda checked, c=col: self._on_color_selected(c))
            color_layout.addWidget(btn)
            self.color_buttons.append(btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        # Description Field
        layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit(self)
        self.desc_edit.setPlaceholderText("Brief overview of the project")
        if project:
            self.desc_edit.setText(project.description)
        layout.addWidget(self.desc_edit)

        # Keywords Field
        layout.addWidget(QLabel("Window Title Keywords (comma separated):"))
        self.kw_edit = QLineEdit(self)
        self.kw_edit.setPlaceholderText("e.g. turf, booking, stadium")
        if project:
            self.kw_edit.setText(", ".join(project.keywords))
        layout.addWidget(self.kw_edit)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Project" if project else "Create Project")
        self.save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)
        self._apply_dialog_theme()

    def _on_color_selected(self, color_hex: str) -> None:
        self.selected_color = color_hex
        for idx, col in enumerate(PRESET_COLORS):
            btn = self.color_buttons[idx]
            is_active = (col.lower() == color_hex.lower())
            border = "2px solid #FFFFFF" if is_active else "1px solid transparent"
            btn.setStyleSheet(f"background-color: {col}; border-radius: 14px; border: {border};")

    def _on_save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
            return
        self.accept()

    def get_data(self) -> Tuple[str, str, str, List[str]]:
        name = self.name_edit.text().strip()
        desc = self.desc_edit.text().strip()
        kw_text = self.kw_edit.text().strip()
        kws = [k.strip().lower() for k in kw_text.split(",") if k.strip()]
        return name, self.selected_color, desc, kws

    def _apply_dialog_theme(self) -> None:
        if self.is_dark:
            self.setStyleSheet("""
                QDialog { background-color: #1E1E21; color: #F4F4F6; }
                QLabel { color: #E4E4E7; font-size: 11px; font-weight: 500; }
                QLineEdit {
                    background-color: #28282C;
                    color: #F4F4F6;
                    border: 1px solid #3F3F46;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QLineEdit:focus { border: 1px solid #6366F1; }
                QPushButton {
                    padding: 6px 14px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 500;
                }
            """)
            self.cancel_btn.setStyleSheet("""
                background-color: #28282C;
                color: #A1A1AA;
                border: 1px solid #3F3F46;
            """)
            self.save_btn.setStyleSheet("""
                background-color: #F4F4F6;
                color: #18181B;
                border: 1px solid #F4F4F6;
                font-weight: 600;
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #FFFFFF; color: #111111; }
                QLabel { color: #4B4B46; font-size: 11px; font-weight: 500; }
                QLineEdit {
                    background-color: #FAFAF8;
                    color: #111111;
                    border: 1px solid #DCD6CA;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QLineEdit:focus { border: 1px solid #6366F1; }
                QPushButton {
                    padding: 6px 14px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 500;
                }
            """)
            self.cancel_btn.setStyleSheet("""
                background-color: #F2ECE1;
                color: #555550;
                border: 1px solid #DCD6CA;
            """)
            self.save_btn.setStyleSheet("""
                background-color: #111111;
                color: #FFFFFF;
                border: 1px solid #111111;
                font-weight: 600;
            """)


class ProjectSummaryCard(QFrame):
    """Clickable card representing a project's metrics overview."""

    clicked = pyqtSignal(str)

    def __init__(self, data: Dict[str, Any], is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data = data
        self.is_dark = is_dark
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("ProjectSummaryCard")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(10)

        # Header Row: Color dot, Name, Time badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Color dot indicator
        self.dot = QFrame()
        self.dot.setFixedSize(10, 10)
        color = data.get("color") or "#6366F1"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        top_row.addWidget(self.dot)

        # Project Name
        self.name_lbl = QLabel(data.get("name", "Project"))
        self.name_lbl.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        top_row.addWidget(self.name_lbl)
        top_row.addStretch()

        # Tracked duration badge
        mins = data.get("tracked_minutes", 0.0)
        self.time_badge = QLabel(f"Tracked: {format_duration(mins)}")
        self.time_badge.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        self.time_badge.setObjectName("TimeBadge")
        top_row.addWidget(self.time_badge)

        self.layout.addLayout(top_row)

        # Description / Keywords Row
        desc_text = data.get("description") or ""
        if not desc_text and data.get("keywords"):
            desc_text = f"Keywords: {', '.join(data.get('keywords', []))}"
        if desc_text:
            self.desc_lbl = QLabel(desc_text)
            self.desc_lbl.setFont(QFont("Inter", 10))
            self.desc_lbl.setObjectName("DescLabel")
            self.desc_lbl.setWordWrap(True)
            self.layout.addWidget(self.desc_lbl)

        # Task Completion Progress Row
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        total_tasks = data.get("total_tasks", 0)
        completed_tasks = data.get("completed_tasks", 0)
        pct = int(round(data.get("completion_rate", 0.0) * 100))

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(pct)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        progress_row.addWidget(self.progress_bar, 1)

        self.progress_lbl = QLabel(f"{completed_tasks}/{total_tasks} tasks ({pct}%)")
        self.progress_lbl.setFont(QFont("Inter", 10))
        self.progress_lbl.setObjectName("ProgressText")
        progress_row.addWidget(self.progress_lbl)

        self.layout.addLayout(progress_row)

        # Top Apps Row
        top_apps = data.get("top_apps", [])
        if top_apps:
            apps_row = QHBoxLayout()
            apps_row.setSpacing(6)
            apps_lbl = QLabel("Top apps:")
            apps_lbl.setFont(QFont("Inter", 10))
            apps_lbl.setObjectName("ProgressText")
            apps_row.addWidget(apps_lbl)

            for app_name, app_mins in top_apps:
                chip = QLabel(f"{app_name} ({format_duration(app_mins)})")
                chip.setFont(QFont("Inter", 10))
                chip.setObjectName("AppChip")
                apps_row.addWidget(chip)
            apps_row.addStretch()
            self.layout.addLayout(apps_row)

        self.apply_theme()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.data.get("name", ""))
            event.accept()
        else:
            super().mousePressEvent(event)

    def apply_theme(self) -> None:
        color = self.data.get("color") or "#6366F1"
        if self.is_dark:
            self.setStyleSheet(f"""
                QFrame#ProjectSummaryCard {{
                    background-color: #242427;
                    border: 1px solid #333338;
                    border-radius: 8px;
                }}
                QFrame#ProjectSummaryCard:hover {{
                    border-color: #4A4A52;
                    background-color: #2A2A2E;
                }}
                QLabel {{ color: #F4F4F6; }}
                QLabel#TimeBadge {{
                    background-color: #1E1E22;
                    color: #E4E4E7;
                    border: 1px solid #3F3F46;
                    border-radius: 6px;
                    padding: 3px 8px;
                }}
                QLabel#DescLabel {{ color: #A1A1AA; }}
                QLabel#ProgressText {{ color: #71717A; }}
                QLabel#AppChip {{
                    background-color: #1E1E22;
                    color: #A1A1AA;
                    border: 1px solid #333338;
                    border-radius: 4px;
                    padding: 2px 6px;
                }}
                QProgressBar {{
                    background-color: #333338;
                    border: none;
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#ProjectSummaryCard {{
                    background-color: #FFFFFF;
                    border: 1px solid #E5E0D8;
                    border-radius: 8px;
                }}
                QFrame#ProjectSummaryCard:hover {{
                    border-color: #C8C0B2;
                    background-color: #FAF8F5;
                }}
                QLabel {{ color: #111111; }}
                QLabel#TimeBadge {{
                    background-color: #F7F5F0;
                    color: #222220;
                    border: 1px solid #DCD6CA;
                    border-radius: 6px;
                    padding: 3px 8px;
                }}
                QLabel#DescLabel {{ color: #666660; }}
                QLabel#ProgressText {{ color: #888880; }}
                QLabel#AppChip {{
                    background-color: #F7F5F0;
                    color: #555550;
                    border: 1px solid #E5E0D8;
                    border-radius: 4px;
                    padding: 2px 6px;
                }}
                QProgressBar {{
                    background-color: #EBE6DC;
                    border: none;
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)


class ProjectsOverviewPage(QWidget):
    """Visual Executive Dashboard and Overview feed of all projects."""

    project_selected = pyqtSignal(str)
    new_project_clicked = pyqtSignal()

    def __init__(self, repo: StorageRepository, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.active_timeframe = "all_time"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Action Toolbar: Timeframe Chips, + New Project Button
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_tf_today = QPushButton("Today")
        self.btn_tf_week = QPushButton("This Week")
        self.btn_tf_month = QPushButton("This Month")
        self.btn_tf_all = QPushButton("All Time")

        for btn in [self.btn_tf_today, self.btn_tf_week, self.btn_tf_month, self.btn_tf_all]:
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.btn_tf_all.setChecked(True)

        self.btn_tf_today.clicked.connect(lambda: self._set_timeframe("today"))
        self.btn_tf_week.clicked.connect(lambda: self._set_timeframe("this_week"))
        self.btn_tf_month.clicked.connect(lambda: self._set_timeframe("this_month"))
        self.btn_tf_all.clicked.connect(lambda: self._set_timeframe("all_time"))

        toolbar.addWidget(self.btn_tf_today)
        toolbar.addWidget(self.btn_tf_week)
        toolbar.addWidget(self.btn_tf_month)
        toolbar.addWidget(self.btn_tf_all)
        toolbar.addStretch()

        self.btn_new_project = QPushButton("+ New Project")
        self.btn_new_project.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_new_project.clicked.connect(self.new_project_clicked.emit)
        toolbar.addWidget(self.btn_new_project)

        layout.addLayout(toolbar)

        # Labels preserved for backward compatibility
        self.lbl_metric_projects = QLabel("Projects: 0")
        self.lbl_metric_time = QLabel("Tracked: 0m")
        self.lbl_metric_tasks = QLabel("Tasks: 0 / 0")

        # 2. Main Scroll Area for Executive Dashboard & Project Cards
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("ProjectsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(0, 4, 4, 16)
        self.content_layout.setSpacing(14)

        # Section 1: Executive KPI Cards (2x2 Grid for generous card width & readability)
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(10)

        self.kpi_hero = KpiStatCard("Total Tracked Time", "0h", "", is_hero=True, is_dark=self.is_dark, parent=self.scroll_content)
        self.kpi_projects = KpiStatCard("Active Projects", "0", "", is_hero=False, is_dark=self.is_dark, parent=self.scroll_content)
        self.kpi_top_app = KpiStatCard("Top Application", "None", "", is_hero=False, is_dark=self.is_dark, parent=self.scroll_content)
        self.kpi_tasks = KpiStatCard("Tasks Completed", "0 / 0", "", is_hero=False, is_dark=self.is_dark, parent=self.scroll_content)

        self.kpi_grid.addWidget(self.kpi_hero, 0, 0)
        self.kpi_grid.addWidget(self.kpi_projects, 0, 1)
        self.kpi_grid.addWidget(self.kpi_top_app, 1, 0)
        self.kpi_grid.addWidget(self.kpi_tasks, 1, 1)
        self.content_layout.addLayout(self.kpi_grid)

        # Section 2: Visual Comparison Chart
        self.chart_widget = ProjectComparisonChartWidget(is_dark=self.is_dark, parent=self.scroll_content)
        self.content_layout.addWidget(self.chart_widget)

        # Section 3: Visual Application Usage Analytics
        self.apps_widget = AppUsageAnalyticsWidget(is_dark=self.is_dark, parent=self.scroll_content)
        self.content_layout.addWidget(self.apps_widget)

        # Section 3: Projects Directory Header & Cards
        dir_header = QHBoxLayout()
        dir_header.setSpacing(8)

        self.lbl_directory_title = QLabel("Projects Directory")
        self.lbl_directory_title.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        dir_header.addWidget(self.lbl_directory_title)

        self.lbl_directory_count = QLabel("0 Projects")
        self.lbl_directory_count.setObjectName("DirectoryBadge")
        self.lbl_directory_count.setFont(QFont("Inter", 9, QFont.Weight.Medium))
        dir_header.addWidget(self.lbl_directory_count)
        dir_header.addStretch()

        self.content_layout.addLayout(dir_header)

        self.cards_container = QWidget(self.scroll_content)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.addWidget(self.cards_container)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        self.apply_theme()
        self.refresh()

    def _set_timeframe(self, timeframe: str) -> None:
        self.active_timeframe = timeframe
        self.btn_tf_today.setChecked(timeframe == "today")
        self.btn_tf_week.setChecked(timeframe == "this_week")
        self.btn_tf_month.setChecked(timeframe == "this_month")
        self.btn_tf_all.setChecked(timeframe == "all_time")
        self.refresh()

    def refresh(self) -> None:
        """Fetch updated project metrics and re-render charts, stats, and project cards."""
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # 1. Fetch high-level analytics
        analytics = self.repo.get_dashboard_analytics(timeframe=self.active_timeframe)

        tot_mins = analytics.get("total_tracked_minutes", 0.0)
        tot_hrs = analytics.get("total_tracked_hours", 0.0)
        chg_pct = analytics.get("change_percentage", 0.0)
        chg_str = f"+{chg_pct}%" if chg_pct > 0 else (f"{chg_pct}%" if chg_pct < 0 else "")
        self.kpi_hero.update_data(f"{tot_hrs}h", chg_str)

        active_cnt = analytics.get("active_projects_count", 0)
        self.kpi_projects.update_data(str(active_cnt), "Active")

        top_app = analytics.get("top_app")
        if top_app:
            self.kpi_top_app.update_data(top_app["app_name"], f"{top_app.get('hours', 0.0)}h")
        else:
            self.kpi_top_app.update_data("None", "")

        completed_tasks = analytics.get("completed_tasks_count", 0)
        open_tasks = analytics.get("open_tasks_count", 0)
        tot_tasks = completed_tasks + open_tasks
        task_pct = f"{round(completed_tasks / tot_tasks * 100)}%" if tot_tasks > 0 else ""
        self.kpi_tasks.update_data(f"{completed_tasks} / {tot_tasks}", task_pct)

        # Update legacy labels
        self.lbl_metric_projects.setText(f"Projects: {active_cnt}")
        self.lbl_metric_time.setText(f"Tracked: {format_duration(tot_mins)}")
        self.lbl_metric_tasks.setText(f"Tasks: {completed_tasks} / {tot_tasks}")

        # 2. Update Visual Charts
        self.chart_widget.set_data(
            analytics.get("chart_project_series", []),
            analytics.get("chart_bucket_labels", []),
        )
        self.apps_widget.set_data(
            analytics.get("apps_breakdown", []),
            tot_hrs,
        )

        # 3. Fetch project overview metrics for drilldown cards
        metrics_list = self.repo.get_projects_overview_metrics(timeframe=self.active_timeframe)
        self.lbl_directory_count.setText(f"{len(metrics_list)} Projects")

        if not metrics_list:
            empty_card = QFrame()
            empty_card.setObjectName("EmptyCard")
            empty_layout = QVBoxLayout(empty_card)
            empty_layout.setContentsMargins(20, 32, 20, 32)
            empty_layout.setSpacing(8)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel("No projects configured")
            title.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            sub = QLabel("Click '+ New Project' to define project names, colors, and keyword matching rules.")
            sub.setFont(QFont("Inter", 11))
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub.setWordWrap(True)

            empty_layout.addWidget(title)
            empty_layout.addWidget(sub)
            self.cards_layout.addWidget(empty_card)
        else:
            for data in metrics_list:
                card = ProjectSummaryCard(data, is_dark=self.is_dark)
                card.clicked.connect(self.project_selected.emit)
                self.cards_layout.addWidget(card)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.kpi_hero.set_theme(is_dark)
        self.kpi_projects.set_theme(is_dark)
        self.kpi_top_app.set_theme(is_dark)
        self.kpi_tasks.set_theme(is_dark)
        self.chart_widget.set_theme(is_dark)
        self.apps_widget.set_theme(is_dark)
        self.apply_theme()
        self.refresh()

    def apply_theme(self) -> None:
        if self.is_dark:
            chip_style = """
                QPushButton {
                    background-color: #242427;
                    color: #A1A1AA;
                    border: 1px solid #3F3F46;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:checked {
                    background-color: #F4F4F6;
                    color: #18181B;
                    border: 1px solid #F4F4F6;
                    font-weight: 600;
                }
                QPushButton:hover:!checked {
                    background-color: #2E2E33;
                    color: #FFFFFF;
                }
            """
            btn_new_style = """
                QPushButton {
                    background-color: #2E2E33;
                    color: #F4F4F6;
                    border: 1px solid #4A4A52;
                    border-radius: 12px;
                    padding: 4px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #383840;
                    border-color: #6366F1;
                }
            """
            badge_style = """
                QLabel#DirectoryBadge {
                    background-color: #242427;
                    color: #A1A1AA;
                    border: 1px solid #333338;
                    border-radius: 6px;
                    padding: 2px 8px;
                    font-size: 10px;
                }
                QFrame#EmptyCard {
                    background-color: #242427;
                    border: 1px dashed #3F3F46;
                    border-radius: 8px;
                }
                QFrame#EmptyCard QLabel { color: #A1A1AA; }
            """
            dir_title_color = "#F4F4F6"
        else:
            chip_style = """
                QPushButton {
                    background-color: #FFFFFF;
                    color: #666660;
                    border: 1px solid #DCD6CA;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:checked {
                    background-color: #111111;
                    color: #FFFFFF;
                    border: 1px solid #111111;
                    font-weight: 600;
                }
                QPushButton:hover:!checked {
                    background-color: #F2ECE1;
                    color: #111111;
                }
            """
            btn_new_style = """
                QPushButton {
                    background-color: #111111;
                    color: #FFFFFF;
                    border: 1px solid #111111;
                    border-radius: 12px;
                    padding: 4px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #2E2E33;
                }
            """
            badge_style = """
                QLabel#DirectoryBadge {
                    background-color: #FFFFFF;
                    color: #71717A;
                    border: 1px solid #E5E0D8;
                    border-radius: 6px;
                    padding: 2px 8px;
                    font-size: 10px;
                }
                QFrame#EmptyCard {
                    background-color: #FFFFFF;
                    border: 1px dashed #DCD6CA;
                    border-radius: 8px;
                }
                QFrame#EmptyCard QLabel { color: #666660; }
            """
            dir_title_color = "#111111"

        self.btn_tf_today.setStyleSheet(chip_style)
        self.btn_tf_week.setStyleSheet(chip_style)
        self.btn_tf_month.setStyleSheet(chip_style)
        self.btn_tf_all.setStyleSheet(chip_style)
        self.btn_new_project.setStyleSheet(btn_new_style)
        self.lbl_directory_title.setStyleSheet(f"color: {dir_title_color};")
        self.setStyleSheet(badge_style)

        scrollbar_color = "rgba(255, 255, 255, 0.15)" if self.is_dark else "rgba(0, 0, 0, 0.15)"
        scrollbar_hover = "rgba(255, 255, 255, 0.3)" if self.is_dark else "rgba(0, 0, 0, 0.3)"
        scroll_style = f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {scrollbar_color};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scrollbar_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """
        self.scroll_area.setStyleSheet(scroll_style)
        self.scroll_content.setStyleSheet("background: transparent;")


class ProjectDetailPage(QWidget):
    """Detailed view of a single project covering tasks, apps breakdown, and keywords."""

    back_clicked = pyqtSignal()
    project_updated = pyqtSignal()

    def __init__(self, repo: StorageRepository, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.current_project_name = ""
        self.active_timeframe = "all_time"
        self.active_tab = "tasks"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Navigation & Actions Header
        nav_row = QHBoxLayout()
        nav_row.setSpacing(10)

        self.btn_back = QPushButton("< All Projects")
        self.btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back.clicked.connect(self.back_clicked.emit)
        nav_row.addWidget(self.btn_back)

        self.color_dot = QFrame()
        self.color_dot.setFixedSize(12, 12)
        self.color_dot.setStyleSheet("background-color: #6366F1; border-radius: 6px;")
        nav_row.addWidget(self.color_dot)

        self.title_lbl = QLabel("Project Details")
        self.title_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        nav_row.addWidget(self.title_lbl)
        nav_row.addStretch()

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_edit.clicked.connect(self._on_edit_project)
        nav_row.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.clicked.connect(self._on_delete_project)
        nav_row.addWidget(self.btn_delete)

        layout.addLayout(nav_row)

        # 2. Timeframe Filter Chips
        tf_row = QHBoxLayout()
        tf_row.setSpacing(8)

        self.btn_tf_today = QPushButton("Today")
        self.btn_tf_week = QPushButton("This Week")
        self.btn_tf_month = QPushButton("This Month")
        self.btn_tf_all = QPushButton("All Time")

        for btn in [self.btn_tf_today, self.btn_tf_week, self.btn_tf_month, self.btn_tf_all]:
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.btn_tf_all.setChecked(True)

        self.btn_tf_today.clicked.connect(lambda: self._set_timeframe("today"))
        self.btn_tf_week.clicked.connect(lambda: self._set_timeframe("this_week"))
        self.btn_tf_month.clicked.connect(lambda: self._set_timeframe("this_month"))
        self.btn_tf_all.clicked.connect(lambda: self._set_timeframe("all_time"))

        tf_row.addWidget(self.btn_tf_today)
        tf_row.addWidget(self.btn_tf_week)
        tf_row.addWidget(self.btn_tf_month)
        tf_row.addWidget(self.btn_tf_all)
        tf_row.addStretch()

        layout.addLayout(tf_row)

        # 3. Metrics Summary Strip
        self.metrics_bar = QFrame(self)
        self.metrics_bar.setObjectName("MetricsBar")
        metrics_layout = QHBoxLayout(self.metrics_bar)
        metrics_layout.setContentsMargins(0, 0, 0, 4)
        metrics_layout.setSpacing(8)

        self.lbl_metric_time = QLabel("Tracked: 0m")
        self.lbl_metric_time.setObjectName("MetricBadge")
        self.lbl_metric_tasks = QLabel("Tasks: 0 completed (0 open)")
        self.lbl_metric_tasks.setObjectName("MetricBadge")
        self.lbl_metric_sessions = QLabel("Sessions: 0")
        self.lbl_metric_sessions.setObjectName("MetricBadge")

        metrics_layout.addWidget(self.lbl_metric_time)
        metrics_layout.addWidget(self.lbl_metric_tasks)
        metrics_layout.addWidget(self.lbl_metric_sessions)
        metrics_layout.addStretch()

        layout.addWidget(self.metrics_bar)

        # 4. Section Tabs (Tasks | App Breakdown | Rules & Keywords)
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        self.btn_tab_tasks = QPushButton("Tasks")
        self.btn_tab_apps = QPushButton("App Breakdown")
        self.btn_tab_keywords = QPushButton("Keywords && Rules")

        for btn in [self.btn_tab_tasks, self.btn_tab_apps, self.btn_tab_keywords]:
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.btn_tab_tasks.setChecked(True)

        self.btn_tab_tasks.clicked.connect(lambda: self._set_tab("tasks"))
        self.btn_tab_apps.clicked.connect(lambda: self._set_tab("apps"))
        self.btn_tab_keywords.clicked.connect(lambda: self._set_tab("keywords"))

        tab_row.addWidget(self.btn_tab_tasks)
        tab_row.addWidget(self.btn_tab_apps)
        tab_row.addWidget(self.btn_tab_keywords)
        tab_row.addStretch()

        layout.addLayout(tab_row)

        # 5. Detail Content Stack
        self.content_stack = QStackedWidget(self)

        # 5a. Tasks Page
        self.tasks_page = QWidget()
        tasks_layout = QVBoxLayout(self.tasks_page)
        tasks_layout.setContentsMargins(0, 0, 0, 0)
        tasks_layout.setSpacing(8)

        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tasks_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tasks_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.tasks_content = QWidget()
        self.tasks_content_layout = QVBoxLayout(self.tasks_content)
        self.tasks_content_layout.setContentsMargins(0, 4, 4, 12)
        self.tasks_content_layout.setSpacing(8)
        self.tasks_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.tasks_scroll.setWidget(self.tasks_content)
        tasks_layout.addWidget(self.tasks_scroll)
        self.content_stack.addWidget(self.tasks_page)

        # 5b. Apps Breakdown Page
        self.apps_page = QWidget()
        apps_layout = QVBoxLayout(self.apps_page)
        apps_layout.setContentsMargins(0, 0, 0, 0)
        apps_layout.setSpacing(8)

        self.apps_scroll = QScrollArea()
        self.apps_scroll.setWidgetResizable(True)
        self.apps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.apps_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.apps_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.apps_content = QWidget()
        self.apps_content_layout = QVBoxLayout(self.apps_content)
        self.apps_content_layout.setContentsMargins(0, 4, 4, 12)
        self.apps_content_layout.setSpacing(8)
        self.apps_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.apps_scroll.setWidget(self.apps_content)
        apps_layout.addWidget(self.apps_scroll)
        self.content_stack.addWidget(self.apps_page)

        # 5c. Keywords & Rules Page
        self.keywords_page = QWidget()
        kw_layout = QVBoxLayout(self.keywords_page)
        kw_layout.setContentsMargins(0, 0, 0, 0)
        kw_layout.setSpacing(8)

        self.kw_scroll = QScrollArea()
        self.kw_scroll.setWidgetResizable(True)
        self.kw_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.kw_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.kw_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.kw_content = QWidget()
        self.kw_content_layout = QVBoxLayout(self.kw_content)
        self.kw_content_layout.setContentsMargins(0, 4, 4, 12)
        self.kw_content_layout.setSpacing(8)
        self.kw_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.kw_scroll.setWidget(self.kw_content)
        kw_layout.addWidget(self.kw_scroll)
        self.content_stack.addWidget(self.keywords_page)

        layout.addWidget(self.content_stack, 1)

        self.apply_theme()

    def _set_timeframe(self, timeframe: str) -> None:
        self.active_timeframe = timeframe
        self.btn_tf_today.setChecked(timeframe == "today")
        self.btn_tf_week.setChecked(timeframe == "this_week")
        self.btn_tf_month.setChecked(timeframe == "this_month")
        self.btn_tf_all.setChecked(timeframe == "all_time")
        self.load_project(self.current_project_name)

    def _set_tab(self, tab_key: str) -> None:
        self.active_tab = tab_key
        self.btn_tab_tasks.setChecked(tab_key == "tasks")
        self.btn_tab_apps.setChecked(tab_key == "apps")
        self.btn_tab_keywords.setChecked(tab_key == "keywords")

        if tab_key == "tasks":
            self.content_stack.setCurrentWidget(self.tasks_page)
        elif tab_key == "apps":
            self.content_stack.setCurrentWidget(self.apps_page)
        elif tab_key == "keywords":
            self.content_stack.setCurrentWidget(self.keywords_page)

    def load_project(self, project_name: str) -> None:
        """Load and display comprehensive details for the specified project."""
        self.current_project_name = project_name
        detail = self.repo.get_project_detail(project_name, timeframe=self.active_timeframe)
        proj: ProjectRecord = detail.get("project")

        # Update Header
        self.title_lbl.setText(project_name)
        color = proj.color if proj else "#6366F1"
        self.color_dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")

        # Disable delete for Untagged
        is_untagged = (project_name.lower() == "untagged")
        self.btn_delete.setEnabled(not is_untagged)
        self.btn_edit.setEnabled(not is_untagged)

        # Update Summary Badges
        mins = detail.get("tracked_minutes", 0.0)
        self.lbl_metric_time.setText(f"Tracked: {format_duration(mins)}")

        completed_tasks = detail.get("completed_tasks", 0)
        open_tasks = detail.get("open_tasks", 0)
        self.lbl_metric_tasks.setText(f"Tasks: {completed_tasks} done ({open_tasks} open)")

        sess_count = detail.get("total_sessions", 0)
        self.lbl_metric_sessions.setText(f"Sessions: {sess_count}")

        # Render Tasks
        self._render_tasks(detail.get("tasks", []))

        # Render App Breakdown
        self._render_apps(detail.get("apps_breakdown", []))

        # Render Keywords
        kws = proj.keywords if proj else []
        self._render_keywords(kws, proj.description if proj else "")

    def _render_tasks(self, tasks: List[TaskRecord]) -> None:
        while self.tasks_content_layout.count() > 0:
            item = self.tasks_content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not tasks:
            empty = QLabel("No tasks tagged to this project yet.")
            empty.setFont(QFont("Inter", 11))
            empty.setStyleSheet("color: #71717A; padding: 20px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_content_layout.addWidget(empty)
            return

        for task in tasks:
            card = QFrame()
            card.setObjectName("DetailItemCard")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(12, 10, 12, 10)
            c_layout.setSpacing(6)

            t_row = QHBoxLayout()
            t_row.setSpacing(8)

            status_color = "#10B981" if task.status == "done" else ("#F59E0B" if task.status in ("in_progress", "pending") else "#71717A")
            status_dot = QFrame()
            status_dot.setFixedSize(8, 8)
            status_dot.setStyleSheet(f"background-color: {status_color}; border-radius: 4px;")
            t_row.addWidget(status_dot)

            t_title = QLabel(task.title)
            t_title.setFont(QFont("Inter", 12, QFont.Weight.Medium))
            t_row.addWidget(t_title)
            t_row.addStretch()

            status_lbl = QLabel(task.status.replace("_", " ").title())
            status_lbl.setFont(QFont("Inter", 10))
            status_lbl.setStyleSheet(f"color: {status_color}; font-weight: 600;")
            t_row.addWidget(status_lbl)

            c_layout.addLayout(t_row)

            # Subtasks
            for sub in task.subtasks:
                s_row = QHBoxLayout()
                s_row.setContentsMargins(16, 0, 0, 0)
                s_row.setSpacing(6)
                s_dot = QLabel("•")
                s_dot.setStyleSheet("color: #71717A;")
                s_title = QLabel(sub.title)
                s_title.setFont(QFont("Inter", 11))
                s_title.setStyleSheet("color: #A1A1AA;" if self.is_dark else "color: #555550;")
                s_row.addWidget(s_dot)
                s_row.addWidget(s_title)
                s_row.addStretch()
                c_layout.addLayout(s_row)

            self.tasks_content_layout.addWidget(card)

    def _render_apps(self, apps: List[Dict[str, Any]]) -> None:
        while self.apps_content_layout.count() > 0:
            item = self.apps_content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not apps:
            empty = QLabel("No application usage logged for this project in the selected timeframe.")
            empty.setFont(QFont("Inter", 11))
            empty.setStyleSheet("color: #71717A; padding: 20px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.apps_content_layout.addWidget(empty)
            return

        for app_info in apps:
            card = QFrame()
            card.setObjectName("DetailItemCard")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(12, 10, 12, 10)
            c_layout.setSpacing(6)

            row = QHBoxLayout()
            app_lbl = QLabel(app_info.get("app_name", "Unknown"))
            app_lbl.setFont(QFont("Inter", 12, QFont.Weight.Medium))
            row.addWidget(app_lbl)
            row.addStretch()

            mins = app_info.get("minutes", 0.0)
            pct = app_info.get("percentage", 0.0)
            stat_lbl = QLabel(f"{format_duration(mins)} ({pct}%)")
            stat_lbl.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
            row.addWidget(stat_lbl)
            c_layout.addLayout(row)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(round(pct)))
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            c_layout.addWidget(bar)

            self.apps_content_layout.addWidget(card)

    def _render_keywords(self, keywords: List[str], description: str) -> None:
        while self.kw_content_layout.count() > 0:
            item = self.kw_content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        card = QFrame()
        card.setObjectName("DetailItemCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(10)

        d_title = QLabel("Description:")
        d_title.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        c_layout.addWidget(d_title)

        d_val = QLabel(description or "No description provided.")
        d_val.setFont(QFont("Inter", 11))
        d_val.setStyleSheet("color: #A1A1AA;" if self.is_dark else "color: #555550;")
        d_val.setWordWrap(True)
        c_layout.addWidget(d_val)

        c_layout.addSpacing(6)

        k_title = QLabel("Auto-Tracking Matching Keywords:")
        k_title.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        c_layout.addWidget(k_title)

        if not keywords:
            k_val = QLabel("No keywords configured. Window titles will not be auto-tagged to this project.")
            k_val.setFont(QFont("Inter", 11))
            k_val.setStyleSheet("color: #71717A;")
            c_layout.addWidget(k_val)
        else:
            chips_layout = QHBoxLayout()
            chips_layout.setSpacing(6)
            for kw in keywords:
                chip = QLabel(kw)
                chip.setFont(QFont("Inter", 10))
                chip.setObjectName("KeywordChip")
                chips_layout.addWidget(chip)
            chips_layout.addStretch()
            c_layout.addLayout(chips_layout)

        self.kw_content_layout.addWidget(card)

    def _on_edit_project(self) -> None:
        projects = self.repo.get_all_projects()
        target = next((p for p in projects if p.name == self.current_project_name), None)
        if not target:
            return
        dlg = ProjectDialog(self, is_dark=self.is_dark, project=target)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, color, desc, kws = dlg.get_data()
            self.repo.create_or_update_project(name, kws, color=color, description=desc)
            self.current_project_name = name
            self.load_project(name)
            self.project_updated.emit()

    def _on_delete_project(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete project '{self.current_project_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.repo.delete_project_by_name(self.current_project_name)
            self.project_updated.emit()
            self.back_clicked.emit()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.apply_theme()
        if self.current_project_name:
            self.load_project(self.current_project_name)

    def apply_theme(self) -> None:
        if self.is_dark:
            btn_style = """
                QPushButton {
                    background-color: #242427;
                    color: #A1A1AA;
                    border: 1px solid #3F3F46;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2E2E33;
                    color: #FFFFFF;
                }
            """
            chip_style = """
                QPushButton {
                    background-color: #242427;
                    color: #A1A1AA;
                    border: 1px solid #3F3F46;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:checked {
                    background-color: #F4F4F6;
                    color: #18181B;
                    border: 1px solid #F4F4F6;
                    font-weight: 600;
                }
                QPushButton:hover:!checked {
                    background-color: #2E2E33;
                    color: #FFFFFF;
                }
            """
            card_style = """
                QFrame#DetailItemCard {
                    background-color: #242427;
                    border: 1px solid #333338;
                    border-radius: 8px;
                }
                QLabel { color: #F4F4F6; }
                QLabel#KeywordChip {
                    background-color: #1E1E22;
                    color: #A1A1AA;
                    border: 1px solid #333338;
                    border-radius: 4px;
                    padding: 3px 8px;
                }
                QProgressBar {
                    background-color: #333338;
                    border: none;
                    border-radius: 3px;
                }
                QProgressBar::chunk {
                    background-color: #6366F1;
                    border-radius: 3px;
                }
            """
            badge_style = """
                QFrame#MetricsBar { background: transparent; border: none; }
                QLabel#MetricBadge {
                    background-color: #242427;
                    color: #E4E4E7;
                    border: 1px solid #333338;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
            """
        else:
            btn_style = """
                QPushButton {
                    background-color: #FFFFFF;
                    color: #555550;
                    border: 1px solid #DCD6CA;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #F2ECE1;
                    color: #111111;
                }
            """
            chip_style = """
                QPushButton {
                    background-color: #FFFFFF;
                    color: #666660;
                    border: 1px solid #DCD6CA;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:checked {
                    background-color: #111111;
                    color: #FFFFFF;
                    border: 1px solid #111111;
                    font-weight: 600;
                }
                QPushButton:hover:!checked {
                    background-color: #F2ECE1;
                    color: #111111;
                }
            """
            card_style = """
                QFrame#DetailItemCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E5E0D8;
                    border-radius: 8px;
                }
                QLabel { color: #111111; }
                QLabel#KeywordChip {
                    background-color: #F7F5F0;
                    color: #555550;
                    border: 1px solid #DCD6CA;
                    border-radius: 4px;
                    padding: 3px 8px;
                }
                QProgressBar {
                    background-color: #EBE6DC;
                    border: none;
                    border-radius: 3px;
                }
                QProgressBar::chunk {
                    background-color: #6366F1;
                    border-radius: 3px;
                }
            """
            badge_style = """
                QFrame#MetricsBar { background: transparent; border: none; }
                QLabel#MetricBadge {
                    background-color: #FFFFFF;
                    color: #222220;
                    border: 1px solid #DCD6CA;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
            """

        self.btn_back.setStyleSheet(btn_style)
        self.btn_edit.setStyleSheet(btn_style)
        self.btn_delete.setStyleSheet(btn_style)

        self.btn_tf_today.setStyleSheet(chip_style)
        self.btn_tf_week.setStyleSheet(chip_style)
        self.btn_tf_month.setStyleSheet(chip_style)
        self.btn_tf_all.setStyleSheet(chip_style)

        self.btn_tab_tasks.setStyleSheet(chip_style)
        self.btn_tab_apps.setStyleSheet(chip_style)
        self.btn_tab_keywords.setStyleSheet(chip_style)

        self.metrics_bar.setStyleSheet(badge_style)
        self.setStyleSheet(card_style)
        self.tasks_scroll.setStyleSheet("background: transparent;")
        self.tasks_content.setStyleSheet("background: transparent;")
        self.apps_scroll.setStyleSheet("background: transparent;")
        self.apps_content.setStyleSheet("background: transparent;")
        self.kw_scroll.setStyleSheet("background: transparent;")
        self.kw_content.setStyleSheet("background: transparent;")


class ProjectDashboardView(QWidget):
    """Main view wrapper managing transitions between Projects Overview and Project Detail."""

    project_changed = pyqtSignal()

    def __init__(self, repo: StorageRepository, parent: Optional[QWidget] = None, is_dark: bool = True):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget(self)

        self.overview_page = ProjectsOverviewPage(self.repo, is_dark=self.is_dark, parent=self)
        self.detail_page = ProjectDetailPage(self.repo, is_dark=self.is_dark, parent=self)

        self.stack.addWidget(self.overview_page)
        self.stack.addWidget(self.detail_page)

        layout.addWidget(self.stack)

        # Wire Signals
        self.overview_page.project_selected.connect(self._show_detail)
        self.overview_page.new_project_clicked.connect(self._create_new_project)
        self.detail_page.back_clicked.connect(self._show_overview)
        self.detail_page.project_updated.connect(self._on_project_updated)

        self.apply_theme()

    def _show_detail(self, project_name: str) -> None:
        self.detail_page.load_project(project_name)
        self.stack.setCurrentWidget(self.detail_page)

    def _show_overview(self) -> None:
        self.overview_page.refresh()
        self.stack.setCurrentWidget(self.overview_page)

    def _on_project_updated(self) -> None:
        self.overview_page.refresh()
        self.project_changed.emit()

    def _create_new_project(self) -> None:
        dlg = ProjectDialog(self, is_dark=self.is_dark)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, color, desc, kws = dlg.get_data()
            self.repo.create_or_update_project(name, kws, color=color, description=desc)
            self.overview_page.refresh()
            self.project_changed.emit()

    def load_data(self) -> None:
        """Refresh dashboard view data."""
        if self.stack.currentWidget() == self.detail_page:
            self.detail_page.load_project(self.detail_page.current_project_name)
        else:
            self.overview_page.refresh()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.overview_page.set_theme(is_dark)
        self.detail_page.set_theme(is_dark)
        self.apply_theme()

    def apply_theme(self) -> None:
        self.setStyleSheet("background: transparent;")
