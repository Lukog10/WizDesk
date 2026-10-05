"""Unit tests for window title sanitization, privacy redaction, and system process exclusion."""

import os
from datetime import datetime, timedelta
import pytest

from wiz.utils.sanitizer import (
    sanitize_window_title,
    clean_app_name,
    is_system_excluded,
    PASSWORD_MANAGER_APPS,
    SENSITIVE_TITLE_KEYWORDS,
    SYSTEM_EXCLUDED_PROCESSES,
    SYSTEM_EXCLUDED_TITLES,
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


def test_clean_app_name():
    """Verify that .exe file extensions are stripped from process names."""
    assert clean_app_name("Antigravity IDE.exe") == "Antigravity IDE"
    assert clean_app_name("explorer.exe") == "explorer"
    assert clean_app_name("CONTROLResonant.exe") == "CONTROLResonant"
    assert clean_app_name("zen.exe") == "zen"
    assert clean_app_name("Code") == "Code"
    assert clean_app_name("my_app.EXE") == "my_app"
    assert clean_app_name(None) == "Unknown"
    assert clean_app_name("") == "Unknown"


def test_is_system_excluded_explorer():
    """Verify Windows Explorer folder windows, desktop, and task switching are excluded."""
    assert is_system_excluded("explorer.exe", "Downloads - File Explorer") is True
    assert is_system_excluded("explorer.exe", "H:\\Projects\\Wiz - File Explorer") is True
    assert is_system_excluded("explorer.exe", "Program Manager") is True
    assert is_system_excluded("explorer", "Task Switching") is True
    assert is_system_excluded("explorer.exe", "") is True
    assert is_system_excluded("explorer", "This PC") is True


def test_is_system_excluded_search_and_system_hosts():
    """Verify Windows Search, Lock Screen, and system shell hosts are excluded."""
    assert is_system_excluded("SearchHost.exe", "Search") is True
    assert is_system_excluded("SearchApp.exe", "Search") is True
    assert is_system_excluded("LockApp.exe", "Windows Default Lock Screen") is True
    assert is_system_excluded("LogonUI.exe", "Logon") is True
    assert is_system_excluded("ShellExperienceHost.exe", "New notification") is True
    assert is_system_excluded("ShellHost.exe", "Windows Input Experience") is True
    assert is_system_excluded("PickerHost.exe", "Open") is True


def test_is_system_excluded_allows_taskmgr_and_wizdesk():
    """Verify Task Manager and WizDesk are NOT excluded and can be logged."""
    assert is_system_excluded("Taskmgr.exe", "Task Manager") is False
    assert is_system_excluded("taskmgr", "Task Manager") is False
    assert is_system_excluded("WizDesk.exe", "WizDesk Workspace") is False
    assert is_system_excluded("WizDesk", "Settings") is False
    assert is_system_excluded("python.exe", "WizDesk", pid=os.getpid()) is False


def test_is_system_excluded_allowed_work_apps():
    """Verify legitimate work applications are not excluded."""
    assert is_system_excluded("Code.exe", "Wiz - Visual Studio Code") is False
    assert is_system_excluded("chrome.exe", "GitHub - Lukog10/WizDesk") is False
    assert is_system_excluded("zen.exe", "Research papers") is False
    assert is_system_excluded("ApplicationFrameHost.exe", "Settings") is False


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


def test_repo_log_session_blocks_excluded_system_processes(tmp_path):
    """Verify StorageRepository.log_session rejects Windows Explorer and system noise, but permits WizDesk and Taskmgr."""
    db = Database(tmp_path / "test_exclusion_repo.db")
    repo = StorageRepository(db)

    t1 = datetime(2026, 10, 5, 10, 0, 0)
    t2 = t1 + timedelta(minutes=10)

    # 1. Attempt to log explorer.exe -> blocked
    s1 = repo.log_session("explorer.exe", "Downloads - File Explorer", t1, t2)
    assert s1 == 0

    # 2. Attempt to log SearchHost.exe -> blocked
    s2 = repo.log_session("SearchHost.exe", "Search", t1, t2)
    assert s2 == 0

    # 3. Log WizDesk -> allowed
    s3 = repo.log_session("WizDesk.exe", "Settings", t1, t2, project_tag="WizDesk")
    assert s3 > 0

    # 4. Log Task Manager -> allowed
    s4 = repo.log_session("Taskmgr.exe", "Task Manager", t1, t2)
    assert s4 > 0

    # 5. Log legitimate developer session
    s5 = repo.log_session("Code.exe", "main.py - WizDesk", t1, t2, project_tag="WizDesk")
    assert s5 > 0

    records = repo.get_sessions_for_date(t1.date())
    assert len(records) == 3
    apps = [r.app_name for r in records]
    assert "WizDesk.exe" in apps
    assert "Taskmgr.exe" in apps
    assert "Code.exe" in apps
