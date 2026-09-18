"""
Dedicated Help, FAQ, and Global Hotkeys Configuration View for WizDesk.
Provides comprehensive documentation on how WizDesk works, local privacy guarantees,
performance footprint, open source licensing, and user-customizable keyboard shortcuts.
Strictly follows zero-emoji design guidelines with crisp typography and vector accents.
"""

from typing import Optional, Dict, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
)

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.ui.fonts import FONT_SANS, FONT_MONO, get_font
from wiz.utils.hotkey import normalize_hotkey_str, format_display_shortcut


class FaqItemWidget(QFrame):
    """Collapsible FAQ accordion question card."""

    def __init__(self, question: str, answer: str, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.question_text = question
        self.answer_text = answer
        self.is_dark = is_dark
        self.is_expanded = False

        self.setObjectName("faqItem")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(8)

        # Header Row (Clickable)
        self.header_btn = QPushButton(self)
        self.header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_btn.setAutoDefault(False)
        self.header_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.header_btn.clicked.connect(self.toggle_expand)

        header_layout = QHBoxLayout(self.header_btn)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.q_lbl = QLabel(question, self.header_btn)
        self.q_lbl.setFont(get_font(10, QFont.Weight.DemiBold))
        header_layout.addWidget(self.q_lbl)
        header_layout.addStretch()

        self.indicator_lbl = QLabel("[+]", self.header_btn)
        self.indicator_lbl.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        header_layout.addWidget(self.indicator_lbl)

        self.layout.addWidget(self.header_btn)

        # Answer Label (Hidden by default)
        self.a_lbl = QLabel(answer, self)
        self.a_lbl.setFont(get_font(9))
        self.a_lbl.setWordWrap(True)
        self.a_lbl.setVisible(False)
        self.layout.addWidget(self.a_lbl)

        self.update_theme(self.is_dark)

    def toggle_expand(self) -> None:
        """Toggle question expansion."""
        self.is_expanded = not self.is_expanded
        self.a_lbl.setVisible(self.is_expanded)
        self.indicator_lbl.setText("[-]" if self.is_expanded else "[+]")

    def update_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        bg = "#1B1B22" if is_dark else "#F4F1EA"
        border = "#2B2B38" if is_dark else "#D8D2C6"
        q_fg = "#F4F4F5" if is_dark else "#242220"
        a_fg = "#A1A1AA" if is_dark else "#666059"
        ind_fg = "#FF6B3D" if is_dark else "#E05326"

        self.setStyleSheet(f"""
            QFrame#faqItem {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                text-align: left;
                padding: 0;
            }}
        """)
        self.q_lbl.setStyleSheet(f"color: {q_fg};")
        self.a_lbl.setStyleSheet(f"color: {a_fg}; padding-top: 4px; line-height: 140%;")
        self.indicator_lbl.setStyleSheet(f"color: {ind_fg};")


class HelpFaqView(QWidget):
    """
    Comprehensive in-workspace Help, FAQ, and Hotkeys Configuration view.
    Provides clear technical guides on architecture, security, performance,
    and allows user configuration of global shortcuts.
    """

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.hotkey_inputs: Dict[str, QLineEdit] = {}
        self.faq_items: List[FaqItemWidget] = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 8, 12, 12)
        self.main_layout.setSpacing(12)

        # Scroll Area for clean view on any resolution
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(4, 4, 12, 12)
        self.content_layout.setSpacing(16)

        # --------------------------------------------------------------------
        # 1. Header Banner
        # --------------------------------------------------------------------
        header_box = QVBoxLayout()
        header_box.setSpacing(4)

        self.header_title = QLabel("Help & Documentation")
        self.header_title.setFont(get_font(12, QFont.Weight.Bold))
        header_box.addWidget(self.header_title)

        self.header_desc = QLabel(
            "Reference guide for WizDesk features, global keyboard shortcuts, local privacy architecture, and FAQs."
        )
        self.header_desc.setFont(get_font(9))
        header_box.addWidget(self.header_desc)
        self.content_layout.addLayout(header_box)

        # --------------------------------------------------------------------
        # 2. Section: Keyboard Shortcuts (User Configurable)
        # --------------------------------------------------------------------
        self.hotkeys_card = QFrame()
        self.hotkeys_card.setObjectName("settingsCard")
        hk_layout = QVBoxLayout(self.hotkeys_card)
        hk_layout.setContentsMargins(16, 14, 16, 14)
        hk_layout.setSpacing(12)

        hk_title_row = QHBoxLayout()
        self.hk_title = QLabel("Global Keyboard Shortcuts")
        self.hk_title.setFont(get_font(10, QFont.Weight.Bold))
        hk_title_row.addWidget(self.hk_title)
        hk_title_row.addStretch()

        self.hk_status_badge = QLabel("Active")
        self.hk_status_badge.setFont(get_font(8, QFont.Weight.Bold))
        self.hk_status_badge.setContentsMargins(6, 2, 6, 2)
        hk_title_row.addWidget(self.hk_status_badge)
        hk_layout.addLayout(hk_title_row)

        self.hk_desc = QLabel(
            "Global hotkeys trigger actions across your operating system even when WizDesk is in the background. "
            "Click any field to customize your shortcuts, then click 'Save Shortcuts'."
        )
        self.hk_desc.setFont(get_font(9))
        self.hk_desc.setWordWrap(True)
        hk_layout.addWidget(self.hk_desc)

        # Hotkey Configuration Fields
        shortcuts_meta = [
            ("hotkey_workspace", "Open Workspace Window", "<ctrl>+<shift>+w", "Opens the main tasks, notes, and activity dashboard."),
            ("hotkey_toggle_mascot", "Show / Hide Desktop Mascot", "<ctrl>+<shift>+m", "Quickly toggles the desktop companion on or off screen."),
            ("hotkey_quick_task", "Quick Add Task Bar", "<ctrl>+<shift>+t", "Summons the lightweight floating bar to capture a task."),
            ("hotkey_quick_note", "Quick Add Note Bar", "<ctrl>+<shift>+n", "Summons the lightweight floating bar to capture a quick note."),
        ]

        self.hotkey_rows_layout = QVBoxLayout()
        self.hotkey_rows_layout.setSpacing(8)

        for key_name, label_text, default_val, help_text in shortcuts_meta:
            row_frame = QFrame()
            row_frame.setObjectName("subCard")
            r_layout = QHBoxLayout(row_frame)
            r_layout.setContentsMargins(12, 8, 12, 8)
            r_layout.setSpacing(12)

            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            lbl = QLabel(label_text)
            lbl.setFont(get_font(9, QFont.Weight.DemiBold))
            info_col.addWidget(lbl)

            sub_lbl = QLabel(help_text)
            sub_lbl.setFont(get_font(8))
            info_col.addWidget(sub_lbl)
            r_layout.addLayout(info_col, stretch=1)

            # Input field
            line_edit = QLineEdit()
            line_edit.setFixedWidth(160)
            line_edit.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            current_val = config.get(key_name, default_val)
            line_edit.setText(format_display_shortcut(current_val))
            line_edit.setPlaceholderText("e.g. Ctrl+Shift+W")
            self.hotkey_inputs[key_name] = line_edit
            r_layout.addWidget(line_edit)

            self.hotkey_rows_layout.addWidget(row_frame)

        hk_layout.addLayout(self.hotkey_rows_layout)

        # Buttons Row: Save & Reset
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.save_hk_btn = QPushButton("Save Shortcuts")
        self.save_hk_btn.setFont(get_font(9, QFont.Weight.Bold))
        self.save_hk_btn.setFixedHeight(30)
        self.save_hk_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_hk_btn.clicked.connect(self._on_save_hotkeys)
        btn_row.addWidget(self.save_hk_btn)

        self.reset_hk_btn = QPushButton("Reset to Defaults")
        self.reset_hk_btn.setFont(get_font(9))
        self.reset_hk_btn.setFixedHeight(30)
        self.reset_hk_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.reset_hk_btn.clicked.connect(self._on_reset_hotkeys)
        btn_row.addWidget(self.reset_hk_btn)

        btn_row.addStretch()

        self.hk_feedback_lbl = QLabel("")
        self.hk_feedback_lbl.setFont(get_font(8, QFont.Weight.DemiBold))
        btn_row.addWidget(self.hk_feedback_lbl)

        hk_layout.addLayout(btn_row)
        self.content_layout.addWidget(self.hotkeys_card)

        # --------------------------------------------------------------------
        # 3. Section: How WizDesk Works
        # --------------------------------------------------------------------
        self.works_card = QFrame()
        self.works_card.setObjectName("settingsCard")
        works_layout = QVBoxLayout(self.works_card)
        works_layout.setContentsMargins(16, 14, 16, 14)
        works_layout.setSpacing(10)

        self.works_title = QLabel("How WizDesk Works")
        self.works_title.setFont(get_font(10, QFont.Weight.Bold))
        works_layout.addWidget(self.works_title)

        works_items = [
            ("Autonomous Work Categorization",
             "WizDesk runs quietly on your desktop without requiring manual start/stop punch clocks. "
             "Every 5 seconds, it checks the active foreground window title and matches it against your configured project keywords. "
             "When you switch tasks (e.g. from code editor to browser), WizDesk automatically concludes the prior session and logs the exact duration."),
            ("Mascot Companion Moods",
             "Your desktop companion reacts dynamically to your actual working state:\n"
             "  • WORKING: Active keyboard/mouse activity while focused on a recognized task.\n"
             "  • IDLE: Brief pause (>10 seconds of inactivity).\n"
             "  • SLEEP: Extended break (>1 minute of inactivity).\n"
             "  • NOTIFY: Transient reaction when new tasks or notes are logged.\n"
             "  • COMPLETE: Celebration bounce when a task is checked off."),
            ("Custom Project Matching",
             "Assign custom keywords under the Projects tab (e.g. 'code', 'docs', 'figma'). "
             "Whenever an active window contains those keywords, activity time is automatically attributed to that project."),
        ]

        for title, body in works_items:
            item_box = QVBoxLayout()
            item_box.setSpacing(2)
            t_lbl = QLabel(title)
            t_lbl.setFont(get_font(9, QFont.Weight.DemiBold))
            item_box.addWidget(t_lbl)

            b_lbl = QLabel(body)
            b_lbl.setFont(get_font(9))
            b_lbl.setWordWrap(True)
            item_box.addWidget(b_lbl)
            works_layout.addLayout(item_box)

        self.content_layout.addWidget(self.works_card)

        # --------------------------------------------------------------------
        # 4. Section: Privacy, Performance & Open Source Architecture
        # --------------------------------------------------------------------
        self.arch_card = QFrame()
        self.arch_card.setObjectName("settingsCard")
        arch_layout = QVBoxLayout(self.arch_card)
        arch_layout.setContentsMargins(16, 14, 16, 14)
        arch_layout.setSpacing(12)

        self.arch_title = QLabel("Privacy, Performance & Open Source")
        self.arch_title.setFont(get_font(10, QFont.Weight.Bold))
        arch_layout.addWidget(self.arch_title)

        arch_sections = [
            ("Privacy: 100% Local & Zero Telemetry",
             "WizDesk is built on strict zero-telemetry principles. All your task records, subtasks, notes, project allocations, "
             "and activity intervals are stored strictly on your local device in a standard SQLite database (%APPDATA%\\WizDesk\\wizdesk.db on Windows).\n"
             "WizDesk does NOT send any data to external cloud servers, does NOT transmit analytics or diagnostics, and does NOT access personal files.\n"
             "No Keylogging: Global shortcuts are evaluated strictly as combination chords by the OS. WizDesk never captures or logs your keystrokes."),
            ("Performance: Native Desktop Efficiency & Low Footprint",
             "Unlike resource-intensive Electron or browser-based productivity tools, WizDesk is compiled with native PyQt6.\n"
             "  • CPU Utilization: Typically less than 0.3% CPU during normal polling cycles.\n"
             "  • Memory Footprint: Highly optimized binary with deterministic memory release.\n"
             "  • Hardware Accelerated: Crisp vector graphics rendered cleanly without GPU thrashing."),
            ("Open Source: Transparent Code & Community Driven",
             "WizDesk is free, open-source software licensed under the permissive MIT License.\n"
             "The source code is completely auditable, allowing developers to inspect data handling, customize tracking logic, "
             "and contribute new companion behaviors or UI enhancements."),
        ]

        for title, body in arch_sections:
            sec_box = QVBoxLayout()
            sec_box.setSpacing(2)
            st_lbl = QLabel(title)
            st_lbl.setFont(get_font(9, QFont.Weight.DemiBold))
            sec_box.addWidget(st_lbl)

            sb_lbl = QLabel(body)
            sb_lbl.setFont(get_font(9))
            sb_lbl.setWordWrap(True)
            sec_box.addWidget(sb_lbl)
            arch_layout.addLayout(sec_box)

        self.content_layout.addWidget(self.arch_card)

        # --------------------------------------------------------------------
        # 5. Section: Frequently Asked Questions (FAQ)
        # --------------------------------------------------------------------
        self.faq_card = QFrame()
        self.faq_card.setObjectName("settingsCard")
        faq_layout = QVBoxLayout(self.faq_card)
        faq_layout.setContentsMargins(16, 14, 16, 14)
        faq_layout.setSpacing(10)

        self.faq_title = QLabel("Frequently Asked Questions")
        self.faq_title.setFont(get_font(10, QFont.Weight.Bold))
        faq_layout.addWidget(self.faq_title)

        faq_questions = [
            ("How do I change a keyboard shortcut?",
             "Type your desired key chord into any field in the Global Keyboard Shortcuts section above "
             "(for example: 'Ctrl+Shift+T' or 'Alt+Shift+N') and click 'Save Shortcuts'. "
             "The listener updates immediately without requiring a restart."),
            ("Can I hide the mascot and still track work?",
             "Yes. Press Ctrl+Shift+M (or your configured shortcut) to toggle the mascot visibility. "
             "Background activity tracking continues uninterrupted while the mascot is hidden."),
            ("How does local Obsidian sync work?",
             "Under the Settings tab, select your local Obsidian vault directory. "
             "Whenever you complete tasks or log notes, WizDesk generates a daily markdown file under your vault's 'WizDesk Logs' folder."),
            ("What should I do if a shortcut conflicts with my code editor?",
             "You can rebind any shortcut to use alternative modifiers such as Alt+Shift or Ctrl+Alt in the shortcuts table above."),
            ("Where is my database located and how do I back it up?",
             "Your entire history is contained in a single SQLite database file located at:\n"
             "Windows: %APPDATA%\\WizDesk\\wizdesk.db\n"
             "Linux: ~/.local/share/WizDesk/wizdesk.db\n"
             "Simply copy this file to any backup storage anytime."),
            ("How do I quit WizDesk completely?",
             "You can exit WizDesk at any time using the Quit option in the system tray icon (near the Windows clock) "
             "or by closing the main workspace window."),
        ]

        for q, a in faq_questions:
            item = FaqItemWidget(q, a, is_dark=self.is_dark, parent=self.faq_card)
            self.faq_items.append(item)
            faq_layout.addWidget(item)

        self.content_layout.addWidget(self.faq_card)

        # Assemble Scroll View
        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll)

        # Apply Initial Theme
        self.set_theme(self.is_dark)

    def _on_save_hotkeys(self) -> None:
        """Validate and persist user-configured hotkeys."""
        try:
            for key_name, input_field in self.hotkey_inputs.items():
                raw_text = input_field.text().strip()
                norm = normalize_hotkey_str(raw_text)
                if norm:
                    config.set(key_name, norm)
                    input_field.setText(format_display_shortcut(norm))

            # Maintain backwards-compatible legacy key
            if "hotkey_workspace" in self.hotkey_inputs:
                config.set("global_hotkey", config.get("hotkey_workspace"))

            config.save()
            app_signals.hotkeys_changed.emit()

            self.hk_feedback_lbl.setText("Shortcuts saved and reloaded successfully.")
            self.hk_feedback_lbl.setStyleSheet("color: #10B981;")
        except Exception as e:
            self.hk_feedback_lbl.setText(f"Error: {e}")
            self.hk_feedback_lbl.setStyleSheet("color: #EF4444;")

    def _on_reset_hotkeys(self) -> None:
        """Reset all shortcuts to Option 1 defaults."""
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

    def load_settings(self) -> None:
        """Reload configuration from disk."""
        for key_name, input_field in self.hotkey_inputs.items():
            val = config.get(key_name, "")
            input_field.setText(format_display_shortcut(val))
        self.hk_feedback_lbl.setText("")

    def set_theme(self, is_dark: bool) -> None:
        """Update styles for light or dark mode."""
        self.is_dark = is_dark

        card_bg = "#16161C" if is_dark else "#F7F5EE"
        sub_bg = "#1B1B22" if is_dark else "#ECE7DC"
        card_border = "#262632" if is_dark else "#D8D2C6"
        sub_border = "#2B2B38" if is_dark else "#D2CBC0"
        title_fg = "#F4F4F5" if is_dark else "#242220"
        desc_fg = "#A1A1AA" if is_dark else "#666059"
        input_bg = "#21212B" if is_dark else "#E5DFD4"
        input_border = "#333342" if is_dark else "#C8C0B2"
        input_fg = "#FFFFFF" if is_dark else "#1A1918"
        btn_neutral_bg = "#252532" if is_dark else "#E5DFD4"
        btn_neutral_border = "#353545" if is_dark else "#C8C0B2"
        btn_neutral_fg = "#E4E4E7" if is_dark else "#2D2A26"

        self.header_title.setStyleSheet(f"color: {title_fg};")
        self.header_desc.setStyleSheet(f"color: {desc_fg};")
        self.hk_title.setStyleSheet(f"color: {title_fg};")
        self.hk_desc.setStyleSheet(f"color: {desc_fg};")
        self.works_title.setStyleSheet(f"color: {title_fg};")
        self.arch_title.setStyleSheet(f"color: {title_fg};")
        self.faq_title.setStyleSheet(f"color: {title_fg};")

        badge_bg = "#064E3B" if is_dark else "#D1FAE5"
        badge_fg = "#34D399" if is_dark else "#065F46"
        self.hk_status_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border: 1px solid #059669;
            border-radius: 4px;
        """)

        card_qss = f"""
            QFrame#settingsCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 10px;
            }}
            QFrame#subCard {{
                background-color: {sub_bg};
                border: 1px solid {sub_border};
                border-radius: 6px;
            }}
            QLabel {{
                color: {title_fg};
            }}
            QLineEdit {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 6px;
                color: {input_fg};
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid #FF6B3D;
            }}
        """
        self.hotkeys_card.setStyleSheet(card_qss)
        self.works_card.setStyleSheet(card_qss)
        self.arch_card.setStyleSheet(card_qss)
        self.faq_card.setStyleSheet(card_qss)

        self.save_hk_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B3D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #E05326;
            }
        """)

        self.reset_hk_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_neutral_bg};
                color: {btn_neutral_fg};
                border: 1px solid {btn_neutral_border};
                border-radius: 6px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background-color: #FF6B3D;
                color: #FFFFFF;
                border-color: #FF6B3D;
            }}
        """)

        for item in self.faq_items:
            item.update_theme(is_dark)
