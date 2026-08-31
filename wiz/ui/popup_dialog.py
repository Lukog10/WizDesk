"""
Project Tracking & Task Management Window for WizDesk.
Implements the card-based reference design with hierarchical subtasks,
timestamped logs, project tagging, and Obsidian sync integration.
"""

from datetime import datetime, date
from typing import Optional, List, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QRectF
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
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.core.state_machine import StateMachine
from wiz.storage.models import StorageRepository, TaskRecord, SubtaskRecord, TaskLogRecord


class CircularCheckButton(QWidget):
    """Circular status check button with To Do, In Progress, and Done states."""

    status_changed = pyqtSignal(str)  # 'not_started', 'in_progress', 'done'

    def __init__(self, status: str = "not_started", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._status = status
        self.setFixedSize(24, 24)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    @property
    def status(self) -> str:
        return self._status

    def set_status(self, status: str) -> None:
        if self._status != status:
            self._status = status
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Toggle between not_started and done (or advance state)
            if self._status in ("done", "completed"):
                self._status = "not_started"
            else:
                self._status = "done"
            self.update()
            self.status_changed.emit(self._status)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(2.0, 2.0, 20.0, 20.0)

        if self._status in ("done", "completed"):
            # Solid green circle with crisp white checkmark
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#34C759"))
            painter.drawEllipse(rect)

            # Draw white checkmark
            pen = QPen(QColor("#FFFFFF"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(int(rect.x() + 5.5), int(rect.y() + 10.5), int(rect.x() + 9.0), int(rect.y() + 14.0))
            painter.drawLine(int(rect.x() + 9.0), int(rect.y() + 14.0), int(rect.x() + 15.0), int(rect.y() + 6.5))

        elif self._status in ("in_progress", "pending"):
            # Subtle accent ring with centered dot
            pen = QPen(QColor("#007AFF"), 2.0, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(QColor("#F0F7FF"))
            painter.drawEllipse(rect)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#007AFF"))
            inner_rect = QRectF(8.0, 8.0, 8.0, 8.0)
            painter.drawEllipse(inner_rect)

        else:
            # Empty circular outline
            pen = QPen(QColor("#C7C7CC"), 1.8, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(rect)

        painter.end()


class FlagButton(QWidget):
    """Vector priority flag button."""

    toggled = pyqtSignal(bool)

    def __init__(self, flagged: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._flagged = flagged
        self.setFixedSize(22, 22)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    @property
    def isFlagged(self) -> bool:
        return self._flagged

    def setFlagged(self, value: bool) -> None:
        if self._flagged != value:
            self._flagged = value
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._flagged = not self._flagged
            self.update()
            self.toggled.emit(self._flagged)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = QColor("#34C759") if self._flagged else QColor("#C7C7CC")
        pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if self._flagged:
            painter.setBrush(color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw flagpole
        painter.drawLine(5, 3, 5, 19)

        # Draw flag banner
        path = QPainterPath()
        path.moveTo(5, 4)
        path.lineTo(16, 8)
        path.lineTo(5, 12)
        path.closeSubpath()
        painter.drawPath(path)

        painter.end()


class SegmentedFilterBar(QWidget):
    """Pill capsule segmented filter bar (All, To Do, In Progress, Done)."""

    filter_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.options = ["All", "To Do", "In Progress", "Done"]
        self.current_filter = "All"
        self._buttons: Dict[str, QPushButton] = {}

        self.setFixedHeight(42)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(4)

        self.setStyleSheet("""
            QWidget {
                background-color: #EFEFF4;
                border-radius: 12px;
            }
        """)

        for opt in self.options:
            btn = QPushButton(opt)
            btn.setFixedHeight(34)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, o=opt: self.set_active_filter(o))
            self._buttons[opt] = btn
            self.layout.addWidget(btn)

        self._update_button_styles()

    def set_active_filter(self, filter_name: str) -> None:
        if filter_name in self.options and self.current_filter != filter_name:
            self.current_filter = filter_name
            self._update_button_styles()
            self.filter_changed.emit(filter_name)

    def _update_button_styles(self) -> None:
        for opt, btn in self._buttons.items():
            if opt == self.current_filter:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #111113;
                        border: none;
                        border-radius: 9px;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 13px;
                        font-weight: bold;
                        padding: 0 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #8E8E93;
                        border: none;
                        border-radius: 9px;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 13px;
                        font-weight: 500;
                        padding: 0 14px;
                    }
                    QPushButton:hover {
                        color: #1A1A1E;
                        background-color: rgba(255, 255, 255, 0.5);
                    }
                """)


class TaskCardWidget(QFrame):
    """
    Elevated card widget representing a task, with circular check button,
    timestamp, priority flag, and expandable subtask/log drawer.
    """

    status_toggled = pyqtSignal(int, str)  # task_id, new_status
    subtask_toggled = pyqtSignal(int, str)  # subtask_id, new_status
    subtask_added = pyqtSignal(int, str)  # task_id, title
    log_added = pyqtSignal(int, str)  # task_id, content
    task_deleted = pyqtSignal(int)  # task_id

    def __init__(self, task: TaskRecord, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task = task
        self.task_id = task.id or 0
        self._is_expanded = False

        self.setObjectName("taskCard")
        self.setStyleSheet("""
            QFrame#taskCard {
                background-color: #FFFFFF;
                border: 1px solid #ECECEF;
                border-radius: 16px;
            }
        """)

        # Add card shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 12))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(16, 14, 16, 14)
        self.card_layout.setSpacing(10)

        # --- Top Header Row ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # 1. Circular Checkbox
        is_done = task.status in ("done", "completed")
        self.check_btn = CircularCheckButton(status=task.status, parent=self)
        self.check_btn.status_changed.connect(self._on_status_changed)
        header_layout.addWidget(self.check_btn)

        # 2. Middle Content (Title + Timestamp/Metadata)
        content_col = QVBoxLayout()
        content_col.setSpacing(3)

        self.title_label = QLabel(task.title)
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self._update_title_style(is_done)
        content_col.addWidget(self.title_label)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        time_str = task.created_at.strftime("%I:%M %p").lstrip("0")
        self.time_label = QLabel(f"{time_str}")
        self.time_label.setStyleSheet("color: #8E8E93; font-size: 12px; font-family: 'Segoe UI';")
        meta_layout.addWidget(self.time_label)

        if task.project_tag:
            tag_label = QLabel(f"[{task.project_tag}]")
            tag_label.setStyleSheet("color: #007AFF; font-size: 11px; font-weight: bold; font-family: 'Segoe UI';")
            meta_layout.addWidget(tag_label)

        if task.subtasks:
            done_st = sum(1 for st in task.subtasks if st.status in ("done", "completed"))
            st_badge = QLabel(f"{done_st}/{len(task.subtasks)} subtasks")
            st_badge.setStyleSheet("color: #636366; font-size: 11px; font-family: 'Segoe UI';")
            meta_layout.addWidget(st_badge)

        meta_layout.addStretch()
        content_col.addLayout(meta_layout)
        header_layout.addLayout(content_col, stretch=1)

        # 3. Flag / Priority Button
        self.flag_btn = FlagButton(flagged=is_done, parent=self)
        header_layout.addWidget(self.flag_btn)

        # 4. Expand Chevron
        self.expand_btn = QPushButton("v" if self._is_expanded else ">")
        self.expand_btn.setFixedSize(20, 20)
        self.expand_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8E8E93;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #111111;
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.expand_btn)

        self.card_layout.addLayout(header_layout)

        # --- Expandable Detail Drawer ---
        self.drawer_widget = QWidget()
        self.drawer_widget.setVisible(False)
        self.drawer_layout = QVBoxLayout(self.drawer_widget)
        self.drawer_layout.setContentsMargins(36, 6, 0, 4)
        self.drawer_layout.setSpacing(8)

        # Subtasks Section (PRD 4.4)
        if task.subtasks:
            st_header = QLabel("Subtasks:")
            st_header.setStyleSheet("color: #8E8E93; font-size: 11px; font-weight: bold; text-transform: uppercase;")
            self.drawer_layout.addWidget(st_header)

            for st in task.subtasks:
                st_row = QHBoxLayout()
                st_done = st.status in ("done", "completed")

                st_check = CircularCheckButton(status=st.status, parent=self)
                st_check.setFixedSize(18, 18)
                st_check.status_changed.connect(lambda s, st_id=st.id: self.subtask_toggled.emit(st_id or 0, s))
                st_row.addWidget(st_check)

                st_text = QLabel(st.title)
                st_text.setFont(QFont("Segoe UI", 10))
                if st_done:
                    st_text.setStyleSheet("color: #8E8E93; text-decoration: line-through;")
                else:
                    st_text.setStyleSheet("color: #1A1A1E;")
                st_row.addWidget(st_text, stretch=1)
                self.drawer_layout.addLayout(st_row)

        # Subtask quick add
        add_st_layout = QHBoxLayout()
        self.st_input = QLineEdit()
        self.st_input.setPlaceholderText("+ Add subtask... (Enter)")
        self.st_input.setStyleSheet("""
            QLineEdit {
                background-color: #F6F6F8;
                color: #1A1A1E;
                border: 1px solid #E2E2E6;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
        """)
        self.st_input.returnPressed.connect(self._on_add_subtask)
        add_st_layout.addWidget(self.st_input)
        self.drawer_layout.addLayout(add_st_layout)

        # Task Running Logs Trail (PRD 4.4)
        if task.task_logs:
            log_header = QLabel("Progress Log Trail:")
            log_header.setStyleSheet("color: #8E8E93; font-size: 11px; font-weight: bold; text-transform: uppercase;")
            self.drawer_layout.addWidget(log_header)

            for log in task.task_logs:
                time_tag = log.created_at.strftime("%H:%M")
                log_row = QLabel(f"- {time_tag} - {log.content}")
                log_row.setStyleSheet("color: #48484A; font-size: 12px; font-family: 'Consolas', monospace;")
                self.drawer_layout.addWidget(log_row)

        # Log quick add
        add_log_layout = QHBoxLayout()
        self.log_input = QLineEdit()
        self.log_input.setPlaceholderText("+ Add progress update log... (Enter)")
        self.log_input.setStyleSheet("""
            QLineEdit {
                background-color: #F6F6F8;
                color: #1A1A1E;
                border: 1px solid #E2E2E6;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
        """)
        self.log_input.returnPressed.connect(self._on_add_log)
        add_log_layout.addWidget(self.log_input)
        self.drawer_layout.addLayout(add_log_layout)

        # Action bar
        act_layout = QHBoxLayout()
        del_btn = QPushButton("Delete Task")
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #FF3B30;
                border: none;
                font-size: 11.5px;
                font-weight: bold;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        del_btn.clicked.connect(lambda: self.task_deleted.emit(self.task_id))
        act_layout.addWidget(del_btn)
        act_layout.addStretch()
        self.drawer_layout.addLayout(act_layout)

        self.card_layout.addWidget(self.drawer_widget)

        # Context Menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def toggle_expand(self) -> None:
        self._is_expanded = not self._is_expanded
        self.drawer_widget.setVisible(self._is_expanded)
        self.expand_btn.setText("v" if self._is_expanded else ">")

    def _update_title_style(self, is_done: bool) -> None:
        if is_done:
            self.title_label.setStyleSheet("""
                QLabel {
                    color: #8E8E93;
                    text-decoration: line-through;
                    font-size: 15px;
                    font-weight: bold;
                }
            """)
        else:
            self.title_label.setStyleSheet("""
                QLabel {
                    color: #1C1C1E;
                    text-decoration: none;
                    font-size: 15px;
                    font-weight: bold;
                }
            """)

    def _on_status_changed(self, new_status: str) -> None:
        is_done = new_status in ("done", "completed")
        self._update_title_style(is_done)
        self.flag_btn.setFlagged(is_done)
        self.status_toggled.emit(self.task_id, new_status)

    def _on_add_subtask(self) -> None:
        title = self.st_input.text().strip()
        if title:
            self.subtask_added.emit(self.task_id, title)
            self.st_input.clear()

    def _on_add_log(self) -> None:
        content = self.log_input.text().strip()
        if content:
            self.log_added.emit(self.task_id, content)
            self.log_input.clear()

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                color: #1A1A1E;
                border: 1px solid #E0E0E6;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #F0F0F4;
                color: #000000;
            }
        """)

        action_todo = menu.addAction("Move to To Do")
        action_prog = menu.addAction("Move to In Progress")
        action_done = menu.addAction("Move to Done")
        menu.addSeparator()
        action_delete = menu.addAction("Delete Task")

        action = menu.exec(self.mapToGlobal(pos))
        if action == action_todo:
            self.status_toggled.emit(self.task_id, "not_started")
        elif action == action_prog:
            self.status_toggled.emit(self.task_id, "in_progress")
        elif action == action_done:
            self.status_toggled.emit(self.task_id, "done")
        elif action == action_delete:
            self.task_deleted.emit(self.task_id)


class QuickEntryDialog(QDialog):
    """
    Project Tracking and Task Management Window for WizDesk.
    Matches the card-based reference design with header navigation,
    segmented filter capsule bar, task card list, and rapid task creation.
    """

    def __init__(self, state_machine: StateMachine, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.state_machine = state_machine
        self.repo = repository or StorageRepository()
        self.active_project_filter: Optional[str] = None

        # Window settings
        self.setWindowTitle("WizDesk - My Tasks")
        self.setMinimumSize(420, 680)
        self.resize(460, 720)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        # Outer Layout
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(14, 14, 14, 14)
        self.outer_layout.setSpacing(0)

        # Main Outer Card Frame (#FAFAFC)
        self.outer_frame = QFrame()
        self.outer_frame.setObjectName("mainFrame")
        self.outer_frame.setStyleSheet("""
            QFrame#mainFrame {
                background-color: #FAFAFC;
                border: 1px solid #EBEBF0;
                border-radius: 28px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 8)
        self.outer_frame.setGraphicsEffect(shadow)

        self.frame_layout = QVBoxLayout(self.outer_frame)
        self.frame_layout.setContentsMargins(24, 20, 24, 24)
        self.frame_layout.setSpacing(16)

        # --- Top Navigation Bar (Hamburger, Title, Options) ---
        nav_layout = QHBoxLayout()

        # Hamburger Menu Button
        self.menu_btn = QPushButton("≡")
        self.menu_btn.setFixedSize(32, 32)
        self.menu_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 22px;
                font-weight: bold;
                color: #1C1C1E;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #EFEFF4;
            }
        """)
        self.menu_btn.clicked.connect(self._show_project_menu)
        nav_layout.addWidget(self.menu_btn)

        nav_layout.addStretch()

        # Options Button (···)
        self.options_btn = QPushButton("···")
        self.options_btn.setFixedSize(32, 32)
        self.options_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.options_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 20px;
                font-weight: bold;
                color: #1C1C1E;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #EFEFF4;
            }
        """)
        self.options_btn.clicked.connect(self._show_options_menu)
        nav_layout.addWidget(self.options_btn)

        # Close Window Button (x)
        self.close_btn = QPushButton("x")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                font-weight: bold;
                color: #8E8E93;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(0,0,0,0.06);
                color: #111111;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        nav_layout.addWidget(self.close_btn)

        self.frame_layout.addLayout(nav_layout)

        # --- Header Title & Date Subtitle ---
        header_col = QVBoxLayout()
        header_col.setSpacing(4)

        self.title_label = QLabel("My Tasks")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #111113;
                font-family: 'Segoe UI', sans-serif;
                font-size: 28px;
                font-weight: 800;
            }
        """)
        header_col.addWidget(self.title_label)

        current_date_str = datetime.now().strftime("%B %d, %Y")
        self.date_label = QLabel(current_date_str)
        self.date_label.setStyleSheet("""
            QLabel {
                color: #8E8E93;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        header_col.addWidget(self.date_label)

        self.frame_layout.addLayout(header_col)

        # --- Segmented Filter Bar (All, To Do, In Progress, Done) ---
        self.filter_bar = SegmentedFilterBar()
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        self.frame_layout.addWidget(self.filter_bar)

        # --- Task Card List (Scroll Area) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #D1D1D6;
                min-height: 24px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.task_list_container = QWidget()
        self.task_list_container.setStyleSheet("background: transparent;")
        self.task_list_layout = QVBoxLayout(self.task_list_container)
        self.task_list_layout.setContentsMargins(0, 4, 0, 4)
        self.task_list_layout.setSpacing(12)
        self.task_list_layout.addStretch()

        self.scroll_area.setWidget(self.task_list_container)
        self.frame_layout.addWidget(self.scroll_area, stretch=1)

        # --- Bottom Add Task Bar ---
        add_card = QFrame()
        add_card.setObjectName("addCard")
        add_card.setStyleSheet("""
            QFrame#addCard {
                background-color: #FFFFFF;
                border: 1px solid #ECECEF;
                border-radius: 16px;
            }
        """)
        add_layout = QHBoxLayout(add_card)
        add_layout.setContentsMargins(14, 8, 14, 8)
        add_layout.setSpacing(8)

        plus_icon = QLabel("+")
        plus_icon.setStyleSheet("color: #8E8E93; font-size: 18px; font-weight: bold;")
        add_layout.addWidget(plus_icon)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("Add a new task... (Press Enter)")
        self.add_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #1C1C1E;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
        """)
        self.add_input.returnPressed.connect(self._on_quick_add_task)
        add_layout.addWidget(self.add_input, stretch=3)

        self.project_combo = QComboBox()
        self.project_combo.setEditable(True)
        self.project_combo.setPlaceholderText("Project")
        self.project_combo.setStyleSheet("""
            QComboBox {
                background-color: #F2F2F7;
                color: #1C1C1E;
                border: none;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self._populate_projects()
        add_layout.addWidget(self.project_combo, stretch=1)

        self.frame_layout.addWidget(add_card)
        self.outer_layout.addWidget(self.outer_frame)

        # Frameless Drag state
        self._drag_pos = QPoint()

        # Seed initial tasks if database is brand new
        self._seed_initial_data_if_empty()

        # Initial render
        self.refresh_tasks()

    def _seed_initial_data_if_empty(self) -> None:
        """Seed sample tasks matching the reference aesthetic if empty."""
        existing = self.repo.get_task_hierarchy()
        if not existing:
            self.repo.create_or_update_project("Work", ["work", "email", "standup", "report", "presentation"])
            self.repo.create_or_update_project("Personal", ["personal", "workout", "gym"])

            t1 = self.repo.create_task("Reply to emails", project_tag="Work")
            t2 = self.repo.create_task("Prepare presentation", project_tag="Work")
            st2_1 = self.repo.create_subtask(t2, "Gather slide metrics")
            st2_2 = self.repo.create_subtask(t2, "Review with team")

            t3 = self.repo.create_task("Team stand-up", project_tag="Work")
            t4 = self.repo.create_task("Review report", project_tag="Work")

            t5 = self.repo.create_task("Workout", project_tag="Personal")
            self.repo.update_task_status(t5, "done")

    def _populate_projects(self) -> None:
        projects = self.repo.get_all_projects()
        names = [p.name for p in projects]
        if not names:
            names = ["Work", "Personal"]
        self.project_combo.clear()
        self.project_combo.addItems(names)

    def _show_project_menu(self) -> None:
        """Hamburger menu to filter by project."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                color: #1A1A1E;
                border: 1px solid #E0E0E6;
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #F2F2F7;
            }
        """)

        all_action = menu.addAction("All Projects")
        menu.addSeparator()

        projects = self.repo.get_all_projects()
        proj_actions = {}
        for p in projects:
            proj_actions[menu.addAction(p.name)] = p.name

        action = menu.exec(self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height() + 4)))
        if action == all_action:
            self.active_project_filter = None
            self.title_label.setText("My Tasks")
            self.refresh_tasks()
        elif action in proj_actions:
            chosen = proj_actions[action]
            self.active_project_filter = chosen
            self.title_label.setText(chosen)
            self.refresh_tasks()

    def _show_options_menu(self) -> None:
        """Options menu for sync, settings, and project management."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                color: #1A1A1E;
                border: 1px solid #E0E0E6;
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #F2F2F7;
            }
        """)

        sync_action = menu.addAction("Sync to Obsidian Vault")
        settings_action = menu.addAction("Settings and Preferences")
        menu.addSeparator()
        add_proj_action = menu.addAction("Create New Project Tag")

        action = menu.exec(self.options_btn.mapToGlobal(QPoint(0, self.options_btn.height() + 4)))
        if action == sync_action:
            app_signals.request_sync.emit()
        elif action == settings_action:
            app_signals.request_settings.emit()
        elif action == add_proj_action:
            name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
            if ok and name.strip():
                self.repo.create_or_update_project(name.strip(), [name.strip().lower()])
                self._populate_projects()

    def _on_filter_changed(self, filter_name: str) -> None:
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        """Re-populate task card list."""
        while self.task_list_layout.count() > 1:
            child = self.task_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        filter_name = self.filter_bar.current_filter
        tasks = self.repo.get_task_hierarchy(status_filter=filter_name)

        if self.active_project_filter:
            tasks = [t for t in tasks if t.project_tag == self.active_project_filter]

        if not tasks:
            empty_lbl = QLabel(f"No {filter_name.lower()} tasks.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #8E8E93; font-size: 14px; font-family: 'Segoe UI'; padding: 40px 0;")
            self.task_list_layout.insertWidget(0, empty_lbl)
            return

        for idx, task in enumerate(tasks):
            card = TaskCardWidget(task, self.task_list_container)
            card.status_toggled.connect(self._on_task_status_toggled)
            card.subtask_toggled.connect(self._on_subtask_status_toggled)
            card.subtask_added.connect(self._on_subtask_added)
            card.log_added.connect(self._on_log_added)
            card.task_deleted.connect(self._on_task_deleted)
            self.task_list_layout.insertWidget(idx, card)

    def _on_task_status_toggled(self, task_id: int, new_status: str) -> None:
        self.repo.update_task_status(task_id, new_status)
        if new_status in ("done", "completed"):
            self.state_machine.trigger_complete(duration_ms=3000)
        elif new_status in ("in_progress", "pending"):
            self.state_machine.trigger_working()

        self.refresh_tasks()

    def _on_subtask_status_toggled(self, subtask_id: int, new_status: str) -> None:
        self.repo.update_subtask_status(subtask_id, new_status)
        if new_status in ("done", "completed"):
            self.state_machine.trigger_complete(duration_ms=2000)
        self.refresh_tasks()

    def _on_subtask_added(self, task_id: int, title: str) -> None:
        self.repo.create_subtask(task_id, title)
        self.refresh_tasks()

    def _on_log_added(self, task_id: int, content: str) -> None:
        self.repo.add_task_log(task_id, content)
        self.refresh_tasks()

    def _on_task_deleted(self, task_id: int) -> None:
        self.repo.delete_task(task_id)
        self.refresh_tasks()

    def _on_quick_add_task(self) -> None:
        title = self.add_input.text().strip()
        if not title:
            return

        project = self.project_combo.currentText().strip() or (self.active_project_filter or "Work")
        task_id = self.repo.create_task(title, project_tag=project)

        self.add_input.clear()
        self._populate_projects()
        self.refresh_tasks()
        app_signals.task_created.emit(task_id)

    # --- Mouse drag for frameless movement ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
