"""Centralized typography definitions for WizDesk (Option A: Plus Jakarta Sans + JetBrains Mono)."""

from PyQt6.QtGui import QFont, QFontDatabase

from wiz.core.config import config

# Primary UI Sans Stack: Modern geometric SaaS font with open counters and high legibility
# NOTE: Qt stylesheet CSS 2.1 subset — no web-only aliases (-apple-system, BlinkMacSystemFont).
# Double-quoted names for reliable parsing in f-string stylesheets.
FONT_SANS = (
    '"Plus Jakarta Sans", "Inter", "Segoe UI", "Helvetica Neue", sans-serif'
)

# Primary Developer Mono Stack: Precision tabular numerals, timestamps, and metrics
FONT_MONO = (
    '"JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", monospace'
)

SANS_FAMILIES = [
    "Plus Jakarta Sans",
    "Inter",
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
    """Register bundled Plus Jakarta Sans and JetBrains Mono fonts into QFontDatabase."""
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return True

    fonts_dir = config.assets_dir / "fonts"
    if not fonts_dir.exists():
        fonts_dir = config.root_dir / "assets" / "fonts"

    success = False
    if fonts_dir.exists():
        for font_file in ["PlusJakartaSans-Variable.ttf", "JetBrainsMono-Variable.ttf"]:
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
) -> QFont:
    """Return an appropriately configured QFont with graceful fallback to system defaults."""
    if not _FONTS_LOADED:
        init_fonts()
    font = QFont()
    font.setFamilies(MONO_FAMILIES if mono else SANS_FAMILIES)
    font.setPointSize(max(1, int(size)) if size and size > 0 else 10)
    font.setWeight(weight)
    return font
