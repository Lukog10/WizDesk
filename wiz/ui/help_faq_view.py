"""
Modernized Help, FAQ, and Platform Documentation View for WizDesk.
Implements the clean FAQ accordion layout with category filtering and
the editorial Platform Documentation guide matching Riddle UI.
Zero-telemetry and zero-emoji compliance.
"""

from typing import Optional, Dict, List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QStackedWidget,
    QButtonGroup,
)

from wiz.ui.fonts import FONT_SANS, FONT_MONO, get_font


class FaqItemWidget(QFrame):
    """
    Clean, rounded accordion card for FAQ items.
    Features modern typography, smooth toggle between '+' and '-',
    and refined border/background styling with generous body padding.
    """

    def __init__(
        self,
        question: str,
        answer: str,
        category: str = "general",
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.question_text = question
        self.answer_text = answer
        self.category = category
        self.is_dark = is_dark
        self.is_expanded = False

        self.setObjectName("faqItem")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 18, 20, 18)
        self.layout.setSpacing(10)

        # Header Button (Entire row clickable)
        self.header_btn = QPushButton(self)
        self.header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_btn.setAutoDefault(False)
        self.header_btn.setDefault(False)
        self.header_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.header_btn.clicked.connect(self.toggle_expand)

        header_layout = QHBoxLayout(self.header_btn)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.q_lbl = QLabel(question, self.header_btn)
        self.q_lbl.setFont(get_font(10.5, QFont.Weight.DemiBold))
        self.q_lbl.setWordWrap(True)
        header_layout.addWidget(self.q_lbl, stretch=1)

        # Sleek + / - toggle indicator
        self.indicator_lbl = QLabel("+", self.header_btn)
        self.indicator_lbl.setFont(get_font(13, QFont.Weight.Medium))
        self.indicator_lbl.setFixedWidth(18)
        self.indicator_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.indicator_lbl)

        self.layout.addWidget(self.header_btn)

        # Answer Label (Hidden by default)
        self.a_lbl = QLabel(self)
        self.a_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.a_lbl.setFont(get_font(9.5))
        self.a_lbl.setWordWrap(True)
        self.a_lbl.setVisible(False)
        self.a_lbl.setContentsMargins(0, 6, 0, 2)
        self.layout.addWidget(self.a_lbl)

        self.update_theme(self.is_dark)

    def toggle_expand(self) -> None:
        """Toggle question expansion."""
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, expanded: bool) -> None:
        """Explicitly set expansion state."""
        self.is_expanded = expanded
        self.a_lbl.setVisible(self.is_expanded)
        self.indicator_lbl.setText("-" if self.is_expanded else "+")

    def update_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        bg = "#18181C" if is_dark else "#F9F7F2"
        border = "#262630" if is_dark else "#E2DDD4"
        q_fg = "#F4F4F6" if is_dark else "#1E1C1A"
        a_fg = "#A1A1AA" if is_dark else "#5E5851"
        ind_fg = "#FF6B3D" if is_dark else "#D94E23"

        self.setStyleSheet(f"""
            QFrame#faqItem {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                text-align: left;
                padding: 0;
            }}
        """)
        self.q_lbl.setStyleSheet(f"color: {q_fg};")
        self.indicator_lbl.setStyleSheet(f"color: {ind_fg};")
        self.a_lbl.setText(
            f"<div style='color: {a_fg}; line-height: 1.6; font-size: 13px; font-family: {FONT_SANS};'>"
            f"{self.answer_text}"
            f"</div>"
        )


