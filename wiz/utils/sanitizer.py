"""Data sanitization and privacy redaction utilities for WizDesk."""

from typing import Optional

PASSWORD_MANAGER_APPS = {
    "1password.exe",
    "bitwarden.exe",
    "keepass.exe",
    "keepassxc.exe",
    "lastpass.exe",
    "dashlane.exe",
    "enpass.exe",
    "nordpass.exe",
    "authy.exe",
}

SENSITIVE_TITLE_KEYWORDS = (
    "inprivate",
    "incognito",
    "private browsing",
    "master password",
    "sign in",
    "login",
    "log in",
    "logon",
    "banking",
    "bank",
    "credit card",
    "two-factor",
    "2-factor",
    "2fa",
    "authenticator",
    "one-time password",
    "otp",
)


def clean_app_name(app_name: Optional[str]) -> str:
    """
    Remove executable file extensions (e.g. .exe) from application names for clean display.
    Example: 'Antigravity IDE.exe' -> 'Antigravity IDE', 'zen.exe' -> 'zen'.
    """
    if not app_name:
        return "Unknown"
    name = app_name.strip()
    if name.lower().endswith(".exe"):
        name = name[:-4].strip()
    return name or "Unknown"


def sanitize_window_title(window_title: Optional[str], app_name: Optional[str] = "") -> str:
    """Sanitize and redact sensitive or confidential window titles before recording."""
    if not window_title:
        return ""

    app_clean = (app_name or "").lower().strip()
    app_base = app_clean[:-4] if app_clean.endswith(".exe") else app_clean
    if app_clean in PASSWORD_MANAGER_APPS or f"{app_base}.exe" in PASSWORD_MANAGER_APPS:
        return "[Password Manager]"

    title_lower = window_title.lower()
    for kw in SENSITIVE_TITLE_KEYWORDS:
        if kw in title_lower:
            return "[Private Activity]"

    return window_title.strip()

