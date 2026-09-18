"""
Side Navigation Bar for WizDesk Widescreen Shell.
Provides persistent left navigation across Tasks, Quick Notes, Activity, Projects, and Settings.
Strictly adheres to WizDesk brand colors (#FF6B3D Mascot Orange-Red, #10B981 Emerald).
"""

from typing import Optional, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
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
)

from wiz.ui.icons import get_app_pixmap
from wiz.ui.fonts import FONT_SANS, get_font


class NavPillButton(QPushButton):
    """
    Ergonomic navigation pill button inheriting from QPushButton.
    Features integrated vector icon, text label, count badge,
    and a 3px active indicator bar.
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

        self.setFixedHeight(38)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setDefault(False)

        self.clicked.connect(lambda: self.mode_selected.emit(self.mode_id))

    def set_active(self, active: bool) -> None:
        if self.is_active != active:
            self.is_active = active
            self.update()

    def set_badge_count(self, count: int) -> None:
        if self.badge_count != count:
            self.badge_count = max(0, count)
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

        # Determine color tokens
        if self.is_active:
            bg_color = QColor(255, 107, 61, 45) if self.is_dark else QColor("#FEECE5")
            text_color = QColor("#FFAB91") if self.is_dark else QColor("#D84315")
            icon_color = QColor("#FF8E6B") if self.is_dark else QColor("#FF5722")
        elif self.is_hovered:
            bg_color = QColor(255, 255, 255, 12) if self.is_dark else QColor(0, 0, 0, 10)
            text_color = QColor("#F4F4F5") if self.is_dark else QColor("#242220")
            icon_color = QColor("#D4D4D8") if self.is_dark else QColor("#44403C")
        else:
            bg_color = Qt.GlobalColor.transparent
            text_color = QColor("#A1A1AA") if self.is_dark else QColor("#57534E")
            icon_color = QColor("#71717A") if self.is_dark else QColor("#78716C")

        # 1. Background capsule
        if bg_color != Qt.GlobalColor.transparent:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(QRectF(4, 2, w - 8, h - 4), 8, 8)

        # 2. Vector Icon (Left aligned around x=18)
        self._draw_vector_icon(painter, 18, (h - 16) // 2, 16, icon_color)

        # 4. Text Label
        painter.setPen(text_color)
        font = get_font(10, QFont.Weight.DemiBold if self.is_active else QFont.Weight.Medium)
        painter.setFont(font)

        text_x = 42
        text_w = w - text_x - (44 if self.badge_count > 0 else 10)
        text_rect = QRectF(text_x, 0, text_w, h)
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self.label,
        )

        # 5. Badge Pill (Right aligned if badge_count > 0)
        if self.badge_count > 0:
            badge_str = str(self.badge_count) if self.badge_count < 100 else "99+"
            b_font = get_font(8, QFont.Weight.Bold)
            painter.setFont(b_font)

            badge_text_w = max(18.0, float(len(badge_str) * 7 + 10))
            badge_h = 18.0
            badge_x = float(w - badge_text_w - 12)
            badge_y = float((h - badge_h) / 2)

            badge_bg = (
                QColor(255, 107, 61, 65) if self.is_dark else QColor("#FFDCCF")
            )
            badge_fg = (
                QColor("#FFCCBC") if self.is_dark else QColor("#BF360C")
            )

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(badge_bg))
            painter.drawRoundedRect(
                QRectF(badge_x, badge_y, badge_text_w, badge_h),
                9,
                9,
            )

            painter.setPen(badge_fg)
            painter.drawText(
                QRectF(badge_x, badge_y, badge_text_w, badge_h),
                int(Qt.AlignmentFlag.AlignCenter),
                badge_str,
            )

        painter.end()

    def _draw_vector_icon(
        self, painter: QPainter, x: int, y: int, size: int, color: QColor
    ) -> None:
        """Draw crisp antialiased geometric icon for each mode."""
        painter.save()
        pen = QPen(color, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.GlobalColor.transparent)

        if self.icon_type == "tasks":
            # Checklist icon: box + checkmark
            painter.drawRoundedRect(QRectF(x + 1, y + 2, 13, 12), 2.5, 2.5)
            path = QPainterPath()
            path.moveTo(x + 4.2, y + 8.0)
            path.lineTo(x + 6.8, y + 10.6)
            path.lineTo(x + 11.0, y + 5.8)
            painter.drawPath(path)

        elif self.icon_type == "notes":
            # Document/pad icon with two lines
            painter.drawRoundedRect(QRectF(x + 2, y + 1, 12, 14), 2.5, 2.5)
            painter.drawLine(int(x + 5), int(y + 6), int(x + 11), int(y + 6))
            painter.drawLine(int(x + 5), int(y + 9), int(x + 9), int(y + 9))

        elif self.icon_type == "activity":
            # Pulse / waveform line
            path = QPainterPath()
            path.moveTo(x + 1, y + 8)
            path.lineTo(x + 4.5, y + 8)
            path.lineTo(x + 6.5, y + 3.5)
            path.lineTo(x + 9.5, y + 12.5)
            path.lineTo(x + 11.5, y + 8)
            path.lineTo(x + 15, y + 8)
            painter.drawPath(path)

        elif self.icon_type == "projects":
            # 2x2 grid / dashboard blocks
            painter.drawRoundedRect(QRectF(x + 1.5, y + 1.5, 5.5, 5.5), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(x + 9.0, y + 1.5, 5.5, 5.5), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(x + 1.5, y + 9.0, 5.5, 5.5), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(x + 9.0, y + 9.0, 5.5, 5.5), 1.5, 1.5)

        elif self.icon_type == "settings":
            # Gear / sliders icon
            painter.drawEllipse(QRectF(x + 4.5, y + 4.5, 7, 7))
            painter.drawLine(int(x + 8), int(y + 1.5), int(x + 8), int(y + 4.0))
            painter.drawLine(int(x + 8), int(y + 12.0), int(x + 8), int(y + 14.5))
            painter.drawLine(int(x + 1.5), int(y + 8), int(x + 4.0), int(y + 8))
            painter.drawLine(int(x + 12.0), int(y + 8), int(x + 14.5), int(y + 8))

        elif self.icon_type == "help":
            # Circular help badge with question mark
            painter.drawEllipse(QRectF(x + 1.5, y + 1.5, 13, 13))
            path = QPainterPath()
            path.moveTo(x + 5.5, y + 6.0)
            path.quadTo(x + 8.0, y + 4.0, x + 10.0, y + 6.0)
            path.quadTo(x + 10.0, y + 8.0, x + 8.0, y + 9.5)
            painter.drawPath(path)
            painter.drawLine(int(x + 8), int(y + 11.5), int(x + 8), int(y + 12.0))

        painter.restore()


class SideNavBar(QWidget):
    """
    Dedicated Left Side Navigation Bar.
    Fixed width 190px, houses WizDesk branding with tracking status dot,
    middle navigation pills (Tasks, Notes, Activity, Projects),
    and bottom utility footer (Settings, Theme toggle).
    """

    mode_changed = pyqtSignal(str)
    theme_toggle_requested = pyqtSignal()

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.current_mode = "tasks"
        self.pills: Dict[str, NavPillButton] = {}

        self.setFixedWidth(190)
        self.setObjectName("sideNavBar")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 14, 10, 14)
        self.main_layout.setSpacing(6)

        # 1. Brand Header
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(6, 2, 6, 12)
        brand_layout.setSpacing(8)

        self.logo_lbl = QLabel()
        self.logo_lbl.setFixedSize(24, 24)
        pix = get_app_pixmap(24, "wiz-idle.svg")
        if not pix.isNull():
            self.logo_lbl.setPixmap(pix)
        brand_layout.addWidget(self.logo_lbl)

        self.brand_title = QLabel("WizDesk")
        self.brand_title.setFont(get_font(11, QFont.Weight.Bold))
        brand_layout.addWidget(self.brand_title)
        brand_layout.addStretch()

        # Status dot removed per user request (preserved hidden for backwards compatibility)
        self.status_dot = QLabel()
        self.status_dot.hide()

        self.main_layout.addLayout(brand_layout)

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
        theme_row = QHBoxLayout()
        theme_row.setContentsMargins(6, 4, 6, 0)
        theme_row.setSpacing(8)

        self.theme_btn = QPushButton()
        self.theme_btn.setFixedHeight(30)
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.setAutoDefault(False)
        self.theme_btn.setDefault(False)
        self.theme_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.theme_btn.clicked.connect(self.theme_toggle_requested.emit)
        theme_row.addWidget(self.theme_btn)

        self.main_layout.addLayout(theme_row)

        # Apply initial theme & active state
        self.set_theme(self.is_dark)
        self.set_active_mode("tasks")

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

        self.brand_title.setStyleSheet(f"color: {brand_color};")
        self.workspace_lbl.setStyleSheet(f"color: {sub_color}; padding-left: 8px; margin-bottom: 2px;")
        self.divider.setStyleSheet(f"background-color: {border_color}; border: none;")

        theme_text = "Light Mode" if is_dark else "Dark Mode"
        theme_symbol = "☀" if is_dark else "☾"
        self.theme_btn.setText(f"{theme_symbol}  {theme_text}")
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {border_color};
                border-radius: 6px;
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
                padding: 0 10px;
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
