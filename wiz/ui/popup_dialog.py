"""Quick-Entry popup dialog for notes, hierarchical tasks, and subtask log tracking."""

from datetime import datetime, date
from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QFrame,
    QMessageBox,
    QInputDialog,
    QHeaderView,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.core.state_machine import StateMachine
from wiz.storage.models import StorageRepository, TaskRecord, SubtaskRecord, NoteRecord


DARK_STYLE = """
QDialog {
    background-color: #16161D;
    color: #F7F3EA;
    border: 1px solid #2E2E3C;
    border-radius: 12px;
}
QLabel {
    color: #F7F3EA;
    font-family: 'Segoe UI', sans-serif;
}
QLineEdit, QComboBox {
    background-color: #21212B;
    color: #FFFFFF;
    border: 1px solid #363647;
    border-radius: 6px;
    padding: 8px 12px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #FF5E7E;
}
QPushButton {
    background-color: #2D2D3B;
    color: #F7F3EA;
    border: 1px solid #3E3E50;
    border-radius: 6px;
    padding: 8px 16px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #3B3B4E;
    border-color: #FF5E7E;
}
QPushButton#primaryBtn {
    background-color: #FF5E7E;
    color: #FFFFFF;
    border: none;
}
QPushButton#primaryBtn:hover {
    background-color: #FF7592;
}
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background-color: #1E1E28;
    color: #A0A0B0;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: bold;
    font-size: 13px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background-color: #252533;
    color: #F7F3EA;
    border-bottom: 2px solid #FF5E7E;
}
QListWidget, QTreeWidget {
    background-color: #1C1C26;
    color: #F7F3EA;
    border: 1px solid #2B2B38;
    border-radius: 8px;
    padding: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QListWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #252533;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #2D2D3D;
    color: #FFFFFF;
}
QTreeWidget::item {
    padding: 4px 2px;
}
QHeaderView::section {
    background-color: #20202B;
    color: #A0A0B0;
    border: none;
    padding: 4px 8px;
    font-weight: bold;
}
"""


