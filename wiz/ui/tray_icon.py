"""System Tray Icon and tray menu management for WizDesk."""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget
from PyQt6.QtSvg import QSvgRenderer

from wiz.core.config import config
from wiz.core.state_machine import MascotState, StateMachine
from wiz.core.signals import app_signals


class TrayIcon(QSystemTrayIcon):
    """
    System tray icon providing quick shortcuts, state indicators,
    and a right-click context menu.
    """

    def __init__(self, state_machine: StateMachine, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state_machine = state_machine

        # Set tray icon from rendered SVG
        self._update_icon()
        self.setToolTip("WizDesk - Desktop Companion and Work Tracker")

        # Build context menu
        self._build_menu()

        # Connect signals
        self.activated.connect(self._on_activated)
        self.state_machine.state_changed.connect(self._on_state_changed)

    def _render_mascot_icon(self, state: MascotState, size: int = 64) -> QIcon:
        """Render a crisp QIcon from the given MascotState SVG."""
        asset_path = config.get_asset_path(state.asset_filename)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        if asset_path.exists():
            renderer = QSvgRenderer(str(asset_path))
            if renderer.isValid():
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                renderer.render(painter)
                painter.end()

        return QIcon(pixmap)

    def _update_icon(self) -> None:
        """Update the system tray icon to match current state."""
        icon = self._render_mascot_icon(self.state_machine.current_state)
        self.setIcon(icon)

    def _on_state_changed(self, new_state: MascotState, old_state: MascotState) -> None:
        """Update tray icon when mascot state changes."""
        self._update_icon()
        self._rebuild_state_menu()

    def _build_menu(self) -> None:
        """Construct the system tray context menu."""
        self.menu = QMenu()
        self.menu.setStyleSheet("""
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
        action_note = self.menu.addAction("Quick Note / Task")
        action_note.setShortcut("Ctrl+Shift+W")
        action_note.triggered.connect(lambda: app_signals.request_quick_entry.emit())

        # Toggle Mascot Visibility Action
        action_toggle = self.menu.addAction("Show / Hide Mascot")
        action_toggle.triggered.connect(lambda: app_signals.toggle_mascot_visibility.emit())

        self.menu.addSeparator()

        # State Switcher Submenu
        self.state_menu = self.menu.addMenu("Mascot State")
        self.state_menu.setStyleSheet(self.menu.styleSheet())
        self._rebuild_state_menu()

        # Sync Obsidian Action
        action_sync = self.menu.addAction("Sync Obsidian Daily Note")
        action_sync.triggered.connect(lambda: app_signals.request_sync.emit())

        self.menu.addSeparator()

        # Settings Action
        action_settings = self.menu.addAction("Settings")
        action_settings.triggered.connect(lambda: app_signals.request_settings.emit())

        # Quit Action
        action_quit = self.menu.addAction("Quit WizDesk")
        action_quit.triggered.connect(lambda: app_signals.quit_application.emit())

        self.setContextMenu(self.menu)

    def _rebuild_state_menu(self) -> None:
        """Rebuild the mascot state submenu with checkmarks on the active state."""
        self.state_menu.clear()
        current = self.state_machine.current_state

        for state in MascotState:
            action = self.state_menu.addAction(state.value.capitalize())
            if current == state:
                action.setText(f"[x] {state.value.capitalize()}")
            action.triggered.connect(lambda checked, s=state: self.state_machine.set_state(s))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon clicks."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click toggles mascot window
            app_signals.toggle_mascot_visibility.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click opens quick entry popup
            app_signals.request_quick_entry.emit()
