"""Custom QComboBox with crisp painted down arrow for consistent theme rendering."""

from typing import Optional
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPolygonF, QColor, QBrush
from PyQt6.QtWidgets import QComboBox, QWidget


class ArrowComboBox(QComboBox):
    """
    QComboBox subclass that draws a crisp, antialiased down arrow (chevron)
    in paintEvent, ensuring a visible arrow regardless of Qt stylesheet overrides.
    """

    def __init__(self, parent: Optional[QWidget] = None, is_dark: bool = True):
        super().__init__(parent)
        self.is_dark: bool = is_dark

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        arrow_color = QColor("#A1A1AA") if getattr(self, "is_dark", True) else QColor("#71717A")

        w = self.width()
        h = self.height()
        arrow_w = 7.0
        arrow_h = 4.5
        center_x = w - 12.0
        center_y = h / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(arrow_color))
        poly = QPolygonF([
            QPointF(center_x - arrow_w / 2.0, center_y - arrow_h / 2.0),
            QPointF(center_x + arrow_w / 2.0, center_y - arrow_h / 2.0),
            QPointF(center_x, center_y + arrow_h / 2.0),
        ])
        painter.drawPolygon(poly)
        painter.end()
