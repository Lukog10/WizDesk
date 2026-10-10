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

SYSTEM_EXCLUDED_PROCESSES = {
    "explorer.exe",
    "explorer",
    "searchhost.exe",
    "searchhost",
    "searchapp.exe",
    "searchapp",
    "searchui.exe",
    "searchui",
    "cortana.exe",
    "cortana",
    "lockapp.exe",
    "lockapp",
    "logonui.exe",
    "logonui",
    "consent.exe",
    "consent",
    "credentialuibroker.exe",
    "credentialuibroker",
    "shellexperiencehost.exe",
    "shellexperiencehost",
    "startmenuexperiencehost.exe",
    "startmenuexperiencehost",
    "shellhost.exe",
    "shellhost",
    "textinputhost.exe",
    "textinputhost",
    "pickerhost.exe",
    "pickerhost",
    "screenclippinghost.exe",
    "screenclippinghost",
}

SYSTEM_EXCLUDED_TITLES = {
    "program manager",
    "windows default lock screen",
    "search",
    "start",
    "task switching",
    "task view",
    "snap assist",
    "system tray overflow window",
    "system tray overflow window.",
    "quick settings",
    "notification center",
    "new notification",
    "windows input experience",
}


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


def is_system_excluded(
    app_name: Optional[str],
    window_title: Optional[str] = "",
    pid: Optional[int] = None,
) -> bool:
    """
    Determine whether an active window or process represents Windows system shell
    infrastructure (e.g. Windows Explorer, Search, Lock Screen, Desktop wallpaper)
    and should therefore be excluded from activity logging.
    Task Manager and WizDesk are explicitly tracked and not excluded.
    """
    # 1. Check empty or unidentifiable window states
    raw_app = (app_name or "").strip()
    title = (window_title or "").strip()
    title_lower = title.lower()

    if not raw_app and not title:
        return True

    # 2. Check process name against system exclusions
    app_lower = raw_app.lower()
    clean_app_lower = clean_app_name(raw_app).lower()

    if app_lower in SYSTEM_EXCLUDED_PROCESSES or clean_app_lower in SYSTEM_EXCLUDED_PROCESSES:
        return True

    # 3. Check specific shell host frames
    if clean_app_lower == "applicationframehost":
        if not title or title_lower in SYSTEM_EXCLUDED_TITLES:
            return True

    # 4. Check window title against system titles (e.g. Program Manager desktop, Search popup)
    if title_lower in SYSTEM_EXCLUDED_TITLES:
        return True

    # 5. Check unknown app with empty title
    if app_lower in ("unknown", "") and not title:
        return True

    return False


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
