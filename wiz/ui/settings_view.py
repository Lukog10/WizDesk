"""
Embedded Settings View for WizDesk Widescreen Shell.
Provides in-workspace categorized configuration for General preferences,
Global Hotkeys, Project Auto-Tagging Keywords, and Obsidian Vault Integration.
Styled to match the Untitled UI design with clean category tabs and two-column setting rows.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget,
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
    QInputDialog,
    QScrollArea,
    QStackedWidget,
    QSizePolicy,
    QDialog,
    QMessageBox,
)

from wiz.core.config import config
from wiz.core.crypto import CryptoManager, crypto_manager
from wiz.core.signals import app_signals
from wiz.storage.backup import backup_manager
from wiz.storage.models import StorageRepository
from wiz.ui.fonts import FONT_SANS, FONT_DISPLAY, FONT_MONO, get_font
from wiz.ui.checkbox import RoundedCheckbox
from wiz.ui.pill_number_picker import DurationPillSelector, PillSpinBox
from wiz.utils.hotkey import normalize_hotkey_str, format_display_shortcut

# Shared component alias for backwards compatibility and tests
SettingsCheckbox = RoundedCheckbox


class KeyDisplayDialog(QDialog):
    """Untitled UI modal displaying the user's personal private encryption key."""

    def __init__(self, key_str: str, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.key_str = key_str
        self.is_dark = is_dark
        self.setWindowTitle("Personal Private Key")
        self.setFixedSize(580, 270)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Personal Master Recovery Key", self)
        title.setFont(get_font(13, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel(
            "This 256-bit recovery key decrypts your WizDesk database. "
            "Keep it stored securely. You can use it to recover your data on any computer.",
            self,
        )
        subtitle.setFont(get_font(9))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Key display box
        self.key_edit = QLineEdit(self.key_str, self)
        self.key_edit.setReadOnly(True)
        self.key_edit.setFont(QFont(FONT_MONO, 10, QFont.Weight.Bold))
        self.key_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_edit.setFixedHeight(44)
        layout.addWidget(self.key_edit)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.copy_btn = QPushButton("Copy Key", self)
        self.copy_btn.setFont(get_font(10, QFont.Weight.Bold))
        self.copy_btn.setFixedHeight(36)
        self.copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_btn.clicked.connect(self._copy_key)
        btn_layout.addWidget(self.copy_btn)

        self.close_btn = QPushButton("Done", self)
        self.close_btn.setFont(get_font(10, QFont.Weight.Medium))
        self.close_btn.setFixedHeight(36)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)
        self._apply_styling()

    def _copy_key(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.key_str)
        self.copy_btn.setText("Copied to Clipboard!")
        QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copy Key"))

    def _apply_styling(self) -> None:
        bg = "#18181B" if self.is_dark else "#FAF8F5"
        text = "#F4F4F5" if self.is_dark else "#242220"
        subtext = "#A1A1AA" if self.is_dark else "#78716C"
        input_bg = "#27272A" if self.is_dark else "#EDE9E0"
        input_border = "#3F3F46" if self.is_dark else "#D6D0C5"
        accent = "#C2410C" if self.is_dark else "#BA3F1A"
        btn_bg = "#27272A" if self.is_dark else "#EBE6DC"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
            }}
            QLabel {{
                color: {text};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {accent};
                border: 1px solid {input_border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 14px;
            }}
        """)
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #EA580C;
            }}
        """)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {text};
                border: 1px solid {input_border};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {input_border};
            }}
        """)


class SettingsCategoryBar(QFrame):
    """
    Untitled UI style category tab navigation bar.
    Displays a horizontal row of rounded tabs in a contained border strip.
    """

    category_selected = pyqtSignal(str)

    CATEGORIES = [
        ("general", "General"),
        ("hotkeys", "Hotkeys"),
        ("projects", "Projects"),
        ("integrations", "Integrations"),
        ("security", "Security & Backup"),
    ]

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.active_category = "general"
        self.buttons: Dict[str, QPushButton] = {}
        self._init_ui()

    @property
    def current_category(self) -> str:
        return self.active_category

    def _init_ui(self) -> None:
        self.setObjectName("SettingsCategoryBar")
        self.setFixedHeight(38)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)

        for cat_id, cat_label in self.CATEGORIES:
            btn = QPushButton(cat_label, self)
            btn.setFixedHeight(30)
            btn.setFont(get_font(11, QFont.Weight.DemiBold))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, c=cat_id: self._on_btn_clicked(c))
            self.buttons[cat_id] = btn
            layout.addWidget(btn, stretch=1)

        self.apply_theme()

    def _on_btn_clicked(self, cat_id: str) -> None:
        self.set_active_category(cat_id)
        self.category_selected.emit(cat_id)

    def set_active_category(self, cat_id: str) -> None:
        self.active_category = cat_id
        self.apply_theme()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.apply_theme()

    def apply_theme(self) -> None:
        if self.is_dark:
            container_bg = "rgba(255, 255, 255, 0.03)"
            container_border = "rgba(255, 255, 255, 0.12)"
            btn_color = "#A1A1AA"
            btn_hover_bg = "rgba(255, 255, 255, 0.05)"
            btn_hover_color = "#F4F4F6"
            active_bg = "rgba(255, 255, 255, 0.08)"
            active_color = "#FAFAFA"
            active_border = "rgba(255, 255, 255, 0.14)"
        else:
            container_bg = "rgba(0, 0, 0, 0.03)"
            container_border = "rgba(0, 0, 0, 0.10)"
            btn_color = "#57534E"
            btn_hover_bg = "rgba(0, 0, 0, 0.04)"
            btn_hover_color = "#18181B"
            active_bg = "#FFFFFF"
            active_color = "#18181B"
            active_border = "rgba(0, 0, 0, 0.10)"

        self.setStyleSheet(f"""
            QFrame#SettingsCategoryBar {{
                background-color: {container_bg};
                border: 1px solid {container_border};
                border-radius: 8px;
            }}
        """)

        for cid, btn in self.buttons.items():
            is_active = (cid == self.active_category)
            if is_active:
                btn.setFont(get_font(11, QFont.Weight.Bold))
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_bg};
                        color: {active_color};
                        border: 1px solid {active_border};
                        border-radius: 6px;
                        padding: 0 14px;
                        font-family: {FONT_SANS};
                        font-size: 11px;
                        font-weight: 600;
                    }}
                """)
            else:
                btn.setFont(get_font(11, QFont.Weight.DemiBold))
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {btn_color};
                        border: 1px solid transparent;
                        border-radius: 6px;
                        padding: 0 14px;
                        font-family: {FONT_SANS};
                        font-size: 11px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: {btn_hover_bg};
                        color: {btn_hover_color};
                    }}
                """)


class SettingsView(QWidget):
    """
    Embedded settings view placed inside the main workspace stack.
    Categorizes settings into General, Hotkeys, Projects, and Integrations
    using the Untitled UI layout paradigm.
    """

    saved = pyqtSignal()
    projects_changed = pyqtSignal()

    def __init__(
        self,
        repository: Optional[StorageRepository] = None,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.repo = repository or StorageRepository()
        self.is_dark = is_dark
        self.hotkey_inputs: Dict[str, QLineEdit] = {}

        self._init_ui()

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(12)

        # 1. Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.title_lbl = QLabel("Settings", self)
        self.title_lbl.setFont(get_font(15, QFont.Weight.Bold, display=True))
        header_layout.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel("Manage your desktop preferences, keyboard shortcuts, and project workflows.", self)
        self.subtitle_lbl.setFont(get_font(9))
        header_layout.addWidget(self.subtitle_lbl)

        self.main_layout.addLayout(header_layout)

        # 2. Untitled UI Style Category Bar
        self.category_bar = SettingsCategoryBar(is_dark=self.is_dark, parent=self)
        self.category_bar.category_selected.connect(self.switch_to_category)
        self.main_layout.addWidget(self.category_bar)

        # 3. Stack of Categorized Settings Pages
        self.stack = QStackedWidget(self)

        self.page_general = self._build_general_page()
        self.page_hotkeys = self._build_hotkeys_page()
        self.page_projects = self._build_projects_page()
        self.page_integrations = self._build_integrations_page()
        self.page_security = self._build_security_page()

        self.stack.addWidget(self.page_general)       # index 0: general
        self.stack.addWidget(self.page_hotkeys)       # index 1: hotkeys
        self.stack.addWidget(self.page_projects)      # index 2: projects
        self.stack.addWidget(self.page_integrations)  # index 3: integrations
        self.stack.addWidget(self.page_security)      # index 4: security

        self.main_layout.addWidget(self.stack, stretch=1)

        # 4. Universal Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(4, 4, 4, 0)
        bottom_bar.setSpacing(10)

        self.status_pill = QLabel("All settings up to date", self)
        self.status_pill.setFont(get_font(9, QFont.Weight.Medium))
        bottom_bar.addWidget(self.status_pill)

        bottom_bar.addStretch()

        self.save_btn = QPushButton("Save Settings", self)
        self.save_btn.setFont(get_font(11, QFont.Weight.Bold))
        self.save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_btn.setAutoDefault(False)
        self.save_btn.setDefault(False)
        self.save_btn.clicked.connect(self.save_settings)
        bottom_bar.addWidget(self.save_btn)

        self.main_layout.addLayout(bottom_bar)

        # Apply initial theme & load data
        self.apply_theme()
        self.load_settings()

    def _create_card_container(self) -> QFrame:
        """Create an elevated panel card for containing a setting category."""
        card = QFrame(self)
        card.setObjectName("SettingsCard")
        return card

    def _create_setting_row(
        self,
        title: str,
        description: str,
        control_widget: QWidget,
        parent_layout: QVBoxLayout,
        include_divider: bool = True,
    ) -> None:
        """
        Build an Untitled UI two-column setting row:
        Left: Title (bold) + Description (small muted)
        Right: Control widget
        """
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 6, 0, 6)
        row_layout.setSpacing(16)

        # Left Column: Label + Description
        left_box = QVBoxLayout()
        left_box.setSpacing(2)
        left_box.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title, row_widget)
        title_lbl.setFont(get_font(10, QFont.Weight.DemiBold))
        title_lbl.setObjectName("SettingRowTitle")
        left_box.addWidget(title_lbl)

        desc_lbl = QLabel(description, row_widget)
        desc_lbl.setFont(get_font(9))
        desc_lbl.setObjectName("SettingRowDesc")
        desc_lbl.setWordWrap(True)
        left_box.addWidget(desc_lbl)

        row_layout.addLayout(left_box, stretch=1)

        # Right Column: Control Widget
        row_layout.addWidget(control_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        parent_layout.addWidget(row_widget)

        if include_divider:
            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setObjectName("SettingDivider")
            div.setFixedHeight(1)
            parent_layout.addWidget(div)

    # ----------------------------------------------------------------
    # Category Page 1: General Preferences
    # ----------------------------------------------------------------
    def _build_general_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 6, 12, 6)
        layout.setSpacing(10)

        # Section Heading
        self.gen_heading = QLabel("General & Companion Behavior", container)
        self.gen_heading.setFont(get_font(12, QFont.Weight.Bold, display=True))
        layout.addWidget(self.gen_heading)

        self.gen_subheading = QLabel("Configure desktop mascot animations, window tracking behavior, and app startup.", container)
        self.gen_subheading.setFont(get_font(9))
        layout.addWidget(self.gen_subheading)

        # Row 1: Floating bob animation
        self.float_anim_check = SettingsCheckbox(
            checked=config.get("enable_floating_animation", True),
            size=18,
            parent=container,
            is_dark=self.is_dark,
        )
        self._create_setting_row(
            title="Floating Mascot Animation",
            description="Mascot gently bobs and floats on screen with smooth sinusoidal motion.",
            control_widget=self.float_anim_check,
            parent_layout=layout,
        )

        # Row 2: Always on top
        self.always_on_top_check = SettingsCheckbox(
            checked=config.get("always_on_top", True),
            size=18,
            parent=container,
            is_dark=self.is_dark,
        )
        self._create_setting_row(
            title="Always On Top",
            description="Keep the desktop companion floating above full-screen windows and active applications.",
            control_widget=self.always_on_top_check,
            parent_layout=layout,
        )

        # Row 3: Tracking interval (Compact Pill: [ 5 min ])
        self.interval_spin = DurationPillSelector(
            min_minutes=1,
            max_minutes=720,
            default_minutes=max(1, config.get("tracking_interval_seconds", 300) // 60),
            is_dark=self.is_dark,
            parent=container,
        )
        self._create_setting_row(
            title="Activity Tracking Interval",
            description="Frequency of active window polling and automatic session chunk logging.",
            control_widget=self.interval_spin,
            parent_layout=layout,
        )

        # Row 4: Launch on startup
        self.autostart_check = SettingsCheckbox(
            checked=config.get("auto_start_on_login", False),
            size=18,
            parent=container,
            is_dark=self.is_dark,
        )
        self._create_setting_row(
            title="Launch on Windows Startup",
            description="Automatically launch WizDesk in the background when your computer turns on.",
            control_widget=self.autostart_check,
            parent_layout=layout,
        )

        # Row 5: Sound effects
        self.sound_check = SettingsCheckbox(
            checked=config.get("sound_effects", False),
            size=18,
            parent=container,
            is_dark=self.is_dark,
        )
        self._create_setting_row(
            title="Sound Effects & Chimes",
            description="Play a subtle, crisp sound chime upon completing tasks or timers.",
            control_widget=self.sound_check,
            parent_layout=layout,
            include_divider=False,
        )

        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    # ----------------------------------------------------------------
    # Category Page 2: Keyboard Shortcuts (Hotkeys)
    # ----------------------------------------------------------------
    def _build_hotkeys_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 6, 12, 6)
        layout.setSpacing(10)

        # Section Heading with Active status pill
        header_row = QHBoxLayout()
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(2)

        self.hk_heading = QLabel("Global Keyboard Shortcuts", container)
        self.hk_heading.setFont(get_font(12, QFont.Weight.Bold, display=True))
        header_vbox.addWidget(self.hk_heading)

        self.hk_subheading = QLabel(
            "Global hotkeys trigger actions across your operating system even when WizDesk is in the background.",
            container,
        )
        self.hk_subheading.setFont(get_font(9))
        self.hk_subheading.setWordWrap(True)
        header_vbox.addWidget(self.hk_subheading)
        header_row.addLayout(header_vbox, stretch=1)

        self.hk_active_badge = QLabel("Active", container)
        self.hk_active_badge.setFont(get_font(8, QFont.Weight.Bold))
        self.hk_active_badge.setObjectName("ActiveBadge")
        header_row.addWidget(self.hk_active_badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)

        # Hotkey Configuration Fields
        shortcuts_meta = [
            ("hotkey_workspace", "Open Workspace Window", "<ctrl>+<shift>+w", "Opens the main tasks, notes, and activity dashboard."),
            ("hotkey_toggle_mascot", "Show / Hide Desktop Mascot", "<ctrl>+<shift>+m", "Quickly toggles the desktop companion on or off screen."),
            ("hotkey_quick_task", "Quick Add Task Bar", "<ctrl>+<shift>+t", "Summons the lightweight floating bar to capture a task."),
            ("hotkey_quick_note", "Quick Add Note Bar", "<ctrl>+<shift>+n", "Summons the lightweight floating bar to capture a quick note."),
        ]

        for i, (key_name, label_text, default_val, help_text) in enumerate(shortcuts_meta):
            line_edit = QLineEdit(container)
            line_edit.setFixedWidth(150)
            line_edit.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            curr_val = config.get(key_name, default_val)
            line_edit.setText(format_display_shortcut(curr_val))
            line_edit.setPlaceholderText("e.g. Ctrl+Shift+W")
            self.hotkey_inputs[key_name] = line_edit

            self._create_setting_row(
                title=label_text,
                description=help_text,
                control_widget=line_edit,
                parent_layout=layout,
                include_divider=(i < len(shortcuts_meta) - 1),
            )

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 10, 0, 0)
        btn_row.setSpacing(8)

        self.save_hk_btn = QPushButton("Save Shortcuts", container)
        self.save_hk_btn.setFont(get_font(9, QFont.Weight.Bold))
        self.save_hk_btn.setFixedHeight(30)
        self.save_hk_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_hk_btn.clicked.connect(self._on_save_hotkeys)
        btn_row.addWidget(self.save_hk_btn)

        self.reset_hk_btn = QPushButton("Reset to Defaults", container)
        self.reset_hk_btn.setFont(get_font(9))
        self.reset_hk_btn.setFixedHeight(30)
        self.reset_hk_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.reset_hk_btn.clicked.connect(self._on_reset_hotkeys)
        btn_row.addWidget(self.reset_hk_btn)

        btn_row.addStretch(1)

        self.hk_feedback_lbl = QLabel("", container)
        self.hk_feedback_lbl.setFont(get_font(8, QFont.Weight.DemiBold))
        btn_row.addWidget(self.hk_feedback_lbl)

        layout.addLayout(btn_row)
        layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    def _on_save_hotkeys(self) -> None:
        """Validate and persist user-configured hotkeys."""
        try:
            for key_name, input_field in self.hotkey_inputs.items():
                raw_text = input_field.text().strip()
                norm = normalize_hotkey_str(raw_text)
                if norm:
                    config.set(key_name, norm)
                    input_field.setText(format_display_shortcut(norm))

            if "hotkey_workspace" in self.hotkey_inputs:
                config.set("global_hotkey", config.get("hotkey_workspace"))

            config.save()
            app_signals.hotkeys_changed.emit()

            self.hk_feedback_lbl.setText("Shortcuts saved successfully.")
            self.hk_feedback_lbl.setStyleSheet("color: #10B981;")
            QTimer.singleShot(2500, lambda: self.hk_feedback_lbl.setText(""))
        except Exception as e:
            self.hk_feedback_lbl.setText(f"Error: {e}")
            self.hk_feedback_lbl.setStyleSheet("color: #EF4444;")

    def _on_reset_hotkeys(self) -> None:
        """Reset all shortcuts to default combinations."""
        defaults = {
            "hotkey_workspace": "<ctrl>+<shift>+w",
            "hotkey_toggle_mascot": "<ctrl>+<shift>+m",
            "hotkey_quick_task": "<ctrl>+<shift>+t",
            "hotkey_quick_note": "<ctrl>+<shift>+n",
        }
        for k, v in defaults.items():
            config.set(k, v)
            if k in self.hotkey_inputs:
                self.hotkey_inputs[k].setText(format_display_shortcut(v))

        config.set("global_hotkey", defaults["hotkey_workspace"])
        config.save()
        app_signals.hotkeys_changed.emit()

        self.hk_feedback_lbl.setText("Reset to default shortcuts.")
        self.hk_feedback_lbl.setStyleSheet("color: #FF6B3D;")
        QTimer.singleShot(2500, lambda: self.hk_feedback_lbl.setText(""))

    # ----------------------------------------------------------------
    # Category Page 3: Projects & Auto-Tagging
    # ----------------------------------------------------------------
    def _build_projects_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 6, 12, 6)
        layout.setSpacing(10)

        self.proj_heading = QLabel("Project Auto-Tagging Keywords", container)
        self.proj_heading.setFont(get_font(12, QFont.Weight.Bold, display=True))
        layout.addWidget(self.proj_heading)

        self.proj_subheading = QLabel(
            "Active windows matching these keywords are automatically categorized into project sections during tracking.",
            container,
        )
        self.proj_subheading.setFont(get_font(9))
        self.proj_subheading.setWordWrap(True)
        layout.addWidget(self.proj_subheading)

        self.proj_table = QTableWidget(container)
        self.proj_table.setColumnCount(2)
        self.proj_table.setHorizontalHeaderLabels(["Project Name", "Matching Keywords (comma-separated)"])
        self.proj_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proj_table.verticalHeader().setVisible(False)
        self.proj_table.verticalHeader().setDefaultSectionSize(32)
        self.proj_table.setFixedHeight(180)
        self.proj_table.itemChanged.connect(self._on_table_item_changed)
        layout.addWidget(self.proj_table)

        # Action buttons below table
        proj_btn_layout = QHBoxLayout()
        proj_btn_layout.setContentsMargins(0, 4, 0, 0)
        proj_btn_layout.setSpacing(8)

        self.add_proj_btn = QPushButton("+ Add Project", container)
        self.add_proj_btn.setFont(get_font(10, QFont.Weight.Bold))
        self.add_proj_btn.setFixedHeight(30)
        self.add_proj_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_proj_btn.clicked.connect(self._on_add_project)
        proj_btn_layout.addWidget(self.add_proj_btn)

        self.del_proj_btn = QPushButton("Remove Selected", container)
        self.del_proj_btn.setFont(get_font(10, QFont.Weight.DemiBold))
        self.del_proj_btn.setFixedHeight(30)
        self.del_proj_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.del_proj_btn.clicked.connect(self._on_remove_project)
        proj_btn_layout.addWidget(self.del_proj_btn)
        proj_btn_layout.addStretch(1)

        layout.addLayout(proj_btn_layout)
        layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    def _load_projects(self) -> None:
        """Load projects from database into table."""
        self.proj_table.blockSignals(True)
        projects = self.repo.get_all_projects()
        self.proj_table.setRowCount(len(projects))

        font_name = get_font(9)
        font_kw = get_font(8, mono=True)

        name_color = QColor("#D4D4D8" if self.is_dark else "#52525B")
        kw_color = QColor("#A1A1AA" if self.is_dark else "#71717A")

        for row, p in enumerate(projects):
            name_item = QTableWidgetItem(p.name)
            name_item.setData(Qt.ItemDataRole.UserRole, p.name)
            name_item.setFont(font_name)
            name_item.setForeground(name_color)

            kw_item = QTableWidgetItem(", ".join(p.keywords))
            kw_item.setFont(font_kw)
            kw_item.setForeground(kw_color)

            self.proj_table.setItem(row, 0, name_item)
            self.proj_table.setItem(row, 1, kw_item)
        self.proj_table.blockSignals(False)

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle inline editing of project names and keywords."""
        row = item.row()
        name_item = self.proj_table.item(row, 0)
        kw_item = self.proj_table.item(row, 1)
        if name_item and kw_item:
            pname = name_item.text().strip()
            old_name = name_item.data(Qt.ItemDataRole.UserRole)
            kw_str = kw_item.text().strip()
            if pname:
                keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
                if old_name and old_name != pname:
                    self.repo.rename_project(old_name, pname, keywords=keywords)
                    name_item.setData(Qt.ItemDataRole.UserRole, pname)
                else:
                    self.repo.create_or_update_project(pname, keywords)
                self.projects_changed.emit()
                app_signals.projects_changed.emit()

    def _on_add_project(self) -> None:
        """Add a new project row to table and database."""
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
        self.projects_changed.emit()
        app_signals.projects_changed.emit()

    def _on_remove_project(self) -> None:
        """Remove selected project from table and database."""
        row = self.proj_table.currentRow()
        if row >= 0:
            name_item = self.proj_table.item(row, 0)
            if name_item:
                proj_name = name_item.text()
                self.repo.delete_project_by_name(proj_name)
                self._load_projects()
                self.projects_changed.emit()
                app_signals.projects_changed.emit()

    # ----------------------------------------------------------------
    # Category Page 4: Integrations (Obsidian)
    # ----------------------------------------------------------------
    def _build_integrations_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 6, 12, 6)
        layout.setSpacing(10)

        self.obs_heading = QLabel("Obsidian Vault Integration", container)
        self.obs_heading.setFont(get_font(12, QFont.Weight.Bold, display=True))
        layout.addWidget(self.obs_heading)

        self.obs_subheading = QLabel(
            "Connect your local Obsidian Vault folder to automatically sync your daily work logs, completed tasks, and notes.",
            container,
        )
        self.obs_subheading.setFont(get_font(9))
        self.obs_subheading.setWordWrap(True)
        layout.addWidget(self.obs_subheading)

        # Row 1: Vault Folder Path
        vault_ctrl = QWidget()
        vault_ctrl_layout = QHBoxLayout(vault_ctrl)
        vault_ctrl_layout.setContentsMargins(0, 0, 0, 0)
        vault_ctrl_layout.setSpacing(8)

        self.vault_path_input = QLineEdit(vault_ctrl)
        self.vault_path_input.setPlaceholderText("Path to Obsidian Vault root folder...")
        self.vault_path_input.setText(config.get("obsidian_vault_path", ""))
        self.vault_path_input.setFixedWidth(280)
        vault_ctrl_layout.addWidget(self.vault_path_input)

        self.browse_btn = QPushButton("Browse", vault_ctrl)
        self.browse_btn.setFixedHeight(30)
        self.browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.browse_btn.clicked.connect(self._on_browse_vault)
        vault_ctrl_layout.addWidget(self.browse_btn)

        self._create_setting_row(
            title="Obsidian Vault Directory",
            description="Root folder of your local Obsidian vault on disk.",
            control_widget=vault_ctrl,
            parent_layout=layout,
        )

        # Row 2: Logs Subfolder Name
        self.vault_logs_folder_input = QLineEdit(container)
        self.vault_logs_folder_input.setPlaceholderText("e.g. WizDesk Logs")
        self.vault_logs_folder_input.setText(config.get("obsidian_logs_folder", "WizDesk Logs"))
        self.vault_logs_folder_input.setFixedWidth(200)

        self._create_setting_row(
            title="Daily Logs Subfolder",
            description="Folder name inside your vault where daily Markdown tracking logs are stored.",
            control_widget=self.vault_logs_folder_input,
            parent_layout=layout,
        )

        # Row 3: Auto-Sync Status
        self.sync_status_badge = QLabel("Active" if config.get("obsidian_vault_path") else "Not Configured", container)
        self.sync_status_badge.setFont(get_font(8, QFont.Weight.Bold))
        self.sync_status_badge.setObjectName("SyncBadge")

        self._create_setting_row(
            title="Automatic Daily Notes Sync",
            description="Automatically flushes work sessions, completed tasks, and notes to daily files upon application idle or shutdown.",
            control_widget=self.sync_status_badge,
            parent_layout=layout,
            include_divider=False,
        )

        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _on_browse_vault(self) -> None:
        """Open directory picker for selecting the Obsidian Vault folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Obsidian Vault Directory")
        if folder:
            self.vault_path_input.setText(folder)
            self._update_sync_status()

    def _update_sync_status(self) -> None:
        is_set = bool(self.vault_path_input.text().strip())
        self.sync_status_badge.setText("Active" if is_set else "Not Configured")
        self._apply_badge_style(self.sync_status_badge, is_active=is_set)

    # ----------------------------------------------------------------
    # Category Page 5: Security & Database Backup
    # ----------------------------------------------------------------
    def _build_security_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 6, 12, 6)
        layout.setSpacing(10)

        self.sec_heading = QLabel("Database Security & Backups", container)
        self.sec_heading.setFont(get_font(12, QFont.Weight.Bold, display=True))
        layout.addWidget(self.sec_heading)

        self.sec_subheading = QLabel(
            "Protect your tasks and logs with hardware-backed AES-256-GCM encryption at rest, and manage point-in-time database backups.",
            container,
        )
        self.sec_subheading.setFont(get_font(9))
        self.sec_subheading.setWordWrap(True)
        layout.addWidget(self.sec_subheading)

        # Row 1: Encryption Status & Toggle
        enc_ctrl = QWidget()
        enc_layout = QHBoxLayout(enc_ctrl)
        enc_layout.setContentsMargins(0, 0, 0, 0)
        enc_layout.setSpacing(8)

        self.enc_status_badge = QLabel("Not Configured", enc_ctrl)
        self.enc_status_badge.setFont(get_font(8, QFont.Weight.Bold))
        self.enc_status_badge.setObjectName("SecurityBadge")
        enc_layout.addWidget(self.enc_status_badge)

        self.toggle_enc_btn = QPushButton("Enable Encryption", enc_ctrl)
        self.toggle_enc_btn.setFont(get_font(10, QFont.Weight.DemiBold))
        self.toggle_enc_btn.setFixedHeight(30)
        self.toggle_enc_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.toggle_enc_btn.clicked.connect(self._on_toggle_encryption)
        enc_layout.addWidget(self.toggle_enc_btn)

        self._create_setting_row(
            title="Database Encryption (AES-256-GCM)",
            description="Encrypt all tasks, notes, sessions, and logs at rest. Master key is secured by Windows DPAPI for instant zero-prompt login.",
            control_widget=enc_ctrl,
            parent_layout=layout,
        )

        # Row 2: Personal Master Key
        self.view_key_btn = QPushButton("View / Export Key", container)
        self.view_key_btn.setFont(get_font(10, QFont.Weight.DemiBold))
        self.view_key_btn.setFixedHeight(30)
        self.view_key_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.view_key_btn.clicked.connect(self._on_view_private_key)

        self._create_setting_row(
            title="Personal Master Key",
            description="View or copy your 256-bit private key. Store this safely to recover or migrate your database on other machines.",
            control_widget=self.view_key_btn,
            parent_layout=layout,
        )

        # Row 3: Automated Backups Checkbox
        self.auto_backup_check = SettingsCheckbox(
            checked=config.get("auto_backup_enabled", True),
            size=18,
            parent=container,
            is_dark=self.is_dark,
        )
        self._create_setting_row(
            title="Automated Backups",
            description="Create daily rolling snapshot backups of your database automatically on application start.",
            control_widget=self.auto_backup_check,
            parent_layout=layout,
        )

        # Row 4: Retention Count (Compact Pill: [ 5 snapshots ])
        self.backup_retention_spin = PillSpinBox(
            min_val=1,
            max_val=30,
            default_val=int(config.get("max_backups_retained", 5)),
            unit="snapshots",
            is_dark=self.is_dark,
            parent=container,
        )
        self._create_setting_row(
            title="Retention Limit",
            description="Number of automated backup snapshots to keep before pruning older files.",
            control_widget=self.backup_retention_spin,
            parent_layout=layout,
        )

        # Row 5: Backup & Restore Actions
        actions_ctrl = QWidget()
        act_layout = QHBoxLayout(actions_ctrl)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.setSpacing(8)

        self.create_backup_btn = QPushButton("Create Backup Now", actions_ctrl)
        self.create_backup_btn.setFont(get_font(10, QFont.Weight.DemiBold))
        self.create_backup_btn.setFixedHeight(30)
        self.create_backup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.create_backup_btn.clicked.connect(self._on_create_backup_now)
        act_layout.addWidget(self.create_backup_btn)

        self.restore_backup_btn = QPushButton("Restore from File...", actions_ctrl)
        self.restore_backup_btn.setFont(get_font(10, QFont.Weight.DemiBold))
        self.restore_backup_btn.setFixedHeight(30)
        self.restore_backup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.restore_backup_btn.clicked.connect(self._on_restore_backup)
        act_layout.addWidget(self.restore_backup_btn)

        self._create_setting_row(
            title="Database Snapshots",
            description="Generate a new point-in-time backup snapshot or restore from a .bak / .wbak file.",
            control_widget=actions_ctrl,
            parent_layout=layout,
            include_divider=False,
        )

        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _refresh_encryption_ui(self) -> None:
        """Update encryption badge, button text, and key visibility."""
        is_enc = bool(self.repo.db.is_encrypted)
        if is_enc:
            self.enc_status_badge.setText("Active")
            self._apply_badge_style(self.enc_status_badge, is_active=True)
            self.toggle_enc_btn.setText("Disable Encryption")
            self.view_key_btn.setEnabled(True)
        else:
            self.enc_status_badge.setText("Not Configured")
            self._apply_badge_style(self.enc_status_badge, is_active=False)
            self.toggle_enc_btn.setText("Enable Encryption")
            self.view_key_btn.setEnabled(crypto_manager.has_stored_key())

    def _on_toggle_encryption(self) -> None:
        """Toggle AES-256-GCM database encryption at rest."""
        if not self.repo.db.is_encrypted:
            ok, key_str = self.repo.db.enable_encryption()
            if ok:
                self._refresh_encryption_ui()
                self.status_pill.setText("Database encrypted with AES-256-GCM")
                self.status_pill.setStyleSheet(
                    f"color: #10B981; font-weight: 600; font-family: {FONT_SANS}; font-size: 12px;"
                )
                QTimer.singleShot(
                    2500,
                    lambda: self.status_pill.setText("All settings up to date") or self._refresh_status_pill_style(),
                )
                dlg = KeyDisplayDialog(key_str, is_dark=self.is_dark, parent=self)
                dlg.exec()
        else:
            reply = QMessageBox.question(
                self,
                "Disable Encryption",
                "Are you sure you want to decrypt your database?\n\n"
                "The database will be stored as standard plaintext SQLite on disk.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                ok, msg = self.repo.db.disable_encryption()
                if ok:
                    self._refresh_encryption_ui()
                    self.status_pill.setText("Database decrypted to standard format")
                    self.status_pill.setStyleSheet(
                        f"color: #10B981; font-weight: 600; font-family: {FONT_SANS}; font-size: 12px;"
                    )
                    QTimer.singleShot(
                        2500,
                        lambda: self.status_pill.setText("All settings up to date") or self._refresh_status_pill_style(),
                    )

    def _on_view_private_key(self) -> None:
        """Open the personal private key export modal."""
        key = crypto_manager.load_key_dpapi()
        if key:
            key_str = CryptoManager.format_key_for_display(key)
            dlg = KeyDisplayDialog(key_str, is_dark=self.is_dark, parent=self)
            dlg.exec()
        else:
            QMessageBox.information(
                self,
                "Private Key",
                "No encryption key found. Encryption is currently disabled.",
            )

    def _on_create_backup_now(self) -> None:
        """Trigger an immediate point-in-time snapshot backup."""
        try:
            path = backup_manager.create_backup(self.repo.db, tag="manual")
            self.status_pill.setText(f"Snapshot created: {path.name}")
            self.status_pill.setStyleSheet(
                f"color: #10B981; font-weight: 600; font-family: {FONT_SANS}; font-size: 12px;"
            )
            QTimer.singleShot(
                2500,
                lambda: self.status_pill.setText("All settings up to date") or self._refresh_status_pill_style(),
            )
        except Exception as e:
            QMessageBox.warning(self, "Backup Error", f"Failed to create backup: {e}")

    def _on_restore_backup(self) -> None:
        """Prompt user for backup file and restore database state."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File",
            str(backup_manager.backup_dir),
            "Backup Files (*.bak *.wbak);;All Files (*)",
        )
        if not file_path:
            return

        chosen = Path(file_path)
        reply = QMessageBox.question(
            self,
            "Restore Database",
            f"Restore database from '{chosen.name}'?\n\n"
            "Your current tasks and notes will be replaced. "
            "A pre-restore safety snapshot will be taken automatically before restoring.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. Take safety snapshot
                backup_manager.create_backup(self.repo.db, tag="pre-restore")
                # 2. Restore
                backup_manager.restore_backup(chosen, self.repo.db)
                self._refresh_encryption_ui()
                self._load_projects()
                self.projects_changed.emit()
                app_signals.tasks_changed.emit()
                self.status_pill.setText("Database restored successfully!")
                self.status_pill.setStyleSheet(
                    f"color: #10B981; font-weight: 600; font-family: {FONT_SANS}; font-size: 12px;"
                )
                QTimer.singleShot(
                    2500,
                    lambda: self.status_pill.setText("All settings up to date") or self._refresh_status_pill_style(),
                )
            except Exception as e:
                QMessageBox.critical(self, "Restore Failed", f"Failed to restore backup: {e}")

    # ----------------------------------------------------------------
    # Navigation & Lifecycle
    # ----------------------------------------------------------------
    def switch_to_category(self, cat_id: str) -> None:
        """Switch category page in the stack widget."""
        cat_map = {
            "general": 0,
            "hotkeys": 1,
            "projects": 2,
            "integrations": 3,
            "security": 4,
        }
        idx = cat_map.get(cat_id.lower(), 0)
        self.stack.setCurrentIndex(idx)
        self.category_bar.set_active_category(cat_id.lower())

    def load_settings(self) -> None:
        """Reload configuration and projects into UI controls."""
        self.vault_path_input.setText(config.get("obsidian_vault_path", ""))
        self.vault_logs_folder_input.setText(config.get("obsidian_logs_folder", "WizDesk Logs"))
        self.float_anim_check.setChecked(config.get("enable_floating_animation", True))
        self.always_on_top_check.setChecked(config.get("always_on_top", True))
        self.autostart_check.setChecked(config.get("auto_start_on_login", False))
        self.sound_check.setChecked(config.get("sound_effects", False))

        # Security & Backups
        self.auto_backup_check.setChecked(config.get("auto_backup_enabled", True))
        self.backup_retention_spin.setValue(int(config.get("max_backups_retained", 5)))
        self._refresh_encryption_ui()

        curr_interval_min = max(1, config.get("tracking_interval_seconds", 300) // 60)
        self.interval_spin.setValue(curr_interval_min)

        for key_name, input_field in self.hotkey_inputs.items():
            val = config.get(key_name, "")
            input_field.setText(format_display_shortcut(val))

        self._load_projects()
        self._update_sync_status()

    def save_settings(self) -> None:
        """Persist settings to config and database with visual feedback."""
        # General
        is_anim = self.float_anim_check.isChecked() if callable(self.float_anim_check.isChecked) else self.float_anim_check.isChecked
        config.set("enable_floating_animation", bool(is_anim))
        config.set("always_on_top", bool(self.always_on_top_check.isChecked()))
        config.set("tracking_interval_seconds", self.interval_spin.value() * 60)
        config.set("auto_start_on_login", bool(self.autostart_check.isChecked()))
        config.set("sound_effects", bool(self.sound_check.isChecked()))

        # Integrations
        config.set("obsidian_vault_path", self.vault_path_input.text().strip())
        config.set("obsidian_logs_folder", self.vault_logs_folder_input.text().strip() or "WizDesk Logs")

        # Security & Backups
        config.set("auto_backup_enabled", bool(self.auto_backup_check.isChecked()))
        config.set("max_backups_retained", int(self.backup_retention_spin.value()))

        # Hotkeys
        for key_name, input_field in self.hotkey_inputs.items():
            raw_text = input_field.text().strip()
            norm = normalize_hotkey_str(raw_text)
            if norm:
                config.set(key_name, norm)
                input_field.setText(format_display_shortcut(norm))

        if "hotkey_workspace" in self.hotkey_inputs:
            config.set("global_hotkey", config.get("hotkey_workspace"))

        config.save()
        app_signals.hotkeys_changed.emit()
        self._update_sync_status()

        # Update feedback status
        self.status_pill.setText("Settings saved successfully")
        self.status_pill.setStyleSheet(
            f"color: #10B981; font-weight: 600; font-family: {FONT_SANS}; font-size: 12px;"
        )
        QTimer.singleShot(
            2500,
            lambda: self.status_pill.setText("All settings up to date") or self._refresh_status_pill_style(),
        )

        self.saved.emit()

    def _refresh_status_pill_style(self) -> None:
        color = "#71717A" if self.is_dark else "#94A3B8"
        self.status_pill.setStyleSheet(f"color: {color}; font-family: {FONT_SANS}; font-size: 12px;")

    def _apply_badge_style(self, badge: QLabel, is_active: bool = True) -> None:
        if is_active:
            bg = "#1B382B" if self.is_dark else "#ECFDF5"
            border = "#235B43" if self.is_dark else "#A7F3D0"
            color = "#34D399" if self.is_dark else "#059669"
        else:
            bg = "#27272A" if self.is_dark else "#F3EFE9"
            border = "#3F3F46" if self.is_dark else "#D6D0C5"
            color = "#71717A" if self.is_dark else "#78716C"

        badge.setStyleSheet(f"""
            background-color: {bg};
            color: {color};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 2px 8px;
            font-family: {FONT_SANS};
            font-size: 10px;
            font-weight: 600;
        """)

    def set_theme(self, is_dark: bool) -> None:
        """Apply dark or light theme with WizDesk brand colors."""
        self.is_dark = is_dark
        self.float_anim_check.set_dark_mode(is_dark)
        self.always_on_top_check.set_dark_mode(is_dark)
        self.autostart_check.set_dark_mode(is_dark)
        self.sound_check.set_dark_mode(is_dark)
        self.auto_backup_check.set_dark_mode(is_dark)
        self.interval_spin.set_theme(is_dark)
        self.backup_retention_spin.set_theme(is_dark)
        self.category_bar.set_theme(is_dark)
        self.apply_theme()

    def apply_theme(self) -> None:
        """Apply complete theme styling."""
        is_dark = self.is_dark

        inner_bg = "#18181B" if is_dark else "#FAF8F5"
        text_primary = "#F4F4F5" if is_dark else "#242220"
        text_secondary = "#A1A1AA" if is_dark else "#78716C"
        input_bg = "#27272A" if is_dark else "#EDE9E0"
        input_border = "#3F3F46" if is_dark else "#D6D0C5"
        input_focus = "#C2410C" if is_dark else "#BA3F1A"

        save_bg = "#C2410C" if is_dark else "#BA3F1A"
        save_hover = "#A3360E" if is_dark else "#9E3414"
        save_pressed = "#872A09" if is_dark else "#7D280E"

        btn_neutral_bg = "#27272A" if is_dark else "#EBE6DC"
        btn_neutral_border = "#3F3F46" if is_dark else "#D6D0C5"
        btn_neutral_text = "#F4F4F5" if is_dark else "#242220"
        btn_neutral_hover_bg = "#3F3F46" if is_dark else "#DDD7CC"

        btn_danger_bg = "#3B1818" if is_dark else "#FEF2F2"
        btn_danger_border = "#5C1D1D" if is_dark else "#FEE2E2"
        btn_danger_text = "#F87171" if is_dark else "#EF4444"
        btn_danger_hover_bg = "#4C1D1D" if is_dark else "#FEE2E2"

        div_color = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.06)"
        table_grid = "#27272A" if is_dark else "#EFECE5"
        table_header_bg = "#27272A" if is_dark else "#EBE6DC"
        table_header_border = "#3F3F46" if is_dark else "#D6D0C5"

        # Headers
        self.title_lbl.setStyleSheet(f"color: {text_primary};")
        self.subtitle_lbl.setStyleSheet(f"color: {text_secondary};")

        self.gen_heading.setStyleSheet(f"color: {text_primary};")
        self.gen_subheading.setStyleSheet(f"color: {text_secondary};")
        self.hk_heading.setStyleSheet(f"color: {text_primary};")
        self.hk_subheading.setStyleSheet(f"color: {text_secondary};")
        self.proj_heading.setStyleSheet(f"color: {text_primary};")
        self.proj_subheading.setStyleSheet(f"color: {text_secondary};")
        self.obs_heading.setStyleSheet(f"color: {text_primary};")
        self.obs_subheading.setStyleSheet(f"color: {text_secondary};")
        self.sec_heading.setStyleSheet(f"color: {text_primary};")
        self.sec_subheading.setStyleSheet(f"color: {text_secondary};")

        self._refresh_status_pill_style()
        self._apply_badge_style(self.hk_active_badge, is_active=True)
        self._update_sync_status()
        self._refresh_encryption_ui()

        # Setting row titles and descriptions via parent container style
        for lbl in self.findChildren(QLabel, "SettingRowTitle"):
            lbl.setStyleSheet(f"color: {text_primary};")
        for lbl in self.findChildren(QLabel, "SettingRowDesc"):
            lbl.setStyleSheet(f"color: {text_secondary};")
        for div in self.findChildren(QFrame, "SettingDivider"):
            div.setStyleSheet(f"background-color: {div_color}; max-height: 1px; border: none;")

        # Inputs styling
        input_qss = f"""
            QLineEdit, QSpinBox {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 6px;
                padding: 4px 10px;
                font-family: {FONT_SANS};
                font-size: 11px;
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
                background: rgba(255, 255, 255, 0.1) if is_dark else rgba(0, 0, 0, 0.06);
            }}
        """
        self.vault_path_input.setStyleSheet(input_qss)
        self.vault_logs_folder_input.setStyleSheet(input_qss)
        self.interval_spin.set_theme(is_dark)
        self.backup_retention_spin.set_theme(is_dark)
        for inp in self.hotkey_inputs.values():
            inp.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {text_primary};
                    border: 1px solid {input_border};
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-family: {FONT_MONO};
                    font-size: 11px;
                    font-weight: bold;
                }}
                QLineEdit:focus {{
                    background-color: {inner_bg};
                    border: 1.5px solid {input_focus};
                }}
            """)

        # Neutral buttons
        neutral_btn_qss = f"""
            QPushButton {{
                background-color: {btn_neutral_bg};
                color: {btn_neutral_text};
                border: 1px solid {btn_neutral_border};
                border-radius: 6px;
                padding: 5px 12px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_neutral_hover_bg};
                border-color: {input_focus};
            }}
        """
        self.browse_btn.setStyleSheet(neutral_btn_qss)
        self.add_proj_btn.setStyleSheet(neutral_btn_qss)
        self.reset_hk_btn.setStyleSheet(neutral_btn_qss)
        self.toggle_enc_btn.setStyleSheet(neutral_btn_qss)
        self.view_key_btn.setStyleSheet(neutral_btn_qss)
        self.create_backup_btn.setStyleSheet(neutral_btn_qss)
        self.restore_backup_btn.setStyleSheet(neutral_btn_qss)

        # Danger button
        self.del_proj_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_danger_bg};
                color: {btn_danger_text};
                border: 1px solid {btn_danger_border};
                border-radius: 6px;
                padding: 5px 12px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_danger_hover_bg};
            }}
        """)

        # Accent Action buttons (Save Settings & Save Shortcuts)
        accent_btn_qss = f"""
            QPushButton {{
                background-color: {save_bg};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {save_hover};
            }}
            QPushButton:pressed {{
                background-color: {save_pressed};
            }}
        """
        self.save_btn.setStyleSheet(accent_btn_qss)
        self.save_hk_btn.setStyleSheet(accent_btn_qss)

        # Projects Table
        self.proj_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {inner_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 6px;
                gridline-color: {table_grid};
                font-family: {FONT_SANS};
                font-size: 11px;
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
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {table_header_bg};
                color: {text_secondary};
                border: none;
                border-bottom: 1px solid {table_header_border};
                padding: 5px 10px;
                font-family: {FONT_SANS};
                font-size: 10px;
                font-weight: 600;
            }}
        """)
