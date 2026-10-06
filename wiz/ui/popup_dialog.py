"""
Minimalist, card-based activity, task, subtask, and quick-note tracking window for WizDesk.
Implements the exact layout hierarchy:
1. Outer window controls (Minimize, Maximize, Close).
2. Inside White Card:
   - Top: Tasks | Quick Notes switcher
   - Below Switcher: Formatted Date (e.g. August 31, Monday)
   - Below Date: To-do | Completed | Pending | On Hold | Cancelled status bar
   - Task / Subtask / Note Content Area
   - Task options: Add subtasks, inline subtask checkoffs, and Move to Section (e.g. Personal -> Work)
   - Bottom Add Bar with Section selector & Create Section option
"""

import sys
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QDate, QTimer, QSize
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QMouseEvent,
    QKeyEvent,
    QCursor,
    QTextCharFormat,
    QGuiApplication,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QScrollArea,
    QFrame,
    QMenu,
    QGraphicsDropShadowEffect,
    QStackedWidget,
    QCalendarWidget,
    QSizePolicy,
    QColorDialog,
    QPlainTextEdit,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.core.state_machine import StateMachine
from wiz.storage.models import StorageRepository, TaskRecord, SubtaskRecord, NoteRecord, TagRecord, ProjectRecord
from wiz.ui.icons import get_app_icon, get_status_icon, render_tinted_svg
from wiz.sync.obsidian import sync_today_logs, sync_permanent_note
from wiz.ui.timeline_view import TimelineView
from wiz.ui.project_dashboard_view import ProjectDashboardView, PRESET_COLORS
from wiz.ui.sidebar_widget import SideNavBar
from wiz.ui.settings_view import SettingsView
from wiz.ui.help_faq_view import HelpFaqView
from wiz.ui.calendar_view import CalendarView
from wiz.ui.arrow_combo import ArrowComboBox


from wiz.ui.fonts import FONT_SANS, FONT_DISPLAY, FONT_MONO, get_font
from wiz.ui.checkbox import RoundedCheckbox


def get_context_menu_style(is_dark: bool = False) -> str:
    bg = "#18181B" if is_dark else "#FFFFFF"
    color = "#F4F4F5" if is_dark else "#18181B"
    border = "#27272A" if is_dark else "#E4E4E7"
    hover_bg = "#27272A" if is_dark else "#FEECE5"
    hover_color = "#FAFAFA" if is_dark else "#D84315"
    disabled_color = "#71717A" if is_dark else "#A1A1AA"
    return f"""
        QMenu {{
            background-color: {bg};
            color: {color};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 4px;
            font-family: {FONT_SANS};
            font-size: 12px;
        }}
        QMenu::item {{
            padding: 7px 32px 7px 8px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {hover_bg};
            color: {hover_color};
        }}
        QMenu::item:disabled {{
            color: {disabled_color};
        }}
        QMenu::right-arrow {{
            margin-right: 10px;
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {border};
            margin: 4px 6px;
        }}
    """



CALENDAR_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


class CalendarPopupDialog(QDialog):
    """
    Clean, minimalist popup calendar for WizDesk date navigation.
    Matches the card-based aesthetic with rounded corners, subtle borders, and smooth shadows.
    Supports dynamic Light and Dark themes.
    """

    def __init__(self, current_date: date, parent: Optional[QWidget] = None, is_dark: Optional[bool] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Date - WizDesk")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(310)

        self.selected_date = current_date
        self.is_dark = is_dark if is_dark is not None else (config.theme == "dark")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card_bg = "#18181B" if self.is_dark else "#FFFFFF"
        card_border = "#27272A" if self.is_dark else "#E5E5EA"
        combo_bg = "#27272A" if self.is_dark else "#F4F4F6"
        combo_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        combo_text = "#F4F4F5" if self.is_dark else "#18181B"
        nav_btn_color = "#A1A1AA" if self.is_dark else "#71717A"
        nav_btn_hover_color = "#FF8E6B" if self.is_dark else "#BA3F1A"
        nav_btn_hover_bg = "#27272A" if self.is_dark else "#EAEAEB"
        table_text = "#F4F4F5" if self.is_dark else "#18181B"
        table_hover_bg = "rgba(255, 107, 61, 40)" if self.is_dark else "#FEECE5"
        table_sel_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        table_sel_text = "#FFFFFF"
        today_btn_bg = "#27272A" if self.is_dark else "#F4F4F6"
        today_btn_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        today_btn_text = "#F4F4F5" if self.is_dark else "#18181B"
        today_btn_hover_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        today_btn_hover_text = "#FFFFFF"

        card = QFrame()
        card.setObjectName("calCard")
        card.setStyleSheet(f"""
            QFrame#calCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 14px;
            }}
            QComboBox {{
                background-color: {combo_bg};
                border: 1px solid {combo_border};
                border-radius: 6px;
                padding: 4px 22px 4px 8px;
                color: {combo_text};
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QComboBox:hover {{
                background-color: {nav_btn_hover_bg};
                border-color: {"#C2410C" if self.is_dark else "#BA3F1A"};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {card_bg};
                color: {combo_text};
                border: 1px solid {card_border};
                border-radius: 8px;
                selection-background-color: {nav_btn_hover_bg};
                selection-color: {combo_text};
                padding: 4px;
                font-family: {FONT_SANS};
                font-size: 12px;
                outline: none;
            }}
            QPushButton#calNavBtn {{
                background-color: transparent;
                color: {nav_btn_color};
                border: 1px solid transparent;
                border-radius: 6px;
                font-family: {FONT_SANS};
                font-size: 14px;
                font-weight: bold;
                padding: 2px 8px;
            }}
            QPushButton#calNavBtn:hover {{
                background-color: {nav_btn_hover_bg};
                color: {nav_btn_hover_color};
                border: 1px solid {"#C2410C" if self.is_dark else "#BA3F1A"};
            }}
            QCalendarWidget {{
                background-color: {card_bg};
                border: none;
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {card_bg};
                background-color: {card_bg};
            }}
            QCalendarWidget QTableView {{
                background-color: {card_bg};
                alternate-background-color: {card_bg};
                color: {table_text};
                font-family: {FONT_SANS};
                font-size: 12px;
                selection-background-color: {table_sel_bg};
                selection-color: {table_sel_text};
                border: none;
                outline: none;
            }}
            QCalendarWidget QTableView:item {{
                border-radius: 6px;
                padding: 2px;
            }}
            QCalendarWidget QTableView:item:hover {{
                background-color: {table_hover_bg};
                color: {table_text};
            }}
            QCalendarWidget QTableView:item:selected {{
                background-color: {table_sel_bg};
                color: {table_sel_text};
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # Custom Top Navigation Bar with matching dropdown boxes for Month & Year
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self.prev_btn = QPushButton("‹")
        self.prev_btn.setObjectName("calNavBtn")
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_btn.clicked.connect(self._on_prev_month)
        nav_layout.addWidget(self.prev_btn)

        self.month_combo = ArrowComboBox(self, is_dark=self.is_dark)
        self.month_combo.addItems(CALENDAR_MONTHS)
        self.month_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.month_combo.currentIndexChanged.connect(self._on_combo_page_changed)
        nav_layout.addWidget(self.month_combo, stretch=3)

        self.year_combo = ArrowComboBox(self, is_dark=self.is_dark)
        for y in range(2020, 2036):
            self.year_combo.addItem(str(y))
        self.year_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.year_combo.currentIndexChanged.connect(self._on_combo_page_changed)
        nav_layout.addWidget(self.year_combo, stretch=2)

        self.next_btn = QPushButton("›")
        self.next_btn.setObjectName("calNavBtn")
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_btn.clicked.connect(self._on_next_month)
        nav_layout.addWidget(self.next_btn)

        card_layout.addLayout(nav_layout)

        self.calendar = QCalendarWidget()
        self.calendar.setNavigationBarVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.setGridVisible(False)
        self.calendar.setSelectedDate(QDate(current_date.year, current_date.month, current_date.day))

        # Format header days cleanly in muted grey
        hdr_font = get_font(9, QFont.Weight.DemiBold)
        hdr_fmt = QTextCharFormat()
        hdr_fmt.setForeground(QColor("#A1A1AA" if self.is_dark else "#71717A"))
        hdr_fmt.setFont(hdr_font)
        self.calendar.setHeaderTextFormat(hdr_fmt)

        # Neutralize weekend text to clean theme color
        work_font = get_font(9)
        work_fmt = QTextCharFormat()
        work_fmt.setForeground(QColor("#F4F4F5" if self.is_dark else "#18181B"))
        work_fmt.setFont(work_font)
        for day in [
            Qt.DayOfWeek.Sunday,
            Qt.DayOfWeek.Monday,
            Qt.DayOfWeek.Tuesday,
            Qt.DayOfWeek.Wednesday,
            Qt.DayOfWeek.Thursday,
            Qt.DayOfWeek.Friday,
            Qt.DayOfWeek.Saturday,
        ]:
            self.calendar.setWeekdayTextFormat(day, work_fmt)

        self.calendar.currentPageChanged.connect(self._sync_combos_from_page)
        self.calendar.activated.connect(self._on_date_selected)
        self.calendar.clicked.connect(self._on_date_selected)
        card_layout.addWidget(self.calendar)

        self._sync_combos_from_page(self.calendar.yearShown(), self.calendar.monthShown())

        # Quick 'Today' button
        today_btn = QPushButton("Go to Today")
        today_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        today_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {today_btn_bg};
                color: {today_btn_text};
                border: 1px solid {today_btn_border};
                border-radius: 6px;
                padding: 6px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {today_btn_hover_bg};
                color: {today_btn_hover_text};
                border: 1px solid {today_btn_hover_bg};
            }}
        """)
        today_btn.clicked.connect(self._on_today_clicked)
        card_layout.addWidget(today_btn)

        layout.addWidget(card)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 60 if self.is_dark else 40))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

    def _sync_combos_from_page(self, year: int, month: int) -> None:
        """Keep month and year dropdowns in sync when navigating pages."""
        self.month_combo.blockSignals(True)
        self.year_combo.blockSignals(True)
        self.month_combo.setCurrentIndex(month - 1)
        self.year_combo.setCurrentText(str(year))
        self.month_combo.blockSignals(False)
        self.year_combo.blockSignals(False)

    def _on_combo_page_changed(self) -> None:
        """Update calendar view when month or year dropdown changes."""
        m = self.month_combo.currentIndex() + 1
        y = int(self.year_combo.currentText() or str(self.selected_date.year))
        self.calendar.setCurrentPage(y, m)

    def _on_prev_month(self) -> None:
        cur_y = self.calendar.yearShown()
        cur_m = self.calendar.monthShown()
        if cur_m == 1:
            self.calendar.setCurrentPage(cur_y - 1, 12)
        else:
            self.calendar.setCurrentPage(cur_y, cur_m - 1)

    def _on_next_month(self) -> None:
        cur_y = self.calendar.yearShown()
        cur_m = self.calendar.monthShown()
        if cur_m == 12:
            self.calendar.setCurrentPage(cur_y + 1, 1)
        else:
            self.calendar.setCurrentPage(cur_y, cur_m + 1)

    def _on_date_selected(self, qdate: QDate) -> None:
        self.selected_date = date(qdate.year(), qdate.month(), qdate.day())
        self.accept()

    def _on_today_clicked(self) -> None:
        self.selected_date = date.today()
        self.accept()


class CreateSectionDialog(QDialog):
    """
    Custom modal dialog for creating a new Section / Project in WizDesk.
    Matches the full feature set of ProjectDialog (all colors, description, and auto-track keywords).
    Replaces default OS input dialogs with WizDesk's clean minimalist rounded card design.
    Supports preset color swatches (3x8 grid of 24 colors) and custom color picker.
    Supports dynamic Light & Dark themes.
    """

    last_selected_color: str = "#FF6B3D"
    last_description: str = ""
    last_keywords: List[str] = []

    def __init__(self, parent: Optional[QWidget] = None, is_dark: Optional[bool] = None):
        super().__init__(parent)
        self.setWindowTitle("Create Section - WizDesk")
        self.setWindowIcon(get_app_icon("wiz-idle.svg"))
        self.setFixedSize(430, 485)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)

        self.is_dark = is_dark if is_dark is not None else (config.theme == "dark")

        # Pick a smart default color (first unused palette color or brand orange)
        used: set[str] = set()
        try:
            used = {p.color.upper() for p in StorageRepository().get_all_projects() if p.color}
        except Exception:
            pass
        chosen = None
        for c in PRESET_COLORS:
            if c.upper() not in used:
                chosen = c
                break
        self.selected_color = chosen or PRESET_COLORS[0]
        CreateSectionDialog.last_selected_color = self.selected_color

        card_bg = "#18181B" if self.is_dark else "#FFFFFF"
        card_border = "#27272A" if self.is_dark else "#E5E5EA"
        title_color = "#F4F4F5" if self.is_dark else "#18181B"
        label_color = "#A1A1AA" if self.is_dark else "#71717A"
        close_btn_color = "#71717A" if self.is_dark else "#A1A1AA"
        input_bg = "#27272A" if self.is_dark else "#F4F4F6"
        input_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        input_text = "#F4F4F5" if self.is_dark else "#18181B"
        input_focus_border = "#C2410C" if self.is_dark else "#BA3F1A"
        cancel_bg = "#27272A" if self.is_dark else "#F4F4F6"
        cancel_text = "#A1A1AA" if self.is_dark else "#71717A"
        cancel_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        cancel_hover_bg = "#3F3F46" if self.is_dark else "#EAEAEB"
        submit_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        submit_text = "#FFFFFF"
        submit_hover_bg = "#A3360E" if self.is_dark else "#9E3414"

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(12, 12, 12, 12)

        self.card = QFrame()
        self.card.setObjectName("createSectionCard")
        self.card.setStyleSheet(f"""
            QFrame#createSectionCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 18px;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 60 if self.is_dark else 40))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 16, 20, 16)
        self.card_layout.setSpacing(8)

        # Header Row
        hdr_layout = QHBoxLayout()
        hdr_title = QLabel("Create New Section")
        hdr_title.setStyleSheet(f"""
            QLabel {{
                color: {title_color};
                font-family: {FONT_SANS};
                font-size: 14px;
                font-weight: 700;
            }}
        """)
        hdr_layout.addWidget(hdr_title)
        hdr_layout.addStretch()

        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {close_btn_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 12px;
                font-weight: bold;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                color: {title_color};
                background-color: {input_bg};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        hdr_layout.addWidget(close_btn)
        self.card_layout.addLayout(hdr_layout)

        # Section Name Field
        name_lbl = QLabel("Section Name:")
        name_lbl.setStyleSheet(f"""
            QLabel {{
                color: {label_color};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        self.card_layout.addWidget(name_lbl)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("e.g. TurfLine, Research, WizDesk")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                background-color: {card_bg};
                border: 1.5px solid {input_focus_border};
            }}
        """)
        self.input_field.returnPressed.connect(self._on_submit)
        self.card_layout.addWidget(self.input_field)

        # Color Selection Header
        color_hdr = QHBoxLayout()
        color_hdr.setContentsMargins(0, 2, 0, 0)
        color_lbl = QLabel("Section Accent Color:")
        color_lbl.setStyleSheet(f"""
            QLabel {{
                color: {label_color};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        color_hdr.addWidget(color_lbl)
        color_hdr.addStretch()

        self.btn_custom_color = QPushButton("+ Custom Color…")
        self.btn_custom_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_custom_color.setFont(get_font(9, QFont.Weight.Medium))
        self.btn_custom_color.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {"#FF8E6B" if self.is_dark else "#C2410C"};
                border: none;
                padding: 1px 4px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                color: {"#FFFFFF" if self.is_dark else "#18181B"};
            }}
        """)
        self.btn_custom_color.clicked.connect(self._on_pick_custom_color)
        color_hdr.addWidget(self.btn_custom_color)
        self.card_layout.addLayout(color_hdr)

        # Preset Color Swatches (3 rows of 8 = all 24 colors)
        self.swatch_presets = PRESET_COLORS
        swatches_layout = QGridLayout()
        swatches_layout.setSpacing(6)
        swatches_layout.setContentsMargins(0, 0, 0, 0)
        self.swatch_buttons: List[QPushButton] = []
        for idx, col in enumerate(self.swatch_presets):
            r = idx // 8
            c = idx % 8
            s_btn = QPushButton()
            s_btn.setFixedSize(22, 22)
            s_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            is_active = (col.lower() == self.selected_color.lower())
            active_border = "2.5px solid #FFFFFF" if self.is_dark else "2.5px solid #18181B"
            normal_border = "1px solid rgba(255, 255, 255, 0.15)" if self.is_dark else "1px solid rgba(0, 0, 0, 0.12)"
            border = active_border if is_active else normal_border
            s_btn.setStyleSheet(f"background-color: {col}; border-radius: 11px; border: {border};")
            s_btn.clicked.connect(lambda checked, col_val=col: self._on_color_selected(col_val))
            swatches_layout.addWidget(s_btn, r, c)
            self.swatch_buttons.append(s_btn)
        self.card_layout.addLayout(swatches_layout)

        if self.selected_color.upper() not in [c.upper() for c in PRESET_COLORS]:
            self.btn_custom_color.setText(f"Custom: {self.selected_color}")

        # Description Field
        desc_lbl = QLabel("Description:")
        desc_lbl.setStyleSheet(f"""
            QLabel {{
                color: {label_color};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        self.card_layout.addWidget(desc_lbl)

        self.desc_field = QLineEdit()
        self.desc_field.setPlaceholderText("Brief overview of the project")
        self.desc_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                background-color: {card_bg};
                border: 1.5px solid {input_focus_border};
            }}
        """)
        self.desc_field.returnPressed.connect(self._on_submit)
        self.card_layout.addWidget(self.desc_field)

        # Keywords Field
        kw_lbl = QLabel("Window Title Keywords (comma separated):")
        kw_lbl.setStyleSheet(f"""
            QLabel {{
                color: {label_color};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        self.card_layout.addWidget(kw_lbl)

        self.kw_field = QLineEdit()
        self.kw_field.setPlaceholderText("e.g. turf, booking, stadium")
        self.kw_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                background-color: {card_bg};
                border: 1.5px solid {input_focus_border};
            }}
        """)
        self.kw_field.returnPressed.connect(self._on_submit)
        self.card_layout.addWidget(self.kw_field)

        # Aliases for parity with ProjectDialog
        self.name_edit = self.input_field
        self.desc_edit = self.desc_field
        self.kw_edit = self.kw_field

        # Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cancel_bg};
                color: {cancel_text};
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {cancel_hover_bg};
                color: {cancel_hover_color};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        submit_btn = QPushButton("Create Section")
        submit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        submit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {submit_bg};
                color: {submit_text};
                border: none;
                border-radius: 8px;
                padding: 7px 18px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {submit_hover_bg};
            }}
        """)
        submit_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(submit_btn)

        self.card_layout.addLayout(btn_layout)
        self.outer_layout.addWidget(self.card)

    def _on_color_selected(self, color_hex: str) -> None:
        self.selected_color = color_hex
        CreateSectionDialog.last_selected_color = color_hex
        found = False
        active_border = "2.5px solid #FFFFFF" if self.is_dark else "2.5px solid #18181B"
        normal_border = "1px solid rgba(255, 255, 255, 0.15)" if self.is_dark else "1px solid rgba(0, 0, 0, 0.12)"
        for idx, col in enumerate(self.swatch_presets):
            btn = self.swatch_buttons[idx]
            is_active = (col.lower() == color_hex.lower())
            if is_active:
                found = True
            b = active_border if is_active else normal_border
            btn.setStyleSheet(f"background-color: {col}; border-radius: 11px; border: {b};")

        if not found:
            self.btn_custom_color.setText(f"Custom: {color_hex}")
        else:
            self.btn_custom_color.setText("+ Custom Color…")

    def _on_pick_custom_color(self) -> None:
        initial = QColor(self.selected_color) if QColor.isValidColor(self.selected_color) else QColor("#FF6B3D")
        color = QColorDialog.getColor(initial, self, "Select Section Color")
        if color.isValid():
            self._on_color_selected(color.name().upper())

    def _on_submit(self) -> None:
        if self.section_name:
            CreateSectionDialog.last_selected_color = self.selected_color
            CreateSectionDialog.last_description = self.description
            CreateSectionDialog.last_keywords = self.keywords
            self.accept()

    @property
    def section_name(self) -> str:
        return self.input_field.text().strip()

    @property
    def description(self) -> str:
        return self.desc_field.text().strip()

    @property
    def keywords(self) -> List[str]:
        kw_text = self.kw_field.text().strip()
        kws = [k.strip().lower() for k in kw_text.split(",") if k.strip()]
        if kws:
            return kws
        name = self.section_name
        return [name.lower()] if name else []

    def get_data(self) -> Tuple[str, str, str, List[str]]:
        """Return (section_name, color, description, keywords)."""
        return self.section_name, self.selected_color, self.description, self.keywords

    @classmethod
    def get_section_details(
        cls, parent: Optional[QWidget] = None
    ) -> tuple[str, str, str, list[str], bool]:
        """Show custom modal dialog and return (section_name, color, description, keywords, accepted)."""
        dlg = cls(parent)
        dlg.input_field.setFocus()
        if parent:
            p_geo = parent.geometry()
            dlg.move(
                p_geo.center().x() - (dlg.width() // 2),
                p_geo.center().y() - (dlg.height() // 2),
            )
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted and dlg.section_name:
            cls.last_selected_color = dlg.selected_color
            cls.last_description = dlg.description
            cls.last_keywords = dlg.keywords
            return dlg.section_name, dlg.selected_color, dlg.description, dlg.keywords, True
        return "", "", "", [], False

    @classmethod
    def get_section_name(cls, parent: Optional[QWidget] = None) -> tuple[str, bool]:
        """Show custom modal dialog and return (section_name, accepted)."""
        name, color, desc, kws, ok = cls.get_section_details(parent)
        return name, ok

    @classmethod
    def get_section_data(cls, parent: Optional[QWidget] = None) -> tuple[str, str, bool]:
        """Show custom modal dialog and return (section_name, color, accepted)."""
        name, color, desc, kws, ok = cls.get_section_details(parent)
        return name, color, ok

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()
        super().paintEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class SegmentedFilterBar(QWidget):
    """Pill capsule segmented filter bar matching the FAQ & Documentation switcher style."""

    filter_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.options = ["Task", "In progress", "Completed", "Cancelled"]
        self.current_filter = "Task"
        self.is_dark = is_dark
        self._buttons: Dict[str, QPushButton] = {}

        self.setObjectName("SegmentedFilterBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(38)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(3, 3, 3, 3)
        self.layout.setSpacing(3)

        for opt in self.options:
            btn = QPushButton(opt)
            btn.setFixedHeight(30)
            btn.setFont(get_font(11, QFont.Weight.DemiBold))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, o=opt: self.set_active_filter(o))
            self._buttons[opt] = btn
            self.layout.addWidget(btn, stretch=1)

        self._update_container_style()
        self._update_button_styles()

    def set_dark_mode(self, is_dark: bool) -> None:
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self._update_container_style()
            self._update_button_styles()

    def _update_container_style(self) -> None:
        switcher_bg = "rgba(255, 255, 255, 0.03)" if self.is_dark else "#EAEAEB"
        switcher_border = "rgba(255, 255, 255, 0.12)" if self.is_dark else "#E4E4E7"
        self.setStyleSheet(f"""
            QWidget#SegmentedFilterBar, SegmentedFilterBar {{
                background-color: {switcher_bg};
                border: 1px solid {switcher_border};
                border-radius: 8px;
            }}
        """)

    def set_active_filter(self, filter_name: str) -> None:
        """Switch active filter tab."""
        if filter_name in self.options and self.current_filter != filter_name:
            self.current_filter = filter_name
            self._update_button_styles()
            self.filter_changed.emit(filter_name)

    def _update_button_styles(self) -> None:
        """Update button styles to match the elevated FAQ & Documentation switcher tabs."""
        is_dark = self.is_dark
        active_tab_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "#FFFFFF"
        active_tab_fg = "#FAFAFA" if is_dark else "#18181B"
        active_tab_border = "rgba(255, 255, 255, 0.14)" if is_dark else "#E4E4E7"
        inactive_tab_fg = "#A1A1AA" if is_dark else "#71717A"
        hover_fg = "#FAFAFA" if is_dark else "#18181B"
        hover_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.04)"

        for opt, btn in self._buttons.items():
            if opt == self.current_filter:
                btn.setFont(get_font(11, QFont.Weight.Bold))
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_tab_bg};
                        color: {active_tab_fg};
                        border: 1px solid {active_tab_border};
                        border-radius: 6px;
                        font-family: {FONT_SANS};
                        font-size: 11px;
                        font-weight: 600;
                        padding: 0 10px;
                    }}
                """)
            else:
                btn.setFont(get_font(11, QFont.Weight.Medium))
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {inactive_tab_fg};
                        border: 1px solid transparent;
                        border-radius: 6px;
                        font-family: {FONT_SANS};
                        font-size: 11px;
                        font-weight: 500;
                        padding: 0 10px;
                    }}
                    QPushButton:hover {{
                        color: {hover_fg};
                        background-color: {hover_bg};
                    }}
                """)


