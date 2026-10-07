"""
High-precision animated toggle switch widget for WizDesk UI.
Matches Untitled UI design standards with smooth sliding animation,
tactile drop shadow, anti-aliased pill track, and full keyboard/mouse interaction.
"""

from typing import Optional
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QPainter, QCursor, QMouseEvent, QKeyEvent, QPen
from PyQt6.QtWidgets import QWidget


class _CallableBool(int):
    """Integer subclass that can be invoked as a function returning its boolean truth value.

    Ensures both property-style access (`if switch.isChecked:`) and
    Qt method-style access (`if switch.isChecked():`) evaluate accurately.
    """

    def __call__(self) -> bool:
        return bool(self)


class ToggleSwitch(QWidget):
    """Modern iOS/Untitled UI style toggle switch with smooth animated thumb transitions."""

    toggled = pyqtSignal(bool)

    def __init__(
        self,
        checked: bool = False,
        parent: Optional[QWidget] = None,
        is_dark: bool = False,
        width: int = 38,
        height: int = 22,
    ):
        super().__init__(parent)
        self._checked: bool = bool(checked)
        self._thumb_pos: float = 1.0 if self._checked else 0.0
        self.is_dark: bool = is_dark
        self._is_hovered: bool = False
        self._width: int = width
        self._height: int = height

        self.setFixedSize(self._width, self._height)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("background: transparent;")

        # Smooth slide transition animation
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_thumb_position(self) -> float:
        return self._thumb_pos

    def set_thumb_position(self, pos: float) -> None:
        self._thumb_pos = pos
        self.update()

    thumb_position = pyqtProperty(float, get_thumb_position, set_thumb_position)

    @property
    def isChecked(self) -> _CallableBool:
        """Return boolean callable state compatible with both property and method syntax."""
        return _CallableBool(1 if self._checked else 0)

    def setChecked(self, value: bool) -> None:
        """Set the switch state and trigger smooth animation if changed."""
        val = bool(value)
        if self._checked != val:
            self._checked = val
            self._anim.stop()
            self._anim.setStartValue(self._thumb_pos)
            self._anim.setEndValue(1.0 if self._checked else 0.0)
            self._anim.start()
            self.toggled.emit(self._checked)

    def set_dark_mode(self, is_dark: bool) -> None:
        """Update dark mode state and refresh visuals."""
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.update()

    def set_theme(self, is_dark: bool) -> None:
        """Alias for set_dark_mode for unified theme synchronization."""
        self.set_dark_mode(is_dark)

    def enterEvent(self, event) -> None:
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.setChecked(not self._checked)
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pos = max(0.0, min(1.0, self._thumb_pos))
        w = float(self._width)
        h = float(self._height)
        corner_radius = h / 2.0

        # Dynamic track colors with smooth active interpolation
        if self.is_dark:
            off_bg = QColor("#52525B") if self._is_hovered else QColor("#3F3F46")
            on_bg = QColor("#EA580C") if self._is_hovered else QColor("#C2410C")
        else:
            off_bg = QColor("#D4D4D8") if self._is_hovered else QColor("#E4E4E7")
            on_bg = QColor("#C2410C") if self._is_hovered else QColor("#BA3F1A")

        # Linear RGB color blend across animation curve
        r = int(off_bg.red() + pos * (on_bg.red() - off_bg.red()))
        g = int(off_bg.green() + pos * (on_bg.green() - off_bg.green()))
        b = int(off_bg.blue() + pos * (on_bg.blue() - off_bg.blue()))
        track_color = QColor(r, g, b)

        track_rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, corner_radius, corner_radius)

        # Subtle border for light mode inactive state
        if not self.is_dark and pos < 0.2:
            border_pen = QPen(QColor("#D4D4D8"), 1.0)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(track_rect, corner_radius, corner_radius)

        # Focus ring when navigated via keyboard
        if self.hasFocus():
            focus_pen = QPen(QColor("#C2410C" if self.is_dark else "#BA3F1A"), 1.5)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(1.0, 1.0, w - 2.0, h - 2.0), corner_radius, corner_radius)

        # Thumb metrics
        padding = 3.0
        thumb_diameter = h - (padding * 2.0)
        travel_dist = w - thumb_diameter - (padding * 2.0)
        thumb_x = padding + (pos * travel_dist)
        thumb_y = padding

        # Tactile drop shadow below thumb
        painter.setPen(Qt.PenStyle.NoPen)
        shadow_color = QColor(0, 0, 0, 40 if not self.is_dark else 60)
        painter.setBrush(shadow_color)
        painter.drawEllipse(QRectF(thumb_x, thumb_y + 1.0, thumb_diameter, thumb_diameter))

        # White circular thumb
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(thumb_x, thumb_y, thumb_diameter, thumb_diameter))

        painter.end()
