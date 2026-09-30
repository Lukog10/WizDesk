"""Unit tests for OS credential authentication and private key security."""

import sys
from unittest.mock import MagicMock, patch
import pytest

from wiz.utils.auth import (
    authenticate_user,
    _prompt_windows_credentials,
    ERROR_SUCCESS,
    ERROR_CANCELLED,
)


def test_authenticate_user_cancelled(monkeypatch):
    """Test that cancelling the credential prompt returns False."""
    mock_credui = MagicMock()
    mock_credui.CredUIPromptForWindowsCredentialsW.return_value = ERROR_CANCELLED

    with patch("ctypes.windll.credui", mock_credui):
        result = _prompt_windows_credentials()
        assert result is False


def test_authenticate_user_success(monkeypatch):
    """Test successful credential prompt and token verification."""
    mock_credui = MagicMock()

    def mock_prompt(pUiInfo, dwAuthError, pulAuthPackage, pvInAuthBuffer, ulInAuthBufferSize, ppvOutAuthBuffer, pulOutAuthBufferSize, pfSave, dwFlags):
        ppvOutAuthBuffer._obj.value = 0x12345678
        pulOutAuthBufferSize._obj.value = 128
        return ERROR_SUCCESS

    mock_credui.CredUIPromptForWindowsCredentialsW.side_effect = mock_prompt

    def mock_unpack(flags, in_buf, in_len, user, user_len, dom, dom_len, pwd, pwd_len):
        user.value = "TestUser"
        dom.value = "WORKGROUP"
        pwd.value = "SecretPass123"
        return True

    mock_credui.CredUnPackAuthenticationBufferW.side_effect = mock_unpack

    mock_token = MagicMock()
    mock_logon = MagicMock(return_value=mock_token)

    with patch("ctypes.windll.credui", mock_credui), \
         patch("ctypes.windll.ole32.CoTaskMemFree") as mock_free, \
         patch("win32security.LogonUser", mock_logon):

        result = _prompt_windows_credentials()
        assert result is True
        mock_token.Close.assert_called_once()
        mock_free.assert_called_once()


def test_authenticate_user_invalid_logon(monkeypatch):
    """Test that invalid password during LogonUser returns False."""
    mock_credui = MagicMock()

    def mock_prompt(pUiInfo, dwAuthError, pulAuthPackage, pvInAuthBuffer, ulInAuthBufferSize, ppvOutAuthBuffer, pulOutAuthBufferSize, pfSave, dwFlags):
        ppvOutAuthBuffer._obj.value = 0x12345678
        pulOutAuthBufferSize._obj.value = 128
        return ERROR_SUCCESS

    mock_credui.CredUIPromptForWindowsCredentialsW.side_effect = mock_prompt

    def mock_unpack(flags, in_buf, in_len, user, user_len, dom, dom_len, pwd, pwd_len):
        user.value = "TestUser"
        dom.value = ""
        pwd.value = "BadPassword"
        return True

    mock_credui.CredUnPackAuthenticationBufferW.side_effect = mock_unpack
    mock_logon = MagicMock(side_effect=Exception("Logon failure (1326)"))

    with patch("ctypes.windll.credui", mock_credui), \
         patch("ctypes.windll.ole32.CoTaskMemFree") as mock_free, \
         patch("win32security.LogonUser", mock_logon):

        result = _prompt_windows_credentials()
        assert result is False
        mock_free.assert_called_once()


def test_authenticate_user_dispatch(monkeypatch):
    """Test public authenticate_user wrapper dispatch."""
    with patch("wiz.utils.auth._prompt_windows_credentials", return_value=True) as mock_win:
        if sys.platform == "win32":
            res = authenticate_user(parent_hwnd=123)
            assert res is True
            mock_win.assert_called_once_with(
                parent_hwnd=123,
                title="WizDesk Security",
                message="Please enter your Windows credentials to view and export your private recovery key.",
            )


def test_settings_view_private_key_auth_denied(qapp, tmp_path):
    """Test that SettingsView does not open KeyDisplayDialog if OS auth fails."""
    from wiz.storage.db import Database
    from wiz.storage.models import StorageRepository
    from wiz.ui.settings_view import SettingsView
    from wiz.core.crypto import crypto_manager

    db = Database(tmp_path / "test_auth_gate.db")
    repo = StorageRepository(db)
    view = SettingsView(repository=repo, is_dark=True)

    with patch.object(crypto_manager, "load_key_dpapi", return_value=b"0" * 32), \
         patch("wiz.ui.settings_view.authenticate_user", return_value=False) as mock_auth, \
         patch("wiz.ui.settings_view.KeyDisplayDialog.exec") as mock_dialog_exec:

        view._on_view_private_key()
        mock_auth.assert_called_once()
        mock_dialog_exec.assert_not_called()
        assert "Authentication cancelled or failed" in view.status_pill.text()

    view.close()


def test_settings_view_private_key_auth_granted(qapp, tmp_path):
    """Test that SettingsView opens KeyDisplayDialog if OS auth succeeds."""
    from wiz.storage.db import Database
    from wiz.storage.models import StorageRepository
    from wiz.ui.settings_view import SettingsView
    from wiz.core.crypto import crypto_manager

    db = Database(tmp_path / "test_auth_gate.db")
    repo = StorageRepository(db)
    view = SettingsView(repository=repo, is_dark=True)

    with patch.object(crypto_manager, "load_key_dpapi", return_value=b"1" * 32), \
         patch("wiz.ui.settings_view.authenticate_user", return_value=True) as mock_auth, \
         patch("wiz.ui.settings_view.KeyDisplayDialog.exec") as mock_dialog_exec:

        view._on_view_private_key()
        mock_auth.assert_called_once()
        mock_dialog_exec.assert_called_once()

    view.close()


def test_auth_win32security_missing_fails_closed(monkeypatch):
    """Test that missing win32security fails closed and returns False."""
    with patch("wiz.utils.auth.win32security", None):
        assert _prompt_windows_credentials() is False


def test_auth_linux_stub_fails_closed():
    """Test that Linux stub authentication fails closed and returns False."""
    from wiz.utils.auth import _prompt_linux_credentials
    assert _prompt_linux_credentials() is False


def test_authenticate_user_unsupported_platform_fails_closed():
    """Test that unsupported OS platforms fail closed and return False."""
    with patch("sys.platform", "darwin"):
        assert authenticate_user() is False

