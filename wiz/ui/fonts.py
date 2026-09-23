"""Centralized typography definitions for WizDesk (Space Grotesk + IBM Plex Sans + JetBrains Mono)."""

from PyQt6.QtGui import QFont, QFontDatabase

from wiz.core.config import config

# Display & Headings Stack: Distinctive geometric grotesque for app titles, project headers, section headings
FONT_DISPLAY = '"Space Grotesk"'

# Primary UI & Body Sans Stack: High-legibility industrial workhorse for buttons, task lists, settings, labels
FONT_SANS = '"IBM Plex Sans"'

# Monospace Stack: Tabular numerals and code metrics for timers, timestamps, shortcuts, session logs
FONT_MONO = '"JetBrains Mono"'

DISPLAY_FAMILIES = [
    "Space Grotesk",
    "IBM Plex Sans",
    "Segoe UI",
    "sans-serif",
]

SANS_FAMILIES = [
    "IBM Plex Sans",
    "Segoe UI",
    "SF Pro Text",
    "Helvetica Neue",
    "sans-serif",
]

MONO_FAMILIES = [
    "JetBrains Mono",
    "Cascadia Code",
    "Fira Code",
    "Consolas",
    "SF Mono",
    "monospace",
]

_FONTS_LOADED = False


def init_fonts() -> bool:
    """Register bundled Space Grotesk, IBM Plex Sans, and JetBrains Mono fonts into QFontDatabase."""
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return True

    fonts_dir = config.assets_dir / "fonts"
    if not fonts_dir.exists():
        fonts_dir = config.root_dir / "assets" / "fonts"

    success = False
    if fonts_dir.exists():
        for font_file in [
            "SpaceGrotesk-Variable.ttf",
            "IBMPlexSans-Variable.ttf",
            "JetBrainsMono-Variable.ttf",
            "PlusJakartaSans-Variable.ttf",
        ]:
            font_path = fonts_dir / font_file
            if font_path.exists():
                font_id = QFontDatabase.addApplicationFont(str(font_path))
                if font_id >= 0:
                    success = True

    _FONTS_LOADED = True
    return success


def get_font(
    size: int = 10,
    weight: QFont.Weight = QFont.Weight.Normal,
    mono: bool = False,
    display: bool = False,
) -> QFont:
    """Return an appropriately configured QFont with graceful fallback to system defaults."""
    if not _FONTS_LOADED:
        init_fonts()
    font = QFont()
    if mono:
        font.setFamilies(MONO_FAMILIES)
    elif display:
        font.setFamilies(DISPLAY_FAMILIES)
    else:
        font.setFamilies(SANS_FAMILIES)
    font.setPointSize(max(1, int(size)) if size and size > 0 else 10)
    font.setWeight(weight)
    return font
