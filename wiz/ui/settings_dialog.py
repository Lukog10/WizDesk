"""Settings and preferences dialog for WizDesk with elevated card and frameless design."""

from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QColor, QCursor, QPainter, QPen, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QGraphicsDropShadowEffect,
    QInputDialog,
    QWidget,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.storage.models import StorageRepository
from wiz.ui.icons import get_app_icon, get_app_pixmap

FONT_SANS = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'SF Mono', monospace"


class SettingsCheckbox(QWidget):
    """Custom rounded-square checkbox widget matching WizDesk design language and supporting dark mode."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, size: int = 18, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self._checked = checked
        self._size = size
        self.is_dark = is_dark
        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

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

        margin = 1.5
        s = float(self._size) - (margin * 2)
        rect = QRectF(margin, margin, s, s)
        radius = 4.0

        if self._checked:
            # Filled rounded square with checkmark
            bg_color = QColor("#FAFAFA") if self.is_dark else QColor("#18181B")
            check_color = QColor("#18181B") if self.is_dark else QColor("#FFFFFF")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(rect, radius, radius)

            # Draw checkmark
            scale = self._size / 18.0
            pen = QPen(check_color, 1.8 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            p1 = QPoint(int(margin + 4.0 * scale), int(margin + 9.0 * scale))
            p2 = QPoint(int(margin + 7.5 * scale), int(margin + 12.5 * scale))
            p3 = QPoint(int(margin + 13.5 * scale), int(margin + 5.5 * scale))
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)
        else:
            # Neutral outline with background fill
            border_color = QColor("#52525B") if self.is_dark else QColor("#D4D4D8")
            bg_color = QColor("#27272A") if self.is_dark else QColor("#FFFFFF")

            painter.setBrush(bg_color)
            painter.setPen(QPen(border_color, 1.5))
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()


class SettingsDialog(QDialog):
    """Configuration dialog for Obsidian vault path, intervals, theme, and project keywords."""

    def __init__(self, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.repo = repository or StorageRepository()
        self._drag_pos: Optional[QPoint] = None
        self.is_dark = (config.theme == "dark")

        # Window Properties
        self.setWindowTitle("WizDesk - Settings")
        self.setWindowIcon(get_app_icon("wiz-idle.svg"))
        self.setMinimumSize(520, 600)
        self.resize(560, 650)
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

        self.brand_lbl = QLabel("  WizDesk")
        self.brand_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        top_bar.addWidget(self.brand_lbl)
        top_bar.addStretch()

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(22, 22)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.clicked.connect(self.showMinimized)
        controls_layout.addWidget(self.min_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.reject)
        controls_layout.addWidget(self.close_btn)

        top_bar.addLayout(controls_layout)
        self.frame_layout.addLayout(top_bar)

        # Inner Card
        self.card = QFrame()
        self.card.setObjectName("innerCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 18, 20, 18)
        self.card_layout.setSpacing(14)

        # Header Title
        self.title_lbl = QLabel("Settings")
        self.title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.card_layout.addWidget(self.title_lbl)

        # ----------------------------------------------------
        # Section 1: Obsidian Vault Configuration
        # ----------------------------------------------------
        obs_box = QVBoxLayout()
        obs_box.setSpacing(4)

        self.obs_title = QLabel("Obsidian Vault Integration")
        self.obs_title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        obs_box.addWidget(self.obs_title)

        self.obs_desc = QLabel("Select your local Obsidian Vault folder to automatically sync your daily Markdown logs.")
        self.obs_desc.setFont(QFont("Segoe UI", 9))
        obs_box.addWidget(self.obs_desc)

        vault_input_layout = QHBoxLayout()
        vault_input_layout.setSpacing(8)

        self.vault_path_input = QLineEdit()
        self.vault_path_input.setPlaceholderText("Path to Obsidian Vault root folder...")
        self.vault_path_input.setText(config.get("obsidian_vault_path", ""))
        vault_input_layout.addWidget(self.vault_path_input, stretch=1)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.browse_btn.clicked.connect(self._on_browse_vault)
        vault_input_layout.addWidget(self.browse_btn)

        obs_box.addLayout(vault_input_layout)
        self.card_layout.addLayout(obs_box)

        # Divider 1
        self.div1 = QFrame()
        self.div1.setFrameShape(QFrame.Shape.HLine)
        self.card_layout.addWidget(self.div1)

        # ----------------------------------------------------
        # Section 2: General & Tracking Preferences
        # ----------------------------------------------------
        pref_box = QVBoxLayout()
        pref_box.setSpacing(8)

        self.pref_title = QLabel("General & Tracking Preferences")
        self.pref_title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        pref_box.addWidget(self.pref_title)

        # Preference Row 1: Floating bob animation & Dark Mode
        pref_row_1 = QHBoxLayout()
        pref_row_1.setSpacing(10)

        self.float_anim_check = SettingsCheckbox(checked=config.get("enable_floating_animation", True), size=18, parent=self.card, is_dark=self.is_dark)
        pref_row_1.addWidget(self.float_anim_check)

        self.anim_lbl = QLabel("Enable floating bob animation")
        self.anim_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.anim_lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.anim_lbl.mousePressEvent = lambda e: self.float_anim_check.setChecked(not self.float_anim_check.isChecked())
        pref_row_1.addWidget(self.anim_lbl)

        pref_row_1.addStretch()

        self.dark_mode_check = SettingsCheckbox(checked=(config.theme == "dark"), size=18, parent=self.card, is_dark=self.is_dark)
        self.dark_mode_check.toggled.connect(self._on_dark_mode_toggled)
        pref_row_1.addWidget(self.dark_mode_check)

        self.dark_mode_lbl = QLabel("Dark mode")
        self.dark_mode_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.dark_mode_lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dark_mode_lbl.mousePressEvent = lambda e: self.dark_mode_check.setChecked(not self.dark_mode_check.isChecked())
        pref_row_1.addWidget(self.dark_mode_lbl)

        pref_box.addLayout(pref_row_1)

        # Preference Row 2: Auto-tracking interval
        pref_row_2 = QHBoxLayout()
        pref_row_2.setSpacing(10)

        self.interval_lbl = QLabel("Auto-tracking interval:")
        self.interval_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        pref_row_2.addWidget(self.interval_lbl)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        curr_interval_min = max(1, config.get("tracking_interval_seconds", 300) // 60)
        self.interval_spin.setValue(curr_interval_min)
        self.interval_spin.setSuffix(" min")
        self.interval_spin.setFixedWidth(90)
        pref_row_2.addWidget(self.interval_spin)
        pref_row_2.addStretch()

        pref_box.addLayout(pref_row_2)
        self.card_layout.addLayout(pref_box)

        # Divider 2
        self.div2 = QFrame()
        self.div2.setFrameShape(QFrame.Shape.HLine)
        self.card_layout.addWidget(self.div2)

        # ----------------------------------------------------
        # Section 3: Project Auto-Tagging Keywords
        # ----------------------------------------------------
        proj_box = QVBoxLayout()
        proj_box.setSpacing(8)

        self.proj_title = QLabel("Project Auto-Tagging Keywords")
        self.proj_title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        proj_box.addWidget(self.proj_title)

        self.proj_desc = QLabel("Active windows matching these keywords are automatically categorized into project sections.")
        self.proj_desc.setFont(QFont("Segoe UI", 9))
        proj_box.addWidget(self.proj_desc)

        self.proj_table = QTableWidget()
        self.proj_table.setColumnCount(2)
        self.proj_table.setHorizontalHeaderLabels(["Project Name", "Matching Keywords (comma-separated)"])
        self.proj_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proj_table.verticalHeader().setVisible(False)
        self.proj_table.verticalHeader().setDefaultSectionSize(32)
        self.proj_table.setFixedHeight(130)
        self.proj_table.itemChanged.connect(self._on_table_item_changed)
        proj_box.addWidget(self.proj_table)

        # Action buttons placed cleanly outside and below the table
        proj_btn_layout = QHBoxLayout()
        proj_btn_layout.setContentsMargins(0, 4, 0, 0)
        proj_btn_layout.setSpacing(8)

        self.add_proj_btn = QPushButton("+ Add Project")
        self.add_proj_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_proj_btn.clicked.connect(self._on_add_project)
        proj_btn_layout.addWidget(self.add_proj_btn)

        self.del_proj_btn = QPushButton("Remove Selected")
        self.del_proj_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.del_proj_btn.clicked.connect(self._on_remove_project)
        proj_btn_layout.addWidget(self.del_proj_btn)
        proj_btn_layout.addStretch()

        proj_box.addLayout(proj_btn_layout)
        self.card_layout.addLayout(proj_box)

        # Divider 3
        self.div3 = QFrame()
        self.div3.setFrameShape(QFrame.Shape.HLine)
        self.card_layout.addWidget(self.div3)

        # ----------------------------------------------------
        # Bottom Action Buttons
        # ----------------------------------------------------
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(self.save_btn)

        self.card_layout.addLayout(bottom_layout)
        self.frame_layout.addWidget(self.card)

        # Connect theme changed broadcast
        app_signals.theme_changed.connect(self.apply_theme)

        # Apply initial theme stylesheet
        self.apply_theme(config.theme)

        # Load projects
        self._load_projects()

    def _on_dark_mode_toggled(self, checked: bool) -> None:
        """Handle dark mode checkbox click in real-time."""
        new_theme = "dark" if checked else "light"
        config.set_theme(new_theme)
        app_signals.theme_changed.emit(new_theme)

    def apply_theme(self, theme_name: str) -> None:
        """Dynamically apply Light or Dark theme styling to the settings dialog."""
        self.is_dark = (theme_name.lower() == "dark")

        # Sync checkbox state without re-triggering signal
        self.dark_mode_check.blockSignals(True)
        self.dark_mode_check.setChecked(self.is_dark)
        self.dark_mode_check.set_dark_mode(self.is_dark)
        self.float_anim_check.set_dark_mode(self.is_dark)
        self.dark_mode_check.blockSignals(False)

        # Color tokens
        outer_bg = "#121214" if self.is_dark else "#E6E6EA"
        outer_border = "#27272A" if self.is_dark else "#D8D8DE"
        inner_bg = "#18181B" if self.is_dark else "#FFFFFF"
        inner_border = "#27272A" if self.is_dark else "#ECECEF"
        text_primary = "#F4F4F5" if self.is_dark else "#18181B"
        text_secondary = "#A1A1AA" if self.is_dark else "#71717A"
        input_bg = "#27272A" if self.is_dark else "#F4F4F5"
        input_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        input_focus = "#FAFAFA" if self.is_dark else "#18181B"
        btn_neutral_bg = "#27272A" if self.is_dark else "#F4F4F5"
        btn_neutral_border = "#3F3F46" if self.is_dark else "#E4E4E7"
        btn_neutral_text = "#F4F4F5" if self.is_dark else "#18181B"
        btn_neutral_hover_bg = "#3F3F46" if self.is_dark else "#E4E4E7"
        btn_danger_bg = "#3B1818" if self.is_dark else "#FEF2F2"
        btn_danger_border = "#5C1D1D" if self.is_dark else "#FEE2E2"
        btn_danger_text = "#F87171" if self.is_dark else "#EF4444"
        btn_danger_hover_bg = "#4C1D1D" if self.is_dark else "#FEE2E2"
        btn_danger_hover_text = "#FCA5A5" if self.is_dark else "#DC2626"
        btn_save_bg = "#FAFAFA" if self.is_dark else "#18181B"
        btn_save_text = "#18181B" if self.is_dark else "#FFFFFF"
        btn_save_hover = "#E4E4E7" if self.is_dark else "#27272A"
        div_color = "#27272A" if self.is_dark else "#F4F4F5"
        table_grid = "#27272A" if self.is_dark else "#F4F4F5"
        table_header_bg = "#27272A" if self.is_dark else "#F4F4F5"
        table_header_border = "#3F3F46" if self.is_dark else "#E4E4E7"

        # 1. Outer Frame & Inner Card
        self.outer_frame.setStyleSheet(f"""
            QFrame#outerFrame {{
                background-color: {outer_bg};
                border: 1px solid {outer_border};
                border-radius: 24px;
            }}
        """)
        self.card.setStyleSheet(f"""
            QFrame#innerCard {{
                background-color: {inner_bg};
                border: 1px solid {inner_border};
                border-radius: 18px;
            }}
        """)

        # 2. Window Controls
        self.brand_lbl.setStyleSheet(f"color: {text_secondary};")
        self.min_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_secondary};
                border: none;
                font-family: {FONT_MONO};
                font-size: 13px;
                font-weight: bold;
                border-radius: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08) if self.is_dark else rgba(0, 0, 0, 0.08);
                color: {text_primary};
            }}
        """)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_secondary};
                border: none;
                font-family: {FONT_MONO};
                font-size: 11px;
                font-weight: bold;
                border-radius: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.15);
                color: #EF4444;
            }}
        """)

        # 3. Typography
        self.title_lbl.setStyleSheet(f"color: {text_primary};")
        self.obs_title.setStyleSheet(f"color: {text_primary};")
        self.obs_desc.setStyleSheet(f"color: {text_secondary};")
        self.pref_title.setStyleSheet(f"color: {text_primary};")
        self.anim_lbl.setStyleSheet(f"color: {text_primary};")
        self.dark_mode_lbl.setStyleSheet(f"color: {text_primary};")
        self.interval_lbl.setStyleSheet(f"color: {text_secondary};")
        self.proj_title.setStyleSheet(f"color: {text_primary};")
        self.proj_desc.setStyleSheet(f"color: {text_secondary};")

        # 4. Input boxes & SpinBox
        input_qss = f"""
            QLineEdit, QSpinBox {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                background-color: {inner_bg};
                border: 1.5px solid {input_focus};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                border: none;
                background: transparent;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: rgba(255, 255, 255, 0.1) if self.is_dark else rgba(0, 0, 0, 0.06);
                border-radius: 3px;
            }}
        """
        self.vault_path_input.setStyleSheet(input_qss)
        self.interval_spin.setStyleSheet(input_qss)

        # 5. Buttons
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_neutral_bg};
                color: {btn_neutral_text};
                border: 1px solid {btn_neutral_border};
                border-radius: 8px;
                padding: 6px 14px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_neutral_hover_bg};
                border-color: {input_focus};
            }}
        """)

        self.add_proj_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_neutral_bg};
                color: {btn_neutral_text};
                border: 1px solid {btn_neutral_border};
                border-radius: 8px;
                padding: 6px 14px;
                font-family: {FONT_SANS};
                font-size: 11.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_neutral_hover_bg};
                border-color: {input_focus};
            }}
        """)

        self.del_proj_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_danger_bg};
                color: {btn_danger_text};
                border: 1px solid {btn_danger_border};
                border-radius: 8px;
                padding: 6px 14px;
                font-family: {FONT_SANS};
                font-size: 11.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_danger_hover_bg};
                color: {btn_danger_hover_text};
            }}
        """)

        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_neutral_bg};
                color: {text_secondary};
                border: 1px solid {btn_neutral_border};
                border-radius: 8px;
                padding: 7px 18px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {btn_neutral_hover_bg};
                color: {text_primary};
                border-color: {input_focus};
            }}
        """)

        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_save_bg};
                color: {btn_save_text};
                border: none;
                border-radius: 8px;
                padding: 7px 20px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_save_hover};
            }}
        """)

        # 6. Dividers
        div_style = f"background-color: {div_color}; max-height: 1px; border: none;"
        self.div1.setStyleSheet(div_style)
        self.div2.setStyleSheet(div_style)
        self.div3.setStyleSheet(div_style)

        # 7. Project Table
        self.proj_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {inner_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 8px;
                gridline-color: {table_grid};
                font-family: {FONT_SANS};
                font-size: 12px;
                selection-background-color: {input_bg};
                selection-color: {text_primary};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget QLineEdit {{
                background-color: {inner_bg};
                color: {text_primary};
                border: 1.5px solid {input_focus};
                border-radius: 4px;
                padding: 2px 6px;
                margin: 1px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: {table_header_bg};
                color: {text_secondary};
                border: none;
                border-bottom: 1px solid {table_header_border};
                padding: 6px 10px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
        """)

        self._load_projects()

    def mousePressEvent(self, event) -> None:
        """Capture drag start position on left click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """Reposition window smoothly when dragged."""
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """Reset drag position on release."""
        self._drag_pos = None
        event.accept()

    def _on_browse_vault(self) -> None:
        """Open directory picker for selecting the Obsidian Vault folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Obsidian Vault Directory")
        if folder:
            self.vault_path_input.setText(folder)

    def _load_projects(self) -> None:
        """Load projects from database into table with clean secondary styling."""
        self.proj_table.blockSignals(True)
        projects = self.repo.get_all_projects()
        self.proj_table.setRowCount(len(projects))

        font_name = QFont("Segoe UI", 9)
        font_name.setWeight(QFont.Weight.Normal)
        font_kw = QFont("JetBrains Mono", 8)

        name_color = QColor("#D4D4D8" if self.is_dark else "#52525B")
        kw_color = QColor("#A1A1AA" if self.is_dark else "#71717A")

        for row, p in enumerate(projects):
            name_item = QTableWidgetItem(p.name)
            name_item.setFont(font_name)
            name_item.setForeground(name_color)

            kw_item = QTableWidgetItem(", ".join(p.keywords))
            kw_item.setFont(font_kw)
            kw_item.setForeground(kw_color)

            self.proj_table.setItem(row, 0, name_item)
            self.proj_table.setItem(row, 1, kw_item)
        self.proj_table.blockSignals(False)

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle inline editing of project names and keywords directly in table."""
        row = item.row()
        name_item = self.proj_table.item(row, 0)
        kw_item = self.proj_table.item(row, 1)
        if name_item and kw_item:
            pname = name_item.text().strip()
            kw_str = kw_item.text().strip()
            if pname:
                keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
                self.repo.create_or_update_project(pname, keywords)

    def _on_add_project(self) -> None:
        """Add a new row to the project keyword table."""
        name, ok1 = QInputDialog.getText(self, "New Project", "Project Name:")
        if not ok1 or not name.strip():
            return
        keywords, ok2 = QInputDialog.getText(self, "Keywords", "Keywords (comma-separated):")
        if not ok2:
            return

        self.repo.create_or_update_project(
            name.strip(),
            [k.strip() for k in keywords.split(",") if k.strip()],
        )
        self._load_projects()

    def _on_remove_project(self) -> None:
        """Remove the selected project from table and database."""
        row = self.proj_table.currentRow()
        if row >= 0:
            name_item = self.proj_table.item(row, 0)
            if name_item:
                proj_name = name_item.text()
                with self.repo.db.cursor() as cur:
                    cur.execute("DELETE FROM projects WHERE name = ?", (proj_name,))
                self._load_projects()

    def _on_save(self) -> None:
        """Persist settings to config."""
        config.set("obsidian_vault_path", self.vault_path_input.text().strip())
        is_anim = self.float_anim_check.isChecked() if callable(self.float_anim_check.isChecked) else self.float_anim_check.isChecked
        config.set("enable_floating_animation", bool(is_anim))
        is_dark = self.dark_mode_check.isChecked() if callable(self.dark_mode_check.isChecked) else self.dark_mode_check.isChecked
        config.set_theme("dark" if is_dark else "light")
        config.set("tracking_interval_seconds", self.interval_spin.value() * 60)
        config.save()
        self.accept()
