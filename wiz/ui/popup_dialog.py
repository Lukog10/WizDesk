"""Minimalist, card-based activity and task tracking dialog matching the reference design."""

from datetime import datetime, date
from typing import Optional, List, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QRect, QRectF
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
from wiz.storage.models import StorageRepository, TaskRecord, SubtaskRecord


class RoundedCheckbox(QWidget):
    """Custom rounded-square checkbox widget matching the reference aesthetic."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(20, 20)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    @property
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        if self._checked != value:
            self._checked = value
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

        rect = QRectF(2.0, 2.0, 16.0, 16.0)
        radius = 4.5

        if self._checked:
            # Filled dark rounded square with crisp white checkmark
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#18181B"))
            painter.drawRoundedRect(rect, radius, radius)

            # Draw white checkmark path
            pen = QPen(QColor("#FFFFFF"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(int(rect.x() + 4.5), int(rect.y() + 8.5), int(rect.x() + 7.5), int(rect.y() + 11.5))
            painter.drawLine(int(rect.x() + 7.5), int(rect.y() + 11.5), int(rect.x() + 12.0), int(rect.y() + 5.0))
        else:
            # Clean subtle grey rounded outline
            pen = QPen(QColor("#D0D0D6"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()


class SegmentedFilterBar(QWidget):
    """Pill capsule segmented filter bar (To-do, Completed, Pending, On Hold, Cancelled)."""

    filter_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.options = ["To-do", "Completed", "Pending", "On Hold", "Cancelled"]
        self.current_filter = "To-do"
        self._buttons: Dict[str, QPushButton] = {}

        self.setFixedHeight(38)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(3, 3, 3, 3)
        self.layout.setSpacing(2)

        self.setStyleSheet("""
            QWidget {
                background-color: #ECECF0;
                border-radius: 9px;
            }
        """)

        for opt in self.options:
            btn = QPushButton(opt)
            btn.setFixedHeight(32)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, o=opt: self.set_active_filter(o))
            self._buttons[opt] = btn
            self.layout.addWidget(btn)

        self._update_button_styles()

    def set_active_filter(self, filter_name: str) -> None:
        """Switch active filter tab."""
        if filter_name in self.options and self.current_filter != filter_name:
            self.current_filter = filter_name
            self._update_button_styles()
            self.filter_changed.emit(filter_name)

    def _update_button_styles(self) -> None:
        """Update button styles to give the active button a white pill elevation."""
        for opt, btn in self._buttons.items():
            if opt == self.current_filter:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #111113;
                        border: none;
                        border-radius: 7px;
                        font-family: 'Consolas', 'Cascadia Code', 'SF Mono', monospace;
                        font-size: 12.5px;
                        font-weight: bold;
                        padding: 0 10px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #72727D;
                        border: none;
                        border-radius: 7px;
                        font-family: 'Consolas', 'Cascadia Code', 'SF Mono', monospace;
                        font-size: 12.5px;
                        font-weight: 500;
                        padding: 0 10px;
                    }
                    QPushButton:hover {
                        color: #222226;
                        background-color: rgba(255, 255, 255, 0.4);
                    }
                """)


