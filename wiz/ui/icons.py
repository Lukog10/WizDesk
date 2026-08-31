"""Application icon and SVG asset helper utilities for WizDesk."""

from pathlib import Path
from typing import Optional
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtCore import Qt
from PyQt6.QtSvg import QSvgRenderer

from wiz.core.config import config


def get_app_pixmap(size: int = 32, asset_name: str = "wiz-idle.svg") -> QPixmap:
    """Render a crisp QPixmap from the given SVG asset."""
    # Support both wiz-idle.svg and idle.svg
    asset_path = config.get_asset_path(asset_name)
    if not asset_path.exists():
        if asset_name == "idle.svg":
            asset_path = config.get_asset_path("wiz-idle.svg")
        elif asset_name == "wiz-idle.svg":
            asset_path = config.get_asset_path("idle.svg")

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
