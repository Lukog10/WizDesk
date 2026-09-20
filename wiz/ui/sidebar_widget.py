"""
Side Navigation Bar for WizDesk Widescreen Shell.
Provides persistent left navigation across Tasks, Quick Notes, Activity, Projects, and Settings.
Strictly adheres to WizDesk brand colors (#FF6B3D Mascot Orange-Red, #10B981 Emerald).
"""

from typing import Optional, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QSize
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QBrush,
    QCursor,
    QPaintEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QSpacerItem,
)

from wiz.ui.icons import get_app_pixmap, render_tinted_svg, get_status_icon
from wiz.ui.fonts import FONT_SANS, get_font


class NavPillButton(QPushButton):
    """
    Ergonomic navigation pill button inheriting from QPushButton.
    Features integrated vector icon, text label, count badge,
    and supports both expanded and collapsed icon-only modes.
    """

    mode_selected = pyqtSignal(str)

    def __init__(
        self,
        mode_id: str,
        label: str,
        icon_type: str = "tasks",
        badge_count: int = 0,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.mode_id = mode_id
        self.label = label
        self.icon_type = icon_type
        self.badge_count = badge_count
        self.is_dark = is_dark
        self.is_active = False
        self.is_hovered = False
        self.is_collapsed = False

        self.setFixedSize(170, 42)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)

        self._update_tooltip()
        self.clicked.connect(lambda: self.mode_selected.emit(self.mode_id))

    def _update_tooltip(self) -> None:
        """Update tooltip to show label and count."""
        if self.badge_count > 0:
            self.setToolTip(f"{self.label} ({self.badge_count})")
        else:
            self.setToolTip(self.label)

    def set_collapsed(self, collapsed: bool) -> None:
        """Toggle between expanded pill and collapsed icon-only state."""
        self.is_collapsed = collapsed
        if collapsed:
            self.setFixedSize(44, 42)
        else:
            self.setFixedSize(170, 42)
        self._update_tooltip()
        self.updateGeometry()
        self.update()

    def set_active(self, active: bool) -> None:
        if self.is_active != active:
            self.is_active = active
            self.update()

    def set_badge_count(self, count: int) -> None:
        if self.badge_count != count:
            self.badge_count = max(0, count)
            self._update_tooltip()
            self.update()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def enterEvent(self, event) -> None:
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        h = self.height()

        # Accent color: Thick, dense, rich deeper accent fill that blends in smoothly
        accent_color = QColor("#C2410C") if self.is_dark else QColor("#BA3F1A")

        if self.is_active:
            bg_color = accent_color
            text_color = QColor("#FFFFFF")
            icon_color = QColor("#FFFFFF")
        elif self.is_hovered:
            bg_color = QColor(255, 255, 255, 14) if self.is_dark else QColor(0, 0, 0, 10)
            text_color = QColor("#FFFFFF") if self.is_dark else QColor("#18181B")
            icon_color = QColor("#FFFFFF") if self.is_dark else QColor("#18181B")
        else:
            bg_color = Qt.GlobalColor.transparent
            text_color = QColor("#9CA3AF") if self.is_dark else QColor("#57534E")
            icon_color = QColor("#9CA3AF") if self.is_dark else QColor("#78716C")

        # 1. Background capsule (Dense, thick pill with 10px smooth radius)
        if bg_color != Qt.GlobalColor.transparent:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 10, 10)

        # 2. Vector Icon (Crisp geometric icon, centered when collapsed)
        if self.is_collapsed:
            icon_x = (w - 16) // 2
        else:
            icon_x = 16
        self._draw_vector_icon(painter, icon_x, (h - 16) // 2, 16, icon_color)

        # 3. Text Label (drawn only when expanded)
        if not self.is_collapsed:
            painter.setPen(text_color)
            font = get_font(10, QFont.Weight.Bold if self.is_active else QFont.Weight.Medium)
            painter.setFont(font)

            text_x = 42
            text_w = w - text_x - (46 if self.badge_count > 0 else 10)
            text_rect = QRectF(text_x, 0, text_w, h)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                self.label,
            )

        # 4. Badge Indicator (Pill in expanded mode, mini dot in collapsed mode)
        if self.badge_count > 0:
            if self.is_collapsed:
                # Mini dot indicator at top-right of the icon
                dot_x = float((w - 16) // 2 + 13)
                dot_y = float((h - 16) // 2 - 1)
                dot_color = QColor("#FFFFFF") if self.is_active else (QColor("#FF6B3D") if self.is_dark else QColor("#BA3F1A"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(dot_color))
                painter.drawEllipse(QRectF(dot_x, dot_y, 6.0, 6.0))
            else:
                badge_str = str(self.badge_count) if self.badge_count < 100 else "99+"
                b_font = get_font(8, QFont.Weight.Bold)
                painter.setFont(b_font)

                badge_text_w = max(20.0, float(len(badge_str) * 7 + 10))
                badge_h = 20.0
                badge_x = float(w - badge_text_w - 10)
                badge_y = float((h - badge_h) / 2)

                if self.is_active:
                    badge_bg = QColor(255, 255, 255, 65)
                    badge_fg = QColor("#FFFFFF")
                elif self.is_hovered:
                    badge_bg = QColor(255, 255, 255, 30) if self.is_dark else QColor(0, 0, 0, 22)
                    badge_fg = QColor("#FFFFFF") if self.is_dark else QColor("#18181B")
                else:
                    badge_bg = QColor(255, 255, 255, 20) if self.is_dark else QColor(0, 0, 0, 16)
                    badge_fg = QColor("#D4D4D8") if self.is_dark else QColor("#57534E")

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(badge_bg))
                painter.drawRoundedRect(
                    QRectF(badge_x, badge_y, badge_text_w, badge_h),
                    10,
                    10,
                )

                painter.setPen(badge_fg)
                painter.drawText(
                    QRectF(badge_x, badge_y, badge_text_w, badge_h),
                    int(Qt.AlignmentFlag.AlignCenter),
                    badge_str,
                )

        painter.end()

    # Mapping from icon_type to SVG asset filename
    _SVG_ICON_MAP = {
        "tasks": "icons/tasklist-24.svg",
        "notes": "icons/notes-bold.svg",
        "activity": "icons/activity-03.svg",
        "projects": "icons/dashboard-2-rounded.svg",
        "settings": "icons/settings.svg",
        "help": "icons/interface-help-question-circle-circle-faq-frame-help-info-mark-more-query-question.svg",
    }

    def _draw_vector_icon(
        self, painter: QPainter, x: int, y: int, size: int, color: QColor
    ) -> None:
        """Draw crisp icon for each mode using SVG assets."""
        svg_name = self._SVG_ICON_MAP.get(self.icon_type)
        if svg_name:
            # Render tinted SVG asset with 2px padding for visual balance
            render_tinted_svg(
                painter, svg_name, color.name(), float(x + 1), float(y + 1), float(size - 2)
            )


class SidebarToggleButton(QPushButton):
    """Clean icon button using side-bar-fill.svg to collapse and expand the sidebar."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.is_collapsed = False
        self.setFixedSize(28, 28)
        self.setIconSize(QSize(16, 16))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setToolTip("Collapse sidebar")
        self.update_style()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update_style()

    def set_collapsed(self, collapsed: bool) -> None:
        self.is_collapsed = collapsed
        self.setToolTip("Expand sidebar" if collapsed else "Collapse sidebar")
        self.update_style()

    def update_style(self, hover: bool = False) -> None:
        normal_fg = "#9CA3AF" if self.is_dark else "#78716C"
        hover_fg = "#FAFAFA" if self.is_dark else "#18181B"
        hover_bg = "#27272A" if self.is_dark else "#DAD5CB"
        c = hover_fg if hover else normal_fg
        self.setIcon(get_status_icon("icons/side-bar-fill.svg", c, 16))
        self.setIconSize(QSize(16, 16))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
        """)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.update_style(hover=True)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.update_style(hover=False)


class SideNavBar(QWidget):
    """
    Dedicated Left Side Navigation Bar.
    Supports full width 190px (expanded) and compact 58px (collapsed icon-only),
    houses WizDesk branding, sidebar toggle button, navigation pills (Tasks, Notes, Activity, Projects),
    and bottom utility footer (Settings, Help & FAQ, Theme toggle).
    """

    mode_changed = pyqtSignal(str)
    theme_toggle_requested = pyqtSignal()
    sidebar_toggled = pyqtSignal(bool)  # emits is_collapsed

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.is_collapsed = False
        self.current_mode = "tasks"
        self.pills: Dict[str, NavPillButton] = {}

        self.setFixedWidth(190)
        self.setObjectName("sideNavBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 14, 10, 14)
        self.main_layout.setSpacing(6)

        # 1. Brand Header & Collapse Toggle
        self.brand_layout = QHBoxLayout()
        self.brand_layout.setContentsMargins(4, 2, 4, 12)
        self.brand_layout.setSpacing(6)

        self.brand_container = QWidget()
        brand_c_layout = QHBoxLayout(self.brand_container)
        brand_c_layout.setContentsMargins(0, 0, 0, 0)
        brand_c_layout.setSpacing(8)

        self.logo_lbl = QLabel()
        self.logo_lbl.setFixedSize(24, 24)
        pix = get_app_pixmap(24, "wiz-idle.svg")
        if not pix.isNull():
            self.logo_lbl.setPixmap(pix)
        brand_c_layout.addWidget(self.logo_lbl)

        self.brand_title = QLabel("WizDesk")
        self.brand_title.setFont(get_font(11, QFont.Weight.Bold))
        brand_c_layout.addWidget(self.brand_title)

        self.brand_layout.addWidget(self.brand_container)

        self.header_spacer_left = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.brand_layout.addItem(self.header_spacer_left)

        self.toggle_btn = SidebarToggleButton(is_dark=self.is_dark, parent=self)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.brand_layout.addWidget(self.toggle_btn)

        self.header_spacer_right = QSpacerItem(0, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.brand_layout.addItem(self.header_spacer_right)

        # Status dot removed per user request (preserved hidden for backwards compatibility)
        self.status_dot = QLabel()
        self.status_dot.hide()

        self.main_layout.addLayout(self.brand_layout)

        # 2. Section Header: Workspace
        self.workspace_lbl = QLabel("WORKSPACE")
        self.workspace_lbl.setFont(get_font(8, QFont.Weight.Bold))
        self.workspace_lbl.setStyleSheet("padding-left: 8px; margin-bottom: 2px;")
        self.main_layout.addWidget(self.workspace_lbl)

        # 3. Main Navigation Pills
        nav_defs = [
            ("tasks", "Tasks", "tasks"),
            ("notes", "Quick Notes", "notes"),
            ("activity", "Activity", "activity"),
            ("projects", "Projects", "projects"),
        ]

        for m_id, label, icon_type in nav_defs:
            pill = NavPillButton(
                mode_id=m_id,
                label=label,
                icon_type=icon_type,
                is_dark=self.is_dark,
                parent=self,
            )
            pill.mode_selected.connect(self._on_pill_selected)
            self.pills[m_id] = pill
            self.main_layout.addWidget(pill)

        # Vertical stretch to push settings and theme toggle to bottom
        self.main_layout.addStretch()

        # 4. Divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFixedHeight(1)
        self.main_layout.addWidget(self.divider)

        # 5. Utility Pills (Settings, Help & FAQ)
        self.settings_pill = NavPillButton(
            mode_id="settings",
            label="Settings",
            icon_type="settings",
            is_dark=self.is_dark,
            parent=self,
        )
        self.settings_pill.mode_selected.connect(self._on_pill_selected)
        self.pills["settings"] = self.settings_pill
        self.main_layout.addWidget(self.settings_pill)

        self.help_pill = NavPillButton(
            mode_id="help",
            label="Help & FAQ",
            icon_type="help",
            is_dark=self.is_dark,
            parent=self,
        )
        self.help_pill.mode_selected.connect(self._on_pill_selected)
        self.pills["help"] = self.help_pill
        self.main_layout.addWidget(self.help_pill)

        # 6. Theme Toggle Row
        self.theme_row = QHBoxLayout()
        self.theme_row.setContentsMargins(6, 4, 6, 0)
        self.theme_row.setSpacing(8)

        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(170, 30)
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.setAutoDefault(False)
        self.theme_btn.setDefault(False)
        self.theme_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.theme_btn.clicked.connect(self.theme_toggle_requested.emit)
        self.theme_row.addWidget(self.theme_btn)

        self.main_layout.addLayout(self.theme_row)

        # Apply initial theme & active state
        self.set_theme(self.is_dark)
        self.set_active_mode("tasks")

    def toggle_sidebar(self) -> None:
        """Toggle between expanded and collapsed sidebar."""
        self.set_collapsed(not self.is_collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Set collapsed state.

        Wraps all child-widget mutations in setUpdatesEnabled(False/True) so
        that Qt does not paint any intermediate partially-changed layout frame
        (e.g. sidebar width already 58 px but pills still 170 px wide).
        Without this guard, DWM composites each partial frame and the user
        sees a brief but visible flash of mismatched geometry ("glitch").
        """
        # Suppress intermediate paints while we batch-modify child sizes
        self.setUpdatesEnabled(False)

        self.is_collapsed = collapsed
        if self.is_collapsed:
            self.setFixedWidth(58)
            self.main_layout.setContentsMargins(7, 14, 7, 14)
            self.brand_container.hide()
            self.workspace_lbl.hide()
            self.brand_layout.setContentsMargins(0, 2, 0, 12)
            self.header_spacer_right.changeSize(1, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.toggle_btn.set_collapsed(True)
            self.theme_row.setContentsMargins(0, 4, 0, 0)
            self.theme_btn.setFixedSize(44, 30)
            theme_symbol = "☀" if self.is_dark else "☾"
            self.theme_btn.setText(theme_symbol)
            self.theme_btn.setToolTip("Switch to Light Mode" if self.is_dark else "Switch to Dark Mode")
        else:
            self.setFixedWidth(190)
            self.main_layout.setContentsMargins(10, 14, 10, 14)
            self.brand_container.show()
            self.workspace_lbl.show()
            self.brand_layout.setContentsMargins(4, 2, 4, 12)
            self.header_spacer_right.changeSize(0, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            self.toggle_btn.set_collapsed(False)
            self.theme_row.setContentsMargins(6, 4, 6, 0)
            self.theme_btn.setFixedSize(170, 30)
            theme_text = "Light Mode" if self.is_dark else "Dark Mode"
            theme_symbol = "☀" if self.is_dark else "☾"
            self.theme_btn.setText(f"{theme_symbol}  {theme_text}")
            self.theme_btn.setToolTip("")

        self.brand_layout.invalidate()

        for pill in self.pills.values():
            pill.set_collapsed(self.is_collapsed)

        self.main_layout.activate()
        self.updateGeometry()

        # Re-enable updates and force a single, synchronous repaint of the
        # fully-consistent final state (repaint is synchronous; update is not).
        self.setUpdatesEnabled(True)
        self.repaint()
        self.sidebar_toggled.emit(self.is_collapsed)

    def _on_pill_selected(self, mode: str) -> None:
        self.set_active_mode(mode)
        self.mode_changed.emit(mode)

    def set_active_mode(self, mode: str) -> None:
        self.current_mode = mode
        for m_id, pill in self.pills.items():
            pill.set_active(m_id == mode)

    def set_tasks_badge(self, count: int) -> None:
        if "tasks" in self.pills:
            self.pills["tasks"].set_badge_count(count)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark

        # Theme color variables - Softer Light Mode & Calibrated Warm Neutrals
        bg_color = "#16161A" if is_dark else "#E2DDD4"
        brand_color = "#F4F4F5" if is_dark else "#242220"
        sub_color = "#71717A" if is_dark else "#78716C"
        border_color = "#232328" if is_dark else "#D6D0C5"
        btn_bg = "#232328" if is_dark else "#DAD5CB"
        btn_fg = "#D4D4D8" if is_dark else "#44403C"
        btn_hover = "#2D2D34" if is_dark else "#D0CAC0"

        self.setStyleSheet(f"""
            QWidget#sideNavBar {{
                background-color: {bg_color};
                border-right: 1px solid {border_color};
                border-top-left-radius: 18px;
                border-bottom-left-radius: 18px;
            }}
        """)

        self.logo_lbl.setStyleSheet("background: transparent;")
        self.brand_title.setStyleSheet(f"color: {brand_color}; background: transparent;")
        self.workspace_lbl.setStyleSheet(f"color: {sub_color}; background: transparent; padding-left: 8px; margin-bottom: 2px;")
        self.divider.setStyleSheet(f"background-color: {border_color}; border: none;")

        self.toggle_btn.set_theme(is_dark)

        theme_text = "Light Mode" if is_dark else "Dark Mode"
        theme_symbol = "☀" if is_dark else "☾"
        if self.is_collapsed:
            self.theme_btn.setFixedSize(44, 30)
            self.theme_btn.setText(theme_symbol)
            self.theme_btn.setToolTip(f"Switch to {theme_text}")
        else:
            self.theme_btn.setFixedSize(170, 30)
            self.theme_btn.setText(f"{theme_symbol}  {theme_text}")
            self.theme_btn.setToolTip("")

        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {border_color};
                border-radius: 6px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
                padding: 0 4px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: {brand_color};
            }}
        """)

        # Propagate to pills
        for pill in self.pills.values():
            pill.set_theme(is_dark)
