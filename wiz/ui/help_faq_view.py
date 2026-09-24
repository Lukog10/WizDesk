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
    Features modern typography, smooth toggle between '+' and '—',
    and refined border/background styling.
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
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(6)

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
        self.q_lbl.setFont(get_font(10, QFont.Weight.DemiBold))
        self.q_lbl.setWordWrap(True)
        header_layout.addWidget(self.q_lbl, stretch=1)

        # Sleek + / — toggle indicator
        self.indicator_lbl = QLabel("+", self.header_btn)
        self.indicator_lbl.setFont(get_font(12, QFont.Weight.Medium))
        self.indicator_lbl.setFixedWidth(16)
        self.indicator_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, expanded: bool) -> None:
        """Explicitly set expansion state."""
        self.is_expanded = expanded
        self.a_lbl.setVisible(self.is_expanded)
        self.indicator_lbl.setText("—" if self.is_expanded else "+")

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
        self.q_lbl.setStyleSheet(f"color: {q_fg}; line-height: 130%;")
        self.a_lbl.setStyleSheet(f"color: {a_fg}; padding-top: 6px; line-height: 145%;")
        self.indicator_lbl.setStyleSheet(f"color: {ind_fg};")


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

        self.header_title = QLabel("Frequently asked question", self)
        self.header_title.setFont(get_font(14, QFont.Weight.Bold))
        header_info.addWidget(self.header_title)

        self.header_desc = QLabel(
            "here's everything you need to know to get started, manage your workspace, and troubleshoot the most frequent issues.",
            self,
        )
        self.header_desc.setFont(get_font(9))
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
             "What is this platform used for?",
             "WizDesk is designed to help you organize work tasks, capture quick notes, and track focused time automatically without requiring manual start/stop clocks. Your desktop companion gently reflects your current work mood."),
            ("general",
             "How do I add tasks and log quick notes?",
             "Click '+ Add task' in the Tasks tab or press Enter after typing in the bottom bar. Quick notes can be captured instantly in the Quick Notes tab or summoned globally via your configured shortcuts."),
            ("general",
             "How do I completely exit WizDesk?",
             "Right-click the system tray icon (near the Windows clock) and choose Quit, or close the main workspace window when finished with your work session."),
            ("mascot",
             "How does autonomous work categorization work?",
             "Every 5 seconds, WizDesk checks the active foreground window title against your configured project keywords. When you switch focus (e.g. from editor to browser), the previous session automatically concludes and logs the exact duration."),
            ("mascot",
             "What are the desktop companion moods?",
             "Your companion reacts dynamically: WORKING (typing/clicking on active task with spinning eyes), IDLE (monitoring focus with cursor-tracking eyes), SLEEP (inactivity >60s), NOTIFY (transient feedback when tasks are added), and COMPLETE (celebration bounce on task completion)."),
            ("mascot",
             "How do cursor-tracking dot eyes work?",
             "In the Monitor / IDLE state, the desktop mascot's eyes smoothly track your mouse cursor coordinates across the screen in real time. When window activity is detected and tasks are actively being logged, the eyes seamlessly transition into thin, spinning circular eyes in WORKING mode."),
            ("mascot",
             "Does WizDesk have sound effects and can I customize them?",
             "Yes. WizDesk includes a built-in procedural sound engine generating 16-bit PCM WAV chimes for wake up, sleep, completion, cancellations, work logs, and mascot pokes/drags. You can toggle audio on or off and calibrate volume under Settings > General."),
            ("mascot",
             "Can I hide the desktop mascot and still track work?",
             "Yes. Toggle the companion anytime using Ctrl+Shift+M (or your customized hotkey in Settings). Window time tracking continues uninterrupted in the background."),
            ("privacy",
             "Is my data safe and private on this platform?",
             "Yes. WizDesk is built on strict zero-telemetry principles. All your task records, subtasks, notes, project allocations, and activity logs are stored strictly on your local device in a standard SQLite database. No data is ever sent to external cloud servers."),
            ("privacy",
             "Does WizDesk log my keystrokes or screen?",
             "No. WizDesk only inspects the active window title bar every 5 seconds to attribute time to projects. Keystrokes, screen recordings, and personal documents are never logged or stored."),
            ("privacy",
             "How does Database Encryption (AES-256-GCM) work?",
             "WizDesk supports hardware-backed AES-256-GCM authenticated encryption at rest. When enabled under Settings > Security, your database is decrypted into secure memory on startup and written to disk encrypted with atomic replacement. Zero unencrypted plaintext remains on disk."),
            ("privacy",
             "How do I enable encryption and what is my Personal Master Key?",
             "Navigate to Settings > Security and click 'Enable Encryption'. WizDesk generates a cryptographically secure 256-bit key and binds it to your Windows user account via Windows DPAPI for instant, zero-prompt login. You also receive an exportable master key ('WIZK-XXXX-...') which you can back up safely for disaster recovery or machine migration."),
            ("privacy",
             "Can I disable database encryption later?",
             "Yes. Click 'Disable Encryption' under Settings > Security. WizDesk safely decrypts your encrypted payload and restores it as a standard SQLite database on disk."),
            ("backup",
             "How do automated database backups work?",
             "When Automated Backups is toggled on under Settings > Security, WizDesk automatically creates a rolling snapshot of your database every day when the app starts. If encryption is enabled, backups are securely encrypted as .wbak files; otherwise they are saved as standard .bak files."),
            ("backup",
             "How do I create an immediate manual backup?",
             "Go to Settings > Security and click 'Create Backup Now'. WizDesk instantly snapshots your current database with a timestamp and 'manual' tag in your local backups directory (%APPDATA%\\WizDesk\\backups). Manual snapshots are never auto-pruned."),
            ("backup",
             "What is the backup retention limit and how does pruning work?",
             "You can set a retention limit (1 to 30 snapshots) under Settings > Security. When your automated backups exceed this number, the oldest automatic snapshots are pruned to conserve disk space. Manual and pre-restore snapshots are always preserved."),
            ("backup",
             "How do I restore my database from a backup file?",
             "Under Settings > Security, click 'Restore from File...' and select any .bak or .wbak file. WizDesk verifies SQLite integrity (PRAGMA integrity_check) and takes an automatic safety 'pre-restore' snapshot of your active database before applying the restore."),
            ("backup",
             "How do I export and migrate data to another computer?",
             "Copy your .bak or .wbak snapshot files from %APPDATA%\\WizDesk\\backups to your new device. If your backups are encrypted (.wbak), export your Personal Master Key from Settings > Security ('View / Export Key') and use it to decrypt and restore your data on the target system."),
            ("obsidian",
             "How does local Obsidian sync work?",
             "Under Settings > Integrations, configure your local Obsidian vault root folder. Whenever you complete tasks or record notes, WizDesk automatically appends them to daily markdown files in your vault."),
            ("obsidian",
             "Can I customize the daily logs subfolder?",
             "Yes. Under Settings > Integrations, you can set the daily logs subfolder name (defaults to 'WizDesk Logs'). WizDesk creates the folder automatically if it doesn't already exist."),
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
    # PAGE 2: DOCUMENTATION INTERFACE (Reference Image 2)
    # ------------------------------------------------------------------------
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
            sec_lbl = QLabel(section_title.upper(), self.docs_nav_col)
            sec_lbl.setFont(get_font(7, QFont.Weight.Bold))
            sec_lbl.setObjectName("docSectionHeading")
            doc_nav_layout.addWidget(sec_lbl)

            for topic in topics:
                t_btn = QPushButton(f"• {topic}", self.docs_nav_col)
                t_btn.setFont(get_font(8.5, QFont.Weight.Medium))
                t_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                t_btn.setAutoDefault(False)
                t_btn.setDefault(False)
                t_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                t_btn.setObjectName("docTopicBtn")
                t_btn.clicked.connect(lambda checked, t=topic: self._on_doc_topic_clicked(t))
                self.doc_topic_btns.append(t_btn)
                doc_nav_layout.addWidget(t_btn)

            doc_nav_layout.addSpacing(6)

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
        self.doc_layout.setContentsMargins(8, 4, 18, 16)
        self.doc_layout.setSpacing(14)

        # Doc Header
        self.doc_title = QLabel("Platform Guide", self.doc_content_widget)
        self.doc_title.setFont(get_font(14, QFont.Weight.Bold))
        self.doc_layout.addWidget(self.doc_title)

        self.doc_intro = QLabel(
            "WizDesk is a lightweight, local-first desktop productivity companion and autonomous time intelligence platform. "
            "It runs quietly in the background, eliminating the need for manual punch clocks and complex time-tracking setups.",
            self.doc_content_widget,
        )
        self.doc_intro.setFont(get_font(9.5))
        self.doc_intro.setWordWrap(True)
        self.doc_layout.addWidget(self.doc_intro)

        # Section 1: Autonomous Window Tracking Engine
        self.sec_tracking = self._create_doc_section(
            title="Autonomous Window Tracking Engine",
            body="Instead of requiring manual timers, WizDesk polls your active foreground window every 5 seconds. "
                 "When a foreground window matches any of your configured project keywords (e.g. 'code', 'docs', 'figma'), "
                 "time is automatically attributed to that project.\n\n"
                 "When you switch applications, the previous session is immediately concluded and written to your local database.",
        )
        self.doc_layout.addWidget(self.sec_tracking)

        # Section 2: Mascot Companion Behaviors, Eye-Tracking & Audio
        self.sec_mascot = self._create_doc_section(
            title="Desktop Companion Moods, Eye-Tracking & Sound Engine",
            body="Your companion dynamically animates based on your work state:\n\n"
                 "• WORKING: Active keyboard and mouse input while focused on recognized tasks. Mascot displays thin spinning circular eyes.\n"
                 "• IDLE: Brief pause in activity (>10 seconds). Mascot eyes smoothly follow your mouse cursor coordinates across the screen.\n"
                 "• SLEEP: Extended break (>1 minute or custom inactivity timeout). Mascot curls up to rest.\n"
                 "• NOTIFY: Transient visual feedback when new tasks or notes are logged.\n"
                 "• COMPLETE: Celebration bounce when a task is checked off.\n\n"
                 "Procedural Sound Engine: Organic 16-bit PCM WAV audio chimes trigger on state transitions (wake, sleep, complete, cancel, work log, poke/drag). Audio can be toggled and volume adjusted in Settings > General.",
        )
        self.doc_layout.addWidget(self.sec_mascot)

        # Section 3: Database Encryption (AES-256-GCM)
        self.sec_encryption = self._create_doc_section(
            title="Database Encryption (AES-256-GCM) & Key Management",
            body="Protect all tasks, subtasks, notes, project allocations, and activity logs at rest using authenticated AES-256-GCM encryption.\n\n"
                 "• In-Memory Decryption: On application launch, the database payload is decrypted into secure memory and runs with high throughput. Data is committed back to disk encrypted with atomic replacement. Zero unencrypted plaintext remains on disk.\n"
                 "• Windows DPAPI: Your 256-bit encryption key is securely stored using Windows Data Protection API, bound to your Windows user account credentials for seamless zero-prompt unlock.\n"
                 "• Personal Master Key: Export your 64-character hex master key (formatted as WIZK-XXXX-...) anytime under Settings > Security to maintain disaster recovery capability.",
        )
        self.doc_layout.addWidget(self.sec_encryption)

        # Section 4: Automated & On-Demand Backup System
        self.sec_backups = self._create_doc_section(
            title="Automated & On-Demand Backup System",
            body="Keep your workspace data safe from accidental loss with automated and manual point-in-time snapshots:\n\n"
                 "• Automated Rolling Backups: Automatically creates daily snapshots on application startup. Saved as .wbak (when encrypted) or .bak (standard SQLite).\n"
                 "• Configurable Retention Limit: Set between 1 and 30 snapshots under Settings > Security. Old automatic snapshots are pruned to conserve disk space, while manual backups are never deleted.\n"
                 "• Storage Location: Snapshots are stored locally in %APPDATA%\\WizDesk\\backups (Windows) or ~/.local/share/WizDesk/backups (Linux).",
        )
        self.doc_layout.addWidget(self.sec_backups)

        # Section 5: Data Restoration & Migration
        self.sec_restore = self._create_doc_section(
            title="Data Export, Restoration & Machine Migration",
            body="Restore or migrate your entire workspace with complete confidence:\n\n"
                 "• Pre-Restore Safety Snapshot: WizDesk automatically captures a 'pre-restore' backup of your existing database before overwriting, ensuring zero risk of accidental data loss.\n"
                 "• SQLite Integrity Validation: Every restored database undergoes rigorous validation (PRAGMA integrity_check) before being activated.\n"
                 "• Machine Migration: Copy your backup file to any computer and restore it via Settings > Security > 'Restore from File...'. For encrypted databases, provide your Personal Master Key to decrypt.",
        )
        self.doc_layout.addWidget(self.sec_restore)

        # Section 6: Privacy & Zero Telemetry Architecture
        self.sec_privacy = self._create_doc_section(
            title="Privacy & 100% Local Storage Architecture",
            body="WizDesk adheres strictly to zero-telemetry principles. All information is stored in a standard SQLite database on your device:\n\n"
                 "Windows: %APPDATA%\\WizDesk\\wizdesk.db\n"
                 "Linux: ~/.local/share/WizDesk/wizdesk.db\n\n"
                 "WizDesk has no cloud dependency, captures no analytics, and never reads personal files.",
        )
        self.doc_layout.addWidget(self.sec_privacy)

        # Section 7: Obsidian Daily Logs Sync
        self.sec_obsidian = self._create_doc_section(
            title="Obsidian Vault Daily Logs Sync",
            body="Connect your local Obsidian Vault under Settings > Integrations. "
                 "WizDesk formats completed tasks and work session durations into daily Markdown files inside your vault's logs folder.",
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
        elif topic in ("Mascot States", "Mascot States & Audio", "Sound Engine") and hasattr(self, "sec_mascot"):
            self.doc_scroll.ensureWidgetVisible(self.sec_mascot)
        elif topic == "AES-256 Encryption" and hasattr(self, "sec_encryption"):
            self.doc_scroll.ensureWidgetVisible(self.sec_encryption)
        elif topic == "Database Backups" and hasattr(self, "sec_backups"):
            self.doc_scroll.ensureWidgetVisible(self.sec_backups)
        elif topic == "Restore & Migration" and hasattr(self, "sec_restore"):
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

    def _create_doc_section(self, title: str, body: str) -> QFrame:
        """Create a styled editorial documentation card."""
        card = QFrame()
        card.setObjectName("docCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(6)

        t_lbl = QLabel(title, card)
        t_lbl.setFont(get_font(10.5, QFont.Weight.Bold))
        t_lbl.setObjectName("docCardTitle")
        c_layout.addWidget(t_lbl)

        b_lbl = QLabel(body, card)
        b_lbl.setFont(get_font(9))
        b_lbl.setWordWrap(True)
        b_lbl.setObjectName("docCardBody")
        c_layout.addWidget(b_lbl)

        return card

    # ------------------------------------------------------------------------
    # NAVIGATION & CATEGORY FILTERING
    # ------------------------------------------------------------------------
    def switch_view_mode(self, mode: str) -> None:
        """Switch between FAQs and Documentation."""
        self.current_mode = mode
        if mode == "faq":
            self.stack.setCurrentIndex(0)
            self.tag_pill.setText("/ FAQS")
            self.header_title.setText("Frequently asked question")
            self.header_desc.setText(
                "here's everything you need to know to get started, manage your workspace, and troubleshoot the most frequent issues."
            )
        else:
            self.stack.setCurrentIndex(1)
            self.tag_pill.setText("/ DOCS")
            self.header_title.setText("Platform Documentation")
            self.header_desc.setText(
                "Comprehensive architecture overview, autonomous tracking engine specifications, and local privacy guarantees."
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
            self.doc_intro.setStyleSheet(f"color: {desc_fg}; line-height: 140%;")

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
                    QLabel#docCardBody {{
                        color: {desc_fg};
                        line-height: 145%;
                    }}
                """)

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