class QuickEntryDialog(QDialog):
    """
    Quick-Entry modal popup allowing fast capture of one-off notes
    or structured hierarchical tasks, subtasks, and progress logs.
    """

    def __init__(self, state_machine: StateMachine, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.state_machine = state_machine
        self.repo = repository or StorageRepository()

        self.setWindowTitle("Wiz — Log Activity")
        self.setMinimumSize(540, 520)
        self.setStyleSheet(DARK_STYLE)

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

        # Header Title
        header_layout = QHBoxLayout()
        title_label = QLabel("👻  Wiz Log Capture")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        self.main_layout.addLayout(header_layout)

        # Tabs: Notes vs Tasks
        self.tabs = QTabWidget()
        self.tab_notes = QWidget()
        self.tab_tasks = QWidget()

        self._setup_notes_tab()
        self._setup_tasks_tab()

        self.tabs.addTab(self.tab_notes, "📝  Quick Notes")
        self.tabs.addTab(self.tab_tasks, "📋  Tasks & Subtasks")
        self.main_layout.addWidget(self.tabs)

        # Load initial data
        self.refresh_notes()
        self.refresh_tasks()

    # --- Notes Tab ---

    def _setup_notes_tab(self) -> None:
        """Construct the quick notes capture view."""
        layout = QVBoxLayout(self.tab_notes)
        layout.setContentsMargins(6, 12, 6, 6)
        layout.setSpacing(10)

        # Input row
        input_layout = QHBoxLayout()
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("What did you just work on or note? (Press Enter)")
        self.note_input.returnPressed.connect(self._on_save_note)
        input_layout.addWidget(self.note_input, stretch=3)

        self.note_project_combo = QComboBox()
        self.note_project_combo.setEditable(True)
        self.note_project_combo.setPlaceholderText("Project Tag")
        self._populate_project_combos()
        input_layout.addWidget(self.note_project_combo, stretch=1)

        add_note_btn = QPushButton("Add Note")
        add_note_btn.setObjectName("primaryBtn")
        add_note_btn.clicked.connect(self._on_save_note)
        input_layout.addWidget(add_note_btn)

        layout.addLayout(input_layout)

        # Notes list for today
        list_header = QLabel("Today's Notes:")
        list_header.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        layout.addWidget(list_header)

        self.notes_list = QListWidget()
        self.notes_list.itemChanged.connect(self._on_note_item_changed)
        layout.addWidget(self.notes_list)

    def _populate_project_combos(self) -> None:
        """Populate project tag choices from the database."""
        projects = self.repo.get_all_projects()
        names = [""] + [p.name for p in projects]
        self.note_project_combo.clear()
        self.note_project_combo.addItems(names)
        if hasattr(self, "task_project_combo"):
            self.task_project_combo.clear()
            self.task_project_combo.addItems(names)

    def _on_save_note(self) -> None:
        """Save a new note and trigger celebration state if note is completed."""
        content = self.note_input.text().strip()
        if not content:
            return

        tag = self.note_project_combo.currentText().strip() or None
        note_id = self.repo.create_note(content, project_tag=tag)

        self.note_input.clear()
        self.refresh_notes()

        # Emit signal and trigger mascot celebration
        app_signals.note_created.emit(note_id)
        self.state_machine.trigger_complete(duration_ms=3000)

    def refresh_notes(self) -> None:
        """Reload notes from repository."""
        self.notes_list.blockSignals(True)
        self.notes_list.clear()

        notes = self.repo.get_notes_for_date(date.today())
        for note in notes:
            item = QListWidgetItem()
            prefix = f"[{note.project_tag}] " if note.project_tag else ""
            item.setText(f"{prefix}{note.content}  ({note.created_at.strftime('%H:%M')})")
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if note.is_completed else Qt.CheckState.Unchecked)

            if note.is_completed:
                item.setForeground(QColor("#808090"))
            self.notes_list.addItem(item)

        self.notes_list.blockSignals(False)

    def _on_note_item_changed(self, item: QListWidgetItem) -> None:
        """Handle toggling note completed checkbox."""
        note_id = item.data(Qt.ItemDataRole.UserRole)
        is_checked = (item.checkState() == Qt.CheckState.Checked)
        self.repo.toggle_note_completed(note_id, is_checked)

        if is_checked:
            item.setForeground(QColor("#808090"))
            self.state_machine.trigger_complete(duration_ms=3000)
        else:
            item.setForeground(QColor("#F7F3EA"))

    # --- Tasks Tab ---

    def _setup_tasks_tab(self) -> None:
        """Construct the hierarchical task management view."""
        layout = QVBoxLayout(self.tab_tasks)
        layout.setContentsMargins(6, 12, 6, 6)
        layout.setSpacing(10)

        # Task input row
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Create a new task... (e.g. Build TurfLine booking)")
        self.task_input.returnPressed.connect(self._on_save_task)
        input_layout.addWidget(self.task_input, stretch=3)

        self.task_project_combo = QComboBox()
        self.task_project_combo.setEditable(True)
        self.task_project_combo.setPlaceholderText("Project Tag")
        input_layout.addWidget(self.task_project_combo, stretch=1)

        add_task_btn = QPushButton("Add Task")
        add_task_btn.setObjectName("primaryBtn")
        add_task_btn.clicked.connect(self._on_save_task)
        input_layout.addWidget(add_task_btn)

        layout.addLayout(input_layout)

        # Task hierarchy tree view
        self.task_tree = QTreeWidget()
        self.task_tree.setHeaderLabels(["Task / Subtask / Log Trail", "Status", "Time"])
        self.task_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.task_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.task_tree)

        # Action buttons for selected tree item
        btn_layout = QHBoxLayout()

        add_subtask_btn = QPushButton("➕ Add Subtask")
        add_subtask_btn.clicked.connect(self._on_add_subtask_prompt)
        btn_layout.addWidget(add_subtask_btn)

        add_log_btn = QPushButton("💬 Add Progress Log")
        add_log_btn.clicked.connect(self._on_add_log_prompt)
        btn_layout.addWidget(add_log_btn)

        toggle_status_btn = QPushButton("✓ Toggle Done")
        toggle_status_btn.clicked.connect(self._on_toggle_status_selected)
        btn_layout.addWidget(toggle_status_btn)

        layout.addLayout(btn_layout)

    def _on_save_task(self) -> None:
        """Create a new parent task."""
        title = self.task_input.text().strip()
        if not title:
            return

        tag = self.task_project_combo.currentText().strip() or None
        task_id = self.repo.create_task(title, project_tag=tag)

        self.task_input.clear()
        self.refresh_tasks()
        app_signals.task_created.emit(task_id)

    def refresh_tasks(self) -> None:
        """Reload task hierarchy tree."""
        self.task_tree.clear()
        tasks = self.repo.get_task_hierarchy()

        for task in tasks:
            task_item = QTreeWidgetItem(self.task_tree)
            tag_str = f"[{task.project_tag}] " if task.project_tag else ""
            task_item.setText(0, f"📌 {tag_str}{task.title}")
            task_item.setText(1, task.status.upper().replace("_", " "))
            task_item.setText(2, task.created_at.strftime("%H:%M"))
            task_item.setData(0, Qt.ItemDataRole.UserRole, ("task", task.id, task.status))

            # Colorize status
            if task.status == "done":
                task_item.setForeground(0, QColor("#808090"))
                task_item.setForeground(1, QColor("#4EAA64"))
            elif task.status == "in_progress":
                task_item.setForeground(1, QColor("#FFAE33"))
            else:
                task_item.setForeground(1, QColor("#A0A0B0"))

            # Parent logs
            for log in task.task_logs:
                log_item = QTreeWidgetItem(task_item)
                log_item.setText(0, f"  💬 {log.content}")
                log_item.setText(2, log.created_at.strftime("%H:%M"))
                log_item.setForeground(0, QColor("#B0B0C0"))

            # Subtasks
            for subtask in task.subtasks:
                sub_item = QTreeWidgetItem(task_item)
                sub_item.setText(0, f"  ↳ {subtask.title}")
                sub_item.setText(1, subtask.status.upper().replace("_", " "))
                sub_item.setText(2, subtask.created_at.strftime("%H:%M"))
                sub_item.setData(0, Qt.ItemDataRole.UserRole, ("subtask", subtask.id, subtask.status))

                if subtask.status == "done":
                    sub_item.setForeground(0, QColor("#808090"))
                    sub_item.setForeground(1, QColor("#4EAA64"))
                elif subtask.status == "in_progress":
                    sub_item.setForeground(1, QColor("#FFAE33"))

                # Subtask logs
                for log in subtask.logs:
                    sub_log_item = QTreeWidgetItem(sub_item)
                    sub_log_item.setText(0, f"    💬 {log.content}")
                    sub_log_item.setText(2, log.created_at.strftime("%H:%M"))
                    sub_log_item.setForeground(0, QColor("#B0B0C0"))

            task_item.setExpanded(True)

    def _on_add_subtask_prompt(self) -> None:
        """Prompt to add a subtask under the selected task."""
        item = self.task_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Select Task", "Please select a task to add a subtask under.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type, item_id, _ = data
        task_id = item_id if item_type == "task" else None
        if item_type == "subtask":
            # If a subtask was selected, get parent task
            parent = item.parent()
            if parent:
                p_data = parent.data(0, Qt.ItemDataRole.UserRole)
                if p_data:
                    task_id = p_data[1]

        if not task_id:
            return

        text, ok = QInputDialog.getText(self, "New Subtask", "Enter subtask title:")
        if ok and text.strip():
            self.repo.create_subtask(task_id, text.strip())
            self.refresh_tasks()

    def _on_add_log_prompt(self) -> None:
        """Prompt to append a timestamped progress log to the selected task or subtask."""
        item = self.task_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Select Item", "Please select a task or subtask to add a progress log.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type, item_id, _ = data
        if item_type == "task":
            task_id = item_id
            subtask_id = None
        else:
            subtask_id = item_id
            parent = item.parent()
            p_data = parent.data(0, Qt.ItemDataRole.UserRole) if parent else None
            task_id = p_data[1] if p_data else item_id

        text, ok = QInputDialog.getText(self, "Add Progress Update", "Log entry (e.g. hit CORS bug / fixed and testing):")
        if ok and text.strip():
            self.repo.add_task_log(task_id, text.strip(), subtask_id=subtask_id)
            self.refresh_tasks()

    def _on_toggle_status_selected(self) -> None:
        """Toggle status of selected task or subtask through: not_started -> in_progress -> done."""
        item = self.task_tree.currentItem()
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type, item_id, current_status = data
        next_status_map = {
            "not_started": "in_progress",
            "in_progress": "done",
            "done": "not_started",
        }
        next_status = next_status_map.get(current_status, "in_progress")

        if item_type == "task":
            self.repo.update_task_status(item_id, next_status)
        else:
            self.repo.update_subtask_status(item_id, next_status)

        if next_status == "done":
            self.state_machine.trigger_complete(duration_ms=3500)

        self.refresh_tasks()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Close dialog on Escape key."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
