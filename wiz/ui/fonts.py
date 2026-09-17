"""Centralized typography definitions for WizDesk (Option A: Plus Jakarta Sans + JetBrains Mono)."""

from typing import Sequence
from PyQt6.QtGui import QFont

# Primary UI Sans Stack: Modern geometric SaaS font with open counters and high legibility
FONT_SANS = (
    "'Plus Jakarta Sans', 'Inter', 'Segoe UI', -apple-system, "
    "BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif"
)

# Primary Developer Mono Stack: Precision tabular numerals, timestamps, and metrics
FONT_MONO = (
    "'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'SF Mono', monospace"
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


def get_font(
    size: int = 10,
    weight: QFont.Weight = QFont.Weight.Normal,
    mono: bool = False,
) -> QFont:
    """Return an appropriately configured QFont with graceful fallback to system defaults."""
    font = QFont()
    font.setFamilies(MONO_FAMILIES if mono else SANS_FAMILIES)
    if size > 0:
        font.setPointSize(size)
    font.setWeight(weight)
    return font
