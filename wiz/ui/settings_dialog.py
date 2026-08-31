"""Settings and preferences dialog for WizDesk."""

from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QInputDialog,
)

from wiz.core.config import config
from wiz.storage.models import StorageRepository


class SettingsDialog(QDialog):
    """Configuration dialog for Obsidian vault path, intervals, and project keywords."""

    def __init__(self, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.repo = repository or StorageRepository()

        self.setWindowTitle("WizDesk - Settings and Preferences")
        self.setMinimumSize(520, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #16161D;
                color: #F7F3EA;
                border: 1px solid #2E2E3C;
                border-radius: 10px;
            }
            QLabel {
                color: #F7F3EA;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit, QSpinBox {
                background-color: #21212B;
                color: #FFFFFF;
                border: 1px solid #363647;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QCheckBox {
                color: #F7F3EA;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                spacing: 8px;
            }
            QPushButton {
                background-color: #2D2D3B;
                color: #F7F3EA;
                border: 1px solid #3E3E50;
                border-radius: 6px;
                padding: 6px 14px;
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
            QTableWidget {
                background-color: #1C1C26;
                color: #F7F3EA;
                border: 1px solid #2B2B38;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #20202B;
                color: #A0A0B0;
                border: none;
                padding: 4px;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        title = QLabel("WizDesk Settings")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        layout.addWidget(title)

        # Section 1: Obsidian Vault Configuration
        obs_header = QLabel("Obsidian Vault Integration:")
        obs_header.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        layout.addWidget(obs_header)

        vault_layout = QHBoxLayout()
        self.vault_path_input = QLineEdit()
        self.vault_path_input.setPlaceholderText("Path to Obsidian Vault root folder...")
        self.vault_path_input.setText(config.get("obsidian_vault_path", ""))
        vault_layout.addWidget(self.vault_path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_vault)
        vault_layout.addWidget(browse_btn)
        layout.addLayout(vault_layout)

        # Section 2: General Preferences
        pref_layout = QHBoxLayout()

        self.float_anim_check = QCheckBox("Enable floating bob animation")
        self.float_anim_check.setChecked(config.get("enable_floating_animation", True))
        pref_layout.addWidget(self.float_anim_check)

        layout.addLayout(pref_layout)

        # Section 3: Project Keyword Mappings
        proj_header = QLabel("Project Auto-Tagging Keywords:")
        proj_header.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        layout.addWidget(proj_header)

        self.proj_table = QTableWidget()
        self.proj_table.setColumnCount(2)
        self.proj_table.setHorizontalHeaderLabels(["Project Name", "Matching Keywords (comma-separated)"])
        self.proj_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.proj_table)

        proj_btn_layout = QHBoxLayout()
        add_proj_btn = QPushButton("Add Project")
        add_proj_btn.clicked.connect(self._on_add_project)
        proj_btn_layout.addWidget(add_proj_btn)

        del_proj_btn = QPushButton("Remove Selected")
        del_proj_btn.clicked.connect(self._on_remove_project)
        proj_btn_layout.addWidget(del_proj_btn)
        layout.addLayout(proj_btn_layout)

        # Bottom Buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(save_btn)

        layout.addLayout(bottom_layout)

        self._load_projects()

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
        config.set("enable_floating_animation", self.float_anim_check.isChecked())
        config.save()
        self.accept()
