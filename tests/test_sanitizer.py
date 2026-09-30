"""Unit tests for window title sanitization and privacy redaction."""

from datetime import datetime, timedelta
import pytest

from wiz.utils.sanitizer import (
    sanitize_window_title,
    PASSWORD_MANAGER_APPS,
    SENSITIVE_TITLE_KEYWORDS,
)
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository


def test_sanitize_password_manager_apps():
    """Verify password managers are masked to [Password Manager]."""
    for app in PASSWORD_MANAGER_APPS:
        redacted = sanitize_window_title("My Secret Vault - Unlocked", app_name=app)
        assert redacted == "[Password Manager]"


def test_sanitize_sensitive_title_keywords():
    """Verify sensitive title keywords trigger [Private Activity] redaction."""
    cases = [
        ("Google Chrome - New Incognito Tab", "chrome.exe"),
        ("Microsoft Edge - InPrivate Browsing", "msedge.exe"),
        ("Chase Online Banking - Account Summary", "chrome.exe"),
        ("Sign In to your Account - Google Accounts", "firefox.exe"),
        ("Enter Master Password to Unlock", "app.exe"),
        ("Two-Factor Authentication (2FA) Code", "browser.exe"),
        ("Payment - Credit Card Checkout", "chrome.exe"),
    ]
    for title, app in cases:
        redacted = sanitize_window_title(title, app_name=app)
        assert redacted == "[Private Activity]"


def test_sanitize_normal_development_titles():
    """Verify normal work and development window titles are not redacted."""
    normal_cases = [
        ("Wiz - Visual Studio Code", "Code.exe"),
        ("TurfLine Booking Flow - Figma", "Figma.exe"),
        ("Command Prompt - python main.py", "cmd.exe"),
        ("Slack | #engineering", "slack.exe"),
        ("Spotify Premium", "spotify.exe"),
    ]
    for title, app in normal_cases:
        assert sanitize_window_title(title, app_name=app) == title


def test_log_session_sanitization_integration(tmp_path):
    """Verify StorageRepository.log_session applies sanitization to recorded sessions."""
    db = Database(tmp_path / "test_sec_sessions.db")
    repo = StorageRepository(db)

    t1 = datetime(2026, 9, 30, 10, 0, 0)
    t2 = t1 + timedelta(minutes=15)

    # 1. Log password manager session
    s_id = repo.log_session(
        app_name="bitwarden.exe",
        window_title="Bitwarden - Master Password Input",
        start_time=t1,
        end_time=t2,
    )
    assert s_id > 0

    sessions = repo.get_sessions_for_date(t1.date())
    assert len(sessions) == 1
    assert sessions[0].window_title == "[Password Manager]"

    # 2. Log normal developer session
    repo.log_session(
        app_name="Code.exe",
        window_title="WizDesk - storage/models.py",
        start_time=t2,
        end_time=t2 + timedelta(minutes=20),
    )
    sessions2 = repo.get_sessions_for_date(t1.date())
    assert len(sessions2) == 2
    assert sessions2[1].window_title == "WizDesk - storage/models.py"
