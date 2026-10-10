"""Operating System credential authentication utilities for WizDesk."""

import os
import sys
from typing import Optional

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    try:
        import win32security
    except ImportError:
        win32security = None

    class _CREDUI_INFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hwndParent", wintypes.HWND),
            ("pszMessageText", wintypes.LPCWSTR),
            ("pszCaptionText", wintypes.LPCWSTR),
            ("hbmBanner", wintypes.HBITMAP),
        ]

    # Setup argtypes once at import time
    try:
        _credui = ctypes.windll.credui
        _credui.CredUIPromptForWindowsCredentialsW.argtypes = [
            ctypes.POINTER(_CREDUI_INFOW),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.ULONG),
            wintypes.LPCVOID,
            wintypes.ULONG,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.ULONG),
            ctypes.POINTER(wintypes.BOOL),
            wintypes.DWORD,
        ]
        _credui.CredUIPromptForWindowsCredentialsW.restype = wintypes.DWORD

        _credui.CredUnPackAuthenticationBufferW.argtypes = [
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.ULONG,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        _credui.CredUnPackAuthenticationBufferW.restype = wintypes.BOOL
    except Exception:
        pass


CREDUIWIN_GENERIC = 0x0001
CREDUIWIN_CHECKBOX = 0x0002
CREDUIWIN_AUTHPACKAGE_ONLY = 0x0010
CREDUIWIN_IN_CRED_ONLY = 0x0020
CREDUIWIN_ENUMERATE_ADMINS = 0x0100
CREDUIWIN_ENUMERATE_CURRENT_USER = 0x0200

ERROR_SUCCESS = 0
ERROR_CANCELLED = 1223


def _prompt_windows_credentials(
    parent_hwnd: Optional[int] = None,
    title: str = "WizDesk Security",
    message: str = "Please enter your Windows credentials to view and export your private recovery key.",
) -> bool:
    """
    Prompt for Windows user credentials via CredUI and verify with LogonUser.
    Returns True if authentication succeeds, False if cancelled or invalid.
    """
    if win32security is None:
        print("[Auth] Security error: win32security is not available. Failing closed.")
        return False

    credui = ctypes.windll.credui
    ole32 = ctypes.windll.ole32

    ui_info = _CREDUI_INFOW()
    ui_info.cbSize = ctypes.sizeof(_CREDUI_INFOW)
    ui_info.hwndParent = wintypes.HWND(parent_hwnd or 0)
    ui_info.pszMessageText = message
    ui_info.pszCaptionText = title
    ui_info.hbmBanner = None

    auth_package = wintypes.ULONG(0)
    out_auth_buffer = ctypes.c_void_p(0)
    out_auth_buffer_size = wintypes.ULONG(0)
    save_checked = wintypes.BOOL(False)

    flags = CREDUIWIN_GENERIC | CREDUIWIN_ENUMERATE_CURRENT_USER

    status = credui.CredUIPromptForWindowsCredentialsW(
        ctypes.byref(ui_info),
        0,
        ctypes.byref(auth_package),
        None,
        0,
        ctypes.byref(out_auth_buffer),
        ctypes.byref(out_auth_buffer_size),
        ctypes.byref(save_checked),
        flags,
    )

    if status != ERROR_SUCCESS:
        return False

    if not out_auth_buffer.value or out_auth_buffer_size.value == 0:
        return False

    try:
        user_buf = ctypes.create_unicode_buffer(512)
        domain_buf = ctypes.create_unicode_buffer(512)
        password_buf = ctypes.create_unicode_buffer(512)
        user_len = wintypes.DWORD(512)
        domain_len = wintypes.DWORD(512)
        password_len = wintypes.DWORD(512)

        unpacked = credui.CredUnPackAuthenticationBufferW(
            0,
            out_auth_buffer,
            out_auth_buffer_size,
            user_buf,
            ctypes.byref(user_len),
            domain_buf,
            ctypes.byref(domain_len),
            password_buf,
            ctypes.byref(password_len),
        )

        if not unpacked:
            return False

        user = user_buf.value
        domain = domain_buf.value
        password = password_buf.value

        try:
            # Security verification: Verify user matches currently logged in Windows user
            current_user = os.environ.get("USERNAME", "")
            if current_user:
                clean_user = user.split("\\")[-1].split("@")[0].strip().lower()
                if clean_user != current_user.strip().lower():
                    print(f"[Auth] Security error: User '{user}' does not match active login '{current_user}'. Failing closed.")
                    return False

            token = win32security.LogonUser(
                user,
                domain if domain else None,
                password,
                win32security.LOGON32_LOGON_INTERACTIVE,
                win32security.LOGON32_PROVIDER_DEFAULT,
            )
            if token:
                token.Close()
                return True
        except Exception:
            return False

    finally:
        # Zeroize sensitive plaintext password buffer in memory before releasing
        try:
            ctypes.memset(ctypes.byref(password_buf), 0, ctypes.sizeof(password_buf))
        except Exception:
            pass
        if out_auth_buffer.value:
            ole32.CoTaskMemFree(out_auth_buffer)

    return False


def _prompt_linux_credentials(
    title: str = "WizDesk Security",
    message: str = "Please enter your password to view and export your private recovery key.",
) -> bool:
    """Placeholder for Linux PAM/Polkit authentication in upcoming Linux build."""
    print("[Auth] Linux PAM/Polkit integration is not yet active. Failing closed.")
    return False


def authenticate_user(
    parent_hwnd: Optional[int] = None,
    title: str = "WizDesk Security",
    message: str = "Please enter your Windows credentials to view and export your private recovery key.",
) -> bool:
    """
    Authenticate the current user against native operating system credentials.
    On Windows, this presents the Windows Security dialog and verifies with LogonUser.
    """
    if sys.platform == "win32":
        return _prompt_windows_credentials(parent_hwnd=parent_hwnd, title=title, message=message)
    elif sys.platform.startswith("linux"):
        return _prompt_linux_credentials(title=title, message=message)
    print(f"[Auth] Platform {sys.platform} does not have an active credential verifier. Failing closed.")
    return False
