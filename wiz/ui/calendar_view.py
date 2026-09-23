"""Calendar and Scheduling view for WizDesk.

Provides a dedicated two-pane layout:
1. Left Pane (~250px): Interactive Month Calendar grid with dot indicators (Orange = active, Emerald = completed),
   month navigation (<, >), and quick jump presets (Today, Upcoming 7 Days, Overdue).
2. Right Pane (~500px+): Scheduled Agenda showing tasks for the selected date or preset,
   with inline fast task scheduling (+ Add task for this day...), full TaskRowWidget interaction,
   and clean typography with zero emojis.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import calendar

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QRectF, QSize
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QCursor,
    QMouseEvent,
    QPaintEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    QComboBox,
    QSizePolicy,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.storage.models import StorageRepository, TaskRecord
from wiz.ui.icons import get_status_icon
from wiz.ui.fonts import FONT_SANS, FONT_MONO, get_font
from wiz.ui.arrow_combo import ArrowComboBox


class MonthCalendarGridWidget(QWidget):
    """Custom-rendered monthly calendar grid with dot status indicators for scheduled tasks."""

    date_selected = pyqtSignal(date)

    def __init__(self, selected_date: date, parent: Optional[QWidget] = None, is_dark: bool = True):
        super().__init__(parent)
        self.current_year = selected_date.year
        self.current_month = selected_date.month
        self.selected_date = selected_date
        self.is_dark = is_dark
        self.date_status_map: Dict[str, str] = {}  # "YYYY-MM-DD" -> "active" | "completed"
        self._cell_rects: Dict[date, QRectF] = {}

        self.setFixedHeight(210)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def set_month(self, year: int, month: int, date_status_map: Optional[Dict[str, str]] = None) -> None:
        """Update active year and month and refresh."""
        self.current_year = year
        self.current_month = month
        if date_status_map is not None:
            self.date_status_map = date_status_map
        self.update()

    def set_selected_date(self, target_date: date) -> None:
        """Select a date and trigger repaint."""
        self.selected_date = target_date
        self.current_year = target_date.year
        self.current_month = target_date.month
        self.update()

    def set_dark_mode(self, is_dark: bool) -> None:
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for d, rect in self._cell_rects.items():
                if rect.contains(pos):
                    self.selected_date = d
                    self.update()
                    self.date_selected.emit(d)
                    return
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        col_w = w / 7.0
        header_h = 24.0
        row_h = (h - header_h) / 6.0

        # Colors
        header_text_color = QColor("#71717A" if self.is_dark else "#A1A1AA")
        day_text_color = QColor("#E4E4E7" if self.is_dark else "#27272A")
        dim_text_color = QColor("#3F3F46" if self.is_dark else "#D4D4D8")
        today_border_color = QColor("#FF6B3D")
        selected_bg_color = QColor("#FF6B3D")
        selected_text_color = QColor("#FFFFFF")
        dot_active_color = QColor("#FF6B3D")
        dot_completed_color = QColor("#10B981")

        # 1. Weekday headers (Mo, Tu, We, Th, Fr, Sa, Su)
        weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        painter.setFont(get_font(9, QFont.Weight.DemiBold))
        painter.setPen(header_text_color)
        for i, day_name in enumerate(weekdays):
            r = QRectF(i * col_w, 0, col_w, header_h)
            painter.drawText(r, int(Qt.AlignmentFlag.AlignCenter), day_name)

        # 2. Month days grid
        self._cell_rects.clear()
        cal = calendar.Calendar(firstweekday=0)  # 0 = Monday
        month_days = list(cal.itermonthdates(self.current_year, self.current_month))

        today_dt = date.today()
        painter.setFont(get_font(9, QFont.Weight.Medium))

        row = 0
        col = 0
        for d in month_days:
            if row >= 6:
                break
            x = col * col_w
            y = header_h + row * row_h
            cell_rect = QRectF(x, y, col_w, row_h)
            is_current_month = (d.month == self.current_month)

            if is_current_month:
                self._cell_rects[d] = cell_rect

            # Draw day cell
            is_selected = (d == self.selected_date and is_current_month)
            is_today = (d == today_dt)
            d_str = d.strftime("%Y-%m-%d")
            has_tasks = d_str in self.date_status_map

            # Selection Pill or Today Ring
            pill_size = min(col_w - 4, row_h - 4, 26.0)
            pill_rect = QRectF(
                cell_rect.center().x() - pill_size / 2.0,
                cell_rect.center().y() - pill_size / 2.0 - 1.0,
                pill_size,
                pill_size,
            )

            if is_selected:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(selected_bg_color)
                painter.drawRoundedRect(pill_rect, 6.0, 6.0)
                painter.setPen(selected_text_color)
            elif is_today and is_current_month:
                painter.setPen(today_border_color)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(pill_rect, 6.0, 6.0)
                painter.setPen(day_text_color)
            elif is_current_month:
                painter.setPen(day_text_color)
            else:
                painter.setPen(dim_text_color)

            # Draw day number text
            text_rect = QRectF(cell_rect.x(), cell_rect.y(), col_w, row_h - 4.0)
            painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignCenter), str(d.day))

            # Draw status dot if day has scheduled tasks
            if has_tasks and is_current_month:
                status = self.date_status_map.get(d_str, "active")
                dot_color = dot_completed_color if status == "completed" else dot_active_color
                if is_selected:
                    dot_color = QColor("#FFFFFF")
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(dot_color)
                dot_r = 2.0
                dot_y = cell_rect.bottom() - 4.0
                painter.drawEllipse(QRectF(cell_rect.center().x() - dot_r, dot_y - dot_r, dot_r * 2, dot_r * 2))

            col += 1
            if col == 7:
                col = 0
                row += 1

        painter.end()


class CalendarView(QWidget):
    """Dedicated Calendar and Schedule View for WizDesk."""

    task_created = pyqtSignal(int)
    task_updated = pyqtSignal(int)

    def __init__(self, repo: StorageRepository, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.selected_date = date.today()
        self.active_preset: Optional[str] = None  # None (specific date), "upcoming", "overdue"

        self._init_ui()
        self.load_data()

    def _init_ui(self) -> None:
        """Build the master-detail two-pane layout."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # -------------------------------------------------------------
        # Left Pane: Month Navigator, Grid, and Quick Presets (~250px)
        # -------------------------------------------------------------
        self.left_pane = QWidget(self)
        self.left_pane.setFixedWidth(250)
        left_layout = QVBoxLayout(self.left_pane)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        # 1. Month Navigation Header: [ < ] Month Year [ > ] + Today
        month_nav_layout = QHBoxLayout()
        month_nav_layout.setContentsMargins(0, 0, 0, 0)
        month_nav_layout.setSpacing(6)

        self.prev_month_btn = QPushButton("‹")
        self.prev_month_btn.setFixedSize(26, 26)
        self.prev_month_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_month_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prev_month_btn.clicked.connect(self._on_prev_month)
        month_nav_layout.addWidget(self.prev_month_btn)

        self.month_label = QLabel()
        self.month_label.setFont(get_font(11, QFont.Weight.Bold))
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        month_nav_layout.addWidget(self.month_label, stretch=1)

        self.next_month_btn = QPushButton("›")
        self.next_month_btn.setFixedSize(26, 26)
        self.next_month_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_month_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.next_month_btn.clicked.connect(self._on_next_month)
        month_nav_layout.addWidget(self.next_month_btn)

        left_layout.addLayout(month_nav_layout)

        # 2. Interactive Month Calendar Grid
        self.grid_widget = MonthCalendarGridWidget(self.selected_date, parent=self.left_pane, is_dark=self.is_dark)
        self.grid_widget.date_selected.connect(self._on_grid_date_selected)
        left_layout.addWidget(self.grid_widget)

        # 3. Subtle horizontal separator
        left_sep = QFrame()
        left_sep.setFrameShape(QFrame.Shape.HLine)
        left_sep.setFixedHeight(1)
        self.left_sep = left_sep
        left_layout.addWidget(left_sep)

        # 4. Quick Views Header & Preset Buttons
        views_lbl = QLabel("QUICK VIEWS")
        views_lbl.setFont(get_font(8, QFont.Weight.Bold))
        self.views_lbl = views_lbl
        left_layout.addWidget(views_lbl)

        presets_layout = QVBoxLayout()
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(5)

        self.btn_today_preset = QPushButton("Today")
        self.btn_today_preset.setFixedHeight(30)
        self.btn_today_preset.setFont(get_font(10, QFont.Weight.Medium))
        self.btn_today_preset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_today_preset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_today_preset.clicked.connect(self._on_select_today_preset)
        presets_layout.addWidget(self.btn_today_preset)

        self.btn_upcoming_preset = QPushButton("Upcoming (7 Days)")
        self.btn_upcoming_preset.setFixedHeight(30)
        self.btn_upcoming_preset.setFont(get_font(10, QFont.Weight.Medium))
        self.btn_upcoming_preset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_upcoming_preset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_upcoming_preset.clicked.connect(self._on_select_upcoming_preset)
        presets_layout.addWidget(self.btn_upcoming_preset)

        self.btn_overdue_preset = QPushButton("Overdue Tasks")
        self.btn_overdue_preset.setFixedHeight(30)
        self.btn_overdue_preset.setFont(get_font(10, QFont.Weight.Medium))
        self.btn_overdue_preset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_overdue_preset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_overdue_preset.clicked.connect(self._on_select_overdue_preset)
        presets_layout.addWidget(self.btn_overdue_preset)

        left_layout.addLayout(presets_layout)
        left_layout.addStretch()

        self.main_layout.addWidget(self.left_pane)

        # -------------------------------------------------------------
        # Vertical Divider
        # -------------------------------------------------------------
        self.v_divider = QFrame()
        self.v_divider.setFrameShape(QFrame.Shape.VLine)
        self.v_divider.setFixedWidth(1)
        self.main_layout.addWidget(self.v_divider)

        # -------------------------------------------------------------
        # Right Pane: Scheduled Agenda & Task Creation (~500px+)
        # -------------------------------------------------------------
        self.right_pane = QWidget(self)
        right_layout = QVBoxLayout(self.right_pane)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        # 1. Agenda Header (Date title + count badge)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.agenda_title = QLabel()
        self.agenda_title.setFont(get_font(13, QFont.Weight.Bold))
        header_row.addWidget(self.agenda_title)

        self.task_count_badge = QLabel()
        self.task_count_badge.setFont(get_font(9, QFont.Weight.DemiBold))
        self.task_count_badge.setFixedHeight(20)
        header_row.addWidget(self.task_count_badge)

        header_row.addStretch()
        right_layout.addLayout(header_row)

        # 2. Inline Fast Task Scheduling Bar
        self.add_bar_container = QWidget(self.right_pane)
        add_bar_layout = QHBoxLayout(self.add_bar_container)
        add_bar_layout.setContentsMargins(0, 0, 0, 0)
        add_bar_layout.setSpacing(8)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("+ Add task for this day... (Press Enter)")
        self.add_input.setFixedHeight(34)
        self.add_input.setFont(get_font(10))
        self.add_input.returnPressed.connect(self._on_submit_task)
        add_bar_layout.addWidget(self.add_input, stretch=1)

        self.section_combo = ArrowComboBox()
        self.section_combo.setFixedHeight(34)
        self.section_combo.setFixedWidth(140)
        self.section_combo.setFont(get_font(10))
        add_bar_layout.addWidget(self.section_combo)

        self.add_btn = QPushButton("Schedule")
        self.add_btn.setFixedHeight(34)
        self.add_btn.setFixedWidth(80)
        self.add_btn.setFont(get_font(10, QFont.Weight.Bold))
        self.add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_btn.clicked.connect(self._on_submit_task)
        add_bar_layout.addWidget(self.add_btn)

        right_layout.addWidget(self.add_bar_container)

        # 3. Task List Scroll Area
        self.scroll_area = QScrollArea(self.right_pane)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.task_list_container = QWidget()
        self.task_list_layout = QVBoxLayout(self.task_list_container)
        self.task_list_layout.setContentsMargins(0, 4, 0, 4)
        self.task_list_layout.setSpacing(6)
        self.task_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.task_list_container)
        right_layout.addWidget(self.scroll_area, stretch=1)

        # 4. Empty State Label
        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFont(get_font(11))
        self.empty_label.hide()
        right_layout.addWidget(self.empty_label)

        self.main_layout.addWidget(self.right_pane, stretch=1)

        self._apply_theme()

    def set_dark_mode(self, is_dark: bool) -> None:
        """Switch dark / light mode styles."""
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.grid_widget.set_dark_mode(is_dark)
            self._apply_theme()
            self._refresh_agenda()

    def _apply_theme(self) -> None:
        """Apply CSS styling matching WizDesk palette."""
        bg_pane = "#18181B" if self.is_dark else "#FAF8F5"
        border_color = "#27272A" if self.is_dark else "#E4E4E7"
        text_primary = "#FAFAFA" if self.is_dark else "#18181B"
        text_muted = "#71717A" if self.is_dark else "#A1A1AA"
        btn_nav_bg = "#27272A" if self.is_dark else "#E4E4E7"
        btn_nav_hover = "#3F3F46" if self.is_dark else "#D4D4D8"

        self.setStyleSheet(f"""
            QWidget#CalendarView {{
                background-color: transparent;
            }}
        """)

        # Left pane background
        self.left_pane.setStyleSheet(f"""
            background-color: {bg_pane};
            border-top-left-radius: 12px;
            border-bottom-left-radius: 12px;
        """)

        self.month_label.setStyleSheet(f"color: {text_primary};")
        self.views_lbl.setStyleSheet(f"color: {text_muted}; letter-spacing: 0.5px; padding-left: 2px;")
        self.left_sep.setStyleSheet(f"background-color: {border_color};")
        self.v_divider.setStyleSheet(f"background-color: {border_color};")

        nav_btn_qss = f"""
            QPushButton {{
                background-color: {btn_nav_bg};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_nav_hover};
            }}
        """
        self.prev_month_btn.setStyleSheet(nav_btn_qss)
        self.next_month_btn.setStyleSheet(nav_btn_qss)

        # Preset buttons styling
        self._update_preset_button_styles()

        # Right pane styling
        self.right_pane.setStyleSheet("background-color: transparent;")
        self.agenda_title.setStyleSheet(f"color: {text_primary};")

        badge_bg = "#27272A" if self.is_dark else "#E4E4E7"
        badge_fg = "#A1A1AA" if self.is_dark else "#52525B"
        self.task_count_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border-radius: 10px;
            padding: 2px 8px;
        """)

        input_bg = "#27272A" if self.is_dark else "#EDE9E0"
        input_fg = "#F4F4F5" if self.is_dark else "#242220"
        input_border = "#3F3F46" if self.is_dark else "#D6D0C5"
        self.add_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_fg};
                border: 1px solid {input_border};
                border-radius: 6px;
                padding: 0 10px;
                font-family: {FONT_SANS};
            }}
            QLineEdit:focus {{
                border: 1.5px solid #FF6B3D;
            }}
        """)

        self.section_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {input_bg};
                color: {input_fg};
                border: 1px solid {input_border};
                border-radius: 6px;
                padding-left: 10px;
                padding-right: 24px;
                font-family: {FONT_SANS};
            }}
        """)

        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF6B3D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #E05326;
            }}
        """)

        self.empty_label.setStyleSheet(f"color: {text_muted}; padding: 40px 0;")

    def _update_preset_button_styles(self) -> None:
        """Update active/inactive styles of the quick preset buttons."""
        border_color = "#27272A" if self.is_dark else "#E4E4E7"
        text_primary = "#FAFAFA" if self.is_dark else "#18181B"
        text_muted = "#A1A1AA" if self.is_dark else "#71717A"
        active_bg = "#FF6B3D"
        active_fg = "#FFFFFF"

        presets = [
            ("today", self.btn_today_preset),
            ("upcoming", self.btn_upcoming_preset),
            ("overdue", self.btn_overdue_preset),
        ]

        for p_key, btn in presets:
            is_active = (self.active_preset == p_key) or (p_key == "today" and self.active_preset is None and self.selected_date == date.today())
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_bg};
                        color: {active_fg};
                        border: none;
                        border-radius: 6px;
                        text-align: left;
                        padding-left: 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {text_muted};
                        border: 1px solid transparent;
                        border-radius: 6px;
                        text-align: left;
                        padding-left: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {"#27272A" if self.is_dark else "#F4F0E8"};
                        color: {text_primary};
                    }}
                """)

    def load_data(self) -> None:
        """Full refresh of project dropdown, calendar month dots, and task agenda."""
        self._populate_sections()
        self._refresh_month_grid()
        self._refresh_agenda()

    def _populate_sections(self) -> None:
        """Populate project section combobox."""
        projects = self.repo.get_all_projects()
        names = [p.name for p in projects]
        if not names:
            names = ["Work", "Personal Projects"]

        cur = self.section_combo.currentText()
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        for name in names:
            self.section_combo.addItem(name)
        if cur and cur in names:
            self.section_combo.setCurrentText(cur)
        elif names:
            self.section_combo.setCurrentIndex(0)
        self.section_combo.blockSignals(False)

    def _refresh_month_grid(self) -> None:
        """Fetch dots for current month and update grid."""
        y = self.grid_widget.current_year
        m = self.grid_widget.current_month
        summary = self.repo.get_scheduled_summary_for_month(y, m)
        self.grid_widget.set_month(y, m, summary)

        # Update month label (e.g. September 2026)
        dt = date(y, m, 1)
        self.month_label.setText(dt.strftime("%B %Y"))

    def _on_prev_month(self) -> None:
        y = self.grid_widget.current_year
        m = self.grid_widget.current_month - 1
        if m < 1:
            m = 12
            y -= 1
        self.grid_widget.current_year = y
        self.grid_widget.current_month = m
        self._refresh_month_grid()

    def _on_next_month(self) -> None:
        y = self.grid_widget.current_year
        m = self.grid_widget.current_month + 1
        if m > 12:
            m = 1
            y += 1
        self.grid_widget.current_year = y
        self.grid_widget.current_month = m
        self._refresh_month_grid()

    def _on_grid_date_selected(self, target_date: date) -> None:
        """User clicked a date in the month grid."""
        self.selected_date = target_date
        self.active_preset = None
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _on_select_today_preset(self) -> None:
        """Preset shortcut: Today."""
        self.selected_date = date.today()
        self.active_preset = None
        self.grid_widget.set_selected_date(self.selected_date)
        self._refresh_month_grid()
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _on_select_upcoming_preset(self) -> None:
        """Preset shortcut: Upcoming."""
        self.active_preset = "upcoming"
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _on_select_overdue_preset(self) -> None:
        """Preset shortcut: Overdue."""
        self.active_preset = "overdue"
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _refresh_agenda(self) -> None:
        """Render the scheduled tasks according to the active date or preset."""
        # Clear existing items
        while self.task_list_layout.count() > 0:
            item = self.task_list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        # Query tasks based on active view mode
        if self.active_preset == "upcoming":
            self.agenda_title.setText("Upcoming Scheduled Tasks (Next 7 Days)")
            self.add_bar_container.hide()
            tasks = self.repo.get_task_hierarchy(status_filter="upcoming")
            empty_text = "No upcoming tasks scheduled for the next 7 days."
        elif self.active_preset == "overdue":
            self.agenda_title.setText("Overdue Tasks")
            self.add_bar_container.hide()
            tasks = self.repo.get_task_hierarchy(status_filter="unfinished")
            empty_text = "No overdue tasks! You're completely caught up."
        else:
            # Single day view
            is_today = (self.selected_date == date.today())
            date_str = self.selected_date.strftime("%B %d, %A")
            if is_today:
                date_str = f"Today — {date_str}"
            self.agenda_title.setText(date_str)
            self.add_bar_container.show()
            self.add_input.setPlaceholderText(f"+ Add task for {self.selected_date.strftime('%b %d')}... (Press Enter)")
            tasks = self.repo.get_task_hierarchy(target_date=self.selected_date, status_filter="task")
            empty_text = f"No tasks scheduled for {self.selected_date.strftime('%B %d')}."

        # Update counter badge
        count = len(tasks)
        self.task_count_badge.setText(f"{count} {'task' if count == 1 else 'tasks'}")

        # Render tasks
        if not tasks:
            self.empty_label.setText(empty_text)
            self.empty_label.show()
            self.scroll_area.hide()
        else:
            self.empty_label.hide()
            self.scroll_area.show()

            # Import TaskRowWidget safely inside method to avoid circular module imports
            from wiz.ui.popup_dialog import TaskRowWidget

            projects = [p.name for p in self.repo.get_all_projects()]
            if not projects:
                projects = ["Work", "Personal Projects"]

            for task in tasks:
                row = TaskRowWidget(task=task, all_projects=projects, is_dark=self.is_dark, parent=self.task_list_container)
                self._connect_task_row(row)
                self.task_list_layout.addWidget(row)

    def _connect_task_row(self, row) -> None:
        """Bind TaskRowWidget signals to storage updates and local refresh."""
        row.status_toggled.connect(self._on_row_status_changed)
        row.task_renamed.connect(self._on_row_task_renamed)
        row.project_changed.connect(self._on_row_project_changed)
        row.subtask_added.connect(self._on_row_subtask_added)
        row.subtask_toggled.connect(self._on_row_subtask_status_changed)
        row.subtask_deleted.connect(self._on_row_subtask_deleted)
        row.subtask_renamed.connect(self._on_row_subtask_renamed)
        row.schedule_changed.connect(self._on_row_schedule_changed)
        row.repeat_changed.connect(self._on_row_repeat_changed)

    def _on_row_status_changed(self, task_id: int, new_status: str) -> None:
        self.repo.update_task_status(task_id, new_status)
        self.task_updated.emit(task_id)
        app_signals.task_updated.emit(task_id)
        self._refresh_month_grid()
        self._refresh_agenda()

    def _on_row_task_renamed(self, task_id: int, new_title: str) -> None:
        self.repo.update_task_title(task_id, new_title)
        self.task_updated.emit(task_id)
        app_signals.task_updated.emit(task_id)

    def _on_row_project_changed(self, task_id: int, new_project: str) -> None:
        self.repo.update_task_project(task_id, new_project)
        self.task_updated.emit(task_id)
        app_signals.task_updated.emit(task_id)

    def _on_row_subtask_added(self, task_id: int, title: str) -> None:
        self.repo.create_subtask(task_id, title)
        self.task_updated.emit(task_id)
        app_signals.task_updated.emit(task_id)
        self._refresh_agenda()

    def _on_row_subtask_status_changed(self, subtask_id: int, new_status: str) -> None:
        self.repo.update_subtask_status(subtask_id, new_status)
        app_signals.task_updated.emit(0)

    def _on_row_subtask_deleted(self, subtask_id: int) -> None:
        self.repo.delete_subtask(subtask_id)
        app_signals.task_updated.emit(0)
        self._refresh_agenda()

    def _on_row_subtask_renamed(self, subtask_id: int, new_title: str) -> None:
        self.repo.update_subtask_title(subtask_id, new_title)
        app_signals.task_updated.emit(0)

    def _on_row_schedule_changed(self, task_id: int, new_date_str: str) -> None:
        self.repo.update_task_schedule(task_id, new_date_str if new_date_str else None)
        self.task_updated.emit(task_id)
        app_signals.task_updated.emit(task_id)
        self._refresh_month_grid()
        self._refresh_agenda()

    def _on_row_repeat_changed(self, task_id: int, new_repeat: str) -> None:
        self.repo.update_task_repeat(task_id, new_repeat)
        self.task_updated.emit(task_id)
        app_signals.task_updated.emit(task_id)

    def _on_submit_task(self) -> None:
        """Submit a new task pre-assigned to the selected date."""
        title = self.add_input.text().strip()
        if not title:
            return

        proj = self.section_combo.currentText() or "Work"
        sched_date = self.selected_date.strftime("%Y-%m-%d")

        task_id = self.repo.create_task(
            title=title,
            project_tag=proj,
            scheduled_date=sched_date,
            repeat_mode="none",
        )
        self.add_input.clear()
        self._refresh_month_grid()
        self._refresh_agenda()
        self.task_created.emit(task_id)
        app_signals.task_created.emit(task_id)
