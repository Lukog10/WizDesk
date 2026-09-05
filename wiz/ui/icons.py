"""Application icon and SVG asset helper utilities for WizDesk."""

from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtCore import Qt
from PyQt6.QtSvg import QSvgRenderer

from wiz.core.config import config


def get_app_pixmap(size: int = 32, asset_name: str = "wiz-idle.svg") -> QPixmap:
    """Render a crisp QPixmap from the given SVG asset."""
    # Map legacy alias idle.svg to wiz-idle.svg
    resolved_name = "wiz-idle.svg" if asset_name == "idle.svg" else asset_name
    asset_path = config.get_asset_path(resolved_name)

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

    return pixmap


def get_app_icon(asset_name: str = "wiz-idle.svg") -> QIcon:
    """Return a multi-resolution QIcon constructed from the mascot SVG for crisp OS rendering."""
    icon = QIcon()
    for size in [16, 20, 24, 32, 48, 64, 128, 256]:
        pm = get_app_pixmap(size, asset_name=asset_name)
        if not pm.isNull():
            icon.addPixmap(pm)
    return icon