class EditableTaskLabel(QLabel):
    """A QLabel that emits double_clicked on mouse double click for inline editing."""
    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class InlineEditInput(QLineEdit):
    """A QLineEdit that handles Enter to submit, Escape to cancel, and FocusOut to submit."""
    editing_cancelled = pyqtSignal()

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._is_cancelling = False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._is_cancelling = True
            self.editing_cancelled.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


def format_task_time_tracking(
    created_at: Optional[datetime],
    completed_at: Optional[datetime],
    is_done: bool = False,
    is_cancelled: bool = False,
) -> str:
    """
    Format task or subtask time tracking metadata.
    When created and completed on the same day:
        '(9:30 AM - 1:15 PM)'
    When an older task is completed on a different day (e.g. rescheduled to today):
        '(Oct 1, 9:30 AM - Oct 5, 1:15 PM)'
    When uncompleted on the same day as created:
        '(9:30 AM)'
    When uncompleted on a later day than created:
        '(Oct 1, 9:30 AM)'
    """
    if not created_at:
        return ""

    time_created = created_at.strftime("%I:%M %p").lstrip("0")
    current_year = datetime.now().year

    def format_date_part(dt: datetime) -> str:
        if dt.year != current_year:
            return f"{dt.strftime('%b')} {dt.day}, {dt.year}"
        return f"{dt.strftime('%b')} {dt.day}"

    date_created = format_date_part(created_at)

    if (is_done or is_cancelled) and completed_at:
        time_completed = completed_at.strftime("%I:%M %p").lstrip("0")
        date_completed = format_date_part(completed_at)

        if created_at.date() == completed_at.date():
            return f"({time_created} - {time_completed})"
        else:
            return f"({date_created}, {time_created} - {date_completed}, {time_completed})"

    if created_at.date() == datetime.now().date():
        return f"({time_created})"
    else:
        return f"({date_created}, {time_created})"


def format_duration_seconds(seconds: int, compact: bool = False) -> str:
    """Format duration in seconds to MM:SS, H:MM:SS, or compact string e.g. 24m or 1h 15m."""
    if seconds <= 0:
        return "00:00" if not compact else "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if compact:
        if hours > 0:
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        return f"{max(1, minutes)}m"
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class SubtaskRowWidget(QWidget):
    """Single subtask row nested under a parent task with rename & delete support."""

    status_toggled = pyqtSignal(int, str)  # subtask_id, new_status
    delete_requested = pyqtSignal(int)  # subtask_id
    subtask_renamed = pyqtSignal(int, str)  # subtask_id, new_title

    def __init__(self, subtask: SubtaskRecord, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.subtask = subtask
        self.subtask_id = subtask.id or 0
        self.is_dark = is_dark

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 1, 0, 1)
        self.main_layout.setSpacing(1)

        # Top row: Checkbox, Title, and Delete ('x') button
        self.top_widget = QWidget()
        top_layout = QHBoxLayout(self.top_widget)
        top_layout.setContentsMargins(28, 2, 4, 1)
        top_layout.setSpacing(8)

        is_done = (subtask.status in ("done", "completed"))
        self.checkbox = RoundedCheckbox(checked=is_done, size=16, parent=self.top_widget, is_dark=self.is_dark)
        self.checkbox.toggled.connect(self._on_toggled)
        top_layout.addWidget(self.checkbox)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.label = EditableTaskLabel(subtask.title)
        self.label.setFont(get_font(9))
        self.label.setToolTip("Double-click or right-click to rename")
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.label.double_clicked.connect(self.start_renaming)
        top_layout.addWidget(self.label, stretch=1)

        edit_bg = "#18181B" if self.is_dark else "#FFFFFF"
        edit_color = "#F4F4F5" if self.is_dark else "#18181B"
        edit_border = "#C2410C" if self.is_dark else "#BA3F1A"

        self.edit_input = InlineEditInput(subtask.title, self)
        self.edit_input.setFont(get_font(9))
        self.edit_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {edit_bg};
                color: {edit_color};
                border: 1.5px solid {edit_border};
                border-radius: 4px;
                padding: 1px 6px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
        """)
        self.edit_input.setVisible(False)
        self.edit_input.returnPressed.connect(self._finish_renaming)
        self.edit_input.editing_cancelled.connect(self._cancel_renaming)
        top_layout.addWidget(self.edit_input, stretch=1)

        del_btn = QPushButton("x")
        del_btn.setFixedSize(16, 16)
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn_color = "#71717A" if self.is_dark else "#A1A1AA"
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {del_btn_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 10px;
                font-weight: bold;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                color: #EF4444;
                background-color: rgba(239, 68, 68, 0.15);
            }}
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.subtask_id))
        top_layout.addWidget(del_btn)
        self.main_layout.addWidget(self.top_widget)

        # Bottom row: Timestamp placed below the subtask title
        self.time_bar_widget = QWidget()
        time_layout = QHBoxLayout(self.time_bar_widget)
        time_layout.setContentsMargins(52, 0, 4, 2)
        time_layout.setSpacing(4)

        time_color = "#71717A" if self.is_dark else "#71717A"
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: {time_color};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
            }}
        """)
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        self.main_layout.addWidget(self.time_bar_widget)

        self._update_label_style(is_done)

    def start_renaming(self) -> None:
        """Enter inline subtask renaming mode."""
        self.edit_input.setText(self.subtask.title)
        self.label.setVisible(False)
        self.edit_input.setVisible(True)
        self.edit_input.setFocus()
        self.edit_input.selectAll()

    def _finish_renaming(self) -> None:
        """Save renamed subtask title."""
        if self.edit_input.isHidden():
            return
        new_title = self.edit_input.text().strip()
        self.edit_input.setVisible(False)
        self.label.setVisible(True)
        if new_title and new_title != self.subtask.title:
            self.subtask.title = new_title
            self.label.setText(new_title)
            self.subtask_renamed.emit(self.subtask_id, new_title)

    def _cancel_renaming(self) -> None:
        """Cancel inline subtask renaming."""
        self.edit_input.setText(self.subtask.title)
        self.edit_input.setVisible(False)
        self.label.setVisible(True)

    def _update_time_label(self, is_done: bool) -> None:
        self.time_label.setText(
            format_task_time_tracking(
                created_at=self.subtask.created_at,
                completed_at=self.subtask.completed_at,
                is_done=is_done,
                is_cancelled=False,
            )
        )

    def _update_label_style(self, is_done: bool) -> None:
        self._update_time_label(is_done)
        done_color = "#71717A" if self.is_dark else "#A1A1AA"
        active_color = "#D4D4D8" if self.is_dark else "#18181B"

        if is_done:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {done_color};
                    text-decoration: line-through;
                    font-family: {FONT_SANS};
                    font-size: 12px;
                }}
            """)
        else:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 12px;
                }}
            """)

    def _on_toggled(self, checked: bool) -> None:
        new_status = "done" if checked else "not_started"
        self.subtask.status = new_status
        if checked:
            self.subtask.completed_at = datetime.now()
        else:
            self.subtask.completed_at = None
        self._update_label_style(checked)
        self.status_toggled.emit(self.subtask_id, new_status)

    def contextMenuEvent(self, event) -> None:
        """Handle right-click context menu event for subtasks."""
        self._show_context_menu(event.pos())

    def _show_context_menu(self, pos: QPoint) -> None:
        """Display subtask context menu with Rename, Toggle Done, and Delete options."""
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))

        icon_color = "#D4D4D8" if self.is_dark else "#18181B"
        delete_color = "#EF4444"

        action_rename = menu.addAction(
            get_status_icon("icons/rename.svg", icon_color, 14), "Rename Subtask"
        )

        is_done = (self.subtask.status in ("done", "completed"))
        toggle_label = "Mark Incomplete" if is_done else "Mark Done"
        action_toggle = menu.addAction(toggle_label)

        menu.addSeparator()
        action_delete = menu.addAction(
            get_status_icon("icons/delete.svg", delete_color, 14), "Delete Subtask"
        )

        action = menu.exec(self.mapToGlobal(pos))
        if action == action_rename:
            self.start_renaming()
        elif action == action_toggle:
            self.checkbox.setChecked(not is_done)
        elif action == action_delete:
            self.delete_requested.emit(self.subtask_id)


class SubtaskAddButton(QPushButton):
    """Icon-only button for toggling inline subtask input."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._hovered: bool = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Add Subtask")
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.set_theme(is_dark)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.normal_color = "#71717A"
        self.hover_color = "#FAFAFA" if is_dark else "#18181B"
        self.hover_bg = "#27272A" if is_dark else "#EAEAEB"
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.hover_bg))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        c = self.hover_color if self._hovered else self.normal_color
        render_tinted_svg(painter, "icons/subtask.svg", c, 5, 5, 14)
        painter.end()


class ScheduleIconButton(QPushButton):
    """Icon-only button for scheduling a task with popup date menu."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.scheduled_date: Optional[str] = None
        self._hovered: bool = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Schedule Date")
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.set_theme(is_dark)

    def set_scheduled_date(self, dt_str: Optional[str]) -> None:
        self.scheduled_date = dt_str
        if dt_str:
            self.setToolTip(f"Scheduled: {dt_str}")
        else:
            self.setToolTip("Schedule Date")
        self.update()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.normal_color = "#71717A"
        self.hover_color = "#FAFAFA" if is_dark else "#18181B"
        self.active_color = "#FF6B3D" if is_dark else "#BA3F1A"
        self.hover_bg = "#27272A" if is_dark else "#EAEAEB"
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.hover_bg))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        if self.scheduled_date:
            c = self.hover_color if self._hovered else self.active_color
        else:
            c = self.hover_color if self._hovered else self.normal_color
        render_tinted_svg(painter, "icons/schedule.svg", c, 5, 5, 14)
        painter.end()


class RepeatIconButton(QPushButton):
    """Icon-only button for configuring task repeat mode with popup menu."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.repeat_mode: str = "none"
        self._hovered: bool = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Repeat Mode")
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.set_theme(is_dark)

    def set_repeat_mode(self, mode: str) -> None:
        self.repeat_mode = mode or "none"
        if self.repeat_mode != "none":
            self.setToolTip(f"Repeat: {self.repeat_mode.capitalize()}")
        else:
            self.setToolTip("Repeat Mode")
        self.update()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.normal_color = "#71717A"
        self.hover_color = "#FAFAFA" if is_dark else "#18181B"
        self.active_color = "#38BDF8" if is_dark else "#0284C7"
        self.hover_bg = "#27272A" if is_dark else "#EAEAEB"
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.hover_bg))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        if self.repeat_mode and self.repeat_mode != "none":
            c = self.hover_color if self._hovered else self.active_color
        else:
            c = self.hover_color if self._hovered else self.normal_color
        render_tinted_svg(painter, "icons/repeat.svg", c, 5, 5, 14)
        painter.end()


class TaskDeleteButton(QPushButton):
    """Icon-only button for deleting a task with red hover state."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._hovered: bool = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Delete Task")
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.set_theme(is_dark)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.normal_color = "#71717A"
        self.hover_color = "#EF4444"
        self.hover_bg = "rgba(239, 68, 68, 0.15)"
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.hover_bg))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        c = self.hover_color if self._hovered else self.normal_color
        render_tinted_svg(painter, "icons/delete.svg", c, 5, 5, 14)
        painter.end()


AVAILABLE_TAG_ICONS = [
    "code", "terminal", "bug", "git", "database", "server", "api", "cpu",
    "palette", "pen", "layout", "sparkle", "camera", "image",
    "target", "compass", "flag", "star", "bookmark", "folder", "briefcase",
    "book", "search", "clipboard", "file-text", "link", "lightbulb",
    "message", "mail", "globe", "shield", "coffee", "heart",
]


class TagIconChoiceButton(QPushButton):
    """Button in TagCreateDialog icon picker grid."""

    def __init__(self, icon_key: str, is_dark: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_key = icon_key
        self.is_dark = is_dark
        self.is_selected = False
        self._hovered = False
        self.setFixedSize(28, 28)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        clean_tooltip = icon_key.replace("-", " ").capitalize()
        self.setToolTip(clean_tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bg = "#3F3F46" if self.is_dark else "#E4E4E7"
        if self.is_selected:
            painter.setPen(QColor("#C2410C" if self.is_dark else "#BA3F1A"))
            painter.setBrush(QColor("rgba(194, 65, 12, 0.2)" if self.is_dark else "rgba(186, 63, 26, 0.15)"))
            painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 6, 6)
        elif self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(bg))
            painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 6, 6)

        c = "#FF8E6B" if (self.is_selected or self._hovered) else ("#A1A1AA" if self.is_dark else "#71717A")
        render_tinted_svg(painter, f"tags/{self.icon_key}.svg", c, 6, 6, 16)
        painter.end()


class TagPreviewPill(QWidget):
    """Live preview badge shown inside TagCreateDialog."""

    def __init__(self, icon_key: str, name: str, color_hex: str, is_dark: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_key = icon_key
        self.tag_name = name
        self.color_hex = color_hex
        self.is_dark = is_dark
        self.setFixedHeight(22)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(22, 0, 10, 0)
        self.layout.setSpacing(4)

        self.lbl = QLabel(name)
        self.lbl.setFont(get_font(10, QFont.Weight.Medium))
        self.layout.addWidget(self.lbl)
        self._update_style()

    def update_content(self, icon_key: str, name: str, color_hex: str, is_dark: bool) -> None:
        self.icon_key = icon_key
        self.tag_name = name
        self.color_hex = color_hex
        self.is_dark = is_dark
        self.lbl.setText(name)
        self._update_style()
        self.update()

    def _update_style(self) -> None:
        c = QColor(self.color_hex) if self.color_hex else QColor("#3B82F6")
        r, g, b = c.red(), c.green(), c.blue()
        bg_alpha = 0.22 if self.is_dark else 0.12
        border_alpha = 0.45 if self.is_dark else 0.30
        text_color = "#F4F4F5" if self.is_dark else "#18181B"
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba({r}, {g}, {b}, {bg_alpha});
                border: 1px solid rgba({r}, {g}, {b}, {border_alpha});
                border-radius: 11px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {text_color};
            }}
        """)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        render_tinted_svg(painter, f"tags/{self.icon_key}.svg", self.color_hex, 6, 5, 12)
        painter.end()


class TagBadgeWidget(QWidget):
    """Compact pill badge displaying a tag icon, name, and color theme."""

    clicked = pyqtSignal(int)  # tag_id

    def __init__(self, tag: TagRecord, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.tag = tag
        self.is_dark = is_dark
        self.setFixedHeight(18)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(f"Tag: {tag.name}")
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(19, 0, 7, 0)
        layout.setSpacing(4)

        self.name_label = QLabel(tag.name)
        self.name_label.setFont(get_font(9, QFont.Weight.Medium))
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.name_label)

        self._update_style()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self._update_style()
        self.update()

    def _update_style(self) -> None:
        c = QColor(self.tag.color) if self.tag.color else QColor("#3B82F6")
        r, g, b = c.red(), c.green(), c.blue()
        bg_alpha = 0.22 if self.is_dark else 0.12
        border_alpha = 0.45 if self.is_dark else 0.30
        text_color = "#F4F4F5" if self.is_dark else "#18181B"
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba({r}, {g}, {b}, {bg_alpha});
                border: 1px solid rgba({r}, {g}, {b}, {border_alpha});
                border-radius: 9px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {text_color};
            }}
        """)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.tag.id is not None:
                self.clicked.emit(self.tag.id)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        icon_name = self.tag.icon or "tag"
        c_hex = self.tag.color or "#3B82F6"
        render_tinted_svg(painter, f"tags/{icon_name}.svg", c_hex, 5, 4, 10)
        painter.end()


