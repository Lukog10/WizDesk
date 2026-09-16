"""
High-performance, antialiased custom vector chart widgets for WizDesk visual analytics.
Rendered purely via PyQt6 QPainter:
1. ProjectComparisonChartWidget: Dual-mode (Bar Chart & Line/Area Chart) comparing project hours over time.
2. AppUsageAnalyticsWidget: Dual-mode (Donut Chart & Horizontal Bar Chart) visualizing app hours.
3. KpiStatCard: Executive metric card with hero accent and change indicators.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import (
    QFont,
    QFontMetrics,
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


class MicroSparklineCanvas(QWidget):
    """Mini antialiased trend curve drawn inside KpiHeroCard."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.values: List[float] = []
        self.is_hovered: bool = False
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, values: List[float]) -> None:
        self.values = values
        self.update()

    def set_hovered(self, hovered: bool) -> None:
        if self.is_hovered != hovered:
            self.is_hovered = hovered
            self.update()

    def paintEvent(self, event) -> None:
        if not self.values or len(self.values) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        max_val = max(max(self.values), 0.1)

        points = []
        step = w / (len(self.values) - 1)
        for i, val in enumerate(self.values):
            px = i * step
            py = (h - 3.0) - (val / max_val * (h - 6.0))
            points.append(QPointF(px, py))

        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]
            ctrl1 = QPointF(p0.x() + (p1.x() - p0.x()) / 2.0, p0.y())
            ctrl2 = QPointF(p0.x() + (p1.x() - p0.x()) / 2.0, p1.y())
            path.cubicTo(ctrl1, ctrl2, p1)

        # Gradient area under curve
        area_path = QPainterPath(path)
        area_path.lineTo(w, h)
        area_path.lineTo(0.0, h)
        area_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        top_alpha = 90 if self.is_hovered else 60
        grad.setColorAt(0.0, QColor(255, 255, 255, top_alpha))
        grad.setColorAt(1.0, QColor(255, 255, 255, 4))
        painter.fillPath(area_path, grad)

        # Line stroke
        stroke_width = 2.2 if self.is_hovered else 1.8
        pen = QPen(QColor(255, 255, 255, 255 if self.is_hovered else 220), stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.strokePath(path, pen)

        # End node
        if points:
            last_pt = points[-1]
            if self.is_hovered:
                # Glowing outer halo
                painter.setBrush(QColor(255, 255, 255, 75))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(last_pt, 6.0, 6.0)
                painter.setBrush(QColor("#FFFFFF"))
                painter.setPen(QPen(QColor("#3730A3"), 1.8))
                painter.drawEllipse(last_pt, 3.0, 3.0)
            else:
                painter.setBrush(QColor("#FFFFFF"))
                painter.setPen(QPen(QColor("#4F46E5"), 1.5))
                painter.drawEllipse(last_pt, 2.5, 2.5)


class KpiStatCard(QFrame):
    """Executive KPI card with numerical value, title, status pill, subtitle, and micro sparkline."""

    def __init__(
        self,
        title: str,
        value: str,
        change_text: str = "",
        subtitle: str = "",
        is_hero: bool = False,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title_text = title
        self.value_text = value
        self.change_text = change_text
        self.subtitle_text = subtitle
        self.is_hero = is_hero
        self.is_dark = is_dark
        self.setObjectName("KpiHeroCard" if self.is_hero else "KpiStatCard")

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(84)

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
        self.lbl_change.setObjectName("KpiChangeBadge")
        self.lbl_change.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        self.lbl_change.setVisible(bool(change_text))
        top_row.addWidget(self.lbl_change)

        layout.addLayout(top_row)

        # Value row
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("KpiValue")
        self.lbl_value.setFont(QFont("Inter", 19, QFont.Weight.Bold))
        layout.addWidget(self.lbl_value)

        # Subtitle row
        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setFont(QFont("Inter", 9, QFont.Weight.Normal))
        self.lbl_subtitle.setVisible(bool(subtitle))
        layout.addWidget(self.lbl_subtitle)

        # Mini Progress Bar for tasks
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Micro-sparkline for hero card
        if self.is_hero:
            self.sparkline = MicroSparklineCanvas(self)
            layout.addWidget(self.sparkline)
        else:
            self.sparkline = None

        layout.addStretch()
        self.apply_theme()

    def enterEvent(self, event) -> None:
        if self.is_hero and self.sparkline:
            self.sparkline.set_hovered(True)
        try:
            super().enterEvent(event)
        except TypeError:
            pass

    def leaveEvent(self, event) -> None:
        if self.is_hero and self.sparkline:
            self.sparkline.set_hovered(False)
        try:
            super().leaveEvent(event)
        except TypeError:
            pass

    def set_sparkline_data(self, values: List[float]) -> None:
        if self.sparkline:
            self.sparkline.set_data(values)

    def update_data(
        self,
        value: str,
        change_text: str = "",
        subtitle: str = "",
        progress_pct: Optional[int] = None,
    ) -> None:
        self.value_text = value
        self.change_text = change_text
        self.subtitle_text = subtitle
        self.lbl_value.setText(value)
        self.lbl_change.setText(change_text)
        self.lbl_change.setVisible(bool(change_text))
        self.lbl_subtitle.setText(subtitle)
        self.lbl_subtitle.setVisible(bool(subtitle))

        if progress_pct is not None:
            self.progress_bar.setValue(max(0, min(100, progress_pct)))
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)

        self.apply_theme()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.apply_theme()

    def apply_theme(self) -> None:
        if self.is_hero:
            self.setStyleSheet("""
                QFrame#KpiHeroCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #3730A3);
                    border: 1px solid #6366F1;
                    border-radius: 12px;
                }
                QFrame#KpiHeroCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5B52F2, stop:1 #4338CA);
                    border: 1px solid #818CF8;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            self.lbl_title.setStyleSheet("color: rgba(255, 255, 255, 0.85); border: none; background: transparent;")
            self.lbl_value.setStyleSheet("color: #FFFFFF; font-size: 22px; font-weight: bold; border: none; background: transparent;")
            self.lbl_subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.72); border: none; background: transparent; font-size: 10px;")
            self.lbl_change.setStyleSheet("""
                QLabel#KpiChangeBadge {
                    background-color: rgba(255, 255, 255, 0.2);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 9px;
                    padding: 2px 8px;
                }
                QFrame#KpiHeroCard:hover QLabel#KpiChangeBadge {
                    background-color: rgba(255, 255, 255, 0.3);
                }
            """)
        else:
            if self.is_dark:
                bg = "#242427"
                border = "#333338"
                hover_bg = "#2A2A2F"
                hover_border = "#4F46E5"
                text_color = "#F4F4F6"
                sub_color = "#A1A1AA"
                badge_bg = "#2A2A2E"
                badge_color = "#10B981" if "+" in self.change_text else ("#F43F5E" if "-" in self.change_text else "#A1A1AA")
                prog_bg = "#333338"
                prog_chunk = "#10B981"
                prog_chunk_hover = "#34D399"
            else:
                bg = "#FFFFFF"
                border = "#E5E0D8"
                hover_bg = "#FAF9F6"
                hover_border = "#6366F1"
                text_color = "#111111"
                sub_color = "#71717A"
                badge_bg = "#F4F4F5"
                badge_color = "#059669" if "+" in self.change_text else ("#E11D48" if "-" in self.change_text else "#71717A")
                prog_bg = "#E5E0D8"
                prog_chunk = "#059669"
                prog_chunk_hover = "#10B981"

            self.setStyleSheet(f"""
                QFrame#KpiStatCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 12px;
                }}
                QFrame#KpiStatCard:hover {{
                    background-color: {hover_bg};
                    border: 1px solid {hover_border};
                }}
                QLabel {{
                    border: none;
                    background: transparent;
                }}
                QFrame#KpiStatCard:hover QLabel#KpiValue {{
                    color: {"#FFFFFF" if self.is_dark else "#000000"};
                }}
                QProgressBar {{
                    background-color: {prog_bg};
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background-color: {prog_chunk};
                    border-radius: 2px;
                }}
                QFrame#KpiStatCard:hover QProgressBar::chunk {{
                    background-color: {prog_chunk_hover};
                }}
            """)
            self.lbl_title.setStyleSheet(f"color: {sub_color}; border: none; background: transparent;")
            self.lbl_value.setStyleSheet(f"color: {text_color}; border: none; background: transparent; font-size: 20px;")
            self.lbl_subtitle.setStyleSheet(f"color: {sub_color}; border: none; background: transparent; font-size: 10px;")
            self.lbl_change.setStyleSheet(f"""
                QLabel#KpiChangeBadge {{
                    background-color: {badge_bg};
                    color: {badge_color};
                    border: 1px solid {border};
                    border-radius: 9px;
                    padding: 2px 8px;
                }}
                QFrame#KpiStatCard:hover QLabel#KpiChangeBadge {{
                    border-color: {hover_border};
                }}
            """)



COMPARISON_PALETTE = [
    "#6366F1",  # Indigo
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#EC4899",  # Rose
    "#06B6D4",  # Cyan
    "#8B5CF6",  # Violet
    "#F43F5E",  # Coral
    "#3B82F6",  # Electric Blue
    "#14B8A6",  # Teal
    "#EAB308",  # Gold
]


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
        self.spotlight_series: Optional[str] = None

        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setMinimumHeight(175)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_spotlight_series(self, name: Optional[str]) -> None:
        if self.spotlight_series != name:
            self.spotlight_series = name
            self.update()

    def set_data(self, series: List[Dict[str, Any]], bucket_labels: List[str]) -> None:
        # Guarantee distinct colors across all compared series
        used_colors = set()
        sanitized_series = []
        palette_idx = 0

        # First pass: preserve unique explicit colors for named projects
        pre_assigned = []
        for s in series:
            s_copy = dict(s)
            c = s_copy.get("color")
            name = s_copy.get("name", "")
            if name != "Untagged" and c and c not in used_colors:
                used_colors.add(c)
                pre_assigned.append((s_copy, c))
            else:
                pre_assigned.append((s_copy, None))

        # Second pass: assign distinct palette colors for untagged or duplicate projects
        for s_copy, c in pre_assigned:
            if not c:
                while palette_idx < len(COMPARISON_PALETTE) and COMPARISON_PALETTE[palette_idx] in used_colors:
                    palette_idx += 1
                if palette_idx < len(COMPARISON_PALETTE):
                    c = COMPARISON_PALETTE[palette_idx]
                    palette_idx += 1
                else:
                    c = COMPARISON_PALETTE[len(used_colors) % len(COMPARISON_PALETTE)]
                used_colors.add(c)
            s_copy["color"] = c
            sanitized_series.append(s_copy)

        self.series = sanitized_series
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
            is_hovered_label = (self.hover_bucket_idx == i)
            if is_hovered_label:
                painter.setPen(QColor("#FFFFFF" if self.is_dark else "#111111"))
                painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
            else:
                painter.setPen(text_color)
                painter.setFont(QFont("Inter", 8, QFont.Weight.Medium))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # 4. Hover Shaded Column Highlight (clean translucent focus without vertical crosshair line)
        if self.hover_bucket_idx is not None and self.hover_bucket_idx < num_b:
            col_x = margin_left + self.hover_bucket_idx * b_width

            # Soft column highlight
            h_col = QColor(99, 102, 241, 14 if self.is_dark else 22)
            painter.fillRect(QRectF(col_x, margin_top, b_width, plot_h), h_col)

        # 5. Render Data (Bar Mode or Area Mode)
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
                    is_bucket_hovered = (self.hover_bucket_idx == b_idx)

                    for s_idx, s in enumerate(active_series):
                        hours_list = s.get("hours", [])
                        val = hours_list[b_idx] if b_idx < len(hours_list) else 0.0
                        bar_h = max(2.0, (val / y_max) * plot_h) if val > 0 else 0.0

                        bx = start_x + s_idx * (individual_w + bar_gap)
                        by = margin_top + plot_h - bar_h

                        is_spotlighted = (self.spotlight_series == s.get("name"))
                        is_dimmed = (self.spotlight_series is not None and not is_spotlighted)

                        bar_color = QColor(s.get("color", "#6366F1"))
                        if is_spotlighted:
                            bar_color = bar_color.lighter(125)
                        elif is_dimmed:
                            bar_color.setAlpha(60)
                        elif is_bucket_hovered:
                            # Brighten hovered bars
                            bar_color = bar_color.lighter(115)
                        elif self.hover_bucket_idx is not None:
                            # Dim non-hovered bars slightly
                            bar_color.setAlpha(170)

                        if val > 0:
                            path = QPainterPath()
                            radius = min(4.0, individual_w / 2.0)
                            path.addRoundedRect(QRectF(bx, by, individual_w, bar_h), radius, radius)
                            painter.fillPath(path, bar_color)
                            if is_bucket_hovered or is_spotlighted:
                                stroke_pen = QPen(QColor(255, 255, 255, 180 if is_spotlighted else 140), 1.2 if is_spotlighted else 1.0)
                                painter.strokePath(path, stroke_pen)
            else:
                # Area / Line Mode: Smooth Bezier Splines
                for s in reversed(active_series):
                    color = QColor(s.get("color", "#6366F1"))
                    hours_list = s.get("hours", [])

                    is_spotlighted = (self.spotlight_series == s.get("name"))
                    is_dimmed = (self.spotlight_series is not None and not is_spotlighted)
                    if is_dimmed:
                        color.setAlpha(60)

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
                        grad_color_top.setAlpha(20 if is_dimmed else (80 if self.is_dark else 70))
                        grad_color_bot = QColor(color)
                        grad_color_bot.setAlpha(2 if is_dimmed else 6)
                        gradient.setColorAt(0.0, grad_color_top)
                        gradient.setColorAt(1.0, grad_color_bot)

                        painter.fillPath(area_path, gradient)

                        # Draw the line curve
                        pen = QPen(color, 3.2 if is_spotlighted else 2.5)
                        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                        painter.strokePath(path, pen)

                        # Draw vertices with hover halo rings
                        for b_i, pt in enumerate(points):
                            is_node_hovered = (self.hover_bucket_idx == b_i)
                            if is_node_hovered or is_spotlighted:
                                # Outer glowing halo ring
                                halo_color = QColor(color)
                                halo_color.setAlpha(70 if is_spotlighted else 60)
                                painter.setBrush(halo_color)
                                painter.setPen(Qt.PenStyle.NoPen)
                                painter.drawEllipse(pt, 8.5 if is_spotlighted else 7.5, 8.5 if is_spotlighted else 7.5)

                                # Core node
                                painter.setBrush(QColor("#FFFFFF"))
                                painter.setPen(QPen(color, 2.5))
                                painter.drawEllipse(pt, 4.2 if is_spotlighted else 4.0, 4.2 if is_spotlighted else 4.0)
                            else:
                                painter.setBrush(QColor("#FFFFFF" if not self.is_dark else "#18181B"))
                                painter.setPen(QPen(color, 2.0))
                                painter.drawEllipse(pt, 3.2, 3.2)

        # 6. Render Executive Glassmorphic Tooltip Card
        if self.hover_bucket_idx is not None and self.hover_bucket_idx < len(self.bucket_labels) and self.hover_pos:
            b_name = self.bucket_labels[self.hover_bucket_idx]

            # Gather active project rows for this bucket
            active_rows = []
            total_b_hours = 0.0
            for s in self.series:
                h_list = s.get("hours", [])
                val = h_list[self.hover_bucket_idx] if self.hover_bucket_idx < len(h_list) else 0.0
                total_b_hours += val
                if val > 0 or len(self.series) <= 3:
                    active_rows.append((s.get("color", "#6366F1"), s.get("name", "Project"), val))

            if active_rows:
                painter.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
                title_text = f"{b_name}"
                total_badge_text = f"{total_b_hours:.1f}h total"

                painter.setFont(QFont("Inter", 8, QFont.Weight.Normal))
                fm_sub = painter.fontMetrics()
                max_name_w = 0
                for _, name, h_val in active_rows:
                    row_w = fm_sub.horizontalAdvance(f"{name}  {h_val:.1f}h") + 30
                    if row_w > max_name_w:
                        max_name_w = row_w

                card_w = max(145.0, float(max_name_w + 24))
                header_h = 24.0
                row_h = 17.0
                card_h = header_h + 8.0 + (len(active_rows) * row_h) + 6.0

                # Intelligent positioning
                raw_x = float(self.hover_pos.x())
                raw_y = float(self.hover_pos.y())

                if raw_x + card_w + 16 <= w - margin_right:
                    card_x = raw_x + 14.0
                elif raw_x - card_w - 16 >= margin_left:
                    card_x = raw_x - card_w - 14.0
                else:
                    card_x = max(margin_left + 4, min(w - margin_right - card_w - 4, raw_x - card_w / 2.0))

                card_y = max(4.0, min(h - card_h - 4.0, raw_y - card_h / 2.0))

                card_rect = QRectF(card_x, card_y, card_w, card_h)

                card_bg = QColor("#18181B" if self.is_dark else "#FFFFFF")
                card_border = QColor("#3F3F46" if self.is_dark else "#D4D4D8")

                card_path = QPainterPath()
                card_path.addRoundedRect(card_rect, 8.0, 8.0)

                # Soft shadow
                shadow_color = QColor(0, 0, 0, 80 if self.is_dark else 28)
                painter.fillPath(card_path.translated(0, 2), shadow_color)

                painter.fillPath(card_path, card_bg)
                painter.strokePath(card_path, QPen(card_border, 1.0))

                # Header text
                painter.setFont(QFont("Inter", 9, QFont.Weight.Bold))
                painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
                painter.drawText(QRectF(card_x + 10, card_y + 5, card_w - 65, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_text)

                # Total badge
                painter.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
                painter.setPen(QColor("#818CF8" if self.is_dark else "#4F46E5"))
                painter.drawText(QRectF(card_x + card_w - 62, card_y + 5, 52, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, total_badge_text)

                # Divider
                painter.setPen(QPen(QColor("#27272A" if self.is_dark else "#E5E5E7"), 1.0))
                painter.drawLine(QPointF(card_x + 8, card_y + 23), QPointF(card_x + card_w - 8, card_y + 23))

                # Project rows
                curr_y = card_y + 27
                painter.setFont(QFont("Inter", 8, QFont.Weight.Normal))
                for color_hex, name, h_val in active_rows:
                    # Color dot
                    painter.setBrush(QColor(color_hex))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(card_x + 14, curr_y + 7), 3.2, 3.2)

                    # Project name
                    painter.setPen(QColor("#A1A1AA" if self.is_dark else "#52525B"))
                    painter.drawText(QRectF(card_x + 22, curr_y, card_w - 68, 15), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

                    # Hours
                    painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
                    painter.drawText(QRectF(card_x + card_w - 44, curr_y, 34, 15), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{h_val:.1f}h")

                    curr_y += row_h


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
        self._render_legend(self.canvas.series)

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
            pill = QFrame()
            pill.setObjectName("LegendPill")
            pill.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(6, 2, 6, 2)
            pill_layout.setSpacing(6)

            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {s.get('color', '#6366F1')}; border-radius: 4px;")
            pill_layout.addWidget(dot)

            name_lbl = QLabel(f"{s['name']} ({s.get('total_hours', 0)}h)")
            name_lbl.setFont(QFont("Inter", 9, QFont.Weight.Medium))
            name_lbl.setStyleSheet("color: #A1A1AA;" if self.is_dark else "color: #71717A;")
            pill_layout.addWidget(name_lbl)

            s_name = s.get("name", "")
            pill.enterEvent = lambda event, name=s_name: self.canvas.set_spotlight_series(name)
            pill.leaveEvent = lambda event: self.canvas.set_spotlight_series(None)

            self.legend_layout.addWidget(pill)
            self.legend_layout.addSpacing(2)

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
        hover_border = "#4A4A54" if self.is_dark else "#D4CEBF"
        capsule_bg = "#1E1E22" if self.is_dark else "#ECECF0"
        title_color = "#F4F4F6" if self.is_dark else "#111111"

        self.setStyleSheet(f"""
            QFrame#ChartCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame#ChartCard:hover {{
                border: 1px solid {hover_border};
            }}
            QFrame#ToggleCapsule {{
                background-color: {capsule_bg};
                border-radius: 6px;
            }}
            QLabel {{
                color: {title_color};
            }}
            QFrame#LegendPill {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QFrame#LegendPill:hover {{
                background-color: {"#2A2A2E" if self.is_dark else "#F4F4F5"};
                border: 1px solid {"#3F3F46" if self.is_dark else "#E5E0D8"};
            }}
        """)


class AppUsageDonutCanvas(QWidget):
    """
    Custom QPainter canvas rendering an executive segmented Donut Chart for application usage statistics.
    Features:
    - Clean proportional donut segments with subtle separator gaps between slices.
    - Outer track fallback for empty / 0h states.
    - Smooth interactive hover tracking with radial popout expansion and luminous halo on the active slice.
    - Dynamic center text morphing: total tracked hours vs. hovered app name, duration, and percentage share.
    - Full two-way hover synchronization with ranked application list.
    """

    donut_hovered = pyqtSignal(int)
    ring_hovered = donut_hovered  # Backwards compatibility alias

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.apps_data: List[Dict[str, Any]] = []
        self.total_hours: float = 0.0
        self.hovered_segment_idx: Optional[int] = None
        self.hover_pos: Optional[QPoint] = None

        self.setMouseTracking(True)
        self.setFixedSize(140, 140)

    @property
    def hovered_ring_idx(self) -> Optional[int]:
        """Backward compatibility getter."""
        return self.hovered_segment_idx

    @hovered_ring_idx.setter
    def hovered_ring_idx(self, val: Optional[int]) -> None:
        """Backward compatibility setter."""
        self.hovered_segment_idx = val

    def set_hovered_ring(self, idx: Optional[int]) -> None:
        """Backward compatibility alias for set_hovered_segment."""
        self.set_hovered_segment(idx)

    def set_hovered_segment(self, idx: Optional[int]) -> None:
        if self.hovered_segment_idx != idx:
            self.hovered_segment_idx = idx
            self.update()

    def set_data(self, apps_data: List[Dict[str, Any]], total_hours: float) -> None:
        self.apps_data = apps_data
        self.total_hours = total_hours
        self.update()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def _get_active_apps(self) -> List[Dict[str, Any]]:
        """Return up to top 5 applications with tracked time or percentage."""
        apps = [a for a in self.apps_data if a.get("hours", 0.0) > 0 or a.get("percentage", 0.0) > 0]
        if not apps and self.apps_data:
            apps = self.apps_data[:5]
        return apps[:5]

    def _compute_slices(self) -> List[Tuple[float, float]]:
        """Compute (start_deg, span_deg) clockwise from 12 o'clock (0.0 to 360.0)."""
        apps = self._get_active_apps()
        if not apps:
            return []

        tot_val = sum(a.get("hours", 0.0) for a in apps)
        if tot_val <= 0:
            tot_val = sum(a.get("percentage", 0.0) for a in apps)
        if tot_val <= 0:
            tot_val = 1.0

        slices: List[Tuple[float, float]] = []
        cur_angle = 0.0
        for i, a in enumerate(apps):
            val = a.get("hours", 0.0) if sum(x.get("hours", 0.0) for x in apps) > 0 else a.get("percentage", 0.0)
            span = (val / tot_val) * 360.0
            slices.append((cur_angle, span))
            cur_angle += span

        return slices

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        dx = pos.x() - cx
        dy = pos.y() - cy
        d = math.hypot(dx, dy)

        inner_r = 34.0
        outer_r = 65.0
        apps = self._get_active_apps()

        found_idx = None
        if inner_r <= d <= outer_r and apps:
            # Angle in degrees clockwise from 12 o'clock (0 to 360)
            angle_cw = (math.degrees(math.atan2(dx, -dy))) % 360.0
            slices = self._compute_slices()
            for idx, (s_start, s_span) in enumerate(slices):
                s_end = s_start + s_span
                if s_start <= angle_cw < s_end or (idx == len(slices) - 1 and angle_cw >= s_start):
                    found_idx = idx
                    break

        if found_idx != self.hovered_segment_idx:
            self.hovered_segment_idx = found_idx
            self.hover_pos = pos.toPoint() if found_idx is not None else None
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor if found_idx is not None else Qt.CursorShape.ArrowCursor))
            self.donut_hovered.emit(found_idx if found_idx is not None else -1)
            self.update()
        elif found_idx is not None:
            self.hover_pos = pos.toPoint()
            self.update()

    def leaveEvent(self, event) -> None:
        if self.hovered_segment_idx is not None:
            self.hovered_segment_idx = None
            self.hover_pos = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.donut_hovered.emit(-1)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        base_outer_r = 60.0
        base_inner_r = 36.0
        track_color = QColor("#333338" if self.is_dark else "#ECECF0")

        apps = self._get_active_apps()
        slices = self._compute_slices()

        # If no active apps or 0 total hours, draw neutral background donut
        if not apps or not slices:
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            path.addEllipse(QRectF(cx - base_outer_r, cy - base_outer_r, base_outer_r * 2, base_outer_r * 2))
            path.addEllipse(QRectF(cx - base_inner_r, cy - base_inner_r, base_inner_r * 2, base_inner_r * 2))
            painter.fillPath(path, track_color)
        else:
            num_slices = len(slices)
            gap_deg = 2.5 if num_slices > 1 else 0.0

            for idx, (app, (start_deg, span_deg)) in enumerate(zip(apps, slices)):
                is_hovered = (self.hovered_segment_idx == idx)

                # Angular slice adjustment for separator gaps
                if num_slices > 1:
                    actual_span = max(1.2, span_deg - gap_deg)
                    draw_start = start_deg + gap_deg / 2.0
                else:
                    actual_span = span_deg
                    draw_start = start_deg

                # Hover radial popout
                if is_hovered:
                    popout = 3.0
                    cur_outer_r = base_outer_r + 3.5
                    cur_inner_r = base_inner_r - 1.0
                    mid_deg = draw_start + actual_span / 2.0
                    mid_rad = math.radians(90.0 - mid_deg)
                    sec_cx = cx + popout * math.cos(mid_rad)
                    sec_cy = cy - popout * math.sin(mid_rad)
                else:
                    cur_outer_r = base_outer_r
                    cur_inner_r = base_inner_r
                    sec_cx = cx
                    sec_cy = cy

                app_color = QColor(app.get("color", "#3B82F6"))
                if is_hovered:
                    app_color = app_color.lighter(118)
                elif self.hovered_segment_idx is not None:
                    app_color.setAlpha(170)

                outer_rect = QRectF(sec_cx - cur_outer_r, sec_cy - cur_outer_r, cur_outer_r * 2, cur_outer_r * 2)
                inner_rect = QRectF(sec_cx - cur_inner_r, sec_cy - cur_inner_r, cur_inner_r * 2, cur_inner_r * 2)

                # Convert clockwise-from-12 to Qt counter-clockwise angles
                qt_start = 90.0 - draw_start
                qt_span = -actual_span

                path = QPainterPath()
                if actual_span >= 359.5:
                    path.setFillRule(Qt.FillRule.OddEvenFill)
                    path.addEllipse(outer_rect)
                    path.addEllipse(inner_rect)
                else:
                    path.arcMoveTo(outer_rect, qt_start)
                    path.arcTo(outer_rect, qt_start, qt_span)
                    path.arcTo(inner_rect, qt_start + qt_span, -qt_span)
                    path.closeSubpath()

                # Draw luminous glow halo on hover
                if is_hovered:
                    glow_pen = QPen(QColor(app_color.red(), app_color.green(), app_color.blue(), 75), 3.0)
                    painter.strokePath(path, glow_pen)

                painter.fillPath(path, app_color)

                # Thin subtle inner stroke for slice separation
                stroke_pen = QPen(QColor(255, 255, 255, 140 if is_hovered else 30), 1.0)
                painter.strokePath(path, stroke_pen)

        # Draw Center Hole Text
        if self.hovered_segment_idx is not None and self.hovered_segment_idx < len(apps):
            app = apps[self.hovered_segment_idx]
            app_name = app.get("app_name", "App")
            if len(app_name) > 11:
                app_name = app_name[:10] + "…"
            hours = app.get("hours", 0.0)
            pct = app.get("percentage", 0)
            pct_str = f"{int(round(pct))}%" if (isinstance(pct, (int, float)) and pct == int(pct)) else f"{pct}%"
            app_color = QColor(app.get("color", "#3B82F6")).lighter(120 if self.is_dark else 100)

            font_title = QFont("Inter", 9, QFont.Weight.Bold)
            fm_t = QFontMetrics(font_title)
            if fm_t.horizontalAdvance(app_name) > 66:
                font_title.setPointSize(8)
            painter.setFont(font_title)
            painter.setPen(app_color)
            painter.drawText(QRectF(cx - 35, cy - 14, 70, 16), Qt.AlignmentFlag.AlignCenter, app_name)

            stat_text = f"{hours}h ({pct_str})"
            font_stat = QFont("Inter", 8, QFont.Weight.DemiBold)
            fm_s = QFontMetrics(font_stat)
            if fm_s.horizontalAdvance(stat_text) > 66:
                font_stat.setPointSize(7)
            painter.setFont(font_stat)
            painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
            painter.drawText(QRectF(cx - 35, cy + 2, 70, 14), Qt.AlignmentFlag.AlignCenter, stat_text)
        else:
            hours_str = f"{self.total_hours}h"
            painter.setFont(QFont("Inter", 14, QFont.Weight.Bold))
            painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
            text_rect = QRectF(cx - 35, cy - 12, 70, 18)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, hours_str)

            painter.setFont(QFont("Inter", 8, QFont.Weight.Medium))
            painter.setPen(QColor("#71717A" if self.is_dark else "#A1A1AA"))
            sub_rect = QRectF(cx - 35, cy + 6, 70, 14)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, "Total Tracked")


