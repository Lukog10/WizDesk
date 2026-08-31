"""Frameless, transparent, draggable, always-on-top companion window."""

from typing import Optional
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QContextMenuEvent, QAction, QGuiApplication, QCursor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu

from wiz.core.config import config
from wiz.core.state_machine import MascotState, StateMachine
from wiz.core.signals import app_signals
from wiz.ui.mascot_widget import MascotWidget


class MascotWindow(QWidget):
    """
    Floating, frameless, transparent, always-on-top desktop companion window.
    Supports dragging, position memory, double-click actions, and context menus.
    """

    def __init__(self, state_machine: StateMachine, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state_machine = state_machine

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

        # Drag state tracking
        self._is_dragging: bool = False
        self._drag_start_position: QPoint = QPoint()

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

    # --- Mouse & Drag Handling ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin dragging on left mouse click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move window smoothly during mouse drag with screen boundary clamping."""
        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_start_position
            clamped_pos = self._clamp_to_screens(new_pos)
            self.move(clamped_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """End drag and persist final screen coordinates."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                self._is_dragging = False
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                config.save_window_position(self.x(), self.y())
                event.accept()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-click on mascot triggers Quick-Entry note/task dialog."""
        if event.button() == Qt.MouseButton.LeftButton:
            app_signals.request_quick_entry.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

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

    # --- Context Menu ---

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Display right-click context menu on mascot."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E1E24;
                color: #F7F3EA;
                border: 1px solid #33333E;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2D2D38;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #33333E;
                margin: 4px 6px;
            }
        """)

        # Quick Note Action
        action_note = menu.addAction("Quick Note / Task")
        action_note.triggered.connect(lambda: app_signals.request_quick_entry.emit())

        menu.addSeparator()

        # State Switcher Submenu (useful for instant testing and manual status)
        state_menu = menu.addMenu("Mascot State")
        state_menu.setStyleSheet(menu.styleSheet())

        for state in MascotState:
            action = state_menu.addAction(state.value.capitalize())
            if self.state_machine.current_state == state:
                action.setText(f"[x] {state.value.capitalize()}")
            # Capture state in default arg
            action.triggered.connect(lambda checked, s=state: self.state_machine.set_state(s))

        menu.addSeparator()

        # Settings
        action_settings = menu.addAction("Settings")
        action_settings.triggered.connect(lambda: app_signals.request_settings.emit())

        # Hide Mascot
        action_hide = menu.addAction("Hide Mascot")
        action_hide.triggered.connect(self.hide)

        menu.addSeparator()

        # Quit
        action_quit = menu.addAction("Quit WizDesk")
        action_quit.triggered.connect(lambda: app_signals.quit_application.emit())

        menu.exec(event.globalPos())