class HelpFaqView(QWidget):
    """
    Modern Help, FAQ & Platform Documentation Hub.
    Combines:
    - View Switcher: [ FAQs ] [ Documentation ]
    - FAQ Page: Category sidebar (General, Mascot, Privacy, Obsidian, View All) + Accordion cards
    - Documentation Page: Editorial platform guide outline + rich reading canvas
    - Quick link to Settings > Hotkeys
    """

    open_settings_requested = pyqtSignal(str)

    FAQ_CATEGORIES = [
        ("all", "View all"),
        ("general", "General"),
        ("mascot", "Mascot && Tracking"),
        ("privacy", "Privacy && Security"),
        ("backup", "Backup && Restore"),
        ("obsidian", "Obsidian Sync"),
    ]

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.current_faq_cat = "all"
        self.faq_items: List[FaqItemWidget] = []
        self.faq_cat_btns: Dict[str, QPushButton] = {}
        self.doc_topic_btns: List[QPushButton] = []

        self._init_ui()

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(14)

        # --------------------------------------------------------------------
        # 1. Top Header Bar
        # --------------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(12)

        # Title & Subtitle Box
        header_info = QVBoxLayout()
        header_info.setSpacing(4)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)

        self.tag_pill = QLabel("/ FAQS", self)
        self.tag_pill.setFont(get_font(8, QFont.Weight.Bold))
        self.tag_pill.setContentsMargins(6, 2, 6, 2)
        self.tag_pill.setObjectName("tagPill")
        tag_row.addWidget(self.tag_pill)
        tag_row.addStretch()

        header_info.addLayout(tag_row)

        self.header_title = QLabel("Frequently Asked Questions", self)
        self.header_title.setFont(get_font(14, QFont.Weight.Bold))
        header_info.addWidget(self.header_title)

        self.header_desc = QLabel(
            "Answers to common questions about tracking, encryption, backups, and setup.",
            self,
        )
        self.header_desc.setFont(get_font(9.5))
        self.header_desc.setWordWrap(True)
        header_info.addWidget(self.header_desc)

        header_bar.addLayout(header_info, stretch=1)

        # Segmented View Switcher: [ FAQs ] [ Documentation ]
        self.mode_switcher_frame = QFrame(self)
        self.mode_switcher_frame.setObjectName("modeSwitcher")
        switcher_layout = QHBoxLayout(self.mode_switcher_frame)
        switcher_layout.setContentsMargins(3, 3, 3, 3)
        switcher_layout.setSpacing(4)

        self.faq_tab_btn = QPushButton("FAQs", self.mode_switcher_frame)
        self.faq_tab_btn.setFont(get_font(9, QFont.Weight.Bold))
        self.faq_tab_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.faq_tab_btn.setAutoDefault(False)
        self.faq_tab_btn.setDefault(False)
        self.faq_tab_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.faq_tab_btn.clicked.connect(lambda: self.switch_view_mode("faq"))
        switcher_layout.addWidget(self.faq_tab_btn)

        self.docs_tab_btn = QPushButton("Documentation", self.mode_switcher_frame)
        self.docs_tab_btn.setFont(get_font(9, QFont.Weight.Bold))
        self.docs_tab_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.docs_tab_btn.setAutoDefault(False)
        self.docs_tab_btn.setDefault(False)
        self.docs_tab_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.docs_tab_btn.clicked.connect(lambda: self.switch_view_mode("docs"))
        switcher_layout.addWidget(self.docs_tab_btn)

        header_bar.addWidget(self.mode_switcher_frame, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.main_layout.addLayout(header_bar)

        # --------------------------------------------------------------------
        # 2. Main Stacked Container (Page 0: FAQs, Page 1: Documentation)
        # --------------------------------------------------------------------
        self.stack = QStackedWidget(self)

        self.page_faq = self._build_faq_page()
        self.page_docs = self._build_docs_page()

        self.stack.addWidget(self.page_faq)   # Index 0
        self.stack.addWidget(self.page_docs)  # Index 1

        self.main_layout.addWidget(self.stack, stretch=1)

        # Apply initial theme & view
        self.current_mode = "faq"
        self.set_theme(self.is_dark)

    # ------------------------------------------------------------------------
    # PAGE 1: FAQ INTERFACE (Reference Image 1)
    # ------------------------------------------------------------------------
    def _build_faq_page(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(16)

        # Left Column: Category Navigation Pills
        self.faq_nav_col = QFrame(container)
        self.faq_nav_col.setFixedWidth(160)
        self.faq_nav_col.setStyleSheet("background: transparent; border: none;")
        nav_layout = QVBoxLayout(self.faq_nav_col)
        nav_layout.setContentsMargins(0, 4, 0, 0)
        nav_layout.setSpacing(6)

        for cat_id, cat_title in self.FAQ_CATEGORIES:
            btn = QPushButton(cat_title, self.faq_nav_col)
            btn.setFont(get_font(9, QFont.Weight.Medium))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(lambda checked, c=cat_id: self.filter_faq_category(c))
            self.faq_cat_btns[cat_id] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)

        # Contribute link box at bottom of category nav
        self.contribute_box = QFrame(self.faq_nav_col)
        self.contribute_box.setObjectName("contributeBox")
        contribute_layout = QVBoxLayout(self.contribute_box)
        contribute_layout.setContentsMargins(10, 10, 10, 10)
        contribute_layout.setSpacing(6)

        contribute_lbl = QLabel("Contribute", self.contribute_box)
        contribute_lbl.setFont(get_font(8.5, QFont.Weight.Bold))
        contribute_layout.addWidget(contribute_lbl)

        contribute_sub = QLabel("WizDesk is open-source. Report issues or contribute on GitHub.", self.contribute_box)
        contribute_sub.setFont(get_font(7.5))
        contribute_sub.setWordWrap(True)
        contribute_layout.addWidget(contribute_sub)

        self.github_btn = QPushButton("Contribute on GitHub →", self.contribute_box)
        self.github_btn.setFont(get_font(8, QFont.Weight.DemiBold))
        self.github_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.github_btn.setAutoDefault(False)
        self.github_btn.setDefault(False)
        self.github_btn.clicked.connect(self._open_github)
        contribute_layout.addWidget(self.github_btn)

        # Backwards-compatibility aliases
        self.open_settings_btn = self.github_btn
        self.hk_link_box = self.contribute_box

        nav_layout.addWidget(self.contribute_box)
        layout.addWidget(self.faq_nav_col)

        # Right Column: Scrollable Accordion Cards
        self.faq_scroll = QScrollArea(container)
        self.faq_scroll.setWidgetResizable(True)
        self.faq_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.faq_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.faq_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.faq_scroll.setStyleSheet("background: transparent; border: none;")

        self.faq_list_widget = QWidget()
        self.faq_list_widget.setStyleSheet("background: transparent;")
        self.faq_list_layout = QVBoxLayout(self.faq_list_widget)
        self.faq_list_layout.setContentsMargins(4, 4, 10, 8)
        self.faq_list_layout.setSpacing(10)

        # FAQ Question Dataset
        faq_data = [
            ("general",
             "What does WizDesk do?",
             "WizDesk is a desktop task manager and automated time tracker. It logs time to your projects by checking active window titles, lets you capture quick notes, and displays a desktop companion that reflects your current work state."),
            ("general",
             "How do I create tasks and notes?",
             "Click '+ Add task' in the Tasks tab or press Enter in the bottom input bar. Notes can be captured instantly in the Quick Notes tab or opened from anywhere with global shortcuts."),
            ("general",
             "How do I quit WizDesk?",
             "Right-click the tray icon near the Windows clock and select Quit, or close the main workspace window."),
            ("mascot",
             "How does window time tracking work?",
             "Every 5 seconds, WizDesk checks your active window title against your project keywords. When a match is found, time is logged to that project. When you switch windows, the previous session concludes and saves its duration to the database."),
            ("mascot",
             "What do the mascot states mean?",
             "The companion indicates your work activity: Working (typing or clicking on a recognized task with spinning eyes), Idle (no activity for 10 seconds with cursor-tracking eyes), Sleep (inactive for 1 minute or more), Notify (brief alert when adding tasks or notes), and Complete (short animation when finishing a task)."),
            ("mascot",
             "How do the cursor-tracking eyes work?",
             "In Idle mode, the mascot eyes follow your mouse cursor coordinates across the screen. When you return to active work, the eyes change to spinning indicators to show active time logging."),
            ("mascot",
             "Can I turn off sound effects?",
             "Yes. Built-in sound effects play for wake, sleep, task completion, cancellation, and interaction. You can change volume or disable sounds under Settings > General."),
            ("mascot",
             "Can I hide the mascot?",
             "Yes. Press Ctrl+Shift+M (or your configured shortcut in Settings > Hotkeys) to hide or show the mascot. Window tracking continues in the background."),
            ("privacy",
             "Where is my data stored?",
             "All tasks, subtasks, notes, project mappings, and logs are stored locally on your machine in a SQLite database. WizDesk does not send telemetry or sync data to external servers."),
            ("privacy",
             "Does WizDesk log keystrokes or record screens?",
             "No. WizDesk only reads active window title strings every 5 seconds to attribute project time. It never records keystrokes, screenshots, or file contents."),
            ("privacy",
             "How does Database Encryption work?",
             "WizDesk supports AES-256-GCM encryption at rest. When enabled under Settings > Security, the database is loaded into memory on launch and saved back to disk encrypted. No plaintext files remain on disk."),
            ("privacy",
             "How is the encryption key secured?",
             "Your 256-bit encryption key is stored through Windows DPAPI and tied to your user login for automatic startup. You can also view and copy your master key (formatted as WIZK-...) in Settings > Security for manual backup."),
            ("privacy",
             "Can I turn off encryption?",
             "Yes. Click 'Disable Encryption' in Settings > Security. WizDesk decrypts your database back to standard SQLite format."),
            ("backup",
             "How do automated backups work?",
             "When enabled under Settings > Security, WizDesk creates a snapshot backup on application startup. Encrypted databases save as .wbak files, while standard databases save as .bak files."),
            ("backup",
             "How do I create a manual backup?",
             "Go to Settings > Security and click 'Create Backup Now'. A timestamped snapshot is saved to your local backups folder (%APPDATA%\\WizDesk\\backups). Manual snapshots are never pruned."),
            ("backup",
             "How does the retention limit work?",
             "Set the retention count (1 to 30 snapshots) under Settings > Security. When automatic backups exceed this count, the oldest automatic snapshots are removed. Manual and pre-restore backups are kept."),
            ("backup",
             "How do I restore from a backup?",
             "Click 'Restore from File...' in Settings > Security and choose a .bak or .wbak file. WizDesk runs an integrity check and creates a pre-restore safety snapshot before replacing your active data."),
            ("backup",
             "How do I move my data to another computer?",
             "Copy your .bak or .wbak backup files from %APPDATA%\\WizDesk\\backups to the new machine. If using encrypted .wbak files, export your master key from Settings > Security and enter it during restoration on the target computer."),
            ("obsidian",
             "How does Obsidian sync work?",
             "Under Settings > Integrations, select your Obsidian vault folder. WizDesk writes completed tasks and daily logged time into Markdown notes inside your vault."),
            ("obsidian",
             "Can I change the vault folder for logs?",
             "Yes. You can customize the subfolder name under Settings > Integrations (defaults to 'WizDesk Logs'). WizDesk creates it if it does not exist."),
        ]

        for cat, q, a in faq_data:
            item = FaqItemWidget(question=q, answer=a, category=cat, is_dark=self.is_dark, parent=self.faq_list_widget)
            self.faq_items.append(item)
            self.faq_list_layout.addWidget(item)

        self.faq_list_layout.addStretch(1)
        self.faq_scroll.setWidget(self.faq_list_widget)
        layout.addWidget(self.faq_scroll, stretch=1)

        return container

    # ------------------------------------------------------------------------
    # PAGE 2: DOCUMENTATION INTERFACE
    # ------------------------------------------------------------------------
    def _format_doc_body_html(self, body: str, color: Optional[str] = None) -> str:
        """Format plain text documentation body into spacious HTML with line spacing."""
        if not color:
            color = "#A1A1AA" if self.is_dark else "#5E5851"
        strong_color = "#F4F4F6" if self.is_dark else "#18181B"
        blocks = body.split("\n\n")
        html_parts = []
        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue
            if any(l.startswith("•") for l in lines):
                bullet_items = []
                for line in lines:
                    if line.startswith("•"):
                        content = line[1:].strip()
                        if ":" in content:
                            prefix, rest = content.split(":", 1)
                            bullet_items.append(
                                f"<div style='margin-bottom: 8px; line-height: 1.6;'>"
                                f"• <strong style='color: {strong_color};'>{prefix}:</strong>"
                                f"{rest}"
                                f"</div>"
                            )
                        else:
                            bullet_items.append(
                                f"<div style='margin-bottom: 8px; line-height: 1.6;'>• {content}</div>"
                            )
                    else:
                        bullet_items.append(
                            f"<div style='margin-bottom: 8px; line-height: 1.6;'>{line}</div>"
                        )
                html_parts.append(f"<div style='margin-bottom: 10px;'>{''.join(bullet_items)}</div>")
            else:
                html_parts.append(
                    f"<p style='margin: 0 0 12px 0; line-height: 1.6;'>{' '.join(lines)}</p>"
                )

        return (
            f"<div style='color: {color}; font-size: 13px; font-family: {FONT_SANS};'>"
            f"{''.join(html_parts)}"
            f"</div>"
        )

    def _create_doc_section(self, title: str, body: str) -> QFrame:
        """Create a styled editorial documentation card with generous spacing."""
        card = QFrame()
        card.setObjectName("docCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(22, 20, 22, 20)
        c_layout.setSpacing(12)

        t_lbl = QLabel(title, card)
        t_lbl.setFont(get_font(11, QFont.Weight.Bold))
        t_lbl.setObjectName("docCardTitle")
        c_layout.addWidget(t_lbl)

        b_lbl = QLabel(card)
        b_lbl.setTextFormat(Qt.TextFormat.RichText)
        b_lbl.setFont(get_font(9.5))
        b_lbl.setWordWrap(True)
        b_lbl.setObjectName("docCardBody")
        b_lbl.setProperty("raw_body", body)
        b_lbl.setText(self._format_doc_body_html(body))
        c_layout.addWidget(b_lbl)

        return card

    def _build_docs_page(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(18)

        # Left Column: Documentation Outline Sidebar
        self.docs_nav_col = QFrame(container)
        self.docs_nav_col.setFixedWidth(170)
        self.docs_nav_col.setStyleSheet("background: transparent; border: none;")
        doc_nav_layout = QVBoxLayout(self.docs_nav_col)
        doc_nav_layout.setContentsMargins(0, 4, 0, 0)
        doc_nav_layout.setSpacing(4)

        doc_structure = [
            ("Overview", ["Introduction", "Quick Start"]),
            ("Concepts", ["Autonomous Engine", "Mascot States & Audio", "Project Rules"]),
            ("Security & Backups", ["AES-256 Encryption", "Database Backups", "Restore & Migration"]),
            ("Architecture", ["Local SQLite", "Zero Telemetry"]),
            ("Integrations", ["Obsidian Sync", "Shortcuts"]),
        ]

        for section_title, topics in doc_structure:
            sec_lbl = QLabel(section_title.upper().replace("&&", "&"), self.docs_nav_col)
            sec_lbl.setFont(get_font(7, QFont.Weight.Bold))
            sec_lbl.setObjectName("docSectionHeading")
            doc_nav_layout.addWidget(sec_lbl)

            for topic in topics:
                # In QPushButton, ampersands must be doubled to display properly
                btn_display_text = f"• {topic}".replace("&", "&&")
                t_btn = QPushButton(btn_display_text, self.docs_nav_col)
                t_btn.setFont(get_font(8.5, QFont.Weight.Medium))
                t_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                t_btn.setAutoDefault(False)
                t_btn.setDefault(False)
                t_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                t_btn.setObjectName("docTopicBtn")
                t_btn.clicked.connect(lambda checked, t=topic: self._on_doc_topic_clicked(t))
                self.doc_topic_btns.append(t_btn)
                doc_nav_layout.addWidget(t_btn)

            doc_nav_layout.addSpacing(8)

        doc_nav_layout.addStretch(1)
        layout.addWidget(self.docs_nav_col)

        # Right Column: Editorial Platform Guide Reading Canvas
        self.doc_scroll = QScrollArea(container)
        self.doc_scroll.setWidgetResizable(True)
        self.doc_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.doc_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.doc_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.doc_scroll.setStyleSheet("background: transparent; border: none;")

        self.doc_content_widget = QWidget()
        self.doc_content_widget.setStyleSheet("background: transparent;")
        self.doc_layout = QVBoxLayout(self.doc_content_widget)
        self.doc_layout.setContentsMargins(8, 4, 18, 24)
        self.doc_layout.setSpacing(18)

        # Doc Header
        self.doc_title = QLabel("Platform Guide", self.doc_content_widget)
        self.doc_title.setFont(get_font(14, QFont.Weight.Bold))
        self.doc_layout.addWidget(self.doc_title)

        self.doc_intro = QLabel(self.doc_content_widget)
        self.doc_intro.setTextFormat(Qt.TextFormat.RichText)
        self.doc_intro.setFont(get_font(10))
        self.doc_intro.setWordWrap(True)
        self.doc_intro.setText(
            f"<div style='line-height: 1.65; font-size: 13.5px; font-family: {FONT_SANS}; margin-top: 4px; margin-bottom: 6px;'>"
            "WizDesk tracks your project work and captures quick notes from your desktop. "
            "It logs time automatically based on your active windows, stores all data locally in SQLite, "
            "and features an on-screen companion that shows your current activity."
            "</div>"
        )
        self.doc_layout.addWidget(self.doc_intro)

        # Section 1: Autonomous Window Tracking Engine
        self.sec_tracking = self._create_doc_section(
            title="Automated Window Tracking",
            body="WizDesk inspects the active window title every 5 seconds. If the title matches any keyword configured for a project (such as 'code', 'docs', or 'figma'), time is logged to that project.\n\n"
                 "When you switch to another window, WizDesk finishes the current session and saves the duration to your local SQLite database.",
        )
        self.doc_layout.addWidget(self.sec_tracking)

        # Section 2: Mascot Companion Behaviors, Eye-Tracking & Audio
        self.sec_mascot = self._create_doc_section(
            title="Desktop Companion & Sound Engine",
            body="The desktop companion reflects your current activity:\n\n"
                 "• Working: Active typing or clicking on a recognized task. Displays spinning eyes.\n"
                 "• Idle: Inactive for more than 10 seconds. Eyes track the mouse cursor across the screen.\n"
                 "• Sleep: Inactive for more than 1 minute (configurable in Settings). Mascot rests.\n"
                 "• Notify: Brief alert when you add a task or note.\n"
                 "• Complete: Short animation when you finish a task.\n\n"
                 "Sound Effects: Built-in audio cues play for wake, sleep, completion, cancellation, and interaction. You can adjust volume or turn off sounds in Settings > General.",
        )
        self.doc_layout.addWidget(self.sec_mascot)

        # Section 3: Database Encryption (AES-256-GCM)
        self.sec_encryption = self._create_doc_section(
            title="Database Encryption (AES-256-GCM)",
            body="Encrypt all tasks, notes, sessions, and activity logs using AES-256-GCM authenticated encryption.\n\n"
                 "• Secure Storage: Decrypted into memory at startup. Changes are saved back to disk encrypted with atomic writes. No unencrypted text is written to disk.\n"
                 "• Windows DPAPI: The 256-bit encryption key is stored via Windows DPAPI and tied to your Windows user account for zero-prompt login.\n"
                 "• Master Key: Export your 64-character master key (formatted as WIZK-...) anytime in Settings > Security for backup or migration.",
        )
        self.doc_layout.addWidget(self.sec_encryption)

        # Section 4: Automated & On-Demand Backup System
        self.sec_backups = self._create_doc_section(
            title="Automated Backups & Snapshots",
            body="Keep your workspace data safe from accidental loss with automated and manual point-in-time snapshots:\n\n"
                 "• Automatic Backups: Creates daily snapshot backups on startup. Encrypted backups use .wbak; unencrypted backups use .bak.\n"
                 "• Retention Limit: Keeps between 1 and 30 snapshots (set in Settings > Security). Old automatic backups are pruned automatically. Manual backups are never deleted.\n"
                 "• Storage Location: Backups are stored in %APPDATA%\\WizDesk\\backups on Windows or ~/.local/share/WizDesk/backups on Linux.",
        )
        self.doc_layout.addWidget(self.sec_backups)

        # Section 5: Data Restoration & Migration
        self.sec_restore = self._create_doc_section(
            title="Restoration & Machine Migration",
            body="Restore or migrate your entire workspace with complete confidence:\n\n"
                 "• Pre-Restore Snapshot: WizDesk takes a safety snapshot before restoring any backup so you cannot overwrite data by accident.\n"
                 "• Integrity Check: Validates SQLite file integrity (PRAGMA integrity_check) before loading restored data.\n"
                 "• Migration: Copy your backup file to a new machine and restore it via Settings > Security > Restore from File. For encrypted files, enter your Master Key.",
        )
        self.doc_layout.addWidget(self.sec_restore)

        # Section 6: Privacy & Zero Telemetry Architecture
        self.sec_privacy = self._create_doc_section(
            title="Privacy & Local-Only Storage",
            body="WizDesk does not collect analytics, send telemetry, or connect to external servers. All data stays on your machine:\n\n"
                 "• Windows: %APPDATA%\\WizDesk\\wizdesk.db\n"
                 "• Linux: ~/.local/share/WizDesk/wizdesk.db\n\n"
                 "Only active window title bars are checked for project keywords. Keystrokes, screen contents, and personal files are never recorded.",
        )
        self.doc_layout.addWidget(self.sec_privacy)

        # Section 7: Obsidian Daily Logs Sync
        self.sec_obsidian = self._create_doc_section(
            title="Obsidian Daily Logs Sync",
            body="Connect your Obsidian vault in Settings > Integrations. WizDesk appends completed tasks and logged time into daily Markdown notes inside your chosen subfolder (default: WizDesk Logs).",
        )
        self.doc_layout.addWidget(self.sec_obsidian)

        self.doc_layout.addStretch(1)
        self.doc_scroll.setWidget(self.doc_content_widget)
        layout.addWidget(self.doc_scroll, stretch=1)

        return container

    def _on_doc_topic_clicked(self, topic: str) -> None:
        """Handle clicking a topic in the documentation outline."""
        if topic in ("Introduction", "Quick Start"):
            self.doc_scroll.verticalScrollBar().setValue(0)
        elif topic in ("Autonomous Engine", "Project Rules") and hasattr(self, "sec_tracking"):
            self.doc_scroll.ensureWidgetVisible(self.sec_tracking)
        elif "Mascot States" in topic and hasattr(self, "sec_mascot"):
            self.doc_scroll.ensureWidgetVisible(self.sec_mascot)
        elif topic == "AES-256 Encryption" and hasattr(self, "sec_encryption"):
            self.doc_scroll.ensureWidgetVisible(self.sec_encryption)
        elif topic == "Database Backups" and hasattr(self, "sec_backups"):
            self.doc_scroll.ensureWidgetVisible(self.sec_backups)
        elif "Restore" in topic and hasattr(self, "sec_restore"):
            self.doc_scroll.ensureWidgetVisible(self.sec_restore)
        elif topic in ("Local SQLite", "Zero Telemetry") and hasattr(self, "sec_privacy"):
            self.doc_scroll.ensureWidgetVisible(self.sec_privacy)
        elif topic == "Obsidian Sync" and hasattr(self, "sec_obsidian"):
            self.doc_scroll.ensureWidgetVisible(self.sec_obsidian)
        elif topic == "Shortcuts":
            self.open_settings_requested.emit("hotkeys")

    def _open_github(self) -> None:
        """Open the official WizDesk GitHub repository in the default web browser."""
        QDesktopServices.openUrl(QUrl("https://github.com/Lukog10/WizDesk"))

    # ------------------------------------------------------------------------
    # NAVIGATION & CATEGORY FILTERING
    # ------------------------------------------------------------------------
    def switch_view_mode(self, mode: str) -> None:
        """Switch between FAQs and Documentation."""
        self.current_mode = mode
        if mode == "faq":
            self.stack.setCurrentIndex(0)
            self.tag_pill.setText("/ FAQS")
            self.header_title.setText("Frequently Asked Questions")
            self.header_desc.setText(
                "Answers to common questions about tracking, encryption, backups, and setup."
            )
        else:
            self.stack.setCurrentIndex(1)
            self.tag_pill.setText("/ DOCS")
            self.header_title.setText("Platform Documentation")
            self.header_desc.setText(
                "Architecture overview, window tracking details, local database storage, and security guides."
            )
        self.apply_theme()

    def filter_faq_category(self, category: str) -> None:
        """Filter FAQ items by category."""
        self.current_faq_cat = category
        for item in self.faq_items:
            if category == "all" or item.category == category:
                item.setVisible(True)
            else:
                item.setVisible(False)
        self.apply_theme()

    def load_settings(self) -> None:
        """Hook called when view is activated."""
        pass

    # ------------------------------------------------------------------------
    # THEME ENGINE
    # ------------------------------------------------------------------------
    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.apply_theme()

    def apply_theme(self) -> None:
        is_dark = self.is_dark

        # Palette
        title_fg = "#F4F4F6" if is_dark else "#18181B"
        desc_fg = "#A1A1AA" if is_dark else "#57534E"
        tag_bg = "rgba(255, 107, 61, 0.12)" if is_dark else "rgba(234, 88, 12, 0.10)"
        tag_fg = "#FF825C" if is_dark else "#C2410C"
        tag_border = "rgba(255, 107, 61, 0.28)" if is_dark else "rgba(234, 88, 12, 0.25)"

        switcher_bg = "#18181B" if is_dark else "#ECE7DC"
        switcher_border = "#27272A" if is_dark else "#D8D2C6"
        active_tab_bg = "#27272A" if is_dark else "#FFFFFF"
        active_tab_fg = "#FAFAFA" if is_dark else "#18181B"
        active_tab_border = "#3F3F46" if is_dark else "#D5CEC2"
        inactive_tab_fg = "#A1A1AA" if is_dark else "#6B655B"

        card_bg = "#18181C" if is_dark else "#F9F7F2"
        card_border = "#262630" if is_dark else "#E2DDD4"

        # Headers
        self.header_title.setStyleSheet(f"color: {title_fg};")
        self.header_desc.setStyleSheet(f"color: {desc_fg};")
        self.tag_pill.setStyleSheet(f"""
            QLabel#tagPill {{
                background-color: {tag_bg};
                color: {tag_fg};
                border: 1px solid {tag_border};
                border-radius: 4px;
            }}
        """)

        # Switcher Frame
        self.mode_switcher_frame.setStyleSheet(f"""
            QFrame#modeSwitcher {{
                background-color: {switcher_bg};
                border: 1px solid {switcher_border};
                border-radius: 8px;
            }}
        """)

        # Switcher Tabs
        for btn, is_active in [
            (self.faq_tab_btn, self.current_mode == "faq"),
            (self.docs_tab_btn, self.current_mode == "docs"),
        ]:
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_tab_bg};
                        color: {active_tab_fg};
                        border: 1px solid {active_tab_border};
                        border-radius: 6px;
                        padding: 5px 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {inactive_tab_fg};
                        border: none;
                        padding: 5px 14px;
                    }}
                    QPushButton:hover {{
                        color: {title_fg};
                    }}
                """)

        # FAQ Category Navigation Buttons
        cat_active_bg = "rgba(255, 107, 61, 0.12)" if is_dark else "rgba(234, 88, 12, 0.10)"
        cat_active_fg = "#FF825C" if is_dark else "#C2410C"
        cat_active_border = "rgba(255, 107, 61, 0.28)" if is_dark else "rgba(234, 88, 12, 0.25)"
        cat_hover_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.04)"

        for cat_id, btn in self.faq_cat_btns.items():
            is_active = (cat_id == self.current_faq_cat)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {cat_active_bg};
                        color: {cat_active_fg};
                        border: 1px solid {cat_active_border};
                        border-radius: 6px;
                        text-align: left;
                        padding: 7px 12px;
                        font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {inactive_tab_fg};
                        border: 1px solid transparent;
                        border-radius: 6px;
                        text-align: left;
                        padding: 7px 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {cat_hover_bg};
                        color: {title_fg};
                    }}
                """)

        # Contribute link box in FAQ nav
        link_box_bg = "#16161A" if is_dark else "#F1EBE1"
        link_box_border = "#24242C" if is_dark else "#DFD8CD"
        self.contribute_box.setStyleSheet(f"""
            QFrame#contributeBox {{
                background-color: {link_box_bg};
                border: 1px solid {link_box_border};
                border-radius: 8px;
            }}
            QLabel {{
                color: {desc_fg};
            }}
        """)
        github_fg = "#FF855D" if is_dark else "#BA3F1A"
        github_hover_fg = "#FFA07A" if is_dark else "#9E3414"
        self.github_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {github_fg};
                border: 1px solid {tag_border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: {tag_bg};
                color: {github_hover_fg};
            }}
        """)

        # FAQ Items
        for item in self.faq_items:
            item.update_theme(is_dark)

        # Docs Page Styling
        if hasattr(self, "doc_title"):
            self.doc_title.setStyleSheet(f"color: {title_fg};")
            self.doc_intro.setText(
                f"<div style='color: {desc_fg}; line-height: 1.65; font-size: 13.5px; font-family: {FONT_SANS}; margin-top: 4px; margin-bottom: 6px;'>"
                "WizDesk tracks your project work and captures quick notes from your desktop. "
                "It logs time automatically based on your active windows, stores all data locally in SQLite, "
                "and features an on-screen companion that shows your current activity."
                "</div>"
            )

            for btn in self.doc_topic_btns:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {inactive_tab_fg};
                        border: none;
                        text-align: left;
                        padding: 4px 6px;
                    }}
                    QPushButton:hover {{
                        color: {title_fg};
                    }}
                """)

            for card in self.findChildren(QFrame, "docCard"):
                card.setStyleSheet(f"""
                    QFrame#docCard {{
                        background-color: {card_bg};
                        border: 1px solid {card_border};
                        border-radius: 10px;
                    }}
                    QLabel#docCardTitle {{
                        color: {title_fg};
                    }}
                """)
                b_lbl = card.findChild(QLabel, "docCardBody")
                if b_lbl:
                    raw_body = b_lbl.property("raw_body")
                    if raw_body:
                        b_lbl.setText(self._format_doc_body_html(raw_body, desc_fg))

            for sec_lbl in self.findChildren(QLabel, "docSectionHeading"):
                sec_lbl.setStyleSheet(f"color: {'#71717A' if is_dark else '#8C8377'}; padding-top: 4px;")

        # Custom Slim Scrollbars
        scroll_thumb = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"
        scroll_thumb_hover = "#FF6B3D" if is_dark else "#EA580C"
        scrollbar_qss = f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_thumb};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_thumb_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """
        if hasattr(self, "faq_scroll"):
            self.faq_scroll.setStyleSheet(scrollbar_qss)
        if hasattr(self, "doc_scroll"):
            self.doc_scroll.setStyleSheet(scrollbar_qss)
