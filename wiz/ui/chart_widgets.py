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
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QProgressBar,
    QSizePolicy,
    QScrollArea,
)

from wiz.ui.fonts import FONT_SANS, FONT_MONO, get_font


class MicroSparklineCanvas(QWidget):
    """Mini antialiased trend curve drawn inside KpiHeroCard."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.values: List[float] = []
        self.is_hovered: bool = False
        self.setFixedHeight(22)
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
            py = (h - 2.0) - (val / max_val * (h - 4.0))
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
        stroke_width = 2.0 if self.is_hovered else 1.6
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
                painter.drawEllipse(last_pt, 5.0, 5.0)
                painter.setBrush(QColor("#FFFFFF"))
                painter.setPen(QPen(QColor("#3730A3"), 1.6))
                painter.drawEllipse(last_pt, 2.5, 2.5)
            else:
                painter.setBrush(QColor("#FFFFFF"))
                painter.setPen(QPen(QColor("#4F46E5"), 1.4))
                painter.drawEllipse(last_pt, 2.0, 2.0)


class KpiStatCard(QFrame):
    """
    Compact executive KPI card with numerical value, title, circular arrow badge,
    subtitle, and micro sparkline or progress bar.
    Designed for a non-scrolling 4-column horizontal strip.
    """

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
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(88)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        # Backward compatibility placeholders (hidden per user request)
        self.badge_icon = QLabel()
        self.badge_icon.hide()
        self.badge_arrow = QLabel()
        self.badge_arrow.hide()

        # Value row: Value with inline change badge next to it matching reference image
        val_row = QHBoxLayout()
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(6)

        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("KpiValue")
        self.lbl_value.setMinimumWidth(0)
        initial_size = 15 if len(value) > 7 else 18
        self.lbl_value.setFont(get_font(initial_size, QFont.Weight.Bold))
        val_row.addWidget(self.lbl_value)

        self.lbl_change = QLabel(change_text)
        self.lbl_change.setObjectName("KpiChangeBadge")
        self.lbl_change.setFont(get_font(8, QFont.Weight.DemiBold))
        self.lbl_change.setVisible(bool(change_text))
        val_row.addWidget(self.lbl_change)
        val_row.addStretch()

        layout.addLayout(val_row)

        # Title row
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("KpiTitle")
        self.lbl_title.setFont(get_font(9, QFont.Weight.Medium))
        layout.addWidget(self.lbl_title)

        # Subtitle preserved for backward compatibility
        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setObjectName("KpiSubtitle")
        self.lbl_subtitle.setVisible(False)
        layout.addWidget(self.lbl_subtitle)

        # Mini Progress Bar for tasks
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(5)
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

    def minimumSizeHint(self) -> QSize:
        return QSize(100, 88)

    def sizeHint(self) -> QSize:
        return QSize(150, 88)

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

        # Auto-elide if text is long to maintain fixed static card size
        display_val = value
        if len(value) > 13:
            display_val = value[:11] + "…"
            self.lbl_value.setToolTip(value)
            self.setToolTip(f"{self.title_text}: {value}")
        else:
            self.lbl_value.setToolTip("")
            self.setToolTip("")
        self.lbl_value.setText(display_val)

        # Auto-adjust font size to avoid wrapping in compact card width
        font_size = 18
        if len(display_val) > 12:
            font_size = 13
        elif len(display_val) > 8:
            font_size = 15
        self.lbl_value.setFont(get_font(font_size, QFont.Weight.Bold))

        self.lbl_change.setText(change_text)
        self.lbl_change.setVisible(bool(change_text))
        self.lbl_subtitle.setText(subtitle)

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
            self.lbl_title.setStyleSheet(f"color: rgba(255, 255, 255, 0.85); border: none; background: transparent; font-family: {FONT_SANS}; font-size: 9px;")
            val_font_size = "15px" if len(self.value_text) > 7 else "18px"
            self.lbl_value.setStyleSheet(f"color: #FFFFFF; font-family: {FONT_SANS}; font-size: {val_font_size}; font-weight: bold; border: none; background: transparent;")
            self.lbl_subtitle.setStyleSheet(f"color: rgba(255, 255, 255, 0.72); border: none; background: transparent; font-family: {FONT_SANS}; font-size: 8px;")
            self.lbl_change.setStyleSheet(f"""
                QLabel#KpiChangeBadge {{
                    background-color: rgba(255, 255, 255, 0.2);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 0px 4px;
                    font-family: {FONT_SANS};
                    font-size: 8px;
                }}
                QFrame#KpiHeroCard:hover QLabel#KpiChangeBadge {{
                    background-color: rgba(255, 255, 255, 0.3);
                }}
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
                arrow_bg = "#1F1F22"
                arrow_border = "#333338"
                arrow_color = "#A1A1AA"
                icon_bg = "#1F1F22"
                icon_border = "#333338"
                icon_color = "#A1A1AA"
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
                arrow_bg = "#F4F4F5"
                arrow_border = "#E5E0D8"
                arrow_color = "#71717A"
                icon_bg = "#F4F4F5"
                icon_border = "#E5E0D8"
                icon_color = "#71717A"

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
                QLabel#KpiIconBadge {{
                    background-color: {icon_bg};
                    color: {icon_color};
                }}
                QLabel#KpiTitle {{
                    color: {sub_color};
                    font-family: {FONT_SANS};
                    font-size: 9px;
                }}
                QLabel#KpiChangeBadge {{
                    background-color: {badge_bg};
                    color: {badge_color};
                    border-radius: 6px;
                    padding: 0px 4px;
                }}
                QProgressBar {{
                    background-color: {prog_bg};
                    border: none;
                    border-radius: 2.5px;
                }}
                QProgressBar::chunk {{
                    background-color: {prog_chunk};
                    border-radius: 2.5px;
                }}
                QFrame#KpiStatCard:hover QProgressBar::chunk {{
                    background-color: {prog_chunk_hover};
                }}
            """)
            val_font_size = "15px" if len(self.value_text) > 7 else "18px"
            self.lbl_value.setStyleSheet(f"color: {text_color}; font-family: {FONT_SANS}; font-size: {val_font_size}; font-weight: bold; border: none; background: transparent;")
            self.lbl_subtitle.setStyleSheet(f"color: {sub_color}; border: none; background: transparent; font-family: {FONT_SANS}; font-size: 9px;")
            self.lbl_change.setStyleSheet(f"""
                QLabel#KpiChangeBadge {{
                    background-color: {badge_bg};
                    color: {badge_color};
                    border: 1px solid {border};
                    border-radius: 7px;
                    padding: 1px 5px;
                    font-family: {FONT_SANS};
                    font-size: 8px;
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
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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

        # Round max_val up to clean increment with tight headroom (filling 75-90% of chart)
        if max_val <= 1.0:
            y_max = 1.0
            ticks = [0.0, 0.5, 1.0]
        elif max_val <= 2.5:
            y_max = 2.5
            ticks = [0.0, 1.0, 2.0, 2.5]
        elif max_val <= 4.0:
            y_max = 4.0
            ticks = [0.0, 1.0, 2.0, 3.0, 4.0]
        elif max_val <= 6.0:
            y_max = 6.5
            ticks = [0.0, 2.0, 4.0, 6.0]
        elif max_val <= 8.0:
            y_max = 8.5
            ticks = [0.0, 2.0, 4.0, 6.0, 8.0]
        else:
            step = math.ceil(max_val / 4.0)
            y_max = float(step * 4)
            ticks = [float(i * step) for i in range(5)]

        # 2. Draw horizontal grid lines & Y-axis labels
        painter.setFont(get_font(8, QFont.Weight.Medium))
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
                painter.setFont(get_font(8, QFont.Weight.Bold))
            else:
                painter.setPen(text_color)
                painter.setFont(get_font(8, QFont.Weight.Medium))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # 4. Draw Day Background Slots & Hover Shaded Column Highlight
        slot_w = min(b_width * 0.72, 24.0)
        slot_color = QColor(255, 255, 255, 6 if self.is_dark else 10)
        for b_i in range(num_b):
            cx_b = margin_left + (b_i + 0.5) * b_width
            slot_path = QPainterPath()
            slot_path.addRoundedRect(QRectF(cx_b - slot_w / 2.0, margin_top + 4, slot_w, plot_h - 4), 4.0, 4.0)
            painter.fillPath(slot_path, slot_color)

        if self.hover_bucket_idx is not None and self.hover_bucket_idx < num_b:
            col_x = margin_left + self.hover_bucket_idx * b_width
            h_col = QColor(99, 102, 241, 16 if self.is_dark else 24)
            painter.fillRect(QRectF(col_x, margin_top, b_width, plot_h), h_col)

        # 5. Render Data (Bar Mode or Area Mode)
        if self.series and num_b > 0:
            active_series = [s for s in self.series if sum(s.get("hours", [])) > 0]
            if not active_series:
                active_series = self.series[:1]  # Draw baseline if empty

            if self.chart_mode == "bar":
                # Render vertical grouped bars with dynamic active-series packing
                for b_idx in range(num_b):
                    center_x = margin_left + (b_idx + 0.5) * b_width
                    is_bucket_hovered = (self.hover_bucket_idx == b_idx)

                    # Dynamic packing: only render projects with tracked hours for this bucket
                    day_series = []
                    for s in active_series:
                        hours_list = s.get("hours", [])
                        val = hours_list[b_idx] if b_idx < len(hours_list) else 0.0
                        if val > 0.01:
                            day_series.append((s, val))

                    day_cnt = len(day_series)
                    if day_cnt == 0:
                        continue

                    if day_cnt == 1:
                        ind_w = min(b_width * 0.50, 20.0)
                        gap = 0.0
                        tot_w = ind_w
                    elif day_cnt == 2:
                        gap = 2.5
                        ind_w = min((b_width * 0.72 - gap) / 2.0, 15.0)
                        tot_w = ind_w * 2 + gap
                    else:
                        gap = 2.0
                        tot_w = min(b_width * 0.85, day_cnt * 13.0)
                        ind_w = max(4.0, (tot_w - (day_cnt - 1) * gap) / day_cnt)

                    start_x = center_x - (tot_w / 2.0)

                    for d_idx, (s, val) in enumerate(day_series):
                        bar_h = max(3.0, (val / y_max) * plot_h)
                        bx = start_x + d_idx * (ind_w + gap)
                        by = margin_top + plot_h - bar_h

                        is_spotlighted = (self.spotlight_series == s.get("name"))
                        is_dimmed = (self.spotlight_series is not None and not is_spotlighted)

                        bar_color = QColor(s.get("color", "#6366F1"))
                        if is_spotlighted:
                            bar_color = bar_color.lighter(125)
                        elif is_dimmed:
                            bar_color.setAlpha(60)
                        elif is_bucket_hovered:
                            bar_color = bar_color.lighter(115)
                        elif self.hover_bucket_idx is not None:
                            bar_color.setAlpha(170)

                        path = QPainterPath()
                        r = min(4.5, ind_w / 2.0, bar_h)
                        path.moveTo(bx, by + bar_h)
                        path.lineTo(bx, by + r)
                        path.arcTo(bx, by, r * 2, r * 2, 180, -90)
                        path.lineTo(bx + ind_w - r, by)
                        path.arcTo(bx + ind_w - r * 2, by, r * 2, r * 2, 90, -90)
                        path.lineTo(bx + ind_w, by + bar_h)
                        path.closeSubpath()

                        painter.fillPath(path, bar_color)
                        if is_bucket_hovered or is_spotlighted:
                            stroke_pen = QPen(QColor(255, 255, 255, 200 if is_spotlighted else 150), 1.2 if is_spotlighted else 1.0)
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
                        grad_color_top.setAlpha(30 if is_dimmed else (115 if self.is_dark else 95))
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

                        # Draw vertices with hover halo rings (skip zero dots on inactive days)
                        for b_i, pt in enumerate(points):
                            val = hours_list[b_i] if b_i < len(hours_list) else 0.0
                            is_node_hovered = (self.hover_bucket_idx == b_i)
                            if val <= 0.01 and not is_spotlighted and not is_node_hovered:
                                continue

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
                painter.setFont(get_font(9, QFont.Weight.DemiBold))
                title_text = f"{b_name}"
                total_badge_text = f"{total_b_hours:.1f}h total"

                painter.setFont(get_font(8, QFont.Weight.Normal))
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
                painter.setFont(get_font(9, QFont.Weight.Bold))
                painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
                painter.drawText(QRectF(card_x + 10, card_y + 5, card_w - 65, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_text)

                # Total badge
                painter.setFont(get_font(8, QFont.Weight.DemiBold))
                painter.setPen(QColor("#818CF8" if self.is_dark else "#4F46E5"))
                painter.drawText(QRectF(card_x + card_w - 62, card_y + 5, 52, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, total_badge_text)

                # Divider
                painter.setPen(QPen(QColor("#27272A" if self.is_dark else "#E5E5E7"), 1.0))
                painter.drawLine(QPointF(card_x + 8, card_y + 23), QPointF(card_x + card_w - 8, card_y + 23))

                # Project rows
                curr_y = card_y + 27
                painter.setFont(get_font(8, QFont.Weight.Normal))
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
    """Card containing ProjectComparisonCanvas, title, submetrics, Bar/Area toggle, and color legend."""

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setObjectName("ChartCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row: Title and Mode Switcher
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.lbl_title = QLabel("Statistics")
        self.lbl_title.setFont(get_font(11, QFont.Weight.DemiBold))
        header_row.addWidget(self.lbl_title)
        header_row.addStretch()

        # Bar vs Area toggle buttons (Fixed height and width to prevent stretching)
        self.capsule = QFrame()
        self.capsule.setObjectName("ToggleCapsule")
        self.capsule.setFixedHeight(24)
        self.capsule.setFixedWidth(78)
        capsule_layout = QHBoxLayout(self.capsule)
        capsule_layout.setContentsMargins(2, 2, 2, 2)
        capsule_layout.setSpacing(2)

        self.btn_bar = QPushButton("Bar")
        self.btn_bar.setFixedSize(36, 20)
        self.btn_bar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_bar.clicked.connect(lambda: self._set_mode("bar"))
        capsule_layout.addWidget(self.btn_bar)

        self.btn_area = QPushButton("Area")
        self.btn_area.setFixedSize(36, 20)
        self.btn_area.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_area.clicked.connect(lambda: self._set_mode("area"))
        capsule_layout.addWidget(self.btn_area)

        header_row.addWidget(self.capsule, 0, Qt.AlignmentFlag.AlignVCenter)
        self.capsule.hide()
        layout.addLayout(header_row)

        # Sub-metrics row matching reference design
        self.submetrics_row = QHBoxLayout()
        self.submetrics_row.setSpacing(24)

        m1_col = QVBoxLayout()
        m1_col.setSpacing(1)
        self.lbl_sub1_title = QLabel("Tracked Hours")
        self.lbl_sub1_title.setObjectName("SubmetricTitle")
        self.lbl_sub1_title.setFont(get_font(8, QFont.Weight.Medium))
        self.lbl_sub1_val = QLabel("0.0h")
        self.lbl_sub1_val.setObjectName("SubmetricVal")
        self.lbl_sub1_val.setFont(get_font(13, QFont.Weight.Bold))
        m1_col.addWidget(self.lbl_sub1_title)
        m1_col.addWidget(self.lbl_sub1_val)
        self.submetrics_row.addLayout(m1_col)

        # Backward compatibility placeholder (hidden per user request)
        self.submetric_sep = QFrame()
        self.submetric_sep.hide()

        m2_col = QVBoxLayout()
        m2_col.setSpacing(1)
        self.lbl_sub2_title = QLabel("Peak Period")
        self.lbl_sub2_title.setObjectName("SubmetricTitle")
        self.lbl_sub2_title.setFont(get_font(8, QFont.Weight.Medium))
        self.lbl_sub2_val = QLabel("0.0h")
        self.lbl_sub2_val.setObjectName("SubmetricVal")
        self.lbl_sub2_val.setFont(get_font(13, QFont.Weight.Bold))
        m2_col.addWidget(self.lbl_sub2_title)
        m2_col.addWidget(self.lbl_sub2_val)
        self.submetrics_row.addLayout(m2_col)

        self.submetrics_row.addStretch()
        layout.addLayout(self.submetrics_row)

        # Canvas (Expands to absorb remaining card height)
        self.canvas = ProjectComparisonCanvas(is_dark=self.is_dark, parent=self)
        layout.addWidget(self.canvas, 1)

        # Legend Grid in fixed-height container to preserve static canvas size across filters
        self.legend_container = QWidget(self)
        self.legend_container.setObjectName("LegendContainer")
        self.legend_container.setFixedHeight(38)
        self.legend_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.legend_layout = QGridLayout(self.legend_container)
        self.legend_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_layout.setHorizontalSpacing(8)
        self.legend_layout.setVerticalSpacing(3)
        layout.addWidget(self.legend_container)

        self.apply_theme()
        self._update_toggle_styles()

    def minimumSizeHint(self) -> QSize:
        return QSize(180, 200)

    def sizeHint(self) -> QSize:
        return QSize(340, 340)

    def set_data(
        self,
        series: List[Dict[str, Any]],
        bucket_labels: List[str],
        total_hours: Optional[float] = None,
        change_pct: Optional[float] = None,
    ) -> None:
        self.canvas.set_data(series, bucket_labels)
        self._render_legend(self.canvas.series)

        # Update submetrics
        tot = total_hours if total_hours is not None else sum(s.get("total_hours", 0.0) for s in series)
        self.lbl_sub1_val.setText(f"{tot:.1f}h")

        # Find peak bucket
        peak_h = 0.0
        peak_lbl = ""
        num_b = len(bucket_labels)
        for b_idx in range(num_b):
            b_tot = sum(s.get("hours", [])[b_idx] for s in series if b_idx < len(s.get("hours", [])))
            if b_tot > peak_h:
                peak_h = b_tot
                peak_lbl = bucket_labels[b_idx]
        if peak_h > 0:
            self.lbl_sub2_val.setText(f"{peak_h:.1f}h ({peak_lbl})")
        else:
            self.lbl_sub2_val.setText("0.0h")

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

        for idx, s in enumerate(series[:4]):
            pill = QFrame()
            pill.setObjectName("LegendPill")
            pill.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            pill.setMinimumWidth(0)
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(4, 2, 4, 2)
            pill_layout.setSpacing(4)

            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {s.get('color', '#6366F1')}; border-radius: 3px;")
            pill_layout.addWidget(dot)

            name = s['name']
            if len(name) > 10:
                name = name[:9] + "…"
            name_lbl = QLabel(f"{name} ({s.get('total_hours', 0):.1f}h)")
            name_lbl.setFont(get_font(8, QFont.Weight.Medium))
            name_lbl.setStyleSheet("color: #A1A1AA;" if self.is_dark else "color: #71717A;")
            pill_layout.addWidget(name_lbl)

            s_name = s.get("name", "")
            pill.enterEvent = lambda event, name=s_name: self.canvas.set_spotlight_series(name)
            pill.leaveEvent = lambda event: self.canvas.set_spotlight_series(None)

            row = idx // 2
            col = idx % 2
            self.legend_layout.addWidget(pill, row, col)

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
        self.setFixedSize(160, 160)

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

        inner_r = 38.0
        outer_r = 72.0
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

        base_outer_r = 66.0
        base_inner_r = 44.0
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
            if len(app_name) > 12:
                app_name = app_name[:11] + "…"
            hours = app.get("hours", 0.0)
            pct = app.get("percentage", 0)
            pct_str = f"{int(round(pct))}%" if (isinstance(pct, (int, float)) and pct == int(pct)) else f"{pct}%"
            app_color = QColor(app.get("color", "#3B82F6")).lighter(120 if self.is_dark else 100)

            font_title = get_font(10, QFont.Weight.Bold)
            fm_t = QFontMetrics(font_title)
            if fm_t.horizontalAdvance(app_name) > 68:
                font_title.setPointSize(8)
            painter.setFont(font_title)
            painter.setPen(app_color)
            painter.drawText(QRectF(cx - 36, cy - 14, 72, 16), Qt.AlignmentFlag.AlignCenter, app_name)

            stat_text = f"{hours}h ({pct_str})"
            font_stat = get_font(8, QFont.Weight.DemiBold)
            fm_s = QFontMetrics(font_stat)
            if fm_s.horizontalAdvance(stat_text) > 68:
                font_stat.setPointSize(7)
            painter.setFont(font_stat)
            painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
            painter.drawText(QRectF(cx - 36, cy + 3, 72, 14), Qt.AlignmentFlag.AlignCenter, stat_text)
        else:
            hours_str = f"{self.total_hours}h"
            painter.setFont(get_font(15, QFont.Weight.Bold))
            painter.setPen(QColor("#FAFAFA" if self.is_dark else "#111111"))
            text_rect = QRectF(cx - 36, cy - 14, 72, 18)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, hours_str)

            painter.setFont(get_font(7, QFont.Weight.Medium))
            painter.setPen(QColor("#71717A" if self.is_dark else "#A1A1AA"))
            sub_rect = QRectF(cx - 36, cy + 5, 72, 12)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, "Total Tracked")


# Backward compatibility alias
AppUsageRingCanvas = AppUsageDonutCanvas


class ProjectTargetRow(QFrame):
    """
    Catchy, minimalist project target row matching modern executive dashboard references.
    Displays:
    - Project color dot + name
    - Hours tracked + percentage share
    - Sleek rounded horizontal progress track filled with project's signature color
    - Interactive hover elevation and click-to-drilldown
    """

    clicked = pyqtSignal(str)

    def __init__(
        self,
        project_name: str,
        color: str,
        hours: float,
        pct: int,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.project_name = project_name
        self.color = color
        self.hours = hours
        self.pct = max(0, min(100, pct))
        self.is_dark = is_dark
        self.setObjectName("ProjectTargetRow")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumWidth(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(3)

        # Line 1: Dot + Name, Right: Hours & %
        header = QHBoxLayout()
        header.setSpacing(6)

        dot = QFrame()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background-color: {self.color}; border-radius: 3px;")
        header.addWidget(dot)

        self.lbl_name = QLabel(self.project_name)
        self.lbl_name.setFont(get_font(9, QFont.Weight.DemiBold))
        self.lbl_name.setMinimumWidth(0)
        header.addWidget(self.lbl_name, 1)

        stat_str = f"{self.hours:.1f}h ({self.pct}%)" if self.hours > 0 else f"{self.pct}%"
        self.lbl_stat = QLabel(stat_str)
        self.lbl_stat.setFont(get_font(8, QFont.Weight.Medium))
        self.lbl_stat.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_stat.setMinimumWidth(0)
        header.addWidget(self.lbl_stat)

        layout.addLayout(header)

        # Line 2: Rounded Progress Track
        self.prog = QProgressBar(self)
        self.prog.setFixedHeight(5)
        self.prog.setMinimumWidth(0)
        self.prog.setRange(0, 100)
        self.prog.setValue(self.pct)
        self.prog.setTextVisible(False)
        layout.addWidget(self.prog)

        self.apply_theme()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_name)
        super().mousePressEvent(event)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.apply_theme()

    def apply_theme(self) -> None:
        bg_hover = "#2A2A2F" if self.is_dark else "#F4F4F5"
        border_hover = "#3F3F46" if self.is_dark else "#E5E0D8"
        text_color = "#F4F4F6" if self.is_dark else "#18181B"
        stat_color = "#A1A1AA" if self.is_dark else "#71717A"
        prog_bg = "#333338" if self.is_dark else "#E5E0D8"

        self.setStyleSheet(f"""
            QFrame#ProjectTargetRow {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QFrame#ProjectTargetRow:hover {{
                background-color: {bg_hover};
                border: 1px solid {border_hover};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
            QProgressBar {{
                background-color: {prog_bg};
                border: none;
                border-radius: 2.5px;
            }}
            QProgressBar::chunk {{
                background-color: {self.color};
                border-radius: 2.5px;
            }}
        """)
        self.lbl_name.setStyleSheet(f"color: {text_color};")
        self.lbl_stat.setStyleSheet(f"color: {stat_color};")


class ProjectTrackingWidget(QFrame):
    """
    Dedicated Project Tracking card matching executive dashboard reference.
    Displays:
    - Header with title 'Project Tracking' and active count badge (e.g. '3 Active')
    - Concise subtitle: 'Target vs Actual progress'
    - Vertical list of ProjectTargetRow items with progress tracks
    - Interactive hover elevation and click-to-drilldown
    """

    project_selected = pyqtSignal(str)
    new_project_clicked = pyqtSignal()

    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.projects_data: List[Dict[str, Any]] = []
        self.total_hours: float = 0.0
        self.setObjectName("ProjectTrackingCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row: Title + Active Badge
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(4)

        self.lbl_title = QLabel("Project Tracking")
        self.lbl_title.setFont(get_font(10, QFont.Weight.DemiBold))
        header_row.addWidget(self.lbl_title)
        header_row.addStretch()

        self.lbl_targets_count = QLabel("0 Active")
        self.lbl_targets_count.setObjectName("TargetsBadge")
        self.lbl_targets_count.setFont(get_font(8, QFont.Weight.Medium))
        header_row.addWidget(self.lbl_targets_count)

        layout.addLayout(header_row)

        self.lbl_subtitle = QLabel("Target vs Actual progress")
        self.lbl_subtitle.setFont(get_font(8))
        layout.addWidget(self.lbl_subtitle)

        # Scroll Area for Target Rows
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("ProjectTrackingScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container inside Scroll Area
        self.targets_container = QWidget()
        self.targets_container.setObjectName("ProjectTrackingContainer")
        self.targets_layout = QVBoxLayout(self.targets_container)
        self.targets_layout.setContentsMargins(0, 0, 4, 0)
        self.targets_layout.setSpacing(4)
        self.scroll_area.setWidget(self.targets_container)

        layout.addWidget(self.scroll_area, 1)

        self.apply_theme()

    def minimumSizeHint(self) -> QSize:
        return QSize(180, 160)

    def sizeHint(self) -> QSize:
        return QSize(240, 228)

    def set_project_targets(self, projects: List[Dict[str, Any]], total_hours: float) -> None:
        """Render catchy minimalist project progress targets matching reference design."""
        self.projects_data = projects
        self.total_hours = total_hours

        # Clear existing rows
        while self.targets_layout.count() > 0:
            item = self.targets_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        active_projects = [p for p in projects if p.get("tracked_minutes", 0) > 0 or p.get("total_tasks", 0) > 0]
        display_projects = active_projects if active_projects else projects

        self.lbl_targets_count.setText(f"{len(projects)} Active")

        if not display_projects:
            empty = QLabel("No active projects. Click '+ New Project' to start.")
            empty.setFont(get_font(8))
            empty.setStyleSheet("color: #71717A; padding: 6px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.targets_layout.addWidget(empty)
            self.targets_layout.addStretch()
            return

        for p in display_projects:
            mins = p.get("tracked_minutes", 0.0)
            h = mins / 60.0
            pct = int(round((h / total_hours * 100))) if total_hours > 0 else int(round(p.get("completion_rate", 0.0) * 100))
            row = ProjectTargetRow(
                project_name=p["name"],
                color=p.get("color", "#6366F1"),
                hours=h,
                pct=pct,
                is_dark=self.is_dark,
                parent=self.targets_container,
            )
            row.clicked.connect(self.project_selected.emit)
            self.targets_layout.addWidget(row)

        self.targets_layout.addStretch()

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.apply_theme()
        if hasattr(self, "projects_data"):
            self.set_project_targets(self.projects_data, self.total_hours)

    def apply_theme(self) -> None:
        bg = "#242427" if self.is_dark else "#FFFFFF"
        border = "#333338" if self.is_dark else "#E5E0D8"
        hover_border = "#4A4A54" if self.is_dark else "#D4CEBF"
        title_color = "#F4F4F6" if self.is_dark else "#111111"
        sub_color = "#A1A1AA" if self.is_dark else "#71717A"
        badge_bg = "#1F1F22" if self.is_dark else "#F4F4F5"
        badge_border = "#333338" if self.is_dark else "#E5E0D8"
        badge_color = "#A1A1AA" if self.is_dark else "#71717A"
        scrollbar_thumb = "#3F3F46" if self.is_dark else "#D4CEBF"
        scrollbar_thumb_hover = "#52525B" if self.is_dark else "#A1A1AA"

        self.lbl_subtitle.setStyleSheet(f"color: {sub_color};")
        self.setStyleSheet(f"""
            QFrame#ProjectTrackingCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame#ProjectTrackingCard:hover {{
                border: 1px solid {hover_border};
            }}
            QLabel {{
                color: {title_color};
            }}
            QLabel#TargetsBadge {{
                background-color: {badge_bg};
                color: {badge_color};
                border: 1px solid {badge_border};
                border-radius: 6px;
                padding: 1px 6px;
            }}
            QScrollArea#ProjectTrackingScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget#ProjectTrackingContainer {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {scrollbar_thumb};
                min-height: 20px;
                border-radius: 2.5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {scrollbar_thumb_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)


class AppUsageAnalyticsWidget(QFrame):
    """
    Combined Application Distribution & Project Targets Card matching reference design.
    Upper Section: Application Distribution (Donut Chart or Bar Chart).
    Lower Section: Catchy, minimalist Project Targets with colored progress tracks.
    """

    project_selected = pyqtSignal(str)
    new_project_clicked = pyqtSignal()

    def __init__(
        self,
        is_dark: bool = True,
        show_targets: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.is_dark = is_dark
        self.show_targets = show_targets
        self.active_mode = "donut"  # 'donut' or 'bar'
        self.apps_data: List[Dict[str, Any]] = []
        self.projects_data: List[Dict[str, Any]] = []
        self.total_hours: float = 0.0
        self.setObjectName("AppUsageCard")
        if not self.show_targets:
            self.setFixedHeight(296)
        self.setMinimumWidth(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row: Title & Toggle
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self.lbl_title = QLabel("Distribution")
        self.lbl_title.setFont(get_font(11, QFont.Weight.DemiBold))
        header_row.addWidget(self.lbl_title)
        header_row.addStretch()

        # Capsule Switcher: Donut vs Bar (properly sized to prevent text truncation)
        self.capsule = QFrame()
        self.capsule.setObjectName("ToggleCapsule")
        self.capsule.setFixedHeight(24)
        self.capsule.setFixedWidth(88)
        capsule_layout = QHBoxLayout(self.capsule)
        capsule_layout.setContentsMargins(2, 2, 2, 2)
        capsule_layout.setSpacing(2)

        self.btn_donut = QPushButton("Donut")
        self.btn_donut.setFixedSize(42, 20)
        self.btn_donut.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_donut.clicked.connect(lambda: self._set_mode("donut"))
        capsule_layout.addWidget(self.btn_donut)

        # Backward compatibility alias
        self.btn_ring = self.btn_donut

        self.btn_bar = QPushButton("Bar")
        self.btn_bar.setFixedSize(38, 20)
        self.btn_bar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_bar.clicked.connect(lambda: self._set_mode("bar"))
        capsule_layout.addWidget(self.btn_bar)

        header_row.addWidget(self.capsule, 0, Qt.AlignmentFlag.AlignVCenter)
        self.capsule.hide()
        layout.addLayout(header_row)

        # Upper Section: Stacked Views (Donut vs Bar)
        self.stack = QStackedWidget(self)

        # 1. Donut View Container
        self.donut_page = QWidget()
        donut_page_layout = QVBoxLayout(self.donut_page)
        donut_page_layout.setContentsMargins(0, 0, 0, 0)
        donut_page_layout.setSpacing(3)
        donut_page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Donut Canvas centered
        donut_center_row = QHBoxLayout()
        donut_center_row.setContentsMargins(0, 0, 0, 0)
        donut_center_row.addStretch()
        self.donut_canvas = AppUsageDonutCanvas(is_dark=self.is_dark, parent=self.donut_page)
        donut_center_row.addWidget(self.donut_canvas)
        donut_center_row.addStretch()
        donut_page_layout.addLayout(donut_center_row)

        # Backward compatibility alias
        self.ring_page = self.donut_page
        self.ring_canvas = self.donut_canvas

        # Compact 2-column micro legend for top apps
        self.donut_list_layout = QGridLayout()
        self.donut_list_layout.setContentsMargins(0, 0, 0, 0)
        self.donut_list_layout.setHorizontalSpacing(6)
        self.donut_list_layout.setVerticalSpacing(2)
        donut_page_layout.addLayout(self.donut_list_layout)

        # Backward compatibility alias
        self.ring_list_layout = self.donut_list_layout

        self.stack.addWidget(self.donut_page)

        # 2. Bar View Container
        self.bar_page = QWidget()
        self.bar_page_layout = QVBoxLayout(self.bar_page)
        self.bar_page_layout.setContentsMargins(0, 2, 0, 2)
        self.bar_page_layout.setSpacing(4)
        self.stack.addWidget(self.bar_page)

        layout.addWidget(self.stack)

        # Divider between Apps and Projects
        self.divider = QFrame()
        self.divider.setFixedHeight(1)
        self.divider.setObjectName("SectionDivider")
        layout.addWidget(self.divider)

        # Lower Section: Project Targets
        self.targets_header = QWidget()
        targets_header_layout = QHBoxLayout(self.targets_header)
        targets_header_layout.setContentsMargins(0, 0, 0, 0)
        targets_header_layout.setSpacing(6)

        self.lbl_targets_title = QLabel("Project Targets")
        self.lbl_targets_title.setFont(get_font(10, QFont.Weight.DemiBold))
        targets_header_layout.addWidget(self.lbl_targets_title)
        targets_header_layout.addStretch()

        self.lbl_targets_count = QLabel("0 Active")
        self.lbl_targets_count.setObjectName("TargetsBadge")
        self.lbl_targets_count.setFont(get_font(8, QFont.Weight.Medium))
        targets_header_layout.addWidget(self.lbl_targets_count)
        layout.addWidget(self.targets_header)

        self.targets_container = QWidget()
        self.targets_layout = QVBoxLayout(self.targets_container)
        self.targets_layout.setContentsMargins(0, 0, 0, 0)
        self.targets_layout.setSpacing(4)
        layout.addWidget(self.targets_container)

        if not self.show_targets:
            self.divider.hide()
            self.targets_header.hide()
            self.targets_container.hide()
            layout.addStretch()

        self.apply_theme()
        self._update_toggle_styles()

    def minimumSizeHint(self) -> QSize:
        if not self.show_targets:
            return QSize(180, 296)
        return QSize(180, 280)

    def sizeHint(self) -> QSize:
        if not self.show_targets:
            return QSize(240, 296)
        return QSize(260, 360)

    def set_data(self, apps_data: List[Dict[str, Any]], total_hours: float) -> None:
        self.apps_data = apps_data
        self.total_hours = total_hours
        self.donut_canvas.set_data(apps_data, total_hours)
        self._render_donut_app_list(apps_data)
        self._render_bar_app_list(apps_data)

    def set_project_targets(self, projects: List[Dict[str, Any]], total_hours: float) -> None:
        """Render catchy minimalist project progress targets matching reference design."""
        self.projects_data = projects
        self.total_hours = total_hours

        # Clear existing rows
        while self.targets_layout.count() > 0:
            item = self.targets_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        active_projects = [p for p in projects if p.get("tracked_minutes", 0) > 0 or p.get("total_tasks", 0) > 0]
        if not active_projects and projects:
            active_projects = projects[:3]
        display_projects = active_projects[:3] if active_projects else projects[:3]

        self.lbl_targets_count.setText(f"{len(projects)} Active")

        if not display_projects:
            empty = QLabel("No active projects. Click '+ New Project' to start.")
            empty.setFont(get_font(8))
            empty.setStyleSheet("color: #71717A; padding: 6px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.targets_layout.addWidget(empty)
            return

        for p in display_projects:
            mins = p.get("tracked_minutes", 0.0)
            h = mins / 60.0
            pct = int(round((h / total_hours * 100))) if total_hours > 0 else int(round(p.get("completion_rate", 0.0) * 100))
            row = ProjectTargetRow(
                project_name=p["name"],
                color=p.get("color", "#6366F1"),
                hours=h,
                pct=pct,
                is_dark=self.is_dark,
                parent=self.targets_container,
            )
            row.clicked.connect(self.project_selected.emit)
            self.targets_layout.addWidget(row)

    def _set_mode(self, mode: str) -> None:
        if mode in ("donut", "ring"):
            self.active_mode = "donut"
            self.stack.setCurrentWidget(self.donut_page)
        else:
            self.active_mode = "bar"
            self.stack.setCurrentWidget(self.bar_page)
        self._update_toggle_styles()

    def _render_donut_app_list(self, apps: List[Dict[str, Any]]) -> None:
        while self.donut_list_layout.count() > 0:
            item = self.donut_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not apps:
            empty = QLabel("No app activity")
            empty.setFont(get_font(8))
            empty.setStyleSheet("color: #71717A; padding: 2px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.donut_list_layout.addWidget(empty)
            return

        for idx, app in enumerate(apps[:3]):
            row_frame = QFrame()
            row_frame.setObjectName("AppDonutRow")
            row_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            row_frame.setMinimumWidth(0)
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(2, 1, 2, 1)
            row.setSpacing(2)

            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {app.get('color', '#3B82F6')}; border-radius: 3px;")
            row.addWidget(dot)

            app_name = app["app_name"]
            if len(app_name) > 10:
                app_name = app_name[:9] + "…"
            name_lbl = QLabel(app_name)
            name_lbl.setFont(get_font(8, QFont.Weight.Medium))
            row.addWidget(name_lbl)

            pct_lbl = QLabel(f"{int(round(app.get('percentage', 0)))}%")
            pct_lbl.setFont(get_font(8, QFont.Weight.DemiBold))
            pct_color = "#10B981" if self.is_dark else "#059669"
            pct_lbl.setStyleSheet(f"color: {pct_color};")
            row.addWidget(pct_lbl)

            row_frame.enterEvent = lambda event, i=idx: self.donut_canvas.set_hovered_segment(i)
            row_frame.leaveEvent = lambda event: self.donut_canvas.set_hovered_segment(None)

            if idx == 2:
                self.donut_list_layout.addWidget(row_frame, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
            else:
                self.donut_list_layout.addWidget(row_frame, 0, idx)

    # Backward compatibility alias
    _render_ring_app_list = _render_donut_app_list

    def _render_bar_app_list(self, apps: List[Dict[str, Any]]) -> None:
        while self.bar_page_layout.count() > 0:
            item = self.bar_page_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not apps:
            empty = QLabel("No application activity recorded.")
            empty.setFont(get_font(8))
            empty.setStyleSheet("color: #71717A; padding: 10px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bar_page_layout.addWidget(empty)
            return

        for app in apps[:3]:
            item_frame = QFrame()
            item_frame.setObjectName("AppUsageBarItem")
            item_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            item_frame.setMinimumWidth(0)
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(6, 2, 6, 2)
            item_layout.setSpacing(2)

            row = QHBoxLayout()
            row.setSpacing(5)

            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {app.get('color', '#3B82F6')}; border-radius: 3px;")
            row.addWidget(dot)

            name_lbl = QLabel(app["app_name"])
            name_lbl.setFont(get_font(8, QFont.Weight.Medium))
            row.addWidget(name_lbl, 1)

            stat_lbl = QLabel(f"{app.get('hours', 0.0)}h ({app.get('percentage', 0)}%)")
            stat_lbl.setFont(get_font(8, QFont.Weight.DemiBold))
            stat_lbl.setStyleSheet("color: #A1A1AA;" if self.is_dark else "color: #71717A;")
            stat_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(stat_lbl)

            item_layout.addLayout(row)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(round(app.get("percentage", 0.0))))
            bar.setTextVisible(False)
            bar.setFixedHeight(5)

            bar_bg = "#333338" if self.is_dark else "#E5E0D8"
            bar_color = app.get("color", "#3B82F6")
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {bar_bg};
                    border: none;
                    border-radius: 2.5px;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                    border-radius: 2.5px;
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
        if hasattr(self, "projects_data"):
            self.set_project_targets(self.projects_data, self.total_hours)

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
        divider_color = "#333338" if self.is_dark else "#E5E0D8"
        badge_bg = "#1F1F22" if self.is_dark else "#F4F4F5"
        badge_border = "#333338" if self.is_dark else "#E5E0D8"
        badge_color = "#A1A1AA" if self.is_dark else "#71717A"

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
            QFrame#SectionDivider {{
                background-color: {divider_color};
                border: none;
            }}
            QLabel {{
                color: {title_color};
            }}
            QLabel#TargetsBadge {{
                background-color: {badge_bg};
                color: {badge_color};
                border: 1px solid {badge_border};
                border-radius: 6px;
                padding: 1px 6px;
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
                border-radius: 6px;
            }}
            QFrame#AppUsageBarItem:hover {{
                background-color: {"#2A2A2E" if self.is_dark else "#FAF8F5"};
                border: 1px solid {"#3F3F46" if self.is_dark else "#E5E0D8"};
            }}
        """)


