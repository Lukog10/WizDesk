"""
High-performance, antialiased custom vector chart widgets for WizDesk visual analytics.
Rendered purely via PyQt6 QPainter:
1. ProjectComparisonChartWidget: Dual-mode (Bar Chart & Line/Area Chart) comparing project hours over time.
2. AppUsageAnalyticsWidget: Dual-mode (Concentric Ring Gauge & Horizontal Bar Chart) visualizing app hours.
3. KpiStatCard: Executive metric card with hero accent and change indicators.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPen,
    QBrush,
    QPainterPath,
    QLinearGradient,
    QCursor,
    QMouseEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QProgressBar,
    QSizePolicy,
)

FONT_SANS = "'Inter', 'Segoe UI', -apple-system, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Consolas', monospace"


class KpiStatCard(QFrame):
    """Executive KPI card with large numerical value, title, and percentage change indicator."""

    def __init__(
        self,
        title: str,
        value: str,
        change_text: str = "",
        is_hero: bool = False,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title_text = title
        self.value_text = value
        self.change_text = change_text
        self.is_hero = is_hero
        self.is_dark = is_dark
        self.setObjectName("KpiHeroCard" if self.is_hero else "KpiStatCard")

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(78)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Top row: Title and Change Badge
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()

        self.lbl_change = QLabel(change_text)
        self.lbl_change.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        self.lbl_change.setVisible(bool(change_text))
        top_row.addWidget(self.lbl_change)

        layout.addLayout(top_row)

        # Value row
        self.lbl_value = QLabel(value)
        self.lbl_value.setFont(QFont("Inter", 19, QFont.Weight.Bold))
        layout.addWidget(self.lbl_value)
        layout.addStretch()

        self.apply_theme()

    def update_data(self, value: str, change_text: str = "") -> None:
        self.value_text = value
        self.change_text = change_text
        self.lbl_value.setText(value)
        self.lbl_change.setText(change_text)
        self.lbl_change.setVisible(bool(change_text))

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.apply_theme()

    def apply_theme(self) -> None:
        if self.is_hero:
            self.setStyleSheet("""
                QFrame#KpiHeroCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #4338CA);
                    border: 1px solid #6366F1;
                    border-radius: 12px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            self.lbl_title.setStyleSheet("color: rgba(255, 255, 255, 0.85); border: none; background: transparent;")
            self.lbl_value.setStyleSheet("color: #FFFFFF; font-size: 22px; font-weight: bold; border: none; background: transparent;")
            self.lbl_change.setStyleSheet("""
                background-color: rgba(255, 255, 255, 0.2);
                color: #FFFFFF;
                border: none;
                border-radius: 9px;
                padding: 2px 8px;
            """)
        else:
            if self.is_dark:
                bg = "#242427"
                border = "#333338"
                text_color = "#F4F4F6"
                sub_color = "#A1A1AA"
                badge_bg = "#2A2A2E"
                badge_color = "#10B981" if "+" in self.change_text else ("#F43F5E" if "-" in self.change_text else "#A1A1AA")
            else:
                bg = "#FFFFFF"
                border = "#E5E0D8"
                text_color = "#111111"
                sub_color = "#71717A"
                badge_bg = "#F4F4F5"
                badge_color = "#059669" if "+" in self.change_text else ("#E11D48" if "-" in self.change_text else "#71717A")

            self.setStyleSheet(f"""
                QFrame#KpiStatCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 12px;
                }}
                QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
            self.lbl_title.setStyleSheet(f"color: {sub_color}; border: none; background: transparent;")
            self.lbl_value.setStyleSheet(f"color: {text_color}; border: none; background: transparent; font-size: 20px;")
            self.lbl_change.setStyleSheet(f"""
                background-color: {badge_bg};
                color: {badge_color};
                border: 1px solid {border};
                border-radius: 9px;
                padding: 2px 8px;
            """)


class ProjectComparisonCanvas(QWidget):
    """Custom QPainter canvas rendering vertical bar or smooth bezier spline area charts."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.chart_mode = "bar"  # 'bar' or 'area'
        self.series: List[Dict[str, Any]] = []
        self.bucket_labels: List[str] = []
        self.hover_bucket_idx: Optional[int] = None
        self.hover_pos: Optional[QPoint] = None

        self.setMouseTracking(True)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, series: List[Dict[str, Any]], bucket_labels: List[str]) -> None:
        self.series = series
        self.bucket_labels = bucket_labels
        self.hover_bucket_idx = None
        self.update()

    def set_chart_mode(self, mode: str) -> None:
        self.chart_mode = mode
        self.update()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.bucket_labels:
            self.hover_bucket_idx = None
            self.hover_pos = None
            self.update()
            return

        x = event.position().x()
        margin_left = 34.0
        margin_right = 14.0
        plot_w = max(1.0, self.width() - margin_left - margin_right)
        num_b = len(self.bucket_labels)
        b_width = plot_w / num_b

        if margin_left <= x <= self.width() - margin_right:
            idx = int((x - margin_left) / b_width)
            self.hover_bucket_idx = max(0, min(num_b - 1, idx))
            self.hover_pos = event.position().toPoint()
        else:
            self.hover_bucket_idx = None
            self.hover_pos = None

        self.update()

    def leaveEvent(self, event) -> None:
        self.hover_bucket_idx = None
        self.hover_pos = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        margin_left = 34.0
        margin_right = 14.0
        margin_top = 18.0
        margin_bottom = 20.0

        plot_w = max(10.0, w - margin_left - margin_right)
        plot_h = max(10.0, h - margin_top - margin_bottom)

        grid_color = QColor("#333338" if self.is_dark else "#E5E0D8")
        text_color = QColor("#71717A" if self.is_dark else "#A1A1AA")

        # 1. Determine maximum hours across all series
        max_val = 0.5
        for s in self.series:
            for val in s.get("hours", []):
                if val > max_val:
                    max_val = val

        # Round max_val up to clean increment (1, 2, 4, 8, 12, etc.)
        if max_val <= 1.0:
            y_max = 1.0
            ticks = [0.0, 0.5, 1.0]
        elif max_val <= 3.0:
            y_max = 3.0
            ticks = [0.0, 1.0, 2.0, 3.0]
        elif max_val <= 6.0:
            y_max = 6.0
            ticks = [0.0, 2.0, 4.0, 6.0]
        elif max_val <= 12.0:
            y_max = 12.0
            ticks = [0.0, 4.0, 8.0, 12.0]
        else:
            y_max = math.ceil(max_val / 5.0) * 5.0
            ticks = [0.0, round(y_max * 0.33, 1), round(y_max * 0.66, 1), y_max]

        # 2. Draw horizontal grid lines & Y-axis labels
        painter.setFont(QFont("Inter", 8, QFont.Weight.Medium))
        for tick in ticks:
            y = margin_top + plot_h - (tick / y_max * plot_h)
            # Dashed gridline
            pen = QPen(grid_color, 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(QPointF(margin_left, y), QPointF(margin_left + plot_w, y))

            # Label
            painter.setPen(text_color)
            tick_str = f"{int(tick)}h" if tick == int(tick) else f"{tick}h"
            painter.drawText(QRectF(0, y - 8, margin_left - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, tick_str)

        num_b = len(self.bucket_labels) if self.bucket_labels else 1
        b_width = plot_w / num_b

        # 3. Draw X-axis Labels
        for i, label in enumerate(self.bucket_labels):
            bx = margin_left + i * b_width
            rect = QRectF(bx, margin_top + plot_h + 4, b_width, 18)
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # 4. Render Data (Bar Mode or Area Mode)
        if self.series and num_b > 0:
            active_series = [s for s in self.series if sum(s.get("hours", [])) > 0]
            if not active_series:
                active_series = self.series[:1]  # Draw baseline if empty

            if self.chart_mode == "bar":
                # Render vertical grouped bars
                num_s = len(active_series)
                bar_gap = 2.0
                total_bar_w = min(b_width * 0.72, num_s * 14.0)
                individual_w = max(4.0, (total_bar_w - (num_s - 1) * bar_gap) / num_s)

                for b_idx in range(num_b):
                    center_x = margin_left + (b_idx + 0.5) * b_width
                    start_x = center_x - (total_bar_w / 2.0)

                    # Highlight background if hovered
                    if self.hover_bucket_idx == b_idx:
                        h_bg = QColor(255, 255, 255, 12 if self.is_dark else 20)
                        painter.fillRect(QRectF(margin_left + b_idx * b_width, margin_top, b_width, plot_h), h_bg)

                    for s_idx, s in enumerate(active_series):
                        hours_list = s.get("hours", [])
                        val = hours_list[b_idx] if b_idx < len(hours_list) else 0.0
                        bar_h = max(2.0, (val / y_max) * plot_h) if val > 0 else 0.0

                        bx = start_x + s_idx * (individual_w + bar_gap)
                        by = margin_top + plot_h - bar_h

                        bar_color = QColor(s.get("color", "#6366F1"))
                        if val > 0:
                            path = QPainterPath()
                            radius = min(4.0, individual_w / 2.0)
                            path.addRoundedRect(QRectF(bx, by, individual_w, bar_h), radius, radius)
                            painter.fillPath(path, bar_color)
            else:
                # Area / Line Mode: Smooth Bezier Splines
                for s in reversed(active_series):
                    color = QColor(s.get("color", "#6366F1"))
                    hours_list = s.get("hours", [])

                    points: List[QPointF] = []
                    for b_idx in range(num_b):
                        val = hours_list[b_idx] if b_idx < len(hours_list) else 0.0
                        px = margin_left + (b_idx + 0.5) * b_width
                        py = margin_top + plot_h - ((val / y_max) * plot_h)
                        points.append(QPointF(px, py))

                    if len(points) >= 2:
                        path = QPainterPath()
                        path.moveTo(points[0])

                        # Cubic bezier interpolation
                        for i in range(len(points) - 1):
                            p0 = points[i]
                            p1 = points[i + 1]
                            ctrl1 = QPointF(p0.x() + (p1.x() - p0.x()) / 2.0, p0.y())
                            ctrl2 = QPointF(p0.x() + (p1.x() - p0.x()) / 2.0, p1.y())
                            path.cubicTo(ctrl1, ctrl2, p1)

                        # Draw translucent gradient area
                        area_path = QPainterPath(path)
                        area_path.lineTo(points[-1].x(), margin_top + plot_h)
                        area_path.lineTo(points[0].x(), margin_top + plot_h)
                        area_path.closeSubpath()

                        gradient = QLinearGradient(0, margin_top, 0, margin_top + plot_h)
                        grad_color_top = QColor(color)
                        grad_color_top.setAlpha(80 if self.is_dark else 70)
                        grad_color_bot = QColor(color)
                        grad_color_bot.setAlpha(6)
                        gradient.setColorAt(0.0, grad_color_top)
                        gradient.setColorAt(1.0, grad_color_bot)

                        painter.fillPath(area_path, gradient)

                        # Draw the line curve
                        pen = QPen(color, 2.5)
                        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                        painter.strokePath(path, pen)

                        # Draw vertices
                        for pt in points:
                            painter.setBrush(QColor("#FFFFFF" if not self.is_dark else "#18181B"))
                            painter.setPen(QPen(color, 2.0))
                            painter.drawEllipse(pt, 3.5, 3.5)

        # 5. Render Hover Tooltip
        if self.hover_bucket_idx is not None and self.hover_bucket_idx < len(self.bucket_labels) and self.hover_pos:
            b_name = self.bucket_labels[self.hover_bucket_idx]
            lines = [f"{b_name}"]
            for s in self.series:
                h_list = s.get("hours", [])
                h_val = h_list[self.hover_bucket_idx] if self.hover_bucket_idx < len(h_list) else 0.0
                if h_val > 0 or len(self.series) <= 3:
                    lines.append(f"{s['name']}: {h_val}h")

            if len(lines) > 1:
                painter.setFont(QFont("Inter", 9, QFont.Weight.Medium))
                fm = painter.fontMetrics()
                tip_w = max(fm.horizontalAdvance(line) for line in lines) + 20
                tip_h = len(lines) * 16 + 10

                tip_x = min(w - tip_w - 10, max(10, self.hover_pos.x() - tip_w // 2))
                tip_y = max(6, self.hover_pos.y() - tip_h - 12)

                tip_rect = QRectF(tip_x, tip_y, tip_w, tip_h)
                tip_bg = QColor("#18181B" if self.is_dark else "#FFFFFF")
                tip_border = QColor("#3F3F46" if self.is_dark else "#D4D4D8")

                path = QPainterPath()
                path.addRoundedRect(tip_rect, 6, 6)
                painter.fillPath(path, tip_bg)
                painter.strokePath(path, QPen(tip_border, 1))

                painter.setPen(QColor("#FAFAFA" if self.is_dark else "#18181B"))
                for idx, line in enumerate(lines):
                    ly = tip_y + 8 + idx * 16
                    if idx == 0:
                        painter.setFont(QFont("Inter", 9, QFont.Weight.Bold))
                    else:
                        painter.setFont(QFont("Inter", 8, QFont.Weight.Normal))
                    painter.drawText(QRectF(tip_x + 10, ly - 6, tip_w - 20, 16), Qt.AlignmentFlag.AlignLeft, line)


class ProjectComparisonChartWidget(QFrame):
    """Card containing ProjectComparisonCanvas, title, Bar/Area toggle, and color legend."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setObjectName("ChartCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(8)

        # Header Row: Title and Mode Switcher
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.lbl_title = QLabel("Project Comparison")
        self.lbl_title.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        header_row.addWidget(self.lbl_title)
        header_row.addStretch()

        # Bar vs Area toggle buttons
        self.capsule = QFrame()
        self.capsule.setObjectName("ToggleCapsule")
        capsule_layout = QHBoxLayout(self.capsule)
        capsule_layout.setContentsMargins(2, 2, 2, 2)
        capsule_layout.setSpacing(2)

        self.btn_bar = QPushButton("Bar")
        self.btn_bar.setFixedHeight(22)
        self.btn_bar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_bar.clicked.connect(lambda: self._set_mode("bar"))
        capsule_layout.addWidget(self.btn_bar)

        self.btn_area = QPushButton("Area")
        self.btn_area.setFixedHeight(22)
        self.btn_area.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_area.clicked.connect(lambda: self._set_mode("area"))
        capsule_layout.addWidget(self.btn_area)

        header_row.addWidget(self.capsule)
        layout.addLayout(header_row)

        # Canvas
        self.canvas = ProjectComparisonCanvas(is_dark=self.is_dark, parent=self)
        layout.addWidget(self.canvas)

        # Legend Row
        self.legend_layout = QHBoxLayout()
        self.legend_layout.setSpacing(10)
        layout.addLayout(self.legend_layout)

        self.apply_theme()
        self._update_toggle_styles()

    def set_data(self, series: List[Dict[str, Any]], bucket_labels: List[str]) -> None:
        self.canvas.set_data(series, bucket_labels)
        self._render_legend(series)

    def _set_mode(self, mode: str) -> None:
        self.canvas.set_chart_mode(mode)
        self._update_toggle_styles()

    def _render_legend(self, series: List[Dict[str, Any]]) -> None:
        # Clear existing legend
        while self.legend_layout.count() > 0:
            item = self.legend_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        for s in series[:5]:
            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {s.get('color', '#6366F1')}; border-radius: 4px;")
            self.legend_layout.addWidget(dot)

            name_lbl = QLabel(f"{s['name']} ({s.get('total_hours', 0)}h)")
            name_lbl.setFont(QFont("Inter", 9, QFont.Weight.Medium))
            name_lbl.setStyleSheet("color: #A1A1AA;" if self.is_dark else "color: #71717A;")
            self.legend_layout.addWidget(name_lbl)
            self.legend_layout.addSpacing(6)

        self.legend_layout.addStretch()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.canvas.set_theme(is_dark)
        self.apply_theme()
        self._update_toggle_styles()

    def _update_toggle_styles(self) -> None:
        mode = self.canvas.chart_mode
        active_bg = "#18181B" if self.is_dark else "#FFFFFF"
        active_color = "#F4F4F6" if self.is_dark else "#18181B"
        inactive_color = "#A1A1AA" if self.is_dark else "#71717A"

        btn_base = f"""
            QPushButton {{
                border: none;
                border-radius: 5px;
                font-family: {FONT_SANS};
                font-size: 10px;
                font-weight: 600;
                padding: 0 8px;
            }}
        """
        self.btn_bar.setStyleSheet(btn_base + (f"background-color: {active_bg}; color: {active_color};" if mode == "bar" else f"background: transparent; color: {inactive_color};"))
        self.btn_area.setStyleSheet(btn_base + (f"background-color: {active_bg}; color: {active_color};" if mode == "area" else f"background: transparent; color: {inactive_color};"))

    def apply_theme(self) -> None:
        bg = "#242427" if self.is_dark else "#FFFFFF"
        border = "#333338" if self.is_dark else "#E5E0D8"
        capsule_bg = "#1E1E22" if self.is_dark else "#ECECF0"
        title_color = "#F4F4F6" if self.is_dark else "#111111"

        self.setStyleSheet(f"""
            QFrame#ChartCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame#ToggleCapsule {{
                background-color: {capsule_bg};
                border-radius: 6px;
            }}
            QLabel {{
                color: {title_color};
            }}
        """)


class AppUsageRingCanvas(QWidget):
    """Custom QPainter canvas rendering multi-arc concentric rings matching the reference image."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.apps_data: List[Dict[str, Any]] = []
        self.total_hours: float = 0.0

        self.setFixedSize(140, 140)

    def set_data(self, apps_data: List[Dict[str, Any]], total_hours: float) -> None:
        self.apps_data = apps_data
        self.total_hours = total_hours
        self.update()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        base_radius = min(cx, cy) - 10.0
        ring_thickness = 7.0
        ring_gap = 5.0

        top_apps = self.apps_data[:3]
        track_color = QColor("#333338" if self.is_dark else "#ECECF0")

        # 1. Draw concentric arcs for up to top 3 applications
        for idx, app in enumerate(top_apps):
            r = base_radius - idx * (ring_thickness + ring_gap)
            if r <= 8:
                break

            arc_rect = QRectF(cx - r, cy - r, r * 2, r * 2)

            # Draw background track
            track_pen = QPen(track_color, ring_thickness, Qt.PenStyle.SolidLine)
            track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(track_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(arc_rect, 225 * 16, -270 * 16)

            # Draw colored active percentage arc
            pct = min(100.0, max(0.0, app.get("percentage", 0.0)))
            active_span = int(- (pct / 100.0) * 270.0 * 16.0)
            if active_span != 0:
                app_color = QColor(app.get("color", "#3B82F6"))
                active_pen = QPen(app_color, ring_thickness, Qt.PenStyle.SolidLine)
                active_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(active_pen)
                painter.drawArc(arc_rect, 225 * 16, active_span)

        # 2. Draw Center Text (Total Hours)
        hours_str = f"{self.total_hours}h"
        painter.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
        text_rect = QRectF(cx - 50, cy - 14, 100, 20)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, hours_str)

        painter.setFont(QFont("Inter", 8, QFont.Weight.Medium))
        painter.setPen(QColor("#71717A" if self.is_dark else "#A1A1AA"))
        sub_rect = QRectF(cx - 50, cy + 6, 100, 16)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, "Total Tracked")


class AppUsageAnalyticsWidget(QFrame):
    """
    Application Statistics card supporting both:
    1. Ring / Radial Gauge Mode (Concentric arcs like reference image).
    2. Horizontal Comparative Bar Chart Mode (Hours per app with percentage bars).
    """

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.active_mode = "ring"  # 'ring' or 'bar'
        self.apps_data: List[Dict[str, Any]] = []
        self.setObjectName("AppUsageCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Row: Title & Toggle
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self.lbl_title = QLabel("App Statistics")
        self.lbl_title.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        header_row.addWidget(self.lbl_title)
        header_row.addStretch()

        # Capsule Switcher: Ring vs Bar
        self.capsule = QFrame()
        self.capsule.setObjectName("ToggleCapsule")
        capsule_layout = QHBoxLayout(self.capsule)
        capsule_layout.setContentsMargins(2, 2, 2, 2)
        capsule_layout.setSpacing(2)

        self.btn_ring = QPushButton("Ring")
        self.btn_ring.setFixedHeight(22)
        self.btn_ring.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ring.clicked.connect(lambda: self._set_mode("ring"))
        capsule_layout.addWidget(self.btn_ring)

        self.btn_bar = QPushButton("Bar")
        self.btn_bar.setFixedHeight(22)
        self.btn_bar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_bar.clicked.connect(lambda: self._set_mode("bar"))
        capsule_layout.addWidget(self.btn_bar)

        header_row.addWidget(self.capsule)
        layout.addLayout(header_row)

        # Stacked Views (Ring vs Bar)
        self.stack = QStackedWidget(self)

        # 1. Ring View Container (Side-by-side: Ring Gauge on left, Ranked Breakdown on right)
        self.ring_page = QWidget()
        self.ring_page.setMinimumHeight(150)
        ring_page_layout = QHBoxLayout(self.ring_page)
        ring_page_layout.setContentsMargins(0, 4, 0, 4)
        ring_page_layout.setSpacing(16)

        self.ring_canvas = AppUsageRingCanvas(is_dark=self.is_dark, parent=self.ring_page)
        ring_page_layout.addWidget(self.ring_canvas)

        self.ring_list_layout = QVBoxLayout()
        self.ring_list_layout.setContentsMargins(0, 0, 0, 0)
        self.ring_list_layout.setSpacing(8)
        self.ring_list_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        ring_page_layout.addLayout(self.ring_list_layout, 1)

        self.stack.addWidget(self.ring_page)

        # 2. Bar View Container
        self.bar_page = QWidget()
        self.bar_page_layout = QVBoxLayout(self.bar_page)
        self.bar_page_layout.setContentsMargins(0, 4, 0, 0)
        self.bar_page_layout.setSpacing(8)
        self.stack.addWidget(self.bar_page)

        layout.addWidget(self.stack)

        self.apply_theme()
        self._update_toggle_styles()

    def set_data(self, apps_data: List[Dict[str, Any]], total_hours: float) -> None:
        self.apps_data = apps_data
        self.ring_canvas.set_data(apps_data, total_hours)
        self._render_ring_app_list(apps_data)
        self._render_bar_app_list(apps_data)

    def _set_mode(self, mode: str) -> None:
        self.active_mode = mode
        if mode == "ring":
            self.stack.setCurrentWidget(self.ring_page)
        else:
            self.stack.setCurrentWidget(self.bar_page)
        self._update_toggle_styles()

    def _render_ring_app_list(self, apps: List[Dict[str, Any]]) -> None:
        # Clear list
        while self.ring_list_layout.count() > 0:
            item = self.ring_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not apps:
            empty = QLabel("No application activity recorded.")
            empty.setFont(QFont("Inter", 10))
            empty.setStyleSheet("color: #71717A; padding: 12px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ring_list_layout.addWidget(empty)
            return

        for app in apps[:4]:
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(6)

            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {app.get('color', '#3B82F6')}; border-radius: 4px;")
            row.addWidget(dot)

            name_lbl = QLabel(app["app_name"])
            name_lbl.setFont(QFont("Inter", 10, QFont.Weight.Medium))
            row.addWidget(name_lbl, 1)

            hours_lbl = QLabel(f"{app.get('hours', 0.0)}h")
            hours_lbl.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
            hours_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(hours_lbl)

            pct_lbl = QLabel(f"+{app.get('percentage', 0)}%" if app.get('percentage', 0) > 0 else "0%")
            pct_lbl.setFont(QFont("Inter", 9, QFont.Weight.Medium))
            pct_bg = "#2A2A2E" if self.is_dark else "#F4F4F5"
            pct_color = "#10B981" if self.is_dark else "#059669"
            pct_lbl.setStyleSheet(f"background-color: {pct_bg}; color: {pct_color}; border-radius: 6px; padding: 2px 6px;")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(pct_lbl)

            self.ring_list_layout.addWidget(row_widget)

    def _render_bar_app_list(self, apps: List[Dict[str, Any]]) -> None:
        # Clear bar layout
        while self.bar_page_layout.count() > 0:
            item = self.bar_page_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not apps:
            empty = QLabel("No application activity recorded.")
            empty.setFont(QFont("Inter", 10))
            empty.setStyleSheet("color: #71717A; padding: 20px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bar_page_layout.addWidget(empty)
            return

        for app in apps[:5]:
            item_frame = QFrame()
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(0, 3, 0, 3)
            item_layout.setSpacing(3)

            row = QHBoxLayout()
            row.setSpacing(6)

            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {app.get('color', '#3B82F6')}; border-radius: 4px;")
            row.addWidget(dot)

            name_lbl = QLabel(app["app_name"])
            name_lbl.setFont(QFont("Inter", 10, QFont.Weight.Medium))
            row.addWidget(name_lbl, 1)

            stat_lbl = QLabel(f"{app.get('hours', 0.0)}h ({app.get('percentage', 0)}%)")
            stat_lbl.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
            stat_lbl.setStyleSheet("color: #A1A1AA;" if self.is_dark else "color: #71717A;")
            stat_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(stat_lbl)

            item_layout.addLayout(row)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(round(app.get("percentage", 0.0))))
            bar.setTextVisible(False)
            bar.setFixedHeight(6)

            bar_bg = "#333338" if self.is_dark else "#E5E0D8"
            bar_color = app.get("color", "#3B82F6")
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {bar_bg};
                    border: none;
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                    border-radius: 3px;
                }}
            """)
            item_layout.addWidget(bar)
            self.bar_page_layout.addWidget(item_frame)

        self.bar_page_layout.addStretch()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.ring_canvas.set_theme(is_dark)
        self.apply_theme()
        self._update_toggle_styles()
        self._render_ring_app_list(self.apps_data)
        self._render_bar_app_list(self.apps_data)

    def _update_toggle_styles(self) -> None:
        mode = self.active_mode
        active_bg = "#18181B" if self.is_dark else "#FFFFFF"
        active_color = "#F4F4F6" if self.is_dark else "#18181B"
        inactive_color = "#A1A1AA" if self.is_dark else "#71717A"

        btn_base = f"""
            QPushButton {{
                border: none;
                border-radius: 5px;
                font-family: {FONT_SANS};
                font-size: 10px;
                font-weight: 600;
                padding: 0 8px;
            }}
        """
        self.btn_ring.setStyleSheet(btn_base + (f"background-color: {active_bg}; color: {active_color};" if mode == "ring" else f"background: transparent; color: {inactive_color};"))
        self.btn_bar.setStyleSheet(btn_base + (f"background-color: {active_bg}; color: {active_color};" if mode == "bar" else f"background: transparent; color: {inactive_color};"))

    def apply_theme(self) -> None:
        bg = "#242427" if self.is_dark else "#FFFFFF"
        border = "#333338" if self.is_dark else "#E5E0D8"
        capsule_bg = "#1E1E22" if self.is_dark else "#ECECF0"
        title_color = "#F4F4F6" if self.is_dark else "#111111"

        self.setStyleSheet(f"""
            QFrame#AppUsageCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame#ToggleCapsule {{
                background-color: {capsule_bg};
                border-radius: 6px;
            }}
            QLabel {{
                color: {title_color};
            }}
        """)
