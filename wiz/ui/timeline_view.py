"""Dedicated chronological activity timeline view for WizDesk."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtCore import Qt, QSize, QPointF
from PyQt6.QtGui import QFont, QPainter, QPolygonF, QColor, QBrush
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFrame,
    QSizePolicy,
)

from wiz.storage.models import StorageRepository
from wiz.ui.icons import get_app_pixmap


def format_duration(minutes: float) -> str:
    """Format minutes into human readable string (e.g., 2h 15m or 45m)."""
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


class ResponsiveProjectCombo(QComboBox):
    """Compact combobox badge that dynamically hugs its current text with a crisp down arrow."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._is_dark: bool = True
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.currentIndexChanged.connect(lambda: self.updateGeometry())

    def set_theme(self, is_dark: bool) -> None:
        self._is_dark = is_dark
        self.update()

    def sizeHint(self) -> QSize:
        base_hint = super().sizeHint()
        text_w = self.fontMetrics().horizontalAdvance(self.currentText())
        # Snug content width: 10px left pad + text + 8px gap + 7px arrow + 10px right pad
        w = max(76, text_w + 35)
        return QSize(w, base_hint.height())

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        arrow_color = QColor("#A1A1AA") if self._is_dark else QColor("#71717A")

        w = self.width()
        h = self.height()
        arrow_w = 7.0
        arrow_h = 4.5
        center_x = w - 11.0
        center_y = h / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(arrow_color))
        poly = QPolygonF([
            QPointF(center_x - arrow_w / 2.0, center_y - arrow_h / 2.0),
            QPointF(center_x + arrow_w / 2.0, center_y - arrow_h / 2.0),
            QPointF(center_x, center_y + arrow_h / 2.0),
        ])
        painter.drawPolygon(poly)
        painter.end()