# Backward compatibility alias
AppUsageRingCanvas = AppUsageDonutCanvas


class AppUsageAnalyticsWidget(QFrame):
    """
    Application Statistics card supporting both:
    1. Segmented Donut Chart Mode (Proportional angular slices with interactive hover).
    2. Horizontal Comparative Bar Chart Mode (Hours per app with percentage bars).
    """

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.active_mode = "donut"  # 'donut' or 'bar'
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

        # Capsule Switcher: Donut vs Bar
        self.capsule = QFrame()
        self.capsule.setObjectName("ToggleCapsule")
        capsule_layout = QHBoxLayout(self.capsule)
        capsule_layout.setContentsMargins(2, 2, 2, 2)
        capsule_layout.setSpacing(2)

        self.btn_donut = QPushButton("Donut")
        self.btn_donut.setFixedHeight(22)
        self.btn_donut.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_donut.clicked.connect(lambda: self._set_mode("donut"))
        capsule_layout.addWidget(self.btn_donut)

        # Backward compatibility alias
        self.btn_ring = self.btn_donut

        self.btn_bar = QPushButton("Bar")
        self.btn_bar.setFixedHeight(22)
        self.btn_bar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_bar.clicked.connect(lambda: self._set_mode("bar"))
        capsule_layout.addWidget(self.btn_bar)

        header_row.addWidget(self.capsule)
        layout.addLayout(header_row)

        # Stacked Views (Donut vs Bar)
        self.stack = QStackedWidget(self)

        # 1. Donut View Container (Side-by-side: Donut Chart on left, Ranked Breakdown on right)
        self.donut_page = QWidget()
        self.donut_page.setMinimumHeight(150)
        donut_page_layout = QHBoxLayout(self.donut_page)
        donut_page_layout.setContentsMargins(0, 4, 0, 4)
        donut_page_layout.setSpacing(16)

        self.donut_canvas = AppUsageDonutCanvas(is_dark=self.is_dark, parent=self.donut_page)
        donut_page_layout.addWidget(self.donut_canvas)

        # Backward compatibility alias
        self.ring_page = self.donut_page
        self.ring_canvas = self.donut_canvas

        self.donut_list_layout = QVBoxLayout()
        self.donut_list_layout.setContentsMargins(0, 0, 0, 0)
        self.donut_list_layout.setSpacing(6)
        self.donut_list_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        donut_page_layout.addLayout(self.donut_list_layout, 1)

        # Backward compatibility alias
        self.ring_list_layout = self.donut_list_layout

        self.stack.addWidget(self.donut_page)

        # 2. Bar View Container
        self.bar_page = QWidget()
        self.bar_page_layout = QVBoxLayout(self.bar_page)
        self.bar_page_layout.setContentsMargins(0, 4, 0, 0)
        self.bar_page_layout.setSpacing(6)
        self.stack.addWidget(self.bar_page)

        layout.addWidget(self.stack)

        self.apply_theme()
        self._update_toggle_styles()

    def set_data(self, apps_data: List[Dict[str, Any]], total_hours: float) -> None:
        self.apps_data = apps_data
        self.donut_canvas.set_data(apps_data, total_hours)
        self._render_donut_app_list(apps_data)
        self._render_bar_app_list(apps_data)

    def _set_mode(self, mode: str) -> None:
        if mode in ("donut", "ring"):
            self.active_mode = "donut"
            self.stack.setCurrentWidget(self.donut_page)
        else:
            self.active_mode = "bar"
            self.stack.setCurrentWidget(self.bar_page)
        self._update_toggle_styles()

    def _render_donut_app_list(self, apps: List[Dict[str, Any]]) -> None:
        # Clear list
        while self.donut_list_layout.count() > 0:
            item = self.donut_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not apps:
            empty = QLabel("No application activity recorded.")
            empty.setFont(QFont("Inter", 10))
            empty.setStyleSheet("color: #71717A; padding: 12px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.donut_list_layout.addWidget(empty)
            return

        for idx, app in enumerate(apps[:4]):
            row_frame = QFrame()
            row_frame.setObjectName("AppDonutRow")
            row_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(6, 3, 6, 3)
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

            row_frame.enterEvent = lambda event, i=idx: self.donut_canvas.set_hovered_segment(i)
            row_frame.leaveEvent = lambda event: self.donut_canvas.set_hovered_segment(None)

            self.donut_list_layout.addWidget(row_frame)

    # Backward compatibility alias
    _render_ring_app_list = _render_donut_app_list

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
            item_frame.setObjectName("AppUsageBarItem")
            item_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(8, 4, 8, 4)
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
        self.donut_canvas.set_theme(is_dark)
        self.apply_theme()
        self._update_toggle_styles()
        self._render_donut_app_list(self.apps_data)
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
        self.btn_donut.setStyleSheet(btn_base + (f"background-color: {active_bg}; color: {active_color};" if mode in ("donut", "ring") else f"background: transparent; color: {inactive_color};"))
        self.btn_bar.setStyleSheet(btn_base + (f"background-color: {active_bg}; color: {active_color};" if mode == "bar" else f"background: transparent; color: {inactive_color};"))

    def apply_theme(self) -> None:
        bg = "#242427" if self.is_dark else "#FFFFFF"
        border = "#333338" if self.is_dark else "#E5E0D8"
        hover_border = "#4A4A54" if self.is_dark else "#D4CEBF"
        capsule_bg = "#1E1E22" if self.is_dark else "#ECECF0"
        title_color = "#F4F4F6" if self.is_dark else "#111111"

        self.setStyleSheet(f"""
            QFrame#AppUsageCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame#AppUsageCard:hover {{
                border: 1px solid {hover_border};
            }}
            QFrame#ToggleCapsule {{
                background-color: {capsule_bg};
                border-radius: 6px;
            }}
            QLabel {{
                color: {title_color};
            }}
            QFrame#AppDonutRow, QFrame#AppRingRow {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QFrame#AppDonutRow:hover, QFrame#AppRingRow:hover {{
                background-color: {"#2E2E33" if self.is_dark else "#F4F4F5"};
                border: 1px solid {"#3F3F46" if self.is_dark else "#E5E0D8"};
            }}
            QFrame#AppUsageBarItem {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
            }}
            QFrame#AppUsageBarItem:hover {{
                background-color: {"#2A2A2E" if self.is_dark else "#FAF8F5"};
                border: 1px solid {"#3F3F46" if self.is_dark else "#E5E0D8"};
            }}
        """)

