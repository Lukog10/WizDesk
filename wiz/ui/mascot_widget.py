"""High-DPI SVG mascot renderer widget with smooth state rendering, cursor gaze tracking, and animations."""

import math
from typing import Dict, Optional
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtProperty, QPointF
from PyQt6.QtGui import QPainter, QPaintEvent, QPen, QColor, QCursor
from PyQt6.QtWidgets import QWidget
from PyQt6.QtSvg import QSvgRenderer

from wiz.core.config import config
from wiz.core.state_machine import MascotState, StateMachine


class MascotWidget(QWidget):
    """
    Renders the Wiz ghost mascot SVG with high-DPI scaling,
    smooth floating bob animation, real-time cursor eye-tracking in Monitor/Idle mode,
    and delicate thin spinning eyes in work logging mode.
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

        # Cursor eye-tracking state (in SVG 200x240 coordinates)
        self._eye_ox: float = 0.0
        self._eye_oy: float = 0.0

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
        """Vertical bob offset in pixels."""
        return self._float_offset

    @float_offset.setter
    def float_offset(self, val: float) -> None:
        self._float_offset = val
        self.update()

    def _update_animation(self) -> None:
        """60 FPS tick updating float bob, cursor gaze lerp, and spinner angle."""
        self._time_elapsed += 0.016

        # Continuous floating bob
        if config.get("enable_floating_animation", True):
            # Slow, organic breathing sine wave ~ 4s period, ±4px offset
            self._float_offset = math.sin(self._time_elapsed * 1.6) * 4.0
        else:
            self._float_offset = 0.0

        # Cursor gaze calculation
        try:
            cursor_pos = QCursor.pos()
            # Widget center in global screen coordinates
            center_global = self.mapToGlobal(self.rect().center())
            dx = float(cursor_pos.x() - center_global.x())
            dy = float(cursor_pos.y() - center_global.y())
            dist = math.hypot(dx, dy)

            # Max socket radius in SVG coordinates
            max_socket_r = 3.6
            if dist > 2.0:
                # Gaze smoothly saturates as cursor moves further away (up to 450px)
                reach = min(1.0, dist / 450.0)
                target_ox = (dx / dist) * max_socket_r * reach
                target_oy = (dy / dist) * max_socket_r * reach
            else:
                target_ox = 0.0
                target_oy = 0.0

            # Smooth exponential damping (lerp) for natural eye movement
            self._eye_ox += (target_ox - self._eye_ox) * 0.22
            self._eye_oy += (target_oy - self._eye_oy) * 0.22
        except Exception:
            self._eye_ox = 0.0
            self._eye_oy = 0.0

        # Working spinner rotation (spin speed: 3.5 deg per frame)
        if self.state_machine.current_state == MascotState.WORKING:
            self._spinner_angle = (self._spinner_angle + 3.5) % 360.0

        self.update()

    def _on_state_changed(self, new_state: MascotState, old_state: MascotState) -> None:
        """Trigger immediate repaint upon state change."""
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render the mascot SVG scaled smoothly to the widget bounds with float offset and eye tracking."""
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

        if current_state == MascotState.IDLE:
            # Render Monitor state with real-time cursor eye tracking
            self._render_idle_monitor_state(painter, target_rect, draw_w, draw_h)
        elif current_state == MascotState.WORKING:
            # Render Work logging state with thin spinning arcs
            self._render_working_state(painter, target_rect, draw_w, draw_h)
        else:
            # Render standard expressive SVG for NOTIFY, COMPLETE, SLEEP
            renderer.render(painter, target_rect)

        painter.end()

    def _render_idle_monitor_state(self, painter: QPainter, target_rect: QRectF, draw_w: float, draw_h: float) -> None:
        """Render IDLE / Monitor state with dot pupils dynamically following cursor movement."""
        idle_renderer = self._renderers.get(MascotState.IDLE)
        if idle_renderer:
            idle_renderer.render(painter, target_rect)

        # Scale factors from 200x240 SVG viewBox to draw bounds
        scale_x = draw_w / 200.0
        scale_y = draw_h / 240.0

        # Base eye centers in 200x240 viewBox: (82, 128) and (118, 128)
        left_eye_center = QPointF(target_rect.x() + 82.0 * scale_x, target_rect.y() + 128.0 * scale_y)
        right_eye_center = QPointF(target_rect.x() + 118.0 * scale_x, target_rect.y() + 128.0 * scale_y)

        # 1. Cover static SVG eye circles with body color (#F7F3EA)
        cover_r = 8.5 * scale_x
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F7F3EA"))
        painter.drawEllipse(left_eye_center, cover_r, cover_r)
        painter.drawEllipse(right_eye_center, cover_r, cover_r)

        # 2. Draw dynamic tracking pupils with smooth gaze offset
        gaze_offset = QPointF(self._eye_ox * scale_x, self._eye_oy * scale_y)
        pupil_r = 6.2 * scale_x

        painter.setBrush(QColor("#111111"))
        painter.drawEllipse(left_eye_center + gaze_offset, pupil_r, pupil_r)
        painter.drawEllipse(right_eye_center + gaze_offset, pupil_r, pupil_r)

        # 3. Add specular highlight (cute glint) on top-left of each pupil
        glint_r = 1.8 * scale_x
        glint_offset = gaze_offset + QPointF(-1.8 * scale_x, -1.8 * scale_y)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(left_eye_center + glint_offset, glint_r, glint_r)
        painter.drawEllipse(right_eye_center + glint_offset, glint_r, glint_r)

    def _render_working_state(self, painter: QPainter, target_rect: QRectF, draw_w: float, draw_h: float) -> None:
        """Render the working state with delicate thin spinning arc rings tracking workspace focus."""
        idle_renderer = self._renderers.get(MascotState.IDLE)
        if idle_renderer:
            idle_renderer.render(painter, target_rect)

        # Scale factors from 200x240 SVG viewBox to draw bounds
        scale_x = draw_w / 200.0
        scale_y = draw_h / 240.0

        # Eye centers with slight cursor orientation
        subtle_ox = self._eye_ox * 0.45 * scale_x
        subtle_oy = self._eye_oy * 0.45 * scale_y
        left_eye = QPointF(target_rect.x() + 82.0 * scale_x + subtle_ox, target_rect.y() + 128.0 * scale_y + subtle_oy)
        right_eye = QPointF(target_rect.x() + 118.0 * scale_x + subtle_ox, target_rect.y() + 128.0 * scale_y + subtle_oy)

        cover_r = 8.5 * scale_x
        eye_r = 6.8 * scale_x

        # Cover idle eyes with body color (#F7F3EA)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F7F3EA"))
        painter.drawEllipse(left_eye, cover_r, cover_r)
        painter.drawEllipse(right_eye, cover_r, cover_r)

        # Draw delicate, thin spinning arcs
        # Stroke width thinned down from 5.0 to 1.8px
        stroke_w = max(1.5, 3.2 * scale_x)
        # Brand terracotta / warm focused accent
        spinner_color = QColor("#BA3F1A")
        pen = QPen(spinner_color, stroke_w, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.RoundCap)
        pen.setDashPattern([3.6, 2.2])
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Left eye rotation
        painter.save()
        painter.translate(left_eye)
        painter.rotate(self._spinner_angle)
        painter.drawEllipse(QPointF(0, 0), eye_r, eye_r)
        painter.restore()

        # Right eye rotation (offset by 90 degrees)
        painter.save()
        painter.translate(right_eye)
        painter.rotate(self._spinner_angle + 90.0)
        painter.drawEllipse(QPointF(0, 0), eye_r, eye_r)
        painter.restore()
