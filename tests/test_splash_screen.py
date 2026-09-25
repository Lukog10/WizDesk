"""Unit tests for the SplashScreen component."""

import time
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from wiz.ui.splash_screen import SplashScreen, WorkspaceSplashOverlay


def test_splash_screen_initialization(qapp):
    """Test SplashScreen geometry, window flags, and child widgets."""
    splash = SplashScreen(is_dark=True, min_display_sec=0.1)

    # Assert dimensions
    assert splash.width() == 460
    assert splash.height() == 280

    # Assert window flags
    flags = splash.windowFlags()
    assert bool(flags & Qt.WindowType.FramelessWindowHint)
    assert bool(flags & Qt.WindowType.WindowStaysOnTopHint)
    assert bool(flags & Qt.WindowType.SplashScreen)

    # Assert widget structure
    assert hasattr(splash, "card")
    assert hasattr(splash, "icon_lbl")
    assert hasattr(splash, "title_lbl")
    assert hasattr(splash, "status_lbl")
    assert hasattr(splash, "progress_bar")
    assert hasattr(splash, "version_lbl")

    # Assert content
    assert splash.title_lbl.text() == "WizDesk"
    assert splash.status_lbl.text() == "Starting WizDesk..."
    assert splash.progress_bar.value() == 0
    assert splash.version_lbl.text() == "v1.0.0"

    splash.close()


def test_splash_screen_progress_stepping(qapp):
    """Test updating progress bar values and status labels."""
    splash = SplashScreen(is_dark=True, min_display_sec=0.1)

    splash.set_progress(25, "Loading local database...")
    assert splash.progress_bar.value() == 25
    assert splash.status_lbl.text() == "Loading local database..."

    splash.set_progress(55, "Starting background tracker...")
    assert splash.progress_bar.value() == 55
    assert splash.status_lbl.text() == "Starting background tracker..."

    splash.set_progress(100, "Ready")
    assert splash.progress_bar.value() == 100
    assert splash.status_lbl.text() == "Ready"

    splash.close()


def test_splash_screen_fade_and_finish(qapp):
    """Test that finish initiates smooth fade and emits splash_closed."""
    splash = SplashScreen(is_dark=True, min_display_sec=0.01)
    splash.show()

    closed_events = []
    splash.splash_closed.connect(lambda: closed_events.append(True))
    splash.finish()

    start = time.monotonic()
    while not closed_events and (time.monotonic() - start < 2.0):
        qapp.processEvents()
        time.sleep(0.02)

    assert len(closed_events) == 1


def test_splash_screen_theme_toggle(qapp):
    """Test switching between dark and light themes."""
    splash = SplashScreen(is_dark=True, min_display_sec=0.1)
    assert splash.is_dark

    splash.update_theme(is_dark=False)
    assert not splash.is_dark

    splash.update_theme(is_dark=True)
    assert splash.is_dark

    splash.close()


def test_workspace_splash_overlay_initialization_and_theme(qapp):
    """Test WorkspaceSplashOverlay widgets, layout, and theme updates."""
    overlay = WorkspaceSplashOverlay(is_dark=True)

    assert hasattr(overlay, "icon_lbl")
    assert hasattr(overlay, "status_lbl")
    assert hasattr(overlay, "progress_bar")
    assert overlay.status_lbl.text() == "Loading workspace..."
    assert overlay.is_dark

    overlay.update_theme(is_dark=False)
    assert not overlay.is_dark

    overlay.close()


def test_workspace_splash_overlay_show_and_fade(qapp):
    """Test that WorkspaceSplashOverlay displays and fades out cleanly."""
    overlay = WorkspaceSplashOverlay(is_dark=True)
    overlay.show_and_fade(duration_ms=40)

    start = time.monotonic()
    while overlay.isVisible() and (time.monotonic() - start < 2.0):
        qapp.processEvents()
        time.sleep(0.02)

    assert overlay.isHidden()
    overlay.close()


def test_wiz_application_with_splash(qapp):
    """Test that WizApplication steps through splash screen progress and finishes."""
    from wiz.__main__ import WizApplication

    splash = SplashScreen(is_dark=True, min_display_sec=0.01)
    wiz_app = WizApplication(splash=splash)

    assert splash.progress_bar.value() == 80
    assert splash.status_lbl.text() == "Preparing desktop companion..."

    wiz_app.start()
    assert splash.progress_bar.value() == 100
    assert splash.status_lbl.text() == "Ready"

    start = time.monotonic()
    while splash.isVisible() and (time.monotonic() - start < 2.0):
        qapp.processEvents()
        time.sleep(0.02)

    assert splash.isHidden()
    wiz_app.quit()


