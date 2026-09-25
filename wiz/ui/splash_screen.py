"""Startup Splash Screen and Loading Spinner components for WizDesk."""

import time
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QApplication,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter, QPen

from wiz.ui.icons import get_app_pixmap
from wiz.ui.fonts import get_font, FONT_SANS


class LoadingSpinner(QWidget):
    """
    Hardware-accelerated circular spinner widget with smooth 60 FPS animation.
    Draws a minimalist rounded arc with brand terracotta accent (#FF6B3D).
    """

    def __init__(
        self,
        size: int = 28,
        stroke_width: float = 2.8,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._size = size
        self._stroke_width = stroke_width
        self.is_dark = is_dark
        self._angle: float = 0.0

        self.setFixedSize(size, size)
        self.update_theme(is_dark)

        # 60 FPS rotation timer (~16ms)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._rotate)
        self._timer.start()

    def _rotate(self) -> None:
        """Advance rotation angle smoothly."""
        self._angle = (self._angle + 6.0) % 360.0
        self.update()

    def update_theme(self, is_dark: bool = True) -> None:
        """Update track and accent colors based on theme."""
        self.is_dark = is_dark
        self._track_color = "#27272A" if is_dark else "#E4E4E7"
        self._accent_color = "#FF6B3D"  # Brand terracotta accent
        self.update()

    def paintEvent(self, event) -> None:
        """Draw circular track and rotating arc."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        inset = self._stroke_width / 2.0
        rect = QRectF(inset, inset, self.width() - self._stroke_width, self.height() - self._stroke_width)

        # Subtle background ring
        pen_track = QPen(QColor(self._track_color), self._stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_track)
        painter.drawEllipse(rect)

        # Rotating accent arc (100 degrees sweep)
        pen_arc = QPen(QColor(self._accent_color), self._stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_arc)
        start_angle = int(self._angle * 16)
        span_angle = int(100 * 16)
        painter.drawArc(rect, start_angle, span_angle)
        painter.end()


class _ProgressBarShim:
    """Lightweight compatibility shim for tests and callers expecting QProgressBar."""

    def __init__(self, get_val):
        self._get_val = get_val

    def value(self) -> int:
        return self._get_val()

    def setValue(self, val: int) -> None:
        pass


class SplashScreen(QWidget):
    """
    Modern minimalist frameless startup splash card.
    Displays mascot icon, title, rotating circular spinner, and dynamic loading status.
    Fades out cleanly once initialization finishes and minimum hold time has elapsed.
    """

    splash_closed = pyqtSignal()

    def __init__(self, is_dark: bool = True, min_display_sec: float = 2.4, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.min_display_sec = min_display_sec
        self._start_time = time.monotonic()
        self._is_finishing = False
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._progress_value: int = 0

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

        card_layout.addSpacing(10)

        # App Title (No subtitle)
        self.title_lbl = QLabel("WizDesk", self.card)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setFont(get_font(18, QFont.Weight.Bold))
        self.title_lbl.setObjectName("splashTitle")
        card_layout.addWidget(self.title_lbl)

        card_layout.addSpacing(18)

        # Centered Circular Spinner Loading
        spinner_layout = QHBoxLayout()
        spinner_layout.setContentsMargins(0, 0, 0, 0)
        self.spinner = LoadingSpinner(size=30, stroke_width=3.0, is_dark=self.is_dark, parent=self.card)
        spinner_layout.addStretch(1)
        spinner_layout.addWidget(self.spinner)
        spinner_layout.addStretch(1)
        card_layout.addLayout(spinner_layout)

        card_layout.addSpacing(12)

        # Dynamic Status text
        self.status_lbl = QLabel("Starting WizDesk...", self.card)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(get_font(9.5, QFont.Weight.Medium))
        self.status_lbl.setObjectName("splashStatus")
        card_layout.addWidget(self.status_lbl)

        card_layout.addStretch(1)

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
        """Update progress milestone value and status description."""
        self._progress_value = max(0, min(100, value))
        if text:
            self.status_lbl.setText(text)
        QApplication.processEvents()

    def set_status(self, text: str) -> None:
        """Update status description."""
        self.status_lbl.setText(text)
        QApplication.processEvents()

    @property
    def progress_value(self) -> int:
        """Current progress percentage value."""
        return self._progress_value

    @property
    def progress_bar(self) -> _ProgressBarShim:
        """Compatibility property for legacy callers and tests."""
        return _ProgressBarShim(lambda: self._progress_value)

    def finish(self) -> None:
        """
        Complete initialization and initiate smooth fade-out.
        Enforces min_display_sec to ensure calm, premium pacing.
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
        """Animate window opacity from 1.0 to 0.0 over 400ms."""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(400)
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
        if hasattr(self, "spinner"):
            self.spinner.update_theme(is_dark)

        bg_card = "#16161A" if is_dark else "#FFFFFF"
        border_card = "#27272A" if is_dark else "#D8D8DE"
        title_fg = "#F4F4F5" if is_dark else "#18181B"
        status_fg = "#A1A1AA" if is_dark else "#71717A"
        version_fg = "#71717A" if is_dark else "#A1A1AA"

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
        """)


class WorkspaceSplashOverlay(QFrame):
    """
    Subtle loading transition overlay shown when QuickEntryDialog is opened for the first time.
    Features the mascot icon, rotating circular spinner, and 'Loading workspace...' label.
    Fades out cleanly over 350ms using QGraphicsOpacityEffect.
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
        layout.setSpacing(12)

        # Mascot icon (36x36)
        self.icon_lbl = QLabel(self)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setPixmap(get_app_pixmap(size=36, asset_name="wiz-idle.svg"))
        layout.addWidget(self.icon_lbl)

        # Circular spinner (24px)
        spinner_layout = QHBoxLayout()
        spinner_layout.setContentsMargins(0, 0, 0, 0)
        self.spinner = LoadingSpinner(size=24, stroke_width=2.6, is_dark=self.is_dark, parent=self)
        spinner_layout.addStretch(1)
        spinner_layout.addWidget(self.spinner)
        spinner_layout.addStretch(1)
        layout.addLayout(spinner_layout)

        # Status label
        self.status_lbl = QLabel("Loading workspace...", self)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(get_font(10, QFont.Weight.Medium))
        self.status_lbl.setObjectName("overlayStatus")
        layout.addWidget(self.status_lbl)

        self.update_theme(is_dark)
        self.hide()

    @property
    def progress_bar(self) -> _ProgressBarShim:
        """Compatibility property for legacy callers and tests."""
        return _ProgressBarShim(lambda: 0)

    def update_theme(self, is_dark: bool = True) -> None:
        """Apply theme colors matching the inner workspace card."""
        self.is_dark = is_dark
        if hasattr(self, "spinner"):
            self.spinner.update_theme(is_dark)

        bg = "rgba(22, 22, 26, 0.95)" if is_dark else "rgba(246, 244, 238, 0.95)"
        text_fg = "#F4F4F5" if is_dark else "#18181B"

        self.setStyleSheet(f"""
            QFrame#workspaceSplashOverlay {{
                background-color: {bg};
                border-radius: 14px;
            }}
            QLabel#overlayStatus {{
                color: {text_fg};
                font-family: {FONT_SANS};
            }}
        """)

    def show_and_fade(self, duration_ms: int = 900) -> None:
        """Display the overlay and schedule smooth fade-out."""
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self._opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self) -> None:
        """Animate opacity from 1.0 to 0.0 over 350ms."""
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(350)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()
