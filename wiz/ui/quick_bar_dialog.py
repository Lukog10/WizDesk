"""
Compact, floating quick-bar popups for rapid task and note entry.
Triggered via Left Double-Click (Quick Task Bar) and Left Triple-Click (Quick Note Bar) on the Wiz Mascot.
"""

from datetime import date
from typing import Optional
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QColor, QCursor, QGuiApplication, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QWidget,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.core.state_machine import StateMachine
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import CreateSectionDialog, ProjectIconButton, TagIconButton
from wiz.ui.fonts import FONT_SANS, FONT_MONO, get_font


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
        self.setFixedSize(500, 102)

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

        self.mode_badge = QLabel("Quick Task")
        self.mode_badge.setFont(get_font(9, QFont.Weight.DemiBold))
        hdr_layout.addWidget(self.mode_badge)

        self.hint_label = QLabel("(Hotkeys: Ctrl+Shift+T / Ctrl+Shift+N)")
        self.hint_label.setFont(get_font(8))
        hdr_layout.addWidget(self.hint_label)

        hdr_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setToolTip("Close (Esc)")
        self.close_btn.clicked.connect(self.hide)
        hdr_layout.addWidget(self.close_btn)

        self.card_layout.addLayout(hdr_layout)

        # Input Row: LineEdit + Project Icon Button + Tag Icon Button + Submit Button
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(6)

        self.input_field = QLineEdit()
        self.input_field.returnPressed.connect(self._on_submit)
        input_row.addWidget(self.input_field, stretch=1)

        self.project_btn = ProjectIconButton(is_dark=self.is_dark, parent=self.card)
        self.project_btn.create_project_requested.connect(self._open_create_section_dialog)
        self.project_btn.project_selected.connect(self._on_project_selected)
        self.project_combo = self.project_btn  # backward compatibility alias
        input_row.addWidget(self.project_btn)

        self.tag_btn = TagIconButton(self.repo, is_dark=self.is_dark, parent=self.card)
        self.tag_combo = self.tag_btn  # backward compatibility alias
        input_row.addWidget(self.tag_btn)

        self.submit_btn = QPushButton("Add")
        self.submit_btn.setFont(get_font(11, QFont.Weight.Bold))
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
        self._populate_tags()

    def _populate_projects(self) -> None:
        """Populate project icon button with database projects."""
        projects = self.repo.get_all_projects()
        self.project_btn.set_projects(projects)
        if self._last_selected_project:
            self.project_btn.setCurrentText(self._last_selected_project)

    def _populate_tags(self) -> None:
        """Refresh tag button state."""
        self.tag_btn.update()

    def _on_project_selected(self, proj_name: str) -> None:
        self._last_selected_project = proj_name

    def _open_create_section_dialog(self) -> None:
        dlg = CreateSectionDialog(is_dark=self.is_dark, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_sec = dlg.section_name
            if new_sec:
                self.repo.create_or_update_project(
                    new_sec,
                    dlg.keywords or [new_sec.lower()],
                    color=dlg.selected_color,
                    description=dlg.description,
                )
                self._populate_projects()
                self.project_btn.setCurrentText(new_sec)
                self._last_selected_project = new_sec

    def show_mode(self, mode: str = "task", mascot_rect: Optional[QRect] = None) -> None:
        """Configure mode ('task' or 'note'), reposition near mascot, and focus input."""
        self.mode = mode
        self._populate_projects()
        self.tag_btn.clear_selection()

        if mode == "note":
            self.mode_badge.setText("Quick Work Note")
            self.input_field.setPlaceholderText("+ Log a quick work note... (Press Enter)")
            self.submit_btn.setText("Log Note")
        else:
            self.mode_badge.setText("Quick Task")
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

        proj = self.project_btn.current_project
        if proj in ("None", "+ Create Section...", "Create Section...", ""):
            proj = None

        tag_ids = self.tag_btn.selected_tag_ids or None

        if self.mode == "note":
            note_id = self.repo.create_note(text, project_tag=proj, tag_ids=tag_ids)
            self.state_machine.trigger_notify(duration_ms=3500)
            app_signals.note_created.emit(note_id)
        else:
            today_str = date.today().strftime("%Y-%m-%d")
            task_id = self.repo.create_task(text, project_tag=proj, scheduled_date=today_str, tag_ids=tag_ids)
            self.state_machine.trigger_notify(duration_ms=3500)
            app_signals.task_created.emit(task_id)

        self.input_field.clear()
        self.tag_btn.clear_selection()
        self.hide()

    def apply_theme(self, theme_name: str) -> None:
        """Dynamically style the quick bar popup for Light or Dark theme."""
        self.is_dark = (theme_name.lower() == "dark")

        # Color tokens
        card_bg = "#18181B" if self.is_dark else "#FFFFFF"
        card_border = "#27272A" if self.is_dark else "#E5E5EA"
        text_primary = "#F4F4F5" if self.is_dark else "#18181B"
        text_secondary = "#A1A1AA" if self.is_dark else "#71717A"
        input_bg = "#27272A" if self.is_dark else "#F4F4F6"
        input_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        input_focus = "#C2410C" if self.is_dark else "#BA3F1A"
        btn_action_bg = "#C2410C" if self.is_dark else "#BA3F1A"
        btn_action_text = "#FFFFFF"
        btn_action_hover = "#A3360E" if self.is_dark else "#9E3414"

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
                font-size: 12px;
                word-spacing: 1px;
            }}
            QLineEdit:focus {{
                background-color: {card_bg};
                border: 1.5px solid {input_focus};
            }}
        """)

        # 4. Project and Tag Icon Buttons
        if hasattr(self, "project_btn"):
            self.project_btn.set_theme(self.is_dark)
        if hasattr(self, "tag_btn"):
            self.tag_btn.set_theme(self.is_dark)

        # 5. Submit Action Button
        self.submit_btn.setFont(get_font(11, QFont.Weight.Bold))
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

    def hideEvent(self, event) -> None:
        """Play sound cue when popup is dismissed."""
        try:
            from wiz.core.sound import sound_manager
            sound_manager.play_window_close()
        except Exception:
            pass
        super().hideEvent(event)