class TaskRowWidget(QWidget):
    """Single task row with custom checkbox and monospace label."""

    status_toggled = pyqtSignal(int, str)  # task_id, new_status
    action_requested = pyqtSignal(str, int)  # action_type, task_id

    def __init__(self, task: TaskRecord, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task = task
        self.task_id = task.id or 0

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(10)

        is_done = (task.status in ("done", "completed"))
        self.checkbox = RoundedCheckbox(checked=is_done, parent=self)
        self.checkbox.toggled.connect(self._on_checkbox_toggled)
        self.layout.addWidget(self.checkbox)

        self.label = QLabel(task.title)
        self.label.setFont(QFont("Consolas", 11, QFont.Weight.Medium))
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._update_label_style(is_done)
        self.layout.addWidget(self.label, stretch=1)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _update_label_style(self, is_done: bool) -> None:
        if is_done:
            self.label.setStyleSheet("""
                QLabel {
                    color: #9898A0;
                    text-decoration: line-through;
                    font-family: 'Consolas', 'Cascadia Code', monospace;
                    font-size: 13.5px;
                }
            """)
        else:
            self.label.setStyleSheet("""
                QLabel {
                    color: #1A1A1E;
                    text-decoration: none;
                    font-family: 'Consolas', 'Cascadia Code', monospace;
                    font-size: 13.5px;
                }
            """)

    def _on_checkbox_toggled(self, checked: bool) -> None:
        new_status = "done" if checked else "not_started"
        self._update_label_style(checked)
        self.status_toggled.emit(self.task_id, new_status)

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                color: #1A1A1E;
                border: 1px solid #E0E0E6;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
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

        action_todo = menu.addAction("Move to To-do")
        action_pending = menu.addAction("Move to Pending")
        action_on_hold = menu.addAction("Move to On Hold")
        action_cancelled = menu.addAction("Move to Cancelled")
        menu.addSeparator()
        action_delete = menu.addAction("Delete Task")

        action = menu.exec(self.mapToGlobal(pos))
        if action == action_todo:
            self.status_toggled.emit(self.task_id, "not_started")
        elif action == action_pending:
            self.status_toggled.emit(self.task_id, "in_progress")
        elif action == action_on_hold:
            self.status_toggled.emit(self.task_id, "on_hold")
        elif action == action_cancelled:
            self.status_toggled.emit(self.task_id, "cancelled")
        elif action == action_delete:
            self.action_requested.emit("delete", self.task_id)


class ProjectGroupWidget(QWidget):
    """Collapsible project section with chevron header (e.g. ▼ Work)."""

    def __init__(self, project_name: str, tasks: List[TaskRecord], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project_name = project_name
        self.tasks = tasks
        self._is_expanded = True

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 8, 0, 8)
        self.main_layout.setSpacing(6)

        # Header bar
        self.header_btn = QPushButton(f"v {project_name}")
        self.header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 15px;
                font-weight: bold;
                color: #111113;
                padding: 4px 0;
            }
            QPushButton:hover {
                color: #44444C;
            }
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
    Minimalist desktop window matching the reference design with dynamic date header,
    pill capsule filter bar, grouped project sections, and rounded checkboxes.
    """

    def __init__(self, state_machine: StateMachine, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.state_machine = state_machine
        self.repo = repository or StorageRepository()

        # Window settings
        self.setWindowTitle("WizDesk - Tasks")
        self.setMinimumSize(480, 560)
        self.resize(500, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        # Main Outer Container Layout
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(12, 12, 12, 12)
        self.outer_layout.setSpacing(0)

        # Outer rounded card frame (#E8E8EC)
        self.outer_frame = QFrame()
        self.outer_frame.setObjectName("outerFrame")
        self.outer_frame.setStyleSheet("""
            QFrame#outerFrame {
                background-color: #E6E6EA;
                border: 1px solid #D8D8DE;
                border-radius: 24px;
            }
        """)

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 6)
        self.outer_frame.setGraphicsEffect(shadow)

        self.frame_layout = QVBoxLayout(self.outer_frame)
        self.frame_layout.setContentsMargins(18, 14, 18, 18)
        self.frame_layout.setSpacing(12)

        # Top Bar: Date header + Window Controls (Minimize, Maximize, Close)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)
        top_bar.setSpacing(6)

        current_date_str = datetime.now().strftime("%B %d, %A")
        self.date_label = QLabel(current_date_str)
        self.date_label.setStyleSheet("""
            QLabel {
                color: #55555C;
                font-family: 'Consolas', 'Cascadia Code', 'SF Mono', monospace;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        top_bar.addStretch()
        top_bar.addWidget(self.date_label)
        top_bar.addStretch()

        # Window Controls Container
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(4)

        btn_style = """
            QPushButton {
                background: transparent;
                color: #777780;
                border: none;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 13px;
                font-weight: bold;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.08);
                color: #111111;
            }
        """

        # 1. Minimize Button
        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(22, 22)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(self.showMinimized)
        controls_layout.addWidget(self.min_btn)

        # 2. Maximize / Restore Button
        self.max_btn = QPushButton("□")
        self.max_btn.setFixedSize(22, 22)
        self.max_btn.setToolTip("Maximize")
        self.max_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.max_btn.setStyleSheet(btn_style)
        self.max_btn.clicked.connect(self._toggle_maximize_restore)
        controls_layout.addWidget(self.max_btn)

        # 3. Close Button
        self.close_btn = QPushButton("x")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setStyleSheet(btn_style)
        self.close_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.close_btn)

        top_bar.addLayout(controls_layout)
        self.frame_layout.addLayout(top_bar)

        # Inner Canvas Card (Pure White #FFFFFF)
        self.inner_card = QFrame()
        self.inner_card.setObjectName("innerCard")
        self.inner_card.setStyleSheet("""
            QFrame#innerCard {
                background-color: #FFFFFF;
                border-radius: 18px;
                border: 1px solid #ECECEF;
            }
        """)
        self.inner_layout = QVBoxLayout(self.inner_card)
        self.inner_layout.setContentsMargins(16, 16, 16, 16)
        self.inner_layout.setSpacing(12)

        # 1. Segmented Filter Capsule Bar
        self.filter_bar = SegmentedFilterBar()
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        self.inner_layout.addWidget(self.filter_bar)

        # 2. Scrollable Tasks Area
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
                background: #D8D8DC;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        self.inner_layout.addWidget(self.scroll_area, stretch=1)

        # 3. Bottom Inline Add Task Bar
        add_bar_layout = QHBoxLayout()
        add_bar_layout.setSpacing(8)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("+ Add task... (Press Enter)")
        self.add_input.setStyleSheet("""
            QLineEdit {
                background-color: #F6F6F8;
                color: #1A1A1E;
                border: 1px solid #E2E2E6;
                border-radius: 8px;
                padding: 8px 12px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 13px;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                border: 1.5px solid #111111;
            }
        """)
        self.add_input.returnPressed.connect(self._on_quick_add_task)
        add_bar_layout.addWidget(self.add_input, stretch=3)

        self.project_combo = QComboBox()
        self.project_combo.setEditable(True)
        self.project_combo.setPlaceholderText("Project")
        self.project_combo.setStyleSheet("""
            QComboBox {
                background-color: #F6F6F8;
                color: #1A1A1E;
                border: 1px solid #E2E2E6;
                border-radius: 8px;
                padding: 6px 10px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 12.5px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self._populate_projects()
        add_bar_layout.addWidget(self.project_combo, stretch=1)

        add_btn = QPushButton("Add")
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #111113;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 12.5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #333338;
            }
        """)
        add_btn.clicked.connect(self._on_quick_add_task)
        add_bar_layout.addWidget(add_btn)

        self.inner_layout.addLayout(add_bar_layout)

        self.frame_layout.addWidget(self.inner_card, stretch=1)
        self.outer_layout.addWidget(self.outer_frame)

        # Drag state for frameless window movement
        self._drag_pos = QPoint()

        # Seed sample projects/tasks if repository is completely blank
        self._seed_initial_data_if_empty()

        # Initial render
        self.refresh_tasks()

    def _seed_initial_data_if_empty(self) -> None:
        """Seed clean initial tasks matching the reference if database has no tasks."""
        existing = self.repo.get_task_hierarchy()
        if not existing:
            # Seed Work project
            self.repo.create_or_update_project("Work", ["work", "code", "landing", "testing"])
            self.repo.create_task("Finalize landing page wireframes", project_tag="Work")
            self.repo.create_task("Conduct user testing on prototypes", project_tag="Work")
            self.repo.create_task("Implement feedback and iterate on designs", project_tag="Work")

            # Seed Personal Projects
            self.repo.create_or_update_project("Personal Projects", ["personal", "figma", "motion", "hero"])
            self.repo.create_task("Explore motion interaction ideas", project_tag="Personal Projects")
            self.repo.create_task("Improve Figma variables structure", project_tag="Personal Projects")
            self.repo.create_task("Design new hero section concept", project_tag="Personal Projects")

    def _populate_projects(self) -> None:
        """Populate project selector choices."""
        projects = self.repo.get_all_projects()
        names = [p.name for p in projects]
        if not names:
            names = ["Work", "Personal Projects"]
        self.project_combo.clear()
        self.project_combo.addItems(names)

    def _on_filter_changed(self, filter_name: str) -> None:
        """Called when a segmented filter pill is clicked."""
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        """Re-render the task list grouped by project under the current filter."""
        # Clear existing rows in content layout
        while self.content_layout.count() > 1:
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        active_filter = self.filter_bar.current_filter
        tasks = self.repo.get_task_hierarchy(status_filter=active_filter)

        # Group tasks by project tag
        grouped: Dict[str, List[TaskRecord]] = {}
        for t in tasks:
            proj = t.project_tag or "General"
            grouped.setdefault(proj, []).append(t)

        if not grouped:
            empty_label = QLabel(f"No {active_filter.lower()} tasks found.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("""
                QLabel {
                    color: #9999A2;
                    font-family: 'Consolas', 'Cascadia Code', monospace;
                    font-size: 13px;
                    padding: 40px 0;
                }
            """)
            self.content_layout.insertWidget(0, empty_label)
            return

        idx = 0
        for project_name, task_list in grouped.items():
            group_widget = ProjectGroupWidget(project_name, task_list, self.content_widget)

            for task in task_list:
                row = TaskRowWidget(task, group_widget.tasks_container)
                row.status_toggled.connect(self._on_task_status_toggled)
                row.action_requested.connect(self._on_task_action)
                group_widget.tasks_layout.addWidget(row)

            self.content_layout.insertWidget(idx, group_widget)
            idx += 1

    def _on_task_status_toggled(self, task_id: int, new_status: str) -> None:
        """Handle checkbox check/uncheck status change."""
        self.repo.update_task_status(task_id, new_status)
        if new_status == "done":
            self.state_machine.trigger_complete(duration_ms=3000)

        # Refresh list
        self.refresh_tasks()

    def _on_task_action(self, action_type: str, task_id: int) -> None:
        """Handle task deletion or other actions."""
        if action_type == "delete":
            self.repo.delete_task(task_id)
            self.refresh_tasks()

    def _on_quick_add_task(self) -> None:
        """Add a new task under the active or chosen project."""
        title = self.add_input.text().strip()
        if not title:
            return

        project = self.project_combo.currentText().strip() or "Work"
        task_id = self.repo.create_task(title, project_tag=project)

        self.add_input.clear()
        self._populate_projects()
        self.refresh_tasks()
        app_signals.task_created.emit(task_id)

    def _toggle_maximize_restore(self) -> None:
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("□")
            self.max_btn.setToolTip("Maximize")
            self.outer_layout.setContentsMargins(12, 12, 12, 12)
            self.outer_frame.setStyleSheet("""
                QFrame#outerFrame {
                    background-color: #E6E6EA;
                    border: 1px solid #D8D8DE;
                    border-radius: 24px;
                }
            """)
        else:
            self.showMaximized()
            self.max_btn.setText("❐")
            self.max_btn.setToolTip("Restore")
            self.outer_layout.setContentsMargins(0, 0, 0, 0)
            self.outer_frame.setStyleSheet("""
                QFrame#outerFrame {
                    background-color: #E6E6EA;
                    border: none;
                    border-radius: 0px;
                }
            """)

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
