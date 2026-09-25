"""Startup Splash Screen component for WizDesk."""

import time
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QApplication,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from wiz.ui.icons import get_app_pixmap
from wiz.ui.fonts import get_font, FONT_SANS


class SplashScreen(QWidget):
    """
    Modern minimalist frameless startup splash card.
    Displays mascot icon, title, dynamic loading status, and smooth terracotta progress bar.
    Fades out cleanly once initialization finishes and minimum hold time has elapsed.
    """

    splash_closed = pyqtSignal()

    def __init__(self, is_dark: bool = True, min_display_sec: float = 1.2, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.min_display_sec = min_display_sec
        self._start_time = time.monotonic()
        self._is_finishing = False
        self._fade_anim: Optional[QPropertyAnimation] = None

        # Window flags and attributes
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        # Fixed dimensions
        self.setFixedSize(460, 280)

        # Build UI layout
        self._init_ui()
        self.center_on_screen()
        self.update_theme(is_dark)

    def _init_ui(self) -> None:
        """Construct the visual hierarchy of the splash card."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        # Main Card Container
        self.card = QFrame(self)
        self.card.setObjectName("splashCard")

        # Soft ambient shadow
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 90 if self.is_dark else 35))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 28, 32, 24)
        card_layout.setSpacing(0)

        # Mascot Icon
        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_lbl = QLabel(self.card)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = get_app_pixmap(size=64, asset_name="wiz-idle.svg")
        self.icon_lbl.setPixmap(pixmap)
        icon_layout.addWidget(self.icon_lbl)
        card_layout.addLayout(icon_layout)

        card_layout.addSpacing(12)

        # App Title (No subtitle)
        self.title_lbl = QLabel("WizDesk", self.card)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setFont(get_font(18, QFont.Weight.Bold))
        self.title_lbl.setObjectName("splashTitle")
        card_layout.addWidget(self.title_lbl)

        card_layout.addStretch(1)

        # Status text
        self.status_lbl = QLabel("Starting WizDesk...", self.card)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_lbl.setFont(get_font(9, QFont.Weight.Medium))
        self.status_lbl.setObjectName("splashStatus")
        card_layout.addWidget(self.status_lbl)

        card_layout.addSpacing(8)

        # Progress bar
        self.progress_bar = QProgressBar(self.card)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setObjectName("splashProgress")
        card_layout.addWidget(self.progress_bar)

        card_layout.addSpacing(14)

        # Footer (Version indicator)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        self.version_lbl = QLabel("v1.0.0", self.card)
        self.version_lbl.setFont(get_font(8, QFont.Weight.Normal))
        self.version_lbl.setObjectName("splashVersion")
        footer_layout.addWidget(self.version_lbl)
        footer_layout.addStretch(1)
        card_layout.addLayout(footer_layout)

        root_layout.addWidget(self.card)

    def center_on_screen(self) -> None:
        """Position the splash card in the center of the active primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def set_progress(self, value: int, text: Optional[str] = None) -> None:
        """Update progress bar value (0-100) and optional status description."""
        self.progress_bar.setValue(max(0, min(100, value)))
        if text:
            self.status_lbl.setText(text)
        QApplication.processEvents()

    def finish(self) -> None:
        """
        Complete the progress and initiate smooth fade-out.
        Enforces min_display_sec to prevent rapid UI flashing.
        """
        if self._is_finishing:
            return
        self._is_finishing = True
        self.set_progress(100, "Ready")

        elapsed = time.monotonic() - self._start_time
        remaining = self.min_display_sec - elapsed
        if remaining > 0:
            QTimer.singleShot(int(remaining * 1000), self._start_fade_out)
        else:
            self._start_fade_out()

    def _start_fade_out(self) -> None:
        """Animate window opacity from 1.0 to 0.0 over 300ms."""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_finished)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        """Emit completion signal and close the splash window."""
        self.splash_closed.emit()
        self.close()

    def update_theme(self, is_dark: bool = True) -> None:
        """Apply theme colors matching WizDesk design tokens."""
        self.is_dark = is_dark
        bg_card = "#16161A" if is_dark else "#FFFFFF"
        border_card = "#27272A" if is_dark else "#D8D8DE"
        title_fg = "#F4F4F5" if is_dark else "#18181B"
        status_fg = "#A1A1AA" if is_dark else "#71717A"
        version_fg = "#71717A" if is_dark else "#A1A1AA"
        progress_track = "#27272A" if is_dark else "#E4E4E7"
        progress_chunk = "#FF6B3D"  # Brand terracotta

        self.card.setStyleSheet(f"""
            QFrame#splashCard {{
                background-color: {bg_card};
                border: 1px solid {border_card};
                border-radius: 20px;
            }}
            QLabel#splashTitle {{
                color: {title_fg};
                font-family: {FONT_SANS};
            }}
            QLabel#splashStatus {{
                color: {status_fg};
                font-family: {FONT_SANS};
            }}
            QLabel#splashVersion {{
                color: {version_fg};
                font-family: {FONT_SANS};
            }}
            QProgressBar#splashProgress {{
                background-color: {progress_track};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar#splashProgress::chunk {{
                background-color: {progress_chunk};
                border-radius: 2px;
            }}
        """)


class WorkspaceSplashOverlay(QFrame):
    """
    Subtle loading transition overlay shown when QuickEntryDialog is opened for the first time.
    Features the mascot icon, 'Loading workspace...' label, and an animated terracotta progress bar.
    Fades out cleanly over 200ms using QGraphicsOpacityEffect.
    """

    def __init__(self, parent: Optional[QWidget] = None, is_dark: bool = True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setObjectName("workspaceSplashOverlay")

        # Opacity effect for smooth fading
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_anim: Optional[QPropertyAnimation] = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        # Mascot icon (40x40)
        self.icon_lbl = QLabel(self)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setPixmap(get_app_pixmap(size=40, asset_name="wiz-idle.svg"))
        layout.addWidget(self.icon_lbl)

        # Status label
        self.status_lbl = QLabel("Loading workspace...", self)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(get_font(10, QFont.Weight.Medium))
        self.status_lbl.setObjectName("overlayStatus")
        layout.addWidget(self.status_lbl)

        # Slim progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedWidth(140)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setObjectName("overlayProgress")
        layout.addWidget(self.progress_bar, 0, Qt.AlignmentFlag.AlignCenter)

        self.update_theme(is_dark)
        self.hide()

    def update_theme(self, is_dark: bool = True) -> None:
        """Apply theme colors matching the inner workspace card."""
        self.is_dark = is_dark
        bg = "rgba(22, 22, 26, 0.95)" if is_dark else "rgba(246, 244, 238, 0.95)"
        text_fg = "#F4F4F5" if is_dark else "#18181B"
        progress_track = "#27272A" if is_dark else "#E4E4E7"
        progress_chunk = "#FF6B3D"

        self.setStyleSheet(f"""
            QFrame#workspaceSplashOverlay {{
                background-color: {bg};
                border-radius: 14px;
            }}
            QLabel#overlayStatus {{
                color: {text_fg};
                font-family: {FONT_SANS};
            }}
            QProgressBar#overlayProgress {{
                background-color: {progress_track};
                border: none;
                border-radius: 1.5px;
            }}
            QProgressBar#overlayProgress::chunk {{
                background-color: {progress_chunk};
                border-radius: 1.5px;
            }}
        """)

    def show_and_fade(self, duration_ms: int = 400) -> None:
        """Display the overlay and schedule smooth fade-out."""
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self._opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self) -> None:
        """Animate opacity from 1.0 to 0.0 over 200ms."""
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

