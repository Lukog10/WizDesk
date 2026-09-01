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

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QRectF, QDate
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPen,
    QBrush,
    QMouseEvent,
    QKeyEvent,
    QPainterPath,
    QCursor,
    QAction,
    QTextCharFormat,
)
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QScrollArea,
    QFrame,
    QMenu,
    QComboBox,
    QGraphicsDropShadowEffect,
    QMessageBox,
    QInputDialog,
    QStackedWidget,
    QCalendarWidget,
    QToolButton,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.core.state_machine import StateMachine, MascotState
from wiz.storage.models import StorageRepository, TaskRecord, SubtaskRecord, NoteRecord
from wiz.ui.icons import get_app_icon, get_app_pixmap
from wiz.sync.obsidian import sync_today_logs


# Professional Typography Stacks
FONT_SANS = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'SF Mono', monospace"

def get_context_menu_style(is_dark: bool = False) -> str:
    bg = "#18181B" if is_dark else "#FFFFFF"
    color = "#F4F4F5" if is_dark else "#18181B"
    border = "#27272A" if is_dark else "#E4E4E7"
    hover_bg = "#27272A" if is_dark else "#F4F4F5"
    hover_color = "#FAFAFA" if is_dark else "#000000"
    disabled_color = "#71717A" if is_dark else "#A1A1AA"
    return f"""
        QMenu {{
            background-color: {bg};
            color: {color};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 4px;
            font-family: {FONT_SANS};
            font-size: 12.5px;
        }}
        QMenu::item {{
            padding: 6px 32px 6px 14px;
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


CONTEXT_MENU_STYLE = get_context_menu_style(False)


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
        card_border = "#27272A" if self.is_dark else "#E4E4E7"
        combo_bg = "#27272A" if self.is_dark else "#F4F4F5"
        combo_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        combo_text = "#F4F4F5" if self.is_dark else "#18181B"
        nav_btn_color = "#A1A1AA" if self.is_dark else "#71717A"
        nav_btn_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        nav_btn_hover_bg = "#27272A" if self.is_dark else "#F4F4F5"
        table_text = "#F4F4F5" if self.is_dark else "#18181B"
        table_hover_bg = "#27272A" if self.is_dark else "#F4F4F5"
        table_sel_bg = "#FAFAFA" if self.is_dark else "#18181B"
        table_sel_text = "#18181B" if self.is_dark else "#FFFFFF"
        today_btn_bg = "#27272A" if self.is_dark else "#F4F4F5"
        today_btn_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        today_btn_text = "#F4F4F5" if self.is_dark else "#18181B"
        today_btn_hover_bg = "#3F3F46" if self.is_dark else "#E4E4E7"

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
                padding: 4px 8px;
                color: {combo_text};
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QComboBox:hover {{
                background-color: {nav_btn_hover_bg};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 14px;
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
                border: 1px solid {combo_border};
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

        self.month_combo = QComboBox()
        self.month_combo.addItems(CALENDAR_MONTHS)
        self.month_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.month_combo.currentIndexChanged.connect(self._on_combo_page_changed)
        nav_layout.addWidget(self.month_combo, stretch=3)

        self.year_combo = QComboBox()
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
        hdr_font = QFont("Segoe UI")
        hdr_font.setPointSize(9)
        hdr_font.setWeight(QFont.Weight.DemiBold)
        hdr_fmt = QTextCharFormat()
        hdr_fmt.setForeground(QColor("#A1A1AA" if self.is_dark else "#71717A"))
        hdr_fmt.setFont(hdr_font)
        self.calendar.setHeaderTextFormat(hdr_fmt)

        # Neutralize weekend text to clean theme color
        work_font = QFont("Segoe UI")
        work_font.setPointSize(9)
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
                font-size: 11.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {today_btn_hover_bg};
                color: #FFFFFF;
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
    Custom modal dialog for creating a new Section in WizDesk.
    Replaces default OS input dialogs with WizDesk's clean minimalist rounded card design.
    Supports dynamic Light & Dark themes.
    """

    def __init__(self, parent: Optional[QWidget] = None, is_dark: Optional[bool] = None):
        super().__init__(parent)
        self.setWindowTitle("Create Section - WizDesk")
        self.setWindowIcon(get_app_icon("wiz-idle.svg"))
        self.setFixedSize(380, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)

        self.is_dark = is_dark if is_dark is not None else (config.theme == "dark")

        card_bg = "#18181B" if self.is_dark else "#FFFFFF"
        card_border = "#27272A" if self.is_dark else "#E4E4E7"
        title_color = "#F4F4F5" if self.is_dark else "#18181B"
        close_btn_color = "#71717A" if self.is_dark else "#A1A1AA"
        input_bg = "#27272A" if self.is_dark else "#F4F4F5"
        input_border = "#3F3F46" if self.is_dark else "#D4D4D8"
        input_text = "#F4F4F5" if self.is_dark else "#18181B"
        input_focus_border = "#FAFAFA" if self.is_dark else "#18181B"
        cancel_bg = "#27272A" if self.is_dark else "#F4F4F5"
        cancel_text = "#A1A1AA" if self.is_dark else "#52525B"
        cancel_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        cancel_hover_bg = "#3F3F46" if self.is_dark else "#E4E4E7"
        submit_bg = "#FAFAFA" if self.is_dark else "#18181B"
        submit_text = "#18181B" if self.is_dark else "#FFFFFF"
        submit_hover_bg = "#E4E4E7" if self.is_dark else "#3F3F46"

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
        self.card_layout.setContentsMargins(20, 18, 20, 18)
        self.card_layout.setSpacing(12)

        # Header Row
        hdr_layout = QHBoxLayout()
        hdr_title = QLabel("Create New Section")
        hdr_title.setStyleSheet(f"""
            QLabel {{
                color: {title_color};
                font-family: {FONT_SANS};
                font-size: 14.5px;
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

        # Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Section name (e.g. Design, Backend, Marketing)...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 9px 12px;
                font-family: {FONT_SANS};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                background-color: {card_bg};
                border: 1.5px solid {input_focus_border};
            }}
        """)
        self.input_field.returnPressed.connect(self._on_submit)
        self.card_layout.addWidget(self.input_field)

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
                padding: 8px 16px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
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
                padding: 8px 18px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
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

    def _on_submit(self) -> None:
        if self.section_name:
            self.accept()

    @property
    def section_name(self) -> str:
        return self.input_field.text().strip()

    @classmethod
    def get_section_name(cls, parent: Optional[QWidget] = None) -> tuple[str, bool]:
        """Show custom modal dialog and return (section_name, accepted)."""
        dlg = cls(parent)
        dlg.input_field.setFocus()
        if parent:
            # Center over parent geometry
            p_geo = parent.geometry()
            dlg.move(
                p_geo.center().x() - (dlg.width() // 2),
                p_geo.center().y() - (dlg.height() // 2),
            )
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted and dlg.section_name:
            return dlg.section_name, True
        return "", False

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


class RoundedCheckbox(QWidget):
    """Custom rounded-square checkbox widget with high-precision anti-aliased rendering and dark mode support."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, size: int = 20, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self._checked = checked
        self._size = size
        self.is_dark = is_dark
        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    @property
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        if self._checked != value:
            self._checked = value
            self.update()
            self.toggled.emit(self._checked)

    def set_dark_mode(self, is_dark: bool) -> None:
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        margin = 2.0
        s = float(self._size) - (margin * 2)
        rect = QRectF(margin, margin, s, s)
        radius = 4.0 if self._size >= 18 else 3.0

        if self._checked:
            # Filled rounded square with checkmark
            bg_color = QColor("#FAFAFA") if self.is_dark else QColor("#18181B")
            check_color = QColor("#18181B") if self.is_dark else QColor("#FFFFFF")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(rect, radius, radius)

            # Draw checkmark path scaled to size
            scale = self._size / 20.0
            pen = QPen(check_color, 1.8 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            p1_x = rect.x() + (4.5 * scale)
            p1_y = rect.y() + (8.5 * scale)
            p2_x = rect.x() + (7.5 * scale)
            p2_y = rect.y() + (11.5 * scale)
            p3_x = rect.x() + (12.0 * scale)
            p3_y = rect.y() + (5.0 * scale)
            painter.drawLine(int(p1_x), int(p1_y), int(p2_x), int(p2_y))
            painter.drawLine(int(p2_x), int(p2_y), int(p3_x), int(p3_y))
        else:
            # Clean subtle rounded outline
            border_color = QColor("#52525B") if self.is_dark else QColor("#D0D0D6")
            bg_color = QColor("#27272A") if self.is_dark else QColor("#FFFFFF")

            pen = QPen(border_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()


class SegmentedFilterBar(QWidget):
    """Pill capsule segmented filter bar (Task, In progress, Completed, Cancelled) with Light/Dark support."""

    filter_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.options = ["Task", "In progress", "Completed", "Cancelled"]
        self.current_filter = "Task"
        self.is_dark = is_dark
        self._buttons: Dict[str, QPushButton] = {}

        self.setFixedHeight(38)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(3, 3, 3, 3)
        self.layout.setSpacing(2)

        for opt in self.options:
            btn = QPushButton(opt)
            btn.setFixedHeight(32)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, o=opt: self.set_active_filter(o))
            self._buttons[opt] = btn
            self.layout.addWidget(btn)

        self._update_container_style()
        self._update_button_styles()

    def set_dark_mode(self, is_dark: bool) -> None:
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self._update_container_style()
            self._update_button_styles()

    def _update_container_style(self) -> None:
        bg = "#27272A" if self.is_dark else "#ECECF0"
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border-radius: 9px;
            }}
        """)

    def set_active_filter(self, filter_name: str) -> None:
        """Switch active filter tab."""
        if filter_name in self.options and self.current_filter != filter_name:
            self.current_filter = filter_name
            self._update_button_styles()
            self.filter_changed.emit(filter_name)

    def _update_button_styles(self) -> None:
        """Update button styles to give the active button an elevated pill look."""
        active_bg = "#18181B" if self.is_dark else "#FFFFFF"
        active_color = "#F4F4F5" if self.is_dark else "#111113"
        inactive_color = "#A1A1AA" if self.is_dark else "#71717A"
        hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        hover_bg = "rgba(255, 255, 255, 0.08)" if self.is_dark else "rgba(255, 255, 255, 0.4)"

        for opt, btn in self._buttons.items():
            if opt == self.current_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_bg};
                        color: {active_color};
                        border: none;
                        border-radius: 7px;
                        font-family: {FONT_SANS};
                        font-size: 12.5px;
                        font-weight: 600;
                        padding: 0 10px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {inactive_color};
                        border: none;
                        border-radius: 7px;
                        font-family: {FONT_SANS};
                        font-size: 12.5px;
                        font-weight: 500;
                        padding: 0 10px;
                    }}
                    QPushButton:hover {{
                        color: {hover_color};
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
        self.label.setFont(QFont("Segoe UI", 9))
        self.label.setToolTip("Double-click or right-click to rename")
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.label.double_clicked.connect(self.start_renaming)
        top_layout.addWidget(self.label, stretch=1)

        edit_bg = "#18181B" if self.is_dark else "#FFFFFF"
        edit_color = "#F4F4F5" if self.is_dark else "#18181B"
        edit_border = "#FAFAFA" if self.is_dark else "#18181B"

        self.edit_input = InlineEditInput(subtask.title, self)
        self.edit_input.setFont(QFont("Segoe UI", 9))
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
        del_btn_color = "#71717A" if self.is_dark else "#D4D4D8"
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

        time_color = "#71717A" if self.is_dark else "#A1A1AA"
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: {time_color};
                font-family: {FONT_SANS};
                font-size: 10.5px;
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
        created_str = self.subtask.created_at.strftime("%I:%M %p").lstrip("0") if self.subtask.created_at else ""
        if is_done and self.subtask.completed_at and created_str:
            comp_str = self.subtask.completed_at.strftime("%I:%M %p").lstrip("0")
            self.time_label.setText(f"({created_str} - {comp_str})")
        elif created_str:
            self.time_label.setText(f"({created_str})")
        else:
            self.time_label.setText("")

    def _update_label_style(self, is_done: bool) -> None:
        self._update_time_label(is_done)
        done_color = "#71717A" if self.is_dark else "#A1A1AA"
        active_color = "#D4D4D8" if self.is_dark else "#52525B"

        if is_done:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {done_color};
                    text-decoration: line-through;
                    font-family: {FONT_SANS};
                    font-size: 12.5px;
                }}
            """)
        else:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 12.5px;
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

        action_rename = menu.addAction("Rename Subtask")

        is_done = (self.subtask.status in ("done", "completed"))
        toggle_label = "Mark Incomplete" if is_done else "Mark Done"
        action_toggle = menu.addAction(toggle_label)

        menu.addSeparator()
        action_delete = menu.addAction("Delete Subtask")

        action = menu.exec(self.mapToGlobal(pos))
        if action == action_rename:
            self.start_renaming()
        elif action == action_toggle:
            self.checkbox.setChecked(not is_done)
        elif action == action_delete:
            self.delete_requested.emit(self.subtask_id)


class TaskRowWidget(QWidget):
    """
    Parent task row featuring:
    - Custom rounded checkbox & task title with inline renaming (double-click or context menu)
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

    def __init__(self, task: TaskRecord, all_projects: List[str], parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.task = task
        self.task_id = task.id or 0
        self.all_projects = all_projects
        self.is_dark = is_dark

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 2, 0, 2)
        self.main_layout.setSpacing(3)

        # Top row: Checkbox, Title, + Subtask button
        self.top_widget = QWidget()
        top_layout = QHBoxLayout(self.top_widget)
        top_layout.setContentsMargins(4, 3, 4, 3)
        top_layout.setSpacing(10)

        is_done = (task.status in ("done", "completed"))
        self.checkbox = RoundedCheckbox(checked=is_done, size=20, parent=self.top_widget, is_dark=self.is_dark)
        self.checkbox.toggled.connect(self._on_checkbox_toggled)
        top_layout.addWidget(self.checkbox)

        self.label = EditableTaskLabel(task.title)
        self.label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.label.setToolTip("Double-click or right-click to rename")
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.label.double_clicked.connect(self.start_renaming)
        top_layout.addWidget(self.label, stretch=1)

        edit_bg = "#18181B" if self.is_dark else "#FFFFFF"
        edit_color = "#F4F4F5" if self.is_dark else "#18181B"
        edit_border = "#FAFAFA" if self.is_dark else "#18181B"

        self.edit_input = InlineEditInput(task.title, self)
        self.edit_input.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
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

        # "+ subtask" button
        self.add_sub_btn = QPushButton("+ subtask")
        self.add_sub_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        sub_btn_color = "#71717A" if self.is_dark else "#A1A1AA"
        sub_btn_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        sub_btn_hover_bg = "#27272A" if self.is_dark else "#F4F4F5"
        self.add_sub_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {sub_btn_color};
                border: none;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
                padding: 2px 6px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: {sub_btn_hover_color};
                background-color: {sub_btn_hover_bg};
            }}
        """)
        self.add_sub_btn.clicked.connect(self._toggle_subtask_input)
        top_layout.addWidget(self.add_sub_btn)

        self.main_layout.addWidget(self.top_widget)

        # Status dropdown & time label directly below task title
        self.status_bar_widget = QWidget()
        status_bar_layout = QHBoxLayout(self.status_bar_widget)
        status_bar_layout.setContentsMargins(34, 0, 4, 3)
        status_bar_layout.setSpacing(10)

        self.status_combo = QComboBox()
        self.status_combo.setEditable(False)
        self.status_combo.addItems(["Status", "In progress", "Completed", "Cancelled"])
        self.status_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.status_combo.currentIndexChanged.connect(self._on_status_combo_changed)
        status_bar_layout.addWidget(self.status_combo)

        # Time metadata label
        time_color = "#71717A" if self.is_dark else "#A1A1AA"
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: {time_color};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
            }}
        """)
        status_bar_layout.addWidget(self.time_label)

        status_bar_layout.addStretch()
        self.main_layout.addWidget(self.status_bar_widget)

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

        sub_in_bg = "#27272A" if self.is_dark else "#F4F4F5"
        sub_in_border = "#3F3F46" if self.is_dark else "#D4D4D8"
        sub_in_text = "#F4F4F5" if self.is_dark else "#18181B"
        sub_in_focus = "#FAFAFA" if self.is_dark else "#18181B"

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
            }}
            QLineEdit:focus {{
                background-color: {edit_bg};
                border: 1.5px solid {sub_in_focus};
            }}
        """)
        self.sub_input.returnPressed.connect(self._on_submit_subtask)
        sub_input_layout.addWidget(self.sub_input, stretch=1)

        sub_btn_bg = "#FAFAFA" if self.is_dark else "#18181B"
        sub_btn_text = "#18181B" if self.is_dark else "#FFFFFF"
        sub_btn_hover = "#E4E4E7" if self.is_dark else "#3F3F46"

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
                font-size: 11.5px;
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

    def _on_status_combo_changed(self, index: int) -> None:
        """Handle status selection change from the dropdown."""
        text = self.status_combo.currentText()
        if text == "In progress":
            new_status = "in_progress"
            self.task.completed_at = None
        elif text == "Completed":
            new_status = "done"
            if not self.task.completed_at:
                self.task.completed_at = datetime.now()
        elif text == "Cancelled":
            new_status = "cancelled"
            if not self.task.completed_at:
                self.task.completed_at = datetime.now()
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

        # Time metadata display (e.g. (1:36 PM - 1:57 PM) or (1:36 PM))
        created_str = self.task.created_at.strftime("%I:%M %p").lstrip("0") if self.task.created_at else ""
        if (is_done or is_cancelled) and self.task.completed_at and created_str:
            comp_str = self.task.completed_at.strftime("%I:%M %p").lstrip("0")
            self.time_label.setText(f"({created_str} - {comp_str})")
        elif created_str:
            self.time_label.setText(f"({created_str})")
        else:
            self.time_label.setText("")

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
            self.status_combo.setCurrentText("Status")
        self.status_combo.blockSignals(False)

        # Text colors
        done_color = "#71717A" if self.is_dark else "#A1A1AA"
        active_color = "#F4F4F5" if self.is_dark else "#18181B"

        # Label styling
        if is_done:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {done_color};
                    text-decoration: line-through;
                    font-family: {FONT_SANS};
                    font-size: 13.5px;
                }}
            """)
        elif is_cancelled:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {done_color};
                    text-decoration: line-through;
                    font-style: italic;
                    font-family: {FONT_SANS};
                    font-size: 13.5px;
                }}
            """)
        elif is_in_progress:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 13.5px;
                    font-weight: 600;
                }}
            """)
        else:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 13.5px;
                    font-weight: 500;
                }}
            """)

        # Dropdown popup styling
        combo_popup_bg = "#18181B" if self.is_dark else "#FFFFFF"
        combo_popup_text = "#F4F4F5" if self.is_dark else "#18181B"
        combo_popup_border = "#27272A" if self.is_dark else "#E4E4E7"
        combo_popup_sel_bg = "#27272A" if self.is_dark else "#F4F4F5"
        combo_popup_sel_text = "#FFFFFF" if self.is_dark else "#000000"

        # Dropdown styling based on state
        if is_in_progress:
            self.status_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {'rgba(59, 130, 246, 0.20)' if self.is_dark else 'rgba(37, 99, 235, 0.10)'};
                    color: {'#60A5FA' if self.is_dark else '#2563EB'};
                    border: 1px solid {'rgba(96, 165, 250, 0.40)' if self.is_dark else 'rgba(37, 99, 235, 0.35)'};
                    border-radius: 6px;
                    font-family: {FONT_SANS};
                    font-size: 11px;
                    font-weight: 600;
                    padding: 2px 22px 2px 8px;
                    min-height: 22px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 16px;
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
                    font-size: 11.5px;
                }}
            """)
        elif is_done:
            self.status_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {'rgba(52, 211, 153, 0.20)' if self.is_dark else 'rgba(16, 185, 129, 0.10)'};
                    color: {'#34D399' if self.is_dark else '#059669'};
                    border: 1px solid {'rgba(52, 211, 153, 0.40)' if self.is_dark else 'rgba(16, 185, 129, 0.35)'};
                    border-radius: 6px;
                    font-family: {FONT_SANS};
                    font-size: 11px;
                    font-weight: 600;
                    padding: 2px 22px 2px 8px;
                    min-height: 22px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 16px;
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
                    font-size: 11.5px;
                }}
            """)
        elif is_cancelled:
            self.status_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {'rgba(248, 113, 113, 0.20)' if self.is_dark else 'rgba(239, 68, 68, 0.10)'};
                    color: {'#F87171' if self.is_dark else '#DC2626'};
                    border: 1px solid {'rgba(248, 113, 113, 0.35)' if self.is_dark else 'rgba(239, 68, 68, 0.30)'};
                    border-radius: 6px;
                    font-family: {FONT_SANS};
                    font-size: 11px;
                    font-weight: 600;
                    padding: 2px 22px 2px 8px;
                    min-height: 22px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 16px;
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
                    font-size: 11.5px;
                }}
            """)
        else:
            default_bg = "#27272A" if self.is_dark else "#F4F4F5"
            default_color = "#A1A1AA" if self.is_dark else "#71717A"
            default_border = "#3F3F46" if self.is_dark else "#E4E4E7"
            hover_border = "#52525B" if self.is_dark else "#D4D4D8"
            hover_color = "#FAFAFA" if self.is_dark else "#18181B"

            self.status_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {default_bg};
                    color: {default_color};
                    border: 1px solid {default_border};
                    border-radius: 6px;
                    font-family: {FONT_SANS};
                    font-size: 11px;
                    font-weight: 500;
                    padding: 2px 22px 2px 8px;
                    min-height: 22px;
                }}
                QComboBox:hover {{
                    color: {hover_color};
                    border-color: {hover_border};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 16px;
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
                    font-size: 11.5px;
                }}
            """)

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

    def _cancel_renaming(self) -> None:
        """Cancel inline task renaming."""
        self.edit_input.setText(self.task.title)
        self.edit_input.setVisible(False)
        self.label.setVisible(True)

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(self.is_dark))

        action_rename = menu.addAction("Rename Task")
        action_add_sub = menu.addAction("+ Add Subtask")
        menu.addSeparator()

        # "Move to Section" submenu
        section_menu = menu.addMenu("Move to Section")
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
        action_task = menu.addAction("Move to Task")
        action_in_progress = menu.addAction("Move to In progress")
        action_completed = menu.addAction("Move to Completed")
        action_cancelled = menu.addAction("Move to Cancelled")
        menu.addSeparator()
        action_delete = menu.addAction("Delete Task")

        action = menu.exec(self.mapToGlobal(pos))
        if action == action_rename:
            self.start_renaming()
        elif action == action_add_sub:
            self._toggle_subtask_input(force_show=True)
        elif action == action_new_sec:
            name, ok = CreateSectionDialog.get_section_name(self)
            if ok and name.strip():
                self.project_changed.emit(self.task_id, name.strip())
        elif action == action_task:
            self.status_toggled.emit(self.task_id, "not_started")
        elif action == action_in_progress:
            self.status_toggled.emit(self.task_id, "in_progress")
        elif action == action_completed:
            self.status_toggled.emit(self.task_id, "done")
        elif action == action_cancelled:
            self.status_toggled.emit(self.task_id, "cancelled")
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
        self.label.setFont(QFont("Segoe UI", 10))
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
        time_color = "#71717A" if self.is_dark else "#A1A1AA"
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
        del_btn_color = "#71717A" if self.is_dark else "#D4D4D8"
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

        section_menu = menu.addMenu("Move to Section")
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
        action_delete = menu.addAction("Delete Note")

        action = menu.exec(global_pos)
        if action == action_new_sec:
            name, ok = CreateSectionDialog.get_section_name(self)
            if ok and name.strip():
                self.project_changed.emit(self.note_id, name.strip())
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
            name, ok = CreateSectionDialog.get_section_name(self)
            if ok and name.strip():
                self.project_changed.emit(self.note_id, name.strip())

    def _update_text_style(self, is_done: bool) -> None:
        done_color = "#71717A" if self.is_dark else "#A1A1AA"
        active_color = "#F4F4F5" if self.is_dark else "#18181B"

        if is_done:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {done_color};
                    text-decoration: line-through;
                    font-family: {FONT_SANS};
                    font-size: 13.5px;
                }}
            """)
        else:
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {active_color};
                    text-decoration: none;
                    font-family: {FONT_SANS};
                    font-size: 13.5px;
                    font-weight: 500;
                }}
            """)

    def _on_toggled(self, checked: bool) -> None:
        self._update_text_style(checked)
        self.toggled.emit(self.note_id, checked)


class ProjectGroupWidget(QWidget):
    """Collapsible project section with chevron header (e.g. ▼ Work)."""

    def __init__(self, project_name: str, tasks: List[TaskRecord], parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self.project_name = project_name
        self.tasks = tasks
        self.is_dark = is_dark
        self._is_expanded = True

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 8, 0, 8)
        self.main_layout.setSpacing(6)

        # Header bar
        header_color = "#F4F4F5" if self.is_dark else "#18181B"
        header_hover = "#A1A1AA" if self.is_dark else "#52525B"

        self.header_btn = QPushButton(f"v {project_name}")
        self.header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                text-align: left;
                font-family: {FONT_SANS};
                font-size: 14.5px;
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

        # Tasks container
        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(12, 0, 0, 0)
        self.tasks_layout.setSpacing(6)
        self.main_layout.addWidget(self.tasks_container)

    def toggle_collapse(self) -> None:
        """Toggle section expansion."""
        self._is_expanded = not self._is_expanded
        self.tasks_container.setVisible(self._is_expanded)
        arrow = "v" if self._is_expanded else ">"
        self.header_btn.setText(f"{arrow} {self.project_name}")


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
        self.is_dark = (config.theme == "dark")

        # Window settings
        self.setWindowTitle("WizDesk - Workspace")
        self.setWindowIcon(get_app_icon("wiz-idle.svg"))
        self.setMinimumSize(480, 600)
        self.resize(520, 680)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

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

        # Frame Inner Layout
        self.frame_layout = QVBoxLayout(self.outer_frame)
        self.frame_layout.setContentsMargins(12, 10, 12, 12)
        self.frame_layout.setSpacing(8)

        # Top Bar: Frameless Drag Region & Window Controls
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)

        # Subtle drag hint / branding
        self.brand_lbl = QLabel("  WizDesk")
        self.brand_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        top_bar.addWidget(self.brand_lbl)
        top_bar.addStretch()

        # Window control buttons (Theme, —, □, x)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        self.theme_btn = QPushButton("☀" if self.is_dark else "☾")
        self.theme_btn.setFixedSize(22, 22)
        self.theme_btn.setToolTip("Switch to Light Mode" if self.is_dark else "Switch to Dark Mode")
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.clicked.connect(self.toggle_theme)
        controls_layout.addWidget(self.theme_btn)

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(22, 22)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.clicked.connect(self.showMinimized)
        controls_layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("□")
        self.max_btn.setFixedSize(22, 22)
        self.max_btn.setToolTip("Maximize")
        self.max_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.max_btn.clicked.connect(self._toggle_maximize_restore)
        controls_layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("x")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.close_btn)

        top_bar.addLayout(controls_layout)
        self.frame_layout.addLayout(top_bar)

        # --- Inner Canvas Card ---
        self.inner_card = QFrame()
        self.inner_card.setObjectName("innerCard")
        self.inner_layout = QVBoxLayout(self.inner_card)
        self.inner_layout.setContentsMargins(18, 16, 18, 16)
        self.inner_layout.setSpacing(12)

        # 1. Inside Page Header: Tasks | Quick Notes Switcher
        page_header_layout = QHBoxLayout()
        page_header_layout.setContentsMargins(0, 0, 0, 0)
        page_header_layout.addStretch()

        self.mode_capsule = QFrame()
        self.mode_capsule.setObjectName("modeCapsule")
        mode_layout = QHBoxLayout(self.mode_capsule)
        mode_layout.setContentsMargins(3, 3, 3, 3)
        mode_layout.setSpacing(2)

        self.tasks_mode_btn = QPushButton("Tasks")
        self.tasks_mode_btn.setFixedHeight(30)
        self.tasks_mode_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.tasks_mode_btn.clicked.connect(lambda: self._set_view_mode("tasks"))
        mode_layout.addWidget(self.tasks_mode_btn)

        self.notes_mode_btn = QPushButton("Quick Notes")
        self.notes_mode_btn.setFixedHeight(30)
        self.notes_mode_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.notes_mode_btn.clicked.connect(lambda: self._set_view_mode("notes"))
        mode_layout.addWidget(self.notes_mode_btn)

        page_header_layout.addWidget(self.mode_capsule)
        page_header_layout.addStretch()
        self.inner_layout.addLayout(page_header_layout)

        # 2. Date Header with Navigation & Interactive Calendar Picker
        date_header_layout = QHBoxLayout()
        date_header_layout.setContentsMargins(0, 0, 0, 0)
        date_header_layout.setSpacing(6)
        date_header_layout.addStretch()

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
        self.today_pill_btn.setFixedHeight(26)
        self.today_pill_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.today_pill_btn.clicked.connect(self._on_today_clicked)
        self.today_pill_btn.setVisible(False)
        date_header_layout.addWidget(self.today_pill_btn)

        date_header_layout.addStretch()
        self.inner_layout.addLayout(date_header_layout)

        # Initialize date display
        self._update_date_display()

        # Stacked Widget for Tasks vs Quick Notes
        self.stack = QStackedWidget()

        # ==========================================
        # PAGE 1: TASKS VIEW
        # ==========================================
        self.tasks_page = QWidget()
        tasks_page_layout = QVBoxLayout(self.tasks_page)
        tasks_page_layout.setContentsMargins(0, 0, 0, 0)
        tasks_page_layout.setSpacing(12)

        # 3. Status Filter Capsule Bar (Below the Date)
        self.filter_bar = SegmentedFilterBar(is_dark=self.is_dark)
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        tasks_page_layout.addWidget(self.filter_bar)

        # 4. Scrollable Tasks Area (Without visible scrollbar)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
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

        # 5. Bottom Add Task Bar with Section Selector & Create Section Option
        add_task_layout = QHBoxLayout()
        add_task_layout.setSpacing(8)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("+ Add task... (Press Enter)")
        self.add_input.returnPressed.connect(self._on_quick_add_task)
        add_task_layout.addWidget(self.add_input, stretch=3)

        self.project_combo = QComboBox()
        self.project_combo.setEditable(False)
        self.project_combo.currentIndexChanged.connect(self._on_project_combo_changed)
        add_task_layout.addWidget(self.project_combo, stretch=1)

        self.add_task_btn = QPushButton("Add")
        self.add_task_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_task_btn.clicked.connect(self._on_quick_add_task)
        add_task_layout.addWidget(self.add_task_btn)

        tasks_page_layout.addLayout(add_task_layout)
        self.stack.addWidget(self.tasks_page)

        # ==========================================
        # PAGE 2: QUICK NOTES VIEW
        # ==========================================
        self.notes_page = QWidget()
        notes_page_layout = QVBoxLayout(self.notes_page)
        notes_page_layout.setContentsMargins(0, 0, 0, 0)
        notes_page_layout.setSpacing(12)

        # Notes subtitle / hint
        self.notes_hdr = QLabel("Track work progress notes, thoughts, or blockers for today:")
        notes_page_layout.addWidget(self.notes_hdr)

        # Scrollable Notes Area (Without visible scrollbar)
        self.notes_scroll = QScrollArea()
        self.notes_scroll.setWidgetResizable(True)
        self.notes_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.notes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notes_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        self.notes_content_widget = QWidget()
        self.notes_content_widget.setStyleSheet("background: transparent;")
        self.notes_content_layout = QVBoxLayout(self.notes_content_widget)
        self.notes_content_layout.setContentsMargins(4, 4, 4, 4)
        self.notes_content_layout.setSpacing(8)
        self.notes_content_layout.addStretch()

        self.notes_scroll.setWidget(self.notes_content_widget)
        notes_page_layout.addWidget(self.notes_scroll, stretch=1)

        # Bottom Add Note Bar
        add_note_layout = QHBoxLayout()
        add_note_layout.setSpacing(8)

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("+ Log a quick work note... (Press Enter)")
        self.note_input.returnPressed.connect(self._on_quick_add_note)
        add_note_layout.addWidget(self.note_input, stretch=3)

        self.note_project_combo = QComboBox()
        self.note_project_combo.setEditable(False)
        self.note_project_combo.currentIndexChanged.connect(self._on_note_project_combo_changed)
        add_note_layout.addWidget(self.note_project_combo, stretch=1)

        self.add_note_btn = QPushButton("Log Note")
        self.add_note_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_note_btn.clicked.connect(self._on_quick_add_note)
        add_note_layout.addWidget(self.add_note_btn)

        notes_page_layout.addLayout(add_note_layout)
        self.stack.addWidget(self.notes_page)

        self.inner_layout.addWidget(self.stack, stretch=1)
        self.frame_layout.addWidget(self.inner_card, stretch=1)

        # Drag state for frameless window movement
        self._drag_pos = QPoint()

        # Connect theme changed broadcast
        app_signals.theme_changed.connect(self.apply_theme)

        # Apply initial theme stylesheet
        self.apply_theme(config.theme)

        # Seed sample projects/tasks if repository is completely blank
        self._seed_initial_data_if_empty()

        # Initial populate & render
        self._populate_projects()
        self._set_view_mode("tasks")

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

        # Color tokens
        outer_bg = "#121214" if self.is_dark else "#E6E6EA"
        outer_border = "#27272A" if self.is_dark else "#D8D8DE"
        inner_bg = "#18181B" if self.is_dark else "#FFFFFF"
        inner_border = "#27272A" if self.is_dark else "#ECECEF"
        brand_color = "#A1A1AA" if self.is_dark else "#71717A"
        ctrl_btn_color = "#A1A1AA" if self.is_dark else "#52525B"
        ctrl_btn_hover_bg = "rgba(255, 255, 255, 0.08)" if self.is_dark else "rgba(0, 0, 0, 0.08)"
        ctrl_btn_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        mode_capsule_bg = "#27272A" if self.is_dark else "#ECECF0"
        day_btn_color = "#A1A1AA" if self.is_dark else "#71717A"
        day_btn_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        day_btn_hover_bg = "#27272A" if self.is_dark else "#F4F4F5"
        day_btn_hover_color = "#FAFAFA" if self.is_dark else "#18181B"
        date_btn_color = "#F4F4F5" if self.is_dark else "#27272A"
        today_pill_bg = "#FAFAFA" if self.is_dark else "#18181B"
        today_pill_color = "#18181B" if self.is_dark else "#FFFFFF"
        today_pill_hover = "#E4E4E7" if self.is_dark else "#3F3F46"
        input_bg = "#27272A" if self.is_dark else "#F4F4F5"
        input_color = "#F4F4F5" if self.is_dark else "#18181B"
        input_border = "#3F3F46" if self.is_dark else "#D4D4D8"
        input_focus_border = "#FAFAFA" if self.is_dark else "#18181B"
        combo_popup_bg = "#18181B" if self.is_dark else "#FFFFFF"
        combo_popup_border = "#27272A" if self.is_dark else "#E4E4E7"
        combo_popup_sel_bg = "#27272A" if self.is_dark else "#F4F4F5"
        combo_popup_sel_text = "#FFFFFF" if self.is_dark else "#000000"
        btn_action_bg = "#FAFAFA" if self.is_dark else "#18181B"
        btn_action_color = "#18181B" if self.is_dark else "#FFFFFF"
        btn_action_hover = "#E4E4E7" if self.is_dark else "#3F3F46"
        notes_hdr_color = "#A1A1AA" if self.is_dark else "#71717A"

        # 1. Outer Frame & Inner Card
        self.outer_frame.setStyleSheet(f"""
            QFrame#outerFrame {{
                background-color: {outer_bg};
                border: 1px solid {outer_border};
                border-radius: 24px;
            }}
        """)
        self.inner_card.setStyleSheet(f"""
            QFrame#innerCard {{
                background-color: {inner_bg};
                border-radius: 20px;
                border: 1px solid {inner_border};
            }}
        """)

        # 2. Window Controls
        self.brand_lbl.setStyleSheet(f"color: {brand_color};")
        ctrl_qss = f"""
            QPushButton {{
                background-color: transparent;
                color: {ctrl_btn_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 13px;
                font-weight: bold;
                border-radius: 11px;
            }}
            QPushButton:hover {{
                background-color: {ctrl_btn_hover_bg};
                color: {ctrl_btn_hover_color};
            }}
        """
        self.theme_btn.setStyleSheet(ctrl_qss)
        self.min_btn.setStyleSheet(ctrl_qss)
        self.max_btn.setStyleSheet(ctrl_qss)
        self.close_btn.setStyleSheet(ctrl_qss)

        # 3. Mode Capsule
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
                font-family: {FONT_MONO};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {day_btn_hover_color};
                background-color: {day_btn_hover_bg};
                border-color: {input_border};
            }}
        """
        self.prev_day_btn.setStyleSheet(day_nav_qss)
        self.next_day_btn.setStyleSheet(day_nav_qss)

        self.date_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {date_btn_color};
                border: none;
                font-family: {FONT_MONO};
                font-size: 13.5px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {day_btn_hover_bg};
            }}
        """)

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
                padding: 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
                font-weight: 500;
                min-width: 130px;
            }}
            QComboBox:hover {{
                border-color: {input_focus_border};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
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
                font-size: 12.5px;
            }}
        """
        self.project_combo.setStyleSheet(combo_qss)
        self.note_project_combo.setStyleSheet(combo_qss)

        btn_action_qss = f"""
            QPushButton {{
                background-color: {btn_action_bg};
                color: {btn_action_color};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_action_hover};
            }}
        """
        self.add_task_btn.setStyleSheet(btn_action_qss)
        self.add_note_btn.setStyleSheet(btn_action_qss)

        # 7. Notes Header
        self.notes_hdr.setStyleSheet(f"""
            QLabel {{
                color: {notes_hdr_color};
                font-family: {FONT_SANS};
                font-size: 12.5px;
                font-weight: 500;
            }}
        """)

        # 8. Re-apply mode buttons
        self._set_view_mode(self.current_view_mode)

    def _set_view_mode(self, mode: str) -> None:
        """Switch between Tasks mode and Quick Notes mode."""
        self.current_view_mode = mode
        active_bg = "#18181B" if self.is_dark else "#FFFFFF"
        active_color = "#F4F4F5" if self.is_dark else "#18181B"
        inactive_color = "#A1A1AA" if self.is_dark else "#71717A"
        hover_color = "#FAFAFA" if self.is_dark else "#18181B"

        if mode == "tasks":
            self.stack.setCurrentWidget(self.tasks_page)
            self.tasks_mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {active_bg};
                    color: {active_color};
                    border: none;
                    border-radius: 7px;
                    font-family: {FONT_SANS};
                    font-size: 12.5px;
                    font-weight: 600;
                    padding: 0 14px;
                }}
            """)
            self.notes_mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {inactive_color};
                    border: none;
                    border-radius: 7px;
                    font-family: {FONT_SANS};
                    font-size: 12.5px;
                    font-weight: 500;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    color: {hover_color};
                }}
            """)
            self.refresh_tasks()
        else:
            self.stack.setCurrentWidget(self.notes_page)
            self.notes_mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {active_bg};
                    color: {active_color};
                    border: none;
                    border-radius: 7px;
                    font-family: {FONT_SANS};
                    font-size: 12.5px;
                    font-weight: 600;
                    padding: 0 14px;
                }}
            """)
            self.tasks_mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {inactive_color};
                    border: none;
                    border-radius: 7px;
                    font-family: {FONT_SANS};
                    font-size: 12.5px;
                    font-weight: 500;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    color: {hover_color};
                }}
            """)
            self.refresh_notes()

    def _seed_initial_data_if_empty(self) -> None:
        """Seed default project categories if database has no projects."""
        projects = self.repo.get_all_projects()
        if not projects:
            self.repo.create_or_update_project("Work", ["work", "code"])
            self.repo.create_or_update_project("Personal Projects", ["personal"])

    def _populate_projects(self) -> None:
        """Populate project/section choices with '+ Create Section...' option."""
        projects = self.repo.get_all_projects()
        names = [p.name for p in projects]
        if not names:
            names = ["Work", "Personal Projects"]

        current_sel = self.project_combo.currentText() if hasattr(self, "project_combo") else ""

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

        if hasattr(self, "note_project_combo"):
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

    def _on_project_combo_changed(self, index: int) -> None:
        """Handle selection of '+ Create Section...' in task project combo."""
        text = self.project_combo.currentText()
        if text == "+ Create Section...":
            name, ok = CreateSectionDialog.get_section_name(self)
            if ok and name.strip():
                clean_name = name.strip()
                self.repo.create_or_update_project(clean_name, [clean_name.lower()])
                self._populate_projects()
                self.project_combo.setCurrentText(clean_name)
            else:
                if self.project_combo.count() > 0:
                    self.project_combo.setCurrentIndex(0)

    def _on_note_project_combo_changed(self, index: int) -> None:
        """Handle selection of '+ Create Section...' in note project combo."""
        text = self.note_project_combo.currentText()
        if text == "+ Create Section...":
            name, ok = CreateSectionDialog.get_section_name(self)
            if ok and name.strip():
                clean_name = name.strip()
                self.repo.create_or_update_project(clean_name, [clean_name.lower()])
                self._populate_projects()
                self.note_project_combo.setCurrentText(clean_name)
            else:
                if self.note_project_combo.count() > 0:
                    self.note_project_combo.setCurrentIndex(0)

    def _on_filter_changed(self, filter_name: str) -> None:
        """Called when a segmented filter pill is clicked."""
        self.refresh_tasks()

    def _update_date_display(self) -> None:
        """Update date button label and 'Today' shortcut indicator."""
        date_str = self.selected_date.strftime("%B %d, %A")
        self.date_btn.setText(date_str)
        is_today = (self.selected_date == date.today())
        self.today_pill_btn.setVisible(not is_today)

    def set_selected_date(self, target_date: date) -> None:
        """Set the active view date and refresh tasks and notes."""
        self.selected_date = target_date
        self._update_date_display()
        self.refresh_tasks()
        self.refresh_notes()

    def _on_prev_day(self) -> None:
        """Navigate to previous day."""
        self.set_selected_date(self.selected_date - timedelta(days=1))

    def _on_next_day(self) -> None:
        """Navigate to next day."""
        self.set_selected_date(self.selected_date + timedelta(days=1))

    def _on_today_clicked(self) -> None:
        """Jump back to today."""
        self.set_selected_date(date.today())

    def _open_calendar(self) -> None:
        """Open popup calendar picker."""
        dlg = CalendarPopupDialog(self.selected_date, self, is_dark=self.is_dark)
        btn_pos = self.date_btn.mapToGlobal(QPoint(0, self.date_btn.height() + 4))
        x = btn_pos.x() + (self.date_btn.width() // 2) - (dlg.width() // 2)
        y = btn_pos.y()
        dlg.move(x, y)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.set_selected_date(dlg.selected_date)

    def refresh_tasks(self) -> None:
        """Re-render the task list for the selected date grouped by project under the current filter."""
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        active_filter = self.filter_bar.current_filter
        tasks = self.repo.get_task_hierarchy(target_date=self.selected_date, status_filter=active_filter)

        all_projects = [p.name for p in self.repo.get_all_projects()]
        if not all_projects:
            all_projects = ["Work", "Personal Projects"]

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
                row = TaskRowWidget(task, all_projects, group_widget.tasks_container, is_dark=self.is_dark)
                row.status_toggled.connect(self._on_task_status_toggled)
                row.action_requested.connect(self._on_task_action)
                row.project_changed.connect(self._on_task_project_changed)
                row.task_renamed.connect(self._on_task_renamed)
                row.subtask_added.connect(self._on_subtask_added)
                row.subtask_toggled.connect(self._on_subtask_toggled)
                row.subtask_deleted.connect(self._on_subtask_deleted)
                row.subtask_renamed.connect(self._on_subtask_renamed)
                group_widget.tasks_layout.addWidget(row)

            self.content_layout.addWidget(group_widget)

        self.content_layout.addStretch()

    def refresh_notes(self) -> None:
        """Re-render the quick notes list for the selected date."""
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
        sync_today_logs(emit_signal=False)

    def _on_task_renamed(self, task_id: int, new_title: str) -> None:
        """Handle renaming a task."""
        self.repo.update_task_title(task_id, new_title)
        self.refresh_tasks()
        sync_today_logs(emit_signal=False)

    def _on_task_action(self, action_type: str, task_id: int) -> None:
        """Handle task deletion or other actions."""
        if action_type == "delete":
            self.repo.delete_task(task_id)
            self.refresh_tasks()
            sync_today_logs(emit_signal=False)

    def _on_task_project_changed(self, task_id: int, new_project: str) -> None:
        """Handle moving a task to a different section/project."""
        self.repo.create_or_update_project(new_project, [new_project.lower()])
        self.repo.update_task_project(task_id, new_project)
        self._populate_projects()
        self.refresh_tasks()
        sync_today_logs(emit_signal=False)

    def _on_subtask_added(self, task_id: int, title: str) -> None:
        """Add a subtask under a task."""
        self.repo.create_subtask(task_id, title)
        self.refresh_tasks()
        self.state_machine.trigger_notify(duration_ms=3500)
        sync_today_logs(emit_signal=False)

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
        sync_today_logs(emit_signal=False)

    def _on_subtask_renamed(self, subtask_id: int, new_title: str) -> None:
        """Handle renaming a subtask."""
        self.repo.update_subtask_title(subtask_id, new_title)
        self.refresh_tasks()
        sync_today_logs(emit_signal=False)

    def _on_subtask_deleted(self, subtask_id: int) -> None:
        """Delete a subtask."""
        self.repo.delete_subtask(subtask_id)
        self.refresh_tasks()
        sync_today_logs(emit_signal=False)

    def _on_note_toggled(self, note_id: int, is_completed: bool) -> None:
        """Toggle note completion status."""
        self.repo.toggle_note_completed(note_id, is_completed)
        if is_completed:
            self.state_machine.trigger_complete(duration_ms=3500)
        else:
            self.state_machine.revert_to_baseline()
        sync_today_logs(emit_signal=False)

    def _on_note_deleted(self, note_id: int) -> None:
        """Delete a note."""
        self.repo.delete_note(note_id)
        self.refresh_notes()
        sync_today_logs(emit_signal=False)

    def _on_quick_add_task(self) -> None:
        """Submit quick task from bottom input bar."""
        title = self.add_input.text().strip()
        if not title:
            return

        proj = self.project_combo.currentText()
        if proj == "+ Create Section..." or not proj:
            proj = "Work"

        # If adding a task while viewing another date, switch to today so user sees their new task
        if self.selected_date != date.today():
            self.set_selected_date(date.today())

        task_id = self.repo.create_task(title, project_tag=proj)
        self.add_input.clear()
        self.refresh_tasks()
        self.state_machine.trigger_notify(duration_ms=3500)
        app_signals.task_created.emit(task_id)

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

        note_id = self.repo.create_note(content, project_tag=proj)
        self.note_input.clear()
        self.refresh_notes()
        self.state_machine.trigger_notify(duration_ms=3500)
        app_signals.note_created.emit(note_id)

    def _toggle_maximize_restore(self) -> None:
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event) -> None:
        """Handle window state changes (e.g. Maximize / Restore / Snap)."""
        if event.type() == event.Type.WindowStateChange:
            if self.isMaximized():
                self.max_btn.setText("❐")
                self.max_btn.setToolTip("Restore")
                if hasattr(self, "_shadow_effect"):
                    self._shadow_effect.setEnabled(False)
            else:
                self.max_btn.setText("□")
                self.max_btn.setToolTip("Maximize")
                if hasattr(self, "_shadow_effect"):
                    self._shadow_effect.setEnabled(True)
            self.update()
        super().changeEvent(event)

    def paintEvent(self, event) -> None:
        """Explicitly clear translucent surface buffer to prevent widget ghosting on resize/maximize."""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()
        super().paintEvent(event)

    # --- Mouse drag & double click for frameless window movement & maximize ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize_restore()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and not self._drag_pos.isNull() and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

