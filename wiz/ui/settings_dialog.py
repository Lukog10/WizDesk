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
from wiz.storage.models import StorageRepository
from wiz.ui.icons import get_app_icon, get_app_pixmap

FONT_SANS = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'SF Mono', monospace"


class SettingsCheckbox(QWidget):
    """Custom rounded-square checkbox widget matching WizDesk design language."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, size: int = 18, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checked = checked
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        if self._checked != value:
            self._checked = value
            self.update()
            self.toggled.emit(self._checked)

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
            # Filled dark rounded square with crisp white checkmark
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#18181B"))
            painter.drawRoundedRect(rect, radius, radius)

            # Draw white checkmark
            scale = self._size / 18.0
            pen = QPen(QColor("#FFFFFF"), 1.8 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            p1 = QPoint(int(margin + 4.0 * scale), int(margin + 9.0 * scale))
            p2 = QPoint(int(margin + 7.5 * scale), int(margin + 12.5 * scale))
            p3 = QPoint(int(margin + 13.5 * scale), int(margin + 5.5 * scale))
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)
        else:
            # Neutral outline with soft white fill
            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(QPen(QColor("#D4D4D8"), 1.5))
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()


class SettingsDialog(QDialog):
    """Configuration dialog for Obsidian vault path, intervals, and project keywords."""

    def __init__(self, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.repo = repository or StorageRepository()
        self._drag_pos: Optional[QPoint] = None

        # Window Properties
        self.setWindowTitle("WizDesk - Settings")
        self.setWindowIcon(get_app_icon("wiz-idle.svg"))
        self.setMinimumSize(520, 580)
        self.resize(560, 620)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        # Main Outer Container Layout
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(12, 12, 12, 12)
        self.outer_layout.setSpacing(0)

        # Outer rounded card frame (#E6E6EA)
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
        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setBlurRadius(28)
        self._shadow_effect.setColor(QColor(0, 0, 0, 35))
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

        brand_lbl = QLabel("  WizDesk")
        brand_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        brand_lbl.setStyleSheet("color: #71717A;")
        top_bar.addWidget(brand_lbl)
        top_bar.addStretch()

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: #52525B;
                border: none;
                font-family: {FONT_MONO};
                font-size: 13px;
                font-weight: bold;
                border-radius: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.08);
                color: #18181B;
            }}
        """

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(22, 22)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(self.showMinimized)
        controls_layout.addWidget(self.min_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #52525B;
                border: none;
                font-family: {FONT_MONO};
                font-size: 11px;
                font-weight: bold;
                border-radius: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.12);
                color: #EF4444;
            }}
        """)
        self.close_btn.clicked.connect(self.reject)
        controls_layout.addWidget(self.close_btn)

        top_bar.addLayout(controls_layout)
        self.frame_layout.addLayout(top_bar)

        # Elevated White Inner Card (#FFFFFF)
        self.card = QFrame()
        self.card.setObjectName("innerCard")
        self.card.setStyleSheet(f"""
            QFrame#innerCard {{
                background-color: #FFFFFF;
                border: 1px solid #ECECEF;
                border-radius: 18px;
            }}
            QLabel {{
                font-family: {FONT_SANS};
                color: #18181B;
            }}
            QLineEdit, QSpinBox {{
                background-color: #F4F4F5;
                color: #18181B;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                padding: 6px 12px;
                font-family: {FONT_SANS};
                font-size: 12px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                background-color: #FFFFFF;
                border: 1.5px solid #18181B;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                border: none;
                background: transparent;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: rgba(0, 0, 0, 0.06);
                border-radius: 3px;
            }}
            QTableWidget {{
                background-color: #FFFFFF;
                color: #18181B;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                gridline-color: #F4F4F5;
                font-family: {FONT_SANS};
                font-size: 12px;
                selection-background-color: #F4F4F5;
                selection-color: #18181B;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
            }}
            QHeaderView::section {{
                background-color: #F4F4F5;
                color: #71717A;
                border: none;
                border-bottom: 1px solid #E4E4E7;
                padding: 6px 10px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(14)

        # Header Title
        title_lbl = QLabel("Settings")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        card_layout.addWidget(title_lbl)

        # ----------------------------------------------------
        # Section 1: Obsidian Vault Configuration
        # ----------------------------------------------------
        obs_box = QVBoxLayout()
        obs_box.setSpacing(4)

        obs_title = QLabel("Obsidian Vault Integration")
        obs_title.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #18181B;")
        obs_box.addWidget(obs_title)

        obs_desc = QLabel("Select your local Obsidian Vault folder to automatically sync your daily Markdown logs.")
        obs_desc.setStyleSheet("font-size: 11px; color: #71717A;")
        obs_box.addWidget(obs_desc)

        vault_input_layout = QHBoxLayout()
        vault_input_layout.setSpacing(8)

        self.vault_path_input = QLineEdit()
        self.vault_path_input.setPlaceholderText("Path to Obsidian Vault root folder...")
        self.vault_path_input.setText(config.get("obsidian_vault_path", ""))
        vault_input_layout.addWidget(self.vault_path_input, stretch=1)

        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F4F4F5;
                color: #18181B;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                padding: 6px 14px;
                font-family: {FONT_SANS};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #E4E4E7;
                border-color: #D4D4D8;
            }}
        """)
        browse_btn.clicked.connect(self._on_browse_vault)
        vault_input_layout.addWidget(browse_btn)

        obs_box.addLayout(vault_input_layout)
        card_layout.addLayout(obs_box)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setStyleSheet("background-color: #F4F4F5; max-height: 1px; border: none;")
        card_layout.addWidget(div1)

        # ----------------------------------------------------
        # Section 2: General & Tracking Preferences
        # ----------------------------------------------------
        pref_box = QVBoxLayout()
        pref_box.setSpacing(8)

        pref_title = QLabel("General & Tracking Preferences")
        pref_title.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #18181B;")
        pref_box.addWidget(pref_title)

        pref_row = QHBoxLayout()
        pref_row.setSpacing(10)

        self.float_anim_check = SettingsCheckbox(checked=config.get("enable_floating_animation", True), size=18, parent=self.card)
        pref_row.addWidget(self.float_anim_check)

        anim_lbl = QLabel("Enable floating bob animation")
        anim_lbl.setStyleSheet("font-size: 12.5px; color: #18181B; font-weight: 500;")
        anim_lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        anim_lbl.mousePressEvent = lambda e: self.float_anim_check.setChecked(not self.float_anim_check.isChecked())
        pref_row.addWidget(anim_lbl)

        pref_row.addStretch()

        interval_lbl = QLabel("Auto-tracking interval:")
        interval_lbl.setStyleSheet("font-size: 12px; color: #52525B; font-weight: 500;")
        pref_row.addWidget(interval_lbl)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        curr_interval_min = max(1, config.get("tracking_interval_seconds", 300) // 60)
        self.interval_spin.setValue(curr_interval_min)
        self.interval_spin.setSuffix(" min")
        self.interval_spin.setFixedWidth(90)
        pref_row.addWidget(self.interval_spin)

        pref_box.addLayout(pref_row)
        card_layout.addLayout(pref_box)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("background-color: #F4F4F5; max-height: 1px; border: none;")
        card_layout.addWidget(div2)

        # ----------------------------------------------------
        # Section 3: Project Auto-Tagging Keywords
        # ----------------------------------------------------
        proj_box = QVBoxLayout()
        proj_box.setSpacing(6)

        proj_title = QLabel("Project Auto-Tagging Keywords")
        proj_title.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #18181B;")
        proj_box.addWidget(proj_title)

        proj_desc = QLabel("Active windows matching these keywords are automatically categorized into project sections.")
        proj_desc.setStyleSheet("font-size: 11px; color: #71717A;")
        proj_box.addWidget(proj_desc)

        self.proj_table = QTableWidget()
        self.proj_table.setColumnCount(2)
        self.proj_table.setHorizontalHeaderLabels(["Project Name", "Matching Keywords (comma-separated)"])
        self.proj_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proj_table.verticalHeader().setVisible(False)
        self.proj_table.setFixedHeight(120)
        proj_box.addWidget(self.proj_table)

        proj_btn_layout = QHBoxLayout()
        proj_btn_layout.setSpacing(8)

        add_proj_btn = QPushButton("+ Add Project")
        add_proj_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_proj_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F4F4F5;
                color: #18181B;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                padding: 5px 12px;
                font-family: {FONT_SANS};
                font-size: 11.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #E4E4E7;
                border-color: #D4D4D8;
            }}
        """)
        add_proj_btn.clicked.connect(self._on_add_project)
        proj_btn_layout.addWidget(add_proj_btn)

        del_proj_btn = QPushButton("Remove Selected")
        del_proj_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_proj_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEF2F2;
                color: #EF4444;
                border: 1px solid #FEE2E2;
                border-radius: 8px;
                padding: 5px 12px;
                font-family: {FONT_SANS};
                font-size: 11.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #FEE2E2;
                color: #DC2626;
            }}
        """)
        del_proj_btn.clicked.connect(self._on_remove_project)
        proj_btn_layout.addWidget(del_proj_btn)
        proj_btn_layout.addStretch()

        proj_box.addLayout(proj_btn_layout)
        card_layout.addLayout(proj_box)

        # Divider
        div3 = QFrame()
        div3.setFrameShape(QFrame.Shape.HLine)
        div3.setStyleSheet("background-color: #F4F4F5; max-height: 1px; border: none;")
        card_layout.addWidget(div3)

        # ----------------------------------------------------
        # Bottom Buttons
        # ----------------------------------------------------
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F4F4F5;
                color: #52525B;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                padding: 7px 18px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #E4E4E7;
                color: #18181B;
                border-color: #D4D4D8;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #18181B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 20px;
                font-family: {FONT_SANS};
                font-size: 12.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #27272A;
            }}
        """)
        save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(save_btn)

        card_layout.addLayout(bottom_layout)

        self.frame_layout.addWidget(self.card)

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
        """Load projects from database into table."""
        projects = self.repo.get_all_projects()
        self.proj_table.setRowCount(len(projects))
        for row, p in enumerate(projects):
            name_item = QTableWidgetItem(p.name)
            kw_item = QTableWidgetItem(", ".join(p.keywords))
            self.proj_table.setItem(row, 0, name_item)
            self.proj_table.setItem(row, 1, kw_item)

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
        config.set("tracking_interval_seconds", self.interval_spin.value() * 60)
        config.save()
        self.accept()