class RowTagButton(QPushButton):
    """Subtle icon-only button to manage tags on a task row."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._hovered: bool = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Add or manage tags")
        self.setFixedSize(18, 18)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.set_theme(is_dark)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.normal_color = "#71717A"
        self.hover_color = "#FF8E6B" if is_dark else "#BA3F1A"
        self.hover_bg = "#27272A" if is_dark else "#EAEAEB"
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.hover_bg))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        c = self.hover_color if self._hovered else self.normal_color
        render_tinted_svg(painter, "tag.svg", c, 3, 3, 12)
        painter.end()


class TagCreateDialog(QDialog):
    """Modal dialog for creating a custom tag with name, curated vector icon, and accent color."""

    def __init__(self, repo: StorageRepository, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.selected_icon = "code"
        self.selected_color = "#3B82F6"
        self.created_tag: Optional[TagRecord] = None

        self.setWindowTitle("Create Tag - WizDesk")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card_bg = "#18181B" if self.is_dark else "#FFFFFF"
        card_border = "#27272A" if self.is_dark else "#E5E5EA"
        title_color = "#F4F4F5" if self.is_dark else "#18181B"
        label_color = "#A1A1AA" if self.is_dark else "#71717A"
        input_bg = "#27272A" if self.is_dark else "#F4F4F6"
        input_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        input_text = "#F4F4F5" if self.is_dark else "#18181B"
        input_focus_border = "#C2410C" if self.is_dark else "#BA3F1A"
        close_btn_color = "#71717A" if self.is_dark else "#A1A1AA"

        self.card = QFrame()
        self.card.setObjectName("tagDialogCard")
        self.card.setStyleSheet(f"""
            QFrame#tagDialogCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 60 if self.is_dark else 40))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(18, 16, 18, 16)
        self.card_layout.setSpacing(10)

        # Header Row
        hdr_layout = QHBoxLayout()
        hdr_title = QLabel("Create New Tag")
        hdr_title.setFont(get_font(13, QFont.Weight.Bold))
        hdr_title.setStyleSheet(f"color: {title_color};")
        hdr_layout.addWidget(hdr_title)
        hdr_layout.addStretch()

        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {close_btn_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 12px;
                font-weight: bold;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                color: {title_color};
                background-color: {input_bg};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        hdr_layout.addWidget(close_btn)
        self.card_layout.addLayout(hdr_layout)

        # Tag Name Input
        name_lbl = QLabel("Tag Name:")
        name_lbl.setFont(get_font(11, QFont.Weight.DemiBold))
        name_lbl.setStyleSheet(f"color: {label_color};")
        self.card_layout.addWidget(name_lbl)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Coding, Debug, Design, Research")
        self.name_input.setFont(get_font(11))
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 10px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {input_focus_border};
            }}
        """)
        self.name_input.textChanged.connect(self._update_preview)
        self.card_layout.addWidget(self.name_input)

        # Icon Selection Header
        icon_lbl = QLabel("Choose Icon:")
        icon_lbl.setFont(get_font(11, QFont.Weight.DemiBold))
        icon_lbl.setStyleSheet(f"color: {label_color};")
        self.card_layout.addWidget(icon_lbl)

        # Icon Grid Picker
        icon_scroll = QScrollArea()
        icon_scroll.setFixedHeight(128)
        icon_scroll.setWidgetResizable(True)
        icon_scroll.setFrameShape(QFrame.Shape.NoFrame)
        icon_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        icon_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        icon_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
            }
        """)

        icon_container = QWidget()
        icon_container.setStyleSheet("background: transparent;")
        icon_grid = QGridLayout(icon_container)
        icon_grid.setSpacing(4)
        icon_grid.setContentsMargins(0, 0, 0, 0)

        self.icon_buttons: Dict[str, TagIconChoiceButton] = {}
        row = 0
        col = 0
        for icon_key in AVAILABLE_TAG_ICONS:
            ibtn = TagIconChoiceButton(icon_key, self.is_dark, self)
            ibtn.clicked.connect(lambda _, k=icon_key: self._on_icon_selected(k))
            icon_grid.addWidget(ibtn, row, col)
            self.icon_buttons[icon_key] = ibtn
            col += 1
            if col >= 9:
                col = 0
                row += 1

        icon_scroll.setWidget(icon_container)
        self.card_layout.addWidget(icon_scroll)

        # Color Selection Header
        color_hdr = QHBoxLayout()
        color_lbl = QLabel("Tag Color:")
        color_lbl.setFont(get_font(11, QFont.Weight.DemiBold))
        color_lbl.setStyleSheet(f"color: {label_color};")
        color_hdr.addWidget(color_lbl)
        color_hdr.addStretch()

        self.btn_custom_color = QPushButton("+ Custom Color...")
        self.btn_custom_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_custom_color.setFont(get_font(10, QFont.Weight.Medium))
        self.btn_custom_color.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {"#FF8E6B" if self.is_dark else "#C2410C"};
                border: none;
                padding: 1px 4px;
            }}
            QPushButton:hover {{
                color: {"#FFFFFF" if self.is_dark else "#18181B"};
            }}
        """)
        self.btn_custom_color.clicked.connect(self._on_pick_custom_color)
        color_hdr.addWidget(self.btn_custom_color)
        self.card_layout.addLayout(color_hdr)

        # Preset Color Swatches (2 rows of 8)
        swatch_layout = QGridLayout()
        swatch_layout.setSpacing(5)
        swatch_layout.setContentsMargins(0, 0, 0, 0)
        self.swatch_buttons: List[tuple] = []
        preset_tag_colors = PRESET_COLORS[:16] if len(PRESET_COLORS) >= 16 else PRESET_COLORS
        for idx, c_val in enumerate(preset_tag_colors):
            r_idx = idx // 8
            c_idx = idx % 8
            s_btn = QPushButton()
            s_btn.setFixedSize(22, 22)
            s_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            s_btn.clicked.connect(lambda _, col=c_val: self._on_color_selected(col))
            swatch_layout.addWidget(s_btn, r_idx, c_idx)
            self.swatch_buttons.append((s_btn, c_val))
        self.card_layout.addLayout(swatch_layout)

        # Live Preview Pill Row
        preview_hdr = QLabel("Live Preview:")
        preview_hdr.setFont(get_font(10, QFont.Weight.DemiBold))
        preview_hdr.setStyleSheet(f"color: {label_color}; margin-top: 2px;")
        self.card_layout.addWidget(preview_hdr)

        self.preview_pill = TagPreviewPill(self.selected_icon, "Sample Tag", self.selected_color, self.is_dark)
        self.card_layout.addWidget(self.preview_pill, 0, Qt.AlignmentFlag.AlignLeft)

        # Action Buttons (Cancel / Create)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 6, 0, 0)
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(get_font(11, QFont.Weight.Medium))
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {"#3F3F46" if self.is_dark else "#E4E4E7"};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.create_btn = QPushButton("Create Tag")
        self.create_btn.setFont(get_font(11, QFont.Weight.Bold))
        self.create_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        action_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {action_bg};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
            }}
            QPushButton:hover {{
                background-color: {"#A3360E" if self.is_dark else "#9E3414"};
            }}
        """)
        self.create_btn.clicked.connect(self._on_create_clicked)
        btn_layout.addWidget(self.create_btn)

        self.card_layout.addLayout(btn_layout)
        layout.addWidget(self.card)

        # Set initial selections
        self._update_icon_buttons_style()
        self._update_color_buttons_style()
        self._update_preview()

    def _on_icon_selected(self, icon_key: str) -> None:
        self.selected_icon = icon_key
        self._update_icon_buttons_style()
        self._update_preview()

    def _on_color_selected(self, color_hex: str) -> None:
        self.selected_color = color_hex
        self._update_color_buttons_style()
        self._update_preview()

    def _on_pick_custom_color(self) -> None:
        initial = QColor(self.selected_color)
        chosen = QColorDialog.getColor(initial, self, "Select Tag Color")
        if chosen.isValid():
            self.selected_color = chosen.name().upper()
            self._update_color_buttons_style()
            self._update_preview()

    def _update_icon_buttons_style(self) -> None:
        for k, btn in self.icon_buttons.items():
            btn.set_selected(k == self.selected_icon)

    def _update_color_buttons_style(self) -> None:
        for btn, c_val in self.swatch_buttons:
            is_sel = (c_val.lower() == self.selected_color.lower())
            active_border = "2.5px solid #FFFFFF" if self.is_dark else "2.5px solid #18181B"
            normal_border = "1px solid rgba(255, 255, 255, 0.15)" if self.is_dark else "1px solid rgba(0, 0, 0, 0.12)"
            border = active_border if is_sel else normal_border
            btn.setStyleSheet(f"background-color: {c_val}; border-radius: 11px; border: {border};")

    def _update_preview(self) -> None:
        name = self.name_input.text().strip() or "Sample Tag"
        self.preview_pill.update_content(self.selected_icon, name, self.selected_color, self.is_dark)

    def _on_create_clicked(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            self.name_input.setFocus()
            return
        tag = self.repo.create_tag(name, self.selected_icon, self.selected_color)
        self.created_tag = tag
        app_signals.tags_changed.emit()
        self.accept()


class ProjectIconButton(QPushButton):
    """Icon-only 28x28 button for choosing active project with upward popup menu."""

    project_selected = pyqtSignal(str)
    create_project_requested = pyqtSignal()

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.current_project: str = "Work"
        self.project_colors: Dict[str, str] = {}
        self.all_projects: List[str] = ["Work", "Personal Projects"]
        self._hovered: bool = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(f"Project: {self.current_project}")
        self.setFixedSize(28, 28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.clicked.connect(self._show_project_menu)
        self.set_theme(is_dark)

    def currentText(self) -> str:
        """Compatibility accessor for code expecting a QComboBox interface."""
        return self.current_project

    def setCurrentText(self, text: str) -> None:
        """Compatibility setter for code expecting a QComboBox interface."""
        self.current_project = text.strip() if text else "Work"
        self.setToolTip(f"Project: {self.current_project}")
        self.update()

    def set_projects(self, projects: List[Any]) -> None:
        """Update available project choices and their colors."""
        names: List[str] = []
        colors: Dict[str, str] = {}
        for p in projects:
            if hasattr(p, "name"):
                names.append(p.name)
                if hasattr(p, "color") and p.color:
                    colors[p.name] = p.color
            elif isinstance(p, str):
                names.append(p)
        if names:
            self.all_projects = names
            self.project_colors = colors
            if self.current_project not in names:
                self.current_project = names[0]
                self.setToolTip(f"Project: {self.current_project}")
        self.update()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.normal_color = "#71717A"
        self.hover_color = "#FAFAFA" if is_dark else "#18181B"
        self.hover_bg = "#27272A" if is_dark else "#EAEAEB"
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.hover_bg))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 6, 6)

        c = self.hover_color if self._hovered else self.normal_color
        render_tinted_svg(painter, "folder.svg", c, 6, 6, 16)

        dot_color_hex = self.project_colors.get(self.current_project, "#3B82F6")
        painter.setPen(QColor("#18181B" if self.is_dark else "#FFFFFF"))
        painter.setBrush(QColor(dot_color_hex))
        painter.drawEllipse(18, 18, 7, 7)
        painter.end()

    def _show_project_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))
        action_map: Dict[Any, str] = {}
        for name in self.all_projects:
            is_active = (name == self.current_project)
            display_text = f"{name}  ✓" if is_active else name
            proj_color = self.project_colors.get(name, "#3B82F6")
            proj_icon = get_status_icon("folder.svg", proj_color, size=16)
            act = menu.addAction(proj_icon, display_text)
            action_map[act] = name

        menu.addSeparator()
        create_icon = get_status_icon("icons/subtask.svg", "#C2410C" if self.is_dark else "#BA3F1A", size=16)
        act_create = menu.addAction(create_icon, "+ Create Section...")

        menu_size = menu.sizeHint()
        btn_pos = self.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(btn_pos.x(), btn_pos.y() - menu_size.height() - 4)

        chosen = menu.exec(target_pos)
        if chosen == act_create:
            self.create_project_requested.emit()
        elif chosen in action_map:
            new_proj = action_map[chosen]
            self.current_project = new_proj
            self.setToolTip(f"Project: {self.current_project}")
            self.project_selected.emit(new_proj)
            self.update()


class TagIconButton(QPushButton):
    """Icon-only 28x28 button for choosing tags with upward popup checklist and tag creation."""

    tags_selection_changed = pyqtSignal(list)  # list of int (tag_ids)

    def __init__(self, repo: StorageRepository, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.selected_tag_ids: List[int] = []
        self._hovered: bool = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Assign Tags")
        self.setFixedSize(28, 28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.clicked.connect(self._show_tags_menu)
        self.set_theme(is_dark)

    def clear_selection(self) -> None:
        self.selected_tag_ids = []
        self._update_tooltip()
        self.update()

    def set_selected_tag_ids(self, tag_ids: List[int]) -> None:
        self.selected_tag_ids = list(tag_ids)
        self._update_tooltip()
        self.update()

    def _update_tooltip(self) -> None:
        if not self.selected_tag_ids:
            self.setToolTip("Assign Tags")
            return
        all_tags = {t.id: t.name for t in self.repo.get_all_tags() if t.id is not None}
        names = [all_tags[tid] for tid in self.selected_tag_ids if tid in all_tags]
        self.setToolTip(f"Tags: {', '.join(names)}" if names else "Assign Tags")

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.normal_color = "#71717A"
        self.hover_color = "#FAFAFA" if is_dark else "#18181B"
        self.active_color = "#FF6B3D" if is_dark else "#BA3F1A"
        self.hover_bg = "#27272A" if is_dark else "#EAEAEB"
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.hover_bg))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 6, 6)

        has_tags = bool(self.selected_tag_ids)
        c = self.active_color if has_tags else (self.hover_color if self._hovered else self.normal_color)

        if len(self.selected_tag_ids) == 1:
            all_tags_map = {t.id: t for t in self.repo.get_all_tags() if t.id is not None}
            sel_tag = all_tags_map.get(self.selected_tag_ids[0])
            if sel_tag:
                icon_file = f"tags/{sel_tag.icon or 'tag'}.svg"
                render_tinted_svg(painter, icon_file, sel_tag.color or self.active_color, 6, 6, 16)
            else:
                render_tinted_svg(painter, "tag.svg", c, 6, 6, 16)
        else:
            render_tinted_svg(painter, "tag.svg", c, 6, 6, 16)

        if has_tags:
            dot_color = self.active_color
            if len(self.selected_tag_ids) == 1:
                all_tags_map = {t.id: t for t in self.repo.get_all_tags() if t.id is not None}
                sel_tag = all_tags_map.get(self.selected_tag_ids[0])
                if sel_tag and sel_tag.color:
                    dot_color = sel_tag.color
            painter.setPen(QColor("#18181B" if self.is_dark else "#FFFFFF"))
            painter.setBrush(QColor(dot_color))
            painter.drawEllipse(18, 18, 7, 7)
        painter.end()

    def _show_tags_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))
        all_tags = self.repo.get_all_tags()

        act_tag_map: Dict[Any, TagRecord] = {}
        for tag in all_tags:
            is_checked = (tag.id in self.selected_tag_ids)
            display_text = f"{tag.name}  ✓" if is_checked else tag.name
            tag_icon = get_status_icon(f"tags/{tag.icon or 'tag'}.svg", tag.color or "#3B82F6", size=16)
            act = menu.addAction(tag_icon, display_text)
            act_tag_map[act] = tag

        menu.addSeparator()
        create_icon = get_status_icon("tags/tag.svg", "#C2410C" if self.is_dark else "#BA3F1A", size=16)
        act_create = menu.addAction(create_icon, "+ Create Tag...")
        if self.selected_tag_ids:
            clear_icon = get_status_icon("icons/delete.svg", "#EF4444", size=14)
            act_clear = menu.addAction(clear_icon, "Clear Tags")
        else:
            act_clear = None

        menu_size = menu.sizeHint()
        btn_pos = self.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(btn_pos.x(), btn_pos.y() - menu_size.height() - 4)

        chosen = menu.exec(target_pos)
        if chosen == act_create:
            dlg = TagCreateDialog(self.repo, self, is_dark=self.is_dark)
            cal_pos = self.mapToGlobal(QPoint(0, 0))
            dlg.move(cal_pos.x() - 150, cal_pos.y() - 360)
            if dlg.exec() == QDialog.DialogCode.Accepted and hasattr(dlg, "created_tag") and dlg.created_tag and dlg.created_tag.id:
                if dlg.created_tag.id not in self.selected_tag_ids:
                    self.selected_tag_ids.append(dlg.created_tag.id)
                self._update_tooltip()
                self.tags_selection_changed.emit(self.selected_tag_ids)
                self.update()
        elif act_clear and chosen == act_clear:
            self.clear_selection()
            self.tags_selection_changed.emit(self.selected_tag_ids)
        elif chosen in act_tag_map:
            tag = act_tag_map[chosen]
            if tag.id is not None:
                if tag.id in self.selected_tag_ids:
                    self.selected_tag_ids.remove(tag.id)
                else:
                    self.selected_tag_ids.append(tag.id)
                self._update_tooltip()
                self.tags_selection_changed.emit(self.selected_tag_ids)
                self.update()