class AppSessionCard(QFrame):
    """Card displaying a contiguous application tracking block."""

    def __init__(self, session: Dict[str, Any], is_dark: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._init_ui(session)

    def _init_ui(self, session: Dict[str, Any]) -> None:
        self.setObjectName("AppSessionCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Left Column: Time & Duration
        left_box = QVBoxLayout()
        left_box.setSpacing(2)
        left_box.setContentsMargins(0, 0, 0, 0)

        start_time_str = session["start_time"].strftime("%H:%M")
        end_time_str = session["end_time"].strftime("%H:%M")
        time_label = QLabel(f"{start_time_str} - {end_time_str}", self)
        time_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))

        duration_str = format_duration(session.get("duration_minutes", 0.0))
        dur_label = QLabel(duration_str, self)
        dur_label.setFont(QFont("Segoe UI", 9))

        left_box.addWidget(time_label)
        left_box.addWidget(dur_label)
        layout.addLayout(left_box, 0)

        # Middle Column: App name and window title
        mid_box = QVBoxLayout()
        mid_box.setSpacing(3)
        mid_box.setContentsMargins(0, 0, 0, 0)

        app_name = session.get("app_name") or "Unknown"
        app_label = QLabel(app_name, self)
        app_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        window_title = session.get("window_title") or ""
        if len(window_title) > 65:
            window_title = window_title[:62] + "..."
        win_label = QLabel(window_title, self)
        win_label.setFont(QFont("Segoe UI", 9))
        win_label.setWordWrap(False)

        mid_box.addWidget(app_label)
        mid_box.addWidget(win_label)
        layout.addLayout(mid_box, 1)

        # Right Column: Project Tag Pill
        project_tag = session.get("project_tag")
        if project_tag:
            tag_label = QLabel(f"[{project_tag}]", self)
            tag_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tag_label.setObjectName("ProjectPill")
            layout.addWidget(tag_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self._apply_style(time_label, dur_label, app_label, win_label)

    def _apply_style(
        self,
        time_lbl: QLabel,
        dur_lbl: QLabel,
        app_lbl: QLabel,
        win_lbl: QLabel,
    ) -> None:
        if self.is_dark:
            self.setStyleSheet(
                """
                QFrame#AppSessionCard {
                    background-color: #242427;
                    border: 1px solid #333338;
                    border-radius: 8px;
                }
                QLabel#ProjectPill {
                    background-color: #2E2E33;
                    color: #A1A1AA;
                    border: 1px solid #3F3F46;
                    border-radius: 4px;
                    padding: 2px 8px;
                }
                """
            )
            time_lbl.setStyleSheet("color: #F4F4F6;")
            dur_lbl.setStyleSheet("color: #71717A;")
            app_lbl.setStyleSheet("color: #FFFFFF;")
            win_lbl.setStyleSheet("color: #A1A1AA;")
        else:
            self.setStyleSheet(
                """
                QFrame#AppSessionCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E2DDD2;
                    border-radius: 8px;
                }
                QLabel#ProjectPill {
                    background-color: #EBE6DC;
                    color: #555550;
                    border: 1px solid #DCD6CA;
                    border-radius: 4px;
                    padding: 2px 8px;
                }
                """
            )
            time_lbl.setStyleSheet("color: #111111;")
            dur_lbl.setStyleSheet("color: #777770;")
            app_lbl.setStyleSheet("color: #111111;")
            win_lbl.setStyleSheet("color: #666660;")


class MilestoneCard(QFrame):
    """Card displaying a task completion or note milestone."""

    def __init__(self, event: Dict[str, Any], is_dark: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._init_ui(event)

    def _init_ui(self, event: Dict[str, Any]) -> None:
        self.setObjectName("MilestoneCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Left: Timestamp
        time_box = QVBoxLayout()
        time_box.setSpacing(2)
        time_box.setContentsMargins(0, 0, 0, 0)

        ts = event["timestamp"]
        ts_str = ts.strftime("%H:%M") if isinstance(ts, datetime) else str(ts)[:5]
        time_label = QLabel(ts_str, self)
        time_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))

        event_type = event.get("event_type", "task")
        type_str = "[COMPLETED]" if event_type == "task" else "[NOTE]"
        type_badge = QLabel(type_str, self)
        type_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        type_badge.setObjectName("TypeBadge")

        time_box.addWidget(time_label)
        time_box.addWidget(type_badge)
        layout.addLayout(time_box, 0)

        # Middle: Title and context
        mid_box = QVBoxLayout()
        mid_box.setSpacing(2)
        mid_box.setContentsMargins(0, 0, 0, 0)

        title_text = event.get("title") or ""
        title_label = QLabel(title_text, self)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        title_label.setWordWrap(True)

        subtitle_text = event.get("subtitle") or ""
        subtitle_label = QLabel(subtitle_text, self)
        subtitle_label.setFont(QFont("Segoe UI", 9))

        mid_box.addWidget(title_label)
        if subtitle_text:
            mid_box.addWidget(subtitle_label)
        layout.addLayout(mid_box, 1)

        # Right: Project Pill if available
        project_tag = event.get("project_tag")
        if project_tag:
            proj_label = QLabel(f"[{project_tag}]", self)
            proj_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            proj_label.setObjectName("ProjectPill")
            layout.addWidget(proj_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self._apply_style(time_label, type_badge, title_label, subtitle_label, event_type)

    def _apply_style(
        self,
        time_lbl: QLabel,
        type_badge: QLabel,
        title_lbl: QLabel,
        sub_lbl: QLabel,
        event_type: str,
    ) -> None:
        if self.is_dark:
            border_color = "#384E3A" if event_type == "task" else "#4A3F2C"
            type_color = "#4ADE80" if event_type == "task" else "#FBBF24"
            self.setStyleSheet(
                f"""
                QFrame#MilestoneCard {{
                    background-color: #242427;
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
                QLabel#ProjectPill {{
                    background-color: #2E2E33;
                    color: #A1A1AA;
                    border: 1px solid #3F3F46;
                    border-radius: 4px;
                    padding: 2px 8px;
                }}
                """
            )
            time_lbl.setStyleSheet("color: #F4F4F6;")
            type_badge.setStyleSheet(f"color: {type_color};")
            title_lbl.setStyleSheet("color: #FFFFFF;")
            sub_lbl.setStyleSheet("color: #71717A;")
        else:
            border_color = "#C8E6C9" if event_type == "task" else "#FFE082"
            type_color = "#2E7D32" if event_type == "task" else "#E65100"
            self.setStyleSheet(
                f"""
                QFrame#MilestoneCard {{
                    background-color: #FFFFFF;
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
                QLabel#ProjectPill {{
                    background-color: #EBE6DC;
                    color: #555550;
                    border: 1px solid #DCD6CA;
                    border-radius: 4px;
                    padding: 2px 8px;
                }}
                """
            )
            time_lbl.setStyleSheet("color: #111111;")
            type_badge.setStyleSheet(f"color: {type_color};")
            title_lbl.setStyleSheet("color: #111111;")
            sub_lbl.setStyleSheet("color: #666660;")


class EmptyStateCard(QFrame):
    """Centered empty state when no activity exists for a day."""

    def __init__(self, is_dark: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("EmptyStateCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 40)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(self)
        pix = get_app_pixmap(size=56, asset_name="wiz-idle.svg")
        icon_label.setPixmap(pix)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel("No activity recorded for this date", self)
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Active application sessions and completed tasks will appear here as you work.", self)
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        if self.is_dark:
            self.setStyleSheet("background: transparent; border: none;")
            title.setStyleSheet("color: #F4F4F6;")
            subtitle.setStyleSheet("color: #71717A;")
        else:
            self.setStyleSheet("background: transparent; border: none;")
            title.setStyleSheet("color: #111111;")
            subtitle.setStyleSheet("color: #777770;")


class TimelineView(QWidget):
    """
    Dedicated view component displaying chronological work logs,
    contiguous application sessions, and task milestones.
    """

    def __init__(self, repo: StorageRepository, is_dark: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.current_date_str: str = datetime.now().strftime("%Y-%m-%d")

        self._category_filter: str = "all"  # 'all' | 'apps' | 'tasks' | 'notes'
        self._project_filter: str = "all"   # 'all' | specific project tag | 'untagged'

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 4, 0, 0)
        main_layout.setSpacing(8)

        # 1. Top Metrics Strip (individual badges)
        self.metrics_bar = QFrame(self)
        self.metrics_bar.setObjectName("MetricsBar")
        metrics_layout = QHBoxLayout(self.metrics_bar)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(8)

        self.lbl_metric_time = QLabel("Tracked: 0m", self.metrics_bar)
        self.lbl_metric_time.setObjectName("MetricBadge")
        self.lbl_metric_time.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))

        self.lbl_metric_tasks = QLabel("Completed: 0 tasks", self.metrics_bar)
        self.lbl_metric_tasks.setObjectName("MetricBadge")
        self.lbl_metric_tasks.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))

        self.lbl_metric_apps = QLabel("Apps: 0", self.metrics_bar)
        self.lbl_metric_apps.setObjectName("MetricBadge")
        self.lbl_metric_apps.setFont(QFont("Segoe UI", 9))

        metrics_layout.addWidget(self.lbl_metric_time)
        metrics_layout.addWidget(self.lbl_metric_tasks)
        metrics_layout.addWidget(self.lbl_metric_apps)
        metrics_layout.addStretch(1)

        main_layout.addWidget(self.metrics_bar)

        # 2. Filter Bar (Category Chips + Project Dropdown)
        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(0, 0, 0, 0)
        filter_bar.setSpacing(6)

        self.btn_all = QPushButton("All", self)
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self._set_category_filter("all"))

        self.btn_apps = QPushButton("Apps", self)
        self.btn_apps.setCheckable(True)
        self.btn_apps.clicked.connect(lambda: self._set_category_filter("apps"))

        self.btn_tasks = QPushButton("Tasks", self)
        self.btn_tasks.setCheckable(True)
        self.btn_tasks.clicked.connect(lambda: self._set_category_filter("tasks"))

        self.btn_notes = QPushButton("Quick Notes", self)
        self.btn_notes.setCheckable(True)
        self.btn_notes.clicked.connect(lambda: self._set_category_filter("notes"))

        filter_bar.addWidget(self.btn_all)
        filter_bar.addWidget(self.btn_apps)
        filter_bar.addWidget(self.btn_tasks)
        filter_bar.addWidget(self.btn_notes)
        filter_bar.addStretch(1)

        self.project_combo = ResponsiveProjectCombo(self)
        self.project_combo.addItem("All Projects")
        self.project_combo.currentIndexChanged.connect(self._on_project_filter_changed)
        filter_bar.addWidget(self.project_combo)

        main_layout.addLayout(filter_bar)

        # 3. Scroll Area for Events
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("TimelineScrollArea")

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.events_layout = QVBoxLayout(self.scroll_content)
        self.events_layout.setContentsMargins(0, 4, 4, 12)
        self.events_layout.setSpacing(8)
        self.events_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.apply_theme()

    def set_theme(self, is_dark: bool) -> None:
        """Update theme mode and refresh view components."""
        self.is_dark = is_dark
        self.apply_theme()
        self.load_date(self.current_date_str)

    def apply_theme(self) -> None:
        """Apply styles for Light or Dark theme."""
        if self.is_dark:
            self.metrics_bar.setStyleSheet(
                """
                QFrame#MetricsBar {
                    background: transparent;
                    border: none;
                }
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
            )
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
            combo_style = """
                QComboBox {
                    background-color: #242427;
                    color: #F4F4F6;
                    border: 1px solid #3F3F46;
                    border-radius: 6px;
                    padding: 4px 20px 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 0px;
                }
                QComboBox QAbstractItemView {
                    background-color: #242427;
                    color: #F4F4F6;
                    selection-background-color: #3F3F46;
                    border: 1px solid #3F3F46;
                    min-width: 130px;
                }
            """
            scroll_style = """
                QScrollArea#TimelineScrollArea { background: transparent; }
                QWidget#ScrollContent { background: transparent; }
            """
        else:
            self.metrics_bar.setStyleSheet(
                """
                QFrame#MetricsBar {
                    background: transparent;
                    border: none;
                }
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
            )
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
            combo_style = """
                QComboBox {
                    background-color: #FFFFFF;
                    color: #111111;
                    border: 1px solid #DCD6CA;
                    border-radius: 6px;
                    padding: 4px 20px 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 0px;
                }
                QComboBox QAbstractItemView {
                    background-color: #FFFFFF;
                    color: #111111;
                    selection-background-color: #EBE6DC;
                    border: 1px solid #DCD6CA;
                    min-width: 130px;
                }
            """
            scroll_style = """
                QScrollArea#TimelineScrollArea { background: transparent; }
                QWidget#ScrollContent { background: transparent; }
            """

        self.btn_all.setStyleSheet(chip_style)
        self.btn_apps.setStyleSheet(chip_style)
        self.btn_tasks.setStyleSheet(chip_style)
        self.btn_notes.setStyleSheet(chip_style)
        self.project_combo.set_theme(self.is_dark)
        self.project_combo.setStyleSheet(combo_style)
        self.scroll_area.setStyleSheet(scroll_style)

    def _set_category_filter(self, category: str) -> None:
        """Handle category filter switch."""
        self._category_filter = category
        self.btn_all.setChecked(category == "all")
        self.btn_apps.setChecked(category == "apps")
        self.btn_tasks.setChecked(category == "tasks")
        self.btn_notes.setChecked(category == "notes")
        self._render_timeline()

    def _on_project_filter_changed(self) -> None:
        """Handle project dropdown selection."""
        current_text = self.project_combo.currentText()
        if current_text == "All Projects":
            self._project_filter = "all"
        elif current_text == "Untagged":
            self._project_filter = "untagged"
        else:
            self._project_filter = current_text
        self._render_timeline()

    def load_date(self, date_str: str) -> None:
        """Load and display activity timeline for the given date (YYYY-MM-DD)."""
        self.current_date_str = date_str
        self._refresh_project_dropdown()
        self._refresh_metrics()
        self._render_timeline()

    def _refresh_project_dropdown(self) -> None:
        """Update project combo options based on available projects."""
        current_sel = self.project_combo.currentText()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem("All Projects")

        # Get projects from database
        try:
            projects = self.repo.get_all_projects()
            for p in projects:
                self.project_combo.addItem(p.name)
        except Exception:
            pass

        self.project_combo.addItem("Untagged")

        # Restore selection if still present
        idx = self.project_combo.findText(current_sel)
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)
        else:
            self.project_combo.setCurrentIndex(0)
            self._project_filter = "all"
        self.project_combo.blockSignals(False)

    def _refresh_metrics(self) -> None:
        """Update top metrics badges."""
        metrics = self.repo.get_day_metrics(self.current_date_str)
        dur_str = format_duration(metrics.get("total_tracked_minutes", 0.0))
        tasks_count = metrics.get("completed_tasks_count", 0)
        apps_count = metrics.get("unique_apps_count", 0)

        self.lbl_metric_time.setText(f"Tracked: {dur_str}")
        self.lbl_metric_tasks.setText(f"Completed: {tasks_count} tasks")
        self.lbl_metric_apps.setText(f"Apps: {apps_count}")

    def _render_timeline(self) -> None:
        """Fetch, filter, and render timeline event cards."""
        # 1. Clear existing cards
        while self.events_layout.count() > 0:
            item = self.events_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # 2. Fetch unified events
        events = self.repo.get_day_timeline_events(self.current_date_str)

        # 3. Apply Filters
        filtered: List[Dict[str, Any]] = []
        for ev in events:
            # Category filter
            if self._category_filter == "apps" and ev["event_type"] != "session":
                continue
            if self._category_filter == "tasks" and ev["event_type"] != "task":
                continue
            if self._category_filter == "notes" and ev["event_type"] != "note":
                continue

            # Project filter
            proj = ev.get("project_tag")
            if self._project_filter != "all":
                if self._project_filter == "untagged" and proj:
                    continue
                if self._project_filter != "untagged" and (not proj or proj.lower() != self._project_filter.lower()):
                    continue

            filtered.append(ev)

        # 4. Render Empty State or Cards
        if not filtered:
            empty_card = EmptyStateCard(is_dark=self.is_dark, parent=self.scroll_content)
            self.events_layout.addWidget(empty_card)
            return

        for ev in filtered:
            if ev["event_type"] == "session":
                card = AppSessionCard(ev["raw"], is_dark=self.is_dark, parent=self.scroll_content)
                self.events_layout.addWidget(card)
            else:
                card = MilestoneCard(ev, is_dark=self.is_dark, parent=self.scroll_content)
                self.events_layout.addWidget(card)
