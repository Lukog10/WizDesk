"""Frameless, transparent, draggable, always-on-top companion window."""

from typing import Optional
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QMouseEvent, QGuiApplication, QCursor
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from wiz.core.config import config
from wiz.core.state_machine import MascotState, StateMachine
from wiz.core.signals import app_signals
from wiz.ui.mascot_widget import MascotWidget
from wiz.ui.icons import get_app_icon


class MascotWindow(QWidget):
    """
    Floating, frameless, transparent, always-on-top desktop companion window.
    Supports dragging, position memory, double-click (Task Bar), triple-click (Note Bar), and context menus.
    """

    def __init__(self, state_machine: StateMachine, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state_machine = state_machine
        self.setWindowIcon(get_app_icon("wiz-idle.svg"))

        # Window flags: frameless, stays on top, tool window (avoids cluttering taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Set default size
        w, h = config.window_size
        self.resize(w, h)

        # Layout and mascot rendering widget
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.mascot_widget = MascotWidget(self.state_machine, self)
        self.layout.addWidget(self.mascot_widget)

        # Drag & Click Gesture Tracking
        self._is_dragging: bool = False
        self._press_global_pos: QPoint = QPoint()
        self._drag_start_position: QPoint = QPoint()

        # Multi-click gesture timer (for Double-click Quick Task vs Triple-click Quick Note)
        self._click_count: int = 0
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(280)
        self._click_timer.timeout.connect(self._on_click_timeout)

        # Position on screen
        self._init_window_position()

        # Connect signals
        app_signals.toggle_mascot_visibility.connect(self.toggle_visibility)

    def _init_window_position(self) -> None:
        """Place window at saved position or default to bottom-right corner."""
        saved_pos = config.window_position
        if saved_pos:
            self.move(saved_pos[0], saved_pos[1])
            return

        # Default positioning: bottom-right corner of primary screen
        primary_screen = QGuiApplication.primaryScreen()
        if primary_screen:
            geom = primary_screen.availableGeometry()
            w, h = self.width(), self.height()
            margin = 35
            x = geom.right() - w - margin
            y = geom.bottom() - h - margin
            self.move(x, y)
            config.save_window_position(x, y)

    def toggle_visibility(self) -> None:
        """Toggle mascot window between visible and hidden."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    # --- Mouse & Drag Handling with Multi-Click Gesture Detection ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin tracking drag and click gestures on left mouse click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._press_global_pos = event.globalPosition().toPoint()
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move window smoothly during mouse drag with screen boundary clamping."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            dist = (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength()
            if dist > 4 or self._is_dragging:
                if not self._is_dragging:
                    self._is_dragging = True
                    self._click_count = 0
                    self._click_timer.stop()
                    self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

                new_pos = event.globalPosition().toPoint() - self._drag_start_position
                clamped_pos = self._clamp_to_screens(new_pos)
                self.move(clamped_pos)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """End drag or register click gesture for double/triple click."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                self._is_dragging = False
                self._click_count = 0
                self._click_timer.stop()
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                config.save_window_position(self.x(), self.y())
                event.accept()
                return
            else:
                # Registered click without dragging
                self._click_count += 1
                self._click_timer.start(280)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Qt native double click hook - accept to allow unified multi-click timer processing."""
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _on_click_timeout(self) -> None:
        """Handle multi-click gestures once click pause is reached."""
        count = self._click_count
        self._click_count = 0

        if count >= 2:
            # Double-click: directly open the main workspace window
            app_signals.request_quick_entry.emit()

    def _clamp_to_screens(self, pos: QPoint) -> QPoint:
        """Ensure the window does not get dragged completely off-screen."""
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        if not screen:
            return pos

        geom = screen.virtualGeometry()
        min_visible = 30  # At least 30px visible on screen
        clamped_x = max(geom.left() - self.width() + min_visible, min(pos.x(), geom.right() - min_visible))
        clamped_y = max(geom.top() - self.height() + min_visible, min(pos.y(), geom.bottom() - min_visible))
        return QPoint(clamped_x, clamped_y)

    def contextMenuEvent(self, event) -> None:
        """Right-click menu disabled in favor of global hotkeys."""
        event.accept()