class TagFilterBar(QWidget):
    """Horizontal filter chips for filtering tasks by tag."""

    tag_selected = pyqtSignal(object)  # tag_id: Optional[int]

    def __init__(self, repo: StorageRepository, is_dark: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.selected_tag_id: Optional[int] = None
        self._explicitly_hidden: bool = False

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 2, 4, 2)
        self.layout.setSpacing(6)

        self.rebuild_chips()

    def hide(self) -> None:
        self._explicitly_hidden = True
        super().hide()

    def setVisible(self, visible: bool) -> None:
        if not visible:
            self._explicitly_hidden = True
        super().setVisible(visible)

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.rebuild_chips()

    def rebuild_chips(self) -> None:
        while self.layout.count() > 0:
            item = self.layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if self._explicitly_hidden:
            return

        all_tags = self.repo.get_all_tags()
        if not all_tags:
            super().setVisible(False)
            return

        super().setVisible(True)

        all_btn = QPushButton("All")
        all_btn.setFixedHeight(22)
        all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        all_btn.setFont(get_font(9, QFont.Weight.Medium))
        is_all_active = (self.selected_tag_id is None)
        self._style_chip(all_btn, is_all_active, None)
        all_btn.clicked.connect(lambda: self._select_tag(None))
        self.layout.addWidget(all_btn)

        for tag in all_tags:
            is_active = (self.selected_tag_id == tag.id)
            btn = QPushButton(f"{tag.name}")
            btn.setFixedHeight(22)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFont(get_font(9, QFont.Weight.Medium))
            self._style_chip(btn, is_active, tag.color)
            btn.clicked.connect(lambda _, tid=tag.id: self._select_tag(tid))
            self.layout.addWidget(btn)

        self.layout.addStretch()

    def _select_tag(self, tag_id: Optional[int]) -> None:
        if self.selected_tag_id == tag_id and tag_id is not None:
            self.selected_tag_id = None
        else:
            self.selected_tag_id = tag_id
        self.rebuild_chips()
        self.tag_selected.emit(self.selected_tag_id)

    def _style_chip(self, btn: QPushButton, is_active: bool, tag_color: Optional[str]) -> None:
        if is_active:
            bg = "#C2410C" if self.is_dark else "#BA3F1A"
            text_color = "#FFFFFF"
            border = "none"
        else:
            bg = "#27272A" if self.is_dark else "#E4E4E7"
            text_color = "#F4F4F5" if self.is_dark else "#3F3F46"
            border = f"1px solid {tag_color}" if tag_color else ("1px solid #3F3F46" if self.is_dark else "1px solid #D4D4D8")

        hover_bg = "#3F3F46" if self.is_dark else "#D4D4D8"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: {border};
                border-radius: 11px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg if not is_active else bg};
            }}
        """)


class TaskStopwatchWidget(QWidget):
    """
    Interactive task stopwatch widget.
    Features:
    - Stopwatch toggle button (start / pause)
    - Live ticking timer label (1000ms QTimer)
    - When task is completed, shows static duration badge (e.g. 24m or 1h 15m)
    - Persists elapsed time and session start to SQLite via repo
    """

    timer_toggled = pyqtSignal(int, bool)  # task_id, is_running

    def __init__(
        self,
        task: TaskRecord,
        repo: Optional[StorageRepository] = None,
        is_dark: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.task = task
        self.task_id = task.id or 0
        self.repo = repo
        self.is_dark = is_dark
        self._btn_hovered = False

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)

        # Stopwatch toggle icon button
        self.btn = QPushButton(self)
        self.btn.setFixedSize(18, 18)
        self.btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.btn.clicked.connect(self._toggle_stopwatch)
        self.btn.paintEvent = self._paint_btn
        self.btn.enterEvent = self._on_btn_enter
        self.btn.leaveEvent = self._on_btn_leave
        self.layout.addWidget(self.btn)

        # Elapsed time label
        self.time_label = QLabel(self)
        self.time_label.setFont(get_font(10, QFont.Weight.Medium))
        self.layout.addWidget(self.time_label)

        # Live ticker timer
        self.ticker = QTimer(self)
        self.ticker.setInterval(1000)
        self.ticker.timeout.connect(self._on_tick)

        self.refresh()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.refresh()

    def _paint_btn(self, event) -> None:
        painter = QPainter(self.btn)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        is_running = self.task.is_timer_running
        active_color = "#C2410C" if self.is_dark else "#BA3F1A"
        normal_color = "#71717A" if self.is_dark else "#A1A1AA"
        hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        hover_bg = "#27272A" if self.is_dark else "#EAEAEB"

        if self._btn_hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(hover_bg))
            painter.drawRoundedRect(0, 0, self.btn.width(), self.btn.height(), 4, 4)

        c = active_color if is_running else (hover_color if self._btn_hovered else normal_color)
        render_tinted_svg(painter, "stopwatch.svg", c, 2, 2, 14)
        painter.end()

    def _on_btn_enter(self, event) -> None:
        self._btn_hovered = True
        self.btn.update()

    def _on_btn_leave(self, event) -> None:
        self._btn_hovered = False
        self.btn.update()

    def _on_tick(self) -> None:
        if self.task.is_timer_running:
            elapsed = self.task.total_elapsed_seconds
            self.time_label.setText(format_duration_seconds(elapsed, compact=False))

    def refresh(self) -> None:
        """Update visual state and ticker based on task status and timer state."""
        is_done = self.task.status in ("done", "completed", "cancelled", "canceled")
        is_running = self.task.is_timer_running and not is_done
        elapsed = self.task.total_elapsed_seconds

        time_fg = "#A1A1AA" if self.is_dark else "#71717A"
        running_fg = "#C2410C" if self.is_dark else "#BA3F1A"

        if is_done:
            self.ticker.stop()
            self.btn.setVisible(False)
            if elapsed > 0:
                compact_str = format_duration_seconds(elapsed, compact=True)
                self.time_label.setText(compact_str)
                self.time_label.setStyleSheet(f"""
                    QLabel {{
                        color: {time_fg};
                        background: transparent;
                        font-family: {FONT_MONO};
                        font-size: 10px;
                        font-weight: 600;
                    }}
                """)
                self.time_label.setVisible(True)
                self.setVisible(True)
            else:
                self.time_label.setText("")
                self.time_label.setVisible(False)
                self.setVisible(False)
        else:
            self.btn.setVisible(True)
            self.setVisible(True)
            if is_running:
                if not self.ticker.isActive():
                    self.ticker.start()
                self.btn.setToolTip("Pause stopwatch")
                live_str = format_duration_seconds(elapsed, compact=False)
                self.time_label.setText(live_str)
                self.time_label.setStyleSheet(f"""
                    QLabel {{
                        color: {running_fg};
                        background: transparent;
                        font-family: {FONT_MONO};
                        font-size: 10px;
                        font-weight: bold;
                    }}
                """)
                self.time_label.setVisible(True)
            else:
                self.ticker.stop()
                self.btn.setToolTip("Start stopwatch")
                if elapsed > 0:
                    paused_str = format_duration_seconds(elapsed, compact=False)
                    self.time_label.setText(paused_str)
                    self.time_label.setStyleSheet(f"""
                        QLabel {{
                            color: {time_fg};
                            background: transparent;
                            font-family: {FONT_MONO};
                            font-size: 10px;
                            font-weight: 500;
                        }}
                    """)
                    self.time_label.setVisible(True)
                else:
                    self.time_label.setText("")
                    self.time_label.setVisible(False)
        self.btn.update()

    def _toggle_stopwatch(self) -> None:
        """Toggle timer between running and paused."""
        repo = self.repo
        if not repo:
            p = self.parent()
            while p is not None:
                if hasattr(p, "repo") and p.repo:
                    repo = p.repo
                    break
                p = p.parent()
        if not repo:
            repo = StorageRepository()

        if self.task.is_timer_running:
            repo.pause_task_stopwatch(self.task_id)
            self.task.duration_seconds = self.task.total_elapsed_seconds
            self.task.timer_started_at = None
            self.refresh()
            self.timer_toggled.emit(self.task_id, False)
        else:
            repo.start_task_stopwatch(self.task_id)
            self.task.timer_started_at = datetime.now()
            self.task.status = "in_progress"
            self.refresh()
            self.timer_toggled.emit(self.task_id, True)

    def closeEvent(self, event) -> None:
        if hasattr(self, "ticker") and self.ticker.isActive():
            self.ticker.stop()
        super().closeEvent(event)


class TaskRowWidget(QWidget):
    """
    Parent task row featuring:
    - Custom rounded checkbox & task title with inline renaming (double-click or context menu)
    - Schedule date button & repeat mode button with status badges
    - Nested subtask list with checkboxes & renaming
    - '+ subtask' inline adder
    - Right-click context menu with 'Rename Task', 'Move to Section ->', status moves, and 'Delete Task'
    """

    status_toggled = pyqtSignal(int, str)  # task_id, new_status
    action_requested = pyqtSignal(str, int)  # action_type, task_id
    project_changed = pyqtSignal(int, str)  # task_id, new_project
    task_renamed = pyqtSignal(int, str)  # task_id, new_title
    subtask_added = pyqtSignal(int, str)  # task_id, subtask_title
    subtask_toggled = pyqtSignal(int, str)  # subtask_id, new_status
    subtask_deleted = pyqtSignal(int)  # subtask_id
    subtask_renamed = pyqtSignal(int, str)  # subtask_id, new_title
    schedule_changed = pyqtSignal(int, str)  # task_id, new_scheduled_date
    repeat_changed = pyqtSignal(int, str)  # task_id, new_repeat_mode
    task_tags_changed = pyqtSignal(int, list)  # task_id, tag_ids

    def __init__(self, task: TaskRecord, all_projects: List[str], parent: Optional[QWidget] = None, is_dark: bool = False, repo: Optional[StorageRepository] = None):
        super().__init__(parent)
        self.task = task
        self.task_id = task.id or 0
        self.all_projects = all_projects
        self.is_dark = is_dark
        self.repo = repo

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 2, 0, 2)
        self.main_layout.setSpacing(3)

        # Top row: Checkbox, Title, Schedule, Repeat, + Subtask button
        self.top_widget = QWidget()
        top_layout = QHBoxLayout(self.top_widget)
        top_layout.setContentsMargins(4, 3, 4, 3)
        top_layout.setSpacing(6)

        is_done = (task.status in ("done", "completed"))
        self.checkbox = RoundedCheckbox(checked=is_done, size=20, parent=self.top_widget, is_dark=self.is_dark)
        self.checkbox.toggled.connect(self._on_checkbox_toggled)
        top_layout.addWidget(self.checkbox)

        self.label = EditableTaskLabel(task.title)
        self.label.setFont(get_font(10, QFont.Weight.Medium))
        self.label.setToolTip("Double-click or right-click to rename")
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.label.double_clicked.connect(self.start_renaming)
        top_layout.addWidget(self.label, stretch=1)

        edit_bg = "#18181B" if self.is_dark else "#FFFFFF"
        edit_color = "#F4F4F5" if self.is_dark else "#18181B"
        edit_border = "#C2410C" if self.is_dark else "#BA3F1A"

        self.edit_input = InlineEditInput(task.title, self)
        self.edit_input.setFont(get_font(10, QFont.Weight.Medium))
        self.edit_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {edit_bg};
                color: {edit_color};
                border: 1.5px solid {edit_border};
                border-radius: 5px;
                padding: 2px 6px;
                font-family: {FONT_SANS};
                font-size: 13px;
            }}
        """)
        self.edit_input.setVisible(False)
        self.edit_input.returnPressed.connect(self._finish_renaming)
        self.edit_input.editing_cancelled.connect(self._cancel_renaming)
        top_layout.addWidget(self.edit_input, stretch=1)

        # Schedule icon-only button
        self.schedule_btn = ScheduleIconButton(is_dark=self.is_dark, parent=self.top_widget)
        self.schedule_btn.set_scheduled_date(self.task.scheduled_date)
        self.schedule_btn.clicked.connect(self._pick_schedule)
        top_layout.addWidget(self.schedule_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Repeat icon-only button
        self.repeat_btn = RepeatIconButton(is_dark=self.is_dark, parent=self.top_widget)
        self.repeat_btn.set_repeat_mode(self.task.repeat_mode)
        self.repeat_btn.clicked.connect(self._pick_repeat)
        top_layout.addWidget(self.repeat_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Subtask icon-only button
        self.add_sub_btn = SubtaskAddButton(is_dark=self.is_dark, parent=self.top_widget)
        self.add_sub_btn.clicked.connect(self._toggle_subtask_input)
        top_layout.addWidget(self.add_sub_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Delete icon-only button
        self.delete_btn = TaskDeleteButton(is_dark=self.is_dark, parent=self.top_widget)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        top_layout.addWidget(self.delete_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(self.top_widget)

        # Status dropdown, time label, and schedule/repeat badges directly below task title
        self.status_bar_widget = QWidget()
        status_bar_layout = QHBoxLayout(self.status_bar_widget)
        status_bar_layout.setContentsMargins(34, 0, 4, 3)
        status_bar_layout.setSpacing(8)

        self.status_combo = ArrowComboBox(self, is_dark=self.is_dark)
        self.status_combo.setEditable(False)
        self.status_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._populate_status_combo()
        self.status_combo.currentIndexChanged.connect(self._on_status_combo_changed)
        status_bar_layout.addWidget(self.status_combo)

        # Time metadata label
        time_color = "#71717A" if self.is_dark else "#71717A"
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: {time_color};
                font-family: {FONT_MONO};
                font-size: 11px;
                font-weight: 500;
            }}
        """)
        status_bar_layout.addWidget(self.time_label)

        # Active task stopwatch widget
        self.stopwatch_widget = TaskStopwatchWidget(
            task=self.task,
            repo=self.repo,
            is_dark=self.is_dark,
            parent=self.status_bar_widget,
        )
        self.stopwatch_widget.timer_toggled.connect(self._on_stopwatch_toggled)
        status_bar_layout.addWidget(self.stopwatch_widget)

        # Schedule date badge (removed per user request to streamline task rows)
        self.schedule_badge = QLabel()
        self.schedule_badge.setFixedHeight(18)
        self.schedule_badge.setVisible(False)

        # Repeat mode badge
        self.repeat_badge = QLabel()
        self.repeat_badge.setFixedHeight(18)
        self.repeat_badge.setVisible(False)
        status_bar_layout.addWidget(self.repeat_badge)

        # Tag badges container
        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(4)
        status_bar_layout.addWidget(self.tags_container)

        # Row tag button to edit tags directly on this task
        self.row_tag_btn = RowTagButton(is_dark=self.is_dark, parent=self.status_bar_widget)
        self.row_tag_btn.clicked.connect(self._on_manage_tags_clicked)
        status_bar_layout.addWidget(self.row_tag_btn)

        status_bar_layout.addStretch()
        self.main_layout.addWidget(self.status_bar_widget)
        self._update_badges()

        # Subtasks container
        self.subtasks_container = QWidget()
        self.subtasks_layout = QVBoxLayout(self.subtasks_container)
        self.subtasks_layout.setContentsMargins(0, 0, 0, 0)
        self.subtasks_layout.setSpacing(2)

        # Populate existing subtasks
        for st in task.subtasks:
            st_row = SubtaskRowWidget(st, self.subtasks_container, is_dark=self.is_dark)
            st_row.status_toggled.connect(self.subtask_toggled.emit)
            st_row.delete_requested.connect(self.subtask_deleted.emit)
            st_row.subtask_renamed.connect(self.subtask_renamed.emit)
            self.subtasks_layout.addWidget(st_row)

        # Inline subtask input bar (hidden by default)
        self.sub_input_widget = QWidget()
        sub_input_layout = QHBoxLayout(self.sub_input_widget)
        sub_input_layout.setContentsMargins(28, 2, 4, 2)
        sub_input_layout.setSpacing(6)

        sub_in_bg = "#27272A" if self.is_dark else "#F4F4F6"
        sub_in_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        sub_in_text = "#F4F4F5" if self.is_dark else "#18181B"
        sub_in_focus = "#C2410C" if self.is_dark else "#BA3F1A"

        self.sub_input = QLineEdit()
        self.sub_input.setPlaceholderText("+ Add subtask... (Press Enter)")
        self.sub_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {sub_in_bg};
                color: {sub_in_text};
                border: 1px solid {sub_in_border};
                border-radius: 6px;
                padding: 4px 8px;
                font-family: {FONT_SANS};
                font-size: 12px;
                word-spacing: 1px;
            }}
            QLineEdit:focus {{
                background-color: {edit_bg};
                border: 1.5px solid {sub_in_focus};
            }}
        """)
        self.sub_input.returnPressed.connect(self._on_submit_subtask)
        sub_input_layout.addWidget(self.sub_input, stretch=1)

        sub_btn_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        sub_btn_text = "#FFFFFF"
        sub_btn_hover = "#A3360E" if self.is_dark else "#9E3414"

        sub_add_confirm_btn = QPushButton("Add")
        sub_add_confirm_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        sub_add_confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {sub_btn_bg};
                color: {sub_btn_text};
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {sub_btn_hover};
            }}
        """)
        sub_add_confirm_btn.clicked.connect(self._on_submit_subtask)
        sub_input_layout.addWidget(sub_add_confirm_btn)

        self.sub_input_widget.setVisible(False)
        self.subtasks_layout.addWidget(self.sub_input_widget)

        self.main_layout.addWidget(self.subtasks_container)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Initialize visual status representation
        self._update_status_ui(task.status or "not_started")

    def _toggle_subtask_input(self, force_show: bool = False) -> None:
        """Toggle inline subtask input visibility."""
        is_vis = self.sub_input_widget.isVisible()
        new_vis = True if force_show else not is_vis
        self.sub_input_widget.setVisible(new_vis)
        if new_vis:
            self.sub_input.setFocus()

    def _on_submit_subtask(self) -> None:
        """Submit new subtask."""
        title = self.sub_input.text().strip()
        if not title:
            return
        self.subtask_added.emit(self.task_id, title)
        self.sub_input.clear()
        self.sub_input_widget.setVisible(False)

    def _populate_status_combo(self) -> None:
        """Populate the status dropdown with monochrome icons and labels."""
        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        sub_color = "#A1A1AA" if self.is_dark else "#71717A"
        self.status_combo.addItem(get_status_icon("icons/status-circle-ring.svg", sub_color, size=13), "Open")
        self.status_combo.addItem(get_status_icon("icons/in-progress.svg", sub_color, size=13), "In progress")
        self.status_combo.addItem(get_status_icon("icons/media-media-complete.svg", sub_color, size=13), "Completed")
        self.status_combo.addItem(get_status_icon("icons/cancelled.svg", sub_color, size=13), "Cancelled")
        self.status_combo.blockSignals(False)

    def set_theme(self, is_dark: bool) -> None:
        """Dynamically update theme on the task row."""
        self.is_dark = is_dark
        self.checkbox.set_theme(is_dark)
        self.status_combo.set_theme(is_dark)
        if hasattr(self, "add_sub_btn") and hasattr(self.add_sub_btn, "set_theme"):
            self.add_sub_btn.set_theme(is_dark)
        if hasattr(self, "schedule_btn") and hasattr(self.schedule_btn, "set_theme"):
            self.schedule_btn.set_theme(is_dark)
        if hasattr(self, "repeat_btn") and hasattr(self.repeat_btn, "set_theme"):
            self.repeat_btn.set_theme(is_dark)
        if hasattr(self, "delete_btn") and hasattr(self.delete_btn, "set_theme"):
            self.delete_btn.set_theme(is_dark)
        if hasattr(self, "stopwatch_widget") and hasattr(self.stopwatch_widget, "set_theme"):
            self.stopwatch_widget.set_theme(is_dark)
        self._populate_status_combo()
        self._update_status_ui(self.task.status)
        self._update_badges()

    def _on_stopwatch_toggled(self, task_id: int, is_running: bool) -> None:
        """Handle stopwatch start/pause toggle."""
        if is_running:
            self.task.status = "in_progress"
            self._update_status_ui("in_progress")
            self.status_toggled.emit(self.task_id, "in_progress")
        else:
            self.stopwatch_widget.refresh()

    def _update_badges(self) -> None:
        """Update visual badges for scheduled date / overdue status and repeat mode."""
        if self.task.scheduled_date:
            self.schedule_btn.set_scheduled_date(self.task.scheduled_date)
        else:
            self.schedule_btn.set_scheduled_date(None)
        self.schedule_badge.setVisible(False)

        if self.task.is_recurring:
            mode_display = {
                "daily": "Daily",
                "weekdays": "Weekdays",
                "weekends": "Weekends",
            }.get(self.task.repeat_mode, self.task.repeat_mode.capitalize())

            bg = "rgba(56, 189, 248, 0.14)" if self.is_dark else "#E0F2FE"
            fg = "#38BDF8" if self.is_dark else "#0284C7"
            border = "rgba(56, 189, 248, 0.35)" if self.is_dark else "#BAE6FD"

            self.repeat_badge.setText(mode_display)
            self.repeat_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg};
                    color: {fg};
                    border: 1px solid {border};
                    border-radius: 4px;
                    padding: 0 6px;
                    font-family: {FONT_SANS};
                    font-size: 10px;
                    font-weight: 600;
                }}
            """)
            self.repeat_badge.setVisible(True)
            self.repeat_btn.set_repeat_mode(self.task.repeat_mode)
        else:
            self.repeat_badge.setVisible(False)
            self.repeat_btn.set_repeat_mode("none")

        # Update tag badges
        if hasattr(self, "tags_layout"):
            while self.tags_layout.count() > 0:
                item = self.tags_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

            for tag in getattr(self.task, "tags", []):
                badge = TagBadgeWidget(tag, parent=self.tags_container, is_dark=self.is_dark)
                badge.clicked.connect(lambda _, tid=tag.id: self._on_manage_tags_clicked())
                self.tags_layout.addWidget(badge)

    def _on_manage_tags_clicked(self) -> None:
        """Open popup menu to manage tags on this task."""
        repo = getattr(self, "repo", None)
        if not repo:
            p = self.parent()
            while p is not None:
                if hasattr(p, "repo"):
                    repo = p.repo
                    break
                p = p.parent()
        if not repo:
            repo = StorageRepository()

        all_tags = repo.get_all_tags()
        current_tag_ids = [t.id for t in getattr(self.task, "tags", []) if t.id is not None]

        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))

        act_tag_map: Dict[Any, TagRecord] = {}
        for tag in all_tags:
            is_checked = (tag.id in current_tag_ids)
            display_text = f"{tag.name}  ✓" if is_checked else tag.name
            tag_icon = get_status_icon(f"tags/{tag.icon or 'tag'}.svg", tag.color or "#3B82F6", size=16)
            act = menu.addAction(tag_icon, display_text)
            act_tag_map[act] = tag

        menu.addSeparator()
        create_icon = get_status_icon("tags/tag.svg", "#C2410C" if self.is_dark else "#BA3F1A", size=16)
        act_create = menu.addAction(create_icon, "+ Create Tag...")

        menu_size = menu.sizeHint()
        btn_pos = self.row_tag_btn.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(btn_pos.x(), btn_pos.y() - menu_size.height() - 4)

        chosen = menu.exec(target_pos)
        if chosen == act_create:
            dlg = TagCreateDialog(repo, self, is_dark=self.is_dark)
            cal_pos = self.row_tag_btn.mapToGlobal(QPoint(0, 0))
            dlg.move(cal_pos.x() - 150, cal_pos.y() - 360)
            if dlg.exec() == QDialog.DialogCode.Accepted and hasattr(dlg, "created_tag") and dlg.created_tag and dlg.created_tag.id:
                new_tag = dlg.created_tag
                if new_tag.id not in current_tag_ids:
                    current_tag_ids.append(new_tag.id)
                    self.task.tags.append(new_tag)
                    self.task_tags_changed.emit(self.task_id, current_tag_ids)
                    self._update_badges()
        elif chosen in act_tag_map:
            tag = act_tag_map[chosen]
            if tag.id is not None:
                if tag.id in current_tag_ids:
                    current_tag_ids.remove(tag.id)
                    self.task.tags = [t for t in self.task.tags if t.id != tag.id]
                else:
                    current_tag_ids.append(tag.id)
                    self.task.tags.append(tag)
                self.task_tags_changed.emit(self.task_id, current_tag_ids)
                self._update_badges()

    def _pick_schedule(self) -> None:
        """Open menu to update schedule date for this task."""
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))
        icon_color = "#D4D4D8" if self.is_dark else "#18181B"

        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)

        act_today = menu.addAction(
            get_status_icon("icons/icons8-today-100.png", icon_color, 14),
            f"Today ({today.strftime('%b %d')})",
        )
        act_tomorrow = menu.addAction(
            get_status_icon("icons/icons8-plus-1-day-100.png", icon_color, 14),
            f"Tomorrow ({tomorrow.strftime('%b %d')})",
        )
        act_next_week = menu.addAction(
            get_status_icon("icons/icons8-week-view-100.png", icon_color, 14),
            f"Next Week ({next_week.strftime('%b %d')})",
        )
        menu.addSeparator()
        act_pick = menu.addAction(get_status_icon("icons/schedule.svg", icon_color, 14), "Pick Date...")

        if self.task.scheduled_date:
            menu.addSeparator()
            act_clear = menu.addAction(
                get_status_icon("icons/icons8-no-entry-100.png", icon_color, 14),
                "Clear Date",
            )
        else:
            act_clear = None

        menu_size = menu.sizeHint()
        btn_pos = self.schedule_btn.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(btn_pos.x(), btn_pos.y() - menu_size.height() - 4)

        action = menu.exec(target_pos)
        if action == act_today:
            new_date = today.strftime("%Y-%m-%d")
            self.task.scheduled_date = new_date
            self.schedule_changed.emit(self.task_id, new_date)
            self._update_badges()
        elif action == act_tomorrow:
            new_date = tomorrow.strftime("%Y-%m-%d")
            self.task.scheduled_date = new_date
            self.schedule_changed.emit(self.task_id, new_date)
            self._update_badges()
        elif action == act_next_week:
            new_date = next_week.strftime("%Y-%m-%d")
            self.task.scheduled_date = new_date
            self.schedule_changed.emit(self.task_id, new_date)
            self._update_badges()
        elif action == act_pick:
            init_dt = today
            if self.task.scheduled_date:
                try:
                    init_dt = date.fromisoformat(self.task.scheduled_date)
                except Exception:
                    pass
            dlg = CalendarPopupDialog(init_dt, self, is_dark=self.is_dark)
            cal_pos = self.schedule_btn.mapToGlobal(QPoint(0, 0))
            dlg.move(cal_pos.x() - 100, cal_pos.y() - 360)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_date = dlg.selected_date.strftime("%Y-%m-%d")
                self.task.scheduled_date = new_date
                self.schedule_changed.emit(self.task_id, new_date)
                self._update_badges()
        elif act_clear and action == act_clear:
            self.task.scheduled_date = None
            self.schedule_changed.emit(self.task_id, "clear")
            self._update_badges()

    def _pick_repeat(self) -> None:
        """Open menu to update repeat mode for this task."""
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))
        icon_color = "#D4D4D8" if self.is_dark else "#18181B"

        act_none = menu.addAction(
            get_status_icon("icons/icons8-no-entry-100.png", icon_color, 14),
            "None (One-time)",
        )
        act_daily = menu.addAction(get_status_icon("icons/repeat.svg", icon_color, 14), "Daily (Every day)")
        act_weekdays = menu.addAction(get_status_icon("icons/repeat.svg", icon_color, 14), "Weekdays (Mon - Fri)")
        act_weekends = menu.addAction(get_status_icon("icons/repeat.svg", icon_color, 14), "Weekends (Sat - Sun)")

        menu_size = menu.sizeHint()
        btn_pos = self.repeat_btn.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(btn_pos.x(), btn_pos.y() - menu_size.height() - 4)

        action = menu.exec(target_pos)
        mode = None
        if action == act_none:
            mode = "none"
        elif action == act_daily:
            mode = "daily"
        elif action == act_weekdays:
            mode = "weekdays"
        elif action == act_weekends:
            mode = "weekends"

        if mode is not None:
            self.task.repeat_mode = mode
            self.repeat_changed.emit(self.task_id, mode)
            self._update_badges()

    def _on_status_combo_changed(self, index: int) -> None:
        """Handle status selection change from the dropdown."""
        text = self.status_combo.currentText()
        if text in ("In progress", "In Progress"):
            new_status = "in_progress"
            self.task.completed_at = None
        elif text == "Completed":
            new_status = "done"
            if not self.task.completed_at:
                self.task.completed_at = datetime.now()
            if self.task.is_timer_running:
                delta = int((datetime.now() - self.task.timer_started_at).total_seconds())
                self.task.duration_seconds += max(0, delta)
                self.task.timer_started_at = None
        elif text == "Cancelled":
            new_status = "cancelled"
            if not self.task.completed_at:
                self.task.completed_at = datetime.now()
            if self.task.is_timer_running:
                delta = int((datetime.now() - self.task.timer_started_at).total_seconds())
                self.task.duration_seconds += max(0, delta)
                self.task.timer_started_at = None
        else:
            new_status = "not_started"
            self.task.completed_at = None

        self.task.status = new_status
        self._update_status_ui(new_status)
        self.status_toggled.emit(self.task_id, new_status)

    def _on_checkbox_toggled(self, checked: bool) -> None:
        new_status = "done" if checked else "not_started"
        if checked:
            if not self.task.completed_at:
                self.task.completed_at = datetime.now()
            if self.task.is_timer_running:
                delta = int((datetime.now() - self.task.timer_started_at).total_seconds())
                self.task.duration_seconds += max(0, delta)
                self.task.timer_started_at = None
        else:
            self.task.completed_at = None
        self.task.status = new_status
        self._update_status_ui(new_status)
        self.status_toggled.emit(self.task_id, new_status)

    def _update_status_ui(self, status: str) -> None:
        """Synchronize task checkbox, label text decorations, and status dropdown."""
        is_done = status in ("done", "completed")
        is_cancelled = status in ("cancelled", "canceled")
        is_in_progress = status in ("in_progress", "pending", "ongoing")

        # Time metadata display (e.g. (1:36 PM - 1:57 PM) or (Oct 1, 1:36 PM - Oct 5, 1:57 PM))
        self.time_label.setText(
            format_task_time_tracking(
                created_at=self.task.created_at,
                completed_at=self.task.completed_at,
                is_done=is_done,
                is_cancelled=is_cancelled,
            )
        )

        # Sync checkbox state without re-triggering signal
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(is_done)
        self.checkbox.blockSignals(False)

        # Sync combobox current text without re-triggering signal
        self.status_combo.blockSignals(True)
        if is_in_progress:
            self.status_combo.setCurrentText("In progress")
        elif is_done:
            self.status_combo.setCurrentText("Completed")
        elif is_cancelled:
            self.status_combo.setCurrentText("Cancelled")
        else:
            self.status_combo.setCurrentText("Open")
        self.status_combo.blockSignals(False)

        # Text colors
        done_color = "#71717A" if self.is_dark else "#A1A1AA"
        active_color = "#F4F4F5" if self.is_dark else "#18181B"

        # Label styling
        if is_done:
            self.label.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    border: none;
                    color: {done_color};
                    text-decoration: line-through;
                    font-family: {FONT_SANS};
                    font-size: 13px;
                }}
            """)
        elif is_cancelled:
            self.label.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    border: none;
                    color: {done_color};
                    text-decoration: line-through;
                    font-style: italic;
                    font-family: {FONT_SANS};
                    font-size: 13px;
                }}
            """)
        elif is_in_progress:
            self.label.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    border: none;
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 13px;
                    font-weight: 600;
                }}
            """)
        else:
            self.label.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    border: none;
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 13px;
                    font-weight: 500;
                }}
            """)

        # Dropdown popup & monochrome styling without colored fills
        hover_bg = "#2E2E33" if self.is_dark else "#EAEAEB"
        hover_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        combo_popup_bg = "#1E1E22" if self.is_dark else "#FFFFFF"
        combo_popup_text = "#F4F4F5" if self.is_dark else "#18181B"
        combo_popup_border = "#333338" if self.is_dark else "#E4E4E7"
        combo_popup_sel_bg = "rgba(194, 65, 12, 0.22)" if self.is_dark else "#FEECE5"
        combo_popup_sel_text = "#FFAB91" if self.is_dark else "#BA3F1A"

        self.status_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: transparent;
                color: {combo_popup_text};
                border: 1px solid transparent;
                border-radius: 6px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
                padding: 2px 20px 2px 6px;
                min-height: 22px;
            }}
            QComboBox:hover {{
                background-color: {hover_bg};
                border: 1px solid {hover_border};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {combo_popup_bg};
                color: {combo_popup_text};
                border: 1px solid {combo_popup_border};
                border-radius: 8px;
                selection-background-color: {combo_popup_sel_bg};
                selection-color: {combo_popup_sel_text};
                padding: 4px;
                font-family: {FONT_SANS};
                font-size: 11px;
            }}
        """)
        self._update_badges()
        if hasattr(self, "stopwatch_widget"):
            self.stopwatch_widget.refresh()

    def start_renaming(self) -> None:
        """Enter inline task renaming mode."""
        self.edit_input.setText(self.task.title)
        self.label.setVisible(False)
        self.edit_input.setVisible(True)
        self.edit_input.setFocus()
        self.edit_input.selectAll()

    def _finish_renaming(self) -> None:
        """Save renamed task title."""
        if self.edit_input.isHidden():
            return
        new_title = self.edit_input.text().strip()
        self.edit_input.setVisible(False)
        self.label.setVisible(True)
        if new_title and new_title != self.task.title:
            self.task.title = new_title
            self.label.setText(new_title)
            self.task_renamed.emit(self.task_id, new_title)

    def _on_delete_clicked(self) -> None:
        """Trigger task deletion request."""
        self.action_requested.emit("delete", self.task_id)

    def _cancel_renaming(self) -> None:
        """Cancel inline task renaming."""
        self.edit_input.setText(self.task.title)
        self.edit_input.setVisible(False)
        self.label.setVisible(True)

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))

        # Theme-aware icon color
        icon_color = "#D4D4D8" if self.is_dark else "#18181B"
        delete_color = "#EF4444"

        action_rename = menu.addAction(
            get_status_icon("icons/rename.svg", icon_color, 14), "Rename Task"
        )
        action_schedule = menu.addAction(
            get_status_icon("icons/schedule.svg", icon_color, 14), "Schedule Task..."
        )
        action_repeat = menu.addAction(
            get_status_icon("icons/repeat.svg", icon_color, 14), "Repeat Task..."
        )
        action_add_sub = menu.addAction(
            get_status_icon("icons/subtask.svg", icon_color, 14), "Add Subtask"
        )
        action_tags = menu.addAction(
            get_status_icon("icons/tag.svg", icon_color, 14), "Manage Tags..."
        )
        menu.addSeparator()

        # "Move to Section" submenu
        move_icon = get_status_icon("icons/move.svg", icon_color, 14)
        section_menu = menu.addMenu(move_icon, "Move to Section")
        section_menu.setStyleSheet(get_context_menu_style(self.is_dark))
        curr_proj = self.task.project_tag or "General"

        for proj in self.all_projects:
            act = section_menu.addAction(f"Section: {proj}")
            if proj == curr_proj:
                act.setEnabled(False)
            act.triggered.connect(lambda checked, p=proj: self.project_changed.emit(self.task_id, p))

        section_menu.addSeparator()
        action_new_sec = section_menu.addAction("+ Create New Section...")

        menu.addSeparator()
        action_delete = menu.addAction(
            get_status_icon("icons/delete.svg", delete_color, 14), "Delete Task"
        )

        action = menu.exec(self.mapToGlobal(pos))
        if action == action_rename:
            self.start_renaming()
        elif action == action_schedule:
            self._pick_schedule()
        elif action == action_repeat:
            self._pick_repeat()
        elif action == action_add_sub:
            self._toggle_subtask_input(force_show=True)
        elif action == action_tags:
            self._on_manage_tags_clicked()
        elif action == action_new_sec:
            name, color, desc, kws, ok = CreateSectionDialog.get_section_details(self)
            if ok and name.strip():
                clean_name = name.strip()
                StorageRepository().create_or_update_project(
                    clean_name,
                    kws or [clean_name.lower()],
                    color=color,
                    description=desc,
                )
                self.project_changed.emit(self.task_id, clean_name)
        elif action == action_delete:
            self.action_requested.emit("delete", self.task_id)


class NoteRowWidget(QWidget):
    """
    Single quick work note row featuring:
    - Completion checkbox
    - Note content
    - Clickable section tag with right-click context menu and section switching
    - Timestamp
    - Delete button ('x')
    """

    toggled = pyqtSignal(int, bool)  # note_id, is_completed
    delete_requested = pyqtSignal(int)  # note_id
    project_changed = pyqtSignal(int, str)  # note_id, new_project

    def __init__(self, note: NoteRecord, all_projects: List[str], parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.note = note
        self.note_id = note.id or 0
        self.all_projects = all_projects
        self.is_dark = is_dark

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 6, 4, 6)
        self.layout.setSpacing(10)

        self.checkbox = RoundedCheckbox(checked=note.is_completed, size=20, parent=self, is_dark=self.is_dark)
        self.checkbox.toggled.connect(self._on_toggled)
        self.layout.addWidget(self.checkbox)

        # Content column
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)

        self.label = QLabel(note.content)
        self.label.setFont(get_font(10))
        self._update_text_style(note.is_completed)
        content_layout.addWidget(self.label)

        # Meta row: tag + timestamp
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        tag_text = note.project_tag or "General"
        self.tag_btn = QPushButton(f"[{tag_text}]")
        self.tag_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.tag_btn.setToolTip("Click to change section")

        tag_color = "#60A5FA" if self.is_dark else "#2563EB"
        tag_hover_color = "#93C5FD" if self.is_dark else "#1D4ED8"
        tag_hover_bg = "rgba(59, 130, 246, 0.15)" if self.is_dark else "rgba(37, 99, 235, 0.08)"

        self.tag_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {tag_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 11px;
                font-weight: 600;
                padding: 1px 4px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {tag_hover_bg};
                color: {tag_hover_color};
            }}
        """)
        self.tag_btn.clicked.connect(self._show_section_menu)
        meta_layout.addWidget(self.tag_btn)

        time_str = note.created_at.strftime("%I:%M %p").lstrip("0")
        time_color = "#71717A" if self.is_dark else "#71717A"
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"""
            QLabel {{
                color: {time_color};
                font-family: {FONT_MONO};
                font-size: 11px;
            }}
        """)
        meta_layout.addWidget(time_lbl)
        meta_layout.addStretch()

        content_layout.addLayout(meta_layout)
        self.layout.addLayout(content_layout, stretch=1)

        # Delete button
        del_btn = QPushButton("x")
        del_btn.setFixedSize(18, 18)
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn_color = "#71717A" if self.is_dark else "#71717A"
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {del_btn_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 11px;
                font-weight: bold;
                border-radius: 9px;
            }}
            QPushButton:hover {{
                color: #EF4444;
                background-color: rgba(239, 68, 68, 0.15);
            }}
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.note_id))
        self.layout.addWidget(del_btn)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_section_menu(self) -> None:
        """Show section selection menu when clicking on section badge."""
        self._open_section_menu(self.tag_btn.mapToGlobal(QPoint(0, self.tag_btn.height())))

    def _show_context_menu(self, pos: QPoint) -> None:
        """Show full context menu on right click."""
        self._open_context_menu(self.mapToGlobal(pos))

    def _open_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))

        icon_color = "#D4D4D8" if self.is_dark else "#44403C"
        delete_color = "#EF4444"

        move_icon = get_status_icon("icons/move.svg", icon_color, 14)
        section_menu = menu.addMenu(move_icon, "Move to Section")
        section_menu.setStyleSheet(get_context_menu_style(self.is_dark))
        curr_proj = self.note.project_tag or "General"

        for proj in self.all_projects:
            act = section_menu.addAction(f"Section: {proj}")
            if proj == curr_proj:
                act.setEnabled(False)
            act.triggered.connect(lambda checked, p=proj: self.project_changed.emit(self.note_id, p))

        section_menu.addSeparator()
        action_new_sec = section_menu.addAction("+ Create New Section...")

        menu.addSeparator()
        action_delete = menu.addAction(
            get_status_icon("icons/delete.svg", delete_color, 14), "Delete Note"
        )

        action = menu.exec(global_pos)
        if action == action_new_sec:
            name, color, desc, kws, ok = CreateSectionDialog.get_section_details(self)
            if ok and name.strip():
                clean_name = name.strip()
                StorageRepository().create_or_update_project(
                    clean_name,
                    kws or [clean_name.lower()],
                    color=color,
                    description=desc,
                )
                self.project_changed.emit(self.note_id, clean_name)
        elif action == action_delete:
            self.delete_requested.emit(self.note_id)

    def _open_section_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))

        curr_proj = self.note.project_tag or "General"
        for proj in self.all_projects:
            act = menu.addAction(f"Section: {proj}")
            if proj == curr_proj:
                act.setEnabled(False)
            act.triggered.connect(lambda checked, p=proj: self.project_changed.emit(self.note_id, p))

        menu.addSeparator()
        action_new_sec = menu.addAction("+ Create New Section...")

        action = menu.exec(global_pos)
        if action == action_new_sec:
            name, color, desc, kws, ok = CreateSectionDialog.get_section_details(self)
            if ok and name.strip():
                clean_name = name.strip()
                StorageRepository().create_or_update_project(
                    clean_name,
                    kws or [clean_name.lower()],
                    color=color,
                    description=desc,
                )
                self.project_changed.emit(self.note_id, clean_name)

    def _update_text_style(self, is_done: bool) -> None:
        done_color = "#71717A" if self.is_dark else "#A1A1AA"
        active_color = "#F4F4F5" if self.is_dark else "#18181B"

        if is_done:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {done_color};
                    text-decoration: line-through;
                    font-family: {FONT_SANS};
                    font-size: 13px;
                }}
            """)
        else:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 13px;
                    font-weight: 500;
                }}
            """)

    def _on_toggled(self, checked: bool) -> None:
        self._update_text_style(checked)
        self.toggled.emit(self.note_id, checked)


