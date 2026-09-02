"""UI module for Wiz - Mascot Window, SVG Rendering, Tray, and Popups."""

from wiz.ui.mascot_widget import MascotWidget
from wiz.ui.mascot_window import MascotWindow
from wiz.ui.tray_icon import TrayIcon
from wiz.ui.popup_dialog import QuickEntryDialog
from wiz.ui.quick_bar_dialog import QuickBarPopup
from wiz.ui.settings_dialog import SettingsDialog
from wiz.ui.icons import get_app_icon, get_app_pixmap

__all__ = [
    "MascotWidget",
    "MascotWindow",
    "TrayIcon",
    "QuickEntryDialog",
    "QuickBarPopup",
    "SettingsDialog",
    "get_app_icon",
    "get_app_pixmap",
]
