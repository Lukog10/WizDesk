"""Tests for Windows Startup registry management and SettingsView integration."""

import sys
import pytest
from PyQt6.QtWidgets import QApplication

from wiz.core.autostart import (
    get_launch_command,
    is_autostart_enabled,
    set_autostart,
    APP_NAME,
    REG_KEY_PATH,
)
from wiz.core.config import config
from wiz.storage.models import StorageRepository
from wiz.ui.settings_view import SettingsView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def repo(tmp_path):
    from wiz.storage.db import Database
    db_file = tmp_path / "test_autostart.db"
    return StorageRepository(Database(db_file))


def test_get_launch_command():
    """Verify launch command resolves to an executable or python string."""
    cmd = get_launch_command()
    assert isinstance(cmd, str)
    assert len(cmd) > 0
    assert "WizDesk" in cmd or "python" in cmd.lower()


def test_set_and_query_autostart():
    """Test registry write, read, and delete operations."""
    if sys.platform != "win32":
        pytest.skip("Windows-only autostart registry test")

    # Initial cleanup to known state
    set_autostart(False)
    assert not is_autostart_enabled()

    # Enable
    success = set_autostart(True)
    assert success is True
    assert is_autostart_enabled() is True

    # Disable
    success_disable = set_autostart(False)
    assert success_disable is True
    assert is_autostart_enabled() is False


def test_settings_view_autostart_toggle(qapp, repo):
    """Test SettingsView checkbox interaction with autostart registry."""
    if sys.platform != "win32":
        pytest.skip("Windows-only autostart registry test")

    set_autostart(False)
    config.set("auto_start_on_login", False)

    view = SettingsView(repository=repo, is_dark=True)
    assert not view.autostart_check.isChecked()

    # Toggle to True
    view.autostart_check.setChecked(True)
    assert is_autostart_enabled() is True
    assert config.get("auto_start_on_login") is True

    # Toggle to False
    view.autostart_check.setChecked(False)
    assert is_autostart_enabled() is False
    assert config.get("auto_start_on_login") is False

    # Save settings check
    view.autostart_check.setChecked(True)
    view.save_settings()
    assert is_autostart_enabled() is True
    assert config.get("auto_start_on_login") is True

    # Cleanup
    view.autostart_check.setChecked(False)
    view.save_settings()
    assert is_autostart_enabled() is False
    view.close()