class NoteCardWidget(QWidget):
    """
    Card representing a permanent note in the left master list.
    Displays:
    - Note title (bold, prominent)
    - Pinned badge / indicator
    - Body preview snippet
    - Project badge and Tag pills
    - Formatted updated timestamp
    - Delete button
    """

    selected = pyqtSignal(int)  # note_id
    delete_requested = pyqtSignal(int)  # note_id
    pin_toggled = pyqtSignal(int, bool)  # note_id, is_pinned

    def __init__(
        self,
        note: NoteRecord,
        is_selected: bool = False,
        is_dark: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.note = note
        self.note_id = note.id or 0
        self.is_selected = is_selected
        self.is_dark = is_dark
        self._hovered = False

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(74)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        # Top row: Pinned badge, Title, Delete button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        if note.is_pinned:
            pin_lbl = QLabel("PINNED")
            pin_lbl.setFont(get_font(8, QFont.Weight.Bold))
            pin_lbl.setStyleSheet("color: #F97316; font-size: 8px; font-weight: bold;")
            top_row.addWidget(pin_lbl)

        title_text = note.title.strip() if note.title else "Untitled Note"
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setFont(get_font(10, QFont.Weight.Bold))
        top_row.addWidget(self.title_lbl, stretch=1)

        self.del_btn = QPushButton("x")
        self.del_btn.setFixedSize(16, 16)
        self.del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.del_btn.setToolTip("Delete note")
        del_color = "#71717A" if self.is_dark else "#A1A1AA"
        self.del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {del_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 10px;
                font-weight: bold;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                color: #EF4444;
                background-color: rgba(239, 68, 68, 0.15);
            }}
        """)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.note_id))
        top_row.addWidget(self.del_btn)
        layout.addLayout(top_row)

        # Snippet preview
        snippet = (note.content or "").strip().replace("\n", " ")
        if len(snippet) > 55:
            snippet = snippet[:52] + "..."
        if not snippet:
            snippet = "Empty note..."

        snip_color = "#A1A1AA" if self.is_dark else "#71717A"
        self.snip_lbl = QLabel(snippet)
        self.snip_lbl.setFont(get_font(9))
        self.snip_lbl.setStyleSheet(f"color: {snip_color}; font-size: 11px;")
        layout.addWidget(self.snip_lbl)

        # Bottom row: project badge, tag pills, time
        bot_row = QHBoxLayout()
        bot_row.setContentsMargins(0, 0, 0, 0)
        bot_row.setSpacing(4)

        if note.project_tag:
            p_badge = QLabel(f"[{note.project_tag}]")
            p_badge.setFont(get_font(8, QFont.Weight.Medium))
            p_badge.setStyleSheet(f"color: {'#38BDF8' if self.is_dark else '#0284C7'}; font-size: 9px;")
            bot_row.addWidget(p_badge)

        for tag in getattr(note, "tags", [])[:2]:
            t_badge = QLabel(tag.name)
            t_badge.setFont(get_font(8))
            c = tag.color or "#3B82F6"
            t_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(59, 130, 246, 0.15);
                    color: {c};
                    border: 1px solid rgba(59, 130, 246, 0.3);
                    border-radius: 4px;
                    padding: 0 4px;
                    font-size: 9px;
                }}
            """)
            bot_row.addWidget(t_badge)

        bot_row.addStretch()

        time_val = note.updated_at or note.created_at
        time_str = time_val.strftime("%b %d") if time_val else ""
        self.time_lbl = QLabel(time_str)
        self.time_lbl.setFont(get_font(8))
        self.time_lbl.setStyleSheet(f"color: {del_color}; font-size: 9px;")
        bot_row.addWidget(self.time_lbl)

        layout.addLayout(bot_row)
        self._update_style()

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self._update_style()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self._update_style()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self._update_style()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self._update_style()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.note_id)
        super().mousePressEvent(event)

    def _update_style(self) -> None:
        accent = "#C2410C" if self.is_dark else "#BA3F1A"
        if self.is_selected:
            bg = "rgba(194, 65, 12, 0.18)" if self.is_dark else "#FFF7ED"
            border = f"1.5px solid {accent}"
        elif self._hovered:
            bg = "#27272A" if self.is_dark else "#F4F4F6"
            border = f"1px solid {'#3F3F46' if self.is_dark else '#E4E4E7'}"
        else:
            bg = "#1F1F23" if self.is_dark else "#FFFFFF"
            border = f"1px solid {'#27272A' if self.is_dark else '#E5E5EA'}"

        text_color = "#F4F4F5" if self.is_dark else "#18181B"
        self.title_lbl.setStyleSheet(f"color: {text_color}; font-weight: 600; font-size: 11px;")
        self.setStyleSheet(f"""
            NoteCardWidget {{
                background-color: {bg};
                border: {border};
                border-radius: 8px;
            }}
        """)


