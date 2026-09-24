"""Calendar and Scheduling view for WizDesk.

Implements card-based borders matching WizDesk design standards:
1. Left Column (~285px):
   - Calendar Card: Rounded container holding month navigation and month grid.
   - Quick Views Card: Rounded container holding Today, Upcoming (7 Days), and Overdue Tasks presets.
2. Right Column (Agenda Card):
   - Rounded container with top header (Active Date / Preset + count badge),
     middle scrollable task list, and bottom-pinned scheduling add bar (matching Tasks & Notes).
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

        self.setFixedHeight(215)
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
                    event.accept()
                    return
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.accept()

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
        header_text_color = QColor("#71717A" if self.is_dark else "#78716C")
        day_text_color = QColor("#E4E4E7" if self.is_dark else "#242220")
        dim_text_color = QColor("#3F3F46" if self.is_dark else "#C8C2B6")
        today_border_color = QColor("#C2410C" if self.is_dark else "#BA3F1A")
        selected_bg_color = QColor("#C2410C" if self.is_dark else "#BA3F1A")
        selected_text_color = QColor("#FFFFFF")
        dot_active_color = QColor("#C2410C" if self.is_dark else "#BA3F1A")
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
            pill_size = min(col_w - 6, row_h - 4, 28.0)
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


class CategoryFilterButton(QPushButton):
    """Category filter button displaying project name and task count badge."""

    def __init__(self, name: str, count: int, is_active: bool, is_dark: bool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.category_name = name
        self.count = count
        self.is_active = is_active
        self.is_dark = is_dark
        self.setFixedHeight(30)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(6)

        self.name_label = QLabel(name)
        self.name_label.setObjectName("catName")
        self.name_label.setFont(get_font(9, QFont.Weight.Medium))
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.name_label)

        layout.addStretch()

        self.count_badge = QLabel(str(count))
        self.count_badge.setObjectName("catCount")
        self.count_badge.setFont(get_font(8, QFont.Weight.Bold))
        self.count_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_badge.setFixedHeight(18)
        self.count_badge.setMinimumWidth(20)
        layout.addWidget(self.count_badge)

        self.update_appearance(count, is_active, is_dark)

    def update_appearance(self, count: int, is_active: bool, is_dark: bool) -> None:
        self.count = count
        self.is_active = is_active
        self.is_dark = is_dark
        self.count_badge.setText(str(count))

        text_primary = "#FAFAFA" if self.is_dark else "#242220"
        text_muted = "#A1A1AA" if self.is_dark else "#78716C"
        active_bg = "#C2410C" if self.is_dark else "#BA3F1A"

        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {active_bg};
                    border: none;
                    border-radius: 6px;
                }}
            """)
            self.name_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
            self.count_badge.setStyleSheet("""
                background-color: rgba(255, 255, 255, 0.28);
                color: #FFFFFF;
                border-radius: 9px;
                padding: 0 4px;
                border: none;
            """)
        else:
            hover_bg = "#27272A" if self.is_dark else "#EDE8DF"
            badge_bg = "#27272A" if self.is_dark else "#EDE8DF"
            badge_fg = "#A1A1AA" if self.is_dark else "#78716C"
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                }}
            """)
            self.name_label.setStyleSheet(f"color: {text_muted}; background: transparent; border: none;")
            self.count_badge.setStyleSheet(f"""
                background-color: {badge_bg};
                color: {badge_fg};
                border-radius: 9px;
                padding: 0 4px;
                border: none;
            """)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if not self.is_active:
            text_primary = "#FAFAFA" if self.is_dark else "#18181B"
            self.name_label.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if not self.is_active:
            text_muted = "#A1A1AA" if self.is_dark else "#71717A"
            self.name_label.setStyleSheet(f"color: {text_muted}; background: transparent; border: none;")


class CalendarView(QWidget):
    """Dedicated Calendar and Schedule View for WizDesk with card-based borders."""

    task_created = pyqtSignal(int)
    task_updated = pyqtSignal(int)

    def __init__(self, repo: StorageRepository, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.selected_date = date.today()
        self.active_preset: Optional[str] = None  # None (specific date), "upcoming", "overdue"
        self.selected_category_filter: Optional[str] = None  # None = "All"
        self.category_buttons: Dict[str, CategoryFilterButton] = {}

        self._init_ui()
        self.load_data()

    def _init_ui(self) -> None:
        """Build the card-based master-detail layout."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # Left Column (~275px): Calendar Card + Quick Views Card + Categories Card
        # -------------------------------------------------------------
        self.left_column = QWidget(self)
        self.left_column.setFixedWidth(275)
        left_col_layout = QVBoxLayout(self.left_column)
        left_col_layout.setContentsMargins(0, 0, 0, 0)
        left_col_layout.setSpacing(10)

        # 1. Calendar Card
        self.calendar_card = QFrame(self.left_column)
        self.calendar_card.setObjectName("calendarCard")
        cal_card_layout = QVBoxLayout(self.calendar_card)
        cal_card_layout.setContentsMargins(12, 12, 12, 12)
        cal_card_layout.setSpacing(10)

        # Month Navigation Header: [ < ] Month Year [ > ]
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

        cal_card_layout.addLayout(month_nav_layout)

        # Interactive Month Calendar Grid
        self.grid_widget = MonthCalendarGridWidget(self.selected_date, parent=self.calendar_card, is_dark=self.is_dark)
        self.grid_widget.date_selected.connect(self._on_grid_date_selected)
        cal_card_layout.addWidget(self.grid_widget)

        left_col_layout.addWidget(self.calendar_card)

        # 2. Quick Views Card
        self.quick_views_card = QFrame(self.left_column)
        self.quick_views_card.setObjectName("quickViewsCard")
        qv_card_layout = QVBoxLayout(self.quick_views_card)
        qv_card_layout.setContentsMargins(12, 12, 12, 12)
        qv_card_layout.setSpacing(6)

        views_lbl = QLabel("QUICK VIEWS")
        views_lbl.setFont(get_font(8, QFont.Weight.Bold))
        self.views_lbl = views_lbl
        qv_card_layout.addWidget(views_lbl)

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

        qv_card_layout.addLayout(presets_layout)

        left_col_layout.addWidget(self.quick_views_card)

        # 3. Project / Task Categories Card (Below Quick Views)
        self.categories_card = QFrame(self.left_column)
        self.categories_card.setObjectName("categoriesCard")
        cat_card_layout = QVBoxLayout(self.categories_card)
        cat_card_layout.setContentsMargins(12, 12, 12, 12)
        cat_card_layout.setSpacing(6)

        self.categories_lbl = QLabel("CATEGORIES")
        self.categories_lbl.setFont(get_font(8, QFont.Weight.Bold))
        cat_card_layout.addWidget(self.categories_lbl)

        self.cat_buttons_layout = QVBoxLayout()
        self.cat_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_buttons_layout.setSpacing(5)
        cat_card_layout.addLayout(self.cat_buttons_layout)
        cat_card_layout.addStretch()

        left_col_layout.addWidget(self.categories_card)
        left_col_layout.addStretch()

        self.main_layout.addWidget(self.left_column)

        # -------------------------------------------------------------
        # Right Column: Agenda Card (Header, Tasks list, Bottom Add Bar)
        # -------------------------------------------------------------
        self.agenda_card = QFrame(self)
        self.agenda_card.setObjectName("agendaCard")
        agenda_layout = QVBoxLayout(self.agenda_card)
        agenda_layout.setContentsMargins(14, 12, 14, 12)
        agenda_layout.setSpacing(10)

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
        agenda_layout.addLayout(header_row)

        # 2. Task List Scroll Area (Middle)
        self.scroll_area = QScrollArea(self.agenda_card)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.task_list_container = QWidget()
        self.task_list_layout = QVBoxLayout(self.task_list_container)
        self.task_list_layout.setContentsMargins(0, 2, 0, 2)
        self.task_list_layout.setSpacing(6)
        self.task_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.task_list_container)
        agenda_layout.addWidget(self.scroll_area, stretch=1)

        # Empty State Label (takes stretch=1 so bottom add bar stays statically pinned at the bottom)
        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFont(get_font(11))
        self.empty_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.empty_label.hide()
        agenda_layout.addWidget(self.empty_label, stretch=1)

        # 3. Bottom Task Scheduling Add Bar (Pinned at bottom like Tasks & Notes)
        self.add_bar_container = QWidget(self.agenda_card)
        add_bar_layout = QHBoxLayout(self.add_bar_container)
        add_bar_layout.setContentsMargins(0, 4, 0, 0)
        add_bar_layout.setSpacing(8)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("+ Add task for this day... (Press Enter)")
        self.add_input.setFixedHeight(34)
        self.add_input.setFont(get_font(10))
        self.add_input.returnPressed.connect(self._on_submit_task)
        add_bar_layout.addWidget(self.add_input, stretch=1)

        self.section_combo = ArrowComboBox(self.add_bar_container, is_dark=self.is_dark)
        self.section_combo.setFixedHeight(34)
        self.section_combo.setFixedWidth(130)
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

        agenda_layout.addWidget(self.add_bar_container)

        self.main_layout.addWidget(self.agenda_card, stretch=1)

        self._apply_theme()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def set_dark_mode(self, is_dark: bool) -> None:
        """Switch dark / light mode styles."""
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.grid_widget.set_dark_mode(is_dark)
            self._apply_theme()
            self._refresh_agenda()

    def _apply_theme(self) -> None:
        """Apply CSS styling matching WizDesk card and border palette."""
        card_bg = "#18181B" if self.is_dark else "#FAF8F5"
        card_border = "#27272A" if self.is_dark else "#DFD9CE"
        text_primary = "#FAFAFA" if self.is_dark else "#242220"
        text_muted = "#71717A" if self.is_dark else "#78716C"
        btn_nav_bg = "#27272A" if self.is_dark else "#EDE7DC"
        btn_nav_hover = "#3F3F46" if self.is_dark else "#E2DDD4"

        self.setStyleSheet(f"""
            QWidget#CalendarView {{
                background-color: transparent;
            }}
        """)

        card_qss = f"""
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: 12px;
        """
        self.calendar_card.setStyleSheet(f"QFrame#calendarCard {{ {card_qss} }}")
        self.quick_views_card.setStyleSheet(f"QFrame#quickViewsCard {{ {card_qss} }}")
        self.agenda_card.setStyleSheet(f"QFrame#agendaCard {{ {card_qss} }}")
        self.categories_card.setStyleSheet(f"QFrame#categoriesCard {{ {card_qss} }}")

        self.month_label.setStyleSheet(f"color: {text_primary}; border: none; background: transparent;")
        self.views_lbl.setStyleSheet(f"color: {text_muted}; letter-spacing: 0.5px; padding-left: 2px; border: none; background: transparent;")
        self.categories_lbl.setStyleSheet(f"color: {text_muted}; letter-spacing: 0.5px; padding-left: 2px; border: none; background: transparent;")

        for cat, btn in self.category_buttons.items():
            is_active = (self.selected_category_filter is None and cat == "All") or (self.selected_category_filter == cat)
            btn.update_appearance(btn.count, is_active, self.is_dark)

        nav_btn_qss = f"""
            QPushButton {{
                background-color: {btn_nav_bg};
                color: {text_primary};
                border: 1px solid {card_border};
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

        # Transparent containers inside cards
        self.left_column.setStyleSheet("background: transparent; border: none;")
        self.task_list_container.setStyleSheet("background: transparent; border: none;")
        self.add_bar_container.setStyleSheet("background: transparent; border: none;")

        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 0px;
                margin: 0px;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 0px;
                margin: 0px;
            }
        """)
        self.scroll_area.viewport().setStyleSheet("background-color: transparent; border: none;")

        # Preset buttons styling
        self._update_preset_button_styles()

        # Agenda header styling
        self.agenda_title.setStyleSheet(f"color: {text_primary}; border: none; background: transparent;")

        badge_bg = "#27272A" if self.is_dark else "#EDE8DF"
        badge_fg = "#A1A1AA" if self.is_dark else "#78716C"
        self.task_count_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border: none;
            border-radius: 10px;
            padding: 2px 8px;
        """)

        # Add bar inputs
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
                border: 1.5px solid {"#C2410C" if self.is_dark else "#BA3F1A"};
            }}
        """)

        self.section_combo.set_theme(self.is_dark)
        combo_popup_bg = "#18181B" if self.is_dark else "#FAF8F5"
        combo_popup_border = "#27272A" if self.is_dark else "#D6D0C5"
        combo_popup_sel_bg = "rgba(194, 65, 12, 0.22)" if self.is_dark else "#FEECE5"
        combo_popup_sel_text = "#FFAB91" if self.is_dark else "#BA3F1A"
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
            QComboBox:hover {{
                border: 1px solid {"#C2410C" if self.is_dark else "#BA3F1A"};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {combo_popup_bg};
                color: {input_fg};
                border: 1px solid {combo_popup_border};
                border-radius: 6px;
                selection-background-color: {combo_popup_sel_bg};
                selection-color: {combo_popup_sel_text};
                padding: 4px;
                font-family: {FONT_SANS};
                font-size: 11px;
            }}
        """)

        btn_action_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        btn_action_hover = "#A3360E" if self.is_dark else "#9E3414"
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_action_bg};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {btn_action_hover};
            }}
        """)

        self.empty_label.setStyleSheet(f"color: {text_muted}; border: none; background: transparent;")

    def _update_preset_button_styles(self) -> None:
        """Update active/inactive styles of the quick preset buttons."""
        border_color = "#27272A" if self.is_dark else "#DFD9CE"
        text_primary = "#FAFAFA" if self.is_dark else "#242220"
        text_muted = "#A1A1AA" if self.is_dark else "#78716C"
        active_bg = "#C2410C" if self.is_dark else "#BA3F1A"
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
                        background-color: {"#27272A" if self.is_dark else "#EDE8DF"};
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
        self.selected_category_filter = None
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _on_select_today_preset(self) -> None:
        """Preset shortcut: Today."""
        self.selected_date = date.today()
        self.active_preset = None
        self.selected_category_filter = None
        self.grid_widget.set_selected_date(self.selected_date)
        self._refresh_month_grid()
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _on_select_upcoming_preset(self) -> None:
        """Preset shortcut: Upcoming."""
        self.active_preset = "upcoming"
        self.selected_category_filter = None
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _on_select_overdue_preset(self) -> None:
        """Preset shortcut: Overdue."""
        self.active_preset = "overdue"
        self.selected_category_filter = None
        self._update_preset_button_styles()
        self._refresh_agenda()

    def _on_category_clicked(self, cat: str) -> None:
        """Filter agenda by clicked project category, or toggle back to All."""
        if cat == "All" or self.selected_category_filter == cat:
            self.selected_category_filter = None
        else:
            self.selected_category_filter = cat
        self._refresh_agenda()

    def _refresh_categories(self, counts: Dict[str, int], total_count: int) -> None:
        """Populate or update category buttons displaying task counts."""
        projects = [p.name for p in self.repo.get_all_projects()]
        if not projects:
            projects = ["Work", "Personal Projects"]
        for p in counts.keys():
            if p not in projects and p != "General":
                projects.append(p)

        cat_names = ["All"] + sorted(list(set(projects)))

        # Rebuild if the set of categories has changed
        if set(self.category_buttons.keys()) != set(cat_names):
            while self.cat_buttons_layout.count() > 0:
                item = self.cat_buttons_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
            self.category_buttons.clear()

            for cat in cat_names:
                count = total_count if cat == "All" else counts.get(cat, 0)
                is_active = (self.selected_category_filter is None and cat == "All") or (self.selected_category_filter == cat)
                btn = CategoryFilterButton(cat, count, is_active, self.is_dark, parent=self.categories_card)
                btn.clicked.connect(lambda checked, c=cat: self._on_category_clicked(c))
                self.category_buttons[cat] = btn
                self.cat_buttons_layout.addWidget(btn)
        else:
            for cat in cat_names:
                count = total_count if cat == "All" else counts.get(cat, 0)
                is_active = (self.selected_category_filter is None and cat == "All") or (self.selected_category_filter == cat)
                if cat in self.category_buttons:
                    self.category_buttons[cat].update_appearance(count, is_active, self.is_dark)

    def _refresh_agenda(self) -> None:
        """Render the scheduled tasks according to the active date, preset, and category filter."""
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
            # Single day view: remove double dash per user request
            is_today = (self.selected_date == date.today())
            if is_today:
                date_str = f"Today, {self.selected_date.strftime('%B %d')}"
            else:
                date_str = self.selected_date.strftime("%B %d, %A")
            self.agenda_title.setText(date_str)
            self.add_bar_container.show()
            self.add_input.setPlaceholderText("+ Add task... (Enter)")
            tasks = self.repo.get_task_hierarchy(target_date=self.selected_date, status_filter="task")
            empty_text = f"No tasks scheduled for {self.selected_date.strftime('%B %d')}."

        # Calculate counts per project category for all tasks in the current view
        counts_by_project: Dict[str, int] = {}
        for t in tasks:
            tag = t.project_tag or "General"
            counts_by_project[tag] = counts_by_project.get(tag, 0) + 1

        self._refresh_categories(counts_by_project, len(tasks))

        # Filter by selected category if active
        if self.selected_category_filter:
            display_tasks = [t for t in tasks if (t.project_tag or "General") == self.selected_category_filter]
        else:
            display_tasks = tasks

        # Update counter badge
        count = len(display_tasks)
        self.task_count_badge.setText(f"{count} {'task' if count == 1 else 'tasks'}")

        # Render tasks
        if not display_tasks:
            if self.selected_category_filter:
                self.empty_label.setText(f"No tasks in '{self.selected_category_filter}'.")
            else:
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

            for task in display_tasks:
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
