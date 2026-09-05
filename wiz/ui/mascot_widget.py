"""High-DPI SVG mascot renderer widget with smooth state rendering and animations."""

import math
from typing import Dict, Optional
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtProperty, QPointF
from PyQt6.QtGui import QPainter, QPaintEvent, QPen, QColor
from PyQt6.QtWidgets import QWidget
from PyQt6.QtSvg import QSvgRenderer

from wiz.core.config import config
from wiz.core.state_machine import MascotState, StateMachine


class MascotWidget(QWidget):
    """
    Renders the Wiz ghost mascot SVG with high-DPI scaling,
    smooth floating bob animation, and dynamic eye rotation in working state.
    """

    def __init__(self, state_machine: StateMachine, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state_machine = state_machine

        # SVG Renderers cache for each mascot state
        self._renderers: Dict[MascotState, QSvgRenderer] = {}
        self._load_svg_renderers()

        # Animation states
        self._float_offset: float = 0.0  # Vertical bob offset in pixels
        self._time_elapsed: float = 0.0
        self._spinner_angle: float = 0.0  # Rotation angle for working state eyes

        # Main animation timer (60 FPS ~ 16ms)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._update_animation)
        self._anim_timer.start()

        # Connect to state changes
        self.state_machine.state_changed.connect(self._on_state_changed)

        # Widget styling
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def _load_svg_renderers(self) -> None:
        """Load and cache QSvgRenderer for each mascot state."""
        for state in MascotState:
            asset_path = config.get_asset_path(state.asset_filename)
            if asset_path.exists():
                renderer = QSvgRenderer(str(asset_path))
                if renderer.isValid():
                    self._renderers[state] = renderer
                else:
                    print(f"[MascotWidget] Warning: SVG invalid for state {state.value} at {asset_path}")
            else:
                print(f"[MascotWidget] Warning: SVG not found for state {state.value} at {asset_path}")

    @pyqtProperty(float)
    def float_offset(self) -> float:
        """Vertical floating offset in pixels."""
        return self._float_offset

    @float_offset.setter
    def float_offset(self, value: float) -> None:
        self._float_offset = value
        self.update()

    def _update_animation(self) -> None:
        """Tick animation clock: updates floating sine wave and spinner eye angle."""
        if config.get("enable_floating_animation", True):
            self._time_elapsed += 0.035
            # Gentle 4px sine floating wave (period ~ 2.8s)
            self._float_offset = math.sin(self._time_elapsed) * 4.0
        else:
            self._float_offset = 0.0

        # Rotate spinner eyes if in WORKING state
        if self.state_machine.current_state == MascotState.WORKING:
            self._spinner_angle = (self._spinner_angle + 4.0) % 360.0

        self.update()

    def _on_state_changed(self, new_state: MascotState, old_state: MascotState) -> None:
        """Trigger immediate repaint upon state change."""
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render the mascot SVG scaled smoothly to the widget bounds with float offset."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        current_state = self.state_machine.current_state
        renderer = self._renderers.get(current_state) or self._renderers.get(MascotState.IDLE)

        if not renderer:
            painter.end()
            return

        w = float(self.width())
        h = float(self.height())

        # Keep original 200:240 aspect ratio centered
        target_aspect = 200.0 / 240.0
        widget_aspect = w / h

        if widget_aspect > target_aspect:
            # Constrained by height
            draw_h = h - 16.0  # margin for float bob
            draw_w = draw_h * target_aspect
        else:
            # Constrained by width
            draw_w = w - 16.0
            draw_h = draw_w / target_aspect

        x = (w - draw_w) / 2.0
        y = (h - draw_h) / 2.0 + self._float_offset

        target_rect = QRectF(x, y, draw_w, draw_h)

        if current_state == MascotState.WORKING:
            # Render base mascot from working SVG or idle SVG
            # In working SVG, render base body and dynamically rotate dashed spinner eyes
            self._render_working_state(painter, target_rect, draw_w, draw_h)
        else:
            # Render standard SVG for current state
            renderer.render(painter, target_rect)

        painter.end()

    def _render_working_state(self, painter: QPainter, target_rect: QRectF, draw_w: float, draw_h: float) -> None:
        """Render the working state with smoothly rotating dashed spinner eyes."""
        # First render the base idle body
        idle_renderer = self._renderers.get(MascotState.IDLE)
        if idle_renderer:
            idle_renderer.render(painter, target_rect)

        # Scale factors from 200x240 SVG viewBox to draw bounds
        scale_x = draw_w / 200.0
        scale_y = draw_h / 240.0

        # Overwrite the idle black eyes with ivory cover circles, then draw rotating dashed spinner circles
        # Eye centers in 200x240 viewBox: (82, 128) and (118, 128)
        left_eye = QPointF(target_rect.x() + 82.0 * scale_x, target_rect.y() + 128.0 * scale_y)
        right_eye = QPointF(target_rect.x() + 118.0 * scale_x, target_rect.y() + 128.0 * scale_y)
        eye_r = 9.0 * scale_x
        cover_r = 10.0 * scale_x

        # Cover idle eyes with body color (#F7F3EA)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F7F3EA"))
        painter.drawEllipse(left_eye, cover_r, cover_r)
        painter.drawEllipse(right_eye, cover_r, cover_r)

        # Draw rotating spinner eyes
        stroke_w = max(2.5, 5.0 * scale_x)
        pen = QPen(QColor("#5B564C"), stroke_w, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.RoundCap)
        # 20 on, 13 off pattern scaled
        pen.setDashPattern([3.5, 2.3])
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Left eye rotation
        painter.save()
        painter.translate(left_eye)
        painter.rotate(self._spinner_angle)
        painter.drawEllipse(QPointF(0, 0), eye_r, eye_r)
        painter.restore()

        # Right eye rotation (offset by 90 degrees for organic twin feel)
        painter.save()
        painter.translate(right_eye)
        painter.rotate(self._spinner_angle + 90.0)
        painter.drawEllipse(QPointF(0, 0), eye_r, eye_r)
        painter.restore()
