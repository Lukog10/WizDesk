# Design Specification: OS Credential Authentication for Private Key Access

**Date**: 2026-09-29  
**Author**: DeepMind Antigravity / Pair Programming Agent  
**Status**: Ready for Implementation  
**Spec Location**: `docs/superpowers/specs/2026-09-29-os-credential-auth-key-security-design.md`

---

## 1. Overview and Goals

WizDesk protects user data with AES-256-GCM encryption and DPAPI local key storage. In Settings, users can view and copy their personal private recovery key.

To prevent unauthorized local users from viewing or exporting the master recovery key if the computer is left unlocked, WizDesk must require native operating system credential verification (Windows password or PIN) before displaying or copying the key.

### Key Objectives
1. **OS-Level Credential Gate**: When the user clicks "View Private Key", invoke the native Windows Security credentials prompt before opening the key display dialog.
2. **Strict Access Denial**: If the user cancels the prompt or provides incorrect credentials, the recovery key must not be decrypted or displayed.
3. **Seamless Windows Integration**: Use Windows native CredUI and Win32 Security APIs without introducing external third-party dependencies.
4. **Linux-Ready Architecture**: Encapsulate authentication in an isolated utility module (`wiz/utils/auth.py`) that abstracts OS-specific authentication mechanisms (Windows CredUI on Windows, PAM/Polkit on Linux).
5. **No Disruptions to Existing Flow**: Normal database operations and automatic background backups continue to run via DPAPI without manual prompts.

---

## 2. Architecture and Data Flow

### 2.1 Module Structure

```
wiz/
  utils/
    auth.py                # OS-level authentication helper (CredUI + LogonUser)
  ui/
    settings_view.py       # Invokes auth gate in _on_view_private_key() and KeyDisplayDialog
```

### 2.2 Sequence of Operations

1. User opens WizDesk Settings and navigates to the "Security & Backups" category.
2. User clicks the "View Private Key" button.
3. `_on_view_private_key()` calls `authenticate_user(parent_hwnd, title, message)` in `wiz.utils.auth`.
4. On Windows, `authenticate_user()` displays `CredUIPromptForWindowsCredentialsW` attached to the WizDesk window handle.
5. User enters their Windows account password or PIN:
   - **Success**: CredUI returns `ERROR_SUCCESS`, credentials are unpacked with `CredUnPackAuthenticationBufferW`, and validated via `win32security.LogonUser`.
   - **Cancel**: CredUI returns `ERROR_CANCELLED` (1223), function returns `False`.
   - **Invalid Password**: `LogonUser` fails with error code 1326, function displays an inline notice and returns `False`.
6. Only if `authenticate_user()` returns `True`, `crypto_manager.load_key_dpapi()` is invoked, and `KeyDisplayDialog` is opened.

---

## 3. Detailed Component Design

### 3.1 `wiz/utils/auth.py`

#### Function: `authenticate_user(parent_hwnd: Optional[int] = None, title: str = "WizDesk Security", message: str = "Please enter your Windows credentials to view and export your private recovery key.") -> bool`

- **Parameters**:
  - `parent_hwnd`: Optional integer representing the parent window HWND so the dialog displays centered and modal to WizDesk.
  - `title`: Dialog title text.
  - `message`: Explanatory prompt message.
- **Return Value**:
  - `bool`: `True` if credentials were authenticated by the OS, `False` otherwise.
- **Windows Implementation**:
  - Uses `ctypes.windll.credui.CredUIPromptForWindowsCredentialsW`.
  - Uses `CREDUIWIN_GENERIC | CREDUIWIN_ENUMERATE_CURRENT_USER` flags.
  - Unpacks the authentication buffer via `CredUnPackAuthenticationBufferW`.
  - Verifies interactive logon session via `win32security.LogonUser(username, domain, password, win32security.LOGON32_LOGON_INTERACTIVE, win32security.LOGON32_PROVIDER_DEFAULT)`.
  - Safely releases allocated CoTaskMem memory using `ctypes.windll.ole32.CoTaskMemFree`.
- **Cross-Platform Fallback**:
  - If running on Linux or non-Windows, provides a stub that can be wired to PAM/Polkit, currently returning `True` or prompting via system dialogue.

### 3.2 `wiz/ui/settings_view.py`

- In `_on_view_private_key(self)`:
  - Obtain the current window's native HWND: `parent_hwnd = int(self.window().winId()) if hasattr(self.window(), "winId") else None`.
  - Call `authenticate_user(parent_hwnd=parent_hwnd, title="WizDesk Security", message="Please enter your Windows credentials to view your private recovery key.")`.
  - If authentication fails or is cancelled, show a brief warning pill/dialog: "Authentication required to view your recovery key." and return immediately without loading or displaying the key.
- In `KeyDisplayDialog`:
  - Retain the key display, copy button, and done button.
  - Key is only loaded into the dialog after successful OS authentication.

---

## 4. Error Handling and Edge Cases

1. **User Cancels Dialog**:
   - `CredUIPromptForWindowsCredentialsW` returns `1223` (`ERROR_CANCELLED`).
   - Handled gracefully: no exception raised, returns `False`.
2. **Incorrect Password**:
   - `win32security.LogonUser` raises an exception with error code `1326` (`ERROR_LOGON_FAILURE`).
   - Caught and logged, user is shown an "Incorrect credentials" message box or pill, returns `False`.
3. **No Password Set on Local Account**:
   - `win32security.LogonUser` succeeds with empty password if the system policy permits blank password console logons.
4. **Domain / Microsoft Accounts**:
   - `CredUnPackAuthenticationBufferW` handles UPN, domain\username, or local usernames transparently.

---

## 5. Testing Plan

1. **Unit Tests (`tests/test_auth.py`)**:
   - Mock `CredUIPromptForWindowsCredentialsW` and `LogonUser` to verify:
     - Return code `0` with valid logon returns `True`.
     - Return code `1223` (cancellation) returns `False`.
     - Logon failure exception returns `False`.
     - Buffer memory cleanup runs reliably in finally blocks.
2. **Integration Tests (`tests/test_sidebar_and_shell.py`)**:
   - Test `_on_view_private_key` with mocked `authenticate_user`:
     - When `authenticate_user` returns `False`, `KeyDisplayDialog` is never instantiated or displayed.
     - When `authenticate_user` returns `True`, `KeyDisplayDialog` is opened.