class NoteEditorWidget(QWidget):
    """
    Document editor pane for permanent notes.
    Features:
    - Large editable title
    - Project icon button
    - Tag icon button
    - Pin toggle
    - Delete button
    - Multi-line Markdown editor (QPlainTextEdit)
    - Auto-save timer with debouncing (300ms)
    - Obsidian Vault synchronization
    - Word and character counter
    """

    note_updated = pyqtSignal(int)  # note_id
    note_deleted = pyqtSignal(int)  # note_id

    def __init__(
        self,
        repo: StorageRepository,
        is_dark: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.active_note: Optional[NoteRecord] = None
        self._is_loading: bool = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)
        self.main_layout.setSpacing(8)

        # Empty state container
        self.empty_widget = QWidget(self)
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)

        empty_fg = "#71717A" if self.is_dark else "#A1A1AA"
        empty_title = QLabel("Select a Note to Edit")
        empty_title.setFont(get_font(12, QFont.Weight.Bold))
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet(f"color: {empty_fg}; font-size: 13px; font-weight: 600;")
        empty_layout.addWidget(empty_title)

        empty_sub = QLabel("Select a note from the left, or enter a title above to create a new permanent note.")
        empty_sub.setFont(get_font(10))
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_sub.setStyleSheet(f"color: {empty_fg}; font-size: 11px;")
        empty_layout.addWidget(empty_sub)
        self.main_layout.addWidget(self.empty_widget, stretch=1)

        # Editor container
        self.editor_widget = QWidget(self)
        editor_layout = QVBoxLayout(self.editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)

        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)

        # Note title input
        self.title_input = QLineEdit()
        self.title_input.setFont(get_font(13, QFont.Weight.Bold))
        self.title_input.setPlaceholderText("Untitled Note")
        self.title_input.textChanged.connect(self._on_title_changed)
        toolbar.addWidget(self.title_input, stretch=1)

        # Project icon button
        self.project_btn = ProjectIconButton(is_dark=self.is_dark, parent=self.editor_widget)
        self.project_btn.project_selected.connect(self._on_project_selected)
        toolbar.addWidget(self.project_btn)

        # Tag icon button
        self.tag_btn = TagIconButton(repo=self.repo, is_dark=self.is_dark, parent=self.editor_widget)
        self.tag_btn.tags_selection_changed.connect(self._on_tags_selected)
        toolbar.addWidget(self.tag_btn)

        # Pin toggle button
        self.pin_btn = QPushButton("Pin")
        self.pin_btn.setFixedHeight(28)
        self.pin_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pin_btn.setFont(get_font(9, QFont.Weight.Medium))
        self.pin_btn.clicked.connect(self._toggle_pin)
        toolbar.addWidget(self.pin_btn)

        # Delete button
        self.del_btn = QPushButton("Delete")
        self.del_btn.setFixedHeight(28)
        self.del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.del_btn.setFont(get_font(9, QFont.Weight.Medium))
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 5px;
                padding: 0 8px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.15);
            }
        """)
        self.del_btn.clicked.connect(self._on_delete_clicked)
        toolbar.addWidget(self.del_btn)

        editor_layout.addLayout(toolbar)

        # Multi-line Markdown plain text editor
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(get_font(10))
        self.text_edit.setPlaceholderText("Start writing your note in Markdown... Use # Headers, - Lists, bold, and code")
        self.text_edit.textChanged.connect(self._on_content_changed)
        editor_layout.addWidget(self.text_edit, stretch=1)

        # Bottom info bar: Save status and Word count
        bot_bar = QHBoxLayout()
        bot_bar.setContentsMargins(4, 0, 4, 0)
        bot_bar.setSpacing(10)

        self.save_status_lbl = QLabel("Saved")
        self.save_status_lbl.setFont(get_font(9))
        self.save_status_lbl.setStyleSheet("color: #10B981; font-weight: 500;")
        bot_bar.addWidget(self.save_status_lbl)

        bot_bar.addStretch()

        self.stats_lbl = QLabel("0 words | 0 chars")
        self.stats_lbl.setFont(get_font(9))
        bot_bar.addWidget(self.stats_lbl)

        editor_layout.addLayout(bot_bar)
        self.main_layout.addWidget(self.editor_widget, stretch=1)

        # Auto-save debounce timer
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(300)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_active_note)

        self.editor_widget.setVisible(False)
        self.empty_widget.setVisible(True)
        self.set_theme(self.is_dark)

    def load_note(self, note: Optional[NoteRecord]) -> None:
        """Load a note into the editor or show empty state if None."""
        if self.save_timer.isActive():
            self.save_timer.stop()
            self._save_active_note()

        self._is_loading = True
        self.active_note = note
        if note is None:
            self.empty_widget.setVisible(True)
            self.editor_widget.setVisible(False)
            self._is_loading = False
            return

        self.empty_widget.setVisible(False)
        self.editor_widget.setVisible(True)

        self.title_input.setText(note.title or "")
        self.text_edit.setPlainText(note.content or "")

        # Set project and tags
        projects = self.repo.get_all_projects()
        self.project_btn.set_projects(projects)
        if note.project_tag:
            self.project_btn.setCurrentText(note.project_tag)

        tag_ids = [t.id for t in getattr(note, "tags", []) if t.id is not None]
        self.tag_btn.set_selected_tag_ids(tag_ids)

        self._update_pin_btn_style()
        self._update_stats()
        self.save_status_lbl.setText("Saved")
        self.save_status_lbl.setStyleSheet("color: #10B981; font-weight: 500;")
        self._is_loading = False

    def _on_title_changed(self) -> None:
        if self._is_loading or not self.active_note:
            return
        self.save_status_lbl.setText("Saving...")
        self.save_status_lbl.setStyleSheet("color: #F59E0B; font-weight: 500;")
        self.save_timer.start()

    def _on_content_changed(self) -> None:
        if self._is_loading or not self.active_note:
            return
        self._update_stats()
        self.save_status_lbl.setText("Saving...")
        self.save_status_lbl.setStyleSheet("color: #F59E0B; font-weight: 500;")
        self.save_timer.start()

    def _update_stats(self) -> None:
        text = self.text_edit.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        stats_color = "#71717A" if self.is_dark else "#A1A1AA"
        self.stats_lbl.setText(f"{words} words | {chars} chars")
        self.stats_lbl.setStyleSheet(f"color: {stats_color}; font-size: 10px;")

    def _on_project_selected(self, proj_name: str) -> None:
        if not self.active_note:
            return
        self.active_note.project_tag = proj_name
        self.save_timer.start()

    def _on_tags_selected(self, tag_ids: List[int]) -> None:
        if not self.active_note:
            return
        self.save_timer.start()

    def _toggle_pin(self) -> None:
        if not self.active_note:
            return
        self.active_note.is_pinned = not self.active_note.is_pinned
        self._update_pin_btn_style()
        self.save_timer.start()

    def _update_pin_btn_style(self) -> None:
        if not self.active_note:
            return
        is_pinned = self.active_note.is_pinned
        if is_pinned:
            self.pin_btn.setText("Pinned")
            self.pin_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(249, 115, 22, 0.15);
                    color: #F97316;
                    border: 1px solid rgba(249, 115, 22, 0.4);
                    border-radius: 5px;
                    padding: 0 8px;
                    font-weight: 600;
                }
            """)
        else:
            border_c = "#3F3F46" if self.is_dark else "#E4E4E7"
            fg_c = "#A1A1AA" if self.is_dark else "#71717A"
            self.pin_btn.setText("Pin")
            self.pin_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {fg_c};
                    border: 1px solid {border_c};
                    border-radius: 5px;
                    padding: 0 8px;
                }}
            """)

    def _save_active_note(self) -> None:
        if not self.active_note or self.active_note.id is None:
            return
        title = self.title_input.text().strip()
        content = self.text_edit.toPlainText()
        project = self.project_btn.currentText()
        tags = self.tag_btn.selected_tag_ids

        self.repo.update_permanent_note(
            note_id=self.active_note.id,
            title=title,
            content=content,
            project_tag=project,
            tag_ids=tags,
            is_pinned=self.active_note.is_pinned,
        )
        self.active_note.title = title
        self.active_note.content = content
        self.active_note.project_tag = project

        # Sync to Obsidian vault
        try:
            sync_permanent_note(self.active_note)
        except Exception:
            pass

        self.save_status_lbl.setText("Saved")
        self.save_status_lbl.setStyleSheet("color: #10B981; font-weight: 500;")
        self.note_updated.emit(self.active_note.id)

    def _on_delete_clicked(self) -> None:
        if not self.active_note or self.active_note.id is None:
            return
        nid = self.active_note.id
        self.repo.delete_permanent_note(nid)
        self.load_note(None)
        self.note_deleted.emit(nid)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.project_btn.set_theme(is_dark)
        self.tag_btn.set_theme(is_dark)

        title_bg = "#27272A" if is_dark else "#FFFFFF"
        title_fg = "#F4F4F5" if is_dark else "#18181B"
        title_border = "#3F3F46" if is_dark else "#E4E4E7"
        editor_bg = "#18181B" if is_dark else "#FFFFFF"
        editor_fg = "#F4F4F5" if is_dark else "#18181B"
        editor_border = "#27272A" if is_dark else "#E4E4E7"

        self.title_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {title_bg};
                color: {title_fg};
                border: 1px solid {title_border};
                border-radius: 6px;
                padding: 4px 8px;
                font-family: {FONT_SANS};
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {"#C2410C" if is_dark else "#BA3F1A"};
            }}
        """)
        self.text_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {editor_bg};
                color: {editor_fg};
                border: 1px solid {editor_border};
                border-radius: 8px;
                padding: 10px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QPlainTextEdit:focus {{
                border: 1.5px solid {"#C2410C" if is_dark else "#BA3F1A"};
            }}
        """)
        self._update_pin_btn_style()
        self._update_stats()


class PermanentNotesWorkspaceWidget(QWidget):
    """
    Two-pane knowledge base workspace for permanent long-form notes.
    Features:
    - Top creation bar: Title input + Project button + Tag button + Create button
    - Left Master List: Search filter + scrollable NoteCardWidget cards list
    - Right Detail Editor: NoteEditorWidget with real-time editing and debounced auto-save
    """

    note_selected = pyqtSignal(int)
    note_created = pyqtSignal(int)

    def __init__(
        self,
        repo: StorageRepository,
        is_dark: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.repo = repo
        self.is_dark = is_dark
        self.active_note_id: Optional[int] = None
        self.all_notes: List[NoteRecord] = []

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(10)

        # 1. Top Create Note Bar
        create_bar = QHBoxLayout()
        create_bar.setContentsMargins(0, 0, 0, 0)
        create_bar.setSpacing(8)

        self.note_title_input = QLineEdit()
        self.note_title_input.setPlaceholderText("+ Enter Note Title... (e.g. Architecture Decisions, API Contract)")
        self.note_title_input.returnPressed.connect(self._on_create_clicked)
        create_bar.addWidget(self.note_title_input, stretch=1)

        self.note_project_btn = ProjectIconButton(is_dark=self.is_dark, parent=self)
        create_bar.addWidget(self.note_project_btn)

        self.note_tag_btn = TagIconButton(repo=self.repo, is_dark=self.is_dark, parent=self)
        create_bar.addWidget(self.note_tag_btn)

        self.create_note_btn = QPushButton("Create Note")
        self.create_note_btn.setFont(get_font(11, QFont.Weight.Bold))
        self.create_note_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.create_note_btn.clicked.connect(self._on_create_clicked)
        create_bar.addWidget(self.create_note_btn)

        outer_layout.addLayout(create_bar)

        # 2. Main Body Split Pane (Left Master List + Right Detail Editor)
        body_widget = QWidget(self)
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        # Left Master Pane: Search + Notes Cards Scroll Area (260px wide)
        left_pane = QWidget()
        left_pane.setFixedWidth(260)
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes...")
        self.search_input.textChanged.connect(self._on_search_changed)
        left_layout.addWidget(self.search_input)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cards_scroll.setStyleSheet("background: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.cards_scroll.setWidget(self.cards_container)
        left_layout.addWidget(self.cards_scroll, stretch=1)
        body_layout.addWidget(left_pane)

        # Divider line
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedWidth(1)
        self.divider = div
        body_layout.addWidget(div)

        # Right Detail Pane: Document Editor
        self.editor = NoteEditorWidget(repo=self.repo, is_dark=self.is_dark, parent=body_widget)
        self.editor.note_updated.connect(self._on_note_saved)
        self.editor.note_deleted.connect(self._on_note_deleted)
        body_layout.addWidget(self.editor, stretch=1)

        outer_layout.addWidget(body_widget, stretch=1)

        self.set_theme(self.is_dark)

    def set_projects(self, projects: List[Any]) -> None:
        """Update projects list across child buttons."""
        self.note_project_btn.set_projects(projects)
        self.editor.project_btn.set_projects(projects)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.note_project_btn.set_theme(is_dark)
        self.note_tag_btn.set_theme(is_dark)
        self.editor.set_theme(is_dark)

        in_bg = "#27272A" if is_dark else "#FFFFFF"
        in_fg = "#F4F4F5" if is_dark else "#18181B"
        in_border = "#3F3F46" if is_dark else "#E4E4E7"
        focus_border = "#C2410C" if is_dark else "#BA3F1A"
        btn_bg = "#C2410C" if is_dark else "#BA3F1A"
        btn_hover = "#A3360E" if is_dark else "#9E3414"
        div_color = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"

        input_style = f"""
            QLineEdit {{
                background-color: {in_bg};
                color: {in_fg};
                border: 1px solid {in_border};
                border-radius: 8px;
                padding: 6px 10px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {focus_border};
            }}
        """
        self.note_title_input.setStyleSheet(input_style)
        self.search_input.setStyleSheet(input_style)

        self.create_note_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        self.divider.setStyleSheet(f"background-color: {div_color}; border: none;")

        # Update cards theme
        for i in range(self.cards_layout.count()):
            w = self.cards_layout.itemAt(i).widget()
            if isinstance(w, NoteCardWidget):
                w.set_theme(is_dark)

    def load_notes(self) -> None:
        """Fetch permanent notes and populate the cards list."""
        self.all_notes = self.repo.get_permanent_notes()
        self._render_cards()

    def _render_cards(self) -> None:
        """Render filtered note cards."""
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        query = self.search_input.text().strip().lower()
        filtered = self.all_notes
        if query:
            filtered = [
                n for n in self.all_notes
                if query in (n.title or "").lower()
                or query in (n.content or "").lower()
                or query in (n.project_tag or "").lower()
            ]

        if not filtered:
            empty_lbl = QLabel("No notes found.")
            empty_lbl.setFont(get_font(9))
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c = "#71717A" if self.is_dark else "#A1A1AA"
            empty_lbl.setStyleSheet(f"color: {c}; padding: 30px 0;")
            self.cards_layout.addWidget(empty_lbl)
            self.cards_layout.addStretch()
            if self.active_note_id is None:
                self.editor.load_note(None)
            return

        for note in filtered:
            is_sel = (note.id == self.active_note_id)
            card = NoteCardWidget(note, is_selected=is_sel, is_dark=self.is_dark, parent=self.cards_container)
            card.selected.connect(self.select_note)
            card.delete_requested.connect(self._on_note_deleted)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

        # If active note is not set, select first note
        if (self.active_note_id is None or not any(n.id == self.active_note_id for n in filtered)) and filtered:
            self.select_note(filtered[0].id)

    def select_note(self, note_id: int) -> None:
        """Select a note as active in the cards list and editor."""
        self.active_note_id = note_id
        matching = [n for n in self.all_notes if n.id == note_id]
        note = matching[0] if matching else None

        # Update card selection states
        for i in range(self.cards_layout.count()):
            w = self.cards_layout.itemAt(i).widget()
            if isinstance(w, NoteCardWidget):
                w.set_selected(w.note_id == note_id)

        self.editor.load_note(note)
        self.note_selected.emit(note_id)

    def _on_search_changed(self) -> None:
        self._render_cards()

    def _on_create_clicked(self) -> None:
        """Create new permanent note from top input bar."""
        title = self.note_title_input.text().strip()
        if not title:
            self.note_title_input.setFocus()
            return

        proj = self.note_project_btn.currentText()
        if proj == "+ Create Section..." or not proj:
            proj = "Work"
        tags = self.note_tag_btn.selected_tag_ids

        note_id = self.repo.create_permanent_note(
            title=title,
            content="",
            project_tag=proj,
            tag_ids=tags,
        )
        self.note_title_input.clear()
        self.note_tag_btn.clear_selection()
        self.load_notes()
        self.select_note(note_id)
        self.editor.text_edit.setFocus()
        self.note_created.emit(note_id)
        app_signals.note_created.emit(note_id)

    def _on_note_saved(self, note_id: int) -> None:
        """Refresh snippets on note cards after auto-save."""
        self.all_notes = self.repo.get_permanent_notes()
        for i in range(self.cards_layout.count()):
            w = self.cards_layout.itemAt(i).widget()
            if isinstance(w, NoteCardWidget) and w.note_id == note_id:
                matching = [n for n in self.all_notes if n.id == note_id]
                if matching:
                    w.note = matching[0]
                    w.title_lbl.setText(w.note.title or "Untitled Note")
                    snip = (w.note.content or "").strip().replace("\n", " ")
                    w.snip_lbl.setText(snip[:52] + "..." if len(snip) > 55 else (snip or "Empty note..."))
                    t_val = w.note.updated_at or w.note.created_at
                    w.time_lbl.setText(t_val.strftime("%b %d") if t_val else "")

    def _on_note_deleted(self, note_id: int) -> None:
        """Handle deletion of a note."""
        self.all_notes = [n for n in self.all_notes if n.id != note_id]
        if self.active_note_id == note_id:
            self.active_note_id = None
        self._render_cards()


class ProjectGroupWidget(QWidget):
    """Collapsible project section with SVG arrow header and divider line."""

    def __init__(self, project_name: str, tasks: List[TaskRecord], parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.project_name = project_name
        self.tasks = tasks
        self.is_dark = is_dark
        self._is_expanded = True

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 6, 0, 10)
        self.main_layout.setSpacing(6)

        # Header bar
        header_color = "#F4F4F5" if self.is_dark else "#18181B"
        header_hover = "#A1A1AA" if self.is_dark else "#71717A"

        self.header_btn = QPushButton(f"  {project_name}", self)
        self.header_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.header_btn.setAutoDefault(False)
        self.header_btn.setDefault(False)
        self.header_btn.setIcon(get_status_icon("icons/arrow-down-2-duotone.svg", header_color, 14))
        self.header_btn.setIconSize(QSize(14, 14))
        self.header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                text-align: left;
                font-family: {FONT_DISPLAY};
                font-size: 14px;
                font-weight: 700;
                color: {header_color};
                padding: 4px 0;
            }}
            QPushButton:hover {{
                color: {header_hover};
            }}
        """)
        self.header_btn.clicked.connect(self.toggle_collapse)
        self.main_layout.addWidget(self.header_btn)

        # Medium transparent divider line below project header
        divider_color = "rgba(255, 255, 255, 0.12)" if self.is_dark else "rgba(0, 0, 0, 0.10)"
        self.divider = QFrame(self)
        self.divider.setFixedHeight(1)
        self.divider.setObjectName("ProjectDivider")
        self.divider.setStyleSheet(f"background-color: {divider_color}; border: none;")
        self.main_layout.addWidget(self.divider)

        # Tasks container
        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(12, 6, 0, 0)
        self.tasks_layout.setSpacing(6)
        self.main_layout.addWidget(self.tasks_container)

    def toggle_collapse(self) -> None:
        """Toggle section expansion and swap down/up arrow icons."""
        self._is_expanded = not self._is_expanded
        self.tasks_container.setVisible(self._is_expanded)
        header_color = "#F4F4F5" if self.is_dark else "#18181B"
        icon_name = "icons/arrow-down-2-duotone.svg" if self._is_expanded else "icons/arrow-up-2-duotone.svg"
        self.header_btn.setIcon(get_status_icon(icon_name, header_color, 14))

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        header_color = "#F4F4F5" if self.is_dark else "#18181B"
        header_hover = "#A1A1AA" if self.is_dark else "#71717A"
        divider_color = "rgba(255, 255, 255, 0.12)" if self.is_dark else "rgba(0, 0, 0, 0.10)"
        self.header_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                text-align: left;
                font-family: {FONT_DISPLAY};
                font-size: 14px;
                font-weight: 700;
                color: {header_color};
                padding: 4px 0;
            }}
            QPushButton:hover {{
                color: {header_hover};
            }}
        """)
        icon_name = "icons/arrow-down-2-duotone.svg" if self._is_expanded else "icons/arrow-up-2-duotone.svg"
        self.header_btn.setIcon(get_status_icon(icon_name, header_color, 14))
        if hasattr(self, "divider"):
            self.divider.setStyleSheet(f"background-color: {divider_color}; border: none;")


class QuickEntryDialog(QDialog):
    """
    Refined WizDesk workspace:
    - Outer Top Bar: Window Controls (Theme Toggle, Minimize, Maximize, Close).
    - Inside Card (Light or Dark):
      1. Tasks | Quick Notes switcher
      2. Dynamic Date (e.g. August 31, Monday)
      3. Filter Capsule Bar (Task, In progress, Completed, Cancelled)
      4. Task / Subtask / Note scroll area
      5. Bottom Add Bar with Section picker and Create Section option
    """

    def __init__(self, state_machine: StateMachine, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.state_machine = state_machine
        self.repo = repository or StorageRepository()
        self.current_view_mode = "tasks"
        self.selected_date: date = date.today()
        self.repo.roll_recurring_tasks(today=self.selected_date)
        self.is_dark = (config.theme == "dark")
        self._pending_task_schedule: Optional[str] = None
        self._pending_task_repeat: str = "none"

        # Single-shot debounce timer for syncing to Obsidian vault without freezing UI
        self._sync_timer = QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.setInterval(350)
        self._sync_timer.timeout.connect(lambda: sync_today_logs(emit_signal=False))

        # Window settings
        self.setWindowTitle("WizDesk - Workspace")
        self.setWindowIcon(get_app_icon("wiz-idle.svg"))
        screen = QGuiApplication.primaryScreen()
        avail_geo = screen.availableGeometry() if screen else None
        target_w = 920
        target_h = 680
        if avail_geo and avail_geo.height() < 740:
            target_h = min(680, max(560, avail_geo.height() - 60))
        self.setMinimumSize(780, min(560, target_h))
        self.resize(target_w, target_h)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        flags = Qt.WindowType.FramelessWindowHint
        if config.get("always_on_top", False):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        # Frameless window dragging state
        self._drag_start_pos: Optional[QPoint] = None
        self._window_start_pos: Optional[QPoint] = None
        self._is_dragging: bool = False

        # Main Outer Container Layout
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(12, 12, 12, 12)
        self.outer_layout.setSpacing(0)

        # Outer rounded card frame
        self.outer_frame = QFrame()
        self.outer_frame.setObjectName("outerFrame")

        # Add drop shadow
        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setBlurRadius(28)
        self._shadow_effect.setColor(QColor(0, 0, 0, 50 if self.is_dark else 35))
        self._shadow_effect.setOffset(0, 6)
        self.outer_frame.setGraphicsEffect(self._shadow_effect)

        self.outer_layout.addWidget(self.outer_frame)

        # Frame Split Layout: Left Sidebar + Right Workspace
        self.frame_layout = QHBoxLayout(self.outer_frame)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        self.frame_layout.setSpacing(0)

        # 1. Left Side Navigation Bar (190px or 58px)
        self.sidebar = SideNavBar(is_dark=self.is_dark, parent=self.outer_frame)
        self.sidebar.mode_changed.connect(self._set_view_mode)
        self.sidebar.theme_toggle_requested.connect(self.toggle_theme)
        self.sidebar.sidebar_toggled.connect(self._on_sidebar_toggled)
        self.frame_layout.addWidget(self.sidebar)

        # Backwards-compatible aliases for mode buttons
        self.tasks_mode_btn = self.sidebar.pills["tasks"]
        self.notes_mode_btn = self.sidebar.pills["notes"]
        self.activity_mode_btn = self.sidebar.pills["activity"]
        self.projects_mode_btn = self.sidebar.pills["projects"]
        self.settings_mode_btn = self.sidebar.pills["settings"]
        self.help_mode_btn = self.sidebar.pills["help"]
        self.mode_capsule = QFrame()
        self.mode_capsule.setObjectName("modeCapsule")
        self.mode_capsule.setVisible(False)
        self.brand_lbl = self.sidebar.brand_title

        # 2. Right Main Workspace Container (~710px)
        self.workspace_container = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_container)
        self.workspace_layout.setContentsMargins(16, 12, 16, 14)
        self.workspace_layout.setSpacing(8)

        # Top Bar: Dynamic Page Title + Contextual Header Actions + Window Controls
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(12)

        # Dynamic Page Title
        self.page_title_lbl = QLabel("Tasks & To-Dos")
        self.page_title_lbl.setFont(get_font(13, QFont.Weight.Bold, display=True))
        top_bar.addWidget(self.page_title_lbl)

        # Contextual Date Header (visible in tasks & activity)
        self.date_header_container = QWidget()
        date_header_layout = QHBoxLayout(self.date_header_container)
        date_header_layout.setContentsMargins(0, 0, 0, 0)
        date_header_layout.setSpacing(6)

        self.prev_day_btn = QPushButton("<")
        self.prev_day_btn.setFixedSize(26, 26)
        self.prev_day_btn.setToolTip("Previous Day")
        self.prev_day_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_day_btn.clicked.connect(self._on_prev_day)
        date_header_layout.addWidget(self.prev_day_btn)

        self.date_btn = QPushButton()
        self.date_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.date_btn.setToolTip("Click to open calendar")
        self.date_btn.clicked.connect(self._open_calendar)
        date_header_layout.addWidget(self.date_btn)

        self.next_day_btn = QPushButton(">")
        self.next_day_btn.setFixedSize(26, 26)
        self.next_day_btn.setToolTip("Next Day")
        self.next_day_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_day_btn.clicked.connect(self._on_next_day)
        date_header_layout.addWidget(self.next_day_btn)

        self.today_pill_btn = QPushButton("Today")
        self.today_pill_btn.setFixedHeight(24)
        self.today_pill_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.today_pill_btn.clicked.connect(self._on_today_clicked)
        self.today_pill_btn.setVisible(False)
        date_header_layout.addWidget(self.today_pill_btn)

        top_bar.addStretch()

        # Window Control Buttons (-, x) - enlarged to 28x28 with refined symbols
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        # Preserved hidden for backwards compatibility with tests and signals
        self.theme_btn = QPushButton("☀" if self.is_dark else "☾")
        self.theme_btn.hide()

        self.min_btn = QPushButton("−")
        self.min_btn.setFixedSize(28, 28)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.setAutoDefault(False)
        self.min_btn.setDefault(False)
        self.min_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.min_btn.clicked.connect(self._on_minimize_clicked)
        controls_layout.addWidget(self.min_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setAutoDefault(False)
        self.close_btn.setDefault(False)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.close_btn)

        top_bar.addLayout(controls_layout)
        self.workspace_layout.addLayout(top_bar)

        # Initialize date display
        self._update_date_display()

        # --- Inner Canvas Card ---
        self.inner_card = QFrame()
        self.inner_card.setObjectName("innerCard")
        self.inner_layout = QVBoxLayout(self.inner_card)
        self.inner_layout.setContentsMargins(14, 10, 14, 10)
        self.inner_layout.setSpacing(12)

        # Contextual Date Header inside inner card (visible in tasks, notes, activity)
        self.inner_layout.addWidget(self.date_header_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Stacked Widget for Pages
        self.stack = QStackedWidget()

        # ==========================================
        # PAGE 1: TASKS VIEW
        # ==========================================
        self.tasks_page = QWidget()
        tasks_page_layout = QVBoxLayout(self.tasks_page)
        tasks_page_layout.setContentsMargins(0, 10, 0, 0)
        tasks_page_layout.setSpacing(12)

        # 3. Status Filter Capsule Bar (Below the Date)
        self.filter_bar = SegmentedFilterBar(is_dark=self.is_dark)
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        tasks_page_layout.addWidget(self.filter_bar)

        # Hidden tag filter helper retained for internal/test compatibility
        self.tag_filter_bar = TagFilterBar(self.repo, is_dark=self.is_dark, parent=self.tasks_page)
        self.tag_filter_bar.tag_selected.connect(self._on_tag_filter_changed)
        self.tag_filter_bar.hide()

        # 4. Scrollable Tasks Area (Without visible scrollbar)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.scroll_area.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        self.scroll_area.setStyleSheet("""
            QScrollArea, QScrollArea > QWidget > QWidget {
                background: transparent;
                border: none;
            }
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        tasks_page_layout.addWidget(self.scroll_area, stretch=1)

        # 5. Bottom Add Task Bar with Project Button, Tag Button, Schedule, Repeat & Add Button
        add_task_layout = QHBoxLayout()
        add_task_layout.setSpacing(6)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("+ Add task... (Press Enter)")
        self.add_input.returnPressed.connect(self._on_quick_add_task)
        add_task_layout.addWidget(self.add_input, stretch=1)

        self.project_btn = ProjectIconButton(is_dark=self.is_dark, parent=self.tasks_page)
        self.project_btn.create_project_requested.connect(self._on_create_project_requested)
        add_task_layout.addWidget(self.project_btn)
        # Compatibility alias for existing tests and methods
        self.project_combo = self.project_btn

        self.tag_btn = TagIconButton(self.repo, is_dark=self.is_dark, parent=self.tasks_page)
        add_task_layout.addWidget(self.tag_btn)

        self.add_schedule_btn = ScheduleIconButton(is_dark=self.is_dark, parent=self.tasks_page)
        self.add_schedule_btn.clicked.connect(self._pick_quick_add_schedule)
        add_task_layout.addWidget(self.add_schedule_btn)

        self.add_repeat_btn = RepeatIconButton(is_dark=self.is_dark, parent=self.tasks_page)
        self.add_repeat_btn.clicked.connect(self._pick_quick_add_repeat)
        add_task_layout.addWidget(self.add_repeat_btn)

        self.add_task_btn = QPushButton("Add")
        self.add_task_btn.setFont(get_font(12, QFont.Weight.Bold))
        self.add_task_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_task_btn.clicked.connect(self._on_quick_add_task)
        add_task_layout.addWidget(self.add_task_btn)

        tasks_page_layout.addLayout(add_task_layout)
        self.stack.addWidget(self.tasks_page)

        # ==========================================
        # PAGE 2: PERMANENT NOTES WORKSPACE
        # ==========================================
        self.notes_page = QWidget()
        notes_page_layout = QVBoxLayout(self.notes_page)
        notes_page_layout.setContentsMargins(0, 4, 0, 0)
        notes_page_layout.setSpacing(0)

        self.notes_workspace = PermanentNotesWorkspaceWidget(
            self.repo,
            is_dark=self.is_dark,
            parent=self.notes_page,
        )
        notes_page_layout.addWidget(self.notes_workspace)
        self.stack.addWidget(self.notes_page)

        # Backward compatibility aliases for existing tests and dialog interactions
        self.notes_scroll = self.notes_workspace.cards_scroll
        self.notes_content_widget = self.notes_workspace.cards_container
        self.notes_content_layout = self.notes_workspace.cards_layout
        self.note_input = self.notes_workspace.note_title_input
        self.note_project_combo = self.notes_workspace.note_project_btn
        self.add_note_btn = self.notes_workspace.create_note_btn

        # 3. Dedicated Calendar & Scheduling Page
        self.calendar_view = CalendarView(self.repo, is_dark=self.is_dark, parent=self.stack)
        self.calendar_view.task_created.connect(self._on_calendar_task_activity)
        self.calendar_view.task_updated.connect(self._on_calendar_task_activity)
        self.stack.addWidget(self.calendar_view)

        # 4. Activity Timeline Page
        self.timeline_view = TimelineView(self.repo, is_dark=self.is_dark, parent=self.stack)
        self.stack.addWidget(self.timeline_view)

        # 5. Projects Dashboard Page
        self.project_dashboard_view = ProjectDashboardView(self.repo, parent=self.stack, is_dark=self.is_dark)
        self.project_dashboard_view.project_changed.connect(self._populate_projects)
        self.stack.addWidget(self.project_dashboard_view)

        # 5. Embedded Settings Page
        self.settings_view = SettingsView(self.repo, is_dark=self.is_dark, parent=self.stack)
        self.settings_view.projects_changed.connect(self._populate_projects)
        self.stack.addWidget(self.settings_view)

        # 6. Embedded Help & Documentation Page
        self.help_faq_view = HelpFaqView(is_dark=self.is_dark, parent=self.stack)
        self.help_faq_view.open_settings_requested.connect(self._on_open_settings_category)
        self.stack.addWidget(self.help_faq_view)

        self.inner_layout.addWidget(self.stack, stretch=1)
        self.workspace_layout.addWidget(self.inner_card, stretch=1)
        self.frame_layout.addWidget(self.workspace_container, stretch=1)

        # Drag state for frameless window movement
        self._drag_pos = QPoint()

        # Connect broadcast signals for real-time workspace synchronization
        app_signals.theme_changed.connect(self.apply_theme)
        app_signals.always_on_top_changed.connect(self._apply_always_on_top)
        app_signals.session_polled.connect(self._on_background_session_polled)
        app_signals.task_created.connect(self._on_background_task_activity)
        app_signals.task_updated.connect(self._on_background_task_activity)
        app_signals.task_completed.connect(self._on_background_task_activity)
        app_signals.projects_changed.connect(self._on_projects_changed_sync)
        app_signals.tags_changed.connect(self._on_tags_changed_sync)

        self.active_tag_filter_id: Optional[int] = None

        # Apply initial theme stylesheet
        self.apply_theme(config.theme)

        # Seed sample projects/tasks if repository is completely blank
        self._seed_initial_data_if_empty()

        # Initial populate & render
        self._populate_projects()
        self._set_view_mode("tasks")

        # Restore saved sidebar collapsed state
        if config.sidebar_collapsed:
            self.sidebar.set_collapsed(True)

        # Disable autoDefault and default on all child QPushButton widgets to prevent Enter key activations
        for btn in self.findChildren(QPushButton):
            btn.setAutoDefault(False)
            btn.setDefault(False)

    def _on_sidebar_toggled(self, collapsed: bool) -> None:
        """Handle sidebar toggle and persist user preference."""
        config.set_sidebar_collapsed(collapsed)
        # Defer the heavy visual refresh to the next event-loop iteration so
        # the layout system finishes recalculating *before* we flush the
        # QGraphicsDropShadowEffect pixel cache.  Without the deferral the
        # effect may snapshot an intermediate (half-laid-out) state.
        QTimer.singleShot(0, self._flush_sidebar_repaint)

    def _flush_sidebar_repaint(self) -> None:
        """Force layout recalculation and recreate the drop shadow effect.

        QGraphicsDropShadowEffect renders all children of outer_frame into an
        internal offscreen pixmap.  When child widgets resize (sidebar
        collapse/expand) this buffer retains stale pixels from the *previous*
        layout, producing a visible ghosting flash on Windows DWM combined with
        WA_TranslucentBackground.  The only reliable cross-platform fix is to
        detach and re-create the effect, which forces Qt to allocate a fresh
        buffer at the correct dimensions.
        """
        # 1. Force parent layout recalculation
        if hasattr(self, "frame_layout"):
            self.frame_layout.invalidate()
            self.frame_layout.activate()

        # 2. Recreate the shadow effect to flush its internal pixel cache
        if hasattr(self, "outer_frame"):
            self.outer_frame.setGraphicsEffect(None)
            self._shadow_effect = QGraphicsDropShadowEffect(self)
            self._shadow_effect.setBlurRadius(28)
            self._shadow_effect.setColor(
                QColor(0, 0, 0, 50 if self.is_dark else 35)
            )
            self._shadow_effect.setOffset(0, 6)
            self.outer_frame.setGraphicsEffect(self._shadow_effect)
            self.outer_frame.repaint()

        self.repaint()

    def _apply_always_on_top(self, always_on_top: bool) -> None:
        """Update window flags when Always On Top setting changes smoothly without glitching."""
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                if hwnd:
                    # HWND_TOPMOST (-1) if always_on_top else HWND_NOTOPMOST (-2)
                    # SWP_NOSIZE (1) | SWP_NOMOVE (2) | SWP_NOACTIVATE (0x10) | SWP_FRAMECHANGED (0x20) | SWP_SHOWWINDOW (0x40)
                    target_z = -1 if always_on_top else -2
                    ctypes.windll.user32.SetWindowPos(
                        hwnd,
                        target_z,
                        0, 0, 0, 0,
                        0x0001 | 0x0002 | 0x0010 | 0x0020 | 0x0040
                    )
            except Exception:
                pass
        elif self.isVisible():
            self.show()
        # Reinforce mascot companion visibility above workspace dialog
        app_signals.ensure_mascot_visible.emit()

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes and broadcast."""
        new_theme = "light" if self.is_dark else "dark"
        config.set_theme(new_theme)
        app_signals.theme_changed.emit(new_theme)

    def apply_theme(self, theme_name: str) -> None:
        """Dynamically apply Light or Dark theme styling to the entire workspace."""
        self.is_dark = (theme_name.lower() == "dark")
        self.theme_btn.setText("☀" if self.is_dark else "☾")
        self.theme_btn.setToolTip("Switch to Light Mode" if self.is_dark else "Switch to Dark Mode")

        # Update sidebar theme
        if hasattr(self, "sidebar"):
            self.sidebar.set_theme(self.is_dark)

        # Update filter bar theme
        if hasattr(self, "filter_bar"):
            self.filter_bar.set_dark_mode(self.is_dark)

        # Update tag filter bar and bottom add buttons
        if hasattr(self, "tag_filter_bar"):
            self.tag_filter_bar.set_dark_mode(self.is_dark)
        if hasattr(self, "project_btn"):
            self.project_btn.set_theme(self.is_dark)
        if hasattr(self, "tag_btn"):
            self.tag_btn.set_theme(self.is_dark)

        # Color tokens - Brand aligned & Crisp Modern Light Mode
        outer_bg = "#121214" if self.is_dark else "#F4F4F6"
        outer_border = "#27272A" if self.is_dark else "#E4E4E7"
        inner_bg = "#18181B" if self.is_dark else "#F0F0F2"
        inner_border = "#27272A" if self.is_dark else "#E4E4E7"
        page_title_color = "#F4F4F5" if self.is_dark else "#18181B"
        ctrl_btn_color = "#A1A1AA" if self.is_dark else "#71717A"
        ctrl_btn_hover_bg = "rgba(255, 255, 255, 0.08)" if self.is_dark else "rgba(0, 0, 0, 0.05)"
        ctrl_btn_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        mode_capsule_bg = "#27272A" if self.is_dark else "#F0F0F2"
        day_btn_color = "#A1A1AA" if self.is_dark else "#71717A"
        day_btn_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        day_btn_hover_bg = "#27272A" if self.is_dark else "#EAEAEB"
        day_btn_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        date_btn_color = "#F4F4F5" if self.is_dark else "#18181B"
        today_pill_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        today_pill_color = "#FFFFFF"
        today_pill_hover = "#A3360E" if self.is_dark else "#9E3414"
        input_bg = "#27272A" if self.is_dark else "#FFFFFF"
        input_color = "#F4F4F5" if self.is_dark else "#18181B"
        input_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        input_focus_border = "#C2410C" if self.is_dark else "#BA3F1A"
        combo_popup_bg = "#18181B" if self.is_dark else "#FFFFFF"
        combo_popup_border = "#27272A" if self.is_dark else "#E4E4E7"
        combo_popup_sel_bg = "rgba(194, 65, 12, 0.22)" if self.is_dark else "#FEECE5"
        combo_popup_sel_text = "#FFAB91" if self.is_dark else "#BA3F1A"
        btn_action_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        btn_action_color = "#FFFFFF"
        btn_action_hover = "#A3360E" if self.is_dark else "#9E3414"

        # Update shadow effect color to match new theme
        if hasattr(self, "_shadow_effect"):
            self._shadow_effect.setColor(
                QColor(0, 0, 0, 50 if self.is_dark else 35)
            )

        # Style QToolTip so tooltips never render with native Windows Vista white/yellow background
        tooltip_bg = "#18181B" if self.is_dark else "#FFFFFF"
        tooltip_color = "#F4F4F5" if self.is_dark else "#18181B"
        tooltip_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        self.setStyleSheet(f"""
            QToolTip {{
                background-color: {tooltip_bg};
                color: {tooltip_color};
                border: 1px solid {tooltip_border};
                border-radius: 6px;
                padding: 4px 8px;
                font-family: {FONT_SANS};
                font-size: 11px;
            }}
        """)

        # 1. Outer Frame & Inner Card
        self.outer_frame.setStyleSheet(f"""
            QFrame#outerFrame {{
                background-color: {outer_bg};
                border: 1px solid {outer_border};
                border-radius: 20px;
            }}
        """)
        self.inner_card.setStyleSheet(f"""
            QFrame#innerCard {{
                background-color: {inner_bg};
                border-radius: 16px;
                border: 1px solid {inner_border};
            }}
        """)

        # 2. Window Controls & Title
        if hasattr(self, "page_title_lbl"):
            self.page_title_lbl.setStyleSheet(f"color: {page_title_color};")

        min_qss = f"""
            QPushButton {{
                background-color: transparent;
                color: {ctrl_btn_color};
                border: none;
                font-family: {FONT_SANS};
                font-size: 15px;
                font-weight: bold;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background-color: {ctrl_btn_hover_bg};
                color: {ctrl_btn_hover_color};
            }}
        """
        self.min_btn.setStyleSheet(min_qss)
        self.theme_btn.setStyleSheet(min_qss)

        close_hover_bg = "rgba(239, 68, 68, 0.20)" if self.is_dark else "rgba(239, 68, 68, 0.12)"
        close_hover_color = "#EF4444" if self.is_dark else "#DC2626"
        close_qss = f"""
            QPushButton {{
                background-color: transparent;
                color: {ctrl_btn_color};
                border: none;
                font-family: {FONT_SANS};
                font-size: 13px;
                font-weight: bold;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background-color: {close_hover_bg};
                color: {close_hover_color};
            }}
        """
        self.close_btn.setStyleSheet(close_qss)

        # 3. Mode Capsule (legacy compatibility)
        if hasattr(self, "mode_capsule"):
            self.mode_capsule.setStyleSheet(f"""
                QFrame#modeCapsule {{
                    background-color: {mode_capsule_bg};
                    border-radius: 9px;
                }}
            """)

        # 4. Date header
        day_nav_qss = f"""
            QPushButton {{
                background: transparent;
                color: {day_btn_color};
                border: 1px solid {day_btn_border};
                border-radius: 6px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {day_btn_hover_color};
                background-color: {day_btn_hover_bg};
                border-color: {input_focus_border};
            }}
        """
        self.prev_day_btn.setStyleSheet(day_nav_qss)
        self.next_day_btn.setStyleSheet(day_nav_qss)

        self.date_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {date_btn_color};
                border: none;
                font-family: {FONT_SANS};
                font-size: 13px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {day_btn_hover_bg};
            }}
        """)

        self.today_pill_btn.setFont(get_font(11, QFont.Weight.Bold))
        self.today_pill_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {today_pill_bg};
                color: {today_pill_color};
                border: none;
                border-radius: 6px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background-color: {today_pill_hover};
            }}
        """)

        # 5. Filter bar
        self.filter_bar.set_dark_mode(self.is_dark)

        # 6. Bottom Add Task / Note inputs & buttons
        input_qss = f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_color};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 8px 12px;
                font-family: {FONT_SANS};
                font-size: 13px;
                word-spacing: 1px;
            }}
            QLineEdit:focus {{
                background-color: {inner_bg};
                border: 1.5px solid {input_focus_border};
            }}
        """
        self.add_input.setStyleSheet(input_qss)
        self.note_input.setStyleSheet(input_qss)

        combo_qss = f"""
            QComboBox {{
                background-color: {input_bg};
                color: {input_color};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 24px 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 500;
                min-width: 130px;
            }}
            QComboBox:hover {{
                border-color: {input_focus_border};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {combo_popup_bg};
                color: {input_color};
                border: 1px solid {combo_popup_border};
                border-radius: 8px;
                selection-background-color: {combo_popup_sel_bg};
                selection-color: {combo_popup_sel_text};
                padding: 4px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
        """
        if hasattr(self, "project_combo"):
            if isinstance(self.project_combo, ProjectIconButton):
                self.project_combo.set_theme(self.is_dark)
            elif hasattr(self.project_combo, "setStyleSheet"):
                self.project_combo.set_theme(self.is_dark)
                self.project_combo.setStyleSheet(combo_qss)

        if hasattr(self, "note_project_combo"):
            if isinstance(self.note_project_combo, ProjectIconButton):
                self.note_project_combo.set_theme(self.is_dark)
            elif hasattr(self.note_project_combo, "setStyleSheet"):
                self.note_project_combo.set_theme(self.is_dark)
                self.note_project_combo.setStyleSheet(combo_qss)

        if hasattr(self, "notes_workspace"):
            self.notes_workspace.set_theme(self.is_dark)

        if hasattr(self, "add_schedule_btn"):
            self.add_schedule_btn.set_theme(self.is_dark)
        if hasattr(self, "add_repeat_btn"):
            self.add_repeat_btn.set_theme(self.is_dark)

        btn_action_qss = f"""
            QPushButton {{
                background-color: {btn_action_bg};
                color: {btn_action_color};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_action_hover};
            }}
        """
        self.add_task_btn.setFont(get_font(12, QFont.Weight.Bold))
        self.add_task_btn.setStyleSheet(btn_action_qss)
        self.add_note_btn.setFont(get_font(12, QFont.Weight.Bold))
        self.add_note_btn.setStyleSheet(btn_action_qss)

        # 7. Update timeline, project dashboard & settings view themes
        if hasattr(self, "timeline_view"):
            self.timeline_view.set_theme(self.is_dark)
        if hasattr(self, "calendar_view"):
            self.calendar_view.set_dark_mode(self.is_dark)
        if hasattr(self, "project_dashboard_view"):
            self.project_dashboard_view.set_theme(self.is_dark)
        if hasattr(self, "settings_view"):
            self.settings_view.set_theme(self.is_dark)
        if hasattr(self, "help_faq_view"):
            self.help_faq_view.set_theme(self.is_dark)

        # 8. Re-apply mode buttons
        self._set_view_mode(self.current_view_mode)

    def _set_view_mode(self, mode: str) -> None:
        """Switch between Tasks, Quick Notes, Activity Timeline, Projects, Settings, and Help mode."""
        self.current_view_mode = mode

        if hasattr(self, "sidebar"):
            self.sidebar.set_active_mode(mode)

        titles = {
            "tasks": "Tasks & To-Dos",
            "calendar": "Calendar & Schedule",
            "notes": "Quick Notes",
            "activity": "Activity Timeline",
            "projects": "Projects Dashboard",
            "settings": "Settings & Preferences",
            "help": "Help & Documentation",
        }
        if hasattr(self, "page_title_lbl"):
            self.page_title_lbl.setText(titles.get(mode, "WizDesk"))

        if hasattr(self, "date_header_container"):
            self.date_header_container.setVisible(mode not in ("projects", "settings", "help", "calendar"))

        if mode == "tasks":
            self.stack.setCurrentWidget(self.tasks_page)
            self.refresh_tasks()
        elif mode == "calendar" and hasattr(self, "calendar_view"):
            self.stack.setCurrentWidget(self.calendar_view)
            self.calendar_view.load_data()
        elif mode == "notes":
            self.stack.setCurrentWidget(self.notes_page)
            self.refresh_notes()
        elif mode == "activity" and hasattr(self, "timeline_view"):
            self.stack.setCurrentWidget(self.timeline_view)
            self.timeline_view.load_date(self.selected_date.strftime("%Y-%m-%d"))
        elif mode == "projects" and hasattr(self, "project_dashboard_view"):
            self.stack.setCurrentWidget(self.project_dashboard_view)
            self.project_dashboard_view.load_data()
        elif mode == "settings" and hasattr(self, "settings_view"):
            self.stack.setCurrentWidget(self.settings_view)
            self.settings_view.load_settings()
        elif mode == "help" and hasattr(self, "help_faq_view"):
            self.stack.setCurrentWidget(self.help_faq_view)
            self.help_faq_view.load_settings()

    def _on_open_settings_category(self, category: str) -> None:
        """Switch to settings view and activate requested category."""
        self._set_view_mode("settings")
        if hasattr(self, "settings_view"):
            self.settings_view.switch_to_category(category)

    def _seed_initial_data_if_empty(self) -> None:
        """Seed default project categories if database has no projects."""
        projects = self.repo.get_all_projects()
        if not projects:
            self.repo.create_or_update_project("Work", ["work", "code"])
            self.repo.create_or_update_project("Personal Projects", ["personal"])

    def _populate_projects(self) -> None:
        """Populate project choices with '+ Create Section...' option."""
        projects = self.repo.get_all_projects()
        names = [p.name for p in projects]
        if not names:
            names = ["Work", "Personal Projects"]

        if hasattr(self, "project_btn") and isinstance(self.project_btn, ProjectIconButton):
            self.project_btn.set_projects(projects)
        elif hasattr(self, "project_combo") and hasattr(self.project_combo, "clear"):
            current_sel = self.project_combo.currentText()
            self.project_combo.blockSignals(True)
            self.project_combo.clear()
            for name in names:
                self.project_combo.addItem(name)
            self.project_combo.insertSeparator(self.project_combo.count())
            self.project_combo.addItem("+ Create Section...")

            if current_sel and current_sel in names:
                self.project_combo.setCurrentText(current_sel)
            else:
                self.project_combo.setCurrentIndex(0)
            self.project_combo.blockSignals(False)

        if hasattr(self, "notes_workspace"):
            self.notes_workspace.set_projects(projects)

        if hasattr(self, "note_project_combo"):
            if isinstance(self.note_project_combo, ProjectIconButton):
                self.note_project_combo.set_projects(projects)
            elif hasattr(self.note_project_combo, "clear"):
                note_sel = self.note_project_combo.currentText()
                self.note_project_combo.blockSignals(True)
                self.note_project_combo.clear()
                for name in names:
                    self.note_project_combo.addItem(name)
                self.note_project_combo.insertSeparator(self.note_project_combo.count())
                self.note_project_combo.addItem("+ Create Section...")

                if note_sel and note_sel in names:
                    self.note_project_combo.setCurrentText(note_sel)
                else:
                    self.note_project_combo.setCurrentIndex(0)
                self.note_project_combo.blockSignals(False)

    def _on_create_project_requested(self) -> None:
        """Handle request to create a new section from project icon button."""
        name, color, desc, kws, ok = CreateSectionDialog.get_section_details(self)
        if ok and name.strip():
            clean_name = name.strip()
            self.repo.create_or_update_project(
                clean_name,
                kws or [clean_name.lower()],
                color=color,
                description=desc,
            )
            self._populate_projects()
            if hasattr(self, "project_btn"):
                self.project_btn.setCurrentText(clean_name)

    def _on_tag_filter_changed(self, tag_id: Optional[int]) -> None:
        """Handle tag filter chip selection."""
        self.active_tag_filter_id = tag_id
        self.refresh_tasks()

    def _on_tags_changed_sync(self) -> None:
        """Synchronize tag changes across filter chips and task rows."""
        if hasattr(self, "tag_filter_bar"):
            self.tag_filter_bar.rebuild_chips()
        if hasattr(self, "tag_btn"):
            self.tag_btn.update()
        if hasattr(self, "refresh_tasks"):
            self.refresh_tasks()

    def _on_task_tags_changed(self, task_id: int, tag_ids: List[int]) -> None:
        """Handle updating tags assigned to a task."""
        self.repo.set_task_tags(task_id, tag_ids)
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_project_combo_changed(self, index: int) -> None:
        """Handle selection of '+ Create Section...' in task project combo."""
        text = self.project_combo.currentText()
        if text == "+ Create Section...":
            name, color, desc, kws, ok = CreateSectionDialog.get_section_details(self)
            if ok and name.strip():
                clean_name = name.strip()
                self.repo.create_or_update_project(
                    clean_name,
                    kws or [clean_name.lower()],
                    color=color,
                    description=desc,
                )
                self._populate_projects()
                self.project_combo.setCurrentText(clean_name)
            else:
                if self.project_combo.count() > 0:
                    self.project_combo.setCurrentIndex(0)

    def _on_note_project_combo_changed(self, index: int) -> None:
        """Handle selection of '+ Create Section...' in note project combo."""
        text = self.note_project_combo.currentText()
        if text == "+ Create Section...":
            name, color, desc, kws, ok = CreateSectionDialog.get_section_details(self)
            if ok and name.strip():
                clean_name = name.strip()
                self.repo.create_or_update_project(
                    clean_name,
                    kws or [clean_name.lower()],
                    color=color,
                    description=desc,
                )
                self._populate_projects()
                self.note_project_combo.setCurrentText(clean_name)
            else:
                if self.note_project_combo.count() > 0:
                    self.note_project_combo.setCurrentIndex(0)

    def _on_filter_changed(self, filter_name: str) -> None:
        """Called when a segmented filter pill is clicked."""
        self._update_date_display()
        self.refresh_tasks()

    def _update_date_display(self) -> None:
        """Update date button label and 'Today' shortcut indicator."""
        date_str = self.selected_date.strftime("%B %d, %A")
        self.date_btn.setText(date_str)
        is_today = (self.selected_date == date.today())
        self.today_pill_btn.setVisible(not is_today)

    def showEvent(self, event) -> None:
        """Roll recurring tasks when opening or re-showing the dialog."""
        super().showEvent(event)
        self.repo.roll_recurring_tasks(today=date.today())
        if hasattr(self, "current_view_mode") and self.current_view_mode == "tasks":
            self.refresh_tasks()

    def set_selected_date(self, target_date: date) -> None:
        """Set the active view date and refresh tasks, notes, and activity timeline."""
        self.selected_date = target_date
        self.repo.roll_recurring_tasks(today=date.today())
        self._update_date_display()
        self.refresh_tasks()
        self.refresh_notes()
        if hasattr(self, "timeline_view"):
            self.timeline_view.load_date(self.selected_date.strftime("%Y-%m-%d"))
        if hasattr(self, "project_dashboard_view") and self.current_view_mode == "projects":
            self.project_dashboard_view.load_data()

    def _on_prev_day(self) -> None:
        """Navigate to previous day."""
        self.set_selected_date(self.selected_date - timedelta(days=1))

    def _on_next_day(self) -> None:
        """Navigate to next day."""
        self.set_selected_date(self.selected_date + timedelta(days=1))

    def _on_today_clicked(self) -> None:
        """Jump back to today."""
        self.set_selected_date(date.today())

    def _on_calendar_task_activity(self, task_id: int) -> None:
        """Handle task activity originating from Calendar view."""
        self.refresh_tasks()
        if hasattr(self, "project_dashboard_view") and self.current_view_mode == "projects":
            self.project_dashboard_view.load_data()

    def _on_background_session_polled(self, app_name: str, window_title: str, project_tag: str) -> None:
        """Handle background activity tracker polling to update active views in real-time."""
        if self.isVisible():
            if hasattr(self, "project_dashboard_view") and self.current_view_mode == "projects":
                self.project_dashboard_view.load_data()
            elif hasattr(self, "timeline_view") and self.current_view_mode == "activity" and self.selected_date == date.today():
                self.timeline_view.load_date(self.selected_date.strftime("%Y-%m-%d"))

    def _on_background_task_activity(self, task_id: int) -> None:
        """Refresh dashboard, calendar, or task views when tasks change."""
        if getattr(self, "_suppress_task_activity_sync", False):
            return
        if self.isVisible():
            if hasattr(self, "calendar_view") and self.current_view_mode == "calendar":
                self.calendar_view.load_data()
            if hasattr(self, "project_dashboard_view") and self.current_view_mode == "projects":
                self.project_dashboard_view.load_data()
            elif hasattr(self, "current_view_mode") and self.current_view_mode == "tasks":
                self.refresh_tasks()

    def _on_projects_changed_sync(self) -> None:
        """Handle real-time project synchronization across all views."""
        self._populate_projects()
        if hasattr(self, "refresh_tasks"):
            self.refresh_tasks()
        if hasattr(self, "refresh_notes"):
            self.refresh_notes()
        if hasattr(self, "project_dashboard_view"):
            self.project_dashboard_view.load_data()
        if hasattr(self, "timeline_view"):
            self.timeline_view.load_date(self.selected_date.strftime("%Y-%m-%d"))

    def _open_calendar(self) -> None:
        """Open popup calendar picker."""
        dlg = CalendarPopupDialog(self.selected_date, self, is_dark=self.is_dark)
        btn_pos = self.date_btn.mapToGlobal(QPoint(0, self.date_btn.height() + 4))
        x = btn_pos.x() + (self.date_btn.width() // 2) - (dlg.width() // 2)
        y = btn_pos.y()
        dlg.move(x, y)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.set_selected_date(dlg.selected_date)

    def _on_task_schedule_changed(self, task_id: int, sched_str: str) -> None:
        """Handle schedule date update on an existing task."""
        val = None if (sched_str == "" or sched_str.strip().lower() == "clear") else sched_str.strip()
        self.repo.update_task_schedule(task_id, scheduled_date=val or "")
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_task_repeat_changed(self, task_id: int, mode_str: str) -> None:
        """Handle repeat mode update on an existing task."""
        self.repo.update_task_schedule(task_id, repeat_mode=mode_str)
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _pick_quick_add_schedule(self) -> None:
        """Open popup menu to pick scheduled date for the new task."""
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))
        icon_color = "#D4D4D8" if self.is_dark else "#44403C"

        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)

        act_today = menu.addAction(
            get_status_icon("icons/icons8-today-100.png", icon_color, 14),
            f"Today ({today.strftime('%b %d')})",
        )
        act_tomorrow = menu.addAction(
            get_status_icon("icons/icons8-plus-1-day-100.png", icon_color, 14),
            f"Tomorrow ({tomorrow.strftime('%b %d')})",
        )
        act_next_week = menu.addAction(
            get_status_icon("icons/icons8-week-view-100.png", icon_color, 14),
            f"Next Week ({next_week.strftime('%b %d')})",
        )
        menu.addSeparator()
        act_pick = menu.addAction(get_status_icon("icons/schedule.svg", icon_color, 14), "Pick Date...")

        if self._pending_task_schedule:
            menu.addSeparator()
            act_clear = menu.addAction(
                get_status_icon("icons/icons8-no-entry-100.png", icon_color, 14),
                "Clear Schedule (One-time today)",
            )
        else:
            act_clear = None

        menu_size = menu.sizeHint()
        btn_pos = self.add_schedule_btn.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(btn_pos.x(), btn_pos.y() - menu_size.height() - 4)

        action = menu.exec(target_pos)
        if action == act_today:
            self._pending_task_schedule = today.strftime("%Y-%m-%d")
        elif action == act_tomorrow:
            self._pending_task_schedule = tomorrow.strftime("%Y-%m-%d")
        elif action == act_next_week:
            self._pending_task_schedule = next_week.strftime("%Y-%m-%d")
        elif action == act_pick:
            dlg = CalendarPopupDialog(today, self, is_dark=self.is_dark)
            cal_pos = self.add_schedule_btn.mapToGlobal(QPoint(0, 0))
            dlg.move(cal_pos.x() - 100, cal_pos.y() - 360)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._pending_task_schedule = dlg.selected_date.strftime("%Y-%m-%d")
        elif act_clear and action == act_clear:
            self._pending_task_schedule = None

        self.add_schedule_btn.set_scheduled_date(self._pending_task_schedule)

    def _pick_quick_add_repeat(self) -> None:
        """Open popup menu to pick repeat mode for the new task."""
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))
        icon_color = "#D4D4D8" if self.is_dark else "#44403C"

        act_none = menu.addAction(
            get_status_icon("icons/icons8-no-entry-100.png", icon_color, 14),
            "None (One-time)",
        )
        act_daily = menu.addAction(get_status_icon("icons/repeat.svg", icon_color, 14), "Daily (Every day)")
        act_weekdays = menu.addAction(get_status_icon("icons/repeat.svg", icon_color, 14), "Weekdays (Mon - Fri)")
        act_weekends = menu.addAction(get_status_icon("icons/repeat.svg", icon_color, 14), "Weekends (Sat - Sun)")

        menu_size = menu.sizeHint()
        btn_pos = self.add_repeat_btn.mapToGlobal(QPoint(0, 0))
        target_pos = QPoint(btn_pos.x(), btn_pos.y() - menu_size.height() - 4)

        action = menu.exec(target_pos)
        if action == act_none:
            self._pending_task_repeat = "none"
        elif action == act_daily:
            self._pending_task_repeat = "daily"
        elif action == act_weekdays:
            self._pending_task_repeat = "weekdays"
        elif action == act_weekends:
            self._pending_task_repeat = "weekends"

        self.add_repeat_btn.set_repeat_mode(self._pending_task_repeat)

    def refresh_tasks(self) -> None:
        """Re-render the task list for the selected date grouped by project under the current filter."""
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        active_filter = self.filter_bar.current_filter
        active_tag_id = getattr(self, "active_tag_filter_id", None)
        tasks = self.repo.get_task_hierarchy(
            target_date=self.selected_date,
            status_filter=active_filter,
            tag_id=active_tag_id,
        )

        all_projects = [p.name for p in self.repo.get_all_projects()]
        if not all_projects:
            all_projects = ["Work", "Personal Projects"]

        # Update sidebar task counter badge with open tasks
        if hasattr(self, "sidebar"):
            all_today_tasks = self.repo.get_task_hierarchy(target_date=self.selected_date, status_filter="all")
            open_count = sum(1 for t in all_today_tasks if t.status != "done")
            self.sidebar.set_tasks_badge(open_count)

        # Group tasks by project tag
        grouped: Dict[str, List[TaskRecord]] = {}
        for t in tasks:
            proj = t.project_tag or "General"
            grouped.setdefault(proj, []).append(t)

        if not grouped:
            if active_filter.lower() in ("task", "all"):
                empty_msg = f"No tasks recorded for {self.selected_date.strftime('%B %d')}."
            elif active_filter.lower() == "in progress":
                empty_msg = f"No in progress tasks for {self.selected_date.strftime('%B %d')}."
            elif active_filter.lower() == "completed":
                empty_msg = f"No completed tasks for {self.selected_date.strftime('%B %d')}."
            elif active_filter.lower() == "cancelled":
                empty_msg = f"No cancelled tasks for {self.selected_date.strftime('%B %d')}."
            else:
                empty_msg = f"No {active_filter.lower()} tasks found."

            empty_label = QLabel(empty_msg)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_color = "#71717A" if self.is_dark else "#A1A1AA"
            empty_label.setStyleSheet(f"""
                QLabel {{
                    color: {empty_color};
                    font-family: {FONT_SANS};
                    font-size: 13px;
                    padding: 40px 0;
                }}
            """)
            self.content_layout.addWidget(empty_label)
            self.content_layout.addStretch()
            return

        for project_name, task_list in grouped.items():
            group_widget = ProjectGroupWidget(project_name, task_list, self.content_widget, is_dark=self.is_dark)

            for task in task_list:
                row = TaskRowWidget(task, all_projects, group_widget.tasks_container, is_dark=self.is_dark, repo=self.repo)
                row.status_toggled.connect(self._on_task_status_toggled)
                row.action_requested.connect(self._on_task_action)
                row.project_changed.connect(self._on_task_project_changed)
                row.task_renamed.connect(self._on_task_renamed)
                row.task_tags_changed.connect(self._on_task_tags_changed)
                row.subtask_added.connect(self._on_subtask_added)
                row.subtask_toggled.connect(self._on_subtask_toggled)
                row.subtask_deleted.connect(self._on_subtask_deleted)
                row.subtask_renamed.connect(self._on_subtask_renamed)
                row.schedule_changed.connect(self._on_task_schedule_changed)
                row.repeat_changed.connect(self._on_task_repeat_changed)
                group_widget.tasks_layout.addWidget(row)

            self.content_layout.addWidget(group_widget)

        self.content_layout.addStretch()

    def refresh_notes(self) -> None:
        """Re-render the notes workspace."""
        if hasattr(self, "notes_workspace"):
            self.notes_workspace.load_notes()
            return

        while self.notes_content_layout.count() > 0:
            item = self.notes_content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        notes = self.repo.get_notes_for_date(self.selected_date)
        all_projects = [p.name for p in self.repo.get_all_projects()]
        if not all_projects:
            all_projects = ["Work", "Personal Projects"]

        if not notes:
            empty_color = "#71717A" if self.is_dark else "#A1A1AA"
            empty_label = QLabel(f"No notes logged for {self.selected_date.strftime('%B %d')}.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                QLabel {{
                    color: {empty_color};
                    font-family: {FONT_SANS};
                    font-size: 13px;
                    padding: 40px 0;
                }}
            """)
            self.notes_content_layout.addWidget(empty_label)
            self.notes_content_layout.addStretch()
            return

        for note in notes:
            row = NoteRowWidget(note, all_projects, self.notes_content_widget, is_dark=self.is_dark)
            row.toggled.connect(self._on_note_toggled)
            row.delete_requested.connect(self._on_note_deleted)
            row.project_changed.connect(self._on_note_project_changed)
            self.notes_content_layout.addWidget(row)

        self.notes_content_layout.addStretch()

    def _on_note_project_changed(self, note_id: int, new_project: str) -> None:
        """Handle moving a quick note to a different section/project."""
        self.repo.create_or_update_project(new_project, [new_project.lower()])
        self.repo.update_note_project(note_id, new_project)
        self._populate_projects()
        self.refresh_notes()

    def _trigger_debounced_sync(self) -> None:
        """Trigger a debounced sync to the Obsidian vault to prevent UI lag on rapid clicks."""
        self._sync_timer.start(350)

    def closeEvent(self, event) -> None:
        """Ensure any pending debounced sync is flushed before closing."""
        if hasattr(self, "_sync_timer") and self._sync_timer.isActive():
            self._sync_timer.stop()
            sync_today_logs(emit_signal=False)
        super().closeEvent(event)

    def _on_task_status_toggled(self, task_id: int, new_status: str) -> None:
        """Handle task status change (In progress, Completed, Cancelled, etc.)."""
        self.repo.update_task_status(task_id, new_status)
        if new_status in ("done", "completed", "cancelled", "canceled"):
            self.state_machine.trigger_complete(duration_ms=3500)
        elif new_status in ("in_progress", "pending", "ongoing"):
            self.state_machine.trigger_working()
        else:
            self.state_machine.revert_to_baseline()

        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_task_renamed(self, task_id: int, new_title: str) -> None:
        """Handle renaming a task."""
        self.repo.update_task_title(task_id, new_title)
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_task_action(self, action_type: str, task_id: int) -> None:
        """Handle task deletion or other actions."""
        if action_type == "delete":
            self.repo.delete_task(task_id)
            app_signals.task_deleted.emit(task_id)
            self.refresh_tasks()
            self._trigger_debounced_sync()

    def _on_task_project_changed(self, task_id: int, new_project: str) -> None:
        """Handle moving a task to a different section/project."""
        self.repo.create_or_update_project(new_project, [new_project.lower()])
        self.repo.update_task_project(task_id, new_project)
        self._populate_projects()
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_subtask_added(self, task_id: int, title: str) -> None:
        """Add a subtask under a task."""
        self.repo.create_subtask(task_id, title)
        self.refresh_tasks()
        self.state_machine.trigger_notify(duration_ms=3500)
        self._trigger_debounced_sync()

    def _on_subtask_toggled(self, subtask_id: int, new_status: str) -> None:
        """Toggle subtask status."""
        self.repo.update_subtask_status(subtask_id, new_status)
        if new_status in ("done", "completed", "cancelled", "canceled"):
            self.state_machine.trigger_complete(duration_ms=3500)
        elif new_status in ("in_progress", "pending", "ongoing"):
            self.state_machine.trigger_working()
        else:
            self.state_machine.revert_to_baseline()
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_subtask_renamed(self, subtask_id: int, new_title: str) -> None:
        """Handle renaming a subtask."""
        self.repo.update_subtask_title(subtask_id, new_title)
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_subtask_deleted(self, subtask_id: int) -> None:
        """Delete a subtask."""
        self.repo.delete_subtask(subtask_id)
        self.refresh_tasks()
        self._trigger_debounced_sync()

    def _on_note_toggled(self, note_id: int, is_completed: bool) -> None:
        """Toggle note completion status."""
        self.repo.toggle_note_completed(note_id, is_completed)
        self.refresh_notes()
        if is_completed:
            self.state_machine.trigger_complete(duration_ms=3500)
        else:
            self.state_machine.revert_to_baseline()
        self._trigger_debounced_sync()

    def _on_note_deleted(self, note_id: int) -> None:
        """Delete a note."""
        self.repo.delete_note(note_id)
        self.refresh_notes()
        self._trigger_debounced_sync()

    def _on_quick_add_task(self) -> None:
        """Submit quick task from bottom input bar."""
        title = self.add_input.text().strip()
        if not title:
            return

        proj = self.project_combo.currentText()
        if proj == "+ Create Section..." or not proj:
            proj = "Work"

        sched = self._pending_task_schedule
        rep = self._pending_task_repeat

        # If user did not pick an explicit schedule and is viewing another date:
        if sched is None:
            if self.selected_date != date.today():
                sched = self.selected_date.strftime("%Y-%m-%d")

        task_id = self.repo.create_task(
            title,
            project_tag=proj,
            scheduled_date=sched,
            repeat_mode=rep,
        )

        # Attach pending tags from tag_btn
        if hasattr(self, "tag_btn"):
            for tid in self.tag_btn.selected_tag_ids:
                self.repo.add_task_tag(task_id, tid)
            self.tag_btn.clear_selection()

        self.add_input.clear()
        self._pending_task_schedule = None
        self._pending_task_repeat = "none"
        if hasattr(self, "add_schedule_btn"):
            self.add_schedule_btn.set_scheduled_date(None)
        if hasattr(self, "add_repeat_btn"):
            self.add_repeat_btn.set_repeat_mode("none")
        if hasattr(self, "tag_btn"):
            self.tag_btn.clear_selection()

        self.refresh_tasks()
        self.state_machine.trigger_notify(duration_ms=3500)
        self._suppress_task_activity_sync = True
        try:
            app_signals.task_created.emit(task_id)
        finally:
            self._suppress_task_activity_sync = False

    def _on_quick_add_note(self) -> None:
        """Submit quick work note from bottom input bar."""
        content = self.note_input.text().strip()
        if not content:
            return

        proj = self.note_project_combo.currentText()
        if proj == "+ Create Section..." or not proj:
            proj = "Work"

        if self.selected_date != date.today():
            self.set_selected_date(date.today())

        note_id = self.repo.create_note(content, project_tag=proj, title=content)
        self.note_input.clear()
        self.refresh_notes()
        if hasattr(self, "notes_workspace"):
            self.notes_workspace.select_note(note_id)
        self.state_machine.trigger_notify(duration_ms=3500)
        app_signals.note_created.emit(note_id)

    def _on_minimize_clicked(self) -> None:
        """Minimize the workspace dialog while ensuring the companion mascot remains active and visible."""
        self.showMinimized()
        app_signals.ensure_mascot_visible.emit()

    def changeEvent(self, event) -> None:
        """Handle window state changes (e.g. minimize/restore shadow effect, companion persistence)."""
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                app_signals.ensure_mascot_visible.emit()
            if self.isMaximized():
                if hasattr(self, "_shadow_effect"):
                    self._shadow_effect.setEnabled(False)
            else:
                if hasattr(self, "_shadow_effect"):
                    self._shadow_effect.setEnabled(True)
            self.update()
        super().changeEvent(event)

    def paintEvent(self, event) -> None:
        """Explicitly clear translucent surface buffer to prevent widget ghosting."""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()
        super().paintEvent(event)

    # --- Mouse drag for frameless window movement ---

    def _is_in_draggable_area(self, global_pos: QPoint) -> bool:
        """Allow dragging ONLY from the top title bar header or sidebar brand header, never from workspace content."""
        if self.isMaximized():
            return False

        # 1. NEVER allow dragging from anywhere inside the workspace content card
        if hasattr(self, "inner_card") and self.inner_card.isVisible():
            inner_local = self.inner_card.mapFromGlobal(global_pos)
            if self.inner_card.rect().contains(inner_local):
                return False

        # 2. Exclude interactive controls (buttons, inputs, combos, checkboxes, scrollbars, etc.)
        local_pos = self.mapFromGlobal(global_pos)
        child = self.childAt(local_pos)
        if child is not None:
            from PyQt6.QtWidgets import (
                QAbstractButton,
                QAbstractSpinBox,
                QComboBox,
                QLineEdit,
                QTextEdit,
                QScrollBar,
            )
            if isinstance(child, (QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit, QTextEdit, QScrollBar)):
                return False

        # 3. Page Title Label ("Tasks & To-Dos", "Calendar & Schedule", etc.)
        if hasattr(self, "page_title_lbl"):
            title_local = self.page_title_lbl.mapFromGlobal(global_pos)
            if self.page_title_lbl.rect().contains(title_local):
                return True

        # 4. Top Title Bar Header strip (the area in workspace_container above inner_card)
        if hasattr(self, "workspace_container") and hasattr(self, "inner_card"):
            ws_local = self.workspace_container.mapFromGlobal(global_pos)
            inner_top_y = self.inner_card.y()
            if 0 <= ws_local.y() < inner_top_y and 0 <= ws_local.x() <= self.workspace_container.width():
                return True

        # 5. Top Brand Area of the Sidebar (top 42px of sidebar)
        if hasattr(self, "sidebar"):
            sb_local = self.sidebar.mapFromGlobal(global_pos)
            if 0 <= sb_local.y() < 42 and 0 <= sb_local.x() <= self.sidebar.width():
                return True

        return False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            global_pt = event.globalPosition().toPoint()
            if self._is_in_draggable_area(global_pt):
                self._drag_start_pos = global_pt
                self._window_start_pos = self.frameGeometry().topLeft()
                self._is_dragging = False
                event.accept()
                return
            else:
                self._drag_start_pos = None
                self._window_start_pos = None
                self._is_dragging = False
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_start_pos is not None
            and self._window_start_pos is not None
            and not self.isMaximized()
        ):
            current_pt = event.globalPosition().toPoint()
            delta = current_pt - self._drag_start_pos
            if not self._is_dragging:
                # Require drag threshold before actually moving window (prevents click jitter)
                if delta.manhattanLength() >= QApplication.startDragDistance():
                    self._is_dragging = True
            if self._is_dragging:
                self.move(self._window_start_pos + delta)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start_pos = None
        self._window_start_pos = None
        self._is_dragging = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Suppress Enter/Return at the dialog level so QDialog does not trigger default/theme buttons
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        try:
            from wiz.core.sound import sound_manager
            sound_manager.play_window_close()
        except Exception:
            pass
        super().closeEvent(event)


