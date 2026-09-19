"""Application icon and SVG asset helper utilities for WizDesk."""

import re
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtCore import Qt, QByteArray
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


def render_tinted_svg(
    painter: QPainter,
    svg_name: str,
    color_hex: str,
    x: float,
    y: float,
    size: float,
) -> None:
    """Render a tinted SVG asset directly onto an active QPainter at (x, y) with given size.

    Replaces both fill and stroke color attributes to support all SVG icon styles.
    """
    asset_path = config.get_asset_path(svg_name)
    if not asset_path.exists():
        return

    content = asset_path.read_text(encoding="utf-8")
    # Replace fill attributes (but not fill="none")
    tinted = re.sub(r'fill="(?!none)[^"]*"', f'fill="{color_hex}"', content)
    # Replace stroke attributes (but not stroke="none")
    tinted = re.sub(r'stroke="(?!none)[^"]*"', f'stroke="{color_hex}"', tinted)
    # Replace color="currentColor" for SVGs that use it
    tinted = tinted.replace('color="currentColor"', f'color="{color_hex}"')

    renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))
    if renderer.isValid():
        from PyQt6.QtCore import QRectF
        renderer.render(painter, QRectF(x, y, size, size))


def get_status_icon(svg_name: str, color_hex: str, size: int = 14) -> QIcon:
    """Load an SVG icon from assets/, dynamically tint it with color_hex, and return a crisp high-DPI QIcon."""
    asset_path = config.get_asset_path(svg_name)
    if not asset_path.exists():
        return QIcon()

    content = asset_path.read_text(encoding="utf-8")
    if 'fill="' in content:
        tinted = re.sub(r'fill="[^"]*"', f'fill="{color_hex}"', content)
    else:
        tinted = content.replace('<path ', f'<path fill="{color_hex}" ')

    renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    icon = QIcon()
    icon.addPixmap(pixmap)
    return icon

