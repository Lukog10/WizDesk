"""
Compact, floating quick-bar popups for rapid task and note entry.
Triggered via Left Double-Click (Quick Task Bar) and Left Triple-Click (Quick Note Bar) on the Wiz Mascot.
"""

from typing import Optional, List
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QCursor, QGuiApplication, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QWidget,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.core.state_machine import StateMachine
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import CreateSectionDialog

FONT_SANS = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'SF Mono', monospace"


class QuickBarPopup(QDialog):
    """Floating, frameless compact bar popup for quick task and note logging."""

    def __init__(
        self,
        state_machine: StateMachine,
        repository: Optional[StorageRepository] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.state_machine = state_machine
        self.repo = repository or StorageRepository()
        self.mode = "task"  # "task" or "note"
        self.is_dark = (config.theme == "dark")
        self._last_selected_project = "Work"

        # Window configuration
        self.setWindowTitle("WizDesk - Quick Entry")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(500, 106)

        # Outer layout
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(12, 10, 12, 12)
        self.outer_layout.setSpacing(0)

        # Inner rounded card
        self.card = QFrame()
        self.card.setObjectName("quickBarCard")

        # Drop shadow
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(24)
        self._shadow.setOffset(0, 5)
        self.card.setGraphicsEffect(self._shadow)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 10, 14, 12)
        self.card_layout.setSpacing(8)

        # Header: Mode badge + Dismiss button
        hdr_layout = QHBoxLayout()
        hdr_layout.setContentsMargins(0, 0, 0, 0)
        hdr_layout.setSpacing(6)

        self.mode_badge = QLabel("✦ Quick Task")
        self.mode_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        hdr_layout.addWidget(self.mode_badge)

        self.hint_label = QLabel("(Double-click Wiz for Task, Triple-click for Note)")
        self.hint_label.setFont(QFont("Segoe UI", 8))
        hdr_layout.addWidget(self.hint_label)

        hdr_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setToolTip("Close (Esc)")
        self.close_btn.clicked.connect(self.hide)
        hdr_layout.addWidget(self.close_btn)

        self.card_layout.addLayout(hdr_layout)

        # Input Row: LineEdit + Project Selector + Submit Button
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.returnPressed.connect(self._on_submit)
        input_row.addWidget(self.input_field, stretch=1)

        self.project_combo = QComboBox()
        self.project_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.project_combo.setFixedWidth(135)
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        input_row.addWidget(self.project_combo)

        self.submit_btn = QPushButton("Add")
        self.submit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.submit_btn.clicked.connect(self._on_submit)
        input_row.addWidget(self.submit_btn)

        self.card_layout.addLayout(input_row)
        self.outer_layout.addWidget(self.card)

        # Listen for theme changes across app
        app_signals.theme_changed.connect(self.apply_theme)

        # Apply initial theme
        self.apply_theme(config.theme)
        self._populate_projects()

    def _populate_projects(self) -> None:
        """Populate project combo with database projects and section creator."""
        self.project_combo.blockSignals(True)
        current = self.project_combo.currentText() or self._last_selected_project
        self.project_combo.clear()

        projects = self.repo.get_all_projects()
        pnames = [p.name for p in projects]
        if not pnames:
            pnames = ["Work", "Personal"]

        for p in pnames:
            self.project_combo.addItem(p)

        self.project_combo.insertSeparator(self.project_combo.count())
        self.project_combo.addItem("+ Create Section...")

        if current in pnames:
            self.project_combo.setCurrentText(current)
        else:
            self.project_combo.setCurrentIndex(0)

        self.project_combo.blockSignals(False)

    def _on_project_changed(self, text: str) -> None:
        """Handle selection change or new section creation in combo box."""
        if text == "+ Create Section...":
            dlg = CreateSectionDialog(is_dark=self.is_dark, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_sec = dlg.section_name
                if new_sec:
                    self.repo.create_or_update_project(new_sec, [new_sec.lower()])
                    self._populate_projects()
                    self.project_combo.setCurrentText(new_sec)
                    self._last_selected_project = new_sec
            else:
                self.project_combo.setCurrentText(self._last_selected_project)
        elif text:
            self._last_selected_project = text

    def show_mode(self, mode: str = "task", mascot_rect: Optional[QRect] = None) -> None:
        """Configure mode ('task' or 'note'), reposition near mascot, and focus input."""
        self.mode = mode
        self._populate_projects()

        if mode == "note":
            self.mode_badge.setText("✦ Quick Work Note")
            self.input_field.setPlaceholderText("+ Log a quick work note... (Press Enter)")
            self.submit_btn.setText("Log Note")
        else:
            self.mode_badge.setText("✦ Quick Task")
            self.input_field.setPlaceholderText("+ Add task... (Press Enter)")
            self.submit_btn.setText("Add")

        self.input_field.clear()

        # Position smartly near the mascot
        if mascot_rect is not None and not mascot_rect.isNull():
            self._reposition_near_mascot(mascot_rect)

        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

    def _reposition_near_mascot(self, mascot_rect: QRect) -> None:
        """Position popup nicely adjacent to the mascot while respecting screen edges."""
        screen = QGuiApplication.screenAt(mascot_rect.center()) or QGuiApplication.primaryScreen()
        if not screen:
            return

        screen_geom = screen.availableGeometry()
        margin = 12

        # Center horizontally with mascot
        popup_w = self.width()
        popup_h = self.height()

        target_x = mascot_rect.center().x() - (popup_w // 2)
        target_x = max(screen_geom.left() + margin, min(target_x, screen_geom.right() - popup_w - margin))

        # Position above mascot if mascot is in lower half of screen; otherwise below
        if mascot_rect.center().y() > screen_geom.center().y():
            target_y = mascot_rect.top() - popup_h - 6
            if target_y < screen_geom.top() + margin:
                target_y = mascot_rect.bottom() + 6
        else:
            target_y = mascot_rect.bottom() + 6
            if target_y + popup_h > screen_geom.bottom() - margin:
                target_y = mascot_rect.top() - popup_h - 6

        target_y = max(screen_geom.top() + margin, min(target_y, screen_geom.bottom() - popup_h - margin))
        self.move(int(target_x), int(target_y))

    def _on_submit(self) -> None:
        """Handle task or note creation and broadcast events."""
        text = self.input_field.text().strip()
        if not text:
            return

        proj = self.project_combo.currentText()
        if proj == "+ Create Section..." or not proj:
            proj = "Work"

        if self.mode == "note":
            note_id = self.repo.create_note(text, project_tag=proj)
            self.state_machine.trigger_notify(duration_ms=3500)
            app_signals.note_created.emit(note_id)
        else:
            task_id = self.repo.create_task(text, project_tag=proj)
            self.state_machine.trigger_notify(duration_ms=3500)
            app_signals.task_created.emit(task_id)

        self.input_field.clear()
        self.hide()

    def apply_theme(self, theme_name: str) -> None:
        """Dynamically style the quick bar popup for Light or Dark theme."""
        self.is_dark = (theme_name.lower() == "dark")

        # Color tokens
        card_bg = "#18181B" if self.is_dark else "#FFFFFF"
        card_border = "#27272A" if self.is_dark else "#E4E4E7"
        text_primary = "#F4F4F5" if self.is_dark else "#18181B"
        text_secondary = "#A1A1AA" if self.is_dark else "#71717A"
        input_bg = "#27272A" if self.is_dark else "#F4F4F5"
        input_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        input_focus = "#FAFAFA" if self.is_dark else "#18181B"
        btn_action_bg = "#FAFAFA" if self.is_dark else "#18181B"
        btn_action_text = "#18181B" if self.is_dark else "#FFFFFF"
        btn_action_hover = "#E4E4E7" if self.is_dark else "#27272A"
        dropdown_bg = "#27272A" if self.is_dark else "#F4F4F5"
        dropdown_hover = "#3F3F46" if self.is_dark else "#E4E4E7"

        # 1. Outer Card & Shadow
        self.card.setStyleSheet(f"""
            QFrame#quickBarCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 16px;
            }}
        """)
        self._shadow.setColor(QColor(0, 0, 0, 70 if self.is_dark else 35))

        # 2. Header
        self.mode_badge.setStyleSheet(f"color: {text_primary}; font-family: {FONT_SANS};")
        self.hint_label.setStyleSheet(f"color: {text_secondary}; font-family: {FONT_SANS};")
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {text_secondary};
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

        # 3. Input LineEdit
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
            }}
            QLineEdit:focus {{
                background-color: {card_bg};
                border: 1.5px solid {input_focus};
            }}
        """)

        # 4. Project ComboBox
        self.project_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {dropdown_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 10px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 500;
            }}
            QComboBox:hover {{
                background-color: {dropdown_hover};
                border-color: {input_focus};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 14px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {card_bg};
                color: {text_primary};
                border: 1px solid {card_border};
                border-radius: 8px;
                selection-background-color: {dropdown_hover};
                selection-color: {text_primary};
                padding: 4px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
        """)

        # 5. Submit Action Button
        self.submit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_action_bg};
                color: {btn_action_text};
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_action_hover};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Dismiss on Escape key press."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)
