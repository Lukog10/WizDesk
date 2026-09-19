"""Shared custom rounded-square checkbox widget for WizDesk UI."""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QCursor, QMouseEvent
from PyQt6.QtWidgets import QWidget


class _CallableBool(int):
    """Integer subclass that can be invoked as a function returning its boolean truth value."""
    def __call__(self) -> bool:
        return bool(self)


class RoundedCheckbox(QWidget):
    """Custom rounded-square checkbox widget with high-precision anti-aliased rendering and dark mode support."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, size: int = 20, parent: Optional[QWidget] = None, is_dark: bool = False):
        super().__init__(parent)
        self._checked = checked
        self._size = size
        self.is_dark = is_dark
        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    @property
    def isChecked(self) -> _CallableBool:
        return _CallableBool(1 if self._checked else 0)

    def setChecked(self, value: bool) -> None:
        if self._checked != value:
            self._checked = value
            self.update()
            self.toggled.emit(self._checked)

    def set_dark_mode(self, is_dark: bool) -> None:
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.update()

    def set_theme(self, is_dark: bool) -> None:
        """Alias for set_dark_mode to support theme switching calls."""
        self.set_dark_mode(is_dark)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        margin = 2.0
        s = float(self._size) - (margin * 2)
        rect = QRectF(margin, margin, s, s)
        radius = 4.0 if self._size >= 18 else 3.0

        if self._checked:
            # Brand deeper accent filled rounded square with white checkmark
            bg_color = QColor("#C2410C") if self.is_dark else QColor("#BA3F1A")
            check_color = QColor("#FFFFFF")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(rect, radius, radius)

            # Draw checkmark path scaled to size
            scale = self._size / 20.0
            pen = QPen(check_color, 1.8 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            p1_x = rect.x() + (4.5 * scale)
            p1_y = rect.y() + (8.5 * scale)
            p2_x = rect.x() + (7.5 * scale)
            p2_y = rect.y() + (11.5 * scale)
            p3_x = rect.x() + (12.0 * scale)
            p3_y = rect.y() + (5.0 * scale)
            painter.drawLine(int(p1_x), int(p1_y), int(p2_x), int(p2_y))
            painter.drawLine(int(p2_x), int(p2_y), int(p3_x), int(p3_y))
        else:
            # Clean subtle rounded outline
            border_color = QColor("#52525B") if self.is_dark else QColor("#C8C2B6")
            bg_color = QColor("#27272A") if self.is_dark else QColor("#EDE9E0")

            pen = QPen(border_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()
